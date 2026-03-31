# News Alpha — Full System Writeup & Antigravity Build Prompt

---

## PART 1: SYSTEM OVERVIEW & DESIGN RATIONALE

### What News Alpha Is

News Alpha is a semantic market sentiment analyzer and signal generation platform built for Wall Street club analysts. It ingests real-time financial news, processes it through a multi-layer NLP pipeline, and surfaces high-conviction market signals with plain-English rationale. The goal is a single workbench where any analyst can arrive, see what is moving narratively in the market today, drill into a sector, and understand *why* a signal fired — without having to read hundreds of headlines manually.

The system is not a news aggregator. It is a signal layer on top of news. The distinction matters: every headline that enters the pipeline is scored, attributed to sectors, and checked against a rolling 30-day memory of what "normal" looks like. Only when something deviates meaningfully from that normal does it surface as a signal. Analysts see the anomaly, not the noise.

---

### Core Components

**1. Ingestion Worker**
A scheduled job (runs every 15 minutes) that pulls headlines from RSS feeds, financial news scrapers, and APIs (MoneyControl, ET Markets, Bloomberg RSS, NSE announcements). Each headline is deduplicated by hashing the source and normalized text, timestamped, cleaned, and pushed through the scoring pipeline before being stored.

**2. Embedding Layer**
Every headline is converted to a 384-dimensional dense vector using `all-MiniLM-L6-v2` from Sentence-Transformers. These embeddings are stored in Postgres via the `pgvector` extension alongside the raw headline. They are never recomputed after initial ingestion — this keeps the rolling-window similarity queries cheap.

**3. Surprise Score Engine (Three-Layer)**
The core alpha logic. Measures how much today's headlines deviate from the 30-day baseline across three orthogonal dimensions:

- **Layer 1 — Lexical Surprise (weight: 0.25):** Fits a TF-IDF vectorizer on the 30-day headline corpus. Transforms both the 30-day corpus and today's headlines into averaged TF-IDF vectors. Computes cosine distance between the two. A sudden flood of rare vocabulary (e.g. "moratorium", "ED investigation", "NPA divergence") pulls the today-vector far from the baseline-vector and produces a high lexical surprise score. Fast and noisy — acts as a trip wire.

- **Layer 2 — Semantic Surprise (weight: 0.45):** Computes the cosine distance between the mean of today's headline embeddings and the rolling mean embedding (precomputed nightly per sector over 30 days). Unlike lexical surprise, this catches *meaning* shifts even when the vocabulary stays similar. If headlines about banking move from "growth and lending" narratives to "stress and provisioning" narratives, semantic surprise detects it even if individual words overlap. This is the most reliable layer and gets the highest weight.

- **Layer 3 — Event-Type Surprise (weight: 0.30):** Classifies each headline into one of several event types: `earnings`, `regulatory_action`, `management_change`, `macro_shock`, `merger_acquisition`, `legal`, `rating_change`. Tracks the frequency of each event type per sector daily. Computes a spike score by comparing today's event-type frequency against the 30-day daily average. A sudden cluster of `regulatory_action` events in Banking — even if the language is normal — is a meaningful signal.

**Composite Score:** `score = 0.25×lexical + 0.45×semantic + 0.30×event_type`

A signal fires when `score > 0.65` OR when at least 2 of the 3 layers individually exceed their per-layer threshold (0.50). This dual-trigger prevents any single noisy layer from flooding the feed.

**4. Sector Attribution Model**
A soft multi-label classifier that maps each headline to a probability distribution across sectors: Banking, IT, Auto, Pharma, FMCG, Energy, Infrastructure. Built on top of frozen Sentence-Transformer embeddings with a One-vs-Rest Logistic Regression classifier (C=0.5, regularized). Trained on ~300 manually verified headlines auto-labeled in batches using the Anthropic API.

Critically, the output is a probability distribution, not a hard label:
```json
{"Banking": 0.62, "NBFC": 0.28, "Auto": 0.10}
```
This allows a headline like "RBI tightens NBFC liquidity norms ahead of auto loan season" to correctly spread attribution across three sectors rather than forcing a single bucket. Downstream signal aggregation uses these probabilities as weights.

**5. Signal Generator with LLM Rationale**
When the Surprise Score engine fires a signal, the top 8 contributing headlines are passed to the Anthropic API (`claude-sonnet-4-20250514`) with a structured prompt requesting exactly 3 bullet points: (1) what narrative shift is occurring, (2) which sub-sector or stock type is most exposed, (3) whether this is risk-on or risk-off. The rationale is stored in the `signals` table and displayed verbatim on the signal card in the UI. This is what makes analysts trust the output — every signal comes with a human-readable "why."

**6. FastAPI Backend**
Four primary endpoints:
- `GET /signals` — ranked signal feed, filterable by sector and conviction level
- `GET /sector/{sector_name}` — sector deep-dive with rolling sentiment and surprise trend
- `GET /search` — semantic search over all headlines using pgvector cosine similarity
- `GET /signal/{signal_id}/rationale` — fetch or lazily generate the LLM rationale

**7. React Analyst Dashboard**
Two primary views. The Signal Feed (homepage) shows a ranked list of fired signals with sector badges, surprise scores, conviction levels, and expandable LLM rationale. The Sector View shows a 7-day rolling sentiment line chart, surprise score trend, and live headline feed for the selected sector. A persistent semantic search bar sits in the header.

---

### Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE headlines (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source       TEXT NOT NULL,
  raw_text     TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  ingested_at  TIMESTAMPTZ DEFAULT NOW(),
  embedding    VECTOR(384),
  UNIQUE(source, raw_text)
);

CREATE TABLE headline_scores (
  headline_id    UUID REFERENCES headlines(id),
  surprise       FLOAT,
  sentiment      FLOAT,
  sector_probs   JSONB,
  event_type     TEXT,
  scored_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rolling_baselines (
  sector         TEXT NOT NULL,
  computed_at    TIMESTAMPTZ NOT NULL,
  mean_embedding VECTOR(384),
  PRIMARY KEY (sector, computed_at)
);

CREATE TABLE signals (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sector         TEXT,
  triggered_at   TIMESTAMPTZ,
  surprise_val   FLOAT,
  layers         JSONB,
  rationale      TEXT,
  headline_ids   UUID[],
  conviction     TEXT CHECK (conviction IN ('low','medium','high'))
);
```

---

### TF-IDF Lexical Surprise — Deep Dive

TF-IDF assigns each word a weight based on two factors: how often it appears today (term frequency) and how rare it is across the 30-day corpus (inverse document frequency). Words like "RBI" or "earnings" appear every day so they receive low IDF weight. A word like "moratorium" that suddenly floods today's headlines but was barely present last month receives a high IDF weight — it pulls the today-vector sharply away from the baseline-vector.

Key implementation choices:
- `ngram_range=(1,2)` — bigrams matter in financial text. "NPA divergence" as a bigram is a specific regulatory signal that individual words would miss.
- Fit on baseline, transform today — IDF weights are calibrated to what is "normal". Words absent from the baseline receive maximum IDF penalty.
- `sublinear_tf=True` — uses log(1+tf) instead of raw tf, compressing outlier term frequencies in short headlines.
- `min_df=3, max_df=0.85` — filters out hapax terms and near-universal filler words.
- Custom financial tokenizer preserving hyphenated compounds: "non-performing", "mark-to-market", "write-off".

Weakness: sensitive to source mix changes and weekend corpus size differences. This is why it is the lowest-weighted layer (0.25) and acts as a trip wire rather than a definitive signal.

---

### Semantic Surprise — Deep Dive

Operates on the dense embedding space rather than vocabulary. The rolling mean embedding for each sector is precomputed nightly as the arithmetic mean of all 384-dimensional headline embeddings from the past 30 days for that sector. This rolling mean is the "center of gravity" of normal narrative for that sector.

At scoring time, today's headline embeddings for a sector are averaged into a single vector, and cosine distance is computed against the rolling mean. Because the embedding space encodes meaning rather than surface vocabulary, this layer catches narrative shifts even when phrasing stays similar. A shift in Banking headlines from "credit growth and expansion" to "stress tests and provisioning" will produce a high semantic surprise even if individual words like "bank", "loan", and "RBI" appear in both periods.

This layer gets the highest weight (0.45) because it is the most robust to surface noise and best captures the genuine underlying narrative shift that matters for market signal generation.

---

### Event-Type Surprise — Deep Dive

Each headline is classified into one of: `earnings`, `regulatory_action`, `management_change`, `macro_shock`, `merger_acquisition`, `legal`, `rating_change`, `other`. Classification uses a small zero-shot prompt to the Anthropic API in batches during ingestion, cached in the `headline_scores` table.

The insight is that even if the language of regulatory headlines is familiar, a sudden *cluster* of regulatory events in a sector within a single day is anomalous. The spike score for each event type is: `min(today_count / 30day_daily_avg / 5, 1.0)`. The maximum spike across all event types for a sector becomes the event-type surprise score. Normalizing by 5 means a 5× spike in any event type saturates the score at 1.0.

This layer captures structural regime shifts — a single bad earnings headline is noise; five management change headlines across Banking in one day is a signal.

---

## PART 2: ANTIGRAVITY BUILD PROMPT

---

> **Copy everything below this line verbatim into Antigravity.**

---

# BUILD PROMPT: News Alpha — Wall Street Club Analyst Workbench

## Project identity

Build a full-stack web application called **News Alpha**. It is a semantic market sentiment analyzer and signal generation platform for a Wall Street club. The primary users are equity analysts who need a single place to monitor market narrative shifts, identify anomalies, and get plain-English explanations for why a signal fired.

The aesthetic should feel like a Bloomberg terminal crossed with a modern data product. Dark-first. Dense with information but never cluttered. Every pixel earns its place. Think: Vercel dashboard meets Refinitiv Eikon. The vibe is "serious tool built by people who trade."

---

## Tech stack

**Frontend:** React (Vite), TailwindCSS, Recharts for charts, React Query for data fetching.

**Backend:** Python, FastAPI, SQLAlchemy (async), asyncpg.

**Database:** PostgreSQL with pgvector extension.

**ML/NLP:**
- `sentence-transformers` (model: `all-MiniLM-L6-v2`)
- `scikit-learn` (TfidfVectorizer, LogisticRegression, OneVsRestClassifier)
- `transformers` (FinBERT for sentiment scoring)
- `anthropic` Python SDK for LLM rationale generation

**Queue/Scheduler:** APScheduler (in-process) or Celery Beat for the ingestion worker.

**Deployment target:** Railway or Render. Single Dockerfile.

---

## Database schema (implement exactly)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE headlines (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source       TEXT NOT NULL,
  raw_text     TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  ingested_at  TIMESTAMPTZ DEFAULT NOW(),
  embedding    VECTOR(384),
  UNIQUE(source, raw_text)
);

CREATE TABLE headline_scores (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  headline_id UUID REFERENCES headlines(id) ON DELETE CASCADE,
  surprise    FLOAT,
  sentiment   FLOAT,
  sector_probs JSONB,
  event_type  TEXT,
  scored_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rolling_baselines (
  sector         TEXT NOT NULL,
  computed_at    TIMESTAMPTZ NOT NULL,
  mean_embedding VECTOR(384),
  PRIMARY KEY (sector, computed_at)
);

CREATE TABLE signals (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sector       TEXT NOT NULL,
  triggered_at TIMESTAMPTZ DEFAULT NOW(),
  surprise_val FLOAT NOT NULL,
  layers       JSONB,
  rationale    TEXT,
  headline_ids UUID[],
  conviction   TEXT CHECK (conviction IN ('low','medium','high'))
);
```

Create indexes:
```sql
CREATE INDEX ON headlines USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON signals (triggered_at DESC);
CREATE INDEX ON headline_scores (headline_id);
```

---

## Backend: file structure

```
backend/
  main.py                  # FastAPI app entry point
  config.py                # env vars, constants
  models.py                # SQLAlchemy ORM models
  database.py              # async engine + session factory
  routers/
    signals.py             # GET /signals, GET /signal/{id}/rationale
    sectors.py             # GET /sector/{sector_name}
    search.py              # GET /search
  pipeline/
    ingestion.py           # RSS fetcher + dedup + normalize
    embedder.py            # SentenceTransformer wrapper
    surprise_engine.py     # Three-layer Surprise Score
    sector_attributor.py   # Multi-label sector classifier
    sentiment_scorer.py    # FinBERT wrapper
    event_classifier.py    # Event-type classifier via Anthropic API
    signal_generator.py    # Fires signals + generates rationale
    baseline_updater.py    # Nightly rolling mean embedding job
  scheduler.py             # APScheduler job definitions
```

---

## Backend: implement each module

### `pipeline/embedder.py`

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]
```

### `pipeline/surprise_engine.py`

```python
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.spatial.distance import cosine
from collections import Counter
import re

WEIGHTS = {"lexical": 0.25, "semantic": 0.45, "event": 0.30}
COMPOSITE_THRESHOLD = 0.65
LAYER_THRESHOLD = 0.50

def financial_tokenizer(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"(?<=\w)-(?=\w)", "_", text)
    return text.split()

def build_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        tokenizer=financial_tokenizer,
        max_features=8000,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.85,
        sublinear_tf=True,
        strip_accents="unicode",
    )

def lexical_surprise(today_texts: list[str], baseline_texts: list[str]) -> float:
    if not today_texts or not baseline_texts:
        return 0.0
    vec = build_vectorizer()
    vec.fit(baseline_texts)
    today_vec = np.asarray(vec.transform(today_texts).mean(axis=0))
    base_vec  = np.asarray(vec.transform(baseline_texts).mean(axis=0))
    return float(cosine(today_vec.flatten(), base_vec.flatten()))

def semantic_surprise(today_embeddings: np.ndarray, rolling_mean: np.ndarray) -> float:
    if len(today_embeddings) == 0:
        return 0.0
    today_mean = np.mean(today_embeddings, axis=0)
    return float(cosine(today_mean, rolling_mean))

def event_surprise(today_events: list[str], baseline_counts: Counter, baseline_days: int = 30) -> float:
    if not today_events:
        return 0.0
    today_counts = Counter(today_events)
    spikes = []
    for event, count in today_counts.items():
        avg = baseline_counts.get(event, 0) / max(baseline_days, 1)
        avg = max(avg, 0.1)
        spikes.append(min(count / avg / 5.0, 1.0))
    return max(spikes) if spikes else 0.0

def composite_score(lexical: float, semantic: float, event: float) -> dict:
    scores = {"lexical": lexical, "semantic": semantic, "event": event}
    composite = sum(WEIGHTS[k] * v for k, v in scores.items())
    layers_triggered = [k for k, v in scores.items() if v > LAYER_THRESHOLD]
    fired = composite > COMPOSITE_THRESHOLD or len(layers_triggered) >= 2
    conviction = "high" if composite > 0.80 else "medium" if composite > 0.65 else "low"
    return {
        "score": round(composite, 4),
        "layers": {k: round(v, 4) for k, v in scores.items()},
        "layers_triggered": layers_triggered,
        "fired": fired,
        "conviction": conviction,
    }
```

### `pipeline/sector_attributor.py`

```python
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
import numpy as np
import pickle, os

SECTORS = ["Banking", "IT", "Auto", "Pharma", "FMCG", "Energy", "Infrastructure"]
MODEL_PATH = "sector_model.pkl"

class SectorAttributor:
    def __init__(self):
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self.mlb = MultiLabelBinarizer(classes=SECTORS)
        self.clf = OneVsRestClassifier(LogisticRegression(C=0.5, max_iter=500))
        self.trained = False

    def train(self, texts: list[str], labels: list[list[str]]):
        embeddings = self.encoder.encode(texts, batch_size=32, normalize_embeddings=True)
        Y = self.mlb.fit_transform(labels)
        self.clf.fit(embeddings, Y)
        self.trained = True
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({"clf": self.clf, "mlb": self.mlb}, f)

    def load(self):
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                data = pickle.load(f)
            self.clf = data["clf"]
            self.mlb = data["mlb"]
            self.trained = True

    def predict_proba(self, text: str) -> dict[str, float]:
        if not self.trained:
            self.load()
        emb = self.encoder.encode([text], normalize_embeddings=True)
        probs = [est.predict_proba(emb)[0][1] for est in self.clf.estimators_]
        return {sector: round(float(p), 3) for sector, p in zip(SECTORS, probs)}
```

### `pipeline/signal_generator.py`

```python
import anthropic

client = anthropic.Anthropic()

def generate_rationale(headlines: list[str], sector: str, score: float, layers: dict) -> str:
    layers_str = ", ".join(f"{k}: {v:.2f}" for k, v in layers.items())
    prompt = f"""You are a quant analyst assistant for a Wall Street investment club.

These headlines triggered a market anomaly signal for the {sector} sector.
Composite Surprise Score: {score:.3f}
Layer breakdown: {layers_str}

Headlines that fired this signal:
{chr(10).join(f"- {h}" for h in headlines[:8])}

Write exactly 3 bullet points. Each bullet must be 15 words or fewer. Be specific and actionable.
1. What narrative shift is occurring in this sector
2. Which sub-sector, stock type, or name is most exposed
3. Whether this is risk-on or risk-off and why

No preamble, no generic statements. Just the 3 bullets."""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

def classify_event_type(headline: str) -> str:
    EVENT_TYPES = ["earnings", "regulatory_action", "management_change",
                   "macro_shock", "merger_acquisition", "legal", "rating_change", "other"]
    prompt = f"""Classify this financial headline into exactly one event type.
Event types: {', '.join(EVENT_TYPES)}
Headline: "{headline}"
Return only the event type label, nothing else."""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}]
    )
    result = msg.content[0].text.strip().lower()
    return result if result in EVENT_TYPES else "other"
```

### `routers/signals.py`

```python
from fastapi import APIRouter, Query
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/signals", tags=["signals"])

@router.get("")
async def get_signals(
    sector: str | None = None,
    conviction: str | None = None,
    since_hours: int = 24,
    limit: int = 50,
):
    """Main signal feed. Returns signals sorted by surprise score descending."""
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    # query signals table, filter by sector/conviction/since, order by surprise_val DESC
    ...

@router.get("/{signal_id}/rationale")
async def get_rationale(signal_id: str):
    """Fetch existing rationale or lazily generate it if missing."""
    # fetch signal from DB
    # if rationale is None: fetch contributing headlines, call generate_rationale(), store, return
    ...
```

### `routers/search.py`

```python
from fastapi import APIRouter, Query

router = APIRouter(prefix="/search", tags=["search"])

@router.get("")
async def semantic_search(q: str, limit: int = 20):
    """Semantic search over all headlines using pgvector cosine similarity."""
    # embed query string
    # SELECT h.*, hs.sector_probs, hs.sentiment, hs.surprise
    # FROM headlines h JOIN headline_scores hs ON h.id = hs.headline_id
    # ORDER BY h.embedding <=> $1::vector LIMIT $2
    ...
```

---

## Frontend: pages and components

### Page 1: Signal Feed (route: `/`)

**Layout:** Full-height dark sidebar (240px) listing sectors with real-time signal counts. Main content area shows the signal feed.

**Header:** Logo "NEWS ALPHA" in monospace. Semantic search bar. Live ingestion status indicator (green pulse when worker ran < 5 min ago, amber otherwise).

**Signal card component** — build `<SignalCard />` with:
- Top row: sector badge (colored by sector), conviction badge (`HIGH` / `MEDIUM` / `LOW` in respective colors), surprise score as a numeric readout (e.g. `0.812`), time ago (e.g. "14 min ago")
- Layer breakdown: three small horizontal bars labeled `LEX`, `SEM`, `EVT` showing the per-layer scores. Fill color transitions from gray (low) to amber (medium) to red (high).
- Rationale: three bullet points rendered as plain text. Show a skeleton loader while fetching.
- Collapsed by default. Clicking the card expands to show the contributing headlines (max 8, each with its own sentiment indicator dot: green positive, red negative, gray neutral).
- Footer: "Show sector view →" link.

**Filter bar:** pill toggles for sectors and conviction level. Multi-select. Resets to "All" by default.

### Page 2: Sector View (route: `/sector/:sectorName`)

**Layout:** Same sidebar. Main area split into top charts row and bottom headline feed.

**Top left chart:** 7-day rolling sentiment line chart using Recharts `<LineChart>`. X axis: dates. Y axis: -1 to +1. Line color: green above 0, red below. Zero-line dashed. Chart title: "Rolling sentiment — {sector}".

**Top right chart:** 7-day surprise score bar chart using Recharts `<BarChart>`. Bar fill: color-coded by conviction threshold (gray < 0.50, amber 0.50–0.65, red > 0.65). Chart title: "Surprise score — {sector}".

**Headline feed:** Scrollable list of the most recent 50 headlines for this sector. Each row: timestamp, sentiment dot, sector probability badge (shows the sector probability as a percentage, e.g. "Banking 72%"), headline text. Clicking a headline opens a drawer on the right showing full scores.

### Page 3: Search Results (route: `/search?q=...`)

**Layout:** Full width, no sidebar. Search bar centered at top (large, prominent). Results below as cards: headline text, source badge, timestamp, sector probs as small pills, sentiment score, cosine similarity score shown as "Relevance: 94%".

---

## Frontend: design tokens (implement as CSS variables)

```css
:root {
  --bg-primary: #0a0a0a;
  --bg-secondary: #111111;
  --bg-tertiary: #1a1a1a;
  --bg-card: #141414;
  --border: #222222;
  --border-bright: #333333;

  --text-primary: #e8e8e8;
  --text-secondary: #888888;
  --text-muted: #555555;

  --accent-red: #ff3b3b;
  --accent-amber: #f5a623;
  --accent-green: #22c55e;
  --accent-blue: #3b82f6;

  --conviction-high: #ff3b3b;
  --conviction-medium: #f5a623;
  --conviction-low: #888888;

  --sector-banking: #3b82f6;
  --sector-it: #8b5cf6;
  --sector-auto: #f5a623;
  --sector-pharma: #22c55e;
  --sector-fmcg: #06b6d4;
  --sector-energy: #f97316;
  --sector-infra: #84cc16;

  --font-mono: "JetBrains Mono", "Fira Code", monospace;
  --font-sans: "IBM Plex Sans", sans-serif;
}
```

Use `--font-mono` for scores, numeric readouts, timestamps, and the logo. Use `--font-sans` for all body text and labels. Load both from Google Fonts.

---

## Ingestion sources to implement

Implement RSS polling for these sources (add more as needed):
- `https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms` — ET Markets
- `https://www.moneycontrol.com/rss/business.xml` — Moneycontrol Business
- `https://feeds.feedburner.com/ndtvprofit-latest` — NDTV Profit

Parse each with `feedparser`. Normalize: strip HTML tags, decode entities, truncate to 280 characters, lowercase for hashing.

---

## Scheduler jobs (implement with APScheduler)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Every 15 minutes: ingest + score
scheduler.add_job(run_ingestion_pipeline, "interval", minutes=15)

# Every night at 02:00 IST: recompute rolling baseline embeddings per sector
scheduler.add_job(update_rolling_baselines, "cron", hour=20, minute=30)  # 20:30 UTC = 02:00 IST

# Every hour: retrain sector attributor if >50 new labeled headlines
scheduler.add_job(maybe_retrain_sector_model, "interval", hours=1)
```

---

## Environment variables required

```
DATABASE_URL=postgresql+asyncpg://user:pass@host/newsalpha
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Sector color coding (use consistently across all components)

| Sector | Color |
|---|---|
| Banking | Blue `#3b82f6` |
| IT | Purple `#8b5cf6` |
| Auto | Amber `#f5a623` |
| Pharma | Green `#22c55e` |
| FMCG | Cyan `#06b6d4` |
| Energy | Orange `#f97316` |
| Infrastructure | Lime `#84cc16` |

---

## Conviction level display rules

- `high` (score > 0.80): red badge, `!` prefix, card has a 1px red left border accent
- `medium` (score 0.65–0.80): amber badge, no border accent
- `low` (score < 0.65 but signal fired via dual-layer trigger): gray badge, reduced opacity card

---

## Key UX behaviors to implement

1. **Polling:** Signal feed auto-refreshes every 5 minutes via React Query `refetchInterval`. Show a subtle "Updated X min ago" counter in the header.
2. **Lazy rationale generation:** If `rationale` is null on a signal, hitting the card triggers a `POST /signal/{id}/generate-rationale` request and shows a shimmer loader for 2–3 seconds while the LLM generates. Do not pre-generate all rationales — generate on first view.
3. **Semantic search debounce:** 400ms debounce on the search input before firing the API request. Show a "Searching semantically across {n} headlines..." micro-copy below the input while loading.
4. **Layer bar animation:** When a signal card expands, animate the LEX/SEM/EVT bars filling from 0 to their actual value over 600ms with an ease-out curve.
5. **Sector sidebar counts:** Show a live count of signals in the last 24h next to each sector name. Highlight sectors with `high` conviction signals in the accent color.
6. **Empty state:** If no signals have fired in the selected time window, show a copy that says "No anomalies detected in the last {X}h. Market narrative is within normal range." Not a generic empty state — make it feel like a deliberate "all clear" readout.

---

## What NOT to build (scope boundaries)

- No user authentication for v1. Treat it as an internal club tool — single shared instance.
- No real-time WebSocket streaming. Polling is sufficient.
- No backtesting or P&L tracking. This is a signal dashboard, not a trading system.
- No mobile-specific layout. Desktop-first only.
- No multi-tenancy. Single Postgres database, single deployment.

---

## Definition of done

The app is complete when:
1. The ingestion worker runs on schedule and correctly populates `headlines` and `headline_scores`.
2. The Surprise Score engine produces a `composite_score` dict for any sector given today's and baseline's data.
3. The Sector Attributor returns a sector probability distribution for any input headline.
4. The signal generator fires a signal and stores a non-null `rationale` for at least one test case.
5. All four API endpoints return correct, well-typed JSON responses.
6. The Signal Feed page renders signal cards with layer bars, conviction badges, and expandable rationale.
7. The Sector View page renders both charts with real data from the DB.
8. Semantic search returns ranked results with similarity scores.
9. The app runs end-to-end in Docker via a single `docker-compose up`.

---

*End of Antigravity build prompt.*

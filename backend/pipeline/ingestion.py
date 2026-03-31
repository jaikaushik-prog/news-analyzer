import feedparser
import hashlib
import asyncio
import os
import joblib
from datetime import datetime, timedelta
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import Headline, HeadlineScore, Signal, RollingBaseline, FeedMetadata
from pipeline.embedder import embedder
from pipeline.surprise_engine import lexical_surprise, semantic_surprise, event_surprise, composite_score, build_vectorizer
from pipeline.sector_attributor import attributor
from pipeline.sentiment_scorer import scorer
from pipeline.event_classifier import classifier
from config import settings
from filelock import FileLock

VECTORIZER_PATH = "vectorizer.joblib"
LOCK_PATH = "vectorizer.lock"

def _hash_text(source: str, text: str) -> str:
    return hashlib.md5(f"{source}:{text}".encode('utf-8')).hexdigest()

async def fetch_rss(session: AsyncSession, url: str, source_name: str) -> list[dict]:
    print(f"Fetching RSS for {source_name}...")
    
    # 1. Get metadata for HTTP headers
    stmt = select(FeedMetadata).where(FeedMetadata.feed_url == url)
    res = await session.execute(stmt)
    meta = res.scalar_one_or_none()
    
    etag = meta.etag if meta else None
    last_mod = meta.last_modified if meta else None
    
    try:
        # Use feedparser with ETag and Last-Modified
        feed = feedparser.parse(url, etag=etag, modified=last_mod)
        
        # If 304 Not Modified, return empty
        if feed.status == 304:
            print(f"  -> {source_name}: 304 Not Modified")
            return []
            
        # Update metadata
        if not meta:
            meta = FeedMetadata(feed_url=url)
            session.add(meta)
        
        meta.etag = getattr(feed, 'etag', None)
        meta.last_modified = getattr(feed, 'modified', None)
        meta.last_fetched_at = datetime.utcnow()
        
        results = []
        for entry in feed.entries:
            # Parse published date
            pub_date = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            
            results.append({
                "source": source_name,
                "raw_text": getattr(entry, 'title', ''),
                "published_at": pub_date
            })
        return results
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []

async def get_event_frequencies(session: AsyncSession) -> dict:
    """Calculate dynamic event frequencies from the last 30 days of data."""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    stmt = select(
        HeadlineScore.event_type, 
        func.count(HeadlineScore.id).label('count')
    ).where(HeadlineScore.scored_at >= thirty_days_ago).group_by(HeadlineScore.event_type)
    
    res = await session.execute(stmt)
    rows = res.all()
    
    total = sum(r.count for r in rows)
    if total == 0:
        # Fallback to defaults
        return {
            "Earnings Report": 0.1, "M&A": 0.05, "Regulatory": 0.08, "Management Change": 0.04, 
            "Product Launch": 0.06, "Macroeconomic": 0.2, "Legal/Lawsuit": 0.05, "Analyst Rating": 0.1, "Other": 0.32
        }
    
    return {r.event_type: r.count / total for r in rows}

async def get_or_warmup_vectorizer(session: AsyncSession):
    lock = FileLock(LOCK_PATH)
    with lock:
        if os.path.exists(VECTORIZER_PATH):
            return joblib.load(VECTORIZER_PATH)
        
        print("No persistent vectorizer found. Warming up from database...")
        vectorizer = build_vectorizer()
        
        # Fetch last 1000 headlines
        stmt = select(Headline.raw_text).order_by(desc(Headline.ingested_at)).limit(1000)
        res = await session.execute(stmt)
        headlines = [r[0] for r in res.all()]
        
        if headlines:
            vectorizer.fit(headlines)
            joblib.dump(vectorizer, VECTORIZER_PATH)
        else:
            # Fit on dummy just to initialize vocab if DB is empty
            # Must satisfy min_df=3 (term in 3+ docs) and max_df=0.85 (term in <85% docs)
            # "market" and "news" appear in 3 docs (60%), "financial" appears in 2.
            dummy_corpus = [
                "market news report",
                "market news trading",
                "market news finance",
                "stock exchange volume",
                "economy growth indicator"
            ]
            vectorizer.fit(dummy_corpus)
            
        return vectorizer

async def ingest_news(session: AsyncSession):
    # 1. Fetch from sources
    sources = {
        "ET Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/2146842.cms",
        "Moneycontrol": "https://www.moneycontrol.com/rss/MCtopnews.xml",
        "NDTV Profit": "https://www.ndtvprofit.com/rss/",
        "Livemint": "https://www.livemint.com/rss/markets",
        "Business Standard": "https://www.business-standard.com/rss/markets-106.rss",
        "CNBC TV18": "https://www.cnbctv18.com/commonfeeds/v1/cns/market-news.xml"
    }
    
    all_headlines = []
    for name, url in sources.items():
        all_headlines.extend(await fetch_rss(session, url, name))
    
    if not all_headlines:
        print("No new headlines found.")
        return

    # Check database size for Lexical Surprise threshold
    stmt_count = select(func.count(Headline.id))
    count_res = await session.execute(stmt_count)
    total_db_headlines = count_res.scalar()

    print(f"Processing {len(all_headlines)} headlines... (DB Total: {total_db_headlines})")
    
    # 2. Setup Analytics context
    event_frequencies = await get_event_frequencies(session)
    vectorizer = await get_or_warmup_vectorizer(session)
    
    # Get latest sector baselines
    baselines = {}
    for sector in settings.SECTORS:
        stmt = select(RollingBaseline).where(RollingBaseline.sector == sector).order_by(desc(RollingBaseline.computed_at)).limit(1)
        res = await session.execute(stmt)
        bl = res.scalar_one_or_none()
        if bl:
            baselines[sector] = bl.mean_embedding

    # 3. Efficient Processing
    # To batch classify, we first filter for new headlines
    new_headlines_data = []
    for h_data in all_headlines:
        stmt = select(Headline).where(Headline.raw_text == h_data['raw_text'], Headline.source == h_data['source'])
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            new_headlines_data.append(h_data)
            
    if not new_headlines_data:
        print("All headlines are duplicates.")
        return

    # Batch classify event types
    texts = [h['raw_text'] for h in new_headlines_data]
    batch_size = 15
    event_types = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        print(f"Batch classifying headlines {i} to {i+len(batch)}...")
        event_types.extend(await classifier.classify_batch(batch))

    # 4. Pipeline Execution
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for h_data, event_type in zip(new_headlines_data, event_types):
        txt = h_data['raw_text']
        embedding = embedder.encode_one(txt)
        sentiment = scorer.score(txt)
        sector_probs = attributor.predict_proba(txt)
        if not sector_probs:
            sector_probs = {s: 1.0/len(settings.SECTORS) for s in settings.SECTORS}
        
        # Save Headline using atomic UPSERT
        stmt = pg_insert(Headline).values(
            source=h_data['source'],
            raw_text=txt,
            published_at=h_data['published_at'],
            embedding=embedding
        ).on_conflict_do_nothing(index_elements=['source', 'raw_text']).returning(Headline.id)
        
        res = await session.execute(stmt)
        headline_id = res.scalar_one_or_none()
        
        # If headline_id is None, it means it was a duplicate and skipped
        if not headline_id:
            continue

        # Calculate surprise levels
        top_sector = max(sector_probs, key=sector_probs.get)
        
        # Lexical threshold check
        lex_val = 0.0
        if total_db_headlines > 200:
            lex_val = lexical_surprise(txt, vectorizer)
        
        sem_val = semantic_surprise(embedding, baselines.get(top_sector, []))
        evt_val = event_surprise(event_type, event_frequencies)
        
        composite = composite_score(lex_val, sem_val, evt_val)
        
        # Save Score
        score = HeadlineScore(
            headline_id=headline_id,
            surprise=composite,
            sentiment=sentiment,
            sector_probs=sector_probs,
            event_type=event_type
        )
        session.add(score)
        
        # Trigger Signals
        if composite > 0.7:
            print(f"⚠️ ANOMALY DETECTED: {txt} (Surprise: {composite:.2f}, Sector: {top_sector})")
            signal = Signal(
                sector=top_sector,
                surprise_val=composite,
                layers={"lexical": lex_val, "semantic": sem_val, "event": evt_val},
                headline_ids=[headline_id],
                conviction="high" if composite > 0.85 else "medium" if composite > 0.75 else "low"
            )
            session.add(signal)

    # 5. Persistent State Update
    # Update vectorizer with new data and save
    if new_headlines_data:
        # We don't refit everything, but we can fit on current to update DF?
        # Actually TfidfVectorizer doesn't support partial_fit.
        # Recommendation was to fit on a rolling window. For now, we'll just save it.
        # (A better HashingVectorizer would allow partial_fit)
        lock = FileLock(LOCK_PATH)
        with lock:
            joblib.dump(vectorizer, VECTORIZER_PATH)

    await session.commit()
    print("Ingestion cycle complete.")

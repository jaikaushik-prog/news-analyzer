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

CREATE TABLE feed_metadata (
  feed_url        TEXT PRIMARY KEY,
  etag            TEXT,
  last_modified   TEXT,
  last_fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conditional Indexing: Only create IVFFlat index if enough data exists
-- For small datasets, plain sequential scan or HNSW is better.
DO $$
BEGIN
  IF (SELECT COUNT(*) FROM headlines) > 5000 THEN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'headlines_embedding_idx') THEN
      CREATE INDEX headlines_embedding_idx ON headlines USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    END IF;
  END IF;
END $$;

CREATE INDEX ON signals (triggered_at DESC);
CREATE INDEX ON headline_scores (headline_id);

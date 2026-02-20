-- SRMA Engine initial schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Reviews (systematic review projects)
CREATE TABLE IF NOT EXISTS reviews (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'draft',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Papers
CREATE TABLE IF NOT EXISTS papers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id       UUID REFERENCES reviews(id) ON DELETE CASCADE,
    title           TEXT,
    abstract        TEXT,
    authors         JSONB,
    year            INTEGER,
    doi             TEXT,
    source_file     TEXT,
    grobid_tei      TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    screening_label TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_papers_review_id ON papers(review_id);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_title_trgm ON papers USING GIN (title gin_trgm_ops);

-- Stats jobs
CREATE TABLE IF NOT EXISTS stats_jobs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id   UUID REFERENCES reviews(id) ON DELETE CASCADE,
    job_type    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    input_data  JSONB,
    result_data JSONB,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

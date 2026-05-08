-- Book Recommender: initial PostgreSQL schema (pgvector).
-- Run once on an empty database (e.g. Docker entrypoint) or apply manually.
--
-- Embedding size defaults to 1024 (see OPENAI_EMBEDDING_DIMENSIONS / app.config.settings.openai).
-- If you change the embedding model dimensions, alter the VECTOR(...) type accordingly.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS books (
    isbn13 TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,
    categories TEXT,
    genre TEXT,
    description TEXT,
    published_year INTEGER,
    average_rating DOUBLE PRECISION,
    num_pages INTEGER,
    ratings_count INTEGER,
    thumbnail TEXT,
    large_thumbnail TEXT,
    title_and_subtiles TEXT,
    anger DOUBLE PRECISION DEFAULT 0.0,
    disgust DOUBLE PRECISION DEFAULT 0.0,
    fear DOUBLE PRECISION DEFAULT 0.0,
    joy DOUBLE PRECISION DEFAULT 0.0,
    sadness DOUBLE PRECISION DEFAULT 0.0,
    surprise DOUBLE PRECISION DEFAULT 0.0,
    neutral DOUBLE PRECISION DEFAULT 0.0,
    is_children BOOLEAN DEFAULT FALSE,
    embedding VECTOR(1024)
);

CREATE INDEX IF NOT EXISTS books_embedding_idx
    ON books USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- =============================================================================
-- Migration 002: Upgrade embedding dimensions from 768 → 3072
-- Model: gemini-embedding-001 (output_dimensionality=3072)
-- Run this on the VPS once, then re-run your ingestion/embedding scripts
-- =============================================================================
-- NOTE: Changing vector dimensions requires dropping and recreating the column.
-- Existing 768-dim embeddings will be cleared and must be regenerated.
-- =============================================================================

BEGIN;

-- ── 1. funding_calls ─────────────────────────────────────────────────────────
ALTER TABLE public.funding_calls DROP COLUMN IF EXISTS embedding;
ALTER TABLE public.funding_calls
    ADD COLUMN embedding public.vector(3072);

COMMENT ON COLUMN public.funding_calls.embedding IS
    'Vector embedding (3072-dim) for semantic search using gemini-embedding-001';

-- ── 2. document_chunks ───────────────────────────────────────────────────────
-- Drop the index first (if it exists) to avoid conflicts
DROP INDEX IF EXISTS public.document_chunks_embedding_idx;

ALTER TABLE public.document_chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE public.document_chunks
    ADD COLUMN embedding public.vector(3072);

ALTER TABLE public.document_chunks
    ALTER COLUMN embedding_model SET DEFAULT 'gemini-embedding-001';

-- ── 3. embedding_cache ───────────────────────────────────────────────────────
-- Cache is invalid now anyway (old 768-dim entries), just truncate and rebuild
TRUNCATE TABLE public.embedding_cache;

ALTER TABLE public.embedding_cache DROP COLUMN IF EXISTS embedding;
ALTER TABLE public.embedding_cache
    ADD COLUMN embedding public.vector(3072) NOT NULL;

ALTER TABLE public.embedding_cache
    ALTER COLUMN model_version SET DEFAULT 'gemini-embedding-001';

-- NOTE: pgvector < 0.7 does not support indexes on vectors with > 2000 dimensions.
-- Semantic search will still work via exact (sequential) scan — fast enough for
-- moderate data sizes. Upgrade pgvector to 0.7+ for halfvec HNSW support if needed.

COMMIT;

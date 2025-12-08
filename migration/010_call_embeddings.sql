-- Migration: Add embedding column to funding_calls for semantic search
-- This enables semantic/fuzzy matching for cross-domain queries like "AI in healthcare"

-- Add embedding column (768 dimensions for Google text-embedding-004)
ALTER TABLE funding_calls
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Create index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_funding_calls_embedding
ON funding_calls
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Add a column to track when embedding was generated
ALTER TABLE funding_calls
ADD COLUMN IF NOT EXISTS embedding_updated_at timestamp with time zone;

-- Create a function to search calls by semantic similarity
CREATE OR REPLACE FUNCTION search_calls_semantic(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 20,
    filter_status text DEFAULT NULL,
    filter_open_only boolean DEFAULT true
)
RETURNS TABLE (
    id uuid,
    topic_code varchar,
    title text,
    scope text,
    expected_outcome text,
    deadline date,
    status varchar,
    cluster varchar,
    action_type varchar,
    budget_total numeric,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        fc.id,
        fc.topic_code,
        fc.title,
        fc.scope,
        fc.expected_outcome,
        fc.deadline,
        fc.status,
        fc.cluster,
        fc.action_type,
        fc.budget_total,
        1 - (fc.embedding <=> query_embedding) as similarity
    FROM funding_calls fc
    WHERE
        fc.embedding IS NOT NULL
        AND (filter_status IS NULL OR fc.status = filter_status)
        AND (NOT filter_open_only OR (
            fc.status != 'closed'
            AND (fc.deadline IS NULL OR fc.deadline >= CURRENT_DATE)
        ))
        AND 1 - (fc.embedding <=> query_embedding) > match_threshold
    ORDER BY fc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON COLUMN funding_calls.embedding IS 'Vector embedding (768-dim) for semantic search using Google text-embedding-004';
COMMENT ON FUNCTION search_calls_semantic IS 'Search funding calls using semantic similarity with query embedding';

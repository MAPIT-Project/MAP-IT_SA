-- ============================================================================
-- Project Embeddings Table Creation
-- ============================================================================
-- Purpose: Store vector embeddings for semantic project search
-- Model: gemini-embedding-001 (Google Gemini)
-- Dimension: 3072
-- Created: 2024-12-03
-- Updated: 2026-03-10 (migrated from text-embedding-004/768-dim)
-- ============================================================================

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing table if re-creating (use with caution in production)
-- DROP TABLE IF EXISTS project_embeddings CASCADE;

-- Create project_embeddings table
-- NOTE: project_id is INTEGER to match projects.id column type
CREATE TABLE IF NOT EXISTS project_embeddings (
    project_id INTEGER PRIMARY KEY,

    -- Vector embeddings (3072 dimensions for gemini-embedding-001)
    title_embedding vector(3072),          -- Embedding of project title only
    objective_embedding vector(3072),      -- Embedding of objective only
    combined_embedding vector(3072),       -- Embedding of title + objective (first 2000 chars)

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    model_version TEXT DEFAULT 'gemini-embedding-001',
    text_length INTEGER,                  -- Length of text used for embedding
    embedding_status TEXT DEFAULT 'completed',  -- completed, failed, pending
    error_message TEXT,                   -- Error message if embedding failed

    -- Foreign key to projects table
    CONSTRAINT fk_project
        FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- NOTE: IVFFlat indexes require data to exist before they can be built properly.
-- Run this index creation AFTER generating embeddings:
--
-- CREATE INDEX IF NOT EXISTS idx_project_embeddings_combined
--     ON project_embeddings
--     USING ivfflat (combined_embedding vector_cosine_ops)
--     WITH (lists = 100);
--
-- For now, we create a simple btree index on project_id and will use exact search.
-- After bulk insert, run: VACUUM ANALYZE project_embeddings;
-- Then create the vector indexes.

-- Index for faster lookups by project_id
CREATE INDEX IF NOT EXISTS idx_project_embeddings_project_id
    ON project_embeddings(project_id);

-- Index for filtering by status
CREATE INDEX IF NOT EXISTS idx_project_embeddings_status
    ON project_embeddings(embedding_status);

-- Index for filtering by model version (useful for migrations)
CREATE INDEX IF NOT EXISTS idx_project_embeddings_model
    ON project_embeddings(model_version);

-- ============================================================================
-- Table Comments (Documentation)
-- ============================================================================

COMMENT ON TABLE project_embeddings IS
    'Vector embeddings for semantic project search using text-embedding-004 model';

COMMENT ON COLUMN project_embeddings.project_id IS
    'Foreign key to projects table';

COMMENT ON COLUMN project_embeddings.title_embedding IS
    'Vector embedding of project title only (768 dimensions)';

COMMENT ON COLUMN project_embeddings.objective_embedding IS
    'Vector embedding of project objective only (768 dimensions)';

COMMENT ON COLUMN project_embeddings.combined_embedding IS
    'Vector embedding of title + objective (first 2000 chars, 768 dimensions)';

COMMENT ON COLUMN project_embeddings.model_version IS
    'Embedding model version (e.g., text-embedding-004)';

COMMENT ON COLUMN project_embeddings.text_length IS
    'Length of text used for generating combined_embedding';

COMMENT ON COLUMN project_embeddings.embedding_status IS
    'Status: completed, failed, or pending';

-- ============================================================================
-- Trigger for automatic updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_project_embeddings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_project_embeddings_timestamp ON project_embeddings;

CREATE TRIGGER trigger_update_project_embeddings_timestamp
    BEFORE UPDATE ON project_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_project_embeddings_timestamp();

-- ============================================================================
-- Grant Permissions (adjust as needed for your setup)
-- ============================================================================

-- Grant permissions to mapit_user (if needed)
GRANT ALL ON project_embeddings TO mapit_user;

-- ============================================================================
-- Utility Views
-- ============================================================================

-- View for monitoring embedding coverage
CREATE OR REPLACE VIEW v_embedding_coverage AS
SELECT
    COUNT(DISTINCT p.id) as total_projects,
    COUNT(DISTINCT pe.project_id) as embedded_projects,
    COUNT(DISTINCT p.id) - COUNT(DISTINCT pe.project_id) as missing_embeddings,
    ROUND(100.0 * COUNT(DISTINCT pe.project_id) / NULLIF(COUNT(DISTINCT p.id), 0), 2) as coverage_percent
FROM projects p
LEFT JOIN project_embeddings pe ON p.id = pe.project_id
WHERE p.title IS NOT NULL AND p.objective IS NOT NULL;

COMMENT ON VIEW v_embedding_coverage IS
    'Monitor embedding coverage across all projects';

-- View for embedding quality metrics
CREATE OR REPLACE VIEW v_embedding_stats AS
SELECT
    model_version,
    embedding_status,
    COUNT(*) as count,
    AVG(text_length) as avg_text_length,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM project_embeddings
GROUP BY model_version, embedding_status
ORDER BY model_version, embedding_status;

COMMENT ON VIEW v_embedding_stats IS
    'Statistics about embeddings by model version and status';

-- ============================================================================
-- Verification Queries (Run after creation)
-- ============================================================================

-- Check table exists
-- SELECT * FROM information_schema.tables WHERE table_name = 'project_embeddings';

-- Check indexes
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'project_embeddings';

-- Check coverage
-- SELECT * FROM v_embedding_coverage;

-- Check stats
-- SELECT * FROM v_embedding_stats;

-- ============================================================================
-- Success Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ project_embeddings table created successfully';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run: python scripts/generate_project_embeddings.py';
    RAISE NOTICE '2. Monitor progress: SELECT * FROM v_embedding_coverage;';
    RAISE NOTICE '3. After bulk insert: VACUUM ANALYZE project_embeddings;';
    RAISE NOTICE '4. Create vector indexes (see script below)';
END $$;

-- ============================================================================
-- POST-EMBEDDING: Create Vector Indexes
-- ============================================================================
-- Run this AFTER generating embeddings to enable fast similarity search.
-- IVFFlat requires at least 100 * lists rows to work well.
-- For 13,865 projects, lists=100 is appropriate.

-- Run: VACUUM ANALYZE project_embeddings;

-- Then create the index:
-- CREATE INDEX IF NOT EXISTS idx_project_embeddings_combined
--     ON project_embeddings
--     USING ivfflat (combined_embedding vector_cosine_ops)
--     WITH (lists = 100);

-- Alternatively, for even faster search (but slower builds), use HNSW:
-- CREATE INDEX IF NOT EXISTS idx_project_embeddings_combined_hnsw
--     ON project_embeddings
--     USING hnsw (combined_embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

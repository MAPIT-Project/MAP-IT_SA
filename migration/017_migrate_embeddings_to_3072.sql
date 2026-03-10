-- ============================================================================
-- Migration: Upgrade project embeddings from 768-dim to 3072-dim
-- ============================================================================
-- Model change: text-embedding-004 (deprecated) → gemini-embedding-001
-- Dimension change: 768 → 3072
-- Date: 2026-03-10
-- ============================================================================

-- Step 1: Drop the existing IVFFlat vector index (incompatible with new dimension)
DROP INDEX IF EXISTS idx_project_embeddings_combined;
DROP INDEX IF EXISTS idx_project_embeddings_combined_hnsw;

-- Step 2: Clear all existing embeddings (768-dim data is incompatible with 3072-dim columns)
UPDATE project_embeddings
SET combined_embedding = NULL,
    title_embedding = NULL,
    objective_embedding = NULL,
    embedding_status = 'pending',
    model_version = NULL,
    error_message = 'Pending re-generation with gemini-embedding-001 (3072-dim)',
    updated_at = NOW();

-- Step 3: ALTER vector columns from 768 to 3072 dimensions
ALTER TABLE project_embeddings
    ALTER COLUMN title_embedding TYPE vector(3072),
    ALTER COLUMN objective_embedding TYPE vector(3072),
    ALTER COLUMN combined_embedding TYPE vector(3072);

-- Step 4: Update default model version
ALTER TABLE project_embeddings
    ALTER COLUMN model_version SET DEFAULT 'gemini-embedding-001';

-- Step 5: Update table and column comments
COMMENT ON TABLE project_embeddings IS
    'Vector embeddings for semantic project search using gemini-embedding-001 model (3072-dim)';

COMMENT ON COLUMN project_embeddings.title_embedding IS
    'Vector embedding of project title only (3072 dimensions)';

COMMENT ON COLUMN project_embeddings.objective_embedding IS
    'Vector embedding of project objective only (3072 dimensions)';

COMMENT ON COLUMN project_embeddings.combined_embedding IS
    'Vector embedding of title + objective (first 2000 chars, 3072 dimensions)';

-- Step 6: Verify migration
DO $$
DECLARE
    pending_count INTEGER;
    col_type TEXT;
BEGIN
    -- Check pending count
    SELECT COUNT(*) INTO pending_count
    FROM project_embeddings WHERE embedding_status = 'pending';

    -- Check column dimension (via atttypmod for vector columns)
    SELECT format_type(atttypid, atttypmod) INTO col_type
    FROM pg_attribute
    WHERE attrelid = 'project_embeddings'::regclass
      AND attname = 'combined_embedding';

    RAISE NOTICE '✅ Migration complete';
    RAISE NOTICE '📊 Embeddings pending re-generation: %', pending_count;
    RAISE NOTICE '📊 combined_embedding column type: %', col_type;
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run: python scripts/generate_project_embeddings.py';
    RAISE NOTICE '2. Monitor: SELECT * FROM v_embedding_coverage;';
    RAISE NOTICE '3. After completion: VACUUM ANALYZE project_embeddings;';
    RAISE NOTICE '4. Create HNSW index (see bottom of this file)';
END $$;

-- ============================================================================
-- POST-REGENERATION: Create Vector Index
-- ============================================================================
-- Run AFTER all embeddings are regenerated:
--
-- VACUUM ANALYZE project_embeddings;
--
-- HNSW index (recommended for 3072-dim - better recall than IVFFlat at high dimensions):
-- CREATE INDEX IF NOT EXISTS idx_project_embeddings_combined_hnsw
--     ON project_embeddings
--     USING hnsw (combined_embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);
--
-- Or IVFFlat (faster build, slightly lower recall):
-- CREATE INDEX IF NOT EXISTS idx_project_embeddings_combined
--     ON project_embeddings
--     USING ivfflat (combined_embedding vector_cosine_ops)
--     WITH (lists = 100);

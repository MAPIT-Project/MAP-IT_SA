-- ================================================================
-- PROPOSAL EXAMPLES ENHANCEMENT
-- ================================================================
-- Enhances proposal_examples table for CORDIS project extraction
-- and semantic search capabilities
--
-- Author: AI Assistant
-- Date: 2025-12-04
-- Task: 06_POPULATE_EXAMPLES
-- ================================================================

-- Add new columns if they don't exist
DO $$
BEGIN
    -- Add project_id column (links to CORDIS projects)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'project_id'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN project_id VARCHAR(50);
    END IF;

    -- Add section_type column (excellence_objectives, impact_expected, etc.)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'section_type'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN section_type VARCHAR(50);
    END IF;

    -- Add content column (main text content)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'content'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN content TEXT;
    END IF;

    -- Add source column (cordis, manual, etc.)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'source'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN source VARCHAR(20) DEFAULT 'cordis';
    END IF;

    -- Add cluster column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'cluster'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN cluster VARCHAR(50);
    END IF;

    -- Add action_type column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'action_type'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN action_type VARCHAR(20);
    END IF;

    -- Add embedding column (vector for semantic search)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'example_embedding'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN example_embedding vector(768);
    END IF;

    -- Add quality_score column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'quality_score'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN quality_score DECIMAL(3,2);
    END IF;

    -- Add enrichment_data column (LLM analysis)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'enrichment_data'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN enrichment_data JSONB;
    END IF;

    -- Add enriched_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'enriched_at'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN enriched_at TIMESTAMP;
    END IF;

    -- Add updated_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE proposal_examples ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
    END IF;
END $$;

-- Create unique constraint for deduplication (project_id + section_type)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'proposal_examples_project_section_unique'
    ) THEN
        ALTER TABLE proposal_examples
        ADD CONSTRAINT proposal_examples_project_section_unique
        UNIQUE (project_id, section_type);
    END IF;
EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE 'Constraint already exists or duplicate data exists';
END $$;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_proposal_examples_project_id
ON proposal_examples(project_id);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_cluster
ON proposal_examples(cluster);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_action_type
ON proposal_examples(action_type);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_section_type
ON proposal_examples(section_type);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_quality
ON proposal_examples(quality_score DESC);

CREATE INDEX IF NOT EXISTS idx_proposal_examples_source
ON proposal_examples(source);

-- Create embedding index for vector search (only if column exists and has data)
-- Using cosine distance for similarity search
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_examples' AND column_name = 'example_embedding'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_proposal_examples_embedding
        ON proposal_examples
        USING ivfflat (example_embedding vector_cosine_ops)
        WITH (lists = 100);
    END IF;
EXCEPTION
    WHEN undefined_column THEN
        RAISE NOTICE 'example_embedding column does not exist yet';
END $$;

-- Create view for high-quality examples
CREATE OR REPLACE VIEW high_quality_examples AS
SELECT
    pe.id,
    pe.project_id,
    pe.section_type,
    pe.content,
    pe.cluster,
    pe.action_type,
    pe.quality_score,
    pe.source,
    p.acronym as project_acronym,
    p.title as project_title,
    p."totalCost" as total_cost,
    p."ecMaxContribution" as ec_contribution
FROM proposal_examples pe
LEFT JOIN projects p ON pe.project_id = p.id
WHERE pe.quality_score >= 0.7
ORDER BY pe.quality_score DESC;

-- Function to find similar examples by embedding
CREATE OR REPLACE FUNCTION find_similar_examples(
    query_embedding vector(768),
    target_section_type VARCHAR DEFAULT NULL,
    target_cluster VARCHAR DEFAULT NULL,
    target_action_type VARCHAR DEFAULT NULL,
    limit_count INT DEFAULT 5
)
RETURNS TABLE (
    id INT,
    project_id VARCHAR,
    section_type VARCHAR,
    content TEXT,
    cluster VARCHAR,
    action_type VARCHAR,
    quality_score DECIMAL,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.id,
        pe.project_id,
        pe.section_type,
        pe.content,
        pe.cluster,
        pe.action_type,
        pe.quality_score,
        1 - (pe.example_embedding <=> query_embedding) as similarity
    FROM proposal_examples pe
    WHERE
        pe.example_embedding IS NOT NULL
        AND pe.quality_score >= 0.6
        AND (target_section_type IS NULL OR pe.section_type = target_section_type)
        AND (target_cluster IS NULL OR pe.cluster = target_cluster)
        AND (target_action_type IS NULL OR pe.action_type = target_action_type)
    ORDER BY pe.example_embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Statistics view
CREATE OR REPLACE VIEW proposal_examples_stats AS
SELECT
    section_type,
    cluster,
    action_type,
    COUNT(*) as example_count,
    AVG(quality_score) as avg_quality,
    COUNT(*) FILTER (WHERE enrichment_data IS NOT NULL) as enriched_count,
    COUNT(*) FILTER (WHERE example_embedding IS NOT NULL) as embedded_count
FROM proposal_examples
WHERE project_id IS NOT NULL
GROUP BY section_type, cluster, action_type
ORDER BY example_count DESC;

-- Summary message
DO $$
BEGIN
    RAISE NOTICE 'Proposal examples enhancement migration completed successfully!';
    RAISE NOTICE 'New columns: project_id, section_type, content, cluster, action_type, example_embedding, quality_score, enrichment_data';
    RAISE NOTICE 'New indexes: project_id, cluster, action_type, section_type, quality, embedding';
    RAISE NOTICE 'New functions: find_similar_examples()';
    RAISE NOTICE 'New views: high_quality_examples, proposal_examples_stats';
END $$;

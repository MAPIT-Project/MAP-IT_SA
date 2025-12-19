-- Migration: Ensure 100% Embedding Coverage
-- Priority 4.4 from IMPROVEMENT_ROADMAP.md
--
-- This migration creates the infrastructure to ensure all projects have embeddings:
-- 1. A view to identify projects needing embeddings
-- 2. An embedding queue table for background processing
-- 3. Triggers to automatically queue new/updated projects
-- 4. Indexes for efficient queue processing

-- ============================================================================
-- Embedding Queue Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS embedding_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    rcn TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    priority INTEGER NOT NULL DEFAULT 0,      -- Higher = more urgent
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT embedding_queue_project_unique UNIQUE (project_id)
);

-- Index for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_embedding_queue_status
    ON embedding_queue(status, priority DESC, created_at ASC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_embedding_queue_project
    ON embedding_queue(project_id);

-- ============================================================================
-- View: Projects Needing Embeddings
-- ============================================================================

CREATE OR REPLACE VIEW projects_needing_embeddings AS
SELECT
    p.id,
    p.rcn,
    p.title,
    p.objective,
    p.start_date,
    p.updated_at AS project_updated_at,
    pe.updated_at AS embedding_updated_at,
    CASE
        WHEN pe.id IS NULL THEN 'missing'
        WHEN pe.embedding IS NULL THEN 'null_embedding'
        WHEN pe.updated_at < p.updated_at THEN 'stale'
        ELSE 'ok'
    END AS embedding_status
FROM projects p
LEFT JOIN project_embeddings pe ON p.id = pe.project_id
WHERE
    pe.id IS NULL
    OR pe.embedding IS NULL
    OR pe.updated_at < p.updated_at
ORDER BY p.updated_at DESC;

-- ============================================================================
-- View: Embedding Coverage Statistics
-- ============================================================================

CREATE OR REPLACE VIEW embedding_coverage_stats AS
WITH stats AS (
    SELECT
        COUNT(*) AS total_projects,
        COUNT(pe.id) AS projects_with_embeddings,
        COUNT(CASE WHEN pe.embedding IS NOT NULL THEN 1 END) AS valid_embeddings,
        COUNT(CASE WHEN pe.updated_at >= p.updated_at THEN 1 END) AS fresh_embeddings
    FROM projects p
    LEFT JOIN project_embeddings pe ON p.id = pe.project_id
),
queue_stats AS (
    SELECT
        COUNT(*) AS total_queued,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending,
        COUNT(CASE WHEN status = 'processing' THEN 1 END) AS processing,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed
    FROM embedding_queue
    WHERE created_at > NOW() - INTERVAL '7 days'
)
SELECT
    s.total_projects,
    s.projects_with_embeddings,
    s.valid_embeddings,
    s.fresh_embeddings,
    ROUND(s.valid_embeddings::NUMERIC / NULLIF(s.total_projects, 0) * 100, 2) AS coverage_percent,
    ROUND(s.fresh_embeddings::NUMERIC / NULLIF(s.total_projects, 0) * 100, 2) AS freshness_percent,
    q.pending AS queue_pending,
    q.processing AS queue_processing,
    q.failed AS queue_failed
FROM stats s
CROSS JOIN queue_stats q;

-- ============================================================================
-- Function: Queue Project for Embedding
-- ============================================================================

CREATE OR REPLACE FUNCTION queue_embedding_generation()
RETURNS TRIGGER AS $$
BEGIN
    -- Only queue if the project has meaningful content
    IF NEW.title IS NOT NULL AND LENGTH(NEW.title) > 0 THEN
        INSERT INTO embedding_queue (
            project_id,
            rcn,
            status,
            priority,
            created_at,
            updated_at
        )
        VALUES (
            NEW.id,
            NEW.rcn,
            'pending',
            CASE
                WHEN TG_OP = 'INSERT' THEN 10  -- New projects get higher priority
                ELSE 5  -- Updates get normal priority
            END,
            NOW(),
            NOW()
        )
        ON CONFLICT (project_id) DO UPDATE SET
            status = 'pending',
            priority = GREATEST(embedding_queue.priority, EXCLUDED.priority),
            attempts = 0,
            error_message = NULL,
            updated_at = NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Trigger: Auto-Queue on Project Insert/Update
-- ============================================================================

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS trg_queue_embedding ON projects;

-- Create trigger for INSERT and UPDATE
CREATE TRIGGER trg_queue_embedding
AFTER INSERT OR UPDATE OF title, objective, id ON projects
FOR EACH ROW
EXECUTE FUNCTION queue_embedding_generation();

-- ============================================================================
-- Function: Claim Next Batch from Queue
-- ============================================================================

CREATE OR REPLACE FUNCTION claim_embedding_batch(
    batch_size INTEGER DEFAULT 50,
    worker_id TEXT DEFAULT 'default'
)
RETURNS TABLE (
    project_id TEXT,
    rcn TEXT,
    title TEXT,
    objective TEXT
) AS $$
DECLARE
    claimed_ids TEXT[];
BEGIN
    -- Lock and claim batch atomically
    WITH claimed AS (
        UPDATE embedding_queue
        SET
            status = 'processing',
            processing_started_at = NOW(),
            updated_at = NOW(),
            attempts = attempts + 1
        WHERE id IN (
            SELECT eq.id
            FROM embedding_queue eq
            WHERE eq.status = 'pending'
                AND eq.attempts < eq.max_attempts
            ORDER BY eq.priority DESC, eq.created_at ASC
            LIMIT batch_size
            FOR UPDATE SKIP LOCKED
        )
        RETURNING embedding_queue.project_id
    )
    SELECT array_agg(c.project_id) INTO claimed_ids FROM claimed c;

    -- Return project details for claimed items
    RETURN QUERY
    SELECT
        p.id::TEXT AS project_id,
        p.rcn::TEXT AS rcn,
        p.title,
        p.objective
    FROM projects p
    WHERE p.id = ANY(claimed_ids);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function: Mark Embedding Complete
-- ============================================================================

CREATE OR REPLACE FUNCTION mark_embedding_complete(
    p_project_id TEXT,
    p_success BOOLEAN,
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    IF p_success THEN
        UPDATE embedding_queue
        SET
            status = 'completed',
            completed_at = NOW(),
            updated_at = NOW()
        WHERE project_id = p_project_id;
    ELSE
        UPDATE embedding_queue
        SET
            status = CASE
                WHEN attempts >= max_attempts THEN 'failed'
                ELSE 'pending'
            END,
            error_message = p_error_message,
            updated_at = NOW()
        WHERE project_id = p_project_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function: Queue All Missing Embeddings (one-time)
-- ============================================================================

CREATE OR REPLACE FUNCTION queue_all_missing_embeddings()
RETURNS INTEGER AS $$
DECLARE
    queued_count INTEGER;
BEGIN
    INSERT INTO embedding_queue (project_id, rcn, status, priority)
    SELECT
        p.id,
        p.rcn,
        'pending',
        1  -- Low priority for bulk backfill
    FROM projects p
    LEFT JOIN project_embeddings pe ON p.id = pe.project_id
    WHERE pe.id IS NULL OR pe.embedding IS NULL
    ON CONFLICT (project_id) DO NOTHING;

    GET DIAGNOSTICS queued_count = ROW_COUNT;
    RETURN queued_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function: Clean Up Old Completed Queue Entries
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_embedding_queue(
    days_to_keep INTEGER DEFAULT 7
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM embedding_queue
    WHERE status = 'completed'
        AND completed_at < NOW() - (days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Initial Population: Queue all projects without embeddings
-- ============================================================================

-- Uncomment to run one-time population:
-- SELECT queue_all_missing_embeddings();

-- ============================================================================
-- Grants (adjust schema/roles as needed)
-- ============================================================================

-- Grant access to application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON embedding_queue TO app_user;
-- GRANT SELECT ON projects_needing_embeddings TO app_user;
-- GRANT SELECT ON embedding_coverage_stats TO app_user;
-- GRANT EXECUTE ON FUNCTION claim_embedding_batch TO app_user;
-- GRANT EXECUTE ON FUNCTION mark_embedding_complete TO app_user;

COMMENT ON TABLE embedding_queue IS 'Queue for background embedding generation';
COMMENT ON VIEW projects_needing_embeddings IS 'Projects that need embedding generation or update';
COMMENT ON VIEW embedding_coverage_stats IS 'Statistics about embedding coverage';
COMMENT ON FUNCTION queue_embedding_generation IS 'Trigger function to queue projects for embedding';
COMMENT ON FUNCTION claim_embedding_batch IS 'Atomically claim a batch of projects for embedding processing';
COMMENT ON FUNCTION mark_embedding_complete IS 'Mark an embedding job as complete or failed';

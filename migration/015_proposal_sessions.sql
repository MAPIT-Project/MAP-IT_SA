-- ================================================================
-- PROPOSAL SESSIONS - UNIFIED SESSION MANAGEMENT
-- ================================================================
-- This migration adds proposal session management for the AI
-- Proposal Writer unified architecture.
--
-- Purpose:
-- - Track active proposal writing sessions
-- - Store session state (document + conversation)
-- - Enable session persistence across page refreshes
-- - Support section locking during AI generation
--
-- Author: AI Assistant
-- Date: 2025-12-09
-- Version: 1.0
-- ================================================================

-- ================================================================
-- 1. PROPOSAL SESSIONS TABLE
-- ================================================================
-- Central table for tracking active proposal writing sessions

CREATE TABLE IF NOT EXISTS proposal_sessions (
    id SERIAL PRIMARY KEY,

    -- Session identification
    session_id UUID NOT NULL UNIQUE,

    -- References
    proposal_id INTEGER REFERENCES proposals(id) ON DELETE CASCADE,
    conversation_id INTEGER,
    user_id VARCHAR(100) NOT NULL,

    -- Active context
    active_section_id VARCHAR(100),

    -- Session state (JSON blob for flexibility)
    -- Contains: document state, conversation messages, suggestions, gaps
    session_state JSONB DEFAULT '{}',

    -- Status tracking
    status VARCHAR(20) DEFAULT 'active',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_session_status CHECK (
        status IN ('active', 'paused', 'completed', 'expired')
    )
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON proposal_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_proposal ON proposal_sessions(proposal_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON proposal_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON proposal_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_activity ON proposal_sessions(last_activity_at DESC);

-- Composite index for finding active sessions by user and proposal
CREATE INDEX IF NOT EXISTS idx_sessions_user_proposal_active
    ON proposal_sessions(user_id, proposal_id)
    WHERE status = 'active';


-- ================================================================
-- 2. AUTO-UPDATE ACTIVITY TIMESTAMP
-- ================================================================

CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_activity_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trigger_update_session_activity'
    ) THEN
        CREATE TRIGGER trigger_update_session_activity
            BEFORE UPDATE ON proposal_sessions
            FOR EACH ROW
            EXECUTE FUNCTION update_session_activity();
    END IF;
END $$;


-- ================================================================
-- 3. SESSION CLEANUP FUNCTION
-- ================================================================
-- Function to expire inactive sessions (called by scheduled job)

CREATE OR REPLACE FUNCTION cleanup_expired_sessions(
    expiry_hours INTEGER DEFAULT 24
)
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE proposal_sessions
    SET status = 'expired'
    WHERE status = 'active'
    AND last_activity_at < NOW() - (expiry_hours || ' hours')::INTERVAL;

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;


-- ================================================================
-- 4. SECTION LOCKS TABLE (for fine-grained locking)
-- ================================================================
-- Tracks which sections are currently locked and by whom

CREATE TABLE IF NOT EXISTS section_locks (
    id SERIAL PRIMARY KEY,

    -- References
    session_id UUID NOT NULL REFERENCES proposal_sessions(session_id) ON DELETE CASCADE,
    section_id VARCHAR(100) NOT NULL,

    -- Lock info
    lock_type VARCHAR(20) NOT NULL DEFAULT 'locked_by_ai',
    locked_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint: one lock per section per session
    UNIQUE (session_id, section_id),

    CONSTRAINT valid_lock_type CHECK (
        lock_type IN ('locked_by_ai', 'locked_by_user')
    )
);

CREATE INDEX IF NOT EXISTS idx_locks_session ON section_locks(session_id);


-- ================================================================
-- 5. SESSION MESSAGES TABLE (for efficient message retrieval)
-- ================================================================
-- Stores conversation messages separately for better query performance

CREATE TABLE IF NOT EXISTS session_messages (
    id SERIAL PRIMARY KEY,

    -- References
    session_id UUID NOT NULL REFERENCES proposal_sessions(session_id) ON DELETE CASCADE,

    -- Message data
    message_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,

    -- Metadata
    tools_used TEXT[] DEFAULT '{}',
    sections_affected TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_message_role CHECK (
        role IN ('user', 'assistant', 'system')
    )
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON session_messages(session_id, created_at DESC);


-- ================================================================
-- 6. HELPER VIEWS
-- ================================================================

-- View: Active sessions with proposal info
CREATE OR REPLACE VIEW active_sessions_overview AS
SELECT
    ps.id,
    ps.session_id,
    ps.user_id,
    ps.status,
    ps.active_section_id,
    ps.created_at,
    ps.last_activity_at,
    p.proposal_title,
    p.proposal_acronym,
    p.call_identifier,
    p.completion_percentage,
    (SELECT COUNT(*) FROM session_messages sm WHERE sm.session_id = ps.session_id) as message_count,
    (SELECT COUNT(*) FROM section_locks sl WHERE sl.session_id = ps.session_id) as locked_sections
FROM proposal_sessions ps
LEFT JOIN proposals p ON ps.proposal_id = p.id
WHERE ps.status = 'active';


-- View: Session activity summary
CREATE OR REPLACE VIEW session_activity_summary AS
SELECT
    DATE(last_activity_at) as activity_date,
    COUNT(DISTINCT session_id) as active_sessions,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT proposal_id) as proposals_worked_on
FROM proposal_sessions
WHERE status IN ('active', 'completed')
AND last_activity_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(last_activity_at)
ORDER BY activity_date DESC;


-- ================================================================
-- 7. GRANTS (adjust as needed for your setup)
-- ================================================================
-- GRANT ALL ON proposal_sessions TO your_app_user;
-- GRANT ALL ON section_locks TO your_app_user;
-- GRANT ALL ON session_messages TO your_app_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO your_app_user;


-- ================================================================
-- MIGRATION COMPLETE
-- ================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Proposal Sessions migration completed successfully!';
    RAISE NOTICE '📊 Created tables: proposal_sessions, section_locks, session_messages';
    RAISE NOTICE '📊 Created views: active_sessions_overview, session_activity_summary';
    RAISE NOTICE '📊 Created functions: cleanup_expired_sessions';
    RAISE NOTICE '🚀 Unified session management ready for AI Proposal Writer';
END $$;

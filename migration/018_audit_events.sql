-- Migration: Audit Events
-- Creates tables for comprehensive audit logging

-- Main audit events table
CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Actor information
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    session_id VARCHAR(255),

    -- Resource information
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_name VARCHAR(500),

    -- Request information
    ip_address INET,
    user_agent VARCHAR(512),
    request_id VARCHAR(255),
    endpoint VARCHAR(500),
    http_method VARCHAR(10),

    -- Outcome
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    error_code VARCHAR(100),

    -- Additional context
    details JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    -- Performance
    duration_ms FLOAT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit_events(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_session ON audit_events(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_success ON audit_events(success) WHERE success = false;

-- Composite index for audit trail queries
CREATE INDEX IF NOT EXISTS idx_audit_events_trail
    ON audit_events(resource_type, resource_id, timestamp DESC);

-- Composite index for user activity queries
CREATE INDEX IF NOT EXISTS idx_audit_events_user_activity
    ON audit_events(user_id, timestamp DESC);

-- Partial index for security events
CREATE INDEX IF NOT EXISTS idx_audit_events_security
    ON audit_events(timestamp DESC)
    WHERE event_type LIKE 'auth.%' OR event_type LIKE 'admin.%';

-- Partition the table by month for better performance and easier cleanup
-- Note: This requires PostgreSQL 10+
-- For production, consider partitioning by month:
/*
CREATE TABLE audit_events (
    ...
) PARTITION BY RANGE (timestamp);

CREATE TABLE audit_events_2025_01 PARTITION OF audit_events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
*/

-- View for security-relevant events
CREATE OR REPLACE VIEW audit_security_events AS
SELECT *
FROM audit_events
WHERE event_type IN (
    'auth.login',
    'auth.login_failed',
    'auth.logout',
    'auth.token_refresh',
    'auth.api_key_created',
    'auth.api_key_revoked',
    'admin.user_created',
    'admin.user_updated',
    'admin.user_deleted',
    'admin.settings_changed',
    'system.rate_limit',
    'system.error'
)
ORDER BY timestamp DESC;

-- View for failed operations
CREATE OR REPLACE VIEW audit_failed_events AS
SELECT *
FROM audit_events
WHERE success = false
ORDER BY timestamp DESC;

-- View for user activity summary
CREATE OR REPLACE VIEW audit_user_summary AS
SELECT
    user_id,
    DATE(timestamp) as activity_date,
    COUNT(*) as total_events,
    COUNT(*) FILTER (WHERE event_type LIKE 'query.%') as query_count,
    COUNT(*) FILTER (WHERE event_type LIKE 'proposal.%') as proposal_count,
    COUNT(*) FILTER (WHERE event_type LIKE 'search.%') as search_count,
    COUNT(*) FILTER (WHERE success = false) as failed_count,
    AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration_ms,
    MAX(timestamp) as last_activity
FROM audit_events
WHERE user_id IS NOT NULL
GROUP BY user_id, DATE(timestamp);

-- View for daily statistics
CREATE OR REPLACE VIEW audit_daily_stats AS
SELECT
    DATE(timestamp) as event_date,
    COUNT(*) as total_events,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) FILTER (WHERE success = false) as failed_events,
    COUNT(*) FILTER (WHERE event_type LIKE 'auth.login%') as login_events,
    COUNT(*) FILTER (WHERE event_type = 'auth.login_failed') as failed_logins,
    AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL) as avg_duration_ms
FROM audit_events
GROUP BY DATE(timestamp)
ORDER BY event_date DESC;

-- Function to cleanup old audit events (for scheduled job)
CREATE OR REPLACE FUNCTION cleanup_old_audit_events(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_events
    WHERE timestamp < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Deleted % audit events older than % days', deleted_count, retention_days;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE audit_events IS 'Comprehensive audit log for all system operations';
COMMENT ON VIEW audit_security_events IS 'Security-relevant audit events for monitoring';
COMMENT ON VIEW audit_failed_events IS 'Failed operations for debugging';
COMMENT ON VIEW audit_user_summary IS 'Daily activity summary per user';
COMMENT ON VIEW audit_daily_stats IS 'System-wide daily statistics';

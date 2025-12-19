-- Migration: Saved Searches and Alerts
-- Creates tables for saved search configurations and alert management

-- Saved searches table
CREATE TABLE IF NOT EXISTS saved_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    search_type VARCHAR(50) NOT NULL CHECK (search_type IN ('calls', 'projects', 'partners')),
    parameters JSONB NOT NULL DEFAULT '{}',
    alert_config JSONB NOT NULL DEFAULT '{"enabled": false, "frequency": "daily", "channel": "email"}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP WITH TIME ZONE,
    last_result_hash VARCHAR(64),
    is_active BOOLEAN DEFAULT true,
    run_count INTEGER DEFAULT 0,
    alert_count INTEGER DEFAULT 0
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_saved_searches_user_id ON saved_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_searches_user_active ON saved_searches(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_saved_searches_type ON saved_searches(search_type);
CREATE INDEX IF NOT EXISTS idx_saved_searches_alert_enabled ON saved_searches(is_active)
    WHERE (alert_config->>'enabled')::boolean = true;
CREATE INDEX IF NOT EXISTS idx_saved_searches_last_run ON saved_searches(last_run);

-- Search run history for debugging and analytics
CREATE TABLE IF NOT EXISTS saved_search_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_id UUID NOT NULL REFERENCES saved_searches(id) ON DELETE CASCADE,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    result_count INTEGER DEFAULT 0,
    new_count INTEGER DEFAULT 0,
    result_hash VARCHAR(64),
    execution_time_ms FLOAT,
    alert_sent BOOLEAN DEFAULT false,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_search_runs_search_id ON saved_search_runs(search_id);
CREATE INDEX IF NOT EXISTS idx_search_runs_executed_at ON saved_search_runs(executed_at DESC);

-- Alert history for tracking sent notifications
CREATE TABLE IF NOT EXISTS saved_search_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_id UUID NOT NULL REFERENCES saved_searches(id) ON DELETE CASCADE,
    run_id UUID REFERENCES saved_search_runs(id) ON DELETE SET NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('email', 'webhook', 'both')),
    new_results_count INTEGER,
    payload JSONB,
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_search_alerts_search_id ON saved_search_alerts(search_id);
CREATE INDEX IF NOT EXISTS idx_search_alerts_sent_at ON saved_search_alerts(sent_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_saved_search_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS trg_saved_searches_updated_at ON saved_searches;
CREATE TRIGGER trg_saved_searches_updated_at
    BEFORE UPDATE ON saved_searches
    FOR EACH ROW
    EXECUTE FUNCTION update_saved_search_timestamp();

-- View for searches due for immediate processing
CREATE OR REPLACE VIEW saved_searches_due_immediate AS
SELECT s.*
FROM saved_searches s
WHERE s.is_active = true
  AND (s.alert_config->>'enabled')::boolean = true
  AND s.alert_config->>'frequency' = 'immediate'
  AND (s.last_run IS NULL OR s.last_run < CURRENT_TIMESTAMP - INTERVAL '5 minutes');

-- View for searches due for daily processing
CREATE OR REPLACE VIEW saved_searches_due_daily AS
SELECT s.*
FROM saved_searches s
WHERE s.is_active = true
  AND (s.alert_config->>'enabled')::boolean = true
  AND s.alert_config->>'frequency' = 'daily'
  AND (s.last_run IS NULL OR s.last_run < CURRENT_TIMESTAMP - INTERVAL '23 hours');

-- View for searches due for weekly processing
CREATE OR REPLACE VIEW saved_searches_due_weekly AS
SELECT s.*
FROM saved_searches s
WHERE s.is_active = true
  AND (s.alert_config->>'enabled')::boolean = true
  AND s.alert_config->>'frequency' = 'weekly'
  AND (s.last_run IS NULL OR s.last_run < CURRENT_TIMESTAMP - INTERVAL '6 days 23 hours');

-- Aggregated view for user statistics
CREATE OR REPLACE VIEW saved_search_user_stats AS
SELECT
    user_id,
    COUNT(*) AS total_searches,
    COUNT(*) FILTER (WHERE is_active) AS active_searches,
    SUM(run_count) AS total_runs,
    SUM(alert_count) AS total_alerts,
    MAX(last_run) AS last_activity
FROM saved_searches
GROUP BY user_id;

COMMENT ON TABLE saved_searches IS 'User-saved search configurations with alert settings';
COMMENT ON TABLE saved_search_runs IS 'History of saved search executions';
COMMENT ON TABLE saved_search_alerts IS 'History of sent alert notifications';

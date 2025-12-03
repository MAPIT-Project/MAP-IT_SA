-- Tool Usage Analytics Schema
-- Tracks tool usage patterns, performance, and quality metrics for optimization

-- Tool usage events table
CREATE TABLE IF NOT EXISTS tool_usage_analytics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    conversation_id VARCHAR(255),
    query_hash VARCHAR(64),
    tool_name VARCHAR(100) NOT NULL,
    parameters JSONB,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    result_count INTEGER,
    result_quality_score FLOAT,
    speculative BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tool_usage_timestamp ON tool_usage_analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool_name ON tool_usage_analytics(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_usage_success ON tool_usage_analytics(success);
CREATE INDEX IF NOT EXISTS idx_tool_usage_conversation ON tool_usage_analytics(conversation_id);

-- Aggregated metrics table (for dashboards and analysis)
CREATE TABLE IF NOT EXISTS tool_performance_metrics (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    avg_execution_time_ms FLOAT,
    p50_execution_time_ms FLOAT,
    p95_execution_time_ms FLOAT,
    avg_result_count FLOAT,
    avg_quality_score FLOAT,
    speculative_hits INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tool_name, period_start)
);

-- Tool combination patterns (what tools are used together)
CREATE TABLE IF NOT EXISTS tool_combination_analytics (
    id SERIAL PRIMARY KEY,
    tool_sequence TEXT[] NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    avg_total_time_ms FLOAT,
    success_rate FLOAT,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tool_sequence)
);

-- Index for tool sequence queries
CREATE INDEX IF NOT EXISTS idx_tool_combo_sequence ON tool_combination_analytics USING GIN(tool_sequence);

-- View for recent tool performance
CREATE OR REPLACE VIEW v_tool_performance_24h AS
SELECT
    tool_name,
    COUNT(*) as total_calls,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
    ROUND(AVG(execution_time_ms)::numeric, 0) as avg_time_ms,
    ROUND((SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::numeric, 1) as success_rate_pct
FROM tool_usage_analytics
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY tool_name
ORDER BY total_calls DESC;

-- View for popular tool combinations
CREATE OR REPLACE VIEW v_popular_tool_combos AS
SELECT
    tool_sequence,
    occurrence_count,
    ROUND(avg_total_time_ms::numeric, 0) as avg_time_ms,
    ROUND((success_rate * 100)::numeric, 1) as success_rate_pct,
    last_seen
FROM tool_combination_analytics
WHERE occurrence_count > 5
ORDER BY occurrence_count DESC
LIMIT 20;

-- Function to aggregate metrics (can be called by a scheduled job)
CREATE OR REPLACE FUNCTION aggregate_tool_metrics(
    p_period_hours INTEGER DEFAULT 24
)
RETURNS void AS $$
DECLARE
    v_period_start TIMESTAMPTZ;
    v_period_end TIMESTAMPTZ;
BEGIN
    v_period_end := NOW();
    v_period_start := NOW() - (p_period_hours || ' hours')::INTERVAL;

    -- Delete existing metrics for this period
    DELETE FROM tool_performance_metrics
    WHERE period_start = DATE_TRUNC('hour', v_period_start)
      AND period_end = DATE_TRUNC('hour', v_period_end);

    -- Insert aggregated metrics
    INSERT INTO tool_performance_metrics (
        tool_name, period_start, period_end,
        total_calls, successful_calls, failed_calls,
        avg_execution_time_ms, p50_execution_time_ms, p95_execution_time_ms,
        avg_result_count, avg_quality_score, speculative_hits
    )
    SELECT
        tool_name,
        DATE_TRUNC('hour', v_period_start),
        DATE_TRUNC('hour', v_period_end),
        COUNT(*),
        SUM(CASE WHEN success THEN 1 ELSE 0 END),
        SUM(CASE WHEN NOT success THEN 1 ELSE 0 END),
        AVG(execution_time_ms),
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time_ms),
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms),
        AVG(result_count),
        AVG(result_quality_score),
        SUM(CASE WHEN speculative THEN 1 ELSE 0 END)
    FROM tool_usage_analytics
    WHERE timestamp BETWEEN v_period_start AND v_period_end
    GROUP BY tool_name;
END;
$$ LANGUAGE plpgsql;

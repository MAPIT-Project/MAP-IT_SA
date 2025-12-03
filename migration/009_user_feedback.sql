-- User Feedback Schema
-- Collects and analyzes user feedback on AI responses for quality improvement

-- Response feedback table
CREATE TABLE IF NOT EXISTS response_feedback (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255),
    query_text TEXT,
    response_text TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_type VARCHAR(50),  -- 'helpful', 'not_helpful', 'incorrect', 'incomplete', 'other'
    feedback_text TEXT,
    tools_used TEXT[],
    query_type VARCHAR(50),  -- 'faq', 'search_calls', 'search_projects', etc.
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_feedback_conversation ON response_feedback(conversation_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON response_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON response_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON response_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_tools ON response_feedback USING GIN(tools_used);

-- Aggregated feedback insights (for dashboards)
CREATE TABLE IF NOT EXISTS feedback_insights (
    id SERIAL PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_feedback INTEGER DEFAULT 0,
    avg_rating FLOAT,
    rating_distribution JSONB,  -- {1: 5, 2: 10, 3: 20, 4: 30, 5: 35}
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,
    incorrect_count INTEGER DEFAULT 0,
    incomplete_count INTEGER DEFAULT 0,
    top_issues JSONB,  -- [{text: "...", count: 5}, ...]
    tool_ratings JSONB,  -- {tool_name: {avg_rating: 4.2, count: 50}, ...}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(period_start)
);

-- View for recent feedback metrics
CREATE OR REPLACE VIEW v_feedback_metrics_7d AS
SELECT
    COUNT(*) as total_feedback,
    ROUND(AVG(rating)::numeric, 2) as avg_rating,
    SUM(CASE WHEN feedback_type = 'helpful' THEN 1 ELSE 0 END) as helpful_count,
    SUM(CASE WHEN feedback_type = 'not_helpful' THEN 1 ELSE 0 END) as not_helpful_count,
    SUM(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END) as incorrect_count,
    SUM(CASE WHEN feedback_type = 'incomplete' THEN 1 ELSE 0 END) as incomplete_count,
    ROUND((SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100)::numeric, 1) as satisfaction_rate
FROM response_feedback
WHERE created_at > NOW() - INTERVAL '7 days';

-- View for tool-specific feedback
CREATE OR REPLACE VIEW v_tool_feedback AS
SELECT
    unnest(tools_used) as tool_name,
    COUNT(*) as usage_count,
    ROUND(AVG(rating)::numeric, 2) as avg_rating,
    SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative_count
FROM response_feedback
WHERE tools_used IS NOT NULL
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY unnest(tools_used)
ORDER BY usage_count DESC;

-- Function to aggregate feedback insights
CREATE OR REPLACE FUNCTION aggregate_feedback_insights(
    p_date DATE DEFAULT CURRENT_DATE - 1
)
RETURNS void AS $$
DECLARE
    v_period_start DATE;
    v_period_end DATE;
BEGIN
    v_period_start := p_date;
    v_period_end := p_date + 1;

    -- Delete existing entry for this period
    DELETE FROM feedback_insights WHERE period_start = v_period_start;

    -- Insert aggregated insights
    INSERT INTO feedback_insights (
        period_start, period_end, total_feedback, avg_rating,
        rating_distribution, helpful_count, not_helpful_count,
        incorrect_count, incomplete_count
    )
    SELECT
        v_period_start,
        v_period_end,
        COUNT(*),
        AVG(rating),
        jsonb_object_agg(
            rating::text,
            rating_count
        ) FILTER (WHERE rating IS NOT NULL),
        SUM(CASE WHEN feedback_type = 'helpful' THEN 1 ELSE 0 END),
        SUM(CASE WHEN feedback_type = 'not_helpful' THEN 1 ELSE 0 END),
        SUM(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END),
        SUM(CASE WHEN feedback_type = 'incomplete' THEN 1 ELSE 0 END)
    FROM (
        SELECT
            rating,
            feedback_type,
            COUNT(*) OVER (PARTITION BY rating) as rating_count
        FROM response_feedback
        WHERE created_at >= v_period_start AND created_at < v_period_end
    ) sub;
END;
$$ LANGUAGE plpgsql;

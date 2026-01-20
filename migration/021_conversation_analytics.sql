-- Conversation Analytics Schema
-- Stores all conversation messages and responses for analytics and iteration
-- Created: 2026-01-05

-- Main conversation analytics table
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id SERIAL PRIMARY KEY,

    -- Identifiers
    conversation_id INTEGER NOT NULL,
    user_id INTEGER DEFAULT 1,
    message_id UUID DEFAULT gen_random_uuid(),

    -- Message content
    question TEXT NOT NULL,
    response TEXT,

    -- Classification and tools
    tools_used TEXT[],
    confidence FLOAT,

    -- Timing
    response_time_ms INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Rich metadata (stores full raw response for detailed analysis)
    metadata JSONB DEFAULT '{}',

    -- Session info
    session_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- Status tracking
    status VARCHAR(50) DEFAULT 'completed',  -- 'completed', 'error', 'timeout'
    error_message TEXT,

    -- Analytics flags
    was_helpful BOOLEAN,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_conv_analytics_conversation ON conversation_analytics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_user ON conversation_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_created ON conversation_analytics(created_at);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_status ON conversation_analytics(status);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_confidence ON conversation_analytics(confidence);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_tools ON conversation_analytics USING GIN(tools_used);
CREATE INDEX IF NOT EXISTS idx_conv_analytics_metadata ON conversation_analytics USING GIN(metadata);

-- Full-text search on questions
CREATE INDEX IF NOT EXISTS idx_conv_analytics_question_search ON conversation_analytics USING GIN(to_tsvector('english', question));

-- Daily aggregates for dashboard
CREATE TABLE IF NOT EXISTS conversation_analytics_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,

    -- Volume metrics
    total_messages INTEGER DEFAULT 0,
    unique_conversations INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,

    -- Quality metrics
    avg_confidence FLOAT,
    avg_response_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    timeout_count INTEGER DEFAULT 0,

    -- Tool usage breakdown
    tool_usage JSONB DEFAULT '{}',  -- {tool_name: count, ...}

    -- Confidence distribution
    confidence_distribution JSONB DEFAULT '{}',  -- {high: n, medium: n, low: n}

    -- Top questions (for identifying patterns)
    top_question_patterns JSONB DEFAULT '[]',

    -- User satisfaction (if rated)
    avg_rating FLOAT,
    total_ratings INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- View for recent analytics (last 24 hours)
CREATE OR REPLACE VIEW v_conversation_analytics_24h AS
SELECT
    COUNT(*) as total_messages,
    COUNT(DISTINCT conversation_id) as unique_conversations,
    COUNT(DISTINCT user_id) as unique_users,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence,
    ROUND(AVG(response_time_ms)::numeric, 0) as avg_response_time_ms,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
    SUM(CASE WHEN confidence >= 0.7 THEN 1 ELSE 0 END) as high_confidence_count,
    SUM(CASE WHEN confidence >= 0.4 AND confidence < 0.7 THEN 1 ELSE 0 END) as medium_confidence_count,
    SUM(CASE WHEN confidence < 0.4 OR confidence IS NULL THEN 1 ELSE 0 END) as low_confidence_count
FROM conversation_analytics
WHERE created_at > NOW() - INTERVAL '24 hours';

-- View for tool usage analytics
CREATE OR REPLACE VIEW v_tool_usage_analytics AS
SELECT
    tool_name,
    COUNT(*) as usage_count,
    ROUND(AVG(ca.confidence)::numeric, 3) as avg_confidence_when_used,
    ROUND(AVG(ca.response_time_ms)::numeric, 0) as avg_response_time_ms
FROM conversation_analytics ca,
     LATERAL unnest(ca.tools_used) as tool_name
WHERE ca.created_at > NOW() - INTERVAL '30 days'
GROUP BY tool_name
ORDER BY usage_count DESC;

-- View for question patterns (for identifying common queries)
CREATE OR REPLACE VIEW v_question_patterns AS
SELECT
    CASE
        WHEN question ILIKE '%call%' OR question ILIKE '%funding%' THEN 'funding_calls'
        WHEN question ILIKE '%project%' OR question ILIKE '%cordis%' THEN 'projects'
        WHEN question ILIKE '%partner%' OR question ILIKE '%consortium%' THEN 'partners'
        WHEN question ILIKE '%budget%' OR question ILIKE '%cost%' THEN 'budget'
        WHEN question ILIKE '%eligibl%' THEN 'eligibility'
        WHEN question ILIKE '%deadline%' OR question ILIKE '%when%' THEN 'timing'
        WHEN question ILIKE '%horizon%' OR question ILIKE '%cluster%' THEN 'programme_info'
        ELSE 'other'
    END as question_category,
    COUNT(*) as count,
    ROUND(AVG(confidence)::numeric, 3) as avg_confidence,
    ROUND(AVG(response_time_ms)::numeric, 0) as avg_response_time_ms
FROM conversation_analytics
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY question_category
ORDER BY count DESC;

-- Function to aggregate daily analytics
CREATE OR REPLACE FUNCTION aggregate_conversation_analytics_daily(p_date DATE DEFAULT CURRENT_DATE - 1)
RETURNS void AS $$
BEGIN
    INSERT INTO conversation_analytics_daily (
        date,
        total_messages,
        unique_conversations,
        unique_users,
        avg_confidence,
        avg_response_time_ms,
        error_count,
        timeout_count,
        tool_usage,
        confidence_distribution,
        avg_rating,
        total_ratings
    )
    SELECT
        p_date,
        COUNT(*),
        COUNT(DISTINCT conversation_id),
        COUNT(DISTINCT user_id),
        AVG(confidence),
        AVG(response_time_ms)::integer,
        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END),
        (
            SELECT jsonb_object_agg(tool_name, tool_count)
            FROM (
                SELECT unnest(tools_used) as tool_name, COUNT(*) as tool_count
                FROM conversation_analytics
                WHERE created_at::date = p_date
                GROUP BY unnest(tools_used)
            ) tool_counts
        ),
        jsonb_build_object(
            'high', SUM(CASE WHEN confidence >= 0.7 THEN 1 ELSE 0 END),
            'medium', SUM(CASE WHEN confidence >= 0.4 AND confidence < 0.7 THEN 1 ELSE 0 END),
            'low', SUM(CASE WHEN confidence < 0.4 OR confidence IS NULL THEN 1 ELSE 0 END)
        ),
        AVG(user_rating),
        SUM(CASE WHEN user_rating IS NOT NULL THEN 1 ELSE 0 END)
    FROM conversation_analytics
    WHERE created_at::date = p_date
    ON CONFLICT (date) DO UPDATE SET
        total_messages = EXCLUDED.total_messages,
        unique_conversations = EXCLUDED.unique_conversations,
        unique_users = EXCLUDED.unique_users,
        avg_confidence = EXCLUDED.avg_confidence,
        avg_response_time_ms = EXCLUDED.avg_response_time_ms,
        error_count = EXCLUDED.error_count,
        timeout_count = EXCLUDED.timeout_count,
        tool_usage = EXCLUDED.tool_usage,
        confidence_distribution = EXCLUDED.confidence_distribution,
        avg_rating = EXCLUDED.avg_rating,
        total_ratings = EXCLUDED.total_ratings,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE conversation_analytics IS 'Stores all conversation messages and responses for analytics, iteration, and quality improvement';
COMMENT ON COLUMN conversation_analytics.tools_used IS 'Array of tool names used to answer the question';
COMMENT ON COLUMN conversation_analytics.confidence IS 'AI-reported confidence in the response (0.0 to 1.0)';
COMMENT ON COLUMN conversation_analytics.metadata IS 'Full raw response metadata in JSON format for detailed analysis';

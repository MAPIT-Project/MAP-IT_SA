-- DDL Schema Migration: 009_user_feedback
-- Target: Collecting user feedback and generating quality improvements insights

-- 1. Response Feedback Table
CREATE TABLE IF NOT EXISTS response_feedback (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) NOT NULL,
    message_id VARCHAR(100),
    query_text TEXT,
    response_text TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5), -- 1 to 5 stars rating
    feedback_type VARCHAR(50),                         -- 'helpful', 'not_helpful', 'incorrect', 'incomplete', 'other'
    feedback_text TEXT,                                 -- Free text comments
    tools_used TEXT[],                                  -- List of tools that were active during query
    query_type VARCHAR(100),                            -- Intent classification/query category
    response_time_ms INTEGER,                           -- Speed of request execution
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_response_feedback_conv_id ON response_feedback(conversation_id);
CREATE INDEX IF NOT EXISTS idx_response_feedback_rating ON response_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_response_feedback_type ON response_feedback(feedback_type);

-- 2. Feedback Insights Table (Aggregated reports and analysis of system weak points)
CREATE TABLE IF NOT EXISTS feedback_insights (
    id SERIAL PRIMARY KEY,
    insight_type VARCHAR(50) NOT NULL,                  -- 'tool_improvement', 'completeness', 'accuracy'
    priority VARCHAR(10) DEFAULT 'medium',              -- 'low', 'medium', 'high'
    message TEXT NOT NULL,                              -- Recommendation message
    data JSONB DEFAULT '{}'::jsonb,                     -- Analytical numbers / support data
    resolved BOOLEAN DEFAULT FALSE,                     -- Resolution status
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_insights_resolved ON feedback_insights(resolved);
CREATE INDEX IF NOT EXISTS idx_feedback_insights_type ON feedback_insights(insight_type);

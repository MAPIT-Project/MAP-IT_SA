-- DDL Schema Migration: 008_tool_analytics
-- Target: Conversation Logging and Tool Performance Tracking

-- 1. Conversation Analytics Table
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) NOT NULL,
    user_id INTEGER DEFAULT 1,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    question TEXT NOT NULL,
    response TEXT,
    tools_used TEXT[],                                 -- Array of tools executed for this message
    confidence NUMERIC(4, 3),                          -- Model confidence score
    response_time_ms INTEGER,                           -- Total processing time
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,                 -- Context metadata, program info, etc.
    session_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'completed',             -- completed, error, interrupted
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_analytics_conv_id ON conversation_analytics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_created ON conversation_analytics(created_at);

-- 2. Tool Usage Analytics Table
CREATE TABLE IF NOT EXISTS tool_usage_analytics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    conversation_id VARCHAR(100),
    query_hash VARCHAR(16),
    tool_name VARCHAR(100) NOT NULL,
    parameters JSONB,                                  -- Arguments passed to the tool
    execution_time_ms INTEGER,                         -- Execution duration in ms
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    result_count INTEGER,                              -- Number of records returned
    result_quality_score NUMERIC(3, 2),                -- Optional LLM or metric quality score
    speculative BOOLEAN DEFAULT FALSE,                 -- Whether run as a speculative/parallel task
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tool_usage_tool_name ON tool_usage_analytics(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_usage_conv_id ON tool_usage_analytics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_timestamp ON tool_usage_analytics(timestamp);

-- 3. Tool Combination Analytics Table (Sequences of tools used together)
CREATE TABLE IF NOT EXISTS tool_combination_analytics (
    id SERIAL PRIMARY KEY,
    tool_sequence TEXT[] UNIQUE NOT NULL,               -- Unique ordered array of tool names
    occurrence_count INTEGER DEFAULT 1,
    avg_total_time_ms NUMERIC(10, 2),
    success_rate NUMERIC(4, 3),                         -- Success percentage (0.0 to 1.0)
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tool_combination_sequence ON tool_combination_analytics USING gin (tool_sequence);

-- Simple migration script for Context-Aware AI System v2
-- Core tables only, no complex functions

-- 1. Conversation Memory Table
CREATE TABLE IF NOT EXISTS conversation_memory (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Fact Store Table
CREATE TABLE IF NOT EXISTS conversation_facts (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    fact_type VARCHAR(100) NOT NULL,
    fact_content TEXT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 0.5,
    source_message_id INTEGER,
    extracted_at TIMESTAMP DEFAULT NOW()
);

-- 3. Entity Cards Table
CREATE TABLE IF NOT EXISTS entity_cards (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    entity_data JSONB,
    first_mentioned_at TIMESTAMP DEFAULT NOW(),
    last_referenced_at TIMESTAMP DEFAULT NOW(),
    reference_count INTEGER DEFAULT 1
);

-- 4. Retrieval Cache Table
CREATE TABLE IF NOT EXISTS retrieval_cache (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    query_hash VARCHAR(64) NOT NULL,
    retrieved_chunks JSONB,
    relevance_scores JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    ttl_seconds INTEGER DEFAULT 3600
);

-- 5. Tool Execution Log
CREATE TABLE IF NOT EXISTS tool_execution_log (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    message_id INTEGER,
    tool_name VARCHAR(100) NOT NULL,
    tool_input JSONB,
    tool_output JSONB,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes separately
CREATE INDEX IF NOT EXISTS idx_conversation_memory_type 
    ON conversation_memory(conversation_id, memory_type);

CREATE INDEX IF NOT EXISTS idx_facts_conversation 
    ON conversation_facts(conversation_id);

CREATE INDEX IF NOT EXISTS idx_facts_confidence 
    ON conversation_facts(conversation_id, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_entity_cards_conversation 
    ON entity_cards(conversation_id, entity_type);

CREATE INDEX IF NOT EXISTS idx_entity_cards_references 
    ON entity_cards(conversation_id, reference_count DESC);

CREATE INDEX IF NOT EXISTS idx_retrieval_cache_query 
    ON retrieval_cache(conversation_id, query_hash);

CREATE INDEX IF NOT EXISTS idx_tool_log_conversation 
    ON tool_execution_log(conversation_id);

-- Add unique constraints
ALTER TABLE conversation_memory 
ADD CONSTRAINT IF NOT EXISTS unique_conversation_memory 
UNIQUE (conversation_id, memory_type);

ALTER TABLE entity_cards 
ADD CONSTRAINT IF NOT EXISTS unique_entity_cards 
UNIQUE (conversation_id, entity_type, entity_name);

ALTER TABLE retrieval_cache 
ADD CONSTRAINT IF NOT EXISTS unique_retrieval_cache 
UNIQUE (conversation_id, query_hash);

-- Add migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES ('v2.0.0_context_aware_ai')
ON CONFLICT (version) DO NOTHING;
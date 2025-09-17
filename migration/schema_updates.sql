-- Migration script for Context-Aware AI System v2
-- Run this to update your database schema

-- 1. Conversation Memory Table
CREATE TABLE IF NOT EXISTS conversation_memory (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    memory_type VARCHAR(50) NOT NULL, -- 'summary', 'facts', 'entities'
    content JSONB NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(conversation_id, memory_type)
);

-- 2. Fact Store Table
CREATE TABLE IF NOT EXISTS conversation_facts (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    fact_type VARCHAR(100) NOT NULL, -- 'decision', 'constraint', 'preference', 'entity'
    fact_content TEXT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 0.5,
    source_message_id INTEGER,
    extracted_at TIMESTAMP DEFAULT NOW()
);

-- 3. Entity Cards Table
CREATE TABLE IF NOT EXISTS entity_cards (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- 'project', 'organization', 'person', 'topic'
    entity_name VARCHAR(255) NOT NULL,
    entity_data JSONB,
    first_mentioned_at TIMESTAMP DEFAULT NOW(),
    last_referenced_at TIMESTAMP DEFAULT NOW(),
    reference_count INTEGER DEFAULT 1,
    UNIQUE(conversation_id, entity_type, entity_name)
);

-- 4. Retrieval Cache Table
CREATE TABLE IF NOT EXISTS retrieval_cache (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    query_hash VARCHAR(64) NOT NULL,
    retrieved_chunks JSONB,
    relevance_scores JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    ttl_seconds INTEGER DEFAULT 3600,
    UNIQUE(conversation_id, query_hash)
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

-- 6. Document Chunks Table (for new chunking strategy)
CREATE TABLE IF NOT EXISTS document_chunks_v2 (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(100) UNIQUE NOT NULL,
    document_id VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    token_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7. Add vector search extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- 8. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversation_memory_type 
    ON conversation_memory(conversation_id, memory_type);

CREATE INDEX IF NOT EXISTS idx_facts_confidence 
    ON conversation_facts(conversation_id, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_entity_cards_references 
    ON entity_cards(conversation_id, reference_count DESC);

-- 9. Create cleanup function for old cache entries
CREATE OR REPLACE FUNCTION cleanup_old_cache() RETURNS void AS $$
BEGIN
    DELETE FROM retrieval_cache 
    WHERE created_at < NOW() - INTERVAL '1 day';
END;
$$ LANGUAGE plpgsql;

-- 10. Create trigger for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversation_memory_updated_at 
    BEFORE UPDATE ON conversation_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 11. Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- 12. Add migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES ('v2.0.0_context_aware_ai')
ON CONFLICT (version) DO NOTHING;

-- Migration complete!
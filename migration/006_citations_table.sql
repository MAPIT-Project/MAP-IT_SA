-- Migration script for Citations Table
-- This table will store citations from streaming responses

CREATE TABLE IF NOT EXISTS citations (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    message_id INTEGER,
    citation_type VARCHAR(50) NOT NULL, -- 'project', 'call', 'document'
    citation_key VARCHAR(255) NOT NULL, -- project ID, call ID, etc.
    citation_data JSONB NOT NULL, -- Full citation data
    citation_text TEXT, -- Text representation of the citation
    relevance_score DECIMAL(5,4),
    position_in_response INTEGER, -- Position of citation in the response
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_citations_conversation 
    ON citations(conversation_id);

CREATE INDEX IF NOT EXISTS idx_citations_message 
    ON citations(message_id);

CREATE INDEX IF NOT EXISTS idx_citations_type 
    ON citations(citation_type);

CREATE INDEX IF NOT EXISTS idx_citations_key 
    ON citations(citation_key);

CREATE INDEX IF NOT EXISTS idx_citations_relevance 
    ON citations(relevance_score DESC);

-- Add unique constraint to prevent duplicate citations
CREATE UNIQUE INDEX IF NOT EXISTS idx_citations_unique 
    ON citations(conversation_id, message_id, citation_key, position_in_response);

-- Add migration tracking (create table if not exists first)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES ('v2.0.1_citations_table')
ON CONFLICT (version) DO NOTHING;
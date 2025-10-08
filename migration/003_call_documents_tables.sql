-- Migration: Call Documents System
-- Purpose: Add tables for call-specific document storage and RAG

-- Table 1: Call Documents
-- Stores metadata and content for call-specific documents
CREATE TABLE IF NOT EXISTS call_documents (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    document_title VARCHAR(500),
    document_content TEXT,
    document_url VARCHAR(1000),
    file_path VARCHAR(500),
    section_name VARCHAR(255),
    page_numbers VARCHAR(50),
    last_updated TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for call_documents
CREATE INDEX IF NOT EXISTS idx_call_documents_identifier ON call_documents(call_identifier);
CREATE INDEX IF NOT EXISTS idx_call_documents_type ON call_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_call_documents_call_type ON call_documents(call_identifier, document_type);

-- Table 2: Document Chunks
-- Stores chunked text for RAG retrieval
CREATE TABLE IF NOT EXISTS call_document_chunks (
    id SERIAL PRIMARY KEY,
    call_document_id INTEGER NOT NULL,
    call_identifier VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    section_title VARCHAR(255),
    page_numbers INTEGER[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (call_document_id) REFERENCES call_documents(id) ON DELETE CASCADE
);

-- Indexes for call_document_chunks
CREATE INDEX IF NOT EXISTS idx_call_chunks_call ON call_document_chunks(call_identifier);
CREATE INDEX IF NOT EXISTS idx_call_chunks_document ON call_document_chunks(call_document_id);
CREATE INDEX IF NOT EXISTS idx_call_chunks_section ON call_document_chunks(section_title);

-- Full-text search index for chunks
CREATE INDEX IF NOT EXISTS idx_call_chunks_text_search 
ON call_document_chunks USING gin(to_tsvector('english', chunk_text));

-- Table 3: Conversation Call Context
-- Tracks which call a conversation is focused on
CREATE TABLE IF NOT EXISTS conversation_call_context (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    call_identifier VARCHAR(255) NOT NULL,
    call_title TEXT,
    call_deadline TIMESTAMP,
    call_budget_total BIGINT,
    interest_level VARCHAR(50) DEFAULT 'medium',
    preparation_stage VARCHAR(100) DEFAULT 'discovery',
    notes TEXT,
    last_mentioned_at TIMESTAMP DEFAULT NOW(),
    reference_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(conversation_id, call_identifier)
);

-- Indexes for conversation_call_context
CREATE INDEX IF NOT EXISTS idx_conv_call_context_conv ON conversation_call_context(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conv_call_context_call ON conversation_call_context(call_identifier);
CREATE INDEX IF NOT EXISTS idx_conv_call_context_recent ON conversation_call_context(last_mentioned_at DESC);

-- Comments for documentation
COMMENT ON TABLE call_documents IS 'Stores call-specific documents (PDFs, guides, templates) for RAG';
COMMENT ON TABLE call_document_chunks IS 'Text chunks from call documents for semantic search and retrieval';
COMMENT ON TABLE conversation_call_context IS 'Tracks which funding call each conversation is focused on';

COMMENT ON COLUMN call_documents.document_type IS 'Type: work_programme, topic_description, application_guide, eligibility_rules, evaluation_guide, budget_template, proposal_template, faq, other';
COMMENT ON COLUMN conversation_call_context.preparation_stage IS 'Stage: discovery, eligibility, drafting, review, submission';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON call_documents TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON call_document_chunks TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON conversation_call_context TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE call_documents_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE call_document_chunks_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE conversation_call_context_id_seq TO your_app_user;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Call documents tables created successfully!';
    RAISE NOTICE 'Tables: call_documents, call_document_chunks, conversation_call_context';
END $$;


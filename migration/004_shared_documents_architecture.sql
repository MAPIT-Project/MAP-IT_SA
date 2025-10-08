-- Migration: Shared Documents Architecture
-- Purpose: Store documents once, link them to multiple calls via mappings

-- Drop old tables (if you want to start fresh - CAREFUL!)
-- DROP TABLE IF EXISTS call_document_chunks CASCADE;
-- DROP TABLE IF EXISTS call_documents CASCADE;

-- Table 1: Shared Documents Repository
-- Stores each unique document once
CREATE TABLE IF NOT EXISTS shared_documents (
    id SERIAL PRIMARY KEY,
    document_key VARCHAR(255) UNIQUE NOT NULL, -- e.g., "he_general_annexes_2023-2025"
    document_type VARCHAR(100) NOT NULL, -- work_programme, general_annexes, programme_guide, etc.
    document_title VARCHAR(500),
    document_version VARCHAR(50), -- e.g., "2023-2025", "v1.2"
    scope VARCHAR(100), -- 'global' (all calls), 'cluster' (one cluster), 'call' (specific call)
    scope_identifier VARCHAR(255), -- NULL for global, 'CLUSTER-6' for cluster, 'CALL-ID' for specific
    document_content TEXT,
    document_url VARCHAR(1000),
    file_path VARCHAR(500),
    file_hash VARCHAR(64), -- SHA256 hash to detect duplicates
    last_updated TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for shared_documents
CREATE INDEX IF NOT EXISTS idx_shared_docs_key ON shared_documents(document_key);
CREATE INDEX IF NOT EXISTS idx_shared_docs_type ON shared_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_shared_docs_scope ON shared_documents(scope, scope_identifier);
CREATE INDEX IF NOT EXISTS idx_shared_docs_hash ON shared_documents(file_hash);

-- Table 2: Call-Document Mappings
-- Many-to-many relationship between calls and documents
CREATE TABLE IF NOT EXISTS call_document_mappings (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) NOT NULL,
    document_id INTEGER NOT NULL,
    relevance_score DECIMAL(3,2) DEFAULT 1.0, -- How relevant is this doc to this call (0.0-1.0)
    is_primary BOOLEAN DEFAULT FALSE, -- Is this the main document for this call?
    mapping_source VARCHAR(100) DEFAULT 'manual', -- 'manual', 'api', 'inferred'
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (document_id) REFERENCES shared_documents(id) ON DELETE CASCADE,
    UNIQUE(call_identifier, document_id)
);

-- Indexes for call_document_mappings
CREATE INDEX IF NOT EXISTS idx_call_doc_map_call ON call_document_mappings(call_identifier);
CREATE INDEX IF NOT EXISTS idx_call_doc_map_doc ON call_document_mappings(document_id);
CREATE INDEX IF NOT EXISTS idx_call_doc_map_primary ON call_document_mappings(call_identifier, is_primary);

-- Table 3: Document Chunks (Updated)
-- Now references shared_documents instead of call-specific documents
DROP TABLE IF EXISTS shared_document_chunks CASCADE;
CREATE TABLE IF NOT EXISTS shared_document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    section_title VARCHAR(255),
    page_numbers INTEGER[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (document_id) REFERENCES shared_documents(id) ON DELETE CASCADE
);

-- Indexes for shared_document_chunks
CREATE INDEX IF NOT EXISTS idx_shared_chunks_doc ON shared_document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_shared_chunks_section ON shared_document_chunks(section_title);
CREATE INDEX IF NOT EXISTS idx_shared_chunks_text_search 
ON shared_document_chunks USING gin(to_tsvector('english', chunk_text));

-- View: Call-Specific Document Access
-- Makes it easy to query "all chunks for a specific call"
CREATE OR REPLACE VIEW call_document_chunks_view AS
SELECT 
    cdm.call_identifier,
    sd.document_key,
    sd.document_type,
    sd.document_title,
    sdc.id as chunk_id,
    sdc.chunk_text,
    sdc.chunk_index,
    sdc.section_title,
    sdc.page_numbers,
    sdc.token_count,
    cdm.relevance_score,
    cdm.is_primary
FROM call_document_mappings cdm
JOIN shared_documents sd ON cdm.document_id = sd.id
JOIN shared_document_chunks sdc ON sd.id = sdc.document_id;

-- Helper function: Get all chunks for a call
CREATE OR REPLACE FUNCTION get_chunks_for_call(
    p_call_identifier VARCHAR,
    p_search_query TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    chunk_id INTEGER,
    chunk_text TEXT,
    section_title VARCHAR,
    document_type VARCHAR,
    document_title VARCHAR,
    relevance_score DECIMAL
) AS $$
BEGIN
    IF p_search_query IS NULL THEN
        -- Return all chunks
        RETURN QUERY
        SELECT 
            sdc.id,
            sdc.chunk_text,
            sdc.section_title,
            sd.document_type,
            sd.document_title,
            cdm.relevance_score
        FROM call_document_mappings cdm
        JOIN shared_documents sd ON cdm.document_id = sd.id
        JOIN shared_document_chunks sdc ON sd.id = sdc.document_id
        WHERE cdm.call_identifier = p_call_identifier
        ORDER BY cdm.is_primary DESC, cdm.relevance_score DESC
        LIMIT p_limit;
    ELSE
        -- Full-text search
        RETURN QUERY
        SELECT 
            sdc.id,
            sdc.chunk_text,
            sdc.section_title,
            sd.document_type,
            sd.document_title,
            cdm.relevance_score
        FROM call_document_mappings cdm
        JOIN shared_documents sd ON cdm.document_id = sd.id
        JOIN shared_document_chunks sdc ON sd.id = sdc.document_id
        WHERE cdm.call_identifier = p_call_identifier
          AND to_tsvector('english', sdc.chunk_text) @@ plainto_tsquery('english', p_search_query)
        ORDER BY 
            ts_rank(to_tsvector('english', sdc.chunk_text), plainto_tsquery('english', p_search_query)) DESC,
            cdm.is_primary DESC
        LIMIT p_limit;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE shared_documents IS 'Central repository for all Horizon Europe documents (stored once, referenced many times)';
COMMENT ON TABLE call_document_mappings IS 'Many-to-many mapping between calls and documents';
COMMENT ON TABLE shared_document_chunks IS 'Text chunks from shared documents for semantic search';
COMMENT ON COLUMN shared_documents.scope IS 'Document scope: global (all calls), cluster (one cluster), call (specific call)';
COMMENT ON COLUMN shared_documents.document_key IS 'Unique identifier like "he_general_annexes_2023-2025" or "he_wp_cluster6_2023-2025"';
COMMENT ON COLUMN call_document_mappings.relevance_score IS 'How relevant is this document to this call (1.0 = primary, 0.5 = somewhat relevant)';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Shared documents architecture created successfully!';
    RAISE NOTICE 'Tables: shared_documents, call_document_mappings, shared_document_chunks';
    RAISE NOTICE 'View: call_document_chunks_view';
    RAISE NOTICE 'Function: get_chunks_for_call(call_id, search_query, limit)';
END $$;



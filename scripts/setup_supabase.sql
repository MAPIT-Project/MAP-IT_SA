-- Horizon Europe RAG System - Supabase Setup Script
-- Run this script in your Supabase SQL editor to set up the database

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Create documents table for storing source documents
CREATE TABLE IF NOT EXISTS horizon_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL CHECK (source_type IN ('pdf', 'web', 'cordis', 'manual')),
    source_url TEXT,
    file_path TEXT,
    title TEXT NOT NULL,
    document_type TEXT CHECK (document_type IN (
        'work_programme', 
        'programme_guide', 
        'call_text',
        'grant_agreement',
        'faq',
        'manual',
        'policy',
        'template'
    )),
    programme_year TEXT,
    programme_part TEXT, -- e.g., 'Cluster 4', 'Pillar 2'
    language TEXT DEFAULT 'en',
    version TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'processing', 'failed')),
    file_hash TEXT, -- For duplicate detection
    total_chunks INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    
    -- Constraints
    CONSTRAINT unique_file_hash UNIQUE(file_hash)
);

-- Create document chunks with embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES horizon_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_hash TEXT NOT NULL, -- For duplicate detection
    content TEXT NOT NULL,
    content_length INTEGER,
    embedding vector(768), -- Google text-embedding-004 dimension
    
    -- Metadata fields
    section_title TEXT,
    page_number INTEGER,
    chapter TEXT,
    subsection TEXT,
    
    -- Search optimization
    content_tokens tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    token_count INTEGER,
    embedding_model TEXT DEFAULT 'text-embedding-004',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_chunk_per_doc UNIQUE(document_id, chunk_index),
    CONSTRAINT unique_chunk_hash UNIQUE(chunk_hash)
);

-- Create search queries log for analytics
CREATE TABLE IF NOT EXISTS search_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT NOT NULL,
    query_embedding vector(768),
    search_type TEXT CHECK (search_type IN ('semantic', 'keyword', 'hybrid')),
    filters JSONB,
    results_count INTEGER,
    top_chunk_ids UUID[],
    response_time_ms INTEGER,
    user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create document processing jobs
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES horizon_documents(id) ON DELETE CASCADE,
    job_type TEXT CHECK (job_type IN ('pdf_extraction', 'web_scraping', 'embedding_generation', 'chunking')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    progress INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Create cached embeddings for common queries
CREATE TABLE IF NOT EXISTS embedding_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text_hash TEXT UNIQUE NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    model_version TEXT DEFAULT 'text-embedding-004',
    usage_count INTEGER DEFAULT 1,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
-- Vector similarity search indexes
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_cosine ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_chunks_content_gin ON document_chunks USING gin(content_tokens);
CREATE INDEX IF NOT EXISTS idx_documents_title_trgm ON horizon_documents USING gin(title gin_trgm_ops);

-- Metadata and filtering indexes
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_documents_type ON horizon_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_year ON horizon_documents(programme_year);
CREATE INDEX IF NOT EXISTS idx_documents_status ON horizon_documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created ON horizon_documents(created_at DESC);

-- Compound indexes for common queries
CREATE INDEX IF NOT EXISTS idx_documents_active_type ON horizon_documents(status, document_type) 
WHERE status = 'active';

-- Enable Row Level Security
ALTER TABLE horizon_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Public read access for active documents
CREATE POLICY "Public documents are viewable by everyone" 
ON horizon_documents FOR SELECT 
USING (status = 'active');

CREATE POLICY "Public chunks are viewable by everyone" 
ON document_chunks FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM horizon_documents 
        WHERE horizon_documents.id = document_chunks.document_id 
        AND horizon_documents.status = 'active'
    )
);

-- Service role can manage all documents
CREATE POLICY "Service role can manage all documents" 
ON horizon_documents FOR ALL 
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage all chunks" 
ON document_chunks FOR ALL 
USING (auth.role() = 'service_role');

-- Create stored functions
-- Function for semantic search with metadata filtering
CREATE OR REPLACE FUNCTION search_documents(
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_document_type TEXT DEFAULT NULL,
    filter_year TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    document_title TEXT,
    document_type TEXT,
    similarity FLOAT,
    metadata JSONB,
    section_title TEXT,
    page_number INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id as chunk_id,
        c.document_id,
        c.content,
        d.title as document_title,
        d.document_type,
        1 - (c.embedding <=> query_embedding) as similarity,
        c.metadata,
        c.section_title,
        c.page_number
    FROM document_chunks c
    JOIN horizon_documents d ON c.document_id = d.id
    WHERE 
        d.status = 'active'
        AND (filter_document_type IS NULL OR d.document_type = filter_document_type)
        AND (filter_year IS NULL OR d.programme_year = filter_year)
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function for hybrid search (vector + keyword)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(768),
    query_text TEXT,
    match_count INT DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    document_title TEXT,
    combined_score FLOAT,
    section_title TEXT,
    page_number INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT 
            c.id,
            c.document_id,
            c.content,
            c.section_title,
            c.page_number,
            1 - (c.embedding <=> query_embedding) as vector_score
        FROM document_chunks c
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    text_search AS (
        SELECT 
            c.id,
            c.document_id,
            c.content,
            c.section_title,
            c.page_number,
            ts_rank(c.content_tokens, plainto_tsquery('english', query_text)) as text_score
        FROM document_chunks c
        WHERE c.content_tokens @@ plainto_tsquery('english', query_text)
        ORDER BY text_score DESC
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT 
            COALESCE(v.id, t.id) as chunk_id,
            COALESCE(v.document_id, t.document_id) as doc_id,
            COALESCE(v.content, t.content) as content_text,
            COALESCE(v.section_title, t.section_title) as section_title,
            COALESCE(v.page_number, t.page_number) as page_number,
            COALESCE(v.vector_score, 0) * vector_weight + 
            COALESCE(t.text_score, 0) * (1 - vector_weight) as score
        FROM vector_search v
        FULL OUTER JOIN text_search t ON v.id = t.id
    )
    SELECT 
        combined.chunk_id,
        combined.doc_id as document_id,
        combined.content_text as content,
        d.title as document_title,
        combined.score as combined_score,
        combined.section_title,
        combined.page_number
    FROM combined
    JOIN horizon_documents d ON combined.doc_id = d.id
    WHERE d.status = 'active'
    ORDER BY combined.score DESC
    LIMIT match_count;
END;
$$;

-- Function for keyword search
CREATE OR REPLACE FUNCTION keyword_search(
    query_text TEXT,
    limit_count INT DEFAULT 10,
    filter_document_type TEXT DEFAULT NULL,
    filter_year TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    document_title TEXT,
    document_type TEXT,
    score FLOAT,
    section_title TEXT,
    page_number INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id as chunk_id,
        c.document_id,
        c.content,
        d.title as document_title,
        d.document_type,
        ts_rank(c.content_tokens, plainto_tsquery('english', query_text)) as score,
        c.section_title,
        c.page_number
    FROM document_chunks c
    JOIN horizon_documents d ON c.document_id = d.id
    WHERE 
        c.content_tokens @@ plainto_tsquery('english', query_text)
        AND d.status = 'active'
        AND (filter_document_type IS NULL OR d.document_type = filter_document_type)
        AND (filter_year IS NULL OR d.programme_year = filter_year)
    ORDER BY score DESC
    LIMIT limit_count;
END;
$$;

-- Function to get document statistics
CREATE OR REPLACE FUNCTION get_document_stats()
RETURNS TABLE (
    total_documents BIGINT,
    total_chunks BIGINT,
    documents_by_type JSONB,
    documents_by_year JSONB,
    avg_chunks_per_document NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT d.id) as total_documents,
        COUNT(c.id) as total_chunks,
        jsonb_object_agg(
            COALESCE(d.document_type, 'unknown'), 
            doc_type_counts.count
        ) FILTER (WHERE d.document_type IS NOT NULL) as documents_by_type,
        jsonb_object_agg(
            COALESCE(d.programme_year, 'unknown'), 
            doc_year_counts.count
        ) FILTER (WHERE d.programme_year IS NOT NULL) as documents_by_year,
        AVG(d.total_chunks) as avg_chunks_per_document
    FROM horizon_documents d
    LEFT JOIN document_chunks c ON d.id = c.document_id
    LEFT JOIN LATERAL (
        SELECT document_type, COUNT(*) as count 
        FROM horizon_documents 
        WHERE status = 'active'
        GROUP BY document_type
    ) doc_type_counts ON d.document_type = doc_type_counts.document_type
    LEFT JOIN LATERAL (
        SELECT programme_year, COUNT(*) as count 
        FROM horizon_documents 
        WHERE status = 'active'
        GROUP BY programme_year
    ) doc_year_counts ON d.programme_year = doc_year_counts.programme_year
    WHERE d.status = 'active'
    GROUP BY doc_type_counts.count, doc_year_counts.count;
END;
$$;

-- Insert some sample data for testing (optional)
-- Uncomment the following lines if you want to add sample data

/*
INSERT INTO horizon_documents (
    title, 
    source_type, 
    document_type, 
    programme_year,
    status,
    metadata
) VALUES (
    'Sample Horizon Europe Work Programme 2023-2024',
    'manual',
    'work_programme',
    '2023-2024',
    'active',
    '{"sample": true, "description": "Sample document for testing"}'
);
*/

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO anon, authenticated;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Horizon Europe RAG database setup completed successfully!';
    RAISE NOTICE 'Tables created: horizon_documents, document_chunks, search_queries, ingestion_jobs, embedding_cache';
    RAISE NOTICE 'Indexes created for optimal performance';
    RAISE NOTICE 'RLS policies configured for security';
    RAISE NOTICE 'Search functions created: search_documents, hybrid_search, keyword_search, get_document_stats';
    RAISE NOTICE 'Ready to start ingesting documents and performing vector search!';
END $$;
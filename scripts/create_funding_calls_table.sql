-- ============================================================================
-- FUNDING CALLS TABLE
-- Generic table for storing structured call data from any EU funding programme
-- ============================================================================

-- Drop existing table if it exists (be careful in production!)
DROP TABLE IF EXISTS funding_calls CASCADE;

-- Create the main funding_calls table
CREATE TABLE funding_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Programme identification
    programme VARCHAR(50) NOT NULL,  -- 'horizon_europe', 'digital_europe', 'life', etc.
    programme_part VARCHAR(100),      -- 'Cluster 5', 'Pillar II', etc.
    work_programme_year INTEGER,      -- Year of the Work Programme document
    
    -- Call identification
    topic_code VARCHAR(100) NOT NULL UNIQUE,  -- e.g., 'HORIZON-CL5-2026-02-D3-14'
    call_identifier VARCHAR(100),              -- Parent call ID if applicable
    
    -- Basic info
    title TEXT NOT NULL,
    action_type VARCHAR(50),          -- 'RIA', 'IA', 'CSA', 'ERC-STG', 'EIC-Accelerator', etc.
    
    -- Dates
    call_year INTEGER,                -- Year the call is for (from topic code)
    opening_date DATE,
    deadline DATE,
    second_stage_deadline DATE,       -- For two-stage calls
    
    -- Status (can be updated)
    status VARCHAR(20) DEFAULT 'upcoming',  -- 'open', 'upcoming', 'closed', 'cancelled'
    
    -- Financial info
    budget_total DECIMAL(15, 2),      -- Total budget for this topic
    budget_per_project_min DECIMAL(15, 2),
    budget_per_project_max DECIMAL(15, 2),
    expected_projects INTEGER,        -- Expected number of grants
    funding_rate INTEGER,             -- Funding rate percentage (e.g., 100 for RIA)
    
    -- Content (the good stuff!)
    expected_outcome TEXT,
    scope TEXT,
    eligibility TEXT,
    
    -- Classification
    cluster VARCHAR(50),              -- 'CL1', 'CL2', etc. for Horizon Europe
    destination VARCHAR(200),         -- Destination name
    tags TEXT[],                      -- Keywords/tags for search
    
    -- Source tracking
    source_document_id UUID,          -- Link to horizon_documents if applicable
    source_document_title TEXT,
    source_page_number INTEGER,
    
    -- Portal URL
    portal_url TEXT,
    
    -- Flexible metadata for programme-specific fields
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_programme CHECK (programme IN (
        'horizon_europe',
        'horizon_plus',
        'digital_europe', 
        'life',
        'creative_europe',
        'edf',
        'euratom',
        'erasmus',
        'cef',
        'interreg',
        'other'
    )),
    CONSTRAINT valid_status CHECK (status IN ('open', 'upcoming', 'closed', 'cancelled'))
);

-- Create indexes for fast searching
CREATE INDEX idx_funding_calls_programme ON funding_calls(programme);
CREATE INDEX idx_funding_calls_topic_code ON funding_calls(topic_code);
CREATE INDEX idx_funding_calls_call_year ON funding_calls(call_year);
CREATE INDEX idx_funding_calls_status ON funding_calls(status);
CREATE INDEX idx_funding_calls_action_type ON funding_calls(action_type);
CREATE INDEX idx_funding_calls_cluster ON funding_calls(cluster);
CREATE INDEX idx_funding_calls_deadline ON funding_calls(deadline);

-- Full-text search index on title, scope, and expected_outcome
CREATE INDEX idx_funding_calls_fts ON funding_calls 
    USING gin(to_tsvector('english', 
        COALESCE(title, '') || ' ' || 
        COALESCE(scope, '') || ' ' || 
        COALESCE(expected_outcome, '')
    ));

-- GIN index on tags array
CREATE INDEX idx_funding_calls_tags ON funding_calls USING gin(tags);

-- GIN index on metadata JSONB
CREATE INDEX idx_funding_calls_metadata ON funding_calls USING gin(metadata);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_funding_calls_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER funding_calls_update_timestamp
    BEFORE UPDATE ON funding_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_funding_calls_timestamp();

-- ============================================================================
-- SEARCH FUNCTION
-- Efficient full-text search with filtering
-- ============================================================================

CREATE OR REPLACE FUNCTION search_funding_calls(
    search_query TEXT,
    filter_programme TEXT DEFAULT NULL,
    filter_status TEXT DEFAULT NULL,
    filter_action_type TEXT DEFAULT NULL,
    filter_cluster TEXT DEFAULT NULL,
    filter_year INTEGER DEFAULT NULL,
    include_closed BOOLEAN DEFAULT FALSE,
    max_results INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    programme VARCHAR(50),
    topic_code VARCHAR(100),
    title TEXT,
    action_type VARCHAR(50),
    status VARCHAR(20),
    deadline DATE,
    budget_total DECIMAL(15, 2),
    expected_outcome TEXT,
    scope TEXT,
    cluster VARCHAR(50),
    portal_url TEXT,
    relevance_score REAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fc.id,
        fc.programme,
        fc.topic_code,
        fc.title,
        fc.action_type,
        fc.status,
        fc.deadline,
        fc.budget_total,
        fc.expected_outcome,
        fc.scope,
        fc.cluster,
        fc.portal_url,
        ts_rank(
            to_tsvector('english', 
                COALESCE(fc.title, '') || ' ' || 
                COALESCE(fc.scope, '') || ' ' || 
                COALESCE(fc.expected_outcome, '')
            ),
            plainto_tsquery('english', search_query)
        ) AS relevance_score
    FROM funding_calls fc
    WHERE 
        -- Text search
        to_tsvector('english', 
            COALESCE(fc.title, '') || ' ' || 
            COALESCE(fc.scope, '') || ' ' || 
            COALESCE(fc.expected_outcome, '')
        ) @@ plainto_tsquery('english', search_query)
        -- Filters
        AND (filter_programme IS NULL OR fc.programme = filter_programme)
        AND (filter_action_type IS NULL OR fc.action_type = filter_action_type)
        AND (filter_cluster IS NULL OR fc.cluster = filter_cluster)
        AND (filter_year IS NULL OR fc.call_year = filter_year)
        AND (filter_status IS NULL OR fc.status = filter_status)
        AND (include_closed OR fc.status != 'closed')
    ORDER BY relevance_score DESC, fc.deadline ASC NULLS LAST
    LIMIT max_results;
END;
$$;

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View for open and upcoming calls only
CREATE OR REPLACE VIEW active_funding_calls AS
SELECT * FROM funding_calls
WHERE status IN ('open', 'upcoming')
ORDER BY deadline ASC NULLS LAST;

-- View for Horizon Europe calls only
CREATE OR REPLACE VIEW horizon_europe_calls AS
SELECT * FROM funding_calls
WHERE programme = 'horizon_europe'
ORDER BY call_year DESC, topic_code ASC;

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- This will be populated by the extraction script
-- Example structure:
/*
INSERT INTO funding_calls (
    programme, topic_code, title, action_type, 
    call_year, deadline, status,
    budget_total, expected_projects,
    expected_outcome, scope,
    cluster, portal_url
) VALUES (
    'horizon_europe',
    'HORIZON-CL5-2026-02-D3-14',
    'Development of innovative solutions strengthening the security of renewable energy value chains',
    'CSA',
    2026,
    '2026-09-04',
    'upcoming',
    5000000,
    2,
    'The security of Europe''s clean energy system will benefit from...',
    'Activities have to include: (1) networking related to...',
    'CL5',
    'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-CL5-2026-02-D3-14'
);
*/

-- Grant access to the API user (adjust username as needed)
-- GRANT SELECT, INSERT, UPDATE ON funding_calls TO api_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO api_user;

COMMENT ON TABLE funding_calls IS 'Structured funding call data extracted from EU programme Work Programmes. Supports Horizon Europe, Digital Europe, LIFE, and other EU funding programmes.';


-- Migration 005: Add Call Metadata Table
-- Store structured data extracted directly from EU Portal API
-- This gives the AI instant access to eligibility, budget, deadlines without searching PDFs

CREATE TABLE IF NOT EXISTS call_metadata (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) UNIQUE NOT NULL,
    
    -- Basic info
    title TEXT,
    summary TEXT,
    call_title TEXT,
    status VARCHAR(50),
    
    -- Dates
    opening_date TIMESTAMP,
    deadline_date TIMESTAMP,
    
    -- Budget
    budget_overview JSONB,
    min_contribution BIGINT,
    max_contribution BIGINT,
    expected_grants INTEGER,
    
    -- Eligibility (CRITICAL - extracted from API)
    eligible_countries TEXT, -- "Member States and Associated Countries"
    eligibility_restrictions TEXT, -- Any specific restrictions
    eligibility_conditions_html TEXT, -- Full HTML for reference
    
    -- Other structured data
    types_of_action TEXT[],
    cross_cutting_priorities TEXT[],
    tags TEXT[],
    keywords TEXT[],
    
    -- Links
    topic_url VARCHAR(1000),
    api_data_url VARCHAR(1000),
    
    -- Raw API response (for debugging/future use)
    raw_api_response JSONB,
    
    -- Metadata
    fetched_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_call_metadata_identifier ON call_metadata(call_identifier);
CREATE INDEX IF NOT EXISTS idx_call_metadata_deadline ON call_metadata(deadline_date);
CREATE INDEX IF NOT EXISTS idx_call_metadata_status ON call_metadata(status);
CREATE INDEX IF NOT EXISTS idx_call_metadata_search 
    ON call_metadata USING gin(to_tsvector('english', title || ' ' || COALESCE(summary, '')));

-- Comments
COMMENT ON TABLE call_metadata IS 'Structured metadata extracted directly from EU Portal API - gives AI instant access to key info';
COMMENT ON COLUMN call_metadata.eligible_countries IS 'Extracted from topicConditions HTML - e.g., "Member States and Associated Countries"';
COMMENT ON COLUMN call_metadata.eligibility_restrictions IS 'Any specific restrictions - e.g., "entities controlled by non-eligible countries excluded"';
COMMENT ON COLUMN call_metadata.eligibility_conditions_html IS 'Full eligibility HTML from API response for reference';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Call metadata table created successfully!';
    RAISE NOTICE '📊 Now the AI can access eligibility rules directly without searching PDFs';
END $$;


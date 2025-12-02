-- Fix for keyword_search function type mismatch
-- The ts_rank() function returns REAL, but the function was declared to return FLOAT (double precision)
-- This causes: "Returned type real does not match expected type double precision in column 6"

-- Drop the old function first
DROP FUNCTION IF EXISTS keyword_search(TEXT, INT, TEXT, TEXT);

-- Recreate with correct type casting
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
    score DOUBLE PRECISION,  -- Explicitly use DOUBLE PRECISION
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
        ts_rank(c.content_tokens, plainto_tsquery('english', query_text))::DOUBLE PRECISION as score,  -- Cast to DOUBLE PRECISION
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

-- Verify the function works
-- SELECT * FROM keyword_search('consortium eligibility', 5);


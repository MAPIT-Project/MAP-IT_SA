-- Fix for hybrid_search function type mismatch
-- ts_rank() returns REAL, needs to be cast to DOUBLE PRECISION

DROP FUNCTION IF EXISTS hybrid_search(vector(768), TEXT, INT, FLOAT);

CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(768),
    query_text TEXT,
    match_count INT DEFAULT 10,
    vector_weight DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    document_title TEXT,
    combined_score DOUBLE PRECISION,
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
            (1 - (c.embedding <=> query_embedding))::DOUBLE PRECISION as vector_score
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
            ts_rank(c.content_tokens, plainto_tsquery('english', query_text))::DOUBLE PRECISION as text_score
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
            (COALESCE(v.vector_score, 0.0) * vector_weight + 
             COALESCE(t.text_score, 0.0) * (1.0 - vector_weight))::DOUBLE PRECISION as score
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

-- Test the function
-- SELECT * FROM hybrid_search(
--     (SELECT embedding FROM document_chunks LIMIT 1),
--     'consortium eligibility Member State',
--     10,
--     0.5
-- );


-- Preserve editions and filter active documents before retrieval limits.
BEGIN;
CREATE OR REPLACE FUNCTION public.mapit_document_year_matches(document_period text, requested_year text)
RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT CASE
  WHEN requested_year IS NULL THEN true
  WHEN document_period = requested_year THEN true
  WHEN document_period ~ '^20[0-9]{2}-20[0-9]{2}$' AND requested_year ~ '^20[0-9]{2}$'
  THEN requested_year::integer BETWEEN substring(document_period,1,4)::integer
       AND substring(document_period,6,4)::integer
  ELSE false END;
$$;

CREATE OR REPLACE FUNCTION public.hybrid_search(query_embedding vector, query_text text, match_count integer DEFAULT 10, vector_weight double precision DEFAULT 0.5)
 RETURNS TABLE(chunk_id uuid, document_id uuid, content text, document_title text, combined_score double precision, section_title text, page_number integer)
 LANGUAGE plpgsql
AS $function$
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
        FROM document_chunks c JOIN horizon_documents active_doc ON active_doc.id=c.document_id AND active_doc.status='active'
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
        FROM document_chunks c JOIN horizon_documents active_doc ON active_doc.id=c.document_id AND active_doc.status='active'
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
$function$
;

CREATE OR REPLACE FUNCTION public.search_documents(query_embedding vector, match_threshold double precision DEFAULT 0.7, match_count integer DEFAULT 10, filter_document_type text DEFAULT NULL::text, filter_year text DEFAULT NULL::text)
 RETURNS TABLE(chunk_id uuid, document_id uuid, content text, document_title text, document_type text, similarity double precision, metadata jsonb, section_title text, page_number integer)
 LANGUAGE plpgsql
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        c.id as chunk_id,
        c.document_id,
        c.content,
        d.title as document_title,
        d.document_type,
        1 - (c.embedding <=> query_embedding) as similarity,
        COALESCE(c.metadata, '{}'::jsonb) || jsonb_build_object('source_url',d.source_url,'document_version',d.version,'programme_year',d.programme_year,'provenance',d.metadata->'provenance') as metadata,
        c.section_title,
        c.page_number
    FROM document_chunks c
    JOIN horizon_documents d ON c.document_id = d.id
    WHERE
        d.status = 'active'
        AND (filter_document_type IS NULL OR d.document_type = filter_document_type)
        AND public.mapit_document_year_matches(d.programme_year, filter_year)
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.keyword_search(query_text text, limit_count integer DEFAULT 10, filter_document_type text DEFAULT NULL::text, filter_year text DEFAULT NULL::text)
 RETURNS TABLE(chunk_id uuid, document_id uuid, content text, document_title text, document_type text, score double precision, section_title text, page_number integer)
 LANGUAGE plpgsql
AS $function$
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
        AND public.mapit_document_year_matches(d.programme_year, filter_year)
    ORDER BY score DESC
    LIMIT limit_count;
END;
$function$
;
COMMIT;

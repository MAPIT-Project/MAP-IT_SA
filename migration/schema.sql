-- MAP-IT Database Schema Setup Script
-- Generated from active tables in the running PostgreSQL/Supabase database.
-- Contains schemas for both frontend (webapp-ui) and backend (MAP-IT_SA) projects.
-- Excludes all unused/deprecated tables.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

pg_dump: warning: there are circular foreign-key constraints on this table:
pg_dump: detail: key
pg_dump: hint: You might not be able to restore the dump without using --disable-triggers or temporarily dropping the constraints.
pg_dump: hint: Consider using a full dump instead of a --data-only dump to avoid this problem.
--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8
-- Dumped by pg_dump version 15.8

SET statement_timeout = 0;

SET lock_timeout = 0;

SET idle_in_transaction_session_timeout = 0;

SET client_encoding = 'UTF8';

SET standard_conforming_strings = on;

SELECT pg_catalog.set_config('search_path', '', false);

SET check_function_bodies = false;

SET xmloption = content;

SET client_min_messages = warning;

SET row_security = off;


--
-- Name: _realtime; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA _realtime;


--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA auth;


--
-- Name: drizzle; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA drizzle;


--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA extensions;


--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA graphql;


--
-- Name: graphql_public; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA graphql_public;


--
-- Name: pg_net; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;



--
-- Name: EXTENSION pg_net; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pg_net IS 'Async HTTP';



--
-- Name: pgbouncer; Type: SCHEMA; Schema: -; Owner: pgbouncer
--

CREATE SCHEMA pgbouncer;


--
-- Name: pgsodium; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA pgsodium;


--
-- Name: pgsodium; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgsodium WITH SCHEMA pgsodium;



--
-- Name: EXTENSION pgsodium; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pgsodium IS 'Pgsodium is a modern cryptography library for Postgres.';



--
-- Name: realtime; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA realtime;


--
-- Name: storage; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA storage;


--
-- Name: supabase_functions; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA supabase_functions;


--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA vault;


--
-- Name: btree_gin; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gin WITH SCHEMA public;



--
-- Name: EXTENSION btree_gin; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION btree_gin IS 'support for indexing common datatypes in GIN';



--
-- Name: pg_graphql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_graphql WITH SCHEMA graphql;



--
-- Name: EXTENSION pg_graphql; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pg_graphql IS 'pg_graphql: GraphQL support';



--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;



--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';



--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;



--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';



--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;



--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';



--
-- Name: pgjwt; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgjwt WITH SCHEMA extensions;



--
-- Name: EXTENSION pgjwt; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pgjwt IS 'JSON Web Token API for Postgresql';



--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;



--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';



--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;



--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';



--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;



--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';



--
-- Name: aal_level; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.aal_level AS ENUM (
    'aal1',
    'aal2',
    'aal3'
);


--
-- Name: code_challenge_method; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.code_challenge_method AS ENUM (
    's256',
    'plain'
);


--
-- Name: factor_status; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.factor_status AS ENUM (
    'unverified',
    'verified'
);


--
-- Name: factor_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.factor_type AS ENUM (
    'totp',
    'webauthn',
    'phone'
);


--
-- Name: one_time_token_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.one_time_token_type AS ENUM (
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token'
);


--
-- Name: role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.role AS ENUM (
    'owner',
    'admin',
    'member'
);


--
-- Name: sender; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.sender AS ENUM (
    'ai',
    'user',
    'system'
);


--
-- Name: action; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.action AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'TRUNCATE',
    'ERROR'
);


--
-- Name: equality_op; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.equality_op AS ENUM (
    'eq',
    'neq',
    'lt',
    'lte',
    'gt',
    'gte',
    'in'
);


--
-- Name: user_defined_filter; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.user_defined_filter AS (
	column_name text,
	op realtime.equality_op,
	value text
);


--
-- Name: wal_column; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.wal_column AS (
	name text,
	type_name text,
	type_oid oid,
	value jsonb,
	is_pkey boolean,
	is_selectable boolean
);


--
-- Name: wal_rls; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.wal_rls AS (
	wal jsonb,
	is_rls_enabled boolean,
	subscription_ids uuid[],
	errors text[]
);


--
-- Name: email(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.email() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select
  coalesce(
    nullif(current_setting('request.jwt.claim.email', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email')
  )::text
$$;


--
-- Name: FUNCTION email(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION auth.email() IS 'Deprecated. Use auth.jwt() -> ''email'' instead.';



--
-- Name: jwt(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.jwt() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
  select
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$$;


--
-- Name: role(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select
  coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )::text
$$;


--
-- Name: FUNCTION role(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION auth.role() IS 'Deprecated. Use auth.jwt() -> ''role'' instead.';



--
-- Name: uid(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$
  select
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;


--
-- Name: FUNCTION uid(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION auth.uid() IS 'Deprecated. Use auth.jwt() -> ''sub'' instead.';



--
-- Name: grant_pg_cron_access(); Type: FUNCTION; Schema: extensions; Owner: postgres
--

CREATE FUNCTION extensions.grant_pg_cron_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_cron'
  )
  THEN
    grant usage on schema cron to postgres with grant option;

    alter default privileges in schema cron grant all on tables to postgres with grant option;
    alter default privileges in schema cron grant all on functions to postgres with grant option;
    alter default privileges in schema cron grant all on sequences to postgres with grant option;

    alter default privileges for user supabase_admin in schema cron grant all
        on sequences to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on tables to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on functions to postgres with grant option;

    grant all privileges on all tables in schema cron to postgres with grant option;
    revoke all on table cron.job from postgres;
    grant select on table cron.job to postgres with grant option;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_cron_access(); Type: COMMENT; Schema: extensions; Owner: postgres
--

COMMENT ON FUNCTION extensions.grant_pg_cron_access() IS 'Grants access to pg_cron';



--
-- Name: grant_pg_graphql_access(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.grant_pg_graphql_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    func_is_graphql_resolve bool;
BEGIN
    func_is_graphql_resolve = (
        SELECT n.proname = 'resolve'
        FROM pg_event_trigger_ddl_commands() AS ev
        LEFT JOIN pg_catalog.pg_proc AS n
        ON ev.objid = n.oid
    );

    IF func_is_graphql_resolve
    THEN
        -- Update public wrapper to pass all arguments through to the pg_graphql resolve func
        DROP FUNCTION IF EXISTS graphql_public.graphql;
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language sql
        as $$
            select graphql.resolve(
                query := query,
                variables := coalesce(variables, '{}'),
                "operationName" := "operationName",
                extensions := extensions
            );
        $$;

        -- This hook executes when `graphql.resolve` is created. That is not necessarily the last
        -- function in the extension so we need to grant permissions on existing entities AND
        -- update default permissions to any others that are created after `graphql.resolve`
        grant usage on schema graphql to postgres, anon, authenticated, service_role;
        grant select on all tables in schema graphql to postgres, anon, authenticated, service_role;
        grant execute on all functions in schema graphql to postgres, anon, authenticated, service_role;
        grant all on all sequences in schema graphql to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on tables to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on functions to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on sequences to postgres, anon, authenticated, service_role;

        -- Allow postgres role to allow granting usage on graphql and graphql_public schemas to custom roles
        grant usage on schema graphql_public to postgres with grant option;
        grant usage on schema graphql to postgres with grant option;
    END IF;

END;
$_$;


--
-- Name: FUNCTION grant_pg_graphql_access(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION extensions.grant_pg_graphql_access() IS 'Grants access to pg_graphql';



--
-- Name: grant_pg_net_access(); Type: FUNCTION; Schema: extensions; Owner: postgres
--

CREATE FUNCTION extensions.grant_pg_net_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_net'
  )
  THEN
    GRANT USAGE ON SCHEMA net TO supabase_functions_admin, postgres, anon, authenticated, service_role;

    ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
    ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

    ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
    ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

    REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
    REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

    GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
    GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_net_access(); Type: COMMENT; Schema: extensions; Owner: postgres
--

COMMENT ON FUNCTION extensions.grant_pg_net_access() IS 'Grants access to pg_net';



--
-- Name: pgrst_ddl_watch(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.pgrst_ddl_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
  LOOP
    IF cmd.command_tag IN (
      'CREATE SCHEMA', 'ALTER SCHEMA'
    , 'CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE'
    , 'CREATE FOREIGN TABLE', 'ALTER FOREIGN TABLE'
    , 'CREATE VIEW', 'ALTER VIEW'
    , 'CREATE MATERIALIZED VIEW', 'ALTER MATERIALIZED VIEW'
    , 'CREATE FUNCTION', 'ALTER FUNCTION'
    , 'CREATE TRIGGER'
    , 'CREATE TYPE', 'ALTER TYPE'
    , 'CREATE RULE'
    , 'COMMENT'
    )
    -- don't notify in case of CREATE TEMP table or other objects created on pg_temp
    AND cmd.schema_name is distinct from 'pg_temp'
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: pgrst_drop_watch(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.pgrst_drop_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects()
  LOOP
    IF obj.object_type IN (
      'schema'
    , 'table'
    , 'foreign table'
    , 'view'
    , 'materialized view'
    , 'function'
    , 'trigger'
    , 'type'
    , 'rule'
    )
    AND obj.is_temporary IS false -- no pg_temp objects
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: set_graphql_placeholder(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.set_graphql_placeholder() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
    DECLARE
    graphql_is_dropped bool;
    BEGIN
    graphql_is_dropped = (
        SELECT ev.schema_name = 'graphql_public'
        FROM pg_event_trigger_dropped_objects() AS ev
        WHERE ev.schema_name = 'graphql_public'
    );

    IF graphql_is_dropped
    THEN
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language plpgsql
        as $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;
    END IF;

    END;
$_$;


--
-- Name: FUNCTION set_graphql_placeholder(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION extensions.set_graphql_placeholder() IS 'Reintroduces placeholder function for graphql_public.graphql';



--
-- Name: get_auth(text); Type: FUNCTION; Schema: pgbouncer; Owner: postgres
--

CREATE FUNCTION pgbouncer.get_auth(p_usename text) RETURNS TABLE(username text, password text)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RAISE WARNING 'PgBouncer auth request: %', p_usename;

    RETURN QUERY
    SELECT usename::TEXT, passwd::TEXT FROM pg_catalog.pg_shadow
    WHERE usename = p_usename;
END;
$$;


--
-- Name: calculate_completion_percentage(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_completion_percentage(p_proposal_id integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    total_sections INTEGER;
    completed_sections INTEGER;
BEGIN
    -- Get expected number of sections (simplified - assumes RIA)
    total_sections := 7; -- Excellence (3) + Impact (2) + Implementation (2)

    -- Count completed sections (>100 words and quality score >0.5)
    SELECT COUNT(*)
    INTO completed_sections
    FROM proposal_sections
    WHERE proposal_id = p_proposal_id
    AND is_current = TRUE
    AND word_count >= 100
    AND (quality_score >= 0.5 OR quality_score IS NULL);

    RETURN LEAST(100, (completed_sections * 100 / total_sections));
END;
$$;


--
-- Name: calculate_requested_funding(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_requested_funding() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.requested_funding = NEW.total_eligible_costs * NEW.funding_rate;
    RETURN NEW;
END;
$$;


--
-- Name: calculate_word_count(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_word_count() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.word_count = array_length(regexp_split_to_array(NEW.section_content, '\s+'), 1);
    RETURN NEW;
END;
$$;


--
-- Name: cleanup_expired_sessions(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_expired_sessions(expiry_hours integer DEFAULT 24) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE proposal_sessions
    SET status = 'expired'
    WHERE status = 'active'
    AND last_activity_at < NOW() - (expiry_hours || ' hours')::INTERVAL;

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$;


--
-- Name: get_chunks_for_call(character varying, text, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_chunks_for_call(p_call_identifier character varying, p_search_query text DEFAULT NULL::text, p_limit integer DEFAULT 10) RETURNS TABLE(chunk_id integer, chunk_text text, section_title character varying, document_type character varying, document_title character varying, relevance_score numeric)
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: get_current_sections(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_current_sections(p_proposal_id integer) RETURNS TABLE(section_id character varying, section_name character varying, section_content text, word_count integer, quality_score numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        ps.section_id,
        ps.section_name,
        ps.section_content,
        ps.word_count,
        ps.quality_score
    FROM proposal_sections ps
    WHERE ps.proposal_id = p_proposal_id
    AND ps.is_current = TRUE
    ORDER BY ps.section_order;
END;
$$;


--
-- Name: get_document_stats(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_document_stats() RETURNS TABLE(total_documents bigint, total_chunks bigint, documents_by_type jsonb, documents_by_year jsonb, avg_chunks_per_document numeric)
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


--
-- Name: hybrid_search(public.vector, text, integer, double precision); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.hybrid_search(query_embedding public.vector, query_text text, match_count integer DEFAULT 10, vector_weight double precision DEFAULT 0.5) RETURNS TABLE(chunk_id uuid, document_id uuid, content text, document_title text, combined_score double precision, section_title text, page_number integer)
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


--
-- Name: keyword_search(text, integer, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.keyword_search(query_text text, limit_count integer DEFAULT 10, filter_document_type text DEFAULT NULL::text, filter_year text DEFAULT NULL::text) RETURNS TABLE(chunk_id uuid, document_id uuid, content text, document_title text, document_type text, score double precision, section_title text, page_number integer)
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


--
-- Name: search_calls_semantic(public.vector, double precision, integer, text, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.search_calls_semantic(query_embedding public.vector, match_threshold double precision DEFAULT 0.5, match_count integer DEFAULT 20, filter_status text DEFAULT NULL::text, filter_open_only boolean DEFAULT true) RETURNS TABLE(id uuid, topic_code character varying, title text, scope text, expected_outcome text, deadline date, status character varying, cluster character varying, action_type character varying, budget_total numeric, similarity double precision)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        fc.id,
        fc.topic_code,
        fc.title,
        fc.scope,
        fc.expected_outcome,
        fc.deadline,
        fc.status,
        fc.cluster,
        fc.action_type,
        fc.budget_total,
        1 - (fc.embedding <=> query_embedding) as similarity
    FROM funding_calls fc
    WHERE
        fc.embedding IS NOT NULL
        AND (filter_status IS NULL OR fc.status = filter_status)
        AND (NOT filter_open_only OR (
            fc.status != 'closed'
            AND (fc.deadline IS NULL OR fc.deadline >= CURRENT_DATE)
        ))
        AND 1 - (fc.embedding <=> query_embedding) > match_threshold
    ORDER BY fc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


--
-- Name: FUNCTION search_calls_semantic(query_embedding public.vector, match_threshold double precision, match_count integer, filter_status text, filter_open_only boolean); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.search_calls_semantic(query_embedding public.vector, match_threshold double precision, match_count integer, filter_status text, filter_open_only boolean) IS 'Search funding calls using semantic similarity with query embedding';



--
-- Name: search_documents(public.vector, double precision, integer, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.search_documents(query_embedding public.vector, match_threshold double precision DEFAULT 0.7, match_count integer DEFAULT 10, filter_document_type text DEFAULT NULL::text, filter_year text DEFAULT NULL::text) RETURNS TABLE(chunk_id uuid, document_id uuid, content text, document_title text, document_type text, similarity double precision, metadata jsonb, section_title text, page_number integer)
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


--
-- Name: search_funding_calls(text, text, text, text, text, integer, boolean, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.search_funding_calls(search_query text, filter_programme text DEFAULT NULL::text, filter_status text DEFAULT NULL::text, filter_action_type text DEFAULT NULL::text, filter_cluster text DEFAULT NULL::text, filter_year integer DEFAULT NULL::integer, include_closed boolean DEFAULT false, max_results integer DEFAULT 20) RETURNS TABLE(id uuid, programme character varying, topic_code character varying, title text, action_type character varying, status character varying, deadline date, budget_total numeric, expected_outcome text, scope text, cluster character varying, portal_url text, relevance_score real)
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


--
-- Name: update_funding_calls_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_funding_calls_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_project_embeddings_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_project_embeddings_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_proposal_completion(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_proposal_completion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE proposals
    SET completion_percentage = calculate_completion_percentage(NEW.proposal_id)
    WHERE id = NEW.proposal_id;

    RETURN NEW;
END;
$$;


--
-- Name: update_proposal_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_proposal_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_session_activity(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_session_activity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.last_activity_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: apply_rls(jsonb, integer); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer DEFAULT (1024 * 1024)) RETURNS SETOF realtime.wal_rls
    LANGUAGE plpgsql
    AS $$
declare
-- Regclass of the table e.g. public.notes
entity_ regclass = (quote_ident(wal ->> 'schema') || '.' || quote_ident(wal ->> 'table'))::regclass;

-- I, U, D, T: insert, update ...
action realtime.action = (
    case wal ->> 'action'
        when 'I' then 'INSERT'
        when 'U' then 'UPDATE'
        when 'D' then 'DELETE'
        else 'ERROR'
    end
);

-- Is row level security enabled for the table
is_rls_enabled bool = relrowsecurity from pg_class where oid = entity_;

subscriptions realtime.subscription[] = array_agg(subs)
    from
        realtime.subscription subs
    where
        subs.entity = entity_;

-- Subscription vars
roles regrole[] = array_agg(distinct us.claims_role::text)
    from
        unnest(subscriptions) us;

working_role regrole;
claimed_role regrole;
claims jsonb;

subscription_id uuid;
subscription_has_access bool;
visible_to_subscription_ids uuid[] = '{}';

-- structured info for wal's columns
columns realtime.wal_column[];
-- previous identity values for update/delete
old_columns realtime.wal_column[];

error_record_exceeds_max_size boolean = octet_length(wal::text) > max_record_bytes;

-- Primary jsonb output for record
output jsonb;

begin
perform set_config('role', null, true);

columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'columns') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

old_columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'identity') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

for working_role in select * from unnest(roles) loop

    -- Update `is_selectable` for columns and old_columns
    columns =
        array_agg(
            (
                c.name,
                c.type_name,
                c.type_oid,
                c.value,
                c.is_pkey,
                pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
            )::realtime.wal_column
        )
        from
            unnest(columns) c;

    old_columns =
            array_agg(
                (
                    c.name,
                    c.type_name,
                    c.type_oid,
                    c.value,
                    c.is_pkey,
                    pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
                )::realtime.wal_column
            )
            from
                unnest(old_columns) c;

    if action <> 'DELETE' and count(1) = 0 from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            -- subscriptions is already filtered by entity
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 400: Bad Request, no primary key']
        )::realtime.wal_rls;

    -- The claims role does not have SELECT permission to the primary key of entity
    elsif action <> 'DELETE' and sum(c.is_selectable::int) <> count(1) from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 401: Unauthorized']
        )::realtime.wal_rls;

    else
        output = jsonb_build_object(
            'schema', wal ->> 'schema',
            'table', wal ->> 'table',
            'type', action,
            'commit_timestamp', to_char(
                ((wal ->> 'timestamp')::timestamptz at time zone 'utc'),
                'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
            ),
            'columns', (
                select
                    jsonb_agg(
                        jsonb_build_object(
                            'name', pa.attname,
                            'type', pt.typname
                        )
                        order by pa.attnum asc
                    )
                from
                    pg_attribute pa
                    join pg_type pt
                        on pa.atttypid = pt.oid
                where
                    attrelid = entity_
                    and attnum > 0
                    and pg_catalog.has_column_privilege(working_role, entity_, pa.attname, 'SELECT')
            )
        )
        -- Add "record" key for insert and update
        || case
            when action in ('INSERT', 'UPDATE') then
                jsonb_build_object(
                    'record',
                    (
                        select
                            jsonb_object_agg(
                                -- if unchanged toast, get column name and value from old record
                                coalesce((c).name, (oc).name),
                                case
                                    when (c).name is null then (oc).value
                                    else (c).value
                                end
                            )
                        from
                            unnest(columns) c
                            full outer join unnest(old_columns) oc
                                on (c).name = (oc).name
                        where
                            coalesce((c).is_selectable, (oc).is_selectable)
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                    )
                )
            else '{}'::jsonb
        end
        -- Add "old_record" key for update and delete
        || case
            when action = 'UPDATE' then
                jsonb_build_object(
                        'old_record',
                        (
                            select jsonb_object_agg((c).name, (c).value)
                            from unnest(old_columns) c
                            where
                                (c).is_selectable
                                and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                        )
                    )
            when action = 'DELETE' then
                jsonb_build_object(
                    'old_record',
                    (
                        select jsonb_object_agg((c).name, (c).value)
                        from unnest(old_columns) c
                        where
                            (c).is_selectable
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                            and ( not is_rls_enabled or (c).is_pkey ) -- if RLS enabled, we can't secure deletes so filter to pkey
                    )
                )
            else '{}'::jsonb
        end;

        -- Create the prepared statement
        if is_rls_enabled and action <> 'DELETE' then
            if (select 1 from pg_prepared_statements where name = 'walrus_rls_stmt' limit 1) > 0 then
                deallocate walrus_rls_stmt;
            end if;
            execute realtime.build_prepared_statement_sql('walrus_rls_stmt', entity_, columns);
        end if;

        visible_to_subscription_ids = '{}';

        for subscription_id, claims in (
                select
                    subs.subscription_id,
                    subs.claims
                from
                    unnest(subscriptions) subs
                where
                    subs.entity = entity_
                    and subs.claims_role = working_role
                    and (
                        realtime.is_visible_through_filters(columns, subs.filters)
                        or (
                          action = 'DELETE'
                          and realtime.is_visible_through_filters(old_columns, subs.filters)
                        )
                    )
        ) loop

            if not is_rls_enabled or action = 'DELETE' then
                visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
            else
                -- Check if RLS allows the role to see the record
                perform
                    -- Trim leading and trailing quotes from working_role because set_config
                    -- doesn't recognize the role as valid if they are included
                    set_config('role', trim(both '"' from working_role::text), true),
                    set_config('request.jwt.claims', claims::text, true);

                execute 'execute walrus_rls_stmt' into subscription_has_access;

                if subscription_has_access then
                    visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
                end if;
            end if;
        end loop;

        perform set_config('role', null, true);

        return next (
            output,
            is_rls_enabled,
            visible_to_subscription_ids,
            case
                when error_record_exceeds_max_size then array['Error 413: Payload Too Large']
                else '{}'
            end
        )::realtime.wal_rls;

    end if;
end loop;

perform set_config('role', null, true);
end;
$$;


--
-- Name: broadcast_changes(text, text, text, text, text, record, record, text); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text DEFAULT 'ROW'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- Declare a variable to hold the JSONB representation of the row
    row_data jsonb := '{}'::jsonb;
BEGIN
    IF level = 'STATEMENT' THEN
        RAISE EXCEPTION 'function can only be triggered for each row, not for each statement';
    END IF;
    -- Check the operation type and handle accordingly
    IF operation = 'INSERT' OR operation = 'UPDATE' OR operation = 'DELETE' THEN
        row_data := jsonb_build_object('old_record', OLD, 'record', NEW, 'operation', operation, 'table', table_name, 'schema', table_schema);
        PERFORM realtime.send (row_data, event_name, topic_name);
    ELSE
        RAISE EXCEPTION 'Unexpected operation type: %', operation;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to process the row: %', SQLERRM;
END;

$$;


--
-- Name: build_prepared_statement_sql(text, regclass, realtime.wal_column[]); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) RETURNS text
    LANGUAGE sql
    AS $$
      /*
      Builds a sql string that, if executed, creates a prepared statement to
      tests retrive a row from *entity* by its primary key columns.
      Example
          select realtime.build_prepared_statement_sql('public.notes', '{"id"}'::text[], '{"bigint"}'::text[])
      */
          select
      'prepare ' || prepared_statement_name || ' as
          select
              exists(
                  select
                      1
                  from
                      ' || entity || '
                  where
                      ' || string_agg(quote_ident(pkc.name) || '=' || quote_nullable(pkc.value #>> '{}') , ' and ') || '
              )'
          from
              unnest(columns) pkc
          where
              pkc.is_pkey
          group by
              entity
      $$;


--
-- Name: cast(text, regtype); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime."cast"(val text, type_ regtype) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    AS $$
    declare
      res jsonb;
    begin
      execute format('select to_jsonb(%L::'|| type_::text || ')', val)  into res;
      return res;
    end
    $$;


--
-- Name: check_equality_op(realtime.equality_op, regtype, text, text); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE
    AS $$
      /*
      Casts *val_1* and *val_2* as type *type_* and check the *op* condition for truthiness
      */
      declare
          op_symbol text = (
              case
                  when op = 'eq' then '='
                  when op = 'neq' then '!='
                  when op = 'lt' then '<'
                  when op = 'lte' then '<='
                  when op = 'gt' then '>'
                  when op = 'gte' then '>='
                  when op = 'in' then '= any'
                  else 'UNKNOWN OP'
              end
          );
          res boolean;
      begin
          execute format(
              'select %L::'|| type_::text || ' ' || op_symbol
              || ' ( %L::'
              || (
                  case
                      when op = 'in' then type_::text || '[]'
                      else type_::text end
              )
              || ')', val_1, val_2) into res;
          return res;
      end;
      $$;


--
-- Name: is_visible_through_filters(realtime.wal_column[], realtime.user_defined_filter[]); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
    /*
    Should the record be visible (true) or filtered out (false) after *filters* are applied
    */
        select
            -- Default to allowed when no filters present
            $2 is null -- no filters. this should not happen because subscriptions has a default
            or array_length($2, 1) is null -- array length of an empty array is null
            or bool_and(
                coalesce(
                    realtime.check_equality_op(
                        op:=f.op,
                        type_:=coalesce(
                            col.type_oid::regtype, -- null when wal2json version <= 2.4
                            col.type_name::regtype
                        ),
                        -- cast jsonb to text
                        val_1:=col.value #>> '{}',
                        val_2:=f.value
                    ),
                    false -- if null, filter does not match
                )
            )
        from
            unnest(filters) f
            join unnest(columns) col
                on f.column_name = col.name;
    $_$;


--
-- Name: list_changes(name, name, integer, integer); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) RETURNS SETOF realtime.wal_rls
    LANGUAGE sql
    SET log_min_messages TO 'fatal'
    AS $$
      with pub as (
        select
          concat_ws(
            ',',
            case when bool_or(pubinsert) then 'insert' else null end,
            case when bool_or(pubupdate) then 'update' else null end,
            case when bool_or(pubdelete) then 'delete' else null end
          ) as w2j_actions,
          coalesce(
            string_agg(
              realtime.quote_wal2json(format('%I.%I', schemaname, tablename)::regclass),
              ','
            ) filter (where ppt.tablename is not null and ppt.tablename not like '% %'),
            ''
          ) w2j_add_tables
        from
          pg_publication pp
          left join pg_publication_tables ppt
            on pp.pubname = ppt.pubname
        where
          pp.pubname = publication
        group by
          pp.pubname
        limit 1
      ),
      w2j as (
        select
          x.*, pub.w2j_add_tables
        from
          pub,
          pg_logical_slot_get_changes(
            slot_name, null, max_changes,
            'include-pk', 'true',
            'include-transaction', 'false',
            'include-timestamp', 'true',
            'include-type-oids', 'true',
            'format-version', '2',
            'actions', pub.w2j_actions,
            'add-tables', pub.w2j_add_tables
          ) x
      )
      select
        xyz.wal,
        xyz.is_rls_enabled,
        xyz.subscription_ids,
        xyz.errors
      from
        w2j,
        realtime.apply_rls(
          wal := w2j.data::jsonb,
          max_record_bytes := max_record_bytes
        ) xyz(wal, is_rls_enabled, subscription_ids, errors)
      where
        w2j.w2j_add_tables <> ''
        and xyz.subscription_ids[1] is not null
    $$;


--
-- Name: quote_wal2json(regclass); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.quote_wal2json(entity regclass) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
      select
        (
          select string_agg('' || ch,'')
          from unnest(string_to_array(nsp.nspname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
        )
        || '.'
        || (
          select string_agg('' || ch,'')
          from unnest(string_to_array(pc.relname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
          )
      from
        pg_class pc
        join pg_namespace nsp
          on pc.relnamespace = nsp.oid
      where
        pc.oid = entity
    $$;


--
-- Name: send(jsonb, text, text, boolean); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean DEFAULT true) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  BEGIN
    -- Set the topic configuration
    EXECUTE format('SET LOCAL realtime.topic TO %L', topic);

    -- Attempt to insert the message
    INSERT INTO realtime.messages (payload, event, topic, private, extension)
    VALUES (payload, event, topic, private, 'broadcast');
  EXCEPTION
    WHEN OTHERS THEN
      -- Capture and notify the error
      PERFORM pg_notify(
          'realtime:system',
          jsonb_build_object(
              'error', SQLERRM,
              'function', 'realtime.send',
              'event', event,
              'topic', topic,
              'private', private
          )::text
      );
  END;
END;
$$;


--
-- Name: subscription_check_filters(); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.subscription_check_filters() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    /*
    Validates that the user defined filters for a subscription:
    - refer to valid columns that the claimed role may access
    - values are coercable to the correct column type
    */
    declare
        col_names text[] = coalesce(
                array_agg(c.column_name order by c.ordinal_position),
                '{}'::text[]
            )
            from
                information_schema.columns c
            where
                format('%I.%I', c.table_schema, c.table_name)::regclass = new.entity
                and pg_catalog.has_column_privilege(
                    (new.claims ->> 'role'),
                    format('%I.%I', c.table_schema, c.table_name)::regclass,
                    c.column_name,
                    'SELECT'
                );
        filter realtime.user_defined_filter;
        col_type regtype;

        in_val jsonb;
    begin
        for filter in select * from unnest(new.filters) loop
            -- Filtered column is valid
            if not filter.column_name = any(col_names) then
                raise exception 'invalid column for filter %', filter.column_name;
            end if;

            -- Type is sanitized and safe for string interpolation
            col_type = (
                select atttypid::regtype
                from pg_catalog.pg_attribute
                where attrelid = new.entity
                      and attname = filter.column_name
            );
            if col_type is null then
                raise exception 'failed to lookup type for column %', filter.column_name;
            end if;

            -- Set maximum number of entries for in filter
            if filter.op = 'in'::realtime.equality_op then
                in_val = realtime.cast(filter.value, (col_type::text || '[]')::regtype);
                if coalesce(jsonb_array_length(in_val), 0) > 100 then
                    raise exception 'too many values for `in` filter. Maximum 100';
                end if;
            else
                -- raises an exception if value is not coercable to type
                perform realtime.cast(filter.value, col_type);
            end if;

        end loop;

        -- Apply consistent order to filters so the unique constraint on
        -- (subscription_id, entity, filters) can't be tricked by a different filter order
        new.filters = coalesce(
            array_agg(f order by f.column_name, f.op, f.value),
            '{}'
        ) from unnest(new.filters) f;

        return new;
    end;
    $$;


--
-- Name: to_regrole(text); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.to_regrole(role_name text) RETURNS regrole
    LANGUAGE sql IMMUTABLE
    AS $$ select role_name::regrole $$;


--
-- Name: topic(); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION realtime.topic() RETURNS text
    LANGUAGE sql STABLE
    AS $$
select nullif(current_setting('realtime.topic', true), '')::text;
$$;


--
-- Name: add_prefixes(text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.add_prefixes(_bucket_id text, _name text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    prefixes text[];
BEGIN
    prefixes := "storage"."get_prefixes"("_name");

    IF array_length(prefixes, 1) > 0 THEN
        INSERT INTO storage.prefixes (name, bucket_id)
        SELECT UNNEST(prefixes) as name, "_bucket_id" ON CONFLICT DO NOTHING;
    END IF;
END;
$$;


--
-- Name: can_insert_object(text, text, uuid, jsonb); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  INSERT INTO "storage"."objects" ("bucket_id", "name", "owner", "metadata") VALUES (bucketid, name, owner, metadata);
  -- hack to rollback the successful insert
  RAISE sqlstate 'PT200' using
  message = 'ROLLBACK',
  detail = 'rollback successful insert';
END
$$;


--
-- Name: delete_prefix(text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.delete_prefix(_bucket_id text, _name text) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    -- Check if we can delete the prefix
    IF EXISTS(
        SELECT FROM "storage"."prefixes"
        WHERE "prefixes"."bucket_id" = "_bucket_id"
          AND level = "storage"."get_level"("_name") + 1
          AND "prefixes"."name" COLLATE "C" LIKE "_name" || '/%'
        LIMIT 1
    )
    OR EXISTS(
        SELECT FROM "storage"."objects"
        WHERE "objects"."bucket_id" = "_bucket_id"
          AND "storage"."get_level"("objects"."name") = "storage"."get_level"("_name") + 1
          AND "objects"."name" COLLATE "C" LIKE "_name" || '/%'
        LIMIT 1
    ) THEN
    -- There are sub-objects, skip deletion
    RETURN false;
    ELSE
        DELETE FROM "storage"."prefixes"
        WHERE "prefixes"."bucket_id" = "_bucket_id"
          AND level = "storage"."get_level"("_name")
          AND "prefixes"."name" = "_name";
        RETURN true;
    END IF;
END;
$$;


--
-- Name: delete_prefix_hierarchy_trigger(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.delete_prefix_hierarchy_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    prefix text;
BEGIN
    prefix := "storage"."get_prefix"(OLD."name");

    IF coalesce(prefix, '') != '' THEN
        PERFORM "storage"."delete_prefix"(OLD."bucket_id", prefix);
    END IF;

    RETURN OLD;
END;
$$;


--
-- Name: extension(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.extension(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
_filename text;
BEGIN
	select string_to_array(name, '/') into _parts;
	select _parts[array_length(_parts,1)] into _filename;
	-- @todo return the last part instead of 2
	return reverse(split_part(reverse(_filename), '.', 1));
END
$$;


--
-- Name: filename(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.filename(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
	select string_to_array(name, '/') into _parts;
	return _parts[array_length(_parts,1)];
END
$$;


--
-- Name: foldername(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.foldername(name text) RETURNS text[]
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
	select string_to_array(name, '/') into _parts;
	return _parts[1:array_length(_parts,1)-1];
END
$$;


--
-- Name: get_level(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.get_level(name text) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
SELECT array_length(string_to_array("name", '/'), 1);
$$;


--
-- Name: get_prefix(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.get_prefix(name text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
SELECT
    CASE WHEN strpos("name", '/') > 0 THEN
             regexp_replace("name", '[\/]{1}[^\/]+\/?$', '')
         ELSE
             ''
        END;
$_$;


--
-- Name: get_prefixes(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.get_prefixes(name text) RETURNS text[]
    LANGUAGE plpgsql IMMUTABLE STRICT
    AS $$
DECLARE
    parts text[];
    prefixes text[];
    prefix text;
BEGIN
    -- Split the name into parts by '/'
    parts := string_to_array("name", '/');
    prefixes := '{}';

    -- Construct the prefixes, stopping one level below the last part
    FOR i IN 1..array_length(parts, 1) - 1 LOOP
            prefix := array_to_string(parts[1:i], '/');
            prefixes := array_append(prefixes, prefix);
    END LOOP;

    RETURN prefixes;
END;
$$;


--
-- Name: get_size_by_bucket(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.get_size_by_bucket() RETURNS TABLE(size bigint, bucket_id text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    return query
        select sum((metadata->>'size')::int) as size, obj.bucket_id
        from "storage".objects as obj
        group by obj.bucket_id;
END
$$;


--
-- Name: list_multipart_uploads_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, next_key_token text DEFAULT ''::text, next_upload_token text DEFAULT ''::text) RETURNS TABLE(key text, id text, created_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(key COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                        substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1)))
                    ELSE
                        key
                END AS key, id, created_at
            FROM
                storage.s3_multipart_uploads
            WHERE
                bucket_id = $5 AND
                key ILIKE $1 || ''%'' AND
                CASE
                    WHEN $4 != '''' AND $6 = '''' THEN
                        CASE
                            WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                                substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                key COLLATE "C" > $4
                            END
                    ELSE
                        true
                END AND
                CASE
                    WHEN $6 != '''' THEN
                        id COLLATE "C" > $6
                    ELSE
                        true
                    END
            ORDER BY
                key COLLATE "C" ASC, created_at ASC) as e order by key COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_key_token, bucket_id, next_upload_token;
END;
$_$;


--
-- Name: list_objects_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.list_objects_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, start_after text DEFAULT ''::text, next_token text DEFAULT ''::text) RETURNS TABLE(name text, id uuid, metadata jsonb, updated_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(name COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(name from length($1) + 1)) > 0 THEN
                        substring(name from 1 for length($1) + position($2 IN substring(name from length($1) + 1)))
                    ELSE
                        name
                END AS name, id, metadata, updated_at
            FROM
                storage.objects
            WHERE
                bucket_id = $5 AND
                name ILIKE $1 || ''%'' AND
                CASE
                    WHEN $6 != '''' THEN
                    name COLLATE "C" > $6
                ELSE true END
                AND CASE
                    WHEN $4 != '''' THEN
                        CASE
                            WHEN position($2 IN substring(name from length($1) + 1)) > 0 THEN
                                substring(name from 1 for length($1) + position($2 IN substring(name from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                name COLLATE "C" > $4
                            END
                    ELSE
                        true
                END
            ORDER BY
                name COLLATE "C" ASC) as e order by name COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_token, bucket_id, start_after;
END;
$_$;


--
-- Name: objects_insert_prefix_trigger(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.objects_insert_prefix_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM "storage"."add_prefixes"(NEW."bucket_id", NEW."name");
    NEW.level := "storage"."get_level"(NEW."name");

    RETURN NEW;
END;
$$;


--
-- Name: operation(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.operation() RETURNS text
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN current_setting('storage.operation', true);
END;
$$;


--
-- Name: prefixes_insert_trigger(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.prefixes_insert_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM "storage"."add_prefixes"(NEW."bucket_id", NEW."name");
    RETURN NEW;
END;
$$;


--
-- Name: search(text, text, integer, integer, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.search(prefix text, bucketname text, limits integer DEFAULT 100, levels integer DEFAULT 1, offsets integer DEFAULT 0, search text DEFAULT ''::text, sortcolumn text DEFAULT 'name'::text, sortorder text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $$
declare
    can_bypass_rls BOOLEAN;
begin
    SELECT rolbypassrls
    INTO can_bypass_rls
    FROM pg_roles
    WHERE rolname = coalesce(nullif(current_setting('role', true), 'none'), current_user);

    IF can_bypass_rls THEN
        RETURN QUERY SELECT * FROM storage.search_v1_optimised(prefix, bucketname, limits, levels, offsets, search, sortcolumn, sortorder);
    ELSE
        RETURN QUERY SELECT * FROM storage.search_legacy_v1(prefix, bucketname, limits, levels, offsets, search, sortcolumn, sortorder);
    END IF;
end;
$$;


--
-- Name: search_legacy_v1(text, text, integer, integer, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.search_legacy_v1(prefix text, bucketname text, limits integer DEFAULT 100, levels integer DEFAULT 1, offsets integer DEFAULT 0, search text DEFAULT ''::text, sortcolumn text DEFAULT 'name'::text, sortorder text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
declare
    v_order_by text;
    v_sort_order text;
begin
    case
        when sortcolumn = 'name' then
            v_order_by = 'name';
        when sortcolumn = 'updated_at' then
            v_order_by = 'updated_at';
        when sortcolumn = 'created_at' then
            v_order_by = 'created_at';
        when sortcolumn = 'last_accessed_at' then
            v_order_by = 'last_accessed_at';
        else
            v_order_by = 'name';
        end case;

    case
        when sortorder = 'asc' then
            v_sort_order = 'asc';
        when sortorder = 'desc' then
            v_sort_order = 'desc';
        else
            v_sort_order = 'asc';
        end case;

    v_order_by = v_order_by || ' ' || v_sort_order;

    return query execute
        'with folders as (
           select path_tokens[$1] as folder
           from storage.objects
             where objects.name ilike $2 || $3 || ''%''
               and bucket_id = $4
               and array_length(objects.path_tokens, 1) <> $1
           group by folder
           order by folder ' || v_sort_order || '
     )
     (select folder as "name",
            null as id,
            null as updated_at,
            null as created_at,
            null as last_accessed_at,
            null as metadata from folders)
     union all
     (select path_tokens[$1] as "name",
            id,
            updated_at,
            created_at,
            last_accessed_at,
            metadata
     from storage.objects
     where objects.name ilike $2 || $3 || ''%''
       and bucket_id = $4
       and array_length(objects.path_tokens, 1) = $1
     order by ' || v_order_by || ')
     limit $5
     offset $6' using levels, prefix, search, bucketname, limits, offsets;
end;
$_$;


--
-- Name: search_v1_optimised(text, text, integer, integer, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.search_v1_optimised(prefix text, bucketname text, limits integer DEFAULT 100, levels integer DEFAULT 1, offsets integer DEFAULT 0, search text DEFAULT ''::text, sortcolumn text DEFAULT 'name'::text, sortorder text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
declare
    v_order_by text;
    v_sort_order text;
begin
    case
        when sortcolumn = 'name' then
            v_order_by = 'name';
        when sortcolumn = 'updated_at' then
            v_order_by = 'updated_at';
        when sortcolumn = 'created_at' then
            v_order_by = 'created_at';
        when sortcolumn = 'last_accessed_at' then
            v_order_by = 'last_accessed_at';
        else
            v_order_by = 'name';
        end case;

    case
        when sortorder = 'asc' then
            v_sort_order = 'asc';
        when sortorder = 'desc' then
            v_sort_order = 'desc';
        else
            v_sort_order = 'asc';
        end case;

    v_order_by = v_order_by || ' ' || v_sort_order;

    return query execute
        'with folders as (
           select (string_to_array(name, ''/''))[level] as name
           from storage.prefixes
             where lower(prefixes.name) like lower($2 || $3) || ''%''
               and bucket_id = $4
               and level = $1
           order by name ' || v_sort_order || '
     )
     (select name,
            null as id,
            null as updated_at,
            null as created_at,
            null as last_accessed_at,
            null as metadata from folders)
     union all
     (select path_tokens[level] as "name",
            id,
            updated_at,
            created_at,
            last_accessed_at,
            metadata
     from storage.objects
     where lower(objects.name) like lower($2 || $3) || ''%''
       and bucket_id = $4
       and level = $1
     order by ' || v_order_by || ')
     limit $5
     offset $6' using levels, prefix, search, bucketname, limits, offsets;
end;
$_$;


--
-- Name: search_v2(text, text, integer, integer, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.search_v2(prefix text, bucket_name text, limits integer DEFAULT 100, levels integer DEFAULT 1, start_after text DEFAULT ''::text) RETURNS TABLE(key text, name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
BEGIN
    RETURN query EXECUTE
        $sql$
        SELECT * FROM (
            (
                SELECT
                    split_part(name, '/', $4) AS key,
                    name || '/' AS name,
                    NULL::uuid AS id,
                    NULL::timestamptz AS updated_at,
                    NULL::timestamptz AS created_at,
                    NULL::jsonb AS metadata
                FROM storage.prefixes
                WHERE name COLLATE "C" LIKE $1 || '%'
                AND bucket_id = $2
                AND level = $4
                AND name COLLATE "C" > $5
                ORDER BY prefixes.name COLLATE "C" LIMIT $3
            )
            UNION ALL
            (SELECT split_part(name, '/', $4) AS key,
                name,
                id,
                updated_at,
                created_at,
                metadata
            FROM storage.objects
            WHERE name COLLATE "C" LIKE $1 || '%'
                AND bucket_id = $2
                AND level = $4
                AND name COLLATE "C" > $5
            ORDER BY name COLLATE "C" LIMIT $3)
        ) obj
        ORDER BY name COLLATE "C" LIMIT $3;
        $sql$
        USING prefix, bucket_name, limits, levels, start_after;
END;
$_$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


--
-- Name: http_request(); Type: FUNCTION; Schema: supabase_functions; Owner: supabase_functions_admin
--

CREATE FUNCTION supabase_functions.http_request() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'supabase_functions'
    AS $$
  DECLARE
    request_id bigint;
    payload jsonb;
    url text := TG_ARGV[0]::text;
    method text := TG_ARGV[1]::text;
    headers jsonb DEFAULT '{}'::jsonb;
    params jsonb DEFAULT '{}'::jsonb;
    timeout_ms integer DEFAULT 1000;
  BEGIN
    IF url IS NULL OR url = 'null' THEN
      RAISE EXCEPTION 'url argument is missing';
    END IF;

    IF method IS NULL OR method = 'null' THEN
      RAISE EXCEPTION 'method argument is missing';
    END IF;

    IF TG_ARGV[2] IS NULL OR TG_ARGV[2] = 'null' THEN
      headers = '{"Content-Type": "application/json"}'::jsonb;
    ELSE
      headers = TG_ARGV[2]::jsonb;
    END IF;

    IF TG_ARGV[3] IS NULL OR TG_ARGV[3] = 'null' THEN
      params = '{}'::jsonb;
    ELSE
      params = TG_ARGV[3]::jsonb;
    END IF;

    IF TG_ARGV[4] IS NULL OR TG_ARGV[4] = 'null' THEN
      timeout_ms = 1000;
    ELSE
      timeout_ms = TG_ARGV[4]::integer;
    END IF;

    CASE
      WHEN method = 'GET' THEN
        SELECT http_get INTO request_id FROM net.http_get(
          url,
          params,
          headers,
          timeout_ms
        );
      WHEN method = 'POST' THEN
        payload = jsonb_build_object(
          'old_record', OLD,
          'record', NEW,
          'type', TG_OP,
          'table', TG_TABLE_NAME,
          'schema', TG_TABLE_SCHEMA
        );

        SELECT http_post INTO request_id FROM net.http_post(
          url,
          payload,
          params,
          headers,
          timeout_ms
        );
      ELSE
        RAISE EXCEPTION 'method argument % is invalid', method;
    END CASE;

    INSERT INTO supabase_functions.hooks
      (hook_table_id, hook_name, request_id)
    VALUES
      (TG_RELID, TG_NAME, request_id);

    RETURN NEW;
  END
$$;


--
-- Name: secrets_encrypt_secret_secret(); Type: FUNCTION; Schema: vault; Owner: supabase_admin
--

CREATE FUNCTION vault.secrets_encrypt_secret_secret() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
		BEGIN
		        new.secret = CASE WHEN new.secret IS NULL THEN NULL ELSE
			CASE WHEN new.key_id IS NULL THEN NULL ELSE pg_catalog.encode(
			  pgsodium.crypto_aead_det_encrypt(
				pg_catalog.convert_to(new.secret, 'utf8'),
				pg_catalog.convert_to((new.id::text || new.description::text || new.created_at::text || new.updated_at::text)::text, 'utf8'),
				new.key_id::uuid,
				new.nonce
			  ),
				'base64') END END;
		RETURN new;
		END;
		$$;


SET default_tablespace = '';


SET default_table_access_method = heap;


--
-- Name: extensions; Type: TABLE; Schema: _realtime; Owner: supabase_admin
--

CREATE TABLE _realtime.extensions (
    id uuid NOT NULL,
    type text,
    settings jsonb,
    tenant_external_id text,
    inserted_at timestamp(0) without time zone NOT NULL,
    updated_at timestamp(0) without time zone NOT NULL
);


--
-- Name: schema_migrations; Type: TABLE; Schema: _realtime; Owner: supabase_admin
--

CREATE TABLE _realtime.schema_migrations (
    version bigint NOT NULL,
    inserted_at timestamp(0) without time zone
);


--
-- Name: tenants; Type: TABLE; Schema: _realtime; Owner: supabase_admin
--

CREATE TABLE _realtime.tenants (
    id uuid NOT NULL,
    name text,
    external_id text,
    jwt_secret text,
    max_concurrent_users integer DEFAULT 200 NOT NULL,
    inserted_at timestamp(0) without time zone NOT NULL,
    updated_at timestamp(0) without time zone NOT NULL,
    max_events_per_second integer DEFAULT 100 NOT NULL,
    postgres_cdc_default text DEFAULT 'postgres_cdc_rls'::text,
    max_bytes_per_second integer DEFAULT 100000 NOT NULL,
    max_channels_per_client integer DEFAULT 100 NOT NULL,
    max_joins_per_second integer DEFAULT 500 NOT NULL,
    suspend boolean DEFAULT false,
    jwt_jwks jsonb,
    notify_private_alpha boolean DEFAULT false,
    private_only boolean DEFAULT false NOT NULL
);


--
-- Name: audit_log_entries; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.audit_log_entries (
    instance_id uuid,
    id uuid NOT NULL,
    payload json,
    created_at timestamp with time zone,
    ip_address character varying(64) DEFAULT ''::character varying NOT NULL
);


--
-- Name: TABLE audit_log_entries; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.audit_log_entries IS 'Auth: Audit trail for user actions.';



--
-- Name: flow_state; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.flow_state (
    id uuid NOT NULL,
    user_id uuid,
    auth_code text NOT NULL,
    code_challenge_method auth.code_challenge_method NOT NULL,
    code_challenge text NOT NULL,
    provider_type text NOT NULL,
    provider_access_token text,
    provider_refresh_token text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    authentication_method text NOT NULL,
    auth_code_issued_at timestamp with time zone
);


--
-- Name: TABLE flow_state; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.flow_state IS 'stores metadata for pkce logins';



--
-- Name: identities; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.identities (
    provider_id text NOT NULL,
    user_id uuid NOT NULL,
    identity_data jsonb NOT NULL,
    provider text NOT NULL,
    last_sign_in_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    email text GENERATED ALWAYS AS (lower((identity_data ->> 'email'::text))) STORED,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: TABLE identities; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.identities IS 'Auth: Stores identities associated to a user.';



--
-- Name: COLUMN identities.email; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.identities.email IS 'Auth: Email is a generated column that references the optional email property in the identity_data';



--
-- Name: instances; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.instances (
    id uuid NOT NULL,
    uuid uuid,
    raw_base_config text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: TABLE instances; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.instances IS 'Auth: Manages users across multiple sites.';



--
-- Name: mfa_amr_claims; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.mfa_amr_claims (
    session_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    authentication_method text NOT NULL,
    id uuid NOT NULL
);


--
-- Name: TABLE mfa_amr_claims; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.mfa_amr_claims IS 'auth: stores authenticator method reference claims for multi factor authentication';



--
-- Name: mfa_challenges; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.mfa_challenges (
    id uuid NOT NULL,
    factor_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    ip_address inet NOT NULL,
    otp_code text,
    web_authn_session_data jsonb
);


--
-- Name: TABLE mfa_challenges; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.mfa_challenges IS 'auth: stores metadata about challenge requests made';



--
-- Name: mfa_factors; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.mfa_factors (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    friendly_name text,
    factor_type auth.factor_type NOT NULL,
    status auth.factor_status NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    secret text,
    phone text,
    last_challenged_at timestamp with time zone,
    web_authn_credential jsonb,
    web_authn_aaguid uuid
);


--
-- Name: TABLE mfa_factors; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.mfa_factors IS 'auth: stores metadata about factors';



--
-- Name: one_time_tokens; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.one_time_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_type auth.one_time_token_type NOT NULL,
    token_hash text NOT NULL,
    relates_to text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT one_time_tokens_token_hash_check CHECK ((char_length(token_hash) > 0))
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.refresh_tokens (
    instance_id uuid,
    id bigint NOT NULL,
    token character varying(255),
    user_id character varying(255),
    revoked boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    parent character varying(255),
    session_id uuid
);


--
-- Name: TABLE refresh_tokens; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.refresh_tokens IS 'Auth: Store of tokens used to refresh JWT tokens once they expire.';



--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE; Schema: auth; Owner: supabase_auth_admin
--

CREATE SEQUENCE auth.refresh_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: auth; Owner: supabase_auth_admin
--

ALTER SEQUENCE auth.refresh_tokens_id_seq OWNED BY auth.refresh_tokens.id;



--
-- Name: saml_providers; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.saml_providers (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    entity_id text NOT NULL,
    metadata_xml text NOT NULL,
    metadata_url text,
    attribute_mapping jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    name_id_format text,
    CONSTRAINT "entity_id not empty" CHECK ((char_length(entity_id) > 0)),
    CONSTRAINT "metadata_url not empty" CHECK (((metadata_url = NULL::text) OR (char_length(metadata_url) > 0))),
    CONSTRAINT "metadata_xml not empty" CHECK ((char_length(metadata_xml) > 0))
);


--
-- Name: TABLE saml_providers; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.saml_providers IS 'Auth: Manages SAML Identity Provider connections.';



--
-- Name: saml_relay_states; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.saml_relay_states (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    request_id text NOT NULL,
    for_email text,
    redirect_to text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    flow_state_id uuid,
    CONSTRAINT "request_id not empty" CHECK ((char_length(request_id) > 0))
);


--
-- Name: TABLE saml_relay_states; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.saml_relay_states IS 'Auth: Contains SAML Relay State information for each Service Provider initiated login.';



--
-- Name: schema_migrations; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.schema_migrations (
    version character varying(255) NOT NULL
);


--
-- Name: TABLE schema_migrations; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.schema_migrations IS 'Auth: Manages updates to the auth system.';



--
-- Name: sessions; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    factor_id uuid,
    aal auth.aal_level,
    not_after timestamp with time zone,
    refreshed_at timestamp without time zone,
    user_agent text,
    ip inet,
    tag text
);


--
-- Name: TABLE sessions; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.sessions IS 'Auth: Stores session data associated to a user.';



--
-- Name: COLUMN sessions.not_after; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.sessions.not_after IS 'Auth: Not after is a nullable column that contains a timestamp after which the session should be regarded as expired.';



--
-- Name: sso_domains; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.sso_domains (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    domain text NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "domain not empty" CHECK ((char_length(domain) > 0))
);


--
-- Name: TABLE sso_domains; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.sso_domains IS 'Auth: Manages SSO email address domain mapping to an SSO Identity Provider.';



--
-- Name: sso_providers; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.sso_providers (
    id uuid NOT NULL,
    resource_id text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "resource_id not empty" CHECK (((resource_id = NULL::text) OR (char_length(resource_id) > 0)))
);


--
-- Name: TABLE sso_providers; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.sso_providers IS 'Auth: Manages SSO identity provider information; see saml_providers for SAML.';



--
-- Name: COLUMN sso_providers.resource_id; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.sso_providers.resource_id IS 'Auth: Uniquely identifies a SSO provider according to a user-chosen resource ID (case insensitive), useful in infrastructure as code.';



--
-- Name: users; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.users (
    instance_id uuid,
    id uuid NOT NULL,
    aud character varying(255),
    role character varying(255),
    email character varying(255),
    encrypted_password character varying(255),
    email_confirmed_at timestamp with time zone,
    invited_at timestamp with time zone,
    confirmation_token character varying(255),
    confirmation_sent_at timestamp with time zone,
    recovery_token character varying(255),
    recovery_sent_at timestamp with time zone,
    email_change_token_new character varying(255),
    email_change character varying(255),
    email_change_sent_at timestamp with time zone,
    last_sign_in_at timestamp with time zone,
    raw_app_meta_data jsonb,
    raw_user_meta_data jsonb,
    is_super_admin boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    phone text DEFAULT NULL::character varying,
    phone_confirmed_at timestamp with time zone,
    phone_change text DEFAULT ''::character varying,
    phone_change_token character varying(255) DEFAULT ''::character varying,
    phone_change_sent_at timestamp with time zone,
    confirmed_at timestamp with time zone GENERATED ALWAYS AS (LEAST(email_confirmed_at, phone_confirmed_at)) STORED,
    email_change_token_current character varying(255) DEFAULT ''::character varying,
    email_change_confirm_status smallint DEFAULT 0,
    banned_until timestamp with time zone,
    reauthentication_token character varying(255) DEFAULT ''::character varying,
    reauthentication_sent_at timestamp with time zone,
    is_sso_user boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    is_anonymous boolean DEFAULT false NOT NULL,
    CONSTRAINT users_email_change_confirm_status_check CHECK (((email_change_confirm_status >= 0) AND (email_change_confirm_status <= 2)))
);


--
-- Name: TABLE users; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.users IS 'Auth: Stores user login data within a secure schema.';



--
-- Name: COLUMN users.is_sso_user; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.users.is_sso_user IS 'Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.';



--
-- Name: __drizzle_migrations; Type: TABLE; Schema: drizzle; Owner: postgres
--

CREATE TABLE drizzle.__drizzle_migrations (
    id integer NOT NULL,
    hash text NOT NULL,
    created_at bigint
);


--
-- Name: __drizzle_migrations_id_seq; Type: SEQUENCE; Schema: drizzle; Owner: postgres
--

CREATE SEQUENCE drizzle.__drizzle_migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: __drizzle_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: drizzle; Owner: postgres
--

ALTER SEQUENCE drizzle.__drizzle_migrations_id_seq OWNED BY drizzle.__drizzle_migrations.id;



--
-- Name: funding_calls; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.funding_calls (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    programme character varying(50) NOT NULL,
    programme_part character varying(100),
    work_programme_year integer,
    topic_code character varying(100) NOT NULL,
    call_identifier character varying(100),
    title text NOT NULL,
    action_type character varying(50),
    call_year integer,
    opening_date date,
    deadline date,
    second_stage_deadline date,
    status character varying(20) DEFAULT 'upcoming'::character varying,
    budget_total numeric(15,2),
    budget_per_project_min numeric(15,2),
    budget_per_project_max numeric(15,2),
    expected_projects integer,
    funding_rate integer,
    expected_outcome text,
    scope text,
    eligibility text,
    cluster character varying(50),
    destination character varying(200),
    tags text[],
    source_document_id uuid,
    source_document_title text,
    source_page_number integer,
    portal_url text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    embedding public.vector(768),
    embedding_updated_at timestamp with time zone,
    CONSTRAINT valid_programme CHECK (((programme)::text = ANY ((ARRAY['horizon_europe'::character varying, 'horizon_plus'::character varying, 'digital_europe'::character varying, 'life'::character varying, 'creative_europe'::character varying, 'edf'::character varying, 'euratom'::character varying, 'erasmus'::character varying, 'cef'::character varying, 'interreg'::character varying, 'eu4health'::character varying, 'other'::character varying])::text[]))),
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'upcoming'::character varying, 'closed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: TABLE funding_calls; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.funding_calls IS 'Structured funding call data extracted from EU programme Work Programmes. Supports Horizon Europe, Digital Europe, LIFE, and other EU funding programmes.';



--
-- Name: COLUMN funding_calls.embedding; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.funding_calls.embedding IS 'Vector embedding (768-dim) for semantic search using Google text-embedding-004';



--
-- Name: active_funding_calls; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.active_funding_calls AS
 SELECT funding_calls.id,
    funding_calls.programme,
    funding_calls.programme_part,
    funding_calls.work_programme_year,
    funding_calls.topic_code,
    funding_calls.call_identifier,
    funding_calls.title,
    funding_calls.action_type,
    funding_calls.call_year,
    funding_calls.opening_date,
    funding_calls.deadline,
    funding_calls.second_stage_deadline,
    funding_calls.status,
    funding_calls.budget_total,
    funding_calls.budget_per_project_min,
    funding_calls.budget_per_project_max,
    funding_calls.expected_projects,
    funding_calls.funding_rate,
    funding_calls.expected_outcome,
    funding_calls.scope,
    funding_calls.eligibility,
    funding_calls.cluster,
    funding_calls.destination,
    funding_calls.tags,
    funding_calls.source_document_id,
    funding_calls.source_document_title,
    funding_calls.source_page_number,
    funding_calls.portal_url,
    funding_calls.metadata,
    funding_calls.created_at,
    funding_calls.updated_at
   FROM public.funding_calls
  WHERE ((funding_calls.status)::text = ANY ((ARRAY['open'::character varying, 'upcoming'::character varying])::text[]))
  ORDER BY funding_calls.deadline;


--
-- Name: proposal_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proposal_sessions (
    id integer NOT NULL,
    session_id uuid NOT NULL,
    proposal_id integer,
    conversation_id integer,
    user_id character varying(100) NOT NULL,
    active_section_id character varying(100),
    session_state jsonb DEFAULT '{}'::jsonb,
    status character varying(20) DEFAULT 'active'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    last_activity_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone,
    CONSTRAINT valid_session_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'paused'::character varying, 'completed'::character varying, 'expired'::character varying])::text[])))
);


--
-- Name: proposals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proposals (
    id integer NOT NULL,
    call_identifier character varying(255) NOT NULL,
    conversation_id integer,
    proposal_title character varying(500),
    proposal_acronym character varying(50),
    proposal_type character varying(50) NOT NULL,
    status character varying(50) DEFAULT 'draft'::character varying,
    completion_percentage integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    submitted_at timestamp without time zone,
    user_id character varying(100),
    project_summary text,
    research_area character varying(255),
    duration_months integer,
    total_budget numeric(15,2),
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'in_review'::character varying, 'final'::character varying, 'submitted'::character varying, 'archived'::character varying])::text[])))
);



--
-- Name: call_document_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.call_document_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: call_document_mappings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.call_document_mappings (
    id integer NOT NULL,
    call_identifier character varying(255) NOT NULL,
    document_id integer NOT NULL,
    relevance_score numeric(3,2) DEFAULT 1.0,
    is_primary boolean DEFAULT false,
    mapping_source character varying(100) DEFAULT 'manual'::character varying,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: TABLE call_document_mappings; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.call_document_mappings IS 'Many-to-many mapping between calls and documents';



--
-- Name: COLUMN call_document_mappings.relevance_score; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.call_document_mappings.relevance_score IS 'How relevant is this document to this call (1.0 = primary, 0.5 = somewhat relevant)';



--
-- Name: shared_document_chunks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shared_document_chunks (
    id integer NOT NULL,
    document_id integer NOT NULL,
    chunk_text text NOT NULL,
    chunk_index integer DEFAULT 0,
    token_count integer DEFAULT 0,
    section_title character varying(255),
    page_numbers integer[],
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: TABLE shared_document_chunks; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.shared_document_chunks IS 'Text chunks from shared documents for semantic search';



--
-- Name: shared_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shared_documents (
    id integer NOT NULL,
    document_key character varying(255) NOT NULL,
    document_type character varying(100) NOT NULL,
    document_title character varying(500),
    document_version character varying(50),
    scope character varying(100),
    scope_identifier character varying(255),
    document_content text,
    document_url character varying(1000),
    file_path character varying(500),
    file_hash character varying(64),
    last_updated timestamp without time zone DEFAULT now(),
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: TABLE shared_documents; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.shared_documents IS 'Central repository for all Horizon Europe documents (stored once, referenced many times)';



--
-- Name: COLUMN shared_documents.document_key; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.shared_documents.document_key IS 'Unique identifier like "he_general_annexes_2023-2025" or "he_wp_cluster6_2023-2025"';



--
-- Name: COLUMN shared_documents.scope; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.shared_documents.scope IS 'Document scope: global (all calls), cluster (one cluster), call (specific call)';



--
-- Name: call_document_chunks_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.call_document_chunks_view AS
 SELECT cdm.call_identifier,
    sd.document_key,
    sd.document_type,
    sd.document_title,
    sdc.id AS chunk_id,
    sdc.chunk_text,
    sdc.chunk_index,
    sdc.section_title,
    sdc.page_numbers,
    sdc.token_count,
    cdm.relevance_score,
    cdm.is_primary
   FROM ((public.call_document_mappings cdm
     JOIN public.shared_documents sd ON ((cdm.document_id = sd.id)))
     JOIN public.shared_document_chunks sdc ON ((sd.id = sdc.document_id)));


--
-- Name: call_document_mappings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.call_document_mappings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: call_document_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.call_document_mappings_id_seq OWNED BY public.call_document_mappings.id;



--
-- Name: call_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.call_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: call_metadata; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.call_metadata (
    id integer NOT NULL,
    call_identifier character varying(255) NOT NULL,
    title text,
    summary text,
    call_title text,
    status character varying(50),
    opening_date timestamp without time zone,
    deadline_date timestamp without time zone,
    budget_overview jsonb,
    min_contribution bigint,
    max_contribution bigint,
    expected_grants integer,
    eligible_countries text,
    eligibility_restrictions text,
    eligibility_conditions_html text,
    types_of_action text[],
    cross_cutting_priorities text[],
    tags text[],
    keywords text[],
    topic_url character varying(1000),
    api_data_url character varying(1000),
    raw_api_response jsonb,
    fetched_at timestamp without time zone DEFAULT now(),
    last_updated timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: TABLE call_metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.call_metadata IS 'Structured metadata extracted directly from EU Portal API - gives AI instant access to key info';



--
-- Name: COLUMN call_metadata.eligible_countries; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.call_metadata.eligible_countries IS 'Extracted from topicConditions HTML - e.g., "Member States and Associated Countries"';



--
-- Name: COLUMN call_metadata.eligibility_restrictions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.call_metadata.eligibility_restrictions IS 'Any specific restrictions - e.g., "entities controlled by non-eligible countries excluded"';



--
-- Name: COLUMN call_metadata.eligibility_conditions_html; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.call_metadata.eligibility_conditions_html IS 'Full eligibility HTML from API response for reference';



--
-- Name: call_metadata_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.call_metadata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: call_metadata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.call_metadata_id_seq OWNED BY public.call_metadata.id;



--
-- Name: citations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.citations (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    message_id integer,
    citation_type character varying(50) NOT NULL,
    citation_key character varying(255) NOT NULL,
    citation_data jsonb NOT NULL,
    citation_text text,
    relevance_score numeric(5,4),
    position_in_response integer,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: citations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.citations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: citations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.citations_id_seq OWNED BY public.citations.id;



--
-- Name: client; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.client (
    id integer NOT NULL,
    auth_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    password character varying(255) DEFAULT 'password_not_used'::character varying NOT NULL,
    first_name character varying(255) DEFAULT 'User'::character varying NOT NULL,
    last_name character varying(255) DEFAULT ''::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: client_collaboration; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.client_collaboration (
    id integer NOT NULL,
    collaboration_id integer NOT NULL,
    client_id integer NOT NULL,
    role public.role DEFAULT 'member'::public.role NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: client_collaboration_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.client_collaboration_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: client_collaboration_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.client_collaboration_id_seq OWNED BY public.client_collaboration.id;



--
-- Name: client_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.client_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: client_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.client_id_seq OWNED BY public.client.id;



--
-- Name: collaboration; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.collaboration (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: collaboration_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.collaboration_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: collaboration_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.collaboration_id_seq OWNED BY public.collaboration.id;



--
-- Name: compliance_checks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.compliance_checks (
    id integer NOT NULL,
    proposal_id integer NOT NULL,
    check_type character varying(100) NOT NULL,
    check_category character varying(50),
    check_result character varying(20) NOT NULL,
    result_message text,
    details jsonb DEFAULT '{}'::jsonb,
    checked_at timestamp without time zone DEFAULT now(),
    checked_by character varying(100),
    CONSTRAINT valid_check_result CHECK (((check_result)::text = ANY ((ARRAY['pass'::character varying, 'fail'::character varying, 'warning'::character varying, 'info'::character varying])::text[])))
);


--
-- Name: compliance_checks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.compliance_checks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: compliance_checks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.compliance_checks_id_seq OWNED BY public.compliance_checks.id;



--
-- Name: conversation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversation (
    id integer NOT NULL,
    user_id integer NOT NULL,
    topic character varying(255),
    name character varying(255),
    archived boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    collaboration_id integer
);


--
-- Name: conversation_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversation_analytics (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    user_id integer DEFAULT 1,
    message_id uuid DEFAULT gen_random_uuid(),
    question text NOT NULL,
    response text,
    tools_used text[],
    confidence double precision,
    response_time_ms integer,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb,
    session_id character varying(255),
    ip_address character varying(45),
    user_agent text,
    status character varying(50) DEFAULT 'completed'::character varying,
    error_message text,
    was_helpful boolean,
    user_rating integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT conversation_analytics_user_rating_check CHECK (((user_rating >= 1) AND (user_rating <= 5)))
);


--
-- Name: TABLE conversation_analytics; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.conversation_analytics IS 'Stores all conversation messages and responses for analytics, iteration, and quality improvement';



--
-- Name: COLUMN conversation_analytics.tools_used; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.conversation_analytics.tools_used IS 'Array of tool names used to answer the question';



--
-- Name: COLUMN conversation_analytics.confidence; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.conversation_analytics.confidence IS 'AI-reported confidence in the response (0.0 to 1.0)';



--
-- Name: COLUMN conversation_analytics.metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.conversation_analytics.metadata IS 'Full raw response metadata in JSON format for detailed analysis';


--
-- Name: conversation_analytics_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversation_analytics_daily_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: conversation_analytics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversation_analytics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_analytics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.conversation_analytics_id_seq OWNED BY public.conversation_analytics.id;



--
-- Name: conversation_call_context_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversation_call_context_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: conversation_facts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversation_facts (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    fact_type character varying(100) NOT NULL,
    fact_content text NOT NULL,
    confidence numeric(3,2) DEFAULT 0.5,
    source_message_id integer,
    extracted_at timestamp without time zone DEFAULT now()
);


--
-- Name: conversation_facts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversation_facts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_facts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.conversation_facts_id_seq OWNED BY public.conversation_facts.id;



--
-- Name: conversation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.conversation_id_seq OWNED BY public.conversation.id;



--
-- Name: conversation_memory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversation_memory (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    memory_type character varying(50) NOT NULL,
    content jsonb NOT NULL,
    token_count integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: conversation_memory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.conversation_memory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_memory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.conversation_memory_id_seq OWNED BY public.conversation_memory.id;



--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.document_chunks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    chunk_hash text NOT NULL,
    content text NOT NULL,
    content_length integer,
    embedding public.vector(768),
    section_title text,
    page_number integer,
    chapter text,
    subsection text,
    content_tokens tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content)) STORED,
    metadata jsonb DEFAULT '{}'::jsonb,
    token_count integer,
    embedding_model text DEFAULT 'text-embedding-004'::text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: embedding_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.embedding_cache (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    text_hash text NOT NULL,
    text_content text NOT NULL,
    embedding public.vector(768) NOT NULL,
    model_version text DEFAULT 'text-embedding-004'::text,
    usage_count integer DEFAULT 1,
    last_used timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: entity_cards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.entity_cards (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_name character varying(255) NOT NULL,
    entity_data jsonb,
    first_mentioned_at timestamp without time zone DEFAULT now(),
    last_referenced_at timestamp without time zone DEFAULT now(),
    reference_count integer DEFAULT 1
);


--
-- Name: entity_cards_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.entity_cards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entity_cards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.entity_cards_id_seq OWNED BY public.entity_cards.id;


--
-- Name: feedback_insights_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.feedback_insights_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: horizon_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.horizon_documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_type text NOT NULL,
    source_url text,
    file_path text,
    title text NOT NULL,
    document_type text,
    programme_year text,
    programme_part text,
    language text DEFAULT 'en'::text,
    version text,
    status text DEFAULT 'active'::text,
    file_hash text,
    total_chunks integer DEFAULT 0,
    metadata jsonb DEFAULT '{}'::jsonb,
    processing_started_at timestamp with time zone,
    processing_completed_at timestamp with time zone,
    last_updated timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    created_by uuid,
    CONSTRAINT horizon_documents_document_type_check CHECK ((document_type = ANY (ARRAY['work_programme'::text, 'programme_guide'::text, 'call_text'::text, 'grant_agreement'::text, 'faq'::text, 'manual'::text, 'policy'::text, 'template'::text, 'additional_resource'::text]))),
    CONSTRAINT horizon_documents_source_type_check CHECK ((source_type = ANY (ARRAY['pdf'::text, 'web'::text, 'cordis'::text, 'manual'::text]))),
    CONSTRAINT horizon_documents_status_check CHECK ((status = ANY (ARRAY['active'::text, 'archived'::text, 'processing'::text, 'failed'::text])))
);


--
-- Name: horizon_europe_calls; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.horizon_europe_calls AS
 SELECT funding_calls.id,
    funding_calls.programme,
    funding_calls.programme_part,
    funding_calls.work_programme_year,
    funding_calls.topic_code,
    funding_calls.call_identifier,
    funding_calls.title,
    funding_calls.action_type,
    funding_calls.call_year,
    funding_calls.opening_date,
    funding_calls.deadline,
    funding_calls.second_stage_deadline,
    funding_calls.status,
    funding_calls.budget_total,
    funding_calls.budget_per_project_min,
    funding_calls.budget_per_project_max,
    funding_calls.expected_projects,
    funding_calls.funding_rate,
    funding_calls.expected_outcome,
    funding_calls.scope,
    funding_calls.eligibility,
    funding_calls.cluster,
    funding_calls.destination,
    funding_calls.tags,
    funding_calls.source_document_id,
    funding_calls.source_document_title,
    funding_calls.source_page_number,
    funding_calls.portal_url,
    funding_calls.metadata,
    funding_calls.created_at,
    funding_calls.updated_at
   FROM public.funding_calls
  WHERE ((funding_calls.programme)::text = 'horizon_europe'::text)
  ORDER BY funding_calls.call_year DESC, funding_calls.topic_code;


--
-- Name: improvement_suggestions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.improvement_suggestions (
    id integer NOT NULL,
    section_id integer,
    proposal_id integer NOT NULL,
    suggestion_type character varying(100) NOT NULL,
    suggestion_text text NOT NULL,
    priority character varying(20) NOT NULL,
    affected_text text,
    suggested_replacement text,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    resolved_at timestamp without time zone,
    resolved_by character varying(100),
    CONSTRAINT valid_priority CHECK (((priority)::text = ANY ((ARRAY['critical'::character varying, 'high'::character varying, 'medium'::character varying, 'low'::character varying])::text[]))),
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'applied'::character varying, 'dismissed'::character varying, 'reviewing'::character varying])::text[])))
);


--
-- Name: improvement_suggestions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.improvement_suggestions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: improvement_suggestions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.improvement_suggestions_id_seq OWNED BY public.improvement_suggestions.id;


--
-- Name: message; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.message (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    user_id integer,
    text text NOT NULL,
    sender character varying(50) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    ai_provider character varying(50),
    ai_version character varying(100),
    model_used character varying(100),
    data_source character varying(100),
    processing_time numeric,
    projects_found integer,
    logs_question text,
    logs_model_used character varying(100),
    logs_phases text,
    logs_total_processing_time_ms integer,
    logs_projects_retrieved integer,
    logs_projects_processed integer,
    logs_success boolean,
    logs_average_relevance_score numeric,
    extracted_queries text,
    retrieved_projects text,
    enhanced_project_summaries text,
    portfolio_insights text,
    llm_prompt text,
    rerank_criteria text,
    citations jsonb
);


--
-- Name: COLUMN message.citations; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.message.citations IS 'JSONB field storing citations associated with the message response';



--
-- Name: message_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.message_id_seq OWNED BY public.message.id;



--
-- Name: organizations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organizations (
    "projectID" integer NOT NULL,
    "projectAcronym" text,
    "organisationID" text NOT NULL,
    "vatNumber" text,
    name text,
    "shortName" text,
    "SME" boolean,
    "activityType" text,
    street text,
    "postCode" text,
    city text,
    country text,
    "nutsCode" text,
    geolocation text,
    "organizationURL" text,
    "contactForm" text,
    "contentUpdateDate" timestamp without time zone,
    rcn integer,
    "order" integer,
    role text,
    "ecContribution" numeric,
    "netEcContribution" numeric,
    "totalCost" numeric,
    "endOfParticipation" boolean,
    active boolean,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: project_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_embeddings (
    project_id integer NOT NULL,
    title_embedding public.vector(3072),
    objective_embedding public.vector(3072),
    combined_embedding public.vector(3072),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    model_version text DEFAULT 'gemini-embedding-001'::text,
    text_length integer,
    embedding_status text DEFAULT 'completed'::text,
    error_message text
);


--
-- Name: TABLE project_embeddings; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.project_embeddings IS 'Vector embeddings for semantic project search using text-embedding-004 model';



--
-- Name: COLUMN project_embeddings.project_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.project_embeddings.project_id IS 'Foreign key to projects table';



--
-- Name: COLUMN project_embeddings.title_embedding; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.project_embeddings.title_embedding IS 'Vector embedding of project title only (768 dimensions)';



--
-- Name: COLUMN project_embeddings.objective_embedding; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.project_embeddings.objective_embedding IS 'Vector embedding of project objective only (768 dimensions)';



--
-- Name: COLUMN project_embeddings.combined_embedding; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.project_embeddings.combined_embedding IS 'Vector embedding of title + objective (first 2000 chars, 768 dimensions)';



--
-- Name: COLUMN project_embeddings.model_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.project_embeddings.model_version IS 'Embedding model version (e.g., text-embedding-004)';



--
-- Name: COLUMN project_embeddings.text_length; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.project_embeddings.text_length IS 'Length of text used for generating combined_embedding';



--
-- Name: COLUMN project_embeddings.embedding_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.project_embeddings.embedding_status IS 'Status: completed, failed, or pending';



--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    acronym text,
    status text,
    title text,
    "startDate" date,
    "endDate" date,
    "totalCost" numeric,
    "ecMaxContribution" numeric,
    "legalBasis" text,
    topics text,
    "ecSignatureDate" date,
    "frameworkProgramme" text,
    "masterCall" text,
    "subCall" text,
    "fundingScheme" text,
    nature text,
    objective text,
    "contentUpdateDate" timestamp without time zone,
    rcn integer,
    "grantDoi" text
);


--
-- Name: proposal_activity_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proposal_activity_log (
    id integer NOT NULL,
    proposal_id integer NOT NULL,
    activity_type character varying(100) NOT NULL,
    activity_description text,
    user_id character varying(100),
    changes_made jsonb,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: proposal_activity_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_activity_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposal_activity_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proposal_activity_log_id_seq OWNED BY public.proposal_activity_log.id;



--
-- Name: proposal_budgets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proposal_budgets (
    id integer NOT NULL,
    proposal_id integer NOT NULL,
    consortium_id integer,
    partner_name character varying(255) NOT NULL,
    partner_country character varying(3) NOT NULL,
    partner_type character varying(50) NOT NULL,
    personnel_costs numeric(12,2) DEFAULT 0,
    subcontracting_costs numeric(12,2) DEFAULT 0,
    equipment_costs numeric(12,2) DEFAULT 0,
    other_direct_costs numeric(12,2) DEFAULT 0,
    indirect_costs numeric(12,2) DEFAULT 0,
    total_eligible_costs numeric(12,2) GENERATED ALWAYS AS (((((personnel_costs + subcontracting_costs) + equipment_costs) + other_direct_costs) + indirect_costs)) STORED,
    funding_rate numeric(3,2) NOT NULL,
    requested_funding numeric(12,2),
    personnel_justification text,
    equipment_justification text,
    other_justification text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT valid_funding_rate CHECK ((funding_rate = ANY (ARRAY[0.70, 1.00])))
);


--
-- Name: proposal_budgets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_budgets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposal_budgets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proposal_budgets_id_seq OWNED BY public.proposal_budgets.id;



--
-- Name: proposal_consortium; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proposal_consortium (
    id integer NOT NULL,
    proposal_id integer NOT NULL,
    partner_name character varying(255) NOT NULL,
    partner_short_name character varying(50),
    partner_country character varying(3) NOT NULL,
    partner_type character varying(50) NOT NULL,
    is_coordinator boolean DEFAULT false,
    partner_role text,
    partner_expertise text,
    contact_person character varying(255),
    contact_email character varying(255),
    person_months numeric(6,2),
    budget_share numeric(3,2),
    work_packages integer[],
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT valid_budget_share CHECK (((budget_share >= (0)::numeric) AND (budget_share <= (1)::numeric))),
    CONSTRAINT valid_partner_type CHECK (((partner_type)::text = ANY ((ARRAY['HES'::character varying, 'REC'::character varying, 'PRC'::character varying, 'OTH'::character varying])::text[])))
);


--
-- Name: proposal_consortium_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_consortium_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposal_consortium_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proposal_consortium_id_seq OWNED BY public.proposal_consortium.id;


--
-- Name: proposal_deliverables_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_deliverables_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: proposal_examples; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proposal_examples (
    id integer NOT NULL,
    call_identifier character varying(255),
    section_id character varying(100) NOT NULL,
    section_name character varying(255),
    example_text text NOT NULL,
    evaluation_score numeric(3,1),
    success_factors text[],
    is_public boolean DEFAULT false,
    is_anonymized boolean DEFAULT true,
    added_at timestamp without time zone DEFAULT now(),
    added_by character varying(100),
    tags text[]
);


--
-- Name: proposal_examples_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_examples_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposal_examples_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proposal_examples_id_seq OWNED BY public.proposal_examples.id;


--
-- Name: proposal_milestones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_milestones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: proposal_overview; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.proposal_overview AS
SELECT
    NULL::integer AS id,
    NULL::character varying(255) AS call_identifier,
    NULL::character varying(500) AS proposal_title,
    NULL::character varying(50) AS proposal_acronym,
    NULL::character varying(50) AS proposal_type,
    NULL::character varying(50) AS status,
    NULL::integer AS completion_percentage,
    NULL::timestamp without time zone AS created_at,
    NULL::timestamp without time zone AS updated_at,
    NULL::bigint AS section_count,
    NULL::bigint AS total_words,
    NULL::numeric AS avg_quality_score,
    NULL::bigint AS partner_count,
    NULL::bigint AS country_count,
    NULL::numeric AS total_budget,
    NULL::numeric AS total_funding_requested,
    NULL::bigint AS critical_issues,
    NULL::bigint AS warnings;


--
-- Name: proposal_sections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proposal_sections (
    id integer NOT NULL,
    proposal_id integer NOT NULL,
    section_id character varying(100) NOT NULL,
    section_name character varying(255) NOT NULL,
    section_order integer,
    section_content text,
    word_count integer DEFAULT 0,
    version integer DEFAULT 1,
    parent_version_id integer,
    is_current boolean DEFAULT true,
    compliance_score numeric(3,2),
    quality_score numeric(3,2),
    completeness_score numeric(3,2),
    created_at timestamp without time zone DEFAULT now(),
    created_by character varying(100),
    notes text
);


--
-- Name: proposal_sections_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_sections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposal_sections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proposal_sections_id_seq OWNED BY public.proposal_sections.id;



--
-- Name: proposal_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposal_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proposal_sessions_id_seq OWNED BY public.proposal_sessions.id;


--
-- Name: proposal_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposal_work_packages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposal_work_packages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: proposals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proposals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proposals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proposals_id_seq OWNED BY public.proposals.id;



--
-- Name: response_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.response_feedback (
    id integer NOT NULL,
    conversation_id character varying(255) NOT NULL,
    message_id character varying(255),
    query_text text,
    response_text text,
    rating integer,
    feedback_type character varying(50),
    feedback_text text,
    tools_used text[],
    query_type character varying(50),
    response_time_ms integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT response_feedback_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


--
-- Name: response_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.response_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: response_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.response_feedback_id_seq OWNED BY public.response_feedback.id;


--
-- Name: retrieval_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.retrieval_cache_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schema_migrations (
    version character varying(50) NOT NULL,
    applied_at timestamp without time zone DEFAULT now()
);


--
-- Name: section_criteria_mapping; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.section_criteria_mapping (
    id integer NOT NULL,
    section_id integer NOT NULL,
    criterion_name character varying(255) NOT NULL,
    criterion_category character varying(50),
    addressed boolean DEFAULT false,
    strength_score numeric(3,2),
    evidence text[],
    gaps text[],
    last_checked timestamp without time zone DEFAULT now(),
    checked_by character varying(100)
);


--
-- Name: section_criteria_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.section_criteria_mapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: section_criteria_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.section_criteria_mapping_id_seq OWNED BY public.section_criteria_mapping.id;



--
-- Name: section_locks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.section_locks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: section_quality_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.section_quality_summary AS
SELECT
    NULL::integer AS id,
    NULL::integer AS proposal_id,
    NULL::character varying(100) AS section_id,
    NULL::character varying(255) AS section_name,
    NULL::integer AS word_count,
    NULL::numeric(3,2) AS quality_score,
    NULL::numeric(3,2) AS compliance_score,
    NULL::numeric(3,2) AS completeness_score,
    NULL::bigint AS total_criteria,
    NULL::bigint AS addressed_criteria,
    NULL::numeric AS avg_criteria_strength,
    NULL::bigint AS pending_suggestions,
    NULL::bigint AS critical_suggestions;


--
-- Name: session_activity_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.session_activity_summary AS
 SELECT date(proposal_sessions.last_activity_at) AS activity_date,
    count(DISTINCT proposal_sessions.session_id) AS active_sessions,
    count(DISTINCT proposal_sessions.user_id) AS unique_users,
    count(DISTINCT proposal_sessions.proposal_id) AS proposals_worked_on
   FROM public.proposal_sessions
  WHERE (((proposal_sessions.status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying])::text[])) AND (proposal_sessions.last_activity_at > (now() - '30 days'::interval)))
  GROUP BY (date(proposal_sessions.last_activity_at))
  ORDER BY (date(proposal_sessions.last_activity_at)) DESC;


--
-- Name: session_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.session_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: shared_document_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.shared_document_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shared_document_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.shared_document_chunks_id_seq OWNED BY public.shared_document_chunks.id;



--
-- Name: shared_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.shared_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shared_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.shared_documents_id_seq OWNED BY public.shared_documents.id;



--
-- Name: tool_combination_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tool_combination_analytics (
    id integer NOT NULL,
    tool_sequence text[] NOT NULL,
    occurrence_count integer DEFAULT 1,
    avg_total_time_ms double precision,
    success_rate double precision,
    last_seen timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: tool_combination_analytics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tool_combination_analytics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tool_combination_analytics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tool_combination_analytics_id_seq OWNED BY public.tool_combination_analytics.id;


--
-- Name: tool_execution_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tool_execution_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tool_performance_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tool_performance_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: tool_usage_analytics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tool_usage_analytics (
    id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    conversation_id character varying(255),
    query_hash character varying(64),
    tool_name character varying(100) NOT NULL,
    parameters jsonb,
    execution_time_ms integer,
    success boolean DEFAULT true,
    error_message text,
    result_count integer,
    result_quality_score double precision,
    speculative boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: tool_usage_analytics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tool_usage_analytics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tool_usage_analytics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tool_usage_analytics_id_seq OWNED BY public.tool_usage_analytics.id;



--
-- Name: v_conversation_analytics_24h; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_conversation_analytics_24h AS
 SELECT count(*) AS total_messages,
    count(DISTINCT conversation_analytics.conversation_id) AS unique_conversations,
    count(DISTINCT conversation_analytics.user_id) AS unique_users,
    round((avg(conversation_analytics.confidence))::numeric, 3) AS avg_confidence,
    round(avg(conversation_analytics.response_time_ms), 0) AS avg_response_time_ms,
    sum(
        CASE
            WHEN ((conversation_analytics.status)::text = 'error'::text) THEN 1
            ELSE 0
        END) AS error_count,
    sum(
        CASE
            WHEN (conversation_analytics.confidence >= (0.7)::double precision) THEN 1
            ELSE 0
        END) AS high_confidence_count,
    sum(
        CASE
            WHEN ((conversation_analytics.confidence >= (0.4)::double precision) AND (conversation_analytics.confidence < (0.7)::double precision)) THEN 1
            ELSE 0
        END) AS medium_confidence_count,
    sum(
        CASE
            WHEN ((conversation_analytics.confidence < (0.4)::double precision) OR (conversation_analytics.confidence IS NULL)) THEN 1
            ELSE 0
        END) AS low_confidence_count
   FROM public.conversation_analytics
  WHERE (conversation_analytics.created_at > (now() - '24:00:00'::interval));


--
-- Name: v_embedding_coverage; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_embedding_coverage AS
 SELECT count(DISTINCT p.id) AS total_projects,
    count(DISTINCT pe.project_id) AS embedded_projects,
    (count(DISTINCT p.id) - count(DISTINCT pe.project_id)) AS missing_embeddings,
    round(((100.0 * (count(DISTINCT pe.project_id))::numeric) / (NULLIF(count(DISTINCT p.id), 0))::numeric), 2) AS coverage_percent
   FROM (public.projects p
     LEFT JOIN public.project_embeddings pe ON ((p.id = pe.project_id)))
  WHERE ((p.title IS NOT NULL) AND (p.objective IS NOT NULL));


--
-- Name: VIEW v_embedding_coverage; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_embedding_coverage IS 'Monitor embedding coverage across all projects';



--
-- Name: v_embedding_stats; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_embedding_stats AS
 SELECT project_embeddings.model_version,
    project_embeddings.embedding_status,
    count(*) AS count,
    avg(project_embeddings.text_length) AS avg_text_length,
    min(project_embeddings.created_at) AS first_created,
    max(project_embeddings.created_at) AS last_created
   FROM public.project_embeddings
  GROUP BY project_embeddings.model_version, project_embeddings.embedding_status
  ORDER BY project_embeddings.model_version, project_embeddings.embedding_status;


--
-- Name: VIEW v_embedding_stats; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.v_embedding_stats IS 'Statistics about embeddings by model version and status';



--
-- Name: v_feedback_metrics_7d; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_feedback_metrics_7d AS
 SELECT count(*) AS total_feedback,
    round(avg(response_feedback.rating), 2) AS avg_rating,
    sum(
        CASE
            WHEN ((response_feedback.feedback_type)::text = 'helpful'::text) THEN 1
            ELSE 0
        END) AS helpful_count,
    sum(
        CASE
            WHEN ((response_feedback.feedback_type)::text = 'not_helpful'::text) THEN 1
            ELSE 0
        END) AS not_helpful_count,
    sum(
        CASE
            WHEN ((response_feedback.feedback_type)::text = 'incorrect'::text) THEN 1
            ELSE 0
        END) AS incorrect_count,
    sum(
        CASE
            WHEN ((response_feedback.feedback_type)::text = 'incomplete'::text) THEN 1
            ELSE 0
        END) AS incomplete_count,
    round(((((sum(
        CASE
            WHEN (response_feedback.rating >= 4) THEN 1
            ELSE 0
        END))::double precision / (NULLIF(count(*), 0))::double precision) * (100)::double precision))::numeric, 1) AS satisfaction_rate
   FROM public.response_feedback
  WHERE (response_feedback.created_at > (now() - '7 days'::interval));


--
-- Name: v_popular_tool_combos; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_popular_tool_combos AS
 SELECT tool_combination_analytics.tool_sequence,
    tool_combination_analytics.occurrence_count,
    round((tool_combination_analytics.avg_total_time_ms)::numeric, 0) AS avg_time_ms,
    round(((tool_combination_analytics.success_rate * (100)::double precision))::numeric, 1) AS success_rate_pct,
    tool_combination_analytics.last_seen
   FROM public.tool_combination_analytics
  WHERE (tool_combination_analytics.occurrence_count > 5)
  ORDER BY tool_combination_analytics.occurrence_count DESC
 LIMIT 20;


--
-- Name: v_question_patterns; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_question_patterns AS
 SELECT
        CASE
            WHEN ((conversation_analytics.question ~~* '%call%'::text) OR (conversation_analytics.question ~~* '%funding%'::text)) THEN 'funding_calls'::text
            WHEN ((conversation_analytics.question ~~* '%project%'::text) OR (conversation_analytics.question ~~* '%cordis%'::text)) THEN 'projects'::text
            WHEN ((conversation_analytics.question ~~* '%partner%'::text) OR (conversation_analytics.question ~~* '%consortium%'::text)) THEN 'partners'::text
            WHEN ((conversation_analytics.question ~~* '%budget%'::text) OR (conversation_analytics.question ~~* '%cost%'::text)) THEN 'budget'::text
            WHEN (conversation_analytics.question ~~* '%eligibl%'::text) THEN 'eligibility'::text
            WHEN ((conversation_analytics.question ~~* '%deadline%'::text) OR (conversation_analytics.question ~~* '%when%'::text)) THEN 'timing'::text
            WHEN ((conversation_analytics.question ~~* '%horizon%'::text) OR (conversation_analytics.question ~~* '%cluster%'::text)) THEN 'programme_info'::text
            ELSE 'other'::text
        END AS question_category,
    count(*) AS count,
    round((avg(conversation_analytics.confidence))::numeric, 3) AS avg_confidence,
    round(avg(conversation_analytics.response_time_ms), 0) AS avg_response_time_ms
   FROM public.conversation_analytics
  WHERE (conversation_analytics.created_at > (now() - '30 days'::interval))
  GROUP BY
        CASE
            WHEN ((conversation_analytics.question ~~* '%call%'::text) OR (conversation_analytics.question ~~* '%funding%'::text)) THEN 'funding_calls'::text
            WHEN ((conversation_analytics.question ~~* '%project%'::text) OR (conversation_analytics.question ~~* '%cordis%'::text)) THEN 'projects'::text
            WHEN ((conversation_analytics.question ~~* '%partner%'::text) OR (conversation_analytics.question ~~* '%consortium%'::text)) THEN 'partners'::text
            WHEN ((conversation_analytics.question ~~* '%budget%'::text) OR (conversation_analytics.question ~~* '%cost%'::text)) THEN 'budget'::text
            WHEN (conversation_analytics.question ~~* '%eligibl%'::text) THEN 'eligibility'::text
            WHEN ((conversation_analytics.question ~~* '%deadline%'::text) OR (conversation_analytics.question ~~* '%when%'::text)) THEN 'timing'::text
            WHEN ((conversation_analytics.question ~~* '%horizon%'::text) OR (conversation_analytics.question ~~* '%cluster%'::text)) THEN 'programme_info'::text
            ELSE 'other'::text
        END
  ORDER BY (count(*)) DESC;


--
-- Name: v_tool_feedback; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_tool_feedback AS
 SELECT unnest(response_feedback.tools_used) AS tool_name,
    count(*) AS usage_count,
    round(avg(response_feedback.rating), 2) AS avg_rating,
    sum(
        CASE
            WHEN (response_feedback.rating >= 4) THEN 1
            ELSE 0
        END) AS positive_count,
    sum(
        CASE
            WHEN (response_feedback.rating <= 2) THEN 1
            ELSE 0
        END) AS negative_count
   FROM public.response_feedback
  WHERE ((response_feedback.tools_used IS NOT NULL) AND (response_feedback.created_at > (now() - '30 days'::interval)))
  GROUP BY (unnest(response_feedback.tools_used))
  ORDER BY (count(*)) DESC;


--
-- Name: v_tool_performance_24h; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_tool_performance_24h AS
 SELECT tool_usage_analytics.tool_name,
    count(*) AS total_calls,
    sum(
        CASE
            WHEN tool_usage_analytics.success THEN 1
            ELSE 0
        END) AS successful_calls,
    round(avg(tool_usage_analytics.execution_time_ms), 0) AS avg_time_ms,
    round(((((sum(
        CASE
            WHEN tool_usage_analytics.success THEN 1
            ELSE 0
        END))::double precision / (count(*))::double precision) * (100)::double precision))::numeric, 1) AS success_rate_pct
   FROM public.tool_usage_analytics
  WHERE (tool_usage_analytics."timestamp" > (now() - '24:00:00'::interval))
  GROUP BY tool_usage_analytics.tool_name
  ORDER BY (count(*)) DESC;


--
-- Name: v_tool_usage_analytics; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_tool_usage_analytics AS
 SELECT tool_name.tool_name,
    count(*) AS usage_count,
    round((avg(ca.confidence))::numeric, 3) AS avg_confidence_when_used,
    round(avg(ca.response_time_ms), 0) AS avg_response_time_ms
   FROM public.conversation_analytics ca,
    LATERAL unnest(ca.tools_used) tool_name(tool_name)
  WHERE (ca.created_at > (now() - '30 days'::interval))
  GROUP BY tool_name.tool_name
  ORDER BY (count(*)) DESC;


--
-- Name: messages; Type: TABLE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TABLE realtime.messages (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
)
PARTITION BY RANGE (inserted_at);


--
-- Name: messages_2025_11_17; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.messages_2025_11_17 (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: messages_2025_11_18; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.messages_2025_11_18 (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: messages_2025_11_19; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.messages_2025_11_19 (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: messages_2025_11_20; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.messages_2025_11_20 (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: messages_2025_11_21; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.messages_2025_11_21 (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: messages_2025_11_22; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.messages_2025_11_22 (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: schema_migrations; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.schema_migrations (
    version bigint NOT NULL,
    inserted_at timestamp(0) without time zone
);


--
-- Name: subscription; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.subscription (
    id bigint NOT NULL,
    subscription_id uuid NOT NULL,
    entity regclass NOT NULL,
    filters realtime.user_defined_filter[] DEFAULT '{}'::realtime.user_defined_filter[] NOT NULL,
    claims jsonb NOT NULL,
    claims_role regrole GENERATED ALWAYS AS (realtime.to_regrole((claims ->> 'role'::text))) STORED NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


--
-- Name: subscription_id_seq; Type: SEQUENCE; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE realtime.subscription ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME realtime.subscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



--
-- Name: buckets; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.buckets (
    id text NOT NULL,
    name text NOT NULL,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    public boolean DEFAULT false,
    avif_autodetection boolean DEFAULT false,
    file_size_limit bigint,
    allowed_mime_types text[],
    owner_id text
);


--
-- Name: COLUMN buckets.owner; Type: COMMENT; Schema: storage; Owner: supabase_storage_admin
--

COMMENT ON COLUMN storage.buckets.owner IS 'Field is deprecated, use owner_id instead';



--
-- Name: migrations; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.migrations (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    hash character varying(40) NOT NULL,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: objects; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.objects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    bucket_id text,
    name text,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_accessed_at timestamp with time zone DEFAULT now(),
    metadata jsonb,
    path_tokens text[] GENERATED ALWAYS AS (string_to_array(name, '/'::text)) STORED,
    version text,
    owner_id text,
    user_metadata jsonb,
    level integer
);


--
-- Name: COLUMN objects.owner; Type: COMMENT; Schema: storage; Owner: supabase_storage_admin
--

COMMENT ON COLUMN storage.objects.owner IS 'Field is deprecated, use owner_id instead';



--
-- Name: prefixes; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.prefixes (
    bucket_id text NOT NULL,
    name text NOT NULL COLLATE pg_catalog."C",
    level integer GENERATED ALWAYS AS (storage.get_level(name)) STORED NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: s3_multipart_uploads; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.s3_multipart_uploads (
    id text NOT NULL,
    in_progress_size bigint DEFAULT 0 NOT NULL,
    upload_signature text NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    version text NOT NULL,
    owner_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    user_metadata jsonb
);


--
-- Name: s3_multipart_uploads_parts; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.s3_multipart_uploads_parts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_id text NOT NULL,
    size bigint DEFAULT 0 NOT NULL,
    part_number integer NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    etag text NOT NULL,
    owner_id text,
    version text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: hooks; Type: TABLE; Schema: supabase_functions; Owner: supabase_functions_admin
--

CREATE TABLE supabase_functions.hooks (
    id bigint NOT NULL,
    hook_table_id integer NOT NULL,
    hook_name text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    request_id bigint
);


--
-- Name: TABLE hooks; Type: COMMENT; Schema: supabase_functions; Owner: supabase_functions_admin
--

COMMENT ON TABLE supabase_functions.hooks IS 'Supabase Functions Hooks: Audit trail for triggered hooks.';



--
-- Name: hooks_id_seq; Type: SEQUENCE; Schema: supabase_functions; Owner: supabase_functions_admin
--

CREATE SEQUENCE supabase_functions.hooks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hooks_id_seq; Type: SEQUENCE OWNED BY; Schema: supabase_functions; Owner: supabase_functions_admin
--

ALTER SEQUENCE supabase_functions.hooks_id_seq OWNED BY supabase_functions.hooks.id;



--
-- Name: migrations; Type: TABLE; Schema: supabase_functions; Owner: supabase_functions_admin
--

CREATE TABLE supabase_functions.migrations (
    version text NOT NULL,
    inserted_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: decrypted_secrets; Type: VIEW; Schema: vault; Owner: supabase_admin
--

CREATE VIEW vault.decrypted_secrets AS
 SELECT secrets.id,
    secrets.name,
    secrets.description,
    secrets.secret,
        CASE
            WHEN (secrets.secret IS NULL) THEN NULL::text
            ELSE
            CASE
                WHEN (secrets.key_id IS NULL) THEN NULL::text
                ELSE convert_from(pgsodium.crypto_aead_det_decrypt(decode(secrets.secret, 'base64'::text), convert_to(((((secrets.id)::text || secrets.description) || (secrets.created_at)::text) || (secrets.updated_at)::text), 'utf8'::name), secrets.key_id, secrets.nonce), 'utf8'::name)
            END
        END AS decrypted_secret,
    secrets.key_id,
    secrets.nonce,
    secrets.created_at,
    secrets.updated_at
   FROM vault.secrets;


--
-- Name: messages_2025_11_17; Type: TABLE ATTACH; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages ATTACH PARTITION realtime.messages_2025_11_17 FOR VALUES FROM ('2025-11-17 00:00:00') TO ('2025-11-18 00:00:00');



--
-- Name: messages_2025_11_18; Type: TABLE ATTACH; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages ATTACH PARTITION realtime.messages_2025_11_18 FOR VALUES FROM ('2025-11-18 00:00:00') TO ('2025-11-19 00:00:00');



--
-- Name: messages_2025_11_19; Type: TABLE ATTACH; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages ATTACH PARTITION realtime.messages_2025_11_19 FOR VALUES FROM ('2025-11-19 00:00:00') TO ('2025-11-20 00:00:00');



--
-- Name: messages_2025_11_20; Type: TABLE ATTACH; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages ATTACH PARTITION realtime.messages_2025_11_20 FOR VALUES FROM ('2025-11-20 00:00:00') TO ('2025-11-21 00:00:00');



--
-- Name: messages_2025_11_21; Type: TABLE ATTACH; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages ATTACH PARTITION realtime.messages_2025_11_21 FOR VALUES FROM ('2025-11-21 00:00:00') TO ('2025-11-22 00:00:00');



--
-- Name: messages_2025_11_22; Type: TABLE ATTACH; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages ATTACH PARTITION realtime.messages_2025_11_22 FOR VALUES FROM ('2025-11-22 00:00:00') TO ('2025-11-23 00:00:00');



--
-- Name: refresh_tokens id; Type: DEFAULT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens ALTER COLUMN id SET DEFAULT nextval('auth.refresh_tokens_id_seq'::regclass);



--
-- Name: __drizzle_migrations id; Type: DEFAULT; Schema: drizzle; Owner: postgres
--

ALTER TABLE ONLY drizzle.__drizzle_migrations ALTER COLUMN id SET DEFAULT nextval('drizzle.__drizzle_migrations_id_seq'::regclass);



--
-- Name: call_document_mappings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.call_document_mappings ALTER COLUMN id SET DEFAULT nextval('public.call_document_mappings_id_seq'::regclass);



--
-- Name: call_metadata id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.call_metadata ALTER COLUMN id SET DEFAULT nextval('public.call_metadata_id_seq'::regclass);



--
-- Name: citations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citations ALTER COLUMN id SET DEFAULT nextval('public.citations_id_seq'::regclass);



--
-- Name: client id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client ALTER COLUMN id SET DEFAULT nextval('public.client_id_seq'::regclass);



--
-- Name: client_collaboration id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_collaboration ALTER COLUMN id SET DEFAULT nextval('public.client_collaboration_id_seq'::regclass);



--
-- Name: collaboration id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.collaboration ALTER COLUMN id SET DEFAULT nextval('public.collaboration_id_seq'::regclass);



--
-- Name: compliance_checks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.compliance_checks ALTER COLUMN id SET DEFAULT nextval('public.compliance_checks_id_seq'::regclass);



--
-- Name: conversation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation ALTER COLUMN id SET DEFAULT nextval('public.conversation_id_seq'::regclass);



--
-- Name: conversation_analytics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_analytics ALTER COLUMN id SET DEFAULT nextval('public.conversation_analytics_id_seq'::regclass);



--
-- Name: conversation_facts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_facts ALTER COLUMN id SET DEFAULT nextval('public.conversation_facts_id_seq'::regclass);



--
-- Name: conversation_memory id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_memory ALTER COLUMN id SET DEFAULT nextval('public.conversation_memory_id_seq'::regclass);



--
-- Name: entity_cards id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entity_cards ALTER COLUMN id SET DEFAULT nextval('public.entity_cards_id_seq'::regclass);



--
-- Name: improvement_suggestions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.improvement_suggestions ALTER COLUMN id SET DEFAULT nextval('public.improvement_suggestions_id_seq'::regclass);



--
-- Name: message id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message ALTER COLUMN id SET DEFAULT nextval('public.message_id_seq'::regclass);



--
-- Name: proposal_activity_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_activity_log ALTER COLUMN id SET DEFAULT nextval('public.proposal_activity_log_id_seq'::regclass);



--
-- Name: proposal_budgets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_budgets ALTER COLUMN id SET DEFAULT nextval('public.proposal_budgets_id_seq'::regclass);



--
-- Name: proposal_consortium id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_consortium ALTER COLUMN id SET DEFAULT nextval('public.proposal_consortium_id_seq'::regclass);



--
-- Name: proposal_examples id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_examples ALTER COLUMN id SET DEFAULT nextval('public.proposal_examples_id_seq'::regclass);



--
-- Name: proposal_sections id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sections ALTER COLUMN id SET DEFAULT nextval('public.proposal_sections_id_seq'::regclass);



--
-- Name: proposal_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sessions ALTER COLUMN id SET DEFAULT nextval('public.proposal_sessions_id_seq'::regclass);



--
-- Name: proposals id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposals ALTER COLUMN id SET DEFAULT nextval('public.proposals_id_seq'::regclass);



--
-- Name: response_feedback id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_feedback ALTER COLUMN id SET DEFAULT nextval('public.response_feedback_id_seq'::regclass);



--
-- Name: section_criteria_mapping id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section_criteria_mapping ALTER COLUMN id SET DEFAULT nextval('public.section_criteria_mapping_id_seq'::regclass);



--
-- Name: shared_document_chunks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_document_chunks ALTER COLUMN id SET DEFAULT nextval('public.shared_document_chunks_id_seq'::regclass);



--
-- Name: shared_documents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_documents ALTER COLUMN id SET DEFAULT nextval('public.shared_documents_id_seq'::regclass);



--
-- Name: tool_combination_analytics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_combination_analytics ALTER COLUMN id SET DEFAULT nextval('public.tool_combination_analytics_id_seq'::regclass);



--
-- Name: tool_usage_analytics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_usage_analytics ALTER COLUMN id SET DEFAULT nextval('public.tool_usage_analytics_id_seq'::regclass);



--
-- Name: hooks id; Type: DEFAULT; Schema: supabase_functions; Owner: supabase_functions_admin
--

ALTER TABLE ONLY supabase_functions.hooks ALTER COLUMN id SET DEFAULT nextval('supabase_functions.hooks_id_seq'::regclass);



--
-- Name: extensions extensions_pkey; Type: CONSTRAINT; Schema: _realtime; Owner: supabase_admin
--

ALTER TABLE ONLY _realtime.extensions
    ADD CONSTRAINT extensions_pkey PRIMARY KEY (id);



--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: _realtime; Owner: supabase_admin
--

ALTER TABLE ONLY _realtime.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);



--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: _realtime; Owner: supabase_admin
--

ALTER TABLE ONLY _realtime.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);



--
-- Name: mfa_amr_claims amr_id_pk; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT amr_id_pk PRIMARY KEY (id);



--
-- Name: audit_log_entries audit_log_entries_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.audit_log_entries
    ADD CONSTRAINT audit_log_entries_pkey PRIMARY KEY (id);



--
-- Name: flow_state flow_state_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.flow_state
    ADD CONSTRAINT flow_state_pkey PRIMARY KEY (id);



--
-- Name: identities identities_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);



--
-- Name: identities identities_provider_id_provider_unique; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_provider_id_provider_unique UNIQUE (provider_id, provider);



--
-- Name: instances instances_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.instances
    ADD CONSTRAINT instances_pkey PRIMARY KEY (id);



--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_authentication_method_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_authentication_method_pkey UNIQUE (session_id, authentication_method);



--
-- Name: mfa_challenges mfa_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_pkey PRIMARY KEY (id);



--
-- Name: mfa_factors mfa_factors_last_challenged_at_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_last_challenged_at_key UNIQUE (last_challenged_at);



--
-- Name: mfa_factors mfa_factors_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_pkey PRIMARY KEY (id);



--
-- Name: one_time_tokens one_time_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_pkey PRIMARY KEY (id);



--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);



--
-- Name: refresh_tokens refresh_tokens_token_unique; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_unique UNIQUE (token);



--
-- Name: saml_providers saml_providers_entity_id_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_entity_id_key UNIQUE (entity_id);



--
-- Name: saml_providers saml_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_pkey PRIMARY KEY (id);



--
-- Name: saml_relay_states saml_relay_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_pkey PRIMARY KEY (id);



--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);



--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);



--
-- Name: sso_domains sso_domains_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_pkey PRIMARY KEY (id);



--
-- Name: sso_providers sso_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sso_providers
    ADD CONSTRAINT sso_providers_pkey PRIMARY KEY (id);



--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);



--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);



--
-- Name: __drizzle_migrations __drizzle_migrations_pkey; Type: CONSTRAINT; Schema: drizzle; Owner: postgres
--

ALTER TABLE ONLY drizzle.__drizzle_migrations
    ADD CONSTRAINT __drizzle_migrations_pkey PRIMARY KEY (id);



--
-- Name: call_document_mappings call_document_mappings_call_identifier_document_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.call_document_mappings
    ADD CONSTRAINT call_document_mappings_call_identifier_document_id_key UNIQUE (call_identifier, document_id);



--
-- Name: call_document_mappings call_document_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.call_document_mappings
    ADD CONSTRAINT call_document_mappings_pkey PRIMARY KEY (id);



--
-- Name: call_metadata call_metadata_call_identifier_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.call_metadata
    ADD CONSTRAINT call_metadata_call_identifier_key UNIQUE (call_identifier);



--
-- Name: call_metadata call_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.call_metadata
    ADD CONSTRAINT call_metadata_pkey PRIMARY KEY (id);



--
-- Name: citations citations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citations
    ADD CONSTRAINT citations_pkey PRIMARY KEY (id);



--
-- Name: client client_auth_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_auth_id_key UNIQUE (auth_id);



--
-- Name: client_collaboration client_collaboration_collaboration_id_client_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_collaboration
    ADD CONSTRAINT client_collaboration_collaboration_id_client_id_key UNIQUE (collaboration_id, client_id);



--
-- Name: client_collaboration client_collaboration_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_collaboration
    ADD CONSTRAINT client_collaboration_pkey PRIMARY KEY (id);



--
-- Name: client client_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_email_key UNIQUE (email);



--
-- Name: client client_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_pkey PRIMARY KEY (id);



--
-- Name: collaboration collaboration_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.collaboration
    ADD CONSTRAINT collaboration_pkey PRIMARY KEY (id);



--
-- Name: compliance_checks compliance_checks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.compliance_checks
    ADD CONSTRAINT compliance_checks_pkey PRIMARY KEY (id);



--
-- Name: conversation_analytics conversation_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_analytics
    ADD CONSTRAINT conversation_analytics_pkey PRIMARY KEY (id);



--
-- Name: conversation_facts conversation_facts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_facts
    ADD CONSTRAINT conversation_facts_pkey PRIMARY KEY (id);



--
-- Name: conversation_memory conversation_memory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_memory
    ADD CONSTRAINT conversation_memory_pkey PRIMARY KEY (id);



--
-- Name: conversation conversation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation
    ADD CONSTRAINT conversation_pkey PRIMARY KEY (id);



--
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);



--
-- Name: embedding_cache embedding_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.embedding_cache
    ADD CONSTRAINT embedding_cache_pkey PRIMARY KEY (id);



--
-- Name: embedding_cache embedding_cache_text_hash_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.embedding_cache
    ADD CONSTRAINT embedding_cache_text_hash_key UNIQUE (text_hash);



--
-- Name: entity_cards entity_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entity_cards
    ADD CONSTRAINT entity_cards_pkey PRIMARY KEY (id);



--
-- Name: entity_cards entity_cards_unique_entity; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entity_cards
    ADD CONSTRAINT entity_cards_unique_entity UNIQUE (conversation_id, entity_type, entity_name);



--
-- Name: funding_calls funding_calls_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.funding_calls
    ADD CONSTRAINT funding_calls_pkey PRIMARY KEY (id);



--
-- Name: funding_calls funding_calls_topic_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.funding_calls
    ADD CONSTRAINT funding_calls_topic_code_key UNIQUE (topic_code);



--
-- Name: horizon_documents horizon_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.horizon_documents
    ADD CONSTRAINT horizon_documents_pkey PRIMARY KEY (id);



--
-- Name: improvement_suggestions improvement_suggestions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.improvement_suggestions
    ADD CONSTRAINT improvement_suggestions_pkey PRIMARY KEY (id);



--
-- Name: message message_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);



--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);



--
-- Name: project_embeddings project_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_embeddings
    ADD CONSTRAINT project_embeddings_pkey PRIMARY KEY (project_id);



--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);



--
-- Name: proposal_activity_log proposal_activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_activity_log
    ADD CONSTRAINT proposal_activity_log_pkey PRIMARY KEY (id);



--
-- Name: proposal_budgets proposal_budgets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_budgets
    ADD CONSTRAINT proposal_budgets_pkey PRIMARY KEY (id);



--
-- Name: proposal_consortium proposal_consortium_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_consortium
    ADD CONSTRAINT proposal_consortium_pkey PRIMARY KEY (id);



--
-- Name: proposal_examples proposal_examples_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_examples
    ADD CONSTRAINT proposal_examples_pkey PRIMARY KEY (id);



--
-- Name: proposal_sections proposal_sections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sections
    ADD CONSTRAINT proposal_sections_pkey PRIMARY KEY (id);



--
-- Name: proposal_sections proposal_sections_proposal_id_section_id_version_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sections
    ADD CONSTRAINT proposal_sections_proposal_id_section_id_version_key UNIQUE (proposal_id, section_id, version);



--
-- Name: proposal_sessions proposal_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sessions
    ADD CONSTRAINT proposal_sessions_pkey PRIMARY KEY (id);



--
-- Name: proposal_sessions proposal_sessions_session_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sessions
    ADD CONSTRAINT proposal_sessions_session_id_key UNIQUE (session_id);



--
-- Name: proposals proposals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposals
    ADD CONSTRAINT proposals_pkey PRIMARY KEY (id);



--
-- Name: response_feedback response_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_feedback
    ADD CONSTRAINT response_feedback_pkey PRIMARY KEY (id);



--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);



--
-- Name: section_criteria_mapping section_criteria_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section_criteria_mapping
    ADD CONSTRAINT section_criteria_mapping_pkey PRIMARY KEY (id);



--
-- Name: section_criteria_mapping section_criteria_mapping_section_id_criterion_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section_criteria_mapping
    ADD CONSTRAINT section_criteria_mapping_section_id_criterion_name_key UNIQUE (section_id, criterion_name);



--
-- Name: shared_document_chunks shared_document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_document_chunks
    ADD CONSTRAINT shared_document_chunks_pkey PRIMARY KEY (id);



--
-- Name: shared_documents shared_documents_document_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_documents
    ADD CONSTRAINT shared_documents_document_key_key UNIQUE (document_key);



--
-- Name: shared_documents shared_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_documents
    ADD CONSTRAINT shared_documents_pkey PRIMARY KEY (id);



--
-- Name: tool_combination_analytics tool_combination_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_combination_analytics
    ADD CONSTRAINT tool_combination_analytics_pkey PRIMARY KEY (id);



--
-- Name: tool_combination_analytics tool_combination_analytics_tool_sequence_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_combination_analytics
    ADD CONSTRAINT tool_combination_analytics_tool_sequence_key UNIQUE (tool_sequence);



--
-- Name: tool_usage_analytics tool_usage_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tool_usage_analytics
    ADD CONSTRAINT tool_usage_analytics_pkey PRIMARY KEY (id);



--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE ONLY realtime.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id, inserted_at);



--
-- Name: messages_2025_11_17 messages_2025_11_17_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages_2025_11_17
    ADD CONSTRAINT messages_2025_11_17_pkey PRIMARY KEY (id, inserted_at);



--
-- Name: messages_2025_11_18 messages_2025_11_18_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages_2025_11_18
    ADD CONSTRAINT messages_2025_11_18_pkey PRIMARY KEY (id, inserted_at);



--
-- Name: messages_2025_11_19 messages_2025_11_19_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages_2025_11_19
    ADD CONSTRAINT messages_2025_11_19_pkey PRIMARY KEY (id, inserted_at);



--
-- Name: messages_2025_11_20 messages_2025_11_20_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages_2025_11_20
    ADD CONSTRAINT messages_2025_11_20_pkey PRIMARY KEY (id, inserted_at);



--
-- Name: messages_2025_11_21 messages_2025_11_21_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages_2025_11_21
    ADD CONSTRAINT messages_2025_11_21_pkey PRIMARY KEY (id, inserted_at);



--
-- Name: messages_2025_11_22 messages_2025_11_22_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.messages_2025_11_22
    ADD CONSTRAINT messages_2025_11_22_pkey PRIMARY KEY (id, inserted_at);



--
-- Name: subscription pk_subscription; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.subscription
    ADD CONSTRAINT pk_subscription PRIMARY KEY (id);



--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);



--
-- Name: buckets buckets_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.buckets
    ADD CONSTRAINT buckets_pkey PRIMARY KEY (id);



--
-- Name: migrations migrations_name_key; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_name_key UNIQUE (name);



--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (id);



--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);



--
-- Name: prefixes prefixes_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.prefixes
    ADD CONSTRAINT prefixes_pkey PRIMARY KEY (bucket_id, level, name);



--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_pkey PRIMARY KEY (id);



--
-- Name: s3_multipart_uploads s3_multipart_uploads_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_pkey PRIMARY KEY (id);



--
-- Name: hooks hooks_pkey; Type: CONSTRAINT; Schema: supabase_functions; Owner: supabase_functions_admin
--

ALTER TABLE ONLY supabase_functions.hooks
    ADD CONSTRAINT hooks_pkey PRIMARY KEY (id);



--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: supabase_functions; Owner: supabase_functions_admin
--

ALTER TABLE ONLY supabase_functions.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (version);



--
-- Name: extensions_tenant_external_id_index; Type: INDEX; Schema: _realtime; Owner: supabase_admin
--

CREATE INDEX extensions_tenant_external_id_index ON _realtime.extensions USING btree (tenant_external_id);



--
-- Name: extensions_tenant_external_id_type_index; Type: INDEX; Schema: _realtime; Owner: supabase_admin
--

CREATE UNIQUE INDEX extensions_tenant_external_id_type_index ON _realtime.extensions USING btree (tenant_external_id, type);



--
-- Name: tenants_external_id_index; Type: INDEX; Schema: _realtime; Owner: supabase_admin
--

CREATE UNIQUE INDEX tenants_external_id_index ON _realtime.tenants USING btree (external_id);



--
-- Name: audit_logs_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX audit_logs_instance_id_idx ON auth.audit_log_entries USING btree (instance_id);



--
-- Name: confirmation_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX confirmation_token_idx ON auth.users USING btree (confirmation_token) WHERE ((confirmation_token)::text !~ '^[0-9 ]*$'::text);



--
-- Name: email_change_token_current_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX email_change_token_current_idx ON auth.users USING btree (email_change_token_current) WHERE ((email_change_token_current)::text !~ '^[0-9 ]*$'::text);



--
-- Name: email_change_token_new_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX email_change_token_new_idx ON auth.users USING btree (email_change_token_new) WHERE ((email_change_token_new)::text !~ '^[0-9 ]*$'::text);



--
-- Name: factor_id_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX factor_id_created_at_idx ON auth.mfa_factors USING btree (user_id, created_at);



--
-- Name: flow_state_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX flow_state_created_at_idx ON auth.flow_state USING btree (created_at DESC);



--
-- Name: identities_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX identities_email_idx ON auth.identities USING btree (email text_pattern_ops);



--
-- Name: INDEX identities_email_idx; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON INDEX auth.identities_email_idx IS 'Auth: Ensures indexed queries on the email column';



--
-- Name: identities_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX identities_user_id_idx ON auth.identities USING btree (user_id);



--
-- Name: idx_auth_code; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX idx_auth_code ON auth.flow_state USING btree (auth_code);



--
-- Name: idx_user_id_auth_method; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX idx_user_id_auth_method ON auth.flow_state USING btree (user_id, authentication_method);



--
-- Name: mfa_challenge_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX mfa_challenge_created_at_idx ON auth.mfa_challenges USING btree (created_at DESC);



--
-- Name: mfa_factors_user_friendly_name_unique; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX mfa_factors_user_friendly_name_unique ON auth.mfa_factors USING btree (friendly_name, user_id) WHERE (TRIM(BOTH FROM friendly_name) <> ''::text);



--
-- Name: mfa_factors_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX mfa_factors_user_id_idx ON auth.mfa_factors USING btree (user_id);



--
-- Name: one_time_tokens_relates_to_hash_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX one_time_tokens_relates_to_hash_idx ON auth.one_time_tokens USING hash (relates_to);



--
-- Name: one_time_tokens_token_hash_hash_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX one_time_tokens_token_hash_hash_idx ON auth.one_time_tokens USING hash (token_hash);



--
-- Name: one_time_tokens_user_id_token_type_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX one_time_tokens_user_id_token_type_key ON auth.one_time_tokens USING btree (user_id, token_type);



--
-- Name: reauthentication_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX reauthentication_token_idx ON auth.users USING btree (reauthentication_token) WHERE ((reauthentication_token)::text !~ '^[0-9 ]*$'::text);



--
-- Name: recovery_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX recovery_token_idx ON auth.users USING btree (recovery_token) WHERE ((recovery_token)::text !~ '^[0-9 ]*$'::text);



--
-- Name: refresh_tokens_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_instance_id_idx ON auth.refresh_tokens USING btree (instance_id);



--
-- Name: refresh_tokens_instance_id_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_instance_id_user_id_idx ON auth.refresh_tokens USING btree (instance_id, user_id);



--
-- Name: refresh_tokens_parent_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_parent_idx ON auth.refresh_tokens USING btree (parent);



--
-- Name: refresh_tokens_session_id_revoked_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_session_id_revoked_idx ON auth.refresh_tokens USING btree (session_id, revoked);



--
-- Name: refresh_tokens_updated_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_updated_at_idx ON auth.refresh_tokens USING btree (updated_at DESC);



--
-- Name: saml_providers_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_providers_sso_provider_id_idx ON auth.saml_providers USING btree (sso_provider_id);



--
-- Name: saml_relay_states_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_relay_states_created_at_idx ON auth.saml_relay_states USING btree (created_at DESC);



--
-- Name: saml_relay_states_for_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_relay_states_for_email_idx ON auth.saml_relay_states USING btree (for_email);



--
-- Name: saml_relay_states_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_relay_states_sso_provider_id_idx ON auth.saml_relay_states USING btree (sso_provider_id);



--
-- Name: sessions_not_after_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX sessions_not_after_idx ON auth.sessions USING btree (not_after DESC);



--
-- Name: sessions_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX sessions_user_id_idx ON auth.sessions USING btree (user_id);



--
-- Name: sso_domains_domain_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX sso_domains_domain_idx ON auth.sso_domains USING btree (lower(domain));



--
-- Name: sso_domains_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX sso_domains_sso_provider_id_idx ON auth.sso_domains USING btree (sso_provider_id);



--
-- Name: sso_providers_resource_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX sso_providers_resource_id_idx ON auth.sso_providers USING btree (lower(resource_id));



--
-- Name: unique_phone_factor_per_user; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX unique_phone_factor_per_user ON auth.mfa_factors USING btree (user_id, phone);



--
-- Name: user_id_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX user_id_created_at_idx ON auth.sessions USING btree (user_id, created_at);



--
-- Name: users_email_partial_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX users_email_partial_key ON auth.users USING btree (email) WHERE (is_sso_user = false);



--
-- Name: INDEX users_email_partial_key; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON INDEX auth.users_email_partial_key IS 'Auth: A partial unique index that applies only when is_sso_user is false';



--
-- Name: users_instance_id_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX users_instance_id_email_idx ON auth.users USING btree (instance_id, lower((email)::text));



--
-- Name: users_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX users_instance_id_idx ON auth.users USING btree (instance_id);



--
-- Name: users_is_anonymous_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX users_is_anonymous_idx ON auth.users USING btree (is_anonymous);



--
-- Name: idx_activity_proposal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_activity_proposal ON public.proposal_activity_log USING btree (proposal_id);



--
-- Name: idx_activity_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_activity_timestamp ON public.proposal_activity_log USING btree (created_at DESC);



--
-- Name: idx_activity_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_activity_type ON public.proposal_activity_log USING btree (activity_type);



--
-- Name: idx_budgets_proposal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_budgets_proposal ON public.proposal_budgets USING btree (proposal_id);



--
-- Name: idx_call_doc_map_call; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_call_doc_map_call ON public.call_document_mappings USING btree (call_identifier);



--
-- Name: idx_call_doc_map_doc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_call_doc_map_doc ON public.call_document_mappings USING btree (document_id);



--
-- Name: idx_call_doc_map_primary; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_call_doc_map_primary ON public.call_document_mappings USING btree (call_identifier, is_primary);



--
-- Name: idx_call_metadata_deadline; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_call_metadata_deadline ON public.call_metadata USING btree (deadline_date);



--
-- Name: idx_call_metadata_identifier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_call_metadata_identifier ON public.call_metadata USING btree (call_identifier);



--
-- Name: idx_call_metadata_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_call_metadata_search ON public.call_metadata USING gin (to_tsvector('english'::regconfig, ((title || ' '::text) || COALESCE(summary, ''::text))));



--
-- Name: idx_call_metadata_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_call_metadata_status ON public.call_metadata USING btree (status);



--
-- Name: idx_chunks_chunk_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chunks_chunk_index ON public.document_chunks USING btree (document_id, chunk_index);



--
-- Name: idx_chunks_content_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chunks_content_gin ON public.document_chunks USING gin (content_tokens);



--
-- Name: idx_chunks_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chunks_document_id ON public.document_chunks USING btree (document_id);



--
-- Name: idx_chunks_embedding_cosine; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chunks_embedding_cosine ON public.document_chunks USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');



--
-- Name: idx_citations_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_citations_conversation ON public.citations USING btree (conversation_id);



--
-- Name: idx_citations_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_citations_key ON public.citations USING btree (citation_key);



--
-- Name: idx_citations_message; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_citations_message ON public.citations USING btree (message_id);



--
-- Name: idx_citations_relevance; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_citations_relevance ON public.citations USING btree (relevance_score DESC);



--
-- Name: idx_citations_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_citations_type ON public.citations USING btree (citation_type);



--
-- Name: idx_citations_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_citations_unique ON public.citations USING btree (conversation_id, message_id, citation_key, position_in_response);



--
-- Name: idx_client_auth_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_client_auth_id ON public.client USING btree (auth_id);



--
-- Name: idx_compliance_checked; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_compliance_checked ON public.compliance_checks USING btree (checked_at DESC);



--
-- Name: idx_compliance_proposal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_compliance_proposal ON public.compliance_checks USING btree (proposal_id);



--
-- Name: idx_compliance_result; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_compliance_result ON public.compliance_checks USING btree (check_result);



--
-- Name: idx_consortium_coordinator; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_consortium_coordinator ON public.proposal_consortium USING btree (is_coordinator) WHERE (is_coordinator = true);



--
-- Name: idx_consortium_proposal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_consortium_proposal ON public.proposal_consortium USING btree (proposal_id);



--
-- Name: idx_conv_analytics_confidence; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_confidence ON public.conversation_analytics USING btree (confidence);



--
-- Name: idx_conv_analytics_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_conversation ON public.conversation_analytics USING btree (conversation_id);



--
-- Name: idx_conv_analytics_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_created ON public.conversation_analytics USING btree (created_at);



--
-- Name: idx_conv_analytics_metadata; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_metadata ON public.conversation_analytics USING gin (metadata);



--
-- Name: idx_conv_analytics_question_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_question_search ON public.conversation_analytics USING gin (to_tsvector('english'::regconfig, question));



--
-- Name: idx_conv_analytics_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_status ON public.conversation_analytics USING btree (status);



--
-- Name: idx_conv_analytics_tools; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_tools ON public.conversation_analytics USING gin (tools_used);



--
-- Name: idx_conv_analytics_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conv_analytics_user ON public.conversation_analytics USING btree (user_id);



--
-- Name: idx_conversation_memory_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversation_memory_type ON public.conversation_memory USING btree (conversation_id, memory_type);



--
-- Name: idx_criteria_addressed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_criteria_addressed ON public.section_criteria_mapping USING btree (addressed);



--
-- Name: idx_criteria_section; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_criteria_section ON public.section_criteria_mapping USING btree (section_id);



--
-- Name: idx_documents_active_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_active_type ON public.horizon_documents USING btree (status, document_type) WHERE (status = 'active'::text);



--
-- Name: idx_documents_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_created ON public.horizon_documents USING btree (created_at DESC);



--
-- Name: idx_documents_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_status ON public.horizon_documents USING btree (status);



--
-- Name: idx_documents_title_trgm; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_title_trgm ON public.horizon_documents USING gin (title public.gin_trgm_ops);



--
-- Name: idx_documents_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_type ON public.horizon_documents USING btree (document_type);



--
-- Name: idx_documents_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_year ON public.horizon_documents USING btree (programme_year);



--
-- Name: idx_entity_cards_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_entity_cards_conversation ON public.entity_cards USING btree (conversation_id, entity_type);



--
-- Name: idx_examples_call; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_examples_call ON public.proposal_examples USING btree (call_identifier);



--
-- Name: idx_examples_score; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_examples_score ON public.proposal_examples USING btree (evaluation_score DESC);



--
-- Name: idx_examples_section; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_examples_section ON public.proposal_examples USING btree (section_id);



--
-- Name: idx_examples_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_examples_tags ON public.proposal_examples USING gin (tags);



--
-- Name: idx_facts_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_facts_conversation ON public.conversation_facts USING btree (conversation_id);



--
-- Name: idx_feedback_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feedback_conversation ON public.response_feedback USING btree (conversation_id);



--
-- Name: idx_feedback_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feedback_created ON public.response_feedback USING btree (created_at);



--
-- Name: idx_feedback_rating; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feedback_rating ON public.response_feedback USING btree (rating);



--
-- Name: idx_feedback_tools; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feedback_tools ON public.response_feedback USING gin (tools_used);



--
-- Name: idx_feedback_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_feedback_type ON public.response_feedback USING btree (feedback_type);



--
-- Name: idx_funding_calls_action_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_action_type ON public.funding_calls USING btree (action_type);



--
-- Name: idx_funding_calls_call_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_call_year ON public.funding_calls USING btree (call_year);



--
-- Name: idx_funding_calls_cluster; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_cluster ON public.funding_calls USING btree (cluster);



--
-- Name: idx_funding_calls_deadline; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_deadline ON public.funding_calls USING btree (deadline);



--
-- Name: idx_funding_calls_embedding; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_embedding ON public.funding_calls USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');



--
-- Name: idx_funding_calls_fts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_fts ON public.funding_calls USING gin (to_tsvector('english'::regconfig, ((((COALESCE(title, ''::text) || ' '::text) || COALESCE(scope, ''::text)) || ' '::text) || COALESCE(expected_outcome, ''::text))));



--
-- Name: idx_funding_calls_metadata; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_metadata ON public.funding_calls USING gin (metadata);



--
-- Name: idx_funding_calls_programme; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_programme ON public.funding_calls USING btree (programme);



--
-- Name: idx_funding_calls_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_status ON public.funding_calls USING btree (status);



--
-- Name: idx_funding_calls_tags; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_tags ON public.funding_calls USING gin (tags);



--
-- Name: idx_funding_calls_topic_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_funding_calls_topic_code ON public.funding_calls USING btree (topic_code);



--
-- Name: idx_message_citations; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_citations ON public.message USING gin (citations);



--
-- Name: idx_project_embeddings_model; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_embeddings_model ON public.project_embeddings USING btree (model_version);



--
-- Name: idx_project_embeddings_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_embeddings_project_id ON public.project_embeddings USING btree (project_id);



--
-- Name: idx_project_embeddings_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_embeddings_status ON public.project_embeddings USING btree (embedding_status);



--
-- Name: idx_proposals_call; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_proposals_call ON public.proposals USING btree (call_identifier);



--
-- Name: idx_proposals_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_proposals_conversation ON public.proposals USING btree (conversation_id);



--
-- Name: idx_proposals_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_proposals_status ON public.proposals USING btree (status);



--
-- Name: idx_proposals_updated; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_proposals_updated ON public.proposals USING btree (updated_at DESC);



--
-- Name: idx_proposals_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_proposals_user ON public.proposals USING btree (user_id);



--
-- Name: idx_sections_current; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sections_current ON public.proposal_sections USING btree (proposal_id, is_current) WHERE (is_current = true);



--
-- Name: idx_sections_proposal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sections_proposal ON public.proposal_sections USING btree (proposal_id);



--
-- Name: idx_sections_section_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sections_section_id ON public.proposal_sections USING btree (section_id);



--
-- Name: idx_sessions_activity; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_activity ON public.proposal_sessions USING btree (last_activity_at DESC);



--
-- Name: idx_sessions_proposal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_proposal ON public.proposal_sessions USING btree (proposal_id);



--
-- Name: idx_sessions_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_session_id ON public.proposal_sessions USING btree (session_id);



--
-- Name: idx_sessions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_status ON public.proposal_sessions USING btree (status);



--
-- Name: idx_sessions_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_user ON public.proposal_sessions USING btree (user_id);



--
-- Name: idx_sessions_user_proposal_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_user_proposal_active ON public.proposal_sessions USING btree (user_id, proposal_id) WHERE ((status)::text = 'active'::text);



--
-- Name: idx_shared_chunks_doc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_shared_chunks_doc ON public.shared_document_chunks USING btree (document_id);



--
-- Name: idx_shared_chunks_section; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_shared_chunks_section ON public.shared_document_chunks USING btree (section_title);



--
-- Name: idx_shared_chunks_text_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_shared_chunks_text_search ON public.shared_document_chunks USING gin (to_tsvector('english'::regconfig, chunk_text));



--
-- Name: idx_shared_docs_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_shared_docs_hash ON public.shared_documents USING btree (file_hash);



--
-- Name: idx_shared_docs_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_shared_docs_key ON public.shared_documents USING btree (document_key);



--
-- Name: idx_shared_docs_scope; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_shared_docs_scope ON public.shared_documents USING btree (scope, scope_identifier);



--
-- Name: idx_shared_docs_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_shared_docs_type ON public.shared_documents USING btree (document_type);



--
-- Name: idx_suggestions_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestions_priority ON public.improvement_suggestions USING btree (priority);



--
-- Name: idx_suggestions_proposal; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestions_proposal ON public.improvement_suggestions USING btree (proposal_id);



--
-- Name: idx_suggestions_section; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestions_section ON public.improvement_suggestions USING btree (section_id);



--
-- Name: idx_suggestions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suggestions_status ON public.improvement_suggestions USING btree (status);



--
-- Name: idx_tool_combo_sequence; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tool_combo_sequence ON public.tool_combination_analytics USING gin (tool_sequence);



--
-- Name: idx_tool_usage_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tool_usage_conversation ON public.tool_usage_analytics USING btree (conversation_id);



--
-- Name: idx_tool_usage_success; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tool_usage_success ON public.tool_usage_analytics USING btree (success);



--
-- Name: idx_tool_usage_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tool_usage_timestamp ON public.tool_usage_analytics USING btree ("timestamp");



--
-- Name: idx_tool_usage_tool_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tool_usage_tool_name ON public.tool_usage_analytics USING btree (tool_name);



--
-- Name: ix_realtime_subscription_entity; Type: INDEX; Schema: realtime; Owner: supabase_admin
--

CREATE INDEX ix_realtime_subscription_entity ON realtime.subscription USING btree (entity);



--
-- Name: subscription_subscription_id_entity_filters_key; Type: INDEX; Schema: realtime; Owner: supabase_admin
--

CREATE UNIQUE INDEX subscription_subscription_id_entity_filters_key ON realtime.subscription USING btree (subscription_id, entity, filters);



--
-- Name: bname; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX bname ON storage.buckets USING btree (name);



--
-- Name: bucketid_objname; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX bucketid_objname ON storage.objects USING btree (bucket_id, name);



--
-- Name: idx_multipart_uploads_list; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX idx_multipart_uploads_list ON storage.s3_multipart_uploads USING btree (bucket_id, key, created_at);



--
-- Name: idx_name_bucket_unique; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX idx_name_bucket_unique ON storage.objects USING btree (name COLLATE "C", bucket_id);



--
-- Name: idx_objects_bucket_id_name; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX idx_objects_bucket_id_name ON storage.objects USING btree (bucket_id, name COLLATE "C");



--
-- Name: idx_objects_lower_name; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX idx_objects_lower_name ON storage.objects USING btree ((path_tokens[level]), lower(name) text_pattern_ops, bucket_id, level);



--
-- Name: idx_prefixes_lower_name; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX idx_prefixes_lower_name ON storage.prefixes USING btree (bucket_id, level, ((string_to_array(name, '/'::text))[level]), lower(name) text_pattern_ops);



--
-- Name: name_prefix_search; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX name_prefix_search ON storage.objects USING btree (name text_pattern_ops);



--
-- Name: objects_bucket_id_level_idx; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX objects_bucket_id_level_idx ON storage.objects USING btree (bucket_id, level, name COLLATE "C");



--
-- Name: supabase_functions_hooks_h_table_id_h_name_idx; Type: INDEX; Schema: supabase_functions; Owner: supabase_functions_admin
--

CREATE INDEX supabase_functions_hooks_h_table_id_h_name_idx ON supabase_functions.hooks USING btree (hook_table_id, hook_name);



--
-- Name: supabase_functions_hooks_request_id_idx; Type: INDEX; Schema: supabase_functions; Owner: supabase_functions_admin
--

CREATE INDEX supabase_functions_hooks_request_id_idx ON supabase_functions.hooks USING btree (request_id);



--
-- Name: messages_2025_11_17_pkey; Type: INDEX ATTACH; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER INDEX realtime.messages_pkey ATTACH PARTITION realtime.messages_2025_11_17_pkey;



--
-- Name: messages_2025_11_18_pkey; Type: INDEX ATTACH; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER INDEX realtime.messages_pkey ATTACH PARTITION realtime.messages_2025_11_18_pkey;



--
-- Name: messages_2025_11_19_pkey; Type: INDEX ATTACH; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER INDEX realtime.messages_pkey ATTACH PARTITION realtime.messages_2025_11_19_pkey;



--
-- Name: messages_2025_11_20_pkey; Type: INDEX ATTACH; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER INDEX realtime.messages_pkey ATTACH PARTITION realtime.messages_2025_11_20_pkey;



--
-- Name: messages_2025_11_21_pkey; Type: INDEX ATTACH; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER INDEX realtime.messages_pkey ATTACH PARTITION realtime.messages_2025_11_21_pkey;



--
-- Name: messages_2025_11_22_pkey; Type: INDEX ATTACH; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER INDEX realtime.messages_pkey ATTACH PARTITION realtime.messages_2025_11_22_pkey;



--
-- Name: proposal_overview _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE OR REPLACE VIEW public.proposal_overview AS
 SELECT p.id,
    p.call_identifier,
    p.proposal_title,
    p.proposal_acronym,
    p.proposal_type,
    p.status,
    p.completion_percentage,
    p.created_at,
    p.updated_at,
    count(DISTINCT ps.id) FILTER (WHERE (ps.is_current = true)) AS section_count,
    sum(ps.word_count) FILTER (WHERE (ps.is_current = true)) AS total_words,
    avg(ps.quality_score) FILTER (WHERE (ps.is_current = true)) AS avg_quality_score,
    count(DISTINCT pc.id) AS partner_count,
    count(DISTINCT pc.partner_country) AS country_count,
    sum(pb.total_eligible_costs) AS total_budget,
    sum(pb.requested_funding) AS total_funding_requested,
    count(cc.id) FILTER (WHERE ((cc.check_result)::text = 'fail'::text)) AS critical_issues,
    count(cc.id) FILTER (WHERE ((cc.check_result)::text = 'warning'::text)) AS warnings
   FROM ((((public.proposals p
     LEFT JOIN public.proposal_sections ps ON ((p.id = ps.proposal_id)))
     LEFT JOIN public.proposal_consortium pc ON ((p.id = pc.proposal_id)))
     LEFT JOIN public.proposal_budgets pb ON ((p.id = pb.proposal_id)))
     LEFT JOIN public.compliance_checks cc ON ((p.id = cc.proposal_id)))
  GROUP BY p.id;



--
-- Name: section_quality_summary _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE OR REPLACE VIEW public.section_quality_summary AS
 SELECT ps.id,
    ps.proposal_id,
    ps.section_id,
    ps.section_name,
    ps.word_count,
    ps.quality_score,
    ps.compliance_score,
    ps.completeness_score,
    count(scm.id) AS total_criteria,
    count(scm.id) FILTER (WHERE (scm.addressed = true)) AS addressed_criteria,
    avg(scm.strength_score) AS avg_criteria_strength,
    count(isug.id) FILTER (WHERE ((isug.status)::text = 'pending'::text)) AS pending_suggestions,
    count(isug.id) FILTER (WHERE ((isug.priority)::text = 'critical'::text)) AS critical_suggestions
   FROM ((public.proposal_sections ps
     LEFT JOIN public.section_criteria_mapping scm ON ((ps.id = scm.section_id)))
     LEFT JOIN public.improvement_suggestions isug ON ((ps.id = isug.section_id)))
  WHERE (ps.is_current = true)
  GROUP BY ps.id;



--
-- Name: funding_calls funding_calls_update_timestamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER funding_calls_update_timestamp BEFORE UPDATE ON public.funding_calls FOR EACH ROW EXECUTE FUNCTION public.update_funding_calls_timestamp();



--
-- Name: proposal_budgets trigger_calculate_funding; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_calculate_funding BEFORE INSERT OR UPDATE ON public.proposal_budgets FOR EACH ROW EXECUTE FUNCTION public.calculate_requested_funding();



--
-- Name: proposal_sections trigger_calculate_word_count; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_calculate_word_count BEFORE INSERT OR UPDATE OF section_content ON public.proposal_sections FOR EACH ROW EXECUTE FUNCTION public.calculate_word_count();



--
-- Name: proposal_sections trigger_update_completion; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_update_completion AFTER INSERT OR UPDATE ON public.proposal_sections FOR EACH ROW EXECUTE FUNCTION public.update_proposal_completion();



--
-- Name: project_embeddings trigger_update_project_embeddings_timestamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_update_project_embeddings_timestamp BEFORE UPDATE ON public.project_embeddings FOR EACH ROW EXECUTE FUNCTION public.update_project_embeddings_timestamp();



--
-- Name: proposals trigger_update_proposal_timestamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_update_proposal_timestamp BEFORE UPDATE ON public.proposals FOR EACH ROW EXECUTE FUNCTION public.update_proposal_timestamp();



--
-- Name: proposal_sessions trigger_update_session_activity; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_update_session_activity BEFORE UPDATE ON public.proposal_sessions FOR EACH ROW EXECUTE FUNCTION public.update_session_activity();



--
-- Name: subscription tr_check_filters; Type: TRIGGER; Schema: realtime; Owner: supabase_admin
--

CREATE TRIGGER tr_check_filters BEFORE INSERT OR UPDATE ON realtime.subscription FOR EACH ROW EXECUTE FUNCTION realtime.subscription_check_filters();



--
-- Name: objects objects_delete_delete_prefix; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER objects_delete_delete_prefix AFTER DELETE ON storage.objects FOR EACH ROW EXECUTE FUNCTION storage.delete_prefix_hierarchy_trigger();



--
-- Name: objects objects_insert_create_prefix; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER objects_insert_create_prefix BEFORE INSERT ON storage.objects FOR EACH ROW EXECUTE FUNCTION storage.objects_insert_prefix_trigger();



--
-- Name: objects objects_update_create_prefix; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER objects_update_create_prefix BEFORE UPDATE ON storage.objects FOR EACH ROW WHEN ((new.name <> old.name)) EXECUTE FUNCTION storage.objects_insert_prefix_trigger();



--
-- Name: prefixes prefixes_create_hierarchy; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER prefixes_create_hierarchy BEFORE INSERT ON storage.prefixes FOR EACH ROW WHEN ((pg_trigger_depth() < 1)) EXECUTE FUNCTION storage.prefixes_insert_trigger();



--
-- Name: prefixes prefixes_delete_hierarchy; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER prefixes_delete_hierarchy AFTER DELETE ON storage.prefixes FOR EACH ROW EXECUTE FUNCTION storage.delete_prefix_hierarchy_trigger();



--
-- Name: objects update_objects_updated_at; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER update_objects_updated_at BEFORE UPDATE ON storage.objects FOR EACH ROW EXECUTE FUNCTION storage.update_updated_at_column();



--
-- Name: extensions extensions_tenant_external_id_fkey; Type: FK CONSTRAINT; Schema: _realtime; Owner: supabase_admin
--

ALTER TABLE ONLY _realtime.extensions
    ADD CONSTRAINT extensions_tenant_external_id_fkey FOREIGN KEY (tenant_external_id) REFERENCES _realtime.tenants(external_id) ON DELETE CASCADE;



--
-- Name: identities identities_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;



--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;



--
-- Name: mfa_challenges mfa_challenges_auth_factor_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_auth_factor_id_fkey FOREIGN KEY (factor_id) REFERENCES auth.mfa_factors(id) ON DELETE CASCADE;



--
-- Name: mfa_factors mfa_factors_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;



--
-- Name: one_time_tokens one_time_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;



--
-- Name: refresh_tokens refresh_tokens_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;



--
-- Name: saml_providers saml_providers_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;



--
-- Name: saml_relay_states saml_relay_states_flow_state_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_flow_state_id_fkey FOREIGN KEY (flow_state_id) REFERENCES auth.flow_state(id) ON DELETE CASCADE;



--
-- Name: saml_relay_states saml_relay_states_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;



--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;



--
-- Name: sso_domains sso_domains_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;



--
-- Name: call_document_mappings call_document_mappings_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.call_document_mappings
    ADD CONSTRAINT call_document_mappings_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.shared_documents(id) ON DELETE CASCADE;



--
-- Name: client_collaboration client_collaboration_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_collaboration
    ADD CONSTRAINT client_collaboration_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.client(id) ON DELETE CASCADE;



--
-- Name: client_collaboration client_collaboration_collaboration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.client_collaboration
    ADD CONSTRAINT client_collaboration_collaboration_id_fkey FOREIGN KEY (collaboration_id) REFERENCES public.collaboration(id) ON DELETE CASCADE;



--
-- Name: compliance_checks compliance_checks_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.compliance_checks
    ADD CONSTRAINT compliance_checks_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id) ON DELETE CASCADE;



--
-- Name: conversation conversation_collaboration_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation
    ADD CONSTRAINT conversation_collaboration_id_fkey FOREIGN KEY (collaboration_id) REFERENCES public.collaboration(id);



--
-- Name: document_chunks document_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.horizon_documents(id) ON DELETE CASCADE;



--
-- Name: project_embeddings fk_project; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_embeddings
    ADD CONSTRAINT fk_project FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;



--
-- Name: improvement_suggestions improvement_suggestions_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.improvement_suggestions
    ADD CONSTRAINT improvement_suggestions_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id) ON DELETE CASCADE;



--
-- Name: improvement_suggestions improvement_suggestions_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.improvement_suggestions
    ADD CONSTRAINT improvement_suggestions_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.proposal_sections(id) ON DELETE CASCADE;



--
-- Name: message message_conversation_id_conversation_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_conversation_id_conversation_id_fk FOREIGN KEY (conversation_id) REFERENCES public.conversation(id);



--
-- Name: proposal_activity_log proposal_activity_log_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_activity_log
    ADD CONSTRAINT proposal_activity_log_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id) ON DELETE CASCADE;



--
-- Name: proposal_budgets proposal_budgets_consortium_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_budgets
    ADD CONSTRAINT proposal_budgets_consortium_id_fkey FOREIGN KEY (consortium_id) REFERENCES public.proposal_consortium(id) ON DELETE CASCADE;



--
-- Name: proposal_budgets proposal_budgets_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_budgets
    ADD CONSTRAINT proposal_budgets_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id) ON DELETE CASCADE;



--
-- Name: proposal_consortium proposal_consortium_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_consortium
    ADD CONSTRAINT proposal_consortium_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id) ON DELETE CASCADE;



--
-- Name: proposal_sections proposal_sections_parent_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sections
    ADD CONSTRAINT proposal_sections_parent_version_id_fkey FOREIGN KEY (parent_version_id) REFERENCES public.proposal_sections(id);



--
-- Name: proposal_sections proposal_sections_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sections
    ADD CONSTRAINT proposal_sections_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id) ON DELETE CASCADE;



--
-- Name: proposal_sessions proposal_sessions_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proposal_sessions
    ADD CONSTRAINT proposal_sessions_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.proposals(id) ON DELETE CASCADE;



--
-- Name: section_criteria_mapping section_criteria_mapping_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.section_criteria_mapping
    ADD CONSTRAINT section_criteria_mapping_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.proposal_sections(id) ON DELETE CASCADE;



--
-- Name: shared_document_chunks shared_document_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shared_document_chunks
    ADD CONSTRAINT shared_document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.shared_documents(id) ON DELETE CASCADE;



--
-- Name: objects objects_bucketId_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT "objects_bucketId_fkey" FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);



--
-- Name: prefixes prefixes_bucketId_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.prefixes
    ADD CONSTRAINT "prefixes_bucketId_fkey" FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);



--
-- Name: s3_multipart_uploads s3_multipart_uploads_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);



--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);



--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_upload_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_upload_id_fkey FOREIGN KEY (upload_id) REFERENCES storage.s3_multipart_uploads(id) ON DELETE CASCADE;



--
-- Name: audit_log_entries; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.audit_log_entries ENABLE ROW LEVEL SECURITY;


--
-- Name: flow_state; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.flow_state ENABLE ROW LEVEL SECURITY;


--
-- Name: identities; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.identities ENABLE ROW LEVEL SECURITY;


--
-- Name: instances; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.instances ENABLE ROW LEVEL SECURITY;


--
-- Name: mfa_amr_claims; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.mfa_amr_claims ENABLE ROW LEVEL SECURITY;


--
-- Name: mfa_challenges; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.mfa_challenges ENABLE ROW LEVEL SECURITY;


--
-- Name: mfa_factors; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.mfa_factors ENABLE ROW LEVEL SECURITY;


--
-- Name: one_time_tokens; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.one_time_tokens ENABLE ROW LEVEL SECURITY;


--
-- Name: refresh_tokens; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.refresh_tokens ENABLE ROW LEVEL SECURITY;


--
-- Name: saml_providers; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.saml_providers ENABLE ROW LEVEL SECURITY;


--
-- Name: saml_relay_states; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.saml_relay_states ENABLE ROW LEVEL SECURITY;


--
-- Name: schema_migrations; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.schema_migrations ENABLE ROW LEVEL SECURITY;


--
-- Name: sessions; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.sessions ENABLE ROW LEVEL SECURITY;


--
-- Name: sso_domains; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.sso_domains ENABLE ROW LEVEL SECURITY;


--
-- Name: sso_providers; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.sso_providers ENABLE ROW LEVEL SECURITY;


--
-- Name: users; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;


--
-- Name: document_chunks Public chunks are viewable by everyone; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "Public chunks are viewable by everyone" ON public.document_chunks FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.horizon_documents
  WHERE ((horizon_documents.id = document_chunks.document_id) AND (horizon_documents.status = 'active'::text)))));



--
-- Name: horizon_documents Public documents are viewable by everyone; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "Public documents are viewable by everyone" ON public.horizon_documents FOR SELECT USING ((status = 'active'::text));



--
-- Name: document_chunks Service role can manage all chunks; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "Service role can manage all chunks" ON public.document_chunks USING ((auth.role() = 'service_role'::text));



--
-- Name: horizon_documents Service role can manage all documents; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "Service role can manage all documents" ON public.horizon_documents USING ((auth.role() = 'service_role'::text));



--
-- Name: document_chunks; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;


--
-- Name: horizon_documents; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE public.horizon_documents ENABLE ROW LEVEL SECURITY;


--
-- Name: messages; Type: ROW SECURITY; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;


--
-- Name: buckets; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;


--
-- Name: migrations; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.migrations ENABLE ROW LEVEL SECURITY;


--
-- Name: objects; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;


--
-- Name: prefixes; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.prefixes ENABLE ROW LEVEL SECURITY;


--
-- Name: s3_multipart_uploads; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.s3_multipart_uploads ENABLE ROW LEVEL SECURITY;


--
-- Name: s3_multipart_uploads_parts; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.s3_multipart_uploads_parts ENABLE ROW LEVEL SECURITY;


--
-- Name: supabase_realtime; Type: PUBLICATION; Schema: -; Owner: postgres
--

CREATE PUBLICATION supabase_realtime WITH (publish = 'insert, update, delete, truncate');


--
-- Name: supabase_realtime_messages_publication; Type: PUBLICATION; Schema: -; Owner: supabase_admin
--

CREATE PUBLICATION supabase_realtime_messages_publication WITH (publish = 'insert, update, delete, truncate');


--
-- Name: supabase_realtime message; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY public.message;



--
-- Name: supabase_realtime_messages_publication messages; Type: PUBLICATION TABLE; Schema: realtime; Owner: supabase_admin
--

ALTER PUBLICATION supabase_realtime_messages_publication ADD TABLE ONLY realtime.messages;



--
-- Name: SCHEMA auth; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA auth TO anon;

GRANT USAGE ON SCHEMA auth TO authenticated;

GRANT USAGE ON SCHEMA auth TO service_role;

GRANT ALL ON SCHEMA auth TO supabase_auth_admin;

GRANT ALL ON SCHEMA auth TO dashboard_user;

GRANT ALL ON SCHEMA auth TO postgres;



--
-- Name: SCHEMA extensions; Type: ACL; Schema: -; Owner: postgres
--

GRANT USAGE ON SCHEMA extensions TO anon;

GRANT USAGE ON SCHEMA extensions TO authenticated;

GRANT USAGE ON SCHEMA extensions TO service_role;

GRANT ALL ON SCHEMA extensions TO dashboard_user;



--
-- Name: SCHEMA net; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA net TO supabase_functions_admin;

GRANT USAGE ON SCHEMA net TO postgres;

GRANT USAGE ON SCHEMA net TO anon;

GRANT USAGE ON SCHEMA net TO authenticated;

GRANT USAGE ON SCHEMA net TO service_role;



--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA public TO postgres;

GRANT USAGE ON SCHEMA public TO anon;

GRANT USAGE ON SCHEMA public TO authenticated;

GRANT USAGE ON SCHEMA public TO service_role;



--
-- Name: SCHEMA realtime; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA realtime TO postgres;

GRANT USAGE ON SCHEMA realtime TO anon;

GRANT USAGE ON SCHEMA realtime TO authenticated;

GRANT USAGE ON SCHEMA realtime TO service_role;

GRANT ALL ON SCHEMA realtime TO supabase_realtime_admin;



--
-- Name: SCHEMA storage; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT ALL ON SCHEMA storage TO postgres;

GRANT USAGE ON SCHEMA storage TO anon;

GRANT USAGE ON SCHEMA storage TO authenticated;

GRANT USAGE ON SCHEMA storage TO service_role;

GRANT ALL ON SCHEMA storage TO supabase_storage_admin;

GRANT ALL ON SCHEMA storage TO dashboard_user;



--
-- Name: SCHEMA supabase_functions; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA supabase_functions TO postgres;

GRANT USAGE ON SCHEMA supabase_functions TO anon;

GRANT USAGE ON SCHEMA supabase_functions TO authenticated;

GRANT USAGE ON SCHEMA supabase_functions TO service_role;

GRANT ALL ON SCHEMA supabase_functions TO supabase_functions_admin;



--
-- Name: FUNCTION gtrgm_in(cstring); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_in(cstring) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_in(cstring) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_in(cstring) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_in(cstring) TO service_role;



--
-- Name: FUNCTION gtrgm_out(public.gtrgm); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_out(public.gtrgm) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_out(public.gtrgm) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_out(public.gtrgm) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_out(public.gtrgm) TO service_role;



--
-- Name: FUNCTION halfvec_in(cstring, oid, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_in(cstring, oid, integer) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_in(cstring, oid, integer) TO anon;

GRANT ALL ON FUNCTION public.halfvec_in(cstring, oid, integer) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_in(cstring, oid, integer) TO service_role;



--
-- Name: FUNCTION halfvec_out(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_out(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_out(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_out(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_out(public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_recv(internal, oid, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_recv(internal, oid, integer) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_recv(internal, oid, integer) TO anon;

GRANT ALL ON FUNCTION public.halfvec_recv(internal, oid, integer) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_recv(internal, oid, integer) TO service_role;



--
-- Name: FUNCTION halfvec_send(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_send(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_send(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_send(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_send(public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_typmod_in(cstring[]); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_typmod_in(cstring[]) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_typmod_in(cstring[]) TO anon;

GRANT ALL ON FUNCTION public.halfvec_typmod_in(cstring[]) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_typmod_in(cstring[]) TO service_role;



--
-- Name: FUNCTION sparsevec_in(cstring, oid, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_in(cstring, oid, integer) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_in(cstring, oid, integer) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_in(cstring, oid, integer) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_in(cstring, oid, integer) TO service_role;



--
-- Name: FUNCTION sparsevec_out(public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_out(public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_out(public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_out(public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_out(public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_recv(internal, oid, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_recv(internal, oid, integer) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_recv(internal, oid, integer) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_recv(internal, oid, integer) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_recv(internal, oid, integer) TO service_role;



--
-- Name: FUNCTION sparsevec_send(public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_send(public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_send(public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_send(public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_send(public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_typmod_in(cstring[]); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_typmod_in(cstring[]) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_typmod_in(cstring[]) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_typmod_in(cstring[]) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_typmod_in(cstring[]) TO service_role;



--
-- Name: FUNCTION vector_in(cstring, oid, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_in(cstring, oid, integer) TO postgres;

GRANT ALL ON FUNCTION public.vector_in(cstring, oid, integer) TO anon;

GRANT ALL ON FUNCTION public.vector_in(cstring, oid, integer) TO authenticated;

GRANT ALL ON FUNCTION public.vector_in(cstring, oid, integer) TO service_role;



--
-- Name: FUNCTION vector_out(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_out(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_out(public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_out(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_out(public.vector) TO service_role;



--
-- Name: FUNCTION vector_recv(internal, oid, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_recv(internal, oid, integer) TO postgres;

GRANT ALL ON FUNCTION public.vector_recv(internal, oid, integer) TO anon;

GRANT ALL ON FUNCTION public.vector_recv(internal, oid, integer) TO authenticated;

GRANT ALL ON FUNCTION public.vector_recv(internal, oid, integer) TO service_role;



--
-- Name: FUNCTION vector_send(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_send(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_send(public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_send(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_send(public.vector) TO service_role;



--
-- Name: FUNCTION vector_typmod_in(cstring[]); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_typmod_in(cstring[]) TO postgres;

GRANT ALL ON FUNCTION public.vector_typmod_in(cstring[]) TO anon;

GRANT ALL ON FUNCTION public.vector_typmod_in(cstring[]) TO authenticated;

GRANT ALL ON FUNCTION public.vector_typmod_in(cstring[]) TO service_role;



--
-- Name: FUNCTION array_to_halfvec(real[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_halfvec(real[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_halfvec(real[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_halfvec(real[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_halfvec(real[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_sparsevec(real[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_sparsevec(real[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_sparsevec(real[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_sparsevec(real[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_sparsevec(real[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_vector(real[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_vector(real[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_vector(real[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_vector(real[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_vector(real[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_halfvec(double precision[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_halfvec(double precision[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_halfvec(double precision[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_halfvec(double precision[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_halfvec(double precision[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_sparsevec(double precision[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_sparsevec(double precision[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_sparsevec(double precision[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_sparsevec(double precision[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_sparsevec(double precision[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_vector(double precision[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_vector(double precision[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_vector(double precision[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_vector(double precision[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_vector(double precision[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_halfvec(integer[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_halfvec(integer[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_halfvec(integer[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_halfvec(integer[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_halfvec(integer[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_sparsevec(integer[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_sparsevec(integer[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_sparsevec(integer[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_sparsevec(integer[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_sparsevec(integer[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_vector(integer[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_vector(integer[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_vector(integer[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_vector(integer[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_vector(integer[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_halfvec(numeric[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_halfvec(numeric[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_halfvec(numeric[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_halfvec(numeric[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_halfvec(numeric[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_sparsevec(numeric[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_sparsevec(numeric[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_sparsevec(numeric[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_sparsevec(numeric[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_sparsevec(numeric[], integer, boolean) TO service_role;



--
-- Name: FUNCTION array_to_vector(numeric[], integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.array_to_vector(numeric[], integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.array_to_vector(numeric[], integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.array_to_vector(numeric[], integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.array_to_vector(numeric[], integer, boolean) TO service_role;



--
-- Name: FUNCTION halfvec_to_float4(public.halfvec, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_to_float4(public.halfvec, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_to_float4(public.halfvec, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.halfvec_to_float4(public.halfvec, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_to_float4(public.halfvec, integer, boolean) TO service_role;



--
-- Name: FUNCTION halfvec(public.halfvec, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec(public.halfvec, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.halfvec(public.halfvec, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.halfvec(public.halfvec, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec(public.halfvec, integer, boolean) TO service_role;



--
-- Name: FUNCTION halfvec_to_sparsevec(public.halfvec, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_to_sparsevec(public.halfvec, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_to_sparsevec(public.halfvec, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.halfvec_to_sparsevec(public.halfvec, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_to_sparsevec(public.halfvec, integer, boolean) TO service_role;



--
-- Name: FUNCTION halfvec_to_vector(public.halfvec, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_to_vector(public.halfvec, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_to_vector(public.halfvec, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.halfvec_to_vector(public.halfvec, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_to_vector(public.halfvec, integer, boolean) TO service_role;



--
-- Name: FUNCTION sparsevec_to_halfvec(public.sparsevec, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_to_halfvec(public.sparsevec, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_to_halfvec(public.sparsevec, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_to_halfvec(public.sparsevec, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_to_halfvec(public.sparsevec, integer, boolean) TO service_role;



--
-- Name: FUNCTION sparsevec(public.sparsevec, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec(public.sparsevec, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec(public.sparsevec, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.sparsevec(public.sparsevec, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec(public.sparsevec, integer, boolean) TO service_role;



--
-- Name: FUNCTION sparsevec_to_vector(public.sparsevec, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_to_vector(public.sparsevec, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_to_vector(public.sparsevec, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_to_vector(public.sparsevec, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_to_vector(public.sparsevec, integer, boolean) TO service_role;



--
-- Name: FUNCTION vector_to_float4(public.vector, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_to_float4(public.vector, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.vector_to_float4(public.vector, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.vector_to_float4(public.vector, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.vector_to_float4(public.vector, integer, boolean) TO service_role;



--
-- Name: FUNCTION vector_to_halfvec(public.vector, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_to_halfvec(public.vector, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.vector_to_halfvec(public.vector, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.vector_to_halfvec(public.vector, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.vector_to_halfvec(public.vector, integer, boolean) TO service_role;



--
-- Name: FUNCTION vector_to_sparsevec(public.vector, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_to_sparsevec(public.vector, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.vector_to_sparsevec(public.vector, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.vector_to_sparsevec(public.vector, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.vector_to_sparsevec(public.vector, integer, boolean) TO service_role;



--
-- Name: FUNCTION vector(public.vector, integer, boolean); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector(public.vector, integer, boolean) TO postgres;

GRANT ALL ON FUNCTION public.vector(public.vector, integer, boolean) TO anon;

GRANT ALL ON FUNCTION public.vector(public.vector, integer, boolean) TO authenticated;

GRANT ALL ON FUNCTION public.vector(public.vector, integer, boolean) TO service_role;



--
-- Name: FUNCTION email(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.email() TO dashboard_user;



--
-- Name: FUNCTION jwt(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.jwt() TO postgres;

GRANT ALL ON FUNCTION auth.jwt() TO dashboard_user;



--
-- Name: FUNCTION role(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.role() TO dashboard_user;



--
-- Name: FUNCTION uid(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.uid() TO dashboard_user;



--
-- Name: FUNCTION algorithm_sign(signables text, secret text, algorithm text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.algorithm_sign(signables text, secret text, algorithm text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.algorithm_sign(signables text, secret text, algorithm text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION armor(bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.armor(bytea) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.armor(bytea) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION armor(bytea, text[], text[]); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.armor(bytea, text[], text[]) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.armor(bytea, text[], text[]) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION crypt(text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.crypt(text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.crypt(text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION dearmor(text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.dearmor(text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.dearmor(text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION decrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.decrypt(bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.decrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION decrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.decrypt_iv(bytea, bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.decrypt_iv(bytea, bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION digest(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.digest(bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.digest(bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION digest(text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.digest(text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.digest(text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION encrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.encrypt(bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.encrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION encrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.encrypt_iv(bytea, bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.encrypt_iv(bytea, bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION gen_random_bytes(integer); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_random_bytes(integer) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.gen_random_bytes(integer) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION gen_random_uuid(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_random_uuid() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.gen_random_uuid() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION gen_salt(text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_salt(text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.gen_salt(text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION gen_salt(text, integer); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_salt(text, integer) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.gen_salt(text, integer) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION grant_pg_cron_access(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION extensions.grant_pg_cron_access() FROM postgres;

GRANT ALL ON FUNCTION extensions.grant_pg_cron_access() TO postgres WITH GRANT OPTION;

GRANT ALL ON FUNCTION extensions.grant_pg_cron_access() TO dashboard_user;



--
-- Name: FUNCTION grant_pg_graphql_access(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.grant_pg_graphql_access() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION grant_pg_net_access(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION extensions.grant_pg_net_access() FROM postgres;

GRANT ALL ON FUNCTION extensions.grant_pg_net_access() TO postgres WITH GRANT OPTION;

GRANT ALL ON FUNCTION extensions.grant_pg_net_access() TO dashboard_user;



--
-- Name: FUNCTION hmac(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.hmac(bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.hmac(bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION hmac(text, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.hmac(text, text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.hmac(text, text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pg_stat_statements_reset(userid oid, dbid oid, queryid bigint); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_armor_headers(text, OUT key text, OUT value text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_armor_headers(text, OUT key text, OUT value text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_armor_headers(text, OUT key text, OUT value text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_key_id(bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_key_id(bytea) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_key_id(bytea) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_encrypt(text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_encrypt(text, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text, text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text, text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgrst_ddl_watch(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgrst_ddl_watch() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION pgrst_drop_watch(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgrst_drop_watch() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION set_graphql_placeholder(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.set_graphql_placeholder() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION sign(payload json, secret text, algorithm text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.sign(payload json, secret text, algorithm text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.sign(payload json, secret text, algorithm text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION try_cast_double(inp text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.try_cast_double(inp text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.try_cast_double(inp text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION url_decode(data text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.url_decode(data text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.url_decode(data text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION url_encode(data bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.url_encode(data bytea) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.url_encode(data bytea) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_generate_v1(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v1() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_generate_v1() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_generate_v1mc(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v1mc() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_generate_v1mc() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_generate_v3(namespace uuid, name text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v3(namespace uuid, name text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_generate_v3(namespace uuid, name text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_generate_v4(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v4() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_generate_v4() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_generate_v5(namespace uuid, name text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v5(namespace uuid, name text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_generate_v5(namespace uuid, name text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_nil(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_nil() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_nil() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_ns_dns(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_dns() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_ns_dns() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_ns_oid(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_oid() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_ns_oid() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_ns_url(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_url() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_ns_url() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION uuid_ns_x500(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_x500() TO dashboard_user;

GRANT ALL ON FUNCTION extensions.uuid_ns_x500() TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION verify(token text, secret text, algorithm text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.verify(token text, secret text, algorithm text) TO dashboard_user;

GRANT ALL ON FUNCTION extensions.verify(token text, secret text, algorithm text) TO postgres WITH GRANT OPTION;



--
-- Name: FUNCTION graphql("operationName" text, query text, variables jsonb, extensions jsonb); Type: ACL; Schema: graphql_public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO postgres;

GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO anon;

GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO authenticated;

GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO service_role;



--
-- Name: FUNCTION http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer); Type: ACL; Schema: net; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

GRANT ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin;

GRANT ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO postgres;

GRANT ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO anon;

GRANT ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO authenticated;

GRANT ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO service_role;



--
-- Name: FUNCTION http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer); Type: ACL; Schema: net; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

GRANT ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin;

GRANT ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO postgres;

GRANT ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO anon;

GRANT ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO authenticated;

GRANT ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO service_role;



--
-- Name: FUNCTION get_auth(p_usename text); Type: ACL; Schema: pgbouncer; Owner: postgres
--

REVOKE ALL ON FUNCTION pgbouncer.get_auth(p_usename text) FROM PUBLIC;

GRANT ALL ON FUNCTION pgbouncer.get_auth(p_usename text) TO pgbouncer;



--
-- Name: FUNCTION crypto_aead_det_decrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea); Type: ACL; Schema: pgsodium; Owner: pgsodium_keymaker
--

GRANT ALL ON FUNCTION pgsodium.crypto_aead_det_decrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea) TO service_role;



--
-- Name: FUNCTION crypto_aead_det_encrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea); Type: ACL; Schema: pgsodium; Owner: pgsodium_keymaker
--

GRANT ALL ON FUNCTION pgsodium.crypto_aead_det_encrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea) TO service_role;



--
-- Name: FUNCTION crypto_aead_det_keygen(); Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON FUNCTION pgsodium.crypto_aead_det_keygen() TO service_role;



--
-- Name: FUNCTION aggregate_conversation_analytics_daily(p_date date); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.aggregate_conversation_analytics_daily(p_date date) TO anon;

GRANT ALL ON FUNCTION public.aggregate_conversation_analytics_daily(p_date date) TO authenticated;

GRANT ALL ON FUNCTION public.aggregate_conversation_analytics_daily(p_date date) TO service_role;



--
-- Name: FUNCTION aggregate_feedback_insights(p_date date); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.aggregate_feedback_insights(p_date date) TO anon;

GRANT ALL ON FUNCTION public.aggregate_feedback_insights(p_date date) TO authenticated;

GRANT ALL ON FUNCTION public.aggregate_feedback_insights(p_date date) TO service_role;



--
-- Name: FUNCTION aggregate_tool_metrics(p_period_hours integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.aggregate_tool_metrics(p_period_hours integer) TO anon;

GRANT ALL ON FUNCTION public.aggregate_tool_metrics(p_period_hours integer) TO authenticated;

GRANT ALL ON FUNCTION public.aggregate_tool_metrics(p_period_hours integer) TO service_role;



--
-- Name: FUNCTION binary_quantize(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.binary_quantize(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.binary_quantize(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.binary_quantize(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.binary_quantize(public.halfvec) TO service_role;



--
-- Name: FUNCTION binary_quantize(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.binary_quantize(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.binary_quantize(public.vector) TO anon;

GRANT ALL ON FUNCTION public.binary_quantize(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.binary_quantize(public.vector) TO service_role;



--
-- Name: FUNCTION calculate_completion_percentage(p_proposal_id integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.calculate_completion_percentage(p_proposal_id integer) TO anon;

GRANT ALL ON FUNCTION public.calculate_completion_percentage(p_proposal_id integer) TO authenticated;

GRANT ALL ON FUNCTION public.calculate_completion_percentage(p_proposal_id integer) TO service_role;



--
-- Name: FUNCTION calculate_requested_funding(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.calculate_requested_funding() TO anon;

GRANT ALL ON FUNCTION public.calculate_requested_funding() TO authenticated;

GRANT ALL ON FUNCTION public.calculate_requested_funding() TO service_role;



--
-- Name: FUNCTION calculate_word_count(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.calculate_word_count() TO anon;

GRANT ALL ON FUNCTION public.calculate_word_count() TO authenticated;

GRANT ALL ON FUNCTION public.calculate_word_count() TO service_role;



--
-- Name: FUNCTION cleanup_expired_sessions(expiry_hours integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.cleanup_expired_sessions(expiry_hours integer) TO anon;

GRANT ALL ON FUNCTION public.cleanup_expired_sessions(expiry_hours integer) TO authenticated;

GRANT ALL ON FUNCTION public.cleanup_expired_sessions(expiry_hours integer) TO service_role;



--
-- Name: FUNCTION cosine_distance(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.cosine_distance(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.cosine_distance(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.cosine_distance(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.cosine_distance(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION cosine_distance(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.cosine_distance(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.cosine_distance(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.cosine_distance(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.cosine_distance(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION cosine_distance(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.cosine_distance(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.cosine_distance(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.cosine_distance(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.cosine_distance(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION get_chunks_for_call(p_call_identifier character varying, p_search_query text, p_limit integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.get_chunks_for_call(p_call_identifier character varying, p_search_query text, p_limit integer) TO anon;

GRANT ALL ON FUNCTION public.get_chunks_for_call(p_call_identifier character varying, p_search_query text, p_limit integer) TO authenticated;

GRANT ALL ON FUNCTION public.get_chunks_for_call(p_call_identifier character varying, p_search_query text, p_limit integer) TO service_role;



--
-- Name: FUNCTION get_current_sections(p_proposal_id integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.get_current_sections(p_proposal_id integer) TO anon;

GRANT ALL ON FUNCTION public.get_current_sections(p_proposal_id integer) TO authenticated;

GRANT ALL ON FUNCTION public.get_current_sections(p_proposal_id integer) TO service_role;



--
-- Name: FUNCTION get_document_stats(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.get_document_stats() TO anon;

GRANT ALL ON FUNCTION public.get_document_stats() TO authenticated;

GRANT ALL ON FUNCTION public.get_document_stats() TO service_role;



--
-- Name: FUNCTION gin_btree_consistent(internal, smallint, anyelement, integer, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_btree_consistent(internal, smallint, anyelement, integer, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_btree_consistent(internal, smallint, anyelement, integer, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_btree_consistent(internal, smallint, anyelement, integer, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_btree_consistent(internal, smallint, anyelement, integer, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_anyenum(anyenum, anyenum, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_anyenum(anyenum, anyenum, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_anyenum(anyenum, anyenum, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_anyenum(anyenum, anyenum, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_anyenum(anyenum, anyenum, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_bit(bit, bit, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_bit(bit, bit, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bit(bit, bit, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bit(bit, bit, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bit(bit, bit, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_bool(boolean, boolean, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_bool(boolean, boolean, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bool(boolean, boolean, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bool(boolean, boolean, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bool(boolean, boolean, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_bpchar(character, character, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_bpchar(character, character, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bpchar(character, character, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bpchar(character, character, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bpchar(character, character, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_bytea(bytea, bytea, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_bytea(bytea, bytea, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bytea(bytea, bytea, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bytea(bytea, bytea, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_bytea(bytea, bytea, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_char("char", "char", smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_char("char", "char", smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_char("char", "char", smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_char("char", "char", smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_char("char", "char", smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_cidr(cidr, cidr, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_cidr(cidr, cidr, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_cidr(cidr, cidr, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_cidr(cidr, cidr, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_cidr(cidr, cidr, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_date(date, date, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_date(date, date, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_date(date, date, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_date(date, date, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_date(date, date, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_float4(real, real, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_float4(real, real, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_float4(real, real, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_float4(real, real, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_float4(real, real, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_float8(double precision, double precision, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_float8(double precision, double precision, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_float8(double precision, double precision, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_float8(double precision, double precision, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_float8(double precision, double precision, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_inet(inet, inet, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_inet(inet, inet, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_inet(inet, inet, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_inet(inet, inet, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_inet(inet, inet, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_int2(smallint, smallint, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_int2(smallint, smallint, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int2(smallint, smallint, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int2(smallint, smallint, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int2(smallint, smallint, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_int4(integer, integer, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_int4(integer, integer, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int4(integer, integer, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int4(integer, integer, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int4(integer, integer, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_int8(bigint, bigint, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_int8(bigint, bigint, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int8(bigint, bigint, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int8(bigint, bigint, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_int8(bigint, bigint, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_interval(interval, interval, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_interval(interval, interval, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_interval(interval, interval, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_interval(interval, interval, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_interval(interval, interval, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_macaddr(macaddr, macaddr, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr(macaddr, macaddr, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr(macaddr, macaddr, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr(macaddr, macaddr, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr(macaddr, macaddr, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_macaddr8(macaddr8, macaddr8, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr8(macaddr8, macaddr8, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr8(macaddr8, macaddr8, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr8(macaddr8, macaddr8, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_macaddr8(macaddr8, macaddr8, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_money(money, money, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_money(money, money, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_money(money, money, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_money(money, money, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_money(money, money, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_name(name, name, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_name(name, name, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_name(name, name, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_name(name, name, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_name(name, name, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_numeric(numeric, numeric, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_numeric(numeric, numeric, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_numeric(numeric, numeric, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_numeric(numeric, numeric, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_numeric(numeric, numeric, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_oid(oid, oid, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_oid(oid, oid, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_oid(oid, oid, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_oid(oid, oid, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_oid(oid, oid, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_text(text, text, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_text(text, text, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_text(text, text, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_text(text, text, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_text(text, text, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_time(time without time zone, time without time zone, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_time(time without time zone, time without time zone, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_time(time without time zone, time without time zone, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_time(time without time zone, time without time zone, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_time(time without time zone, time without time zone, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_timestamp(timestamp without time zone, timestamp without time zone, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamp(timestamp without time zone, timestamp without time zone, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamp(timestamp without time zone, timestamp without time zone, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamp(timestamp without time zone, timestamp without time zone, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamp(timestamp without time zone, timestamp without time zone, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_timestamptz(timestamp with time zone, timestamp with time zone, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamptz(timestamp with time zone, timestamp with time zone, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamptz(timestamp with time zone, timestamp with time zone, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamptz(timestamp with time zone, timestamp with time zone, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timestamptz(timestamp with time zone, timestamp with time zone, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_timetz(time with time zone, time with time zone, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_timetz(time with time zone, time with time zone, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timetz(time with time zone, time with time zone, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timetz(time with time zone, time with time zone, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_timetz(time with time zone, time with time zone, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_uuid(uuid, uuid, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_uuid(uuid, uuid, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_uuid(uuid, uuid, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_uuid(uuid, uuid, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_uuid(uuid, uuid, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_compare_prefix_varbit(bit varying, bit varying, smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_compare_prefix_varbit(bit varying, bit varying, smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_compare_prefix_varbit(bit varying, bit varying, smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_compare_prefix_varbit(bit varying, bit varying, smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_compare_prefix_varbit(bit varying, bit varying, smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_enum_cmp(anyenum, anyenum); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_enum_cmp(anyenum, anyenum) TO postgres;

GRANT ALL ON FUNCTION public.gin_enum_cmp(anyenum, anyenum) TO anon;

GRANT ALL ON FUNCTION public.gin_enum_cmp(anyenum, anyenum) TO authenticated;

GRANT ALL ON FUNCTION public.gin_enum_cmp(anyenum, anyenum) TO service_role;



--
-- Name: FUNCTION gin_extract_query_anyenum(anyenum, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_anyenum(anyenum, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_anyenum(anyenum, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_anyenum(anyenum, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_anyenum(anyenum, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_bit(bit, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_bit(bit, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_bit(bit, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_bit(bit, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_bit(bit, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_bool(boolean, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_bool(boolean, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_bool(boolean, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_bool(boolean, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_bool(boolean, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_bpchar(character, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_bpchar(character, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_bpchar(character, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_bpchar(character, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_bpchar(character, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_bytea(bytea, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_bytea(bytea, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_bytea(bytea, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_bytea(bytea, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_bytea(bytea, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_char("char", internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_char("char", internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_char("char", internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_char("char", internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_char("char", internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_cidr(cidr, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_cidr(cidr, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_cidr(cidr, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_cidr(cidr, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_cidr(cidr, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_date(date, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_date(date, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_date(date, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_date(date, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_date(date, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_float4(real, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_float4(real, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_float4(real, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_float4(real, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_float4(real, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_float8(double precision, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_float8(double precision, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_float8(double precision, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_float8(double precision, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_float8(double precision, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_inet(inet, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_inet(inet, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_inet(inet, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_inet(inet, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_inet(inet, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_int2(smallint, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_int2(smallint, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_int2(smallint, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_int2(smallint, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_int2(smallint, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_int4(integer, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_int4(integer, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_int4(integer, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_int4(integer, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_int4(integer, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_int8(bigint, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_int8(bigint, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_int8(bigint, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_int8(bigint, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_int8(bigint, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_interval(interval, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_interval(interval, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_interval(interval, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_interval(interval, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_interval(interval, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_macaddr(macaddr, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr(macaddr, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr(macaddr, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr(macaddr, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr(macaddr, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_macaddr8(macaddr8, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr8(macaddr8, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr8(macaddr8, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr8(macaddr8, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_macaddr8(macaddr8, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_money(money, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_money(money, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_money(money, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_money(money, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_money(money, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_name(name, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_name(name, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_name(name, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_name(name, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_name(name, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_numeric(numeric, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_numeric(numeric, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_numeric(numeric, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_numeric(numeric, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_numeric(numeric, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_oid(oid, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_oid(oid, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_oid(oid, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_oid(oid, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_oid(oid, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_text(text, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_text(text, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_text(text, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_text(text, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_text(text, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_time(time without time zone, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_time(time without time zone, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_time(time without time zone, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_time(time without time zone, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_time(time without time zone, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_timestamp(timestamp without time zone, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_timestamp(timestamp without time zone, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_timestamp(timestamp without time zone, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_timestamp(timestamp without time zone, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_timestamp(timestamp without time zone, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_timestamptz(timestamp with time zone, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_timestamptz(timestamp with time zone, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_timestamptz(timestamp with time zone, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_timestamptz(timestamp with time zone, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_timestamptz(timestamp with time zone, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_timetz(time with time zone, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_timetz(time with time zone, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_timetz(time with time zone, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_timetz(time with time zone, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_timetz(time with time zone, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_trgm(text, internal, smallint, internal, internal, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_uuid(uuid, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_uuid(uuid, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_uuid(uuid, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_uuid(uuid, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_uuid(uuid, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_query_varbit(bit varying, internal, smallint, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_query_varbit(bit varying, internal, smallint, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_query_varbit(bit varying, internal, smallint, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_query_varbit(bit varying, internal, smallint, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_query_varbit(bit varying, internal, smallint, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_anyenum(anyenum, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_anyenum(anyenum, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_anyenum(anyenum, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_anyenum(anyenum, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_anyenum(anyenum, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_bit(bit, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_bit(bit, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_bit(bit, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_bit(bit, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_bit(bit, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_bool(boolean, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_bool(boolean, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_bool(boolean, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_bool(boolean, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_bool(boolean, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_bpchar(character, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_bpchar(character, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_bpchar(character, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_bpchar(character, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_bpchar(character, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_bytea(bytea, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_bytea(bytea, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_bytea(bytea, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_bytea(bytea, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_bytea(bytea, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_char("char", internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_char("char", internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_char("char", internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_char("char", internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_char("char", internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_cidr(cidr, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_cidr(cidr, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_cidr(cidr, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_cidr(cidr, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_cidr(cidr, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_date(date, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_date(date, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_date(date, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_date(date, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_date(date, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_float4(real, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_float4(real, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_float4(real, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_float4(real, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_float4(real, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_float8(double precision, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_float8(double precision, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_float8(double precision, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_float8(double precision, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_float8(double precision, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_inet(inet, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_inet(inet, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_inet(inet, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_inet(inet, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_inet(inet, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_int2(smallint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_int2(smallint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_int2(smallint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_int2(smallint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_int2(smallint, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_int4(integer, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_int4(integer, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_int4(integer, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_int4(integer, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_int4(integer, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_int8(bigint, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_int8(bigint, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_int8(bigint, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_int8(bigint, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_int8(bigint, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_interval(interval, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_interval(interval, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_interval(interval, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_interval(interval, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_interval(interval, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_macaddr(macaddr, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr(macaddr, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr(macaddr, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr(macaddr, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr(macaddr, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_macaddr8(macaddr8, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr8(macaddr8, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr8(macaddr8, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr8(macaddr8, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_macaddr8(macaddr8, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_money(money, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_money(money, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_money(money, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_money(money, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_money(money, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_name(name, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_name(name, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_name(name, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_name(name, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_name(name, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_numeric(numeric, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_numeric(numeric, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_numeric(numeric, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_numeric(numeric, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_numeric(numeric, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_oid(oid, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_oid(oid, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_oid(oid, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_oid(oid, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_oid(oid, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_text(text, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_text(text, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_text(text, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_text(text, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_text(text, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_time(time without time zone, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_time(time without time zone, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_time(time without time zone, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_time(time without time zone, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_time(time without time zone, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_timestamp(timestamp without time zone, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_timestamp(timestamp without time zone, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_timestamp(timestamp without time zone, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_timestamp(timestamp without time zone, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_timestamp(timestamp without time zone, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_timestamptz(timestamp with time zone, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_timestamptz(timestamp with time zone, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_timestamptz(timestamp with time zone, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_timestamptz(timestamp with time zone, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_timestamptz(timestamp with time zone, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_timetz(time with time zone, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_timetz(time with time zone, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_timetz(time with time zone, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_timetz(time with time zone, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_timetz(time with time zone, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_trgm(text, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_trgm(text, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_trgm(text, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_trgm(text, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_trgm(text, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_uuid(uuid, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_uuid(uuid, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_uuid(uuid, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_uuid(uuid, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_uuid(uuid, internal) TO service_role;



--
-- Name: FUNCTION gin_extract_value_varbit(bit varying, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_extract_value_varbit(bit varying, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_extract_value_varbit(bit varying, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_extract_value_varbit(bit varying, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_extract_value_varbit(bit varying, internal) TO service_role;



--
-- Name: FUNCTION gin_numeric_cmp(numeric, numeric); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_numeric_cmp(numeric, numeric) TO postgres;

GRANT ALL ON FUNCTION public.gin_numeric_cmp(numeric, numeric) TO anon;

GRANT ALL ON FUNCTION public.gin_numeric_cmp(numeric, numeric) TO authenticated;

GRANT ALL ON FUNCTION public.gin_numeric_cmp(numeric, numeric) TO service_role;



--
-- Name: FUNCTION gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_trgm_consistent(internal, smallint, text, integer, internal, internal, internal, internal) TO service_role;



--
-- Name: FUNCTION gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gin_trgm_triconsistent(internal, smallint, text, integer, internal, internal, internal) TO service_role;



--
-- Name: FUNCTION gtrgm_compress(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_compress(internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_compress(internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_compress(internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_compress(internal) TO service_role;



--
-- Name: FUNCTION gtrgm_consistent(internal, text, smallint, oid, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_consistent(internal, text, smallint, oid, internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_consistent(internal, text, smallint, oid, internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_consistent(internal, text, smallint, oid, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_consistent(internal, text, smallint, oid, internal) TO service_role;



--
-- Name: FUNCTION gtrgm_decompress(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_decompress(internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_decompress(internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_decompress(internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_decompress(internal) TO service_role;



--
-- Name: FUNCTION gtrgm_distance(internal, text, smallint, oid, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_distance(internal, text, smallint, oid, internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_distance(internal, text, smallint, oid, internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_distance(internal, text, smallint, oid, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_distance(internal, text, smallint, oid, internal) TO service_role;



--
-- Name: FUNCTION gtrgm_options(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_options(internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_options(internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_options(internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_options(internal) TO service_role;



--
-- Name: FUNCTION gtrgm_penalty(internal, internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_penalty(internal, internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_penalty(internal, internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_penalty(internal, internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_penalty(internal, internal, internal) TO service_role;



--
-- Name: FUNCTION gtrgm_picksplit(internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_picksplit(internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_picksplit(internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_picksplit(internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_picksplit(internal, internal) TO service_role;



--
-- Name: FUNCTION gtrgm_same(public.gtrgm, public.gtrgm, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_same(public.gtrgm, public.gtrgm, internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_same(public.gtrgm, public.gtrgm, internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_same(public.gtrgm, public.gtrgm, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_same(public.gtrgm, public.gtrgm, internal) TO service_role;



--
-- Name: FUNCTION gtrgm_union(internal, internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.gtrgm_union(internal, internal) TO postgres;

GRANT ALL ON FUNCTION public.gtrgm_union(internal, internal) TO anon;

GRANT ALL ON FUNCTION public.gtrgm_union(internal, internal) TO authenticated;

GRANT ALL ON FUNCTION public.gtrgm_union(internal, internal) TO service_role;



--
-- Name: FUNCTION halfvec_accum(double precision[], public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_accum(double precision[], public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_accum(double precision[], public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_accum(double precision[], public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_accum(double precision[], public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_add(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_add(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_add(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_add(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_add(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_avg(double precision[]); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_avg(double precision[]) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_avg(double precision[]) TO anon;

GRANT ALL ON FUNCTION public.halfvec_avg(double precision[]) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_avg(double precision[]) TO service_role;



--
-- Name: FUNCTION halfvec_cmp(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_cmp(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_cmp(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_cmp(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_cmp(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_combine(double precision[], double precision[]); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_combine(double precision[], double precision[]) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_combine(double precision[], double precision[]) TO anon;

GRANT ALL ON FUNCTION public.halfvec_combine(double precision[], double precision[]) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_combine(double precision[], double precision[]) TO service_role;



--
-- Name: FUNCTION halfvec_concat(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_concat(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_concat(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_concat(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_concat(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_eq(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_eq(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_eq(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_eq(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_eq(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_ge(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_ge(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_ge(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_ge(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_ge(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_gt(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_gt(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_gt(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_gt(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_gt(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_l2_squared_distance(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_l2_squared_distance(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_l2_squared_distance(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_l2_squared_distance(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_l2_squared_distance(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_le(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_le(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_le(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_le(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_le(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_lt(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_lt(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_lt(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_lt(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_lt(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_mul(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_mul(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_mul(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_mul(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_mul(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_ne(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_ne(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_ne(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_ne(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_ne(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_negative_inner_product(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_negative_inner_product(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_negative_inner_product(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_negative_inner_product(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_negative_inner_product(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_spherical_distance(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_spherical_distance(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_spherical_distance(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_spherical_distance(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_spherical_distance(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION halfvec_sub(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.halfvec_sub(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.halfvec_sub(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.halfvec_sub(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.halfvec_sub(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION hamming_distance(bit, bit); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.hamming_distance(bit, bit) TO postgres;

GRANT ALL ON FUNCTION public.hamming_distance(bit, bit) TO anon;

GRANT ALL ON FUNCTION public.hamming_distance(bit, bit) TO authenticated;

GRANT ALL ON FUNCTION public.hamming_distance(bit, bit) TO service_role;



--
-- Name: FUNCTION hnsw_bit_support(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.hnsw_bit_support(internal) TO postgres;

GRANT ALL ON FUNCTION public.hnsw_bit_support(internal) TO anon;

GRANT ALL ON FUNCTION public.hnsw_bit_support(internal) TO authenticated;

GRANT ALL ON FUNCTION public.hnsw_bit_support(internal) TO service_role;



--
-- Name: FUNCTION hnsw_halfvec_support(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.hnsw_halfvec_support(internal) TO postgres;

GRANT ALL ON FUNCTION public.hnsw_halfvec_support(internal) TO anon;

GRANT ALL ON FUNCTION public.hnsw_halfvec_support(internal) TO authenticated;

GRANT ALL ON FUNCTION public.hnsw_halfvec_support(internal) TO service_role;



--
-- Name: FUNCTION hnsw_sparsevec_support(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.hnsw_sparsevec_support(internal) TO postgres;

GRANT ALL ON FUNCTION public.hnsw_sparsevec_support(internal) TO anon;

GRANT ALL ON FUNCTION public.hnsw_sparsevec_support(internal) TO authenticated;

GRANT ALL ON FUNCTION public.hnsw_sparsevec_support(internal) TO service_role;



--
-- Name: FUNCTION hnswhandler(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.hnswhandler(internal) TO postgres;

GRANT ALL ON FUNCTION public.hnswhandler(internal) TO anon;

GRANT ALL ON FUNCTION public.hnswhandler(internal) TO authenticated;

GRANT ALL ON FUNCTION public.hnswhandler(internal) TO service_role;



--
-- Name: FUNCTION hybrid_search(query_embedding public.vector, query_text text, match_count integer, vector_weight double precision); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.hybrid_search(query_embedding public.vector, query_text text, match_count integer, vector_weight double precision) TO anon;

GRANT ALL ON FUNCTION public.hybrid_search(query_embedding public.vector, query_text text, match_count integer, vector_weight double precision) TO authenticated;

GRANT ALL ON FUNCTION public.hybrid_search(query_embedding public.vector, query_text text, match_count integer, vector_weight double precision) TO service_role;



--
-- Name: FUNCTION inner_product(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.inner_product(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.inner_product(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.inner_product(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.inner_product(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION inner_product(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.inner_product(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.inner_product(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.inner_product(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.inner_product(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION inner_product(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.inner_product(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.inner_product(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.inner_product(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.inner_product(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION ivfflat_bit_support(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.ivfflat_bit_support(internal) TO postgres;

GRANT ALL ON FUNCTION public.ivfflat_bit_support(internal) TO anon;

GRANT ALL ON FUNCTION public.ivfflat_bit_support(internal) TO authenticated;

GRANT ALL ON FUNCTION public.ivfflat_bit_support(internal) TO service_role;



--
-- Name: FUNCTION ivfflat_halfvec_support(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.ivfflat_halfvec_support(internal) TO postgres;

GRANT ALL ON FUNCTION public.ivfflat_halfvec_support(internal) TO anon;

GRANT ALL ON FUNCTION public.ivfflat_halfvec_support(internal) TO authenticated;

GRANT ALL ON FUNCTION public.ivfflat_halfvec_support(internal) TO service_role;



--
-- Name: FUNCTION ivfflathandler(internal); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.ivfflathandler(internal) TO postgres;

GRANT ALL ON FUNCTION public.ivfflathandler(internal) TO anon;

GRANT ALL ON FUNCTION public.ivfflathandler(internal) TO authenticated;

GRANT ALL ON FUNCTION public.ivfflathandler(internal) TO service_role;



--
-- Name: FUNCTION jaccard_distance(bit, bit); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.jaccard_distance(bit, bit) TO postgres;

GRANT ALL ON FUNCTION public.jaccard_distance(bit, bit) TO anon;

GRANT ALL ON FUNCTION public.jaccard_distance(bit, bit) TO authenticated;

GRANT ALL ON FUNCTION public.jaccard_distance(bit, bit) TO service_role;



--
-- Name: FUNCTION keyword_search(query_text text, limit_count integer, filter_document_type text, filter_year text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.keyword_search(query_text text, limit_count integer, filter_document_type text, filter_year text) TO anon;

GRANT ALL ON FUNCTION public.keyword_search(query_text text, limit_count integer, filter_document_type text, filter_year text) TO authenticated;

GRANT ALL ON FUNCTION public.keyword_search(query_text text, limit_count integer, filter_document_type text, filter_year text) TO service_role;



--
-- Name: FUNCTION l1_distance(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l1_distance(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.l1_distance(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.l1_distance(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.l1_distance(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION l1_distance(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l1_distance(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.l1_distance(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.l1_distance(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.l1_distance(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION l1_distance(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l1_distance(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.l1_distance(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.l1_distance(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.l1_distance(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION l2_distance(public.halfvec, public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_distance(public.halfvec, public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.l2_distance(public.halfvec, public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.l2_distance(public.halfvec, public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.l2_distance(public.halfvec, public.halfvec) TO service_role;



--
-- Name: FUNCTION l2_distance(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_distance(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.l2_distance(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.l2_distance(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.l2_distance(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION l2_distance(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_distance(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.l2_distance(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.l2_distance(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.l2_distance(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION l2_norm(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_norm(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.l2_norm(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.l2_norm(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.l2_norm(public.halfvec) TO service_role;



--
-- Name: FUNCTION l2_norm(public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_norm(public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.l2_norm(public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.l2_norm(public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.l2_norm(public.sparsevec) TO service_role;



--
-- Name: FUNCTION l2_normalize(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_normalize(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.l2_normalize(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.l2_normalize(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.l2_normalize(public.halfvec) TO service_role;



--
-- Name: FUNCTION l2_normalize(public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_normalize(public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.l2_normalize(public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.l2_normalize(public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.l2_normalize(public.sparsevec) TO service_role;



--
-- Name: FUNCTION l2_normalize(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.l2_normalize(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.l2_normalize(public.vector) TO anon;

GRANT ALL ON FUNCTION public.l2_normalize(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.l2_normalize(public.vector) TO service_role;



--
-- Name: FUNCTION search_calls_semantic(query_embedding public.vector, match_threshold double precision, match_count integer, filter_status text, filter_open_only boolean); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.search_calls_semantic(query_embedding public.vector, match_threshold double precision, match_count integer, filter_status text, filter_open_only boolean) TO anon;

GRANT ALL ON FUNCTION public.search_calls_semantic(query_embedding public.vector, match_threshold double precision, match_count integer, filter_status text, filter_open_only boolean) TO authenticated;

GRANT ALL ON FUNCTION public.search_calls_semantic(query_embedding public.vector, match_threshold double precision, match_count integer, filter_status text, filter_open_only boolean) TO service_role;



--
-- Name: FUNCTION search_documents(query_embedding public.vector, match_threshold double precision, match_count integer, filter_document_type text, filter_year text); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.search_documents(query_embedding public.vector, match_threshold double precision, match_count integer, filter_document_type text, filter_year text) TO anon;

GRANT ALL ON FUNCTION public.search_documents(query_embedding public.vector, match_threshold double precision, match_count integer, filter_document_type text, filter_year text) TO authenticated;

GRANT ALL ON FUNCTION public.search_documents(query_embedding public.vector, match_threshold double precision, match_count integer, filter_document_type text, filter_year text) TO service_role;



--
-- Name: FUNCTION search_funding_calls(search_query text, filter_programme text, filter_status text, filter_action_type text, filter_cluster text, filter_year integer, include_closed boolean, max_results integer); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.search_funding_calls(search_query text, filter_programme text, filter_status text, filter_action_type text, filter_cluster text, filter_year integer, include_closed boolean, max_results integer) TO anon;

GRANT ALL ON FUNCTION public.search_funding_calls(search_query text, filter_programme text, filter_status text, filter_action_type text, filter_cluster text, filter_year integer, include_closed boolean, max_results integer) TO authenticated;

GRANT ALL ON FUNCTION public.search_funding_calls(search_query text, filter_programme text, filter_status text, filter_action_type text, filter_cluster text, filter_year integer, include_closed boolean, max_results integer) TO service_role;



--
-- Name: FUNCTION set_limit(real); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.set_limit(real) TO postgres;

GRANT ALL ON FUNCTION public.set_limit(real) TO anon;

GRANT ALL ON FUNCTION public.set_limit(real) TO authenticated;

GRANT ALL ON FUNCTION public.set_limit(real) TO service_role;



--
-- Name: FUNCTION show_limit(); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.show_limit() TO postgres;

GRANT ALL ON FUNCTION public.show_limit() TO anon;

GRANT ALL ON FUNCTION public.show_limit() TO authenticated;

GRANT ALL ON FUNCTION public.show_limit() TO service_role;



--
-- Name: FUNCTION show_trgm(text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.show_trgm(text) TO postgres;

GRANT ALL ON FUNCTION public.show_trgm(text) TO anon;

GRANT ALL ON FUNCTION public.show_trgm(text) TO authenticated;

GRANT ALL ON FUNCTION public.show_trgm(text) TO service_role;



--
-- Name: FUNCTION similarity(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.similarity(text, text) TO postgres;

GRANT ALL ON FUNCTION public.similarity(text, text) TO anon;

GRANT ALL ON FUNCTION public.similarity(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.similarity(text, text) TO service_role;



--
-- Name: FUNCTION similarity_dist(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.similarity_dist(text, text) TO postgres;

GRANT ALL ON FUNCTION public.similarity_dist(text, text) TO anon;

GRANT ALL ON FUNCTION public.similarity_dist(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.similarity_dist(text, text) TO service_role;



--
-- Name: FUNCTION similarity_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.similarity_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.similarity_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.similarity_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.similarity_op(text, text) TO service_role;



--
-- Name: FUNCTION sparsevec_cmp(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_cmp(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_cmp(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_cmp(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_cmp(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_eq(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_eq(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_eq(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_eq(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_eq(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_ge(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_ge(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_ge(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_ge(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_ge(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_gt(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_gt(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_gt(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_gt(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_gt(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_l2_squared_distance(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_l2_squared_distance(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_l2_squared_distance(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_l2_squared_distance(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_l2_squared_distance(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_le(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_le(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_le(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_le(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_le(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_lt(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_lt(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_lt(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_lt(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_lt(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_ne(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_ne(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_ne(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_ne(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_ne(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION sparsevec_negative_inner_product(public.sparsevec, public.sparsevec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sparsevec_negative_inner_product(public.sparsevec, public.sparsevec) TO postgres;

GRANT ALL ON FUNCTION public.sparsevec_negative_inner_product(public.sparsevec, public.sparsevec) TO anon;

GRANT ALL ON FUNCTION public.sparsevec_negative_inner_product(public.sparsevec, public.sparsevec) TO authenticated;

GRANT ALL ON FUNCTION public.sparsevec_negative_inner_product(public.sparsevec, public.sparsevec) TO service_role;



--
-- Name: FUNCTION strict_word_similarity(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.strict_word_similarity(text, text) TO postgres;

GRANT ALL ON FUNCTION public.strict_word_similarity(text, text) TO anon;

GRANT ALL ON FUNCTION public.strict_word_similarity(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.strict_word_similarity(text, text) TO service_role;



--
-- Name: FUNCTION strict_word_similarity_commutator_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.strict_word_similarity_commutator_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.strict_word_similarity_commutator_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.strict_word_similarity_commutator_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.strict_word_similarity_commutator_op(text, text) TO service_role;



--
-- Name: FUNCTION strict_word_similarity_dist_commutator_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_commutator_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_commutator_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_commutator_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_commutator_op(text, text) TO service_role;



--
-- Name: FUNCTION strict_word_similarity_dist_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.strict_word_similarity_dist_op(text, text) TO service_role;



--
-- Name: FUNCTION strict_word_similarity_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.strict_word_similarity_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.strict_word_similarity_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.strict_word_similarity_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.strict_word_similarity_op(text, text) TO service_role;



--
-- Name: FUNCTION subvector(public.halfvec, integer, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.subvector(public.halfvec, integer, integer) TO postgres;

GRANT ALL ON FUNCTION public.subvector(public.halfvec, integer, integer) TO anon;

GRANT ALL ON FUNCTION public.subvector(public.halfvec, integer, integer) TO authenticated;

GRANT ALL ON FUNCTION public.subvector(public.halfvec, integer, integer) TO service_role;



--
-- Name: FUNCTION subvector(public.vector, integer, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.subvector(public.vector, integer, integer) TO postgres;

GRANT ALL ON FUNCTION public.subvector(public.vector, integer, integer) TO anon;

GRANT ALL ON FUNCTION public.subvector(public.vector, integer, integer) TO authenticated;

GRANT ALL ON FUNCTION public.subvector(public.vector, integer, integer) TO service_role;



--
-- Name: FUNCTION update_funding_calls_timestamp(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_funding_calls_timestamp() TO anon;

GRANT ALL ON FUNCTION public.update_funding_calls_timestamp() TO authenticated;

GRANT ALL ON FUNCTION public.update_funding_calls_timestamp() TO service_role;



--
-- Name: FUNCTION update_project_embeddings_timestamp(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_project_embeddings_timestamp() TO anon;

GRANT ALL ON FUNCTION public.update_project_embeddings_timestamp() TO authenticated;

GRANT ALL ON FUNCTION public.update_project_embeddings_timestamp() TO service_role;



--
-- Name: FUNCTION update_proposal_completion(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_proposal_completion() TO anon;

GRANT ALL ON FUNCTION public.update_proposal_completion() TO authenticated;

GRANT ALL ON FUNCTION public.update_proposal_completion() TO service_role;



--
-- Name: FUNCTION update_proposal_timestamp(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_proposal_timestamp() TO anon;

GRANT ALL ON FUNCTION public.update_proposal_timestamp() TO authenticated;

GRANT ALL ON FUNCTION public.update_proposal_timestamp() TO service_role;



--
-- Name: FUNCTION update_session_activity(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_session_activity() TO anon;

GRANT ALL ON FUNCTION public.update_session_activity() TO authenticated;

GRANT ALL ON FUNCTION public.update_session_activity() TO service_role;



--
-- Name: FUNCTION vector_accum(double precision[], public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_accum(double precision[], public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_accum(double precision[], public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_accum(double precision[], public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_accum(double precision[], public.vector) TO service_role;



--
-- Name: FUNCTION vector_add(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_add(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_add(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_add(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_add(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_avg(double precision[]); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_avg(double precision[]) TO postgres;

GRANT ALL ON FUNCTION public.vector_avg(double precision[]) TO anon;

GRANT ALL ON FUNCTION public.vector_avg(double precision[]) TO authenticated;

GRANT ALL ON FUNCTION public.vector_avg(double precision[]) TO service_role;



--
-- Name: FUNCTION vector_cmp(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_cmp(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_cmp(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_cmp(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_cmp(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_combine(double precision[], double precision[]); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_combine(double precision[], double precision[]) TO postgres;

GRANT ALL ON FUNCTION public.vector_combine(double precision[], double precision[]) TO anon;

GRANT ALL ON FUNCTION public.vector_combine(double precision[], double precision[]) TO authenticated;

GRANT ALL ON FUNCTION public.vector_combine(double precision[], double precision[]) TO service_role;



--
-- Name: FUNCTION vector_concat(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_concat(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_concat(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_concat(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_concat(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_dims(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_dims(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.vector_dims(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.vector_dims(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.vector_dims(public.halfvec) TO service_role;



--
-- Name: FUNCTION vector_dims(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_dims(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_dims(public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_dims(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_dims(public.vector) TO service_role;



--
-- Name: FUNCTION vector_eq(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_eq(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_eq(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_eq(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_eq(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_ge(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_ge(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_ge(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_ge(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_ge(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_gt(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_gt(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_gt(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_gt(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_gt(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_l2_squared_distance(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_l2_squared_distance(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_l2_squared_distance(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_l2_squared_distance(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_l2_squared_distance(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_le(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_le(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_le(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_le(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_le(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_lt(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_lt(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_lt(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_lt(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_lt(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_mul(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_mul(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_mul(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_mul(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_mul(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_ne(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_ne(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_ne(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_ne(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_ne(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_negative_inner_product(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_negative_inner_product(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_negative_inner_product(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_negative_inner_product(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_negative_inner_product(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_norm(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_norm(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_norm(public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_norm(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_norm(public.vector) TO service_role;



--
-- Name: FUNCTION vector_spherical_distance(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_spherical_distance(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_spherical_distance(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_spherical_distance(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_spherical_distance(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION vector_sub(public.vector, public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.vector_sub(public.vector, public.vector) TO postgres;

GRANT ALL ON FUNCTION public.vector_sub(public.vector, public.vector) TO anon;

GRANT ALL ON FUNCTION public.vector_sub(public.vector, public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.vector_sub(public.vector, public.vector) TO service_role;



--
-- Name: FUNCTION word_similarity(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.word_similarity(text, text) TO postgres;

GRANT ALL ON FUNCTION public.word_similarity(text, text) TO anon;

GRANT ALL ON FUNCTION public.word_similarity(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.word_similarity(text, text) TO service_role;



--
-- Name: FUNCTION word_similarity_commutator_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.word_similarity_commutator_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.word_similarity_commutator_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.word_similarity_commutator_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.word_similarity_commutator_op(text, text) TO service_role;



--
-- Name: FUNCTION word_similarity_dist_commutator_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.word_similarity_dist_commutator_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.word_similarity_dist_commutator_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.word_similarity_dist_commutator_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.word_similarity_dist_commutator_op(text, text) TO service_role;



--
-- Name: FUNCTION word_similarity_dist_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.word_similarity_dist_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.word_similarity_dist_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.word_similarity_dist_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.word_similarity_dist_op(text, text) TO service_role;



--
-- Name: FUNCTION word_similarity_op(text, text); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.word_similarity_op(text, text) TO postgres;

GRANT ALL ON FUNCTION public.word_similarity_op(text, text) TO anon;

GRANT ALL ON FUNCTION public.word_similarity_op(text, text) TO authenticated;

GRANT ALL ON FUNCTION public.word_similarity_op(text, text) TO service_role;



--
-- Name: FUNCTION apply_rls(wal jsonb, max_record_bytes integer); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO postgres;

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO dashboard_user;

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO anon;

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO authenticated;

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO service_role;

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO supabase_realtime_admin;



--
-- Name: FUNCTION broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text) TO postgres;

GRANT ALL ON FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text) TO dashboard_user;



--
-- Name: FUNCTION build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO postgres;

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO dashboard_user;

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO anon;

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO authenticated;

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO service_role;

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO supabase_realtime_admin;



--
-- Name: FUNCTION "cast"(val text, type_ regtype); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO postgres;

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO dashboard_user;

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO anon;

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO authenticated;

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO service_role;

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO supabase_realtime_admin;



--
-- Name: FUNCTION check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO postgres;

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO dashboard_user;

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO anon;

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO authenticated;

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO service_role;

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO supabase_realtime_admin;



--
-- Name: FUNCTION is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO postgres;

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO dashboard_user;

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO anon;

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO authenticated;

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO service_role;

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO supabase_realtime_admin;



--
-- Name: FUNCTION list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO postgres;

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO dashboard_user;

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO anon;

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO authenticated;

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO service_role;

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO supabase_realtime_admin;



--
-- Name: FUNCTION quote_wal2json(entity regclass); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO postgres;

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO dashboard_user;

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO anon;

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO authenticated;

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO service_role;

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO supabase_realtime_admin;



--
-- Name: FUNCTION send(payload jsonb, event text, topic text, private boolean); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean) TO postgres;

GRANT ALL ON FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean) TO dashboard_user;



--
-- Name: FUNCTION subscription_check_filters(); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO postgres;

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO dashboard_user;

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO anon;

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO authenticated;

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO service_role;

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO supabase_realtime_admin;



--
-- Name: FUNCTION to_regrole(role_name text); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO postgres;

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO dashboard_user;

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO anon;

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO authenticated;

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO service_role;

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO supabase_realtime_admin;



--
-- Name: FUNCTION topic(); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION realtime.topic() TO postgres;

GRANT ALL ON FUNCTION realtime.topic() TO dashboard_user;



--
-- Name: FUNCTION http_request(); Type: ACL; Schema: supabase_functions; Owner: supabase_functions_admin
--

REVOKE ALL ON FUNCTION supabase_functions.http_request() FROM PUBLIC;

GRANT ALL ON FUNCTION supabase_functions.http_request() TO postgres;

GRANT ALL ON FUNCTION supabase_functions.http_request() TO anon;

GRANT ALL ON FUNCTION supabase_functions.http_request() TO authenticated;

GRANT ALL ON FUNCTION supabase_functions.http_request() TO service_role;



--
-- Name: FUNCTION avg(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.avg(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.avg(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.avg(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.avg(public.halfvec) TO service_role;



--
-- Name: FUNCTION avg(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.avg(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.avg(public.vector) TO anon;

GRANT ALL ON FUNCTION public.avg(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.avg(public.vector) TO service_role;



--
-- Name: FUNCTION sum(public.halfvec); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sum(public.halfvec) TO postgres;

GRANT ALL ON FUNCTION public.sum(public.halfvec) TO anon;

GRANT ALL ON FUNCTION public.sum(public.halfvec) TO authenticated;

GRANT ALL ON FUNCTION public.sum(public.halfvec) TO service_role;



--
-- Name: FUNCTION sum(public.vector); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION public.sum(public.vector) TO postgres;

GRANT ALL ON FUNCTION public.sum(public.vector) TO anon;

GRANT ALL ON FUNCTION public.sum(public.vector) TO authenticated;

GRANT ALL ON FUNCTION public.sum(public.vector) TO service_role;



--
-- Name: TABLE audit_log_entries; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.audit_log_entries TO dashboard_user;

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.audit_log_entries TO postgres;

GRANT SELECT ON TABLE auth.audit_log_entries TO postgres WITH GRANT OPTION;



--
-- Name: TABLE flow_state; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.flow_state TO postgres;

GRANT SELECT ON TABLE auth.flow_state TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.flow_state TO dashboard_user;



--
-- Name: TABLE identities; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.identities TO postgres;

GRANT SELECT ON TABLE auth.identities TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.identities TO dashboard_user;



--
-- Name: TABLE instances; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.instances TO dashboard_user;

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.instances TO postgres;

GRANT SELECT ON TABLE auth.instances TO postgres WITH GRANT OPTION;



--
-- Name: TABLE mfa_amr_claims; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.mfa_amr_claims TO postgres;

GRANT SELECT ON TABLE auth.mfa_amr_claims TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.mfa_amr_claims TO dashboard_user;



--
-- Name: TABLE mfa_challenges; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.mfa_challenges TO postgres;

GRANT SELECT ON TABLE auth.mfa_challenges TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.mfa_challenges TO dashboard_user;



--
-- Name: TABLE mfa_factors; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.mfa_factors TO postgres;

GRANT SELECT ON TABLE auth.mfa_factors TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.mfa_factors TO dashboard_user;



--
-- Name: TABLE one_time_tokens; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.one_time_tokens TO postgres;

GRANT SELECT ON TABLE auth.one_time_tokens TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.one_time_tokens TO dashboard_user;



--
-- Name: TABLE refresh_tokens; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.refresh_tokens TO dashboard_user;

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.refresh_tokens TO postgres;

GRANT SELECT ON TABLE auth.refresh_tokens TO postgres WITH GRANT OPTION;



--
-- Name: SEQUENCE refresh_tokens_id_seq; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON SEQUENCE auth.refresh_tokens_id_seq TO dashboard_user;

GRANT ALL ON SEQUENCE auth.refresh_tokens_id_seq TO postgres;



--
-- Name: TABLE saml_providers; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.saml_providers TO postgres;

GRANT SELECT ON TABLE auth.saml_providers TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.saml_providers TO dashboard_user;



--
-- Name: TABLE saml_relay_states; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.saml_relay_states TO postgres;

GRANT SELECT ON TABLE auth.saml_relay_states TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.saml_relay_states TO dashboard_user;



--
-- Name: TABLE schema_migrations; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.schema_migrations TO dashboard_user;

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.schema_migrations TO postgres;

GRANT SELECT ON TABLE auth.schema_migrations TO postgres WITH GRANT OPTION;



--
-- Name: TABLE sessions; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.sessions TO postgres;

GRANT SELECT ON TABLE auth.sessions TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.sessions TO dashboard_user;



--
-- Name: TABLE sso_domains; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.sso_domains TO postgres;

GRANT SELECT ON TABLE auth.sso_domains TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.sso_domains TO dashboard_user;



--
-- Name: TABLE sso_providers; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.sso_providers TO postgres;

GRANT SELECT ON TABLE auth.sso_providers TO postgres WITH GRANT OPTION;

GRANT ALL ON TABLE auth.sso_providers TO dashboard_user;



--
-- Name: TABLE users; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.users TO dashboard_user;

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.users TO postgres;

GRANT SELECT ON TABLE auth.users TO postgres WITH GRANT OPTION;



--
-- Name: TABLE pg_stat_statements; Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON TABLE extensions.pg_stat_statements TO postgres WITH GRANT OPTION;



--
-- Name: TABLE pg_stat_statements_info; Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON TABLE extensions.pg_stat_statements_info TO postgres WITH GRANT OPTION;



--
-- Name: TABLE decrypted_key; Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON TABLE pgsodium.decrypted_key TO pgsodium_keyholder;



--
-- Name: TABLE masking_rule; Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON TABLE pgsodium.masking_rule TO pgsodium_keyholder;



--
-- Name: TABLE mask_columns; Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON TABLE pgsodium.mask_columns TO pgsodium_keyholder;



--
-- Name: TABLE funding_calls; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.funding_calls TO anon;

GRANT ALL ON TABLE public.funding_calls TO authenticated;

GRANT ALL ON TABLE public.funding_calls TO service_role;



--
-- Name: TABLE active_funding_calls; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.active_funding_calls TO anon;

GRANT ALL ON TABLE public.active_funding_calls TO authenticated;

GRANT ALL ON TABLE public.active_funding_calls TO service_role;



--
-- Name: TABLE proposal_sessions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposal_sessions TO anon;

GRANT ALL ON TABLE public.proposal_sessions TO authenticated;

GRANT ALL ON TABLE public.proposal_sessions TO service_role;



--
-- Name: TABLE proposals; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposals TO anon;

GRANT ALL ON TABLE public.proposals TO authenticated;

GRANT ALL ON TABLE public.proposals TO service_role;



--
-- Name: TABLE active_sessions_overview; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.active_sessions_overview TO anon;

GRANT ALL ON TABLE public.active_sessions_overview TO authenticated;

GRANT ALL ON TABLE public.active_sessions_overview TO service_role;



--
-- Name: SEQUENCE call_document_chunks_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.call_document_chunks_id_seq TO anon;

GRANT ALL ON SEQUENCE public.call_document_chunks_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.call_document_chunks_id_seq TO service_role;



--
-- Name: TABLE call_document_mappings; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.call_document_mappings TO anon;

GRANT ALL ON TABLE public.call_document_mappings TO authenticated;

GRANT ALL ON TABLE public.call_document_mappings TO service_role;



--
-- Name: TABLE shared_document_chunks; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.shared_document_chunks TO anon;

GRANT ALL ON TABLE public.shared_document_chunks TO authenticated;

GRANT ALL ON TABLE public.shared_document_chunks TO service_role;



--
-- Name: TABLE shared_documents; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.shared_documents TO anon;

GRANT ALL ON TABLE public.shared_documents TO authenticated;

GRANT ALL ON TABLE public.shared_documents TO service_role;



--
-- Name: TABLE call_document_chunks_view; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.call_document_chunks_view TO anon;

GRANT ALL ON TABLE public.call_document_chunks_view TO authenticated;

GRANT ALL ON TABLE public.call_document_chunks_view TO service_role;



--
-- Name: SEQUENCE call_document_mappings_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.call_document_mappings_id_seq TO anon;

GRANT ALL ON SEQUENCE public.call_document_mappings_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.call_document_mappings_id_seq TO service_role;



--
-- Name: SEQUENCE call_documents_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.call_documents_id_seq TO anon;

GRANT ALL ON SEQUENCE public.call_documents_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.call_documents_id_seq TO service_role;



--
-- Name: TABLE call_metadata; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.call_metadata TO anon;

GRANT ALL ON TABLE public.call_metadata TO authenticated;

GRANT ALL ON TABLE public.call_metadata TO service_role;



--
-- Name: SEQUENCE call_metadata_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.call_metadata_id_seq TO anon;

GRANT ALL ON SEQUENCE public.call_metadata_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.call_metadata_id_seq TO service_role;



--
-- Name: TABLE citations; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.citations TO anon;

GRANT ALL ON TABLE public.citations TO authenticated;

GRANT ALL ON TABLE public.citations TO service_role;



--
-- Name: SEQUENCE citations_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.citations_id_seq TO anon;

GRANT ALL ON SEQUENCE public.citations_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.citations_id_seq TO service_role;



--
-- Name: TABLE client; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.client TO anon;

GRANT ALL ON TABLE public.client TO authenticated;

GRANT ALL ON TABLE public.client TO service_role;



--
-- Name: TABLE client_collaboration; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.client_collaboration TO anon;

GRANT ALL ON TABLE public.client_collaboration TO authenticated;

GRANT ALL ON TABLE public.client_collaboration TO service_role;



--
-- Name: SEQUENCE client_collaboration_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.client_collaboration_id_seq TO anon;

GRANT ALL ON SEQUENCE public.client_collaboration_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.client_collaboration_id_seq TO service_role;



--
-- Name: SEQUENCE client_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.client_id_seq TO anon;

GRANT ALL ON SEQUENCE public.client_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.client_id_seq TO service_role;



--
-- Name: TABLE collaboration; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.collaboration TO anon;

GRANT ALL ON TABLE public.collaboration TO authenticated;

GRANT ALL ON TABLE public.collaboration TO service_role;



--
-- Name: SEQUENCE collaboration_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.collaboration_id_seq TO anon;

GRANT ALL ON SEQUENCE public.collaboration_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.collaboration_id_seq TO service_role;



--
-- Name: TABLE compliance_checks; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.compliance_checks TO anon;

GRANT ALL ON TABLE public.compliance_checks TO authenticated;

GRANT ALL ON TABLE public.compliance_checks TO service_role;



--
-- Name: SEQUENCE compliance_checks_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.compliance_checks_id_seq TO anon;

GRANT ALL ON SEQUENCE public.compliance_checks_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.compliance_checks_id_seq TO service_role;



--
-- Name: TABLE conversation; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.conversation TO anon;

GRANT ALL ON TABLE public.conversation TO authenticated;

GRANT ALL ON TABLE public.conversation TO service_role;



--
-- Name: TABLE conversation_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.conversation_analytics TO anon;

GRANT ALL ON TABLE public.conversation_analytics TO authenticated;

GRANT ALL ON TABLE public.conversation_analytics TO service_role;



--
-- Name: SEQUENCE conversation_analytics_daily_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.conversation_analytics_daily_id_seq TO anon;

GRANT ALL ON SEQUENCE public.conversation_analytics_daily_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.conversation_analytics_daily_id_seq TO service_role;



--
-- Name: SEQUENCE conversation_analytics_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.conversation_analytics_id_seq TO anon;

GRANT ALL ON SEQUENCE public.conversation_analytics_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.conversation_analytics_id_seq TO service_role;



--
-- Name: SEQUENCE conversation_call_context_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.conversation_call_context_id_seq TO anon;

GRANT ALL ON SEQUENCE public.conversation_call_context_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.conversation_call_context_id_seq TO service_role;



--
-- Name: TABLE conversation_facts; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.conversation_facts TO anon;

GRANT ALL ON TABLE public.conversation_facts TO authenticated;

GRANT ALL ON TABLE public.conversation_facts TO service_role;



--
-- Name: SEQUENCE conversation_facts_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.conversation_facts_id_seq TO anon;

GRANT ALL ON SEQUENCE public.conversation_facts_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.conversation_facts_id_seq TO service_role;



--
-- Name: SEQUENCE conversation_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.conversation_id_seq TO anon;

GRANT ALL ON SEQUENCE public.conversation_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.conversation_id_seq TO service_role;



--
-- Name: TABLE conversation_memory; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.conversation_memory TO anon;

GRANT ALL ON TABLE public.conversation_memory TO authenticated;

GRANT ALL ON TABLE public.conversation_memory TO service_role;



--
-- Name: SEQUENCE conversation_memory_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.conversation_memory_id_seq TO anon;

GRANT ALL ON SEQUENCE public.conversation_memory_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.conversation_memory_id_seq TO service_role;



--
-- Name: TABLE document_chunks; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.document_chunks TO anon;

GRANT ALL ON TABLE public.document_chunks TO authenticated;

GRANT ALL ON TABLE public.document_chunks TO service_role;



--
-- Name: TABLE embedding_cache; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.embedding_cache TO anon;

GRANT ALL ON TABLE public.embedding_cache TO authenticated;

GRANT ALL ON TABLE public.embedding_cache TO service_role;



--
-- Name: TABLE entity_cards; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.entity_cards TO anon;

GRANT ALL ON TABLE public.entity_cards TO authenticated;

GRANT ALL ON TABLE public.entity_cards TO service_role;



--
-- Name: SEQUENCE entity_cards_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.entity_cards_id_seq TO anon;

GRANT ALL ON SEQUENCE public.entity_cards_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.entity_cards_id_seq TO service_role;



--
-- Name: SEQUENCE feedback_insights_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.feedback_insights_id_seq TO anon;

GRANT ALL ON SEQUENCE public.feedback_insights_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.feedback_insights_id_seq TO service_role;



--
-- Name: TABLE horizon_documents; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.horizon_documents TO anon;

GRANT ALL ON TABLE public.horizon_documents TO authenticated;

GRANT ALL ON TABLE public.horizon_documents TO service_role;



--
-- Name: TABLE horizon_europe_calls; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.horizon_europe_calls TO anon;

GRANT ALL ON TABLE public.horizon_europe_calls TO authenticated;

GRANT ALL ON TABLE public.horizon_europe_calls TO service_role;



--
-- Name: TABLE improvement_suggestions; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.improvement_suggestions TO anon;

GRANT ALL ON TABLE public.improvement_suggestions TO authenticated;

GRANT ALL ON TABLE public.improvement_suggestions TO service_role;



--
-- Name: SEQUENCE improvement_suggestions_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.improvement_suggestions_id_seq TO anon;

GRANT ALL ON SEQUENCE public.improvement_suggestions_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.improvement_suggestions_id_seq TO service_role;



--
-- Name: TABLE message; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.message TO anon;

GRANT ALL ON TABLE public.message TO authenticated;

GRANT ALL ON TABLE public.message TO service_role;



--
-- Name: SEQUENCE message_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.message_id_seq TO anon;

GRANT ALL ON SEQUENCE public.message_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.message_id_seq TO service_role;



--
-- Name: TABLE organizations; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.organizations TO anon;

GRANT ALL ON TABLE public.organizations TO authenticated;

GRANT ALL ON TABLE public.organizations TO service_role;



--
-- Name: TABLE project_embeddings; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.project_embeddings TO anon;

GRANT ALL ON TABLE public.project_embeddings TO authenticated;

GRANT ALL ON TABLE public.project_embeddings TO service_role;



--
-- Name: TABLE projects; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.projects TO anon;

GRANT ALL ON TABLE public.projects TO authenticated;

GRANT ALL ON TABLE public.projects TO service_role;



--
-- Name: TABLE proposal_activity_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposal_activity_log TO anon;

GRANT ALL ON TABLE public.proposal_activity_log TO authenticated;

GRANT ALL ON TABLE public.proposal_activity_log TO service_role;



--
-- Name: SEQUENCE proposal_activity_log_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_activity_log_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_activity_log_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_activity_log_id_seq TO service_role;



--
-- Name: TABLE proposal_budgets; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposal_budgets TO anon;

GRANT ALL ON TABLE public.proposal_budgets TO authenticated;

GRANT ALL ON TABLE public.proposal_budgets TO service_role;



--
-- Name: SEQUENCE proposal_budgets_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_budgets_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_budgets_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_budgets_id_seq TO service_role;



--
-- Name: TABLE proposal_consortium; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposal_consortium TO anon;

GRANT ALL ON TABLE public.proposal_consortium TO authenticated;

GRANT ALL ON TABLE public.proposal_consortium TO service_role;



--
-- Name: SEQUENCE proposal_consortium_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_consortium_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_consortium_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_consortium_id_seq TO service_role;



--
-- Name: SEQUENCE proposal_deliverables_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_deliverables_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_deliverables_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_deliverables_id_seq TO service_role;



--
-- Name: TABLE proposal_examples; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposal_examples TO anon;

GRANT ALL ON TABLE public.proposal_examples TO authenticated;

GRANT ALL ON TABLE public.proposal_examples TO service_role;



--
-- Name: SEQUENCE proposal_examples_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_examples_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_examples_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_examples_id_seq TO service_role;



--
-- Name: SEQUENCE proposal_milestones_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_milestones_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_milestones_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_milestones_id_seq TO service_role;



--
-- Name: TABLE proposal_overview; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposal_overview TO anon;

GRANT ALL ON TABLE public.proposal_overview TO authenticated;

GRANT ALL ON TABLE public.proposal_overview TO service_role;



--
-- Name: TABLE proposal_sections; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.proposal_sections TO anon;

GRANT ALL ON TABLE public.proposal_sections TO authenticated;

GRANT ALL ON TABLE public.proposal_sections TO service_role;



--
-- Name: SEQUENCE proposal_sections_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_sections_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_sections_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_sections_id_seq TO service_role;



--
-- Name: SEQUENCE proposal_sessions_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_sessions_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_sessions_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_sessions_id_seq TO service_role;



--
-- Name: SEQUENCE proposal_templates_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_templates_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_templates_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_templates_id_seq TO service_role;



--
-- Name: SEQUENCE proposal_work_packages_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposal_work_packages_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposal_work_packages_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposal_work_packages_id_seq TO service_role;



--
-- Name: SEQUENCE proposals_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.proposals_id_seq TO anon;

GRANT ALL ON SEQUENCE public.proposals_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.proposals_id_seq TO service_role;



--
-- Name: TABLE response_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.response_feedback TO anon;

GRANT ALL ON TABLE public.response_feedback TO authenticated;

GRANT ALL ON TABLE public.response_feedback TO service_role;



--
-- Name: SEQUENCE response_feedback_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.response_feedback_id_seq TO anon;

GRANT ALL ON SEQUENCE public.response_feedback_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.response_feedback_id_seq TO service_role;



--
-- Name: SEQUENCE retrieval_cache_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.retrieval_cache_id_seq TO anon;

GRANT ALL ON SEQUENCE public.retrieval_cache_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.retrieval_cache_id_seq TO service_role;



--
-- Name: TABLE schema_migrations; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.schema_migrations TO anon;

GRANT ALL ON TABLE public.schema_migrations TO authenticated;

GRANT ALL ON TABLE public.schema_migrations TO service_role;



--
-- Name: TABLE section_criteria_mapping; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.section_criteria_mapping TO anon;

GRANT ALL ON TABLE public.section_criteria_mapping TO authenticated;

GRANT ALL ON TABLE public.section_criteria_mapping TO service_role;



--
-- Name: SEQUENCE section_criteria_mapping_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.section_criteria_mapping_id_seq TO anon;

GRANT ALL ON SEQUENCE public.section_criteria_mapping_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.section_criteria_mapping_id_seq TO service_role;



--
-- Name: SEQUENCE section_locks_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.section_locks_id_seq TO anon;

GRANT ALL ON SEQUENCE public.section_locks_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.section_locks_id_seq TO service_role;



--
-- Name: TABLE section_quality_summary; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.section_quality_summary TO anon;

GRANT ALL ON TABLE public.section_quality_summary TO authenticated;

GRANT ALL ON TABLE public.section_quality_summary TO service_role;



--
-- Name: TABLE session_activity_summary; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.session_activity_summary TO anon;

GRANT ALL ON TABLE public.session_activity_summary TO authenticated;

GRANT ALL ON TABLE public.session_activity_summary TO service_role;



--
-- Name: SEQUENCE session_messages_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.session_messages_id_seq TO anon;

GRANT ALL ON SEQUENCE public.session_messages_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.session_messages_id_seq TO service_role;



--
-- Name: SEQUENCE shared_document_chunks_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.shared_document_chunks_id_seq TO anon;

GRANT ALL ON SEQUENCE public.shared_document_chunks_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.shared_document_chunks_id_seq TO service_role;



--
-- Name: SEQUENCE shared_documents_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.shared_documents_id_seq TO anon;

GRANT ALL ON SEQUENCE public.shared_documents_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.shared_documents_id_seq TO service_role;



--
-- Name: TABLE tool_combination_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.tool_combination_analytics TO anon;

GRANT ALL ON TABLE public.tool_combination_analytics TO authenticated;

GRANT ALL ON TABLE public.tool_combination_analytics TO service_role;



--
-- Name: SEQUENCE tool_combination_analytics_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.tool_combination_analytics_id_seq TO anon;

GRANT ALL ON SEQUENCE public.tool_combination_analytics_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.tool_combination_analytics_id_seq TO service_role;



--
-- Name: SEQUENCE tool_execution_log_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.tool_execution_log_id_seq TO anon;

GRANT ALL ON SEQUENCE public.tool_execution_log_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.tool_execution_log_id_seq TO service_role;



--
-- Name: SEQUENCE tool_performance_metrics_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.tool_performance_metrics_id_seq TO anon;

GRANT ALL ON SEQUENCE public.tool_performance_metrics_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.tool_performance_metrics_id_seq TO service_role;



--
-- Name: TABLE tool_usage_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.tool_usage_analytics TO anon;

GRANT ALL ON TABLE public.tool_usage_analytics TO authenticated;

GRANT ALL ON TABLE public.tool_usage_analytics TO service_role;



--
-- Name: SEQUENCE tool_usage_analytics_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.tool_usage_analytics_id_seq TO anon;

GRANT ALL ON SEQUENCE public.tool_usage_analytics_id_seq TO authenticated;

GRANT ALL ON SEQUENCE public.tool_usage_analytics_id_seq TO service_role;



--
-- Name: TABLE v_conversation_analytics_24h; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_conversation_analytics_24h TO anon;

GRANT ALL ON TABLE public.v_conversation_analytics_24h TO authenticated;

GRANT ALL ON TABLE public.v_conversation_analytics_24h TO service_role;



--
-- Name: TABLE v_embedding_coverage; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_embedding_coverage TO anon;

GRANT ALL ON TABLE public.v_embedding_coverage TO authenticated;

GRANT ALL ON TABLE public.v_embedding_coverage TO service_role;



--
-- Name: TABLE v_embedding_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_embedding_stats TO anon;

GRANT ALL ON TABLE public.v_embedding_stats TO authenticated;

GRANT ALL ON TABLE public.v_embedding_stats TO service_role;



--
-- Name: TABLE v_feedback_metrics_7d; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_feedback_metrics_7d TO anon;

GRANT ALL ON TABLE public.v_feedback_metrics_7d TO authenticated;

GRANT ALL ON TABLE public.v_feedback_metrics_7d TO service_role;



--
-- Name: TABLE v_popular_tool_combos; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_popular_tool_combos TO anon;

GRANT ALL ON TABLE public.v_popular_tool_combos TO authenticated;

GRANT ALL ON TABLE public.v_popular_tool_combos TO service_role;



--
-- Name: TABLE v_question_patterns; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_question_patterns TO anon;

GRANT ALL ON TABLE public.v_question_patterns TO authenticated;

GRANT ALL ON TABLE public.v_question_patterns TO service_role;



--
-- Name: TABLE v_tool_feedback; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_tool_feedback TO anon;

GRANT ALL ON TABLE public.v_tool_feedback TO authenticated;

GRANT ALL ON TABLE public.v_tool_feedback TO service_role;



--
-- Name: TABLE v_tool_performance_24h; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_tool_performance_24h TO anon;

GRANT ALL ON TABLE public.v_tool_performance_24h TO authenticated;

GRANT ALL ON TABLE public.v_tool_performance_24h TO service_role;



--
-- Name: TABLE v_tool_usage_analytics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.v_tool_usage_analytics TO anon;

GRANT ALL ON TABLE public.v_tool_usage_analytics TO authenticated;

GRANT ALL ON TABLE public.v_tool_usage_analytics TO service_role;



--
-- Name: TABLE messages; Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON TABLE realtime.messages TO postgres;

GRANT ALL ON TABLE realtime.messages TO dashboard_user;

GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO anon;

GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO authenticated;

GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO service_role;



--
-- Name: TABLE messages_2025_11_17; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.messages_2025_11_17 TO postgres;

GRANT ALL ON TABLE realtime.messages_2025_11_17 TO dashboard_user;



--
-- Name: TABLE messages_2025_11_18; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.messages_2025_11_18 TO postgres;

GRANT ALL ON TABLE realtime.messages_2025_11_18 TO dashboard_user;



--
-- Name: TABLE messages_2025_11_19; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.messages_2025_11_19 TO postgres;

GRANT ALL ON TABLE realtime.messages_2025_11_19 TO dashboard_user;



--
-- Name: TABLE messages_2025_11_20; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.messages_2025_11_20 TO postgres;

GRANT ALL ON TABLE realtime.messages_2025_11_20 TO dashboard_user;



--
-- Name: TABLE messages_2025_11_21; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.messages_2025_11_21 TO postgres;

GRANT ALL ON TABLE realtime.messages_2025_11_21 TO dashboard_user;



--
-- Name: TABLE messages_2025_11_22; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.messages_2025_11_22 TO postgres;

GRANT ALL ON TABLE realtime.messages_2025_11_22 TO dashboard_user;



--
-- Name: TABLE schema_migrations; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.schema_migrations TO postgres;

GRANT ALL ON TABLE realtime.schema_migrations TO dashboard_user;

GRANT SELECT ON TABLE realtime.schema_migrations TO anon;

GRANT SELECT ON TABLE realtime.schema_migrations TO authenticated;

GRANT SELECT ON TABLE realtime.schema_migrations TO service_role;

GRANT ALL ON TABLE realtime.schema_migrations TO supabase_realtime_admin;



--
-- Name: TABLE subscription; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.subscription TO postgres;

GRANT ALL ON TABLE realtime.subscription TO dashboard_user;

GRANT SELECT ON TABLE realtime.subscription TO anon;

GRANT SELECT ON TABLE realtime.subscription TO authenticated;

GRANT SELECT ON TABLE realtime.subscription TO service_role;

GRANT ALL ON TABLE realtime.subscription TO supabase_realtime_admin;



--
-- Name: SEQUENCE subscription_id_seq; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO postgres;

GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO dashboard_user;

GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO anon;

GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO authenticated;

GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO service_role;

GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO supabase_realtime_admin;



--
-- Name: TABLE buckets; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.buckets TO anon;

GRANT ALL ON TABLE storage.buckets TO authenticated;

GRANT ALL ON TABLE storage.buckets TO service_role;

GRANT ALL ON TABLE storage.buckets TO postgres;



--
-- Name: TABLE migrations; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.migrations TO anon;

GRANT ALL ON TABLE storage.migrations TO authenticated;

GRANT ALL ON TABLE storage.migrations TO service_role;

GRANT ALL ON TABLE storage.migrations TO postgres;



--
-- Name: TABLE objects; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.objects TO anon;

GRANT ALL ON TABLE storage.objects TO authenticated;

GRANT ALL ON TABLE storage.objects TO service_role;

GRANT ALL ON TABLE storage.objects TO postgres;



--
-- Name: TABLE prefixes; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.prefixes TO service_role;

GRANT ALL ON TABLE storage.prefixes TO authenticated;

GRANT ALL ON TABLE storage.prefixes TO anon;



--
-- Name: TABLE s3_multipart_uploads; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.s3_multipart_uploads TO service_role;

GRANT SELECT ON TABLE storage.s3_multipart_uploads TO authenticated;

GRANT SELECT ON TABLE storage.s3_multipart_uploads TO anon;



--
-- Name: TABLE s3_multipart_uploads_parts; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.s3_multipart_uploads_parts TO service_role;

GRANT SELECT ON TABLE storage.s3_multipart_uploads_parts TO authenticated;

GRANT SELECT ON TABLE storage.s3_multipart_uploads_parts TO anon;



--
-- Name: TABLE hooks; Type: ACL; Schema: supabase_functions; Owner: supabase_functions_admin
--

GRANT ALL ON TABLE supabase_functions.hooks TO postgres;

GRANT ALL ON TABLE supabase_functions.hooks TO anon;

GRANT ALL ON TABLE supabase_functions.hooks TO authenticated;

GRANT ALL ON TABLE supabase_functions.hooks TO service_role;



--
-- Name: SEQUENCE hooks_id_seq; Type: ACL; Schema: supabase_functions; Owner: supabase_functions_admin
--

GRANT ALL ON SEQUENCE supabase_functions.hooks_id_seq TO postgres;

GRANT ALL ON SEQUENCE supabase_functions.hooks_id_seq TO anon;

GRANT ALL ON SEQUENCE supabase_functions.hooks_id_seq TO authenticated;

GRANT ALL ON SEQUENCE supabase_functions.hooks_id_seq TO service_role;



--
-- Name: TABLE migrations; Type: ACL; Schema: supabase_functions; Owner: supabase_functions_admin
--

GRANT ALL ON TABLE supabase_functions.migrations TO postgres;

GRANT ALL ON TABLE supabase_functions.migrations TO anon;

GRANT ALL ON TABLE supabase_functions.migrations TO authenticated;

GRANT ALL ON TABLE supabase_functions.migrations TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON SEQUENCES  TO dashboard_user;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON FUNCTIONS  TO dashboard_user;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON TABLES  TO dashboard_user;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON SEQUENCES  TO postgres WITH GRANT OPTION;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON FUNCTIONS  TO postgres WITH GRANT OPTION;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON TABLES  TO postgres WITH GRANT OPTION;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: pgsodium; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium GRANT ALL ON SEQUENCES  TO pgsodium_keyholder;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: pgsodium; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium GRANT ALL ON TABLES  TO pgsodium_keyholder;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: pgsodium_masks; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium_masks GRANT ALL ON SEQUENCES  TO pgsodium_keyiduser;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: pgsodium_masks; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium_masks GRANT ALL ON FUNCTIONS  TO pgsodium_keyiduser;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: pgsodium_masks; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium_masks GRANT ALL ON TABLES  TO pgsodium_keyiduser;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON SEQUENCES  TO dashboard_user;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON FUNCTIONS  TO dashboard_user;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON TABLES  TO dashboard_user;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: supabase_functions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON SEQUENCES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON SEQUENCES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON SEQUENCES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON SEQUENCES  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: supabase_functions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON FUNCTIONS  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON FUNCTIONS  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON FUNCTIONS  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON FUNCTIONS  TO service_role;



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: supabase_functions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON TABLES  TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON TABLES  TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON TABLES  TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA supabase_functions GRANT ALL ON TABLES  TO service_role;



--
-- Name: issue_graphql_placeholder; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER issue_graphql_placeholder ON sql_drop
         WHEN TAG IN ('DROP EXTENSION')
   EXECUTE FUNCTION extensions.set_graphql_placeholder();


--
-- Name: issue_pg_cron_access; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER issue_pg_cron_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_cron_access();


--
-- Name: issue_pg_graphql_access; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER issue_pg_graphql_access ON ddl_command_end
         WHEN TAG IN ('CREATE FUNCTION')
   EXECUTE FUNCTION extensions.grant_pg_graphql_access();


--
-- Name: issue_pg_net_access; Type: EVENT TRIGGER; Schema: -; Owner: postgres
--

CREATE EVENT TRIGGER issue_pg_net_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_net_access();


--
-- Name: pgrst_ddl_watch; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER pgrst_ddl_watch ON ddl_command_end
   EXECUTE FUNCTION extensions.pgrst_ddl_watch();


--
-- Name: pgrst_drop_watch; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER pgrst_drop_watch ON sql_drop
   EXECUTE FUNCTION extensions.pgrst_drop_watch();


--
-- PostgreSQL database dump complete
--

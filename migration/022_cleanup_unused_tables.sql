-- Database Cleanup Migration
-- Removes unused legacy tables and fixes foreign key constraints
-- Created: 2026-01-05
--
-- Tables being removed:
-- 1. client - Legacy user table (not used, app uses user_id integers directly)
-- 2. client_collaboration - Legacy join table (not used)
-- 3. collaboration - Legacy group table (collaboration_service uses Redis)
--
-- Foreign key constraints being removed:
-- - conversation.user_id -> client.id (will use integer user_id directly)
-- - conversation.collaboration_id -> collaboration.id (not used)
-- - message.user_id -> client.id (will use integer user_id directly)

BEGIN;

-- ============================================================================
-- STEP 1: Remove foreign key constraints from conversation table
-- ============================================================================

-- Find and drop FK constraint for conversation.user_id -> client.id
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_name = 'conversation'
        AND kcu.column_name = 'user_id'
        AND ccu.table_name = 'client'
        AND tc.constraint_type = 'FOREIGN KEY';

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE conversation DROP CONSTRAINT ' || constraint_name;
        RAISE NOTICE 'Dropped FK constraint % from conversation.user_id', constraint_name;
    END IF;
END $$;

-- Find and drop FK constraint for conversation.collaboration_id -> collaboration.id
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_name = 'conversation'
        AND kcu.column_name = 'collaboration_id'
        AND ccu.table_name = 'collaboration'
        AND tc.constraint_type = 'FOREIGN KEY';

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE conversation DROP CONSTRAINT ' || constraint_name;
        RAISE NOTICE 'Dropped FK constraint % from conversation.collaboration_id', constraint_name;
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Remove foreign key constraints from message table
-- ============================================================================

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_name = 'message'
        AND kcu.column_name = 'user_id'
        AND ccu.table_name = 'client'
        AND tc.constraint_type = 'FOREIGN KEY';

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE message DROP CONSTRAINT ' || constraint_name;
        RAISE NOTICE 'Dropped FK constraint % from message.user_id', constraint_name;
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Drop the collaboration_id column from conversation (not used)
-- ============================================================================

ALTER TABLE conversation DROP COLUMN IF EXISTS collaboration_id;

-- ============================================================================
-- STEP 4: Drop unused legacy tables
-- ============================================================================

-- Drop client_collaboration first (has FK to both client and collaboration)
DROP TABLE IF EXISTS client_collaboration CASCADE;

-- Drop collaboration table
DROP TABLE IF EXISTS collaboration CASCADE;

-- Drop client table (legacy user table)
DROP TABLE IF EXISTS client CASCADE;

-- ============================================================================
-- STEP 5: Log the migration
-- ============================================================================

INSERT INTO schema_migrations (version)
VALUES ('022_cleanup_unused_tables')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- ============================================================================
-- Verification query (run after migration)
-- ============================================================================
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

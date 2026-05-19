-- SQL Script to clean up unused/deprecated tables in the MAP-IT database.
-- These tables have 0 references in the codebase and are safe to drop.

BEGIN;

DROP TABLE IF EXISTS call_document_chunks CASCADE;
DROP TABLE IF EXISTS call_documents CASCADE;
DROP TABLE IF EXISTS conversation_analytics_daily CASCADE;
DROP TABLE IF EXISTS conversation_call_context CASCADE;
DROP TABLE IF EXISTS feedback_insights CASCADE;
DROP TABLE IF EXISTS ingestion_jobs CASCADE;
DROP TABLE IF EXISTS proposal_deliverables CASCADE;
DROP TABLE IF EXISTS proposal_milestones CASCADE;
DROP TABLE IF EXISTS proposal_templates CASCADE;
DROP TABLE IF EXISTS proposal_work_packages CASCADE;
DROP TABLE IF EXISTS retrieval_cache CASCADE;
DROP TABLE IF EXISTS search_queries CASCADE;
DROP TABLE IF EXISTS section_locks CASCADE;
DROP TABLE IF EXISTS session_messages CASCADE;
DROP TABLE IF EXISTS tool_execution_log CASCADE;
DROP TABLE IF EXISTS tool_performance_metrics CASCADE;

COMMIT;

SELECT 'Clean-up complete: 16 unused tables dropped.' AS status;

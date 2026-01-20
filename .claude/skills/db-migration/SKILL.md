# MAPIT Database Migration Skill

This skill documents database migration patterns for the MAPIT AI project using PostgreSQL.

## Migration Location

```
migration/
├── 003_call_documents_tables.sql
├── 004_shared_documents_architecture.sql
├── 008_tool_analytics.sql
├── 009_user_feedback.sql
├── 015_proposal_sessions.sql
├── 019_tenants.sql
├── 021_conversation_analytics.sql
├── 022_cleanup_unused_tables.sql
└── ...
```

---

## Naming Convention

**Format**: `NNN_descriptive_name.sql`

- `NNN`: Sequential 3-digit number (003-022+)
- `descriptive_name`: snake_case description of what's being added/changed

**Examples**:
- `008_tool_analytics.sql` - Tool usage tracking tables
- `015_proposal_sessions.sql` - Session management
- `022_cleanup_unused_tables.sql` - Legacy cleanup

---

## Migration File Template

```sql
-- ================================================================
-- [MIGRATION TITLE] - [FEATURE NAME]
-- ================================================================
-- This migration adds [feature description].
--
-- Purpose:
-- - [Purpose 1]
-- - [Purpose 2]
-- - [Purpose 3]
--
-- Tables Created:
-- - table_name_1
-- - table_name_2
--
-- Author: [Name/AI Assistant]
-- Date: [YYYY-MM-DD]
-- Version: 1.0
-- ================================================================

-- ============================================================================
-- 1. CREATE TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS table_name (
    -- Primary key
    id SERIAL PRIMARY KEY,
    -- Or UUID for multi-tenancy
    -- id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys
    parent_id INTEGER REFERENCES parent_table(id) ON DELETE CASCADE,

    -- Core fields
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Status with CHECK constraint
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'pending')),

    -- JSONB for flexible metadata
    metadata JSONB DEFAULT '{}',

    -- Arrays
    tags TEXT[],

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add comments
COMMENT ON TABLE table_name IS 'Description of table purpose';
COMMENT ON COLUMN table_name.metadata IS 'Flexible JSON metadata field';

-- ============================================================================
-- 2. CREATE INDEXES
-- ============================================================================

-- Simple indexes
CREATE INDEX IF NOT EXISTS idx_table_name_column
    ON table_name(column_name);

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_table_name_col1_col2
    ON table_name(column1, column2);

-- Partial indexes (filtered)
CREATE INDEX IF NOT EXISTS idx_table_name_active
    ON table_name(column_name)
    WHERE status = 'active';

-- Full-text search (GIN)
CREATE INDEX IF NOT EXISTS idx_table_name_text_search
    ON table_name USING gin(to_tsvector('english', text_column));

-- Array indexes (GIN)
CREATE INDEX IF NOT EXISTS idx_table_name_tags
    ON table_name USING GIN(tags);

-- ============================================================================
-- 3. CREATE VIEWS (Optional)
-- ============================================================================

CREATE OR REPLACE VIEW v_table_summary AS
SELECT
    t.id,
    t.name,
    COUNT(c.id) as child_count
FROM table_name t
LEFT JOIN child_table c ON t.id = c.parent_id
GROUP BY t.id, t.name;

-- ============================================================================
-- 4. CREATE FUNCTIONS (Optional)
-- ============================================================================

CREATE OR REPLACE FUNCTION update_modified_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 5. CREATE TRIGGERS (Optional)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trigger_update_timestamp'
    ) THEN
        CREATE TRIGGER trigger_update_timestamp
            BEFORE UPDATE ON table_name
            FOR EACH ROW
            EXECUTE FUNCTION update_modified_timestamp();
    END IF;
END $$;

-- ============================================================================
-- 6. RECORD MIGRATION
-- ============================================================================

INSERT INTO schema_migrations (version)
VALUES ('NNN_descriptive_name')
ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- VERIFICATION (Run after migration)
-- ============================================================================
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration NNN_descriptive_name completed successfully!';
    RAISE NOTICE '📊 Created tables: table_name';
    RAISE NOTICE '📊 Created indexes: idx_table_name_*';
END $$;
```

---

## Table Creation Patterns

### Basic Table with Serial ID

```sql
CREATE TABLE IF NOT EXISTS my_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Table with UUID (Multi-tenancy)

```sql
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active'
);
```

### Table with Foreign Key (CASCADE)

```sql
CREATE TABLE IF NOT EXISTS child_table (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER NOT NULL
        REFERENCES parent_table(id) ON DELETE CASCADE,
    data TEXT
);
```

### Table with JSONB Metadata

```sql
CREATE TABLE IF NOT EXISTS flexible_table (
    id SERIAL PRIMARY KEY,
    core_field VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}'
);
```

### Table with Array Fields

```sql
CREATE TABLE IF NOT EXISTS tagged_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    tags TEXT[],
    page_numbers INTEGER[]
);
```

### Table with Vector Column (pgvector)

```sql
-- Requires pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE my_table
ADD COLUMN IF NOT EXISTS embedding vector(768);
```

---

## Index Patterns

### Single Column Index

```sql
CREATE INDEX IF NOT EXISTS idx_table_column
    ON table_name(column_name);
```

### Composite Index

```sql
CREATE INDEX IF NOT EXISTS idx_table_col1_col2
    ON table_name(column1, column2);
```

### Partial Index (Filtered)

```sql
CREATE INDEX IF NOT EXISTS idx_table_active_only
    ON table_name(column_name)
    WHERE status = 'active';
```

### Descending Index (Recent First)

```sql
CREATE INDEX IF NOT EXISTS idx_table_recent
    ON table_name(created_at DESC);
```

### Full-Text Search Index (GIN)

```sql
CREATE INDEX IF NOT EXISTS idx_table_text_search
    ON table_name USING gin(
        to_tsvector('english', title || ' ' || COALESCE(description, ''))
    );
```

### Array Index (GIN)

```sql
CREATE INDEX IF NOT EXISTS idx_table_tags
    ON table_name USING GIN(tags);
```

### Vector Similarity Index (IVFFlat)

```sql
CREATE INDEX IF NOT EXISTS idx_table_embedding
    ON table_name
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Index Naming Convention

`idx_tablename_columnname[_descriptor]`

Examples:
- `idx_users_email`
- `idx_projects_status_active`
- `idx_documents_text_search`

---

## Constraint Patterns

### CHECK Constraint (Value Validation)

```sql
-- Inline
status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'pending')),

-- Named constraint
CONSTRAINT valid_rating CHECK (rating BETWEEN 1 AND 5)
```

### UNIQUE Constraint

```sql
-- Single column
email VARCHAR(255) UNIQUE,

-- Multi-column
UNIQUE(tenant_id, user_id)
```

### Foreign Key with CASCADE

```sql
-- Delete children when parent deleted
parent_id INTEGER REFERENCES parent_table(id) ON DELETE CASCADE

-- Set null when parent deleted
parent_id INTEGER REFERENCES parent_table(id) ON DELETE SET NULL
```

---

## Safe Alteration Patterns

### Add Column (Safe)

```sql
ALTER TABLE table_name
ADD COLUMN IF NOT EXISTS new_column data_type;
```

### Add Column with Conditional Check

```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'my_table' AND column_name = 'new_column'
    ) THEN
        ALTER TABLE my_table ADD COLUMN new_column VARCHAR(255);
        CREATE INDEX idx_my_table_new_column ON my_table(new_column);
    END IF;
END $$;
```

### Drop Column (Safe)

```sql
ALTER TABLE table_name
DROP COLUMN IF EXISTS old_column;
```

### Drop Foreign Key (Dynamic)

```sql
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    WHERE tc.table_name = 'my_table'
        AND kcu.column_name = 'foreign_column'
        AND tc.constraint_type = 'FOREIGN KEY';

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE my_table DROP CONSTRAINT ' || constraint_name;
        RAISE NOTICE 'Dropped FK constraint %', constraint_name;
    END IF;
END $$;
```

---

## View Patterns

### Simple Aggregation View

```sql
CREATE OR REPLACE VIEW v_tool_performance_24h AS
SELECT
    tool_name,
    COUNT(*) as total_calls,
    ROUND(AVG(execution_time_ms)::numeric, 0) as avg_time_ms,
    ROUND(
        (SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::numeric,
        1
    ) as success_rate_pct
FROM tool_usage_analytics
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY tool_name
ORDER BY total_calls DESC;
```

### Join View

```sql
CREATE OR REPLACE VIEW v_call_documents AS
SELECT
    cdm.call_identifier,
    sd.document_key,
    sdc.chunk_text,
    cdm.relevance_score
FROM call_document_mappings cdm
JOIN shared_documents sd ON cdm.document_id = sd.id
JOIN shared_document_chunks sdc ON sd.id = sdc.document_id;
```

---

## Function Patterns

### Aggregation Function

```sql
CREATE OR REPLACE FUNCTION aggregate_metrics(p_period_hours INTEGER DEFAULT 24)
RETURNS void AS $$
DECLARE
    v_period_start TIMESTAMPTZ;
    v_period_end TIMESTAMPTZ;
BEGIN
    v_period_end := NOW();
    v_period_start := NOW() - (p_period_hours || ' hours')::INTERVAL;

    -- Delete existing metrics
    DELETE FROM metrics_table
    WHERE period_start = DATE_TRUNC('hour', v_period_start);

    -- Insert new aggregated data
    INSERT INTO metrics_table (tool_name, call_count, avg_time)
    SELECT
        tool_name,
        COUNT(*),
        AVG(execution_time_ms)
    FROM source_table
    WHERE timestamp BETWEEN v_period_start AND v_period_end
    GROUP BY tool_name;
END;
$$ LANGUAGE plpgsql;
```

### Validation Function

```sql
CREATE OR REPLACE FUNCTION check_limit(
    p_tenant_id UUID,
    p_metric VARCHAR(50)
)
RETURNS BOOLEAN AS $$
DECLARE
    current_usage INTEGER;
    max_limit INTEGER;
    tenant_plan VARCHAR(20);
BEGIN
    SELECT plan INTO tenant_plan FROM tenants WHERE id = p_tenant_id;

    -- Plan-based limits
    CASE tenant_plan
        WHEN 'free' THEN max_limit := 50;
        WHEN 'basic' THEN max_limit := 200;
        WHEN 'premium' THEN max_limit := 1000;
        ELSE max_limit := 50;
    END CASE;

    -- Get current usage
    SELECT COALESCE(usage_count, 0) INTO current_usage
    FROM usage_table
    WHERE tenant_id = p_tenant_id;

    RETURN COALESCE(current_usage, 0) < max_limit;
END;
$$ LANGUAGE plpgsql;
```

### Vector Search Function

```sql
CREATE OR REPLACE FUNCTION search_semantic(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 20
)
RETURNS TABLE (id uuid, title text, similarity float)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.title,
        1 - (t.embedding <=> query_embedding) as similarity
    FROM my_table t
    WHERE t.embedding IS NOT NULL
        AND 1 - (t.embedding <=> query_embedding) > match_threshold
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

## Trigger Patterns

### Auto-update Timestamp Trigger

```sql
-- Function
CREATE OR REPLACE FUNCTION update_modified_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Conditional trigger creation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trigger_update_timestamp'
    ) THEN
        CREATE TRIGGER trigger_update_timestamp
            BEFORE UPDATE ON my_table
            FOR EACH ROW
            EXECUTE FUNCTION update_modified_timestamp();
    END IF;
END $$;
```

---

## Transaction Wrapper

For multi-step migrations:

```sql
BEGIN;

-- Step 1
ALTER TABLE table1 ADD COLUMN IF NOT EXISTS new_col VARCHAR(255);

-- Step 2
CREATE INDEX IF NOT EXISTS idx_table1_new_col ON table1(new_col);

-- Step 3
INSERT INTO schema_migrations (version) VALUES ('NNN_migration')
ON CONFLICT (version) DO NOTHING;

COMMIT;
```

---

## Cleanup Migration Pattern

```sql
-- ================================================================
-- CLEANUP: Remove unused tables
-- ================================================================

BEGIN;

-- Step 1: Remove foreign keys first
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    -- Find and drop FK constraints
    FOR constraint_name IN
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        WHERE tc.table_name = 'referencing_table'
        AND tc.constraint_type = 'FOREIGN KEY'
    LOOP
        EXECUTE 'ALTER TABLE referencing_table DROP CONSTRAINT ' || constraint_name;
    END LOOP;
END $$;

-- Step 2: Drop columns
ALTER TABLE table1 DROP COLUMN IF EXISTS unused_column;

-- Step 3: Drop tables (CASCADE for dependencies)
DROP TABLE IF EXISTS unused_table1 CASCADE;
DROP TABLE IF EXISTS unused_table2 CASCADE;

-- Step 4: Record migration
INSERT INTO schema_migrations (version)
VALUES ('022_cleanup_unused_tables')
ON CONFLICT (version) DO NOTHING;

COMMIT;
```

---

## JSONB Aggregation Patterns

### Object Aggregation

```sql
jsonb_object_agg(key_column, value_column)
```

### Build Object

```sql
jsonb_build_object(
    'high', SUM(CASE WHEN score >= 0.7 THEN 1 ELSE 0 END),
    'medium', SUM(CASE WHEN score >= 0.4 AND score < 0.7 THEN 1 ELSE 0 END),
    'low', SUM(CASE WHEN score < 0.4 THEN 1 ELSE 0 END)
)
```

---

## Python Migration Runner

```python
#!/usr/bin/env python3
"""Apply database migration."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def apply_migration(migration_file: str):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return False

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Read migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Execute
        cursor.execute(migration_sql)
        conn.commit()

        print(f"✅ Migration {migration_file} applied successfully!")
        return True

    except psycopg2.Error as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python apply_migration.py <migration_file.sql>")
        sys.exit(1)

    success = apply_migration(sys.argv[1])
    sys.exit(0 if success else 1)
```

---

## Best Practices Checklist

### Safety
- [ ] Use `IF NOT EXISTS` for all CREATE statements
- [ ] Use `IF EXISTS` for all DROP statements
- [ ] Wrap multi-step migrations in transactions
- [ ] Check column/constraint existence before ALTER

### Documentation
- [ ] Add header comment with purpose
- [ ] Add COMMENT ON TABLE/COLUMN
- [ ] Include verification queries
- [ ] Add success message at end

### Performance
- [ ] Create indexes for frequently queried columns
- [ ] Use partial indexes for filtered queries
- [ ] Consider GIN for text/array searches
- [ ] Use CASCADE DELETE for parent-child relationships

### Data Integrity
- [ ] Add CHECK constraints for value validation
- [ ] Add UNIQUE constraints where needed
- [ ] Define foreign keys with appropriate ON DELETE behavior
- [ ] Set NOT NULL for required fields

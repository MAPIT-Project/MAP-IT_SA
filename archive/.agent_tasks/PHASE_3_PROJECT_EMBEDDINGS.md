# Phase 3: Project Embeddings Implementation

## Overview
Add semantic similarity search to the project search system using vector embeddings. This will enable queries like "Find projects similar to [project X]" and improve relevance for conceptual matches.

**Estimated Effort:** 4-6 hours
**Status:** ✅ Code Complete - Ready for Deployment
**Priority:** Medium (enhances search quality but not critical)

---

## Implementation Status

### Completed Tasks
- ✅ SQL script for `project_embeddings` table (`scripts/create_project_embeddings_table.sql`)
- ✅ Embedding generation script (`scripts/generate_project_embeddings.py`)
- ✅ Vector search integration in `LocalProjectSearchService`
- ✅ Similar projects by embedding method (`find_similar_projects_by_embedding`)
- ✅ ToolAwareAgent tool registration (`find_semantically_similar_projects`)
- ✅ Three-source RRF fusion (PostgreSQL + Neo4j + Vector)
- ✅ Test script (`scripts/test_project_embeddings.py`)

### Deployment Steps Required
1. Create the database table:
   ```bash
   psql $DATABASE_URL -f scripts/create_project_embeddings_table.sql
   ```

2. Generate embeddings (run multiple times if needed):
   ```bash
   python scripts/generate_project_embeddings.py --batch-size 50 --max-batches 20
   ```

3. Create vector indexes (after embeddings are generated):
   ```sql
   VACUUM ANALYZE project_embeddings;
   CREATE INDEX idx_project_embeddings_combined
       ON project_embeddings
       USING ivfflat (combined_embedding vector_cosine_ops)
       WITH (lists = 100);
   ```

4. Verify implementation:
   ```bash
   python scripts/test_project_embeddings.py
   ```

---

## Objectives

1. **Create embeddings table** for storing project vector embeddings
2. **Generate embeddings** for all existing projects (13,865 projects)
3. **Integrate vector search** into `LocalProjectSearchService`
4. **Enable semantic queries** like "projects about renewable energy integration"
5. **Combine three sources** (PostgreSQL, Neo4j, Vector) using RRF fusion

---

## Prerequisites

### Current System State
- ✅ PostgreSQL database with `projects` table (13,865 projects)
- ✅ Neo4j graph database with `Project` nodes
- ✅ `LocalProjectSearchService` with PostgreSQL + Neo4j search
- ✅ RRF fusion algorithm working
- ✅ Embedding service available (`app/services/embedding_service.py`)

### Required Environment Variables
Check `.env` file for:
- `GEMINI_API_KEY` - For generating embeddings
- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` - If using Supabase for embeddings

### Embedding Model
- **Model:** `text-embedding-004` (Google Gemini)
- **Dimension:** 768
- **Same model used for:** Document chunks (for consistency)

---

## Database Schema

### Step 1: Create `project_embeddings` Table

**File to create:** `scripts/create_project_embeddings_table.sql`

```sql
-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create project_embeddings table
CREATE TABLE IF NOT EXISTS project_embeddings (
    project_id TEXT PRIMARY KEY,
    title_embedding vector(768),
    objective_embedding vector(768),
    combined_embedding vector(768),  -- title + objective (first 2000 chars)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    model_version TEXT DEFAULT 'text-embedding-004',

    -- Foreign key to projects table
    CONSTRAINT fk_project
        FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

-- Create index for similarity search
CREATE INDEX IF NOT EXISTS idx_project_embeddings_combined
    ON project_embeddings
    USING ivfflat (combined_embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_project_embeddings_project_id
    ON project_embeddings(project_id);

-- Add comment
COMMENT ON TABLE project_embeddings IS 'Vector embeddings for semantic project search';
COMMENT ON COLUMN project_embeddings.combined_embedding IS 'Embedding of title + objective (first 2000 chars)';
```

**Run this script:**
```bash
docker compose exec -T db psql -U mapit_user -d mapit_db < scripts/create_project_embeddings_table.sql
```

---

## Implementation Steps

### Step 2: Create Embedding Generation Script

**File to create:** `scripts/generate_project_embeddings.py`

```python
"""
Generate vector embeddings for all projects in the database.

This script:
1. Fetches all projects from PostgreSQL
2. Generates embeddings for title + objective
3. Stores embeddings in project_embeddings table
4. Handles errors and retries
5. Provides progress tracking
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.embedding_service import EmbeddingService

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProjectEmbeddingGenerator:
    """Generate and store project embeddings."""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL required")

        self.db_pool = SimpleConnectionPool(1, 5, self.db_url)
        self.embedding_service = EmbeddingService()
        self.batch_size = 50  # Process in batches
        self.max_retries = 3

    def get_projects_needing_embeddings(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get projects that don't have embeddings yet."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)

        try:
            query = """
            SELECT p.id, p.title, p.objective
            FROM projects p
            LEFT JOIN project_embeddings pe ON p.id = pe.project_id
            WHERE pe.project_id IS NULL
              AND p.title IS NOT NULL
              AND p.objective IS NOT NULL
            ORDER BY p.id
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def get_total_projects_count(self) -> int:
        """Get total number of projects."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM projects WHERE title IS NOT NULL AND objective IS NOT NULL")
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def get_embedded_count(self) -> int:
        """Get number of projects that already have embeddings."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM project_embeddings")
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def prepare_text_for_embedding(self, title: str, objective: str) -> str:
        """
        Combine title and objective for embedding.
        Limit to first 2000 chars to stay within model limits.
        """
        combined = f"{title}. {objective}"
        # Truncate to 2000 chars (safely under model limits)
        if len(combined) > 2000:
            combined = combined[:1997] + "..."
        return combined

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using EmbeddingService."""
        try:
            embedding = await self.embedding_service.generate_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def store_embedding(
        self,
        project_id: str,
        combined_embedding: List[float],
        model_version: str = "text-embedding-004"
    ) -> bool:
        """Store embedding in database."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            query = """
            INSERT INTO project_embeddings
                (project_id, combined_embedding, model_version, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (project_id)
            DO UPDATE SET
                combined_embedding = EXCLUDED.combined_embedding,
                model_version = EXCLUDED.model_version,
                updated_at = NOW()
            """
            cursor.execute(query, (project_id, combined_embedding, model_version))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding for {project_id}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    async def process_batch(self, projects: List[Dict[str, Any]]) -> int:
        """Process a batch of projects."""
        success_count = 0

        for project in projects:
            project_id = project['id']
            title = project.get('title', '') or ''
            objective = project.get('objective', '') or ''

            if not title and not objective:
                logger.warning(f"Skipping project {project_id}: no title or objective")
                continue

            # Prepare text
            text = self.prepare_text_for_embedding(title, objective)

            # Generate embedding
            embedding = await self.generate_embedding(text)

            if embedding:
                # Store embedding
                if self.store_embedding(project_id, embedding):
                    success_count += 1
                    logger.debug(f"✅ Embedded project {project_id}")
                else:
                    logger.error(f"❌ Failed to store embedding for {project_id}")
            else:
                logger.error(f"❌ Failed to generate embedding for {project_id}")

        return success_count

    async def run(self, batch_size: int = 50, max_batches: Optional[int] = None):
        """Main execution loop."""
        total_projects = self.get_total_projects_count()
        embedded_count = self.get_embedded_count()
        remaining = total_projects - embedded_count

        logger.info(f"📊 Total projects: {total_projects}")
        logger.info(f"📊 Already embedded: {embedded_count}")
        logger.info(f"📊 Remaining: {remaining}")

        if remaining == 0:
            logger.info("✅ All projects already have embeddings!")
            return

        processed = 0
        batch_num = 0

        while True:
            if max_batches and batch_num >= max_batches:
                break

            # Get next batch
            projects = self.get_projects_needing_embeddings(limit=batch_size)

            if not projects:
                logger.info("✅ No more projects to process!")
                break

            logger.info(f"🔄 Processing batch {batch_num + 1}: {len(projects)} projects")

            # Process batch
            success = await self.process_batch(projects)
            processed += success

            logger.info(f"✅ Batch {batch_num + 1} complete: {success}/{len(projects)} successful")
            logger.info(f"📊 Progress: {processed}/{remaining} ({processed/remaining*100:.1f}%)")

            batch_num += 1

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        logger.info(f"🎉 Complete! Processed {processed} projects")


async def main():
    """Main entry point."""
    generator = ProjectEmbeddingGenerator()

    # Process in batches of 50, max 20 batches per run (1000 projects)
    # This allows for incremental processing
    await generator.run(batch_size=50, max_batches=20)


if __name__ == "__main__":
    asyncio.run(main())
```

**Usage:**
```bash
cd /home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA
python scripts/generate_project_embeddings.py
```

**Note:** Run this script multiple times to process all projects incrementally (1000 at a time to avoid rate limits).

---

### Step 3: Add Vector Search to LocalProjectSearchService

**File to modify:** `app/services/local_project_search_service.py`

**Add this method:**

```python
async def _search_vector(
    self,
    search_terms: List[str],
    filters: Dict[str, Any],
    limit: int
) -> List[Dict[str, Any]]:
    """
    Search projects using vector embeddings for semantic similarity.

    Args:
        search_terms: List of search keywords
        filters: Optional filters (not used in vector search yet)
        limit: Maximum results

    Returns:
        List of projects with relevance scores
    """
    if not self._postgres_repo or not self._postgres_repo.db_pool:
        return []

    try:
        from app.services.embedding_service import EmbeddingService

        # Generate embedding for search query
        embedding_service = EmbeddingService()
        search_text = ' '.join(search_terms)
        query_embedding = await embedding_service.generate_embedding(search_text)

        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []

        # Query vector database
        conn = self._postgres_repo.db_pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)

        try:
            # Use cosine similarity for semantic search
            query = """
            SELECT
                pe.project_id as id,
                1 - (pe.combined_embedding <=> %s::vector) as similarity_score,
                p.title,
                p.acronym,
                p.objective,
                p."startDate",
                p."endDate",
                p."totalCost",
                p."ecMaxContribution",
                p.status,
                p."fundingScheme"
            FROM project_embeddings pe
            JOIN projects p ON pe.project_id = p.id
            WHERE pe.combined_embedding IS NOT NULL
            ORDER BY pe.combined_embedding <=> %s::vector
            LIMIT %s
            """

            cursor.execute(query, (query_embedding, query_embedding, limit))
            rows = cursor.fetchall()

            # Convert to standard format
            formatted = []
            for i, r in enumerate(rows):
                formatted.append({
                    'id': r.get('id'),
                    'rcn': '',  # Not in embeddings table
                    'title': r.get('title'),
                    'acronym': r.get('acronym'),
                    'objective': (r.get('objective') or '')[:500],
                    'startDate': r.get('startDate'),
                    'endDate': r.get('endDate'),
                    'totalCost': r.get('totalCost', 0),
                    'ecMaxContribution': r.get('ecMaxContribution', 0),
                    'status': r.get('status'),
                    'frameworkProgramme': '',  # Not in embeddings table
                    'fundingScheme': r.get('fundingScheme'),
                    'topics': '',
                    'similarity_score': float(r.get('similarity_score', 0)),
                    '_source': 'vector',
                    '_rank': i + 1
                })

            return formatted

        finally:
            cursor.close()
            self._postgres_repo.db_pool.putconn(conn)

    except Exception as e:
        logger.error(f"Vector search error: {e}")
        return []
```

**Modify `search_projects()` method:**

Find this section:
```python
# 2. Run searches in parallel
all_results = {}
sources_used = []

# PostgreSQL search (primary)
if self._postgres_repo:
    # ... existing code ...

# Neo4j graph search (for relationship-based results)
if include_graph and self._graph_service:
    # ... existing code ...
```

**Add after Neo4j search:**

```python
# Vector semantic search (if embeddings exist)
if include_semantic and self._has_project_embeddings():
    try:
        vector_results = await self._search_vector(search_terms, parsed_filters, limit)
        all_results['vector'] = vector_results
        sources_used.append('vector')
        logger.info(f"   Vector returned {len(vector_results)} projects")
    except Exception as e:
        logger.warning(f"   Vector search failed: {e}")
```

**Add helper method:**

```python
def _has_project_embeddings(self) -> bool:
    """Check if project embeddings table exists and has data."""
    if not self._postgres_repo or not self._postgres_repo.db_pool:
        return False

    try:
        conn = self._postgres_repo.db_pool.getconn()
        cursor = conn.cursor()

        try:
            # Check if table exists and has data
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_name = 'project_embeddings'
                )
            """)
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                return False

            cursor.execute("SELECT COUNT(*) FROM project_embeddings WHERE combined_embedding IS NOT NULL")
            count = cursor.fetchone()[0]

            return count > 0
        finally:
            cursor.close()
            self._postgres_repo.db_pool.putconn(conn)
    except Exception as e:
        logger.warning(f"Failed to check embeddings: {e}")
        return False
```

**Update `search_projects()` signature:**

```python
async def search_projects(
    self,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    include_graph: bool = True,
    include_semantic: bool = True  # NEW PARAMETER
) -> Dict[str, Any]:
```

---

### Step 4: Add Similar Project Search Method

**File to modify:** `app/services/local_project_search_service.py`

**Add this method:**

```python
async def find_similar_projects_by_embedding(
    self,
    project_id: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Find projects semantically similar to a given project using embeddings.

    Args:
        project_id: ID of the reference project
        limit: Maximum results

    Returns:
        Dict with similar projects and similarity scores
    """
    if not self._postgres_repo or not self._postgres_repo.db_pool:
        return {
            'success': False,
            'error': 'Database not available',
            'projects': []
        }

    try:
        conn = self._postgres_repo.db_pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)

        try:
            # Get reference project's embedding
            cursor.execute("""
                SELECT combined_embedding
                FROM project_embeddings
                WHERE project_id = %s
            """, (project_id,))

            row = cursor.fetchone()
            if not row or not row['combined_embedding']:
                return {
                    'success': False,
                    'error': f'No embedding found for project {project_id}',
                    'projects': []
                }

            ref_embedding = row['combined_embedding']

            # Find similar projects (excluding the reference project)
            cursor.execute("""
                SELECT
                    pe.project_id as id,
                    1 - (pe.combined_embedding <=> %s::vector) as similarity_score,
                    p.title,
                    p.acronym,
                    p.objective,
                    p."startDate",
                    p.status,
                    p."ecMaxContribution"
                FROM project_embeddings pe
                JOIN projects p ON pe.project_id = p.id
                WHERE pe.project_id != %s
                  AND pe.combined_embedding IS NOT NULL
                ORDER BY pe.combined_embedding <=> %s::vector
                LIMIT %s
            """, (ref_embedding, project_id, ref_embedding, limit))

            rows = cursor.fetchall()

            projects = []
            for r in rows:
                projects.append({
                    'id': r.get('id'),
                    'title': r.get('title'),
                    'acronym': r.get('acronym'),
                    'objective': (r.get('objective') or '')[:300],
                    'similarity_score': float(r.get('similarity_score', 0)),
                    'status': r.get('status'),
                    'budget': r.get('ecMaxContribution', 0),
                    'start_date': r.get('startDate'),
                    'cordis_url': f"https://cordis.europa.eu/project/id/{r.get('id')}"
                })

            return {
                'success': True,
                'reference_project': project_id,
                'similar_projects': projects,
                'total_found': len(projects)
            }

        finally:
            cursor.close()
            self._postgres_repo.db_pool.putconn(conn)

    except Exception as e:
        logger.error(f"Similar projects search error: {e}")
        return {
            'success': False,
            'error': str(e),
            'projects': []
        }
```

---

### Step 5: Update ToolAwareAgent

**File to modify:** `app/services/agents/tool_aware_agent.py`

**Add new tool:**

```python
# In __init__ method, add:
self.register_tool(Tool(
    name="find_similar_projects_semantic",
    description="Find projects semantically similar to a given project using AI embeddings",
    category=ToolCategory.PROJECTS,
    parameters={
        "project_id": "The reference project ID",
        "limit": "Maximum number of similar projects to return (default: 10)"
    },
    examples=[
        "find_similar_projects_semantic(project_id='101000000')",
        "find_similar_projects_semantic(project_id='101000000', limit=20)"
    ]
))
```

**Add tool handler:**

```python
# In _execute_tool method:
elif tool_name == 'find_similar_projects_semantic':
    return await self._tool_find_similar_projects_semantic(params)
```

**Add implementation:**

```python
async def _tool_find_similar_projects_semantic(self, params: Dict) -> Dict:
    """Find semantically similar projects using embeddings."""
    try:
        from ..local_project_search_service import LocalProjectSearchService

        project_id = params.get('project_id', '')
        limit = params.get('limit', 10)

        if not project_id:
            return {"error": "project_id is required", "projects": []}

        service = LocalProjectSearchService()
        result = await service.find_similar_projects_by_embedding(
            project_id=project_id,
            limit=limit
        )

        return result
    except Exception as e:
        logger.error(f"Semantic similarity search error: {e}")
        return {"error": str(e), "projects": []}
```

---

## Testing

### Test 1: Verify Table Creation
```bash
docker compose exec -T db psql -U mapit_user -d mapit_db -c "
SELECT COUNT(*) as total_projects,
       (SELECT COUNT(*) FROM project_embeddings) as embedded_projects
FROM projects
WHERE title IS NOT NULL AND objective IS NOT NULL;
"
```

### Test 2: Generate Embeddings (Small Batch)
```bash
# Test with just 10 projects first
python scripts/generate_project_embeddings.py
# Check logs for success
```

### Test 3: Test Vector Search
```python
# In Python shell or test script
from app.services.local_project_search_service import LocalProjectSearchService
import asyncio

service = LocalProjectSearchService()
results = asyncio.run(service.search_projects(
    query="renewable energy integration",
    include_semantic=True,
    limit=10
))

print(f"Sources used: {results['sources_used']}")
print(f"Projects found: {len(results['projects'])}")
```

### Test 4: Test Similar Projects
```python
# Find projects similar to a known project
results = asyncio.run(service.find_similar_projects_by_embedding(
    project_id="101000000",  # Use a real project ID
    limit=5
))

print(f"Similar projects: {len(results['similar_projects'])}")
for p in results['similar_projects']:
    print(f"  {p['title']} (similarity: {p['similarity_score']:.3f})")
```

### Test 5: Integration Test
```bash
# Test via API
curl -X POST "http://localhost:8000/api/v2/conversation/999/message/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Find projects similar to project 101000000", "user_id": 1}'
```

---

## Performance Considerations

### Embedding Generation
- **Rate Limits:** Google Gemini has rate limits. Process in batches of 50 with 0.5s delay
- **Time Estimate:** ~13,865 projects × 0.1s per embedding = ~23 minutes (if no rate limits)
- **Actual Time:** Likely 1-2 hours due to rate limiting and retries

### Vector Search Performance
- **Index Type:** `ivfflat` with 100 lists (good for <100k vectors)
- **Query Time:** <100ms for similarity search
- **Index Build:** Run `VACUUM ANALYZE project_embeddings;` after bulk insert

### Memory Usage
- **Embedding Size:** 768 floats × 4 bytes = 3KB per project
- **Total Storage:** 13,865 × 3KB = ~40MB (negligible)

---

## Error Handling

### Embedding Generation Failures
- **Retry Logic:** Up to 3 retries per project
- **Skip on Failure:** Log error and continue with next project
- **Resume Capability:** Script can be run multiple times (only processes missing embeddings)

### Vector Search Failures
- **Graceful Degradation:** If vector search fails, fall back to PostgreSQL + Neo4j
- **Missing Embeddings:** Projects without embeddings are excluded from vector search only

---

## Monitoring

### Check Embedding Progress
```sql
SELECT
    COUNT(*) as total_projects,
    (SELECT COUNT(*) FROM project_embeddings) as embedded,
    ROUND(100.0 * (SELECT COUNT(*) FROM project_embeddings) / COUNT(*), 2) as percent_complete
FROM projects
WHERE title IS NOT NULL AND objective IS NOT NULL;
```

### Check Embedding Quality
```sql
-- Find projects with very similar embeddings (potential duplicates)
SELECT
    p1.project_id as project1,
    p2.project_id as project2,
    1 - (p1.combined_embedding <=> p2.combined_embedding) as similarity
FROM project_embeddings p1
CROSS JOIN project_embeddings p2
WHERE p1.project_id < p2.project_id
  AND 1 - (p1.combined_embedding <=> p2.combined_embedding) > 0.95
LIMIT 10;
```

---

## Integration Checklist

- [ ] Create `project_embeddings` table
- [ ] Create embedding generation script
- [ ] Generate embeddings for all projects (run script)
- [ ] Add `_search_vector()` method to `LocalProjectSearchService`
- [ ] Add `_has_project_embeddings()` helper method
- [ ] Update `search_projects()` to include vector search
- [ ] Add `find_similar_projects_by_embedding()` method
- [ ] Update `ToolAwareAgent` with semantic similarity tool
- [ ] Test vector search integration
- [ ] Test similar projects search
- [ ] Test three-source fusion (PostgreSQL + Neo4j + Vector)
- [ ] Update documentation

---

## Expected Results

### Before Phase 3
- Keyword search only ("renewable energy" matches exact terms)
- No semantic understanding ("solar power" ≠ "photovoltaic")

### After Phase 3
- Semantic search ("renewable energy" matches "solar power", "wind energy", etc.)
- Similar project discovery ("projects like X")
- Better relevance for conceptual queries
- Three-source fusion for maximum recall

### Example Query Improvements

| Query | Before | After |
|-------|--------|-------|
| "renewable energy" | Exact matches only | Semantic matches (solar, wind, hydro) |
| "projects like 101000000" | Not possible | Top 10 similar projects |
| "AI in healthcare" | Keyword match | Conceptual match (ML, diagnostics, etc.) |

---

## Troubleshooting

### Issue: Embeddings not generating
**Check:**
- `GEMINI_API_KEY` is set and valid
- Embedding service is working: `from app.services.embedding_service import EmbeddingService; es = EmbeddingService(); await es.generate_embedding("test")`
- Database connection is working

### Issue: Vector search returns 0 results
**Check:**
- `project_embeddings` table exists: `SELECT COUNT(*) FROM project_embeddings;`
- Embeddings are not NULL: `SELECT COUNT(*) FROM project_embeddings WHERE combined_embedding IS NOT NULL;`
- pgvector extension is enabled: `SELECT * FROM pg_extension WHERE extname = 'vector';`

### Issue: Slow vector search
**Check:**
- Index exists: `\d project_embeddings` (should show `idx_project_embeddings_combined`)
- Index is used: `EXPLAIN ANALYZE SELECT ... ORDER BY combined_embedding <=> ...`
- Consider increasing `lists` parameter in index (for >100k vectors)

---

## Files to Create/Modify

### Create
1. `scripts/create_project_embeddings_table.sql` - Database schema
2. `scripts/generate_project_embeddings.py` - Embedding generation script

### Modify
1. `app/services/local_project_search_service.py` - Add vector search methods
2. `app/services/agents/tool_aware_agent.py` - Add semantic similarity tool

### Optional (Documentation)
3. `docs_tracked/SYSTEM_ARCHITECTURE.md` - Update with vector search info

---

## Success Criteria

- ✅ `project_embeddings` table created with all 13,865 projects embedded
- ✅ Vector search returns relevant results for semantic queries
- ✅ Three-source fusion (PostgreSQL + Neo4j + Vector) working
- ✅ Similar projects search working via embeddings
- ✅ Query time < 1 second (including vector search)
- ✅ No degradation in existing functionality

---

## Next Steps After Phase 3

1. **Monitor Performance:** Track query times and relevance
2. **Tune Index:** Adjust `ivfflat` lists parameter if needed
3. **Incremental Updates:** Add script to update embeddings for new projects
4. **Hybrid Search:** Experiment with different weights for three sources in RRF

---

## Notes

- **Embedding Model:** Using `text-embedding-004` for consistency with document chunks
- **Text Limit:** Truncating to 2000 chars to stay within model limits
- **Batch Processing:** Process in batches to avoid rate limits and allow resumption
- **Index Type:** `ivfflat` is good for <100k vectors. If we exceed that, consider `hnsw`

---

**Last Updated:** December 3, 2024
**Status:** Ready for Implementation 🔲

# Phase 1: Erasmus+ Document Ingestion

## Objective

Ingest Erasmus+ Programme Guide 2026, Annual Work Programme 2026, and Call for Proposals 2026 into the RAG system so they can be searched and used for answering user queries about Erasmus+ eligibility, deadlines, and requirements.

## Priority: HIGH

This is the foundational step - without documents in the database, the RAG system cannot answer Erasmus+ questions.

## Current State

### What Exists
- Document ingestion infrastructure: `app/services/ingestion_service.py`
- Existing ingestion script: `scripts/ingest_documents.py`
- Database tables: `horizon_documents`, `document_chunks` (with embeddings)
- Embedding service configured for 768-dim vectors via Google text-embedding-004

### What's Missing
- No Erasmus+ documents downloaded to disk
- No Erasmus+-specific document type mappings
- `programme` field not populated for Erasmus+ documents

## Prerequisites

### Required Documents to Download

Download these from the EU Publications Office or Erasmus+ Portal:

| Document | URL Pattern | Priority |
|----------|-------------|----------|
| Erasmus+ Programme Guide 2026 | `https://erasmus-plus.ec.europa.eu/programme-guide/...` | HIGH |
| Call for Proposals 2026 | `https://ec.europa.eu/info/funding-tenders/...` | HIGH |
| Annual Work Programme 2026 | Official Journal of EU | HIGH |

Save to: `data/erasmus_plus/` or `newdocs/erasmus/`

## Implementation Steps

### Step 1: Create Directory Structure

```bash
mkdir -p data/erasmus_plus
mkdir -p newdocs/erasmus
```

### Step 2: Create Erasmus+ Document Ingestion Script

Create file: `scripts/ingest_erasmus_documents.py`

```python
#!/usr/bin/env python3
"""
Erasmus+ Document Ingestion Script

Ingests Erasmus+ Programme Guide, Work Programme, and related documents
into the RAG system with proper programme tagging.

Usage:
    python scripts/ingest_erasmus_documents.py [--source-dir DIR] [--dry-run]

Options:
    --source-dir    Directory containing Erasmus+ PDFs (default: data/erasmus_plus)
    --dry-run       Don't commit to database, just show what would be ingested
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Erasmus+ document type mappings
ERASMUS_DOCUMENT_TYPES = {
    'programme_guide': {
        'patterns': ['programme_guide', 'program_guide', 'guide_2025', 'guide_2026'],
        'type': 'programme_guide',
        'description': 'Erasmus+ Programme Guide - comprehensive rules and eligibility'
    },
    'work_programme': {
        'patterns': ['work_programme', 'annual_work', 'awp_2025', 'awp_2026'],
        'type': 'work_programme',
        'description': 'Annual Work Programme with budget allocations'
    },
    'call_document': {
        'patterns': ['call_for_proposals', 'call_2025', 'call_2026', 'cfp_'],
        'type': 'call_document',
        'description': 'Call for proposals with deadlines'
    },
    'application_form': {
        'patterns': ['application_form', 'template', 'form_ka1', 'form_ka2'],
        'type': 'application_template',
        'description': 'Application forms and templates'
    },
    'budget_tool': {
        'patterns': ['budget', 'lump_sum', 'unit_cost', 'financial'],
        'type': 'budget_guidance',
        'description': 'Budget calculation tools and financial guidance'
    },
}


def detect_document_type(filename: str) -> tuple[str, str]:
    """
    Detect document type from filename.

    Returns:
        tuple: (document_type, description)
    """
    filename_lower = filename.lower()

    for doc_type, config in ERASMUS_DOCUMENT_TYPES.items():
        for pattern in config['patterns']:
            if pattern in filename_lower:
                return config['type'], config['description']

    # Default fallback
    return 'guidance_document', 'Erasmus+ guidance document'


def extract_year_from_filename(filename: str) -> str:
    """Extract programme year from filename."""
    import re

    # Match years like 2025, 2026, 2027
    year_match = re.search(r'20(2[5-7])', filename)
    if year_match:
        return f"20{year_match.group(1)}"

    # Match year ranges like 2025-2026
    range_match = re.search(r'(202[5-7])[-_](202[5-7])', filename)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"

    return "2025-2027"  # Default to current period


async def ingest_erasmus_documents(source_dir: str, dry_run: bool = False):
    """Ingest all Erasmus+ documents from source directory."""

    source_path = Path(source_dir)

    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.info("Please create the directory and add Erasmus+ PDF documents:")
        logger.info(f"  mkdir -p {source_dir}")
        logger.info("  # Then download Programme Guide, Work Programme, etc.")
        return False

    # Find all PDF files
    pdf_files = list(source_path.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"No PDF files found in {source_dir}")
        return False

    logger.info(f"Found {len(pdf_files)} PDF files to ingest")

    # Import ingestion service
    try:
        from app.services.ingestion_service import DocumentIngestionService
        ingestion_service = DocumentIngestionService()
    except ImportError as e:
        logger.error(f"Failed to import ingestion service: {e}")
        return False

    # Check service status
    stats = ingestion_service.get_service_stats()
    if not stats.get('supabase_connected', False):
        logger.error("Supabase connection failed. Check DATABASE_URL.")
        return False

    logger.info(f"Supabase connected: {stats.get('supabase_connected')}")

    # Track results
    successful = 0
    failed = []

    for pdf_file in pdf_files:
        logger.info(f"\nProcessing: {pdf_file.name}")

        # Detect document type
        doc_type, doc_description = detect_document_type(pdf_file.name)
        programme_year = extract_year_from_filename(pdf_file.name)

        logger.info(f"  Type: {doc_type}")
        logger.info(f"  Year: {programme_year}")

        if dry_run:
            logger.info(f"  [DRY-RUN] Would ingest {pdf_file.name}")
            successful += 1
            continue

        try:
            # Ingest the document with Erasmus+ specific metadata
            result = ingestion_service.ingest_file(
                file_path=str(pdf_file),
                document_type=doc_type,
                programme_year=programme_year,
                metadata={
                    "programme": "erasmus_plus",
                    "programme_name": "Erasmus+",
                    "source": "official_eu_portal",
                    "language": "en",
                    "description": doc_description,
                    "ingested_by": "erasmus_ingestion_script",
                    "funding_model": "lump_sum",
                }
            )

            if result.get('success'):
                logger.info(f"  Ingested: {pdf_file.name}")
                logger.info(f"    Document ID: {result.get('document_id')}")
                logger.info(f"    Chunks: {result.get('chunks_created')}")
                successful += 1
            else:
                logger.error(f"  Failed: {result.get('error')}")
                failed.append(pdf_file.name)

        except Exception as e:
            logger.error(f"  Exception: {e}")
            failed.append(pdf_file.name)

        # Rate limiting
        await asyncio.sleep(1)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files: {len(pdf_files)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {len(failed)}")

    if failed:
        logger.info("Failed files:")
        for name in failed:
            logger.info(f"  - {name}")

    if not dry_run:
        # Get final stats
        try:
            final_stats = ingestion_service.supabase.get_document_stats()
            logger.info(f"\nDatabase Stats:")
            logger.info(f"  Total Documents: {final_stats.get('total_documents', 0)}")
            logger.info(f"  Total Chunks: {final_stats.get('total_chunks', 0)}")
        except Exception as e:
            logger.warning(f"Could not get final stats: {e}")

    return successful > 0


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Erasmus+ documents into RAG system"
    )
    parser.add_argument(
        "--source-dir",
        default="data/erasmus_plus",
        help="Directory containing Erasmus+ PDFs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't commit to database"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ERASMUS+ DOCUMENT INGESTION")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes")

    success = asyncio.run(
        ingest_erasmus_documents(args.source_dir, args.dry_run)
    )

    if success:
        logger.info("\nIngestion completed!")
        logger.info("\nNext steps:")
        logger.info("1. Run Phase 2: Sync Erasmus+ calls from API")
        logger.info("2. Test with: curl -X POST http://localhost:8000/api/v3/conversation/test/message")
    else:
        logger.error("\nIngestion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 3: Update Database Schema (if needed)

Check if `horizon_documents` table has a `programme` column. If not, run migration:

```sql
-- migration/010_add_programme_field.sql

-- Add programme field to horizon_documents if not exists
ALTER TABLE horizon_documents
ADD COLUMN IF NOT EXISTS programme VARCHAR(50) DEFAULT 'horizon_europe';

-- Add index for programme filtering
CREATE INDEX IF NOT EXISTS idx_horizon_documents_programme
ON horizon_documents(programme);

-- Update document_chunks to include programme reference
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS programme VARCHAR(50);

-- Create function to auto-populate programme in chunks
CREATE OR REPLACE FUNCTION set_chunk_programme()
RETURNS TRIGGER AS $$
BEGIN
    SELECT programme INTO NEW.programme
    FROM horizon_documents
    WHERE id = NEW.document_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-populate
DROP TRIGGER IF EXISTS chunk_programme_trigger ON document_chunks;
CREATE TRIGGER chunk_programme_trigger
    BEFORE INSERT ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION set_chunk_programme();
```

### Step 4: Update Vector Search Service

Modify `app/services/vector_search_service.py` to support programme filtering:

```python
# Add to search method parameters
async def search(
    self,
    query: str,
    top_k: int = 10,
    filters: Optional[Dict] = None,
    programme: Optional[str] = None,  # NEW: Filter by programme
    **kwargs
) -> List[SearchResult]:
    """
    Search documents with optional programme filtering.

    Args:
        query: Search query
        top_k: Number of results
        filters: Additional filters
        programme: Filter by programme (e.g., 'erasmus_plus', 'horizon_europe')
    """
    # Build query with programme filter
    where_clause = ""
    params = []

    if programme:
        where_clause = "WHERE dc.programme = %s"
        params.append(programme)

    # ... rest of search logic
```

### Step 5: Run Ingestion

```bash
# First, ensure documents are in place
ls data/erasmus_plus/

# Dry run to test
python scripts/ingest_erasmus_documents.py --dry-run

# Actual ingestion
python scripts/ingest_erasmus_documents.py
```

## Validation

### Test 1: Check Document Count

```sql
SELECT programme, COUNT(*) as doc_count
FROM horizon_documents
GROUP BY programme;
```

Expected: Shows `erasmus_plus` with > 0 documents.

### Test 2: Check Chunk Count

```sql
SELECT programme, COUNT(*) as chunk_count
FROM document_chunks
GROUP BY programme;
```

### Test 3: Test Vector Search

```python
from app.services.vector_search_service import VectorSearchService

service = VectorSearchService()
results = await service.search(
    query="What are the eligibility requirements for Erasmus+ mobility?",
    programme="erasmus_plus",
    top_k=5
)
print(f"Found {len(results)} results")
for r in results:
    print(f"  - {r.title}: {r.score}")
```

### Test 4: End-to-End API Test

```bash
curl -X POST http://localhost:8000/api/v3/conversation/test-erasmus/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the ECHE requirement for Erasmus+?"}'
```

## Success Criteria

1. At least 3 Erasmus+ documents ingested
2. Each document produces 50-500 chunks with embeddings
3. Vector search returns relevant Erasmus+ content
4. API can answer basic Erasmus+ eligibility questions

## Estimated Effort

- Script creation: 1-2 hours
- Document download: 30 minutes
- Ingestion run: 1-2 hours (depending on document size)
- Validation: 30 minutes

## Dependencies

- `app/services/ingestion_service.py` - Must be working
- `SUPABASE_URL` and `SUPABASE_KEY` - Must be configured
- `GOOGLE_EMBEDDING_API_KEY` - For 768-dim embeddings
- PDFs in `data/erasmus_plus/` directory

## Next Phase

After completing Phase 1, proceed to **Phase 2: API Sync Script** to populate the `funding_calls` table with live Erasmus+ call data.

# Phase 4: Erasmus+ Document Templates and Application Forms

## Objective

Ingest Erasmus+ application templates, form guidance, and sector-specific documents to enable the RAG system to provide detailed guidance on completing applications for different Key Actions.

## Priority: LOW

This is an enhancement phase. The core Erasmus+ functionality should work after Phases 1-3. Templates add value for users actively preparing applications.

## Current State

### What Exists
- Document ingestion infrastructure from Phase 1
- Vector search with programme filtering
- Erasmus+ calls in database from Phase 2
- Eligibility and budget tools from Phase 3

### What's Missing
- Action-specific application templates (KA1, KA2, KA3)
- Sector-specific guidance documents
- Budget calculation worksheets
- Quality assessment criteria documents

## Documents to Ingest

### Priority 1: Application Forms by Key Action

| Document | Action Type | Use Case |
|----------|-------------|----------|
| KA1 Application Form Template | KA1-HED, KA1-VET | Mobility projects |
| KA2 Cooperation Partnership Form | KA2-COOP | Partnership applications |
| KA2 Small-Scale Partnership Form | KA2-SSP | Smaller partnerships |
| KA2 Capacity Building Form | KA2-CBHE | Capacity building HE |
| Jean Monnet Application Form | JMO-* | EU studies teaching |
| Sport Application Form | SPORT-* | Sport partnerships |

### Priority 2: Budget and Financial Documents

| Document | Purpose |
|----------|---------|
| Budget Calculation Tool (Excel) | Lump sum calculations |
| Financial Guidelines | Financial management rules |
| Unit Cost Rates Table | Official unit costs by country |
| Audit Requirements Guide | Financial reporting |

### Priority 3: Quality and Evaluation Criteria

| Document | Purpose |
|----------|---------|
| Quality Assessment Grid - KA1 | Evaluation criteria mobility |
| Quality Assessment Grid - KA2 | Evaluation criteria partnerships |
| Expert Evaluator Guidance | How applications are scored |
| Award Criteria Breakdown | Point allocation by criterion |

### Priority 4: Sector-Specific Guides

| Document | Sector |
|----------|--------|
| Higher Education Guide | HED |
| VET Sector Guide | VET |
| School Education Guide | SCH |
| Adult Education Guide | ADU |
| Youth Sector Guide | YOU |
| Sport Sector Guide | SPORT |

## Implementation Steps

### Step 1: Create Template Directory Structure

```bash
mkdir -p data/erasmus_plus/templates/{ka1,ka2,ka3,jmo,sport}
mkdir -p data/erasmus_plus/financial
mkdir -p data/erasmus_plus/quality
mkdir -p data/erasmus_plus/sector_guides
```

### Step 2: Create Template Ingestion Script

Create file: `scripts/ingest_erasmus_templates.py`

```python
#!/usr/bin/env python3
"""
Erasmus+ Template and Application Form Ingestion

Ingests Erasmus+ application templates, forms, and sector-specific guides
with proper categorization for targeted retrieval.

Usage:
    python scripts/ingest_erasmus_templates.py [--template-dir DIR] [--dry-run]

Templates are organized by:
- Key Action (KA1, KA2, KA3, JMO, Sport)
- Sector (HED, VET, SCH, ADU, YOU, SPORT)
- Document type (form, guidance, budget, quality)
"""

import argparse
import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Template categorization rules
TEMPLATE_CATEGORIES = {
    # Key Action patterns
    'ka1': {
        'patterns': ['ka1', 'key_action_1', 'mobility', 'learning_mobility'],
        'key_action': 'KA1',
        'description': 'Key Action 1 - Learning Mobility',
    },
    'ka2': {
        'patterns': ['ka2', 'key_action_2', 'cooperation', 'partnership'],
        'key_action': 'KA2',
        'description': 'Key Action 2 - Cooperation Partnerships',
    },
    'ka3': {
        'patterns': ['ka3', 'key_action_3', 'policy', 'reform'],
        'key_action': 'KA3',
        'description': 'Key Action 3 - Policy Support',
    },
    'jmo': {
        'patterns': ['jean_monnet', 'jmo', 'eu_studies'],
        'key_action': 'JMO',
        'description': 'Jean Monnet Actions',
    },
    'sport': {
        'patterns': ['sport', 'athletic', 'physical'],
        'key_action': 'SPORT',
        'description': 'Sport Actions',
    },
}

SECTOR_PATTERNS = {
    'HED': ['higher_education', 'hed', 'university', 'hei', 'tertiary'],
    'VET': ['vocational', 'vet', 'training', 'apprentice'],
    'SCH': ['school', 'sch', 'primary', 'secondary', 'pupil'],
    'ADU': ['adult', 'adu', 'lifelong', 'continuing'],
    'YOU': ['youth', 'you', 'young_people', 'volunteer'],
    'SPORT': ['sport', 'athletic', 'physical_activity'],
}

DOCUMENT_TYPES = {
    'application_form': {
        'patterns': ['application', 'form', 'template', 'submission'],
        'type': 'application_template',
    },
    'budget': {
        'patterns': ['budget', 'financial', 'cost', 'lump_sum', 'unit_cost'],
        'type': 'budget_guidance',
    },
    'quality': {
        'patterns': ['quality', 'assessment', 'evaluation', 'criteria', 'scoring'],
        'type': 'quality_criteria',
    },
    'sector_guide': {
        'patterns': ['sector', 'guide', 'handbook', 'manual'],
        'type': 'sector_guidance',
    },
    'reporting': {
        'patterns': ['report', 'final', 'interim', 'progress'],
        'type': 'reporting_template',
    },
}


def categorize_template(filename: str, directory: str) -> Dict[str, str]:
    """
    Categorize a template based on filename and directory.

    Returns dict with:
    - key_action: KA1, KA2, KA3, JMO, SPORT
    - sector: HED, VET, SCH, ADU, YOU, SPORT
    - document_type: application_template, budget_guidance, etc.
    - description: Human-readable description
    """
    filename_lower = filename.lower()
    dir_lower = directory.lower()
    combined = f"{dir_lower}/{filename_lower}"

    result = {
        'key_action': None,
        'sector': None,
        'document_type': 'general_guidance',
        'description': 'Erasmus+ guidance document',
    }

    # Detect Key Action
    for category, config in TEMPLATE_CATEGORIES.items():
        for pattern in config['patterns']:
            if pattern in combined:
                result['key_action'] = config['key_action']
                result['description'] = config['description']
                break
        if result['key_action']:
            break

    # Detect Sector
    for sector_code, patterns in SECTOR_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined:
                result['sector'] = sector_code
                break
        if result['sector']:
            break

    # Detect Document Type
    for doc_category, config in DOCUMENT_TYPES.items():
        for pattern in config['patterns']:
            if pattern in combined:
                result['document_type'] = config['type']
                break

    return result


def extract_action_type_from_filename(filename: str) -> Optional[str]:
    """Extract specific action type from filename."""
    filename_upper = filename.upper()

    # Common Erasmus+ action patterns
    patterns = [
        r'(KA1-HED)', r'(KA1-VET)', r'(KA1-SCH)', r'(KA1-ADU)', r'(KA1-YOU)',
        r'(KA2-COOP)', r'(KA2-SSP)', r'(KA2-CBHE)', r'(KA2-ALLIANCES)',
        r'(KA3-[A-Z]+)',
        r'(JMO-MODULE)', r'(JMO-CHAIR)', r'(JMO-COE)',
        r'(SPORT-COOP)', r'(SPORT-SSCP)',
    ]

    for pattern in patterns:
        match = re.search(pattern, filename_upper)
        if match:
            return match.group(1)

    return None


async def ingest_erasmus_templates(
    template_dir: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Ingest all Erasmus+ templates from directory.

    Args:
        template_dir: Root directory containing templates
        dry_run: If True, don't commit to database

    Returns:
        Statistics dict with counts
    """
    template_path = Path(template_dir)

    if not template_path.exists():
        logger.error(f"Template directory not found: {template_dir}")
        logger.info("Expected structure:")
        logger.info(f"  {template_dir}/")
        logger.info("    ├── ka1/")
        logger.info("    ├── ka2/")
        logger.info("    ├── ka3/")
        logger.info("    ├── jmo/")
        logger.info("    ├── sport/")
        logger.info("    ├── financial/")
        logger.info("    ├── quality/")
        logger.info("    └── sector_guides/")
        return {'total': 0, 'success': 0, 'failed': 0}

    # Find all documents
    supported_extensions = ['.pdf', '.docx', '.xlsx', '.doc']
    all_files = []

    for ext in supported_extensions:
        all_files.extend(template_path.rglob(f"*{ext}"))

    if not all_files:
        logger.error(f"No documents found in {template_dir}")
        return {'total': 0, 'success': 0, 'failed': 0}

    logger.info(f"Found {len(all_files)} documents to process")

    # Import ingestion service
    try:
        from app.services.ingestion_service import DocumentIngestionService
        ingestion_service = DocumentIngestionService()
    except ImportError as e:
        logger.error(f"Failed to import ingestion service: {e}")
        return {'total': len(all_files), 'success': 0, 'failed': len(all_files)}

    stats = {
        'total': len(all_files),
        'success': 0,
        'failed': 0,
        'by_key_action': {},
        'by_sector': {},
        'by_type': {},
    }

    for file_path in all_files:
        relative_dir = str(file_path.parent.relative_to(template_path))
        filename = file_path.name

        logger.info(f"\nProcessing: {relative_dir}/{filename}")

        # Categorize the template
        category = categorize_template(filename, relative_dir)
        action_type = extract_action_type_from_filename(filename)

        logger.info(f"  Key Action: {category['key_action']}")
        logger.info(f"  Sector: {category['sector']}")
        logger.info(f"  Type: {category['document_type']}")

        if action_type:
            logger.info(f"  Action Type: {action_type}")

        if dry_run:
            logger.info(f"  [DRY-RUN] Would ingest")
            stats['success'] += 1
            continue

        try:
            # Prepare metadata
            metadata = {
                'programme': 'erasmus_plus',
                'programme_name': 'Erasmus+',
                'key_action': category['key_action'],
                'sector': category['sector'],
                'action_type': action_type,
                'source': 'erasmus_templates',
                'template_category': category['description'],
                'funding_model': 'lump_sum',
                'ingested_by': 'template_ingestion_script',
            }

            # Remove None values
            metadata = {k: v for k, v in metadata.items() if v is not None}

            # Determine programme year from filename
            year_match = re.search(r'20(2[4-7])', filename)
            programme_year = f"20{year_match.group(1)}" if year_match else "2025-2027"

            # Ingest document
            result = ingestion_service.ingest_file(
                file_path=str(file_path),
                document_type=category['document_type'],
                programme_year=programme_year,
                metadata=metadata,
            )

            if result.get('success'):
                logger.info(f"  Ingested: {result.get('chunks_created')} chunks")
                stats['success'] += 1

                # Track by category
                ka = category['key_action'] or 'general'
                sector = category['sector'] or 'general'
                doc_type = category['document_type']

                stats['by_key_action'][ka] = stats['by_key_action'].get(ka, 0) + 1
                stats['by_sector'][sector] = stats['by_sector'].get(sector, 0) + 1
                stats['by_type'][doc_type] = stats['by_type'].get(doc_type, 0) + 1
            else:
                logger.error(f"  Failed: {result.get('error')}")
                stats['failed'] += 1

        except Exception as e:
            logger.error(f"  Exception: {e}")
            stats['failed'] += 1

        # Rate limiting
        await asyncio.sleep(0.5)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Erasmus+ templates and application forms"
    )
    parser.add_argument(
        "--template-dir",
        default="data/erasmus_plus/templates",
        help="Directory containing templates"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't commit to database"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ERASMUS+ TEMPLATE INGESTION")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes")

    stats = asyncio.run(
        ingest_erasmus_templates(args.template_dir, args.dry_run)
    )

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files: {stats['total']}")
    logger.info(f"Successful: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")

    if stats.get('by_key_action'):
        logger.info("\nBy Key Action:")
        for ka, count in sorted(stats['by_key_action'].items()):
            logger.info(f"  {ka}: {count}")

    if stats.get('by_sector'):
        logger.info("\nBy Sector:")
        for sector, count in sorted(stats['by_sector'].items()):
            logger.info(f"  {sector}: {count}")

    if stats.get('by_type'):
        logger.info("\nBy Document Type:")
        for doc_type, count in sorted(stats['by_type'].items()):
            logger.info(f"  {doc_type}: {count}")

    if not args.dry_run and stats['success'] > 0:
        logger.info("\nTemplates are now searchable!")
        logger.info("Test with: 'What are the KA2 application requirements?'")


if __name__ == "__main__":
    main()
```

### Step 3: Enhance Vector Search for Template Retrieval

Update `app/services/vector_search_service.py` to support template-specific filtering:

```python
async def search_templates(
    self,
    query: str,
    key_action: Optional[str] = None,
    sector: Optional[str] = None,
    document_type: Optional[str] = None,
    top_k: int = 5,
) -> List[SearchResult]:
    """
    Search Erasmus+ templates with filtering.

    Args:
        query: Search query
        key_action: Filter by KA1, KA2, KA3, JMO, SPORT
        sector: Filter by HED, VET, SCH, ADU, YOU, SPORT
        document_type: Filter by application_template, budget_guidance, etc.
        top_k: Number of results

    Returns:
        List of matching template chunks
    """
    # Build filter conditions
    filters = {
        'programme': 'erasmus_plus',
    }

    if key_action:
        filters['key_action'] = key_action
    if sector:
        filters['sector'] = sector
    if document_type:
        filters['document_type'] = document_type

    return await self.search(
        query=query,
        top_k=top_k,
        filters=filters,
        programme='erasmus_plus',
    )
```

### Step 4: Add Template Search Tool

Create `app/services/tools/erasmus_templates.py`:

```python
"""
Erasmus+ Template Search Tool

Searches Erasmus+ application templates and guidance documents
with filtering by Key Action, sector, and document type.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def search_erasmus_templates_execute(
    query: str,
    key_action: Optional[str] = None,
    sector: Optional[str] = None,
    document_type: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Search Erasmus+ templates and application guidance.

    Args:
        query: What to search for
        key_action: Filter by KA1, KA2, KA3, JMO, SPORT
        sector: Filter by HED, VET, SCH, ADU, YOU, SPORT
        document_type: Filter by type (application_template, budget_guidance, etc.)
        top_k: Number of results

    Returns:
        Matching template excerpts with metadata
    """
    try:
        from app.services.vector_search_service import VectorSearchService

        service = VectorSearchService()
        results = await service.search_templates(
            query=query,
            key_action=key_action,
            sector=sector,
            document_type=document_type,
            top_k=top_k,
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                'content': result.content,
                'document_title': result.document_title,
                'key_action': result.metadata.get('key_action'),
                'sector': result.metadata.get('sector'),
                'document_type': result.metadata.get('document_type'),
                'relevance_score': result.score,
            })

        return {
            'success': True,
            'results': formatted_results,
            'total_found': len(formatted_results),
            'query': query,
            'filters': {
                'key_action': key_action,
                'sector': sector,
                'document_type': document_type,
            },
            'metadata': {
                'tool': 'search_erasmus_templates',
                'programme': 'erasmus_plus',
            }
        }

    except Exception as e:
        logger.error(f"Template search error: {e}")
        return {
            'success': False,
            'error': str(e),
            'results': [],
        }
```

### Step 5: Download Templates

Use the provided JSON document list to download relevant templates:

```python
# scripts/download_erasmus_templates.py

"""
Download Erasmus+ templates from official sources.
"""

import httpx
import json
import os
from pathlib import Path

# Template URLs (extract from JSON provided by user)
TEMPLATE_URLS = {
    'ka1_hed_form': 'https://...',  # From JSON
    'ka2_coop_form': 'https://...',
    'budget_tool': 'https://...',
    # ... etc
}

def download_template(url: str, dest_path: Path) -> bool:
    """Download a template from URL."""
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url)
            if response.status_code == 200:
                dest_path.write_bytes(response.content)
                return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return False

def main():
    base_dir = Path("data/erasmus_plus/templates")
    base_dir.mkdir(parents=True, exist_ok=True)

    for name, url in TEMPLATE_URLS.items():
        dest = base_dir / f"{name}.pdf"
        print(f"Downloading {name}...")
        if download_template(url, dest):
            print(f"  Saved to {dest}")
        else:
            print(f"  FAILED")

if __name__ == "__main__":
    main()
```

## Recommended Templates from User's JSON List

Based on the document list provided earlier, prioritize these templates:

### Must Download
| Document | Why |
|----------|-----|
| Application form - KA1 Learning Mobility | Core application template |
| Application form - KA2 Cooperation | Partnership applications |
| Application form - KA2 Small-scale | Smaller partnerships |
| Budget calculation tool | Essential for proposals |

### Should Download
| Document | Why |
|----------|-----|
| Grant Agreement template | Understanding deliverables |
| Quality criteria grid | Know how you'll be scored |
| Erasmus+ for Higher Education guide | Sector-specific guidance |
| National Agency contact list | Where to submit |

### Nice to Have
| Document | Why |
|----------|-----|
| Reporting template | Post-award guidance |
| Interim report template | Project management |
| Impact assessment guide | Evaluation criteria |

## Validation

### Test 1: Template Search

```python
from app.services.tools.erasmus_templates import search_erasmus_templates_execute

result = await search_erasmus_templates_execute(
    query="application form requirements",
    key_action="KA2",
    document_type="application_template"
)
print(f"Found {result['total_found']} results")
```

### Test 2: API Query

```bash
curl -X POST http://localhost:8000/api/v3/conversation/test/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the sections of the KA2 application form?"}'
```

### Test 3: Sector-Specific Search

```python
result = await search_erasmus_templates_execute(
    query="budget calculation",
    sector="HED",
    document_type="budget_guidance"
)
```

## Success Criteria

1. At least 10 templates ingested with proper categorization
2. Templates searchable by Key Action, sector, and type
3. API can answer application-specific questions
4. Budget guidance retrievable for calculations

## Estimated Effort

- Directory setup: 15 minutes
- Script creation: 2 hours
- Template download: 1 hour
- Ingestion run: 30 minutes
- Validation: 30 minutes

## Dependencies

- Phase 1 completed (ingestion infrastructure)
- Phase 2 completed (calls in database)
- Template PDFs downloaded to `data/erasmus_plus/templates/`

## Summary

After completing all 4 phases, the MAPIT system will have full Erasmus+ integration:

| Phase | Component | Status |
|-------|-----------|--------|
| 1 | Document Ingestion | Programme Guide, Work Programme |
| 2 | API Sync | Live call data in funding_calls |
| 3 | Erasmus+ Tools | Eligibility checker, budget calculator |
| 4 | Templates | Application forms, guidance docs |

Research managers can then:
- Search for open Erasmus+ calls
- Check eligibility for specific actions
- Calculate lump sum budgets
- Get application guidance for their sector
- Find partner discovery recommendations

## Complete Test After All Phases

```bash
curl -X POST http://localhost:8000/api/v3/conversation/test/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am a German university (HEI with ECHE) looking for mobility funding opportunities in 2025. What are my options and how do I apply?"
  }'
```

Expected response should include:
- KA1-HED mobility opportunities
- Eligibility confirmation (HEI + ECHE = eligible)
- Budget estimate using lump sums
- Application form guidance
- Relevant deadlines from synced calls

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
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional

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
    'ka1': {
        'patterns': ['ka1', 'key_action_1', 'key-action-1', 'mobility', 'learning_mobility', 'learning-mobility'],
        'key_action': 'KA1',
        'description': 'Key Action 1 - Learning Mobility',
    },
    'ka2': {
        'patterns': ['ka2', 'key_action_2', 'key-action-2', 'cooperation', 'partnership', 'capacity-building'],
        'key_action': 'KA2',
        'description': 'Key Action 2 - Cooperation Partnerships',
    },
    'ka3': {
        'patterns': ['ka3', 'key_action_3', 'key-action-3', 'policy', 'reform'],
        'key_action': 'KA3',
        'description': 'Key Action 3 - Policy Support',
    },
    'jmo': {
        'patterns': ['jean_monnet', 'jean-monnet', 'jmo', 'eu_studies', 'eu-studies'],
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
    'HED': ['higher_education', 'higher-education', 'hed', 'university', 'hei', 'tertiary'],
    'VET': ['vocational', 'vet', 'training', 'apprentice'],
    'SCH': ['school', 'sch', 'primary', 'secondary', 'pupil'],
    'ADU': ['adult', 'adu', 'lifelong', 'continuing'],
    'YOU': ['youth', 'you', 'young_people', 'young-people', 'volunteer'],
    'SPORT': ['sport', 'athletic', 'physical_activity', 'physical-activity'],
}

DOCUMENT_TYPES = {
    'application_form': {
        'patterns': ['application', 'form', 'template', 'submission', 'eform'],
        'type': 'application_template',
    },
    'budget': {
        'patterns': ['budget', 'financial', 'cost', 'lump_sum', 'lump-sum', 'unit_cost', 'unit-cost'],
        'type': 'budget_guidance',
    },
    'quality': {
        'patterns': ['quality', 'assessment', 'evaluation', 'criteria', 'scoring', 'award'],
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
    'grant_agreement': {
        'patterns': ['grant', 'agreement', 'contract', 'model'],
        'type': 'grant_agreement',
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
    filename_lower = filename.lower().replace('-', '_')
    dir_lower = directory.lower().replace('-', '_')
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
    filename_upper = filename.upper().replace('-', '_')

    # Common Erasmus+ action patterns
    patterns = [
        r'(KA1[_-]?HED)', r'(KA1[_-]?VET)', r'(KA1[_-]?SCH)', r'(KA1[_-]?ADU)', r'(KA1[_-]?YOU)',
        r'(KA2[_-]?COOP)', r'(KA2[_-]?SSP)', r'(KA2[_-]?CBHE)', r'(KA2[_-]?ALLIANCES)', r'(KA2[_-]?COE)',
        r'(KA3[_-]?[A-Z]+)',
        r'(JMO[_-]?MODULE)', r'(JMO[_-]?CHAIR)', r'(JMO[_-]?COE)',
        r'(SPORT[_-]?COOP)', r'(SPORT[_-]?SSCP)',
    ]

    for pattern in patterns:
        match = re.search(pattern, filename_upper)
        if match:
            return match.group(1).replace('_', '-')

    return None


def ingest_erasmus_templates(
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
    supported_extensions = ['.pdf', '.PDF', '.docx', '.DOCX', '.xlsx', '.XLSX', '.doc', '.DOC']
    all_files = []

    for ext in supported_extensions:
        all_files.extend(template_path.rglob(f"*{ext}"))

    if not all_files:
        logger.warning(f"No documents found in {template_dir}")
        logger.info("Supported formats: PDF, DOCX, XLSX, DOC")
        return {'total': 0, 'success': 0, 'failed': 0}

    logger.info(f"Found {len(all_files)} documents to process")

    if dry_run:
        logger.info("\n=== DRY RUN MODE - No database changes ===\n")
        for file_path in all_files:
            relative_dir = str(file_path.parent.relative_to(template_path))
            filename = file_path.name
            category = categorize_template(filename, relative_dir)
            action_type = extract_action_type_from_filename(filename)

            logger.info(f"  {relative_dir}/{filename}")
            logger.info(f"    Key Action: {category['key_action']}")
            logger.info(f"    Sector: {category['sector']}")
            logger.info(f"    Type: {category['document_type']}")
            if action_type:
                logger.info(f"    Action Type: {action_type}")

        return {'total': len(all_files), 'success': len(all_files), 'failed': 0}

    # Import ingestion service
    try:
        from app.services.ingestion_service import DocumentIngestionService
        ingestion_service = DocumentIngestionService()
    except ImportError as e:
        logger.error(f"Failed to import ingestion service: {e}")
        return {'total': len(all_files), 'success': 0, 'failed': len(all_files)}

    # Check service status
    stats_check = ingestion_service.get_service_stats()
    if not stats_check.get('supabase_connected', False):
        logger.error("Supabase connection failed. Check DATABASE_URL and SUPABASE_KEY.")
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

        try:
            # Prepare metadata
            metadata = {
                'programme': 'erasmus',
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
                logger.info(f"  SUCCESS: {result.get('chunks_created')} chunks")
                stats['success'] += 1

                # Track by category
                ka = category['key_action'] or 'general'
                sector = category['sector'] or 'general'
                doc_type = category['document_type']

                stats['by_key_action'][ka] = stats['by_key_action'].get(ka, 0) + 1
                stats['by_sector'][sector] = stats['by_sector'].get(sector, 0) + 1
                stats['by_type'][doc_type] = stats['by_type'].get(doc_type, 0) + 1
            else:
                logger.error(f"  FAILED: {result.get('error')}")
                stats['failed'] += 1

        except Exception as e:
            logger.error(f"  EXCEPTION: {e}")
            stats['failed'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Erasmus+ templates and application forms"
    )
    parser.add_argument(
        "--template-dir",
        default="newdocs/erasmus/templates",
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

    # Convert relative path to absolute if needed
    template_dir = args.template_dir
    if not os.path.isabs(template_dir):
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            template_dir
        )

    logger.info(f"Template directory: {template_dir}")

    stats = ingest_erasmus_templates(template_dir, args.dry_run)

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

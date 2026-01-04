#!/usr/bin/env python3
"""
LIFE Programme Document Ingestion Script

Ingests LIFE Programme Work Programmes, Regulation, and related documents
into the RAG system with proper programme tagging.

Usage:
    python scripts/ingest_life_documents.py [--source-dir DIR] [--dry-run]

Options:
    --source-dir    Directory containing LIFE PDFs (default: newdocs/life)
    --dry-run       Don't commit to database, just show what would be ingested
"""

import argparse
import logging
import os
import re
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


# LIFE document type mappings
LIFE_DOCUMENT_TYPES = {
    'work_programme': {
        'patterns': ['work_programme', 'work-programme', 'mawp', 'multiannual'],
        'type': 'work_programme',
        'description': 'LIFE Multiannual Work Programme with priorities and budgets'
    },
    'regulation': {
        'patterns': ['regulation', '2021_783', '2021-783', 'celex'],
        'type': 'programme_guide',
        'description': 'LIFE Regulation establishing the programme'
    },
    'priority_topics': {
        'patterns': ['priority', 'topics', 'priorities'],
        'type': 'programme_guide',
        'description': 'LIFE Priority Topics for project applications'
    },
    'nature_biodiversity': {
        'patterns': ['nature', 'biodiversity', 'natura', 'habitat'],
        'type': 'programme_guide',
        'description': 'Nature and Biodiversity sub-programme guidance'
    },
    'circular_economy': {
        'patterns': ['circular', 'economy', 'quality_of_life', 'resource'],
        'type': 'programme_guide',
        'description': 'Circular Economy and Quality of Life guidance'
    },
    'climate': {
        'patterns': ['climate', 'mitigation', 'adaptation'],
        'type': 'programme_guide',
        'description': 'Climate Change Mitigation and Adaptation guidance'
    },
    'clean_energy': {
        'patterns': ['energy', 'transition', 'clean_energy', 'renewable'],
        'type': 'programme_guide',
        'description': 'Clean Energy Transition sub-programme guidance'
    },
    'application_guide': {
        'patterns': ['application', 'guide', 'how_to', 'howto'],
        'type': 'manual',
        'description': 'Application guidance and templates'
    },
}

# LIFE Sub-programmes
LIFE_SUBPROGRAMMES = {
    'NAT': 'Nature and Biodiversity',
    'ENV': 'Circular Economy and Quality of Life',
    'CCA': 'Climate Change Mitigation and Adaptation',
    'CET': 'Clean Energy Transition',
}


def detect_document_type(filename: str) -> tuple[str, str]:
    """
    Detect document type from filename.

    Returns:
        tuple: (document_type, description)
    """
    filename_lower = filename.lower()

    for doc_type, config in LIFE_DOCUMENT_TYPES.items():
        for pattern in config['patterns']:
            if pattern in filename_lower:
                return config['type'], config['description']

    # Default fallback
    return 'guidance_document', 'LIFE Programme guidance document'


def extract_year_from_filename(filename: str) -> str:
    """Extract programme year from filename."""
    # Match years like 2021, 2022, 2023, 2024, 2025, 2026, 2027
    year_match = re.search(r'20(2[1-7])', filename)
    if year_match:
        return f"20{year_match.group(1)}"

    # Match year ranges like 2021-2024, 2025-2027
    range_match = re.search(r'(202[1-7])[-_](202[1-7])', filename)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"

    return "2021-2027"  # Default to programme period


def detect_subprogramme(content_preview: str) -> list[str]:
    """Detect LIFE sub-programmes from document content."""
    content_lower = content_preview.lower() if content_preview else ""
    subprogrammes = []

    if any(kw in content_lower for kw in ['nature', 'biodiversity', 'natura 2000', 'habitat', 'species']):
        subprogrammes.append('NAT')
    if any(kw in content_lower for kw in ['circular economy', 'waste', 'water', 'air quality', 'soil']):
        subprogrammes.append('ENV')
    if any(kw in content_lower for kw in ['climate change', 'mitigation', 'adaptation', 'greenhouse']):
        subprogrammes.append('CCA')
    if any(kw in content_lower for kw in ['clean energy', 'energy transition', 'renewable', 'energy efficiency']):
        subprogrammes.append('CET')

    return subprogrammes or ['general']


def ingest_life_documents(source_dir: str, dry_run: bool = False):
    """Ingest all LIFE documents from source directory."""

    source_path = Path(source_dir)

    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.info("Please create the directory and add LIFE PDF documents:")
        logger.info(f"  mkdir -p {source_dir}")
        logger.info("  # Then download Work Programmes, Regulation, etc.")
        return False

    # Find all PDF files (including subdirectories)
    pdf_files = list(source_path.rglob("*.pdf")) + list(source_path.rglob("*.PDF"))

    if not pdf_files:
        logger.error(f"No PDF files found in {source_dir}")
        return False

    logger.info(f"Found {len(pdf_files)} PDF files to ingest")

    if dry_run:
        logger.info("\n=== DRY RUN MODE - No database changes ===\n")
        for pdf_file in pdf_files:
            doc_type, doc_description = detect_document_type(pdf_file.name)
            programme_year = extract_year_from_filename(pdf_file.name)
            logger.info(f"  {pdf_file.name}")
            logger.info(f"    Type: {doc_type}")
            logger.info(f"    Year: {programme_year}")
            logger.info(f"    Description: {doc_description}")
        return True

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
        logger.error("Supabase connection failed. Check DATABASE_URL and SUPABASE_KEY.")
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

        try:
            # Ingest the document with LIFE specific metadata
            result = ingestion_service.ingest_file(
                file_path=str(pdf_file),
                document_type=doc_type,
                programme_year=programme_year,
                metadata={
                    "programme": "life",
                    "programme_name": "LIFE Programme for Environment and Climate Action",
                    "source": "official_eu_portal",
                    "language": "en",
                    "description": doc_description,
                    "ingested_by": "life_ingestion_script",
                    "budget": "5.432 billion EUR (2021-2027)",
                    "implementing_agency": "CINEA",
                }
            )

            if result.get('success'):
                logger.info(f"  SUCCESS: {pdf_file.name}")
                logger.info(f"    Document ID: {result.get('document_id')}")
                logger.info(f"    Chunks: {result.get('chunks_created')}")
                successful += 1
            else:
                logger.error(f"  FAILED: {result.get('error')}")
                failed.append(pdf_file.name)

        except Exception as e:
            logger.error(f"  EXCEPTION: {e}")
            failed.append(pdf_file.name)

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
        description="Ingest LIFE Programme documents into RAG system"
    )
    parser.add_argument(
        "--source-dir",
        default="newdocs/life",
        help="Directory containing LIFE PDFs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't commit to database"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("LIFE PROGRAMME DOCUMENT INGESTION")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes")

    # Convert relative path to absolute if needed
    source_dir = args.source_dir
    if not os.path.isabs(source_dir):
        source_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            source_dir
        )

    logger.info(f"Source directory: {source_dir}")

    success = ingest_life_documents(source_dir, args.dry_run)

    if success:
        logger.info("\nIngestion completed!")
        logger.info("\nNext steps:")
        logger.info("1. Run: python scripts/sync_life_calls_from_api.py")
        logger.info("2. Create LIFE eligibility tools")
        logger.info("3. Test with LIFE queries")
    else:
        logger.error("\nIngestion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

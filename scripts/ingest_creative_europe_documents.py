#!/usr/bin/env python3
"""
Creative Europe Document Ingestion Script

Ingests Creative Europe Programme Work Programmes, Funding Guides, and strand overviews
into the RAG system with proper programme tagging.

Creative Europe has three strands:
- CULTURE: Support for cultural and creative sectors
- MEDIA: Support for audiovisual and film industries
- Cross-sectoral: News media, innovation labs, cross-cutting initiatives

Usage:
    python scripts/ingest_creative_europe_documents.py [--source-dir DIR] [--dry-run]

Options:
    --source-dir    Directory containing Creative Europe PDFs (default: newdocs/creative_europe)
    --dry-run       Don't commit to database, just show what would be ingested
"""

import argparse
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


# Creative Europe document type mappings
# Valid database document_type values: work_programme, programme_guide, call_text,
# grant_agreement, faq, manual, policy, template, additional_resource
CREATIVE_EUROPE_DOCUMENT_TYPES = {
    'annual_work_programme': {
        'patterns': ['annual_work_programme', 'work_programme', 'awp_', '2026_annual', '2025_annual', '2024_annual', '2023_annual', '2022_annual', '2021_annual'],
        'type': 'work_programme',
        'description': 'Creative Europe Annual Work Programme - calls, budgets, objectives'
    },
    'funding_guide': {
        'patterns': ['cultureu', 'funding_guide', 'funding-guide'],
        'type': 'programme_guide',  # Use valid type
        'description': 'CulturEU Funding Guide - comprehensive EU funding for cultural sectors'
    },
    'culture_strand': {
        'patterns': ['culture_strand', 'culture_overview', 'culture_creative_europe'],
        'type': 'programme_guide',  # Use valid type
        'description': 'CULTURE strand - European cooperation projects, networks, platforms'
    },
    'media_strand': {
        'patterns': ['media_strand', 'media_overview', 'media_creative_europe'],
        'type': 'programme_guide',  # Use valid type
        'description': 'MEDIA strand - audiovisual, film development, distribution, training'
    },
    'cross_sectoral': {
        'patterns': ['cross_sectoral', 'cross-sectoral', 'crosssectoral'],
        'type': 'programme_guide',  # Use valid type
        'description': 'Cross-sectoral strand - news media, innovation labs'
    },
    'green_aspects': {
        'patterns': ['green', 'sustainability', 'environmental'],
        'type': 'policy',  # Use valid type - evaluation/sustainability policy
        'description': 'Green aspects quality assessment - sustainability evaluation criteria'
    },
    'programme_brochure': {
        'patterns': ['brochure', 'overview', 'programme_guide'],
        'type': 'additional_resource',  # Use valid type
        'description': 'Creative Europe Programme overview and objectives'
    },
}


def detect_document_type(filename: str) -> tuple[str, str]:
    """
    Detect document type from filename.

    Returns:
        tuple: (document_type, description)
    """
    filename_lower = filename.lower()

    for doc_type, config in CREATIVE_EUROPE_DOCUMENT_TYPES.items():
        for pattern in config['patterns']:
            if pattern in filename_lower:
                return config['type'], config['description']

    # Default fallback
    return 'guidance_document', 'Creative Europe guidance document'


def extract_year_from_filename(filename: str) -> str:
    """Extract programme year from filename."""
    import re

    # Match years like 2021, 2022, 2023, 2024, 2025, 2026, 2027
    year_match = re.search(r'20(2[1-7])', filename)
    if year_match:
        return f"20{year_match.group(1)}"

    # Match year ranges like 2021-2027
    range_match = re.search(r'(202[1-7])[-_](202[1-7])', filename)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"

    return "2021-2027"  # Default to current programme period


def detect_strand(filename: str) -> str:
    """Detect which Creative Europe strand the document relates to."""
    filename_lower = filename.lower()

    if 'media' in filename_lower:
        return 'MEDIA'
    elif 'culture' in filename_lower and 'cross' not in filename_lower:
        return 'CULTURE'
    elif 'cross' in filename_lower or 'sectoral' in filename_lower:
        return 'CROSS-SECTORAL'
    else:
        return 'ALL'  # Applies to entire programme


def ingest_creative_europe_documents(source_dir: str, dry_run: bool = False):
    """Ingest all Creative Europe documents from source directory."""

    source_path = Path(source_dir)

    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.info("Please create the directory and add Creative Europe PDF documents:")
        logger.info(f"  mkdir -p {source_dir}")
        return False

    # Find all PDF files recursively
    pdf_files = list(source_path.glob("**/*.pdf")) + list(source_path.glob("**/*.PDF"))

    if not pdf_files:
        logger.error(f"No PDF files found in {source_dir}")
        return False

    logger.info(f"Found {len(pdf_files)} PDF files to ingest")

    if dry_run:
        logger.info("\n=== DRY RUN MODE - No database changes ===\n")
        for pdf_file in pdf_files:
            doc_type, doc_description = detect_document_type(pdf_file.name)
            programme_year = extract_year_from_filename(pdf_file.name)
            strand = detect_strand(pdf_file.name)
            logger.info(f"  {pdf_file.name}")
            logger.info(f"    Type: {doc_type}")
            logger.info(f"    Strand: {strand}")
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

        # Detect document type and metadata
        doc_type, doc_description = detect_document_type(pdf_file.name)
        programme_year = extract_year_from_filename(pdf_file.name)
        strand = detect_strand(pdf_file.name)

        logger.info(f"  Type: {doc_type}")
        logger.info(f"  Strand: {strand}")
        logger.info(f"  Year: {programme_year}")

        try:
            # Ingest the document with Creative Europe specific metadata
            result = ingestion_service.ingest_file(
                file_path=str(pdf_file),
                document_type=doc_type,
                programme_year=programme_year,
                metadata={
                    "programme": "creative_europe",
                    "programme_name": "Creative Europe",
                    "strand": strand,
                    "source": "official_eu_portal",
                    "language": "en",
                    "description": doc_description,
                    "ingested_by": "creative_europe_ingestion_script",
                    "funding_model": "grants",
                    "programme_period": "2021-2027",
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
        logger.info("\nDatabase Stats:")
        logger.info(f"  Total Documents: {final_stats.get('total_documents', 0)}")
        logger.info(f"  Total Chunks: {final_stats.get('total_chunks', 0)}")
    except Exception as e:
        logger.warning(f"Could not get final stats: {e}")

    return successful > 0


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Creative Europe documents into RAG system"
    )
    parser.add_argument(
        "--source-dir",
        default="newdocs/creative_europe",
        help="Directory containing Creative Europe PDFs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't commit to database"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("CREATIVE EUROPE DOCUMENT INGESTION")
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

    success = ingest_creative_europe_documents(source_dir, args.dry_run)

    if success:
        logger.info("\nIngestion completed!")
        logger.info("\nNext steps:")
        logger.info("1. Run: python scripts/sync_creative_europe_calls.py")
        logger.info("2. Test with: curl -X POST http://localhost:8000/api/v3/conversation/test/message")
    else:
        logger.error("\nIngestion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

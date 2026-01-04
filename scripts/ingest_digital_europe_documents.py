#!/usr/bin/env python3
"""
Digital Europe Document Ingestion Script

Ingests Digital Europe Work Programmes, Regulation, and related documents
into the RAG system with proper programme tagging.

Usage:
    python scripts/ingest_digital_europe_documents.py [--source-dir DIR] [--dry-run]

Options:
    --source-dir    Directory containing Digital Europe PDFs (default: newdocs/digital_europe)
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


# Digital Europe document type mappings
DIGITAL_EUROPE_DOCUMENT_TYPES = {
    'work_programme': {
        'patterns': ['work_programme', 'work-programme', 'wp_', 'wp-', 'wp2023', 'wp2024', 'wp2025'],
        'type': 'work_programme',
        'description': 'Digital Europe Work Programme with call topics and budgets'
    },
    'regulation': {
        'patterns': ['regulation', '2021_694', '2021-694', 'celex'],
        'type': 'programme_guide',  # Use valid type
        'description': 'Digital Europe Regulation establishing the programme'
    },
    'implementing_decision': {
        'patterns': ['implementing_decision', 'implementing-decision', 'c2025', 'c2024'],
        'type': 'grant_agreement',  # Use valid type
        'description': 'Commission Implementing Decision on financing and work programme'
    },
    'amendment': {
        'patterns': ['amendment', 'amend', 'amended'],
        'type': 'work_programme',  # Use valid type
        'description': 'Work Programme Amendment'
    },
    'cybersecurity': {
        'patterns': ['cybersecurity', 'cyber', 'eccc'],
        'type': 'programme_guide',  # Use valid type
        'description': 'Cybersecurity-specific work programme (ECCC managed)'
    },
    'ai': {
        'patterns': ['ai_', 'artificial_intelligence', 'ai-factories'],
        'type': 'programme_guide',  # Use valid type
        'description': 'AI-specific guidance and work programme'
    },
    'edih': {
        'patterns': ['edih', 'innovation_hub', 'digital_innovation'],
        'type': 'programme_guide',  # Use valid type
        'description': 'European Digital Innovation Hubs guidance'
    },
    'skills': {
        'patterns': ['skills', 'training', 'education'],
        'type': 'manual',  # Use valid type
        'description': 'Advanced Digital Skills guidance'
    },
}

# Digital Europe Specific Objectives
DIGITAL_EUROPE_OBJECTIVES = {
    'hpc': 'High Performance Computing',
    'ai': 'Artificial Intelligence',
    'cybersecurity': 'Cybersecurity and Trust',
    'skills': 'Advanced Digital Skills',
    'deployment': 'Deployment and Best Use of Digital Capacities',
    'semiconductors': 'Semiconductors (Chips Act)',
}


def detect_document_type(filename: str) -> tuple[str, str]:
    """
    Detect document type from filename.

    Returns:
        tuple: (document_type, description)
    """
    filename_lower = filename.lower()

    for doc_type, config in DIGITAL_EUROPE_DOCUMENT_TYPES.items():
        for pattern in config['patterns']:
            if pattern in filename_lower:
                return config['type'], config['description']

    # Default fallback
    return 'guidance_document', 'Digital Europe guidance document'


def extract_year_from_filename(filename: str) -> str:
    """Extract programme year from filename."""
    # Match years like 2021, 2022, 2023, 2024, 2025, 2026, 2027
    year_match = re.search(r'20(2[1-7])', filename)
    if year_match:
        return f"20{year_match.group(1)}"

    # Match year ranges like 2021-2022, 2023-2024, 2025-2027
    range_match = re.search(r'(202[1-7])[-_](202[1-7])', filename)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"

    return "2021-2027"  # Default to programme period


def detect_objective(content_preview: str) -> list[str]:
    """Detect Digital Europe objectives from document content."""
    content_lower = content_preview.lower() if content_preview else ""
    objectives = []

    if any(kw in content_lower for kw in ['supercomputing', 'hpc', 'exascale', 'eurohpc']):
        objectives.append('hpc')
    if any(kw in content_lower for kw in ['artificial intelligence', ' ai ', 'machine learning', 'ai factories']):
        objectives.append('ai')
    if any(kw in content_lower for kw in ['cybersecurity', 'cyber', 'soc', 'security']):
        objectives.append('cybersecurity')
    if any(kw in content_lower for kw in ['digital skills', 'training', 'education', 'workforce']):
        objectives.append('skills')
    if any(kw in content_lower for kw in ['deployment', 'edih', 'interoperability', 'digital transformation']):
        objectives.append('deployment')
    if any(kw in content_lower for kw in ['semiconductor', 'chips', 'microelectronics']):
        objectives.append('semiconductors')

    return objectives or ['general']


def ingest_digital_europe_documents(source_dir: str, dry_run: bool = False):
    """Ingest all Digital Europe documents from source directory."""

    source_path = Path(source_dir)

    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.info("Please create the directory and add Digital Europe PDF documents:")
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
            # Ingest the document with Digital Europe specific metadata
            result = ingestion_service.ingest_file(
                file_path=str(pdf_file),
                document_type=doc_type,
                programme_year=programme_year,
                metadata={
                    "programme": "digital_europe",
                    "programme_name": "Digital Europe Programme",
                    "source": "official_eu_portal",
                    "language": "en",
                    "description": doc_description,
                    "ingested_by": "digital_europe_ingestion_script",
                    "budget": "7.588 billion EUR (2021-2027)",
                    "implementing_agency": "DG CONNECT / HaDEA",
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
        description="Ingest Digital Europe documents into RAG system"
    )
    parser.add_argument(
        "--source-dir",
        default="newdocs/digital_europe",
        help="Directory containing Digital Europe PDFs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't commit to database"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("DIGITAL EUROPE DOCUMENT INGESTION")
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

    success = ingest_digital_europe_documents(source_dir, args.dry_run)

    if success:
        logger.info("\nIngestion completed!")
        logger.info("\nNext steps:")
        logger.info("1. Run: python scripts/sync_digital_europe_calls_from_api.py")
        logger.info("2. Create Digital Europe eligibility tools")
        logger.info("3. Test with Digital Europe queries")
    else:
        logger.error("\nIngestion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

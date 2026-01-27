#!/usr/bin/env python3
"""
EU4Health Document Ingestion Script

Ingests EU4Health Annual Work Programmes, Regulation, and related documents
into the RAG system with proper programme tagging.

Usage:
    python scripts/ingest_eu4health_documents.py [--source-dir DIR] [--dry-run]

Options:
    --source-dir    Directory containing EU4Health PDFs (default: newdocs/eu4health)
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


# EU4Health document type mappings
EU4HEALTH_DOCUMENT_TYPES = {
    'annual_work_programme': {
        'patterns': ['awp', 'work_programme', 'work-programme', 'annual_work', 'c2024', 'c2023', 'c2025'],
        'type': 'work_programme',
        'description': 'EU4Health Annual Work Programme with call topics and budgets'
    },
    'regulation': {
        'patterns': ['regulation', '2021_522', '2021-522', 'celex'],
        'type': 'programme_guide',  # Use valid type - regulation is the foundational guide
        'description': 'EU4Health Regulation establishing the programme'
    },
    'call_document': {
        'patterns': ['call_for_proposals', 'call-for-proposals', 'cfp_', 'call_'],
        'type': 'grant_agreement',  # Use valid type
        'description': 'Call for proposals with eligibility and deadlines'
    },
    'action_grant': {
        'patterns': ['action_grant', 'ag_', 'direct_grant', 'project_grant'],
        'type': 'template',  # Use valid type
        'description': 'Action Grant guidance and templates'
    },
    'joint_action': {
        'patterns': ['joint_action', 'ja_', 'member_state'],
        'type': 'manual',  # Use valid type
        'description': 'Joint Action with Member States guidance'
    },
    'procurement': {
        'patterns': ['procurement', 'tender', 'contract'],
        'type': 'manual',  # Use valid type
        'description': 'Procurement and tendering guidance'
    },
    'crisis_preparedness': {
        'patterns': ['crisis', 'preparedness', 'emergency', 'resilience'],
        'type': 'programme_guide',  # Use valid type
        'description': 'Crisis preparedness and health security guidance'
    },
    'disease_prevention': {
        'patterns': ['prevention', 'disease', 'cancer', 'ncd', 'screening'],
        'type': 'programme_guide',  # Use valid type
        'description': 'Disease prevention and health promotion guidance'
    },
    'health_systems': {
        'patterns': ['health_system', 'workforce', 'hta', 'ehr', 'ehds'],
        'type': 'programme_guide',  # Use valid type
        'description': 'Health systems and digital health guidance'
    },
    'digital_health': {
        'patterns': ['digital', 'ehealth', 'telemedicine', 'data'],
        'type': 'programme_guide',  # Use valid type
        'description': 'Digital health and EHDS guidance'
    },
}

# EU4Health funding strands
EU4HEALTH_STRANDS = {
    'crisis': 'Crisis Preparedness',
    'prevention': 'Disease Prevention & Health Promotion',
    'health_systems': 'Health Systems & Workforce',
    'digital': 'Digital Health',
}


def detect_document_type(filename: str) -> tuple[str, str]:
    """
    Detect document type from filename.

    Returns:
        tuple: (document_type, description)
    """
    filename_lower = filename.lower()

    for doc_type, config in EU4HEALTH_DOCUMENT_TYPES.items():
        for pattern in config['patterns']:
            if pattern in filename_lower:
                return config['type'], config['description']

    # Default fallback
    return 'guidance_document', 'EU4Health guidance document'


def extract_year_from_filename(filename: str) -> str:
    """Extract programme year from filename."""
    import re

    # Match years like 2021, 2022, 2023, 2024, 2025
    year_match = re.search(r'20(2[1-7])', filename)
    if year_match:
        return f"20{year_match.group(1)}"

    # Match c2024, c2023 patterns (Commission decision numbers)
    c_year_match = re.search(r'c(202[1-7])', filename.lower())
    if c_year_match:
        return c_year_match.group(1)

    # Match year ranges like 2021-2027
    range_match = re.search(r'(202[1-7])[-_](202[1-7])', filename)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"

    return "2021-2027"  # Default to programme period


def detect_strand(content_preview: str) -> list[str]:
    """Detect EU4Health strands from document content."""
    content_lower = content_preview.lower() if content_preview else ""
    strands = []

    if any(kw in content_lower for kw in ['crisis', 'preparedness', 'emergency', 'resilience', 'antimicrobial', 'amr']):
        strands.append('crisis')
    if any(kw in content_lower for kw in ['prevention', 'cancer', 'ncd', 'screening', 'vaccination', 'hiv']):
        strands.append('prevention')
    if any(kw in content_lower for kw in ['health system', 'workforce', 'hta', 'shortage', 'medicines']):
        strands.append('health_systems')
    if any(kw in content_lower for kw in ['digital', 'ehealth', 'ehds', 'data', 'telemedicine']):
        strands.append('digital')

    return strands or ['general']


def ingest_eu4health_documents(source_dir: str, dry_run: bool = False):
    """Ingest all EU4Health documents from source directory."""

    source_path = Path(source_dir)

    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.info("Please create the directory and add EU4Health PDF documents:")
        logger.info(f"  mkdir -p {source_dir}")
        logger.info("  # Then download AWPs, Regulation, etc.")
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
            # Ingest the document with EU4Health specific metadata
            result = ingestion_service.ingest_file(
                file_path=str(pdf_file),
                document_type=doc_type,
                programme_year=programme_year,
                metadata={
                    "programme": "eu4health",
                    "programme_name": "EU4Health",
                    "source": "official_eu_portal",
                    "language": "en",
                    "description": doc_description,
                    "ingested_by": "eu4health_ingestion_script",
                    "budget": "4.4 billion EUR (2021-2027)",
                    "implementing_agency": "HaDEA",
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
        description="Ingest EU4Health documents into RAG system"
    )
    parser.add_argument(
        "--source-dir",
        default="newdocs/eu4health",
        help="Directory containing EU4Health PDFs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't commit to database"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("EU4HEALTH DOCUMENT INGESTION")
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

    success = ingest_eu4health_documents(source_dir, args.dry_run)

    if success:
        logger.info("\nIngestion completed!")
        logger.info("\nNext steps:")
        logger.info("1. Run: python scripts/sync_eu4health_calls_from_api.py")
        logger.info("2. Create EU4Health eligibility tools")
        logger.info("3. Test with EU4Health queries")
    else:
        logger.error("\nIngestion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

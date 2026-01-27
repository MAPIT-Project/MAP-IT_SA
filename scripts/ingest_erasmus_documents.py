#!/usr/bin/env python3
"""
Erasmus+ Document Ingestion Script

Ingests Erasmus+ Programme Guide, Work Programme, and related documents
into the RAG system with proper programme tagging.

Usage:
    python scripts/ingest_erasmus_documents.py [--source-dir DIR] [--dry-run]

Options:
    --source-dir    Directory containing Erasmus+ PDFs (default: newdocs/erasmus)
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Erasmus+ document type mappings
ERASMUS_DOCUMENT_TYPES = {
    "programme_guide": {
        "patterns": [
            "programme_guide",
            "programme-guide",
            "program_guide",
            "guide_2025",
            "guide_2026",
            "guide-2025",
            "guide-2026",
        ],
        "type": "programme_guide",
        "description": "Erasmus+ Programme Guide - comprehensive rules and eligibility",
    },
    "work_programme": {
        "patterns": [
            "work_programme",
            "work-programme",
            "annual_work",
            "awp_2025",
            "awp_2026",
            "awp-2025",
            "awp-2026",
            "awp-erasmus",
        ],
        "type": "work_programme",
        "description": "Annual Work Programme with budget allocations",
    },
    "call_document": {
        "patterns": ["call_for_proposals", "call-for-proposals", "call_2025", "call_2026", "cfp_"],
        "type": "call_document",
        "description": "Call for proposals with deadlines",
    },
    "application_form": {
        "patterns": ["application_form", "template", "form_ka1", "form_ka2"],
        "type": "application_template",
        "description": "Application forms and templates",
    },
    "budget_tool": {
        "patterns": ["budget", "lump_sum", "unit_cost", "financial"],
        "type": "budget_guidance",
        "description": "Budget calculation tools and financial guidance",
    },
    "ka1_mobility": {
        "patterns": ["ka1", "ka131", "ka171", "mobility", "learning-mobility"],
        "type": "ka1_mobility",
        "description": "KA1 Learning Mobility guidance",
    },
    "ka2_cooperation": {
        "patterns": ["ka2", "ka210", "ka220", "cooperation", "partnerships"],
        "type": "ka2_cooperation",
        "description": "KA2 Cooperation Partnerships guidance",
    },
    "eche": {
        "patterns": ["eche", "charter", "higher-education"],
        "type": "eche_guidance",
        "description": "Erasmus Charter for Higher Education",
    },
}


def detect_document_type(filename: str) -> tuple[str, str]:
    """
    Detect document type from filename.

    Returns:
        tuple: (document_type, description)
    """
    filename_lower = filename.lower()

    for _doc_type, config in ERASMUS_DOCUMENT_TYPES.items():
        for pattern in config["patterns"]:
            if pattern in filename_lower:
                return config["type"], config["description"]

    # Default fallback
    return "guidance_document", "Erasmus+ guidance document"


def extract_year_from_filename(filename: str) -> str:
    """Extract programme year from filename."""
    import re

    # Match years like 2025, 2026, 2027
    year_match = re.search(r"20(2[5-7])", filename)
    if year_match:
        return f"20{year_match.group(1)}"

    # Match year ranges like 2025-2026
    range_match = re.search(r"(202[5-7])[-_](202[5-7])", filename)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"

    return "2025-2027"  # Default to current period


def ingest_erasmus_documents(source_dir: str, dry_run: bool = False):
    """Ingest all Erasmus+ documents from source directory."""

    source_path = Path(source_dir)

    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.info("Please create the directory and add Erasmus+ PDF documents:")
        logger.info(f"  mkdir -p {source_dir}")
        logger.info("  # Then download Programme Guide, Work Programme, etc.")
        return False

    # Find all PDF files
    pdf_files = list(source_path.glob("*.pdf")) + list(source_path.glob("*.PDF"))

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
    if not stats.get("supabase_connected", False):
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
                },
            )

            if result.get("success"):
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
    parser = argparse.ArgumentParser(description="Ingest Erasmus+ documents into RAG system")
    parser.add_argument(
        "--source-dir", default="newdocs/erasmus", help="Directory containing Erasmus+ PDFs"
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't commit to database")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ERASMUS+ DOCUMENT INGESTION")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes")

    # Convert relative path to absolute if needed
    source_dir = args.source_dir
    if not os.path.isabs(source_dir):
        source_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), source_dir
        )

    logger.info(f"Source directory: {source_dir}")

    success = ingest_erasmus_documents(source_dir, args.dry_run)

    if success:
        logger.info("\nIngestion completed!")
        logger.info("\nNext steps:")
        logger.info("1. Run Phase 2: Sync Erasmus+ calls from API")
        logger.info(
            "2. Test with: curl -X POST http://localhost:8000/api/v3/conversation/test/message"
        )
    else:
        logger.error("\nIngestion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

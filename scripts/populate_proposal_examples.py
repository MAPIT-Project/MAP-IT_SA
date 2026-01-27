#!/usr/bin/env python3
"""
Script to populate proposal_examples from CORDIS projects.

Usage:
    python scripts/populate_proposal_examples.py [--batch-size 100] [--max-projects 1000] [--cluster CL4]
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main(args):
    """Main execution function."""
    from app.services.proposal_writing.example_extractor import ExampleEnricher, ExampleExtractor

    logger.info("=" * 60)
    logger.info("PROPOSAL EXAMPLES POPULATION SCRIPT")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now()}")
    logger.info("Configuration:")
    logger.info(f"  - Batch size: {args.batch_size}")
    logger.info(f"  - Max projects: {args.max_projects or 'All'}")
    logger.info(f"  - Clusters: {args.clusters or 'All'}")
    logger.info(f"  - Skip existing: {args.skip_existing}")
    logger.info("=" * 60)

    # Step 1: Extract examples
    logger.info("\n[STEP 1] Extracting examples from projects...")
    extractor = ExampleExtractor()

    clusters = args.clusters.split(',') if args.clusters else None

    extraction_stats = await extractor.extract_from_all_projects(
        batch_size=args.batch_size,
        max_projects=args.max_projects,
        clusters=clusters,
        skip_existing=args.skip_existing
    )

    logger.info("\nExtraction Results:")
    logger.info(f"  - Projects processed: {extraction_stats['projects_processed']}")
    logger.info(f"  - Examples extracted: {extraction_stats['examples_extracted']}")
    logger.info(f"  - Skipped (low quality): {extraction_stats['skipped_low_quality']}")
    logger.info(f"  - Errors: {extraction_stats['errors']}")
    logger.info("\n  By section type:")
    for section_type, count in extraction_stats['examples_by_type'].items():
        logger.info(f"    - {section_type}: {count}")

    # Step 2: Enrich high-quality examples (optional)
    if args.enrich:
        logger.info("\n[STEP 2] Enriching high-quality examples with LLM analysis...")
        enricher = ExampleEnricher()

        enrichment_stats = await enricher.enrich_examples(batch_size=50)

        logger.info("\nEnrichment Results:")
        logger.info(f"  - Examples enriched: {enrichment_stats['enriched']}")
        logger.info(f"  - Errors: {enrichment_stats['errors']}")

    # Step 3: Print final statistics
    logger.info("\n[FINAL] Database Statistics:")
    final_stats = await extractor.get_extraction_stats()

    logger.info(f"  - Total examples: {final_stats['total_examples']}")
    logger.info(f"  - With embeddings: {final_stats['with_embeddings']}")
    logger.info(f"  - High quality (>=0.7): {final_stats['high_quality_count']}")

    logger.info("\n  By section type:")
    for section_type, count in final_stats.get('by_section_type', {}).items():
        logger.info(f"    - {section_type}: {count}")

    logger.info("\n  By action type:")
    for action_type, count in final_stats.get('by_action_type', {}).items():
        logger.info(f"    - {action_type}: {count}")

    logger.info("\n" + "=" * 60)
    logger.info(f"Completed at: {datetime.now()}")
    logger.info("=" * 60)

    return extraction_stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate proposal examples from CORDIS")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of projects to process at once"
    )
    parser.add_argument(
        "--max-projects",
        type=int,
        default=None,
        help="Maximum number of projects to process (default: all)"
    )
    parser.add_argument(
        "--clusters",
        type=str,
        default=None,
        help="Comma-separated list of clusters to process (default: all)"
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Run LLM enrichment after extraction"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip projects that already have examples (default: True)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Process all projects, even those with existing examples"
    )

    args = parser.parse_args()
    asyncio.run(main(args))

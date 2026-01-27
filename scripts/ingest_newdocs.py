#!/usr/bin/env python3
"""
Script to ingest documents from the newdocs directory into the vector database.
This includes 2025 work programmes, guidance documents, grant agreements, etc.
"""

import logging
import sys
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_document_type(file_path: Path) -> str:
    """Infer document type from file path and name."""
    path_str = str(file_path).lower()
    name = file_path.name.lower()
    
    if 'work_programme' in path_str or 'wp-' in name:
        return 'work_programme'
    elif 'grant' in path_str or 'mga' in name or 'agreement' in path_str:
        return 'grant_agreement'
    elif 'guide' in path_str or 'guidance' in path_str:
        return 'programme_guide'
    elif 'template' in path_str or 'form' in path_str:
        return 'template'
    elif 'decision' in name or 'cost' in name:
        return 'cost_decision'
    else:
        return 'manual'


def get_programme_year(file_path: Path) -> str:
    """Extract programme year from file path or name."""
    path_str = str(file_path)
    name = file_path.name
    
    # Check for year in path (e.g., 2025_work_programmes)
    if '2025' in path_str:
        return '2025'
    elif '2024' in path_str:
        return '2024'
    elif '2023' in path_str:
        return '2023'
    
    # Check for year range in name
    if '2021-2022' in name:
        return '2021-2022'
    elif '2023-2024' in name:
        return '2023-2024'
    elif '2025' in name:
        return '2025'
    
    return 'general'


def ingest_newdocs():
    """Ingest all documents from the newdocs directory."""
    try:
        from app.services.ingestion_service import DocumentIngestionService
        
        logger.info("🚀 Initializing ingestion service...")
        ingestion_service = DocumentIngestionService()
        
        # Verify connection
        stats = ingestion_service.get_service_stats()
        if not stats.get('supabase_connected'):
            logger.error("❌ Supabase not connected!")
            return False
        
        logger.info("✅ Ingestion service ready")
        
        # Find all PDF files in newdocs
        newdocs_dir = Path("newdocs")
        if not newdocs_dir.exists():
            logger.error(f"❌ newdocs directory not found: {newdocs_dir}")
            return False
        
        # Get all PDF files
        pdf_files = list(newdocs_dir.rglob("*.pdf"))
        logger.info(f"📄 Found {len(pdf_files)} PDF files")
        
        # Track results
        successful = 0
        failed = 0
        skipped = 0
        
        for i, pdf_file in enumerate(pdf_files):
            logger.info(f"\n[{i+1}/{len(pdf_files)}] Processing: {pdf_file.name}")
            
            try:
                doc_type = get_document_type(pdf_file)
                prog_year = get_programme_year(pdf_file)
                
                logger.info(f"   Type: {doc_type}, Year: {prog_year}")
                
                result = ingestion_service.ingest_file(
                    file_path=str(pdf_file),
                    document_type=doc_type,
                    programme_year=prog_year,
                    metadata={
                        'source_folder': str(pdf_file.parent.name),
                        'original_path': str(pdf_file)
                    }
                )
                
                if result.get('success'):
                    successful += 1
                    chunk_count = result.get('chunks_created', 0)
                    logger.info(f"   ✅ Success! Created {chunk_count} chunks")
                elif 'already exists' in str(result.get('error', '')):
                    skipped += 1
                    logger.info("   ⏭️ Skipped (already exists)")
                else:
                    failed += 1
                    logger.error(f"   ❌ Failed: {result.get('error')}")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                failed += 1
                logger.error(f"   ❌ Exception: {e}")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("INGESTION COMPLETE")
        logger.info("="*60)
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"⏭️ Skipped (duplicates): {skipped}")
        logger.info(f"❌ Failed: {failed}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest newdocs documents')
    parser.add_argument('--dry-run', action='store_true', help='List files without ingesting')
    args = parser.parse_args()
    
    if args.dry_run:
        newdocs_dir = Path("newdocs")
        pdf_files = list(newdocs_dir.rglob("*.pdf"))
        print(f"\nFound {len(pdf_files)} PDF files:")
        for f in pdf_files:
            print(f"  - {f}")
    else:
        success = ingest_newdocs()
        sys.exit(0 if success else 1)


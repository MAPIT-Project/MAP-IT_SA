#!/usr/bin/env python3
"""
Process shared documents and store them in the database.

This script:
1. Scans data/shared_documents/ for PDFs
2. Parses and chunks each document
3. Stores in shared_documents and shared_document_chunks tables
4. Avoids duplicates using file hash

Usage:
    python scripts/process_shared_documents.py [--force]
"""

import sys
import hashlib
import logging
from pathlib import Path
import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.manual_document_upload import SimpleDocumentParser, SimpleChunker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_db_pool():
    """Create database connection pool"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")
    return psycopg2.pool.SimpleConnectionPool(1, 5, db_url)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def infer_document_metadata(filename: str) -> dict:
    """Infer document metadata from filename"""
    name_lower = filename.lower()
    
    metadata = {
        'document_key': filename.replace('.pdf', ''),
        'document_type': 'other',
        'scope': 'unknown',
        'scope_identifier': None,
        'version': '2023-2025'  # Default
    }
    
    # Detect type
    if 'general' in name_lower and 'annex' in name_lower:
        metadata['document_type'] = 'general_annexes'
        metadata['scope'] = 'global'
        metadata['document_title'] = 'Horizon Europe General Annexes'
    elif 'programme' in name_lower and 'guide' in name_lower:
        metadata['document_type'] = 'programme_guide'
        metadata['scope'] = 'global'
        metadata['document_title'] = 'Horizon Europe Programme Guide'
    elif 'work' in name_lower and 'programme' in name_lower or 'wp_cluster' in name_lower:
        metadata['document_type'] = 'work_programme'
        metadata['scope'] = 'cluster'
        # Try to extract cluster number
        for i in range(1, 13):
            if f'cluster{i}' in name_lower or f'cluster_{i}' in name_lower:
                metadata['scope_identifier'] = f'CLUSTER-{i}'
                metadata['document_title'] = f'Work Programme Cluster {i}'
                break
    elif 'mga' in name_lower or 'grant' in name_lower and 'agreement' in name_lower:
        metadata['document_type'] = 'model_grant_agreement'
        metadata['scope'] = 'global'
        metadata['document_title'] = 'Model Grant Agreement'
    elif 'annotated' in name_lower:
        metadata['document_type'] = 'annotated_grant_agreement'
        metadata['scope'] = 'global'
        metadata['document_title'] = 'Annotated Model Grant Agreement'
    
    return metadata


def document_exists(db_pool, file_hash: str) -> int:
    """Check if document already exists (by hash), return ID if exists"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM shared_documents WHERE file_hash = %s
        """, (file_hash,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        db_pool.putconn(conn)


def store_shared_document(db_pool, metadata: dict, file_path: Path, 
                         file_hash: str, parsed: dict, chunks: list):
    """Store document and chunks in database"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        # Insert document
        cursor.execute("""
            INSERT INTO shared_documents (
                document_key, document_type, document_title,
                document_version, scope, scope_identifier,
                document_content, file_path, file_hash,
                last_updated, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            ON CONFLICT (document_key) DO UPDATE SET
                document_content = EXCLUDED.document_content,
                file_hash = EXCLUDED.file_hash,
                last_updated = NOW()
            RETURNING id
        """, (
            metadata['document_key'],
            metadata['document_type'],
            metadata.get('document_title', file_path.stem),
            metadata.get('version', '2023-2025'),
            metadata['scope'],
            metadata.get('scope_identifier'),
            parsed['full_text'],
            str(file_path),
            file_hash,
            Json({'page_count': parsed['metadata'].get('page_count', 0)})
        ))
        
        document_id = cursor.fetchone()[0]
        
        # Delete old chunks for this document
        cursor.execute("""
            DELETE FROM shared_document_chunks WHERE document_id = %s
        """, (document_id,))
        
        # Insert new chunks
        for chunk in chunks:
            cursor.execute("""
                INSERT INTO shared_document_chunks (
                    document_id, chunk_text, chunk_index,
                    token_count, section_title, page_numbers, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                document_id,
                chunk['text'],
                chunk['chunk_index'],
                chunk['token_count'],
                chunk.get('section_title'),
                chunk.get('page_numbers', []),
                Json(chunk.get('metadata', {}))
            ))
        
        conn.commit()
        return document_id
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Process shared documents')
    parser.add_argument('--force', action='store_true', help='Reprocess even if already exists')
    args = parser.parse_args()
    
    # Setup
    docs_dir = Path("data/shared_documents")
    
    if not docs_dir.exists():
        print(f"❌ Directory not found: {docs_dir}")
        print("\n1. Create directory: mkdir -p data/shared_documents/")
        print("2. Download documents: python scripts/download_shared_documents.py")
        return
    
    pdf_files = list(docs_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {docs_dir}")
        print("\nDownload documents first:")
        print("  python scripts/download_shared_documents.py --all")
        return
    
    print("\n🚀 Processing Shared Documents")
    print("="*70 + "\n")
    
    # Initialize
    db_pool = get_db_pool()
    parser = SimpleDocumentParser()
    chunker = SimpleChunker()
    
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'total_chunks': 0
    }
    
    # Process each PDF
    for pdf_file in pdf_files:
        try:
            print(f"📄 Processing: {pdf_file.name}")
            print("-" * 70)
            
            # Compute hash
            file_hash = compute_file_hash(pdf_file)
            logger.info(f"  🔑 File hash: {file_hash[:16]}...")
            
            # Check if already exists
            if not args.force:
                existing_id = document_exists(db_pool, file_hash)
                if existing_id:
                    logger.info(f"  ⏭️  Skipped (already in database, ID: {existing_id})")
                    stats['skipped'] += 1
                    print()
                    continue
            
            # Infer metadata
            metadata = infer_document_metadata(pdf_file.name)
            logger.info(f"  📋 Type: {metadata['document_type']}")
            logger.info(f"  🌍 Scope: {metadata['scope']}" + 
                       (f" ({metadata['scope_identifier']})" if metadata['scope_identifier'] else ""))
            
            # Parse
            parsed = parser.parse_pdf(pdf_file)
            sections_count = len(parsed.get('sections', []))
            logger.info(f"  ✅ Parsed: {sections_count} sections, {parsed['metadata'].get('page_count', 0)} pages")
            
            # Chunk
            chunks = chunker.chunk_document(parsed, metadata['document_key'], metadata['document_type'])
            stats['total_chunks'] += len(chunks)
            logger.info(f"  ✅ Created: {len(chunks)} chunks")
            
            # Store
            logger.info(f"  💾 Storing in database...")
            doc_id = store_shared_document(
                db_pool=db_pool,
                metadata=metadata,
                file_path=pdf_file,
                file_hash=file_hash,
                parsed=parsed,
                chunks=chunks
            )
            logger.info(f"  ✅ Stored (document ID: {doc_id})")
            
            stats['processed'] += 1
            print()
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            stats['errors'] += 1
            print()
    
    # Summary
    print("="*70)
    print("📊 PROCESSING SUMMARY")
    print("="*70)
    print(f"Documents processed: {stats['processed']}")
    print(f"Documents skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print(f"Total chunks created: {stats['total_chunks']}")
    print("="*70 + "\n")
    
    if stats['processed'] > 0:
        print("✅ Shared documents are ready!")
        print("\nNext step: Map documents to specific calls")
        print("  python scripts/map_call_to_documents.py CALL_ID")


if __name__ == "__main__":
    main()



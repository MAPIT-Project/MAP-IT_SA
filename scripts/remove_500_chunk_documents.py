#!/usr/bin/env python3
"""
Remove 500-chunk documents and reprocess them

This script removes documents that have exactly 500 chunks (likely truncated)
and then reprocesses them from the source files.
"""

import logging
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port='54322',
            database='postgres',
            user='postgres',
            password='postgres'
        )
        return conn, conn.cursor(cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None, None

def find_500_chunk_documents():
    """Find documents with exactly 500 chunks"""
    conn, cursor = connect_db()
    if not conn:
        return []
    
    try:
        cursor.execute("""
            SELECT id, title, document_type, file_path, total_chunks, created_at
            FROM horizon_documents 
            WHERE total_chunks = 500
            ORDER BY title;
        """)
        
        docs = cursor.fetchall()
        logger.info(f"🔍 Found {len(docs)} documents with exactly 500 chunks:")
        
        for doc in docs:
            logger.info(f"  📄 {doc['title']}")
            logger.info(f"     Type: {doc['document_type']} | Path: {doc['file_path'][:60]}...")
            
        return docs
        
    except Exception as e:
        logger.error(f"❌ Error finding 500-chunk documents: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def remove_500_chunk_documents():
    """Remove documents with exactly 500 chunks and their associated chunks"""
    conn, cursor = connect_db()
    if not conn:
        return False
    
    try:
        # Get document IDs to remove
        cursor.execute("SELECT id FROM horizon_documents WHERE total_chunks = 500;")
        doc_ids = [row['id'] for row in cursor.fetchall()]
        
        if not doc_ids:
            logger.info("✅ No 500-chunk documents found to remove")
            return True
        
        logger.info(f"🗑️  Removing {len(doc_ids)} documents with 500 chunks...")
        
        # Remove chunks first
        placeholders = ','.join(['%s'] * len(doc_ids))
        cursor.execute(f"DELETE FROM document_chunks WHERE document_id IN ({placeholders})", doc_ids)
        chunks_removed = cursor.rowcount
        
        # Remove documents
        cursor.execute(f"DELETE FROM horizon_documents WHERE id IN ({placeholders})", doc_ids)
        docs_removed = cursor.rowcount
        
        conn.commit()
        
        logger.info(f"✅ Removed {docs_removed} documents and {chunks_removed} chunks")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error removing documents: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    """Main function"""
    logger.info("🔍 Finding and removing 500-chunk documents...")
    logger.info("=" * 60)
    
    # Find 500-chunk documents
    docs_500 = find_500_chunk_documents()
    
    if not docs_500:
        logger.info("✅ No 500-chunk documents found!")
        return True
    
    # Ask for confirmation
    print("\n⚠️  CONFIRMATION REQUIRED")
    print(f"This will remove {len(docs_500)} documents with exactly 500 chunks")
    print("and all their associated chunks from the database.")
    print("\nDocuments to be removed:")
    for doc in docs_500:
        print(f"  🗑️  {doc['title']}")
    
    confirm = input("\nProceed with removal? (yes/no): ").lower().strip()
    
    if confirm in ['yes', 'y']:
        success = remove_500_chunk_documents()
        if success:
            logger.info("✅ 500-chunk documents removed successfully!")
            logger.info("💡 Now you can rerun the ingestion script to reprocess these documents properly.")
        else:
            logger.error("❌ Failed to remove documents")
            return False
    else:
        logger.info("❌ Operation cancelled by user")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

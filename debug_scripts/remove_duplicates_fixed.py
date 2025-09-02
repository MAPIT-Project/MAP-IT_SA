#!/usr/bin/env python3
"""
Remove duplicate documents from the database.
Keep the oldest version of each document (by file_path).
"""

import psycopg2
import json
from datetime import datetime
from pathlib import Path
import logging
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('remove_duplicates.log')
    ]
)
logger = logging.getLogger(__name__)

def get_database_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=54321,
            database="postgres",
            user="postgres",
            password="postgres",
            sslmode="disable"
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

def find_duplicates(conn):
    """Find duplicate documents by file_path."""
    logger.info("🔍 Finding duplicate documents...")
    
    cursor = conn.cursor()
    
    # Find duplicates by file_path
    query = """
    SELECT file_path, 
           array_agg(id ORDER BY created_at ASC) as document_ids,
           array_agg(title ORDER BY created_at ASC) as titles,
           array_agg(created_at ORDER BY created_at ASC) as created_dates,
           COUNT(*) as duplicate_count
    FROM horizon_documents 
    WHERE file_path IS NOT NULL
    GROUP BY file_path 
    HAVING COUNT(*) > 1
    ORDER BY file_path;
    """
    
    cursor.execute(query)
    duplicates = cursor.fetchall()
    
    logger.info(f"📋 Found {len(duplicates)} file paths with duplicates")
    
    duplicates_info = []
    total_duplicates_to_remove = 0
    
    for file_path, document_ids, titles, created_dates, duplicate_count in duplicates:
        # Keep the oldest (first) document, mark others for removal
        keep_id = document_ids[0]
        remove_ids = document_ids[1:]
        
        duplicates_info.append({
            'file_path': file_path,
            'keep_id': keep_id,
            'keep_title': titles[0],
            'keep_created': created_dates[0].isoformat(),
            'remove_ids': remove_ids,
            'remove_count': len(remove_ids)
        })
        
        total_duplicates_to_remove += len(remove_ids)
        
        logger.info(f"📄 {file_path}:")
        logger.info(f"   Keep: {titles[0]} (ID: {keep_id}, Created: {created_dates[0]})")
        for i, remove_id in enumerate(remove_ids):
            logger.info(f"   Remove: {titles[i+1]} (ID: {remove_id}, Created: {created_dates[i+1]})")
    
    cursor.close()
    
    logger.info(f"📊 Total documents to remove: {total_duplicates_to_remove}")
    return duplicates_info

def get_chunk_counts(conn, document_ids):
    """Get chunk counts for documents."""
    if not document_ids:
        return {}
    
    cursor = conn.cursor()
    
    # Get chunk counts
    placeholders = ','.join(['%s'] * len(document_ids))
    query = f"""
    SELECT document_id, COUNT(*) as chunk_count
    FROM document_chunks 
    WHERE document_id IN ({placeholders})
    GROUP BY document_id
    """
    
    cursor.execute(query, document_ids)
    results = cursor.fetchall()
    
    chunk_counts = {doc_id: count for doc_id, count in results}
    cursor.close()
    
    return chunk_counts

def remove_duplicates(conn, duplicates_info):
    """Remove duplicate documents and their associated chunks."""
    if not duplicates_info:
        logger.info("✅ No duplicates to remove")
        return
    
    # Collect all IDs to remove
    all_remove_ids = []
    for dup in duplicates_info:
        all_remove_ids.extend(dup['remove_ids'])
    
    if not all_remove_ids:
        logger.info("✅ No duplicate documents to remove")
        return
    
    # Get chunk counts before removal
    chunk_counts = get_chunk_counts(conn, all_remove_ids)
    total_chunks_to_remove = sum(chunk_counts.values())
    
    logger.info(f"🗑️ About to remove:")
    logger.info(f"   Documents: {len(all_remove_ids)}")
    logger.info(f"   Chunks: {total_chunks_to_remove}")
    
    try:
        cursor = conn.cursor()
        
        # Start transaction
        conn.autocommit = False
        
        # Remove chunks first (due to foreign key constraints)
        if all_remove_ids:
            placeholders = ','.join(['%s'] * len(all_remove_ids))
            delete_chunks_query = f"DELETE FROM document_chunks WHERE document_id IN ({placeholders})"
            cursor.execute(delete_chunks_query, all_remove_ids)
            deleted_chunks = cursor.rowcount
            logger.info(f"🗑️ Deleted {deleted_chunks} chunks")
        
        # Remove documents
        if all_remove_ids:
            placeholders = ','.join(['%s'] * len(all_remove_ids))
            delete_docs_query = f"DELETE FROM horizon_documents WHERE id IN ({placeholders})"
            cursor.execute(delete_docs_query, all_remove_ids)
            deleted_docs = cursor.rowcount
            logger.info(f"🗑️ Deleted {deleted_docs} documents")
        
        # Commit transaction
        conn.commit()
        cursor.close()
        
        logger.info("✅ Successfully removed duplicate documents and chunks")
        
        # Save removal report
        report = {
            'timestamp': datetime.now().isoformat(),
            'duplicates_removed': duplicates_info,
            'total_documents_removed': len(all_remove_ids),
            'total_chunks_removed': deleted_chunks,
            'removed_document_ids': all_remove_ids
        }
        
        report_file = Path('duplicate_removal_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Removal report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"❌ Error removing duplicates: {e}")
        conn.rollback()
        raise
    finally:
        conn.autocommit = True

def verify_removal(conn):
    """Verify that duplicates have been removed."""
    logger.info("🔍 Verifying duplicate removal...")
    
    cursor = conn.cursor()
    
    # Check for remaining duplicates
    query = """
    SELECT file_path, COUNT(*) as count
    FROM horizon_documents 
    WHERE file_path IS NOT NULL
    GROUP BY file_path 
    HAVING COUNT(*) > 1
    """
    
    cursor.execute(query)
    remaining_duplicates = cursor.fetchall()
    
    if remaining_duplicates:
        logger.warning(f"⚠️ Still found {len(remaining_duplicates)} duplicate file paths:")
        for file_path, count in remaining_duplicates:
            logger.warning(f"   {file_path}: {count} documents")
        return False
    else:
        logger.info("✅ No duplicate file paths remaining")
    
    # Get final count
    cursor.execute("SELECT COUNT(*) FROM horizon_documents")
    total_docs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM document_chunks")
    total_chunks = cursor.fetchone()[0]
    
    logger.info(f"📊 Final database state:")
    logger.info(f"   Total documents: {total_docs}")
    logger.info(f"   Total chunks: {total_chunks}")
    
    cursor.close()
    return True

def main():
    """Main function."""
    logger.info("🚀 Starting duplicate document removal...")
    
    # Connect to database
    conn = get_database_connection()
    if not conn:
        logger.error("❌ Failed to connect to database")
        return False
    
    try:
        # Find duplicates
        duplicates_info = find_duplicates(conn)
        
        if not duplicates_info:
            logger.info("✅ No duplicates found!")
            return True
        
        # Ask for confirmation
        print(f"\n⚠️ About to remove {sum(dup['remove_count'] for dup in duplicates_info)} duplicate documents.")
        print("This action cannot be undone!")
        
        response = input("Continue? (yes/no): ").lower().strip()
        if response != 'yes':
            logger.info("❌ Removal cancelled by user")
            return False
        
        # Remove duplicates
        remove_duplicates(conn, duplicates_info)
        
        # Verify removal
        success = verify_removal(conn)
        
        if success:
            logger.info("🎉 Duplicate removal completed successfully!")
        else:
            logger.warning("⚠️ Duplicate removal completed but some issues remain")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error during duplicate removal: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

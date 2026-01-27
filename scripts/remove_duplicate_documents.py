#!/usr/bin/env python3
"""
Remove Duplicate Documents Script

This script identifies and removes duplicate documents from the horizon_documents table
based on file_path and title, keeping only the most recent version of each document.
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('remove_duplicates.log')
    ]
)
logger = logging.getLogger(__name__)

class DuplicateRemover:
    def __init__(self):
        self.conn = None
        self.cursor = None
        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host='localhost',
                port='54322',
                database='postgres',
                user='postgres',
                password='postgres'
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("✅ Connected to database")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def find_duplicates(self):
        """Find duplicate documents based on file_path and title"""
        try:
            query = """
            WITH document_groups AS (
                SELECT 
                    file_path,
                    title,
                    COUNT(*) as duplicate_count,
                    ARRAY_AGG(id::text ORDER BY created_at DESC) as document_ids,
                    ARRAY_AGG(created_at ORDER BY created_at DESC) as created_dates,
                    ARRAY_AGG(total_chunks ORDER BY created_at DESC) as chunk_counts
                FROM horizon_documents 
                GROUP BY file_path, title
                HAVING COUNT(*) > 1
            )
            SELECT * FROM document_groups
            ORDER BY duplicate_count DESC, file_path;
            """
            
            self.cursor.execute(query)
            duplicates = self.cursor.fetchall()
            
            logger.info(f"🔍 Found {len(duplicates)} groups of duplicate documents")
            
            total_duplicates = 0
            for dup in duplicates:
                total_duplicates += dup['duplicate_count'] - 1  # Keep one copy
                logger.info(f"📁 {dup['title'][:50]}... - {dup['duplicate_count']} copies")
                logger.info(f"   Path: {dup['file_path'][:60]}...")
                
            logger.info(f"📊 Total duplicate documents to remove: {total_duplicates}")
            return duplicates
            
        except Exception as e:
            logger.error(f"❌ Error finding duplicates: {e}")
            return []
    
    def remove_duplicate_chunks(self, document_ids_to_remove):
        """Remove chunks for documents that will be deleted"""
        try:
            if not document_ids_to_remove:
                return 0
                
            # Get chunk count before deletion
            placeholders = ','.join(['%s'] * len(document_ids_to_remove))
            self.cursor.execute(
                f"SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({placeholders})",
                document_ids_to_remove
            )
            chunk_count = self.cursor.fetchone()[0]
            
            # Delete chunks
            self.cursor.execute(
                f"DELETE FROM document_chunks WHERE document_id IN ({placeholders})",
                document_ids_to_remove
            )
            
            logger.info(f"🗑️  Removed {chunk_count} chunks from duplicate documents")
            return chunk_count
            
        except Exception as e:
            logger.error(f"❌ Error removing chunks: {e}")
            return 0
    
    def remove_duplicates(self, duplicates, dry_run=True):
        """Remove duplicate documents, keeping the most recent one"""
        total_removed_docs = 0
        total_removed_chunks = 0
        
        try:
            for dup_group in duplicates:
                document_ids = dup_group['document_ids']
                title = dup_group['title']
                
                # Keep the first one (most recent due to ORDER BY created_at DESC)
                keep_id = document_ids[0]
                remove_ids = document_ids[1:]
                
                logger.info(f"📄 Processing: {title[:50]}...")
                logger.info(f"   ✅ Keeping document ID: {keep_id} (most recent)")
                logger.info(f"   🗑️  Removing {len(remove_ids)} duplicates: {remove_ids}")
                
                if not dry_run:
                    # Remove chunks for documents to be deleted
                    chunks_removed = self.remove_duplicate_chunks(remove_ids)
                    total_removed_chunks += chunks_removed
                    
                    # Remove duplicate documents
                    placeholders = ','.join(['%s'] * len(remove_ids))
                    self.cursor.execute(
                        f"DELETE FROM horizon_documents WHERE id IN ({placeholders})",
                        remove_ids
                    )
                    
                    total_removed_docs += len(remove_ids)
                    logger.info(f"   ✅ Removed {len(remove_ids)} duplicate documents and {chunks_removed} chunks")
                else:
                    logger.info(f"   🔄 DRY RUN: Would remove {len(remove_ids)} documents")
            
            if not dry_run:
                self.conn.commit()
                logger.info("✅ Transaction committed successfully")
            
            return total_removed_docs, total_removed_chunks
            
        except Exception as e:
            if not dry_run:
                self.conn.rollback()
            logger.error(f"❌ Error removing duplicates: {e}")
            return 0, 0
    
    def get_final_stats(self):
        """Get final database statistics"""
        try:
            # Count documents
            self.cursor.execute("SELECT COUNT(*) FROM horizon_documents")
            doc_count = self.cursor.fetchone()[0]
            
            # Count chunks
            self.cursor.execute("SELECT COUNT(*) FROM document_chunks")
            chunk_count = self.cursor.fetchone()[0]
            
            # Count by document type
            self.cursor.execute("""
                SELECT document_type, COUNT(*) 
                FROM horizon_documents 
                GROUP BY document_type 
                ORDER BY document_type
            """)
            by_type = self.cursor.fetchall()
            
            logger.info("📊 Final Database Statistics:")
            logger.info(f"   📄 Total Documents: {doc_count}")
            logger.info(f"   🧩 Total Chunks: {chunk_count}")
            logger.info("   📋 Documents by Type:")
            for type_stat in by_type:
                logger.info(f"      {type_stat[1]:3d} {type_stat[0]}")
                
            return doc_count, chunk_count
            
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return 0, 0
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("🔐 Database connection closed")

def main():
    """Main function"""
    logger.info("🧹 Starting Duplicate Document Removal")
    logger.info("=" * 60)
    
    remover = DuplicateRemover()
    
    # Connect to database
    if not remover.connect_db():
        return False
    
    try:
        # Find duplicates
        duplicates = remover.find_duplicates()
        
        if not duplicates:
            logger.info("✅ No duplicate documents found!")
            return True
        
        # Show what would be removed (dry run)
        logger.info("\n🔍 DRY RUN - Analyzing duplicates...")
        logger.info("-" * 40)
        removed_docs, removed_chunks = remover.remove_duplicates(duplicates, dry_run=True)
        
        # Ask for confirmation
        print("\n⚠️  CONFIRMATION REQUIRED")
        print(f"This will remove {sum(len(dup['document_ids']) - 1 for dup in duplicates)} duplicate documents")
        print("and their associated chunks from the database.")
        print("\nDocuments to be kept (most recent version of each):")
        for dup in duplicates:
            print(f"  ✅ {dup['title'][:60]}...")
        
        confirm = input("\nProceed with removal? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            logger.info("\n🗑️  Removing duplicates...")
            logger.info("-" * 40)
            removed_docs, removed_chunks = remover.remove_duplicates(duplicates, dry_run=False)
            
            logger.info("\n✅ Cleanup completed successfully!")
            logger.info(f"   🗑️  Removed {removed_docs} duplicate documents")
            logger.info(f"   🗑️  Removed {removed_chunks} associated chunks")
            
            # Show final stats
            logger.info("\n📊 Updated database statistics:")
            logger.info("-" * 40)
            remover.get_final_stats()
            
        else:
            logger.info("❌ Operation cancelled by user")
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False
    finally:
        remover.close()
    
    logger.info("\n🎉 Duplicate removal process completed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

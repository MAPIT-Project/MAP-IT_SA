#!/usr/bin/env python3
"""
Remove duplicate documents using the database client.
Keep the oldest version of each document (by file_path).
"""

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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to remove duplicates using SQL queries."""
    logger.info("🚀 Starting duplicate document removal...")
    
    # First, let's see what duplicates we have
    logger.info("🔍 Finding duplicate documents...")
    print("\nExecute this query to see duplicates:")
    print("""
SELECT file_path, 
       string_agg(id::text, ', ' ORDER BY created_at ASC) as document_ids,
       string_agg(title, ', ' ORDER BY created_at ASC) as titles,
       COUNT(*) as duplicate_count
FROM horizon_documents 
WHERE file_path IS NOT NULL
GROUP BY file_path 
HAVING COUNT(*) > 1
ORDER BY file_path;
    """)
    
    print("\nThen execute these deletion queries:")
    
    # Query to find and delete duplicate chunks
    delete_chunks_query = """
WITH duplicates_to_remove AS (
    SELECT id
    FROM (
        SELECT id, 
               ROW_NUMBER() OVER (PARTITION BY file_path ORDER BY created_at ASC) as rn
        FROM horizon_documents
        WHERE file_path IS NOT NULL
    ) ranked
    WHERE rn > 1
)
DELETE FROM document_chunks 
WHERE document_id IN (SELECT id FROM duplicates_to_remove);
    """
    
    # Query to delete duplicate documents
    delete_docs_query = """
WITH duplicates_to_remove AS (
    SELECT id
    FROM (
        SELECT id, 
               ROW_NUMBER() OVER (PARTITION BY file_path ORDER BY created_at ASC) as rn
        FROM horizon_documents
        WHERE file_path IS NOT NULL
    ) ranked
    WHERE rn > 1
)
DELETE FROM horizon_documents 
WHERE id IN (SELECT id FROM duplicates_to_remove);
    """
    
    print("\n1. Delete chunks from duplicate documents:")
    print(delete_chunks_query)
    
    print("\n2. Delete duplicate documents:")
    print(delete_docs_query)
    
    print("\n3. Verify removal:")
    print("""
SELECT file_path, COUNT(*) as count
FROM horizon_documents 
WHERE file_path IS NOT NULL
GROUP BY file_path 
HAVING COUNT(*) > 1;
    """)
    
    print("\n4. Check final state:")
    print("""
SELECT 
    (SELECT COUNT(*) FROM horizon_documents) as total_documents,
    (SELECT COUNT(*) FROM document_chunks) as total_chunks;
    """)

if __name__ == "__main__":
    main()

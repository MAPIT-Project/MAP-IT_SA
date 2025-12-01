#!/usr/bin/env python3
"""Quick test of document retrieval"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def test_retrieval(call_id: str, search_term: str):
    """Test full-text search on chunks"""
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    # Full-text search
    cursor.execute("""
        SELECT 
            cd.document_type,
            cdc.section_title,
            LEFT(cdc.chunk_text, 300) as chunk_preview,
            ts_rank(
                to_tsvector('english', cdc.chunk_text),
                plainto_tsquery('english', %s)
            ) as rank
        FROM call_document_chunks cdc
        JOIN call_documents cd ON cdc.call_document_id = cd.id
        WHERE cdc.call_identifier = %s
          AND to_tsvector('english', cdc.chunk_text) @@ plainto_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT 3
    """, (search_term, call_id, search_term))
    
    print(f"\n🔍 Search results for: '{search_term}'")
    print("="*70)
    
    results = cursor.fetchall()
    
    if not results:
        print("❌ No results found")
    else:
        for i, (doc_type, section, preview, rank) in enumerate(results, 1):
            print(f"\n{i}. Document Type: {doc_type}")
            print(f"   Section: {section or 'N/A'}")
            print(f"   Relevance: {rank:.4f}")
            print(f"   Preview: {preview}...")
            print("-"*70)
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python test_document_retrieval.py <CALL_ID> <SEARCH_TERM>")
        print("Example: python test_document_retrieval.py HORIZON-HLTH-2024-TOOL-12-01 eligibility")
        sys.exit(1)
    
    call_id = sys.argv[1]
    search_term = sys.argv[2]
    
    test_retrieval(call_id, search_term)

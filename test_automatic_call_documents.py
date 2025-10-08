#!/usr/bin/env python3
"""
Test the automatic call document service.

This demonstrates the on-demand document fetching:
1. User asks about a call
2. System checks if documents are cached
3. If not: API call → download → process → map
4. Returns chunks ready for RAG

Usage:
    python test_automatic_call_documents.py HORIZON-CL3-2025-02-CS-ECCC-01
"""

import sys
import os
from pathlib import Path
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.call_document_service import CallDocumentService

load_dotenv()


def test_call_documents(call_identifier: str):
    """Test automatic document fetching for a call"""
    
    print("\n" + "="*70)
    print(f"🔍 Testing Automatic Document Service")
    print(f"Call: {call_identifier}")
    print("="*70 + "\n")
    
    # Initialize
    db_url = os.getenv("DATABASE_URL")
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
    
    service = CallDocumentService(db_pool)
    
    # Test 1: Get documents (will fetch if needed)
    print("📋 Step 1: Get/Fetch Documents")
    print("-" * 70)
    
    start_time = time.time()
    result = service.get_call_documents(call_identifier)
    elapsed = time.time() - start_time
    
    if not result:
        print(f"❌ Failed to get documents for {call_identifier}")
        return
    
    print(f"\n✅ Success! ({elapsed:.2f}s)")
    print(f"   Cached: {'Yes (instant)' if result['cached'] else 'No (just fetched)'}")
    print(f"   Documents: {result['documents_count']}")
    print(f"   Chunks: {result['chunks_count']}")
    
    print("\n📚 Documents:")
    for doc in result['documents']:
        print(f"   • {doc['title']}")
        print(f"     Type: {doc['type']}")
    
    # Test 2: Search chunks
    print("\n" + "-" * 70)
    print("📋 Step 2: Search Chunks")
    print("-" * 70)
    
    queries = [
        "eligibility criteria",
        "evaluation process",
        "budget rules"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        chunks = service.search_call_chunks(call_identifier, query, limit=3)
        
        if chunks:
            print(f"   Found {len(chunks)} relevant chunks:")
            for i, chunk in enumerate(chunks, 1):
                print(f"\n   {i}. Section: {chunk['section_title'] or 'N/A'}")
                print(f"      Document: {chunk['document_type']}")
                print(f"      Relevance: {chunk['relevance_score']:.2f}")
                print(f"      Preview: {chunk['chunk_text'][:150]}...")
        else:
            print("   ❌ No chunks found")
    
    # Test 3: Test caching (should be instant)
    print("\n" + "-" * 70)
    print("📋 Step 3: Test Caching (2nd call)")
    print("-" * 70)
    
    start_time = time.time()
    result2 = service.get_call_documents(call_identifier)
    elapsed2 = time.time() - start_time
    
    print(f"\n✅ Cached result: {elapsed2:.4f}s (should be < 0.1s)")
    print(f"   Cached: {result2['cached']}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"✅ First fetch: {elapsed:.2f}s")
    print(f"✅ Cached fetch: {elapsed2:.4f}s")
    print(f"✅ Documents available: {result['documents_count']}")
    print(f"✅ Chunks available: {result['chunks_count']}")
    print(f"✅ Ready for RAG queries!")
    print("="*70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_automatic_call_documents.py <CALL_ID>")
        print("\nExample:")
        print("  python test_automatic_call_documents.py HORIZON-CL3-2025-02-CS-ECCC-01")
        sys.exit(1)
    
    call_id = sys.argv[1]
    test_call_documents(call_id)



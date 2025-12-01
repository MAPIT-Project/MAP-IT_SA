#!/usr/bin/env python3
"""
Simple test of call document retrieval without full conversation system.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool

sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from app.services.call_document_service import CallDocumentService

async def test_simple_retrieval():
    """Test simple call document retrieval"""
    
    print("\n" + "="*70)
    print("🧪 Testing Simple Call Document Retrieval")
    print("="*70 + "\n")
    
    # Setup
    db_url = os.getenv("DATABASE_URL")
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)
    service = CallDocumentService(db_pool)
    
    call_id = "HORIZON-CL3-2025-02-CS-ECCC-01"
    query = "eligibility criteria"
    
    print(f"📋 Call ID: {call_id}")
    print(f"💬 Query: {query}\n")
    print("-" * 70)
    
    # Test retrieval
    print("🔍 Searching call documents...")
    chunks = service.search_call_chunks(
        call_identifier=call_id,
        query=query,
        limit=5
    )
    
    print(f"✅ Found {len(chunks)} chunks\n")
    
    if chunks:
        print("📄 RESULTS:")
        print("=" * 70)
        for i, chunk in enumerate(chunks, 1):
            print(f"\n{i}. Document: {chunk['document_title']}")
            print(f"   Section: {chunk.get('section_title', 'N/A')}")
            print(f"   Type: {chunk['document_type']}")
            print(f"   Relevance: {chunk['relevance_score']:.2f}")
            print(f"   Preview: {chunk['chunk_text'][:200]}...")
            print("-" * 70)
    else:
        print("❌ No chunks found")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(test_simple_retrieval())



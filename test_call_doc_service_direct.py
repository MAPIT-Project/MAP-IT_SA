#!/usr/bin/env python3
"""Direct test of CallDocumentService"""

import os
import psycopg2.pool
from app.services.call_document_service import CallDocumentService

# Database URL
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

# Create connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)

# Create service
service = CallDocumentService(db_pool)

# Test search
call_id = "HORIZON-CL3-2025-02-CS-ECCC-01"
query = "eligibility criteria"

print(f"🔍 Testing search for: {call_id}")
print(f"📝 Query: {query}")
print("=" * 70)

try:
    chunks = service.search_call_chunks(call_id, query, limit=5)
    
    print(f"✅ Found {len(chunks)} chunks")
    print()
    
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}:")
        print(f"  ID: {chunk.get('chunk_id')}")
        print(f"  Document: {chunk.get('document_title')}")
        print(f"  Section: {chunk.get('section_title')}")
        print(f"  Text: {chunk.get('chunk_text', '')[:150]}...")
        print(f"  Score: {chunk.get('relevance_score')}")
        print()
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db_pool.closeall()



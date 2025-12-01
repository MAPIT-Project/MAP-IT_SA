#!/usr/bin/env python3
"""
Add Cluster 3 Work Programme to the database for HORIZON-CL3-2025-02-CS-ECCC-01
"""

import os
import sys
import psycopg2.pool
from app.services.call_document_service import CallDocumentService

# Database URL
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")

print("🔧 Adding Cluster 3 Work Programme for HORIZON-CL3-2025-02-CS-ECCC-01")
print("=" * 70)

# Create connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, db_url)

# Create service
service = CallDocumentService(db_pool)

# Call ID
call_id = "HORIZON-CL3-2025-02-CS-ECCC-01"

print(f"\n📚 Fetching documents for {call_id}...")
print("This will:")
print("  1. Query EU Portal API for call metadata")
print("  2. Extract document URLs")
print("  3. Download PDFs")
print("  4. Parse and chunk documents")
print("  5. Store in database")
print("  6. Create mappings")
print("")

try:
    result = service.get_call_documents(call_id)
    
    print(f"\n✅ SUCCESS!")
    print(f"   Call: {result['call_identifier']}")
    print(f"   Documents: {result['documents_count']}")
    print(f"   Chunks: {result['chunks_count']}")
    print(f"   Cached: {result['cached']}")
    
    if result.get('documents'):
        print(f"\n📄 Documents added:")
        for doc in result['documents'][:5]:
            print(f"   - {doc['title']} ({doc['type']})")
        if len(result['documents']) > 5:
            print(f"   ... and {len(result['documents']) - 5} more")
    
    print(f"\n🎉 You can now ask: 'Can I apply from Switzerland for {call_id}?'")
    print(f"   The AI will have access to the specific call eligibility criteria!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db_pool.closeall()



#!/usr/bin/env python3
"""
Map a call to its relevant documents.

This script determines which shared documents are relevant to a specific call
and creates mappings in the call_document_mappings table.

Usage:
    python scripts/map_call_to_documents.py CALL_ID [--auto]
    
Examples:
    # Auto-detect documents based on call ID
    python scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01 --auto
    
    # Interactive mode
    python scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01
"""

import logging
import os
import re
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

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


def extract_cluster_from_call_id(call_id: str) -> str:
    """Extract cluster from call ID"""
    # Pattern: HORIZON-CL3-... or HORIZON-HLTH-... etc.
    
    # Direct cluster number (CL1, CL2, etc.)
    match = re.search(r'CL(\d+)', call_id, re.IGNORECASE)
    if match:
        return f"CLUSTER-{match.group(1)}"
    
    # Named clusters
    cluster_mappings = {
        'HLTH': 'CLUSTER-1',  # Health
        'INFRA': 'CLUSTER-3',  # Research Infrastructures  
        'CULT': 'CLUSTER-5',  # Culture
        'CIVIL': 'CLUSTER-6',  # Civil Security
        'DIGITAL': 'CLUSTER-7',  # Digital
        'CLIMATE': 'CLUSTER-8',  # Climate
        'FOOD': 'CLUSTER-9',  # Food
        'MSCA': 'MSCA',  # Marie Sklodowska-Curie Actions
        'ERC': 'ERC',  # European Research Council
    }
    
    for key, cluster in cluster_mappings.items():
        if key in call_id.upper():
            return cluster
    
    return None


def get_available_documents(db_pool) -> list:
    """Get all available shared documents"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, document_key, document_type, document_title, 
                   scope, scope_identifier
            FROM shared_documents
            ORDER BY scope DESC, document_type
        """)
        
        docs = []
        for row in cursor.fetchall():
            docs.append({
                'id': row[0],
                'key': row[1],
                'type': row[2],
                'title': row[3],
                'scope': row[4],
                'scope_identifier': row[5]
            })
        return docs
        
    finally:
        db_pool.putconn(conn)


def auto_detect_relevant_documents(call_id: str, all_docs: list) -> list:
    """Automatically detect which documents are relevant to this call"""
    relevant = []
    cluster = extract_cluster_from_call_id(call_id)
    
    logger.info(f"🔍 Detected cluster: {cluster or 'Unknown'}")
    
    for doc in all_docs:
        relevance = 0.0
        is_primary = False
        
        # Global documents (apply to ALL calls)
        if doc['scope'] == 'global':
            relevance = 1.0
            logger.info(f"  ✅ Global document: {doc['key']}")
        
        # Cluster-specific documents
        elif doc['scope'] == 'cluster':
            if cluster and doc['scope_identifier'] == cluster:
                relevance = 1.0
                is_primary = True
                logger.info(f"  ✅ Cluster document: {doc['key']} (primary)")
        
        # Call-specific documents (exact match)
        elif doc['scope'] == 'call':
            if doc['scope_identifier'] == call_id:
                relevance = 1.0
                is_primary = True
                logger.info(f"  ✅ Call-specific document: {doc['key']} (primary)")
        
        if relevance > 0:
            relevant.append({
                'document_id': doc['id'],
                'relevance': relevance,
                'is_primary': is_primary,
                'key': doc['key'],
                'title': doc['title']
            })
    
    return relevant


def create_mappings(db_pool, call_id: str, mappings: list):
    """Create call-to-document mappings in database"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        created = 0
        for mapping in mappings:
            cursor.execute("""
                INSERT INTO call_document_mappings (
                    call_identifier, document_id, relevance_score,
                    is_primary, mapping_source
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (call_identifier, document_id) DO UPDATE SET
                    relevance_score = EXCLUDED.relevance_score,
                    is_primary = EXCLUDED.is_primary
            """, (
                call_id,
                mapping['document_id'],
                mapping['relevance'],
                mapping['is_primary'],
                'auto'
            ))
            created += 1
        
        conn.commit()
        logger.info(f"✅ Created {created} mappings")
        
    except Exception:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)


def verify_mappings(db_pool, call_id: str):
    """Verify and display created mappings"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                sd.document_key,
                sd.document_title,
                sd.document_type,
                cdm.relevance_score,
                cdm.is_primary,
                COUNT(sdc.id) as chunk_count
            FROM call_document_mappings cdm
            JOIN shared_documents sd ON cdm.document_id = sd.id
            LEFT JOIN shared_document_chunks sdc ON sd.id = sdc.document_id
            WHERE cdm.call_identifier = %s
            GROUP BY sd.document_key, sd.document_title, sd.document_type,
                     cdm.relevance_score, cdm.is_primary
            ORDER BY cdm.is_primary DESC, cdm.relevance_score DESC
        """, (call_id,))
        
        print("\n" + "="*70)
        print("📚 MAPPED DOCUMENTS")
        print("="*70)
        
        results = cursor.fetchall()
        
        if not results:
            print("❌ No documents mapped")
        else:
            for row in results:
                key, title, doc_type, relevance, is_primary, chunks = row
                primary_marker = " [PRIMARY]" if is_primary else ""
                print(f"\n  📄 {title}{primary_marker}")
                print(f"     Key: {key}")
                print(f"     Type: {doc_type}")
                print(f"     Relevance: {relevance:.2f}")
                print(f"     Chunks: {chunks}")
        
        # Total chunks available
        cursor.execute("""
            SELECT COUNT(DISTINCT sdc.id)
            FROM call_document_mappings cdm
            JOIN shared_documents sd ON cdm.document_id = sd.id
            JOIN shared_document_chunks sdc ON sd.id = sdc.document_id
            WHERE cdm.call_identifier = %s
        """, (call_id,))
        
        total_chunks = cursor.fetchone()[0]
        
        print("\n" + "="*70)
        print(f"📊 Total chunks available for this call: {total_chunks}")
        print("="*70 + "\n")
        
    finally:
        db_pool.putconn(conn)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Map call to relevant documents')
    parser.add_argument('call_id', help='Call identifier (e.g., HORIZON-CL3-2025-02-CS-ECCC-01)')
    parser.add_argument('--auto', action='store_true', help='Auto-detect documents (no prompts)')
    
    args = parser.parse_args()
    call_id = args.call_id
    
    print(f"\n🔗 Mapping Documents for Call: {call_id}")
    print("="*70 + "\n")
    
    # Initialize
    db_pool = get_db_pool()
    
    # Get available documents
    all_docs = get_available_documents(db_pool)
    
    if not all_docs:
        print("❌ No shared documents found in database")
        print("\nFirst, process shared documents:")
        print("  python scripts/download_shared_documents.py --all")
        print("  python scripts/process_shared_documents.py")
        return
    
    print(f"📚 Found {len(all_docs)} shared documents\n")
    
    # Auto-detect relevant documents
    relevant_docs = auto_detect_relevant_documents(call_id, all_docs)
    
    if not relevant_docs:
        print("\n⚠️  No documents auto-detected for this call")
        print(f"   Call ID: {call_id}")
        print(f"   Detected cluster: {extract_cluster_from_call_id(call_id) or 'Unknown'}")
        print("\nYou may need to:")
        print("  1. Download the cluster-specific work programme")
        print("  2. Process it with: python scripts/process_shared_documents.py")
        return
    
    print(f"\n✅ Auto-detected {len(relevant_docs)} relevant documents")
    
    # Create mappings
    if not args.auto:
        response = input("\nCreate these mappings? [Y/n]: ")
        if response.lower() in ['n', 'no']:
            print("Cancelled")
            return
    
    print("\n💾 Creating mappings...")
    create_mappings(db_pool, call_id, relevant_docs)
    
    # Verify
    verify_mappings(db_pool, call_id)
    
    print("✅ Call-to-document mapping complete!")
    print("\nYou can now query documents for this call:")
    print(f"  SELECT * FROM get_chunks_for_call('{call_id}', 'eligibility', 10);")


if __name__ == "__main__":
    main()



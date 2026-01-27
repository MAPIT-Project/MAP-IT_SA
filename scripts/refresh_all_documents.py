"""
Complete Document Refresh Script
Removes all old documents and imports fresh 2025 documents from newdocs folder
"""

import sys

sys.path.insert(0, '/home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA')

import hashlib
import os
from pathlib import Path

import psycopg2
import PyPDF2
from psycopg2.extras import Json

# Database connection
DB_URL = "postgresql://postgres:postgres@localhost:54322/postgres"

def get_db_pool():
    return psycopg2.pool.SimpleConnectionPool(1, 10, DB_URL)

def clear_all_documents(db_pool):
    """Clear ALL documents and mappings from database"""
    print("="*80)
    print("🗑️  CLEARING ALL EXISTING DOCUMENTS")
    print("="*80)
    
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        # Get counts before deletion
        cursor.execute("SELECT COUNT(*) FROM shared_documents")
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM shared_document_chunks")
        chunk_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM call_document_mappings")
        mapping_count = cursor.fetchone()[0]
        
        print("📊 Current database:")
        print(f"   Documents: {doc_count}")
        print(f"   Chunks: {chunk_count}")
        print(f"   Mappings: {mapping_count}")
        print()
        
        # Delete everything (cascade will handle chunks)
        print("🗑️  Deleting all call_document_mappings...")
        cursor.execute("DELETE FROM call_document_mappings")
        
        print("🗑️  Deleting all shared_document_chunks...")
        cursor.execute("DELETE FROM shared_document_chunks")
        
        print("🗑️  Deleting all shared_documents...")
        cursor.execute("DELETE FROM shared_documents")
        
        print("🗑️  Deleting all call_metadata...")
        cursor.execute("DELETE FROM call_metadata")
        
        conn.commit()
        cursor.close()
        
        print()
        print("✅ Database cleared successfully!")
        print("="*80)
        print()
        
    finally:
        db_pool.putconn(conn)

def classify_document(filename, filepath):
    """Classify document type and scope from filename"""
    filename_lower = filename.lower()
    
    # Work Programmes
    if 'wp-' in filename_lower and 'horizon-2025' in filename_lower:
        # Extract cluster number or topic
        if 'wp-1-' in filename_lower or 'general-introduction' in filename_lower:
            return {'type': 'work_programme', 'scope': 'global', 'scope_id': None, 'version': '2025', 
                    'title': 'HE Work Programme 2025 - 1. General Introduction'}
        elif 'wp-3-' in filename_lower or 'research-infrastructures' in filename_lower:
            return {'type': 'work_programme', 'scope': 'cluster', 'scope_id': 'CLUSTER-3-INFRA', 'version': '2025',
                    'title': 'HE Work Programme 2025 - 3. Research Infrastructures'}
        elif 'wp-4-' in filename_lower or '-health' in filename_lower:
            return {'type': 'work_programme', 'scope': 'cluster', 'scope_id': 'CLUSTER-1', 'version': '2025',
                    'title': 'HE Work Programme 2025 - 4. Health (Cluster 1)'}
        elif 'wp-5-' in filename_lower or 'culture' in filename_lower:
            return {'type': 'work_programme', 'scope': 'cluster', 'scope_id': 'CLUSTER-2', 'version': '2025',
                    'title': 'HE Work Programme 2025 - 5. Culture, Creativity and Inclusive Society (Cluster 2)'}
        elif 'wp-6-' in filename_lower or 'civil-security' in filename_lower:
            return {'type': 'work_programme', 'scope': 'cluster', 'scope_id': 'CLUSTER-3', 'version': '2025',
                    'title': 'HE Work Programme 2025 - 6. Civil Security for Society (Cluster 3)'}
        elif 'wp-7-' in filename_lower or 'digital-industry' in filename_lower:
            return {'type': 'work_programme', 'scope': 'cluster', 'scope_id': 'CLUSTER-4', 'version': '2025',
                    'title': 'HE Work Programme 2025 - 7. Digital, Industry and Space (Cluster 4)'}
        elif 'wp-8-' in filename_lower or 'climate-energy' in filename_lower:
            return {'type': 'work_programme', 'scope': 'cluster', 'scope_id': 'CLUSTER-5', 'version': '2025',
                    'title': 'HE Work Programme 2025 - 8. Climate, Energy and Mobility (Cluster 5)'}
        elif 'wp-9-' in filename_lower or 'food-bioeconomy' in filename_lower:
            return {'type': 'work_programme', 'scope': 'cluster', 'scope_id': 'CLUSTER-6', 'version': '2025',
                    'title': 'HE Work Programme 2025 - 9. Food, Bioeconomy (Cluster 6)'}
        elif 'wp-10-' in filename_lower or 'innovation-ecosystems' in filename_lower:
            return {'type': 'work_programme', 'scope': 'global', 'scope_id': None, 'version': '2025',
                    'title': 'HE Work Programme 2025 - 10. European Innovation Ecosystems'}
        elif 'wp-11-' in filename_lower or 'widening' in filename_lower:
            return {'type': 'work_programme', 'scope': 'global', 'scope_id': None, 'version': '2025',
                    'title': 'HE Work Programme 2025 - 11. Widening Participation'}
        elif 'wp-12-' in filename_lower or 'missions' in filename_lower:
            return {'type': 'work_programme', 'scope': 'global', 'scope_id': None, 'version': '2025',
                    'title': 'HE Work Programme 2025 - 12. Missions'}
        elif 'wp-13-' in filename_lower or 'bauhaus' in filename_lower:
            return {'type': 'work_programme', 'scope': 'global', 'scope_id': None, 'version': '2025',
                    'title': 'HE Work Programme 2025 - 13. New European Bauhaus'}
        elif 'wp-14-' in filename_lower or 'general-annexes' in filename_lower:
            return {'type': 'general_annexes', 'scope': 'global', 'scope_id': None, 'version': '2025',
                    'title': 'HE Work Programme 2025 - 14. General Annexes'}
    
    # Other documents
    if 'programme-guide' in filename_lower:
        return {'type': 'programme_guide', 'scope': 'global', 'scope_id': None, 'version': '2025',
                'title': 'Horizon Europe Programme Guide'}
    elif 'online-manual' in filename_lower or 'online_manual' in filename_lower:
        return {'type': 'online_manual', 'scope': 'global', 'scope_id': None, 'version': '2025',
                'title': 'Funding & Tenders Portal Online Manual'}
    elif 'aga' in filename_lower or 'annotated' in filename_lower:
        return {'type': 'annotated_grant_agreement', 'scope': 'global', 'scope_id': None, 'version': '2025',
                'title': 'EU Grants AGA - Annotated Model Grant Agreement'}
    elif 'legal-entity' in filename_lower or 'lear' in filename_lower:
        return {'type': 'legal_entity_rules', 'scope': 'global', 'scope_id': None, 'version': '2025',
                'title': 'Rules for Legal Entity Validation, LEAR Appointment and Financial Capacity Assessment'}
    else:
        # Generic other document
        title = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ').title()
        return {'type': 'other', 'scope': 'global', 'scope_id': None, 'version': '2025',
                'title': title}

def parse_pdf(filepath):
    """Parse PDF and extract text and metadata"""
    try:
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            page_count = len(pdf_reader.pages)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return {
                'text': text,
                'metadata': {
                    'page_count': page_count,
                    'file_size': os.path.getsize(filepath)
                }
            }
    except Exception as e:
        print(f"   ⚠️  Error parsing PDF: {e}")
        return {'text': '', 'metadata': {'page_count': 0, 'file_size': 0}}

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into chunks"""
    if not text or len(text.strip()) == 0:
        return []
    
    chunks = []
    words = text.split()
    
    if len(words) == 0:
        return []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_content = ' '.join(chunk_words)
        chunks.append(chunk_content)
    
    return chunks

def store_document(db_pool, filepath, doc_info):
    """Store document and its chunks in database"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        # Calculate file hash
        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Check if already exists
        cursor.execute("SELECT id FROM shared_documents WHERE file_hash = %s", (file_hash,))
        existing = cursor.fetchone()
        
        if existing:
            print("   ⏭️  Already exists (hash match)")
            db_pool.putconn(conn)
            return existing[0]
        
        # Parse PDF
        parsed = parse_pdf(filepath)
        
        # Create unique document key
        filename_slug = filepath.stem[:30].lower().replace(' ', '_').replace('-', '_')
        doc_key = f"{doc_info['type']}_{filename_slug}_{file_hash[:8]}".lower()
        
        # Insert document
        cursor.execute("""
            INSERT INTO shared_documents (
                document_key, document_type, document_title, document_version,
                scope, scope_identifier, document_content, file_path, file_hash,
                metadata, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            doc_key,
            doc_info['type'],
            doc_info['title'],
            doc_info['version'],
            doc_info['scope'],
            doc_info['scope_id'],
            parsed['text'][:10000],  # Store first 10k chars
            str(filepath),
            file_hash,
            Json(parsed['metadata'])
        ))
        
        doc_id = cursor.fetchone()[0]
        
        # Chunk and store
        chunks = chunk_text(parsed['text'])
        print(f"   ✂️  Creating {len(chunks)} chunks...")
        
        for idx, chunk_content in enumerate(chunks):
            cursor.execute("""
                INSERT INTO shared_document_chunks (
                    document_id, chunk_text, chunk_index, metadata
                ) VALUES (%s, %s, %s, %s)
            """, (doc_id, chunk_content, idx, Json({})))
        
        conn.commit()
        cursor.close()
        
        print(f"   ✅ Stored document (ID: {doc_id}, {len(chunks)} chunks)")
        return doc_id
        
    except Exception as e:
        print(f"   ❌ Error storing document: {e}")
        conn.rollback()
        return None
    finally:
        db_pool.putconn(conn)

def process_all_documents(db_pool, newdocs_path):
    """Process all documents in newdocs folder"""
    print("="*80)
    print("📥 PROCESSING NEW DOCUMENTS")
    print("="*80)
    print()
    
    processed_count = 0
    
    # Process 2025 Work Programmes first
    wp_dir = Path(newdocs_path) / "2025_work_programmes"
    if wp_dir.exists():
        print("📁 Processing 2025 Work Programmes...")
        print()
        for pdf_file in sorted(wp_dir.glob("*.pdf")):
            print(f"📄 {pdf_file.name}")
            doc_info = classify_document(pdf_file.name, pdf_file)
            doc_id = store_document(db_pool, pdf_file, doc_info)
            if doc_id:
                processed_count += 1
            print()
    
    # Process other documents
    print("📁 Processing Other Documents...")
    print()
    for pdf_file in sorted(Path(newdocs_path).glob("*.pdf")):
        print(f"📄 {pdf_file.name}")
        doc_info = classify_document(pdf_file.name, pdf_file)
        doc_id = store_document(db_pool, pdf_file, doc_info)
        if doc_id:
            processed_count += 1
        print()
    
    print("="*80)
    print(f"✅ Processed {processed_count} documents!")
    print("="*80)
    print()
    
    return processed_count

def show_summary(db_pool):
    """Show summary of what's in the database"""
    print("="*80)
    print("📊 FINAL DATABASE SUMMARY")
    print("="*80)
    print()
    
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        # Count by type
        cursor.execute("""
            SELECT document_type, COUNT(*), SUM((
                SELECT COUNT(*) FROM shared_document_chunks 
                WHERE document_id = sd.id
            ))
            FROM shared_documents sd
            GROUP BY document_type
            ORDER BY document_type
        """)
        
        print("By Document Type:")
        for row in cursor.fetchall():
            print(f"  {row[0]:30} {row[1]:3} docs, {row[2]:5} chunks")
        
        print()
        
        # Total counts
        cursor.execute("SELECT COUNT(*) FROM shared_documents")
        total_docs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM shared_document_chunks")
        total_chunks = cursor.fetchone()[0]
        
        print(f"TOTAL: {total_docs} documents, {total_chunks} chunks")
        print()
        
        # Show 2025 work programmes
        cursor.execute("""
            SELECT document_title 
            FROM shared_documents 
            WHERE document_type = 'work_programme' AND document_version = '2025'
            ORDER BY document_title
        """)
        
        print("2025 Work Programmes:")
        for row in cursor.fetchall():
            print(f"  ✅ {row[0]}")
        
        cursor.close()
        
    finally:
        db_pool.putconn(conn)
    
    print()
    print("="*80)

def main():
    newdocs_path = "/home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA/newdocs"
    
    print()
    print("="*80)
    print("🔄 COMPLETE DOCUMENT REFRESH")
    print("="*80)
    print()
    print(f"Source: {newdocs_path}")
    print(f"Target: {DB_URL}")
    print()
    
    # Get database pool
    db_pool = get_db_pool()
    
    # Step 1: Clear all existing documents
    clear_all_documents(db_pool)
    
    # Step 2: Process all new documents
    processed_count = process_all_documents(db_pool, newdocs_path)
    
    # Step 3: Show summary
    show_summary(db_pool)
    
    print("🎉 REFRESH COMPLETE!")
    print()

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Manual document upload and processing script.

This script processes locally downloaded PDFs and ingests them into the database.

Usage:
    1. Create directory: data/manual_uploads/YOUR_CALL_ID/
    2. Place PDF files in that directory
    3. Run: python scripts/manual_document_upload.py YOUR_CALL_ID

Example:
    mkdir -p data/manual_uploads/HORIZON-HLTH-2024-TOOL-12-01/
    # Download PDFs and place them in the directory
    python scripts/manual_document_upload.py HORIZON-HLTH-2024-TOOL-12-01
"""

import sys
import asyncio
import logging
from pathlib import Path
import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


def get_db_pool():
    """Create database connection pool"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")
    
    return psycopg2.pool.SimpleConnectionPool(
        1, 5, db_url
    )


def infer_document_type(filename: str) -> str:
    """Infer document type from filename"""
    name_lower = filename.lower()
    
    if 'work' in name_lower and 'programme' in name_lower:
        return 'work_programme'
    elif 'call' in name_lower or 'topic' in name_lower or 'fiche' in name_lower:
        return 'topic_description'
    elif 'guide' in name_lower or 'manual' in name_lower:
        if 'evaluation' in name_lower:
            return 'evaluation_guide'
        else:
            return 'application_guide'
    elif 'template' in name_lower:
        if 'budget' in name_lower:
            return 'budget_template'
        else:
            return 'proposal_template'
    elif 'faq' in name_lower:
        return 'faq'
    elif 'eligibility' in name_lower or 'rules' in name_lower:
        return 'eligibility_rules'
    elif 'mga' in name_lower or 'grant' in name_lower and 'agreement' in name_lower:
        return 'model_grant_agreement'
    else:
        return 'other'


class SimpleDocumentParser:
    """Simplified PDF parser using PyPDF2"""
    
    def parse_pdf(self, file_path: Path) -> dict:
        """Parse PDF and extract text"""
        try:
            import PyPDF2
            
            logger.info(f"  📖 Parsing PDF: {file_path.name}")
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                full_text = []
                sections = []
                current_section = None
                
                for page_num, page in enumerate(reader.pages, start=1):
                    text = page.extract_text()
                    
                    # Split into lines
                    lines = text.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Simple heuristic: UPPERCASE or numbered headings
                        is_heading = (
                            (line.isupper() and len(line) < 100) or
                            (line[0].isdigit() and '.' in line[:5] and len(line) < 100)
                        )
                        
                        if is_heading:
                            # Save previous section
                            if current_section:
                                sections.append(current_section)
                            
                            # Start new section
                            current_section = {
                                'title': line,
                                'content': '',
                                'page_numbers': [page_num],
                                'level': 2
                            }
                        elif current_section:
                            current_section['content'] += line + '\n'
                            if page_num not in current_section['page_numbers']:
                                current_section['page_numbers'].append(page_num)
                        
                        full_text.append(line)
                
                # Add last section
                if current_section:
                    sections.append(current_section)
                
                return {
                    'full_text': '\n'.join(full_text),
                    'sections': sections,
                    'metadata': {
                        'page_count': len(reader.pages)
                    }
                }
        
        except Exception as e:
            logger.error(f"  ❌ PDF parsing failed: {e}")
            return {'full_text': '', 'sections': [], 'metadata': {}}


class SimpleChunker:
    """Simple document chunker"""
    
    def __init__(self, max_chunk_size=1000, overlap=200):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_document(self, parsed_doc: dict, call_identifier: str, document_type: str) -> list:
        """Create chunks from parsed document"""
        logger.info(f"  ✂️ Chunking document...")
        
        chunks = []
        
        if parsed_doc.get('sections'):
            # Chunk by sections
            for i, section in enumerate(parsed_doc['sections']):
                section_chunks = self._chunk_section(
                    section, i, call_identifier, document_type
                )
                chunks.extend(section_chunks)
        else:
            # Simple text chunking
            text = parsed_doc.get('full_text', '')
            chunks = self._simple_chunk(text, call_identifier, document_type)
        
        return chunks
    
    def _chunk_section(self, section: dict, start_index: int, call_id: str, doc_type: str) -> list:
        """Chunk a section"""
        chunks = []
        
        section_title = section['title']
        content = section['content']
        page_numbers = section.get('page_numbers', [])
        
        # Add section title to content
        full_content = f"## {section_title}\n\n{content}"
        
        # Split into chunks
        words = full_content.split()
        chunk_size_words = self.max_chunk_size // 4
        
        for i in range(0, len(words), chunk_size_words):
            chunk_words = words[i:i + chunk_size_words]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append({
                'text': chunk_text,
                'chunk_index': start_index + len(chunks),
                'section_title': section_title,
                'page_numbers': page_numbers,
                'token_count': len(chunk_words) * 4,
                'metadata': {
                    'call_identifier': call_id,
                    'document_type': doc_type
                }
            })
        
        return chunks
    
    def _simple_chunk(self, text: str, call_id: str, doc_type: str) -> list:
        """Simple text chunking"""
        chunks = []
        words = text.split()
        chunk_size_words = self.max_chunk_size // 4
        
        for i in range(0, len(words), chunk_size_words):
            chunk_words = words[i:i + chunk_size_words]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append({
                'text': chunk_text,
                'chunk_index': len(chunks),
                'section_title': None,
                'page_numbers': [],
                'token_count': len(chunk_words) * 4,
                'metadata': {
                    'call_identifier': call_id,
                    'document_type': doc_type
                }
            })
        
        return chunks


async def process_manual_documents(call_identifier: str):
    """Process manually uploaded documents"""
    
    # Setup
    upload_dir = Path(f"data/manual_uploads/{call_identifier}")
    
    if not upload_dir.exists():
        print(f"❌ Directory not found: {upload_dir}")
        print(f"\nPlease create it and add PDF files:")
        print(f"  mkdir -p {upload_dir}")
        print(f"  # Copy your PDF files to {upload_dir}/")
        return
    
    # Find PDF files
    pdf_files = list(upload_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {upload_dir}")
        return
    
    print(f"\n🚀 Processing {len(pdf_files)} documents for call: {call_identifier}\n")
    print("="*70)
    
    # Initialize
    db_pool = get_db_pool()
    parser = SimpleDocumentParser()
    chunker = SimpleChunker()
    
    stats = {
        'documents_processed': 0,
        'sections_found': 0,
        'chunks_created': 0,
        'errors': []
    }
    
    # Process each PDF
    for pdf_file in pdf_files:
        try:
            print(f"\n📄 Processing: {pdf_file.name}")
            print("-" * 70)
            
            # Infer document type
            doc_type = infer_document_type(pdf_file.name)
            print(f"  📋 Detected type: {doc_type}")
            
            # Parse
            parsed = parser.parse_pdf(pdf_file)
            sections_count = len(parsed.get('sections', []))
            stats['sections_found'] += sections_count
            print(f"  ✅ Parsed: {sections_count} sections, {parsed['metadata'].get('page_count', 0)} pages")
            
            # Chunk
            chunks = chunker.chunk_document(parsed, call_identifier, doc_type)
            stats['chunks_created'] += len(chunks)
            print(f"  ✅ Created: {len(chunks)} chunks")
            
            # Store in database
            print(f"  💾 Storing in database...")
            store_document_and_chunks(
                db_pool=db_pool,
                call_identifier=call_identifier,
                doc_type=doc_type,
                doc_title=pdf_file.stem,
                file_path=str(pdf_file),
                parsed=parsed,
                chunks=chunks
            )
            print(f"  ✅ Stored successfully")
            
            stats['documents_processed'] += 1
            
        except Exception as e:
            error_msg = f"Failed to process {pdf_file.name}: {e}"
            logger.error(f"❌ {error_msg}")
            stats['errors'].append(error_msg)
            print(f"  ❌ Error: {e}")
    
    # Print summary
    print("\n" + "="*70)
    print("📊 PROCESSING SUMMARY")
    print("="*70)
    print(f"Call identifier: {call_identifier}")
    print(f"Documents processed: {stats['documents_processed']}/{len(pdf_files)}")
    print(f"Sections found: {stats['sections_found']}")
    print(f"Chunks created: {stats['chunks_created']}")
    
    if stats['errors']:
        print(f"\n⚠️ Errors ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"  - {error}")
    else:
        print(f"\n✅ All documents processed successfully!")
    
    print("="*70)
    
    # Query check
    print("\n🔍 Verifying database storage...")
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM call_documents WHERE call_identifier = %s
        """, (call_identifier,))
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM call_document_chunks WHERE call_identifier = %s
        """, (call_identifier,))
        chunk_count = cursor.fetchone()[0]
        
        print(f"  ✅ Database records:")
        print(f"     - Documents: {doc_count}")
        print(f"     - Chunks: {chunk_count}")
        
    finally:
        db_pool.putconn(conn)


def store_document_and_chunks(db_pool, call_identifier: str, doc_type: str, 
                              doc_title: str, file_path: str, parsed: dict, chunks: list):
    """Store document and chunks in database"""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        
        # Insert document
        cursor.execute("""
            INSERT INTO call_documents (
                call_identifier, document_type, document_title,
                document_content, document_url, file_path,
                last_updated, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            RETURNING id
        """, (
            call_identifier,
            doc_type,
            doc_title,
            parsed['full_text'],
            None,  # No URL for manual uploads
            file_path,
            {'page_count': parsed['metadata'].get('page_count', 0)}
        ))
        
        document_id = cursor.fetchone()[0]
        
        # Insert chunks
        for chunk in chunks:
            cursor.execute("""
                INSERT INTO call_document_chunks (
                    call_document_id, call_identifier, chunk_text,
                    chunk_index, token_count, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                document_id,
                call_identifier,
                chunk['text'],
                chunk['chunk_index'],
                chunk['token_count'],
                chunk['metadata']
            ))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/manual_document_upload.py <CALL_IDENTIFIER>")
        print("\nExample:")
        print("  python scripts/manual_document_upload.py HORIZON-HLTH-2024-TOOL-12-01")
        sys.exit(1)
    
    call_identifier = sys.argv[1]
    asyncio.run(process_manual_documents(call_identifier))


if __name__ == "__main__":
    main()


# 📥 Document Ingestion Pipeline for Call Documents

## 🎯 Goal
Automatically fetch, parse, chunk, and store call-specific documents from EU funding portals.

---

## 📊 Data Sources

### **Primary Source: EU Funding & Tenders Portal API**
The EU portal provides structured data about calls AND links to documents:

```python
# Example API endpoint
https://api.tech.ec.europa.eu/search-api/prod/rest/search

# Returns call data including:
{
  "identifier": "HORIZON-HLTH-2024-TOOL-12-01",
  "title": "AI-powered diagnostic tools",
  "documents": [
    {
      "type": "wp",  # Work Programme
      "url": "https://ec.europa.eu/.../wp-2024.pdf"
    },
    {
      "type": "cw",  # Call fiche/description
      "url": "https://ec.europa.eu/.../call-fiche.pdf"
    }
  ]
}
```

### **Standard Document Types Available**

1. **Work Programme (WP)** - The main policy document
2. **Call fiche** - Detailed call description
3. **Guide for Applicants** - How to apply
4. **Proposal Template** - What to submit
5. **Evaluation Guide** - How proposals are assessed
6. **Budget Template** - Budget calculation rules
7. **Model Grant Agreement** - Legal terms
8. **FAQ documents** - Common questions

---

## 🏗️ Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Discover Calls & Documents                      │
│ → Fetch open calls from EU API                          │
│ → Extract document URLs                                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Step 2: Download Documents                              │
│ → Download PDFs, DOC files                              │
│ → Store locally with metadata                           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Step 3: Parse & Extract Text                           │
│ → Extract text from PDFs (preserving structure)        │
│ → Identify sections, headings, tables                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Step 4: Intelligent Chunking                           │
│ → Split by sections (not arbitrary chunks)             │
│ → Preserve context & headers                           │
│ → Create overlapping chunks for continuity             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Step 5: Generate Embeddings                            │
│ → Use embedding model (text-embedding-004)             │
│ → Generate vectors for semantic search                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Step 6: Store in Database                              │
│ → Insert into call_documents table                     │
│ → Create chunks in call_document_chunks                │
│ → Link to funding_calls table                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation

### **Component 1: Document Fetcher**
**File**: `app/services/document_ingestion/document_fetcher.py`

```python
import requests
import logging
from typing import List, Dict, Any
from pathlib import Path
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class EUPortalDocumentFetcher:
    """
    Fetches call documents from EU Funding & Tenders Portal.
    """
    
    BASE_API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    DOCUMENT_STORAGE = Path("./data/call_documents")
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Research-Assistant/1.0',
            'Accept': 'application/json'
        })
        
        # Ensure storage directory exists
        self.DOCUMENT_STORAGE.mkdir(parents=True, exist_ok=True)
    
    async def fetch_call_documents(self, call_identifier: str) -> Dict[str, Any]:
        """
        Fetch all documents associated with a call.
        
        Returns:
            {
                'call_identifier': str,
                'documents': [
                    {
                        'type': 'work_programme',
                        'url': str,
                        'local_path': str,
                        'title': str,
                        'last_updated': datetime
                    }
                ]
            }
        """
        logger.info(f"📥 Fetching documents for call: {call_identifier}")
        
        # Step 1: Get call details from API
        call_data = await self._fetch_call_from_api(call_identifier)
        
        if not call_data:
            logger.warning(f"⚠️ Call {call_identifier} not found in API")
            return {'call_identifier': call_identifier, 'documents': []}
        
        # Step 2: Extract document URLs
        doc_urls = self._extract_document_urls(call_data)
        logger.info(f"📄 Found {len(doc_urls)} documents")
        
        # Step 3: Download each document
        documents = []
        for doc_info in doc_urls:
            try:
                local_path = await self._download_document(
                    url=doc_info['url'],
                    call_identifier=call_identifier,
                    doc_type=doc_info['type']
                )
                
                if local_path:
                    documents.append({
                        'type': doc_info['type'],
                        'url': doc_info['url'],
                        'local_path': str(local_path),
                        'title': doc_info.get('title', 'Untitled'),
                        'last_updated': datetime.now()
                    })
                    logger.info(f"✅ Downloaded: {doc_info['type']}")
            except Exception as e:
                logger.error(f"❌ Failed to download {doc_info['type']}: {e}")
        
        return {
            'call_identifier': call_identifier,
            'documents': documents
        }
    
    async def _fetch_call_from_api(self, call_identifier: str) -> Dict[str, Any]:
        """Fetch call data from EU Portal API"""
        try:
            params = {
                'apiKey': 'SEDIA',  # Public API key
                'text': call_identifier,
                'pageSize': 1,
                'pageNumber': 1
            }
            
            response = self.session.get(self.BASE_API_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results'):
                return data['results'][0]
            
            return None
        except Exception as e:
            logger.error(f"❌ API fetch failed: {e}")
            return None
    
    def _extract_document_urls(self, call_data: Dict) -> List[Dict[str, str]]:
        """Extract document URLs from call data"""
        documents = []
        
        # Work Programme
        if 'workProgramme' in call_data and call_data['workProgramme']:
            wp = call_data['workProgramme']
            if 'pdfUrl' in wp:
                documents.append({
                    'type': 'work_programme',
                    'url': wp['pdfUrl'],
                    'title': wp.get('title', 'Work Programme')
                })
        
        # Call-specific documents
        if 'callDocuments' in call_data:
            for doc in call_data['callDocuments']:
                doc_type = self._map_document_type(doc.get('type', ''))
                if 'url' in doc or 'pdfUrl' in doc:
                    documents.append({
                        'type': doc_type,
                        'url': doc.get('url') or doc.get('pdfUrl'),
                        'title': doc.get('title', doc_type.replace('_', ' ').title())
                    })
        
        # Additional linked documents
        if 'documents' in call_data:
            for doc in call_data['documents']:
                if doc.get('mimeType') == 'application/pdf':
                    doc_type = self._infer_doc_type_from_filename(doc.get('fileName', ''))
                    documents.append({
                        'type': doc_type,
                        'url': doc['url'],
                        'title': doc.get('title', doc.get('fileName', 'Document'))
                    })
        
        return documents
    
    def _map_document_type(self, api_type: str) -> str:
        """Map API document type to our internal types"""
        mapping = {
            'wp': 'work_programme',
            'cw': 'topic_description',
            'guide': 'application_guide',
            'template': 'proposal_template',
            'faq': 'faq',
            'evaluation': 'evaluation_guide',
            'budget': 'budget_template',
            'mga': 'model_grant_agreement'
        }
        return mapping.get(api_type.lower(), 'other')
    
    def _infer_doc_type_from_filename(self, filename: str) -> str:
        """Infer document type from filename"""
        filename_lower = filename.lower()
        
        if 'work' in filename_lower and 'programme' in filename_lower:
            return 'work_programme'
        elif 'call' in filename_lower or 'topic' in filename_lower:
            return 'topic_description'
        elif 'guide' in filename_lower or 'manual' in filename_lower:
            return 'application_guide'
        elif 'template' in filename_lower:
            return 'proposal_template'
        elif 'faq' in filename_lower:
            return 'faq'
        elif 'evaluation' in filename_lower or 'criteria' in filename_lower:
            return 'evaluation_guide'
        elif 'budget' in filename_lower:
            return 'budget_template'
        else:
            return 'other'
    
    async def _download_document(
        self, 
        url: str, 
        call_identifier: str, 
        doc_type: str
    ) -> Path:
        """Download document to local storage"""
        try:
            # Create call-specific directory
            call_dir = self.DOCUMENT_STORAGE / call_identifier
            call_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            extension = self._get_file_extension(url)
            filename = f"{doc_type}_{url_hash}{extension}"
            local_path = call_dir / filename
            
            # Skip if already downloaded
            if local_path.exists():
                logger.info(f"📦 File already exists: {filename}")
                return local_path
            
            # Download file
            logger.info(f"⬇️ Downloading: {url}")
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Save to disk
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"✅ Saved: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"❌ Download failed for {url}: {e}")
            return None
    
    def _get_file_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        from urllib.parse import urlparse
        path = urlparse(url).path
        
        if path.endswith('.pdf'):
            return '.pdf'
        elif path.endswith('.docx'):
            return '.docx'
        elif path.endswith('.doc'):
            return '.doc'
        else:
            return '.pdf'  # Default to PDF
```

---

### **Component 2: Document Parser**
**File**: `app/services/document_ingestion/document_parser.py`

```python
import logging
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
import fitz  # PyMuPDF - better PDF parsing
from docx import Document

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Parses documents and extracts structured text.
    Handles PDFs, DOCX, and other formats.
    """
    
    def parse_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a document and extract structured content.
        
        Returns:
            {
                'full_text': str,
                'sections': [
                    {
                        'title': str,
                        'content': str,
                        'page_numbers': [int],
                        'level': int  # 1=chapter, 2=section, 3=subsection
                    }
                ],
                'metadata': dict
            }
        """
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self._parse_pdf(file_path)
        elif extension in ['.docx', '.doc']:
            return self._parse_docx(file_path)
        else:
            logger.warning(f"⚠️ Unsupported file type: {extension}")
            return {'full_text': '', 'sections': [], 'metadata': {}}
    
    def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Parse PDF with structure preservation"""
        logger.info(f"📄 Parsing PDF: {file_path.name}")
        
        try:
            # Use PyMuPDF for better text extraction
            doc = fitz.open(file_path)
            
            full_text = []
            sections = []
            current_section = None
            
            for page_num, page in enumerate(doc, start=1):
                # Extract text with formatting info
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if block["type"] == 0:  # Text block
                        for line in block.get("lines", []):
                            text = " ".join([span["text"] for span in line.get("spans", [])])
                            
                            # Detect headings (heuristic: larger font, bold)
                            is_heading = self._is_likely_heading(line)
                            
                            if is_heading:
                                # Save previous section
                                if current_section:
                                    sections.append(current_section)
                                
                                # Start new section
                                current_section = {
                                    'title': text,
                                    'content': '',
                                    'page_numbers': [page_num],
                                    'level': self._estimate_heading_level(text)
                                }
                            elif current_section:
                                current_section['content'] += text + '\n'
                                if page_num not in current_section['page_numbers']:
                                    current_section['page_numbers'].append(page_num)
                            
                            full_text.append(text)
            
            # Add last section
            if current_section:
                sections.append(current_section)
            
            doc.close()
            
            return {
                'full_text': '\n'.join(full_text),
                'sections': sections,
                'metadata': {
                    'page_count': len(doc),
                    'file_size': file_path.stat().st_size
                }
            }
            
        except Exception as e:
            logger.error(f"❌ PDF parsing failed: {e}")
            return {'full_text': '', 'sections': [], 'metadata': {}}
    
    def _is_likely_heading(self, line: Dict) -> bool:
        """Heuristic to detect if line is a heading"""
        if not line.get("spans"):
            return False
        
        span = line["spans"][0]
        font_size = span.get("size", 0)
        font_flags = span.get("flags", 0)
        
        # Heuristics:
        # 1. Font size > 12 (usually body text is 10-11)
        # 2. Bold text (font_flags & 2^4)
        # 3. All caps
        # 4. Short text (< 100 chars)
        
        is_bold = (font_flags & 16) != 0
        text = span.get("text", "")
        is_short = len(text) < 100
        is_caps = text.isupper() and len(text) > 5
        
        return (font_size > 12 or (is_bold and is_short) or is_caps)
    
    def _estimate_heading_level(self, text: str) -> int:
        """Estimate heading level (1=chapter, 2=section, etc.)"""
        text_lower = text.lower().strip()
        
        # Chapter/Part indicators
        if any(word in text_lower for word in ['chapter', 'part', 'annex']):
            return 1
        
        # Numbered sections
        if text.startswith(('1.', '2.', '3.', '4.', '5.')):
            # Count dots to determine level
            dots = text[:10].count('.')
            return min(dots + 1, 4)
        
        # Default
        return 2
    
    def _parse_docx(self, file_path: Path) -> Dict[str, Any]:
        """Parse DOCX file"""
        logger.info(f"📄 Parsing DOCX: {file_path.name}")
        
        try:
            doc = Document(file_path)
            
            full_text = []
            sections = []
            current_section = None
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # Detect headings
                if para.style.name.startswith('Heading'):
                    # Save previous section
                    if current_section:
                        sections.append(current_section)
                    
                    # Extract heading level
                    level = int(para.style.name.replace('Heading ', '')) if para.style.name != 'Heading' else 1
                    
                    current_section = {
                        'title': text,
                        'content': '',
                        'page_numbers': [],  # DOCX doesn't have page numbers easily
                        'level': level
                    }
                elif current_section:
                    current_section['content'] += text + '\n'
                
                full_text.append(text)
            
            # Add last section
            if current_section:
                sections.append(current_section)
            
            return {
                'full_text': '\n'.join(full_text),
                'sections': sections,
                'metadata': {
                    'paragraph_count': len(doc.paragraphs)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ DOCX parsing failed: {e}")
            return {'full_text': '', 'sections': [], 'metadata': {}}
```

---

### **Component 3: Smart Chunker**
**File**: `app/services/document_ingestion/document_chunker.py`

```python
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SmartDocumentChunker:
    """
    Intelligently chunks documents for RAG.
    Preserves semantic boundaries (sections, paragraphs).
    """
    
    def __init__(
        self, 
        max_chunk_size: int = 1000,  # tokens
        overlap: int = 200,           # tokens
        preserve_sections: bool = True
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.preserve_sections = preserve_sections
    
    def chunk_document(
        self, 
        parsed_doc: Dict[str, Any],
        call_identifier: str,
        document_type: str
    ) -> List[Dict[str, Any]]:
        """
        Create smart chunks from parsed document.
        
        Returns:
            [
                {
                    'text': str,
                    'chunk_index': int,
                    'section_title': str,
                    'page_numbers': [int],
                    'token_count': int,
                    'metadata': dict
                }
            ]
        """
        logger.info(f"✂️ Chunking document ({document_type}) into semantic chunks")
        
        chunks = []
        chunk_index = 0
        
        if self.preserve_sections and parsed_doc.get('sections'):
            # Chunk by sections (better for semantic coherence)
            for section in parsed_doc['sections']:
                section_chunks = self._chunk_section(
                    section=section,
                    start_index=chunk_index,
                    call_identifier=call_identifier,
                    document_type=document_type
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
        else:
            # Fall back to simple chunking
            text = parsed_doc.get('full_text', '')
            simple_chunks = self._simple_chunk(text, call_identifier, document_type)
            chunks.extend(simple_chunks)
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        return chunks
    
    def _chunk_section(
        self, 
        section: Dict,
        start_index: int,
        call_identifier: str,
        document_type: str
    ) -> List[Dict[str, Any]]:
        """Chunk a single section, preserving context"""
        chunks = []
        
        section_title = section['title']
        content = section['content']
        page_numbers = section.get('page_numbers', [])
        
        # Split content into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk = f"## {section_title}\n\n"
        current_tokens = self._estimate_tokens(current_chunk)
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            # Check if adding this paragraph exceeds max size
            if current_tokens + para_tokens > self.max_chunk_size and current_tokens > 0:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'chunk_index': start_index + len(chunks),
                    'section_title': section_title,
                    'page_numbers': page_numbers,
                    'token_count': current_tokens,
                    'metadata': {
                        'call_identifier': call_identifier,
                        'document_type': document_type,
                        'section_level': section.get('level', 2)
                    }
                })
                
                # Start new chunk with overlap (include section title + last para)
                current_chunk = f"## {section_title}\n\n{para}\n\n"
                current_tokens = self._estimate_tokens(current_chunk)
            else:
                # Add paragraph to current chunk
                current_chunk += para + '\n\n'
                current_tokens += para_tokens
        
        # Save remaining chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'chunk_index': start_index + len(chunks),
                'section_title': section_title,
                'page_numbers': page_numbers,
                'token_count': current_tokens,
                'metadata': {
                    'call_identifier': call_identifier,
                    'document_type': document_type,
                    'section_level': section.get('level', 2)
                }
            })
        
        return chunks
    
    def _simple_chunk(
        self, 
        text: str, 
        call_identifier: str, 
        document_type: str
    ) -> List[Dict[str, Any]]:
        """Simple chunking when sections are not available"""
        chunks = []
        words = text.split()
        
        chunk_size_words = self.max_chunk_size // 4  # Rough approximation
        overlap_words = self.overlap // 4
        
        for i in range(0, len(words), chunk_size_words - overlap_words):
            chunk_words = words[i:i + chunk_size_words]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append({
                'text': chunk_text,
                'chunk_index': len(chunks),
                'section_title': None,
                'page_numbers': [],
                'token_count': len(chunk_words) * 4,  # Rough estimate
                'metadata': {
                    'call_identifier': call_identifier,
                    'document_type': document_type
                }
            })
        
        return chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4
```

---

### **Component 4: Complete Ingestion Orchestrator**
**File**: `app/services/document_ingestion/ingestion_orchestrator.py`

```python
import logging
from typing import List, Dict, Any
import asyncio
from .document_fetcher import EUPortalDocumentFetcher
from .document_parser import DocumentParser
from .document_chunker import SmartDocumentChunker

logger = logging.getLogger(__name__)


class DocumentIngestionOrchestrator:
    """
    Orchestrates the complete document ingestion pipeline.
    """
    
    def __init__(self, db_pool, embedding_service=None):
        self.db_pool = db_pool
        self.embedding_service = embedding_service
        
        self.fetcher = EUPortalDocumentFetcher()
        self.parser = DocumentParser()
        self.chunker = SmartDocumentChunker()
    
    async def ingest_call_documents(self, call_identifier: str) -> Dict[str, Any]:
        """
        Complete ingestion pipeline for a call.
        
        Workflow:
        1. Fetch documents from EU Portal
        2. Parse each document
        3. Chunk intelligently
        4. Generate embeddings
        5. Store in database
        """
        logger.info(f"🚀 Starting ingestion for call: {call_identifier}")
        
        stats = {
            'call_identifier': call_identifier,
            'documents_fetched': 0,
            'documents_parsed': 0,
            'chunks_created': 0,
            'embeddings_generated': 0,
            'errors': []
        }
        
        try:
            # Step 1: Fetch documents
            logger.info("📥 Step 1: Fetching documents...")
            fetch_result = await self.fetcher.fetch_call_documents(call_identifier)
            documents = fetch_result['documents']
            stats['documents_fetched'] = len(documents)
            logger.info(f"✅ Fetched {len(documents)} documents")
            
            # Step 2-6: Process each document
            for doc in documents:
                try:
                    await self._process_single_document(
                        call_identifier=call_identifier,
                        doc_info=doc,
                        stats=stats
                    )
                except Exception as e:
                    error_msg = f"Failed to process {doc['type']}: {e}"
                    logger.error(f"❌ {error_msg}")
                    stats['errors'].append(error_msg)
            
            logger.info(f"✅ Ingestion complete! {stats['chunks_created']} chunks created")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            stats['errors'].append(str(e))
            return stats
    
    async def _process_single_document(
        self,
        call_identifier: str,
        doc_info: Dict,
        stats: Dict
    ):
        """Process a single document through the pipeline"""
        from pathlib import Path
        
        logger.info(f"📄 Processing: {doc_info['type']}")
        
        # Step 2: Parse document
        logger.info("  📖 Parsing...")
        parsed = self.parser.parse_document(Path(doc_info['local_path']))
        stats['documents_parsed'] += 1
        logger.info(f"  ✅ Parsed {len(parsed.get('sections', []))} sections")
        
        # Step 3: Chunk document
        logger.info("  ✂️ Chunking...")
        chunks = self.chunker.chunk_document(
            parsed_doc=parsed,
            call_identifier=call_identifier,
            document_type=doc_info['type']
        )
        stats['chunks_created'] += len(chunks)
        logger.info(f"  ✅ Created {len(chunks)} chunks")
        
        # Step 4: Generate embeddings (if service available)
        if self.embedding_service:
            logger.info("  🧮 Generating embeddings...")
            for chunk in chunks:
                try:
                    embedding = await self.embedding_service.embed(chunk['text'])
                    chunk['embedding'] = embedding
                    stats['embeddings_generated'] += 1
                except Exception as e:
                    logger.error(f"  ❌ Embedding failed: {e}")
                    chunk['embedding'] = None
            logger.info(f"  ✅ Generated {stats['embeddings_generated']} embeddings")
        
        # Step 5: Store in database
        logger.info("  💾 Storing in database...")
        await self._store_document_and_chunks(
            call_identifier=call_identifier,
            doc_info=doc_info,
            parsed=parsed,
            chunks=chunks
        )
        logger.info("  ✅ Stored in database")
    
    async def _store_document_and_chunks(
        self,
        call_identifier: str,
        doc_info: Dict,
        parsed: Dict,
        chunks: List[Dict]
    ):
        """Store document and chunks in database"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # Insert into call_documents
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
                doc_info['type'],
                doc_info['title'],
                parsed['full_text'],
                doc_info['url'],
                doc_info['local_path'],
                {'page_count': parsed['metadata'].get('page_count', 0)}
            ))
            
            document_id = cursor.fetchone()[0]
            
            # Insert chunks
            for chunk in chunks:
                cursor.execute("""
                    INSERT INTO call_document_chunks (
                        call_document_id, call_identifier, chunk_text,
                        chunk_index, token_count, embedding, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    document_id,
                    call_identifier,
                    chunk['text'],
                    chunk['chunk_index'],
                    chunk['token_count'],
                    chunk.get('embedding'),
                    chunk['metadata']
                ))
            
            conn.commit()
            logger.info(f"✅ Stored document {document_id} with {len(chunks)} chunks")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Database storage failed: {e}")
            raise
        finally:
            self.db_pool.putconn(conn)
    
    async def bulk_ingest_open_calls(self, limit: int = 10):
        """Ingest documents for all currently open calls"""
        logger.info(f"🚀 Bulk ingestion starting for {limit} open calls")
        
        # Fetch open calls from database
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT identifier
                FROM funding_calls
                WHERE status = 'open'
                  AND deadline > NOW()
                ORDER BY deadline ASC
                LIMIT %s
            """, (limit,))
            
            call_identifiers = [row[0] for row in cursor.fetchall()]
            logger.info(f"📋 Found {len(call_identifiers)} open calls")
            
        finally:
            self.db_pool.putconn(conn)
        
        # Process each call
        results = []
        for call_id in call_identifiers:
            try:
                result = await self.ingest_call_documents(call_id)
                results.append(result)
                # Brief pause to avoid overwhelming the EU Portal
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"❌ Failed to ingest {call_id}: {e}")
                results.append({
                    'call_identifier': call_id,
                    'error': str(e)
                })
        
        return results
```

---

## 🚀 Usage Scripts

### **Script 1: Ingest Single Call**
**File**: `scripts/ingest_call_documents.py`

```python
#!/usr/bin/env python3
"""
Script to ingest documents for a specific call.

Usage:
    python scripts/ingest_call_documents.py HORIZON-HLTH-2024-TOOL-12-01
"""

import sys
import asyncio
import logging
from app.services.document_ingestion.ingestion_orchestrator import DocumentIngestionOrchestrator
from app.core.database import get_db_pool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_call_documents.py <CALL_IDENTIFIER>")
        sys.exit(1)
    
    call_identifier = sys.argv[1]
    
    print(f"🚀 Starting document ingestion for: {call_identifier}\n")
    
    # Initialize
    db_pool = get_db_pool()
    orchestrator = DocumentIngestionOrchestrator(db_pool)
    
    # Run ingestion
    result = await orchestrator.ingest_call_documents(call_identifier)
    
    # Print results
    print("\n" + "="*60)
    print("📊 INGESTION RESULTS")
    print("="*60)
    print(f"Call: {result['call_identifier']}")
    print(f"Documents fetched: {result['documents_fetched']}")
    print(f"Documents parsed: {result['documents_parsed']}")
    print(f"Chunks created: {result['chunks_created']}")
    print(f"Embeddings generated: {result['embeddings_generated']}")
    
    if result['errors']:
        print(f"\n⚠️ Errors ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"  - {error}")
    else:
        print("\n✅ No errors!")
    
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
```

### **Script 2: Bulk Ingest Open Calls**
**File**: `scripts/bulk_ingest_open_calls.py`

```python
#!/usr/bin/env python3
"""
Script to ingest documents for all open calls.

Usage:
    python scripts/bulk_ingest_open_calls.py --limit 10
"""

import asyncio
import argparse
import logging
from app.services.document_ingestion.ingestion_orchestrator import DocumentIngestionOrchestrator
from app.core.database import get_db_pool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    parser = argparse.ArgumentParser(description='Bulk ingest call documents')
    parser.add_argument('--limit', type=int, default=10, help='Number of calls to process')
    args = parser.parse_args()
    
    print(f"🚀 Starting bulk ingestion for {args.limit} open calls\n")
    
    # Initialize
    db_pool = get_db_pool()
    orchestrator = DocumentIngestionOrchestrator(db_pool)
    
    # Run bulk ingestion
    results = await orchestrator.bulk_ingest_open_calls(limit=args.limit)
    
    # Aggregate results
    total_docs = sum(r.get('documents_fetched', 0) for r in results)
    total_chunks = sum(r.get('chunks_created', 0) for r in results)
    total_errors = sum(len(r.get('errors', [])) for r in results)
    
    print("\n" + "="*60)
    print("📊 BULK INGESTION SUMMARY")
    print("="*60)
    print(f"Calls processed: {len(results)}")
    print(f"Total documents: {total_docs}")
    print(f"Total chunks: {total_chunks}")
    print(f"Total errors: {total_errors}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📅 Automation: Scheduled Updates

### **Cron Job Setup**
**File**: `scripts/setup_document_sync_cron.sh`

```bash
#!/bin/bash

# Add cron job to update call documents daily
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Update call documents every day at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * cd $SCRIPT_DIR/.. && python scripts/bulk_ingest_open_calls.py --limit 50 >> logs/document_sync.log 2>&1") | crontab -

echo "✅ Cron job installed: Daily document sync at 2:00 AM"
```

---

## 🧪 Testing

```python
# Test the pipeline with a single call
python scripts/ingest_call_documents.py HORIZON-HLTH-2024-TOOL-12-01

# Expected output:
# 📥 Fetching documents...
# ✅ Fetched 8 documents
# 📄 Processing: work_programme
#   📖 Parsing...
#   ✅ Parsed 45 sections
#   ✂️ Chunking...
#   ✅ Created 127 chunks
#   💾 Storing in database...
#   ✅ Stored in database
# ...
# 📊 INGESTION RESULTS
# Chunks created: 856
# ✅ No errors!
```

---

## 📦 Required Dependencies

Add to `requirements.txt`:

```
PyPDF2>=3.0.0
PyMuPDF>=1.23.0
python-docx>=1.1.0
requests>=2.31.0
```

---

This pipeline automatically builds your `call_documents` table! 🎉

Run once per call, or set up daily sync to keep documents up-to-date.


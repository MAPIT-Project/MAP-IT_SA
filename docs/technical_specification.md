
# Horizon Europe RAG System - Technical Specification

## 1. Database Schema for Supabase

### 1.1 Enable pgvector Extension
```sql
-- Run this first in Supabase SQL editor
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For text search
CREATE EXTENSION IF NOT EXISTS btree_gin; -- For compound indexes
```

### 1.2 Main Tables Schema
```sql
-- Documents table for storing source documents
CREATE TABLE horizon_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL CHECK (source_type IN ('pdf', 'web', 'cordis', 'manual')),
    source_url TEXT,
    file_path TEXT,
    title TEXT NOT NULL,
    document_type TEXT CHECK (document_type IN (
        'work_programme', 
        'programme_guide', 
        'call_text',
        'grant_agreement',
        'faq',
        'manual',
        'policy',
        'template'
    )),
    programme_year TEXT,
    programme_part TEXT, -- e.g., 'Cluster 4', 'Pillar 2'
    language TEXT DEFAULT 'en',
    version TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'processing', 'failed')),
    file_hash TEXT, -- For duplicate detection
    total_chunks INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    
    -- Indexes
    CONSTRAINT unique_file_hash UNIQUE(file_hash)
);

-- Document chunks with embeddings
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES horizon_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_hash TEXT NOT NULL, -- For duplicate detection
    content TEXT NOT NULL,
    content_length INTEGER,
    embedding vector(768), -- Google text-embedding-004 dimension
    
    -- Metadata fields
    section_title TEXT,
    page_number INTEGER,
    chapter TEXT,
    subsection TEXT,
    
    -- Search optimization
    content_tokens tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    token_count INTEGER,
    embedding_model TEXT DEFAULT 'text-embedding-004',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_chunk_per_doc UNIQUE(document_id, chunk_index),
    CONSTRAINT unique_chunk_hash UNIQUE(chunk_hash)
);

-- Search queries log for analytics
CREATE TABLE search_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT NOT NULL,
    query_embedding vector(768),
    search_type TEXT CHECK (search_type IN ('semantic', 'keyword', 'hybrid')),
    filters JSONB,
    results_count INTEGER,
    top_chunk_ids UUID[],
    response_time_ms INTEGER,
    user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document processing jobs
CREATE TABLE ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES horizon_documents(id) ON DELETE CASCADE,
    job_type TEXT CHECK (job_type IN ('pdf_extraction', 'web_scraping', 'embedding_generation', 'chunking')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    progress INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Cached embeddings for common queries
CREATE TABLE embedding_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text_hash TEXT UNIQUE NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    model_version TEXT DEFAULT 'text-embedding-004',
    usage_count INTEGER DEFAULT 1,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.3 Indexes for Performance
```sql
-- Vector similarity search indexes
CREATE INDEX idx_chunks_embedding_cosine ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Alternative HNSW index (better performance, use in production)
-- CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks 
-- USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Full-text search indexes
CREATE INDEX idx_chunks_content_gin ON document_chunks USING gin(content_tokens);
CREATE INDEX idx_documents_title_trgm ON horizon_documents USING gin(title gin_trgm_ops);

-- Metadata and filtering indexes
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_chunk_index ON document_chunks(document_id, chunk_index);
CREATE INDEX idx_documents_type ON horizon_documents(document_type);
CREATE INDEX idx_documents_year ON horizon_documents(programme_year);
CREATE INDEX idx_documents_status ON horizon_documents(status);
CREATE INDEX idx_documents_created ON horizon_documents(created_at DESC);

-- Compound indexes for common queries
CREATE INDEX idx_documents_active_type ON horizon_documents(status, document_type) 
WHERE status = 'active';
```

### 1.4 Row Level Security (RLS) Policies
```sql
-- Enable RLS
ALTER TABLE horizon_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Public read access for active documents
CREATE POLICY "Public documents are viewable by everyone" 
ON horizon_documents FOR SELECT 
USING (status = 'active');

CREATE POLICY "Public chunks are viewable by everyone" 
ON document_chunks FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM horizon_documents 
        WHERE horizon_documents.id = document_chunks.document_id 
        AND horizon_documents.status = 'active'
    )
);

-- Admin write access (using service key)
CREATE POLICY "Service role can manage all documents" 
ON horizon_documents FOR ALL 
USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage all chunks" 
ON document_chunks FOR ALL 
USING (auth.role() = 'service_role');
```

### 1.5 Functions and Stored Procedures
```sql
-- Function for semantic search with metadata filtering
CREATE OR REPLACE FUNCTION search_documents(
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_document_type TEXT DEFAULT NULL,
    filter_year TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    document_title TEXT,
    document_type TEXT,
    similarity FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id as chunk_id,
        c.document_id,
        c.content,
        d.title as document_title,
        d.document_type,
        1 - (c.embedding <=> query_embedding) as similarity,
        c.metadata
    FROM document_chunks c
    JOIN horizon_documents d ON c.document_id = d.id
    WHERE 
        d.status = 'active'
        AND (filter_document_type IS NULL OR d.document_type = filter_document_type)
        AND (filter_year IS NULL OR d.programme_year = filter_year)
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function for hybrid search (vector + keyword)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(768),
    query_text TEXT,
    match_count INT DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    document_title TEXT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT 
            c.id,
            c.document_id,
            c.content,
            1 - (c.embedding <=> query_embedding) as vector_score
        FROM document_chunks c
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    text_search AS (
        SELECT 
            c.id,
            c.document_id,
            c.content,
            ts_rank(c.content_tokens, plainto_tsquery('english', query_text)) as text_score
        FROM document_chunks c
        WHERE c.content_tokens @@ plainto_tsquery('english', query_text)
        ORDER BY text_score DESC
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT 
            COALESCE(v.id, t.id) as chunk_id,
            COALESCE(v.document_id, t.document_id) as doc_id,
            COALESCE(v.content, t.content) as content_text,
            COALESCE(v.vector_score, 0) * vector_weight + 
            COALESCE(t.text_score, 0) * (1 - vector_weight) as score
        FROM vector_search v
        FULL OUTER JOIN text_search t ON v.id = t.id
    )
    SELECT 
        combined.chunk_id,
        combined.doc_id as document_id,
        combined.content_text as content,
        d.title as document_title,
        combined.score as combined_score
    FROM combined
    JOIN horizon_documents d ON combined.doc_id = d.id
    WHERE d.status = 'active'
    ORDER BY combined.score DESC
    LIMIT match_count;
END;
$$;

-- Function to get document statistics
CREATE OR REPLACE FUNCTION get_document_stats()
RETURNS TABLE (
    total_documents BIGINT,
    total_chunks BIGINT,
    documents_by_type JSONB,
    documents_by_year JSONB,
    avg_chunks_per_document NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT d.id) as total_documents,
        COUNT(c.id) as total_chunks,
        jsonb_object_agg(
            COALESCE(d.document_type, 'unknown'), 
            doc_type_counts.count
        ) FILTER (WHERE d.document_type IS NOT NULL) as documents_by_type,
        jsonb_object_agg(
            COALESCE(d.programme_year, 'unknown'), 
            doc_year_counts.count
        ) FILTER (WHERE d.programme_year IS NOT NULL) as documents_by_year,
        AVG(d.total_chunks) as avg_chunks_per_document
    FROM horizon_documents d
    LEFT JOIN document_chunks c ON d.id = c.document_id
    LEFT JOIN LATERAL (
        SELECT document_type, COUNT(*) as count 
        FROM horizon_documents 
        GROUP BY document_type
    ) doc_type_counts ON d.document_type = doc_type_counts.document_type
    LEFT JOIN LATERAL (
        SELECT programme_year, COUNT(*) as count 
        FROM horizon_documents 
        GROUP BY programme_year
    ) doc_year_counts ON d.programme_year = doc_year_counts.programme_year
    WHERE d.status = 'active'
    GROUP BY doc_type_counts.count, doc_year_counts.count;
END;
$$;
```

## 2. Python Service Implementations

### 2.1 Supabase Client Service
```python
# app/services/supabase_client.py

import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv
import numpy as np

load_dotenv()

class SupabaseVectorStore:
    """Supabase client for vector storage and retrieval."""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Supabase credentials not found in environment")
        
        self.client: Client = create_client(self.url, self.key)
    
    def insert_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new document record."""
        response = self.client.table("horizon_documents").insert(document_data).execute()
        return response.data[0] if response.data else None
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch insert document chunks with embeddings."""
        # Convert numpy arrays to lists for JSON serialization
        for chunk in chunks:
            if isinstance(chunk.get('embedding'), np.ndarray):
                chunk['embedding'] = chunk['embedding'].tolist()
        
        response = self.client.table("document_chunks").insert(chunks).execute()
        return response.data
    
    def semantic_search(
        self,
        query_embedding: np.ndarray,
        match_threshold: float = 0.7,
        match_count: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using vector similarity."""
        embedding_list = query_embedding.tolist()
        
        params = {
            'query_embedding': embedding_list,
            'match_threshold': match_threshold,
            'match_count': match_count,
            'filter_document_type': filters.get('document_type') if filters else None,
            'filter_year': filters.get('year') if filters else None
        }
        
        response = self.client.rpc('search_documents', params).execute()
        return response.data
    
    def hybrid_search(
        self,
        query_text: str,
        query_embedding: np.ndarray,
        match_count: int = 10,
        vector_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining vector and keyword search."""
        embedding_list = query_embedding.tolist()
        
        params = {
            'query_embedding': embedding_list,
            'query_text': query_text,
            'match_count': match_count,
            'vector_weight': vector_weight
        }
        
        response = self.client.rpc('hybrid_search', params).execute()
        return response.data
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        response = self.client.table("horizon_documents")\
            .select("*")\
            .eq("id", document_id)\
            .single()\
            .execute()
        return response.data
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        response = self.client.table("document_chunks")\
            .select("*")\
            .eq("document_id", document_id)\
            .order("chunk_index")\
            .execute()
        return response.data
    
    def update_document_status(
        self, 
        document_id: str, 
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update document processing status."""
        update_data = {"status": status}
        if metadata:
            update_data["metadata"] = metadata
        
        response = self.client.table("horizon_documents")\
            .update(update_data)\
            .eq("id", document_id)\
            .execute()
        return response.data[0] if response.data else None
    
    def check_duplicate(self, file_hash: str) -> bool:
        """Check if a document with the same hash already exists."""
        response = self.client.table("horizon_documents")\
            .select("id")\
            .eq("file_hash", file_hash)\
            .execute()
        return len(response.data) > 0
    
    def get_cached_embedding(self, text_hash: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding if it exists."""
        response = self.client.table("embedding_cache")\
            .select("embedding")\
            .eq("text_hash", text_hash)\
            .single()\
            .execute()
        
        if response.data:
            # Update usage count
            self.client.table("embedding_cache")\
                .update({"usage_count": response.data.get("usage_count", 0) + 1})\
                .eq("text_hash", text_hash)\
                .execute()
            
            return np.array(response.data["embedding"])
        return None
    
    def cache_embedding(
        self, 
        text_content: str, 
        text_hash: str, 
        embedding: np.ndarray
    ) -> None:
        """Cache an embedding for future use."""
        self.client.table("embedding_cache").upsert({
            "text_hash": text_hash,
            "text_content": text_content[:1000],  # Store first 1000 chars for reference
            "embedding": embedding.tolist()
        }).execute()
```

### 2.2 Document Processor Service
```python
# app/services/document_processor.py

import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import PyPDF2
import pdfplumber
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse

class DocumentProcessor:
    """Process various document types for the RAG system."""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.html', '.txt', '.md']
    
    def process_pdf(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from PDF files."""
        text_content = ""
        metadata = {
            "page_count": 0,
            "extraction_method": "pdfplumber"
        }
        
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(file_path) as pdf:
                metadata["page_count"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n[Page {page_num}]\n{page_text}"
                
                # Extract document info
                if pdf.metadata:
                    metadata["pdf_metadata"] = {
                        k: str(v) for k, v in pdf.metadata.items()
                        if v and k in ['Title', 'Author', 'Subject', 'Creator']
                    }
        
        except Exception as e:
            # Fallback to PyPDF2
            metadata["extraction_method"] = "PyPDF2"
            metadata["extraction_error"] = str(e)
            
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    metadata["page_count"] = len(pdf_reader.pages)
                    
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        page_text = page.extract_text()
                        text_content += f"\n[Page {page_num}]\n{page_text}"
            
            except Exception as e2:
                raise Exception(f"Failed to extract PDF: {e2}")
        
        # Clean extracted text
        text_content = self.clean_text(text_content)
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        metadata["file_hash"] = file_hash
        
        return text_content, metadata
    
    def scrape_web_page(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """Scrape and extract text from web pages."""
        metadata = {
            "source_url": url,
            "extraction_method": "beautifulsoup"
        }
        
        try:
            # Fetch the page
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract metadata
            metadata["title"] = soup.find('title').text if soup.find('title') else ""
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract main content (try common content containers)
            main_content = None
            for selector in ['main', 'article', '.content', '#content', 'div.main']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            # Extract text
            text_content = main_content.get_text() if main_content else ""
            
            # Clean text
            text_content = self.clean_text(text_content)
            
            # Extract links for potential crawling
            links = []
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(url, link['href'])
                if self.is_valid_url(absolute_url):
                    links.append(absolute_url)
            
            metadata["links_found"] = len(links)
            metadata["links"] = links[:20]  # Store first 20 links
            
        except Exception as e:
            raise Exception(f"Failed to scrape web page: {e}")
        
        return text_content, metadata
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\@\#\$\%\&\*\+\=]', '', text)
        
        # Fix common OCR errors
        replacements = {
            'ﬁ': 'fi',
            'ﬂ': 'fl',
            'ﬀ': 'ff',
            'ﬃ': 'ffi',
            'ﬄ': 'ffl',
            '–': '-',
            '—': '-',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        return text.strip()
    
    def extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Extract sections and subsections from document text."""
        sections = []
        
        # Common section patterns
        patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^(\d+\.)+\s+(.+)$',  # Numbered sections
            r'^[A-Z][A-Z\s]+$',  # All caps headers
            r'^\[Page \d+\]$',  # Page markers
        ]
        
        lines = text.split('\n')
        current_section = {"title": "Introduction", "content": ""}
        
        for line in lines:
            is_header = False
            
            for pattern in patterns:
                if re.match(pattern, line.strip()):
                    # Save previous section
                    if current_section["content"]:
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = {
                        "title": line.strip(),
                        "content": ""
                    }
                    is_header = True
                    break
            
            if not is_header:
                current_section["content"] += line + "\n"
        
        # Add last section
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and should be crawled."""
        try:
            parsed = urlparse(url)
            
            # Check if it's a valid HTTP/HTTPS URL
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check if it's from allowed domains
            allowed_domains = [
                'europa.eu',
                'ec.europa.eu',
                'cordis.europa.eu',
                'research-and-innovation.ec.europa.eu'
            ]
            
            return any(domain in parsed.netloc for domain in allowed_domains)
        
        except:
            return False
    
    def calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

### 2.3 Chunking Service
```python
# app/services/chunking_service.py

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken

@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    chunk_size: int = 1000  # tokens
    chunk_overlap: int = 200  # tokens
    min_chunk_size: int = 100  # tokens
    max_chunk_size: int = 1500  # tokens
    respect_sentence_boundary: bool = True
    respect_paragraph_boundary: bool = True

class TextChunker:
    """Smart text chunking for optimal retrieval."""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        # Use tiktoken for accurate token counting
        self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def chunk_text(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Chunk text into overlapping segments."""
        chunks = []
        
        # Split into paragraphs first
        paragraphs = self.split_into_paragraphs(text)
        
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # If paragraph is too large, split it
            if para_tokens > self.config.chunk_size:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append(self.create_chunk(
                        current_chunk, chunk_index, current_tokens, metadata
                    ))
                    chunk_index += 1
                
                # Split large paragraph
                para_chunks = self.split_large_paragraph(para)
                for pc in para_chunks:
                    chunks.append(self.create_chunk(
                        pc, chunk_index, self.count_tokens(pc), metadata
                    ))
                    chunk_index += 1
                
                current_chunk = ""
                current_tokens = 0
            
            # If adding paragraph exceeds chunk size
            elif current_tokens + para_tokens > self.config.chunk_size:
                # Save current chunk
                chunks.append(self.create_chunk(
                    current_chunk, chunk_index, current_tokens, metadata
                ))
                chunk_index += 1
                
                # Start new chunk with overlap
                if self.config.chunk_overlap > 0 and current_chunk:
                    overlap_text = self.get_overlap_text(current_chunk)
                    current_chunk = overlap_text + "\n\n" + para
                    current_tokens = self.count_tokens(current_chunk)
                else:
                    current_chunk = para
                    current_tokens = para_tokens
            
            # Add paragraph to current chunk
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk and current_tokens >= self.config.min_chunk_size:
            chunks.append(self.create_chunk(
                current_chunk, chunk_index, current_tokens, metadata
            ))
        
        return chunks
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines or common paragraph markers
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean and filter paragraphs
        cleaned = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 20:  # Minimum paragraph length
                cleaned.append(para)
        
        return cleaned
    
    def split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a large paragraph into smaller chunks."""
        sentences = self.split_into_sentences(paragraph)
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.config.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (can be improved with spaCy or NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def get_overlap_text(self, chunk: str) -> str:
        """Get the overlap text from the end of a chunk."""
        tokens = self.encoder.encode(chunk)
        
        if len(tokens) <= self.config.chunk_overlap:
            return chunk
        
        # Get last N tokens for overlap
        overlap_tokens = tokens[-self.config.chunk_overlap:]
        return self.encoder.decode(overlap_tokens)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
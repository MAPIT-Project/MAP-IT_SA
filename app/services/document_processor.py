"""
Document processor service for extracting text from various document types.
"""

import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import pdfplumber
import PyPDF2
import requests
from bs4 import BeautifulSoup

from ..core.config import settings

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process various document types for the RAG system."""
    
    def __init__(self):
        """Initialize the document processor."""
        self.supported_formats = settings.supported_file_types
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
        
        # Common EU domain patterns for web scraping
        self.allowed_domains = [
            'europa.eu',
            'ec.europa.eu',
            'cordis.europa.eu',
            'research-and-innovation.ec.europa.eu'
        ]
        
        logger.info(f"✅ Document processor initialized. Supported formats: {self.supported_formats}")
    
    def process_file(self, file_path: str, document_type: str | None = None) -> tuple[str, dict[str, Any]]:
        """Process a file and extract text content and metadata."""
        file_path = Path(file_path)
        
        # Validate file
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.stat().st_size > self.max_file_size:
            raise ValueError(f"File too large: {file_path.stat().st_size} bytes > {self.max_file_size} bytes")
        
        file_extension = file_path.suffix.lower()
        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        logger.info(f"📄 Processing file: {file_path.name} ({file_extension})")
        
        # Route to appropriate processor
        if file_extension == '.pdf':
            return self.process_pdf(str(file_path), document_type)
        elif file_extension in ['.txt', '.md']:
            return self.process_text_file(str(file_path), document_type)
        elif file_extension == '.html':
            return self.process_html_file(str(file_path), document_type)
        else:
            raise ValueError(f"No processor available for: {file_extension}")
    
    def process_pdf(self, file_path: str, document_type: str | None = None) -> tuple[str, dict[str, Any]]:
        """Extract text and metadata from PDF files."""
        text_content = ""
        metadata = {
            "page_count": 0,
            "extraction_method": "pdfplumber",
            "document_type": document_type or "unknown",
            "file_size": Path(file_path).stat().st_size
        }
        
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(file_path) as pdf:
                metadata["page_count"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        # Add page marker for better chunking
                        text_content += f"\n\n[Page {page_num}]\n{page_text}"
                
                # Extract document info from PDF metadata
                if pdf.metadata:
                    pdf_metadata = {}
                    for key, value in pdf.metadata.items():
                        if value and key in ['Title', 'Author', 'Subject', 'Creator', 'Producer']:
                            pdf_metadata[key.lower()] = str(value)
                    
                    if pdf_metadata:
                        metadata["pdf_metadata"] = pdf_metadata
                        
                        # Use PDF title if available and no document type specified
                        if not document_type and 'title' in pdf_metadata:
                            metadata["extracted_title"] = pdf_metadata['title']
        
        except Exception as e:
            # Fallback to PyPDF2
            logger.warning(f"⚠️ pdfplumber failed, trying PyPDF2: {e}")
            metadata["extraction_method"] = "PyPDF2"
            metadata["extraction_warning"] = str(e)
            
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    metadata["page_count"] = len(pdf_reader.pages)
                    
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n\n[Page {page_num}]\n{page_text}"
                    
                    # Extract metadata from PyPDF2
                    if pdf_reader.metadata:
                        pdf_metadata = {}
                        for key, value in pdf_reader.metadata.items():
                            if value:
                                clean_key = key.replace('/', '').lower()
                                pdf_metadata[clean_key] = str(value)
                        
                        if pdf_metadata:
                            metadata["pdf_metadata"] = pdf_metadata
            
            except Exception as e2:
                logger.error(f"❌ Both PDF extraction methods failed: {e2}")
                raise Exception(f"Failed to extract PDF: {e2}")
        
        # Clean extracted text
        text_content = self.clean_text(text_content)
        
        if not text_content.strip():
            raise ValueError("No text content extracted from PDF")
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        metadata["file_hash"] = file_hash
        metadata["extraction_date"] = datetime.now(UTC).isoformat()
        metadata["content_length"] = len(text_content)
        
        logger.info(f"✅ PDF processed: {metadata['page_count']} pages, {len(text_content)} chars")
        
        return text_content, metadata
    
    def process_text_file(self, file_path: str, document_type: str | None = None) -> tuple[str, dict[str, Any]]:
        """Process plain text or markdown files."""
        try:
            with open(file_path, encoding='utf-8') as f:
                text_content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, encoding='latin-1') as f:
                text_content = f.read()
        
        # Clean text
        text_content = self.clean_text(text_content)
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        metadata = {
            "document_type": document_type or "text",
            "file_size": Path(file_path).stat().st_size,
            "file_hash": file_hash,
            "extraction_method": "direct_read",
            "extraction_date": datetime.now(UTC).isoformat(),
            "content_length": len(text_content)
        }
        
        logger.info(f"✅ Text file processed: {len(text_content)} chars")
        
        return text_content, metadata
    
    def process_html_file(self, file_path: str, document_type: str | None = None) -> tuple[str, dict[str, Any]]:
        """Process HTML files."""
        with open(file_path, encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract metadata
        title = soup.find('title')
        title_text = title.text.strip() if title else ""
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text content
        text_content = soup.get_text()
        text_content = self.clean_text(text_content)
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        metadata = {
            "document_type": document_type or "html",
            "file_size": Path(file_path).stat().st_size,
            "file_hash": file_hash,
            "extraction_method": "beautifulsoup",
            "extraction_date": datetime.now(UTC).isoformat(),
            "content_length": len(text_content),
            "html_title": title_text
        }
        
        logger.info(f"✅ HTML file processed: {len(text_content)} chars")
        
        return text_content, metadata
    
    def scrape_web_page(self, url: str, document_type: str | None = None) -> tuple[str, dict[str, Any]]:
        """Scrape and extract text from web pages."""
        if not self.is_valid_url(url):
            raise ValueError(f"URL not allowed for scraping: {url}")
        
        metadata = {
            "source_url": url,
            "extraction_method": "web_scraping",
            "document_type": document_type or "web",
            "extraction_date": datetime.now(UTC).isoformat()
        }
        
        try:
            # Fetch the page with proper headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; HorizonEuropeRAG/1.0; +https://example.com/bot)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            metadata["status_code"] = response.status_code
            metadata["content_type"] = response.headers.get('content-type', '')
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract metadata
            title = soup.find('title')
            metadata["page_title"] = title.text.strip() if title else ""
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                metadata["meta_description"] = meta_desc.get('content', '')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Try to find main content area
            main_content = None
            for selector in ['main', 'article', '.content', '#content', '.main-content', 'div.main']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            # Extract text
            text_content = main_content.get_text() if main_content else ""
            
            # Clean text
            text_content = self.clean_text(text_content)
            
            if not text_content.strip():
                raise ValueError("No text content extracted from web page")
            
            # Extract links for potential crawling
            links = []
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(url, link['href'])
                if self.is_valid_url(absolute_url):
                    links.append({
                        'url': absolute_url,
                        'text': link.get_text().strip()[:100]  # First 100 chars of link text
                    })
            
            metadata["links_found"] = len(links)
            metadata["links"] = links[:20]  # Store first 20 links
            metadata["content_length"] = len(text_content)
            
            # Calculate content hash
            content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
            metadata["content_hash"] = content_hash
            
            logger.info(f"✅ Web page scraped: {url} ({len(text_content)} chars)")
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to fetch web page {url}: {e}")
            raise Exception(f"Failed to scrape web page: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to process web page {url}: {e}")
            raise Exception(f"Failed to process web page: {e}")
        
        return text_content, metadata
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\@\#\$\%\&\*\+\=\€\£\¥]', '', text)
        
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
            '…': '...',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove multiple spaces and normalize whitespace
        text = ' '.join(text.split())
        
        # Remove page markers that are too close together (likely OCR artifacts)
        text = re.sub(r'\[Page \d+\]\s*\[Page \d+\]', '[Page]', text)
        
        return text.strip()
    
    def extract_sections(self, text: str) -> list[dict[str, str]]:
        """Extract sections and subsections from document text."""
        sections = []
        
        # Common section patterns for EU documents
        patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^(\d+\.)+\s+(.+)$',  # Numbered sections (1.1, 1.1.1, etc.)
            r'^[A-Z][A-Z\s]{3,}$',  # All caps headers (minimum 4 chars)
            r'^\[Page \d+\]$',  # Page markers
            r'^(CHAPTER|SECTION|PART|ARTICLE)\s+\d+',  # Legal document sections
            r'^(Introduction|Conclusion|Summary|Abstract|Overview)$',  # Common section names
        ]
        
        lines = text.split('\n')
        current_section = {"title": "Introduction", "content": "", "level": 0}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            is_header = False
            header_level = 0
            
            for i, pattern in enumerate(patterns):
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous section if it has content
                    if current_section["content"].strip():
                        sections.append(current_section)
                    
                    # Determine header level
                    if i == 0:  # Markdown headers
                        header_level = len(line) - len(line.lstrip('#'))
                    elif i == 1:  # Numbered sections
                        header_level = line.count('.')
                    else:
                        header_level = 1
                    
                    # Start new section
                    current_section = {
                        "title": line,
                        "content": "",
                        "level": header_level
                    }
                    is_header = True
                    break
            
            if not is_header:
                current_section["content"] += line + "\n"
        
        # Add last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        # Filter out very short sections (likely OCR artifacts)
        filtered_sections = []
        for section in sections:
            if len(section["content"].strip()) > 50:  # Minimum 50 characters
                filtered_sections.append(section)
        
        logger.info(f"✅ Extracted {len(filtered_sections)} sections from document")
        
        return filtered_sections
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and should be crawled."""
        try:
            parsed = urlparse(url)
            
            # Check if it's a valid HTTP/HTTPS URL
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check if it's from allowed domains
            return any(domain in parsed.netloc for domain in self.allowed_domains)
        
        except Exception:
            return False
    
    def calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_file_info(self, file_path: str) -> dict[str, Any]:
        """Get basic file information without processing."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = file_path.stat()
        
        return {
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_supported": file_path.suffix.lower() in self.supported_formats,
            "is_valid_size": stat.st_size <= self.max_file_size
        }
"""
Text chunking service for optimal document segmentation.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import tiktoken

from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    chunk_size: int = 1000  # tokens
    chunk_overlap: int = 200  # tokens
    min_chunk_size: int = 100  # tokens
    max_chunk_size: int = 1500  # tokens
    respect_sentence_boundary: bool = True
    respect_paragraph_boundary: bool = True
    preserve_section_headers: bool = True

class TextChunker:
    """Smart text chunking for optimal retrieval."""
    
    def __init__(self, config: ChunkConfig | None = None):
        """Initialize the text chunker."""
        self.config = config or ChunkConfig(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        # Use tiktoken for accurate token counting
        try:
            self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception as e:
            logger.warning(f"⚠️ Could not load tiktoken encoder: {e}. Using fallback.")
            self.encoder = None
        
        logger.info(f"✅ Text chunker initialized with chunk_size={self.config.chunk_size}, overlap={self.config.chunk_overlap}")
    
    def chunk_text(
        self, 
        text: str, 
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Chunk text into overlapping segments with metadata."""
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for chunking")
            return []
        
        logger.info(f"📝 Chunking text: {len(text)} characters")
        
        # Extract sections if the text has clear structure
        sections = self._extract_document_sections(text)
        
        if len(sections) > 1:
            logger.info(f"📋 Found {len(sections)} sections, using section-aware chunking")
            chunks = self._chunk_by_sections(sections, metadata, document_id)
        else:
            logger.info("📄 No clear sections found, using paragraph-based chunking")
            chunks = self._chunk_by_paragraphs(text, metadata, document_id)
        
        # Post-process chunks
        chunks = self._post_process_chunks(chunks)
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        return chunks
    
    def _extract_document_sections(self, text: str) -> list[dict[str, str]]:
        """Extract document sections with headers."""
        sections = []
        
        # Patterns for section headers (EU document specific)
        header_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^(\d+\.)+\s+(.+)$',  # Numbered sections (1.1, 1.1.1, etc.)
            r'^[A-Z][A-Z\s]{3,50}$',  # All caps headers
            r'^(CHAPTER|SECTION|PART|ARTICLE|ANNEX)\s+[IVX\d]+',  # Legal document sections
            r'^\[Page \d+\]$',  # Page markers
            r'^(Introduction|Background|Objectives?|Scope|Methodology|Results?|Conclusions?|References?|Appendix|Summary|Abstract|Overview)$',
        ]
        
        lines = text.split('\n')
        current_section = {
            "title": "Document Start",
            "content": "",
            "level": 0,
            "start_line": 0
        }
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                current_section["content"] += "\n"
                continue
            
            is_header = False
            header_level = 0
            
            for i, pattern in enumerate(header_patterns):
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous section if it has substantial content
                    if len(current_section["content"].strip()) > 50:
                        sections.append(current_section)
                    
                    # Determine header level
                    if i == 0:  # Markdown headers
                        header_level = len(line) - len(line.lstrip('#'))
                    elif i == 1:  # Numbered sections
                        header_level = line.count('.')
                    elif i in [2, 3]:  # Caps headers and legal sections
                        header_level = 1
                    else:
                        header_level = 2
                    
                    # Start new section
                    current_section = {
                        "title": line,
                        "content": "",
                        "level": header_level,
                        "start_line": line_num
                    }
                    is_header = True
                    break
            
            if not is_header:
                current_section["content"] += line + "\n"
        
        # Add last section
        if len(current_section["content"].strip()) > 50:
            sections.append(current_section)
        
        # If we only found one section, return empty list to use paragraph chunking
        if len(sections) <= 1:
            return []
        
        return sections
    
    def _chunk_by_sections(
        self, 
        sections: list[dict[str, str]], 
        metadata: dict[str, Any] | None, 
        document_id: str | None
    ) -> list[dict[str, Any]]:
        """Chunk text using document sections as boundaries."""
        chunks = []
        chunk_index = 0
        
        for section in sections:
            section_title = section["title"]
            section_content = section["content"].strip()
            
            if not section_content:
                continue
            
            # If section is small enough, keep it as one chunk
            section_tokens = self.count_tokens(section_content)
            
            if section_tokens <= self.config.chunk_size:
                chunk = self._create_chunk(
                    content=section_content,
                    chunk_index=chunk_index,
                    token_count=section_tokens,
                    metadata=metadata,
                    document_id=document_id,
                    section_title=section_title
                )
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Split large section into smaller chunks
                section_chunks = self._split_large_text(
                    section_content, 
                    section_title,
                    chunk_index,
                    metadata,
                    document_id
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
        
        return chunks
    
    def _chunk_by_paragraphs(
        self, 
        text: str, 
        metadata: dict[str, Any] | None, 
        document_id: str | None
    ) -> list[dict[str, Any]]:
        """Chunk text using paragraph boundaries."""
        paragraphs = self._split_into_paragraphs(text)
        chunks = []
        
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # If paragraph is too large, split it
            if para_tokens > self.config.chunk_size:
                # Save current chunk if it exists
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        content=current_chunk,
                        chunk_index=chunk_index,
                        token_count=current_tokens,
                        metadata=metadata,
                        document_id=document_id
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Split large paragraph
                para_chunks = self._split_large_text(
                    para, 
                    None,
                    chunk_index,
                    metadata,
                    document_id
                )
                chunks.extend(para_chunks)
                chunk_index += len(para_chunks)
                
                current_chunk = ""
                current_tokens = 0
            
            # If adding paragraph exceeds chunk size
            elif current_tokens + para_tokens > self.config.chunk_size:
                # Save current chunk
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        content=current_chunk,
                        chunk_index=chunk_index,
                        token_count=current_tokens,
                        metadata=metadata,
                        document_id=document_id
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                if self.config.chunk_overlap > 0 and current_chunk.strip():
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + "\n\n" + para
                    current_tokens = self.count_tokens(current_chunk)
                else:
                    current_chunk = para
                    current_tokens = para_tokens
            
            # Add paragraph to current chunk
            else:
                if current_chunk.strip():
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk.strip() and current_tokens >= self.config.min_chunk_size:
            chunk = self._create_chunk(
                content=current_chunk,
                chunk_index=chunk_index,
                token_count=current_tokens,
                metadata=metadata,
                document_id=document_id
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_large_text(
        self, 
        text: str, 
        section_title: str | None,
        start_index: int,
        metadata: dict[str, Any] | None, 
        document_id: str | None
    ) -> list[dict[str, Any]]:
        """Split large text into smaller chunks."""
        sentences = self._split_into_sentences(text)
        chunks = []
        
        current_chunk = ""
        current_tokens = 0
        chunk_index = start_index
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If single sentence is too large, split by words
            if sentence_tokens > self.config.chunk_size:
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        content=current_chunk,
                        chunk_index=chunk_index,
                        token_count=current_tokens,
                        metadata=metadata,
                        document_id=document_id,
                        section_title=section_title
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Split by words
                word_chunks = self._split_by_words(sentence, chunk_index, metadata, document_id, section_title)
                chunks.extend(word_chunks)
                chunk_index += len(word_chunks)
                
                current_chunk = ""
                current_tokens = 0
                continue
            
            # If adding sentence exceeds chunk size
            if current_tokens + sentence_tokens > self.config.chunk_size:
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        content=current_chunk,
                        chunk_index=chunk_index,
                        token_count=current_tokens,
                        metadata=metadata,
                        document_id=document_id,
                        section_title=section_title
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                if self.config.chunk_overlap > 0 and current_chunk.strip():
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + " " + sentence
                    current_tokens = self.count_tokens(current_chunk)
                else:
                    current_chunk = sentence
                    current_tokens = sentence_tokens
            else:
                if current_chunk.strip():
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk.strip() and current_tokens >= self.config.min_chunk_size:
            chunk = self._create_chunk(
                content=current_chunk,
                chunk_index=chunk_index,
                token_count=current_tokens,
                metadata=metadata,
                document_id=document_id,
                section_title=section_title
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_by_words(
        self, 
        text: str, 
        start_index: int,
        metadata: dict[str, Any] | None, 
        document_id: str | None,
        section_title: str | None
    ) -> list[dict[str, Any]]:
        """Split text by words when sentences are too large."""
        words = text.split()
        chunks = []
        
        current_chunk = ""
        chunk_index = start_index
        
        for word in words:
            test_chunk = current_chunk + " " + word if current_chunk else word
            
            if self.count_tokens(test_chunk) > self.config.chunk_size:
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        content=current_chunk,
                        chunk_index=chunk_index,
                        token_count=self.count_tokens(current_chunk),
                        metadata=metadata,
                        document_id=document_id,
                        section_title=section_title
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                current_chunk = word
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunk = self._create_chunk(
                content=current_chunk,
                chunk_index=chunk_index,
                token_count=self.count_tokens(current_chunk),
                metadata=metadata,
                document_id=document_id,
                section_title=section_title
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> list[str]:
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
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Enhanced sentence splitting for EU documents
        # Handle common abbreviations that shouldn't trigger sentence breaks
        abbreviations = ['Dr.', 'Prof.', 'Mr.', 'Mrs.', 'Ms.', 'vs.', 'etc.', 'i.e.', 'e.g.', 'cf.', 'Art.', 'No.', 'Vol.']
        
        # Temporarily replace abbreviations
        temp_text = text
        for i, abbr in enumerate(abbreviations):
            temp_text = temp_text.replace(abbr, f"__ABBR_{i}__")
        
        # Split by sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', temp_text)
        
        # Restore abbreviations
        for i, abbr in enumerate(abbreviations):
            sentences = [s.replace(f"__ABBR_{i}__", abbr) for s in sentences]
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, chunk: str) -> str:
        """Get the overlap text from the end of a chunk."""
        if not self.encoder:
            # Fallback: use last N words
            words = chunk.split()
            overlap_words = min(len(words), self.config.chunk_overlap // 4)  # Rough estimate
            return " ".join(words[-overlap_words:])
        
        tokens = self.encoder.encode(chunk)
        
        if len(tokens) <= self.config.chunk_overlap:
            return chunk
        
        # Get last N tokens for overlap
        overlap_tokens = tokens[-self.config.chunk_overlap:]
        return self.encoder.decode(overlap_tokens)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0
        
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"⚠️ Token counting failed: {e}")
        
        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4
    
    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        token_count: int,
        metadata: dict[str, Any] | None,
        document_id: str | None,
        section_title: str | None = None,
        page_number: int | None = None
    ) -> dict[str, Any]:
        """Create a chunk dictionary with all metadata."""
        # Extract page number from content if present
        if page_number is None:
            page_match = re.search(r'\[Page (\d+)\]', content)
            if page_match:
                page_number = int(page_match.group(1))
        
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        chunk = {
            'document_id': document_id,
            'chunk_index': chunk_index,
            'chunk_hash': content_hash,
            'content': content.strip(),
            'content_length': len(content),
            'token_count': token_count,
            'section_title': section_title,
            'page_number': page_number,
            'metadata': metadata or {}
        }
        
        # Add chunking metadata
        chunk['metadata'].update({
            'chunk_method': 'smart_chunking',
            'chunk_config': {
                'chunk_size': self.config.chunk_size,
                'chunk_overlap': self.config.chunk_overlap
            },
            'created_at': datetime.now(UTC).isoformat()
        })
        
        return chunk
    
    def _post_process_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Post-process chunks to improve quality."""
        if not chunks:
            return chunks
        
        processed_chunks = []
        
        for chunk in chunks:
            content = chunk['content']
            
            # Skip chunks that are too short
            if len(content.strip()) < self.config.min_chunk_size // 4:  # Character-based minimum
                logger.debug(f"⚠️ Skipping short chunk: {len(content)} chars")
                continue
            
            # Clean up content
            content = self._clean_chunk_content(content)
            chunk['content'] = content
            chunk['content_length'] = len(content)
            
            # Recalculate token count after cleaning
            chunk['token_count'] = self.count_tokens(content)
            
            processed_chunks.append(chunk)
        
        # Renumber chunks after filtering
        for i, chunk in enumerate(processed_chunks):
            chunk['chunk_index'] = i
        
        return processed_chunks
    
    def _clean_chunk_content(self, content: str) -> str:
        """Clean chunk content."""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove page markers if they're at the beginning
        content = re.sub(r'^\[Page \d+\]\s*', '', content)
        
        # Ensure content doesn't start or end with punctuation artifacts
        content = content.strip(' .,;:-')
        
        return content.strip()
    
    def get_chunking_stats(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Get statistics about the chunking results."""
        if not chunks:
            return {}
        
        token_counts = [chunk['token_count'] for chunk in chunks]
        content_lengths = [chunk['content_length'] for chunk in chunks]
        
        stats = {
            'total_chunks': len(chunks),
            'avg_tokens_per_chunk': sum(token_counts) / len(token_counts),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'avg_chars_per_chunk': sum(content_lengths) / len(content_lengths),
            'total_tokens': sum(token_counts),
            'total_characters': sum(content_lengths),
            'chunks_with_sections': len([c for c in chunks if c.get('section_title')]),
            'chunks_with_pages': len([c for c in chunks if c.get('page_number')])
        }
        
        return stats
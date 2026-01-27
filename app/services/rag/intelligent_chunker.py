import hashlib
import re
from dataclasses import dataclass
from typing import Any

# Optional imports with fallbacks
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
except:
    pass

@dataclass
class DocumentChunk:
    """Represents a document chunk with metadata"""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: dict[str, Any]
    embedding: list[float] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'content': self.content,
            'chunk_index': self.chunk_index,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'token_count': self.token_count,
            'metadata': self.metadata,
            'embedding': self.embedding
        }

class IntelligentChunker:
    """
    Advanced document chunking with semantic awareness.
    Implements overlapping chunks with metadata preservation.
    """
    
    def __init__(self,
                 chunk_size: int = 800,  # Increased from 500 for better context
                 chunk_overlap: int = 200,  # Increased from 100 for better context preservation
                 min_chunk_size: int = 300,  # Increased from 200 to prevent fragmentation
                 max_chunk_size: int = 1200):  # Increased from 800 for more complete sections
        """
        Initialize intelligent chunker.
        
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            min_chunk_size: Minimum acceptable chunk size
            max_chunk_size: Maximum acceptable chunk size
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # Initialize tokenizer for accurate token counting
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except:
                self.tokenizer = None
        else:
            self.tokenizer = None
        
        # Initialize text splitter with semantic awareness
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size * 4,  # Approximate chars (1 token ≈ 4 chars)
                chunk_overlap=chunk_overlap * 4,
                separators=["\n\n", "\n", ". ", " ", ""],
                length_function=self._token_length
            )
        else:
            self.text_splitter = None
    
    def chunk_document(self,
                      document: dict[str, Any],
                      chunking_strategy: str = "semantic") -> list[DocumentChunk]:
        """
        Chunk a document using specified strategy.
        
        Args:
            document: Document dictionary with 'content' and 'metadata'
            chunking_strategy: One of 'semantic', 'fixed', 'sentence'
            
        Returns:
            List of DocumentChunk objects
        """
        content = document.get('content', '')
        metadata = document.get('metadata', {})
        document_id = document.get('id', self._generate_doc_id(content))
        
        if not content:
            return []
        
        # Choose chunking strategy
        if chunking_strategy == "semantic":
            chunks = self._semantic_chunking(content)
        elif chunking_strategy == "sentence":
            chunks = self._sentence_chunking(content)
        else:
            chunks = self._fixed_chunking(content)
        
        # Create DocumentChunk objects with metadata
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = self._generate_chunk_id(document_id, i, chunk_text)
            
            # Find character positions
            start_char = content.find(chunk_text)
            end_char = start_char + len(chunk_text) if start_char != -1 else len(chunk_text)
            
            # Create chunk with enriched metadata
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                content=chunk_text,
                chunk_index=i,
                start_char=start_char,
                end_char=end_char,
                token_count=self._token_length(chunk_text),
                metadata=self._enrich_metadata(metadata, chunk_text, i)
            )
            
            document_chunks.append(chunk)
        
        return document_chunks
    
    def _semantic_chunking(self, text: str) -> list[str]:
        """
        Semantic chunking that respects document structure.
        Tries to keep related content together.
        """
        # First, try to identify document sections
        sections = self._identify_sections(text)
        
        all_chunks = []
        for section in sections:
            # If section is small enough, keep it as one chunk
            if self._token_length(section['content']) <= self.chunk_size:
                all_chunks.append(section['content'])
            else:
                # Split large sections semantically
                section_chunks = self._split_semantic_section(section['content'])
                all_chunks.extend(section_chunks)
        
        # Apply overlap between chunks
        overlapped_chunks = self._apply_overlap(all_chunks)
        
        return overlapped_chunks
    
    def _identify_sections(self, text: str) -> list[dict[str, str]]:
        """
        Identify logical sections in document.
        Looks for headers, bullet points, paragraphs.
        """
        sections = []
        
        # Pattern for common section markers
        section_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^(\d+\.?\s+.+)$',   # Numbered sections
            r'^([A-Z][^.!?]*[.!?])$',  # Sentences starting with capital
            r'^(\*\s+.+)$',       # Bullet points
            r'^(-\s+.+)$',        # Dash lists
        ]
        
        lines = text.split('\n')
        current_section = {'title': '', 'content': ''}
        
        for line in lines:
            # Check if line starts a new section
            is_section_start = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    is_section_start = True
                    break
            
            if is_section_start and current_section['content']:
                # Save current section and start new one
                sections.append(current_section)
                current_section = {'title': line.strip(), 'content': line}
            else:
                # Add to current section
                current_section['content'] += '\n' + line if current_section['content'] else line
        
        # Add final section
        if current_section['content']:
            sections.append(current_section)
        
        # If no sections identified, treat as single section
        if not sections:
            sections = [{'title': 'Document', 'content': text}]
        
        return sections
    
    def _split_semantic_section(self, text: str) -> list[str]:
        """
        Split a section into semantic chunks.
        Tries to keep sentences and paragraphs together.
        """
        # Use RecursiveCharacterTextSplitter for semantic splitting
        chunks = self.text_splitter.split_text(text)
        
        # Validate and adjust chunk sizes
        validated_chunks = []
        for chunk in chunks:
            token_count = self._token_length(chunk)
            
            if token_count < self.min_chunk_size and validated_chunks:
                # Merge with previous chunk if too small
                validated_chunks[-1] += ' ' + chunk
            elif token_count > self.max_chunk_size:
                # Split if too large
                sub_chunks = self._split_large_chunk(chunk)
                validated_chunks.extend(sub_chunks)
            else:
                validated_chunks.append(chunk)
        
        return validated_chunks
    
    def _sentence_chunking(self, text: str) -> list[str]:
        """
        Chunk by sentences, grouping them to reach target size.
        """
        if NLTK_AVAILABLE:
            try:
                sentences = sent_tokenize(text)
            except:
                sentences = text.split('. ')
        else:
            sentences = text.split('. ')
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._token_length(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append(' '.join(current_chunk))
                
                # Add overlap from end of current chunk
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_tokens = sum(self._token_length(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _fixed_chunking(self, text: str) -> list[str]:
        """
        Simple fixed-size chunking with overlap.
        """
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            chunks = []
            
            start = 0
            while start < len(tokens):
                end = min(start + self.chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)
                
                # Move start position (with overlap)
                start += self.chunk_size - self.chunk_overlap
            
            return chunks
        else:
            # Fallback to character-based chunking
            chunk_chars = self.chunk_size * 4
            overlap_chars = self.chunk_overlap * 4
            
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + chunk_chars, len(text))
                chunk_text = text[start:end]
                chunks.append(chunk_text)
                start += chunk_chars - overlap_chars
            
            return chunks
    
    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """
        Apply overlap between consecutive chunks.
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk: add overlap from next
                if i + 1 < len(chunks):
                    overlap_text = self._get_overlap_text(chunks[i + 1], from_start=True)
                    overlapped.append(chunk + '\n' + overlap_text)
                else:
                    overlapped.append(chunk)
            elif i == len(chunks) - 1:
                # Last chunk: add overlap from previous
                overlap_text = self._get_overlap_text(chunks[i - 1], from_start=False)
                overlapped.append(overlap_text + '\n' + chunk)
            else:
                # Middle chunks: add overlap from both sides
                prev_overlap = self._get_overlap_text(chunks[i - 1], from_start=False)
                next_overlap = self._get_overlap_text(chunks[i + 1], from_start=True)
                overlapped.append(prev_overlap + '\n' + chunk + '\n' + next_overlap)
        
        return overlapped
    
    def _get_overlap_text(self, text: str, from_start: bool = True) -> str:
        """
        Extract overlap text from chunk.
        """
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            overlap_tokens = self.chunk_overlap
            
            if from_start:
                overlap = tokens[:overlap_tokens]
            else:
                overlap = tokens[-overlap_tokens:]
            
            return self.tokenizer.decode(overlap)
        else:
            # Fallback to character-based
            overlap_chars = self.chunk_overlap * 4
            if from_start:
                return text[:overlap_chars]
            else:
                return text[-overlap_chars:]
    
    def _get_overlap_sentences(self, sentences: list[str]) -> list[str]:
        """
        Get sentences for overlap (last few sentences).
        """
        if not sentences:
            return []
        
        total_tokens = 0
        overlap_sentences = []
        
        for sentence in reversed(sentences):
            sentence_tokens = self._token_length(sentence)
            if total_tokens + sentence_tokens <= self.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                total_tokens += sentence_tokens
            else:
                break
        
        return overlap_sentences
    
    def _split_large_chunk(self, text: str) -> list[str]:
        """
        Split a chunk that exceeds max size.
        """
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            sub_chunks = []
            
            for i in range(0, len(tokens), self.chunk_size):
                sub_chunk_tokens = tokens[i:i + self.chunk_size]
                sub_chunk_text = self.tokenizer.decode(sub_chunk_tokens)
                sub_chunks.append(sub_chunk_text)
            
            return sub_chunks
        else:
            # Fallback to character-based
            chunk_chars = self.chunk_size * 4
            sub_chunks = []
            
            for i in range(0, len(text), chunk_chars):
                sub_chunk = text[i:i + chunk_chars]
                sub_chunks.append(sub_chunk)
            
            return sub_chunks
    
    def _token_length(self, text: str) -> int:
        """
        Calculate token count for text.
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough estimation: 1 token ≈ 4 characters
            return len(text) // 4
    
    def _generate_doc_id(self, content: str) -> str:
        """
        Generate unique document ID from content.
        """
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_chunk_id(self, doc_id: str, index: int, content: str) -> str:
        """
        Generate unique chunk ID.
        """
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{doc_id}_chunk_{index}_{content_hash}"
    
    def _enrich_metadata(self, 
                        base_metadata: dict[str, Any],
                        chunk_content: str,
                        chunk_index: int) -> dict[str, Any]:
        """
        Enrich chunk metadata with additional information.
        """
        metadata = base_metadata.copy()
        
        # Add chunk-specific metadata
        metadata['chunk_index'] = chunk_index
        metadata['chunk_length'] = len(chunk_content)
        metadata['chunk_tokens'] = self._token_length(chunk_content)
        
        # Extract potential keywords (simple approach)
        try:
            words = word_tokenize(chunk_content.lower())
        except:
            words = chunk_content.lower().split()
            
        word_freq = {}
        for word in words:
            if len(word) > 4 and word.isalpha():
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Top 5 keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        metadata['keywords'] = [k[0] for k in keywords]
        
        # Detect chunk type (heuristic)
        content_lower = chunk_content.lower()
        if any(indicator in content_lower for indicator in ['objective', 'goal', 'aim']):
            metadata['chunk_type'] = 'objective'
        elif any(indicator in content_lower for indicator in ['budget', 'cost', 'funding']):
            metadata['chunk_type'] = 'financial'
        elif any(indicator in content_lower for indicator in ['deadline', 'date', 'timeline']):
            metadata['chunk_type'] = 'temporal'
        else:
            metadata['chunk_type'] = 'general'
        
        return metadata
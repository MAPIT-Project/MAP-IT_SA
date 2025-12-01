# 🔍 Enhanced RAG System Implementation Guide

## Overview
This guide provides concrete implementation for a production-ready RAG system with hybrid search, intelligent chunking, and conversation-aware retrieval.

## 1. Intelligent Document Chunking

### File: `app/services/rag/intelligent_chunker.py`

```python
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

# Download required NLTK data
nltk.download('punkt', quiet=True)

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
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
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
                 chunk_size: int = 500,
                 chunk_overlap: int = 100,
                 min_chunk_size: int = 200,
                 max_chunk_size: int = 800):
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
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Initialize text splitter with semantic awareness
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 4,  # Approximate chars (1 token ≈ 4 chars)
            chunk_overlap=chunk_overlap * 4,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=self._token_length
        )
    
    def chunk_document(self,
                      document: Dict[str, Any],
                      chunking_strategy: str = "semantic") -> List[DocumentChunk]:
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
    
    def _semantic_chunking(self, text: str) -> List[str]:
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
    
    def _identify_sections(self, text: str) -> List[Dict[str, str]]:
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
    
    def _split_semantic_section(self, text: str) -> List[str]:
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
    
    def _sentence_chunking(self, text: str) -> List[str]:
        """
        Chunk by sentences, grouping them to reach target size.
        """
        sentences = sent_tokenize(text)
        
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
    
    def _fixed_chunking(self, text: str) -> List[str]:
        """
        Simple fixed-size chunking with overlap.
        """
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
    
    def _apply_overlap(self, chunks: List[str]) -> List[str]:
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
        tokens = self.tokenizer.encode(text)
        overlap_tokens = self.chunk_overlap
        
        if from_start:
            overlap = tokens[:overlap_tokens]
        else:
            overlap = tokens[-overlap_tokens:]
        
        return self.tokenizer.decode(overlap)
    
    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
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
    
    def _split_large_chunk(self, text: str) -> List[str]:
        """
        Split a chunk that exceeds max size.
        """
        tokens = self.tokenizer.encode(text)
        sub_chunks = []
        
        for i in range(0, len(tokens), self.chunk_size):
            sub_chunk_tokens = tokens[i:i + self.chunk_size]
            sub_chunk_text = self.tokenizer.decode(sub_chunk_tokens)
            sub_chunks.append(sub_chunk_text)
        
        return sub_chunks
    
    def _token_length(self, text: str) -> int:
        """
        Calculate token count for text.
        """
        return len(self.tokenizer.encode(text))
    
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
                        base_metadata: Dict[str, Any],
                        chunk_content: str,
                        chunk_index: int) -> Dict[str, Any]:
        """
        Enrich chunk metadata with additional information.
        """
        metadata = base_metadata.copy()
        
        # Add chunk-specific metadata
        metadata['chunk_index'] = chunk_index
        metadata['chunk_length'] = len(chunk_content)
        metadata['chunk_tokens'] = self._token_length(chunk_content)
        
        # Extract potential keywords (simple approach)
        words = word_tokenize(chunk_content.lower())
        word_freq = {}
        for word in words:
            if len(word) > 4 and word.isalpha():
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Top 5 keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        metadata['keywords'] = [k[0] for k in keywords]
        
        # Detect chunk type (heuristic)
        if any(indicator in chunk_content.lower() for indicator in ['objective', 'goal', 'aim']):
            metadata['chunk_type'] = 'objective'
        elif any(indicator in chunk_content.lower() for indicator in ['budget', 'cost', 'funding']):
            metadata['chunk_type'] = 'financial'
        elif any(indicator in chunk_content.lower() for indicator in ['deadline', 'date', 'timeline']):
            metadata['chunk_type'] = 'temporal'
        else:
            metadata['chunk_type'] = 'general'
        
        return metadata
```

## 2. Hybrid Search Pipeline

### File: `app/services/rag/hybrid_search.py`

```python
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import CrossEncoder
import hashlib
import json

@dataclass
class SearchResult:
    """Represents a search result with scoring"""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str  # 'vector', 'keyword', or 'hybrid'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'score': self.score,
            'metadata': self.metadata,
            'source': self.source
        }

class HybridSearchPipeline:
    """
    Advanced hybrid search combining vector and keyword search
    with cross-encoder reranking.
    """
    
    def __init__(self,
                 vector_store,
                 keyword_store,
                 embedding_service,
                 reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize hybrid search pipeline.
        
        Args:
            vector_store: Vector database client
            keyword_store: Keyword search database client
            embedding_service: Service for generating embeddings
            reranker_model: Cross-encoder model for reranking
        """
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        self.embedding_service = embedding_service
        
        # Initialize cross-encoder for reranking
        self.cross_encoder = CrossEncoder(reranker_model)
        
        # Search configuration
        self.vector_weight = 0.7
        self.keyword_weight = 0.3
        self.initial_retrieval_limit = 20
        self.final_limit = 4
    
    async def search(self,
                    query: str,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 4,
                    use_reranking: bool = True) -> List[SearchResult]:
        """
        Perform hybrid search with optional reranking.
        
        Args:
            query: Search query
            filters: Optional metadata filters
            limit: Number of results to return
            use_reranking: Whether to use cross-encoder reranking
            
        Returns:
            List of SearchResult objects
        """
        # Run vector and keyword searches in parallel
        vector_task = asyncio.create_task(
            self._vector_search_async(query, filters, self.initial_retrieval_limit)
        )
        keyword_task = asyncio.create_task(
            self._keyword_search_async(query, filters, self.initial_retrieval_limit)
        )
        
        # Wait for both searches to complete
        vector_results, keyword_results = await asyncio.gather(
            vector_task, keyword_task
        )
        
        # Merge results
        merged_results = self._merge_results(
            vector_results, 
            keyword_results,
            self.vector_weight,
            self.keyword_weight
        )
        
        # Rerank if enabled
        if use_reranking and merged_results:
            reranked_results = self._rerank_results(query, merged_results)
            return reranked_results[:limit]
        else:
            return merged_results[:limit]
    
    async def _vector_search_async(self,
                                  query: str,
                                  filters: Optional[Dict[str, Any]],
                                  limit: int) -> List[SearchResult]:
        """
        Asynchronous vector search.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._vector_search,
            query,
            filters,
            limit
        )
    
    def _vector_search(self,
                      query: str,
                      filters: Optional[Dict[str, Any]],
                      limit: int) -> List[SearchResult]:
        """
        Perform vector similarity search.
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_query_embedding(query)
            
            # Search in vector store
            results = self.vector_store.similarity_search(
                embedding=query_embedding,
                limit=limit,
                filters=filters
            )
            
            # Convert to SearchResult objects
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    chunk_id=result['chunk_id'],
                    content=result['content'],
                    score=result['similarity_score'],
                    metadata=result.get('metadata', {}),
                    source='vector'
                ))
            
            return search_results
            
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    async def _keyword_search_async(self,
                                   query: str,
                                   filters: Optional[Dict[str, Any]],
                                   limit: int) -> List[SearchResult]:
        """
        Asynchronous keyword search.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._keyword_search,
            query,
            filters,
            limit
        )
    
    def _keyword_search(self,
                       query: str,
                       filters: Optional[Dict[str, Any]],
                       limit: int) -> List[SearchResult]:
        """
        Perform keyword-based search.
        """
        try:
            # Process query for keyword search
            processed_query = self._process_query_for_keywords(query)
            
            # Search in keyword store (PostgreSQL FTS)
            results = self.keyword_store.fulltext_search(
                query=processed_query,
                limit=limit,
                filters=filters
            )
            
            # Convert to SearchResult objects
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    chunk_id=result['chunk_id'],
                    content=result['content'],
                    score=result['relevance_score'],
                    metadata=result.get('metadata', {}),
                    source='keyword'
                ))
            
            return search_results
            
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []
    
    def _process_query_for_keywords(self, query: str) -> str:
        """
        Process query for keyword search.
        Extracts important terms and creates search query.
        """
        # Remove common stop words
        stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'been', 'be'}
        
        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Create PostgreSQL tsquery format
        # Use OR between terms for broader matching
        if keywords:
            return ' | '.join(keywords)
        else:
            return query
    
    def _merge_results(self,
                      vector_results: List[SearchResult],
                      keyword_results: List[SearchResult],
                      vector_weight: float,
                      keyword_weight: float) -> List[SearchResult]:
        """
        Merge and deduplicate results from vector and keyword search.
        """
        # Create a dictionary to track unique results
        merged_dict = {}
        
        # Add vector results with weighted scores
        for result in vector_results:
            merged_dict[result.chunk_id] = SearchResult(
                chunk_id=result.chunk_id,
                content=result.content,
                score=result.score * vector_weight,
                metadata=result.metadata,
                source='hybrid'
            )
        
        # Add or update with keyword results
        for result in keyword_results:
            if result.chunk_id in merged_dict:
                # Combine scores if already present
                merged_dict[result.chunk_id].score += result.score * keyword_weight
            else:
                # Add new result
                merged_dict[result.chunk_id] = SearchResult(
                    chunk_id=result.chunk_id,
                    content=result.content,
                    score=result.score * keyword_weight,
                    metadata=result.metadata,
                    source='hybrid'
                )
        
        # Sort by combined score
        merged_results = list(merged_dict.values())
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results
    
    def _rerank_results(self,
                       query: str,
                       results: List[SearchResult]) -> List[SearchResult]:
        """
        Rerank results using cross-encoder.
        """
        if not results:
            return results
        
        # Prepare query-document pairs for cross-encoder
        pairs = [[query, result.content] for result in results]
        
        # Get cross-encoder scores
        ce_scores = self.cross_encoder.predict(pairs)
        
        # Update result scores with cross-encoder scores
        for i, result in enumerate(results):
            # Combine original score with cross-encoder score
            # Give more weight to cross-encoder for final ranking
            result.score = 0.3 * result.score + 0.7 * ce_scores[i]
        
        # Sort by new scores
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    def update_weights(self,
                      vector_weight: float,
                      keyword_weight: float):
        """
        Update search weights dynamically.
        
        Args:
            vector_weight: Weight for vector search (0-1)
            keyword_weight: Weight for keyword search (0-1)
        """
        # Normalize weights
        total = vector_weight + keyword_weight
        self.vector_weight = vector_weight / total
        self.keyword_weight = keyword_weight / total
```

## 3. Conversation-Aware Retrieval

### File: `app/services/rag/conversation_retriever.py`

```python
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import redis
from dataclasses import dataclass

@dataclass
class RetrievalContext:
    """Context for retrieval operations"""
    conversation_id: int
    current_query: str
    conversation_summary: str
    recent_topics: List[str]
    entity_mentions: List[str]
    search_history: List[str]

class ConversationAwareRetriever:
    """
    Retrieval system that understands conversation context
    and caches results for efficiency.
    """
    
    def __init__(self,
                 hybrid_search: HybridSearchPipeline,
                 cache_client: redis.Redis,
                 cache_ttl: int = 3600):
        """
        Initialize conversation-aware retriever.
        
        Args:
            hybrid_search: Hybrid search pipeline
            cache_client: Redis client for caching
            cache_ttl: Cache time-to-live in seconds
        """
        self.hybrid_search = hybrid_search
        self.cache = cache_client
        self.cache_ttl = cache_ttl
    
    async def retrieve(self,
                      context: RetrievalContext,
                      max_chunks: int = 4,
                      use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks considering conversation context.
        
        Args:
            context: Retrieval context with conversation info
            max_chunks: Maximum chunks to retrieve
            use_cache: Whether to use cached results
            
        Returns:
            List of relevant chunks with metadata
        """
        # Formulate context-aware query
        enhanced_query = self._formulate_contextual_query(context)
        
        # Check cache if enabled
        if use_cache:
            cached_results = self._get_cached_results(
                context.conversation_id,
                enhanced_query
            )
            if cached_results:
                return cached_results
        
        # Perform retrieval
        search_results = await self.hybrid_search.search(
            query=enhanced_query,
            filters=self._build_filters(context),
            limit=max_chunks,
            use_reranking=True
        )
        
        # Process and enrich results
        enriched_results = self._enrich_results(search_results, context)
        
        # Cache results
        if use_cache:
            self._cache_results(
                context.conversation_id,
                enhanced_query,
                enriched_results
            )
        
        return enriched_results
    
    def _formulate_contextual_query(self, context: RetrievalContext) -> str:
        """
        Enhance query with conversation context.
        """
        # Start with current query
        enhanced_parts = [context.current_query]
        
        # Add relevant topics from conversation
        if context.recent_topics:
            # Add top 2 most relevant topics
            topic_context = f"Topics: {', '.join(context.recent_topics[:2])}"
            enhanced_parts.append(topic_context)
        
        # Add entity context if relevant
        if context.entity_mentions:
            # Check if entities are relevant to current query
            query_lower = context.current_query.lower()
            relevant_entities = [
                entity for entity in context.entity_mentions
                if any(word in query_lower for word in entity.lower().split())
            ]
            if relevant_entities:
                entity_context = f"Entities: {', '.join(relevant_entities[:2])}"
                enhanced_parts.append(entity_context)
        
        # Add summary context if query seems to reference previous discussion
        reference_indicators = ['that', 'it', 'this', 'mentioned', 'discussed', 'previous']
        if any(indicator in context.current_query.lower() for indicator in reference_indicators):
            if context.conversation_summary:
                # Extract key phrases from summary
                summary_snippet = context.conversation_summary[:200]
                enhanced_parts.append(f"Context: {summary_snippet}")
        
        # Combine parts
        enhanced_query = " | ".join(enhanced_parts)
        
        return enhanced_query
    
    def _build_filters(self, context: RetrievalContext) -> Dict[str, Any]:
        """
        Build metadata filters based on context.
        """
        filters = {}
        
        # Add topic filters if specific domains are discussed
        domain_keywords = {
            'energy': ['renewable', 'solar', 'wind', 'nuclear'],
            'health': ['medical', 'clinical', 'patient', 'disease'],
            'digital': ['AI', 'software', 'data', 'cyber'],
            'climate': ['carbon', 'emission', 'sustainability', 'green']
        }
        
        # Check which domains are relevant
        all_text = ' '.join([
            context.current_query,
            ' '.join(context.recent_topics),
            context.conversation_summary[:500] if context.conversation_summary else ''
        ]).lower()
        
        relevant_domains = []
        for domain, keywords in domain_keywords.items():
            if any(keyword in all_text for keyword in keywords):
                relevant_domains.append(domain)
        
        if relevant_domains:
            filters['domain'] = relevant_domains
        
        # Add temporal filters if dates are mentioned
        current_year = datetime.now().year
        if str(current_year) in context.current_query or str(current_year + 1) in context.current_query:
            filters['year'] = [current_year, current_year + 1]
        
        return filters
    
    def _enrich_results(self,
                       search_results: List[SearchResult],
                       context: RetrievalContext) -> List[Dict[str, Any]]:
        """
        Enrich search results with additional context.
        """
        enriched = []
        
        for result in search_results:
            enriched_result = result.to_dict()
            
            # Add relevance explanation
            enriched_result['relevance_explanation'] = self._explain_relevance(
                result,
                context
            )
            
            # Add citation format
            enriched_result['citation'] = self._format_citation(result)
            
            # Mark if this chunk was previously retrieved
            enriched_result['previously_retrieved'] = self._was_previously_retrieved(
                context.conversation_id,
                result.chunk_id
            )
            
            enriched.append(enriched_result)
        
        return enriched
    
    def _explain_relevance(self,
                          result: SearchResult,
                          context: RetrievalContext) -> str:
        """
        Generate explanation for why this chunk is relevant.
        """
        explanations = []
        
        # Check for direct query match
        query_words = set(context.current_query.lower().split())
        content_words = set(result.content.lower().split())
        common_words = query_words & content_words
        
        if len(common_words) > 2:
            explanations.append(f"Matches query terms: {', '.join(list(common_words)[:3])}")
        
        # Check for topic relevance
        for topic in context.recent_topics[:2]:
            if topic.lower() in result.content.lower():
                explanations.append(f"Related to discussed topic: {topic}")
        
        # Check for entity relevance
        for entity in context.entity_mentions[:2]:
            if entity.lower() in result.content.lower():
                explanations.append(f"Mentions entity: {entity}")
        
        # Check metadata relevance
        if result.metadata.get('chunk_type') == 'objective' and 'objective' in context.current_query.lower():
            explanations.append("Contains objective information")
        elif result.metadata.get('chunk_type') == 'financial' and any(word in context.current_query.lower() for word in ['budget', 'cost', 'funding']):
            explanations.append("Contains financial information")
        
        if explanations:
            return "; ".join(explanations)
        else:
            return f"Semantic similarity score: {result.score:.2f}"
    
    def _format_citation(self, result: SearchResult) -> str:
        """
        Format a citation for the chunk.
        """
        metadata = result.metadata
        
        # Build citation parts
        parts = []
        
        if metadata.get('document_title'):
            parts.append(metadata['document_title'])
        
        if metadata.get('document_id'):
            parts.append(f"Doc ID: {metadata['document_id'][:8]}")
        
        if metadata.get('chunk_index') is not None:
            parts.append(f"Section {metadata['chunk_index'] + 1}")
        
        if metadata.get('page_number'):
            parts.append(f"Page {metadata['page_number']}")
        
        return " | ".join(parts) if parts else f"Chunk {result.chunk_id[:8]}"
    
    def _get_cached_results(self,
                           conversation_id: int,
                           query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached results if available.
        """
        try:
            cache_key = self._generate_cache_key(conversation_id, query)
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            print(f"Cache retrieval error: {e}")
            return None
    
    def _cache_results(self,
                      conversation_id: int,
                      query: str,
                      results: List[Dict[str, Any]]):
        """
        Cache retrieval results.
        """
        try:
            cache_key = self._generate_cache_key(conversation_id, query)
            
            # Store results
            self.cache.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(results)
            )
            
            # Track retrieval history
            history_key = f"retrieval_history:{conversation_id}"
            self.cache.lpush(history_key, query)
            self.cache.ltrim(history_key, 0, 19)  # Keep last 20 queries
            self.cache.expire(history_key, 86400)  # 24 hour TTL
            
            # Track retrieved chunks
            for result in results:
                chunk_key = f"retrieved_chunks:{conversation_id}"
                self.cache.sadd(chunk_key, result['chunk_id'])
                self.cache.expire(chunk_key, 86400)
                
        except Exception as e:
            print(f"Cache storage error: {e}")
    
    def _was_previously_retrieved(self,
                                 conversation_id: int,
                                 chunk_id: str) -> bool:
        """
        Check if chunk was previously retrieved in this conversation.
        """
        try:
            chunk_key = f"retrieved_chunks:{conversation_id}"
            return self.cache.sismember(chunk_key, chunk_id)
        except:
            return False
    
    def _generate_cache_key(self,
                           conversation_id: int,
                           query: str) -> str:
        """
        Generate cache key for query results.
        """
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"retrieval_cache:{conversation_id}:{query_hash}"
    
    def get_retrieval_stats(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get statistics about retrieval for a conversation.
        """
        try:
            history_key = f"retrieval_history:{conversation_id}"
            chunk_key = f"retrieved_chunks:{conversation_id}"
            
            query_history = self.cache.lrange(history_key, 0, -1)
            unique_chunks = self.cache.scard(chunk_key)
            
            return {
                'total_queries': len(query_history),
                'unique_chunks_retrieved': unique_chunks,
                'recent_queries': [q.decode() if isinstance(q, bytes) else q for q in query_history[:5]]
            }
        except:
            return {
                'total_queries': 0,
                'unique_chunks_retrieved': 0,
                'recent_queries': []
            }
```

## 4. Grounded Response Generation

### File: `app/services/rag/response_generator.py`

```python
from typing import List, Dict, Any, Optional, AsyncGenerator
import google.generativeai as genai
import json
import re

class GroundedResponseGenerator:
    """
    Generate responses grounded in retrieved context with citations.
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Initialize response generator.
        
        Args:
            gemini_api_key: Google Gemini API key
        """
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-flash-lite-latest')
    
    def generate_response(self,
                         query: str,
                         context_chunks: List[Dict[str, Any]],
                         conversation_context: str,
                         system_instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate grounded response with citations.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks
            conversation_context: Conversation history/summary
            system_instructions: Optional custom instructions
            
        Returns:
            Response with answer and citations
        """
        # Build prompt
        prompt = self._build_grounded_prompt(
            query,
            context_chunks,
            conversation_context,
            system_instructions
        )
        
        try:
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                )
            )
            
            # Parse and validate response
            parsed_response = self._parse_response(response.text, context_chunks)
            
            return parsed_response
            
        except Exception as e:
            print(f"Generation error: {e}")
            return {
                'answer': "I encountered an error generating the response.",
                'citations': [],
                'confidence': 0.0,
                'grounded': False
            }
    
    async def generate_streaming_response(self,
                                         query: str,
                                         context_chunks: List[Dict[str, Any]],
                                         conversation_context: str,
                                         system_instructions: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming response with progressive output.
        """
        # Build prompt
        prompt = self._build_grounded_prompt(
            query,
            context_chunks,
            conversation_context,
            system_instructions
        )
        
        try:
            # Generate streaming response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                ),
                stream=True
            )
            
            accumulated_text = ""
            
            for chunk in response:
                if chunk.text:
                    accumulated_text += chunk.text
                    
                    # Yield token
                    yield {
                        'type': 'token',
                        'content': chunk.text
                    }
            
            # Parse final response for citations
            parsed_response = self._parse_response(accumulated_text, context_chunks)
            
            # Yield completion with metadata
            yield {
                'type': 'complete',
                'citations': parsed_response['citations'],
                'confidence': parsed_response['confidence'],
                'grounded': parsed_response['grounded']
            }
            
        except Exception as e:
            yield {
                'type': 'error',
                'error': str(e)
            }
    
    def _build_grounded_prompt(self,
                              query: str,
                              context_chunks: List[Dict[str, Any]],
                              conversation_context: str,
                              system_instructions: Optional[str]) -> str:
        """
        Build prompt for grounded generation.
        """
        # Default instructions
        default_instructions = """You are a helpful AI assistant that provides accurate, grounded responses.

CRITICAL RULES:
1. Base your response ONLY on the provided context chunks
2. Cite specific chunks using [1], [2], etc. when referencing information
3. If the context doesn't contain relevant information, explicitly state this
4. Do not invent or assume information not present in the context
5. Be conversational while maintaining accuracy"""

        instructions = system_instructions or default_instructions
        
        # Format context chunks
        formatted_chunks = self._format_context_chunks(context_chunks)
        
        # Build complete prompt
        prompt = f"""{instructions}

CONVERSATION CONTEXT:
{conversation_context if conversation_context else "No previous context"}

RETRIEVED INFORMATION:
{formatted_chunks}

USER QUERY: {query}

RESPONSE INSTRUCTIONS:
- Answer the query using ONLY the retrieved information
- Include citations [1], [2], etc. for each claim
- If you cannot answer from the context, say so clearly
- Be helpful and conversational

Your response:"""

        return prompt
    
    def _format_context_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format context chunks for prompt.
        """
        if not chunks:
            return "No relevant information retrieved."
        
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            citation = chunk.get('citation', f'Chunk {i}')
            content = chunk.get('content', '')
            
            formatted.append(f"[{i}] {citation}\n{content}")
        
        return "\n\n".join(formatted)
    
    def _parse_response(self,
                       response_text: str,
                       context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse response and extract citations.
        """
        # Extract citation numbers from response
        citation_pattern = r'\[(\d+)\]'
        citations_found = re.findall(citation_pattern, response_text)
        
        # Build citation list
        citations = []
        for citation_num in set(citations_found):
            idx = int(citation_num) - 1
            if 0 <= idx < len(context_chunks):
                citations.append({
                    'number': int(citation_num),
                    'chunk_id': context_chunks[idx].get('chunk_id'),
                    'citation': context_chunks[idx].get('citation'),
                    'content_snippet': context_chunks[idx].get('content', '')[:200]
                })
        
        # Calculate confidence based on grounding
        grounded = len(citations) > 0
        confidence = min(1.0, len(citations) * 0.25) if grounded else 0.3
        
        # Check for explicit "no information" statements
        no_info_indicators = [
            "don't have information",
            "context doesn't contain",
            "cannot answer",
            "no relevant information",
            "not mentioned in the context"
        ]
        
        if any(indicator in response_text.lower() for indicator in no_info_indicators):
            grounded = True  # Correctly identified lack of information
            confidence = 0.9
        
        return {
            'answer': response_text,
            'citations': citations,
            'confidence': confidence,
            'grounded': grounded,
            'chunks_used': len(context_chunks)
        }
```

This implementation provides a complete, production-ready RAG system with all the advanced features recommended in the Perplexity conversation.
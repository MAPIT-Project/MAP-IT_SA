
# Horizon Europe RAG System - Technical Specification (Part 2)

## 3. Core Services Implementation (Continued)

### 3.4 Embedding Service
```python
# app/services/embedding_service.py

import os
import hashlib
import numpy as np
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from google.generativeai import embedding
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from functools import lru_cache

class EmbeddingService:
    """Service for generating text embeddings using Google's API."""
    
    def __init__(self, cache_client=None):
        self.api_key = os.getenv("GOOGLE_EMBEDDING_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not found")
        
        genai.configure(api_key=self.api_key)
        
        # Model configuration
        self.model_name = "models/text-embedding-004"
        self.embedding_dimension = 768
        self.batch_size = 100  # Google's API batch limit
        self.cache_client = cache_client  # Supabase client for caching
        
        # Rate limiting
        self.requests_per_minute = 60
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.requests_per_minute
    
    def generate_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """Generate embedding for a single text."""
        # Check cache first
        if use_cache and self.cache_client:
            text_hash = self.calculate_hash(text)
            cached = self.cache_client.get_cached_embedding(text_hash)
            if cached is not None:
                return cached
        
        # Rate limiting
        self._rate_limit()
        
        try:
            # Generate embedding
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
                title="Document chunk"
            )
            
            embedding_array = np.array(result['embedding'])
            
            # Cache the result
            if use_cache and self.cache_client:
                self.cache_client.cache_embedding(text, text_hash, embedding_array)
            
            return embedding_array
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(
        self, 
        texts: List[str], 
        use_cache: bool = True
    ) -> List[np.ndarray]:
        """Generate embeddings for multiple texts in batches."""
        embeddings = []
        texts_to_embed = []
        text_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            if use_cache and self.cache_client:
                text_hash = self.calculate_hash(text)
                cached = self.cache_client.get_cached_embedding(text_hash)
                if cached is not None:
                    embeddings.append((i, cached))
                    continue
            
            texts_to_embed.append(text)
            text_indices.append(i)
        
        # Process uncached texts in batches
        for i in range(0, len(texts_to_embed), self.batch_size):
            batch = texts_to_embed[i:i + self.batch_size]
            batch_indices = text_indices[i:i + self.batch_size]
            
            # Rate limiting
            self._rate_limit()
            
            try:
                # Generate batch embeddings
                results = genai.embed_content(
                    model=self.model_name,
                    content=batch,
                    task_type="retrieval_document"
                )
                
                for j, embedding in enumerate(results['embedding']):
                    embedding_array = np.array(embedding)
                    original_index = batch_indices[j]
                    embeddings.append((original_index, embedding_array))
                    
                    # Cache the result
                    if use_cache and self.cache_client:
                        text = batch[j]
                        text_hash = self.calculate_hash(text)
                        self.cache_client.cache_embedding(text, text_hash, embedding_array)
                
            except Exception as e:
                print(f"Error in batch embedding generation: {e}")
                # Fall back to individual generation
                for j, text in enumerate(batch):
                    try:
                        embedding = self.generate_embedding(text, use_cache)
                        original_index = batch_indices[j]
                        embeddings.append((original_index, embedding))
                    except:
                        # Return zero vector on failure
                        embeddings.append((batch_indices[j], np.zeros(self.embedding_dimension)))
        
        # Sort by original index and return in order
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]
    
    async def generate_embeddings_async(
        self, 
        texts: List[str], 
        max_workers: int = 5
    ) -> List[np.ndarray]:
        """Generate embeddings asynchronously for better performance."""
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            tasks = []
            for text in texts:
                task = loop.run_in_executor(
                    executor, 
                    self.generate_embedding, 
                    text
                )
                tasks.append(task)
            
            embeddings = await asyncio.gather(*tasks)
        
        return embeddings
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a search query."""
        # Rate limiting
        self._rate_limit()
        
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query",  # Different task type for queries
                title="Search query"
            )
            
            return np.array(result['embedding'])
            
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            raise
    
    def _rate_limit(self):
        """Implement rate limiting to avoid API throttling."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def calculate_hash(self, text: str) -> str:
        """Calculate hash for text caching."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """Validate embedding dimensions and values."""
        if embedding.shape[0] != self.embedding_dimension:
            return False
        
        # Check for NaN or infinite values
        if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
            return False
        
        # Check if embedding is not all zeros
        if np.all(embedding == 0):
            return False
        
        return True
```

### 3.5 Vector Search Service
```python
# app/services/vector_search_service.py

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

@dataclass
class SearchResult:
    """Container for search results."""
    chunk_id: str
    document_id: str
    content: str
    document_title: str
    document_type: str
    score: float
    metadata: Dict[str, Any]
    highlights: Optional[List[str]] = None

class VectorSearchService:
    """Advanced vector search with hybrid capabilities."""
    
    def __init__(self, supabase_client, embedding_service):
        self.supabase = supabase_client
        self.embedder = embedding_service
    
    def search(
        self,
        query: str,
        search_type: str = "hybrid",
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        rerank: bool = True
    ) -> List[SearchResult]:
        """Main search interface supporting multiple search types."""
        
        if search_type == "semantic":
            results = self.semantic_search(query, num_results, filters)
        elif search_type == "keyword":
            results = self.keyword_search(query, num_results, filters)
        elif search_type == "hybrid":
            results = self.hybrid_search(query, num_results, filters)
        else:
            raise ValueError(f"Unknown search type: {search_type}")
        
        # Rerank results if requested
        if rerank and len(results) > 1:
            results = self.rerank_results(results, query)
        
        return results
    
    def semantic_search(
        self,
        query: str,
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """Pure semantic search using vector similarity."""
        
        # Generate query embedding
        query_embedding = self.embedder.generate_query_embedding(query)
        
        # Search in Supabase
        raw_results = self.supabase.semantic_search(
            query_embedding=query_embedding,
            match_threshold=similarity_threshold,
            match_count=num_results,
            filters=filters
        )
        
        # Convert to SearchResult objects
        results = []
        for r in raw_results:
            result = SearchResult(
                chunk_id=r['chunk_id'],
                document_id=r['document_id'],
                content=r['content'],
                document_title=r['document_title'],
                document_type=r.get('document_type', 'unknown'),
                score=r['similarity'],
                metadata=r.get('metadata', {})
            )
            results.append(result)
        
        return results
    
    def keyword_search(
        self,
        query: str,
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Traditional keyword-based search."""
        
        # Process query for better keyword matching
        processed_query = self.process_query_keywords(query)
        
        # Execute keyword search in database
        sql_query = """
            SELECT 
                c.id as chunk_id,
                c.document_id,
                c.content,
                d.title as document_title,
                d.document_type,
                ts_rank(c.content_tokens, query) as score,
                c.metadata
            FROM 
                document_chunks c
                JOIN horizon_documents d ON c.document_id = d.id,
                plainto_tsquery('english', %s) query
            WHERE 
                c.content_tokens @@ query
                AND d.status = 'active'
        """
        
        # Add filters if provided
        if filters:
            if filters.get('document_type'):
                sql_query += f" AND d.document_type = '{filters['document_type']}'"
            if filters.get('year'):
                sql_query += f" AND d.programme_year = '{filters['year']}'"
        
        sql_query += " ORDER BY score DESC LIMIT %s"
        
        # Execute query (this would need to be adapted to Supabase client)
        raw_results = self.supabase.client.rpc('keyword_search', {
            'query_text': processed_query,
            'limit_count': num_results
        }).execute()
        
        # Convert to SearchResult objects
        results = []
        for r in raw_results.data:
            result = SearchResult(
                chunk_id=r['chunk_id'],
                document_id=r['document_id'],
                content=r['content'],
                document_title=r['document_title'],
                document_type=r.get('document_type', 'unknown'),
                score=r['score'],
                metadata=r.get('metadata', {}),
                highlights=self.extract_highlights(r['content'], query)
            )
            results.append(result)
        
        return results
    
    def hybrid_search(
        self,
        query: str,
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        vector_weight: float = 0.5
    ) -> List[SearchResult]:
        """Hybrid search combining semantic and keyword search."""
        
        # Generate query embedding
        query_embedding = self.embedder.generate_query_embedding(query)
        
        # Execute hybrid search
        raw_results = self.supabase.hybrid_search(
            query_text=query,
            query_embedding=query_embedding,
            match_count=num_results,
            vector_weight=vector_weight
        )
        
        # Convert to SearchResult objects
        results = []
        for r in raw_results:
            result = SearchResult(
                chunk_id=r['chunk_id'],
                document_id=r['document_id'],
                content=r['content'],
                document_title=r['document_title'],
                document_type=r.get('document_type', 'unknown'),
                score=r['combined_score'],
                metadata=r.get('metadata', {}),
                highlights=self.extract_highlights(r['content'], query)
            )
            results.append(result)
        
        return results
    
    def rerank_results(
        self, 
        results: List[SearchResult], 
        query: str
    ) -> List[SearchResult]:
        """Rerank results using additional signals."""
        
        # Calculate additional ranking signals
        for result in results:
            # Exact match bonus
            if query.lower() in result.content.lower():
                result.score *= 1.2
            
            # Title match bonus
            if query.lower() in result.document_title.lower():
                result.score *= 1.1
            
            # Document type relevance
            if result.document_type in ['work_programme', 'call_text']:
                result.score *= 1.05
            
            # Recency bonus (if metadata contains date)
            if 'year' in result.metadata:
                try:
                    year = int(result.metadata['year'])
                    if year >= 2023:
                        result.score *= 1.1
                except:
                    pass
        
        # Sort by updated scores
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    def process_query_keywords(self, query: str) -> str:
        """Process query for better keyword matching."""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        
        # Tokenize and filter
        words = query.lower().split()
        filtered = [w for w in words if w not in stop_words]
        
        # Handle acronyms and special terms
        special_terms = {
            'ai': 'artificial intelligence',
            'ml': 'machine learning',
            'ict': 'information communication technology',
            'sme': 'small medium enterprise',
            'eu': 'european union'
        }
        
        expanded = []
        for word in filtered:
            if word in special_terms:
                expanded.append(f"({word} OR {special_terms[word]})")
            else:
                expanded.append(word)
        
        return ' '.join(expanded)
    
    def extract_highlights(
        self, 
        content: str, 
        query: str, 
        context_length: int = 100
    ) -> List[str]:
        """Extract highlighted snippets from content."""
        highlights = []
        query_words = query.lower().split()
        
        for word in query_words:
            if len(word) < 3:
                continue
            
            # Find word occurrences
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = pattern.finditer(content)
            
            for match in matches:
                start = max(0, match.start() - context_length)
                end = min(len(content), match.end() + context_length)
                
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                
                highlights.append(snippet)
                
                # Limit to 3 highlights per result
                if len(highlights) >= 3:
                    return highlights
        
        return highlights
    
    def get_similar_chunks(
        self,
        chunk_id: str,
        num_similar: int = 5
    ) -> List[SearchResult]:
        """Find similar chunks to a given chunk."""
        
        # Get the chunk's embedding
        chunk_data = self.supabase.client.table("document_chunks")\
            .select("embedding, content, document_id")\
            .eq("id", chunk_id)\
            .single()\
            .execute()
        
        if not chunk_data.data:
            return []
        
        embedding = np.array(chunk_data.data['embedding'])
        
        # Search for similar chunks
        similar = self.supabase.semantic_search(
            query_embedding=embedding,
            match_count=num_similar + 1  # +1 to exclude self
        )
        
        # Filter out the original chunk and convert to SearchResult
        results = []
        for r in similar:
            if r['chunk_id'] != chunk_id:
                result = SearchResult(
                    chunk_id=r['chunk_id'],
                    document_id=r['document_id'],
                    content=r['content'],
                    document_title=r['document_title'],
                    document_type=r.get('document_type', 'unknown'),
                    score=r['similarity'],
                    metadata=r.get('metadata', {})
                )
                results.append(result)
        
        return results[:num_similar]
```

### 3.6 RAG Integration Service
```python
# app/services/rag_integration_service.py

from typing import List, Dict, Any, Optional, Tuple
import json
from datetime import datetime

class HorizonEuropeRAG:
    """Enhanced RAG system integrating vector search with existing CORDIS search."""
    
    def __init__(
        self,
        vector_search_service,
        existing_cordis_rag,
        embedding_service,
        supabase_client
    ):
        self.vector_search = vector_search_service
        self.cordis_rag = existing_cordis_rag
        self.embedder = embedding_service
        self.supabase = supabase_client
    
    def answer_question(
        self,
        question: str,
        max_context_chunks: int = 5,
        include_projects: bool = True,
        include_documents: bool = True,
        search_type: str = "hybrid"
    ) -> Dict[str, Any]:
        """Main entry point for answering questions about Horizon Europe."""
        
        # Determine intent
        intent = self.classify_intent(question)
        
        # Route to appropriate handler
        if intent == "PROJECT_SEARCH":
            return self.handle_project_query(question)
        elif intent == "CALL_SEARCH":
            return self.handle_call_query(question)
        elif intent == "GENERAL_INFO":
            return self.handle_general_query(question, max_context_chunks, search_type)
        else:
            # Combined search
            return self.handle_combined_query(
                question, 
                max_context_chunks, 
                include_projects, 
                include_documents,
                search_type
            )
    
    def classify_intent(self, question: str) -> str:
        """Classify the user's intent."""
        question_lower = question.lower()
        
        # Project search indicators
        project_keywords = [
            'project', 'funded', 'consortium', 'coordinator',
            'partner', 'results', 'outcome', 'deliverable'
        ]
        
        # Call search indicators
        call_keywords = [
            'call', 'apply', 'deadline', 'proposal', 'submit',
            'funding opportunity', 'open call', 'tender'
        ]
        
        # General info indicators
        info_keywords = [
            'what is', 'how to', 'explain', 'guide', 'process',
            'requirement', 'eligibility', 'rule', 'procedure'
        ]
        
        # Count keyword matches
        project_score = sum(1 for kw in project_keywords if kw in question_lower)
        call_score = sum(1 for kw in call_keywords if kw in question_lower)
        info_score = sum(1 for kw in info_keywords if kw in question_lower)
        
        # Determine primary intent
        scores = {
            'PROJECT_SEARCH': project_score,
            'CALL_SEARCH': call_score,
            'GENERAL_INFO': info_score
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return 'COMBINED'
        
        return max(scores, key=scores.get)
    
    def handle_general_query(
        self,
        question: str,
        max_context_chunks: int,
        search_type: str
    ) -> Dict[str, Any]:
        """Handle general information queries using vector search."""
        
        # Search for relevant document chunks
        search_results = self.vector_search.search(
            query=question,
            search_type=search_type,
            num_results=max_context_chunks * 2,  # Get more for filtering
            rerank=True
        )
        
        # Select best chunks for context
        context_chunks = self.select_context_chunks(search_results, max_context_chunks)
        
        # Build context for LLM
        context = self.build_context(context_chunks)
        
        # Generate answer
        answer = self.generate_answer(question, context, context_chunks)
        
        return {
            'answer': answer,
            'intent': 'GENERAL_INFO',
            'sources': self.format_sources(context_chunks),
            'search_type': search_type,
            'chunks_used': len(context_chunks),
            'confidence': self.calculate_confidence(search_results)
        }
    
    def handle_project_query(self, question: str) -> Dict[str, Any]:
        """Handle project-specific queries using existing CORDIS RAG."""
        
        # Use existing CORDIS RAG system
        result = self.cordis_rag.get_ai_response_with_routing(
            question=question,
            max_projects_to_process=5
        )
        
        # Enhance with document context if relevant
        doc_context = self.get_supporting_documentation(question, max_chunks=2)
        
        if doc_context:
            result['supporting_docs'] = doc_context
            # Optionally regenerate answer with additional context
        
        return result
    
    def handle_call_query(self, question: str) -> Dict[str, Any]:
        """Handle call/funding opportunity queries."""
        
        # Use existing call search functionality
        result = self.cordis_rag.search_for_calls(
            question=question,
            max_results=10
        )
        
        # Enhance with programme documentation
        doc_context = self.get_supporting_documentation(
            question, 
            max_chunks=3,
            doc_types=['work_programme', 'call_text', 'guide']
        )
        
        if doc_context:
            result['supporting_docs'] = doc_context
        
        return result
    
    def handle_combined_query(
        self,
        question: str,
        max_context_chunks: int,
        include_projects: bool,
        include_documents: bool,
        search_type: str
    ) -> Dict[str, Any]:
        """Handle queries requiring both project and document information."""
        
        results = {
            'question': question,
            'intent': 'COMBINED',
            'components': []
        }
        
        # Get document context
        if include_documents:
            doc_results = self.vector_search.search(
                query=question,
                search_type=search_type,
                num_results=max_context_chunks
            )
            results['components'].append({
                'type': 'documents',
                'results': doc_results
            })
        
        # Get project information
        if include_projects:
            project_results = self.cordis_rag.get_ai_response_with_routing(
                question=question,
                max_projects_to_process=3
            )
            results['components'].append({
                'type': 'projects',
                'results': project_results
            })
        
        # Generate combined answer
        combined_context = self.merge_contexts(results['components'])
        answer = self.generate_answer(question, combined_context, [])
        
        results['answer'] = answer
        results['confidence'] = self.calculate_combined_confidence(results['components'])
        
        return results
    
    def select_context_chunks(
        self,
        search_results: List,
        max_chunks: int
    ) -> List:
        """Select the best chunks for context window."""
        
        # Remove duplicate content
        seen_content = set()
        unique_results = []
        
        for result in search_results:
            content_hash = hash(result.content[:200])  # Hash first 200 chars
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        # Diversify by document
        documents_used = {}
        selected = []
        
        for result in unique_results:
            doc_id = result.document_id
            
            # Limit chunks per document
            if doc_id in documents_used:
                if documents_used[doc_id] >= 2:  # Max 2 chunks per doc
                    continue
                documents_used[doc_id] += 1
            else:
                documents_used[doc_id] = 1
            
            selected.append(result)
            
            if len(selected) >= max_chunks:
                break
        
        return selected
    
    def build_context(self, chunks: List) -> str:
        """Build context string from chunks."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            context_part = f"[Source {i}: {chunk.document_title}]\n"
            context_part += f"Type: {chunk.document_type}\n"
            context_part += f"Content: {chunk.content}\n"
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)
    
    def generate_answer(
        self,
        question: str,
        context: str,
        chunks: List
    ) -> str:
        """Generate answer using LLM with context."""
        
        prompt = f"""You are an expert on Horizon Europe, the EU's research and innovation funding programme.
        
Based on the following context from official Horizon Europe documentation, answer the user's question accurately and comprehensively.

Context:
{context}

Question: {question}

Instructions:
- Provide a clear, well-structured answer
- Reference specific documents when possible
- Include relevant details like deadlines, requirements, or procedures
- If the context doesn't contain enough information, acknowledge this
- Be precise about eligibility criteria, evaluation processes, and requirements

Answer:"""
        
        # Use the existing LLM service (Gemini)
        answer = self.cordis_rag._call_llm_for_generation(
            role="Horizon Europe Expert",
            prompt=prompt
        )
        
        return answer
    
    def get_supporting_documentation(
        self,
        question: str,
        max_chunks: int = 3,
        doc_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get supporting documentation for a query."""
        
        filters = {}
        if doc_types:
            filters['document_type'] = doc_types[0]  # Simplified for example
        
        results = self.vector_search.search(
            query=question,
            search_type="semantic",
            num_results=max_chunks,
            filters=filters
        )
        
        return [
            {
                'title': r.document_title,
                'type': r.document_type,
                'excerpt': r.content[:500],
                'relevance': r.score
            }
            for r in results
        ]
    
    def format_sources(self, chunks: List) -> List[Dict[str, str]]:
        """Format source citations."""
        sources = []
        seen_docs = set()
        
        for chunk in chunks:
            doc_id = chunk.document_id
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                sources.append({
                    'title': chunk.document_title,
                    'type': chunk.document_type,
                    'id': doc_id
                })
        
        return sources
    
    def calculate_confidence(self, search_results: List) -> float:
        """Calculate confidence score for the answer."""
        if not search_results:
            return 0.0
        
        # Average of top 3 scores
        top_scores = [r.score for r in search_results[:3]]
        avg_score = sum(top_scores) / len(top_scores)
        
        # Normalize to 0-1 range
        return min(1.0, avg_score)
    
    def calculate_combined_confidence(self, components: List) -> float:
        """Calculate confidence for combined results."""
        confidences = []
        
        for component in components:
            if component['type'] == 'documents':
                scores = [r.score for r in component['results'][:3]]
                if scores:
                    confidences.append(sum(scores) / len(scores))
            elif component['type'] == 'projects':
                # Use existing confidence from CORDIS RAG
                if 'confidence' in component['results']:
                    confidences.append(component['results']['confidence'])
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def merge_contexts(self, components: List) -> str:
        """Merge different context types into a single context."""
        merged = []
        
        for component in components:
            if component['type'] == 'documents':
                doc_context = self.build_context(component['results'][:3])
                merged.append(f"=== Document Context ===\n{doc_context}")
            elif component['type'] == 'projects':
                if 'answer' in component['results']:
                    merged.append(f"=== Project Information ===\n{component['results']['answer'][:1000]}")
        
        return "\n\n".join(merged)
```

## 4. API Implementation

### 4.1 Document Management Routes
```python
# app/api/document_routes.py

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional, List, Dict, Any
import uuid
from pathlib import Path

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = None,
    programme_year: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload a document for processing and ingestion."""
    
    #
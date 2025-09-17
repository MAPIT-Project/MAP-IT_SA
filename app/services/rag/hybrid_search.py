import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os

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
        try:
            from sentence_transformers import CrossEncoder
            self.cross_encoder = CrossEncoder(reranker_model)
        except ImportError:
            print("Warning: sentence-transformers not available, reranking disabled")
            self.cross_encoder = None
        
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
        if use_reranking and merged_results and self.cross_encoder:
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
                    chunk_id=result.get('chunk_id', ''),
                    content=result.get('content', ''),
                    score=result.get('similarity_score', 0.0),
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
                    chunk_id=result.get('chunk_id', ''),
                    content=result.get('content', ''),
                    score=result.get('relevance_score', 0.0),
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
        if not results or not self.cross_encoder:
            return results
        
        try:
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
        except Exception as e:
            print(f"Reranking error: {e}")
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
        if total > 0:
            self.vector_weight = vector_weight / total
            self.keyword_weight = keyword_weight / total

class MockVectorStore:
    """Mock vector store for testing when real one isn't available"""
    
    def similarity_search(self, embedding, limit=10, filters=None):
        # Return mock results
        return [
            {
                'chunk_id': f'mock_chunk_{i}',
                'content': f'Mock content {i} for testing purposes',
                'similarity_score': 0.8 - (i * 0.1),
                'metadata': {'source': 'mock', 'index': i}
            }
            for i in range(min(limit, 3))
        ]

class MockKeywordStore:
    """Mock keyword store for testing when real one isn't available"""
    
    def fulltext_search(self, query, limit=10, filters=None):
        # Return mock results
        return [
            {
                'chunk_id': f'mock_kw_chunk_{i}',
                'content': f'Mock keyword content {i} matching {query}',
                'relevance_score': 0.7 - (i * 0.1),
                'metadata': {'source': 'mock_keyword', 'query': query}
            }
            for i in range(min(limit, 2))
        ]

class MockEmbeddingService:
    """Mock embedding service for testing"""
    
    def generate_query_embedding(self, query):
        # Return mock embedding
        return np.random.rand(768).tolist()
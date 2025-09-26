"""
Vector search service for semantic and hybrid search capabilities.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
import logging
from datetime import datetime

from .supabase_client import SupabaseVectorStore
from .embedding_service import EmbeddingService
from ..core.config import settings

logger = logging.getLogger(__name__)

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
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    highlights: Optional[List[str]] = None

class VectorSearchService:
    """Advanced vector search with hybrid capabilities."""
    
    def __init__(self, supabase_client: Optional[SupabaseVectorStore] = None, embedding_service: Optional[EmbeddingService] = None):
        """Initialize the vector search service."""
        self.supabase = supabase_client or SupabaseVectorStore()
        self.embedder = embedding_service or EmbeddingService(cache_client=self.supabase)
        
        # Search configuration
        self.default_similarity_threshold = settings.similarity_threshold
        self.max_results = settings.max_chunks_per_query * 2  # Get more for reranking
        
        logger.info("✅ Vector search service initialized")
    
    def search(
        self,
        query: str,
        search_type: str = "hybrid",
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: Optional[float] = None,
        rerank: bool = True
    ) -> List[SearchResult]:
        """Main search interface supporting multiple search types."""
        
        if not query or not query.strip():
            logger.warning("⚠️ Empty query provided")
            return []
        
        logger.info(f"🔍 Searching: '{query}' (type: {search_type}, results: {num_results})")
        
        # Use configured threshold if not provided
        threshold = similarity_threshold or self.default_similarity_threshold
        
        try:
            if search_type == "semantic":
                results = self.semantic_search(query, num_results * 2, filters, threshold)
            elif search_type == "keyword":
                results = self.keyword_search(query, num_results * 2, filters)
            elif search_type == "hybrid":
                results = self.hybrid_search(query, num_results * 2, filters, threshold)
            elif search_type == "conversational":
                # For conversational queries, use semantic search as fallback
                logger.info("Using semantic search for conversational query")
                results = self.semantic_search(query, num_results * 2, filters, threshold)
            else:
                logger.warning(f"Unknown search type '{search_type}', defaulting to hybrid")
                results = self.hybrid_search(query, num_results * 2, filters, threshold)
            
            # Rerank results if requested and we have multiple results
            if rerank and len(results) > 1:
                results = self.rerank_results(results, query)
            
            # Limit to requested number of results
            results = results[:num_results]
            
            logger.info(f"✅ Search completed: {len(results)} results returned")
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def semantic_search(
        self,
        query: str,
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """Pure semantic search using vector similarity."""
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.generate_query_embedding(query)
            
            if np.all(query_embedding == 0):
                logger.error("❌ Failed to generate query embedding")
                return []
            
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
                    metadata=r.get('metadata', {}),
                    section_title=r.get('section_title'),
                    page_number=r.get('page_number')
                )
                results.append(result)
            
            logger.info(f"🎯 Semantic search: {len(results)} results (threshold: {similarity_threshold})")
            return results
            
        except Exception as e:
            logger.error(f"❌ Semantic search failed: {e}")
            return []
    
    def keyword_search(
        self,
        query: str,
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Traditional keyword-based search using PostgreSQL full-text search."""
        
        try:
            # Process query for better keyword matching
            processed_query = self.process_query_keywords(query)
            
            # Build search parameters
            search_params = {
                'query_text': processed_query,
                'limit_count': num_results
            }
            
            # Add filters if provided
            if filters:
                if filters.get('document_type'):
                    search_params['filter_document_type'] = filters['document_type']
                if filters.get('year'):
                    search_params['filter_year'] = filters['year']
            
            # Execute keyword search using RPC function
            raw_results = self.supabase.client.rpc('keyword_search', search_params).execute()
            
            if not raw_results.data:
                logger.info("🔍 Keyword search: no results found")
                return []
            
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
                    section_title=r.get('section_title'),
                    page_number=r.get('page_number'),
                    highlights=self.extract_highlights(r['content'], query)
                )
                results.append(result)
            
            logger.info(f"📝 Keyword search: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Keyword search failed: {e}")
            return []
    
    def hybrid_search(
        self,
        query: str,
        num_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7,
        vector_weight: float = 0.6
    ) -> List[SearchResult]:
        """Hybrid search combining semantic and keyword search."""
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.generate_query_embedding(query)
            
            if np.all(query_embedding == 0):
                logger.error("❌ Failed to generate query embedding for hybrid search")
                return []
            
            # Execute hybrid search using RPC function
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
                    section_title=r.get('section_title'),
                    page_number=r.get('page_number'),
                    highlights=self.extract_highlights(r['content'], query)
                )
                results.append(result)
            
            logger.info(f"🔀 Hybrid search: {len(results)} results (vector_weight: {vector_weight})")
            return results
            
        except Exception as e:
            logger.error(f"❌ Hybrid search failed: {e}")
            return []
    
    def rerank_results(
        self, 
        results: List[SearchResult], 
        query: str
    ) -> List[SearchResult]:
        """Rerank results using additional signals."""
        
        if len(results) <= 1:
            return results
        
        logger.info(f"📈 Reranking {len(results)} results")
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Calculate additional ranking signals
        for result in results:
            original_score = result.score
            
            # Exact phrase match bonus
            if query_lower in result.content.lower():
                result.score *= 1.3
                logger.debug(f"📍 Exact phrase match bonus for chunk {result.chunk_id}")
            
            # Title match bonus
            if query_lower in result.document_title.lower():
                result.score *= 1.2
                logger.debug(f"📋 Title match bonus for chunk {result.chunk_id}")
            
            # Section title match bonus
            if result.section_title and query_lower in result.section_title.lower():
                result.score *= 1.15
                logger.debug(f"📑 Section title match bonus for chunk {result.chunk_id}")
            
            # Document type relevance
            if result.document_type in ['work_programme', 'call_text', 'programme_guide']:
                result.score *= 1.1
                logger.debug(f"📄 Document type bonus for chunk {result.chunk_id}")
            
            # Keyword density bonus
            content_words = set(result.content.lower().split())
            keyword_overlap = len(query_words.intersection(content_words))
            if keyword_overlap > 0:
                density_bonus = 1 + (keyword_overlap / len(query_words)) * 0.1
                result.score *= density_bonus
                logger.debug(f"🔤 Keyword density bonus ({keyword_overlap}/{len(query_words)}) for chunk {result.chunk_id}")
            
            # Recency bonus (if metadata contains date)
            if 'year' in result.metadata:
                try:
                    year = int(result.metadata['year'])
                    current_year = datetime.now().year
                    if year >= current_year - 2:  # Last 2 years
                        result.score *= 1.05
                        logger.debug(f"📅 Recency bonus for chunk {result.chunk_id}")
                except (ValueError, TypeError):
                    pass
            
            # Content length penalty for very short chunks
            if len(result.content) < 100:
                result.score *= 0.9
                logger.debug(f"📏 Short content penalty for chunk {result.chunk_id}")
            
            logger.debug(f"📊 Reranking: {result.chunk_id} score {original_score:.3f} -> {result.score:.3f}")
        
        # Sort by updated scores
        results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"✅ Reranking completed")
        return results
    
    def process_query_keywords(self, query: str) -> str:
        """Process query for better keyword matching."""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        # Tokenize and filter
        words = query.lower().split()
        filtered = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Handle acronyms and special terms
        special_terms = {
            'ai': 'artificial intelligence',
            'ml': 'machine learning',
            'ict': 'information communication technology',
            'sme': 'small medium enterprise',
            'eu': 'european union',
            'r&d': 'research development',
            'ip': 'intellectual property',
            'iot': 'internet of things'
        }
        
        expanded = []
        for word in filtered:
            if word in special_terms:
                expanded.append(f"({word} OR {special_terms[word]})")
            else:
                expanded.append(word)
        
        processed_query = ' '.join(expanded)
        logger.debug(f"🔤 Query processed: '{query}' -> '{processed_query}'")
        
        return processed_query
    
    def extract_highlights(
        self, 
        content: str, 
        query: str, 
        context_length: int = 150
    ) -> List[str]:
        """Extract highlighted snippets from content."""
        highlights = []
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        
        for word in query_words[:3]:  # Limit to first 3 words
            # Find word occurrences (case insensitive)
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(content))
            
            for match in matches[:2]:  # Max 2 highlights per word
                start = max(0, match.start() - context_length)
                end = min(len(content), match.end() + context_length)
                
                snippet = content[start:end]
                
                # Add ellipsis if truncated
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                
                # Highlight the matched word
                snippet = pattern.sub(f"**{match.group()}**", snippet)
                
                highlights.append(snippet)
                
                # Limit total highlights
                if len(highlights) >= 3:
                    return highlights
        
        return highlights
    
    def get_similar_chunks(
        self,
        chunk_id: str,
        num_similar: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """Find similar chunks to a given chunk."""
        
        try:
            # Get the chunk's embedding and content
            chunk_data = self.supabase.client.table("document_chunks")\
                .select("embedding, content, document_id")\
                .eq("id", chunk_id)\
                .single()\
                .execute()
            
            if not chunk_data.data:
                logger.warning(f"⚠️ Chunk not found: {chunk_id}")
                return []
            
            embedding = np.array(chunk_data.data['embedding'])
            
            # Search for similar chunks
            similar = self.supabase.semantic_search(
                query_embedding=embedding,
                match_threshold=similarity_threshold,
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
                        metadata=r.get('metadata', {}),
                        section_title=r.get('section_title'),
                        page_number=r.get('page_number')
                    )
                    results.append(result)
            
            results = results[:num_similar]
            logger.info(f"🔗 Found {len(results)} similar chunks to {chunk_id}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error finding similar chunks: {e}")
            return []
    
    def search_by_document_type(
        self,
        query: str,
        document_type: str,
        num_results: int = 5,
        search_type: str = "hybrid"
    ) -> List[SearchResult]:
        """Search within a specific document type."""
        
        filters = {'document_type': document_type}
        
        results = self.search(
            query=query,
            search_type=search_type,
            num_results=num_results,
            filters=filters
        )
        
        logger.info(f"📂 Document type search ({document_type}): {len(results)} results")
        return results
    
    def search_by_programme_year(
        self,
        query: str,
        programme_year: str,
        num_results: int = 5,
        search_type: str = "hybrid"
    ) -> List[SearchResult]:
        """Search within a specific programme year."""
        
        filters = {'year': programme_year}
        
        results = self.search(
            query=query,
            search_type=search_type,
            num_results=num_results,
            filters=filters
        )
        
        logger.info(f"📅 Programme year search ({programme_year}): {len(results)} results")
        return results
    
    def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query."""
        
        if len(partial_query) < 3:
            return []
        
        try:
            # Search for documents with titles containing the partial query
            response = self.supabase.client.table("horizon_documents")\
                .select("title")\
                .ilike("title", f"%{partial_query}%")\
                .eq("status", "active")\
                .limit(limit)\
                .execute()
            
            suggestions = []
            if response.data:
                for doc in response.data:
                    title = doc['title']
                    if title and title not in suggestions:
                        suggestions.append(title)
            
            # Also search in chunk content for common phrases
            if len(suggestions) < limit:
                chunk_response = self.supabase.client.table("document_chunks")\
                    .select("content")\
                    .textSearch("content", partial_query)\
                    .limit(limit - len(suggestions))\
                    .execute()
                
                if chunk_response.data:
                    for chunk in chunk_response.data:
                        content = chunk['content']
                        # Extract sentences containing the partial query
                        sentences = content.split('.')
                        for sentence in sentences:
                            if partial_query.lower() in sentence.lower():
                                clean_sentence = sentence.strip()
                                if len(clean_sentence) > 10 and len(clean_sentence) < 100:
                                    suggestions.append(clean_sentence)
                                    if len(suggestions) >= limit:
                                        break
                        if len(suggestions) >= limit:
                            break
            
            logger.info(f"💡 Generated {len(suggestions)} suggestions for '{partial_query}'")
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error generating suggestions: {e}")
            return []
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get statistics about search performance and usage."""
        
        try:
            # Get basic database stats
            db_stats = self.supabase.get_document_stats()
            
            # Get embedding service stats
            embedding_stats = self.embedder.get_embedding_stats()
            
            stats = {
                'database_stats': db_stats,
                'embedding_stats': embedding_stats,
                'search_config': {
                    'default_similarity_threshold': self.default_similarity_threshold,
                    'max_results': self.max_results,
                    'embedding_dimension': self.embedder.embedding_dimension
                },
                'service_status': {
                    'supabase_connected': self.supabase.test_connection(),
                    'embedding_service_ready': self.embedder.test_embedding_generation()
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting search stats: {e}")
            return {'error': str(e)}
"""
Embedding service for generating text embeddings using Google's API.
"""

import os
import hashlib
import numpy as np
from typing import List, Optional, Dict, Any
import google.generativeai as genai
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from functools import lru_cache
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings using Google's API."""
    
    def __init__(self, cache_client=None):
        """Initialize the embedding service."""
        # Use effective_embedding_api_key which falls back to gemini_api_key
        self.api_key = settings.effective_embedding_api_key
        if not self.api_key:
            raise ValueError("Google Embedding API key not found in configuration (set GOOGLE_EMBEDDING_API_KEY or GEMINI_API_KEY)")
        
        # Configure Google AI
        genai.configure(api_key=self.api_key)
        
        # Model configuration
        self.model_name = settings.embedding_model
        self.embedding_dimension = settings.embedding_dimension
        self.batch_size = 100  # Google's API batch limit
        self.cache_client = cache_client  # Supabase client for caching
        
        # Rate limiting configuration
        self.requests_per_minute = 60
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.requests_per_minute
        
        logger.info(f"✅ Embedding service initialized with model: {self.model_name}")
    
    def generate_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for embedding")
            return np.zeros(self.embedding_dimension)
        
        # Check cache first
        if use_cache and self.cache_client:
            text_hash = self.calculate_hash(text)
            cached = self.cache_client.get_cached_embedding(text_hash)
            if cached is not None:
                logger.debug(f"✅ Using cached embedding for text hash: {text_hash[:8]}...")
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
            
            if not result or 'embedding' not in result:
                logger.error("❌ Invalid response from embedding API")
                return np.zeros(self.embedding_dimension)
            
            embedding_array = np.array(result['embedding'], dtype=np.float32)
            
            # Validate embedding
            if not self.validate_embedding(embedding_array):
                logger.error("❌ Invalid embedding generated")
                return np.zeros(self.embedding_dimension)
            
            # Cache the result
            if use_cache and self.cache_client:
                self.cache_client.cache_embedding(text, text_hash, embedding_array)
            
            logger.debug(f"✅ Generated embedding for text ({len(text)} chars)")
            return embedding_array
            
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            return np.zeros(self.embedding_dimension)
    
    def generate_embeddings_batch(
        self, 
        texts: List[str], 
        use_cache: bool = True
    ) -> List[np.ndarray]:
        """Generate embeddings for multiple texts in batches."""
        if not texts:
            logger.warning("⚠️ Empty text list provided for batch embedding")
            return []
        
        embeddings = []
        texts_to_embed = []
        text_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            if not text or not text.strip():
                embeddings.append((i, np.zeros(self.embedding_dimension)))
                continue
                
            if use_cache and self.cache_client:
                text_hash = self.calculate_hash(text)
                cached = self.cache_client.get_cached_embedding(text_hash)
                if cached is not None:
                    embeddings.append((i, cached))
                    continue
            
            texts_to_embed.append(text)
            text_indices.append(i)
        
        logger.info(f"📊 Batch embedding: {len(texts_to_embed)} new, {len(embeddings)} cached")
        
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
                
                if not results or 'embedding' not in results:
                    logger.error("❌ Invalid batch response from embedding API")
                    # Add zero vectors for failed batch
                    for j, original_index in enumerate(batch_indices):
                        embeddings.append((original_index, np.zeros(self.embedding_dimension)))
                    continue
                
                # Handle single embedding vs list of embeddings
                batch_embeddings = results['embedding']
                if not isinstance(batch_embeddings[0], list):
                    # Single embedding returned
                    batch_embeddings = [batch_embeddings]
                
                for j, embedding in enumerate(batch_embeddings):
                    if j >= len(batch_indices):
                        break
                        
                    embedding_array = np.array(embedding, dtype=np.float32)
                    original_index = batch_indices[j]
                    
                    # Validate embedding
                    if not self.validate_embedding(embedding_array):
                        embedding_array = np.zeros(self.embedding_dimension)
                    
                    embeddings.append((original_index, embedding_array))
                    
                    # Cache the result
                    if use_cache and self.cache_client and j < len(batch):
                        text = batch[j]
                        text_hash = self.calculate_hash(text)
                        self.cache_client.cache_embedding(text, text_hash, embedding_array)
                
                logger.info(f"✅ Generated {len(batch_embeddings)} embeddings in batch")
                
            except Exception as e:
                logger.error(f"❌ Error in batch embedding generation: {e}")
                # Fall back to individual generation
                for j, text in enumerate(batch):
                    try:
                        embedding = self.generate_embedding(text, use_cache)
                        original_index = batch_indices[j]
                        embeddings.append((original_index, embedding))
                    except Exception as individual_error:
                        logger.error(f"❌ Individual embedding failed: {individual_error}")
                        # Return zero vector on failure
                        embeddings.append((batch_indices[j], np.zeros(self.embedding_dimension)))
        
        # Sort by original index and return in order
        embeddings.sort(key=lambda x: x[0])
        result_embeddings = [emb for _, emb in embeddings]
        
        logger.info(f"✅ Completed batch embedding for {len(result_embeddings)} texts")
        return result_embeddings
    
    async def generate_embeddings_async(
        self, 
        texts: List[str], 
        max_workers: int = 5
    ) -> List[np.ndarray]:
        """Generate embeddings asynchronously for better performance."""
        if not texts:
            return []
        
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
            
            embeddings = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        result_embeddings = []
        for i, embedding in enumerate(embeddings):
            if isinstance(embedding, Exception):
                logger.error(f"❌ Async embedding failed for text {i}: {embedding}")
                result_embeddings.append(np.zeros(self.embedding_dimension))
            else:
                result_embeddings.append(embedding)
        
        logger.info(f"✅ Completed async embedding for {len(result_embeddings)} texts")
        return result_embeddings
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a search query."""
        if not query or not query.strip():
            logger.warning("⚠️ Empty query provided for embedding")
            return np.zeros(self.embedding_dimension)
        
        # Rate limiting
        self._rate_limit()
        
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"  # Different task type for queries
            )
            
            if not result or 'embedding' not in result:
                logger.error("❌ Invalid response from query embedding API")
                return np.zeros(self.embedding_dimension)
            
            embedding_array = np.array(result['embedding'], dtype=np.float32)
            
            # Validate embedding
            if not self.validate_embedding(embedding_array):
                logger.error("❌ Invalid query embedding generated")
                return np.zeros(self.embedding_dimension)
            
            logger.debug(f"✅ Generated query embedding ({len(query)} chars)")
            return embedding_array
            
        except Exception as e:
            logger.error(f"❌ Error generating query embedding: {e}")
            return np.zeros(self.embedding_dimension)
    
    def _rate_limit(self):
        """Implement rate limiting to avoid API throttling."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"⏱️ Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def calculate_hash(self, text: str) -> str:
        """Calculate hash for text caching."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """Validate embedding dimensions and values."""
        if embedding.shape[0] != self.embedding_dimension:
            logger.error(f"❌ Invalid embedding dimension: {embedding.shape[0]} != {self.embedding_dimension}")
            return False
        
        # Check for NaN or infinite values
        if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
            logger.error("❌ Embedding contains NaN or infinite values")
            return False
        
        # Check if embedding is not all zeros (unless it's intentionally a zero vector)
        if np.all(embedding == 0):
            logger.warning("⚠️ Embedding is all zeros")
            return True  # Allow zero vectors as they might be intentional fallbacks
        
        # Check if embedding has reasonable magnitude
        magnitude = np.linalg.norm(embedding)
        if magnitude < 1e-6 or magnitude > 100:
            logger.warning(f"⚠️ Unusual embedding magnitude: {magnitude}")
        
        return True
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about embedding generation."""
        stats = {
            'model_name': self.model_name,
            'embedding_dimension': self.embedding_dimension,
            'batch_size': self.batch_size,
            'requests_per_minute': self.requests_per_minute,
            'cache_enabled': self.cache_client is not None
        }
        
        if self.cache_client:
            try:
                # Get cache statistics from Supabase
                cache_stats = self.cache_client.client.table("embedding_cache")\
                    .select("count", count="exact")\
                    .execute()
                stats['cached_embeddings'] = cache_stats.count or 0
            except Exception as e:
                logger.error(f"❌ Error getting cache stats: {e}")
                stats['cached_embeddings'] = 0
        
        return stats
    
    def clear_cache(self, older_than_days: int = 30) -> int:
        """Clear old cached embeddings."""
        if not self.cache_client:
            logger.warning("⚠️ No cache client available")
            return 0
        
        try:
            deleted_count = self.cache_client.cleanup_old_cache(older_than_days)
            logger.info(f"✅ Cleared {deleted_count} old cache entries")
            return deleted_count
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}")
            return 0
    
    def test_embedding_generation(self) -> bool:
        """Test embedding generation with a simple text."""
        try:
            test_text = "This is a test document for Horizon Europe funding."
            embedding = self.generate_embedding(test_text, use_cache=False)
            
            if self.validate_embedding(embedding):
                logger.info("✅ Embedding generation test passed")
                return True
            else:
                logger.error("❌ Embedding generation test failed - invalid embedding")
                return False
                
        except Exception as e:
            logger.error(f"❌ Embedding generation test failed: {e}")
            return False
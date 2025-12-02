"""
Cross-Encoder Reranker for neural reranking of search results.

Uses a cross-encoder model to score query-document pairs and reorder
results by relevance. This provides higher quality ranking than
bi-encoder similarity scores.

Models supported:
- cross-encoder/ms-marco-MiniLM-L-6-v2 (fast, good accuracy)
- cross-encoder/ms-marco-electra-base (slower, better accuracy)

Usage:
    from app.services.data_intelligence.cross_encoder_reranker import CrossEncoderReranker
    
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(query, documents, top_k=10)
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

# Lazy import for sentence_transformers (heavy dependency)
CrossEncoder = None


def _load_cross_encoder():
    """Lazy load the CrossEncoder class."""
    global CrossEncoder
    if CrossEncoder is None:
        try:
            from sentence_transformers import CrossEncoder as CE
            CrossEncoder = CE
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            CrossEncoder = None
    return CrossEncoder


@dataclass
class RankedDocument:
    """A document with its reranking score."""
    content: str
    original_data: Dict[str, Any]
    original_score: float
    rerank_score: float
    original_rank: int
    new_rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.original_data,
            "content": self.content,
            "original_score": self.original_score,
            "rerank_score": self.rerank_score,
            "original_rank": self.original_rank,
            "new_rank": self.new_rank
        }


class CrossEncoderReranker:
    """
    Neural reranker using cross-encoder models.
    
    Provides accurate relevance scoring by processing query-document
    pairs through a transformer model.
    """
    
    # Available models (fast to slow, lower to higher accuracy)
    MODELS = {
        "fast": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "balanced": "cross-encoder/ms-marco-TinyBERT-L-2-v2",
        "accurate": "cross-encoder/ms-marco-electra-base",
    }
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        model_type: str = "fast",
        max_length: int = 512,
        device: str = "cpu"
    ):
        """
        Initialize the Cross-Encoder Reranker.
        
        Args:
            model_name: Specific model name (overrides model_type)
            model_type: One of "fast", "balanced", "accurate"
            max_length: Maximum sequence length for tokenization
            device: Device to run on ("cpu" or "cuda")
        """
        self.model_name = model_name or self.MODELS.get(model_type, self.MODELS["fast"])
        self.max_length = max_length
        self.device = device
        self.model = None
        self._model_loaded = False
        
        # Lazy load - don't load model until first use
        self._initialized = False
    
    def _ensure_model_loaded(self) -> bool:
        """Ensure the model is loaded (lazy loading)."""
        if self._initialized:
            return self._model_loaded
        
        self._initialized = True
        
        CE = _load_cross_encoder()
        if CE is None:
            logger.warning("⚠️ CrossEncoder not available - reranking will be skipped")
            return False
        
        logger.info(f"Loading cross-encoder model: {self.model_name}")
        
        try:
            self.model = CE(
                self.model_name,
                max_length=self.max_length,
                device=self.device
            )
            self._model_loaded = True
            logger.info(f"✅ Cross-encoder model loaded on {self.device}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load cross-encoder: {e}")
            self._model_loaded = False
            return False
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        content_key: str = "content",
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None
    ) -> List[RankedDocument]:
        """
        Rerank documents based on query relevance.
        
        Args:
            query: The search query
            documents: List of documents to rerank (each should have content)
            content_key: Key in document dict containing the text content
            top_k: Maximum number of results to return
            score_threshold: Minimum score to include (sigmoid-like, 0-1)
            
        Returns:
            List of RankedDocument objects ordered by rerank_score
        """
        if not documents:
            return []
        
        if not self._ensure_model_loaded():
            logger.warning("Reranker not available, returning original order")
            return self._create_passthrough_results(documents, content_key)
        
        start_time = time.time()
        
        try:
            # Extract content from documents
            pairs = []
            valid_docs = []
            
            for i, doc in enumerate(documents):
                content = self._extract_content(doc, content_key)
                if content:
                    pairs.append((query, content))
                    valid_docs.append((i, doc, content))
            
            if not pairs:
                return []
            
            # Score all pairs
            scores = self.model.predict(pairs, show_progress_bar=False)
            
            # Create ranked documents
            ranked_docs = []
            for (original_rank, doc, content), score in zip(valid_docs, scores):
                ranked_docs.append(RankedDocument(
                    content=content,
                    original_data=doc,
                    original_score=doc.get("score", doc.get("similarity", 0)),
                    rerank_score=float(score),
                    original_rank=original_rank + 1,
                    new_rank=0  # Will be set after sorting
                ))
            
            # Sort by rerank score (descending)
            ranked_docs.sort(key=lambda x: x.rerank_score, reverse=True)
            
            # Apply threshold filter
            if score_threshold is not None:
                ranked_docs = [d for d in ranked_docs if d.rerank_score >= score_threshold]
            
            # Apply top_k
            if top_k is not None:
                ranked_docs = ranked_docs[:top_k]
            
            # Set new ranks
            for i, doc in enumerate(ranked_docs):
                doc.new_rank = i + 1
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"Reranked {len(documents)} docs → {len(ranked_docs)} results ({duration:.0f}ms)")
            
            return ranked_docs
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return self._create_passthrough_results(documents, content_key)
    
    def rerank_with_fusion(
        self,
        query: str,
        results_list: List[List[Dict[str, Any]]],
        content_key: str = "content",
        top_k: int = 10,
        deduplicate: bool = True
    ) -> List[RankedDocument]:
        """
        Rerank and fuse results from multiple sources.
        
        Args:
            query: The search query
            results_list: List of result lists from different sources
            content_key: Key containing text content
            top_k: Maximum results to return
            deduplicate: Remove duplicate content
            
        Returns:
            Fused and reranked documents
        """
        # Flatten results
        all_docs = []
        for source_results in results_list:
            all_docs.extend(source_results)
        
        # Deduplicate if requested
        if deduplicate:
            all_docs = self._deduplicate(all_docs, content_key)
        
        # Rerank the combined set
        return self.rerank(query, all_docs, content_key, top_k)
    
    def _extract_content(self, doc: Dict[str, Any], content_key: str) -> str:
        """Extract text content from document."""
        
        # Try the specified key first
        content = doc.get(content_key)
        if content:
            return str(content)[:self.max_length * 4]  # Rough char limit
        
        # Try common alternatives
        for key in ["text", "body", "description", "summary", "objective"]:
            content = doc.get(key)
            if content:
                return str(content)[:self.max_length * 4]
        
        # For graph results, construct content from available fields
        if "title" in doc or "name" in doc:
            parts = []
            for key in ["title", "name", "acronym", "description", "objective"]:
                if doc.get(key):
                    parts.append(f"{key}: {doc[key]}")
            if parts:
                return " | ".join(parts)[:self.max_length * 4]
        
        return ""
    
    def _deduplicate(
        self,
        documents: List[Dict[str, Any]],
        content_key: str,
        similarity_threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """Remove near-duplicate documents based on content."""
        
        seen_content = set()
        unique_docs = []
        
        for doc in documents:
            content = self._extract_content(doc, content_key)
            
            # Simple hash-based dedup (exact matches)
            content_hash = hash(content.lower().strip()[:500])
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_docs.append(doc)
        
        if len(unique_docs) < len(documents):
            logger.debug(f"Deduped {len(documents)} → {len(unique_docs)} documents")
        
        return unique_docs
    
    def _create_passthrough_results(
        self,
        documents: List[Dict[str, Any]],
        content_key: str
    ) -> List[RankedDocument]:
        """Create results without reranking (passthrough mode)."""
        
        results = []
        for i, doc in enumerate(documents):
            content = self._extract_content(doc, content_key)
            original_score = doc.get("score", doc.get("similarity", 0))
            
            results.append(RankedDocument(
                content=content,
                original_data=doc,
                original_score=original_score,
                rerank_score=original_score,  # Use original score
                original_rank=i + 1,
                new_rank=i + 1
            ))
        
        return results
    
    def score_pair(self, query: str, document: str) -> float:
        """
        Score a single query-document pair.
        
        Args:
            query: Query text
            document: Document text
            
        Returns:
            Relevance score
        """
        if not self._ensure_model_loaded():
            return 0.0
        
        try:
            scores = self.model.predict([(query, document)])
            return float(scores[0])
        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return 0.0
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "model_loaded": self._model_loaded,
            "max_length": self.max_length,
            "device": self.device
        }


# Singleton instance for reuse
_reranker_instance: Optional[CrossEncoderReranker] = None


def get_reranker(model_type: str = "fast") -> CrossEncoderReranker:
    """Get or create a shared reranker instance."""
    global _reranker_instance
    
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker(model_type=model_type)
    
    return _reranker_instance


if __name__ == "__main__":
    # Test the reranker
    print("\n" + "=" * 60)
    print("CROSS-ENCODER RERANKER TEST")
    print("=" * 60 + "\n")
    
    reranker = CrossEncoderReranker(model_type="fast")
    print(f"Model info: {reranker.get_model_info()}")
    
    # Test documents
    query = "What is the budget for climate research projects?"
    documents = [
        {"content": "Horizon Europe funds research with budgets up to 10 million euros.", "source": "doc1", "score": 0.8},
        {"content": "The climate cluster focuses on energy transition.", "source": "doc2", "score": 0.7},
        {"content": "Budget allocation for research infrastructure projects.", "source": "doc3", "score": 0.9},
        {"content": "Climate research funding in the EU is substantial.", "source": "doc4", "score": 0.6},
    ]
    
    print(f"\nQuery: {query}")
    print(f"Documents: {len(documents)}")
    print("\nOriginal order:")
    for i, doc in enumerate(documents):
        print(f"  {i+1}. [score: {doc['score']}] {doc['content'][:50]}...")
    
    # Rerank
    print("\nReranking...")
    results = reranker.rerank(query, documents, top_k=3)
    
    print("\nReranked results:")
    for r in results:
        print(f"  [{r.original_rank} → {r.new_rank}] Rerank Score: {r.rerank_score:.3f} (was {r.original_score})")
        print(f"      {r.content[:60]}...")
    
    print("\n" + "=" * 60)
    print("✅ Cross-Encoder Reranker test complete!")
    print("=" * 60)


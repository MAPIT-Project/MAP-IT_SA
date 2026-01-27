import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import redis

from .hybrid_search import HybridSearchPipeline, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RetrievalContext:
    """Context for retrieval operations"""

    conversation_id: int
    current_query: str
    conversation_summary: str
    recent_topics: list[str]
    entity_mentions: list[str]
    search_history: list[str]


class ConversationAwareRetriever:
    """
    Retrieval system that understands conversation context
    and caches results for efficiency.
    """

    def __init__(
        self, hybrid_search: HybridSearchPipeline, cache_client: redis.Redis, cache_ttl: int = 3600
    ):
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

    async def retrieve(
        self, context: RetrievalContext, max_chunks: int = 4, use_cache: bool = True
    ) -> list[dict[str, Any]]:
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
            cached_results = self._get_cached_results(context.conversation_id, enhanced_query)
            if cached_results:
                return cached_results

        # Perform retrieval
        search_results = await self.hybrid_search.search(
            query=enhanced_query,
            filters=self._build_filters(context),
            limit=max_chunks,
            use_reranking=True,
        )

        # Process and enrich results
        enriched_results = self._enrich_results(search_results, context)

        # Cache results
        if use_cache:
            self._cache_results(context.conversation_id, enhanced_query, enriched_results)

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
                entity
                for entity in context.entity_mentions
                if any(word in query_lower for word in entity.lower().split())
            ]
            if relevant_entities:
                entity_context = f"Entities: {', '.join(relevant_entities[:2])}"
                enhanced_parts.append(entity_context)

        # Add summary context if query seems to reference previous discussion
        reference_indicators = ["that", "it", "this", "mentioned", "discussed", "previous"]
        if any(indicator in context.current_query.lower() for indicator in reference_indicators):
            if context.conversation_summary:
                # Extract key phrases from summary
                summary_snippet = context.conversation_summary[:200]
                enhanced_parts.append(f"Context: {summary_snippet}")

        # Combine parts
        enhanced_query = " | ".join(enhanced_parts)

        return enhanced_query

    def _build_filters(self, context: RetrievalContext) -> dict[str, Any]:
        """
        Build metadata filters based on context.
        """
        filters = {}

        # Add topic filters if specific domains are discussed
        domain_keywords = {
            "energy": ["renewable", "solar", "wind", "nuclear"],
            "health": ["medical", "clinical", "patient", "disease"],
            "digital": ["AI", "software", "data", "cyber"],
            "climate": ["carbon", "emission", "sustainability", "green"],
        }

        # Check which domains are relevant
        all_text = " ".join(
            [
                context.current_query,
                " ".join(context.recent_topics),
                context.conversation_summary[:500] if context.conversation_summary else "",
            ]
        ).lower()

        relevant_domains = []
        for domain, keywords in domain_keywords.items():
            if any(keyword in all_text for keyword in keywords):
                relevant_domains.append(domain)

        if relevant_domains:
            filters["domain"] = relevant_domains

        # Add temporal filters if dates are mentioned
        current_year = datetime.now().year
        if (
            str(current_year) in context.current_query
            or str(current_year + 1) in context.current_query
        ):
            filters["year"] = [current_year, current_year + 1]

        return filters

    def _enrich_results(
        self, search_results: list[SearchResult], context: RetrievalContext
    ) -> list[dict[str, Any]]:
        """
        Enrich search results with additional context.
        """
        enriched = []

        for result in search_results:
            enriched_result = result.to_dict()

            # Add relevance explanation
            enriched_result["relevance_explanation"] = self._explain_relevance(result, context)

            # Add citation format
            enriched_result["citation"] = self._format_citation(result)

            # Mark if this chunk was previously retrieved
            enriched_result["previously_retrieved"] = self._was_previously_retrieved(
                context.conversation_id, result.chunk_id
            )

            enriched.append(enriched_result)

        return enriched

    def _explain_relevance(self, result: SearchResult, context: RetrievalContext) -> str:
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
        if (
            result.metadata.get("chunk_type") == "objective"
            and "objective" in context.current_query.lower()
        ):
            explanations.append("Contains objective information")
        elif result.metadata.get("chunk_type") == "financial" and any(
            word in context.current_query.lower() for word in ["budget", "cost", "funding"]
        ):
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

        if metadata.get("document_title"):
            parts.append(metadata["document_title"])

        if metadata.get("document_id"):
            parts.append(f"Doc ID: {metadata['document_id'][:8]}")

        if metadata.get("chunk_index") is not None:
            parts.append(f"Section {metadata['chunk_index'] + 1}")

        if metadata.get("page_number"):
            parts.append(f"Page {metadata['page_number']}")

        return " | ".join(parts) if parts else f"Chunk {result.chunk_id[:8]}"

    def _get_cached_results(self, conversation_id: int, query: str) -> list[dict[str, Any]] | None:
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
            logger.info(f"Cache retrieval error: {e}")
            return None

    def _cache_results(self, conversation_id: int, query: str, results: list[dict[str, Any]]):
        """
        Cache retrieval results.
        """
        try:
            cache_key = self._generate_cache_key(conversation_id, query)

            # Store results
            self.cache.setex(cache_key, self.cache_ttl, json.dumps(results))

            # Track retrieval history
            history_key = f"retrieval_history:{conversation_id}"
            self.cache.lpush(history_key, query)
            self.cache.ltrim(history_key, 0, 19)  # Keep last 20 queries
            self.cache.expire(history_key, 86400)  # 24 hour TTL

            # Track retrieved chunks
            for result in results:
                chunk_key = f"retrieved_chunks:{conversation_id}"
                self.cache.sadd(chunk_key, result["chunk_id"])
                self.cache.expire(chunk_key, 86400)

        except Exception as e:
            logger.info(f"Cache storage error: {e}")

    def _was_previously_retrieved(self, conversation_id: int, chunk_id: str) -> bool:
        """
        Check if chunk was previously retrieved in this conversation.
        """
        try:
            chunk_key = f"retrieved_chunks:{conversation_id}"
            return self.cache.sismember(chunk_key, chunk_id)
        except Exception:
            return False

    def _generate_cache_key(self, conversation_id: int, query: str) -> str:
        """
        Generate cache key for query results.
        """
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"retrieval_cache:{conversation_id}:{query_hash}"

    def get_retrieval_stats(self, conversation_id: int) -> dict[str, Any]:
        """
        Get statistics about retrieval for a conversation.
        """
        try:
            history_key = f"retrieval_history:{conversation_id}"
            chunk_key = f"retrieved_chunks:{conversation_id}"

            query_history = self.cache.lrange(history_key, 0, -1)
            unique_chunks = self.cache.scard(chunk_key)

            return {
                "total_queries": len(query_history),
                "unique_chunks_retrieved": unique_chunks,
                "recent_queries": [
                    q.decode() if isinstance(q, bytes) else q for q in query_history[:5]
                ],
            }
        except Exception:
            return {"total_queries": 0, "unique_chunks_retrieved": 0, "recent_queries": []}

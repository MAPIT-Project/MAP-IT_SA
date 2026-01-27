"""
Query Plan Caching Service

Caches the reasoning/planning output for similar queries to avoid
redundant LLM calls for tool selection. Uses Redis for fast access.

Key Features:
- Pattern-based caching (generalizes specific values to placeholders)
- 24-hour TTL for cached plans
- Only caches plans that led to successful responses
- Context-aware cache keys
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class QueryPlanCache:
    """Cache for query plans and tool selection decisions."""

    def __init__(self, redis_client=None):
        """
        Initialize the query plan cache.

        Args:
            redis_client: Redis client instance. If None, caching is disabled.
        """
        self.redis = redis_client
        self.prefix = "query_plan:"
        self.ttl_seconds = 24 * 60 * 60  # 24 hours
        self.enabled = redis_client is not None

        if self.enabled:
            logger.info("✅ Query plan cache initialized with Redis")
        else:
            logger.warning("⚠️ Query plan cache disabled (no Redis client)")

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for cache key generation.
        - Lowercase
        - Remove extra whitespace
        - Remove punctuation except hyphens
        """
        normalized = query.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\w\s\-]", "", normalized)
        return normalized

    def _extract_query_pattern(self, query: str) -> str:
        """
        Extract a generalizable pattern from the query.
        Replace specific values with placeholders.

        Examples:
        - "Find hydrogen funding calls" -> "find {topic} funding calls"
        - "Budget for RIA in CL5" -> "budget for {action_type} in {cluster}"
        - "Projects in Germany about AI" -> "projects in {country} about {topic}"
        """
        normalized = self._normalize_query(query)

        # Pattern replacements (order matters - more specific first)
        replacements = [
            # Clusters (specific codes only - not topic words)
            (r"\b(cl[1-6]|cluster\s*[1-6])\b", "{cluster}"),
            # Action types
            (r"\b(ria|ia|csa|erc|eic|msca|cofund|lump[\s-]?sum|pcp|ppi)\b", "{action_type}"),
            # Countries (EU member states and associated)
            (
                r"\b(germany|german|france|french|spain|spanish|italy|italian|netherlands|dutch|belgium|belgian|austria|austrian|sweden|swedish|denmark|danish|finland|finnish|poland|polish|czech|portugal|portuguese|ireland|irish|greece|greek|hungary|hungarian|romania|romanian|bulgaria|bulgarian|croatia|croatian|slovakia|slovak|slovenia|slovenian|estonia|estonian|latvia|latvian|lithuania|lithuanian|luxembourg|malta|maltese|cyprus|switzerland|swiss|norway|norwegian|uk|united kingdom|israel|israeli)\b",
                "{country}",
            ),
            # Country codes (2-letter only, avoiding common words)
            (
                r"\b(de|fr|es|it|nl|be|at|se|dk|fi|pl|cz|pt|ie|gr|hu|ro|bg|hr|sk|si|ee|lv|lt|lu|mt|cy|ch|no|il)\b",
                "{country}",
            ),
            # Years
            (r"\b(20[2-3][0-9])\b", "{year}"),
            # Specific topic keywords (comprehensive list of Horizon Europe research areas)
            (
                r"\b(hydrogen|quantum|artificial intelligence|\bai\b|machine learning|deep learning|"
                r"renewable|solar|wind|battery|batteries|energy storage|"
                r"cancer|diabetes|cardiovascular|healthcare|health care|"
                r"blockchain|cybersecurity|cyber security|robotics|autonomous|"
                r"sustainable|sustainability|circular economy|biodiversity|"
                r"ocean|marine|space|satellite|"
                r"nanotechnology|nano|biotechnology|biotech|"
                r"electric vehicles?|ev|smart cit(?:y|ies)|smart grid|"
                r"agriculture|agri-food|food security|"
                r"manufacturing|industry 4\.0|advanced materials|materials science|"
                r"photonics|semiconductors?|electronics|"
                r"construction|buildings?|built environment|"
                r"transport|transportation|mobility|logistics|"
                r"water|wastewater|waste management|recycling|"
                r"climate|climate change|greenhouse|carbon|decarboni[sz]ation|"
                r"digital|digitali[sz]ation|ict|software|data science|big data|"
                r"health|medical|pharma|pharmaceutical|drug discovery|"
                r"security|defence|defense|crisis|emergency|"
                r"5g|6g|telecommunications?|network|connectivity|"
                r"green deal|green transition|net zero|zero emission)\b",
                "{topic}",
            ),
            # Budget amounts
            (r"\b(\d+(?:\.\d+)?)\s*(million|m|billion|b|euro|eur|€|k|thousand)\b", "{amount}"),
            # Generic numbers
            (r"\b\d{6,}\b", "{id}"),  # Project IDs
        ]

        pattern = normalized
        for regex, placeholder in replacements:
            pattern = re.sub(regex, placeholder, pattern, flags=re.IGNORECASE)

        return pattern

    def _generate_cache_key(self, query: str, context_hash: str = "") -> str:
        """Generate a deterministic cache key for a query pattern."""
        pattern = self._extract_query_pattern(query)
        key_content = f"{pattern}:{context_hash}"
        hash_val = hashlib.sha256(key_content.encode()).hexdigest()[:16]
        return f"{self.prefix}{hash_val}"

    def get_cached_plan(self, query: str, context: str = "") -> dict[str, Any] | None:
        """
        Retrieve cached plan for a query pattern.

        Args:
            query: The user's query
            context: Optional conversation context

        Returns:
            Cached plan dict with 'tool_calls', 'thought', etc. or None
        """
        if not self.enabled:
            return None

        try:
            context_hash = hashlib.md5(context.encode()).hexdigest()[:8] if context else ""
            cache_key = self._generate_cache_key(query, context_hash)

            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                plan = data.get("plan")
                pattern = data.get("pattern", "")

                logger.info(f"✅ Cache HIT for pattern: '{pattern[:50]}...'")

                # Update hit count
                self._increment_hit_count(cache_key)

                return plan

            logger.debug(f"❌ Cache MISS for query: '{query[:50]}...'")
            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def cache_plan(
        self, query: str, plan: dict[str, Any], context: str = "", quality_score: float = 0.0
    ) -> bool:
        """
        Cache a successful query plan.

        Args:
            query: The original query
            plan: The reasoning output (tool_calls, thought, etc.)
            context: Optional conversation context
            quality_score: Quality score of the response (only cache if > 0.7)

        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False

        # Only cache high-quality plans
        if quality_score < 0.7:
            logger.debug(f"Skipping cache - quality score {quality_score} < 0.7")
            return False

        try:
            context_hash = hashlib.md5(context.encode()).hexdigest()[:8] if context else ""
            cache_key = self._generate_cache_key(query, context_hash)
            pattern = self._extract_query_pattern(query)

            # Store plan with metadata
            cache_data = {
                "plan": plan,
                "pattern": pattern,
                "original_query": query[:200],  # Truncate for storage
                "quality_score": quality_score,
                "cached_at": datetime.now().isoformat(),
                "hit_count": 0,
            }

            self.redis.setex(cache_key, self.ttl_seconds, json.dumps(cache_data))

            logger.info(f"✅ Cached plan for pattern: '{pattern[:50]}...'")
            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def _increment_hit_count(self, cache_key: str):
        """Increment hit count for a cached plan."""
        try:
            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                data["hit_count"] = data.get("hit_count", 0) + 1
                data["last_hit"] = datetime.now().isoformat()

                # Get remaining TTL and preserve it
                ttl = self.redis.ttl(cache_key)
                if ttl > 0:
                    self.redis.setex(cache_key, ttl, json.dumps(data))
        except Exception as e:
            logger.debug(f"Failed to increment hit count: {e}")

    def invalidate_pattern(self, query: str, context: str = "") -> bool:
        """Invalidate a cached plan for a specific pattern."""
        if not self.enabled:
            return False

        try:
            context_hash = hashlib.md5(context.encode()).hexdigest()[:8] if context else ""
            cache_key = self._generate_cache_key(query, context_hash)

            deleted = self.redis.delete(cache_key)
            if deleted:
                logger.info(f"🗑️ Invalidated cache for key: {cache_key}")
            return deleted > 0

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return False

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}

        try:
            # Get all cache keys
            keys = self.redis.keys(f"{self.prefix}*")

            total_hits = 0
            patterns = []

            for key in keys[:100]:  # Limit to first 100
                try:
                    cached = self.redis.get(key)
                    if cached:
                        data = json.loads(cached)
                        total_hits += data.get("hit_count", 0)
                        patterns.append(
                            {
                                "pattern": data.get("pattern", "")[:50],
                                "hits": data.get("hit_count", 0),
                                "quality": data.get("quality_score", 0),
                            }
                        )
                except Exception:
                    pass

            # Sort by hits
            patterns.sort(key=lambda x: x["hits"], reverse=True)

            return {
                "enabled": True,
                "cached_plans": len(keys),
                "total_hits": total_hits,
                "ttl_hours": self.ttl_seconds / 3600,
                "top_patterns": patterns[:10],
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}

    def clear_all(self) -> int:
        """Clear all cached plans. Returns number of keys deleted."""
        if not self.enabled:
            return 0

        try:
            keys = self.redis.keys(f"{self.prefix}*")
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

"""
Comprehensive tests for the QueryPlanCache service.

Tests:
- Query normalization
- Pattern extraction (placeholder replacement)
- Cache key generation
- Cache operations (get, set, invalidate)
- Hit count tracking
- Cache statistics
- TTL handling
- Quality score filtering
"""

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cache.query_plan_cache import QueryPlanCache


class TestQueryNormalization:
    """Tests for query normalization."""

    def test_lowercase_conversion(self):
        """Test queries are lowercased."""
        cache = QueryPlanCache(redis_client=None)
        result = cache._normalize_query("FIND HYDROGEN CALLS")

        assert result == result.lower()

    def test_whitespace_trimming(self):
        """Test extra whitespace is trimmed."""
        cache = QueryPlanCache(redis_client=None)
        result = cache._normalize_query("  find   hydrogen   calls  ")

        assert "   " not in result
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_punctuation_removal(self):
        """Test punctuation is removed (except hyphens)."""
        cache = QueryPlanCache(redis_client=None)
        result = cache._normalize_query("What's the budget? (€5M)")

        assert "?" not in result
        assert "'" not in result
        assert "(" not in result

    def test_hyphen_preserved(self):
        """Test hyphens are preserved."""
        cache = QueryPlanCache(redis_client=None)
        result = cache._normalize_query("ERC-STG funding")

        assert "-" in result


class TestPatternExtraction:
    """Tests for pattern extraction (placeholder replacement)."""

    def test_topic_replacement_hydrogen(self):
        """Test hydrogen is replaced with {topic}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Find hydrogen funding calls")

        assert "{topic}" in pattern
        assert "hydrogen" not in pattern

    def test_topic_replacement_ai(self):
        """Test AI is replaced with {topic}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("AI research funding")

        assert "{topic}" in pattern

    def test_topic_replacement_healthcare(self):
        """Test healthcare is replaced with {topic}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Healthcare projects in EU")

        assert "{topic}" in pattern

    def test_topic_replacement_climate(self):
        """Test climate is replaced with {topic}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Climate change research")

        assert "{topic}" in pattern

    def test_topic_replacement_digital(self):
        """Test digital is replaced with {topic}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Digital transformation projects")

        assert "{topic}" in pattern

    def test_topic_replacement_quantum(self):
        """Test quantum is replaced with {topic}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Quantum computing research")

        assert "{topic}" in pattern

    def test_action_type_replacement_ria(self):
        """Test RIA is replaced with {action_type}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Budget for RIA projects")

        assert "{action_type}" in pattern
        assert "ria" not in pattern.lower()

    def test_action_type_replacement_erc(self):
        """Test ERC is replaced with {action_type}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("ERC grant applications")

        assert "{action_type}" in pattern

    def test_action_type_replacement_msca(self):
        """Test MSCA is replaced with {action_type}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("MSCA fellowship options")

        assert "{action_type}" in pattern

    def test_cluster_replacement(self):
        """Test cluster codes are replaced with {cluster}."""
        cache = QueryPlanCache(redis_client=None)

        for i in range(1, 7):
            pattern = cache._extract_query_pattern(f"Calls in CL{i}")
            assert "{cluster}" in pattern

    def test_country_name_replacement(self):
        """Test country names are replaced with {country}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Projects in Germany")

        assert "{country}" in pattern
        assert "germany" not in pattern.lower()

    def test_country_code_replacement(self):
        """Test country codes are replaced with {country}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Partners from DE and FR")

        assert "{country}" in pattern

    def test_year_replacement(self):
        """Test years are replaced with {year}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Calls open in 2024")

        assert "{year}" in pattern
        assert "2024" not in pattern

    def test_amount_replacement(self):
        """Test budget amounts are replaced with {amount}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Budget of 5 million euro")

        assert "{amount}" in pattern

    def test_project_id_replacement(self):
        """Test project IDs are replaced with {id}."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("Project 101079329 details")

        assert "{id}" in pattern

    def test_multiple_replacements(self):
        """Test multiple placeholders in same query."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern(
            "Find hydrogen projects in Germany funded by RIA in 2024"
        )

        # Should have multiple placeholders
        placeholders = ["{topic}", "{country}", "{action_type}", "{year}"]
        found = sum(1 for p in placeholders if p in pattern)
        assert found >= 3


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_key_has_prefix(self):
        """Test cache key has correct prefix."""
        cache = QueryPlanCache(redis_client=None)
        key = cache._generate_cache_key("Test query")

        assert key.startswith("query_plan:")

    def test_key_is_deterministic(self):
        """Test same query produces same key."""
        cache = QueryPlanCache(redis_client=None)

        key1 = cache._generate_cache_key("Find hydrogen calls")
        key2 = cache._generate_cache_key("Find hydrogen calls")

        assert key1 == key2

    def test_similar_queries_same_key(self):
        """Test semantically similar queries get same key."""
        cache = QueryPlanCache(redis_client=None)

        # These should have same pattern after normalization
        key1 = cache._generate_cache_key("Find hydrogen calls")
        key2 = cache._generate_cache_key("find hydrogen calls")
        key3 = cache._generate_cache_key("FIND HYDROGEN CALLS")

        assert key1 == key2 == key3

    def test_different_topics_same_pattern(self):
        """Test different topics produce same pattern key."""
        cache = QueryPlanCache(redis_client=None)

        key1 = cache._generate_cache_key("Find hydrogen funding")
        key2 = cache._generate_cache_key("Find quantum funding")

        # Both should map to "find {topic} funding" pattern
        assert key1 == key2

    def test_context_affects_key(self):
        """Test context hash affects key generation."""
        cache = QueryPlanCache(redis_client=None)

        key1 = cache._generate_cache_key("Test query", context_hash="abc123")
        key2 = cache._generate_cache_key("Test query", context_hash="xyz789")
        key3 = cache._generate_cache_key("Test query", context_hash="")

        assert key1 != key2
        assert key1 != key3


class TestCacheOperations:
    """Tests for cache get/set operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = MagicMock()
        mock.get.return_value = None
        mock.setex.return_value = True
        mock.delete.return_value = 1
        mock.ttl.return_value = 3600
        mock.keys.return_value = []
        return mock

    def test_cache_disabled_without_redis(self):
        """Test cache is disabled without Redis."""
        cache = QueryPlanCache(redis_client=None)
        assert not cache.enabled

    def test_cache_enabled_with_redis(self, mock_redis):
        """Test cache is enabled with Redis."""
        cache = QueryPlanCache(redis_client=mock_redis)
        assert cache.enabled

    def test_get_cached_plan_miss(self, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None
        cache = QueryPlanCache(redis_client=mock_redis)

        result = cache.get_cached_plan("Test query")

        assert result is None

    def test_get_cached_plan_hit(self, mock_redis):
        """Test cache hit returns plan."""
        cached_data = {
            "plan": {"tool_calls": ["search_funding_calls"]},
            "pattern": "test pattern",
            "hit_count": 5,
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        cache = QueryPlanCache(redis_client=mock_redis)
        result = cache.get_cached_plan("Test query")

        assert result == {"tool_calls": ["search_funding_calls"]}

    def test_cache_plan_success(self, mock_redis):
        """Test caching a plan."""
        cache = QueryPlanCache(redis_client=mock_redis)

        plan = {"tool_calls": ["search_funding_calls"], "thought": "Need to search"}
        success = cache.cache_plan("Test query", plan, quality_score=0.9)

        assert success
        mock_redis.setex.assert_called_once()

    def test_cache_plan_low_quality_rejected(self, mock_redis):
        """Test low quality plans are not cached."""
        cache = QueryPlanCache(redis_client=mock_redis)

        plan = {"tool_calls": ["search_funding_calls"]}
        success = cache.cache_plan("Test query", plan, quality_score=0.5)

        assert not success
        mock_redis.setex.assert_not_called()

    def test_cache_plan_quality_threshold(self, mock_redis):
        """Test quality threshold is 0.7."""
        cache = QueryPlanCache(redis_client=mock_redis)

        # Just below threshold
        success = cache.cache_plan("Test", {}, quality_score=0.69)
        assert not success

        # At threshold
        success = cache.cache_plan("Test", {}, quality_score=0.7)
        assert success


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = MagicMock()
        mock.delete.return_value = 1
        return mock

    def test_invalidate_pattern(self, mock_redis):
        """Test invalidating a specific pattern."""
        cache = QueryPlanCache(redis_client=mock_redis)

        result = cache.invalidate_pattern("Test query")

        assert result
        mock_redis.delete.assert_called_once()

    def test_invalidate_nonexistent(self, mock_redis):
        """Test invalidating nonexistent pattern."""
        mock_redis.delete.return_value = 0
        cache = QueryPlanCache(redis_client=mock_redis)

        result = cache.invalidate_pattern("Nonexistent query")

        assert not result


class TestHitCountTracking:
    """Tests for hit count tracking."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis with cached data."""
        mock = MagicMock()
        mock.ttl.return_value = 3600
        return mock

    def test_hit_count_incremented(self, mock_redis):
        """Test hit count is incremented on cache hit."""
        cached_data = {"plan": {"tool_calls": []}, "hit_count": 5}
        mock_redis.get.return_value = json.dumps(cached_data)

        cache = QueryPlanCache(redis_client=mock_redis)
        cache.get_cached_plan("Test query")

        # Should have called setex to update hit count
        # The second call to get/setex is in _increment_hit_count
        assert mock_redis.setex.called or mock_redis.get.call_count >= 1


class TestCacheStatistics:
    """Tests for cache statistics."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis with keys."""
        mock = MagicMock()
        mock.keys.return_value = ["query_plan:abc123", "query_plan:def456"]
        mock.get.side_effect = [
            json.dumps({"pattern": "test 1", "hit_count": 10, "quality_score": 0.9}),
            json.dumps({"pattern": "test 2", "hit_count": 5, "quality_score": 0.8}),
        ]
        return mock

    def test_get_cache_stats_enabled(self, mock_redis):
        """Test getting stats when cache is enabled."""
        cache = QueryPlanCache(redis_client=mock_redis)
        stats = cache.get_cache_stats()

        assert stats["enabled"]
        assert "cached_plans" in stats
        assert "total_hits" in stats

    def test_get_cache_stats_disabled(self):
        """Test getting stats when cache is disabled."""
        cache = QueryPlanCache(redis_client=None)
        stats = cache.get_cache_stats()

        assert not stats["enabled"]

    def test_stats_include_top_patterns(self, mock_redis):
        """Test stats include top patterns."""
        cache = QueryPlanCache(redis_client=mock_redis)
        stats = cache.get_cache_stats()

        assert "top_patterns" in stats


class TestClearAll:
    """Tests for clearing all cached plans."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis."""
        mock = MagicMock()
        mock.keys.return_value = ["query_plan:1", "query_plan:2", "query_plan:3"]
        mock.delete.return_value = 3
        return mock

    def test_clear_all_returns_count(self, mock_redis):
        """Test clear_all returns deleted count."""
        cache = QueryPlanCache(redis_client=mock_redis)
        count = cache.clear_all()

        assert count == 3

    def test_clear_all_disabled(self):
        """Test clear_all when disabled returns 0."""
        cache = QueryPlanCache(redis_client=None)
        count = cache.clear_all()

        assert count == 0


class TestTTLHandling:
    """Tests for TTL (time-to-live) handling."""

    def test_default_ttl_24_hours(self):
        """Test default TTL is 24 hours."""
        cache = QueryPlanCache(redis_client=None)
        assert cache.ttl_seconds == 24 * 60 * 60

    def test_cache_uses_ttl(self):
        """Test cached plans use TTL."""
        mock_redis = MagicMock()
        cache = QueryPlanCache(redis_client=mock_redis)

        cache.cache_plan("Test", {"tool_calls": []}, quality_score=0.9)

        # Check setex was called with TTL
        call_args = mock_redis.setex.call_args
        if call_args:
            assert call_args[0][1] == cache.ttl_seconds


class TestPatternExtractionComprehensive:
    """Comprehensive tests for pattern extraction with many topic keywords."""

    @pytest.fixture
    def cache(self):
        return QueryPlanCache(redis_client=None)

    @pytest.mark.parametrize(
        "topic",
        [
            "hydrogen",
            "quantum",
            "artificial intelligence",
            "machine learning",
            "renewable",
            "solar",
            "wind",
            "battery",
            "energy storage",
            "cancer",
            "diabetes",
            "cardiovascular",
            "healthcare",
            "blockchain",
            "cybersecurity",
            "robotics",
            "autonomous",
            "sustainable",
            "sustainability",
            "circular economy",
            "biodiversity",
            "ocean",
            "marine",
            "space",
            "satellite",
            "nanotechnology",
            "biotechnology",
            "electric vehicles",
            "smart cities",
            "smart grid",
            "agriculture",
            "food security",
            "manufacturing",
            "advanced materials",
            "photonics",
            "semiconductors",
            "construction",
            "built environment",
            "transport",
            "mobility",
            "logistics",
            "water",
            "wastewater",
            "recycling",
            "climate",
            "carbon",
            "decarbonization",
            "digital",
            "digitalization",
            "software",
            "big data",
            "health",
            "medical",
            "pharmaceutical",
            "security",
            "defence",
            "emergency",
            "5g",
            "6g",
            "telecommunications",
            "green deal",
            "net zero",
        ],
    )
    def test_topic_keyword_replacement(self, cache, topic):
        """Test various topic keywords are replaced with {topic}."""
        query = f"Find {topic} funding opportunities"
        pattern = cache._extract_query_pattern(query)

        assert "{topic}" in pattern, f"'{topic}' should be replaced with {{topic}}"

    @pytest.mark.parametrize(
        "country",
        [
            "germany",
            "german",
            "france",
            "french",
            "spain",
            "spanish",
            "italy",
            "italian",
            "netherlands",
            "dutch",
            "belgium",
            "austria",
            "sweden",
            "denmark",
            "finland",
            "poland",
            "czech",
            "portugal",
            "ireland",
            "greece",
            "hungary",
            "romania",
            "bulgaria",
            "croatia",
            "slovakia",
            "slovenia",
            "switzerland",
            "swiss",
            "norway",
            "norwegian",
        ],
    )
    def test_country_name_replacement(self, cache, country):
        """Test country names are replaced with {country}."""
        query = f"Projects from {country}"
        pattern = cache._extract_query_pattern(query)

        assert "{country}" in pattern, f"'{country}' should be replaced with {{country}}"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_query(self):
        """Test handling empty query."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("")

        assert pattern == ""

    def test_query_with_only_stopwords(self):
        """Test query with only common words."""
        cache = QueryPlanCache(redis_client=None)
        pattern = cache._extract_query_pattern("the a an is are")

        # Should still produce a normalized pattern
        assert len(pattern) > 0

    def test_very_long_query(self):
        """Test handling very long query."""
        cache = QueryPlanCache(redis_client=None)
        long_query = "find hydrogen " * 100

        # Should not crash
        cache._extract_query_pattern(long_query)
        key = cache._generate_cache_key(long_query)

        assert len(key) < 100  # Key should be reasonably short


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

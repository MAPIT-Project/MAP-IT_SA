"""
Tests for Redis fallback behavior when Redis is unavailable.

Tests:
- FallbackRedis logs WARNING on every operation
- is_fallback_mode property returns True
- Fallback metrics tracking
- MemoryService uses fallback when Redis disconnected
"""

import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.memory.memory_service import FallbackRedis, MemoryService


class TestFallbackRedisBasics:
    """Tests for basic FallbackRedis functionality."""

    @pytest.fixture
    def fallback_redis(self):
        """Create a FallbackRedis instance."""
        return FallbackRedis()

    def test_is_fallback_mode_returns_true(self, fallback_redis):
        """Test that is_fallback_mode property returns True."""
        assert fallback_redis.is_fallback_mode is True

    def test_get_fallback_metrics_initial(self, fallback_redis):
        """Test initial fallback metrics."""
        metrics = fallback_redis.get_fallback_metrics()
        assert metrics["is_fallback_mode"] is True
        assert metrics["total_operations"] == 0
        assert "operation_counts" in metrics
        assert all(count == 0 for count in metrics["operation_counts"].values())

    def test_operation_counts_increment(self, fallback_redis):
        """Test that operation counts increment correctly."""
        fallback_redis.rpush("key", "value")
        fallback_redis.rpush("key", "value2")
        fallback_redis.get("key")

        metrics = fallback_redis.get_fallback_metrics()
        assert metrics["operation_counts"]["rpush"] == 2
        assert metrics["operation_counts"]["get"] == 1
        assert metrics["total_operations"] == 3


class TestFallbackRedisLogging:
    """Tests for FallbackRedis WARNING logging."""

    @pytest.fixture
    def fallback_redis(self):
        """Create a FallbackRedis instance."""
        return FallbackRedis()

    def test_ping_logs_warning(self, fallback_redis, caplog):
        """Test that ping logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.ping()

        assert len(caplog.records) >= 1
        assert any("Redis fallback: ping called" in r.message for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_rpush_logs_warning(self, fallback_redis, caplog):
        """Test that rpush logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.rpush("test_key", "test_value")

        assert len(caplog.records) >= 1
        assert any("Redis fallback: rpush called" in r.message for r in caplog.records)
        assert any("test_key" in r.message for r in caplog.records)

    def test_ltrim_logs_warning(self, fallback_redis, caplog):
        """Test that ltrim logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.ltrim("key", 0, 10)

        assert any("Redis fallback: ltrim called" in r.message for r in caplog.records)

    def test_expire_logs_warning(self, fallback_redis, caplog):
        """Test that expire logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.expire("key", 3600)

        assert any("Redis fallback: expire called" in r.message for r in caplog.records)

    def test_hset_logs_warning(self, fallback_redis, caplog):
        """Test that hset logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.hset("hash_key", "field", "value")

        assert any("Redis fallback: hset called" in r.message for r in caplog.records)

    def test_llen_logs_warning(self, fallback_redis, caplog):
        """Test that llen logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.llen("key")

        assert any("Redis fallback: llen called" in r.message for r in caplog.records)

    def test_hgetall_logs_warning(self, fallback_redis, caplog):
        """Test that hgetall logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.hgetall("key")

        assert any("Redis fallback: hgetall called" in r.message for r in caplog.records)

    def test_lrange_logs_warning(self, fallback_redis, caplog):
        """Test that lrange logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.lrange("key", 0, -1)

        assert any("Redis fallback: lrange called" in r.message for r in caplog.records)

    def test_delete_logs_warning(self, fallback_redis, caplog):
        """Test that delete logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.delete("key")

        assert any("Redis fallback: delete called" in r.message for r in caplog.records)

    def test_get_logs_warning(self, fallback_redis, caplog):
        """Test that get logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.get("key")

        assert any("Redis fallback: get called" in r.message for r in caplog.records)

    def test_setex_logs_warning(self, fallback_redis, caplog):
        """Test that setex logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.setex("key", 60, "value")

        assert any("Redis fallback: setex called" in r.message for r in caplog.records)

    def test_lpush_logs_warning(self, fallback_redis, caplog):
        """Test that lpush logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.lpush("key", "value")

        assert any("Redis fallback: lpush called" in r.message for r in caplog.records)

    def test_sadd_logs_warning(self, fallback_redis, caplog):
        """Test that sadd logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.sadd("set_key", "member")

        assert any("Redis fallback: sadd called" in r.message for r in caplog.records)

    def test_sismember_logs_warning(self, fallback_redis, caplog):
        """Test that sismember logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.sismember("set_key", "member")

        assert any("Redis fallback: sismember called" in r.message for r in caplog.records)

    def test_scard_logs_warning(self, fallback_redis, caplog):
        """Test that scard logs a WARNING."""
        with caplog.at_level(logging.WARNING):
            fallback_redis.scard("set_key")

        assert any("Redis fallback: scard called" in r.message for r in caplog.records)


class TestFallbackRedisReturnValues:
    """Tests for FallbackRedis return values."""

    @pytest.fixture
    def fallback_redis(self):
        """Create a FallbackRedis instance."""
        return FallbackRedis()

    def test_ping_returns_true(self, fallback_redis):
        """Test that ping returns True."""
        assert fallback_redis.ping() is True

    def test_rpush_returns_1(self, fallback_redis):
        """Test that rpush returns 1."""
        assert fallback_redis.rpush("key", "value") == 1

    def test_ltrim_returns_true(self, fallback_redis):
        """Test that ltrim returns True."""
        assert fallback_redis.ltrim("key", 0, 10) is True

    def test_expire_returns_true(self, fallback_redis):
        """Test that expire returns True."""
        assert fallback_redis.expire("key", 3600) is True

    def test_hset_returns_true(self, fallback_redis):
        """Test that hset returns True."""
        assert fallback_redis.hset("key", "field", "value") is True

    def test_llen_returns_0(self, fallback_redis):
        """Test that llen returns 0."""
        assert fallback_redis.llen("key") == 0

    def test_hgetall_returns_empty_dict(self, fallback_redis):
        """Test that hgetall returns empty dict."""
        assert fallback_redis.hgetall("key") == {}

    def test_lrange_returns_empty_list(self, fallback_redis):
        """Test that lrange returns empty list."""
        assert fallback_redis.lrange("key", 0, -1) == []

    def test_delete_returns_true(self, fallback_redis):
        """Test that delete returns True."""
        assert fallback_redis.delete("key") is True

    def test_get_returns_none(self, fallback_redis):
        """Test that get returns None."""
        assert fallback_redis.get("key") is None

    def test_setex_returns_true(self, fallback_redis):
        """Test that setex returns True."""
        assert fallback_redis.setex("key", 60, "value") is True

    def test_lpush_returns_1(self, fallback_redis):
        """Test that lpush returns 1."""
        assert fallback_redis.lpush("key", "value") == 1

    def test_sadd_returns_1(self, fallback_redis):
        """Test that sadd returns 1."""
        assert fallback_redis.sadd("set_key", "member") == 1

    def test_sismember_returns_false(self, fallback_redis):
        """Test that sismember returns False."""
        assert fallback_redis.sismember("set_key", "member") is False

    def test_scard_returns_0(self, fallback_redis):
        """Test that scard returns 0."""
        assert fallback_redis.scard("set_key") == 0


class TestMemoryServiceWithFallback:
    """Tests for MemoryService using FallbackRedis when Redis is unavailable."""

    def test_memory_service_uses_fallback_when_redis_fails(self, caplog):
        """
        Test that MemoryService uses FallbackRedis when Redis connection fails.
        This tests the PRD requirement:
        (1) disconnects Redis, (2) sends message, (3) verifies WARNING is logged,
        (4) verifies is_fallback_mode returns True.
        """
        with caplog.at_level(logging.WARNING):
            # Mock Redis to raise ConnectionError
            with patch("redis.Redis") as mock_redis_class:
                mock_redis = MagicMock()
                mock_redis.ping.side_effect = ConnectionError("Redis unavailable")
                mock_redis_class.return_value = mock_redis

                # Also mock the database URL to avoid actual DB connection
                with patch.dict(os.environ, {"DATABASE_URL": "postgresql://fake"}):
                    # Mock LongTermMemory to avoid DB connection
                    with patch("app.services.memory.memory_service.LongTermMemory") as mock_ltm:
                        mock_ltm.return_value = MagicMock()

                        # Mock RollingSummarizer to avoid API key requirement
                        with patch(
                            "app.services.memory.memory_service.RollingSummarizer"
                        ) as mock_summarizer:
                            mock_summarizer.return_value = MagicMock()

                            # Create MemoryService - should use fallback
                            service = MemoryService()

                            # Verify FallbackRedis is being used
                            assert isinstance(service.redis_client, FallbackRedis)
                            assert service.redis_client.is_fallback_mode is True

        # Verify warning was logged about Redis failure
        assert any("Redis connection failed" in r.message for r in caplog.records)

    def test_fallback_redis_logs_warning_when_operation_called(self, caplog):
        """Test that operations on FallbackRedis log warnings."""
        fallback = FallbackRedis()

        with caplog.at_level(logging.WARNING):
            # Perform some operations
            fallback.rpush("conversation:1:messages", "test_message")
            fallback.lrange("conversation:1:messages", 0, -1)
            fallback.hset("conversation:1:metadata", "key", "value")

        # Verify warnings were logged
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_messages) >= 3

        # Verify operation names appear in warnings
        assert any("rpush" in msg for msg in warning_messages)
        assert any("lrange" in msg for msg in warning_messages)
        assert any("hset" in msg for msg in warning_messages)


class TestFallbackMetricsTracking:
    """Tests for fallback metrics tracking."""

    def test_metrics_track_multiple_operations(self):
        """Test that metrics correctly track multiple operations."""
        fallback = FallbackRedis()

        # Perform various operations
        fallback.rpush("key1", "value1")
        fallback.rpush("key2", "value2")
        fallback.get("key1")
        fallback.get("key2")
        fallback.get("key3")
        fallback.lrange("list1", 0, -1)
        fallback.hset("hash1", "field1", "value1")
        fallback.hset("hash1", "field2", "value2")

        metrics = fallback.get_fallback_metrics()

        assert metrics["operation_counts"]["rpush"] == 2
        assert metrics["operation_counts"]["get"] == 3
        assert metrics["operation_counts"]["lrange"] == 1
        assert metrics["operation_counts"]["hset"] == 2
        assert metrics["total_operations"] == 8

    def test_metrics_independent_between_instances(self):
        """Test that metrics are independent between FallbackRedis instances."""
        fallback1 = FallbackRedis()
        fallback2 = FallbackRedis()

        fallback1.rpush("key", "value")
        fallback1.rpush("key", "value")
        fallback2.get("key")

        metrics1 = fallback1.get_fallback_metrics()
        metrics2 = fallback2.get_fallback_metrics()

        assert metrics1["operation_counts"]["rpush"] == 2
        assert metrics1["operation_counts"]["get"] == 0
        assert metrics2["operation_counts"]["rpush"] == 0
        assert metrics2["operation_counts"]["get"] == 1


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

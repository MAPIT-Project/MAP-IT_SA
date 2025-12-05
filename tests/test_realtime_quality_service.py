"""
Tests for RealTimeQualityService (Task 14)

Tests streaming quality feedback, score estimation, and caching.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.proposal_writing.realtime_quality_service import (
    RealTimeQualityService,
    StreamingQualityIndicator,
    StreamingFeedback,
    FeedbackType,
    QualityTier,
)


class TestQualityTier:
    """Tests for QualityTier enum."""

    def test_tier_values(self):
        """Test that all tiers have correct string values."""
        assert QualityTier.POOR.value == "poor"
        assert QualityTier.THRESHOLD.value == "threshold"
        assert QualityTier.ACCEPTABLE.value == "acceptable"
        assert QualityTier.GOOD.value == "good"
        assert QualityTier.EXCELLENT.value == "excellent"
        assert QualityTier.OUTSTANDING.value == "outstanding"


class TestFeedbackType:
    """Tests for FeedbackType enum."""

    def test_feedback_type_values(self):
        """Test that all feedback types have correct string values."""
        assert FeedbackType.QUICK_SCORE.value == "quick_score"
        assert FeedbackType.SUGGESTION_COUNT.value == "suggestion_count"
        assert FeedbackType.QUALITY_TIER.value == "quality_tier"
        assert FeedbackType.THINKING.value == "thinking"
        assert FeedbackType.SCORE_UPDATE.value == "score_update"
        assert FeedbackType.IMPROVEMENT.value == "improvement"
        assert FeedbackType.CELEBRATION.value == "celebration"


class TestStreamingFeedback:
    """Tests for StreamingFeedback dataclass."""

    def test_creation_with_defaults(self):
        """Test creating feedback with default timestamp."""
        feedback = StreamingFeedback(
            type=FeedbackType.QUICK_SCORE,
            value=3.5,
            message="Test message"
        )
        assert feedback.type == FeedbackType.QUICK_SCORE
        assert feedback.value == 3.5
        assert feedback.message == "Test message"
        assert feedback.timestamp is not None

    def test_to_dict(self):
        """Test serialization to dictionary."""
        feedback = StreamingFeedback(
            type=FeedbackType.QUALITY_TIER,
            value="good",
            message="Good quality"
        )
        result = feedback.to_dict()

        assert result["type"] == "quality_tier"
        assert result["value"] == "good"
        assert result["message"] == "Good quality"
        assert "timestamp" in result


class TestRealTimeQualityService:
    """Tests for RealTimeQualityService."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return RealTimeQualityService()

    def test_init(self, service):
        """Test service initialization."""
        assert service.quick_analyzer is not None
        assert service.evaluator is not None
        assert isinstance(service._score_cache, dict)
        assert isinstance(service._last_deep_analysis, dict)

    def test_tier_thresholds_defined(self, service):
        """Test that all tier thresholds are defined."""
        assert QualityTier.POOR in service.TIER_THRESHOLDS
        assert QualityTier.THRESHOLD in service.TIER_THRESHOLDS
        assert QualityTier.ACCEPTABLE in service.TIER_THRESHOLDS
        assert QualityTier.GOOD in service.TIER_THRESHOLDS
        assert QualityTier.EXCELLENT in service.TIER_THRESHOLDS
        assert QualityTier.OUTSTANDING in service.TIER_THRESHOLDS

    def test_celebrations_defined(self, service):
        """Test that celebration thresholds are defined."""
        assert 3.0 in service.CELEBRATIONS
        assert 3.5 in service.CELEBRATIONS
        assert 4.0 in service.CELEBRATIONS
        assert 4.5 in service.CELEBRATIONS

    # --- Quality Tier Calculation Tests ---

    def test_get_quality_tier_poor(self, service):
        """Test quality tier for poor scores."""
        assert service._get_quality_tier(0.0) == QualityTier.POOR
        assert service._get_quality_tier(1.0) == QualityTier.POOR
        assert service._get_quality_tier(2.4) == QualityTier.POOR

    def test_get_quality_tier_threshold(self, service):
        """Test quality tier for threshold scores."""
        assert service._get_quality_tier(2.5) == QualityTier.THRESHOLD
        assert service._get_quality_tier(2.9) == QualityTier.THRESHOLD

    def test_get_quality_tier_acceptable(self, service):
        """Test quality tier for acceptable scores."""
        assert service._get_quality_tier(3.0) == QualityTier.ACCEPTABLE
        assert service._get_quality_tier(3.4) == QualityTier.ACCEPTABLE

    def test_get_quality_tier_good(self, service):
        """Test quality tier for good scores."""
        assert service._get_quality_tier(3.5) == QualityTier.GOOD
        assert service._get_quality_tier(3.9) == QualityTier.GOOD

    def test_get_quality_tier_excellent(self, service):
        """Test quality tier for excellent scores."""
        assert service._get_quality_tier(4.0) == QualityTier.EXCELLENT
        assert service._get_quality_tier(4.4) == QualityTier.EXCELLENT

    def test_get_quality_tier_outstanding(self, service):
        """Test quality tier for outstanding scores."""
        assert service._get_quality_tier(4.5) == QualityTier.OUTSTANDING
        assert service._get_quality_tier(5.0) == QualityTier.OUTSTANDING

    # --- Tier Message Tests ---

    def test_get_tier_message_all_tiers(self, service):
        """Test that all tiers have messages."""
        for tier in QualityTier:
            message = service._get_tier_message(tier)
            assert isinstance(message, str)
            assert len(message) > 0

    def test_get_tier_message_content(self, service):
        """Test specific tier messages."""
        assert "work" in service._get_tier_message(QualityTier.POOR).lower()
        assert "threshold" in service._get_tier_message(QualityTier.THRESHOLD).lower()
        assert "outstanding" in service._get_tier_message(QualityTier.OUTSTANDING).lower()

    # --- Content Hashing Tests ---

    def test_hash_content_deterministic(self, service):
        """Test that same content produces same hash."""
        content = "Test content for hashing"
        hash1 = service._hash_content(content)
        hash2 = service._hash_content(content)
        assert hash1 == hash2

    def test_hash_content_different(self, service):
        """Test that different content produces different hash."""
        hash1 = service._hash_content("Content A")
        hash2 = service._hash_content("Content B")
        assert hash1 != hash2

    def test_hash_content_length(self, service):
        """Test that hash is truncated to 16 characters."""
        content = "Some very long content that would produce a long hash"
        hash_result = service._hash_content(content)
        assert len(hash_result) == 16

    # --- Score Caching Tests ---

    def test_cache_score_and_retrieve(self, service):
        """Test caching and retrieving scores."""
        content_hash = "test_hash_12345"
        score = 4.2

        service._cache_score(content_hash, score)
        cached = service._get_cached_score(content_hash)

        assert cached == score

    def test_get_cached_score_not_found(self, service):
        """Test retrieving non-existent cached score."""
        result = service._get_cached_score("nonexistent_hash")
        assert result is None

    def test_cache_expiry(self, service):
        """Test that old cache entries are cleaned."""
        # Add an old entry manually
        old_hash = "old_hash"
        old_time = datetime.now() - timedelta(minutes=40)
        service._score_cache[old_hash] = (3.0, old_time)

        # Add a new entry to trigger cleanup
        service._cache_score("new_hash", 4.0)

        # Old entry should be removed
        assert old_hash not in service._score_cache

    def test_cache_retrieval_expiry_5_minutes(self, service):
        """Test that cached scores older than 5 minutes are not returned."""
        content_hash = "expiring_hash"

        # Add entry that's 6 minutes old
        old_time = datetime.now() - timedelta(minutes=6)
        service._score_cache[content_hash] = (3.5, old_time)

        # Should return None because it's too old
        result = service._get_cached_score(content_hash)
        assert result is None

    def test_cache_retrieval_within_5_minutes(self, service):
        """Test that cached scores within 5 minutes are returned."""
        content_hash = "fresh_hash"

        # Add entry that's 3 minutes old
        recent_time = datetime.now() - timedelta(minutes=3)
        service._score_cache[content_hash] = (4.0, recent_time)

        # Should return the cached score
        result = service._get_cached_score(content_hash)
        assert result == 4.0

    # --- Quick Score Estimation Tests ---

    def test_estimate_quick_score_short_content(self, service):
        """Test quick score for short content."""
        content = "Short text"
        quick_result = {"total": 0}

        score = service._estimate_quick_score(content, quick_result)

        # Short content should have lower score
        assert score >= 1.0
        assert score <= 5.0

    def test_estimate_quick_score_long_content(self, service):
        """Test quick score for long content with technical terms."""
        content = """
        This is a comprehensive methodology that addresses the project objectives.
        Our innovative framework will deliver measurable impact through consortium
        collaboration. We will achieve key deliverables and milestones aligned with
        Horizon Europe and the European Green Deal for sustainable digital transformation.
        """ * 20  # Make it long enough

        quick_result = {"total": 0}
        score = service._estimate_quick_score(content, quick_result)

        # Long content with technical terms should score higher
        assert score > 2.5

    def test_estimate_quick_score_suggestion_penalty(self, service):
        """Test that suggestions reduce the score."""
        content = "Test content " * 50
        no_suggestions = {"total": 0}
        many_suggestions = {"total": 10}

        score_clean = service._estimate_quick_score(content, no_suggestions)
        score_with_suggestions = service._estimate_quick_score(content, many_suggestions)

        assert score_with_suggestions < score_clean

    def test_estimate_quick_score_bounds(self, service):
        """Test that score stays within 1.0-5.0 bounds."""
        # Very poor content
        poor_score = service._estimate_quick_score("x", {"total": 20})
        assert poor_score >= 1.0

        # Excellent content
        excellent_content = """
        Our innovative methodology framework delivers measurable impact
        through consortium objectives and milestone deliverables aligned
        with Horizon Europe sustainable digital transformation goals.
        """ * 50
        excellent_score = service._estimate_quick_score(excellent_content, {"total": 0})
        assert excellent_score <= 5.0

    def test_estimate_quick_score_empty_content(self, service):
        """Test quick score for empty content."""
        score = service._estimate_quick_score("", {"total": 0})
        assert score >= 1.0
        assert score <= 5.0

    def test_estimate_quick_score_whitespace_only(self, service):
        """Test quick score for whitespace-only content."""
        score = service._estimate_quick_score("   \n\t  ", {"total": 0})
        assert score >= 1.0
        assert score <= 5.0

    def test_estimate_quick_score_missing_total_key(self, service):
        """Test quick score when quick_result has no 'total' key."""
        score = service._estimate_quick_score("Some content here", {})
        assert score >= 1.0
        assert score <= 5.0

    # --- Deep Analysis Decision Tests ---

    def test_should_run_deep_analysis_short_content(self, service):
        """Test that short content skips deep analysis."""
        result = service._should_run_deep_analysis(
            section_id="test",
            content_hash="hash123",
            content_length=100
        )
        assert result is False

    def test_should_run_deep_analysis_cached(self, service):
        """Test that cached content skips deep analysis."""
        content_hash = "cached_hash"
        service._score_cache[content_hash] = (3.5, datetime.now())

        result = service._should_run_deep_analysis(
            section_id="test",
            content_hash=content_hash,
            content_length=500
        )
        assert result is False

    def test_should_run_deep_analysis_recent(self, service):
        """Test that recently analyzed section skips deep analysis."""
        section_id = "recently_analyzed"
        service._last_deep_analysis[section_id] = datetime.now()

        result = service._should_run_deep_analysis(
            section_id=section_id,
            content_hash="new_hash",
            content_length=500
        )
        assert result is False

    def test_should_run_deep_analysis_needed(self, service):
        """Test that uncached long content triggers deep analysis."""
        result = service._should_run_deep_analysis(
            section_id="new_section",
            content_hash="new_content_hash",
            content_length=500
        )
        assert result is True

    # --- Celebration Detection Tests ---

    def test_check_celebration_threshold_crossed(self, service):
        """Test celebration when crossing 3.0 threshold."""
        result = service._check_celebration(2.9, 3.1)
        assert result is not None
        assert result["threshold"] == 3.0

    def test_check_celebration_4_0_crossed(self, service):
        """Test celebration when crossing 4.0 threshold."""
        result = service._check_celebration(3.9, 4.1)
        assert result is not None
        assert result["threshold"] == 4.0

    def test_check_celebration_no_threshold(self, service):
        """Test no celebration when no threshold crossed."""
        result = service._check_celebration(3.5, 3.7)
        assert result is None

    def test_check_celebration_score_decrease(self, service):
        """Test no celebration when score decreases."""
        result = service._check_celebration(4.0, 3.5)
        assert result is None

    # --- Streaming Feedback Tests ---

    @pytest.mark.asyncio
    async def test_stream_feedback_yields_items(self, service):
        """Test that streaming yields feedback items."""
        content = "This is a test proposal section with enough content " * 10

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id="test-section"
        ):
            items.append(feedback)

        # Should have at least suggestion count, quick score, and tier
        types = [item.type for item in items]
        assert FeedbackType.SUGGESTION_COUNT in types
        assert FeedbackType.QUICK_SCORE in types
        assert FeedbackType.QUALITY_TIER in types

    @pytest.mark.asyncio
    async def test_stream_feedback_order(self, service):
        """Test that feedback items come in expected order."""
        content = "Short test content"

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="general",
            section_id="test"
        ):
            items.append(feedback)

        # First should be suggestion count
        assert items[0].type == FeedbackType.SUGGESTION_COUNT
        # Then quick score
        assert items[1].type == FeedbackType.QUICK_SCORE
        # Then quality tier
        assert items[2].type == FeedbackType.QUALITY_TIER

    @pytest.mark.asyncio
    async def test_stream_feedback_uses_cached_score(self, service):
        """Test that cached scores are used instead of estimating."""
        content = "Test content for caching"
        content_hash = service._hash_content(content)

        # Pre-cache a specific score
        service._cache_score(content_hash, 4.5)

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="general",
            section_id="test-cached"
        ):
            items.append(feedback)

        # Find the quick score feedback
        quick_score_item = next(
            (item for item in items if item.type == FeedbackType.QUICK_SCORE),
            None
        )
        assert quick_score_item is not None
        assert quick_score_item.value == 4.5  # Should use cached score

    @pytest.mark.asyncio
    async def test_stream_feedback_with_cluster(self, service):
        """Test streaming feedback with cluster parameter."""
        content = "Test content for cluster analysis " * 10

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id="test-cluster",
            cluster="digital"
        ):
            items.append(feedback)

        # Should still work with cluster parameter
        types = [item.type for item in items]
        assert FeedbackType.QUICK_SCORE in types

    def test_check_celebration_all_thresholds(self, service):
        """Test all celebration thresholds."""
        # Test 3.0 threshold
        result = service._check_celebration(2.5, 3.2)
        assert result["threshold"] == 3.0

        # Test 3.5 threshold
        result = service._check_celebration(3.2, 3.6)
        assert result["threshold"] == 3.5

        # Test 4.0 threshold
        result = service._check_celebration(3.8, 4.2)
        assert result["threshold"] == 4.0

        # Test 4.5 threshold
        result = service._check_celebration(4.3, 4.7)
        assert result["threshold"] == 4.5

    def test_check_celebration_multiple_thresholds_returns_first(self, service):
        """Test that when multiple thresholds are crossed, the first is returned."""
        # Jump from 2.5 to 4.5 crosses 3.0, 3.5, 4.0, 4.5
        result = service._check_celebration(2.5, 4.5)
        # Should return first threshold crossed (3.0)
        assert result["threshold"] == 3.0

    def test_negative_score_handling(self, service):
        """Test handling of negative scores."""
        tier = service._get_quality_tier(-1.0)
        assert tier == QualityTier.POOR

    def test_score_exactly_at_boundaries(self, service):
        """Test scores exactly at tier boundaries."""
        # Exactly 2.5 should be THRESHOLD
        assert service._get_quality_tier(2.5) == QualityTier.THRESHOLD
        # Exactly 3.0 should be ACCEPTABLE
        assert service._get_quality_tier(3.0) == QualityTier.ACCEPTABLE
        # Exactly 4.5 should be OUTSTANDING
        assert service._get_quality_tier(4.5) == QualityTier.OUTSTANDING


class TestStreamingQualityIndicator:
    """Tests for StreamingQualityIndicator helper class."""

    def test_init(self):
        """Test indicator initialization."""
        indicator = StreamingQualityIndicator(
            section_id="test-section",
            section_type="excellence"
        )

        assert indicator.section_id == "test-section"
        assert indicator.section_type == "excellence"
        assert indicator.current_score is None
        assert indicator.current_tier is None
        assert indicator.suggestion_count == 0
        assert indicator.is_analyzing is False

    def test_get_state(self):
        """Test getting current state."""
        indicator = StreamingQualityIndicator("test", "general")
        indicator.current_score = 3.5
        indicator.current_tier = QualityTier.GOOD
        indicator.suggestion_count = 5
        indicator.is_analyzing = True

        state = indicator.get_state()

        assert state["score"] == 3.5
        assert state["tier"] == "good"
        assert state["suggestion_count"] == 5
        assert state["is_analyzing"] is True

    def test_get_state_none_values(self):
        """Test getting state with None values."""
        indicator = StreamingQualityIndicator("test", "general")
        state = indicator.get_state()

        assert state["score"] is None
        assert state["tier"] is None

    @pytest.mark.asyncio
    async def test_update_with_callback(self):
        """Test updating indicator with callback."""
        indicator = StreamingQualityIndicator("test", "general")
        callbacks_received = []

        def callback(feedback):
            callbacks_received.append(feedback)

        await indicator.update(
            content="Test content for analysis " * 10,
            on_feedback=callback
        )

        # Should have received callbacks
        assert len(callbacks_received) > 0

        # State should be updated
        assert indicator.current_score is not None
        assert indicator.current_tier is not None


class TestDeepAnalysisStreaming:
    """Tests for deep analysis streaming path (lines 183-223)."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return RealTimeQualityService()

    @pytest.mark.asyncio
    async def test_deep_analysis_yields_score_update(self, service):
        """Test that deep analysis yields SCORE_UPDATE feedback."""
        # Create a mock evaluation result
        mock_eval_result = MagicMock()
        mock_eval_result.predicted_score = 4.2
        mock_eval_result.confidence = 0.85
        mock_eval_result.criterion_scores = {"criterion_1": 4.0, "criterion_2": 4.5}

        # Mock the evaluator
        service.evaluator.simulate_evaluation = AsyncMock(return_value=mock_eval_result)

        # Long content to trigger deep analysis
        content = "Test content for deep analysis " * 100
        section_id = "deep-test-section"

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id=section_id
        ):
            items.append(feedback)

        # Should have THINKING, SCORE_UPDATE feedback
        types = [item.type for item in items]
        assert FeedbackType.THINKING in types
        assert FeedbackType.SCORE_UPDATE in types

        # Verify SCORE_UPDATE has correct value
        score_update = next(
            (item for item in items if item.type == FeedbackType.SCORE_UPDATE),
            None
        )
        assert score_update is not None
        assert score_update.value["score"] == 4.2
        assert score_update.value["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_deep_analysis_yields_improvement_feedback(self, service):
        """Test that improvement feedback is yielded when score improves."""
        # Set a previous score
        section_id = "improvement-test"
        service._previous_scores[section_id] = 3.0

        # Create mock result with higher score
        mock_eval_result = MagicMock()
        mock_eval_result.predicted_score = 4.0
        mock_eval_result.confidence = 0.90
        mock_eval_result.criterion_scores = {}

        service.evaluator.simulate_evaluation = AsyncMock(return_value=mock_eval_result)

        content = "Test content " * 100

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id=section_id
        ):
            items.append(feedback)

        # Should have IMPROVEMENT feedback
        types = [item.type for item in items]
        assert FeedbackType.IMPROVEMENT in types

        # Verify improvement values
        improvement_item = next(
            (item for item in items if item.type == FeedbackType.IMPROVEMENT),
            None
        )
        assert improvement_item is not None
        assert improvement_item.value["previous"] == 3.0
        assert improvement_item.value["current"] == 4.0
        assert improvement_item.value["change"] == 1.0

    @pytest.mark.asyncio
    async def test_deep_analysis_yields_celebration_feedback(self, service):
        """Test that celebration feedback is yielded when threshold crossed."""
        section_id = "celebration-test"
        service._previous_scores[section_id] = 2.8  # Below 3.0 threshold

        mock_eval_result = MagicMock()
        mock_eval_result.predicted_score = 3.5  # Above 3.0 threshold
        mock_eval_result.confidence = 0.85
        mock_eval_result.criterion_scores = {}

        service.evaluator.simulate_evaluation = AsyncMock(return_value=mock_eval_result)

        content = "Test content " * 100

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id=section_id
        ):
            items.append(feedback)

        # Should have CELEBRATION feedback
        types = [item.type for item in items]
        assert FeedbackType.CELEBRATION in types

        # Verify celebration threshold
        celebration_item = next(
            (item for item in items if item.type == FeedbackType.CELEBRATION),
            None
        )
        assert celebration_item is not None
        assert celebration_item.value == 3.0  # The threshold that was crossed

    @pytest.mark.asyncio
    async def test_deep_analysis_caches_score(self, service):
        """Test that deep analysis caches the score."""
        mock_eval_result = MagicMock()
        mock_eval_result.predicted_score = 4.0
        mock_eval_result.confidence = 0.90
        mock_eval_result.criterion_scores = {}

        service.evaluator.simulate_evaluation = AsyncMock(return_value=mock_eval_result)

        content = "Test content for caching " * 100
        content_hash = service._hash_content(content)

        # Consume the generator
        async for _ in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id="cache-test"
        ):
            pass

        # Score should be cached
        cached_score = service._get_cached_score(content_hash)
        assert cached_score == 4.0

    @pytest.mark.asyncio
    async def test_deep_analysis_updates_last_analysis_time(self, service):
        """Test that deep analysis updates the last analysis timestamp."""
        mock_eval_result = MagicMock()
        mock_eval_result.predicted_score = 3.8
        mock_eval_result.confidence = 0.80
        mock_eval_result.criterion_scores = {}

        service.evaluator.simulate_evaluation = AsyncMock(return_value=mock_eval_result)

        section_id = "timestamp-test"
        content = "Test content " * 100

        # Consume the generator
        async for _ in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id=section_id
        ):
            pass

        # Last analysis time should be updated
        assert section_id in service._last_deep_analysis
        # Should be recent (within last second)
        time_diff = datetime.now() - service._last_deep_analysis[section_id]
        assert time_diff.total_seconds() < 1

    @pytest.mark.asyncio
    async def test_deep_analysis_error_handling(self, service):
        """Test that errors in deep analysis are handled gracefully."""
        # Make the evaluator raise an exception
        service.evaluator.simulate_evaluation = AsyncMock(
            side_effect=Exception("Simulated error")
        )

        content = "Test content " * 100

        items = []
        # Should not raise, should handle error gracefully
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id="error-test"
        ):
            items.append(feedback)

        # Should still get basic feedback (quick score, tier)
        types = [item.type for item in items]
        assert FeedbackType.QUICK_SCORE in types
        assert FeedbackType.QUALITY_TIER in types

        # Should have THINKING=False after error
        thinking_items = [item for item in items if item.type == FeedbackType.THINKING]
        # Last thinking item should be False (thinking done)
        if thinking_items:
            assert any(item.value is False for item in thinking_items)

    @pytest.mark.asyncio
    async def test_deep_analysis_no_improvement_on_decrease(self, service):
        """Test that no improvement feedback when score decreases."""
        section_id = "no-improvement-test"
        service._previous_scores[section_id] = 4.5  # High previous score

        mock_eval_result = MagicMock()
        mock_eval_result.predicted_score = 3.5  # Lower score
        mock_eval_result.confidence = 0.85
        mock_eval_result.criterion_scores = {}

        service.evaluator.simulate_evaluation = AsyncMock(return_value=mock_eval_result)

        content = "Test content " * 100

        items = []
        async for feedback in service.stream_feedback(
            content=content,
            section_type="excellence_objectives",
            section_id=section_id
        ):
            items.append(feedback)

        # Should NOT have IMPROVEMENT feedback
        types = [item.type for item in items]
        assert FeedbackType.IMPROVEMENT not in types

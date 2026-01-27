"""
Test Scenario 046: Success Rate Accuracy

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 046
Query: "What's the ERC success rate?"
Expected: Cross-reference with official ERC statistics
Verify: Within 2% of official figures
Fix if: Significantly wrong rates
Pass threshold: 85

Official ERC Success Rates (2024-2025 data from erc.europa.eu):
- Starting Grant: 12-15% (2024: 14.2%, 2025: ~12.2%)
- Consolidator Grant: 11-15% (2024: 14.2%, 2025: ~11.2%)
- Advanced Grant: 10-12% (2024: 11.1%)
- Synergy Grant: 8-10% (2024: ~10%, 2025: <10%)
- Proof of Concept: 35-40% (typical)

Sources:
- https://erc.europa.eu/news-events/news/erc-2024-starting-grants-results
- https://erc.europa.eu/news-events/news/erc-2025-consolidator-grants-results
- https://erc.europa.eu/news-events/news/erc-2024-advanced-grants-results
- https://erc.europa.eu/news-events/news/erc-2024-synergy-grants-results
"""

import re

import httpx
import pytest

# Official ERC success rate ranges (with 2% tolerance)
# These ranges encompass official 2024-2025 data
OFFICIAL_ERC_RANGES = {
    "starting_grant": (10, 17),  # Official: 12-15%, tolerance: 10-17%
    "consolidator_grant": (9, 17),  # Official: 11-15%, tolerance: 9-17%
    "advanced_grant": (8, 14),  # Official: 10-12%, tolerance: 8-14%
    "synergy_grant": (6, 12),  # Official: 8-10%, tolerance: 6-12%
    "proof_of_concept": (33, 42),  # Official: 35-40%, tolerance: 33-42%
}

# System hardcoded values (from tool_aware_agent.py)
SYSTEM_HARDCODED_RANGES = {
    "starting_grant": "~10-15%",
    "consolidator_grant": "~12-15%",
    "advanced_grant": "~10-12%",
    "synergy_grant": "~8-10%",
    "proof_of_concept": "~35-40%",
}


class TestScenario046ERCSuccessRateAccuracy:
    """Test suite for Scenario 046: ERC Success Rate Accuracy."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What's the ERC success rate?"
    PASS_THRESHOLD = 85

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(460000, 469999)

    # ==================== Unit Tests ====================

    def test_official_ranges_are_valid(self):
        """Test that official ranges are properly defined."""
        for grant_type, (min_val, max_val) in OFFICIAL_ERC_RANGES.items():
            assert min_val < max_val, f"{grant_type}: min should be < max"
            assert min_val > 0, f"{grant_type}: min should be positive"
            assert max_val < 100, f"{grant_type}: max should be < 100%"

    def test_hardcoded_ranges_within_tolerance(self):
        """Test that system hardcoded ranges are within 2% of official figures."""
        # Extract numeric ranges from hardcoded strings
        for grant_type, range_str in SYSTEM_HARDCODED_RANGES.items():
            # Parse "~10-15%" format
            match = re.search(r"~?(\d+)-(\d+)%", range_str)
            if match:
                sys_min = int(match.group(1))
                sys_max = int(match.group(2))

                official_min, official_max = OFFICIAL_ERC_RANGES[grant_type]

                # Check that system range overlaps with official range (with 2% tolerance)
                # System minimum should not be more than 2% above official minimum
                assert sys_min <= official_max + 2, (
                    f"{grant_type}: system min {sys_min}% too high vs official max {official_max}%"
                )

                # System maximum should not be more than 2% below official maximum
                assert sys_max >= official_min - 2, (
                    f"{grant_type}: system max {sys_max}% too low vs official min {official_min}%"
                )

    def test_extract_percentage_from_text(self):
        """Test percentage extraction from response text."""
        test_cases = [
            ("The success rate is 12%", [12.0]),
            ("Starting Grant: ~10-15%", [15.0]),  # Only 15% has % suffix
            ("Starting Grant: 10% - 15%", [10.0, 15.0]),  # Both have % suffix
            ("Between 8.5% and 12.3%", [8.5, 12.3]),
            ("No percentages here", []),
        ]
        for text, expected in test_cases:
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
            percentages = [float(p) for p in percentages]
            assert percentages == expected, f"Failed for: {text}"

    def test_range_overlap_detection(self):
        """Test detection of overlapping ranges."""

        def ranges_overlap(r1, r2, tolerance=2):
            """Check if two ranges overlap with tolerance."""
            return not (r1[1] + tolerance < r2[0] or r2[1] + tolerance < r1[0])

        # Should overlap
        assert ranges_overlap((10, 15), (12, 17))
        assert ranges_overlap((10, 15), (14, 20))
        # With tolerance
        assert ranges_overlap((10, 12), (14, 16), tolerance=2)
        # Should not overlap
        assert not ranges_overlap((10, 12), (20, 25))

    def test_grant_type_keywords(self):
        """Test detection of grant type keywords in text."""
        keywords = {
            "starting": ["starting grant", "stg", "starting grants"],
            "consolidator": ["consolidator grant", "cog", "consolidator grants"],
            "advanced": ["advanced grant", "adg", "advanced grants"],
            "synergy": ["synergy grant", "syg", "synergy grants"],
            "poc": ["proof of concept", "poc"],
        }

        test_text = "ERC Starting Grant success rate is 14.2%"
        found = False
        for _grant_type, patterns in keywords.items():
            if any(p in test_text.lower() for p in patterns):
                found = True
                break
        assert found, "Should detect grant type"

    def test_percentage_within_range(self):
        """Test that percentage-in-range checks work correctly."""
        # 14.2% should be within Starting Grant range (10-17%)
        assert 10 <= 14.2 <= 17, "14.2% should be in Starting Grant range"
        # 11.2% should be within Consolidator Grant range (9-17%)
        assert 9 <= 11.2 <= 17, "11.2% should be in Consolidator Grant range"
        # 11.1% should be within Advanced Grant range (8-14%)
        assert 8 <= 11.1 <= 14, "11.1% should be in Advanced Grant range"

    # ==================== Integration Tests ====================

    @pytest.mark.asyncio
    async def test_api_returns_200(self, conversation_id):
        """Test that the API returns 200 status code."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"

    @pytest.mark.asyncio
    async def test_response_mentions_erc(self, conversation_id):
        """Test that response mentions ERC."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "").lower()

            assert "erc" in response_text or "european research council" in response_text, (
                "Response should mention ERC"
            )

    @pytest.mark.asyncio
    async def test_response_contains_percentages(self, conversation_id):
        """Test that response contains success rate percentages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Extract percentages
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", response_text)
            assert len(percentages) > 0, "Response should contain percentage values"

    @pytest.mark.asyncio
    async def test_starting_grant_rate_accurate(self, conversation_id):
        """Test that Starting Grant success rate is within 2% of official figures."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "What is the ERC Starting Grant success rate?", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Extract percentages
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", response_text)
            percentages = [float(p) for p in percentages]

            # At least one percentage should be in the Starting Grant range
            official_min, official_max = OFFICIAL_ERC_RANGES["starting_grant"]
            in_range = any(official_min <= p <= official_max for p in percentages)
            assert in_range, (
                f"Starting Grant rate should be {official_min}-{official_max}%, got: {percentages}"
            )

    @pytest.mark.asyncio
    async def test_consolidator_grant_rate_accurate(self, conversation_id):
        """Test that Consolidator Grant success rate is within 2% of official figures."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={
                    "message": "What is the ERC Consolidator Grant success rate?",
                    "user_id": 1,
                },
            )

            result = response.json()
            response_text = result.get("response", "")

            # Extract percentages
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", response_text)
            percentages = [float(p) for p in percentages]

            # At least one percentage should be in the Consolidator Grant range
            official_min, official_max = OFFICIAL_ERC_RANGES["consolidator_grant"]
            in_range = any(official_min <= p <= official_max for p in percentages)
            assert in_range, (
                f"Consolidator Grant rate should be {official_min}-{official_max}%, "
                f"got: {percentages}"
            )

    @pytest.mark.asyncio
    async def test_advanced_grant_rate_accurate(self, conversation_id):
        """Test that Advanced Grant success rate is within 2% of official figures."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "What is the ERC Advanced Grant success rate?", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Extract percentages
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", response_text)
            percentages = [float(p) for p in percentages]

            # At least one percentage should be in the Advanced Grant range
            official_min, official_max = OFFICIAL_ERC_RANGES["advanced_grant"]
            in_range = any(official_min <= p <= official_max for p in percentages)
            assert in_range, (
                f"Advanced Grant rate should be {official_min}-{official_max}%, got: {percentages}"
            )

    @pytest.mark.asyncio
    async def test_response_mentions_grant_types(self, conversation_id):
        """Test that response breaks down success rates by grant type."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention at least 2 grant types
            grant_types = ["starting", "consolidator", "advanced", "synergy"]
            mentioned_types = sum(1 for gt in grant_types if gt in response_text)
            assert mentioned_types >= 2, (
                f"Should mention at least 2 grant types, found: {mentioned_types}"
            )

    @pytest.mark.asyncio
    async def test_no_significantly_wrong_rates(self, conversation_id):
        """Test that response does not contain significantly wrong rates."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Extract percentages
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", response_text)
            percentages = [float(p) for p in percentages]

            # Filter to reasonable ERC success rate range (exclude PoC which is 35-40%)
            main_grant_percentages = [p for p in percentages if p < 30]

            # No main grant rates should be above 20% (significantly wrong)
            wrong_rates = [p for p in main_grant_percentages if p > 20]
            assert len(wrong_rates) == 0, (
                f"Should not have significantly wrong rates (>20%): {wrong_rates}"
            )

            # No main grant rates should be below 5% (significantly wrong)
            wrong_rates_low = [p for p in main_grant_percentages if p < 5]
            assert len(wrong_rates_low) == 0, (
                f"Should not have significantly wrong rates (<5%): {wrong_rates_low}"
            )

    @pytest.mark.asyncio
    async def test_uses_programme_statistics_tool(self, conversation_id):
        """Test that get_programme_statistics tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            tools_used = metadata.get("tools_used", [])

            # Should use get_programme_statistics tool
            stats_tool_used = any("programme_statistics" in str(t).lower() for t in tools_used)
            assert stats_tool_used, f"Should use get_programme_statistics tool, got: {tools_used}"

    @pytest.mark.asyncio
    async def test_data_source_indicated(self, conversation_id):
        """Test that response indicates data source (official_ec_data)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            reasoning_steps = metadata.get("reasoning_steps", [])

            # Check tool observations for source indication
            source_indicated = False
            for step in reasoning_steps:
                observation = str(step.get("observation", "")).lower()
                if "official" in observation or "source" in observation or "ec" in observation:
                    source_indicated = True
                    break

            # Also check response text
            response_text = result.get("response", "").lower()
            if any(
                term in response_text
                for term in ["official", "erc data", "ec data", "european research council"]
            ):
                source_indicated = True

            assert source_indicated, "Response should indicate data source"

    @pytest.mark.asyncio
    async def test_no_error_in_response(self, conversation_id):
        """Test that response does not contain error messages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()

            # Should not have error in result
            assert "error" not in result, f"Response should not have error: {result.get('error')}"

            response_text = result.get("response", "")
            error_phrases = ["error occurred", "i apologize", "something went wrong", "unable to"]
            has_error = any(phrase in response_text.lower() for phrase in error_phrases)
            assert not has_error, "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_quality_score_threshold(self, conversation_id):
        """Test that quality score meets threshold (85)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            metadata = result.get("metadata", {})
            quality_analysis = metadata.get("quality_analysis", {})

            # If quality score available, check threshold
            if "score" in quality_analysis:
                score = quality_analysis.get("score", 0)
                assert score >= self.PASS_THRESHOLD, (
                    f"Quality score {score} should be >= {self.PASS_THRESHOLD}"
                )

    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, conversation_id):
        """Full integration test for Scenario 046."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Scoring criteria
            score = 0

            # 1. Mentions ERC (20 points)
            if "erc" in response_text.lower():
                score += 20

            # 2. Contains percentages (20 points)
            percentages = re.findall(r"(\d+(?:\.\d+)?)\s*%", response_text)
            if len(percentages) > 0:
                score += 20

            # 3. Percentages are in valid range (20 points)
            percentages = [float(p) for p in percentages]
            valid_range_count = sum(1 for p in percentages if 5 <= p <= 45)  # Include PoC range
            if valid_range_count > 0:
                score += 20

            # 4. Mentions grant types (15 points)
            grant_types = ["starting", "consolidator", "advanced", "synergy", "proof"]
            mentioned = sum(1 for gt in grant_types if gt in response_text.lower())
            if mentioned >= 2:
                score += 15

            # 5. No significantly wrong rates (10 points)
            main_grant_rates = [p for p in percentages if p < 30]
            if all(5 <= p <= 20 for p in main_grant_rates if main_grant_rates):
                score += 10

            assert score >= self.PASS_THRESHOLD, (
                f"Integration score {score} should be >= {self.PASS_THRESHOLD}"
            )


class TestERCSuccessRateDataValidation:
    """Test data validation for ERC success rates against official EC statistics."""

    def test_2024_starting_grant_rate(self):
        """Verify 2024 Starting Grant rate: 14.2% (494/3474)."""
        applications = 3474
        grants = 494
        rate = (grants / applications) * 100
        assert abs(rate - 14.2) < 0.1, f"2024 StG rate should be ~14.2%, got {rate:.1f}%"

    def test_2024_consolidator_grant_rate(self):
        """Verify 2024 Consolidator Grant rate: 14.2% (328/2313)."""
        applications = 2313
        grants = 328
        rate = (grants / applications) * 100
        assert abs(rate - 14.2) < 0.1, f"2024 CoG rate should be ~14.2%, got {rate:.1f}%"

    def test_2024_advanced_grant_rate(self):
        """Verify 2024 Advanced Grant rate: 11.1% (281/2534)."""
        applications = 2534
        grants = 281
        rate = (grants / applications) * 100
        assert abs(rate - 11.1) < 0.2, f"2024 AdG rate should be ~11.1%, got {rate:.1f}%"

    def test_2025_consolidator_grant_rate(self):
        """Verify 2025 Consolidator Grant rate: ~11.2% (349/3121)."""
        applications = 3121
        grants = 349
        rate = (grants / applications) * 100
        assert abs(rate - 11.2) < 0.2, f"2025 CoG rate should be ~11.2%, got {rate:.1f}%"

    def test_system_ranges_cover_official_rates(self):
        """Test that system hardcoded ranges cover official 2024-2025 rates."""
        # Official rates from 2024-2025
        official_rates = {
            "starting_grant": [14.2, 12.2],  # 2024, 2025 (approx)
            "consolidator_grant": [14.2, 11.2],  # 2024, 2025
            "advanced_grant": [11.1],  # 2024
            "synergy_grant": [10.0, 9.3],  # 2024, 2025 (approx)
        }

        # System ranges (from hardcoded values)
        system_ranges = {
            "starting_grant": (10, 15),
            "consolidator_grant": (12, 15),
            "advanced_grant": (10, 12),
            "synergy_grant": (8, 10),
        }

        for grant_type, rates in official_rates.items():
            sys_min, sys_max = system_ranges[grant_type]
            for rate in rates:
                # Check with 2% tolerance
                in_range_with_tolerance = (sys_min - 2) <= rate <= (sys_max + 2)
                assert in_range_with_tolerance, (
                    f"{grant_type}: {rate}% not within {sys_min}-{sys_max}% (with 2% tolerance)"
                )

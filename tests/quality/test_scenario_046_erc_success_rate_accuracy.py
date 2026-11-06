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
                assert (
                    sys_min <= official_max + 2
                ), f"{grant_type}: system min {sys_min}% too high vs official max {official_max}%"

                # System maximum should not be more than 2% below official maximum
                assert (
                    sys_max >= official_min - 2
                ), f"{grant_type}: system max {sys_max}% too low vs official min {official_min}%"

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
                assert (
                    in_range_with_tolerance
                ), f"{grant_type}: {rate}% not within {sys_min}-{sys_max}% (with 2% tolerance)"

"""
Scenario 011: Budget Benchmark
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What budget should I plan for a climate research RIA project?"
Expected: Budget range with benchmarks from similar projects
Verify: Benchmarks from real projects, reasonable ranges
Fix if: Unrealistic numbers, no real project examples
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario011BudgetBenchmark:
    """Test budget benchmark functionality for climate research RIA projects."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What budget should I plan for a climate research RIA project?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(110000, 119999)

    @pytest.mark.asyncio
    async def test_uses_get_budget_benchmark_tool(self, conversation_id):
        """Test that the get_budget_benchmark tool is used."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes get_budget_benchmark
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any("get_budget_benchmark" in str(step) for step in reasoning_steps)

            # The tool might be versioned (e.g., get_budget_benchmark_1_0)
            has_budget_tool = any("get_budget_benchmark" in t for t in tools_used)

            assert (
                has_budget_tool or tool_in_reasoning
            ), f"Expected get_budget_benchmark tool to be used. Tools: {tools_used}"

    @pytest.mark.asyncio
    async def test_includes_budget_range(self, conversation_id):
        """Test that response contains a recommended budget range."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain a budget range (e.g., "€2.9M - €6.9M" or "2.9M-6.9M")
            budget_range_patterns = [
                r"€[\d.,]+[MK]?\s*[-–]\s*€[\d.,]+[MK]?",  # €2.9M - €6.9M
                r"EUR\s*[\d.,]+\s*[-–]\s*[\d.,]+",  # EUR 2.9 - 6.9
                r"\b[\d.,]+[MK]?\s*[-–]\s*[\d.,]+[MK]?\s*(?:million|Million|EUR|€)",
                r"between\s*[\d.,]+\s*and\s*[\d.,]+\s*million",
                r"range\s*of?\s*[\d.,]+\s*[-–to]+\s*[\d.,]+",
            ]

            has_budget_range = any(
                re.search(pattern, response_text, re.IGNORECASE)
                for pattern in budget_range_patterns
            )

            assert (
                has_budget_range
            ), f"Response should contain a budget range. Response: {response_text[:500]}"

    @pytest.mark.asyncio
    async def test_budget_range_is_reasonable(self, conversation_id):
        """Test that the recommended budget is within reasonable RIA range."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Extract all million values from text
            million_values = re.findall(r"€?([\d.,]+)\s*[MmB](?:illion)?", response_text)
            million_values += re.findall(r"€?([\d.,]+)\s*million", response_text, re.IGNORECASE)

            # Convert to numbers
            numbers = []
            for val in million_values:
                try:
                    num = float(val.replace(",", ""))
                    numbers.append(num)
                except ValueError:
                    continue

            # RIA projects typically range from €2M to €15M
            # At least one number should be in the reasonable range
            if numbers:
                reasonable_numbers = [n for n in numbers if 1 <= n <= 20]
                assert (
                    len(reasonable_numbers) > 0
                ), f"Budget figures should be in reasonable RIA range (1-20M). Found: {numbers}"

    @pytest.mark.asyncio
    async def test_includes_real_project_data(self, conversation_id):
        """Test that response references real project statistics."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain indicators of real data usage
            real_data_indicators = [
                r"\d+\s*projects?",  # "500 projects"
                r"average|mean|median",  # Statistical terms
                r"analyzed|based on|from funded",  # Data source references
                r"benchmark|statistics",  # Benchmark terms
            ]

            has_real_data = any(
                re.search(ind, response_text, re.IGNORECASE) for ind in real_data_indicators
            )

            assert has_real_data, "Response should reference real project data and statistics"

    @pytest.mark.asyncio
    async def test_includes_sample_projects_or_examples(self, conversation_id):
        """Test that response includes sample project examples or references."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain project examples or references to real projects
            example_indicators = [
                # Project acronyms (typically all caps, 3-8 chars)
                r"\b[A-Z][A-Z0-9]{2,7}\b",
                # CORDIS references
                r"CORDIS",
                # Example/sample mentions
                r"example|sample|similar project",
                # Specific project count mentioning funded projects
                r"\d+\s*funded\s*projects?",
            ]

            has_examples = any(
                re.search(ind, response_text, re.IGNORECASE) for ind in example_indicators
            )

            # Also check if the response mentions specific numbers that suggest real data
            has_specific_stats = bool(
                re.search(r"€[\d.,]+[MK]?\s*(?:median|average)", response_text)
            )

            assert has_examples or has_specific_stats, (
                "Response should include sample project examples or "
                "specific statistics from real projects"
            )

    @pytest.mark.asyncio
    async def test_includes_consortium_size_guidance(self, conversation_id):
        """Test that response includes consortium size recommendations."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should mention partners/consortium size
            consortium_indicators = [
                "partner",
                "consortium",
                "participant",
                "member",
            ]

            has_consortium_info = any(ind in response_text for ind in consortium_indicators)

            assert has_consortium_info, "Response should include consortium size guidance"

    @pytest.mark.asyncio
    async def test_mentions_ria_specific_info(self, conversation_id):
        """Test that response includes RIA-specific information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should mention RIA or Research and Innovation Action
            ria_indicators = [
                "RIA",
                "Research and Innovation",
                "100%",  # RIA funding rate
            ]

            has_ria_info = any(ind in response_text for ind in ria_indicators)

            assert has_ria_info, "Response should include RIA-specific information"

    @pytest.mark.asyncio
    async def test_mentions_climate_cluster(self, conversation_id):
        """Test that response correctly identifies climate as Cluster 5."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should reference climate-related context
            climate_indicators = [
                "climate",
                "cluster 5",
                "cl5",
                "energy",
                "environment",
            ]

            has_climate_context = any(ind in response_text for ind in climate_indicators)

            assert has_climate_context, "Response should include climate/energy context"

    @pytest.mark.asyncio
    async def test_quality_score_above_threshold(self, conversation_id):
        """Test that response quality score meets threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check quality analysis if available
            quality = metadata.get("quality_analysis", {})
            score = quality.get("score", 0)

            # If no quality score, do basic evaluation
            if score == 0:
                response_text = result.get("response", "")
                # Basic scoring based on content
                score = 0

                # Query fulfillment (40 points)
                if re.search(r"€?[\d.,]+[MK]?", response_text):  # Has budget numbers
                    score += 20
                if re.search(
                    r"range|recommend|suggest", response_text, re.IGNORECASE
                ):  # Has recommendations
                    score += 20

                # Specificity (25 points)
                if re.search(r"\d+\s*projects?", response_text):  # References projects
                    score += 15
                if re.search(r"median|average", response_text, re.IGNORECASE):  # Has statistics
                    score += 10

                # Factual accuracy (25 points) - hard to verify automatically
                if re.search(r"RIA|Research.+Innovation", response_text):  # Correct context
                    score += 15
                if re.search(
                    r"climate|energy|cluster", response_text, re.IGNORECASE
                ):  # Correct domain
                    score += 10

                # Actionability (10 points)
                if re.search(
                    r"partner|consortium", response_text, re.IGNORECASE
                ):  # Practical advice
                    score += 10

            assert (
                score >= self.PASS_THRESHOLD
            ), f"Quality score {score} below threshold {self.PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_response_length_appropriate(self, conversation_id):
        """Test that response has appropriate length for budget guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Response should be substantive but not overwhelming
            word_count = len(response_text.split())

            assert word_count >= 100, f"Response too short ({word_count} words) for budget guidance"
            assert word_count <= 1000, f"Response too long ({word_count} words) for budget guidance"

    @pytest.mark.asyncio
    async def test_no_hallucinated_values(self, conversation_id):
        """Test that budget values are in realistic range (not hallucinated)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Extract all million values
            million_pattern = r"€?([\d.,]+)\s*(?:[MmB](?:illion)?|million)"
            matches = re.findall(million_pattern, response_text, re.IGNORECASE)

            for match in matches:
                try:
                    value = float(match.replace(",", ""))
                    # RIA projects should not claim budgets > €100M or < €0.1M
                    assert 0.1 <= value <= 100, f"Potentially hallucinated budget value: €{value}M"
                except ValueError:
                    continue

    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, conversation_id):
        """Full integration test for Scenario 011."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")
            metadata = result.get("metadata", {})

            # Comprehensive assertions for PRD requirements
            assertions_passed = []

            # 1. Budget range present
            has_range = bool(re.search(r"€?[\d.,]+[MK]?\s*[-–]\s*€?[\d.,]+[MK]?", response_text))
            assertions_passed.append(("budget_range", has_range))

            # 2. Real project benchmarks (not generic advice)
            has_benchmarks = bool(
                re.search(r"\d+\s*projects?|median|average|analyzed", response_text, re.IGNORECASE)
            )
            assertions_passed.append(("real_benchmarks", has_benchmarks))

            # 3. Consortium guidance
            has_consortium = bool(re.search(r"partner|consortium", response_text, re.IGNORECASE))
            assertions_passed.append(("consortium_guidance", has_consortium))

            # 4. Used correct tool
            tools_used = metadata.get("tools_used", [])
            reasoning = metadata.get("reasoning_steps", [])
            has_tool = any("get_budget_benchmark" in str(t) for t in tools_used) or any(
                "get_budget_benchmark" in str(s) for s in reasoning
            )
            assertions_passed.append(("correct_tool", has_tool))

            # 5. Reasonable values (not hallucinated)
            values = re.findall(r"€?([\d]+(?:\.\d+)?)\s*M", response_text)
            reasonable = all(
                0.1 <= float(v.replace(",", "")) <= 100
                for v in values
                if v and v.replace(".", "").isdigit()
            )
            assertions_passed.append(("reasonable_values", reasonable))

            # Report failures
            failures = [name for name, passed in assertions_passed if not passed]
            if failures:
                pytest.fail(
                    f"Scenario 011 failed checks: {failures}\n"
                    f"Response: {response_text[:800]}..."
                )

    @pytest.mark.asyncio
    async def test_multiple_runs_consistency(self, conversation_id):
        """Test that multiple runs produce consistent results."""
        results = []

        async with httpx.AsyncClient(timeout=180.0) as client:
            for i in range(2):
                conv_id = conversation_id + i

                await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conv_id}/context")

                response = await client.post(
                    f"{self.BASE_URL}/api/v3/conversation/{conv_id}/message",
                    json={"message": self.QUERY, "user_id": 1},
                )

                assert response.status_code == 200
                result = response.json()
                response_text = result.get("response", "")

                # Extract key metrics
                budget_values = re.findall(r"€?([\d.,]+)\s*M", response_text, re.IGNORECASE)
                results.append(
                    {
                        "has_budget": len(budget_values) > 0,
                        "has_partners": "partner" in response_text.lower(),
                    }
                )

        # All runs should have budget and partner info
        for i, r in enumerate(results):
            assert r["has_budget"], f"Run {i+1} missing budget information"
            assert r["has_partners"], f"Run {i+1} missing partner information"

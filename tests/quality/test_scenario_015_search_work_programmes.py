"""
Scenario 015: Search Work Programmes
PRD: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md

Query: "What does the Horizon Europe work programme say about digital twins?"
Expected: Relevant excerpts from official documents
Verify: Quotes are accurate, sources cited
Fix if: Wrong information, no source, outdated documents
Pass threshold: 80
"""

import re

import httpx
import pytest


class TestScenario015SearchWorkProgrammes:
    """Test document search functionality for work programmes."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What does the Horizon Europe work programme say about digital twins?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(150000, 159999)

    @pytest.mark.asyncio
    async def test_uses_search_documents_tool(self, conversation_id):
        """Test that the search_documents tool is used for work programme queries."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            metadata = result.get("metadata", {})

            # Check if tools_used includes search_documents
            tools_used = metadata.get("tools_used", [])

            # Also check reasoning steps for tool calls
            reasoning_steps = metadata.get("reasoning_steps", [])
            tool_in_reasoning = any("search_documents" in str(step) for step in reasoning_steps)

            has_doc_search = any("search_documents" in t for t in tools_used)

            assert has_doc_search or tool_in_reasoning, (
                f"Expected search_documents tool to be used. Tools: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_includes_digital_twin_content(self, conversation_id):
        """Test that response contains digital twin information."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should contain digital twin references
            digital_twin_indicators = [
                "digital twin",
                "digital-twin",
                "digitaltwin",
                "virtual replica",
                "simulation",
            ]

            has_digital_twin = any(ind in response_text for ind in digital_twin_indicators)

            assert has_digital_twin, "Response should contain digital twin information"

    @pytest.mark.asyncio
    async def test_includes_source_citations(self, conversation_id):
        """Test that response includes source citations or references."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain source references
            source_indicators = [
                r"work programme",
                r"source",
                r"according to",
                r"section",
                r"page",
                r"document",
                r"excerpt",
                r"ref:",
                r"cluster\s*\d",
            ]

            sources_found = sum(
                1
                for pattern in source_indicators
                if re.search(pattern, response_text, re.IGNORECASE)
            )

            assert sources_found >= 2, (
                f"Response should include source citations. Found: {sources_found}"
            )

    @pytest.mark.asyncio
    async def test_contains_quoted_content(self, conversation_id):
        """Test that response contains quoted/referenced content from documents."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should contain quoted content indicators
            quote_indicators = [
                r">",  # Blockquote
                r'".*"',  # Quoted text
                r"states that",
                r"mentions",
                r"describes",
                r"says",
                r"excerpt",
            ]

            has_quotes = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in quote_indicators
            )

            # Also check for substantial content (not just generic response)
            has_substantial_content = len(response_text) > 500

            assert has_quotes or has_substantial_content, (
                "Response should contain quoted content or substantial detail from documents"
            )

    @pytest.mark.asyncio
    async def test_references_horizon_europe(self, conversation_id):
        """Test that response references Horizon Europe specifically."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should reference Horizon Europe
            horizon_indicators = [
                "horizon europe",
                "horizon-europe",
                "cluster",
                "pillar",
                "mission",
            ]

            has_horizon_ref = any(ind in response_text for ind in horizon_indicators)

            assert has_horizon_ref, "Response should reference Horizon Europe programme"

    @pytest.mark.asyncio
    async def test_includes_cluster_context(self, conversation_id):
        """Test that response includes relevant cluster context for digital twins."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Digital twins are relevant to multiple clusters - should mention context
            cluster_indicators = [
                r"cluster\s*[1-6]",
                r"cluster-[1-6]",
                r"digital.*industry",
                r"manufacturing",
                r"climate",
                r"health",
                r"transport",
                r"energy",
            ]

            has_cluster_context = any(
                re.search(pattern, response_text, re.IGNORECASE) for pattern in cluster_indicators
            )

            # Or should have substantial technical content
            has_technical_content = len(response_text) > 800

            assert has_cluster_context or has_technical_content, (
                "Response should include cluster context or substantial technical detail"
            )

    @pytest.mark.asyncio
    async def test_no_hallucinated_sources(self, conversation_id):
        """Test that response doesn't contain obviously hallucinated sources."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should not contain obviously wrong programme names
            wrong_sources = [
                "horizon 2020 work programme 2026",  # H2020 ended
                "fp7",  # Old framework
                "horizon 2030",  # Doesn't exist
            ]

            has_wrong_source = any(ws in response_text for ws in wrong_sources)

            assert not has_wrong_source, "Response should not contain hallucinated sources"

    @pytest.mark.asyncio
    async def test_includes_actionable_guidance(self, conversation_id):
        """Test that response includes actionable guidance."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should include actionable guidance
            action_indicators = [
                "next steps",
                "recommend",
                "suggest",
                "consider",
                "check",
                "review",
                "download",
                "portal",
                "http",
            ]

            action_found = sum(1 for a in action_indicators if a in response_text)

            assert action_found >= 1, (
                f"Response should include actionable guidance. Action items found: {action_found}"
            )

    @pytest.mark.asyncio
    async def test_no_error_messages(self, conversation_id):
        """Test that response doesn't contain error messages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "").lower()

            # Should not contain error indicators
            error_indicators = [
                "error occurred",
                "failed to",
                "unable to",
                "something went wrong",
                "i cannot",
                "i don't have access",
                "no documents found",
            ]

            has_error = any(ind in response_text for ind in error_indicators)

            assert not has_error, "Response should not contain error messages"

    @pytest.mark.asyncio
    async def test_response_length_appropriate(self, conversation_id):
        """Test that response has appropriate length for a document query."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should be substantial but not overwhelming
            assert len(response_text) >= 400, (
                f"Response too short for document query: {len(response_text)} chars"
            )
            assert len(response_text) <= 15000, f"Response too long: {len(response_text)} chars"

    @pytest.mark.asyncio
    async def test_quality_score_threshold(self, conversation_id):
        """Test that response meets the quality threshold (80 points)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")
            text_lower = response_text.lower()

            # Calculate quality score based on PRD criteria
            score = 0

            # Query Fulfillment (40 points)
            # - Digital twin content present
            if "digital twin" in text_lower or "digital-twin" in text_lower:
                score += 20
            elif "digital" in text_lower and "twin" in text_lower:
                score += 10

            # - Work programme context
            if "work programme" in text_lower or "horizon europe" in text_lower:
                score += 10
            elif "horizon" in text_lower:
                score += 5

            # - Cluster/topic context
            if re.search(r"cluster\s*\d", response_text, re.IGNORECASE):
                score += 10
            elif any(t in text_lower for t in ["industry", "manufacturing", "climate", "health"]):
                score += 5

            # Specificity (25 points)
            # - Contains quoted/referenced content
            if ">" in response_text or '"' in response_text:  # Blockquote or inline quote
                score += 10
            elif "excerpt" in text_lower or "states that" in text_lower:
                score += 6

            # - Source attribution
            if re.search(r"source|section|page|document", response_text, re.IGNORECASE):
                score += 8
            elif "according to" in text_lower:
                score += 4

            # - Specific details
            numbers_found = len(re.findall(r"\d+", response_text))
            if numbers_found >= 5:
                score += 7
            elif numbers_found >= 2:
                score += 4

            # Factual Accuracy (25 points)
            # - Correct programme reference (Horizon Europe, not H2020)
            if "horizon europe" in text_lower and "2020" not in text_lower:
                score += 15
            elif "horizon europe" in text_lower:
                score += 10
            elif "horizon" in text_lower:
                score += 5

            # - No hallucinated content (bonus for not having errors)
            wrong_sources = ["horizon 2020 work programme 2026", "fp7", "horizon 2030"]
            if not any(ws in text_lower for ws in wrong_sources):
                score += 10

            # Actionability (10 points)
            # - Next steps or recommendations
            action_terms = ["next steps", "recommend", "suggest", "check", "review", "download"]
            if sum(1 for a in action_terms if a in text_lower) >= 2:
                score += 5
            elif sum(1 for a in action_terms if a in text_lower) >= 1:
                score += 3

            # - Links or portal references
            if "http" in response_text or "portal" in text_lower:
                score += 5
            elif "official" in text_lower:
                score += 2

            assert score >= self.PASS_THRESHOLD, (
                f"Quality score {score} is below threshold {self.PASS_THRESHOLD}"
            )

    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, conversation_id):
        """Full integration test for Scenario 015."""
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
            text_lower = response_text.lower()

            # Basic assertions
            assert len(response_text) > 400, (
                f"Response too short for document search: {len(response_text)} chars"
            )

            # Should have digital twin content
            assert "digital twin" in text_lower or "digital-twin" in text_lower, (
                "Missing digital twin content"
            )

            # Should have Horizon Europe reference
            assert "horizon" in text_lower, "Missing Horizon Europe reference"

            # Should have source indicators
            has_source = any(
                ind in text_lower
                for ind in ["source", "work programme", "document", "section", "excerpt"]
            )
            assert has_source, "Missing source citations"

            # Metadata should indicate success
            tools_used = metadata.get("tools_used", [])
            reasoning_steps = metadata.get("reasoning_steps", [])

            # Either search_documents was used or substantial content was generated
            has_doc_tool = any("search_documents" in str(t) for t in tools_used)
            has_doc_in_reasoning = any("search_documents" in str(s) for s in reasoning_steps)

            assert has_doc_tool or has_doc_in_reasoning or len(response_text) > 800, (
                f"Document search should be used or substantial content. Tools: {tools_used}"
            )

    @pytest.mark.asyncio
    async def test_response_structure(self, conversation_id):
        """Test that response has a well-organized structure."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200
            result = response.json()
            response_text = result.get("response", "")

            # Should have structured elements (headers, quotes, lists)
            structure_indicators = [
                r"###?\s+",  # Markdown headers
                r">",  # Blockquotes
                r"^\s*[-*\u2022]\s+",  # List items
                r"\d+\.\s+",  # Numbered lists
                r"\*\*.*\*\*",  # Bold text
            ]

            structure_found = sum(
                1
                for pattern in structure_indicators
                if re.search(pattern, response_text, re.MULTILINE)
            )

            # Either well-structured or substantial prose
            has_good_structure = structure_found >= 2
            has_substantial_prose = len(response_text) > 1000

            assert has_good_structure or has_substantial_prose, (
                f"Response should be well-structured. Structure elements: {structure_found}"
            )

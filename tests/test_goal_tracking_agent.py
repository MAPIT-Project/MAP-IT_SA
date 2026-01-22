"""
Unit tests for the Goal Tracking Agent.

Tests the following functionality:
- Goal extraction from first turn
- Progress tracking across turns (evaluate_progress)
- Completion detection (check_completion)
- Agent can be imported and instantiated by test runner
"""

import pytest
from tests.agents.goal_tracking_agent import CompletionStatus, GoalTrackingAgent, ProgressScore


class TestGoalTrackingAgentImport:
    """Test that the agent can be imported and instantiated."""

    def test_agent_can_be_imported(self):
        """Test that GoalTrackingAgent can be imported."""
        from tests.agents.goal_tracking_agent import GoalTrackingAgent

        assert GoalTrackingAgent is not None

    def test_agent_can_be_instantiated(self):
        """Test that GoalTrackingAgent can be instantiated."""
        agent = GoalTrackingAgent()
        assert agent is not None
        assert agent._goal is None
        assert agent._progress_history == []
        assert agent._turn_count == 0

    def test_agent_instantiation_with_parameters(self):
        """Test agent instantiation with custom parameters."""
        agent = GoalTrackingAgent(model_name="gemini-2.0-flash", use_llm=False)
        assert agent.model_name == "gemini-2.0-flash"
        assert agent.use_llm is False


class TestGoalExtraction:
    """Test goal extraction from user messages."""

    def test_extract_funding_goal(self):
        """Test extracting a 'find funding' goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Find funding calls for hydrogen research")

        assert goal is not None
        assert goal.category == "find_funding"
        assert goal.confidence > 0
        assert "hydrogen" in goal.keywords
        assert goal.description == "Find funding calls for hydrogen research"

    def test_extract_project_search_goal(self):
        """Test extracting a 'find projects' goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Search for similar projects in renewable energy")

        assert goal.category == "find_projects"
        assert goal.confidence > 0

    def test_extract_eligibility_goal(self):
        """Test extracting an eligibility check goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Am I eligible to apply for Horizon Europe funding?")

        assert goal.category == "check_eligibility"
        assert "horizon europe" in goal.keywords

    def test_extract_partner_search_goal(self):
        """Test extracting a partner search goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Find partners for AI research in healthcare")

        assert goal.category == "find_partners"
        assert "ai" in goal.keywords or "healthcare" in goal.description.lower()

    def test_extract_budget_goal(self):
        """Test extracting a budget calculation goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Calculate budget for a 3-year RIA project")

        assert goal.category == "calculate_budget"
        assert "ria" in goal.keywords

    def test_extract_programme_understanding_goal(self):
        """Test extracting a programme understanding goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("What is Horizon Europe and how does it work?")

        assert goal.category == "understand_programme"
        assert "horizon europe" in goal.keywords

    def test_extract_comparison_goal(self):
        """Test extracting a comparison goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Compare RIA vs IA funding types")

        assert goal.category == "compare_options"

    def test_extract_unknown_goal(self):
        """Test extracting an unknown goal category."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Hello, how are you today?")

        assert goal.category == "unknown"
        assert goal.confidence == 0.0

    def test_extract_keywords(self):
        """Test keyword extraction from goal."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal("Find EIC Accelerator calls for SME digital health innovation")

        # Should extract domain-specific terms
        assert "eic" in goal.keywords
        assert "sme" in goal.keywords
        assert "digital" in goal.keywords or "health" in goal.keywords

    def test_extract_sub_goals(self):
        """Test sub-goal extraction from compound queries."""
        agent = GoalTrackingAgent(use_llm=False)
        goal = agent.extract_goal(
            "Find funding calls for hydrogen research and also calculate the budget"
        )

        assert len(goal.sub_goals) >= 1

    def test_set_goal_manually(self):
        """Test manually setting a goal."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find partners for quantum computing research")

        goal = agent.get_goal()
        assert goal is not None
        assert goal.category == "find_partners"
        assert "quantum" in goal.keywords


class TestProgressEvaluation:
    """Test progress evaluation functionality."""

    @pytest.mark.asyncio
    async def test_evaluate_progress_returns_score(self):
        """Test that evaluate_progress returns a ProgressScore."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls for hydrogen research")

        response = """
        I found several funding calls for hydrogen research:
        1. HORIZON-CL5-2024-D3-01: Clean Hydrogen Partnership
           - Budget: 15 million EUR
           - Deadline: March 15, 2024
        2. HORIZON-CL5-2024-D3-02: Hydrogen Storage
           - Budget: 10 million EUR
           - Deadline: April 30, 2024
        """

        progress = await agent.evaluate_progress(
            query="Find hydrogen funding calls",
            response=response,
        )

        assert isinstance(progress, ProgressScore)
        assert 0.0 <= progress.score <= 1.0
        assert progress.turn_number == 1

    @pytest.mark.asyncio
    async def test_progress_increases_with_results(self):
        """Test that progress is higher when results are found."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls for hydrogen research")

        # No results response
        poor_response = "I couldn't find any calls."

        # Results found response
        good_response = """
        Here are the funding calls I found for hydrogen research:
        1. HORIZON-CL5-2024: Clean Energy - Budget 15 million EUR, Deadline Jan 2025
        2. HORIZON-CL5-2025: Hydrogen Storage - Budget 10 million EUR
        These calls are relevant to your research area.
        """

        poor_progress = await agent.evaluate_progress(
            query="Find hydrogen calls", response=poor_response
        )

        agent.reset()
        agent.set_goal("Find funding calls for hydrogen research")

        good_progress = await agent.evaluate_progress(
            query="Find hydrogen calls", response=good_response
        )

        # Good response should have higher progress
        assert good_progress.score > poor_progress.score

    @pytest.mark.asyncio
    async def test_progress_tracks_tools_used(self):
        """Test that tools used are tracked."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls")

        await agent.evaluate_progress(
            query="Find calls",
            response="Found 5 calls.",
            tools_used=["search_funding_calls"],
        )

        await agent.evaluate_progress(
            query="Tell me more",
            response="Here are details.",
            tools_used=["get_call_details"],
        )

        assert "search_funding_calls" in agent._tools_used
        assert "get_call_details" in agent._tools_used

    @pytest.mark.asyncio
    async def test_progress_history_maintained(self):
        """Test that progress history is maintained across turns."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding for research")

        await agent.evaluate_progress("Query 1", "Response 1 with funding information")
        await agent.evaluate_progress("Query 2", "Response 2 with more details")
        await agent.evaluate_progress("Query 3", "Response 3 with budget and deadline")

        assert len(agent._progress_history) == 3
        assert all(isinstance(p, ProgressScore) for p in agent._progress_history)
        assert [p.turn_number for p in agent._progress_history] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_evaluate_progress_extracts_goal_from_first_message(self):
        """Test that goal is auto-extracted from first message if not set."""
        agent = GoalTrackingAgent(use_llm=False)

        # Don't set goal explicitly
        progress = await agent.evaluate_progress(
            query="Find funding calls for solar energy",
            response="Found 3 solar energy calls.",
        )

        # Goal should be auto-extracted
        assert agent._goal is not None
        assert agent._goal.category == "find_funding"
        assert progress.score > 0


class TestCompletionDetection:
    """Test goal completion detection."""

    @pytest.mark.asyncio
    async def test_check_completion_achieved(self):
        """Test completion detection when goal is achieved."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls for hydrogen research")

        # Simulate a successful conversation
        responses = [
            "I found 5 funding calls for hydrogen research with deadlines and budgets.",
            "Here are the details: HORIZON-CL5-2024 has budget 15M EUR, deadline March 2024.",
            "The eligibility requirements are: 3+ partners from EU member states.",
        ]

        for i, response in enumerate(responses):
            await agent.evaluate_progress(
                query=f"Query {i + 1}",
                response=response,
                tools_used=["search_funding_calls"],
            )

        status = agent.check_completion()

        assert isinstance(status, CompletionStatus)
        assert status.progress > 0.5
        assert status.turns_taken == 3
        assert "search_funding_calls" in status.tools_used

    @pytest.mark.asyncio
    async def test_check_completion_not_achieved(self):
        """Test completion detection when goal is not achieved."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls for quantum computing")

        # Simulate unsuccessful conversation
        await agent.evaluate_progress(
            query="Find quantum calls",
            response="I don't have information about that.",
        )

        status = agent.check_completion()

        assert status.status in ["not_achieved", "in_progress"]
        assert status.progress < 0.8

    @pytest.mark.asyncio
    async def test_check_completion_partially_achieved(self):
        """Test completion detection for partial achievement."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls and calculate budget")

        # Only found calls, didn't calculate budget
        await agent.evaluate_progress(
            query="Find calls",
            response="Found 3 calls with deadlines.",
            tools_used=["search_funding_calls"],
        )

        status = agent.check_completion()

        # Should have some progress but not fully achieved
        assert status.progress > 0
        assert status.status in ["in_progress", "partially_achieved", "achieved"]

    def test_check_completion_no_goal(self):
        """Test completion check with no goal set."""
        agent = GoalTrackingAgent(use_llm=False)

        status = agent.check_completion()

        assert status.status == "not_achieved"
        assert status.progress == 0.0
        assert "No goal set" in status.reasoning

    def test_check_completion_no_progress(self):
        """Test completion check with no progress recorded."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding")

        status = agent.check_completion()

        assert status.status == "not_achieved"
        assert status.progress == 0.0
        assert "No progress recorded" in status.reasoning


class TestValidationHelpers:
    """Test validation helper methods for scenario testing."""

    @pytest.mark.asyncio
    async def test_validate_goal_progress(self):
        """Test goal progress validation for scenarios."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls")

        await agent.evaluate_progress(
            query="Find calls",
            response="Found 5 funding calls with budgets and deadlines.",
        )

        # Should pass low threshold
        assert agent.validate_goal_progress(min_progress=0.2) is True

        # May or may not pass high threshold depending on response quality
        high_threshold_result = agent.validate_goal_progress(min_progress=0.9)
        assert isinstance(high_threshold_result, bool)

    @pytest.mark.asyncio
    async def test_validate_goal_achieved(self):
        """Test goal achieved validation for scenarios."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls for hydrogen")

        # Simulate successful responses
        good_responses = [
            "Here are 5 funding calls for hydrogen with deadlines and budgets.",
            "The first call HORIZON-CL5-2024 has 15 million EUR budget.",
            "Found partners in Germany and France with hydrogen experience.",
        ]

        for resp in good_responses:
            await agent.evaluate_progress(
                query="Continue",
                response=resp,
                tools_used=["search_funding_calls"],
            )

        # Check with default threshold
        result = agent.validate_goal_achieved()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_validate_goal_progress_empty(self):
        """Test validation with no progress history."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding")

        # With no progress, only 0.0 threshold should pass
        assert agent.validate_goal_progress(min_progress=0.0) is True
        assert agent.validate_goal_progress(min_progress=0.1) is False


class TestMetricsCollection:
    """Test metrics collection functionality."""

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test comprehensive metrics collection."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls for hydrogen research")

        await agent.evaluate_progress(
            query="Find hydrogen calls",
            response="Found 5 calls with budgets and deadlines.",
            tools_used=["search_funding_calls"],
        )
        await agent.evaluate_progress(
            query="Tell me more about the first one",
            response="HORIZON-CL5-2024 has budget 15M EUR, deadline March.",
            tools_used=["get_call_details"],
        )

        metrics = agent.get_metrics()

        assert metrics.goal is not None
        assert metrics.goal.category == "find_funding"
        assert len(metrics.progress_history) == 2
        assert metrics.total_turns == 2
        assert "search_funding_calls" in metrics.tools_used
        assert "get_call_details" in metrics.tools_used
        assert metrics.final_status is not None

    @pytest.mark.asyncio
    async def test_progress_trend(self):
        """Test progress trend calculation."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding calls")

        # Not enough data
        await agent.evaluate_progress("Q1", "Response 1")
        assert agent.get_progress_trend() == "insufficient_data"

        # Add more data
        await agent.evaluate_progress("Q2", "Response 2 with funding and budget info")
        await agent.evaluate_progress("Q3", "Response 3 with more funding calls and deadlines")

        trend = agent.get_progress_trend()
        assert trend in ["improving", "stable", "declining"]


class TestAgentReset:
    """Test agent reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        """Test that reset clears all agent state."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding")
        await agent.evaluate_progress("Query", "Response with funding info")

        # Verify state exists
        assert agent._goal is not None
        assert len(agent._progress_history) > 0

        # Reset
        agent.reset()

        # Verify state is cleared
        assert agent._goal is None
        assert agent._progress_history == []
        assert agent._tools_used == []
        assert agent._turn_count == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Test handling of empty response."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding")

        progress = await agent.evaluate_progress(query="Find calls", response="")

        assert progress.score >= 0.0
        assert progress.turn_number == 1

    @pytest.mark.asyncio
    async def test_very_long_response(self):
        """Test handling of very long response."""
        agent = GoalTrackingAgent(use_llm=False)
        agent.set_goal("Find funding")

        long_response = "Found funding calls. " * 1000  # Very long response

        progress = await agent.evaluate_progress(query="Find calls", response=long_response)

        assert 0.0 <= progress.score <= 1.0

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self):
        """Test handling of special characters."""
        agent = GoalTrackingAgent(use_llm=False)

        goal = agent.extract_goal("Find funding for AI/ML & data science research (2024-2025)")

        assert goal is not None
        assert goal.category in ["find_funding", "unknown"]

    def test_goal_categories_coverage(self):
        """Test that all goal categories are defined properly."""
        from tests.agents.goal_tracking_agent import GOAL_CATEGORIES

        required_keys = ["patterns", "completion_indicators", "weight"]

        for category, config in GOAL_CATEGORIES.items():
            for key in required_keys:
                assert key in config, f"Missing {key} in {category}"
            assert len(config["patterns"]) > 0
            assert len(config["completion_indicators"]) > 0
            assert 0.0 <= config["weight"] <= 1.0

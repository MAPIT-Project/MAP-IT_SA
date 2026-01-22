"""
Goal Tracking Agent for tracking user goal progress across conversation turns.

This agent tracks user goals in multi-turn conversations:
- Extracts the user's goal from the first turn
- Tracks progress toward goal completion across turns
- Detects when goals are achieved or partially achieved
- Collects success metrics (turns to completion, tools used, etc.)

Usage:
    tracker = GoalTrackingAgent()
    tracker.set_goal("Find funding calls for hydrogen research")
    progress = await tracker.evaluate_progress(query, response)
    completion = tracker.check_completion(conversation)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


# Goal categories for EU funding domain
GOAL_CATEGORIES = {
    "find_funding": {
        "patterns": [
            r"find.*(?:funding|calls?|grants?|opportunities)",
            r"search.*(?:funding|calls?|grants?)",
            r"looking for.*(?:funding|calls?)",
            r"what.*(?:calls?|funding).*available",
            r"show.*(?:calls?|funding)",
        ],
        "completion_indicators": [
            "found",
            "calls available",
            "opportunities",
            "deadline",
            "budget",
            "here are",
            "following calls",
        ],
        "weight": 1.0,
    },
    "find_projects": {
        "patterns": [
            r"find.*projects?",
            r"search.*projects?",
            r"show.*projects?",
            r"looking for.*projects?",
            r"what projects",
            r"similar projects?",
        ],
        "completion_indicators": [
            "found",
            "projects",
            "funded",
            "here are",
            "following projects",
            "similar",
        ],
        "weight": 1.0,
    },
    "understand_programme": {
        "patterns": [
            r"what is.*(?:horizon|erasmus|creative europe)",
            r"explain.*(?:programme|program)",
            r"tell me about.*(?:programme|program|horizon|erasmus)",
            r"how does.*(?:programme|program).*work",
        ],
        "completion_indicators": [
            "pillars",
            "clusters",
            "structure",
            "programme",
            "funding",
            "eligibility",
        ],
        "weight": 0.8,
    },
    "check_eligibility": {
        "patterns": [
            r"(?:am i|are we|is.*organization).*eligible",
            r"eligibility.*(?:for|to)",
            r"can.*(?:apply|participate)",
            r"who can.*(?:apply|participate)",
        ],
        "completion_indicators": [
            "eligible",
            "eligibility",
            "can apply",
            "requirements",
            "criteria",
        ],
        "weight": 0.9,
    },
    "find_partners": {
        "patterns": [
            r"find.*partners?",
            r"search.*partners?",
            r"looking for.*partners?",
            r"partner.*search",
            r"consortium.*partners?",
        ],
        "completion_indicators": [
            "partners",
            "organizations",
            "consortium",
            "collaboration",
            "network",
        ],
        "weight": 1.0,
    },
    "calculate_budget": {
        "patterns": [
            r"calculate.*budget",
            r"budget.*calculation",
            r"how much.*(?:funding|budget)",
            r"what.*budget.*for",
            r"estimate.*(?:budget|costs?)",
        ],
        "completion_indicators": [
            "budget",
            "EUR",
            "million",
            "costs",
            "breakdown",
            "funding rate",
        ],
        "weight": 0.9,
    },
    "plan_proposal": {
        "patterns": [
            r"write.*proposal",
            r"help.*proposal",
            r"plan.*(?:proposal|project)",
            r"proposal.*(?:help|writing|plan)",
            r"prepare.*(?:application|proposal)",
        ],
        "completion_indicators": [
            "proposal",
            "work package",
            "timeline",
            "deliverable",
            "consortium",
            "budget",
        ],
        "weight": 1.0,
    },
    "compare_options": {
        "patterns": [
            r"compare.*(?:programmes?|options?|calls?)",
            r"difference.*between",
            r"which.*(?:better|best)",
            r"(?:pros|cons).*of",
            r"vs\.?|versus",
        ],
        "completion_indicators": [
            "comparison",
            "difference",
            "advantage",
            "disadvantage",
            "recommend",
        ],
        "weight": 0.9,
    },
    "get_statistics": {
        "patterns": [
            r"(?:success|funding).*rate",
            r"statistics.*for",
            r"how many.*(?:projects?|calls?|funded)",
            r"what.*(?:average|typical)",
        ],
        "completion_indicators": [
            "rate",
            "percent",
            "%",
            "average",
            "statistics",
            "projects",
        ],
        "weight": 0.8,
    },
}


@dataclass
class Goal:
    """Represents a user's goal extracted from conversation."""

    description: str
    category: str = "unknown"
    keywords: list[str] = field(default_factory=list)
    extracted_from: str = ""
    confidence: float = 0.0
    sub_goals: list[str] = field(default_factory=list)


@dataclass
class ProgressScore:
    """Progress score for a single evaluation."""

    score: float  # 0.0 to 1.0
    reasoning: str = ""
    indicators_found: list[str] = field(default_factory=list)
    turn_number: int = 0
    query: str = ""
    response_snippet: str = ""


@dataclass
class CompletionStatus:
    """Status of goal completion."""

    status: str  # "achieved", "partially_achieved", "not_achieved", "in_progress"
    progress: float  # 0.0 to 1.0
    turns_taken: int = 0
    tools_used: list[str] = field(default_factory=list)
    reasoning: str = ""
    sub_goal_completion: dict[str, bool] = field(default_factory=dict)
    achieved_at_turn: int | None = None


@dataclass
class ConversationMetrics:
    """Success metrics for a conversation."""

    goal: Goal | None = None
    progress_history: list[ProgressScore] = field(default_factory=list)
    final_status: CompletionStatus | None = None
    total_turns: int = 0
    tools_used: list[str] = field(default_factory=list)
    context_preserved: bool = True
    average_progress_per_turn: float = 0.0


class GoalTrackingAgent:
    """
    Agent that tracks user goal progress across conversation turns.

    Features:
    - Goal extraction from first turn
    - Progress tracking (0.0 to 1.0)
    - Completion detection
    - Success metrics collection
    - LLM-based evaluation when available

    Usage:
        tracker = GoalTrackingAgent()
        tracker.set_goal("Find funding for hydrogen research")

        # After each turn
        progress = await tracker.evaluate_progress(query, response)

        # Check completion
        status = tracker.check_completion(conversation)
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        use_llm: bool = True,
    ):
        """
        Initialize the goal tracking agent.

        Args:
            model_name: Gemini model name for LLM-based evaluation
            use_llm: Whether to use LLM for evaluation (falls back to rules)
        """
        self.model_name = model_name
        self.use_llm = use_llm and genai is not None
        self._model = None
        self._goal: Goal | None = None
        self._progress_history: list[ProgressScore] = []
        self._tools_used: list[str] = []
        self._turn_count = 0

    def _get_model(self):
        """Get or create the Gemini model."""
        if self._model is None and genai:
            try:
                self._model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                logger.warning(f"Failed to create Gemini model: {e}")
        return self._model

    def reset(self):
        """Reset the tracker for a new conversation."""
        self._goal = None
        self._progress_history = []
        self._tools_used = []
        self._turn_count = 0

    # =========================================================================
    # Goal Extraction
    # =========================================================================

    def extract_goal(self, first_message: str) -> Goal:
        """
        Extract the user's goal from their first message.

        Args:
            first_message: The user's first message in the conversation

        Returns:
            Goal object with extracted goal information
        """
        message_lower = first_message.lower()

        # Try to match goal categories
        best_category = "unknown"
        best_confidence = 0.0

        for category, config in GOAL_CATEGORIES.items():
            for pattern in config["patterns"]:
                if re.search(pattern, message_lower):
                    confidence = config["weight"]
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_category = category
                        break

        # Extract keywords
        keywords = self._extract_keywords(first_message)

        # Extract sub-goals if present
        sub_goals = self._extract_sub_goals(first_message)

        goal = Goal(
            description=first_message[:500],  # Truncate long messages
            category=best_category,
            keywords=keywords,
            extracted_from=first_message[:200],
            confidence=best_confidence,
            sub_goals=sub_goals,
        )

        self._goal = goal
        return goal

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from text."""
        keywords = []

        # Domain-specific terms
        domain_terms = [
            "horizon europe",
            "erasmus",
            "creative europe",
            "hydrogen",
            "solar",
            "energy",
            "climate",
            "health",
            "digital",
            "ai",
            "artificial intelligence",
            "quantum",
            "mobility",
            "education",
            "training",
            "research",
            "innovation",
            "sme",
            "university",
            "ria",
            "ia",
            "csa",
            "eic",
            "erc",
            "msca",
        ]

        text_lower = text.lower()
        for term in domain_terms:
            if term in text_lower:
                keywords.append(term)

        return keywords[:10]  # Limit to 10 keywords

    def _extract_sub_goals(self, text: str) -> list[str]:
        """Extract sub-goals from compound queries."""
        sub_goals = []

        # Look for "and", "also", "as well as" patterns
        connectors = [" and ", " also ", " as well as ", ", "]
        text_lower = text.lower()

        for connector in connectors:
            if connector in text_lower:
                parts = text_lower.split(connector)
                for part in parts:
                    part = part.strip()
                    if len(part) > 10:  # Skip very short fragments
                        sub_goals.append(part[:100])

        return sub_goals[:5]  # Limit to 5 sub-goals

    def set_goal(self, goal_description: str):
        """
        Manually set a goal for tracking.

        Args:
            goal_description: Description of the goal
        """
        self._goal = self.extract_goal(goal_description)

    def get_goal(self) -> Goal | None:
        """Get the current goal."""
        return self._goal

    # =========================================================================
    # Progress Evaluation
    # =========================================================================

    async def evaluate_progress(
        self,
        query: str,
        response: str,
        tools_used: list[str] | None = None,
    ) -> ProgressScore:
        """
        Evaluate progress toward the goal after a turn.

        Args:
            query: The user's query in this turn
            response: The assistant's response
            tools_used: List of tools used in this turn

        Returns:
            ProgressScore with 0.0 to 1.0 score
        """
        self._turn_count += 1

        if tools_used:
            self._tools_used.extend(tools_used)

        # If no goal set, extract from first message
        if self._goal is None:
            self.extract_goal(query)

        # Try LLM evaluation first
        if self.use_llm:
            score = await self._evaluate_progress_llm(query, response)
            if score is not None:
                score.turn_number = self._turn_count
                self._progress_history.append(score)
                return score

        # Fall back to rule-based evaluation
        score = self._evaluate_progress_rules(query, response)
        score.turn_number = self._turn_count
        self._progress_history.append(score)
        return score

    async def _evaluate_progress_llm(
        self,
        query: str,
        response: str,
    ) -> ProgressScore | None:
        """Evaluate progress using LLM."""
        model = self._get_model()
        if not model or not self._goal:
            return None

        prompt = f"""You are evaluating progress toward a user's goal in an EU funding conversation.

USER'S GOAL: {self._goal.description}
GOAL CATEGORY: {self._goal.category}
KEYWORDS: {", ".join(self._goal.keywords)}

CURRENT TURN:
User: {query}
Assistant: {response[:2000]}

PREVIOUS PROGRESS: {self._get_previous_progress()}

INSTRUCTIONS:
1. Evaluate how much progress has been made toward the user's goal
2. Consider both the current turn and cumulative progress
3. Look for concrete results, specific information, or actionable next steps

OUTPUT FORMAT (use exactly this format):
PROGRESS_SCORE: [0.0-1.0]
INDICATORS: [comma-separated list of progress indicators found]
REASONING: [brief explanation]

Evaluate now:"""

        try:
            result = model.generate_content(prompt)
            return self._parse_progress_response(result.text, query, response)
        except Exception as e:
            logger.warning(f"LLM progress evaluation failed: {e}")
            return None

    def _get_previous_progress(self) -> str:
        """Get summary of previous progress."""
        if not self._progress_history:
            return "No previous turns"

        scores = [p.score for p in self._progress_history]
        avg = sum(scores) / len(scores) if scores else 0
        return f"Turns: {len(scores)}, Avg progress: {avg:.2f}, Last: {scores[-1]:.2f}"

    def _parse_progress_response(
        self,
        llm_text: str,
        query: str,
        response: str,
    ) -> ProgressScore:
        """Parse LLM progress evaluation response."""
        score = 0.5  # Default
        indicators = []
        reasoning = ""

        # Extract score
        score_match = re.search(r"PROGRESS_SCORE:\s*([\d.]+)", llm_text)
        if score_match:
            try:
                score = min(1.0, max(0.0, float(score_match.group(1))))
            except ValueError:
                pass

        # Extract indicators
        indicators_match = re.search(r"INDICATORS:\s*(.+?)(?:\n|REASONING:)", llm_text)
        if indicators_match:
            indicators = [i.strip() for i in indicators_match.group(1).split(",") if i.strip()]

        # Extract reasoning
        reasoning_match = re.search(r"REASONING:\s*(.+?)$", llm_text, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()[:200]

        return ProgressScore(
            score=score,
            reasoning=reasoning,
            indicators_found=indicators,
            query=query[:100],
            response_snippet=response[:200],
        )

    def _evaluate_progress_rules(
        self,
        query: str,
        response: str,
    ) -> ProgressScore:
        """Rule-based progress evaluation fallback."""
        if not self._goal:
            return ProgressScore(
                score=0.0,
                reasoning="No goal set",
                query=query[:100],
                response_snippet=response[:200],
            )

        score = 0.0
        indicators = []
        response_lower = response.lower()

        # Get completion indicators for goal category
        category_config = GOAL_CATEGORIES.get(self._goal.category, {})
        completion_indicators = category_config.get("completion_indicators", [])

        # Check for completion indicators
        matched_indicators = 0
        for indicator in completion_indicators:
            if indicator.lower() in response_lower:
                matched_indicators += 1
                indicators.append(indicator)

        if completion_indicators:
            indicator_score = min(1.0, matched_indicators / len(completion_indicators))
        else:
            indicator_score = 0.3

        # Check for keyword presence
        keyword_matches = 0
        for keyword in self._goal.keywords:
            if keyword.lower() in response_lower:
                keyword_matches += 1

        if self._goal.keywords:
            keyword_score = min(1.0, keyword_matches / len(self._goal.keywords))
        else:
            keyword_score = 0.3

        # Check response quality indicators
        quality_score = 0.0
        quality_indicators = [
            (len(response) > 500, 0.1, "substantial response"),
            (len(response) > 1000, 0.1, "detailed response"),
            ("deadline" in response_lower, 0.1, "deadline mentioned"),
            ("eur" in response_lower or "million" in response_lower, 0.1, "budget info"),
            (
                any(p in response_lower for p in ["here are", "found", "following"]),
                0.2,
                "results presented",
            ),
            (
                any(p in response for p in ["1.", "2.", "3.", "-", "*"]),
                0.1,
                "structured list",
            ),
        ]

        for condition, value, indicator in quality_indicators:
            if condition:
                quality_score += value
                indicators.append(indicator)

        # Combine scores
        score = (indicator_score * 0.4) + (keyword_score * 0.3) + (quality_score * 0.3)
        score = min(1.0, score)

        # Consider cumulative progress
        if self._progress_history:
            prev_max = max(p.score for p in self._progress_history)
            # Progress should generally increase
            score = max(score, prev_max * 0.9)

        reasoning = f"Indicators: {matched_indicators}/{len(completion_indicators)}, "
        reasoning += f"Keywords: {keyword_matches}/{len(self._goal.keywords)}"

        return ProgressScore(
            score=score,
            reasoning=reasoning,
            indicators_found=indicators,
            query=query[:100],
            response_snippet=response[:200],
        )

    # =========================================================================
    # Completion Detection
    # =========================================================================

    def check_completion(
        self,
        conversation: list[dict[str, Any]] | None = None,
    ) -> CompletionStatus:
        """
        Check if the goal has been achieved.

        Args:
            conversation: Optional list of conversation turns for re-evaluation

        Returns:
            CompletionStatus with achievement status
        """
        if not self._goal:
            return CompletionStatus(
                status="not_achieved",
                progress=0.0,
                reasoning="No goal set",
            )

        if not self._progress_history:
            return CompletionStatus(
                status="not_achieved",
                progress=0.0,
                turns_taken=0,
                reasoning="No progress recorded",
            )

        # Calculate final progress
        scores = [p.score for p in self._progress_history]
        max_progress = max(scores)
        avg_progress = sum(scores) / len(scores)

        # Use max progress as primary indicator
        final_progress = max_progress

        # Determine status
        if final_progress >= 0.8:
            status = "achieved"
            achieved_turn = next(
                (i + 1 for i, p in enumerate(self._progress_history) if p.score >= 0.8),
                len(self._progress_history),
            )
        elif final_progress >= 0.5:
            status = "partially_achieved"
            achieved_turn = None
        elif final_progress >= 0.2:
            status = "in_progress"
            achieved_turn = None
        else:
            status = "not_achieved"
            achieved_turn = None

        # Check sub-goal completion
        sub_goal_completion = {}
        for sub_goal in self._goal.sub_goals:
            # Simple check: is the sub-goal topic mentioned in any response?
            completed = any(
                sub_goal.lower()[:30] in p.response_snippet.lower() for p in self._progress_history
            )
            sub_goal_completion[sub_goal[:50]] = completed

        # Build reasoning
        reasoning_parts = [
            f"Max progress: {max_progress:.2f}",
            f"Avg progress: {avg_progress:.2f}",
            f"Turns: {len(self._progress_history)}",
        ]
        if self._tools_used:
            reasoning_parts.append(f"Tools: {len(set(self._tools_used))}")

        return CompletionStatus(
            status=status,
            progress=final_progress,
            turns_taken=len(self._progress_history),
            tools_used=list(set(self._tools_used)),
            reasoning=", ".join(reasoning_parts),
            sub_goal_completion=sub_goal_completion,
            achieved_at_turn=achieved_turn,
        )

    # =========================================================================
    # Metrics Collection
    # =========================================================================

    def get_metrics(self) -> ConversationMetrics:
        """
        Get comprehensive metrics for the conversation.

        Returns:
            ConversationMetrics with all tracked data
        """
        final_status = self.check_completion()

        # Calculate average progress per turn
        if self._progress_history:
            progress_deltas = []
            prev_score = 0.0
            for p in self._progress_history:
                delta = max(0, p.score - prev_score)
                progress_deltas.append(delta)
                prev_score = p.score
            avg_progress_per_turn = sum(progress_deltas) / len(progress_deltas)
        else:
            avg_progress_per_turn = 0.0

        return ConversationMetrics(
            goal=self._goal,
            progress_history=list(self._progress_history),
            final_status=final_status,
            total_turns=self._turn_count,
            tools_used=list(set(self._tools_used)),
            context_preserved=True,  # Can be validated externally
            average_progress_per_turn=avg_progress_per_turn,
        )

    # =========================================================================
    # Integration Helpers
    # =========================================================================

    def validate_goal_progress(
        self,
        min_progress: float,
    ) -> bool:
        """
        Validate that progress meets minimum threshold.

        Used for scenario validation.

        Args:
            min_progress: Minimum required progress (0.0 to 1.0)

        Returns:
            True if current progress >= min_progress
        """
        if not self._progress_history:
            return min_progress <= 0.0

        current_progress = max(p.score for p in self._progress_history)
        return current_progress >= min_progress

    def validate_goal_achieved(
        self,
        min_progress: float = 0.8,
    ) -> bool:
        """
        Validate that goal is achieved.

        Used for scenario validation.

        Args:
            min_progress: Minimum progress to consider achieved (default 0.8)

        Returns:
            True if goal is achieved
        """
        status = self.check_completion()
        return status.progress >= min_progress

    def get_progress_trend(self) -> str:
        """
        Get the progress trend across turns.

        Returns:
            "improving", "stable", "declining", or "insufficient_data"
        """
        if len(self._progress_history) < 3:
            return "insufficient_data"

        scores = [p.score for p in self._progress_history]
        first_half = scores[: len(scores) // 2]
        second_half = scores[len(scores) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if second_avg > first_avg + 0.1:
            return "improving"
        elif second_avg < first_avg - 0.1:
            return "declining"
        else:
            return "stable"

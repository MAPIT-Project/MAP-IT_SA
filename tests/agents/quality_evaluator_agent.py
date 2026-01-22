"""
Quality Evaluator Agent for scoring response quality.

This agent uses LLM-as-judge methodology to evaluate:
- Query fulfillment
- Response specificity
- Factual accuracy
- Actionability

It supports:
- Single response evaluation
- Conversation flow quality tracking
- Quality degradation detection
- Comparative evaluation

Usage:
    evaluator = QualityEvaluatorAgent(llm_client)
    score = await evaluator.evaluate_response(query, response)
    assert score.total >= 85
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
import re
from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""

    name: str
    score: int
    max_score: int
    reasoning: str = ""

    @property
    def percentage(self) -> float:
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0


@dataclass
class QualityScore:
    """Complete quality score for a response."""

    total_score: int
    max_score: int
    dimension_scores: dict[str, DimensionScore] = field(default_factory=dict)
    passed: bool = False
    feedback: str = ""
    evaluation_time_ms: float = 0.0

    @property
    def percentage(self) -> float:
        return (self.total_score / self.max_score) * 100 if self.max_score > 0 else 0

    def get_dimension(self, name: str) -> DimensionScore | None:
        return self.dimension_scores.get(name)


@dataclass
class ConversationQualityResult:
    """Quality evaluation result for a full conversation."""

    turn_scores: list[QualityScore] = field(default_factory=list)
    average_score: float = 0.0
    min_score: float = 100.0
    max_score: float = 0.0
    degradation_detected: bool = False
    degradation_turn: int = -1
    degradation_amount: float = 0.0
    trend: str = "stable"  # "improving", "stable", "degrading"

    def add_turn_score(self, score: QualityScore):
        self.turn_scores.append(score)
        self._recalculate()

    def _recalculate(self):
        if not self.turn_scores:
            return

        scores = [s.total_score for s in self.turn_scores]
        self.average_score = sum(scores) / len(scores)
        self.min_score = min(scores)
        self.max_score = max(scores)

        # Detect degradation (drop of 15+ points from previous turn)
        for i in range(1, len(scores)):
            drop = scores[i - 1] - scores[i]
            if drop >= 15:
                self.degradation_detected = True
                self.degradation_turn = i
                self.degradation_amount = drop
                break

        # Determine trend
        if len(scores) >= 3:
            first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
            second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2)

            if second_half > first_half + 5:
                self.trend = "improving"
            elif second_half < first_half - 5:
                self.trend = "degrading"
            else:
                self.trend = "stable"


class QualityEvaluatorAgent:
    """
    Agent that evaluates response quality using LLM-as-judge.

    Features:
    - Multi-dimensional quality scoring
    - Conversation-level quality tracking
    - Quality degradation detection
    - Configurable passing threshold
    - Detailed feedback generation
    """

    # Default evaluation dimensions with weights
    DEFAULT_DIMENSIONS = [
        ("query_fulfillment", 40, "Does the response fully address the user's question?"),
        ("specificity", 25, "Is the response specific and detailed rather than vague?"),
        ("factual_accuracy", 25, "Is the information factually correct and verifiable?"),
        ("actionability", 10, "Can the user take action based on this response?"),
    ]

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        passing_threshold: int = 85,
        dimensions: list[tuple[str, int, str]] | None = None,
    ):
        """
        Initialize the quality evaluator.

        Args:
            model_name: Gemini model name for evaluation
            passing_threshold: Minimum score to pass (out of 100)
            dimensions: Custom dimensions as (name, max_points, description)
        """
        self.model_name = model_name
        self.passing_threshold = passing_threshold
        self.dimensions = dimensions or self.DEFAULT_DIMENSIONS
        self._model = None

        # Calculate max possible score
        self.max_total_score = sum(d[1] for d in self.dimensions)

    def _get_model(self):
        """Get or create the Gemini model."""
        if self._model is None and genai:
            try:
                self._model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                logger.error(f"Failed to create Gemini model: {e}")
        return self._model

    def _build_evaluation_prompt(
        self,
        query: str,
        response: str,
        context: str | None = None,
    ) -> str:
        """Build the evaluation prompt for the LLM."""
        dimension_descriptions = "\n".join(
            [
                f"- {name} ({max_points} points): {description}"
                for name, max_points, description in self.dimensions
            ]
        )

        context_section = ""
        if context:
            context_section = f"""
CONVERSATION CONTEXT:
{context}
"""

        return f"""You are an expert evaluator assessing AI responses about EU funding programmes.

EVALUATION DIMENSIONS:
{dimension_descriptions}

USER QUERY:
{query}
{context_section}
AI RESPONSE:
{response}

INSTRUCTIONS:
1. Evaluate the response against each dimension
2. Provide a score and brief reasoning for each
3. Be objective and consistent

OUTPUT FORMAT (use exactly this format):
QUERY_FULFILLMENT: [score]/{self.dimensions[0][1]}
Reasoning: [brief explanation]

SPECIFICITY: [score]/{self.dimensions[1][1]}
Reasoning: [brief explanation]

FACTUAL_ACCURACY: [score]/{self.dimensions[2][1]}
Reasoning: [brief explanation]

ACTIONABILITY: [score]/{self.dimensions[3][1]}
Reasoning: [brief explanation]

OVERALL_FEEDBACK: [1-2 sentence summary of strengths and weaknesses]

Now evaluate the response:"""

    def _parse_evaluation_response(self, eval_text: str) -> tuple[dict[str, DimensionScore], str]:
        """Parse the LLM evaluation response."""
        dimension_scores = {}
        feedback = ""

        # Mapping from prompt format to dimension names
        dimension_mapping = {
            "QUERY_FULFILLMENT": "query_fulfillment",
            "SPECIFICITY": "specificity",
            "FACTUAL_ACCURACY": "factual_accuracy",
            "ACTIONABILITY": "actionability",
        }

        for prompt_name, dim_name in dimension_mapping.items():
            # Find the dimension configuration
            dim_config = next((d for d in self.dimensions if d[0] == dim_name), None)
            if not dim_config:
                continue

            max_score = dim_config[1]

            # Extract score
            pattern = rf"{prompt_name}:\s*(\d+)/{max_score}"
            match = re.search(pattern, eval_text)

            if match:
                score = min(int(match.group(1)), max_score)
            else:
                # Try alternative patterns
                alt_pattern = rf"{prompt_name}:\s*(\d+)"
                alt_match = re.search(alt_pattern, eval_text)
                if alt_match:
                    score = min(int(alt_match.group(1)), max_score)
                else:
                    # Default to 70% if not found
                    score = int(max_score * 0.7)

            # Extract reasoning
            reasoning_pattern = (
                rf"{prompt_name}:.*?Reasoning:\s*(.+?)" r"(?=\n\n|\n[A-Z_]+:|OVERALL_FEEDBACK:|$)"
            )
            reasoning_match = re.search(reasoning_pattern, eval_text, re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

            dimension_scores[dim_name] = DimensionScore(
                name=dim_name,
                score=score,
                max_score=max_score,
                reasoning=reasoning,
            )

        # Extract overall feedback
        feedback_match = re.search(r"OVERALL_FEEDBACK:\s*(.+?)$", eval_text, re.DOTALL)
        if feedback_match:
            feedback = feedback_match.group(1).strip()

        return dimension_scores, feedback

    async def evaluate_response(
        self,
        query: str,
        response: str,
        context: str | None = None,
    ) -> QualityScore:
        """
        Evaluate a single response.

        Args:
            query: The user's query
            response: The AI response to evaluate
            context: Optional conversation context

        Returns:
            QualityScore with detailed dimension scores
        """
        start_time = datetime.now()

        model = self._get_model()
        if not model:
            # Return a default score if model unavailable
            return self._create_default_score("Model unavailable")

        prompt = self._build_evaluation_prompt(query, response, context)

        try:
            result = model.generate_content(prompt)
            eval_text = result.text

            dimension_scores, feedback = self._parse_evaluation_response(eval_text)

            total_score = sum(d.score for d in dimension_scores.values())

            quality_score = QualityScore(
                total_score=total_score,
                max_score=self.max_total_score,
                dimension_scores=dimension_scores,
                passed=total_score >= self.passing_threshold,
                feedback=feedback,
                evaluation_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

            return quality_score

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return self._create_default_score(f"Evaluation failed: {str(e)}")

    def _create_default_score(self, reason: str) -> QualityScore:
        """Create a default score when evaluation fails."""
        dimension_scores = {}
        for name, max_score, _ in self.dimensions:
            dimension_scores[name] = DimensionScore(
                name=name,
                score=int(max_score * 0.7),  # Default to 70%
                max_score=max_score,
                reasoning=reason,
            )

        total = sum(d.score for d in dimension_scores.values())

        return QualityScore(
            total_score=total,
            max_score=self.max_total_score,
            dimension_scores=dimension_scores,
            passed=total >= self.passing_threshold,
            feedback=reason,
        )

    async def evaluate_conversation(
        self,
        turns: list[dict[str, str]],
    ) -> ConversationQualityResult:
        """
        Evaluate quality across a full conversation.

        Args:
            turns: List of dicts with "query" and "response" keys

        Returns:
            ConversationQualityResult with per-turn scores and trends
        """
        result = ConversationQualityResult()

        context_parts = []

        for _i, turn in enumerate(turns):
            query = turn.get("query", turn.get("user_message", ""))
            response = turn.get("response", turn.get("response_text", ""))

            # Build context from previous turns
            context = "\n".join(context_parts[-4:]) if context_parts else None

            score = await self.evaluate_response(query, response, context)
            result.add_turn_score(score)

            # Add to context for next turn
            context_parts.append(f"User: {query[:200]}...")
            context_parts.append(f"Assistant: {response[:200]}...")

        return result

    async def evaluate_with_rubric(
        self,
        query: str,
        response: str,
        rubric: dict[str, list[str]],
    ) -> QualityScore:
        """
        Evaluate response against a specific rubric.

        Args:
            query: The user's query
            response: The AI response
            rubric: Dict mapping requirements to expected elements

        Returns:
            QualityScore based on rubric matching
        """
        dimension_scores = {}
        total_score = 0

        for dimension, requirements in rubric.items():
            matched = 0
            for req in requirements:
                if req.lower() in response.lower():
                    matched += 1

            # Find dimension config
            dim_config = next((d for d in self.dimensions if d[0] == dimension), None)
            if dim_config:
                max_score = dim_config[1]
                if requirements:
                    score = int((matched / len(requirements)) * max_score)
                else:
                    score = max_score
            else:
                max_score = 25
                if requirements:
                    score = int((matched / len(requirements)) * max_score)
                else:
                    score = max_score

            dimension_scores[dimension] = DimensionScore(
                name=dimension,
                score=score,
                max_score=max_score,
                reasoning=f"Matched {matched}/{len(requirements)} requirements",
            )
            total_score += score

        return QualityScore(
            total_score=total_score,
            max_score=self.max_total_score,
            dimension_scores=dimension_scores,
            passed=total_score >= self.passing_threshold,
            feedback=f"Rubric-based evaluation: {total_score}/{self.max_total_score}",
        )

    def quick_evaluate(
        self,
        response: str,
        expected_patterns: list[str],
        min_length: int = 100,
    ) -> QualityScore:
        """
        Quick rule-based evaluation without LLM.

        Args:
            response: The response to evaluate
            expected_patterns: Patterns that should appear
            min_length: Minimum acceptable response length

        Returns:
            QualityScore based on simple rules
        """
        scores = {}

        # Query fulfillment: pattern matching
        pattern_matches = sum(1 for p in expected_patterns if p.lower() in response.lower())
        if expected_patterns:
            pattern_score = int((pattern_matches / len(expected_patterns)) * 40)
        else:
            pattern_score = 30
        scores["query_fulfillment"] = DimensionScore(
            name="query_fulfillment",
            score=pattern_score,
            max_score=40,
            reasoning=f"Matched {pattern_matches}/{len(expected_patterns)} patterns",
        )

        # Specificity: length and detail indicators
        if len(response) >= min_length:
            specificity_score = 25
        else:
            specificity_score = int((len(response) / min_length) * 25)
        detail_words = ["specifically", "for example", "such as", "including"]
        if any(word in response.lower() for word in detail_words):
            specificity_score = min(25, specificity_score + 5)
        scores["specificity"] = DimensionScore(
            name="specificity",
            score=specificity_score,
            max_score=25,
            reasoning=f"Response length: {len(response)} chars",
        )

        # Factual accuracy: assume good unless obvious issues
        accuracy_score = 20 if len(response) > 50 else 15
        scores["factual_accuracy"] = DimensionScore(
            name="factual_accuracy",
            score=accuracy_score,
            max_score=25,
            reasoning="Rule-based estimate",
        )

        # Actionability: look for actionable language
        actionable_words = ["can", "should", "apply", "visit", "check", "contact", "submit"]
        actionable_count = sum(1 for w in actionable_words if w in response.lower())
        actionability_score = min(10, actionable_count * 2)
        scores["actionability"] = DimensionScore(
            name="actionability",
            score=actionability_score,
            max_score=10,
            reasoning=f"Found {actionable_count} actionable indicators",
        )

        total = sum(s.score for s in scores.values())

        return QualityScore(
            total_score=total,
            max_score=100,
            dimension_scores=scores,
            passed=total >= self.passing_threshold,
            feedback="Quick rule-based evaluation",
        )

    async def compare_responses(
        self,
        query: str,
        response_a: str,
        response_b: str,
    ) -> dict[str, Any]:
        """
        Compare two responses and determine which is better.

        Args:
            query: The user's query
            response_a: First response
            response_b: Second response

        Returns:
            Comparison result with scores and winner
        """
        score_a = await self.evaluate_response(query, response_a)
        score_b = await self.evaluate_response(query, response_b)

        if score_a.total_score > score_b.total_score:
            winner = "A"
            margin = score_a.total_score - score_b.total_score
        elif score_b.total_score > score_a.total_score:
            winner = "B"
            margin = score_b.total_score - score_a.total_score
        else:
            winner = "Tie"
            margin = 0

        return {
            "winner": winner,
            "margin": margin,
            "score_a": score_a,
            "score_b": score_b,
            "dimension_comparison": {
                dim: {
                    "a": score_a.dimension_scores.get(dim, DimensionScore(dim, 0, 0)).score,
                    "b": score_b.dimension_scores.get(dim, DimensionScore(dim, 0, 0)).score,
                }
                for dim, _, _ in self.dimensions
            },
        }

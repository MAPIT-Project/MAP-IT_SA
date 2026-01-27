"""
Result Evaluator

Evaluates search results to determine if they sufficiently answer the user's query.
Uses rule-based heuristics for speed, with optional LLM evaluation for edge cases.
"""

import logging
import re
from typing import Any

from .context import AgentContext, EvaluationResult

logger = logging.getLogger(__name__)


class ResultEvaluator:
    """
    Evaluates search results quality.

    Scoring criteria:
    1. Result count - Do we have enough results?
    2. Relevance scores - Are results actually relevant?
    3. Content depth - Do results have substantial content?
    4. Query coverage - Do results contain query terms?
    5. Source diversity - Are results from multiple sources?
    """

    # Thresholds
    MIN_RESULTS_FACTUAL = 2  # Minimum for factual queries
    MIN_RESULTS_EXPLORATORY = 4  # Minimum for exploratory queries
    MIN_RELEVANCE_SCORE = 0.5  # Minimum average relevance
    MIN_CONTENT_LENGTH = 50  # Minimum chars of actual content
    SUFFICIENT_SCORE = 0.65  # Score threshold for "good enough"

    def evaluate(
        self, query: str, query_type: str, results: dict[str, Any], context: AgentContext
    ) -> EvaluationResult:
        """
        Evaluate if results sufficiently answer the query.

        Args:
            query: Original user query
            query_type: 'factual', 'exploratory', or 'procedural'
            results: Search results from execution
            context: Agent context for history

        Returns:
            EvaluationResult with score and analysis
        """
        scores = []
        reasons = []
        suggestions = []

        # 1. Count check
        count_score, count_reason = self._evaluate_count(results, query_type)
        scores.append(count_score)
        reasons.append(count_reason)

        # 2. Relevance check
        relevance_score, relevance_reason = self._evaluate_relevance(results)
        scores.append(relevance_score)
        reasons.append(relevance_reason)

        # 3. Content depth check
        content_score, content_reason = self._evaluate_content_depth(results)
        scores.append(content_score)
        reasons.append(content_reason)

        # 4. Query term coverage
        coverage_score, coverage_reason = self._evaluate_query_coverage(query, results)
        scores.append(coverage_score)
        reasons.append(coverage_reason)

        # 5. Source diversity
        diversity_score, diversity_reason = self._evaluate_source_diversity(results, context)
        scores.append(diversity_score)
        reasons.append(diversity_reason)

        # Calculate weighted final score
        # Count and relevance are most important
        weights = [0.25, 0.30, 0.20, 0.15, 0.10]
        final_score = sum(s * w for s, w in zip(scores, weights, strict=False))

        # Generate suggestions for improvement
        if final_score < self.SUFFICIENT_SCORE:
            suggestions = self._generate_suggestions(scores, results, query, context)

        is_sufficient = final_score >= self.SUFFICIENT_SCORE

        logger.info(
            f"📊 Evaluation: score={final_score:.2f}, sufficient={is_sufficient}, "
            f"counts=[{', '.join(f'{s:.1f}' for s in scores)}]"
        )

        return EvaluationResult(
            score=final_score,
            is_sufficient=is_sufficient,
            reasons=[r for r in reasons if r],  # Filter empty
            suggestions=suggestions,
        )

    def _evaluate_count(self, results: dict[str, Any], query_type: str) -> tuple[float, str]:
        """Evaluate if we have enough results."""
        total = self._count_results(results)

        min_required = (
            self.MIN_RESULTS_FACTUAL if query_type == "factual" else self.MIN_RESULTS_EXPLORATORY
        )

        if total == 0:
            return 0.0, "No results found"
        elif total >= min_required * 2:
            return 1.0, f"Excellent: {total} results found"
        elif total >= min_required:
            return 0.7, f"Good: {total} results (min: {min_required})"
        else:
            return 0.3, f"Limited: only {total} results (need {min_required})"

    def _evaluate_relevance(self, results: dict[str, Any]) -> tuple[float, str]:
        """Evaluate average relevance of results."""
        all_scores = []

        # Check different result types
        for key in ["graph_results", "vector_results", "calls", "documents", "results"]:
            items = results.get(key, [])
            if isinstance(items, list):
                for item in items:
                    score = self._extract_relevance_score(item)
                    if score is not None:
                        all_scores.append(score)

        if not all_scores:
            return 0.5, "No relevance scores available"

        avg_score = sum(all_scores) / len(all_scores)

        if avg_score >= 0.8:
            return 1.0, f"High relevance: {avg_score:.2f}"
        elif avg_score >= self.MIN_RELEVANCE_SCORE:
            return 0.7, f"Good relevance: {avg_score:.2f}"
        elif avg_score >= 0.3:
            return 0.4, f"Low relevance: {avg_score:.2f}"
        else:
            return 0.1, f"Very low relevance: {avg_score:.2f}"

    def _evaluate_content_depth(self, results: dict[str, Any]) -> tuple[float, str]:
        """Evaluate if results have substantial content."""
        content_lengths = []

        for key in ["graph_results", "vector_results", "calls", "documents", "results"]:
            items = results.get(key, [])
            if isinstance(items, list):
                for item in items:
                    content = self._extract_content(item)
                    if content:
                        content_lengths.append(len(content))

        if not content_lengths:
            return 0.3, "No content found in results"

        avg_length = sum(content_lengths) / len(content_lengths)
        long_content_count = sum(1 for length in content_lengths if length > 200)

        if avg_length > 300 and long_content_count >= 2:
            return 1.0, "Rich content with detailed descriptions"
        elif avg_length > 150:
            return 0.7, "Good content depth"
        elif avg_length > self.MIN_CONTENT_LENGTH:
            return 0.5, "Basic content available"
        else:
            return 0.2, "Shallow content - mostly titles/metadata"

    def _evaluate_query_coverage(self, query: str, results: dict[str, Any]) -> tuple[float, str]:
        """Evaluate how many query terms appear in results."""
        # Extract key terms from query (simple approach)
        query_terms = set(
            word.lower()
            for word in re.findall(r"\b\w{3,}\b", query.lower())
            if word not in {"the", "and", "for", "with", "what", "how", "are", "can", "does"}
        )

        if not query_terms:
            return 0.5, "Could not extract query terms"

        # Collect all content
        all_content = self._collect_all_content(results).lower()

        # Check coverage
        found_terms = [t for t in query_terms if t in all_content]
        coverage = len(found_terms) / len(query_terms) if query_terms else 0

        if coverage >= 0.8:
            return 1.0, f"Excellent query coverage: {coverage:.0%}"
        elif coverage >= 0.5:
            return 0.7, f"Good query coverage: {coverage:.0%}"
        elif coverage >= 0.3:
            return 0.4, f"Partial query coverage: {coverage:.0%}"
        else:
            missing = [t for t in query_terms if t not in all_content]
            return 0.1, f"Low coverage ({coverage:.0%}), missing: {', '.join(missing[:3])}"

    def _evaluate_source_diversity(
        self, results: dict[str, Any], context: AgentContext
    ) -> tuple[float, str]:
        """Evaluate if results come from diverse sources."""
        sources_used = set()

        if results.get("graph_results"):
            sources_used.add("graph")
        if results.get("vector_results"):
            sources_used.add("vector")
        if results.get("calls"):
            sources_used.add("calls")
        if results.get("documents"):
            sources_used.add("documents")

        # Also check context for what sources were tried
        set(context.tried_sources) | sources_used

        if len(sources_used) >= 3:
            return 1.0, f"Diverse sources: {', '.join(sources_used)}"
        elif len(sources_used) >= 2:
            return 0.7, f"Multiple sources: {', '.join(sources_used)}"
        elif len(sources_used) == 1:
            return 0.4, f"Single source: {', '.join(sources_used)}"
        else:
            return 0.1, "No sources returned results"

    def _generate_suggestions(
        self, scores: list[float], results: dict[str, Any], query: str, context: AgentContext
    ) -> list[str]:
        """Generate suggestions for improving results."""
        suggestions = []

        # Based on which scores are low
        count_score, relevance_score, content_score, coverage_score, diversity_score = scores

        if count_score < 0.5:
            if "vector" not in context.tried_sources:
                suggestions.append("Try semantic search in document database")
            if "graph" not in context.tried_sources:
                suggestions.append("Try graph database for structured data")
            suggestions.append("Broaden search query terms")

        if relevance_score < 0.5:
            suggestions.append("Refine query to be more specific")
            suggestions.append("Try keyword search instead of semantic")

        if content_score < 0.5:
            suggestions.append("Look for detailed documents rather than summaries")
            if "calls" in context.tried_sources:
                suggestions.append("Enrich call data from EU Portal API")

        if coverage_score < 0.5:
            # Extract missing terms and suggest
            suggestions.append("Add missing key terms to search query")

        if diversity_score < 0.5:
            untried = {"graph", "vector", "calls"} - set(context.tried_sources)
            if untried:
                suggestions.append(f"Try additional sources: {', '.join(untried)}")

        return suggestions[:3]  # Return top 3 suggestions

    def _count_results(self, results: dict[str, Any]) -> int:
        """Count total number of results."""
        total = 0
        for key in ["graph_results", "vector_results", "calls", "documents", "results"]:
            items = results.get(key, [])
            if isinstance(items, list):
                total += len(items)
        return total

    def _extract_relevance_score(self, item: Any) -> float | None:
        """Extract relevance score from a result item."""
        if isinstance(item, dict):
            for key in ["score", "relevance_score", "similarity", "relevance"]:
                if key in item:
                    score = item[key]
                    if isinstance(score, int | float):
                        return float(score)
        return None

    def _extract_content(self, item: Any) -> str:
        """Extract text content from a result item."""
        if isinstance(item, dict):
            for key in ["content", "description", "scope", "text", "summary", "expected_outcome"]:
                if key in item and item[key]:
                    return str(item[key])
            # Combine title + description if available
            parts = []
            if item.get("title"):
                parts.append(str(item["title"]))
            if item.get("description"):
                parts.append(str(item["description"]))
            return " ".join(parts)
        elif isinstance(item, str):
            return item
        return ""

    def _collect_all_content(self, results: dict[str, Any]) -> str:
        """Collect all text content from results."""
        all_text = []

        for key in ["graph_results", "vector_results", "calls", "documents", "results"]:
            items = results.get(key, [])
            if isinstance(items, list):
                for item in items:
                    content = self._extract_content(item)
                    if content:
                        all_text.append(content)

        return " ".join(all_text)

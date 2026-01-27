"""
Result Evaluator

Evaluates search results to determine if they sufficiently answer the user's query.

Strategy:
1. Rule-based evaluation first (fast, cheap)
2. If score is in "uncertain zone" (0.4-0.7), use LLM evaluation
3. LLM evaluation is more accurate but costs tokens

This hybrid approach balances accuracy with cost.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating search results."""
    score: float  # 0.0 to 1.0
    is_sufficient: bool
    reasons: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


class ResultEvaluator:
    """
    Evaluates search results to determine if they answer the user's query.
    
    Hybrid approach:
    1. Rule-based evaluation (fast, free)
    2. LLM evaluation for uncertain cases (accurate, costs tokens)
    
    The "uncertain zone" is 0.4-0.7 - these cases benefit from LLM judgment.
    """
    
    # Thresholds
    SUFFICIENT_SCORE = 0.65  # Score needed to consider results sufficient
    UNCERTAIN_LOW = 0.40     # Below this = clearly bad
    UNCERTAIN_HIGH = 0.70    # Above this = clearly good
    
    # Query type specific thresholds
    THRESHOLDS = {
        'factual': {
            'min_results': 1,
            'min_relevance': 0.6,
            'min_content_length': 50,
        },
        'exploratory': {
            'min_results': 3,
            'min_relevance': 0.5,
            'min_content_length': 100,
        },
        'procedural': {
            'min_results': 2,
            'min_relevance': 0.55,
            'min_content_length': 150,
        },
        'comparison': {
            'min_results': 2,
            'min_relevance': 0.5,
            'min_content_length': 100,
        },
        'default': {
            'min_results': 2,
            'min_relevance': 0.5,
            'min_content_length': 50,
        }
    }
    
    def __init__(self, use_llm_evaluation: bool = True):
        """
        Initialize the evaluator.
        
        Args:
            use_llm_evaluation: Whether to use LLM for edge cases (default: True)
        """
        self.use_llm_evaluation = use_llm_evaluation
        self.llm = None
        
        if use_llm_evaluation:
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
                model_name = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
                self.llm = genai.GenerativeModel(model_name)
                logger.info(f"🧠 ResultEvaluator LLM enabled: {model_name}")
            except Exception as e:
                logger.warning(f"LLM evaluation disabled: {e}")
                self.llm = None
    
    def evaluate(
        self,
        query: str,
        query_type: str,
        results: dict[str, Any],
        entities: list[str] = None
    ) -> EvaluationResult:
        """
        Evaluate if results sufficiently answer the query.
        
        Uses hybrid approach:
        1. Rule-based evaluation first (fast)
        2. LLM evaluation for uncertain cases (score 0.4-0.7)
        
        Args:
            query: Original user query
            query_type: Type of query (factual, exploratory, etc.)
            results: Search results dictionary
            entities: Extracted entities from query
            
        Returns:
            EvaluationResult with score and analysis
        """
        thresholds = self.THRESHOLDS.get(query_type, self.THRESHOLDS['default'])
        
        # Collect all metrics
        metrics = {}
        reasons = []
        suggestions = []
        
        # Metric 1: Result count
        result_count = self._count_results(results)
        metrics['result_count'] = result_count
        count_score, count_reason = self._evaluate_result_count(
            result_count, thresholds['min_results']
        )
        reasons.append(count_reason)
        
        # Metric 2: Relevance scores
        avg_relevance = self._calculate_average_relevance(results)
        metrics['avg_relevance'] = avg_relevance
        relevance_score, relevance_reason = self._evaluate_relevance(
            avg_relevance, thresholds['min_relevance']
        )
        reasons.append(relevance_reason)
        
        # Metric 3: Content quality
        has_content, content_score = self._evaluate_content_quality(
            results, thresholds['min_content_length']
        )
        metrics['content_score'] = content_score
        if has_content:
            reasons.append("Results have detailed content")
        else:
            reasons.append("Results lack detailed content")
            suggestions.append("Try searching with more specific terms")
        
        # Metric 4: Query term coverage
        term_coverage = self._calculate_term_coverage(query, results, entities)
        metrics['term_coverage'] = term_coverage
        coverage_score, coverage_reason = self._evaluate_term_coverage(term_coverage)
        reasons.append(coverage_reason)
        
        # Metric 5: Source diversity
        source_diversity = self._calculate_source_diversity(results)
        metrics['source_diversity'] = source_diversity
        
        # Metric 6: Freshness (for time-sensitive queries)
        freshness_score = self._evaluate_freshness(results, query)
        metrics['freshness'] = freshness_score
        
        # Calculate weighted final score (rule-based)
        rule_based_score = self._calculate_final_score(
            count_score=count_score,
            relevance_score=relevance_score,
            content_score=content_score,
            coverage_score=coverage_score,
            source_diversity=source_diversity,
            freshness_score=freshness_score,
            query_type=query_type
        )
        
        # Check if we should use LLM evaluation for edge cases
        final_score = rule_based_score
        llm_used = False
        
        if (self.use_llm_evaluation and 
            self.llm is not None and 
            self.UNCERTAIN_LOW <= rule_based_score <= self.UNCERTAIN_HIGH):
            
            # Edge case - use LLM for more accurate evaluation
            logger.info(f"📊 Rule-based score {rule_based_score:.2f} in uncertain zone, using LLM evaluation")
            
            try:
                llm_result = self._llm_evaluate(query, query_type, results, entities)
                if llm_result:
                    # Combine rule-based and LLM scores (LLM weighted higher)
                    final_score = (rule_based_score * 0.3) + (llm_result['score'] * 0.7)
                    reasons.extend(llm_result.get('reasons', []))
                    suggestions.extend(llm_result.get('suggestions', []))
                    llm_used = True
                    logger.info(f"🧠 LLM evaluation: {llm_result['score']:.2f} → combined: {final_score:.2f}")
            except Exception as e:
                logger.warning(f"LLM evaluation failed: {e}")
        
        metrics['llm_used'] = llm_used
        metrics['rule_based_score'] = rule_based_score
        
        # Determine if sufficient
        is_sufficient = final_score >= self.SUFFICIENT_SCORE
        
        # Generate suggestions if not sufficient
        if not is_sufficient:
            suggestions.extend(self._generate_suggestions(
                metrics, query, query_type, results
            ))
        
        logger.info(
            f"Evaluation: score={final_score:.2f}, sufficient={is_sufficient}, "
            f"results={result_count}, relevance={avg_relevance:.2f}, llm={llm_used}"
        )
        
        return EvaluationResult(
            score=final_score,
            is_sufficient=is_sufficient,
            reasons=reasons,
            suggestions=suggestions,
            metrics=metrics
        )
    
    def _llm_evaluate(
        self,
        query: str,
        query_type: str,
        results: dict[str, Any],
        entities: list[str] = None
    ) -> dict[str, Any] | None:
        """
        Use LLM to evaluate result quality for edge cases.
        
        Returns dict with score, reasons, and suggestions.
        """
        # Format results for LLM
        results_summary = self._format_results_for_llm(results)
        
        prompt = f"""You are evaluating if search results adequately answer a user's question.

**USER QUESTION:** {query}
**QUESTION TYPE:** {query_type}
**KEY ENTITIES:** {entities or 'None specified'}

**SEARCH RESULTS:**
{results_summary}

**EVALUATION CRITERIA:**
1. RELEVANCE: Do the results relate to the question?
2. COMPLETENESS: Do they fully answer what was asked?
3. ACCURACY: Do they appear factually correct?
4. ACTIONABLE: Can the user act on this information?

**SCORING:**
- 0.9-1.0: Excellent - fully answers the question with high quality
- 0.7-0.9: Good - answers the question but may miss some details
- 0.5-0.7: Partial - answers some aspects but misses important parts
- 0.3-0.5: Poor - barely related or very incomplete
- 0.0-0.3: Bad - doesn't answer the question at all

**OUTPUT FORMAT (JSON only):**
```json
{{
    "score": 0.75,
    "is_sufficient": true,
    "reasons": ["Results directly address eligibility requirements", "Missing specific country details"],
    "suggestions": ["Search for country-specific rules"],
    "explanation": "Brief explanation of your reasoning"
}}
```

Evaluate the results:"""

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config={'temperature': 0.1, 'max_output_tokens': 500}
            )
            
            # Safely get response text
            try:
                response_text = response.text
            except Exception:
                # Response might not have text (safety filter, etc.)
                logger.warning("LLM response has no text, skipping")
                return None
            
            # Parse JSON from response
            json_str = None
            
            # Try code block first
            code_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if code_match:
                json_str = code_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
            
            if json_str:
                # Clean up JSON
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
            
        except Exception as e:
            logger.error(f"LLM evaluation error: {e}")
        
        return None
    
    def _format_results_for_llm(self, results: dict[str, Any], max_chars: int = 2000) -> str:
        """Format results for LLM evaluation prompt."""
        parts = []
        total_chars = 0
        
        for source in ['graph', 'vector', 'documents', 'results']:
            if source in results and total_chars < max_chars:
                data = results[source]
                if isinstance(data, dict):
                    items = data.get('results', [])
                elif isinstance(data, list):
                    items = data
                else:
                    continue
                
                for i, item in enumerate(items[:3]):  # Max 3 per source
                    if isinstance(item, dict):
                        content = item.get('content', str(item))[:300]
                        score = item.get('score', 'N/A')
                        parts.append(f"[{source.upper()} {i+1}] (score: {score})\n{content}\n")
                        total_chars += len(parts[-1])
                        
                        if total_chars >= max_chars:
                            break
        
        return "\n".join(parts) if parts else "No results found"
    
    def _count_results(self, results: dict[str, Any]) -> int:
        """Count total results across all sources."""
        total = 0
        
        # Graph results
        if 'graph' in results:
            graph_data = results['graph']
            if isinstance(graph_data, dict):
                total += len(graph_data.get('results', []))
            elif isinstance(graph_data, list):
                total += len(graph_data)
            
        # Vector results
        if 'vector' in results:
            vector_data = results['vector']
            if isinstance(vector_data, dict):
                total += len(vector_data.get('results', []))
            elif isinstance(vector_data, list):
                total += len(vector_data)
            
        # Document results
        if 'documents' in results:
            total += len(results['documents'])
            
        # Calls results
        if 'calls' in results:
            total += len(results.get('calls', []))
        
        # Generic results list
        if 'results' in results:
            total += len(results['results'])
        
        return total
    
    def _evaluate_result_count(self, count: int, min_required: int) -> tuple[float, str]:
        """Evaluate result count against threshold."""
        if count == 0:
            return 0.0, "No results found"
        elif count >= min_required * 2:
            return 1.0, f"Found {count} results (excellent coverage)"
        elif count >= min_required:
            return 0.7, f"Found {count} results (sufficient)"
        else:
            return 0.3, f"Only {count} results (need at least {min_required})"
    
    def _calculate_average_relevance(self, results: dict[str, Any]) -> float:
        """Calculate average relevance score across results."""
        scores = []
        
        for source in ['graph', 'vector', 'documents', 'results']:
            if source in results:
                data = results[source]
                if isinstance(data, dict):
                    items = data.get('results', [])
                elif isinstance(data, list):
                    items = data
                else:
                    continue
                
            for item in items:
                if isinstance(item, dict):
                        score = item.get('score') or item.get('relevance_score') or item.get('similarity', 0)
                        if score:
                            scores.append(float(score))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _evaluate_relevance(self, avg_relevance: float, min_relevance: float) -> tuple[float, str]:
        """Evaluate average relevance score."""
        if avg_relevance >= min_relevance + 0.2:
            return 1.0, f"High relevance score: {avg_relevance:.2f}"
        elif avg_relevance >= min_relevance:
            return 0.7, f"Good relevance score: {avg_relevance:.2f}"
        elif avg_relevance >= min_relevance - 0.1:
            return 0.4, f"Moderate relevance: {avg_relevance:.2f}"
        else:
            return 0.2, f"Low relevance: {avg_relevance:.2f}"
    
    def _evaluate_content_quality(
        self, 
        results: dict[str, Any], 
        min_length: int
    ) -> tuple[bool, float]:
        """Evaluate if results have substantial content."""
        content_lengths = []
        
        for source in ['graph', 'vector', 'documents', 'results']:
            if source in results:
                data = results[source]
                items = data.get('results', []) if isinstance(data, dict) else data
                
                for item in (items if isinstance(items, list) else []):
                    if isinstance(item, dict):
                        content = item.get('content') or item.get('description') or item.get('scope') or ''
                        content_lengths.append(len(content))
        
        if not content_lengths:
            return False, 0.0
        
        avg_length = sum(content_lengths) / len(content_lengths)
        has_content = avg_length >= min_length
        
        # Score based on content length
        if avg_length >= min_length * 3:
            score = 1.0
        elif avg_length >= min_length * 2:
            score = 0.8
        elif avg_length >= min_length:
            score = 0.6
        elif avg_length >= min_length / 2:
            score = 0.3
        else:
            score = 0.1
        
        return has_content, score
    
    def _calculate_term_coverage(
        self, 
        query: str, 
        results: dict[str, Any],
        entities: list[str] = None
    ) -> float:
        """Calculate what fraction of query terms appear in results."""
        # Extract important terms from query
        query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))
        
        # Add entities
        if entities:
            for entity in entities:
                query_terms.update(re.findall(r'\b\w{3,}\b', entity.lower()))
        
        # Remove common stopwords
        stopwords = {'the', 'and', 'for', 'are', 'what', 'how', 'can', 'does', 'about', 'with'}
        query_terms -= stopwords
        
        if not query_terms:
            return 1.0  # No terms to check
        
        # Collect all result text
        result_text = ""
        for source_data in results.values():
            if isinstance(source_data, dict):
                items = source_data.get('results', [])
            elif isinstance(source_data, list):
                items = source_data
            else:
                continue
            
            for item in items:
                if isinstance(item, dict):
                    result_text += " " + str(item.get('content', ''))
                    result_text += " " + str(item.get('title', ''))
                    result_text += " " + str(item.get('description', ''))
        
        result_text = result_text.lower()
        
        # Count how many query terms appear
        found_terms = sum(1 for term in query_terms if term in result_text)
        
        return found_terms / len(query_terms) if query_terms else 0.0
    
    def _evaluate_term_coverage(self, coverage: float) -> tuple[float, str]:
        """Evaluate query term coverage."""
        if coverage >= 0.8:
            return 1.0, f"Excellent query term coverage: {coverage:.0%}"
        elif coverage >= 0.6:
            return 0.7, f"Good query term coverage: {coverage:.0%}"
        elif coverage >= 0.4:
            return 0.4, f"Partial query term coverage: {coverage:.0%}"
        else:
            return 0.2, f"Poor query term coverage: {coverage:.0%}"
    
    def _calculate_source_diversity(self, results: dict[str, Any]) -> float:
        """Calculate diversity of sources in results."""
        sources_with_results = 0
        total_sources = 0
        
        for source in ['graph', 'vector', 'documents', 'calls', 'api']:
            if source in results:
                total_sources += 1
                data = results[source]
                if isinstance(data, dict):
                    if data.get('results') or data.get('success'):
                        sources_with_results += 1
                elif isinstance(data, list) and len(data) > 0:
                    sources_with_results += 1
        
        if total_sources == 0:
            return 0.0
        
        return sources_with_results / total_sources
    
    def _evaluate_freshness(self, results: dict[str, Any], query: str) -> float:
        """Evaluate freshness of results (for time-sensitive queries)."""
        # Check if query is time-sensitive
        time_sensitive_terms = ['2025', '2026', 'current', 'latest', 'new', 'upcoming', 'open']
        is_time_sensitive = any(term in query.lower() for term in time_sensitive_terms)
        
        if not is_time_sensitive:
            return 0.7  # Neutral score for non-time-sensitive queries
        
        # Check for recent dates in results
        recent_years = ['2025', '2026', '2024']
        result_text = str(results).lower()
        
        has_recent = any(year in result_text for year in recent_years)
        
        return 1.0 if has_recent else 0.3
    
    def _calculate_final_score(
        self,
        count_score: float,
        relevance_score: float,
        content_score: float,
        coverage_score: float,
        source_diversity: float,
        freshness_score: float,
        query_type: str
    ) -> float:
        """Calculate weighted final score based on query type."""
        
        # Weights vary by query type
        weights = {
            'factual': {
                'count': 0.15,
                'relevance': 0.30,
                'content': 0.25,
                'coverage': 0.20,
                'diversity': 0.05,
                'freshness': 0.05
            },
            'exploratory': {
                'count': 0.25,
                'relevance': 0.20,
                'content': 0.20,
                'coverage': 0.15,
                'diversity': 0.15,
                'freshness': 0.05
            },
            'procedural': {
                'count': 0.10,
                'relevance': 0.25,
                'content': 0.35,
                'coverage': 0.20,
                'diversity': 0.05,
                'freshness': 0.05
            },
            'default': {
                'count': 0.20,
                'relevance': 0.25,
                'content': 0.25,
                'coverage': 0.15,
                'diversity': 0.10,
                'freshness': 0.05
            }
        }
        
        w = weights.get(query_type, weights['default'])
        
        final_score = (
            count_score * w['count'] +
            relevance_score * w['relevance'] +
            content_score * w['content'] +
            coverage_score * w['coverage'] +
            source_diversity * w['diversity'] +
            freshness_score * w['freshness']
        )
        
        return min(1.0, max(0.0, final_score))
    
    def _generate_suggestions(
        self,
        metrics: dict[str, float],
        query: str,
        query_type: str,
        results: dict[str, Any]
    ) -> list[str]:
        """Generate improvement suggestions based on metrics."""
        suggestions = []
        
        if metrics.get('result_count', 0) == 0:
            suggestions.append("broaden_query: Try using more general terms")
            suggestions.append("change_source: Try a different data source")
        
        elif metrics.get('avg_relevance', 0) < 0.5:
            suggestions.append("refine_query: Make the query more specific")
            suggestions.append("add_keywords: Add domain-specific keywords")
        
        elif metrics.get('term_coverage', 0) < 0.5:
            suggestions.append("keyword_search: Try keyword-based search instead of semantic")
        
        elif metrics.get('content_score', 0) < 0.5:
            suggestions.append("expand_results: Get more detailed results")
            suggestions.append("different_source: Try document search for detailed content")
        
        return suggestions

"""
Reflector

Analyzes failed search attempts and determines what went wrong.
Provides insights for the replanner to create better strategies.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from .result_evaluator import EvaluationResult

logger = logging.getLogger(__name__)


class FailureRootCause(Enum):
    """Categorized root causes for search failures."""
    QUERY_TOO_BROAD = "query_too_broad"
    QUERY_TOO_NARROW = "query_too_narrow"
    WRONG_SOURCE = "wrong_source"
    MISSING_CONTEXT = "missing_context"
    SEMANTIC_MISMATCH = "semantic_mismatch"  # Semantic search didn't find keyword matches
    DATA_NOT_AVAILABLE = "data_not_available"
    TEMPORAL_MISMATCH = "temporal_mismatch"  # Looking for future/past data
    ENTITY_NOT_FOUND = "entity_not_found"
    UNKNOWN = "unknown"


class ImprovementAction(Enum):
    """Possible improvement actions."""
    REFINE_QUERY = "refine_query"
    BROADEN_QUERY = "broaden_query"
    CHANGE_SOURCE = "change_source"
    ADD_KEYWORDS = "add_keywords"
    TRY_KEYWORD_SEARCH = "try_keyword_search"
    TRY_SEMANTIC_SEARCH = "try_semantic_search"
    ADD_CONTEXT = "add_context"
    NARROW_TIME_RANGE = "narrow_time_range"
    ACKNOWLEDGE_LIMITATION = "acknowledge_limitation"


@dataclass
class ReflectionResult:
    """Result of analyzing a failed attempt."""
    failure_analysis: str
    root_cause: FailureRootCause
    confidence: float  # 0-1
    improvement_action: ImprovementAction
    suggested_query: Optional[str] = None
    suggested_sources: List[str] = field(default_factory=list)
    reasoning: str = ""


class Reflector:
    """
    Analyzes failed attempts and suggests improvements.
    
    Phase 1: Rule-based reflection
    Phase 2: LLM-assisted reflection for complex cases
    """
    
    # Patterns that indicate specific root causes
    PATTERNS = {
        'too_broad': [
            r'^(what|how|why|tell me about)\s+\w+$',  # Very short queries
            r'(everything|all|any)',
        ],
        'too_narrow': [
            r'HORIZON-[A-Z0-9]+-\d{4}-[A-Z0-9]+-\d+-\d+',  # Very specific call ID
            r'"[^"]+"',  # Quoted exact phrases
        ],
        'temporal': [
            r'(2024|2025|2026|2027|2028)',
            r'(upcoming|future|next year|latest|current)',
            r'(deadline|open.*call|closing)',
        ],
    }
    
    def reflect(
        self,
        query: str,
        evaluation: EvaluationResult,
        current_plan: Dict,
        results: Dict[str, Any],
        failed_strategies: List[str],
        entities: List[str] = None
    ) -> ReflectionResult:
        """
        Analyze why results were insufficient and suggest improvements.
        
        Args:
            query: Original user query
            evaluation: The evaluation that determined results were insufficient
            current_plan: The plan that was executed
            results: The results obtained
            failed_strategies: List of previously failed strategies (to avoid)
            entities: Extracted entities
            
        Returns:
            ReflectionResult with analysis and suggestions
        """
        
        # Step 1: Analyze the evaluation metrics
        metrics = evaluation.metrics
        suggestions = evaluation.suggestions
        
        # Step 2: Determine root cause
        root_cause, confidence = self._determine_root_cause(
            query, metrics, results, current_plan, entities
        )
        
        # Step 3: Generate improvement strategy
        action, suggested_query, suggested_sources = self._generate_improvement(
            query, root_cause, current_plan, failed_strategies, metrics, entities
        )
        
        # Step 4: Create analysis narrative
        analysis = self._create_analysis_narrative(
            root_cause, metrics, current_plan, entities
        )
        
        reasoning = self._create_reasoning(
            root_cause, action, suggested_query, suggested_sources
        )
        
        logger.info(
            f"Reflection: root_cause={root_cause.value}, "
            f"action={action.value}, confidence={confidence:.2f}"
        )
        
        return ReflectionResult(
            failure_analysis=analysis,
            root_cause=root_cause,
            confidence=confidence,
            improvement_action=action,
            suggested_query=suggested_query,
            suggested_sources=suggested_sources,
            reasoning=reasoning
        )
    
    def _determine_root_cause(
        self,
        query: str,
        metrics: Dict[str, float],
        results: Dict[str, Any],
        plan: Dict,
        entities: List[str] = None
    ) -> Tuple[FailureRootCause, float]:
        """Determine the most likely root cause of failure."""
        
        causes_scores = []
        
        # Check 1: No results at all
        if metrics.get('result_count', 0) == 0:
            # Could be query too narrow, wrong source, or data not available
            
            # Check if it's a very specific query
            if any(re.search(p, query) for p in self.PATTERNS['too_narrow']):
                causes_scores.append((FailureRootCause.QUERY_TOO_NARROW, 0.8))
            else:
                # Check what sources were tried
                sources_tried = [s.get('source') for s in plan.get('steps', [])]
                if len(sources_tried) < 2:
                    causes_scores.append((FailureRootCause.WRONG_SOURCE, 0.7))
                else:
                    causes_scores.append((FailureRootCause.DATA_NOT_AVAILABLE, 0.6))
        
        # Check 2: Low relevance scores
        elif metrics.get('avg_relevance', 0) < 0.4:
            # Could be semantic mismatch or query too broad
            
            if any(re.search(p, query) for p in self.PATTERNS['too_broad']):
                causes_scores.append((FailureRootCause.QUERY_TOO_BROAD, 0.75))
            else:
                # Semantic search might be missing keyword matches
                causes_scores.append((FailureRootCause.SEMANTIC_MISMATCH, 0.65))
        
        # Check 3: Low term coverage
        elif metrics.get('term_coverage', 0) < 0.4:
            # Results exist but don't contain query terms
            causes_scores.append((FailureRootCause.SEMANTIC_MISMATCH, 0.7))
        
        # Check 4: Temporal mismatch
        if any(re.search(p, query.lower()) for p in self.PATTERNS['temporal']):
            # Query is time-sensitive
            if metrics.get('freshness', 1.0) < 0.5:
                causes_scores.append((FailureRootCause.TEMPORAL_MISMATCH, 0.75))
        
        # Check 5: Entity not found
        if entities and metrics.get('result_count', 0) > 0:
            result_text = str(results).lower()
            entities_found = sum(1 for e in entities if e.lower() in result_text)
            if entities_found < len(entities) / 2:
                causes_scores.append((FailureRootCause.ENTITY_NOT_FOUND, 0.7))
        
        # Return highest confidence root cause
        if causes_scores:
            causes_scores.sort(key=lambda x: x[1], reverse=True)
            return causes_scores[0]
        
        return FailureRootCause.UNKNOWN, 0.3
    
    def _generate_improvement(
        self,
        query: str,
        root_cause: FailureRootCause,
        current_plan: Dict,
        failed_strategies: List[str],
        metrics: Dict[str, float],
        entities: List[str] = None
    ) -> Tuple[ImprovementAction, Optional[str], List[str]]:
        """Generate improvement strategy based on root cause."""
        
        current_sources = [s.get('source') for s in current_plan.get('steps', [])]
        
        # Map root causes to improvement actions
        if root_cause == FailureRootCause.QUERY_TOO_BROAD:
            # Make query more specific
            suggested_query = self._refine_broad_query(query, entities)
            return ImprovementAction.REFINE_QUERY, suggested_query, current_sources
        
        elif root_cause == FailureRootCause.QUERY_TOO_NARROW:
            # Broaden the query
            suggested_query = self._broaden_narrow_query(query)
            return ImprovementAction.BROADEN_QUERY, suggested_query, current_sources
        
        elif root_cause == FailureRootCause.WRONG_SOURCE:
            # Try different sources
            new_sources = self._suggest_alternative_sources(current_sources, query)
            return ImprovementAction.CHANGE_SOURCE, query, new_sources
        
        elif root_cause == FailureRootCause.SEMANTIC_MISMATCH:
            # Try keyword search instead of semantic
            if 'vector' in current_sources:
                suggested_query = self._extract_keywords(query, entities)
                return ImprovementAction.TRY_KEYWORD_SEARCH, suggested_query, current_sources
            else:
                return ImprovementAction.TRY_SEMANTIC_SEARCH, query, current_sources
        
        elif root_cause == FailureRootCause.TEMPORAL_MISMATCH:
            # Add time constraints
            suggested_query = self._add_temporal_context(query)
            return ImprovementAction.NARROW_TIME_RANGE, suggested_query, current_sources
        
        elif root_cause == FailureRootCause.ENTITY_NOT_FOUND:
            # Add entity context
            if entities:
                suggested_query = self._enhance_with_entities(query, entities)
                return ImprovementAction.ADD_CONTEXT, suggested_query, current_sources
        
        elif root_cause == FailureRootCause.DATA_NOT_AVAILABLE:
            # Be honest - data might not exist
            return ImprovementAction.ACKNOWLEDGE_LIMITATION, query, []
        
        # Default: try adding keywords
        suggested_query = self._extract_keywords(query, entities)
        return ImprovementAction.ADD_KEYWORDS, suggested_query, current_sources
    
    def _refine_broad_query(self, query: str, entities: List[str] = None) -> str:
        """Make a broad query more specific."""
        # Add specific focus if entities are available
        if entities and len(entities) > 0:
            return f"{query} specifically for {entities[0]}"
        
        # Add common qualifiers
        if 'horizon' in query.lower() or 'eu' in query.lower():
            return f"{query} requirements and eligibility"
        
        return f"{query} detailed information"
    
    def _broaden_narrow_query(self, query: str) -> str:
        """Make a narrow query broader."""
        # Remove specific call IDs
        broadened = re.sub(r'HORIZON-[A-Z0-9]+-\d{4}-[A-Z0-9]+-\d+-\d+', '', query)
        
        # Remove quoted phrases
        broadened = re.sub(r'"[^"]+"', '', broadened)
        
        # Clean up
        broadened = ' '.join(broadened.split())
        
        # If too short, add context
        if len(broadened.split()) < 3:
            return f"Horizon Europe {broadened} overview"
        
        return broadened
    
    def _suggest_alternative_sources(
        self, 
        current_sources: List[str], 
        query: str
    ) -> List[str]:
        """Suggest alternative data sources to try."""
        all_sources = ['graph', 'vector', 'keyword', 'calls', 'cordis']
        
        # Filter out already tried sources
        alternatives = [s for s in all_sources if s not in current_sources]
        
        # Prioritize based on query type
        query_lower = query.lower()
        
        if 'funding' in query_lower or 'call' in query_lower or 'deadline' in query_lower:
            if 'calls' in alternatives:
                return ['calls'] + [s for s in alternatives if s != 'calls']
        
        if 'project' in query_lower or 'success' in query_lower or 'statistics' in query_lower:
            if 'graph' in alternatives:
                return ['graph'] + [s for s in alternatives if s != 'graph']
            if 'cordis' in alternatives:
                return ['cordis'] + [s for s in alternatives if s != 'cordis']
        
        return alternatives if alternatives else ['vector', 'keyword']
    
    def _extract_keywords(self, query: str, entities: List[str] = None) -> str:
        """Extract important keywords for keyword search."""
        # Get words from query
        words = re.findall(r'\b\w{3,}\b', query.lower())
        
        # Remove stopwords
        stopwords = {
            'the', 'and', 'for', 'are', 'what', 'how', 'can', 'does', 
            'about', 'with', 'this', 'that', 'from', 'have', 'will',
            'tell', 'please', 'want', 'know', 'find', 'show', 'get'
        }
        keywords = [w for w in words if w not in stopwords]
        
        # Add entities
        if entities:
            keywords.extend(entities)
        
        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        return ' '.join(unique_keywords[:8])  # Limit to 8 keywords
    
    def _add_temporal_context(self, query: str) -> str:
        """Add temporal context to query."""
        # Check if year is already specified
        if re.search(r'20\d{2}', query):
            return query
        
        # Add current/upcoming qualifier
        return f"{query} 2025 2026"
    
    def _enhance_with_entities(self, query: str, entities: List[str]) -> str:
        """Enhance query with entity context."""
        entity_str = ' '.join(entities[:3])  # Top 3 entities
        return f"{query} {entity_str}"
    
    def _create_analysis_narrative(
        self,
        root_cause: FailureRootCause,
        metrics: Dict[str, float],
        plan: Dict,
        entities: List[str] = None
    ) -> str:
        """Create a human-readable analysis of what went wrong."""
        
        narratives = {
            FailureRootCause.QUERY_TOO_BROAD: 
                "The query was too broad and returned many loosely related results. "
                "A more specific query would help focus the search.",
            
            FailureRootCause.QUERY_TOO_NARROW:
                "The query was too specific, possibly searching for an exact match "
                "that doesn't exist in the database. Broadening the search may help.",
            
            FailureRootCause.WRONG_SOURCE:
                "The data sources searched may not contain the requested information. "
                "Trying different sources (graph, vector, calls) could find better results.",
            
            FailureRootCause.SEMANTIC_MISMATCH:
                "Semantic search didn't find good matches. The exact terms in the query "
                "may not appear in the documents. Keyword search could work better.",
            
            FailureRootCause.TEMPORAL_MISMATCH:
                "The query appears time-sensitive, but the results don't match the "
                "expected time frame. Adding year or status filters may help.",
            
            FailureRootCause.ENTITY_NOT_FOUND:
                f"The specific entities ({', '.join(entities[:2]) if entities else 'mentioned'}) "
                "were not found in the results. They may not exist in the database.",
            
            FailureRootCause.DATA_NOT_AVAILABLE:
                "The requested information may not be available in the current database. "
                "This could be because it's not yet published or falls outside our data scope.",
            
            FailureRootCause.UNKNOWN:
                "The search returned insufficient results for unclear reasons. "
                "Trying a different approach may help."
        }
        
        base_narrative = narratives.get(root_cause, narratives[FailureRootCause.UNKNOWN])
        
        # Add metrics context
        if metrics.get('result_count', 0) == 0:
            base_narrative += f" No results were returned."
        elif metrics.get('avg_relevance', 0) < 0.5:
            base_narrative += f" Average relevance was low ({metrics.get('avg_relevance', 0):.2f})."
        
        return base_narrative
    
    def _create_reasoning(
        self,
        root_cause: FailureRootCause,
        action: ImprovementAction,
        suggested_query: Optional[str],
        suggested_sources: List[str]
    ) -> str:
        """Create reasoning for the suggested improvement."""
        
        reasoning = f"Root cause identified as {root_cause.value}. "
        reasoning += f"Recommended action: {action.value}. "
        
        if suggested_query:
            reasoning += f"Suggested query: '{suggested_query}'. "
        
        if suggested_sources:
            reasoning += f"Suggested sources: {', '.join(suggested_sources)}."
        
        return reasoning


"""
Replanner

Creates new execution plans based on reflection insights.
Learns from failed attempts to avoid repeating mistakes.
"""

import logging
from typing import Any

from .reflector import ImprovementAction, ReflectionResult

logger = logging.getLogger(__name__)


class Replanner:
    """
    Creates new execution plans based on reflection insights.
    
    Incorporates lessons learned from failed attempts to create
    better strategies on subsequent iterations.
    """
    
    # Source priority for different query types
    SOURCE_PRIORITIES = {
        'funding_query': ['calls', 'vector', 'keyword'],
        'statistics_query': ['graph', 'cordis', 'vector'],
        'eligibility_query': ['vector', 'keyword', 'graph'],
        'project_query': ['cordis', 'graph', 'vector'],
        'general_query': ['vector', 'keyword', 'graph'],
    }
    
    def replan(
        self,
        query: str,
        reflection: ReflectionResult,
        failed_strategies: list[str],
        tried_queries: list[str],
        tried_sources: list[str],
        query_type: str = 'general_query',
        entities: list[str] = None
    ) -> dict[str, Any]:
        """
        Generate a new execution plan incorporating lessons learned.
        
        Args:
            query: Original user query
            reflection: Analysis of why previous attempt failed
            failed_strategies: List of strategies that didn't work
            tried_queries: List of queries already attempted
            tried_sources: List of sources already tried
            query_type: Type of query for source prioritization
            entities: Extracted entities
            
        Returns:
            New execution plan dictionary
        """
        
        # Get the suggested improvements from reflection
        action = reflection.improvement_action
        suggested_query = reflection.suggested_query or query
        suggested_sources = reflection.suggested_sources or []
        
        # Filter out failed/tried approaches
        failed_set = set(failed_strategies)
        tried_queries_set = set(tried_queries)
        tried_sources_set = set(tried_sources)
        
        # Build new plan based on improvement action
        new_plan = self._build_plan_for_action(
            action=action,
            query=query,
            suggested_query=suggested_query,
            suggested_sources=suggested_sources,
            failed_set=failed_set,
            tried_queries_set=tried_queries_set,
            tried_sources_set=tried_sources_set,
            query_type=query_type,
            entities=entities,
            reflection=reflection
        )
        
        logger.info(
            f"Replanned: action={action.value}, "
            f"new_query='{new_plan.get('query', query)[:50]}...', "
            f"sources={[s.get('source') for s in new_plan.get('steps', [])]}"
        )
        
        return new_plan
    
    def _build_plan_for_action(
        self,
        action: ImprovementAction,
        query: str,
        suggested_query: str,
        suggested_sources: list[str],
        failed_set: set[str],
        tried_queries_set: set[str],
        tried_sources_set: set[str],
        query_type: str,
        entities: list[str],
        reflection: ReflectionResult
    ) -> dict[str, Any]:
        """Build a new plan based on the improvement action."""
        
        if action == ImprovementAction.REFINE_QUERY:
            return self._plan_refined_query(
                suggested_query, query_type, tried_sources_set, entities
            )
        
        elif action == ImprovementAction.BROADEN_QUERY:
            return self._plan_broadened_query(
                suggested_query, query_type, tried_sources_set
            )
        
        elif action == ImprovementAction.CHANGE_SOURCE:
            return self._plan_new_sources(
                query, suggested_sources, tried_sources_set, query_type
            )
        
        elif action == ImprovementAction.TRY_KEYWORD_SEARCH:
            return self._plan_keyword_search(
                suggested_query, tried_sources_set
            )
        
        elif action == ImprovementAction.TRY_SEMANTIC_SEARCH:
            return self._plan_semantic_search(query, entities)
        
        elif action == ImprovementAction.ADD_KEYWORDS:
            return self._plan_with_keywords(
                query, suggested_query, tried_sources_set
            )
        
        elif action == ImprovementAction.ADD_CONTEXT:
            return self._plan_with_context(
                suggested_query, entities, tried_sources_set
            )
        
        elif action == ImprovementAction.NARROW_TIME_RANGE:
            return self._plan_temporal_search(
                suggested_query, tried_sources_set
            )
        
        elif action == ImprovementAction.ACKNOWLEDGE_LIMITATION:
            return self._plan_final_attempt(
                query, query_type, entities
            )
        
        # Default: try a hybrid approach
        return self._plan_hybrid_approach(query, query_type, entities)
    
    def _plan_refined_query(
        self,
        refined_query: str,
        query_type: str,
        tried_sources: set[str],
        entities: list[str] = None
    ) -> dict[str, Any]:
        """Plan with a more refined/specific query."""
        
        sources = self.SOURCE_PRIORITIES.get(query_type, ['vector', 'keyword'])
        
        steps = []
        for source in sources[:2]:  # Use top 2 sources
            step = {
                'source': source,
                'query': refined_query,
                'operation': 'semantic_search' if source == 'vector' else 'search',
                'limit': 10
            }
            
            # Add entity filtering for graph queries
            if source == 'graph' and entities:
                step['entities'] = entities[:3]
            
            steps.append(step)
        
        return {
            'query': refined_query,
            'strategy': 'refined_query',
            'steps': steps,
            'reasoning': 'Refined query to be more specific'
        }
    
    def _plan_broadened_query(
        self,
        broadened_query: str,
        query_type: str,
        tried_sources: set[str]
    ) -> dict[str, Any]:
        """Plan with a broader query."""
        
        # Use vector search for broader queries (better semantic matching)
        steps = [
            {
                'source': 'vector',
                'query': broadened_query,
                'operation': 'semantic_search',
                'limit': 15  # More results for broader query
            }
        ]
        
        # Add keyword as backup
        if 'keyword' not in tried_sources:
            steps.append({
                'source': 'keyword',
                'query': broadened_query,
                'operation': 'keyword_search',
                'limit': 10
            })
        
        return {
            'query': broadened_query,
            'strategy': 'broadened_query',
            'steps': steps,
            'reasoning': 'Broadened query to find more general results'
        }
    
    def _plan_new_sources(
        self,
        query: str,
        suggested_sources: list[str],
        tried_sources: set[str],
        query_type: str
    ) -> dict[str, Any]:
        """Plan using different data sources."""
        
        # Filter out already tried sources
        new_sources = [s for s in suggested_sources if s not in tried_sources]
        
        if not new_sources:
            # Fall back to priority list
            priorities = self.SOURCE_PRIORITIES.get(query_type, ['vector', 'graph', 'calls'])
            new_sources = [s for s in priorities if s not in tried_sources]
        
        steps = []
        for source in new_sources[:2]:
            operation = self._get_operation_for_source(source)
            steps.append({
                'source': source,
                'query': query,
                'operation': operation,
                'limit': 10
            })
        
        return {
            'query': query,
            'strategy': 'different_sources',
            'steps': steps,
            'reasoning': f'Trying different sources: {new_sources[:2]}'
        }
    
    def _plan_keyword_search(
        self,
        keyword_query: str,
        tried_sources: set[str]
    ) -> dict[str, Any]:
        """Plan with keyword-based search."""
        
        steps = [
            {
                'source': 'keyword',
                'query': keyword_query,
                'operation': 'keyword_search',
                'limit': 15
            }
        ]
        
        # Also try hybrid search
        steps.append({
            'source': 'vector',
            'query': keyword_query,
            'operation': 'hybrid_search',  # Combines semantic + keyword
            'limit': 10
        })
        
        return {
            'query': keyword_query,
            'strategy': 'keyword_search',
            'steps': steps,
            'reasoning': 'Switched to keyword search for exact term matching'
        }
    
    def _plan_semantic_search(
        self,
        query: str,
        entities: list[str] = None
    ) -> dict[str, Any]:
        """Plan with semantic search."""
        
        steps = [
            {
                'source': 'vector',
                'query': query,
                'operation': 'semantic_search',
                'limit': 15
            }
        ]
        
        return {
            'query': query,
            'strategy': 'semantic_search',
            'steps': steps,
            'reasoning': 'Trying pure semantic search for meaning-based matching'
        }
    
    def _plan_with_keywords(
        self,
        original_query: str,
        keyword_enhanced_query: str,
        tried_sources: set[str]
    ) -> dict[str, Any]:
        """Plan with added keywords."""
        
        steps = [
            {
                'source': 'vector',
                'query': keyword_enhanced_query,
                'operation': 'hybrid_search',
                'limit': 12
            }
        ]
        
        if 'keyword' not in tried_sources:
            steps.append({
                'source': 'keyword',
                'query': keyword_enhanced_query,
                'operation': 'keyword_search',
                'limit': 10
            })
        
        return {
            'query': keyword_enhanced_query,
            'strategy': 'enhanced_keywords',
            'steps': steps,
            'reasoning': 'Added domain-specific keywords to improve matching'
        }
    
    def _plan_with_context(
        self,
        context_enhanced_query: str,
        entities: list[str],
        tried_sources: set[str]
    ) -> dict[str, Any]:
        """Plan with added context from entities."""
        
        steps = [
            {
                'source': 'vector',
                'query': context_enhanced_query,
                'operation': 'semantic_search',
                'limit': 12,
                'entities': entities[:3] if entities else []
            }
        ]
        
        # Add graph search for entity relationships
        if 'graph' not in tried_sources and entities:
            steps.append({
                'source': 'graph',
                'query': context_enhanced_query,
                'operation': 'entity_search',
                'entities': entities[:3],
                'limit': 10
            })
        
        return {
            'query': context_enhanced_query,
            'strategy': 'context_enhanced',
            'steps': steps,
            'reasoning': f'Added context from entities: {entities[:2] if entities else []}'
        }
    
    def _plan_temporal_search(
        self,
        temporal_query: str,
        tried_sources: set[str]
    ) -> dict[str, Any]:
        """Plan with temporal constraints."""
        
        steps = [
            {
                'source': 'calls',  # Calls have the best temporal data
                'query': temporal_query,
                'operation': 'search',
                'limit': 15,
                'filters': {
                    'year': [2025, 2026],
                    'status': ['open', 'upcoming']
                }
            }
        ]
        
        # Backup with vector search
        steps.append({
            'source': 'vector',
            'query': temporal_query,
            'operation': 'semantic_search',
            'limit': 10,
            'filters': {
                'year': '2025'
            }
        })
        
        return {
            'query': temporal_query,
            'strategy': 'temporal_search',
            'steps': steps,
            'reasoning': 'Added time constraints (2025-2026)'
        }
    
    def _plan_final_attempt(
        self,
        query: str,
        query_type: str,
        entities: list[str] = None
    ) -> dict[str, Any]:
        """Final attempt before acknowledging limitation."""
        
        # Try all sources with lower thresholds
        steps = [
            {
                'source': 'vector',
                'query': query,
                'operation': 'semantic_search',
                'limit': 20,
                'similarity_threshold': 0.3  # Lower threshold
            },
            {
                'source': 'keyword',
                'query': query,
                'operation': 'keyword_search',
                'limit': 15
            }
        ]
        
        if entities:
            steps.append({
                'source': 'graph',
                'query': query,
                'operation': 'entity_search',
                'entities': entities,
                'limit': 10
            })
        
        return {
            'query': query,
            'strategy': 'final_attempt',
            'steps': steps,
            'reasoning': 'Final attempt with relaxed constraints',
            'is_final_attempt': True
        }
    
    def _plan_hybrid_approach(
        self,
        query: str,
        query_type: str,
        entities: list[str] = None
    ) -> dict[str, Any]:
        """Default hybrid approach combining multiple strategies."""
        
        steps = [
            {
                'source': 'vector',
                'query': query,
                'operation': 'hybrid_search',
                'limit': 10
            },
            {
                'source': 'keyword',
                'query': query,
                'operation': 'keyword_search',
                'limit': 8
            }
        ]
        
        return {
            'query': query,
            'strategy': 'hybrid',
            'steps': steps,
            'reasoning': 'Using hybrid approach (semantic + keyword)'
        }
    
    def _get_operation_for_source(self, source: str) -> str:
        """Get the appropriate operation for a data source."""
        operations = {
            'vector': 'semantic_search',
            'keyword': 'keyword_search',
            'graph': 'entity_search',
            'calls': 'search',
            'cordis': 'search'
        }
        return operations.get(source, 'search')


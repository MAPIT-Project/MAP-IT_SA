# TASK_07: Data Intelligence Service (Facade)

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_07 |
| **Day** | 5 |
| **Estimated Time** | 2 hours |
| **Dependencies** | TASK_04 (Graph Service), TASK_06 (Query Planner) |
| **Blocks** | TASK_08, TASK_09 |
| **Priority** | Critical |

## Objective

Create the `DataIntelligenceService` class that serves as the main facade for intelligent data retrieval. It orchestrates:
1. Query planning (via QueryPlanner)
2. Graph queries (via GraphSearchService)
3. Vector search (via existing VectorSearchService)
4. Result combination and formatting

## Context

This service is the main entry point for the new intelligent retrieval system. It:
- Receives a user query
- Generates an execution plan
- Executes plan steps in order
- Combines results from multiple sources
- Returns a unified result for answer generation

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│   DataIntelligenceService       │
│                                 │
│  ┌─────────────────────────┐    │
│  │    QueryPlanner         │    │
│  │    (Generate Plan)      │    │
│  └───────────┬─────────────┘    │
│              │                   │
│  ┌───────────▼─────────────┐    │
│  │    Execute Plan Steps   │    │
│  │                         │    │
│  │  ┌─────┐ ┌─────┐ ┌────┐ │    │
│  │  │Graph│ │Vector│ │KW  │ │    │
│  │  └──┬──┘ └──┬──┘ └─┬──┘ │    │
│  │     └───────┼──────┘     │    │
│  │             ▼            │    │
│  │      Combine Results     │    │
│  └───────────┬─────────────┘    │
│              │                   │
└──────────────┼──────────────────┘
               ▼
        IntelligentSearchResult
```

## Files to Create

| Action | File Path |
|--------|-----------|
| CREATE | `app/services/data_intelligence_service.py` |
| MODIFY | `app/services/data_intelligence/__init__.py` |

## Implementation

### File: `app/services/data_intelligence_service.py`

```python
"""
Data Intelligence Service - Main facade for intelligent data retrieval.

Orchestrates query planning, multi-source execution, and result fusion
for sophisticated Horizon Europe queries.

Usage:
    from app.services.data_intelligence_service import DataIntelligenceService

    service = DataIntelligenceService()
    result = await service.search("Can Switzerland participate in Cluster 4?")
    print(result.answer_context)
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

from .data_intelligence.graph_service import GraphSearchService
from .data_intelligence.query_planner import QueryPlanner, QueryPlan, ExecutionStep

logger = logging.getLogger(__name__)


@dataclass
class SourceResult:
    """Result from a single data source."""
    source: str  # "graph", "vector", "keyword"
    operation: str
    data: Any
    success: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class IntelligentSearchResult:
    """Combined result from intelligent multi-source search."""
    query: str
    intent_type: str
    confidence: float
    answer_context: str
    graph_results: List[Dict[str, Any]] = field(default_factory=list)
    vector_results: List[Dict[str, Any]] = field(default_factory=list)
    keyword_results: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    plan: Optional[QueryPlan] = None
    execution_details: List[SourceResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "answer_context": self.answer_context,
            "graph_results": self.graph_results,
            "vector_results": self.vector_results,
            "sources": self.sources,
            "total_time_ms": self.total_time_ms,
            "success": self.success,
            "error": self.error
        }


class DataIntelligenceService:
    """
    Unified intelligent search across graph and vector databases.

    This service:
    1. Uses QueryPlanner to generate execution plans
    2. Executes plans across multiple data sources
    3. Combines and formats results for answer generation
    """

    def __init__(self):
        """Initialize the Data Intelligence Service."""

        # Initialize graph service
        try:
            self.graph_service = GraphSearchService()
            self._graph_available = True
        except Exception as e:
            logger.warning(f"Graph service unavailable: {e}")
            self.graph_service = None
            self._graph_available = False

        # Initialize query planner
        try:
            self.planner = QueryPlanner()
            self._planner_available = True
        except Exception as e:
            logger.warning(f"Query planner unavailable: {e}")
            self.planner = None
            self._planner_available = False

        # Initialize vector search (existing service)
        try:
            from .supabase_client import SupabaseVectorStore
            from .embedding_service import EmbeddingService
            from .vector_search_service import VectorSearchService

            supabase = SupabaseVectorStore()
            embedder = EmbeddingService(cache_client=supabase)
            self.vector_service = VectorSearchService(supabase, embedder)
            self._vector_available = True
        except Exception as e:
            logger.warning(f"Vector service unavailable: {e}")
            self.vector_service = None
            self._vector_available = False

        logger.info(f"✅ Data Intelligence Service initialized")
        logger.info(f"   Graph: {'✓' if self._graph_available else '✗'}")
        logger.info(f"   Vector: {'✓' if self._vector_available else '✗'}")
        logger.info(f"   Planner: {'✓' if self._planner_available else '✗'}")

    async def search(
        self,
        query: str,
        context: str = "",
        max_results: int = 10
    ) -> IntelligentSearchResult:
        """
        Execute intelligent search across all available data sources.

        Args:
            query: User's question
            context: Optional conversation context
            max_results: Maximum results per source

        Returns:
            IntelligentSearchResult with combined data from all sources
        """
        start_time = datetime.now()

        try:
            # Step 1: Generate execution plan
            if self._planner_available:
                plan = await self.planner.generate_plan(query, context)
            else:
                plan = self._create_default_plan(query)

            logger.info(f"📋 Plan generated: {plan.intent_type} ({len(plan.steps)} steps)")

            # Step 2: Execute plan steps
            execution_results = []
            graph_results = []
            vector_results = []
            keyword_results = []
            sources = []

            for step in plan.steps:
                step_start = datetime.now()

                try:
                    if step.source == "graph":
                        result = await self._execute_graph_step(step)
                        if result:
                            graph_results.extend(result if isinstance(result, list) else [result])
                            sources.append({"type": "graph", "operation": step.operation})

                    elif step.source == "vector":
                        result = await self._execute_vector_step(step, plan.cleaned_query)
                        if result:
                            vector_results.extend(result)
                            sources.append({"type": "vector", "operation": step.operation})

                    elif step.source == "keyword":
                        result = await self._execute_keyword_step(step, plan.cleaned_query)
                        if result:
                            keyword_results.extend(result)
                            sources.append({"type": "keyword", "operation": step.operation})

                    step_time = (datetime.now() - step_start).total_seconds() * 1000
                    execution_results.append(SourceResult(
                        source=step.source,
                        operation=step.operation,
                        data=result,
                        success=True,
                        execution_time_ms=step_time
                    ))

                except Exception as e:
                    logger.error(f"Step {step.step_number} failed: {e}")
                    step_time = (datetime.now() - step_start).total_seconds() * 1000
                    execution_results.append(SourceResult(
                        source=step.source,
                        operation=step.operation,
                        data=None,
                        success=False,
                        error=str(e),
                        execution_time_ms=step_time
                    ))

            # Step 3: Build answer context
            answer_context = self._build_answer_context(
                query=query,
                plan=plan,
                graph_results=graph_results,
                vector_results=vector_results,
                keyword_results=keyword_results
            )

            # Calculate total time
            total_time = (datetime.now() - start_time).total_seconds() * 1000

            return IntelligentSearchResult(
                query=query,
                intent_type=plan.intent_type,
                confidence=plan.confidence,
                answer_context=answer_context,
                graph_results=graph_results,
                vector_results=vector_results,
                keyword_results=keyword_results,
                sources=sources,
                plan=plan,
                execution_details=execution_results,
                total_time_ms=total_time,
                success=True
            )

        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            total_time = (datetime.now() - start_time).total_seconds() * 1000

            return IntelligentSearchResult(
                query=query,
                intent_type="error",
                confidence=0.0,
                answer_context="",
                total_time_ms=total_time,
                success=False,
                error=str(e)
            )

    async def _execute_graph_step(self, step: ExecutionStep) -> Optional[Union[Dict, List]]:
        """Execute a graph database operation."""

        if not self._graph_available:
            logger.warning("Graph service not available, skipping graph step")
            return None

        operation = step.operation
        params = step.parameters

        logger.debug(f"Executing graph step: {operation} with {params}")

        # Map operations to GraphSearchService methods
        if operation == "get_call_details":
            return self.graph_service.get_call_details(
                params.get("identifier", "")
            )

        elif operation == "check_country_eligibility":
            return self.graph_service.check_country_eligibility(
                params.get("country_code", ""),
                params.get("cluster_code")
            )

        elif operation == "check_entity_eligibility":
            return self.graph_service.check_entity_type_eligibility(
                params.get("entity_type", ""),
                params.get("action_type")
            )

        elif operation == "get_budget_statistics":
            return self.graph_service.get_budget_statistics(
                params.get("cluster_code"),
                params.get("action_type")
            )

        elif operation == "get_consortium_patterns":
            return self.graph_service.get_consortium_patterns(
                params.get("cluster_code"),
                params.get("min_partners", 3)
            )

        elif operation == "find_similar_topics":
            return self.graph_service.find_similar_topics(
                params.get("topic_code", ""),
                params.get("limit", 10)
            )

        elif operation == "find_organization_partners":
            return self.graph_service.find_organization_partners(
                params.get("org_name", ""),
                params.get("limit", 20)
            )

        elif operation == "get_cluster_overview":
            return self.graph_service.get_cluster_overview()

        elif operation == "search_topics":
            return self.graph_service.search_topics(
                params.get("search_term", ""),
                params.get("limit", 20)
            )

        else:
            logger.warning(f"Unknown graph operation: {operation}")
            return None

    async def _execute_vector_step(
        self,
        step: ExecutionStep,
        cleaned_query: str
    ) -> List[Dict[str, Any]]:
        """Execute a vector search operation."""

        if not self._vector_available:
            logger.warning("Vector service not available, skipping vector step")
            return []

        operation = step.operation
        params = step.parameters

        # Get the search query
        search_query = params.get("query", cleaned_query)
        num_results = params.get("num_results", params.get("limit", 5))

        logger.debug(f"Executing vector step: {operation} - '{search_query}'")

        try:
            if operation in ["semantic_search", "hybrid_search"]:
                search_type = "hybrid" if operation == "hybrid_search" else "semantic"

                results = self.vector_service.search(
                    query=search_query,
                    search_type=search_type,
                    num_results=num_results,
                    similarity_threshold=params.get("similarity_threshold", 0.5)
                )

                # Convert SearchResult objects to dicts
                return [
                    {
                        "content": r.content,
                        "title": r.document_title,
                        "type": r.document_type,
                        "section": r.section_title,
                        "page": r.page_number,
                        "score": r.score,
                        "source": "vector"
                    }
                    for r in results
                ]

            else:
                logger.warning(f"Unknown vector operation: {operation}")
                return []

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _execute_keyword_step(
        self,
        step: ExecutionStep,
        cleaned_query: str
    ) -> List[Dict[str, Any]]:
        """Execute a keyword search operation."""

        if not self._vector_available:
            logger.warning("Vector service not available, skipping keyword step")
            return []

        params = step.parameters
        search_query = params.get("query", cleaned_query)

        logger.debug(f"Executing keyword step: {search_query}")

        try:
            results = self.vector_service.search(
                query=search_query,
                search_type="keyword",
                num_results=params.get("limit", 5)
            )

            return [
                {
                    "content": r.content,
                    "title": r.document_title,
                    "type": r.document_type,
                    "score": r.score,
                    "source": "keyword"
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    def _build_answer_context(
        self,
        query: str,
        plan: QueryPlan,
        graph_results: List[Dict],
        vector_results: List[Dict],
        keyword_results: List[Dict]
    ) -> str:
        """Build context string for LLM answer generation."""

        context_parts = []

        # Add intent and query info
        context_parts.append(f"USER QUERY: {query}")
        context_parts.append(f"DETECTED INTENT: {plan.intent_type} (confidence: {plan.confidence:.2f})")
        context_parts.append("")

        # Add graph results
        if graph_results:
            context_parts.append("=" * 60)
            context_parts.append("STRUCTURED DATA (from Graph Database)")
            context_parts.append("=" * 60)

            for i, result in enumerate(graph_results[:5], 1):
                context_parts.append(f"\n[Graph Result {i}]")

                # Format based on result type
                if isinstance(result, dict):
                    for key, value in result.items():
                        if value is not None and value != "" and key != "source":
                            # Format large numbers
                            if isinstance(value, (int, float)) and value > 1000:
                                context_parts.append(f"  {key}: €{value:,.0f}" if "budget" in key.lower() or "funding" in key.lower() else f"  {key}: {value:,.0f}")
                            elif isinstance(value, list):
                                context_parts.append(f"  {key}: {', '.join(str(v) for v in value[:5])}")
                            else:
                                context_parts.append(f"  {key}: {value}")
                else:
                    context_parts.append(f"  {result}")

            context_parts.append("")

        # Add vector results
        if vector_results:
            context_parts.append("=" * 60)
            context_parts.append("DOCUMENT CONTEXT (from Vector Search)")
            context_parts.append("=" * 60)

            for i, result in enumerate(vector_results[:5], 1):
                title = result.get("title", "Unknown Document")
                doc_type = result.get("type", "")
                section = result.get("section", "")
                content = result.get("content", "")[:600]

                context_parts.append(f"\n[Document {i}: {title}]")
                if doc_type:
                    context_parts.append(f"Type: {doc_type}")
                if section:
                    context_parts.append(f"Section: {section}")
                context_parts.append(f"Content: {content}...")

            context_parts.append("")

        # Add keyword results (if different from vector)
        if keyword_results and not vector_results:
            context_parts.append("=" * 60)
            context_parts.append("KEYWORD SEARCH RESULTS")
            context_parts.append("=" * 60)

            for i, result in enumerate(keyword_results[:3], 1):
                context_parts.append(f"\n[Result {i}: {result.get('title', 'Unknown')}]")
                context_parts.append(result.get("content", "")[:400])

        # Add extracted entities for reference
        if plan.extracted_entities:
            entities = plan.extracted_entities
            entity_info = []
            if entities.topic_codes:
                entity_info.append(f"Topics: {', '.join(entities.topic_codes)}")
            if entities.cluster_codes:
                entity_info.append(f"Clusters: {', '.join(entities.cluster_codes)}")
            if entities.country_codes:
                entity_info.append(f"Countries: {', '.join(entities.country_codes)}")

            if entity_info:
                context_parts.append("")
                context_parts.append("EXTRACTED ENTITIES: " + " | ".join(entity_info))

        return "\n".join(context_parts)

    def _create_default_plan(self, query: str) -> QueryPlan:
        """Create a default plan when planner is unavailable."""
        from .data_intelligence.query_planner import ExtractedEntities

        return QueryPlan(
            intent_type="general",
            confidence=0.5,
            steps=[
                ExecutionStep(
                    step_number=1,
                    source="vector",
                    operation="hybrid_search",
                    parameters={"query": query, "num_results": 5},
                    reason="Default hybrid search"
                )
            ],
            need_graph="never",
            need_vector="required",
            need_keyword="never",
            cleaned_query=query,
            extracted_entities=ExtractedEntities(),
            fallback_strategy="Use vector search only"
        )

    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        return {
            "graph_available": self._graph_available,
            "vector_available": self._vector_available,
            "planner_available": self._planner_available,
            "fully_operational": all([
                self._graph_available,
                self._vector_available,
                self._planner_available
            ])
        }


# Convenience function for quick testing
async def intelligent_search(query: str, context: str = "") -> IntelligentSearchResult:
    """
    Convenience function for intelligent search.

    Usage:
        result = await intelligent_search("Can Switzerland participate?")
        print(result.answer_context)
    """
    service = DataIntelligenceService()
    return await service.search(query, context)


if __name__ == "__main__":
    import asyncio

    async def test_service():
        print("\n=== Testing Data Intelligence Service ===\n")

        service = DataIntelligenceService()

        # Check status
        status = service.get_service_status()
        print(f"Service Status: {status}")
        print()

        # Test queries
        test_queries = [
            "What is the deadline for HORIZON-CL4-2025-DATA-01?",
            "Can an SME from Switzerland participate?",
            "What is the maximum budget for RIA in Cluster 5?",
        ]

        for query in test_queries:
            print(f"Query: {query}")
            result = await service.search(query)
            print(f"  Intent: {result.intent_type}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  Graph results: {len(result.graph_results)}")
            print(f"  Vector results: {len(result.vector_results)}")
            print(f"  Time: {result.total_time_ms:.0f}ms")
            print(f"  Context preview: {result.answer_context[:200]}...")
            print()

    asyncio.run(test_service())
```

### Update: `app/services/data_intelligence/__init__.py`

Add the DataIntelligenceService to exports:

```python
"""
Data Intelligence package for graph-based and hybrid search capabilities.
"""

from .graph_service import GraphSearchService
from .query_planner import QueryPlanner, QueryPlan, ExecutionStep

__all__ = [
    "GraphSearchService",
    "QueryPlanner",
    "QueryPlan",
    "ExecutionStep",
]
```

## Acceptance Criteria

- [ ] DataIntelligenceService class created
- [ ] Successfully initializes all sub-services (graph, vector, planner)
- [ ] `search()` method executes plans and returns results
- [ ] Graph, vector, and keyword steps execute correctly
- [ ] Answer context is properly formatted
- [ ] Error handling prevents crashes
- [ ] Service status reporting works

## Verification Commands

```bash
# 1. Test import
python -c "from app.services.data_intelligence_service import DataIntelligenceService; print('✅ Import OK')"

# 2. Check service status
python -c "
from app.services.data_intelligence_service import DataIntelligenceService
service = DataIntelligenceService()
print(service.get_service_status())
"

# 3. Run built-in test
python app/services/data_intelligence_service.py

# 4. Test a specific query
python -c "
import asyncio
from app.services.data_intelligence_service import DataIntelligenceService

async def test():
    service = DataIntelligenceService()
    result = await service.search('Can Switzerland participate in Cluster 4?')
    print(f'Success: {result.success}')
    print(f'Intent: {result.intent_type}')
    print(f'Graph results: {len(result.graph_results)}')
    print(f'Vector results: {len(result.vector_results)}')

asyncio.run(test())
"
```

## Notes for Agent

1. This is the main integration point - all components come together here
2. Graceful degradation is critical - service should work even if some components fail
3. The answer context format is designed for LLM consumption
4. Execution details help with debugging and observability
5. The service is async to prevent blocking the event loop
6. Graph results are formatted differently based on the operation type

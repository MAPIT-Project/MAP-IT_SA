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
from dataclasses import dataclass, field
from datetime import datetime

try:
    from .data_intelligence.graph_service import GraphSearchService
    from .data_intelligence.query_planner import QueryPlanner, QueryPlan, ExecutionStep, ExtractedEntities
    from .data_intelligence.cross_encoder_reranker import CrossEncoderReranker, RankedDocument
except ImportError:
    from app.services.data_intelligence.graph_service import GraphSearchService
    from app.services.data_intelligence.query_planner import QueryPlanner, QueryPlan, ExecutionStep, ExtractedEntities
    from app.services.data_intelligence.cross_encoder_reranker import CrossEncoderReranker, RankedDocument

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
            logger.info("✅ Graph service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Graph service unavailable: {e}")
            self.graph_service = None
            self._graph_available = False
        
        # Initialize query planner
        try:
            self.planner = QueryPlanner()
            self._planner_available = True
            logger.info("✅ Query planner initialized")
        except Exception as e:
            logger.warning(f"⚠️ Query planner unavailable: {e}")
            self.planner = None
            self._planner_available = False
        
        # Initialize vector search (existing service) - optional
        try:
            try:
                from .vector_search_service import VectorSearchService
            except ImportError:
                from app.services.vector_search_service import VectorSearchService
            self.vector_service = VectorSearchService()
            self._vector_available = True
            logger.info("✅ Vector service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Vector service unavailable: {e}")
            self.vector_service = None
            self._vector_available = False
        
        # Initialize cross-encoder reranker
        try:
            self.reranker = CrossEncoderReranker(model_type="fast")
            self._reranker_available = True
            logger.info("✅ Reranker initialized (lazy loading)")
        except Exception as e:
            logger.warning(f"⚠️ Reranker unavailable: {e}")
            self.reranker = None
            self._reranker_available = False
        
        logger.info(f"🧠 Data Intelligence Service ready")
        logger.info(f"   Graph: {'✓' if self._graph_available else '✗'}")
        logger.info(f"   Vector: {'✓' if self._vector_available else '✗'}")
        logger.info(f"   Planner: {'✓' if self._planner_available else '✗'}")
        logger.info(f"   Reranker: {'✓' if self._reranker_available else '✗'}")
    
    async def search(
        self,
        query: str,
        context: str = "",
        max_results: int = 10,
        rerank: bool = True,
        rerank_threshold: float = -5.0
    ) -> IntelligentSearchResult:
        """
        Execute intelligent search across all available data sources.
        
        Args:
            query: User's question
            context: Optional conversation context
            max_results: Maximum results per source
            rerank: Whether to apply neural reranking (default: True)
            rerank_threshold: Minimum rerank score to include (default: -5.0)
            
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
            
            logger.info(f"📋 Plan: {plan.intent_type} ({len(plan.steps)} steps, confidence: {plan.confidence:.2f})")
            
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
                            if isinstance(result, list):
                                graph_results.extend(result)
                            else:
                                graph_results.append(result)
                            sources.append({"type": "graph", "operation": step.operation})
                        
                    elif step.source == "vector":
                        result = await self._execute_vector_step(step, plan.cleaned_query)
                        if result:
                            # Deduplicate: only add results not already in vector_results
                            existing_contents = {r.get("content", "")[:100] for r in vector_results}
                            for r in result:
                                content_key = r.get("content", "")[:100]
                                if content_key not in existing_contents:
                                    vector_results.append(r)
                                    existing_contents.add(content_key)
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
            
            # Step 3: Rerank and fuse results (if enabled)
            reranked_results = []
            if rerank and self._reranker_available and (graph_results or vector_results or keyword_results):
                reranked_results = self._fuse_and_rerank(
                    query=query,
                    graph_results=graph_results,
                    vector_results=vector_results,
                    keyword_results=keyword_results,
                    top_k=max_results,
                    threshold=rerank_threshold
                )
                
                if reranked_results:
                    # Convert reranked results back to dict format
                    vector_results = [r.to_dict() for r in reranked_results]
                    sources.append({"type": "reranked", "operation": "cross_encoder"})
                    logger.info(f"🔄 Reranked {len(reranked_results)} results")
            
            # Step 4: Build answer context
            answer_context = self._build_answer_context(
                query=query,
                plan=plan,
                graph_results=graph_results if not reranked_results else [],  # Don't duplicate
                vector_results=vector_results,
                keyword_results=keyword_results if not reranked_results else []  # Don't duplicate
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
        
        elif operation in ["check_entity_eligibility", "check_entity_type_eligibility"]:
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
        
        elif operation == "get_organization_profile":
            return self.graph_service.get_organization_profile(
                params.get("org_name", "")
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
        
        logger.debug(f"Executing vector step: {operation} - '{search_query[:50]}...'")
        
        try:
            if operation in ["semantic_search", "hybrid_search"]:
                search_type = "hybrid" if operation == "hybrid_search" else "semantic"
                
                # Lower threshold for better recall on requirements queries
                default_threshold = 0.4  # Lower threshold to find more potential matches
                
                # Use keyword-heavy weight (0.3) for better keyword matching
                # This helps find exact regulatory text that semantic search misses
                vector_weight = params.get("vector_weight", 0.3)
                
                # For hybrid search, truncate query to ~10 words for better keyword matching
                # Long queries dilute the keyword matching effectiveness
                if search_type == "hybrid":
                    query_words = search_query.split()
                    if len(query_words) > 10:
                        search_query = ' '.join(query_words[:10])
                        logger.debug(f"Truncated hybrid query to: {search_query}")
                
                results = self.vector_service.hybrid_search(
                    query=search_query,
                    num_results=num_results * 2,  # Get more results for better chance of finding relevant content
                    similarity_threshold=params.get("similarity_threshold", default_threshold),
                    vector_weight=vector_weight  # Lower = more keyword weight
                ) if search_type == "hybrid" else self.vector_service.semantic_search(
                    query=search_query,
                    num_results=num_results * 2,
                    similarity_threshold=params.get("similarity_threshold", default_threshold)
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
        
        # For requirements queries, prioritize vector results and add guidance
        is_requirements_query = plan.intent_type in ['consortium_requirements', 'eligibility'] or \
                               any(word in query.lower() for word in ['requirement', 'required', 'must', 'rules', 'eligibility'])
        
        if is_requirements_query:
            context_parts.append("=" * 60)
            context_parts.append("⚠️ ANSWER GUIDANCE: This query asks about REQUIREMENTS/RULES.")
            context_parts.append("Prioritize information from DOCUMENT CONTEXT (official rules).")
            context_parts.append("Graph data shows HISTORICAL STATISTICS, not official rules.")
            context_parts.append("If documents don't contain the specific rules, state that clearly.")
            context_parts.append("=" * 60)
            context_parts.append("")
        
        # Add vector results FIRST for requirements queries
        if vector_results and is_requirements_query:
            context_parts.append("=" * 60)
            context_parts.append("📄 OFFICIAL DOCUMENTS (search for requirements/rules here)")
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
        
        # Add graph results (with appropriate label)
        if graph_results:
            context_parts.append("=" * 60)
            if is_requirements_query:
                context_parts.append("📊 HISTORICAL STATISTICS (for context only, NOT official rules)")
            else:
                context_parts.append("STRUCTURED DATA (from Graph Database)")
            context_parts.append("=" * 60)
            
            for i, result in enumerate(graph_results[:5], 1):
                context_parts.append(f"\n[Graph Result {i}]")
                
                # Format based on result type
                if isinstance(result, dict):
                    for key, value in result.items():
                        if value is not None and value != "" and key != "source":
                            # Format large numbers
                            if isinstance(value, (int, float)) and abs(value) > 1000:
                                if "budget" in key.lower() or "funding" in key.lower() or "contribution" in key.lower() or "cost" in key.lower():
                                    context_parts.append(f"  {key}: €{value:,.0f}")
                                else:
                                    context_parts.append(f"  {key}: {value:,.0f}")
                            elif isinstance(value, list):
                                if value:
                                    context_parts.append(f"  {key}: {', '.join(str(v) for v in value[:5])}")
                            else:
                                context_parts.append(f"  {key}: {value}")
                else:
                    context_parts.append(f"  {result}")
            
            context_parts.append("")
        
        # Add vector results (if not already added for requirements query)
        if vector_results and not is_requirements_query:
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
            if entities.action_types:
                entity_info.append(f"Action Types: {', '.join(entities.action_types)}")
            
            if entity_info:
                context_parts.append("")
                context_parts.append("EXTRACTED ENTITIES: " + " | ".join(entity_info))
        
        return "\n".join(context_parts)
    
    def _create_default_plan(self, query: str) -> QueryPlan:
        """Create a default plan when planner is unavailable."""
        
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
    
    def _fuse_and_rerank(
        self,
        query: str,
        graph_results: List[Dict],
        vector_results: List[Dict],
        keyword_results: List[Dict],
        top_k: int = 10,
        threshold: float = -5.0
    ) -> List[RankedDocument]:
        """
        Fuse results from multiple sources and rerank using cross-encoder.
        
        Args:
            query: The search query
            graph_results: Results from graph database
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            top_k: Maximum results to return
            threshold: Minimum rerank score to include
            
        Returns:
            List of reranked documents
        """
        if not self.reranker:
            return []
        
        # Tag results with their source
        all_results = []
        
        for r in graph_results:
            r_copy = r.copy() if isinstance(r, dict) else {"data": r}
            r_copy["_source"] = "graph"
            all_results.append(r_copy)
        
        for r in vector_results:
            r_copy = r.copy() if isinstance(r, dict) else {"data": r}
            r_copy["_source"] = "vector"
            all_results.append(r_copy)
        
        for r in keyword_results:
            r_copy = r.copy() if isinstance(r, dict) else {"data": r}
            r_copy["_source"] = "keyword"
            all_results.append(r_copy)
        
        if not all_results:
            return []
        
        logger.info(f"🔄 Fusing and reranking {len(all_results)} results from multiple sources")
        
        # Rerank all results together
        try:
            reranked = self.reranker.rerank(
                query=query,
                documents=all_results,
                content_key="content",
                top_k=top_k,
                score_threshold=threshold
            )
            return reranked
        except Exception as e:
            logger.error(f"❌ Reranking failed: {e}")
            return []
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        return {
            "graph_available": self._graph_available,
            "vector_available": self._vector_available,
            "planner_available": self._planner_available,
            "reranker_available": self._reranker_available,
            "fully_operational": all([
                self._graph_available,
                self._planner_available
                # Note: vector and reranker are optional enhancements
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
        print("\n" + "=" * 60)
        print("DATA INTELLIGENCE SERVICE TEST")
        print("=" * 60)
        
        service = DataIntelligenceService()
        
        # Check status
        status = service.get_service_status()
        print(f"\n📊 Service Status:")
        print(f"   Graph: {'✓' if status['graph_available'] else '✗'}")
        print(f"   Vector: {'✓' if status['vector_available'] else '✗'}")
        print(f"   Planner: {'✓' if status['planner_available'] else '✗'}")
        print(f"   Fully Operational: {'✓' if status['fully_operational'] else '✗'}")
        
        # Test queries
        test_queries = [
            "What is the deadline for HORIZON-CL4-2025-DATA-01?",
            "Can an SME from Switzerland participate in Cluster 4?",
            "What is the maximum budget for RIA in Cluster 5?",
        ]
        
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"📝 Query: {query}")
            print("=" * 60)
            
            result = await service.search(query)
            
            print(f"   Intent: {result.intent_type} (confidence: {result.confidence:.2f})")
            print(f"   Graph results: {len(result.graph_results)}")
            print(f"   Vector results: {len(result.vector_results)}")
            print(f"   Sources used: {[s['type'] for s in result.sources]}")
            print(f"   Time: {result.total_time_ms:.0f}ms")
            print(f"   Success: {'✓' if result.success else '✗'}")
            
            if result.graph_results:
                print(f"\n   📊 Sample Graph Result:")
                sample = result.graph_results[0]
                for k, v in list(sample.items())[:5]:
                    if v and k != "source":
                        print(f"      {k}: {v}")
            
            print(f"\n   📄 Context Preview ({len(result.answer_context)} chars):")
            preview = result.answer_context[:300].replace('\n', '\n      ')
            print(f"      {preview}...")
        
        print("\n" + "=" * 60)
        print("✅ Data Intelligence Service test complete!")
        print("=" * 60)
    
    asyncio.run(test_service())


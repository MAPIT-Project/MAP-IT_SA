"""
Agentic Manager

Main orchestrator for the self-correcting agentic loop.
Coordinates understanding, planning, execution, evaluation, reflection, and replanning.

For complex queries requiring multiple tools, delegates to ToolAwareAgent.
"""

"""
Agentic Manager

Main orchestrator for intelligent query processing.

ARCHITECTURE (v2.2):
- ALWAYS uses ToolAwareAgent (ReAct pattern) for best results
- Multi-tool reasoning ensures thorough answers from multiple sources
- Self-correcting with evaluation and reflection
- Falls back to simple loop only if ToolAwareAgent is unavailable

The ToolAwareAgent is smart enough to:
- Finish quickly for simple queries (1-2 iterations)
- Use multiple tools and reasoning for complex queries (up to 5 iterations)
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple

from .agent_context import AgentContext, AgentState
from .result_evaluator import ResultEvaluator, EvaluationResult
from .reflector import Reflector, ReflectionResult, FailureRootCause
from .replanner import Replanner

logger = logging.getLogger(__name__)


class AgenticManager:
    """
    Orchestrates the agentic loop for self-correcting query processing.
    
    Flow:
    1. Understand → Parse intent and entities
    2. Plan → Create execution strategy
    3. Execute → Run searches across data sources
    4. Evaluate → Check if results are sufficient
    5. Reflect → If not sufficient, analyze what went wrong
    6. Replan → Create improved strategy
    7. Repeat 3-6 until sufficient or max iterations
    8. Synthesize → Build final response
    """
    
    def __init__(
        self,
        max_iterations: int = 3,
        sufficient_score: float = 0.65,
        enable_multi_tool: bool = True
    ):
        """
        Initialize the Agentic Manager.
        
        Args:
            max_iterations: Maximum number of plan/execute cycles
            sufficient_score: Minimum evaluation score to consider results sufficient
            enable_multi_tool: Whether to enable multi-tool reasoning for complex queries
        """
        self.max_iterations = max_iterations
        self.sufficient_score = sufficient_score
        self.enable_multi_tool = enable_multi_tool
        
        # Initialize components
        self.evaluator = ResultEvaluator()
        self.evaluator.SUFFICIENT_SCORE = sufficient_score
        self.reflector = Reflector()
        self.replanner = Replanner()
        
        # Initialize core services
        self._init_services()
        
        # Initialize multi-tool agent for complex queries
        self.tool_agent = None
        if enable_multi_tool:
            try:
                from .tool_aware_agent import ToolAwareAgent
                self.tool_agent = ToolAwareAgent(max_iterations=5)
                self._tool_agent_available = True
                logger.info(f"🛠️ ToolAwareAgent initialized (multi-tool reasoning enabled)")
            except Exception as e:
                logger.warning(f"⚠️ ToolAwareAgent unavailable: {e}")
                self._tool_agent_available = False
        else:
            self._tool_agent_available = False
        
        logger.info(f"🤖 AgenticManager initialized (max_iterations={max_iterations}, multi_tool={'✓' if self._tool_agent_available else '✗'})")
    
    def _init_services(self):
        """Initialize data intelligence and planning services."""
        try:
            from ..data_intelligence_service import DataIntelligenceService
            self.data_service = DataIntelligenceService()
            self._data_service_available = True
        except Exception as e:
            logger.warning(f"⚠️ Data Intelligence Service unavailable: {e}")
            self.data_service = None
            self._data_service_available = False
        
        try:
            from ..unified_intent_classifier import UnifiedIntentClassifier
            self.intent_classifier = UnifiedIntentClassifier()
            self._classifier_available = True
        except Exception as e:
            logger.warning(f"⚠️ Intent classifier unavailable: {e}")
            self.intent_classifier = None
            self._classifier_available = False
    
    async def process_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        conversation_history: List[Dict] = None,
        stream_progress: bool = False,
        force_simple: bool = False,  # Only use simple loop if explicitly forced
        intent_classification: Optional[Any] = None  # UnifiedIntent from classifier
    ) -> Dict[str, Any]:
        """
        Process a query using the best available method.
        
        ALWAYS uses ToolAwareAgent (ReAct pattern) for best results.
        The agent is smart enough to:
        - Finish quickly for simple queries (1-2 iterations)  
        - Use multiple tools for complex queries (up to 5 iterations)
        
        Only falls back to simple loop if:
        - ToolAwareAgent is unavailable, OR
        - force_simple=True is explicitly set
        
        Args:
            query: User's question
            conversation_id: Optional conversation ID for context
            conversation_history: Previous messages in conversation
            stream_progress: Whether to enable progress streaming
            force_simple: Force using simple loop instead of multi-tool (not recommended)
            intent_classification: Optional UnifiedIntent from classifier
            
        Returns:
            Dict with response, context, and metadata
        """
        # Extract complexity info from classification (for logging/metadata)
        complexity_type = 'auto'
        suggested_tools = []
        
        if intent_classification:
            complexity_type = getattr(intent_classification, 'complexity_type', 'auto')
            suggested_tools = getattr(intent_classification, 'suggested_tools', [])
        
        # ALWAYS use ToolAwareAgent for best results (unless forced to simple or unavailable)
        if self._tool_agent_available and not force_simple:
            logger.info(f"🧠 Using ToolAwareAgent (ReAct) for BEST results")
            if complexity_type != 'auto':
                logger.info(f"   LLM complexity hint: {complexity_type}")
            if suggested_tools:
                logger.info(f"   Suggested tools: {suggested_tools}")
            
            return await self._process_with_tool_agent(
                query=query,
                conversation_history=conversation_history,
                complexity_type=complexity_type,
                suggested_tools=suggested_tools
            )
        
        # Fallback to simple loop only if ToolAwareAgent unavailable
        if not self._tool_agent_available:
            logger.warning("⚠️ ToolAwareAgent unavailable, using simple loop")
        
        # Standard self-correcting loop for simpler queries
        # Initialize context
        context = AgentContext(
            user_query=query,
            conversation_id=conversation_id,
            max_iterations=self.max_iterations
        )
        
        try:
            # PHASE 1: UNDERSTAND
            context.transition_to(AgentState.UNDERSTANDING)
            await self._understand_query(context, conversation_history)
            
            # Main agentic loop
            while context.should_continue():
                context.iteration += 1
                logger.info(f"🔄 Iteration {context.iteration}/{context.max_iterations}")
                
                # PHASE 2: PLAN or REPLAN
                if context.iteration == 1:
                    context.transition_to(AgentState.PLANNING)
                    await self._create_initial_plan(context)
                else:
                    context.transition_to(AgentState.REPLANNING)
                    await self._replan(context)
                
                # PHASE 3: EXECUTE
                context.transition_to(AgentState.EXECUTING)
                await self._execute_plan(context)
                
                # PHASE 4: EVALUATE
                context.transition_to(AgentState.EVALUATING)
                evaluation = self._evaluate_results(context)
                
                # Check if we're done
                if evaluation.is_sufficient:
                    context.record_success(context.get_strategy_description())
                    logger.info(f"✅ Sufficient results after {context.iteration} iteration(s)")
                    break
                
                # PHASE 5: REFLECT (if not sufficient and not last iteration)
                if context.iteration < context.max_iterations:
                    context.transition_to(AgentState.REFLECTING)
                    await self._reflect_on_failure(context, evaluation)
            
            # PHASE 6: SYNTHESIZE
            context.transition_to(AgentState.SYNTHESIZING)
            response = await self._synthesize_response(context)
            context.final_response = response
            context.transition_to(AgentState.COMPLETE)
            
            return self._build_final_output(context, response)
            
        except Exception as e:
            logger.error(f"❌ Agentic processing error: {e}")
            context.transition_to(AgentState.ERROR)
            context.errors.append(str(e))
            return self._build_error_output(context, str(e))
    
    async def _understand_query(
        self,
        context: AgentContext,
        conversation_history: List[Dict] = None
    ) -> None:
        """Phase 1: Understand the user's query."""
        
        if self._classifier_available:
            try:
                # Use intent classifier
                intent_result = await self.intent_classifier.classify_intent(
                    user_message=context.user_query,
                    conversation_id=0,  # Use 0 for standalone queries
                    recent_messages=conversation_history
                )
                
                context.intent = intent_result.primary_intent
                context.entities = intent_result.entities if hasattr(intent_result, 'entities') else []
                context.query_type = self._map_intent_to_query_type(intent_result.primary_intent)
                
                # Determine required sources
                context.requires_graph = intent_result.primary_intent in [
                    'statistics_query', 'country_eligibility', 'consortium_patterns'
                ]
                context.requires_vector = intent_result.primary_intent in [
                    'faq', 'eligibility_query', 'consortium_requirements', 'policy_context'
                ]
                
                logger.info(
                    f"📖 Understood: intent={context.intent}, "
                    f"entities={context.entities[:3]}, type={context.query_type}"
                )
                
            except Exception as e:
                logger.warning(f"Intent classification failed: {e}")
                # Fall back to defaults
                context.intent = "general_query"
                context.query_type = "exploratory"
                context.requires_vector = True
        else:
            # Defaults when classifier unavailable
            context.intent = "general_query"
            context.query_type = "exploratory"
            context.requires_vector = True
    
    def _map_intent_to_query_type(self, intent: str) -> str:
        """Map intent to query type for evaluation."""
        mapping = {
            'faq': 'factual',
            'statistics_query': 'factual',
            'country_eligibility': 'factual',
            'consortium_requirements': 'procedural',
            'consortium_patterns': 'exploratory',
            'funding_query': 'exploratory',
            'project_search': 'exploratory',
            'eligibility_query': 'procedural',
            'policy_context': 'exploratory',
            'general_query': 'exploratory',
        }
        return mapping.get(intent, 'exploratory')
    
    async def _create_initial_plan(self, context: AgentContext) -> None:
        """Phase 2a: Create the initial execution plan."""
        
        if self._data_service_available and hasattr(self.data_service, 'planner'):
            try:
                # Use QueryPlanner from DataIntelligenceService
                plan = await self.data_service.planner.generate_plan(
                    user_query=context.user_query,
                    conversation_context=""
                )
                
                # Convert to dict format
                plan_dict = {
                    'query': context.user_query,
                    'strategy': 'initial_plan',
                    'steps': [
                        {
                            'source': step.source,
                            'operation': step.operation,
                            'query': step.parameters.get('query', context.user_query),
                            'limit': step.parameters.get('limit', 10)
                        }
                        for step in plan.steps
                    ],
                    'reasoning': f"Intent: {plan.intent_type}, Confidence: {plan.confidence:.2f}"
                }
                
                context.record_plan(plan_dict)
                context.tried_queries.append(context.user_query)
                
                for step in plan.steps:
                    if step.source not in context.tried_sources:
                        context.tried_sources.append(step.source)
                
                logger.info(f"📋 Initial plan: {len(plan.steps)} steps")
                
            except Exception as e:
                logger.warning(f"Plan generation failed: {e}")
                await self._create_fallback_plan(context)
        else:
            await self._create_fallback_plan(context)
    
    async def _create_fallback_plan(self, context: AgentContext) -> None:
        """Create a fallback plan when planner is unavailable."""
        
        steps = []
        
        # Vector search is usually helpful
        if context.requires_vector or not context.requires_graph:
            steps.append({
                'source': 'vector',
                'operation': 'hybrid_search',
                'query': context.user_query,
                'limit': 10
            })
        
        # Graph search for statistics
        if context.requires_graph:
            steps.append({
                'source': 'graph',
                'operation': 'entity_search',
                'query': context.user_query,
                'entities': context.entities,
                'limit': 10
            })
        
        # Always have at least vector search
        if not steps:
            steps.append({
                'source': 'vector',
                'operation': 'semantic_search',
                'query': context.user_query,
                'limit': 10
            })
        
        plan_dict = {
            'query': context.user_query,
            'strategy': 'fallback_plan',
            'steps': steps,
            'reasoning': 'Fallback plan - planner unavailable'
        }
        
        context.record_plan(plan_dict)
        context.tried_queries.append(context.user_query)
    
    async def _replan(self, context: AgentContext) -> None:
        """Phase 2b: Create a new plan based on reflection."""
        
        if not context.last_reflection:
            # If no reflection, just modify the query slightly
            await self._create_fallback_plan(context)
            return
        
        reflection = ReflectionResult(
            failure_analysis=context.last_reflection.get('failure_analysis', ''),
            root_cause=FailureRootCause(context.last_reflection.get('root_cause', 'unknown')),
            confidence=context.last_reflection.get('confidence', 0.5),
            improvement_action=context.last_reflection.get('improvement_action'),
            suggested_query=context.last_reflection.get('suggested_query'),
            suggested_sources=context.last_reflection.get('suggested_sources', []),
            reasoning=context.last_reflection.get('reasoning', '')
        )
        
        new_plan = self.replanner.replan(
            query=context.user_query,
            reflection=reflection,
            failed_strategies=context.failed_strategies,
            tried_queries=context.tried_queries,
            tried_sources=context.tried_sources,
            query_type=context.query_type,
            entities=context.entities
        )
        
        context.record_plan(new_plan)
        
        # Track tried queries and sources
        if new_plan.get('query') not in context.tried_queries:
            context.tried_queries.append(new_plan.get('query'))
        
        for step in new_plan.get('steps', []):
            if step.get('source') not in context.tried_sources:
                context.tried_sources.append(step.get('source'))
        
        logger.info(f"📋 Replanned: strategy={new_plan.get('strategy')}")
    
    async def _execute_plan(self, context: AgentContext) -> None:
        """Phase 3: Execute the current plan."""
        
        if not context.current_plan:
            context.results = {}
            return
        
        start_time = datetime.now()
        
        try:
            if self._data_service_available:
                # Use DataIntelligenceService for execution
                search_query = context.current_plan.get('query', context.user_query)
                
                result = await self.data_service.search(
                    query=search_query,
                    context="",
                    max_results=15,
                    rerank=True
                )
                
                # Convert to standard format
                context.results = {
                    'graph': {'results': result.graph_results or []},
                    'vector': {'results': result.vector_results or []},
                    'keyword': {'results': result.keyword_results or []},
                    'answer_context': result.answer_context,
                    'sources': result.sources,
                    'success': result.success
                }
                
            else:
                # Fallback: empty results
                context.results = {
                    'graph': {'results': []},
                    'vector': {'results': []},
                    'keyword': {'results': []},
                    'success': False
                }
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            context.record_results(context.results, execution_time)
            
            total_results = self._count_results(context.results)
            logger.info(f"🔍 Executed: {total_results} results in {execution_time:.0f}ms")
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            context.results = {'success': False, 'error': str(e)}
            context.errors.append(f"Execution: {e}")
    
    def _evaluate_results(self, context: AgentContext) -> EvaluationResult:
        """Phase 4: Evaluate the quality of results."""
        
        evaluation = self.evaluator.evaluate(
            query=context.user_query,
            query_type=context.query_type,
            results=context.results,
            entities=context.entities
        )
        
        context.record_evaluation(
            score=evaluation.score,
            reasons=evaluation.reasons,
            is_sufficient=evaluation.is_sufficient
        )
        
        logger.info(
            f"📊 Evaluation: score={evaluation.score:.2f}, "
            f"sufficient={evaluation.is_sufficient}"
        )
        
        return evaluation
    
    async def _reflect_on_failure(
        self,
        context: AgentContext,
        evaluation: EvaluationResult
    ) -> None:
        """Phase 5: Reflect on why results were insufficient."""
        
        reflection = self.reflector.reflect(
            query=context.user_query,
            evaluation=evaluation,
            current_plan=context.current_plan,
            results=context.results,
            failed_strategies=context.failed_strategies,
            entities=context.entities
        )
        
        # Store for replanning
        context.last_reflection = {
            'failure_analysis': reflection.failure_analysis,
            'root_cause': reflection.root_cause.value,
            'confidence': reflection.confidence,
            'improvement_action': reflection.improvement_action,
            'suggested_query': reflection.suggested_query,
            'suggested_sources': reflection.suggested_sources,
            'reasoning': reflection.reasoning
        }
        
        context.record_failure(
            reason=reflection.failure_analysis,
            strategy_description=context.get_strategy_description()
        )
        
        logger.info(
            f"🔍 Reflection: {reflection.root_cause.value} → "
            f"{reflection.improvement_action.value}"
        )
    
    async def _synthesize_response(self, context: AgentContext) -> str:
        """Phase 6: Synthesize the final response."""
        
        # Use the answer_context from the last successful execution
        answer_context = context.results.get('answer_context', '')
        
        if answer_context:
            return answer_context
        
        # Fallback: build from results
        return self._build_fallback_response(context)
    
    def _build_fallback_response(self, context: AgentContext) -> str:
        """Build a response when answer_context is not available."""
        
        parts = []
        
        # Add result summaries
        vector_results = context.results.get('vector', {}).get('results', [])
        if vector_results:
            parts.append("Based on the available documents:")
            for i, result in enumerate(vector_results[:3], 1):
                content = result.get('content', '')[:200]
                parts.append(f"\n{i}. {content}...")
        
        graph_results = context.results.get('graph', {}).get('results', [])
        if graph_results:
            parts.append("\n\nFrom the knowledge graph:")
            for result in graph_results[:3]:
                if isinstance(result, dict):
                    # Format graph result more nicely
                    formatted = self._format_graph_result(result)
                    parts.append(f"- {formatted}")
        
        if not parts:
            return (
                f"I searched for information about '{context.user_query}' "
                "but found limited results. Please try rephrasing your question "
                "or ask about a more specific aspect."
            )
        
        return '\n'.join(parts)

    def _format_graph_result(self, result: Dict[str, Any]) -> str:
        """Format a graph database result into a readable string."""
        # Handle project results
        if 'acronym' in result or 'project_id' in result:
            acronym = result.get('acronym', '')
            title = result.get('title', '')
            project_id = result.get('project_id', result.get('id', ''))
            if acronym and title:
                return f"{acronym}: {title[:100]}"
            elif title:
                return f"{title[:100]} (ID: {project_id})"
            elif acronym:
                return f"{acronym} (ID: {project_id})"

        # Handle organization results
        if 'organization_name' in result or 'org_name' in result:
            org_name = result.get('organization_name', result.get('org_name', ''))
            country = result.get('country', '')
            if org_name:
                return f"{org_name} ({country})" if country else org_name

        # Handle statistics results
        if 'success_rate' in result or 'funding_amount' in result:
            parts = []
            if 'programme' in result:
                parts.append(result['programme'])
            if 'success_rate' in result:
                parts.append(f"Success rate: {result['success_rate']}")
            if 'funding_amount' in result:
                parts.append(f"Funding: {result['funding_amount']}")
            if parts:
                return " - ".join(parts)

        # Handle topic/cluster results
        if 'topic' in result or 'cluster' in result:
            topic = result.get('topic', result.get('cluster', ''))
            count = result.get('count', result.get('project_count', ''))
            if topic and count:
                return f"{topic}: {count} projects"
            elif topic:
                return topic

        # Fallback: extract key fields
        key_fields = ['name', 'title', 'description', 'content', 'label']
        for field in key_fields:
            if field in result and result[field]:
                return str(result[field])[:150]

        # Last resort: show first few key-value pairs
        items = [(k, v) for k, v in result.items() if v and k not in ['id', 'uuid', 'created_at']][:3]
        if items:
            return ", ".join(f"{k}: {str(v)[:50]}" for k, v in items)

        return "Result data available"

    def _count_results(self, results: Dict[str, Any]) -> int:
        """Count total results across all sources."""
        total = 0
        for source in ['graph', 'vector', 'keyword']:
            if source in results:
                data = results[source]
                if isinstance(data, dict):
                    total += len(data.get('results', []))
                elif isinstance(data, list):
                    total += len(data)
        return total
    
    def _build_final_output(
        self,
        context: AgentContext,
        response: str
    ) -> Dict[str, Any]:
        """Build the final output dictionary."""
        
        return {
            'response': response,
            'success': True,
            'metadata': {
                'iterations': context.iteration,
                'final_quality_score': context.result_quality,
                'confidence': context.confidence_level,
                'is_sufficient': context.is_sufficient,
                'intent': context.intent,
                'query_type': context.query_type,
                'strategies_tried': len(context.plan_history),
                'strategies_failed': len(context.failed_strategies),
                'total_time_ms': (datetime.now() - context.started_at).total_seconds() * 1000
            },
            'context': context.to_dict(),
            'sources': context.results.get('sources', [])
        }
    
    def _build_error_output(
        self,
        context: AgentContext,
        error: str
    ) -> Dict[str, Any]:
        """Build error output dictionary."""
        
        return {
            'response': (
                f"I encountered an issue while searching for information: {error}. "
                "Please try rephrasing your question."
            ),
            'success': False,
            'error': error,
            'metadata': {
                'iterations': context.iteration,
                'state': context.state.value,
                'errors': context.errors
            },
            'context': context.to_dict()
        }
    
    async def _process_with_tool_agent(
        self,
        query: str,
        conversation_history: List[Dict] = None,
        complexity_type: str = 'standard',
        suggested_tools: List[str] = None
    ) -> Dict[str, Any]:
        """
        Process a complex query using the multi-tool ToolAwareAgent.
        
        This enables:
        - Multiple tool calls in sequence or parallel
        - Reasoning between tool calls
        - Cross-referencing results from different sources
        - Drawing conclusions based on combined evidence
        """
        start_time = datetime.now()
        
        try:
            # Build context string from conversation history
            context_str = ""
            if conversation_history:
                recent = conversation_history[-3:]  # Last 3 messages
                for msg in recent:
                    context_str += f"{msg.get('sender', 'user')}: {msg.get('text', '')}\n"
            
            # Call the tool-aware agent
            result = await self.tool_agent.process_query(
                query=query,
                context=context_str,
                conversation_history=conversation_history
            )
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Format the response
            answer = result.get('answer', '')
            reasoning_steps = result.get('reasoning_steps', [])
            sources_used = result.get('sources_used', [])
            
            # Build a nice response with reasoning trace
            response_parts = [answer]
            
            # Add reasoning summary if multiple steps were taken
            if len(reasoning_steps) > 1:
                response_parts.append("\n\n---\n*How I found this:*")
                for step in reasoning_steps[:3]:  # Show first 3 steps
                    tools = step.get('tools_called', [])
                    if tools:
                        response_parts.append(f"- Step {step['step']}: Called {', '.join(tools)}")
            
            # Add sources
            if sources_used:
                response_parts.append(f"\n*Sources: {', '.join(sources_used[:5])}*")
            
            final_response = '\n'.join(response_parts)
            
            return {
                'response': final_response,
                'success': result.get('success', True),
                'metadata': {
                    'mode': 'multi_tool',
                    'complexity_type': complexity_type,
                    'iterations': result.get('iterations', 1),
                    'tools_used': [s for s in sources_used],
                    'reasoning_steps': len(reasoning_steps),
                    'confidence': result.get('confidence', 0.8),
                    'total_time_ms': total_time
                },
                'reasoning_trace': reasoning_steps,
                'sources': sources_used
            }
            
        except Exception as e:
            logger.error(f"❌ ToolAwareAgent error: {e}")
            
            # Fall back to standard processing
            logger.info("Falling back to standard agentic loop")
            context = AgentContext(
                user_query=query,
                max_iterations=self.max_iterations
            )
            
            # Run standard loop
            return await self._run_standard_loop(context, conversation_history)
    
    async def _run_standard_loop(
        self,
        context: AgentContext,
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """Run the standard self-correcting loop."""
        try:
            # PHASE 1: UNDERSTAND
            context.transition_to(AgentState.UNDERSTANDING)
            await self._understand_query(context, conversation_history)
            
            # Main agentic loop
            while context.should_continue():
                context.iteration += 1
                
                if context.iteration == 1:
                    context.transition_to(AgentState.PLANNING)
                    await self._create_initial_plan(context)
                else:
                    context.transition_to(AgentState.REPLANNING)
                    await self._replan(context)
                
                context.transition_to(AgentState.EXECUTING)
                await self._execute_plan(context)
                
                context.transition_to(AgentState.EVALUATING)
                evaluation = self._evaluate_results(context)
                
                if evaluation.is_sufficient:
                    context.record_success(context.get_strategy_description())
                    break
                
                if context.iteration < context.max_iterations:
                    context.transition_to(AgentState.REFLECTING)
                    await self._reflect_on_failure(context, evaluation)
            
            context.transition_to(AgentState.SYNTHESIZING)
            response = await self._synthesize_response(context)
            context.final_response = response
            context.transition_to(AgentState.COMPLETE)
            
            return self._build_final_output(context, response)
            
        except Exception as e:
            context.transition_to(AgentState.ERROR)
            context.errors.append(str(e))
            return self._build_error_output(context, str(e))
    
    async def process_query_streaming(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        conversation_history: List[Dict] = None,
        intent_classification: Optional[Any] = None,  # UnifiedIntent from classifier
        force_simple: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a query with streaming progress updates.
        
        ALWAYS uses ToolAwareAgent (ReAct pattern) for best results.
        Yields status updates showing reasoning steps and tool calls.
        """
        
        # Extract complexity info from classification (for logging)
        complexity_type = 'auto'
        suggested_tools = []
        
        if intent_classification:
            complexity_type = getattr(intent_classification, 'complexity_type', 'auto')
            suggested_tools = getattr(intent_classification, 'suggested_tools', [])
        
        # ALWAYS use multi-tool for best results (unless forced to simple or unavailable)
        if self._tool_agent_available and not force_simple:
            async for update in self._stream_multi_tool_query(
                query, 
                conversation_history,
                complexity_type=complexity_type,
                suggested_tools=suggested_tools
            ):
                yield update
            return
        
        # Fallback only if unavailable
        if not self._tool_agent_available:
            yield {
                'type': 'status',
                'message': 'Using simple search (multi-tool unavailable)',
                'phase': 'fallback'
            }
        
        # Standard streaming for simpler queries
        # Initialize context
        context = AgentContext(
            user_query=query,
            conversation_id=conversation_id,
            max_iterations=self.max_iterations
        )
        
        try:
            # UNDERSTANDING
            yield {'type': 'status', 'message': 'Understanding your question...', 'phase': 'understanding'}
            context.transition_to(AgentState.UNDERSTANDING)
            await self._understand_query(context, conversation_history)
            yield {'type': 'status', 'message': f'Identified intent: {context.intent}', 'phase': 'understanding'}
            
            while context.should_continue():
                context.iteration += 1
                
                # PLANNING
                if context.iteration == 1:
                    yield {'type': 'status', 'message': 'Planning search strategy...', 'phase': 'planning'}
                    context.transition_to(AgentState.PLANNING)
                    await self._create_initial_plan(context)
                else:
                    yield {'type': 'status', 'message': 'Trying a different approach...', 'phase': 'replanning', 'iteration': context.iteration}
                    context.transition_to(AgentState.REPLANNING)
                    await self._replan(context)
                
                # EXECUTING
                yield {'type': 'status', 'message': 'Searching data sources...', 'phase': 'executing', 'iteration': context.iteration}
                context.transition_to(AgentState.EXECUTING)
                await self._execute_plan(context)
                
                result_count = self._count_results(context.results)
                yield {'type': 'progress', 'message': f'Found {result_count} results', 'phase': 'executing', 'count': result_count}
                
                # EVALUATING
                context.transition_to(AgentState.EVALUATING)
                evaluation = self._evaluate_results(context)
                
                if evaluation.is_sufficient:
                    context.record_success(context.get_strategy_description())
                    yield {'type': 'status', 'message': 'Found good results!', 'phase': 'evaluating', 'score': evaluation.score}
                    break
                else:
                    if context.iteration < context.max_iterations:
                        yield {'type': 'status', 'message': f'Results not quite right (score: {evaluation.score:.0%}), refining search...', 'phase': 'reflecting'}
                        context.transition_to(AgentState.REFLECTING)
                        await self._reflect_on_failure(context, evaluation)
            
            # SYNTHESIZING
            yield {'type': 'status', 'message': 'Preparing response...', 'phase': 'synthesizing'}
            context.transition_to(AgentState.SYNTHESIZING)
            response = await self._synthesize_response(context)
            context.final_response = response
            context.transition_to(AgentState.COMPLETE)
            
            # Final response
            yield {
                'type': 'response',
                'response': response,
                'metadata': {
                    'iterations': context.iteration,
                    'quality_score': context.result_quality,
                    'confidence': context.confidence_level
                }
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                'type': 'error',
                'error': str(e),
                'message': f"Error processing query: {e}"
            }
    
    async def _stream_multi_tool_query(
        self,
        query: str,
        conversation_history: List[Dict] = None,
        complexity_type: str = 'simple',
        suggested_tools: List[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream progress for multi-tool reasoning queries.
        
        Shows each tool call and reasoning step as they happen.
        Uses LLM-determined complexity type (not regex!).
        """
        
        yield {
            'type': 'status',
            'message': f'Complex {complexity_type} query detected - using multi-tool reasoning...',
            'phase': 'multi_tool_init',
            'complexity': complexity_type
        }
        
        try:
            # Build context
            context_str = ""
            if conversation_history:
                recent = conversation_history[-3:]
                for msg in recent:
                    context_str += f"{msg.get('sender', 'user')}: {msg.get('text', '')}\n"
            
            # We'll run the tool agent and stream its progress
            # For now, we simulate streaming by running and then yielding results
            # In the future, the ToolAwareAgent could yield intermediate results
            
            yield {
                'type': 'status',
                'message': 'Reasoning about which tools to use...',
                'phase': 'multi_tool_reasoning'
            }
            
            result = await self.tool_agent.process_query(
                query=query,
                context=context_str,
                conversation_history=conversation_history
            )
            
            # Yield reasoning steps as progress updates
            reasoning_steps = result.get('reasoning_steps', [])
            for step in reasoning_steps:
                tools_called = step.get('tools_called', [])
                thought = step.get('thought', '')[:100]
                
                if tools_called:
                    yield {
                        'type': 'progress',
                        'message': f"Step {step['step']}: Calling {', '.join(tools_called)}",
                        'phase': 'multi_tool_executing',
                        'tools': tools_called,
                        'thought': thought
                    }
                else:
                    yield {
                        'type': 'progress',
                        'message': f"Step {step['step']}: {thought}...",
                        'phase': 'multi_tool_analyzing'
                    }
            
            # Show sources used
            sources = result.get('sources_used', [])
            if sources:
                yield {
                    'type': 'progress',
                    'message': f'Gathered data from {len(sources)} sources',
                    'phase': 'multi_tool_gathering',
                    'sources': sources
                }
            
            yield {
                'type': 'status',
                'message': 'Synthesizing answer from multiple sources...',
                'phase': 'multi_tool_synthesizing'
            }
            
            # Final response
            answer = result.get('answer', '')
            
            # Add reasoning trace to response
            if len(reasoning_steps) > 1:
                answer += "\n\n---\n*Reasoning trace:*"
                for step in reasoning_steps[:3]:
                    tools = step.get('tools_called', [])
                    if tools:
                        answer += f"\n- Step {step['step']}: Used {', '.join(tools)}"
            
            yield {
                'type': 'response',
                'response': answer,
                'metadata': {
                    'mode': 'multi_tool',
                    'complexity': complexity_type,
                    'iterations': result.get('iterations', 1),
                    'tools_used': sources,
                    'reasoning_steps': len(reasoning_steps),
                    'confidence': result.get('confidence', 0.8)
                }
            }
            
        except Exception as e:
            logger.error(f"Multi-tool streaming error: {e}")
            yield {
                'type': 'status',
                'message': 'Falling back to standard search...',
                'phase': 'fallback'
            }
            
            # Fall back to standard streaming
            async for update in self._stream_standard_query(query, conversation_history):
                yield update
    
    async def _stream_standard_query(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Fallback standard streaming when multi-tool fails."""
        context = AgentContext(
            user_query=query,
            max_iterations=self.max_iterations
        )
        
        try:
            await self._understand_query(context, conversation_history)
            await self._create_fallback_plan(context)
            await self._execute_plan(context)
            response = await self._synthesize_response(context)
            
            yield {
                'type': 'response',
                'response': response,
                'metadata': {
                    'mode': 'fallback',
                    'quality_score': context.result_quality
                }
            }
        except Exception as e:
            yield {
                'type': 'error',
                'error': str(e)
            }


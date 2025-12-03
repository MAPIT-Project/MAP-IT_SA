"""
Tool-Aware ReAct Agent

An advanced agent that can:
1. Reason about what tools to use
2. Call multiple tools in parallel or sequence
3. Compare and contrast results from different sources
4. Iteratively refine by calling more tools based on conclusions
5. Synthesize a final answer from multiple sources

Based on the ReAct (Reasoning + Acting) pattern.
"""

import logging
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of tools available to the agent."""
    STATISTICS = "statistics"      # Graph DB queries for numbers
    DOCUMENTS = "documents"        # Vector search for text
    CALLS = "calls"               # Funding call search
    PROJECTS = "projects"         # CORDIS project search
    COMPARISON = "comparison"     # Cross-reference tools
    VALIDATION = "validation"     # Fact-checking tools


@dataclass
class Tool:
    """Definition of a tool the agent can use."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]
    examples: List[str] = field(default_factory=list)
    executor: Optional[Callable[..., Awaitable[Any]]] = None
    
    def to_prompt_format(self) -> str:
        """Format tool for LLM prompt."""
        params_str = ", ".join(f"{k}: {v}" for k, v in self.parameters.items())
        return f"- **{self.name}**({params_str}): {self.description}"


@dataclass
class ToolCall:
    """A planned or executed tool call."""
    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str = ""
    result: Any = None
    success: bool = False
    error: Optional[str] = None
    execution_time_ms: float = 0


@dataclass
class ReasoningStep:
    """A single step in the agent's reasoning process."""
    step_number: int
    thought: str
    action: str  # "call_tool", "analyze", "conclude", "compare"
    tool_calls: List[ToolCall] = field(default_factory=list)
    observation: str = ""
    next_action_needed: bool = True


@dataclass 
class AgentPlan:
    """The agent's plan for answering a complex question."""
    query: str
    complexity: str  # "simple", "multi_source", "comparison", "analysis"
    required_sources: List[str]
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    confidence: float = 0.0
    sources_used: List[str] = field(default_factory=list)


class ToolAwareAgent:
    """
    ReAct-style agent that reasons about and uses multiple tools.
    
    Key capabilities:
    - Analyzes query complexity to determine tool needs
    - Calls multiple tools in parallel when independent
    - Sequences tool calls when results depend on each other
    - Compares and contrasts results from different sources
    - Iteratively refines by calling more tools based on findings
    """
    
    # System prompt for the reasoning LLM
    REASONING_PROMPT = """You are an intelligent research assistant for EU funding (Horizon Europe, EIC, ERC, etc.).

## Available Tools

{tools_description}

## Understanding User Intent

The user's message may:
- Be a NEW question: Search for the information they need
- REFER to previous results: "the 4th one", "that call", "tell me more about it"
- BE A COMPLAINT: "only 1 result", "that's not enough", "wtf" → They want more/better results
- ASK FOR MORE: "show me more", "any others" → Search again with same topic

When the user refers to previous conversation:
- Look at CONVERSATION HISTORY to understand what they mean
- If they say "the 3rd call" - find the 3rd call ID from the history
- If they complain about results - search again for the SAME TOPIC with more results

## Your Task

1. **UNDERSTAND**: What does the user actually want?
   - Read the conversation history to understand context
   - Identify if this is a new question or follow-up

2. **DECIDE**: What tools to use (or answer directly if you can)
   - For funding calls → use search_funding_calls
   - For projects → use search_projects
   - For statistics → use get_programme_statistics or get_country_statistics
   - For eligibility rules → use search_documents
   - For comparing things → use compare_programmes

3. **EXECUTE**: Call the tools

4. **RESPOND**: Provide a helpful answer

## Response Format

Respond ONLY with JSON (no other text):
```json
{{
    "thought": "What does the user want? What info do I need?",
    "action": "call_tools" | "conclude",
    "tool_calls": [
        {{
            "tool": "tool_name",
            "parameters": {{"param1": "value1"}},
            "reasoning": "Why this tool helps"
        }}
    ],
    "needs_more_info": true | false,
    "conclusion": "Final answer (if action is 'conclude')"
}}
```

## Rules

1. ALWAYS respond with valid JSON
2. For complaints about few results, search again with the SAME TOPIC
3. For calls/projects, use the dedicated search tools (not search_documents)
4. Can call multiple tools in parallel if independent
5. Cite your sources in the conclusion

## Response Formatting Guidelines

When presenting results to users:
- For funding calls: Show ALL relevant results (up to 10), not just 2-3
- For each call/project: Include title, deadline (if available), cluster/programme, and brief description
- Format as a numbered list for easy reference
- Include call IDs when available so users can ask "tell me more about #3"
- Don't truncate or summarize too aggressively - users want details

## Conversation History

{context}

## Current User Message

{query}

## Previous Steps (this reasoning session)

{previous_steps}

## Tool Results (if any)

{tool_results}

What is your next step? Remember: Output ONLY JSON."""

    def __init__(self, max_iterations: int = 5):
        """Initialize the tool-aware agent."""
        self.max_iterations = max_iterations
        self.tools: Dict[str, Tool] = {}
        self._init_tools()
        self._init_llm()
        
        logger.info(f"🛠️ ToolAwareAgent initialized with {len(self.tools)} tools")
    
    def _init_llm(self):
        """Initialize the LLM for reasoning."""
        import os
        self.llm_provider = os.getenv('DEFAULT_AI_PROVIDER', 'gemini')
        
        if self.llm_provider == 'gemini':
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
                # Use GEMINI_MODEL from env - defaults to latest flash model
                model_name = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
                self.llm = genai.GenerativeModel(model_name)
                logger.info(f"🧠 ToolAwareAgent using model: {model_name}")
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
                self.llm = None
        else:
            self.llm = None
            logger.warning("LLM not configured for ToolAwareAgent")
    
    def _init_tools(self):
        """Initialize all available tools."""
        
        # Graph-based statistics tools
        self.register_tool(Tool(
            name="get_programme_statistics",
            description="Get success rates, funding amounts, and participation statistics for a specific programme or cluster",
            category=ToolCategory.STATISTICS,
            parameters={
                "programme": "Programme name (e.g., 'EIC', 'ERC', 'MSCA', 'Cluster 5')",
                "metric": "Optional: specific metric like 'success_rate', 'avg_funding', 'participation'"
            },
            examples=[
                "get_programme_statistics(programme='EIC Accelerator')",
                "get_programme_statistics(programme='Cluster 5', metric='success_rate')"
            ]
        ))
        
        self.register_tool(Tool(
            name="get_country_statistics",
            description="Get participation and success statistics for a specific country",
            category=ToolCategory.STATISTICS,
            parameters={
                "country": "Country name or code",
                "programme": "Optional: filter by programme"
            },
            examples=[
                "get_country_statistics(country='Germany')",
                "get_country_statistics(country='Netherlands', programme='EIC')"
            ]
        ))
        
        self.register_tool(Tool(
            name="compare_programmes",
            description="Compare statistics between two programmes or clusters",
            category=ToolCategory.COMPARISON,
            parameters={
                "programme_a": "First programme to compare",
                "programme_b": "Second programme to compare",
                "metrics": "List of metrics to compare"
            },
            examples=[
                "compare_programmes(programme_a='EIC', programme_b='ERC', metrics=['success_rate', 'avg_funding'])"
            ]
        ))
        
        # Document search tools
        self.register_tool(Tool(
            name="search_documents",
            description="Search official EU documents for specific information (rules, eligibility, requirements)",
            category=ToolCategory.DOCUMENTS,
            parameters={
                "query": "Search query",
                "document_type": "Optional: 'regulation', 'work_programme', 'guidance', 'template'",
                "max_results": "Optional: number of results (default 5)"
            },
            examples=[
                "search_documents(query='consortium eligibility RIA')",
                "search_documents(query='budget categories', document_type='guidance')"
            ]
        ))
        
        self.register_tool(Tool(
            name="search_specific_topic",
            description="Deep search for a specific topic with semantic understanding",
            category=ToolCategory.DOCUMENTS,
            parameters={
                "topic": "The specific topic to search",
                "context": "Additional context to narrow results"
            },
            examples=[
                "search_specific_topic(topic='third country participation', context='eligibility rules')"
            ]
        ))
        
        # Funding call tools
        self.register_tool(Tool(
            name="search_funding_calls",
            description="Search for open or upcoming funding calls",
            category=ToolCategory.CALLS,
            parameters={
                "keywords": "Keywords to search for",
                "status": "Optional: 'open', 'upcoming', 'closed'",
                "year": "Optional: specific year"
            },
            examples=[
                "search_funding_calls(keywords='hydrogen energy', status='open')",
                "search_funding_calls(keywords='AI healthcare', year=2025)"
            ]
        ))
        
        self.register_tool(Tool(
            name="get_call_details",
            description="Get detailed information about a specific funding call",
            category=ToolCategory.CALLS,
            parameters={
                "call_id": "The call identifier (e.g., 'HORIZON-CL5-2025-D3-01')"
            },
            examples=[
                "get_call_details(call_id='HORIZON-CL5-2025-D3-01')"
            ]
        ))
        
        # Project search tools
        self.register_tool(Tool(
            name="search_projects",
            description="Search CORDIS database for funded projects",
            category=ToolCategory.PROJECTS,
            parameters={
                "keywords": "Keywords to search for",
                "programme": "Optional: filter by programme",
                "country": "Optional: filter by country"
            },
            examples=[
                "search_projects(keywords='quantum computing')",
                "search_projects(keywords='renewable energy', country='Sweden')"
            ]
        ))
        
        self.register_tool(Tool(
            name="get_project_details",
            description="Get detailed information about a specific project",
            category=ToolCategory.PROJECTS,
            parameters={
                "project_id": "The project identifier or acronym"
            },
            examples=[
                "get_project_details(project_id='101000000')"
            ]
        ))
        
        # Relationship-based project discovery tools
        self.register_tool(Tool(
            name="find_similar_projects",
            description="Find projects similar to a given project based on topic, consortium partners, or cluster",
            category=ToolCategory.PROJECTS,
            parameters={
                "project_id": "The reference project ID",
                "similarity_type": "Type: 'topic' (same topic), 'consortium' (shared partners), or 'cluster' (same cluster)"
            },
            examples=[
                "find_similar_projects(project_id='101000000', similarity_type='topic')",
                "find_similar_projects(project_id='101000000', similarity_type='consortium')"
            ]
        ))

        self.register_tool(Tool(
            name="find_semantically_similar_projects",
            description="Find projects semantically similar to a given project using AI embeddings (understands project objectives and descriptions)",
            category=ToolCategory.PROJECTS,
            parameters={
                "project_id": "The reference project ID",
                "limit": "Optional: maximum number of results (default 10)"
            },
            examples=[
                "find_semantically_similar_projects(project_id='101000000')",
                "find_semantically_similar_projects(project_id='101000000', limit=5)"
            ]
        ))
        
        self.register_tool(Tool(
            name="find_organization_projects",
            description="Find all projects an organization has participated in",
            category=ToolCategory.PROJECTS,
            parameters={
                "organization_name": "Name (or partial name) of the organization",
                "role": "Optional: 'coordinator' or 'participant'"
            },
            examples=[
                "find_organization_projects(organization_name='Fraunhofer')",
                "find_organization_projects(organization_name='TU Munich', role='coordinator')"
            ]
        ))
        
        self.register_tool(Tool(
            name="get_collaboration_network",
            description="Get the collaboration network showing which organizations frequently partner together",
            category=ToolCategory.PROJECTS,
            parameters={
                "organization_name": "Name of the organization to find partners for"
            },
            examples=[
                "get_collaboration_network(organization_name='CNRS')"
            ]
        ))
        
        self.register_tool(Tool(
            name="search_by_cluster",
            description="Find projects in a specific research cluster (e.g., Climate, Health, Digital)",
            category=ToolCategory.PROJECTS,
            parameters={
                "cluster": "Cluster name or code (e.g., 'Climate', 'CL5', 'Health')"
            },
            examples=[
                "search_by_cluster(cluster='Climate')",
                "search_by_cluster(cluster='CL4')"
            ]
        ))
        
        # Validation/cross-reference tools
        self.register_tool(Tool(
            name="verify_eligibility",
            description="Check eligibility rules for a specific scenario",
            category=ToolCategory.VALIDATION,
            parameters={
                "entity_type": "Type of entity (SME, university, company, etc.)",
                "country": "Country of the entity",
                "programme": "Target programme",
                "role": "Optional: 'coordinator', 'participant'"
            },
            examples=[
                "verify_eligibility(entity_type='SME', country='Switzerland', programme='Horizon Europe')"
            ]
        ))
        
        self.register_tool(Tool(
            name="cross_reference",
            description="Cross-reference information from multiple sources to verify accuracy",
            category=ToolCategory.VALIDATION,
            parameters={
                "claim": "The claim to verify",
                "sources": "List of source types to check"
            },
            examples=[
                "cross_reference(claim='EIC has 8% success rate', sources=['graph', 'documents'])"
            ]
        ))
    
    def register_tool(self, tool: Tool):
        """Register a tool with the agent."""
        self.tools[tool.name] = tool
    
    def _get_tools_description(self) -> str:
        """Generate tools description for the prompt."""
        by_category = {}
        for tool in self.tools.values():
            cat = tool.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool.to_prompt_format())
        
        sections = []
        for category, tools in by_category.items():
            sections.append(f"### {category.title()} Tools\n" + "\n".join(tools))
        
        return "\n\n".join(sections)
    
    async def process_query(
        self,
        query: str,
        context: str = "",
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a complex query using multi-tool reasoning.
        
        Args:
            query: User's question
            context: Additional context
            conversation_history: Previous messages
            
        Returns:
            Dict with answer, reasoning steps, and sources
        """
        start_time = datetime.now()
        
        # Initialize plan
        plan = AgentPlan(
            query=query,
            complexity=self._assess_complexity(query),
            required_sources=self._identify_required_sources(query)
        )
        
        logger.info(f"🧠 Query complexity: {plan.complexity}, sources needed: {plan.required_sources}")
        
        # ReAct loop
        iteration = 0
        all_tool_results = {}
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 Reasoning iteration {iteration}/{self.max_iterations}")
            
            # Get next action from LLM
            reasoning_result = await self._reason_next_step(
                query=query,
                context=context,
                previous_steps=plan.reasoning_steps,
                tool_results=all_tool_results
            )
            
            if not reasoning_result:
                logger.warning("Reasoning step failed, using fallback")
                break
            
            # Create reasoning step
            step = ReasoningStep(
                step_number=iteration,
                thought=reasoning_result.get('thought', ''),
                action=reasoning_result.get('action', 'conclude')
            )
            
            # Handle different actions
            if step.action == 'call_tools':
                # Execute tool calls
                tool_calls = reasoning_result.get('tool_calls', [])
                step.tool_calls = await self._execute_tool_calls(tool_calls)
                
                # Collect results
                for tc in step.tool_calls:
                    if tc.success:
                        all_tool_results[f"{tc.tool_name}_{iteration}"] = tc.result
                
                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get('needs_more_info', True)
                
            elif step.action == 'analyze_results':
                # Analyze without calling more tools
                step.observation = reasoning_result.get('analysis', '')
                step.next_action_needed = reasoning_result.get('needs_more_info', False)
                
            elif step.action == 'conclude':
                # Final answer
                plan.final_answer = reasoning_result.get('conclusion', '')
                plan.confidence = reasoning_result.get('confidence', 0.8)
                step.next_action_needed = False
            
            plan.reasoning_steps.append(step)
            
            # Check if we should stop
            if not step.next_action_needed:
                logger.info(f"✅ Agent concluded after {iteration} iteration(s)")
                break
        
        # Build final response
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            'answer': plan.final_answer or self._build_fallback_answer(plan),
            'success': plan.final_answer is not None,
            'reasoning_steps': [
                {
                    'step': s.step_number,
                    'thought': s.thought,
                    'action': s.action,
                    'tools_called': [tc.tool_name for tc in s.tool_calls],
                    'observation': s.observation[:200] if s.observation else ''
                }
                for s in plan.reasoning_steps
            ],
            'sources_used': list(all_tool_results.keys()),
            'complexity': plan.complexity,
            'iterations': iteration,
            'confidence': plan.confidence,
            'total_time_ms': total_time
        }
    
    def _assess_complexity(self, query: str) -> str:
        """Assess the complexity of a query."""
        query_lower = query.lower()
        
        # Comparison queries
        if any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference between', 'better']):
            return 'comparison'
        
        # Multi-source queries
        if any(word in query_lower for word in ['and also', 'as well as', 'both', 'multiple']):
            return 'multi_source'
        
        # Analysis queries
        if any(word in query_lower for word in ['why', 'analyze', 'explain the reason', 'how does']):
            return 'analysis'
        
        return 'simple'
    
    def _identify_required_sources(self, query: str) -> List[str]:
        """Identify which data sources are needed."""
        sources = []
        query_lower = query.lower()
        
        # Statistics indicators
        if any(word in query_lower for word in ['rate', 'percentage', 'how many', 'statistics', 'average', 'success']):
            sources.append('statistics')
        
        # Document indicators
        if any(word in query_lower for word in ['eligible', 'requirement', 'rule', 'can i', 'allowed', 'must']):
            sources.append('documents')
        
        # Call indicators
        if any(word in query_lower for word in ['call', 'funding', 'deadline', 'apply', 'open']):
            sources.append('calls')
        
        # Project indicators
        if any(word in query_lower for word in ['project', 'funded', 'example', 'similar']):
            sources.append('projects')
        
        return sources if sources else ['documents']
    
    async def _reason_next_step(
        self,
        query: str,
        context: str,
        previous_steps: List[ReasoningStep],
        tool_results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to reason about the next step."""
        
        # Format previous steps
        steps_text = ""
        for step in previous_steps:
            steps_text += f"\n**Step {step.step_number}**\n"
            steps_text += f"Thought: {step.thought}\n"
            steps_text += f"Action: {step.action}\n"
            if step.tool_calls:
                steps_text += f"Tools called: {[tc.tool_name for tc in step.tool_calls]}\n"
            if step.observation:
                steps_text += f"Observation: {step.observation[:300]}...\n"
        
        # Format tool results - use larger limit to show more results
        results_text = ""
        for name, result in tool_results.items():
            result_str = str(result)[:3000] if result else "No results"
            results_text += f"\n**{name}**: {result_str}\n"
        
        # Build prompt
        prompt = self.REASONING_PROMPT.format(
            tools_description=self._get_tools_description(),
            query=query,
            context=context or "No additional context",
            previous_steps=steps_text or "This is the first step",
            tool_results=results_text or "No tool results yet"
        )
        
        try:
            if self.llm:
                response = await asyncio.to_thread(
                    self.llm.generate_content,
                    prompt
                )
                
                # Parse JSON from response
                response_text = response.text
                
                # Extract JSON block
                json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find raw JSON
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    json_str = json_match.group(0) if json_match else response_text
                
                return json.loads(json_str)
            else:
                # Fallback reasoning
                return self._fallback_reasoning(query, previous_steps, tool_results)
                
        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            return self._fallback_reasoning(query, previous_steps, tool_results)
    
    def _fallback_reasoning(
        self,
        query: str,
        previous_steps: List[ReasoningStep],
        tool_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback reasoning when LLM fails."""
        
        if not previous_steps:
            # First step - call basic search
            return {
                'thought': 'Starting with document search to gather information',
                'action': 'call_tools',
                'tool_calls': [{
                    'tool': 'search_documents',
                    'parameters': {'query': query, 'max_results': 5},
                    'reasoning': 'Initial search for relevant information'
                }],
                'needs_more_info': True
            }
        
        if tool_results:
            # Have results - conclude
            return {
                'thought': 'Have gathered information, forming conclusion',
                'action': 'conclude',
                'conclusion': f"Based on the search results: {str(list(tool_results.values())[:2])[:500]}",
                'confidence': 0.6,
                'needs_more_info': False
            }
        
        return {
            'thought': 'Unable to gather more information',
            'action': 'conclude',
            'conclusion': 'I was unable to find specific information to answer this question.',
            'confidence': 0.3,
            'needs_more_info': False
        }
    
    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[ToolCall]:
        """Execute multiple tool calls (in parallel when possible)."""
        
        results = []
        
        # Group calls that can run in parallel
        parallel_calls = []
        
        for tc in tool_calls:
            tool_name = tc.get('tool')
            params = tc.get('parameters', {})
            reasoning = tc.get('reasoning', '')
            
            tool_call = ToolCall(
                tool_name=tool_name,
                parameters=params,
                reasoning=reasoning
            )
            parallel_calls.append((tool_call, self._execute_single_tool(tool_name, params)))
        
        # Execute in parallel
        if parallel_calls:
            start_time = datetime.now()
            
            tasks = [call[1] for call in parallel_calls]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (tool_call, _) in enumerate(parallel_calls):
                result = task_results[i]
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if isinstance(result, Exception):
                    tool_call.success = False
                    tool_call.error = str(result)
                else:
                    tool_call.success = True
                    tool_call.result = result
                
                tool_call.execution_time_ms = execution_time
                results.append(tool_call)
                
                logger.info(f"🔧 Tool {tool_call.tool_name}: {'✓' if tool_call.success else '✗'}")
        
        return results
    
    async def _execute_single_tool(self, tool_name: str, params: Dict) -> Any:
        """Execute a single tool."""
        
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Route to actual tool implementations
        try:
            if tool_name == 'get_programme_statistics':
                return await self._tool_get_programme_stats(params)
            elif tool_name == 'get_country_statistics':
                return await self._tool_get_country_stats(params)
            elif tool_name == 'compare_programmes':
                return await self._tool_compare_programmes(params)
            elif tool_name == 'search_documents':
                return await self._tool_search_documents(params)
            elif tool_name == 'search_specific_topic':
                return await self._tool_search_specific_topic(params)
            elif tool_name == 'search_funding_calls':
                return await self._tool_search_funding_calls(params)
            elif tool_name == 'get_call_details':
                return await self._tool_get_call_details(params)
            elif tool_name == 'search_projects':
                return await self._tool_search_projects(params)
            elif tool_name == 'find_similar_projects':
                return await self._tool_find_similar_projects(params)
            elif tool_name == 'find_semantically_similar_projects':
                return await self._tool_find_semantically_similar_projects(params)
            elif tool_name == 'find_organization_projects':
                return await self._tool_find_organization_projects(params)
            elif tool_name == 'get_collaboration_network':
                return await self._tool_get_collaboration_network(params)
            elif tool_name == 'search_by_cluster':
                return await self._tool_search_by_cluster(params)
            elif tool_name == 'verify_eligibility':
                return await self._tool_verify_eligibility(params)
            elif tool_name == 'cross_reference':
                return await self._tool_cross_reference(params)
            else:
                return {"error": f"Tool {tool_name} not implemented"}
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}
    
    # ==================== Tool Implementations ====================
    
    async def _tool_get_programme_stats(self, params: Dict) -> Dict:
        """Get programme statistics from graph DB."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()
            
            programme = params.get('programme', '')
            result = await asyncio.to_thread(
                graph.get_programme_statistics,
                programme
            )
            return result or {"message": f"No statistics found for {programme}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_get_country_stats(self, params: Dict) -> Dict:
        """Get country statistics from graph DB."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()
            
            country = params.get('country', '')
            result = await asyncio.to_thread(
                graph.get_country_participation,
                country
            )
            return result or {"message": f"No statistics found for {country}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_compare_programmes(self, params: Dict) -> Dict:
        """Compare two programmes."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()
            
            prog_a = params.get('programme_a', '')
            prog_b = params.get('programme_b', '')
            
            stats_a = await asyncio.to_thread(graph.get_programme_statistics, prog_a)
            stats_b = await asyncio.to_thread(graph.get_programme_statistics, prog_b)
            
            return {
                "comparison": {
                    prog_a: stats_a,
                    prog_b: stats_b
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_search_documents(self, params: Dict) -> Dict:
        """Search documents using vector search."""
        try:
            from ..vector_search_service import VectorSearchService
            vector = VectorSearchService()

            query = params.get('query', '')
            max_results = params.get('max_results', 5)
            doc_type = params.get('document_type')

            # Build filters if document type specified
            filters = None
            if doc_type:
                filters = {'document_type': doc_type}

            # hybrid_search uses num_results, not limit
            results = vector.hybrid_search(
                query=query,
                num_results=max_results,
                filters=filters
            )

            return {
                "documents": [
                    {
                        "content": r.content[:300] if hasattr(r, 'content') else str(r)[:300],
                        "source": r.document_title if hasattr(r, 'document_title') else 'Unknown',
                        "score": r.score if hasattr(r, 'score') else 0
                    }
                    for r in results[:max_results]
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_search_specific_topic(self, params: Dict) -> Dict:
        """Deep search for a specific topic."""
        topic = params.get('topic', '')
        context = params.get('context', '')
        query = f"{topic} {context}".strip()
        
        return await self._tool_search_documents({'query': query, 'max_results': 5})
    
    async def _tool_search_funding_calls(self, params: Dict) -> Dict:
        """Search funding calls."""
        try:
            from ..local_call_search_service import LocalCallSearchService
            call_service = LocalCallSearchService()

            keywords = params.get('keywords', '')
            # Handle keywords being a list or string
            if isinstance(keywords, list):
                keywords = ' '.join(keywords)
            status = params.get('status', 'open')
            year = params.get('year')

            # LocalCallSearchService.search_calls uses 'num_results' not 'limit'
            results = call_service.search_calls(
                query=keywords,
                num_results=15,
                include_closed=(status == 'closed'),
                year_filter=str(year) if year else None
            )

            calls = results.get('calls', [])
            return {
                "calls_found": len(calls),
                "calls": [
                    {
                        "call_id": c.get('call_id', ''),
                        "title": c.get('title', ''),
                        "deadline": c.get('deadline', ''),
                        "type": c.get('action_type', ''),
                        "cluster": c.get('cluster', ''),
                        "budget": c.get('budget', '')
                    }
                    for c in calls[:15]
                ]
            }
        except Exception as e:
            logger.error(f"Funding calls search error: {e}")
            return {"error": str(e), "calls": []}
    
    async def _tool_get_call_details(self, params: Dict) -> Dict:
        """Get details for a specific call."""
        try:
            call_id = params.get('call_id', '')
            if not call_id:
                return {"error": "call_id is required"}

            # First try local search for the call
            from ..local_call_search_service import LocalCallSearchService
            call_service = LocalCallSearchService()

            # Search for the specific call
            results = call_service.search_calls(
                query=call_id,
                num_results=5
            )

            calls = results.get('calls', [])
            for call in calls:
                if call_id.upper() in call.get('call_id', '').upper():
                    return {
                        "call_id": call.get('call_id'),
                        "title": call.get('title'),
                        "description": call.get('description', ''),
                        "deadline": call.get('deadline'),
                        "type": call.get('action_type'),
                        "cluster": call.get('cluster'),
                        "budget": call.get('budget'),
                        "topics": call.get('topics', [])
                    }

            return {"message": f"No details found for {call_id}"}
        except Exception as e:
            logger.error(f"Get call details error: {e}")
            return {"error": str(e)}
    
    async def _tool_search_projects(self, params: Dict) -> Dict:
        """Search CORDIS projects using LOCAL database."""
        try:
            from ..local_project_search_service import LocalProjectSearchService
            
            keywords = params.get('keywords', '')
            country = params.get('country')
            programme = params.get('programme')
            
            # Build the full query including country if provided
            # Let the LocalProjectSearchService handle country extraction from natural language
            query = keywords
            if country:
                query = f"{keywords} {country}"
            
            # Build explicit filters for programme only
            filters = {}
            if programme:
                filters['programme'] = programme.upper()
            
            # Use local search service - it will parse country from query
            service = LocalProjectSearchService()
            results = await service.search_projects(
                query=query,
                filters=filters if filters else None,
                limit=10
            )
            
            return {
                "projects": results.get('projects', []),
                "total_found": results.get('total_found', 0),
                "sources": results.get('sources_used', [])
            }
        except Exception as e:
            logger.error(f"Project search error: {e}")
            return {"error": str(e), "projects": []}
    
    async def _tool_find_similar_projects(self, params: Dict) -> Dict:
        """Find projects similar to a given project."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()
            
            project_id = params.get('project_id', '')
            similarity_type = params.get('similarity_type', 'topic')
            
            if not project_id:
                return {"error": "project_id is required", "projects": []}
            
            results = await asyncio.to_thread(
                graph.find_similar_projects,
                project_id=project_id,
                similarity_type=similarity_type,
                limit=10
            )
            
            return {
                "reference_project": project_id,
                "similarity_type": similarity_type,
                "similar_projects": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Similar projects search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_find_semantically_similar_projects(self, params: Dict) -> Dict:
        """Find semantically similar projects using vector embeddings."""
        try:
            from ..local_project_search_service import LocalProjectSearchService

            project_id = params.get('project_id', '')
            limit = params.get('limit', 10)

            if not project_id:
                return {"error": "project_id is required", "projects": []}

            service = LocalProjectSearchService()
            result = await service.find_similar_projects_by_embedding(
                project_id=project_id,
                limit=limit
            )

            return result
        except Exception as e:
            logger.error(f"Semantic similarity search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_find_organization_projects(self, params: Dict) -> Dict:
        """Find projects by organization."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()
            
            org_name = params.get('organization_name', '')
            role = params.get('role')
            
            if not org_name:
                return {"error": "organization_name is required", "projects": []}
            
            results = await asyncio.to_thread(
                graph.find_projects_by_organization,
                organization_name=org_name,
                role=role,
                limit=20
            )
            
            return {
                "organization": org_name,
                "role_filter": role,
                "projects": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Organization projects search error: {e}")
            return {"error": str(e), "projects": []}
    
    async def _tool_get_collaboration_network(self, params: Dict) -> Dict:
        """Get collaboration network for an organization."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()
            
            org_name = params.get('organization_name', '')
            
            if not org_name:
                return {"error": "organization_name is required", "partners": []}
            
            result = await asyncio.to_thread(
                graph.get_organization_collaboration_network,
                organization_name=org_name,
                depth=1,
                limit=30
            )
            
            return result
        except Exception as e:
            logger.error(f"Collaboration network error: {e}")
            return {"error": str(e), "partners": []}
    
    async def _tool_search_by_cluster(self, params: Dict) -> Dict:
        """Search projects in a specific cluster."""
        try:
            from ..local_project_search_service import LocalProjectSearchService
            service = LocalProjectSearchService()
            
            cluster = params.get('cluster', '')
            
            if not cluster:
                return {"error": "cluster parameter is required", "projects": []}
            
            result = await service.search_projects_by_relationship(
                relationship_type="cluster",
                entity_value=cluster,
                limit=15
            )
            
            return result
        except Exception as e:
            logger.error(f"Cluster search error: {e}")
            return {"error": str(e), "projects": []}
    
    async def _tool_verify_eligibility(self, params: Dict) -> Dict:
        """Verify eligibility for a scenario."""
        entity_type = params.get('entity_type', '')
        country = params.get('country', '')
        programme = params.get('programme', '')
        
        # Search documents for eligibility rules
        query = f"{entity_type} {country} eligibility {programme}"
        return await self._tool_search_documents({'query': query, 'max_results': 5})
    
    async def _tool_cross_reference(self, params: Dict) -> Dict:
        """Cross-reference information from multiple sources."""
        claim = params.get('claim', '')
        sources = params.get('sources', ['documents'])
        
        results = {}
        
        if 'documents' in sources:
            results['documents'] = await self._tool_search_documents({'query': claim})
        
        if 'graph' in sources:
            # Extract key terms for graph search
            results['graph'] = await self._tool_get_programme_stats({'programme': claim})
        
        return {"cross_reference": results}
    
    def _summarize_tool_results(self, tool_calls: List[ToolCall]) -> str:
        """Summarize results from tool calls."""
        summaries = []

        for tc in tool_calls:
            if tc.success:
                # Use larger limit to capture more results
                result_str = str(tc.result)[:2000]
                summaries.append(f"{tc.tool_name}: {result_str}")
            else:
                summaries.append(f"{tc.tool_name}: Failed - {tc.error}")

        return "\n".join(summaries)
    
    def _build_fallback_answer(self, plan: AgentPlan) -> str:
        """Build a fallback answer from collected information."""
        
        if not plan.reasoning_steps:
            return "I was unable to find information to answer this question."
        
        # Collect all observations
        observations = []
        for step in plan.reasoning_steps:
            if step.observation:
                observations.append(step.observation)
        
        if observations:
            return f"Based on my search:\n\n" + "\n\n".join(observations[:3])
        
        return "I searched multiple sources but couldn't find a complete answer to your question."


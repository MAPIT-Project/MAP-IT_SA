"""
Proposal-Aware Agent

An extended ToolAwareAgent that is aware of the current proposal context
and can perform proposal-specific operations like:
- Generate section drafts
- Improve and rewrite content
- Evaluate sections (EU evaluator simulation)
- Analyze gaps and suggest fixes
- Check compliance
- Navigate between sections

The agent receives proposal context with every query, allowing it to
provide contextual assistance based on the current document state.
"""

import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from .prompts import REASONING_PROMPT
from .tool_aware_agent import AgentPlan, ReasoningStep, Tool, ToolAwareAgent, ToolCall, ToolCategory

logger = logging.getLogger(__name__)


class ProposalToolCategory:
    """Categories for proposal-specific tools."""

    WRITING = "proposal_writing"
    QUALITY = "proposal_quality"
    NAVIGATION = "proposal_navigation"
    ANALYSIS = "proposal_analysis"


class ProposalAwareAgent(ToolAwareAgent):
    """
    Extended agent with proposal writing awareness.

    Inherits all capabilities from ToolAwareAgent and adds:
    - Proposal context injection
    - Proposal-specific tools (draft, improve, evaluate, etc.)
    - Section-aware operations
    - Document state tracking

    Usage:
        agent = ProposalAwareAgent()
        result = await agent.process_query(
            query="Write the objectives section",
            context="",
            proposal_context=session.get_context_for_agent()
        )
    """

    # System prompt extension for proposal context
    PROPOSAL_CONTEXT_TEMPLATE = """
## Current Proposal Context

{proposal_context}

## Proposal Writing Guidelines

When helping with proposals:
1. **Be specific** - Reference the call requirements and evaluation criteria
2. **Be structured** - Follow EU proposal conventions (clear objectives, methodology, etc.)
3. **Be measurable** - Include KPIs, metrics, and verifiable outcomes
4. **Be concise** - EU evaluators value clarity over length
5. **Use tool results** - Incorporate insights from similar projects and budget benchmarks

When generating content for a section:
- Focus on the SPECIFIC section (e.g., objectives, methodology)
- Match the expected structure for that section type
- Aim for impactful, evaluator-friendly language
- Reference the call's expected outcomes

When the user asks to "write" or "generate" a section:
- Use generate_section_draft tool
- Then show the generated content in your response

When the user asks to "improve" or "enhance" content:
- Use improve_section tool
- Explain what was improved

When the user asks to "evaluate" or "score" a section:
- Use evaluate_section tool
- Provide the score and detailed feedback
"""

    def __init__(self, max_iterations: int = 5, session_manager=None):
        """
        Initialize the proposal-aware agent.

        Args:
            max_iterations: Maximum reasoning iterations
            session_manager: Optional ProposalSessionManager for state updates
        """
        super().__init__(max_iterations=max_iterations)
        self.session_manager = session_manager
        self._init_proposal_tools()
        logger.info(
            f"📝 ProposalAwareAgent initialized with {len(self.tools)} tools "
            f"(including proposal tools)"
        )

    def _init_proposal_tools(self):
        """Initialize proposal-specific tools."""

        # Section draft generation
        self.register_tool(
            Tool(
                name="generate_section_draft",
                description=(
                    "Generate AI draft content for a proposal section based on "
                    "call requirements and similar funded projects."
                ),
                category=ToolCategory.DOCUMENTS,
                parameters={
                    "section_id": "Section ID (e.g., 'excellence.objectives', 'impact.pathways')",
                    "call_id": "The funding call identifier",
                    "guidance": "Optional: Specific guidance for content generation",
                    "word_target": "Optional: Target word count (default: 500)",
                    "style": "Optional: Writing style ('formal', 'technical', 'accessible')",
                },
                examples=[
                    (
                        "generate_section_draft(section_id='excellence.objectives', "
                        "call_id='HORIZON-CL5-2025-01')"
                    ),
                    (
                        "generate_section_draft(section_id='impact.pathways', "
                        "call_id='HORIZON-CL4-2025-02', word_target=800)"
                    ),
                ],
            )
        )

        # Section improvement
        self.register_tool(
            Tool(
                name="improve_section",
                description=(
                    "Improve existing section content for clarity, impact, and "
                    "compliance with EU evaluation criteria."
                ),
                category=ToolCategory.DOCUMENTS,
                parameters={
                    "section_id": "Section ID to improve",
                    "focus_areas": (
                        "Optional: Areas to focus on "
                        "('clarity', 'impact', 'structure', 'terminology', 'all')"
                    ),
                    "preserve_length": "Optional: Keep similar word count (default: True)",
                },
                examples=[
                    "improve_section(section_id='excellence.methodology', focus_areas='impact')",
                    (
                        "improve_section(section_id='implementation.consortium', "
                        "focus_areas='structure')"
                    ),
                ],
            )
        )

        # Section rewriting
        self.register_tool(
            Tool(
                name="rewrite_section",
                description="Completely rewrite a section with a specific style or approach.",
                category=ToolCategory.DOCUMENTS,
                parameters={
                    "section_id": "Section ID to rewrite",
                    "style": (
                        "Writing style: 'concise', 'impactful', 'eu_evaluator_friendly', "
                        "'technical', 'accessible'"
                    ),
                    "tone": "Optional: Tone adjustment ('confident', 'measured', 'ambitious')",
                },
                examples=[
                    (
                        "rewrite_section(section_id='excellence.objectives', "
                        "style='eu_evaluator_friendly')"
                    ),
                    (
                        "rewrite_section(section_id='impact.dissemination', "
                        "style='impactful', tone='confident')"
                    ),
                ],
            )
        )

        # Section evaluation (EU evaluator simulation)
        self.register_tool(
            Tool(
                name="evaluate_section",
                description=(
                    "Simulate EU evaluator scoring (0-5 scale) with detailed feedback "
                    "on strengths and weaknesses."
                ),
                category=ToolCategory.VALIDATION,
                parameters={
                    "section_id": "Section ID to evaluate",
                    "evaluation_type": "Optional: 'quick' (fast) or 'detailed' (comprehensive)",
                },
                examples=[
                    "evaluate_section(section_id='excellence.methodology')",
                    "evaluate_section(section_id='impact.pathways', evaluation_type='detailed')",
                ],
            )
        )

        # Gap analysis
        self.register_tool(
            Tool(
                name="analyze_gaps",
                description=(
                    "Identify gaps in a section and suggest specific fixes with effort estimates."
                ),
                category=ToolCategory.VALIDATION,
                parameters={
                    "section_id": "Section ID to analyze",
                    "include_fixes": "Optional: Include suggested fixes (default: True)",
                },
                examples=[
                    "analyze_gaps(section_id='excellence.beyond_sota')",
                    "analyze_gaps(section_id='implementation.work_plan', include_fixes=True)",
                ],
            )
        )

        # Compliance check
        self.register_tool(
            Tool(
                name="check_compliance",
                description=(
                    "Check section or full proposal compliance with call requirements and EU rules."
                ),
                category=ToolCategory.VALIDATION,
                parameters={
                    "section_id": "Optional: Specific section (or 'all' for full proposal)",
                    "check_type": "Optional: 'mandatory', 'recommended', or 'all'",
                },
                examples=[
                    "check_compliance(section_id='all')",
                    (
                        "check_compliance(section_id='implementation.consortium', "
                        "check_type='mandatory')"
                    ),
                ],
            )
        )

        # Get inline suggestions
        self.register_tool(
            Tool(
                name="get_suggestions",
                description=(
                    "Get inline text suggestions for grammar, clarity, terminology, "
                    "and EU-specific language."
                ),
                category=ToolCategory.DOCUMENTS,
                parameters={
                    "section_id": "Section ID to get suggestions for",
                    "suggestion_types": (
                        "Optional: Types to include "
                        "('grammar', 'clarity', 'terminology', 'impact', 'all')"
                    ),
                },
                examples=[
                    "get_suggestions(section_id='excellence.objectives')",
                    "get_suggestions(section_id='impact.pathways', suggestion_types='terminology')",
                ],
            )
        )

        # Section navigation / focus
        self.register_tool(
            Tool(
                name="focus_section",
                description=(
                    "Navigate to and focus on a specific section. "
                    "Updates the active section in the UI."
                ),
                category=ToolCategory.DOCUMENTS,
                parameters={"section_id": "Section ID to focus on"},
                examples=[
                    "focus_section(section_id='excellence.objectives')",
                    "focus_section(section_id='impact.dissemination')",
                ],
            )
        )

        # Document overview
        self.register_tool(
            Tool(
                name="get_document_overview",
                description=(
                    "Get a summary of the current proposal state: sections, "
                    "word counts, scores, and gaps."
                ),
                category=ToolCategory.DOCUMENTS,
                parameters={},
                examples=["get_document_overview()"],
            )
        )

    def _build_proposal_prompt(
        self,
        query: str,
        context: str,
        proposal_context: str,
        previous_steps: list[ReasoningStep],
        tool_results: dict[str, Any],
    ) -> str:
        """
        Build the full prompt with proposal context.

        Args:
            query: User query
            context: Conversation context
            proposal_context: Current proposal state
            previous_steps: Previous reasoning steps
            tool_results: Results from previous tool calls

        Returns:
            Full prompt string
        """
        # Build the standard prompt
        selected_knowledge = self._select_knowledge_sections(query, context)
        base_prompt = REASONING_PROMPT.format(
            built_in_knowledge=selected_knowledge,
            tools_description=self._get_tools_description(),
            context=context,
            query=query,
            previous_steps=self._format_previous_steps(previous_steps),
            tool_results=self._format_tool_results(tool_results),
        )

        # Inject proposal context before the current user message
        proposal_section = self.PROPOSAL_CONTEXT_TEMPLATE.format(
            proposal_context=proposal_context or "No active proposal context"
        )

        # Insert proposal context after the main instructions
        parts = base_prompt.split("## Current User Message")
        if len(parts) == 2:
            return parts[0] + proposal_section + "\n## Current User Message" + parts[1]
        else:
            # Fallback: append proposal context
            return base_prompt + "\n\n" + proposal_section

    def _format_previous_steps(self, steps: list[ReasoningStep]) -> str:
        """Format previous reasoning steps for the prompt."""
        if not steps:
            return "None yet"

        formatted = []
        for step in steps:
            tools_str = ", ".join(tc.tool_name for tc in step.tool_calls) or "none"
            formatted.append(
                f"Step {step.step_number}: {step.thought}\n"
                f"  Action: {step.action}\n"
                f"  Tools: {tools_str}\n"
                f"  Observation: {step.observation[:200] if step.observation else 'N/A'}"
            )
        return "\n".join(formatted)

    def _format_tool_results(self, results: dict[str, Any]) -> str:
        """Format tool results for the prompt."""
        if not results:
            return "No tool results yet"

        formatted = []
        for name, result in results.items():
            result_str = str(result)[:1000]  # Truncate long results
            formatted.append(f"**{name}**:\n{result_str}")
        return "\n\n".join(formatted)

    async def process_query(
        self,
        query: str,
        context: str = "",
        conversation_history: list[dict] = None,
        proposal_context: str = "",
        session_id: str = None,
    ) -> dict[str, Any]:
        """
        Process a query with proposal context awareness.

        Args:
            query: User's question or request
            context: Conversation context
            conversation_history: Previous messages
            proposal_context: Current proposal state (from session.get_context_for_agent())
            session_id: Optional session ID for state updates

        Returns:
            Dict with answer, reasoning steps, sources, and any sections affected
        """
        start_time = datetime.now()

        # Try to append call metadata context
        try:
            if self.session_manager and session_id:
                session = await self.session_manager.get_session(session_id)
                if session and session.document and session.document.call_id:
                    from ..call_document_service import CallDocumentService

                    call_doc_service = CallDocumentService(self.session_manager.db_pool)
                    call_metadata = call_doc_service.get_call_metadata(session.document.call_id)
                    if call_metadata:
                        call_context_str = "\n\n### Call Metadata Context\n"
                        for k, v in call_metadata.items():
                            if v and k not in [
                                "raw_api_response",
                                "api_data_url",
                                "eligibility_conditions_html",
                            ]:
                                call_context_str += f"- **{k}**: {v}\n"
                        proposal_context += call_context_str
        except Exception as e:
            logger.warning(f"Could not load call metadata for context: {e}")

        # Store session context for tool execution
        self._current_session_id = session_id
        self._current_proposal_context = proposal_context

        # Initialize plan
        plan = AgentPlan(
            query=query,
            complexity=self._assess_complexity(query),
            required_sources=self._identify_required_sources(query),
        )

        logger.info(f"📝 [ProposalAgent] Query: {query[:50]}... | Complexity: {plan.complexity}")

        # Check if this is a proposal-specific query
        proposal_intent = self._detect_proposal_intent(query)
        if proposal_intent:
            logger.info(f"📝 Detected proposal intent: {proposal_intent}")

        # Start speculative execution
        if self.speculative_executor:
            try:
                await self.speculative_executor.start_speculative_execution(
                    query=query, context=context
                )
            except Exception as e:
                logger.warning(f"Speculative execution failed: {e}")

        # ReAct loop
        iteration = 0
        all_tool_results = {}
        sections_affected = []

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 [ProposalAgent] Iteration {iteration}/{self.max_iterations}")

            # Get next action from LLM with proposal context
            reasoning_result = await self._reason_next_step_with_proposal(
                query=query,
                context=context,
                proposal_context=proposal_context,
                previous_steps=plan.reasoning_steps,
                tool_results=all_tool_results,
            )

            if not reasoning_result:
                logger.warning("Reasoning step failed, using fallback")
                break

            # Create reasoning step
            step = ReasoningStep(
                step_number=iteration,
                thought=reasoning_result.get("thought", ""),
                action=reasoning_result.get("action", "conclude"),
            )

            # Handle different actions
            if step.action == "call_tools":
                tool_calls = reasoning_result.get("tool_calls", [])
                step.tool_calls = await self._execute_tool_calls_with_proposal(tool_calls)

                # Collect results and track affected sections
                for tc in step.tool_calls:
                    if tc.success:
                        all_tool_results[f"{tc.tool_name}_{iteration}"] = tc.result
                        # Track sections affected by this tool
                        if tc.parameters.get("section_id"):
                            sections_affected.append(tc.parameters["section_id"])

                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get("needs_more_info", True)

            elif step.action == "conclude":
                plan.final_answer = reasoning_result.get("conclusion", "")
                plan.confidence = reasoning_result.get("confidence", 0.8)
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            if not step.next_action_needed:
                logger.info(f"✅ [ProposalAgent] Concluded after {iteration} iteration(s)")
                break

        # Build response
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # Cancel unused speculative tasks
        if self.speculative_executor:
            used_tools = {tc.tool_name for step in plan.reasoning_steps for tc in step.tool_calls}
            self.speculative_executor.cancel_unused_speculation(used_tools)

        return {
            "answer": plan.final_answer or self._build_fallback_answer(plan),
            "success": plan.final_answer is not None,
            "reasoning_steps": [
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "tools_called": [tc.tool_name for tc in s.tool_calls],
                    "observation": s.observation[:200] if s.observation else "",
                }
                for s in plan.reasoning_steps
            ],
            "sources_used": list(all_tool_results.keys()),
            "tool_results": all_tool_results,
            "sections_affected": list(set(sections_affected)),
            "complexity": plan.complexity,
            "iterations": iteration,
            "confidence": plan.confidence,
            "total_time_ms": total_time,
            "proposal_intent": proposal_intent,
        }

    async def process_query_streaming(
        self,
        query: str,
        context: str = "",
        conversation_history: list[dict] = None,
        proposal_context: str = "",
        session_id: str = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a query with streaming events.

        Yields events as processing happens, including proposal-specific events:
        - {'type': 'agent_thinking', 'thought': '...'}
        - {'type': 'tool_call', 'tool_name': 'generate_section_draft', ...}
        - {'type': 'section_update', 'section_id': '...', 'content_delta': '...'}
        - {'type': 'agent_complete', 'result': {...}}

        Args:
            query: User's question or request
            context: Conversation context
            conversation_history: Previous messages
            proposal_context: Current proposal state
            session_id: Optional session ID for state updates

        Yields:
            Dict events as processing happens
        """
        start_time = datetime.now()

        # Store session context
        self._current_session_id = session_id
        self._current_proposal_context = proposal_context

        # Initialize plan
        plan = AgentPlan(
            query=query,
            complexity=self._assess_complexity(query),
            required_sources=self._identify_required_sources(query),
        )

        proposal_intent = self._detect_proposal_intent(query)

        # Yield initial status
        yield {
            "type": "status",
            "stage": "processing",
            "message": "Processing proposal request...",
            "proposal_intent": proposal_intent,
        }

        # ReAct loop with streaming
        iteration = 0
        all_tool_results = {}
        sections_affected = []

        while iteration < self.max_iterations:
            iteration += 1

            # Get next action
            reasoning_result = await self._reason_next_step_with_proposal(
                query=query,
                context=context,
                proposal_context=proposal_context,
                previous_steps=plan.reasoning_steps,
                tool_results=all_tool_results,
            )

            if not reasoning_result:
                break

            step = ReasoningStep(
                step_number=iteration,
                thought=reasoning_result.get("thought", ""),
                action=reasoning_result.get("action", "conclude"),
            )

            # Yield thinking event
            yield {
                "type": "agent_thinking",
                "iteration": iteration,
                "thought": step.thought,
                "action": step.action,
            }

            if step.action == "call_tools":
                tool_calls = reasoning_result.get("tool_calls", [])

                # Yield tool call events
                for tc in tool_calls:
                    tool_name = tc.get("tool", "")
                    parameters = tc.get("parameters", {})
                    yield {
                        "type": "tool_call",
                        "iteration": iteration,
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "reasoning": tc.get("reasoning", ""),
                    }

                # Execute tools
                step.tool_calls = await self._execute_tool_calls_with_proposal(tool_calls)

                # Yield tool results and section updates
                for tc in step.tool_calls:
                    result_count = self._count_results(tc.result) if tc.success else 0
                    yield {
                        "type": "tool_result",
                        "tool_name": tc.tool_name,
                        "success": tc.success,
                        "result_count": result_count,
                        "execution_time_ms": tc.execution_time_ms,
                    }

                    if tc.success:
                        all_tool_results[f"{tc.tool_name}_{iteration}"] = tc.result

                        # Yield section update for writing tools
                        section_id = tc.parameters.get("section_id")
                        if section_id and tc.tool_name in (
                            "generate_section_draft",
                            "improve_section",
                            "rewrite_section",
                        ):
                            sections_affected.append(section_id)
                            yield {
                                "type": "section_update",
                                "section_id": section_id,
                                "tool_name": tc.tool_name,
                                "content": (
                                    tc.result.get("content", "")
                                    if isinstance(tc.result, dict)
                                    else str(tc.result)
                                ),
                            }

                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get("needs_more_info", True)

            elif step.action == "conclude":
                plan.final_answer = reasoning_result.get("conclusion", "")
                plan.confidence = reasoning_result.get("confidence", 0.8)
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            if not step.next_action_needed:
                break

        # Yield final result
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        yield {
            "type": "agent_complete",
            "result": {
                "answer": plan.final_answer or self._build_fallback_answer(plan),
                "success": plan.final_answer is not None,
                "sections_affected": list(set(sections_affected)),
                "iterations": iteration,
                "confidence": plan.confidence,
                "total_time_ms": total_time,
                "proposal_intent": proposal_intent,
            },
        }

    async def _reason_next_step_with_proposal(
        self,
        query: str,
        context: str,
        proposal_context: str,
        previous_steps: list[ReasoningStep],
        tool_results: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Get next reasoning step with proposal context.

        Args:
            query: User query
            context: Conversation context
            proposal_context: Proposal state context
            previous_steps: Previous steps
            tool_results: Previous tool results

        Returns:
            Dict with thought, action, tool_calls, etc.
        """
        prompt = self._build_proposal_prompt(
            query=query,
            context=context,
            proposal_context=proposal_context,
            previous_steps=previous_steps,
            tool_results=tool_results,
        )

        try:
            if self.llm:
                response = self.llm.generate_content(prompt)
                response_text = response.text.strip()

                # Parse JSON response
                import json
                import re

                # Extract JSON from markdown code blocks if present
                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
                if json_match:
                    response_text = json_match.group(1)

                return json.loads(response_text)
            else:
                logger.warning("LLM not available for reasoning")
                return None
        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            return None

    async def _execute_tool_calls_with_proposal(self, tool_calls: list[dict]) -> list[ToolCall]:
        """
        Execute tool calls with proposal context awareness.

        Args:
            tool_calls: List of tool call specifications

        Returns:
            List of executed ToolCall objects
        """
        results = []

        for tc_spec in tool_calls:
            tool_name = tc_spec.get("tool", "")
            parameters = tc_spec.get("parameters", {})
            reasoning = tc_spec.get("reasoning", "")

            tc = ToolCall(tool_name=tool_name, parameters=parameters, reasoning=reasoning)

            start_time = datetime.now()

            try:
                # Check if it's a proposal-specific tool
                if tool_name in self._get_proposal_tool_names():
                    result = await self._execute_proposal_tool(tool_name, parameters)
                else:
                    # Use parent's tool execution
                    result = await self._execute_single_tool(tool_name, parameters)

                tc.result = result
                tc.success = True
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                tc.error = str(e)
                tc.success = False

            tc.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            results.append(tc)

        return results

    def _get_proposal_tool_names(self) -> list[str]:
        """Get list of proposal-specific tool names."""
        return [
            "generate_section_draft",
            "improve_section",
            "rewrite_section",
            "evaluate_section",
            "analyze_gaps",
            "check_compliance",
            "get_suggestions",
            "focus_section",
            "get_document_overview",
        ]

    async def _execute_proposal_tool(self, tool_name: str, parameters: dict[str, Any]) -> Any:
        """
        Execute a proposal-specific tool.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Returns:
            Tool result
        """
        try:
            from ..tools.proposal_tools import get_proposal_tool_executor

            executor = get_proposal_tool_executor(session_manager=self.session_manager)
            return await executor.execute_tool(
                tool_name=tool_name,
                parameters=parameters,
                session_id=self._current_session_id,
                proposal_context=self._current_proposal_context,
            )
        except ImportError as e:
            logger.warning(f"Proposal tool executor not available: {e}")
            return {"error": f"Proposal tool executor not available: {e}"}

    def _detect_proposal_intent(self, query: str) -> str | None:
        """
        Detect if the query has a proposal-specific intent.

        Args:
            query: User query

        Returns:
            Intent string or None
        """
        query_lower = query.lower()

        # Writing intents
        if any(kw in query_lower for kw in ["write", "draft", "generate", "create"]):
            if "section" in query_lower or "objectives" in query_lower:
                return "generate_section"

        # Improvement intents
        if any(kw in query_lower for kw in ["improve", "enhance", "better", "strengthen"]):
            return "improve_section"

        # Rewrite intents
        if any(kw in query_lower for kw in ["rewrite", "rephrase", "reformulate"]):
            return "rewrite_section"

        # Evaluation intents
        if any(kw in query_lower for kw in ["evaluate", "score", "assess", "rate"]):
            return "evaluate_section"

        # Gap analysis intents
        if any(kw in query_lower for kw in ["gap", "missing", "what's missing", "lacks"]):
            return "analyze_gaps"

        # Compliance intents
        if any(kw in query_lower for kw in ["compliance", "compliant", "rules", "requirements"]):
            return "check_compliance"

        return None

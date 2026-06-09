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

{document_structure}

{active_section_guidance}

## Proposal Writing Guidelines

You are an expert EU Horizon Europe proposal writer. Your drafts must read as if written
by a senior grant consultant with a >80% success rate. Follow these principles:

1. **Follow the official EU template exactly** — Each section has specific instructions from the
   European Commission. The instructions for the active section are provided above. Follow them precisely.
2. **Write for evaluators** — EU proposals are scored by 3-5 independent experts. They spend ~30min
   per section. Use clear structure, bullet points, bold key terms, and numbered lists.
3. **Be specific and quantifiable** — Include KPIs, TRL levels, person-months, budget figures,
   and concrete metrics. Vague statements score poorly.
4. **Reference the call topic** — Directly address the Expected Outcomes and Scope from the call text.
5. **Use evidence** — Reference similar funded projects, scientific literature, and market data.
6. **Be concise** — Respect page limits. Every sentence must earn its place.

When generating content for a section:
- Follow the OFFICIAL EU INSTRUCTIONS provided in the active section guidance above
- Match the expected structure and cover ALL required points
- Use professional, evaluator-friendly academic language
- Include tables, figures descriptions, and structured lists where the template requires them

When the user asks to "write" or "generate" a section:
- Use generate_section_draft tool
- Then show the generated content in your response

When the user asks to "improve" or "enhance" content:
- Use improve_section tool
- Explain what was improved and why it scores better

When the user asks to "evaluate" or "score" a section:
- Use evaluate_section tool
- Score against the OFFICIAL evaluation criteria for that section
- Provide actionable feedback
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

        # Mark Section Status
        self.register_tool(
            Tool(
                name="mark_section_status",
                description=("Mark a section's progress status (e.g., as 'complete' when done)."),
                category=ToolCategory.DOCUMENTS,
                parameters={
                    "section_id": "Section ID to update",
                    "status": "The new status ('complete', 'in_review', 'draft', 'empty')",
                },
                examples=[
                    "mark_section_status(section_id='excellence.objectives', status='complete')",
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
        Build the full prompt with proposal context and official EU section guidance.

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

        current_date = datetime.now().strftime("%d %B %Y")
        current_year = datetime.now().year
        base_prompt = REASONING_PROMPT.format(
            built_in_knowledge=selected_knowledge,
            tools_description=self._get_tools_description(),
            context=context,
            query=query,
            previous_steps=self._format_previous_steps(previous_steps),
            tool_results=self._format_tool_results(tool_results),
            current_date=current_date,
            current_year=current_year,
        )

        # Resolve document structure and active section guidance from templates
        document_structure = ""
        active_section_guidance = ""
        try:
            from ..templates.he_templates import (
                get_all_sections_overview,
                get_full_section_guidance,
            )

            proposal_type = self._extract_proposal_type(proposal_context)
            document_structure = get_all_sections_overview(proposal_type)

            # Determine active section from the proposal context or the user query
            active_section_id = self._detect_active_section(query, proposal_context)
            if active_section_id:
                active_section_guidance = get_full_section_guidance(
                    proposal_type, active_section_id
                )
                if active_section_guidance:
                    logger.info(f"📋 Injecting EU guidance for section: {active_section_id}")
        except Exception as e:
            logger.warning(f"Could not load template guidance: {e}")

        # Inject proposal context before the current user message
        proposal_section = self.PROPOSAL_CONTEXT_TEMPLATE.format(
            proposal_context=proposal_context or "No active proposal context",
            document_structure=document_structure,
            active_section_guidance=active_section_guidance,
        )

        # Insert proposal context after the main instructions
        parts = base_prompt.split("## Current User Message")
        if len(parts) == 2:
            return parts[0] + proposal_section + "\n## Current User Message" + parts[1]
        else:
            # Fallback: append proposal context
            return base_prompt + "\n\n" + proposal_section

    def _extract_proposal_type(self, proposal_context: str) -> str:
        """Extract proposal type from the proposal context string."""
        for line in proposal_context.split("\n"):
            if "**Type:**" in line:
                # e.g. "**Type:** RIA"
                return line.split("**Type:**")[-1].strip()
        return "RIA"  # Default

    def _detect_active_section(self, query: str, proposal_context: str) -> str | None:
        """
        Detect which section the user is working on from the active section context
        or by matching keywords in the user query dynamically from the template.
        """
        # 1. Check if the proposal context has an explicit active section
        for line in proposal_context.split("\n"):
            if "### Active Section:" in line:
                break

        # 2. Try to detect from the user's query dynamically based on active template
        query_lower = query.lower()
        proposal_type = self._extract_proposal_type(proposal_context)

        try:
            from ..templates.he_templates import get_template_by_type

            template = get_template_by_type(proposal_type)
        except Exception:
            template = {}

        best_match = None
        best_count = 0

        for section_id, data in template.items():
            keywords = data.get("keywords", [])
            # Also extract lowercase words from the section name
            name_words = [
                w.strip(".,()").lower() for w in data.get("name", "").split() if len(w) > 2
            ]
            all_kws = set(keywords + name_words + [section_id])

            match_count = sum(1 for kw in all_kws if kw in query_lower)
            if match_count > best_count:
                best_count = match_count
                best_match = section_id

        return best_match

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
                        # Defensive: check both parameters and result for section_id
                        section_id = tc.parameters.get("section_id")
                        if not section_id and isinstance(tc.result, dict):
                            section_id = tc.result.get("section_id")
                        if section_id:
                            sections_affected.append(section_id)

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

        # Use proposal-specific response formatting
        sections_affected_unique = list(set(sections_affected))
        answer = plan.final_answer or self._build_proposal_response(
            plan, all_tool_results, sections_affected_unique, proposal_intent
        )

        return {
            "answer": answer,
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
            "sections_affected": sections_affected_unique,
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
                        "display_name": self._get_tool_display_name(tool_name),
                        "parameters": parameters,
                        "reasoning": tc.get("reasoning", ""),
                    }

                # Execute tools
                step.tool_calls = await self._execute_tool_calls_with_proposal(tool_calls)

                # Phase 1: Yield tool results
                # Phase 2: Yield section updates (separated to avoid ordering issues)
                pending_section_updates = []

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

                        # Collect section updates for writing tools
                        if tc.tool_name in (
                            "generate_section_draft",
                            "improve_section",
                            "rewrite_section",
                        ):
                            # Defensive: extract section_id from parameters OR result
                            section_id = tc.parameters.get("section_id")
                            if not section_id and isinstance(tc.result, dict):
                                section_id = tc.result.get("section_id")

                            if section_id:
                                content = (
                                    tc.result.get("content", "")
                                    if isinstance(tc.result, dict)
                                    else str(tc.result)
                                )
                                pending_section_updates.append(
                                    {
                                        "section_id": section_id,
                                        "tool_name": tc.tool_name,
                                        "content": content,
                                    }
                                )
                                logger.info(
                                    f"📝 [ProposalAgent] Section update queued: "
                                    f"{section_id} ({len(content)} chars) "
                                    f"via {tc.tool_name}"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ [ProposalAgent] Writing tool {tc.tool_name} "
                                    f"succeeded but no section_id found in "
                                    f"parameters={tc.parameters} or "
                                    f"result keys={list(tc.result.keys()) if isinstance(tc.result, dict) else 'N/A'}"
                                )

                # Phase 2: Emit all section updates after tool results
                for su in pending_section_updates:
                    sections_affected.append(su["section_id"])
                    yield {
                        "type": "section_update",
                        "section_id": su["section_id"],
                        "tool_name": su["tool_name"],
                        "content": su["content"],
                    }
                    logger.info(f"📝 [ProposalAgent] Section update emitted: {su['section_id']}")

                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get("needs_more_info", True)

            elif step.action == "conclude":
                plan.final_answer = reasoning_result.get("conclusion", "")
                plan.confidence = reasoning_result.get("confidence", 0.8)
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            if not step.next_action_needed:
                break

        # Yield final result with proposal-specific response formatting
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        sections_affected_unique = list(set(sections_affected))

        # Use proposal-specific response instead of generic fallback
        answer = plan.final_answer or self._build_proposal_response(
            plan, all_tool_results, sections_affected_unique, proposal_intent
        )

        yield {
            "type": "agent_complete",
            "result": {
                "answer": answer,
                "success": plan.final_answer is not None,
                "sections_affected": sections_affected_unique,
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

        # Writing intents — broader matching for proposal section generation
        writing_keywords = ["write", "draft", "generate", "create", "compose", "prepare"]
        section_keywords = [
            "section",
            "objectives",
            "methodology",
            "ambition",
            "impact",
            "dissemination",
            "work plan",
            "consortium",
            "budget",
            "excellence",
            "implementation",
            "proposal",
            "next logical",
            "state of the art",
            "beyond",
            "pathways",
        ]
        if any(kw in query_lower for kw in writing_keywords):
            if any(sk in query_lower for sk in section_keywords):
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

    # =========================================================================
    # Proposal-Specific Response Formatting
    # =========================================================================

    def _get_tool_display_name(self, tool_name: str) -> str:
        """Get a human-readable display name for a tool."""
        display_names = {
            "find_experienced_partners": "Partner Discovery",
            "get_project_details": "Project Details",
            "search_projects": "Project Search",
            "get_similar_funded_projects": "Similar Projects",
            "get_project_partners": "Project Partners",
            "get_organization_stats": "Organization Stats",
            "find_organization_projects": "Organization Projects",
            "get_collaboration_network": "Collaboration Network",
            "search_funding_calls": "Funding Calls",
            "get_call_details": "Call Details",
            "get_programme_statistics": "Programme Statistics",
            "get_country_statistics": "Country Statistics",
            "compare_programmes": "Programme Comparison",
            "search_documents": "Document Search",
            "calculate_budget": "Budget Calculator",
            "generate_timeline": "Timeline Generator",
            "get_budget_benchmark": "Budget Benchmark",
            "get_consortium_patterns": "Consortium Patterns",
            "analyze_call_history": "Call History Analysis",
            "check_erasmus_eligibility": "Erasmus+ Eligibility",
            "calculate_erasmus_budget": "Erasmus+ Budget",
            "search_erasmus_templates": "Erasmus+ Templates",
            "check_creative_europe_eligibility": "Creative Europe Eligibility",
            "calculate_creative_europe_budget": "Creative Europe Budget",
            "search_creative_europe_templates": "Creative Europe Templates",
            "check_eu4health_eligibility": "EU4Health Eligibility",
            "search_eu4health_templates": "EU4Health Templates",
            "check_digital_europe_eligibility": "Digital Europe Eligibility",
            "check_life_eligibility": "LIFE Eligibility",
            "search_life_templates": "LIFE Templates",
            "search_all_programmes": "All Programmes Search",
            "recommend_programmes": "Programme Recommendations",
            "get_programme_info": "Programme Information",
            "score_proposal_section": "Proposal Section Scoring",
            "score_full_proposal": "Full Proposal Scoring",
            "quick_quality_check": "Quick Quality Check",
            "validate_budget": "Budget Validation",
            # Proposal-specific tools
            "generate_section_draft": "Generate Section Draft",
            "improve_section": "Improve Section",
            "rewrite_section": "Rewrite Section",
            "evaluate_section": "Evaluate Section",
            "analyze_gaps": "Analyze Gaps",
            "get_document_overview": "Document Overview",
            "focus_section": "Focus Section",
            "mark_section_status": "Mark Section Status",
        }
        return display_names.get(tool_name, tool_name.replace("_", " ").title())

    def _build_proposal_response(
        self,
        plan: AgentPlan,
        all_tool_results: dict[str, Any],
        sections_affected: list[str],
        proposal_intent: str | None,
    ) -> str:
        """
        Build a proposal-specific response that summarizes what was done.

        Unlike the generic _build_fallback_answer (which dumps raw project tables
        and formatted research), this produces a concise, actionable summary
        appropriate for the proposal writing context.

        Args:
            plan: The agent's execution plan
            all_tool_results: All tool results collected during execution
            sections_affected: List of section IDs that were updated
            proposal_intent: Detected proposal intent

        Returns:
            A concise, proposal-focused response string
        """
        parts = []

        # 1. Summarize sections that were drafted/updated
        if sections_affected:
            section_names = []
            for sid in sections_affected:
                # Convert "excellence.objectives" → "Objectives (Excellence)"
                section_parts = sid.split(".")
                if len(section_parts) == 2:
                    category = section_parts[0].replace("_", " ").title()
                    name = section_parts[1].replace("_", " ").title()
                    section_names.append(f"**{name}** ({category})")
                else:
                    section_names.append(f"**{sid.replace('_', ' ').title()}**")

            action_verb = self._get_action_verb(proposal_intent)
            if len(section_names) == 1:
                parts.append(f"I've {action_verb} the {section_names[0]} section.")
            else:
                listing = ", ".join(section_names[:-1]) + f" and {section_names[-1]}"
                parts.append(f"I've {action_verb} the following sections: {listing}.")

        # 2. Summarize what sources were used (briefly)
        sources_summary = self._summarize_sources_used(all_tool_results)
        if sources_summary:
            parts.append(f"\n**Sources used:** {sources_summary}")

        # 3. Summarize section content highlights
        content_highlights = self._extract_content_highlights(all_tool_results)
        if content_highlights:
            parts.append("\n**What was covered:**")
            for highlight in content_highlights:
                parts.append(f"- {highlight}")

        # 4. Actionable next steps
        next_steps = self._suggest_next_steps(sections_affected, proposal_intent)
        if next_steps:
            parts.append("\n**Suggested next steps:**")
            for step in next_steps:
                parts.append(f"- {step}")

        if parts:
            return "\n".join(parts)

        # Fallback if nothing meaningful was collected
        return self._build_minimal_proposal_fallback(plan)

    def _get_action_verb(self, proposal_intent: str | None) -> str:
        """Get the appropriate action verb based on intent."""
        verbs = {
            "generate_section": "drafted",
            "improve_section": "improved",
            "rewrite_section": "rewritten",
            "evaluate_section": "evaluated",
            "analyze_gaps": "analyzed gaps in",
            "check_compliance": "checked compliance for",
        }
        return verbs.get(proposal_intent, "updated")

    def _summarize_sources_used(self, all_tool_results: dict[str, Any]) -> str:
        """Create a brief summary of sources consulted."""
        source_parts = []

        for _key, result in all_tool_results.items():
            if not isinstance(result, dict):
                continue

            # Call details
            if "call_id" in result or "topic_code" in result:
                call_id = result.get("call_id") or result.get("topic_code", "")
                title = result.get("title", "")
                if call_id:
                    source_parts.append(
                        f"Call details for {call_id}" + (f" ({title})" if title else "")
                    )

            # Similar projects
            elif "similar_projects" in result:
                count = len(result.get("similar_projects", []))
                matches = result.get("matches_found", count)
                if matches > 0:
                    source_parts.append(f"{matches} similar funded projects")

            # Project details
            elif "acronym" in result and "partners" in result:
                acronym = result.get("acronym", "")
                partner_count = len(result.get("partners", []))
                if acronym:
                    source_parts.append(f"{acronym} project details ({partner_count} partners)")

        if not source_parts:
            return ""
        return ", ".join(source_parts[:4])  # Limit to 4 sources

    def _extract_content_highlights(self, all_tool_results: dict[str, Any]) -> list[str]:
        """Extract brief highlights from generated/updated content."""
        highlights = []

        for _key, result in all_tool_results.items():
            if not isinstance(result, dict):
                continue

            # Content from section drafts
            if "content" in result and "section_id" in result:
                content = result.get("content", "")
                section_id = result.get("section_id", "")
                word_count = len(content.split()) if content else 0

                if word_count > 0:
                    section_name = (
                        section_id.split(".")[-1].replace("_", " ").title()
                        if "." in section_id
                        else section_id.replace("_", " ").title()
                    )
                    highlights.append(f"{section_name}: {word_count} words generated")

        return highlights[:5]  # Limit highlights

    def _suggest_next_steps(
        self, sections_affected: list[str], proposal_intent: str | None
    ) -> list[str]:
        """Suggest next steps based on what was done."""
        steps = []

        if proposal_intent == "generate_section":
            steps.append(
                "Review the generated content and refine it to match your project's specifics"
            )
            steps.append("Replace placeholder text (marked with [...]) with your concrete details")
            if sections_affected:
                # Suggest the next logical section using the actual template dynamically
                try:
                    proposal_context = getattr(self, "_current_proposal_context", "")
                    proposal_type = self._extract_proposal_type(proposal_context)
                    from ..templates.he_templates import get_template_by_type

                    template = get_template_by_type(proposal_type)
                    section_order = list(template.keys())
                except Exception:
                    section_order = []
                last_section = sections_affected[-1] if sections_affected else ""
                try:
                    idx = section_order.index(last_section)
                    if idx + 1 < len(section_order):
                        next_section = section_order[idx + 1]
                        next_name = (
                            template[next_section]["name"]
                            if next_section in template
                            else next_section
                        )
                        steps.append(f"Ask me to draft the next section: **{next_name}**")
                except ValueError:
                    pass

        elif proposal_intent == "improve_section":
            steps.append("Compare the improved version with the original")
            steps.append("Consider running an evaluation to check the score")

        elif proposal_intent == "evaluate_section":
            steps.append("Address the identified weaknesses")
            steps.append("Ask me to improve specific areas")

        return steps[:3]  # Limit to 3 suggestions

    def _build_minimal_proposal_fallback(self, plan: AgentPlan) -> str:
        """Build a minimal fallback when no structured response is available."""
        if plan.reasoning_steps:
            # Use the last thought as context
            last_thought = plan.reasoning_steps[-1].thought
            if last_thought:
                return (
                    f"I processed your request. Here's what I found:\n\n"
                    f"{last_thought}\n\n"
                    f"Let me know if you'd like me to take any specific action."
                )

        return (
            "I've processed your request. " "Please let me know what you'd like me to work on next."
        )

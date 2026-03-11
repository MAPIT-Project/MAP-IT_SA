# isort: skip_file
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

import asyncio
import json
import logging
import os
import re
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Query preprocessing utilities (special chars, language detection, long query handling)
from .query_preprocessing import (  # noqa: F401
    LanguageDetectionResult,
    LongQueryResult,
    SpecialCharResult,
    TranslationResult,
    normalize_special_characters,
    preprocess_long_query,
    preprocess_non_english_query,
)

# Prompt constants (BUILT_IN_KNOWLEDGE, REASONING_PROMPT)
from .prompts import BUILT_IN_KNOWLEDGE, REASONING_PROMPT

# Mixins extracted for maintainability
from .conclusion_builders import ConclusionBuildersMixin
from .context_manager import ContextLimits, ContextWindowManager, _context_manager  # noqa: F401
from .guidance_generators import GuidanceGeneratorsMixin
from .query_detectors import QueryDetectorsMixin
from .response_synthesizer import ResponseSynthesizerMixin
from .tool_executors import ToolExecutorsMixin
from .tool_registry import (  # noqa: F401
    AgentPlan,
    ReasoningStep,
    Tool,
    ToolCall,
    ToolCategory,
    ToolRegistryMixin,
)


class ToolAwareAgent(
    ToolRegistryMixin,
    ToolExecutorsMixin,
    ResponseSynthesizerMixin,
    QueryDetectorsMixin,
    GuidanceGeneratorsMixin,
    ConclusionBuildersMixin,
):
    """
    ReAct-style agent that reasons about and uses multiple tools.

    Key capabilities:
    - Analyzes query complexity to determine tool needs
    - Calls multiple tools in parallel when independent
    - Sequences tool calls when results depend on each other
    - Compares and contrasts results from different sources
    - Iteratively refines by calling more tools based on findings
    """

    def __init__(self, max_iterations: int = 5, enable_quality_analysis: bool = True):
        """Initialize the tool-aware agent.

        Args:
            max_iterations: Maximum number of reasoning iterations.
            enable_quality_analysis: Whether to analyze response quality (default: True).
        """
        self.max_iterations = max_iterations
        self.enable_quality_analysis = enable_quality_analysis
        self._conversation_id: int | None = None
        self._redis_client = None
        self.tools: dict[str, Tool] = {}
        self._init_tools()
        self._init_llm()
        self._init_cache()
        self._init_analytics()
        self._init_speculative_executor()
        self._init_quality_analyzer()

        logger.info(f"🛠️ ToolAwareAgent initialized with {len(self.tools)} tools")

    def _init_cache(self):
        """Initialize query plan cache."""
        try:
            from ..cache.query_plan_cache import QueryPlanCache
            from ..memory.memory_service import MemoryService

            memory = MemoryService()
            self._redis_client = memory.redis_client
            self.plan_cache = QueryPlanCache(self._redis_client)
            logger.info("✅ Query plan cache initialized")
        except Exception as e:
            logger.warning(f"⚠️ Query plan cache unavailable: {e}")
            self.plan_cache = None

    def _init_analytics(self):
        """Initialize tool analytics for usage tracking."""
        try:
            from ..analytics.tool_analytics_service import get_analytics_service

            self.analytics = get_analytics_service()
            logger.info("✅ Tool analytics initialized")
        except Exception as e:
            logger.warning(f"⚠️ Tool analytics unavailable: {e}")
            self.analytics = None

    def _init_speculative_executor(self):
        """Initialize speculative tool executor for parallel execution."""
        try:
            from ..cache.speculative_executor import SpeculativeExecutor

            # Create a wrapper that calls our tool execution method
            async def tool_executor(tool_name: str, params: dict):
                return await self._execute_single_tool(tool_name, params)

            self.speculative_executor = SpeculativeExecutor(tool_executor)
            logger.info("✅ Speculative executor initialized")
        except Exception as e:
            logger.warning(f"⚠️ Speculative executor unavailable: {e}")
            self.speculative_executor = None

    def _init_quality_analyzer(self):
        """Initialize response quality analyzer for monitoring and validation."""
        if not self.enable_quality_analysis:
            self.quality_analyzer = None
            logger.info("📊 Quality analysis disabled")
            return

        try:
            from ..quality.response_quality_analyzer import ResponseQualityAnalyzer

            self.quality_analyzer = ResponseQualityAnalyzer()
            logger.info("✅ Response quality analyzer initialized")
        except Exception as e:
            logger.warning(f"⚠️ Response quality analyzer unavailable: {e}")
            self.quality_analyzer = None

    def _analyze_response_quality(
        self, query: str, answer: str, tool_results: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Analyze the quality of a generated response.

        Args:
            query: The user's original query.
            answer: The generated answer text.
            tool_results: Results from tool executions.

        Returns:
            Quality analysis dict or None if analyzer unavailable.
        """
        if not self.quality_analyzer:
            return None

        try:
            # Analyze the response
            analysis = self.quality_analyzer.analyze(
                query=query, response=answer, tool_results=tool_results
            )

            # Log quality metrics for monitoring
            if analysis.category.value in ("deflection", "empty"):
                logger.warning(
                    f"⚠️ Response quality issue detected: "
                    f"category={analysis.category.value}, score={analysis.score}, "
                    f"deflections={len(analysis.deflection_phrases_found)}"
                )
            else:
                logger.info(
                    f"📊 Response quality: score={analysis.score}, "
                    f"category={analysis.category.value}, "
                    f"confidence={analysis.confidence:.2f}"
                )

            return analysis.to_dict()

        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")
            return None

    def _init_llm(self):
        """Initialize LLMs for reasoning with smart model routing.

        Initializes both a fast model (flash) and a powerful model (pro).
        Smart routing selects the pro model for complex queries (comparisons,
        analysis, multi-source) and the flash model for simple queries.
        """

        self.llm_provider = os.getenv("DEFAULT_AI_PROVIDER", "gemini")
        self.smart_model_routing = os.getenv("SMART_MODEL_ROUTING", "true").lower() == "true"

        if self.llm_provider == "gemini":
            try:
                import google.generativeai as genai

                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

                # Flash model (fast, cost-effective) — used for simple queries
                flash_model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
                self.llm_flash = genai.GenerativeModel(flash_model_name)
                self.flash_model_name = flash_model_name

                # Pro model (powerful, higher quality) — used for complex queries
                pro_model_name = os.getenv("GEMINI_PRO_MODEL", "gemini-3.1-pro-preview")
                self.llm_pro = genai.GenerativeModel(pro_model_name)
                self.pro_model_name = pro_model_name

                # Default active model is flash (switched per-query based on complexity)
                self.llm = self.llm_flash
                self._active_model_name = flash_model_name

                if self.smart_model_routing:
                    logger.info(
                        f"🧠 Smart model routing enabled: "
                        f"flash={flash_model_name}, pro={pro_model_name}"
                    )
                else:
                    logger.info(
                        f"🧠 ToolAwareAgent using model: {flash_model_name} (routing disabled)"
                    )
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
                self.llm = None
                self.llm_flash = None
                self.llm_pro = None
        else:
            self.llm = None
            self.llm_flash = None
            self.llm_pro = None
            logger.warning("LLM not configured for ToolAwareAgent")

    def _select_model_for_query(self, complexity: str, query: str) -> None:
        """Select the appropriate model based on query complexity.

        Switches self.llm to either flash or pro model for the current query.
        Also stores complexity so _reason_next_step can skip pre-routing for complex queries.
        """
        self._current_complexity = complexity

        if not self.smart_model_routing or not self.llm_pro:
            return

        use_pro = complexity in ("comparison", "analysis", "multi_source")

        if use_pro:
            self.llm = self.llm_pro
            self._active_model_name = self.pro_model_name
            logger.info(f"🚀 Using PRO model ({self.pro_model_name}) for {complexity} query")
        else:
            self.llm = self.llm_flash
            self._active_model_name = self.flash_model_name
            logger.info(f"⚡ Using FLASH model ({self.flash_model_name}) for {complexity} query")

    # _init_tools, register_tool, _get_tools_description are provided by ToolRegistryMixin.

    # ── Shared preprocessing for process_query and process_query_streaming ──

    def _preprocess_query(
        self, query: str, context: str
    ) -> tuple[str, str, dict | None, dict | None, LongQueryResult, str]:
        """Preprocess a query: normalize special chars, translate, condense long queries.

        Returns:
            Tuple of (processed_query, updated_context, special_char_metadata,
                       translation_metadata, long_query_result, original_query)
        """
        # Normalize special characters (CO₂→CO2, &→and, smart quotes, etc.)
        special_char_result = normalize_special_characters(query)
        original_query = query
        special_char_metadata = None
        if special_char_result.was_normalized:
            logger.info(
                f"🔤 Normalized special characters in query: "
                f"{', '.join(special_char_result.normalizations_applied)}"
            )
            query = special_char_result.normalized_query
            special_char_metadata = {
                "original_had_special_chars": True,
                "normalizations_applied": special_char_result.normalizations_applied,
            }

        # Handle non-English queries (detect and translate if needed)
        translated_query, translation_metadata = preprocess_non_english_query(query, self.llm)
        if translation_metadata and translation_metadata.get("was_translated"):
            logger.info(
                f"🌐 Translated query from {translation_metadata['original_language_name']}: "
                f"'{query}' → '{translated_query}'"
            )
            query = translated_query

        # Preprocess long queries (500+ characters) to extract key intent
        long_query_result = preprocess_long_query(query, self.llm)
        if long_query_result.was_processed:
            logger.info(
                f"📝 Long query ({long_query_result.query_length} chars) → "
                f"Processed ({len(long_query_result.processed_query)} chars)"
            )
            # Use processed query for reasoning, but keep original for context
            query = long_query_result.processed_query
            # Add original query to context so agent knows full details
            if context:
                context = f"{context}\n\n**Original detailed query:** {original_query}"
            else:
                context = f"**Original detailed query:** {original_query}"

        return (
            query,
            context,
            special_char_metadata,
            translation_metadata,
            long_query_result,
            original_query,
        )

    def _init_plan_and_model(self, query: str) -> AgentPlan:
        """Initialize plan and select model for the query."""
        plan = AgentPlan(
            query=query,
            complexity=self._assess_complexity(query),
            required_sources=self._identify_required_sources(query),
        )
        self._select_model_for_query(plan.complexity, query)
        logger.info(
            f"🧠 Query complexity: {plan.complexity}, sources needed: {plan.required_sources}, "
            f"model: {getattr(self, '_active_model_name', 'unknown')}"
        )
        return plan

    async def _start_speculation(self, query: str, context: str) -> dict:
        """Start speculative execution for likely-needed tools."""
        speculative_tasks = {}
        if self.speculative_executor:
            try:
                speculative_tasks = await self.speculative_executor.start_speculative_execution(
                    query=query, context=context
                )
                if speculative_tasks:
                    logger.info(
                        f"🔮 Started speculative execution for {len(speculative_tasks)} tool(s)"
                    )
            except Exception as e:
                logger.warning(f"Speculative execution failed to start: {e}")
        return speculative_tasks

    def _handle_call_tools_action(
        self,
        step: ReasoningStep,
        reasoning_result: dict,
        all_tool_results: dict,
        tool_results_this_step: dict,
        plan: AgentPlan,
        query: str,
        iteration: int,
    ) -> bool:
        """Process results after call_tools execution. Returns True if loop should break."""
        # Collect results
        for idx, tc in enumerate(step.tool_calls):
            if tc.success:
                all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result
                tool_results_this_step[tc.tool_name] = tc.result

        # Auto-promote to formatted output ONLY for semantic project searches
        # or pagination results. Don't promote generic keyword "projects" results
        # — those may come from org stats, follow-ups, etc. that need LLM synthesis.
        has_semantic_projects = any(
            isinstance(r, dict) and ("similar_projects" in r or "rendered_content" in r)
            for r in tool_results_this_step.values()
        )
        if has_semantic_projects:
            formatted = self._synthesize_from_results(query, tool_results_this_step)
            if formatted and len(formatted) > 200:
                plan.final_answer = formatted
                plan.confidence = 0.90
                step.observation = (
                    f"Executed {len(step.tool_calls)} tool(s) — " f"auto-formatted project results"
                )
                step.next_action_needed = False
                plan.reasoning_steps.append(step)
                return True  # break the loop

        step.observation = self._summarize_tool_results(step.tool_calls)
        step.next_action_needed = reasoning_result.get("needs_more_info", True)

        # Force another iteration when multiple tools were called successfully
        # so the LLM can cross-analyze combined results (e.g., compare partner lists)
        successful_calls = [tc for tc in step.tool_calls if tc.success]
        if len(successful_calls) >= 2 and not step.next_action_needed:
            logger.info(
                f"⚡ Forcing cross-analysis iteration: {len(successful_calls)} tools "
                f"returned results — LLM needs to synthesize combined data"
            )
            step.next_action_needed = True

        return False  # continue the loop

    def _handle_format_action(
        self,
        step: ReasoningStep,
        all_tool_results: dict,
        plan: AgentPlan,
        query: str,
        iteration: int,
    ) -> None:
        """Handle call_tools_and_format action — format results without LLM."""
        tool_results_for_format = {}
        for idx, tc in enumerate(step.tool_calls):
            if tc.success:
                all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result
                tool_results_for_format[tc.tool_name] = tc.result

        formatted_response = self._synthesize_from_results(query, tool_results_for_format)
        plan.final_answer = formatted_response
        plan.confidence = 0.90
        step.observation = f"Executed {len(step.tool_calls)} tool(s) and formatted results"
        step.next_action_needed = False

    def _handle_niche_guidance_action(
        self,
        step: ReasoningStep,
        reasoning_result: dict,
        all_tool_results: dict,
        plan: AgentPlan,
        query: str,
        iteration: int,
    ) -> None:
        """Handle call_tools_with_niche_guidance action."""
        tool_results_for_format = {}
        calls_found = 0
        projects_found = 0
        for idx, tc in enumerate(step.tool_calls):
            if tc.success:
                all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result
                tool_results_for_format[tc.tool_name] = tc.result
                if "calls_found" in tc.result:
                    calls_found = tc.result.get("calls_found", 0)
                if "projects_found" in tc.result:
                    projects_found = tc.result.get("projects_found", 0)
                elif "similar_projects" in tc.result:
                    projects_found = len(tc.result.get("similar_projects", []))

        formatted_response = self._synthesize_from_results(query, tool_results_for_format)
        niche_context = reasoning_result.get("niche_query_context", {})
        has_relevant_results = calls_found > 0 or projects_found > 0
        niche_guidance = self._generate_niche_query_guidance(
            query=query,
            niche_context=niche_context,
            calls_found=calls_found,
            projects_found=projects_found,
            has_relevant_results=has_relevant_results,
        )

        plan.final_answer = formatted_response + "\n\n---\n\n" + niche_guidance
        plan.confidence = 0.75
        step.observation = (
            f"Executed {len(step.tool_calls)} tool(s) for niche query, "
            f"found {calls_found} calls and {projects_found} projects"
        )
        step.next_action_needed = False

    def _finalize_plan(self, plan: AgentPlan) -> None:
        """Cancel unused speculative tasks."""
        if self.speculative_executor:
            used_tools = set()
            for step in plan.reasoning_steps:
                for tc in step.tool_calls:
                    used_tools.add(tc.tool_name)
            self.speculative_executor.cancel_unused_speculation(used_tools)

    def _cache_successful_plan(self, plan: AgentPlan, query: str, context: str) -> None:
        """Cache the first step's plan if query was successful."""
        if self.plan_cache and plan.reasoning_steps and plan.final_answer:
            first_step = plan.reasoning_steps[0] if plan.reasoning_steps else None
            if first_step and first_step.tool_calls:
                first_plan = {
                    "thought": first_step.thought,
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": tc.tool_name,
                            "parameters": tc.parameters,
                            "reasoning": tc.reasoning,
                        }
                        for tc in first_step.tool_calls
                    ],
                    "needs_more_info": first_step.next_action_needed,
                }
                self.plan_cache.cache_plan(
                    query=query,
                    plan=first_plan,
                    context=context,
                    quality_score=plan.confidence or 0.8,
                )

    def _build_result_dict(
        self,
        plan: AgentPlan,
        all_tool_results: dict,
        query: str,
        total_time: float,
        iteration: int,
        long_query_result: LongQueryResult,
        special_char_metadata: dict | None,
        translation_metadata: dict | None,
    ) -> dict[str, Any]:
        """Build the final result dictionary."""
        answer = plan.final_answer or self._build_fallback_answer(plan)

        quality_analysis = self._analyze_response_quality(
            query=query, answer=answer, tool_results=all_tool_results
        )

        result = {
            "answer": answer,
            "success": plan.final_answer is not None,
            "reasoning_steps": [
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "tools_called": [tc.tool_name for tc in s.tool_calls],
                    "observation": s.observation[:500] if s.observation else "",
                }
                for s in plan.reasoning_steps
            ],
            "sources_used": list(all_tool_results.keys()),
            "tool_results": all_tool_results,
            "complexity": plan.complexity,
            "iterations": iteration,
            "confidence": plan.confidence,
            "total_time_ms": total_time,
            "quality_analysis": quality_analysis,
            "model_used": getattr(self, "_active_model_name", "unknown"),
        }

        if long_query_result.was_processed:
            result["long_query_metadata"] = {
                "original_length": long_query_result.query_length,
                "processed_length": len(long_query_result.processed_query),
                "key_details_extracted": long_query_result.key_details,
                "processing_method": long_query_result.processing_note,
            }

        if special_char_metadata:
            result["special_char_metadata"] = special_char_metadata

        if translation_metadata:
            result["translation_metadata"] = translation_metadata

        return result

    async def process_query(
        self,
        query: str,
        context: str = "",
        conversation_history: list[dict] = None,
        conversation_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Process a complex query using multi-tool reasoning.

        Args:
            query: User's question
            context: Additional context
            conversation_history: Previous messages
            conversation_id: Conversation ID for pagination caching

        Returns:
            Dict with answer, reasoning steps, and sources
        """
        start_time = datetime.now()
        self._current_query = query
        self._conversation_id = conversation_id

        # ── Early check: "show more projects" pagination from cached results ──
        show_more_result = self._handle_show_more_request(query)
        if show_more_result:
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            show_more_result["total_time_ms"] = total_time
            return show_more_result

        # Reset context window manager to prevent memory leak across queries
        _context_manager.reset()

        # Preprocess query (special chars, translation, long query)
        query, context, special_char_metadata, translation_metadata, long_query_result, _ = (
            self._preprocess_query(query, context)
        )

        # Initialize plan and select model
        plan = self._init_plan_and_model(query)

        # Start speculative execution
        await self._start_speculation(query, context)

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
                step.tool_calls = await self._execute_tool_calls(tool_calls)
                tool_results_this_step = {}

                should_break = self._handle_call_tools_action(
                    step,
                    reasoning_result,
                    all_tool_results,
                    tool_results_this_step,
                    plan,
                    query,
                    iteration,
                )
                if should_break:
                    break

            elif step.action == "analyze_results":
                step.observation = reasoning_result.get("analysis", "")
                step.next_action_needed = reasoning_result.get("needs_more_info", False)

            elif step.action == "conclude":
                plan.final_answer = reasoning_result.get("conclusion", "")
                plan.confidence = reasoning_result.get("confidence", 0.8)
                step.next_action_needed = False

            elif step.action == "generate_guidance":
                guidance_response = reasoning_result.get("response", "")
                plan.final_answer = guidance_response
                plan.confidence = 0.9
                step.observation = (
                    f"Generated {reasoning_result.get('guidance_type', 'guidance')} guidance"
                )
                step.next_action_needed = False

            elif step.action == "call_tools_and_format":
                tool_calls = reasoning_result.get("tool_calls", [])
                step.tool_calls = await self._execute_tool_calls(tool_calls)
                self._handle_format_action(step, all_tool_results, plan, query, iteration)

            elif step.action == "call_tools_with_niche_guidance":
                tool_calls = reasoning_result.get("tool_calls", [])
                step.tool_calls = await self._execute_tool_calls(tool_calls)
                self._handle_niche_guidance_action(
                    step,
                    reasoning_result,
                    all_tool_results,
                    plan,
                    query,
                    iteration,
                )

            elif step.action == "search_imminent_calls_with_warning":
                imminent_calls_result = await self._search_imminent_calls_with_warning(query)
                plan.final_answer = imminent_calls_result
                plan.confidence = 0.85
                step.observation = (
                    "Searched for imminent deadline calls with feasibility assessment"
                )
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            if not step.next_action_needed:
                logger.info(f"✅ Agent concluded after {iteration} iteration(s)")
                break

        # Finalize
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        self._finalize_plan(plan)
        self._cache_successful_plan(plan, query, context)

        return self._build_result_dict(
            plan,
            all_tool_results,
            query,
            total_time,
            iteration,
            long_query_result,
            special_char_metadata,
            translation_metadata,
        )

    async def process_query_streaming(
        self,
        query: str,
        context: str = "",
        conversation_history: list[dict] = None,
        conversation_id: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process a query and yield events in real-time as reasoning happens.

        Yields events like:
        - {'type': 'agent_thinking', 'iteration': 1, 'thought': '...'}
        - {'type': 'tool_call', 'tool_name': '...', 'parameters': {...}}
        - {'type': 'tool_result', 'tool_name': '...', 'result_summary': '...', 'result_count': 5}
        - {'type': 'agent_complete', 'result': {...}}

        Args:
            query: User's question
            context: Additional context (conversation history)
            conversation_history: Previous messages
            conversation_id: Conversation ID for pagination caching

        Yields:
            Dict events as processing happens
        """
        start_time = datetime.now()
        self._current_query = query
        self._conversation_id = conversation_id

        # ── Early check: "show more projects" pagination from cached results ──
        show_more_result = self._handle_show_more_request(query)
        if show_more_result:
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            show_more_result["total_time_ms"] = total_time
            yield {"type": "agent_complete", "result": show_more_result}
            return

        # Reset context window manager to prevent memory leak across queries
        _context_manager.reset()

        # Preprocess query (special chars, translation, long query)
        query, context, special_char_metadata, translation_metadata, long_query_result, _ = (
            self._preprocess_query(query, context)
        )

        # Initialize plan and select model
        plan = self._init_plan_and_model(query)

        # Start speculative execution
        await self._start_speculation(query, context)

        # ReAct loop with streaming
        iteration = 0
        all_tool_results = {}

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 [Streaming] Reasoning iteration {iteration}/{self.max_iterations}")

            # Get next action from LLM
            reasoning_result = await self._reason_next_step(
                query=query,
                context=context,
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
            logger.info(f"🧠 [Streaming] Action: {step.action}, thought: {step.thought[:100]}")

            # YIELD: Agent thinking event immediately
            yield {
                "type": "agent_thinking",
                "iteration": iteration,
                "thought": step.thought,
                "action": step.action,
            }

            # Handle different actions
            if step.action == "call_tools":
                tool_calls = reasoning_result.get("tool_calls", [])

                # YIELD: Tool call events before execution
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

                # Execute tool calls
                step.tool_calls = await self._execute_tool_calls(tool_calls)

                # YIELD: Tool result events after execution
                tool_results_this_step = {}
                for idx, tc in enumerate(step.tool_calls):
                    result_count = self._count_results(tc.result) if tc.success else 0
                    yield {
                        "type": "tool_result",
                        "iteration": iteration,
                        "tool_name": tc.tool_name,
                        "success": tc.success,
                        "result_count": result_count,
                        "result_summary": str(tc.result)[:300] if tc.result else "No results",
                        "execution_time_ms": tc.execution_time_ms,
                    }

                    if tc.success:
                        all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result
                        tool_results_this_step[tc.tool_name] = tc.result

                # Auto-promote to formatted output ONLY for semantic project searches
                has_semantic_projects = any(
                    isinstance(r, dict) and ("similar_projects" in r or "rendered_content" in r)
                    for r in tool_results_this_step.values()
                )
                if has_semantic_projects:
                    formatted = self._synthesize_from_results(query, tool_results_this_step)
                    if formatted and len(formatted) > 200:
                        plan.final_answer = formatted
                        plan.confidence = 0.90
                        step.observation = (
                            f"Executed {len(step.tool_calls)} tool(s) — "
                            f"auto-formatted project results"
                        )
                        step.next_action_needed = False
                        plan.reasoning_steps.append(step)
                        break

                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get("needs_more_info", True)

                # Force another iteration when multiple tools were called successfully
                successful_calls = [tc for tc in step.tool_calls if tc.success]
                if len(successful_calls) >= 2 and not step.next_action_needed:
                    logger.info(
                        f"⚡ [Streaming] Forcing cross-analysis iteration: "
                        f"{len(successful_calls)} tools returned results — "
                        f"LLM needs to synthesize combined data"
                    )
                    step.next_action_needed = True

            elif step.action == "analyze_results":
                step.observation = reasoning_result.get("analysis", "")
                step.next_action_needed = reasoning_result.get("needs_more_info", False)

            elif step.action == "conclude":
                plan.final_answer = reasoning_result.get("conclusion", "")
                plan.confidence = reasoning_result.get("confidence", 0.8)
                step.next_action_needed = False

            elif step.action == "generate_guidance":
                guidance_response = reasoning_result.get("response", "")
                plan.final_answer = guidance_response
                plan.confidence = 0.9
                step.observation = (
                    f"Generated {reasoning_result.get('guidance_type', 'guidance')} guidance"
                )
                step.next_action_needed = False

            elif step.action == "call_tools_and_format":
                tool_calls = reasoning_result.get("tool_calls", [])
                step.tool_calls = await self._execute_tool_calls(tool_calls)

                # Yield tool events for streaming
                for tc in step.tool_calls:
                    yield {
                        "type": "tool_call",
                        "tool_name": tc.tool_name,
                        "parameters": tc.parameters,
                    }
                    yield {
                        "type": "tool_result",
                        "tool_name": tc.tool_name,
                        "success": tc.success,
                        "result_summary": str(tc.result)[:200] if tc.result else "",
                    }

                self._handle_format_action(step, all_tool_results, plan, query, iteration)

            elif step.action == "call_tools_with_niche_guidance":
                tool_calls = reasoning_result.get("tool_calls", [])
                step.tool_calls = await self._execute_tool_calls(tool_calls)

                # Yield tool events for streaming
                for tc in step.tool_calls:
                    yield {
                        "type": "tool_call",
                        "tool_name": tc.tool_name,
                        "parameters": tc.parameters,
                    }
                    yield {
                        "type": "tool_result",
                        "tool_name": tc.tool_name,
                        "success": tc.success,
                        "result_summary": str(tc.result)[:200] if tc.result else "",
                    }

                self._handle_niche_guidance_action(
                    step,
                    reasoning_result,
                    all_tool_results,
                    plan,
                    query,
                    iteration,
                )

            elif step.action == "search_imminent_calls_with_warning":
                imminent_calls_result = await self._search_imminent_calls_with_warning(query)
                plan.final_answer = imminent_calls_result
                plan.confidence = 0.85
                step.observation = (
                    "Searched for imminent deadline calls with feasibility assessment"
                )
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            if not step.next_action_needed:
                logger.info(f"✅ [Streaming] Agent concluded after {iteration} iteration(s)")
                break

        # Finalize
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        self._finalize_plan(plan)
        self._cache_successful_plan(plan, query, context)

        final_result = self._build_result_dict(
            plan,
            all_tool_results,
            query,
            total_time,
            iteration,
            long_query_result,
            special_char_metadata,
            translation_metadata,
        )
        yield {"type": "agent_complete", "result": final_result}

    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity for model routing and planning.

        Returns:
            "simple" — single-source, straightforward queries (flash model)
            "comparison" — comparing 2+ things side-by-side (pro model)
            "analysis" — explaining WHY, trends, deep reasoning (pro model)
            "multi_source" — needs multiple data types combined (pro model)
        """
        query_lower = query.lower()

        # Comparison queries — need pro for structured side-by-side reasoning
        comparison_patterns = [
            "compare",
            "versus",
            "vs ",
            "vs.",
            "difference between",
            "differ from",
            "better than",
            "how do .* compare",
            "pros and cons",
            "advantages .* disadvantages",
            "which is better",
            "which one",
            "similarities",
        ]
        if any(p in query_lower for p in comparison_patterns):
            return "comparison"

        # Analysis queries — need pro for deep reasoning and explanation
        analysis_patterns = [
            "why ",
            "why?",
            "analyze",
            "analyse",
            "explain the reason",
            "how does .* work",
            "what causes",
            "what drives",
            "trend",
            "pattern",
            "evolution of",
            "impact of",
            "implications",
            "assess",
            "evaluate",
            "critique",
            "success rate",
            "success factor",
            "what makes .* successful",
            "lessons learned",
            "best practice",
        ]
        if any(p in query_lower for p in analysis_patterns):
            return "analysis"

        # Multi-source queries — need pro to synthesize across sources
        # Detect when query asks for multiple distinct data types
        multi_source_signals = 0
        if any(
            w in query_lower for w in ["eligibility", "eligible", "who can apply", "requirements"]
        ):
            multi_source_signals += 1
        if any(w in query_lower for w in ["budget", "funding", "cost", "how much"]):
            multi_source_signals += 1
        if any(w in query_lower for w in ["deadline", "when", "timeline", "schedule"]):
            multi_source_signals += 1
        if any(w in query_lower for w in ["project", "funded", "example", "similar"]):
            multi_source_signals += 1
        if any(w in query_lower for w in ["call", "opportunity", "topic"]):
            multi_source_signals += 1
        if any(
            w in query_lower for w in ["partner", "consortium", "organization", "collaboration"]
        ):
            multi_source_signals += 1
        if any(w in query_lower for w in ["statistic", "rate", "percentage", "average"]):
            multi_source_signals += 1

        if multi_source_signals >= 3:
            return "multi_source"

        # Explicit multi-part connectors
        if any(p in query_lower for p in ["and also", "as well as", "in addition", "furthermore"]):
            if multi_source_signals >= 2:
                return "multi_source"

        # Multi-question detection (contains multiple question marks)
        if query.count("?") >= 2:
            return "multi_source"

        return "simple"

    def _identify_required_sources(self, query: str) -> list[str]:
        """Identify which data sources are needed."""
        sources = []
        query_lower = query.lower()

        # Statistics indicators
        if any(
            word in query_lower
            for word in ["rate", "percentage", "how many", "statistics", "average", "success"]
        ):
            sources.append("statistics")

        # Document indicators
        if any(
            word in query_lower
            for word in ["eligible", "requirement", "rule", "can i", "allowed", "must"]
        ):
            sources.append("documents")

        # Call indicators
        if any(word in query_lower for word in ["call", "funding", "deadline", "apply", "open"]):
            sources.append("calls")

        # Project indicators
        if any(word in query_lower for word in ["project", "funded", "example", "similar"]):
            sources.append("projects")

        return sources if sources else ["documents"]

    def _count_results(self, result: Any) -> int | None:
        """Count the number of results from a tool response."""
        if result is None:
            return 0
        if isinstance(result, dict):
            # Check for common result count keys
            for key in ["count", "total", "total_results", "projects_count", "calls_found"]:
                if key in result:
                    return int(result[key])
            # Check for list-like keys
            for key in ["results", "projects", "calls", "documents", "partners", "organizations"]:
                if key in result and isinstance(result[key], list):
                    return len(result[key])
        if isinstance(result, list):
            return len(result)
        return None

    async def _reason_next_step(
        self,
        query: str,
        context: str,
        previous_steps: list[ReasoningStep],
        tool_results: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Use LLM to reason about the next step."""

        # PRE-ROUTING: For first step, detect queries that must use specific tools
        # This bypasses LLM for obvious cases where it might incorrectly choose search_documents
        # IMPORTANT: This check runs BEFORE cache to override bad cached plans
        # SKIP pre-routing for complex queries (comparison/analysis/multi_source) — let the
        # pro model handle these with full tool-based reasoning for higher quality answers
        complexity = getattr(self, "_current_complexity", "simple")
        if not previous_steps and complexity not in ("comparison", "analysis", "multi_source"):
            pre_routed = self._detect_query_type_for_tool_selection(query, context)
            if pre_routed:
                logger.info(
                    f"🎯 Pre-routed query to {pre_routed.get('tool_calls', [{}])[0].get('tool', 'unknown')}"
                )
                return pre_routed
        elif not previous_steps and complexity in ("comparison", "analysis", "multi_source"):
            logger.info(
                f"🧠 Skipping pre-routing for {complexity} query — using full LLM reasoning"
            )

        # Check cache for first step only (no previous steps or results)
        if not previous_steps and not tool_results and self.plan_cache:
            cached_plan = self.plan_cache.get_cached_plan(query, context)
            if cached_plan:
                logger.info("🚀 Using cached reasoning plan")
                return cached_plan

        # Reset context manager for this reasoning step
        _context_manager.reset()

        # Format previous steps with context-aware truncation
        steps_text = ""
        for step in previous_steps:
            step_text = f"\n**Step {step.step_number}**\n"
            step_text += f"Thought: {step.thought}\n"
            step_text += f"Action: {step.action}\n"
            if step.tool_calls:
                step_text += f"Tools called: {[tc.tool_name for tc in step.tool_calls]}\n"
            if step.observation:
                truncated_obs = _context_manager.truncate_observation(step.observation)
                step_text += f"Observation: {truncated_obs}\n"
            steps_text += step_text

        # Format tool results with context-aware truncation
        results_text = _context_manager.format_results_for_context(tool_results)

        # Add tool hints for specific query types (helps guide LLM to correct tools)
        tool_hint = self._get_tool_hint(query, context)
        enhanced_context = context or "No additional context"
        if tool_hint:
            enhanced_context = f"{enhanced_context}\n\n**TOOL HINT**: {tool_hint}"

        # Build prompt
        prompt = REASONING_PROMPT.format(
            built_in_knowledge=BUILT_IN_KNOWLEDGE,
            tools_description=self._get_tools_description(),
            query=query,
            context=enhanced_context,
            previous_steps=steps_text or "This is the first step",
            tool_results=results_text or "No tool results yet",
        )

        # LLM timeout in seconds (configurable via env, default 30s)

        llm_timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

        try:
            if self.llm:
                # Wrap LLM call with timeout protection
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(self.llm.generate_content, prompt), timeout=llm_timeout
                    )
                except TimeoutError:
                    logger.warning(f"⏰ LLM call timed out after {llm_timeout}s, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results, context)

                # Parse JSON from response
                response_text = response.text

                # Extract JSON block - try multiple patterns for robustness
                json_str = None

                # Pattern 1: Fenced JSON block
                json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)

                # Pattern 2: Any fenced code block (might not have 'json' marker)
                if not json_str:
                    json_match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)
                    if json_match:
                        potential_json = json_match.group(1).strip()
                        if potential_json.startswith("{"):
                            json_str = potential_json

                # Pattern 3: Raw JSON object
                if not json_str:
                    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    json_str = json_match.group(0) if json_match else None

                if not json_str:
                    logger.warning("Could not extract JSON from LLM response, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results, context)

                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as je:
                    # Try to fix common JSON issues
                    fixed_json = self._fix_malformed_json(json_str)
                    if fixed_json:
                        return fixed_json
                    logger.warning(f"JSON decode failed: {je}, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results, context)
            else:
                # Fallback reasoning
                return self._fallback_reasoning(query, previous_steps, tool_results, context)

        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            return self._fallback_reasoning(query, previous_steps, tool_results, context)

    def _fix_malformed_json(self, json_str: str) -> dict[str, Any] | None:
        """Attempt to fix common JSON formatting issues from LLM responses."""
        if not json_str:
            return None

        try:
            # Try as-is first
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        fixed = json_str

        # Remove trailing commas before } or ]
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)

        # Fix single quotes to double quotes (but not inside strings)
        # This is a simplified fix - may not work for all cases
        if "'" in fixed and '"' not in fixed:
            fixed = fixed.replace("'", '"')

        # Remove control characters
        fixed = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", fixed)

        # Try to extract just the JSON object if there's extra text
        obj_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", fixed, re.DOTALL)
        if obj_match:
            fixed = obj_match.group(0)

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    # Query detection methods provided by QueryDetectorsMixin
    # Guidance generation methods provided by GuidanceGeneratorsMixin
    # Conclusion builders provided by ConclusionBuildersMixin

    def _fallback_reasoning(
        self,
        query: str,
        previous_steps: list[ReasoningStep],
        tool_results: dict[str, Any],
        context: str = "",
    ) -> dict[str, Any]:
        """Fallback reasoning when LLM fails."""

        if not previous_steps:
            # First, try to detect specific query types for better tool selection
            # Pass context to enable detection of refinement queries
            detected_tool = self._detect_query_type_for_tool_selection(query, context)
            if detected_tool:
                return detected_tool

            # Default fallback - call basic search with more results
            return {
                "thought": "Starting with document search to gather information",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "search_documents",
                        "parameters": {"query": query, "max_results": 15},  # Increased from 5
                        "reasoning": "Initial search for relevant information",
                    }
                ],
                "needs_more_info": True,
            }

        if tool_results:
            # Have results - synthesize a proper answer
            # Extract and synthesize content from results
            synthesized_content = self._synthesize_from_results(query, tool_results)

            return {
                "thought": "Have gathered information, synthesizing answer",
                "action": "conclude",
                "conclusion": synthesized_content,
                "confidence": 0.7,
                "needs_more_info": False,
            }

        return {
            "thought": "Unable to gather more information",
            "action": "conclude",
            "conclusion": "I was unable to find specific information to answer this question. Please try rephrasing your question or asking about a more specific topic.",
            "confidence": 0.3,
            "needs_more_info": False,
        }

    # ── "Show more projects" pagination support ──

    # Response synthesis methods provided by ResponseSynthesizerMixin

    async def _search_imminent_calls_with_warning(self, query: str) -> str:
        """Search for calls with imminent deadlines AND provide realistic feasibility assessment."""
        from ..tools.imminent_calls import search_imminent_calls_with_warning_execute

        return await search_imminent_calls_with_warning_execute(query)

    def _build_erasmus_guide_search_query(self, query_lower: str) -> str:
        """Build an effective search query for Erasmus+ Programme Guide content."""
        # Extract key terms from the query
        search_terms = []

        # Add quality/evaluation context
        if "quality" in query_lower:
            search_terms.append("quality criteria assessment")
        if "evaluation" in query_lower or "evaluat" in query_lower:
            search_terms.append("evaluation criteria scoring")
        if "award" in query_lower:
            search_terms.append("award criteria")
        if "selection" in query_lower:
            search_terms.append("selection criteria")
        if "eligibility" in query_lower:
            search_terms.append("eligibility criteria")
        if "impact" in query_lower:
            search_terms.append("impact assessment")
        if "relevance" in query_lower:
            search_terms.append("relevance criteria")

        # Add Key Action context
        if "ka1" in query_lower:
            search_terms.append("Key Action 1 mobility")
        elif "ka2" in query_lower:
            search_terms.append("Key Action 2 partnership cooperation")
        elif "ka3" in query_lower:
            search_terms.append("Key Action 3 policy")

        # Add sector context
        if "higher education" in query_lower or "hed" in query_lower:
            search_terms.append("higher education HED")
        elif "vet" in query_lower or "vocational" in query_lower:
            search_terms.append("VET vocational education training")
        elif "school" in query_lower or "sch" in query_lower:
            search_terms.append("school education SCH")
        elif "adult" in query_lower or "adu" in query_lower:
            search_terms.append("adult education ADU")
        elif "youth" in query_lower or "you" in query_lower:
            search_terms.append("youth YOU")

        # Default search if no specific terms extracted
        if not search_terms:
            search_terms.append("quality criteria evaluation assessment award")

        return " ".join(search_terms)

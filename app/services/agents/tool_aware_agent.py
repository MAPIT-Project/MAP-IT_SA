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
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# CONTEXT WINDOW MANAGEMENT
# =============================================================================

@dataclass
class ContextLimits:
    """Configuration for context window limits."""
    # Maximum tokens for various components (approximate, using char/4 ratio)
    max_context_chars: int = 100000  # ~25k tokens
    max_tool_result_chars: int = 5000  # Per tool result
    max_observation_chars: int = 1500  # Per reasoning step
    max_document_chars: int = 600  # Per document in synthesis
    max_documents_per_result: int = 10  # Max docs to include
    max_calls_per_result: int = 15  # Max calls to include
    max_projects_per_result: int = 10  # Max projects to include
    reserved_for_response: int = 4000  # Reserve for output

    @classmethod
    def from_env(cls) -> 'ContextLimits':
        """Load limits from environment variables with defaults."""
        return cls(
            max_context_chars=int(os.getenv('MAX_CONTEXT_CHARS', '100000')),
            max_tool_result_chars=int(os.getenv('MAX_TOOL_RESULT_CHARS', '5000')),
            max_observation_chars=int(os.getenv('MAX_OBSERVATION_CHARS', '1500')),
            max_document_chars=int(os.getenv('MAX_DOCUMENT_CHARS', '600')),
        )


class ContextWindowManager:
    """Manages context window for LLM prompts to prevent overflow."""

    def __init__(self, limits: Optional[ContextLimits] = None):
        self.limits = limits or ContextLimits.from_env()
        self._current_size = 0

    def reset(self):
        """Reset the context size tracker."""
        self._current_size = 0

    def truncate_text(self, text: str, max_chars: int, suffix: str = "...") -> str:
        """Truncate text to max_chars, adding suffix if truncated."""
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[:max_chars - len(suffix)] + suffix

    def truncate_tool_result(self, result: Any) -> str:
        """Truncate a tool result to fit within limits."""
        if result is None:
            return "No results"

        result_str = str(result) if not isinstance(result, str) else result
        return self.truncate_text(result_str, self.limits.max_tool_result_chars)

    def truncate_observation(self, observation: str) -> str:
        """Truncate an observation to fit within limits."""
        return self.truncate_text(observation, self.limits.max_observation_chars)

    def truncate_document(self, content: str) -> str:
        """Truncate document content to fit within limits."""
        return self.truncate_text(content, self.limits.max_document_chars)

    def estimate_prompt_size(self, prompt: str) -> int:
        """Estimate the token count of a prompt (chars / 4 approximation)."""
        return len(prompt) // 4

    def would_exceed_limit(self, additional_chars: int) -> bool:
        """Check if adding more content would exceed the context limit."""
        return (self._current_size + additional_chars) > self.limits.max_context_chars

    def add_to_context(self, content: str) -> str:
        """Add content to context, truncating if necessary."""
        available = self.limits.max_context_chars - self._current_size - self.limits.reserved_for_response
        if available <= 0:
            logger.warning("Context window exhausted, dropping content")
            return ""

        if len(content) > available:
            content = self.truncate_text(content, available)
            logger.warning(f"Content truncated to fit context window ({available} chars)")

        self._current_size += len(content)
        return content

    def format_results_for_context(
        self,
        results: Dict[str, Any],
        priority_keys: Optional[List[str]] = None
    ) -> str:
        """Format tool results for inclusion in context, respecting limits."""
        if not results:
            return "No tool results yet"

        # Prioritize certain result types
        priority_keys = priority_keys or ['calls', 'projects', 'documents']

        formatted_parts = []
        remaining_budget = self.limits.max_context_chars - self._current_size - self.limits.reserved_for_response

        for name, result in results.items():
            if remaining_budget <= 0:
                logger.warning("Skipping remaining results due to context limits")
                break

            result_str = self.truncate_tool_result(result)
            part = f"\n**{name}**: {result_str}\n"

            if len(part) > remaining_budget:
                part = self.truncate_text(part, remaining_budget)

            formatted_parts.append(part)
            remaining_budget -= len(part)

        return "".join(formatted_parts)


# Global context manager instance
_context_manager = ContextWindowManager()


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
    
    # Built-in knowledge for common questions where documents may be incomplete
    BUILT_IN_KNOWLEDGE = """
## Quick Reference: Horizon Europe Facts

### Page Limits for Proposals (Part B - Technical Description)
| Action Type | Standard Page Limit | Notes |
|-------------|---------------------|-------|
| **RIA/IA (single-stage)** | **45 pages** | Sections 1-3 combined |
| **RIA/IA (two-stage, full)** | **45 pages** | After passing stage 1 |
| **RIA/IA (two-stage, outline)** | **10 pages** | Stage 1 only |
| **CSA** | **30 pages** | Shorter scope |
| **ERC grants** | **Variable** | Check specific call |
| **MSCA** | **10-15 pages** | Depends on action |
| **EIC Accelerator** | **Variable** | Short proposal + full |

*Page limits are strictly enforced. Excess pages will be blanked and not evaluated.*

### Organisation Type Eligibility
| Organisation Type | Eligible? | Funding Rate (RIA) | Funding Rate (IA) | Special Notes |
|-------------------|-----------|-------------------|-------------------|---------------|
| **Universities/HEIs** | Yes | 100% | 100% | Must have GEP |
| **Research Institutes** | Yes | 100% | 100% | Must have GEP |
| **SMEs** | Yes | 100% | 70% | EIC Accelerator available |
| **Large Companies** | Yes | 100% | 70% | Cannot lead some calls |
| **NGOs** | Yes | 100% | 100% (non-profit) | Often needed for dissemination |
| **Public Bodies** | Yes | 100% | 100% | Must have GEP |
| **International Orgs** | Case-by-case | Varies | Varies | Check specific call |

### Action Types Summary
| Type | TRL Range | Funding Rate | Focus |
|------|-----------|--------------|-------|
| **RIA** | TRL 2-5 | 100% | Research, new knowledge |
| **IA** | TRL 5-8 | 70%/100% | Demonstration, piloting |
| **CSA** | N/A | 100% | Coordination, networking |

### Consortium Requirements
- **Standard (RIA/IA/CSA)**: 3 independent entities from 3 different EU/AC countries
- **ERC**: Single PI (monobeneficiary)
- **MSCA PF**: Single fellow + host
- **EIC Accelerator**: Single SME or small group

### Budget Limits / Expected EU Contribution per Project
There is NO single fixed budget limit for Innovation Actions (IA) or other action types. Budgets are defined per TOPIC in the Work Programme.

| Action Type | Typical EU Contribution Range | Notes |
|-------------|------------------------------|-------|
| **RIA (standard)** | €3-8 million | Varies by topic complexity |
| **IA (standard)** | €5-15 million | Large-scale demonstrations |
| **IA (flagship/large)** | €15-50 million | Strategic topics only |
| **CSA** | €1-3 million | Coordination activities |
| **ERC Starting** | Up to €1.5 million | 5 years |
| **ERC Consolidator** | Up to €2 million | 5 years |
| **ERC Advanced** | Up to €2.5 million | 5 years |
| **EIC Accelerator** | Up to €2.5M grant + €15M equity | Blended finance |

**How to find actual limits:** Check the specific Call Topic in the Work Programme - it states "Expected EU contribution per project: €X-Y million"

### Getting Started with Proposal Writing
If someone asks "How do I start writing a proposal?" or "Where do I start?", provide this guidance:

1. **Find a relevant call**: Search for open calls on the EU Funding & Tenders Portal that match your research area
2. **Understand the call**: Read the Work Programme topic carefully - understand scope, expected outcomes, and evaluation criteria
3. **Build your consortium**: Most calls require 3+ partners from 3+ different EU/Associated countries
4. **Write the proposal**: Follow the template structure (Excellence, Impact, Implementation)
5. **Use the search tools**: Search for similar funded projects to learn from successful proposals

### Proposal Template Structure (Part B)
Standard RIA/IA proposals have 3 main sections:
- **Section 1: Excellence** - Scientific quality, objectives, methodology, ambition (beyond state-of-art)
- **Section 2: Impact** - Expected outcomes, pathways to impact, dissemination, exploitation
- **Section 3: Implementation** - Work plan, consortium, resources, management

### Evaluation Criteria
| Section | Threshold | Weight | Key aspects |
|---------|-----------|--------|-------------|
| Excellence | 4/5 | ~1/3 | Objectives, methodology, ambition |
| Impact | 4/5 | ~1/3 | Outcomes, dissemination, exploitation |
| Implementation | 3/5 | ~1/3 | Work plan, consortium, resources |
| **Overall** | **10/15** | - | Must pass all thresholds |
"""

    # System prompt for the reasoning LLM
    REASONING_PROMPT = """You are an intelligent research assistant for EU funding (Horizon Europe, EIC, ERC, etc.).

## Built-in Knowledge (USE THIS FOR COMMON QUESTIONS)

{built_in_knowledge}

## Available Tools

{tools_description}

## Understanding User Intent

The user's message may:
- Be a NEW question: Search for the information they need
- REFER to previous results: "the 4th one", "that call", "tell me more about it"
- BE A COMPLAINT: "only 1 result", "that's not enough", "wtf" → They want more/better results
- ASK FOR MORE: "show me more", "any others" → Search again with same topic
- **CHANGE SCOPE**: "what about projects USING X", "X as part of projects", "applied X" → Re-run the SAME analysis tool with expand_scope=True

When the user refers to previous conversation:
- Look at CONVERSATION HISTORY to understand what they mean
- If they say "the 3rd call" - find the 3rd call ID from the history
- If they complain about results - search again for the SAME TOPIC with more results

**CRITICAL: Scope Change Follow-ups**
When user asks to broaden scope after a funding/history analysis (e.g., "what about projects where AI is used?" after asking about AI funding):
- This is NOT a request for different tools (like budget_benchmark or consortium_patterns)
- This IS a request to re-run analyze_call_history with expand_scope=True
- The user wants the SAME type of analysis (funding evolution, trends) but for a BROADER set of projects
- Example: "AI funding evolution" → user asks "what about projects using AI" → re-run analyze_call_history(keywords='AI', expand_scope=True)

## Your Task

1. **UNDERSTAND**: What does the user actually want?
   - Read the conversation history to understand context
   - Identify if this is a new question or follow-up

2. **DECIDE**: What tools to use (or answer directly if you can)
   - For **general guidance** ("how do I start?", "where do I begin?") → Answer from BUILT-IN KNOWLEDGE above, no search needed!
   - For **proposal structure** questions → Answer from BUILT-IN KNOWLEDGE (see "Getting Started" and "Proposal Template Structure")
   - For **specific call ID** (user gives ID like HORIZON-*, CREA-*, EIC-*) → use get_call_details (fetches from EU Portal API)
   - For **finding/searching** funding calls by topic → use search_funding_calls
   - For projects → use search_projects
   - For statistics → use get_programme_statistics or get_country_statistics
   - For **country eligibility** ("Can X participate?", "Is Y eligible?") → use get_country_statistics (provides clear YES/NO answer with participation data)
   - For budget/funding questions → use get_budget_benchmark (returns real data from funded projects)
   - For consortium composition → use get_consortium_patterns (org types, country distribution, coordinator profiles)
   - For finding partners → use find_experienced_partners (organizations with track records in specific topics)
   - For **general eligibility rules** (not country-specific) → use search_documents (use SPECIFIC queries like "consortium eligibility", NOT the full user message)
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
6. **NEVER use the full user message as a search query** - extract key terms only (e.g., "consortium eligibility" not "I want to know about consortium eligibility for my project")
7. For general "how to start" questions, use BUILT-IN KNOWLEDGE directly - don't search

## Response Guidelines

- Show ALL relevant results (up to 10), not just 2-3
- Include call IDs so users can reference them (e.g., "tell me more about #3")
- For funding calls: include title, call ID, type, deadline, cluster, and scope
- Be comprehensive but organized

## CRITICAL: Synthesizing Answers

When action is "conclude", you MUST:
1. SYNTHESIZE information from tool results into a coherent, well-structured answer
2. NEVER just copy raw document fragments - explain them in your own words
3. Use markdown formatting: headings, bullet points, tables where appropriate
4. If documents mention specific rules/requirements, state them clearly
5. If you found relevant info, explain it - don't say "results don't contain information"
6. Structure answers with: Overview → Details → Key Points/Recommendations

**SPECIAL CASE - Timeline Generation:**
When the generate_timeline tool was used, your conclusion MUST include the COMPLETE timeline output:
- ALL work packages with their full details (lead, participants, objectives, tasks, effort, duration)
- ALL deliverables with due dates, types, and dissemination levels
- ALL milestones with due months
- The COMPLETE ASCII Gantt chart (do not truncate or summarize it)
- WP dependencies
- All recommendations
This is critical because users need the full timeline for their proposals. Do NOT summarize or shorten it.

Example good conclusion:
"The minimum consortium composition for Horizon Europe RIA/IA projects is **3 independent legal entities from 3 different EU Member States or Associated Countries**.

### Key Requirements:
- At least 3 legal entities
- Each from a different country
- Countries must be EU Member States or Associated Countries

*Source: Horizon Europe Programme Guide*"

Example BAD conclusion (never do this):
"From document X: The consortium shall... [raw text fragment]"

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
        self._init_cache()
        self._init_analytics()
        self._init_speculative_executor()

        logger.info(f"🛠️ ToolAwareAgent initialized with {len(self.tools)} tools")

    def _init_cache(self):
        """Initialize query plan cache."""
        try:
            from ..cache.query_plan_cache import QueryPlanCache
            from ..memory.memory_service import MemoryService

            memory = MemoryService()
            self.plan_cache = QueryPlanCache(memory.redis_client)
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

        # Budget benchmarking tool
        self.register_tool(Tool(
            name="get_budget_benchmark",
            description="Get real budget statistics from funded Horizon Europe projects. Returns min/max/average/median EU contributions, budget per partner, consortium sizes, and data-driven recommendations.",
            category=ToolCategory.STATISTICS,
            parameters={
                "cluster": "Optional: Cluster code (e.g., 'CL4', 'CL5', 'EIC')",
                "action_type": "Optional: Action type (e.g., 'RIA', 'IA', 'CSA', 'ERC-STG')",
                "topic_keywords": "Optional: Keywords to filter projects (e.g., 'AI', 'hydrogen')",
                "year": "Optional: Filter by funding year"
            },
            examples=[
                "get_budget_benchmark(cluster='CL4', action_type='RIA')",
                "get_budget_benchmark(action_type='IA', topic_keywords='hydrogen')",
                "get_budget_benchmark(cluster='CL5')"
            ]
        ))

        # Consortium patterns tool
        self.register_tool(Tool(
            name="get_consortium_patterns",
            description="Analyze consortium composition patterns from funded projects. Returns organization type distribution (HES, REC, PRC, SME), country participation rates, coordinator profiles, and composition recommendations.",
            category=ToolCategory.STATISTICS,
            parameters={
                "cluster": "Optional: Cluster code (e.g., 'CL4', 'CL5', 'EIC')",
                "action_type": "Optional: Action type (e.g., 'RIA', 'IA', 'CSA')",
                "topic_keywords": "Optional: Keywords to filter projects"
            },
            examples=[
                "get_consortium_patterns(cluster='CL4', action_type='RIA')",
                "get_consortium_patterns(action_type='IA')",
                "get_consortium_patterns(topic_keywords='hydrogen')"
            ]
        ))

        # Partner discovery tool
        self.register_tool(Tool(
            name="find_experienced_partners",
            description="Find organizations with proven track records in specific Horizon Europe topics. Returns organizations ranked by relevant projects, coordination experience, and funding received.",
            category=ToolCategory.PROJECTS,
            parameters={
                "topic_keywords": "Required: Keywords describing the research area (e.g., 'quantum computing')",
                "country": "Optional: Country name or code (e.g., 'Germany', 'DE')",
                "organization_type": "Optional: HES, REC, PRC, SME, university, research",
                "cluster": "Optional: Cluster code (CL4, CL5, etc.)",
                "min_projects": "Optional: Minimum projects to be considered experienced (default: 2)",
                "role_filter": "Optional: 'coordinator' or 'participant'"
            },
            examples=[
                "find_experienced_partners(topic_keywords='quantum computing', country='Germany')",
                "find_experienced_partners(topic_keywords='hydrogen', organization_type='SME')",
                "find_experienced_partners(topic_keywords='AI healthcare', role_filter='coordinator')"
            ]
        ))

        # Similar funded projects tool (semantic search)
        self.register_tool(Tool(
            name="get_similar_funded_projects",
            description="Find funded Horizon Europe projects semantically similar to a description using AI embeddings. Returns projects ranked by similarity with details, consortiums, and insights.",
            category=ToolCategory.PROJECTS,
            parameters={
                "description": "Required: Project idea or description to match (min 20 chars)",
                "cluster": "Optional: Cluster code filter (CL4, CL5, EIC, etc.)",
                "action_type": "Optional: Action type filter (RIA, IA, CSA)",
                "min_budget": "Optional: Minimum EU contribution filter",
                "max_budget": "Optional: Maximum EU contribution filter",
                "year_from": "Optional: Filter for projects starting from year",
                "limit": "Optional: Number of results (default 10)"
            },
            examples=[
                "get_similar_funded_projects(description='AI system for cancer detection using medical imaging')",
                "get_similar_funded_projects(description='Green hydrogen production', cluster='CL5', action_type='RIA')",
                "get_similar_funded_projects(description='Quantum computing applications in drug discovery', limit=5)"
            ]
        ))

        # Call history analysis tool
        self.register_tool(Tool(
            name="analyze_call_history",
            description="""Analyze historical funding patterns for Horizon Europe topics. Shows what got funded, when, funding trends over time, and recommendations.

IMPORTANT - Scope Control with 'expand_scope':
- expand_scope=False (default): Searches for projects where the topic IS the main focus (e.g., "AI research projects")
- expand_scope=True: Searches for projects where the topic is USED/APPLIED (e.g., "projects that use AI as a tool")

When user asks about "projects using X" or "X as part of projects" or "applied X", set expand_scope=True.
This uses AI to automatically expand keywords to related terms (e.g., "AI" → includes "machine learning", "neural networks", "deep learning", etc.)""",
            category=ToolCategory.STATISTICS,
            parameters={
                "topic_pattern": "Optional: Topic code pattern (e.g., 'HORIZON-CL4-2023')",
                "cluster": "Optional: Cluster code (CL4, CL5, EIC, etc.)",
                "keywords": "Optional: Keywords to search in call titles/descriptions",
                "year_from": "Optional: Starting year filter",
                "year_to": "Optional: Ending year filter",
                "action_types": "Optional: List of action types (RIA, IA, CSA)",
                "include_projects": "Optional: Include funded project examples (default true)",
                "expand_scope": "Optional: Set to true to include projects where the topic is USED/APPLIED, not just focused on it. Uses AI to expand keywords to related terms."
            },
            examples=[
                "analyze_call_history(cluster='CL4', keywords='artificial intelligence')  # AI-focused projects only",
                "analyze_call_history(keywords='artificial intelligence', expand_scope=True)  # Projects USING AI",
                "analyze_call_history(keywords='hydrogen', year_from=2022)",
                "analyze_call_history(cluster='CL5', action_types=['RIA', 'IA'])"
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
            description="Get detailed information about a specific funding call by its ID. Use this when the user provides a call ID (e.g., HORIZON-*, CREA-*, EIC-*). This tool fetches from the EU Portal API if not found locally.",
            category=ToolCategory.CALLS,
            parameters={
                "call_id": "The call identifier (e.g., 'HORIZON-CL5-2025-D3-01', 'CREA-MEDIA-2026-FILMSALES')"
            },
            examples=[
                "get_call_details(call_id='HORIZON-CL5-2025-D3-01')",
                "get_call_details(call_id='CREA-MEDIA-2026-FILMSALES')"
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

        # Budget calculator tool (proposal planning)
        self.register_tool(Tool(
            name="calculate_budget",
            description="Calculate realistic budget breakdown for a Horizon Europe proposal. Returns cost categories (personnel, equipment, travel, etc.), per-partner distribution, and benchmarks.",
            category=ToolCategory.STATISTICS,
            parameters={
                "action_type": "Required: Action type (RIA, IA, CSA, ERC-STG, ERC-COG, ERC-ADG)",
                "duration_months": "Required: Project duration in months",
                "num_partners": "Required: Number of consortium partners",
                "total_person_months": "Optional: Total person-months (if known)",
                "target_budget": "Optional: Target total budget in EUR",
                "countries": "Optional: List of partner country codes (e.g., ['DE', 'FR', 'ES'])"
            },
            examples=[
                "calculate_budget(action_type='RIA', duration_months=36, num_partners=8)",
                "calculate_budget(action_type='IA', duration_months=48, num_partners=12, target_budget=10000000)",
                "calculate_budget(action_type='RIA', duration_months=36, num_partners=6, countries=['DE', 'FR', 'ES', 'PL', 'IT', 'NL'])"
            ]
        ))

        # Timeline generator tool (proposal planning)
        self.register_tool(Tool(
            name="generate_timeline",
            description="Generate a project timeline with work packages, deliverables, and milestones for a Horizon Europe proposal. Based on best practices from funded projects.",
            category=ToolCategory.STATISTICS,
            parameters={
                "action_type": "Required: Action type (RIA, IA, CSA, ERC)",
                "duration_months": "Required: Project duration in months",
                "num_partners": "Required: Number of partners",
                "total_person_months": "Required: Total effort in person-months",
                "project_title": "Optional: Project title for naming",
                "start_date": "Optional: Start date (YYYY-MM-DD)"
            },
            examples=[
                "generate_timeline(action_type='RIA', duration_months=36, num_partners=8, total_person_months=300)",
                "generate_timeline(action_type='IA', duration_months=48, num_partners=12, total_person_months=500, project_title='GreenHydrogen')"
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

        # Start speculative execution for likely-needed tools
        speculative_tasks = {}
        if self.speculative_executor:
            try:
                speculative_tasks = await self.speculative_executor.start_speculative_execution(
                    query=query,
                    context=context
                )
                if speculative_tasks:
                    logger.info(f"🔮 Started speculative execution for {len(speculative_tasks)} tool(s)")
            except Exception as e:
                logger.warning(f"Speculative execution failed to start: {e}")
        
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

                # Collect results - use unique keys for each tool call
                for idx, tc in enumerate(step.tool_calls):
                    if tc.success:
                        # Use iteration_idx format to ensure uniqueness when same tool called multiple times
                        all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result

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

        # Cancel any unused speculative tasks
        if self.speculative_executor:
            used_tools = set()
            for step in plan.reasoning_steps:
                for tc in step.tool_calls:
                    used_tools.add(tc.tool_name)
            self.speculative_executor.cancel_unused_speculation(used_tools)

        # Cache the first step's plan if query was successful
        if self.plan_cache and plan.reasoning_steps and plan.final_answer:
            first_step = plan.reasoning_steps[0] if plan.reasoning_steps else None
            if first_step and first_step.tool_calls:
                # Build a cacheable plan from the first step
                first_plan = {
                    'thought': first_step.thought,
                    'action': 'call_tools',
                    'tool_calls': [
                        {
                            'tool': tc.tool_name,
                            'parameters': tc.parameters,
                            'reasoning': tc.reasoning
                        }
                        for tc in first_step.tool_calls
                    ],
                    'needs_more_info': first_step.next_action_needed
                }
                # Use confidence as quality score
                self.plan_cache.cache_plan(
                    query=query,
                    plan=first_plan,
                    context=context,
                    quality_score=plan.confidence or 0.8
                )

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
            'tool_results': all_tool_results,  # Include full tool results for formatting
            'complexity': plan.complexity,
            'iterations': iteration,
            'confidence': plan.confidence,
            'total_time_ms': total_time
        }

    async def process_query_streaming(
        self,
        query: str,
        context: str = "",
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
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

        Yields:
            Dict events as processing happens
        """
        start_time = datetime.now()

        # Initialize plan
        plan = AgentPlan(
            query=query,
            complexity=self._assess_complexity(query),
            required_sources=self._identify_required_sources(query)
        )

        logger.info(f"🧠 [Streaming] Query complexity: {plan.complexity}, sources needed: {plan.required_sources}")

        # Start speculative execution for likely-needed tools
        if self.speculative_executor:
            try:
                speculative_tasks = await self.speculative_executor.start_speculative_execution(
                    query=query,
                    context=context
                )
                if speculative_tasks:
                    logger.info(f"🔮 Started speculative execution for {len(speculative_tasks)} tool(s)")
            except Exception as e:
                logger.warning(f"Speculative execution failed to start: {e}")

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

            # YIELD: Agent thinking event immediately
            yield {
                'type': 'agent_thinking',
                'iteration': iteration,
                'thought': step.thought,
                'action': step.action
            }

            # Handle different actions
            if step.action == 'call_tools':
                tool_calls = reasoning_result.get('tool_calls', [])

                # YIELD: Tool call events before execution
                for tc in tool_calls:
                    tool_name = tc.get('tool', '')
                    parameters = tc.get('parameters', {})
                    yield {
                        'type': 'tool_call',
                        'iteration': iteration,
                        'tool_name': tool_name,
                        'parameters': parameters,
                        'reasoning': tc.get('reasoning', '')
                    }

                # Execute tool calls
                step.tool_calls = await self._execute_tool_calls(tool_calls)

                # YIELD: Tool result events after execution
                for idx, tc in enumerate(step.tool_calls):
                    result_count = self._count_results(tc.result) if tc.success else 0
                    yield {
                        'type': 'tool_result',
                        'iteration': iteration,
                        'tool_name': tc.tool_name,
                        'success': tc.success,
                        'result_count': result_count,
                        'result_summary': str(tc.result)[:300] if tc.result else 'No results',
                        'execution_time_ms': tc.execution_time_ms
                    }

                    if tc.success:
                        # Use iteration_idx format to ensure uniqueness when same tool called multiple times
                        all_tool_results[f"{tc.tool_name}_{iteration}_{idx}"] = tc.result

                step.observation = self._summarize_tool_results(step.tool_calls)
                step.next_action_needed = reasoning_result.get('needs_more_info', True)

            elif step.action == 'analyze_results':
                step.observation = reasoning_result.get('analysis', '')
                step.next_action_needed = reasoning_result.get('needs_more_info', False)

            elif step.action == 'conclude':
                plan.final_answer = reasoning_result.get('conclusion', '')
                plan.confidence = reasoning_result.get('confidence', 0.8)
                step.next_action_needed = False

            plan.reasoning_steps.append(step)

            # Check if we should stop
            if not step.next_action_needed:
                logger.info(f"✅ [Streaming] Agent concluded after {iteration} iteration(s)")
                break

        # Build final response
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # Cancel any unused speculative tasks
        if self.speculative_executor:
            used_tools = set()
            for step in plan.reasoning_steps:
                for tc in step.tool_calls:
                    used_tools.add(tc.tool_name)
            self.speculative_executor.cancel_unused_speculation(used_tools)

        # Cache the first step's plan if successful
        if self.plan_cache and plan.reasoning_steps and plan.final_answer:
            first_step = plan.reasoning_steps[0] if plan.reasoning_steps else None
            if first_step and first_step.tool_calls:
                first_plan = {
                    'thought': first_step.thought,
                    'action': 'call_tools',
                    'tool_calls': [
                        {
                            'tool': tc.tool_name,
                            'parameters': tc.parameters,
                            'reasoning': tc.reasoning
                        }
                        for tc in first_step.tool_calls
                    ],
                    'needs_more_info': first_step.next_action_needed
                }
                self.plan_cache.cache_plan(
                    query=query,
                    plan=first_plan,
                    context=context,
                    quality_score=plan.confidence or 0.8
                )

        # YIELD: Final complete event with full result
        final_result = {
            'answer': plan.final_answer or self._build_fallback_answer(plan),
            'success': plan.final_answer is not None,
            'reasoning_steps': [
                {
                    'step': s.step_number,
                    'thought': s.thought,
                    'action': s.action,
                    'tools_called': [tc.tool_name for tc in s.tool_calls],
                    'observation': s.observation[:500] if s.observation else ''
                }
                for s in plan.reasoning_steps
            ],
            'sources_used': list(all_tool_results.keys()),
            'tool_results': all_tool_results,
            'complexity': plan.complexity,
            'iterations': iteration,
            'confidence': plan.confidence,
            'total_time_ms': total_time
        }

        yield {
            'type': 'agent_complete',
            'result': final_result
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

    def _count_results(self, result: Any) -> Optional[int]:
        """Count the number of results from a tool response."""
        if result is None:
            return 0
        if isinstance(result, dict):
            # Check for common result count keys
            for key in ['count', 'total', 'total_results', 'projects_count', 'calls_found']:
                if key in result:
                    return int(result[key])
            # Check for list-like keys
            for key in ['results', 'projects', 'calls', 'documents', 'partners', 'organizations']:
                if key in result and isinstance(result[key], list):
                    return len(result[key])
        if isinstance(result, list):
            return len(result)
        return None

    async def _reason_next_step(
        self,
        query: str,
        context: str,
        previous_steps: List[ReasoningStep],
        tool_results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to reason about the next step."""

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
        
        # Build prompt
        prompt = self.REASONING_PROMPT.format(
            built_in_knowledge=self.BUILT_IN_KNOWLEDGE,
            tools_description=self._get_tools_description(),
            query=query,
            context=context or "No additional context",
            previous_steps=steps_text or "This is the first step",
            tool_results=results_text or "No tool results yet"
        )
        
        # LLM timeout in seconds (configurable via env, default 30s)
        import os
        llm_timeout = int(os.getenv('LLM_TIMEOUT_SECONDS', '30'))

        try:
            if self.llm:
                # Wrap LLM call with timeout protection
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(self.llm.generate_content, prompt),
                        timeout=llm_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ LLM call timed out after {llm_timeout}s, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results)

                # Parse JSON from response
                response_text = response.text

                # Extract JSON block - try multiple patterns for robustness
                json_str = None

                # Pattern 1: Fenced JSON block
                json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)

                # Pattern 2: Any fenced code block (might not have 'json' marker)
                if not json_str:
                    json_match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
                    if json_match:
                        potential_json = json_match.group(1).strip()
                        if potential_json.startswith('{'):
                            json_str = potential_json

                # Pattern 3: Raw JSON object
                if not json_str:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    json_str = json_match.group(0) if json_match else None

                if not json_str:
                    logger.warning("Could not extract JSON from LLM response, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results)

                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as je:
                    # Try to fix common JSON issues
                    fixed_json = self._fix_malformed_json(json_str)
                    if fixed_json:
                        return fixed_json
                    logger.warning(f"JSON decode failed: {je}, using fallback")
                    return self._fallback_reasoning(query, previous_steps, tool_results)
            else:
                # Fallback reasoning
                return self._fallback_reasoning(query, previous_steps, tool_results)

        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            return self._fallback_reasoning(query, previous_steps, tool_results)

    def _fix_malformed_json(self, json_str: str) -> Optional[Dict[str, Any]]:
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
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)

        # Fix single quotes to double quotes (but not inside strings)
        # This is a simplified fix - may not work for all cases
        if "'" in fixed and '"' not in fixed:
            fixed = fixed.replace("'", '"')

        # Remove control characters
        fixed = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', fixed)

        # Try to extract just the JSON object if there's extra text
        obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', fixed, re.DOTALL)
        if obj_match:
            fixed = obj_match.group(0)

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    def _fallback_reasoning(
        self,
        query: str,
        previous_steps: List[ReasoningStep],
        tool_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback reasoning when LLM fails."""

        if not previous_steps:
            # First step - call basic search with more results
            return {
                'thought': 'Starting with document search to gather information',
                'action': 'call_tools',
                'tool_calls': [{
                    'tool': 'search_documents',
                    'parameters': {'query': query, 'max_results': 15},  # Increased from 5
                    'reasoning': 'Initial search for relevant information'
                }],
                'needs_more_info': True
            }

        if tool_results:
            # Have results - synthesize a proper answer
            # Extract and synthesize content from results
            synthesized_content = self._synthesize_from_results(query, tool_results)

            return {
                'thought': 'Have gathered information, synthesizing answer',
                'action': 'conclude',
                'conclusion': synthesized_content,
                'confidence': 0.7,
                'needs_more_info': False
            }

        return {
            'thought': 'Unable to gather more information',
            'action': 'conclude',
            'conclusion': 'I was unable to find specific information to answer this question. Please try rephrasing your question or asking about a more specific topic.',
            'confidence': 0.3,
            'needs_more_info': False
        }

    def _synthesize_from_results(self, query: str, tool_results: Dict[str, Any]) -> str:
        """Synthesize a coherent answer from tool results."""
        import json
        content_pieces = []

        for name, result in tool_results.items():
            if not isinstance(result, dict):
                continue

            # Extract documents
            if 'documents' in result and isinstance(result['documents'], list):
                for doc in result['documents'][:10]:
                    content = doc.get('content', '')
                    if content and len(content) > 100:
                        content_pieces.append(content.strip())

            # Extract calls info
            elif 'calls' in result and isinstance(result['calls'], list):
                if len(result['calls']) == 0:
                    # Explicitly note that no calls were found
                    content_pieces.append("No open funding calls were found matching your search criteria. This could mean:\n- There are currently no open calls in this topic area\n- Relevant calls may have already closed\n- Upcoming calls may not yet be announced\n\nConsider checking the Horizon Europe Funding & Tenders Portal for the latest information.")
                else:
                    for call in result['calls'][:10]:
                        title = call.get('title', '')
                        call_id = call.get('topic_code', call.get('call_id', ''))
                        if title or call_id:
                            content_pieces.append(f"Call {call_id}: {title}")

            # Extract budget calculation results
            elif result.get('tool_name') == 'calculate_budget' and result.get('success'):
                breakdown = result.get('breakdown', {})
                budget = result.get('calculated_budget', {})
                per_partner = result.get('per_partner', {})

                budget_text = f"""Budget Calculation Results:
- Total Budget: €{budget.get('total_cost', 0):,.0f}
- EU Contribution: €{budget.get('eu_contribution', 0):,.0f} ({budget.get('funding_rate', '100%')})

Breakdown:
- Personnel: €{breakdown.get('personnel', {}).get('amount', 0):,.0f} ({breakdown.get('personnel', {}).get('percentage', 0)}%)
- Equipment: €{breakdown.get('equipment', {}).get('amount', 0):,.0f} ({breakdown.get('equipment', {}).get('percentage', 0)}%)
- Travel: €{breakdown.get('travel', {}).get('amount', 0):,.0f} ({breakdown.get('travel', {}).get('percentage', 0)}%)
- Subcontracting: €{breakdown.get('subcontracting', {}).get('amount', 0):,.0f} ({breakdown.get('subcontracting', {}).get('percentage', 0)}%)
- Other Direct Costs: €{breakdown.get('other_direct', {}).get('amount', 0):,.0f} ({breakdown.get('other_direct', {}).get('percentage', 0)}%)
- Indirect Costs (25% flat rate): €{breakdown.get('indirect', {}).get('amount', 0):,.0f} ({breakdown.get('indirect', {}).get('percentage', 0)}%)

Per Partner Distribution:
- Average per partner: €{per_partner.get('average', 0):,.0f}
- Coordinator (typical): €{per_partner.get('coordinator_typical', 0):,.0f}
- Other partners (typical): €{per_partner.get('partner_typical', 0):,.0f}
"""
                content_pieces.append(budget_text)

            # Extract call details - ENHANCED with full description
            elif result.get('call_id') and result.get('title'):
                call_parts = []
                call_parts.append(f"## Call Details: {result.get('call_id')}\n")
                call_parts.append(f"**Title:** {result.get('title')}")
                call_parts.append(f"**Status:** {result.get('status', 'Unknown')}")
                call_parts.append(f"**Type:** {result.get('type', 'N/A')}")
                call_parts.append(f"**Deadline:** {result.get('deadline', 'N/A')}")

                # Full description without truncation
                description = result.get('description', '')
                if description:
                    # Clean HTML tags if present
                    import re
                    clean_desc = re.sub(r'<[^>]+>', ' ', description)
                    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                    call_parts.append(f"\n**Description:**\n{clean_desc}")

                # Add expected outcomes if available
                expected_outcomes = result.get('expected_outcomes', [])
                if expected_outcomes:
                    call_parts.append("\n**Expected Outcomes:**")
                    for outcome in expected_outcomes[:10]:
                        call_parts.append(f"- {outcome}")

                # Add scope if available
                scope = result.get('scope', '')
                if scope and scope != description:
                    clean_scope = re.sub(r'<[^>]+>', ' ', scope)
                    clean_scope = re.sub(r'\s+', ' ', clean_scope).strip()
                    call_parts.append(f"\n**Scope:**\n{clean_scope}")

                content_pieces.append('\n'.join(call_parts))

            # Extract statistics/benchmark results
            elif result.get('statistics') or result.get('benchmark'):
                stats = result.get('statistics', result.get('benchmark', {}))
                content_pieces.append(f"Statistics: {json.dumps(stats, indent=2, default=str)[:1000]}")

            # Extract timeline generation results - ENHANCED with full details
            elif result.get('tool_name') == 'generate_timeline' and result.get('success'):
                wps = result.get('work_packages', [])
                deliverables = result.get('deliverables', [])
                milestones = result.get('milestones', [])
                params = result.get('parameters', {})
                gantt = result.get('gantt_data', {})
                recommendations = result.get('recommendations', [])

                timeline_parts = []
                timeline_parts.append("## Project Timeline Generated\n")
                timeline_parts.append(f"**Project Parameters:**")
                timeline_parts.append(f"- Duration: {params.get('duration_months', 36)} months")
                timeline_parts.append(f"- Action Type: {params.get('action_type', 'RIA')}")
                timeline_parts.append(f"- Partners: {params.get('num_partners', 8)}")
                timeline_parts.append(f"- Total Effort: {params.get('total_person_months', 0)} person-months")
                timeline_parts.append("")

                # Work Packages with full details
                timeline_parts.append("### Work Packages\n")
                for wp in wps:
                    wp_num = wp.get('number', 0)
                    title = wp.get('title', '')
                    lead = wp.get('lead', 'P1')
                    participants = wp.get('participants', [])
                    start = wp.get('start_month', 1)
                    end = wp.get('end_month', 36)
                    effort = wp.get('effort_pms', 0)
                    objective = wp.get('objective', '')
                    tasks = wp.get('tasks', [])

                    timeline_parts.append(f"**WP{wp_num}: {title}**")
                    timeline_parts.append(f"- Lead: {lead} | Participants: {', '.join(participants[:4]) if participants else 'All'}")
                    timeline_parts.append(f"- Duration: M{start} - M{end} ({end - start + 1} months)")
                    timeline_parts.append(f"- Effort: {effort} person-months")
                    if objective:
                        timeline_parts.append(f"- Objective: *{objective}*")
                    if tasks:
                        timeline_parts.append(f"- Tasks: {'; '.join(tasks[:4])}")
                    timeline_parts.append("")

                # Deliverables
                if deliverables:
                    timeline_parts.append(f"### Deliverables ({len(deliverables)} total)\n")
                    for d in deliverables[:15]:
                        d_id = d.get('id', d.get('seq_id', 'D?'))
                        d_title = d.get('title', '')[:60]
                        d_month = d.get('due_month', 0)
                        d_type = d.get('type', 'R')
                        d_level = d.get('dissemination_level', 'PU')
                        timeline_parts.append(f"- **{d_id}**: {d_title} (M{d_month}, {d_type}, {d_level})")
                    if len(deliverables) > 15:
                        timeline_parts.append(f"- ... and {len(deliverables) - 15} more deliverables")
                    timeline_parts.append("")

                # Milestones
                if milestones:
                    timeline_parts.append(f"### Milestones ({len(milestones)} total)\n")
                    for m in milestones:
                        m_id = m.get('id', 'MS?')
                        m_title = m.get('title', '')
                        m_month = m.get('due_month', 0)
                        timeline_parts.append(f"- **{m_id}**: {m_title} (M{m_month})")
                    timeline_parts.append("")

                # ASCII Gantt Chart
                ascii_chart = gantt.get('ascii_chart', '')
                if ascii_chart:
                    timeline_parts.append("### Gantt Chart\n")
                    timeline_parts.append("```")
                    timeline_parts.append(ascii_chart)
                    timeline_parts.append("```")
                    timeline_parts.append("")

                # WP Dependencies
                dependencies = gantt.get('dependencies', [])
                if dependencies:
                    timeline_parts.append("### WP Dependencies\n")
                    for dep in dependencies[:6]:
                        timeline_parts.append(f"- {dep.get('from')} → {dep.get('to')}: {dep.get('description', '')}")
                    timeline_parts.append("")

                # Recommendations
                if recommendations:
                    timeline_parts.append("### Recommendations\n")
                    for rec in recommendations[:5]:
                        timeline_parts.append(f"- {rec}")

                content_pieces.append('\n'.join(timeline_parts))

            # Extract similar projects results - ENHANCED with full details
            elif 'similar_projects' in result and isinstance(result.get('similar_projects'), list):
                projects = result['similar_projects']
                query_desc = result.get('query_description', '')
                matches = result.get('matches_found', len(projects))
                filters = result.get('filters_applied', {})

                if not projects:
                    content_pieces.append(f"## Similar Projects Search\n\nNo projects found matching: *{query_desc}*")
                else:
                    similar_parts = []
                    similar_parts.append(f"## Similar Funded Projects\n")
                    similar_parts.append(f"**Query:** {query_desc}")
                    if filters:
                        filter_str = ", ".join([f"{k}: {v}" for k, v in filters.items() if v])
                        if filter_str:
                            similar_parts.append(f"**Filters:** {filter_str}")
                    similar_parts.append(f"**Found:** {matches} similar projects\n")

                    for i, p in enumerate(projects[:10], 1):
                        acronym = p.get('acronym', 'N/A')
                        title = p.get('title', 'N/A')
                        score = p.get('similarity_score', 0)
                        budget = p.get('eu_contribution', p.get('total_cost', 0))
                        consortium = p.get('consortium', {})
                        size = consortium.get('size', p.get('partner_count', 0))
                        action_type = p.get('action_type', 'N/A')
                        objective = p.get('objective', '')
                        start_date = p.get('start_date', '')
                        end_date = p.get('end_date', '')
                        coordinator = consortium.get('coordinator', {}).get('name', '')
                        cluster = p.get('cluster', '')

                        budget_str = f"€{budget/1_000_000:.1f}M" if budget > 0 else "N/A"

                        similar_parts.append(f"### {i}. {acronym} [{score:.0%} match]")
                        similar_parts.append(f"**{title}**")
                        similar_parts.append(f"- Type: {action_type} | Budget: {budget_str} | Partners: {size}")
                        if cluster:
                            similar_parts.append(f"- Cluster: {cluster}")
                        if start_date and end_date:
                            similar_parts.append(f"- Duration: {start_date[:7]} to {end_date[:7]}")
                        if coordinator:
                            similar_parts.append(f"- Coordinator: {coordinator}")
                        if objective:
                            obj_preview = objective[:300] + "..." if len(objective) > 300 else objective
                            similar_parts.append(f"- Objective: *{obj_preview}*")
                        similar_parts.append("")

                    # Add insights
                    insights = result.get('insights', [])
                    if insights:
                        similar_parts.append("**Key Insights:**")
                        for insight in insights[:5]:
                            similar_parts.append(f"- {insight}")

                    content_pieces.append('\n'.join(similar_parts))

            # Extract project results
            elif 'projects' in result and isinstance(result['projects'], list):
                for proj in result['projects'][:5]:
                    acronym = proj.get('acronym', '')
                    title = proj.get('title', '')
                    if acronym or title:
                        content_pieces.append(f"Project {acronym}: {title}")

            # Extract country statistics results
            elif 'country_code' in result and 'eligibility' in result:
                country = result.get('country', result.get('country_code', 'Unknown'))
                eligibility = result.get('eligibility', {})
                top_orgs = result.get('top_organizations', [])

                # Get participation history from eligibility
                participation = eligibility.get('participation_history', {})
                org_count = participation.get('organization_count', result.get('organization_count', 0))
                proj_count = participation.get('project_count', 0)
                total_funding = participation.get('total_funding_received', 0)

                # Build clear eligibility answer first
                is_eligible = eligibility.get('is_eligible', False)
                eligibility_status = eligibility.get('eligibility_status', 'Unknown')

                country_text = f"""Country: {country}
**Can participate in Horizon Europe: {'YES' if is_eligible else 'NO'}**
- Status: {eligibility_status}"""

                # Add notes if available
                notes = eligibility.get('notes', [])
                if notes:
                    country_text += f"\n- {notes[0]}"

                # Add participation stats
                if proj_count > 0:
                    country_text += f"""

Participation Statistics:
- Organizations Participating: {org_count:,}
- Projects Involved: {proj_count:,}
- Total Funding Received: €{total_funding:,.0f}"""

                if top_orgs:
                    country_text += f"\n\nTop Organizations ({len(top_orgs)} shown):"
                    for org in top_orgs[:10]:
                        org_name = org.get('name', org.get('organization_name', 'Unknown'))
                        org_projects = org.get('project_count', org.get('projects', 0))
                        org_funding = org.get('total_funding', org.get('funding', 0))
                        country_text += f"\n- {org_name}: {org_projects} projects, €{org_funding:,.0f}"

                content_pieces.append(country_text)

            # Extract programme/cluster statistics results
            elif 'cluster_code' in result or ('programme' in result and 'statistics' in result):
                programme = result.get('programme', result.get('cluster_code', 'Unknown'))
                programme_type = result.get('programme_type', '')
                stats = result.get('statistics', {})
                budget = result.get('budget_details', {})

                programme_text = f"""Programme Statistics for {programme}:"""
                if programme_type:
                    programme_text += f"\n({programme_type})"

                # Handle EIC/ERC/MSCA format with success_rates dict
                if 'success_rates' in stats:
                    success_rates = stats['success_rates']
                    programme_text += f"\n\n{stats.get('description', '')}\n"
                    programme_text += "\nSuccess Rates:"
                    for key, value in success_rates.items():
                        if key != 'note':
                            programme_text += f"\n- {key.replace('_', ' ').title()}: {value}"
                    if success_rates.get('note'):
                        programme_text += f"\n\nNote: {success_rates['note']}"

                    # Add funding info
                    if 'funding' in stats:
                        programme_text += "\n\nFunding Available:"
                        for key, value in stats['funding'].items():
                            programme_text += f"\n- {key.replace('_', ' ').title()}: {value}"

                    # Add eligibility
                    if stats.get('eligibility'):
                        programme_text += f"\n\nEligibility: {stats['eligibility']}"

                    if stats.get('trl_range'):
                        programme_text += f"\nTRL Range: {stats['trl_range']}"

                    # Add evaluation criteria
                    if stats.get('evaluation_criteria'):
                        programme_text += "\n\nEvaluation Criteria:"
                        for criterion in stats['evaluation_criteria']:
                            programme_text += f"\n- {criterion}"
                else:
                    # Standard cluster statistics format
                    if stats:
                        total_projects = stats.get('total_projects', stats.get('project_count', 'N/A'))
                        total_funding = stats.get('total_funding', stats.get('total_budget', 0))
                        avg_budget = stats.get('avg_project_budget', stats.get('average_funding', 0))

                        programme_text += f"""
- Total Projects: {total_projects:,}""" if isinstance(total_projects, int) else f"""
- Total Projects: {total_projects}"""
                        programme_text += f"""
- Total Funding: €{total_funding:,.0f}
- Success Rate: {stats.get('success_rate', 'N/A')}%
- Average Project Budget: €{avg_budget:,.0f}"""

                    if budget:
                        programme_text += f"""

Budget Breakdown:
- Min Budget: €{budget.get('min_budget', 0):,.0f}
- Max Budget: €{budget.get('max_budget', 0):,.0f}
- Median Budget: €{budget.get('median_budget', 0):,.0f}"""

                content_pieces.append(programme_text)

            # Extract call history analysis results
            elif result.get('tool_name') == 'analyze_call_history' or ('timeline' in result and 'trends' in result):
                query_params = result.get('query_params', {})
                keywords = query_params.get('keywords', 'specified criteria')
                cluster = query_params.get('cluster', '')

                calls_analyzed = result.get('calls_analyzed', 0)
                projects_funded = result.get('projects_funded', 0)
                total_funding = result.get('total_funding_allocated', 0)
                timeline = result.get('timeline', {})
                trends = result.get('trends', {})
                top_topics = result.get('top_funded_topics', [])
                sample_projects = result.get('sample_funded_projects', [])
                recommendations = result.get('recommendations', [])

                # Build header
                search_desc = keywords if keywords else (f"Cluster {cluster}" if cluster else "Horizon Europe")
                history_text = f"""## Funding History Analysis: {search_desc}

**Overview:**
- Calls Analyzed: {calls_analyzed}
- Projects Funded: {projects_funded:,}
- Total Funding: €{total_funding/1_000_000_000:.2f} billion
"""

                # Add trend info
                funding_trend = trends.get('funding_trend', 'unknown')
                yoy_growth = trends.get('year_over_year_funding_growth', 0)
                if funding_trend and funding_trend != 'insufficient_data':
                    history_text += f"- Funding Trend: {funding_trend.replace('_', ' ').title()} ({yoy_growth:+.1f}% YoY)\n"

                # Add timeline
                if timeline:
                    history_text += "\n**Funding by Year:**\n"
                    sorted_years = sorted(timeline.keys(), reverse=True)
                    for year in sorted_years[:5]:
                        data = timeline[year]
                        year_projects = data.get('projects_funded', 0)
                        year_funding = data.get('total_funding', 0)
                        avg_budget = data.get('avg_project_budget', 0)
                        history_text += f"- **{year}**: {year_projects:,} projects, €{year_funding/1_000_000:.0f}M total (avg €{avg_budget/1_000_000:.1f}M/project)\n"

                # Add top topics
                if top_topics:
                    history_text += "\n**Top Funded Topics:**\n"
                    for topic in top_topics[:5]:
                        topic_name = topic.get('topic', topic.get('name', 'N/A'))
                        topic_projects = topic.get('projects', topic.get('count', 0))
                        topic_funding = topic.get('total_funding', 0)
                        if topic_funding > 0:
                            history_text += f"- {topic_name}: {topic_projects} projects, €{topic_funding/1_000_000:.0f}M\n"
                        else:
                            history_text += f"- {topic_name}: {topic_projects} projects\n"

                # Add sample projects
                if sample_projects:
                    history_text += "\n**Sample Funded Projects:**\n"
                    for proj in sample_projects[:5]:
                        acronym = proj.get('acronym', 'N/A')
                        title = proj.get('title', '')[:60]
                        budget = proj.get('budget', proj.get('ec_contribution', 0))
                        history_text += f"- **{acronym}**: {title}... (€{budget/1_000_000:.1f}M)\n"

                # Add recommendations
                if recommendations:
                    history_text += "\n**Recommendations:**\n"
                    for rec in recommendations[:3]:
                        history_text += f"- {rec}\n"

                content_pieces.append(history_text)

            # Extract partner discovery results
            elif result.get('tool_name') == 'find_experienced_partners' or 'experienced_partners' in result:
                partners = result.get('experienced_partners', [])
                total_found = result.get('total_found', 0)
                query_params = result.get('query_params', {})
                keywords = query_params.get('topic_keywords', 'specified criteria')

                if not partners and total_found == 0:
                    partner_text = f"""Partner Search Results for '{keywords}':
No organizations found matching your criteria.

Suggestions:
- Try broader keywords (e.g., "energy storage" instead of "solid-state battery")
- Remove the cluster filter to search across all Horizon Europe
- Reduce the minimum projects requirement
- Try searching for related topics"""
                    content_pieces.append(partner_text)
                else:
                    partner_text = f"""Found {total_found} organizations with experience in '{keywords}':

"""
                    for p in partners[:10]:
                        name = p.get('short_name') or p.get('name', 'Unknown')
                        country = p.get('country', 'N/A')
                        org_type = p.get('type', 'N/A')
                        track = p.get('track_record', {})
                        relevant = track.get('relevant_projects', 0)
                        coord = track.get('as_coordinator', 0)
                        total_funding = track.get('total_funding', 0)

                        partner_text += f"• **{name}** ({country}, {org_type})\n"
                        partner_text += f"  - Relevant projects: {relevant}"
                        if coord > 0:
                            partner_text += f" ({coord} as coordinator)"
                        partner_text += f"\n  - Total funding: €{total_funding:,.0f}\n\n"

                    # Add insights if available
                    insights = result.get('aggregated_insights', {})
                    if insights.get('top_countries_in_topic'):
                        partner_text += f"Top countries for this topic: {', '.join(insights['top_countries_in_topic'][:5])}\n"
                    if insights.get('top_org_types'):
                        partner_text += f"Common organization types: {', '.join(insights['top_org_types'][:3])}\n"

                    content_pieces.append(partner_text)

        if not content_pieces:
            return "I found some information but couldn't extract specific details. Please try a more specific question."

        # Combine and deduplicate content
        unique_content = []
        seen = set()
        for piece in content_pieces:
            key = piece[:100].lower()
            if key not in seen:
                seen.add(key)
                unique_content.append(piece)

        # Build a structured response
        # Check for special formatted outputs that should bypass the "Finding X:" wrapper
        # These are detailed outputs that should be returned directly without truncation

        # Markers for detailed content types - prioritize similar projects over call details
        # (since user wants similar projects, not just call info)
        direct_output_markers_priority = [
            '## Similar Funded Projects',  # Highest priority - what user wants
            '## Similar Projects Search',
            '## Project Timeline Generated',
            '## Funding History Analysis:',
            '## Call Details:',  # Lower priority - context, not main answer
        ]

        # Collect ALL content pieces with direct output markers
        direct_outputs = []
        regular_content = []

        for content in unique_content:
            is_direct = False
            for marker in direct_output_markers_priority:
                if marker in content:
                    direct_outputs.append((marker, content))
                    is_direct = True
                    break
            if not is_direct:
                regular_content.append(content)

        # If we have direct outputs, combine them (prioritizing similar projects)
        if direct_outputs:
            # Sort by priority (lower index = higher priority)
            direct_outputs.sort(key=lambda x: direct_output_markers_priority.index(x[0]) if x[0] in direct_output_markers_priority else 999)

            # Combine all direct outputs
            combined_parts = []
            for marker, content in direct_outputs:
                combined_parts.append(content)

            return "\n\n---\n\n".join(combined_parts)

        intro = f"Based on my search for information about '{query}', here's what I found:\n\n"

        # Take top pieces and format
        body_parts = []
        for i, content in enumerate(unique_content[:5], 1):
            # Truncate long pieces (use higher limit for statistics and detailed results)
            is_detailed = any(k in content.lower() for k in ['statistics', 'eligibility', 'organizations', 'funding', 'timeline', 'work package', 'deliverable', 'milestone', 'gantt', 'similar', 'call details', 'budget'])
            max_len = 8000 if is_detailed else 1500
            if len(content) > max_len:
                content = content[:max_len] + "..."
            body_parts.append(f"**Finding {i}:**\n{content}")

        return intro + "\n\n".join(body_parts)
    
    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[ToolCall]:
        """Execute multiple tool calls (in parallel when possible).

        If speculative execution is enabled, check for pre-computed results first.
        """
        results = []

        # Group calls that need execution vs those with speculative results
        to_execute = []
        used_speculative = set()

        for tc in tool_calls:
            tool_name = tc.get('tool')
            params = tc.get('parameters', {})
            reasoning = tc.get('reasoning', '')

            tool_call = ToolCall(
                tool_name=tool_name,
                parameters=params,
                reasoning=reasoning
            )

            # Check for speculative result first (with param validation)
            speculative_result = None
            if self.speculative_executor:
                speculative_result = await self.speculative_executor.get_speculative_result(
                    tool_name,
                    timeout=0.2,  # 200ms timeout for speculative results
                    requested_params=params  # Pass params for compatibility check
                )

            if speculative_result and speculative_result.get('result') is not None:
                # Use speculative result
                tool_call.success = True
                tool_call.result = speculative_result['result']
                tool_call.execution_time_ms = 0  # Already computed
                results.append(tool_call)
                used_speculative.add(tool_name)
                logger.info(f"🎯 Using speculative result for: {tool_name}")

                # Track speculative hit in analytics
                if self.analytics:
                    from ..analytics.tool_analytics_service import ToolUsageEvent
                    await self.analytics.track_tool_usage(ToolUsageEvent(
                        tool_name=tool_name,
                        parameters=params,
                        execution_time_ms=0,
                        success=True,
                        speculative=True,
                        result_count=self._count_results(speculative_result['result'])
                    ))
            else:
                # Need to execute normally
                to_execute.append((tool_call, self._execute_single_tool(tool_name, params)))

        # Execute remaining tools in parallel
        if to_execute:
            start_time = datetime.now()

            tasks = [call[1] for call in to_execute]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, (tool_call, _) in enumerate(to_execute):
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

                # Track in analytics
                if self.analytics:
                    from ..analytics.tool_analytics_service import ToolUsageEvent
                    await self.analytics.track_tool_usage(ToolUsageEvent(
                        tool_name=tool_call.tool_name,
                        parameters=tool_call.parameters,
                        execution_time_ms=int(execution_time),
                        success=tool_call.success,
                        error_message=tool_call.error if not tool_call.success else None,
                        result_count=self._count_results(result) if tool_call.success else None,
                        speculative=False
                    ))

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
            elif tool_name == 'get_budget_benchmark':
                return await self._tool_get_budget_benchmark(params)
            elif tool_name == 'get_consortium_patterns':
                return await self._tool_get_consortium_patterns(params)
            elif tool_name == 'find_experienced_partners':
                return await self._tool_find_experienced_partners(params)
            elif tool_name == 'get_similar_funded_projects':
                return await self._tool_get_similar_funded_projects(params)
            elif tool_name == 'analyze_call_history':
                return await self._tool_analyze_call_history(params)
            elif tool_name == 'calculate_budget':
                return await self._tool_calculate_budget(params)
            elif tool_name == 'generate_timeline':
                return await self._tool_generate_timeline(params)
            else:
                return {"error": f"Tool {tool_name} not implemented"}
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}
    
    # ==================== Tool Implementations ====================
    
    async def _tool_get_programme_stats(self, params: Dict) -> Dict:
        """Get programme/cluster statistics from graph DB."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()

            programme = params.get('programme', '')
            programme_lower = programme.lower()

            # Map programme names to cluster codes (Neo4j uses CLUSTER-X format)
            cluster_map = {
                'cluster 5': 'CLUSTER-5',
                'cluster-5': 'CLUSTER-5',
                'cl5': 'CLUSTER-5',
                'climate': 'CLUSTER-5',
                'energy': 'CLUSTER-5',
                'mobility': 'CLUSTER-5',
                'cluster 4': 'CLUSTER-4',
                'cluster-4': 'CLUSTER-4',
                'cl4': 'CLUSTER-4',
                'digital': 'CLUSTER-4',
                'industry': 'CLUSTER-4',
                'space': 'CLUSTER-4',
                'cluster 6': 'CLUSTER-6',
                'cluster-6': 'CLUSTER-6',
                'cl6': 'CLUSTER-6',
                'food': 'CLUSTER-6',
                'bioeconomy': 'CLUSTER-6',
                'agriculture': 'CLUSTER-6',
                'cluster 1': 'CLUSTER-1',
                'cluster-1': 'CLUSTER-1',
                'cl1': 'CLUSTER-1',
                'health': 'CLUSTER-1',
                'cluster 2': 'CLUSTER-2',
                'cluster-2': 'CLUSTER-2',
                'cl2': 'CLUSTER-2',
                'culture': 'CLUSTER-2',
                'creativity': 'CLUSTER-2',
                'cluster 3': 'CLUSTER-3',
                'cluster-3': 'CLUSTER-3',
                'cl3': 'CLUSTER-3',
                'security': 'CLUSTER-3',
            }

            # Handle EIC/ERC/MSCA separately - these are pillars, not clusters
            # Return known statistics from official EC sources
            if 'eic' in programme_lower or 'accelerator' in programme_lower:
                return {
                    "programme": "EIC Accelerator",
                    "programme_type": "Pillar 3 - Innovative Europe",
                    "statistics": {
                        "description": "EIC Accelerator supports high-risk, high-impact SMEs and startups with breakthrough innovations",
                        "success_rates": {
                            "overall": "2-5%",
                            "short_proposal_to_full": "~25-30%",
                            "full_proposal_to_interview": "~20-25%",
                            "interview_to_funding": "~50-60%",
                            "note": "Success rates vary by cut-off date and are highly competitive"
                        },
                        "funding": {
                            "grant_only": "Up to €2.5 million",
                            "blended_finance": "Up to €2.5M grant + up to €15M equity",
                            "equity_only": "Up to €15 million"
                        },
                        "eligibility": "Single SMEs (including startups) from EU/Associated Countries",
                        "trl_range": "TRL 5-9 (close to market)",
                        "evaluation_criteria": [
                            "Excellence (Breakthrough innovation, Technology readiness)",
                            "Impact (Market potential, Scalability, Team capability)",
                            "Implementation (Business plan, Milestones, Resources)",
                            "Level of risk and need for EU support"
                        ]
                    },
                    "source": "official_ec_data"
                }

            if 'erc' in programme_lower:
                return {
                    "programme": "European Research Council (ERC)",
                    "programme_type": "Pillar 1 - Excellent Science",
                    "statistics": {
                        "description": "ERC funds frontier research by individual investigators",
                        "success_rates": {
                            "starting_grant": "~10-15%",
                            "consolidator_grant": "~12-15%",
                            "advanced_grant": "~10-12%",
                            "synergy_grant": "~8-10%",
                            "proof_of_concept": "~35-40%"
                        },
                        "funding": {
                            "starting_grant": "Up to €1.5M for 5 years",
                            "consolidator_grant": "Up to €2M for 5 years",
                            "advanced_grant": "Up to €2.5M for 5 years",
                            "synergy_grant": "Up to €10M for 6 years (2-4 PIs)"
                        },
                        "eligibility": "Researchers at any career stage hosted by EU/AC institutions",
                        "evaluation_criteria": [
                            "Excellence of the PI (track record, scientific leadership)",
                            "Excellence of the research project (groundbreaking nature, methodology)"
                        ]
                    },
                    "source": "official_ec_data"
                }

            if 'msca' in programme_lower or 'marie' in programme_lower or 'curie' in programme_lower:
                return {
                    "programme": "Marie Skłodowska-Curie Actions (MSCA)",
                    "programme_type": "Pillar 1 - Excellent Science",
                    "statistics": {
                        "description": "MSCA supports researcher mobility, training and career development",
                        "success_rates": {
                            "postdoctoral_fellowships": "~12-15%",
                            "doctoral_networks": "~8-12%",
                            "staff_exchanges": "~25-30%",
                            "cofund": "~20-25%",
                            "citizens": "Varied (outreach programme)"
                        },
                        "funding": {
                            "postdoctoral_fellowships": "Living allowance + mobility + research costs",
                            "doctoral_networks": "Up to €360,000/researcher"
                        },
                        "eligibility": "Researchers at all career stages, with mobility requirements",
                        "evaluation_criteria": [
                            "Excellence (Quality of research/training)",
                            "Impact (Career development, Knowledge transfer)",
                            "Implementation (Work plan, Management)"
                        ]
                    },
                    "source": "official_ec_data"
                }

            # Try to find a matching cluster code for Pillar 2 clusters
            cluster_code = None
            for key, code in cluster_map.items():
                if key in programme_lower:
                    cluster_code = code
                    break

            # Get cluster statistics from Neo4j
            result = await asyncio.to_thread(
                graph.get_cluster_statistics,
                cluster_code
            )

            if result:
                # Also get budget statistics for more detail
                budget_stats = await asyncio.to_thread(
                    graph.get_budget_statistics,
                    cluster_code
                )

                # Combine results
                return {
                    "programme": programme,
                    "cluster_code": cluster_code,
                    "statistics": result,
                    "budget_details": budget_stats,
                    "source": "neo4j_graph"
                }

            return {"message": f"No statistics found for {programme}. Try specific cluster names (e.g., 'Cluster 5 - Climate', 'Health') or programmes (EIC, ERC, MSCA)."}
        except Exception as e:
            logger.error(f"Programme stats error: {e}")
            return {"error": str(e)}
    
    async def _tool_get_country_stats(self, params: Dict) -> Dict:
        """Get country statistics from graph DB."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()

            country = params.get('country', '')

            # Try to extract country code from input
            country_codes = {
                'germany': 'DE', 'german': 'DE',
                'france': 'FR', 'french': 'FR',
                'italy': 'IT', 'italian': 'IT',
                'spain': 'ES', 'spanish': 'ES',
                'netherlands': 'NL', 'dutch': 'NL',
                'belgium': 'BE', 'belgian': 'BE',
                'austria': 'AT', 'austrian': 'AT',
                'sweden': 'SE', 'swedish': 'SE',
                'denmark': 'DK', 'danish': 'DK',
                'finland': 'FI', 'finnish': 'FI',
                'ireland': 'IE', 'irish': 'IE',
                'portugal': 'PT', 'portuguese': 'PT',
                'greece': 'GR', 'greek': 'GR',
                'poland': 'PL', 'polish': 'PL',
                'switzerland': 'CH', 'swiss': 'CH',
                'norway': 'NO', 'norwegian': 'NO',
                'uk': 'GB', 'united kingdom': 'GB', 'britain': 'GB', 'british': 'GB',
                'israel': 'IL', 'israeli': 'IL',
            }

            country_code = None
            country_lower = country.lower()

            # First check if it's already a code (2 letters)
            if len(country) == 2:
                country_code = country.upper()
            else:
                for name, code in country_codes.items():
                    if name in country_lower:
                        country_code = code
                        break

            if not country_code:
                return {"message": f"Could not identify country code for '{country}'. Try using ISO codes like DE, FR, IT."}

            # Get eligibility info
            eligibility = await asyncio.to_thread(
                graph.check_country_eligibility,
                country_code
            )

            # Get top organizations in that country
            top_orgs = await asyncio.to_thread(
                graph.get_top_organizations,
                None,  # no cluster filter
                country_code,
                10  # limit
            )

            return {
                "country": country,
                "country_code": country_code,
                "eligibility": eligibility,
                "top_organizations": top_orgs,
                "organization_count": len(top_orgs),
                "source": "neo4j_graph"
            }
        except Exception as e:
            logger.error(f"Country stats error: {e}")
            return {"error": str(e)}
    
    async def _tool_compare_programmes(self, params: Dict) -> Dict:
        """Compare two programmes/clusters."""
        try:
            from ..data_intelligence.graph_service import GraphSearchService
            graph = GraphSearchService()

            prog_a = params.get('programme_a', '')
            prog_b = params.get('programme_b', '')

            # Use the same cluster mapping as get_programme_stats (Neo4j uses CLUSTER-X format)
            cluster_map = {
                'cluster 5': 'CLUSTER-5', 'cluster-5': 'CLUSTER-5', 'cl5': 'CLUSTER-5',
                'climate': 'CLUSTER-5', 'energy': 'CLUSTER-5', 'mobility': 'CLUSTER-5',
                'cluster 4': 'CLUSTER-4', 'cluster-4': 'CLUSTER-4', 'cl4': 'CLUSTER-4',
                'digital': 'CLUSTER-4', 'industry': 'CLUSTER-4', 'space': 'CLUSTER-4',
                'cluster 6': 'CLUSTER-6', 'cluster-6': 'CLUSTER-6', 'cl6': 'CLUSTER-6',
                'food': 'CLUSTER-6', 'bioeconomy': 'CLUSTER-6', 'agriculture': 'CLUSTER-6',
                'cluster 1': 'CLUSTER-1', 'cluster-1': 'CLUSTER-1', 'cl1': 'CLUSTER-1', 'health': 'CLUSTER-1',
                'cluster 2': 'CLUSTER-2', 'cluster-2': 'CLUSTER-2', 'cl2': 'CLUSTER-2',
                'culture': 'CLUSTER-2', 'creativity': 'CLUSTER-2',
                'cluster 3': 'CLUSTER-3', 'cluster-3': 'CLUSTER-3', 'cl3': 'CLUSTER-3', 'security': 'CLUSTER-3',
                'eic': 'EIC', 'eic accelerator': 'EIC', 'erc': 'ERC', 'msca': 'MSCA', 'marie curie': 'MSCA',
                'ria': 'RIA', 'ia': 'IA', 'csa': 'CSA',
            }

            def get_cluster_code(prog: str) -> Optional[str]:
                prog_lower = prog.lower()
                for key, code in cluster_map.items():
                    if key in prog_lower:
                        return code
                return None

            code_a = get_cluster_code(prog_a)
            code_b = get_cluster_code(prog_b)

            # Get statistics for both
            stats_a = await asyncio.to_thread(graph.get_cluster_statistics, code_a)
            stats_b = await asyncio.to_thread(graph.get_cluster_statistics, code_b)

            return {
                "comparison": {
                    prog_a: {
                        "cluster_code": code_a,
                        "statistics": stats_a[0] if stats_a else None
                    },
                    prog_b: {
                        "cluster_code": code_b,
                        "statistics": stats_b[0] if stats_b else None
                    }
                },
                "source": "neo4j_graph"
            }
        except Exception as e:
            logger.error(f"Compare programmes error: {e}")
            return {"error": str(e)}
    
    async def _tool_search_documents(self, params: Dict) -> Dict:
        """Search documents using vector search."""
        try:
            from ..vector_search_service import VectorSearchService
            vector = VectorSearchService()

            query = params.get('query', '')
            max_results = params.get('max_results', 15)  # Increased default from 5
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
                        "content": r.content[:1500] if hasattr(r, 'content') else str(r)[:1500],  # Increased from 300
                        "source": r.document_title if hasattr(r, 'document_title') else 'Unknown',
                        "title": r.document_title if hasattr(r, 'document_title') else '',
                        "section": r.section if hasattr(r, 'section') else '',
                        "score": r.score if hasattr(r, 'score') else 0
                    }
                    for r in results[:max_results]
                ]
            }
        except Exception as e:
            return {"error": str(e)}

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

            # Pass through ALL available fields for rich formatting
            return {
                "calls_found": len(calls),
                "calls": [
                    {
                        "call_id": c.get('topic_code', ''),  # topic_code is the actual call ID
                        "title": c.get('title', ''),
                        "deadline": c.get('deadline', ''),
                        "type": c.get('action_type', ''),
                        "cluster": c.get('cluster', ''),
                        "budget": c.get('budget', ''),
                        "scope": c.get('scope', '') or c.get('description', ''),
                        "expected_outcome": c.get('expected_outcome', ''),
                        "status": c.get('status', 'open'),
                        "url": c.get('url', ''),
                        "work_programme": c.get('work_programme', ''),
                        "call_year": c.get('call_year', ''),
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

            logger.info(f"🔍 Getting call details for: {call_id}")

            from ..local_call_search_service import LocalCallSearchService
            call_service = LocalCallSearchService()

            # First try the dedicated get_call_details method (includes API enrichment)
            call_details = call_service.get_call_details(call_id)

            # Check if we got valid data (not just empty dict)
            if call_details and (call_details.get('topic_code') or call_details.get('title')):
                logger.info(f"✅ Got call details: {call_details.get('topic_code')} - {call_details.get('title', '')[:50]}")
                return {
                    "call_id": call_details.get('topic_code'),
                    "title": call_details.get('title'),
                    "description": call_details.get('scope') or call_details.get('description', ''),
                    "expected_outcome": call_details.get('expected_outcome', ''),
                    "deadline": str(call_details.get('deadline')) if call_details.get('deadline') else None,
                    "type": call_details.get('action_type'),
                    "cluster": call_details.get('cluster'),
                    "budget": call_details.get('budget'),
                    "status": call_details.get('status'),
                    "url": call_details.get('url') or call_details.get('portal_url'),
                }

            # Fallback: Search for the call using keywords
            # Include closed calls since user is looking for a specific call ID
            logger.info(f"🔎 Fallback: Searching for {call_id}...")
            results = call_service.search_calls(
                query=call_id,
                num_results=10,
                include_closed=True  # Include closed calls when looking up specific call IDs
            )

            calls = results.get('calls', [])
            logger.info(f"Search returned {len(calls)} results")

            for call in calls:
                # Check both topic_code and call_id fields
                topic_code = call.get('topic_code', '') or ''
                if call_id.upper() in topic_code.upper():
                    logger.info(f"✅ Found matching call: {topic_code}")
                    return {
                        "call_id": topic_code,
                        "title": call.get('title'),
                        "description": call.get('scope') or call.get('description', ''),
                        "expected_outcome": call.get('expected_outcome', ''),
                        "deadline": str(call.get('deadline')) if call.get('deadline') else None,
                        "type": call.get('action_type'),
                        "cluster": call.get('cluster'),
                        "budget": call.get('budget'),
                        "status": call.get('status'),
                        "url": call.get('url') or call.get('portal_url'),
                    }

            # If still not found, try searching with just the base call identifier
            # e.g., HORIZON-CL5-2026-02-D4-01 -> search for "HORIZON-CL5-2026"
            if '-' in call_id:
                parts = call_id.split('-')
                if len(parts) >= 4:
                    base_call = '-'.join(parts[:4])  # e.g., HORIZON-CL5-2026-02
                    logger.info(f"🔎 Trying base call search: {base_call}")
                    results = call_service.search_calls(query=base_call, num_results=15, include_closed=True)
                    calls = results.get('calls', [])
                    for call in calls:
                        topic_code = call.get('topic_code', '') or ''
                        if call_id.upper() in topic_code.upper() or topic_code.upper() in call_id.upper():
                            logger.info(f"✅ Found via base search: {topic_code}")
                            return {
                                "call_id": topic_code,
                                "title": call.get('title'),
                                "description": call.get('scope') or call.get('description', ''),
                                "expected_outcome": call.get('expected_outcome', ''),
                                "deadline": str(call.get('deadline')) if call.get('deadline') else None,
                                "type": call.get('action_type'),
                                "cluster": call.get('cluster'),
                                "budget": call.get('budget'),
                                "status": call.get('status'),
                                "url": call.get('url') or call.get('portal_url'),
                            }

            logger.warning(f"❌ No details found for {call_id} in local searches")

            # Last resort: Try direct API fetch via enrichment service
            logger.info(f"🌐 Trying direct EU Portal API fetch for {call_id}...")
            try:
                from ..call_enrichment_service import CallEnrichmentService
                from app.core.config import settings
                enrichment = CallEnrichmentService(settings.database_url)
                api_result = enrichment.get_call_details(call_id, force_refresh=True)
                if api_result and (api_result.get('topic_code') or api_result.get('title')):
                    logger.info(f"✅ Found {call_id} via direct API fetch!")
                    return {
                        "call_id": api_result.get('topic_code') or call_id,
                        "title": api_result.get('title'),
                        "description": api_result.get('scope') or api_result.get('description', ''),
                        "expected_outcome": api_result.get('expected_outcome', ''),
                        "deadline": str(api_result.get('deadline')) if api_result.get('deadline') else None,
                        "type": api_result.get('action_type'),
                        "cluster": api_result.get('cluster'),
                        "budget": api_result.get('budget') or api_result.get('budget_total'),
                        "status": api_result.get('status'),
                        "url": api_result.get('portal_url') or f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id}",
                    }
                else:
                    logger.info(f"⚠️ Direct API fetch returned no valid data for {call_id}")
            except Exception as api_err:
                logger.warning(f"Direct API fetch failed: {api_err}")

            # Try to find similar calls to suggest
            similar_calls = []
            if '-' in call_id:
                parts = call_id.split('-')
                # Search for calls in the same cluster/year
                if len(parts) >= 3:
                    search_term = '-'.join(parts[:3])  # e.g., HORIZON-CL5-2026
                    results = call_service.search_calls(query=search_term, num_results=5, include_closed=True)
                    for call in results.get('calls', [])[:5]:
                        topic_code = call.get('topic_code', '')
                        title = call.get('title', '')
                        if topic_code and title:
                            similar_calls.append(f"- {topic_code}: {title[:60]}...")

            if similar_calls:
                suggestions = "\n".join(similar_calls)
                return {
                    "message": f"Call ID '{call_id}' was not found. This may be an invalid or incomplete call ID.\n\n**Similar calls you might be looking for:**\n{suggestions}\n\nYou can also check the EU Portal directly.",
                    "similar_calls": similar_calls
                }
            else:
                return {"message": f"No details found for {call_id}. This call ID may be invalid or not yet in our database. Please verify the call ID format (e.g., HORIZON-CL5-2026-02-D3-01) and try again, or check the EU Funding & Tenders Portal directly."}
        except Exception as e:
            logger.error(f"Get call details error: {e}")
            import traceback
            traceback.print_exc()
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

    async def _tool_get_budget_benchmark(self, params: Dict) -> Dict:
        """Get budget benchmarks from funded Horizon Europe projects."""
        try:
            from ..tools.budget_benchmark import BudgetBenchmarkTool

            tool = BudgetBenchmarkTool()
            result = tool.get_benchmark(
                cluster=params.get('cluster'),
                action_type=params.get('action_type'),
                topic_keywords=params.get('topic_keywords'),
                year=params.get('year')
            )

            return result

        except Exception as e:
            logger.error(f"Budget benchmark error: {e}")
            return {"error": str(e)}

    async def _tool_get_consortium_patterns(self, params: Dict) -> Dict:
        """Get consortium composition patterns from funded projects."""
        try:
            from ..tools.consortium_patterns import ConsortiumPatternsTool

            tool = ConsortiumPatternsTool()
            result = tool.get_patterns(
                cluster=params.get('cluster'),
                action_type=params.get('action_type'),
                topic_keywords=params.get('topic_keywords'),
                min_projects=params.get('min_projects', 10)
            )

            return result

        except Exception as e:
            logger.error(f"Consortium patterns error: {e}")
            return {"error": str(e)}

    async def _tool_find_experienced_partners(self, params: Dict) -> Dict:
        """Find experienced partners for consortium building."""
        try:
            from ..tools.partner_discovery import PartnerDiscoveryTool

            tool = PartnerDiscoveryTool()
            result = tool.find_partners(
                topic_keywords=params.get('topic_keywords', params.get('keywords', '')),
                country=params.get('country'),
                organization_type=params.get('organization_type'),
                cluster=params.get('cluster'),
                min_projects=params.get('min_projects', 2),
                role_filter=params.get('role_filter'),
                limit=params.get('limit', 20)
            )

            return result

        except Exception as e:
            logger.error(f"Partner discovery error: {e}")
            return {"error": str(e)}

    async def _tool_get_similar_funded_projects(self, params: Dict) -> Dict:
        """Find funded projects semantically similar to a description."""
        try:
            from ..tools.similar_projects import SimilarProjectsTool

            tool = SimilarProjectsTool()
            result = tool.find_similar(
                description=params.get('description', ''),
                cluster=params.get('cluster'),
                action_type=params.get('action_type'),
                min_budget=params.get('min_budget'),
                max_budget=params.get('max_budget'),
                year_from=params.get('year_from'),
                limit=params.get('limit', 10),
                similarity_threshold=params.get('similarity_threshold', 0.3)
            )

            return result

        except Exception as e:
            logger.error(f"Similar projects error: {e}")
            return {"error": str(e)}

    async def _tool_analyze_call_history(self, params: Dict) -> Dict:
        """Analyze historical funding patterns for Horizon Europe topics.

        Supports expand_scope parameter for broader searches (projects USING a technology
        rather than just focusing on it).
        """
        try:
            from ..tools.call_history import CallHistoryTool

            tool = CallHistoryTool()
            result = tool.analyze_history(
                topic_pattern=params.get('topic_pattern'),
                cluster=params.get('cluster'),
                keywords=params.get('keywords'),
                year_from=params.get('year_from'),
                year_to=params.get('year_to'),
                action_types=params.get('action_types'),
                include_projects=params.get('include_projects', True),
                expand_scope=params.get('expand_scope', False),  # NEW: AI-powered keyword expansion
                limit=params.get('limit', 50)
            )

            return result

        except Exception as e:
            logger.error(f"Call history analysis error: {e}")
            return {"error": str(e)}

    async def _tool_calculate_budget(self, params: Dict) -> Dict:
        """Calculate budget breakdown for a Horizon Europe proposal."""
        try:
            from ..tools.budget_calculator import BudgetCalculatorTool

            tool = BudgetCalculatorTool()
            result = tool.calculate_budget(
                action_type=params.get('action_type', 'RIA'),
                duration_months=params.get('duration_months', 36),
                num_partners=params.get('num_partners', 8),
                total_person_months=params.get('total_person_months'),
                target_budget=params.get('target_budget'),
                countries=params.get('countries'),
                include_breakdown=params.get('include_breakdown', True)
            )

            return result

        except Exception as e:
            logger.error(f"Budget calculator error: {e}")
            return {"error": str(e)}

    async def _tool_generate_timeline(self, params: Dict) -> Dict:
        """Generate project timeline with work packages, deliverables, and milestones."""
        try:
            from ..tools.timeline_generator import TimelineGeneratorTool

            tool = TimelineGeneratorTool()
            result = tool.generate_timeline(
                action_type=params.get('action_type', 'RIA'),
                duration_months=params.get('duration_months', 36),
                num_partners=params.get('num_partners', 8),
                total_person_months=params.get('total_person_months', 300),
                project_title=params.get('project_title', 'Project'),
                custom_wps=params.get('custom_wps'),
                start_date=params.get('start_date')
            )

            return result

        except Exception as e:
            logger.error(f"Timeline generator error: {e}")
            return {"error": str(e)}

    def _summarize_tool_results(self, tool_calls: List[ToolCall]) -> str:
        """Summarize results from tool calls in a human-readable format."""
        summaries = []

        for tc in tool_calls:
            if tc.success:
                result = tc.result
                summary = self._format_tool_result_summary(tc.tool_name, result)
                summaries.append(summary)
            else:
                summaries.append(f"{tc.tool_name}: Failed - {tc.error}")

        return "\n".join(summaries)

    def _format_tool_result_summary(self, tool_name: str, result: Any) -> str:
        """Format a single tool result into a readable summary."""
        if not isinstance(result, dict):
            return f"{tool_name}: {str(result)[:500]}"

        # Handle document search results
        if 'documents' in result and isinstance(result['documents'], list):
            docs = result['documents']
            if not docs:
                return f"{tool_name}: No documents found"

            # Extract actual content from documents
            content_parts = []
            for doc in docs[:8]:  # Increased from 3 to 8
                content = doc.get('content', '')
                source = doc.get('source', doc.get('title', 'Unknown'))
                if content:
                    # Clean up the content
                    content = content.strip()[:800]  # Increased from 400
                    content_parts.append(f"From {source}: {content}")

            if content_parts:
                return f"Found {len(docs)} relevant document(s):\n" + "\n\n".join(content_parts)
            return f"{tool_name}: Found {len(docs)} documents (no content extracted)"

        # Handle funding call results
        if 'calls' in result and isinstance(result['calls'], list):
            calls = result['calls']
            if not calls:
                return f"{tool_name}: No funding calls found"
            return f"Found {len(calls)} funding call(s)"

        # Handle project results
        if 'projects' in result and isinstance(result['projects'], list):
            projects = result['projects']
            if not projects:
                return f"{tool_name}: No projects found"
            return f"Found {len(projects)} project(s)"

        # Handle call details
        if 'call_id' in result or 'topic_code' in result:
            call_id = result.get('call_id') or result.get('topic_code')
            title = result.get('title', 'Unknown')
            if call_id and title:
                desc = result.get('description', '')[:200] if result.get('description') else ''
                return f"Call {call_id}: {title}\n{desc}" if desc else f"Call {call_id}: {title}"
            elif result.get('message'):
                return result['message']

        # Handle budget benchmark results
        if 'statistics' in result and 'total_eu_contribution' in result.get('statistics', {}):
            stats = result['statistics']
            contrib = stats.get('total_eu_contribution', {})
            consortium = stats.get('consortium_size', {})
            recs = result.get('recommendations', {})

            parts = [f"Budget Benchmark Analysis ({stats.get('projects_analyzed', 'N/A')} projects):"]

            if contrib:
                avg = contrib.get('average', 0)
                median = contrib.get('median', 0)
                parts.append(f"- EU Contribution: €{median/1_000_000:.1f}M median, €{avg/1_000_000:.1f}M average")
                parts.append(f"- Range: €{contrib.get('min', 0)/1_000_000:.1f}M - €{contrib.get('max', 0)/1_000_000:.1f}M")

            if consortium:
                parts.append(f"- Consortium Size: {consortium.get('median', 0):.0f} partners (avg: {consortium.get('average', 0):.1f})")

            if recs:
                parts.append(f"- Recommended Budget: {recs.get('suggested_budget_range', 'N/A')}")
                parts.append(f"- Recommended Partners: {recs.get('suggested_consortium_size', 'N/A')}")

            return "\n".join(parts)

        # Handle consortium patterns results
        if 'organization_type_distribution' in result and 'consortium_size' in result:
            projects = result.get('projects_analyzed', 'N/A')
            consortium = result.get('consortium_size', {})
            org_dist = result.get('organization_type_distribution', {})
            country_patterns = result.get('country_patterns', {})
            recs = result.get('recommendations', {})

            parts = [f"Consortium Patterns Analysis ({projects} projects):"]

            # Consortium size
            if consortium:
                parts.append(f"- Consortium Size: {consortium.get('median', 0):.0f} partners (avg: {consortium.get('average', 0):.1f})")
                parts.append(f"- Recommended: {consortium.get('recommended', 'N/A')}")

            # Org type distribution
            if org_dist:
                type_parts = []
                for org_type, data in sorted(org_dist.items(), key=lambda x: x[1].get('percentage', 0), reverse=True)[:4]:
                    pct = data.get('percentage', 0)
                    type_parts.append(f"{org_type}: {pct:.0f}%")
                parts.append(f"- Organization Mix: {', '.join(type_parts)}")

            # Top countries
            top_countries = country_patterns.get('top_participating', [])[:5]
            if top_countries:
                countries = [c['country'] for c in top_countries]
                parts.append(f"- Top Countries: {', '.join(countries)}")

            # Geographic diversity
            geo = country_patterns.get('geographic_diversity', {})
            if geo:
                parts.append(f"- Avg Countries per Project: {geo.get('avg_countries', 'N/A')}")

            # Recommendations
            if recs.get('ideal_composition'):
                parts.append(f"- Ideal Mix: {'; '.join(recs['ideal_composition'][:3])}")

            return "\n".join(parts)

        # Handle partner discovery results
        if 'experienced_partners' in result:
            partners = result.get('experienced_partners', [])
            total = result.get('total_found', 0)
            query = result.get('query_params', {})

            if not partners:
                return f"Partner Discovery: No organizations found matching '{query.get('topic_keywords', '')}'"

            parts = [f"Found {total} experienced partners for '{query.get('topic_keywords', '')}':"]

            for p in partners[:5]:
                name = p.get('short_name') or p.get('name', 'Unknown')
                country = p.get('country', '')
                org_type = p.get('type', '')
                track = p.get('track_record', {})
                relevant = track.get('relevant_projects', 0)
                coord = track.get('as_coordinator', 0)
                score = p.get('experience_score', 0)

                coord_str = f", {coord} as coordinator" if coord > 0 else ""
                parts.append(f"- {name} ({country}, {org_type}): {relevant} relevant projects{coord_str} [score: {score}]")

            insights = result.get('aggregated_insights', {})
            if insights.get('top_countries_in_topic'):
                parts.append(f"\nTop countries: {', '.join(insights['top_countries_in_topic'][:5])}")

            return "\n".join(parts)

        # Handle similar projects results - ENHANCED with full details
        if 'similar_projects' in result and isinstance(result['similar_projects'], list):
            projects = result['similar_projects']
            query_desc = result.get('query_description', '')
            matches = result.get('matches_found', len(projects))
            filters = result.get('filters_applied', {})

            if not projects:
                return f"## Similar Projects Search\n\nNo projects found matching: *{query_desc}*"

            parts = []
            parts.append(f"## Similar Funded Projects\n")
            parts.append(f"**Query:** {query_desc}")
            if filters:
                filter_str = ", ".join([f"{k}: {v}" for k, v in filters.items() if v])
                if filter_str:
                    parts.append(f"**Filters:** {filter_str}")
            parts.append(f"**Found:** {matches} similar projects\n")

            for i, p in enumerate(projects[:10], 1):
                acronym = p.get('acronym', 'N/A')
                title = p.get('title', 'N/A')
                score = p.get('similarity_score', 0)
                budget = p.get('eu_contribution', p.get('total_cost', 0))
                consortium = p.get('consortium', {})
                size = consortium.get('size', p.get('partner_count', 0))
                action_type = p.get('action_type', 'N/A')
                objective = p.get('objective', '')
                start_date = p.get('start_date', '')
                end_date = p.get('end_date', '')
                coordinator = consortium.get('coordinator', {}).get('name', '')
                cluster = p.get('cluster', '')

                budget_str = f"€{budget/1_000_000:.1f}M" if budget > 0 else "N/A"

                parts.append(f"### {i}. {acronym} [{score:.0%} match]")
                parts.append(f"**{title}**")
                parts.append(f"- Type: {action_type} | Budget: {budget_str} | Partners: {size}")
                if cluster:
                    parts.append(f"- Cluster: {cluster}")
                if start_date and end_date:
                    parts.append(f"- Duration: {start_date[:7]} to {end_date[:7]}")
                if coordinator:
                    parts.append(f"- Coordinator: {coordinator}")
                if objective:
                    # Show first 300 chars of objective
                    obj_preview = objective[:300] + "..." if len(objective) > 300 else objective
                    parts.append(f"- Objective: *{obj_preview}*")
                parts.append("")

            # Add insights
            insights = result.get('insights', [])
            if insights:
                parts.append("**Key Insights:**")
                for insight in insights[:5]:
                    parts.append(f"- {insight}")

            return "\n".join(parts)

        # Handle timeline generator results
        if 'work_packages' in result and 'deliverables' in result and 'milestones' in result:
            wps = result.get('work_packages', [])
            deliverables = result.get('deliverables', [])
            milestones = result.get('milestones', [])
            params = result.get('parameters', {})
            summary = result.get('summary', {})
            gantt = result.get('gantt_data', {})

            parts = []
            parts.append(f"**Project Timeline Generated**")
            parts.append(f"- Duration: {params.get('duration_months', 36)} months")
            parts.append(f"- Action Type: {params.get('action_type', 'RIA')}")
            parts.append(f"- Partners: {params.get('num_partners', 8)}")
            parts.append(f"- Total Effort: {params.get('total_person_months', 0)} person-months")
            parts.append("")

            # Work Packages Summary
            parts.append("**Work Packages:**")
            for wp in wps:
                wp_num = wp.get('number', 0)
                title = wp.get('title', '')
                lead = wp.get('lead', 'P1')
                start = wp.get('start_month', 1)
                end = wp.get('end_month', 36)
                effort = wp.get('effort_pms', 0)
                objective = wp.get('objective', '')

                parts.append(f"\n**WP{wp_num}: {title}** (Lead: {lead})")
                parts.append(f"  M{start}-M{end} | {effort} PMs")
                if objective:
                    parts.append(f"  *{objective[:100]}*")

                # Show tasks
                tasks = wp.get('tasks', [])
                if tasks:
                    parts.append(f"  Tasks: {'; '.join(tasks[:3])}")

            # Deliverables
            parts.append("")
            parts.append(f"**Deliverables ({len(deliverables)} total):**")
            for d in deliverables[:10]:  # Show first 10
                d_id = d.get('id', 'D?')
                d_title = d.get('title', '')[:50]
                d_month = d.get('due_month', 0)
                d_type = d.get('type', 'R')
                d_level = d.get('dissemination_level', 'PU')
                parts.append(f"  {d_id}: {d_title} (M{d_month}, {d_type}, {d_level})")

            if len(deliverables) > 10:
                parts.append(f"  ... and {len(deliverables) - 10} more")

            # Milestones
            parts.append("")
            parts.append(f"**Milestones ({len(milestones)} total):**")
            for m in milestones:
                m_id = m.get('id', 'MS?')
                m_title = m.get('title', '')
                m_month = m.get('due_month', 0)
                parts.append(f"  {m_id}: {m_title} (M{m_month})")

            # ASCII Gantt Chart
            ascii_chart = gantt.get('ascii_chart', '')
            if ascii_chart:
                parts.append("")
                parts.append("**Gantt Chart:**")
                parts.append("```")
                parts.append(ascii_chart)
                parts.append("```")

            # Dependencies
            dependencies = gantt.get('dependencies', [])
            if dependencies:
                parts.append("")
                parts.append("**WP Dependencies:**")
                for dep in dependencies[:5]:
                    parts.append(f"  {dep.get('from')} → {dep.get('to')}: {dep.get('description', '')}")

            # Recommendations
            recommendations = result.get('recommendations', [])
            if recommendations:
                parts.append("")
                parts.append("**Recommendations:**")
                for rec in recommendations[:4]:
                    parts.append(f"  - {rec}")

            return "\n".join(parts)

        # Handle call history analysis results
        if 'timeline' in result and 'trends' in result:
            calls = result.get('calls_analyzed', 0)
            projects = result.get('projects_funded', 0)
            total_funding = result.get('total_funding_allocated', 0)
            trends = result.get('trends', {})

            parts = [f"Call History Analysis: {calls} calls, {projects} projects funded"]

            if total_funding > 0:
                parts.append(f"Total funding: €{total_funding/1_000_000_000:.1f}B")

            # Trend info
            trend = trends.get('funding_trend', 'unknown')
            growth = trends.get('year_over_year_funding_growth', 0)
            if trend != 'insufficient_data':
                parts.append(f"Trend: {trend.replace('_', ' ')} ({growth:+.1f}% YoY)")

            # Timeline summary
            timeline = result.get('timeline', {})
            if timeline:
                years = sorted(timeline.keys(), reverse=True)[:3]
                for year in years:
                    data = timeline[year]
                    parts.append(f"  {year}: {data.get('projects_funded', 0)} projects, €{data.get('total_funding', 0)/1_000_000:.0f}M")

            # Top topics
            top_topics = result.get('top_funded_topics', [])[:3]
            if top_topics:
                parts.append("\nTop topics:")
                for t in top_topics:
                    parts.append(f"  - {t.get('topic', 'N/A')}: {t.get('projects', 0)} projects")

            # Recommendations
            recommendations = result.get('recommendations', [])[:2]
            if recommendations:
                parts.append(f"\nRecommendations: {'; '.join(recommendations)}")

            return "\n".join(parts)

        # Handle country statistics results
        if 'country_code' in result and 'eligibility' in result:
            country = result.get('country', result.get('country_code', 'Unknown'))
            eligibility = result.get('eligibility', {})
            top_orgs = result.get('top_organizations', [])

            # Get participation history from eligibility
            participation = eligibility.get('participation_history', {})
            org_count = participation.get('organization_count', result.get('organization_count', 0))
            proj_count = participation.get('project_count', 0)
            total_funding = participation.get('total_funding_received', 0)

            # Build clear eligibility answer first
            is_eligible = eligibility.get('is_eligible', False)
            eligibility_status = eligibility.get('eligibility_status', 'Unknown')

            parts = [f"Country: {country}"]
            parts.append(f"**Can participate in Horizon Europe: {'YES' if is_eligible else 'NO'}**")
            parts.append(f"- Status: {eligibility_status}")

            # Add notes if available
            notes = eligibility.get('notes', [])
            if notes:
                parts.append(f"- {notes[0]}")

            if proj_count > 0:
                parts.append(f"\nParticipation Statistics:")
                parts.append(f"- Organizations: {org_count:,}")
                parts.append(f"- Projects: {proj_count:,}")
                parts.append(f"- Total Funding: €{total_funding:,.0f}")

            if top_orgs:
                parts.append(f"\nTop {min(len(top_orgs), 10)} Organizations:")
                for org in top_orgs[:10]:
                    org_name = org.get('name', org.get('organization_name', 'Unknown'))
                    org_projects = org.get('project_count', org.get('projects', 0))
                    org_funding = org.get('total_funding', org.get('funding', 0))
                    parts.append(f"- {org_name}: {org_projects} projects, €{org_funding:,.0f}")

            return "\n".join(parts)

        # Handle programme/cluster statistics results
        if 'cluster_code' in result or ('programme' in result and 'statistics' in result):
            programme = result.get('programme', result.get('cluster_code', 'Unknown'))
            programme_type = result.get('programme_type', '')
            stats = result.get('statistics', {})
            # Ensure stats is a dict, not a list
            if isinstance(stats, list):
                stats = stats[0] if stats else {}
            budget = result.get('budget_details', {})

            parts = [f"Programme Statistics for {programme}:"]
            if programme_type:
                parts.append(f"({programme_type})")

            # Handle EIC/ERC/MSCA format with success_rates dict
            if 'success_rates' in stats:
                success_rates = stats['success_rates']
                if stats.get('description'):
                    parts.append(f"\n{stats['description']}")
                parts.append("\nSuccess Rates:")
                for key, value in success_rates.items():
                    if key != 'note':
                        parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                if success_rates.get('note'):
                    parts.append(f"\nNote: {success_rates['note']}")

                # Add funding info
                if 'funding' in stats:
                    parts.append("\nFunding Available:")
                    for key, value in stats['funding'].items():
                        parts.append(f"- {key.replace('_', ' ').title()}: {value}")

                if stats.get('eligibility'):
                    parts.append(f"\nEligibility: {stats['eligibility']}")

                if stats.get('trl_range'):
                    parts.append(f"TRL Range: {stats['trl_range']}")

            else:
                # Standard cluster statistics format
                if stats:
                    total_projects = stats.get('total_projects', stats.get('project_count', 'N/A'))
                    total_funding = stats.get('total_funding', stats.get('total_budget', 0))
                    success_rate = stats.get('success_rate', 'N/A')
                    avg_budget = stats.get('avg_project_budget', stats.get('average_funding', 0))

                    parts.append(f"- Total Projects: {total_projects:,}" if isinstance(total_projects, int) else f"- Total Projects: {total_projects}")
                    parts.append(f"- Total Funding: €{total_funding:,.0f}")
                    parts.append(f"- Success Rate: {success_rate}%")
                    parts.append(f"- Average Project Budget: €{avg_budget:,.0f}")

                if budget:
                    parts.append("\nBudget Breakdown:")
                    parts.append(f"- Min Budget: €{budget.get('min_budget', 0):,.0f}")
                    parts.append(f"- Max Budget: €{budget.get('max_budget', 0):,.0f}")
                    parts.append(f"- Median Budget: €{budget.get('median_budget', 0):,.0f}")

            return "\n".join(parts)

        # Handle error messages
        if 'error' in result:
            return f"{tool_name}: Error - {result['error']}"

        if 'message' in result:
            return f"{tool_name}: {result['message']}"

        # Default: truncated string representation
        return f"{tool_name}: {str(result)[:500]}"
    
    def _build_fallback_answer(self, plan: AgentPlan) -> str:
        """Build a fallback answer from collected information."""

        if not plan.reasoning_steps:
            return ""  # Return empty to trigger synthesis

        # Collect all tool results from steps
        all_results = {}
        for step in plan.reasoning_steps:
            for tc in step.tool_calls:
                if tc.success and tc.result:
                    all_results[tc.tool_name] = tc.result

        # If we have tool results, synthesize from them
        if all_results:
            return self._synthesize_from_results(plan.query, all_results)

        # Collect meaningful observations (skip raw tool results)
        meaningful_content = []

        for step in plan.reasoning_steps:
            if step.observation:
                obs = step.observation

                # Skip if it looks like raw JSON
                if obs.startswith("{") or obs.startswith("search_") or obs.startswith("get_"):
                    continue

                # Check if this is formatted document content
                if "Found " in obs and "relevant document" in obs:
                    # Extract the actual content from "From source: content" lines
                    lines = obs.split('\n')
                    for line in lines:
                        if line.startswith("From ") and ":" in line:
                            # Extract content after "From Source:"
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                content = parts[1].strip()
                                # Check content quality - skip truncated/malformed text
                                if self._is_quality_content(content):
                                    meaningful_content.append(content)
                elif self._is_quality_content(obs):
                    meaningful_content.append(obs)

        # Only return if we have quality content
        if meaningful_content:
            # Deduplicate similar content
            unique_content = self._deduplicate_content(meaningful_content)
            if unique_content:
                # Format as a proper answer
                intro = f"Based on the information I found about '{plan.query}':\n\n"
                formatted_content = []
                for i, content in enumerate(unique_content[:5], 1):
                    if len(content) > 500:
                        content = content[:500] + "..."
                    formatted_content.append(f"{content}")
                return intro + "\n\n".join(formatted_content)

        # Return empty to trigger LLM synthesis
        return ""

    def _is_quality_content(self, text: str) -> bool:
        """Check if text is quality content suitable for display."""
        if not text or len(text) < 50:
            return False

        # Check for truncated/malformed text patterns
        bad_patterns = [
            # Truncated words at start
            text[:20].count('  ') > 2,  # Multiple spaces
            text.startswith('rmance'),  # Cut-off word
            text.startswith('tion'),
            text.startswith('ing '),
            # Raw data patterns
            "{'documents'" in text,
            '{"documents"' in text,
            "'content':" in text,
            "'score':" in text,
            # Meta/structural content
            "Table of Contents" in text,
            "Page " in text and " of " in text,
        ]

        if any(bad_patterns):
            return False

        # Check for reasonable word structure
        words = text.split()
        if len(words) < 10:
            return False

        # Check that content has actual sentences (periods, capitals)
        if '.' not in text and '?' not in text:
            return False

        return True

    def _deduplicate_content(self, contents: list) -> list:
        """Remove duplicate or very similar content."""
        if not contents:
            return []

        unique = []
        for content in contents:
            # Check if this content is similar to any existing
            is_duplicate = False
            content_start = content[:100].lower()
            for existing in unique:
                existing_start = existing[:100].lower()
                if content_start == existing_start:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(content)

        return unique


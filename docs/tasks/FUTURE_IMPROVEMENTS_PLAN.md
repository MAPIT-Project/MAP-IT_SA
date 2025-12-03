# Future Improvements Implementation Plan

> **Created:** December 3, 2025
> **Status:** Planning Document
> **Estimated Total Effort:** 14-20 days

---

## Table of Contents

1. [Plan Caching for Repeated Query Patterns](#1-plan-caching-for-repeated-query-patterns)
2. [Parallel Execution Within Agentic Iterations](#2-parallel-execution-within-agentic-iterations)
3. [Add More Tools (Budget Calculator, Timeline Generator)](#3-add-more-tools)
4. [Implement Tool Usage Analytics](#4-implement-tool-usage-analytics)
5. [Add User Feedback Loop](#5-add-user-feedback-loop)
6. [Incremental Embedding Updates](#6-incremental-embedding-updates)
7. [V3 Project Formatter Enhancements](#7-v3-project-formatter-enhancements)

---

## 1. Plan Caching for Repeated Query Patterns

**Priority:** High | **Complexity:** Medium | **Estimated Time:** 2-3 days

### Current State

- Redis is already configured and used for Short-Term Memory (`app/services/memory/memory_service.py:23`)
- `ToolAwareAgent` makes LLM calls for reasoning at each iteration (`_reason_next_step()` line 797)
- No caching of query plans or tool selection decisions

### Problem Statement

Similar queries require redundant LLM reasoning to decide which tools to use. For example:
- "Find hydrogen funding calls" and "Find AI funding calls" both need `search_funding_calls`
- "What's the budget for RIA projects?" and "What's the budget for IA projects?" both use `get_budget_benchmark`

### Implementation Plan

#### Step 1: Create Query Plan Cache Service

**File:** `app/services/cache/query_plan_cache.py`

```python
"""
Query Plan Caching Service

Caches the reasoning/planning output for similar queries to avoid
redundant LLM calls for tool selection.
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
import redis
from datetime import timedelta

logger = logging.getLogger(__name__)


class QueryPlanCache:
    """Cache for query plans and tool selection decisions."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "query_plan:"
        self.ttl = timedelta(hours=24)  # Cache plans for 24 hours

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for cache key generation.
        - Lowercase
        - Remove extra whitespace
        - Sort words for order-independence (optional)
        """
        return ' '.join(query.lower().split())

    def _extract_query_pattern(self, query: str) -> str:
        """
        Extract a generalizable pattern from the query.
        Replace specific values with placeholders.

        Examples:
        - "Find hydrogen funding calls" -> "find {topic} funding calls"
        - "Budget for RIA in CL5" -> "budget for {action_type} in {cluster}"
        """
        normalized = self._normalize_query(query)

        # Pattern replacements (order matters - more specific first)
        replacements = [
            # Clusters
            (r'\b(cl[1-6]|cluster\s*[1-6]|health|digital|climate|food|security|culture)\b', '{cluster}'),
            # Action types
            (r'\b(ria|ia|csa|erc|eic|msca)\b', '{action_type}'),
            # Countries
            (r'\b(germany|france|spain|italy|netherlands|belgium|austria|sweden|denmark|finland|poland|czech|portugal|ireland|greece|hungary|romania|bulgaria|croatia|slovakia|slovenia|estonia|latvia|lithuania|luxembourg|malta|cyprus)\b', '{country}'),
            # Years
            (r'\b(20[2-3][0-9])\b', '{year}'),
            # Numbers/budgets
            (r'\b(\d+(?:\.\d+)?)\s*(million|m|billion|b|euro|eur|€)\b', '{budget}'),
        ]

        import re
        pattern = normalized
        for regex, placeholder in replacements:
            pattern = re.sub(regex, placeholder, pattern, flags=re.IGNORECASE)

        return pattern

    def _generate_cache_key(self, query: str, context_hash: str = "") -> str:
        """Generate a deterministic cache key for a query pattern."""
        pattern = self._extract_query_pattern(query)
        key_content = f"{pattern}:{context_hash}"
        hash_val = hashlib.sha256(key_content.encode()).hexdigest()[:16]
        return f"{self.prefix}{hash_val}"

    def get_cached_plan(self, query: str, context: str = "") -> Optional[Dict[str, Any]]:
        """
        Retrieve cached plan for a query pattern.

        Returns:
            Cached plan dict with 'tool_calls', 'thought', etc. or None
        """
        try:
            context_hash = hashlib.md5(context.encode()).hexdigest()[:8] if context else ""
            cache_key = self._generate_cache_key(query, context_hash)

            cached = self.redis.get(cache_key)
            if cached:
                plan = json.loads(cached)
                logger.info(f"✅ Cache hit for query pattern: {cache_key}")
                return plan

            logger.debug(f"❌ Cache miss for query pattern: {cache_key}")
            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def cache_plan(
        self,
        query: str,
        plan: Dict[str, Any],
        context: str = "",
        success: bool = True
    ) -> bool:
        """
        Cache a successful query plan.

        Args:
            query: The original query
            plan: The reasoning output (tool_calls, thought, etc.)
            context: Optional conversation context
            success: Whether the plan led to a successful response
        """
        # Only cache successful plans
        if not success:
            return False

        try:
            context_hash = hashlib.md5(context.encode()).hexdigest()[:8] if context else ""
            cache_key = self._generate_cache_key(query, context_hash)

            # Store plan with metadata
            cache_data = {
                'plan': plan,
                'pattern': self._extract_query_pattern(query),
                'original_query': query,
                'cached_at': datetime.now().isoformat()
            }

            self.redis.setex(
                cache_key,
                self.ttl,
                json.dumps(cache_data)
            )

            logger.info(f"✅ Cached plan for pattern: {cache_key}")
            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            keys = self.redis.keys(f"{self.prefix}*")
            return {
                'cached_plans': len(keys),
                'prefix': self.prefix,
                'ttl_hours': self.ttl.total_seconds() / 3600
            }
        except Exception as e:
            return {'error': str(e)}
```

#### Step 2: Integrate with ToolAwareAgent

**File:** `app/services/agents/tool_aware_agent.py`

```python
# In __init__:
from ..cache.query_plan_cache import QueryPlanCache

def __init__(self, ...):
    # ... existing code ...

    # Initialize plan cache
    try:
        from ..memory.memory_service import MemoryService
        memory = MemoryService()
        self.plan_cache = QueryPlanCache(memory.redis_client)
    except Exception as e:
        logger.warning(f"Plan cache unavailable: {e}")
        self.plan_cache = None

# In _reason_next_step, before LLM call:
async def _reason_next_step(self, query: str, ...):
    # Check cache first (only for first step)
    if not previous_steps and self.plan_cache:
        cached = self.plan_cache.get_cached_plan(query, context)
        if cached and 'plan' in cached:
            logger.info("🚀 Using cached reasoning plan")
            return cached['plan']

    # ... existing LLM reasoning code ...

    # Cache successful plan after execution completes
    # (This happens in process_query after successful response)
```

#### Step 3: Cache Invalidation Strategy

- **Time-based:** 24-hour TTL (configurable)
- **Pattern-based:** Cache per query pattern, not exact query
- **Success-based:** Only cache plans that led to quality responses (score > 0.7)

### Expected Benefits

- **30-50% reduction** in LLM calls for common query patterns
- **Faster responses** for repeat queries (~200ms vs ~2s)
- **Cost savings** on API usage

### Testing Plan

1. Test pattern extraction with various query formats
2. Verify cache hit/miss behavior
3. Measure latency improvement
4. Monitor cache hit rate in production

---

## 2. Parallel Execution Within Agentic Iterations

**Priority:** High | **Complexity:** Medium | **Estimated Time:** 2-3 days

### Current State

- Tools within a single iteration ARE already parallelized (`_execute_tool_calls` line 913-956 uses `asyncio.gather`)
- BUT: Each iteration waits for LLM reasoning before proceeding
- Bottleneck: Sequential `_reason_next_step()` → `_execute_tool_calls()` → repeat

### Problem Statement

The ReAct loop is inherently sequential:
```
Iteration 1: THINK → ACT → OBSERVE
Iteration 2: THINK → ACT → OBSERVE  (waits for iteration 1)
```

For complex queries, we could potentially:
1. Speculate on likely follow-up tool calls
2. Pre-fetch common data while reasoning
3. Pipeline LLM calls with tool execution

### Implementation Plan

#### Step 1: Speculative Tool Pre-fetching

For common query patterns, start fetching data speculatively:

**File:** `app/services/agents/speculative_executor.py`

```python
"""
Speculative execution for common tool patterns.

When we identify a query pattern, we can start fetching data
from likely-needed tools while the LLM is still reasoning.
"""

import asyncio
from typing import Dict, Any, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class SpeculativeExecutor:
    """Execute likely tool calls speculatively."""

    # Common patterns: query keywords -> likely tools
    SPECULATION_PATTERNS = {
        # Funding calls queries
        ('funding', 'calls', 'open', 'deadline'): ['search_funding_calls'],
        ('hydrogen', 'energy', 'climate', 'green'): ['search_funding_calls', 'search_documents'],

        # Project queries
        ('projects', 'funded', 'cordis'): ['search_projects'],
        ('similar', 'projects', 'like'): ['get_similar_funded_projects'],

        # Budget/consortium queries
        ('budget', 'typical', 'average', 'how much'): ['get_budget_benchmark'],
        ('consortium', 'partners', 'composition'): ['get_consortium_patterns'],

        # Statistics queries
        ('statistics', 'success rate', 'funding rate'): ['get_programme_statistics'],
        ('country', 'participation'): ['get_country_statistics'],

        # Comparison queries
        ('compare', 'difference', 'vs', 'versus'): ['compare_programmes'],
    }

    def __init__(self, tool_executor):
        self.tool_executor = tool_executor
        self.speculation_cache: Dict[str, asyncio.Task] = {}

    def identify_likely_tools(self, query: str) -> List[str]:
        """Identify tools that are likely needed for this query."""
        query_lower = query.lower()
        likely_tools: Set[str] = set()

        for keywords, tools in self.SPECULATION_PATTERNS.items():
            if any(kw in query_lower for kw in keywords):
                likely_tools.update(tools)

        return list(likely_tools)[:3]  # Max 3 speculative calls

    async def start_speculative_execution(
        self,
        query: str,
        context: str = ""
    ) -> Dict[str, asyncio.Task]:
        """
        Start speculative tool execution for likely-needed tools.
        Returns tasks that can be awaited later if needed.
        """
        likely_tools = self.identify_likely_tools(query)

        if not likely_tools:
            return {}

        logger.info(f"🔮 Starting speculative execution for: {likely_tools}")

        tasks = {}
        for tool_name in likely_tools:
            # Generate default parameters based on query
            params = self._generate_default_params(tool_name, query)

            # Start execution as background task
            task = asyncio.create_task(
                self.tool_executor(tool_name, params),
                name=f"speculative_{tool_name}"
            )
            tasks[tool_name] = task
            self.speculation_cache[tool_name] = task

        return tasks

    def _generate_default_params(self, tool_name: str, query: str) -> Dict[str, Any]:
        """Generate reasonable default parameters for speculative execution."""
        # Extract keywords from query
        keywords = ' '.join(query.split()[:5])  # First 5 words

        default_params = {
            'search_funding_calls': {'keywords': keywords, 'status': 'open'},
            'search_projects': {'keywords': keywords},
            'search_documents': {'query': query, 'max_results': 10},
            'get_budget_benchmark': {'action_type': 'RIA'},  # Most common
            'get_consortium_patterns': {'action_type': 'RIA'},
            'get_programme_statistics': {'programme': 'Horizon Europe'},
            'get_country_statistics': {'country': 'Germany'},  # Default
            'get_similar_funded_projects': {'query': query, 'limit': 5},
            'compare_programmes': {'programme_a': 'EIC', 'programme_b': 'ERC'},
        }

        return default_params.get(tool_name, {})

    async def get_speculative_result(
        self,
        tool_name: str,
        timeout: float = 0.1
    ) -> Optional[Dict[str, Any]]:
        """
        Get result from speculative execution if available.
        Returns None if not ready within timeout.
        """
        task = self.speculation_cache.get(tool_name)
        if not task:
            return None

        try:
            # Wait briefly for result
            result = await asyncio.wait_for(
                asyncio.shield(task),  # Don't cancel if timeout
                timeout=timeout
            )
            logger.info(f"🎯 Speculative result ready for: {tool_name}")
            return result
        except asyncio.TimeoutError:
            logger.debug(f"⏳ Speculative result not ready: {tool_name}")
            return None
        except Exception as e:
            logger.warning(f"Speculative execution failed: {e}")
            return None

    def cancel_unused_speculation(self, used_tools: Set[str]):
        """Cancel speculative tasks that weren't needed."""
        for tool_name, task in list(self.speculation_cache.items()):
            if tool_name not in used_tools and not task.done():
                task.cancel()
                logger.debug(f"🚫 Cancelled unused speculation: {tool_name}")

        self.speculation_cache.clear()
```

#### Step 2: Integrate with ToolAwareAgent

```python
# In process_query:
async def process_query(self, query: str, context: str = "", ...):
    # Start speculative execution immediately
    speculative = SpeculativeExecutor(self._execute_single_tool)
    spec_tasks = await speculative.start_speculative_execution(query, context)

    # ... existing reasoning loop ...

    # When executing tools, check speculative cache first
    async def _execute_tool_calls_with_speculation(self, tool_calls, speculative):
        results = []
        for tc in tool_calls:
            tool_name = tc.get('tool')

            # Check if we already have speculative result
            spec_result = await speculative.get_speculative_result(tool_name)
            if spec_result:
                # Use speculative result
                results.append(ToolCall(
                    tool_name=tool_name,
                    result=spec_result,
                    success=True,
                    speculative=True
                ))
            else:
                # Execute normally
                result = await self._execute_single_tool(tool_name, tc.get('parameters', {}))
                results.append(...)

        return results
```

#### Step 3: LLM Call Pipelining (Advanced)

For multi-iteration queries, start the next reasoning call while processing current results:

```python
async def _pipelined_iteration(self, ...):
    # Start next reasoning call optimistically
    next_reasoning_task = None

    # Execute current tools
    tool_results = await self._execute_tool_calls(tool_calls)

    # If we have enough results, start reasoning for next iteration
    if self._should_continue(tool_results):
        next_reasoning_task = asyncio.create_task(
            self._reason_next_step(query, steps, tool_results)
        )

    # Process results while reasoning runs
    processed = self._process_tool_results(tool_results)

    # Get reasoning result (should be ready or nearly ready)
    if next_reasoning_task:
        next_step = await next_reasoning_task
```

### Expected Benefits

- **40-60% faster** complex queries (3+ iterations)
- Better utilization of parallel I/O
- Reduced perceived latency

### Testing Plan

1. Benchmark query latency before/after
2. Measure speculation hit rate
3. Verify correctness of pipelined execution
4. Test cancellation of unused speculative tasks

---

## 3. Add More Tools

**Priority:** Medium | **Complexity:** Medium | **Estimated Time:** 3-4 days

### New Tools Needed

Based on user needs and available data:

1. **Budget Calculator** - Help users plan realistic budgets
2. **Timeline Generator** - Generate project timeline based on similar projects

### Tool 1: Budget Calculator

**Purpose:** Calculate recommended budget breakdown for a proposal

**File:** `app/services/tools/budget_calculator.py`

```python
"""
Budget Calculator Tool

Helps users calculate realistic budget breakdowns for Horizon Europe proposals
based on patterns from funded projects.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


@dataclass
class BudgetBreakdown:
    """Budget breakdown by category."""
    personnel: float
    equipment: float
    travel: float
    subcontracting: float
    other_direct: float
    indirect: float
    total: float


class BudgetCalculatorTool:
    """Calculate realistic budget breakdowns for proposals."""

    # Typical cost category ratios by action type (from analysis of funded projects)
    COST_RATIOS = {
        'RIA': {
            'personnel': 0.55,      # 55% personnel
            'equipment': 0.10,      # 10% equipment
            'travel': 0.05,         # 5% travel
            'subcontracting': 0.10, # 10% subcontracting
            'other_direct': 0.05,   # 5% other direct
            'indirect': 0.15,       # 15% indirect (25% of direct)
        },
        'IA': {
            'personnel': 0.45,
            'equipment': 0.15,
            'travel': 0.05,
            'subcontracting': 0.15,
            'other_direct': 0.05,
            'indirect': 0.15,
        },
        'CSA': {
            'personnel': 0.65,
            'equipment': 0.02,
            'travel': 0.10,
            'subcontracting': 0.08,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
        'ERC': {
            'personnel': 0.70,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.00,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
    }

    # Person-month costs by country tier (EUR)
    PM_COSTS = {
        'tier1': 8500,   # DE, FR, NL, BE, AT, DK, SE, FI, LU
        'tier2': 6500,   # ES, IT, PT, IE, CZ, SI, EE
        'tier3': 4500,   # PL, HU, RO, BG, HR, SK, LT, LV
        'default': 7000,
    }

    COUNTRY_TIERS = {
        'tier1': ['DE', 'FR', 'NL', 'BE', 'AT', 'DK', 'SE', 'FI', 'LU', 'NO', 'CH'],
        'tier2': ['ES', 'IT', 'PT', 'IE', 'CZ', 'SI', 'EE', 'GR', 'CY', 'MT'],
        'tier3': ['PL', 'HU', 'RO', 'BG', 'HR', 'SK', 'LT', 'LV'],
    }

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")

    def calculate_budget(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: Optional[int] = None,
        target_budget: Optional[float] = None,
        countries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate recommended budget breakdown.

        Args:
            action_type: RIA, IA, CSA, ERC, etc.
            duration_months: Project duration in months
            num_partners: Number of consortium partners
            total_person_months: Total PMs across all partners (optional)
            target_budget: Target total budget in EUR (optional)
            countries: List of partner countries (optional)

        Returns:
            Budget breakdown with recommendations
        """
        action_type = action_type.upper()
        ratios = self.COST_RATIOS.get(action_type, self.COST_RATIOS['RIA'])

        # Calculate or estimate total budget
        if target_budget:
            total = target_budget
        elif total_person_months:
            avg_pm_cost = self._calculate_avg_pm_cost(countries)
            personnel_cost = total_person_months * avg_pm_cost
            # Personnel is X% of total, so total = personnel / X
            total = personnel_cost / ratios['personnel']
        else:
            # Estimate based on typical budgets
            benchmarks = self._get_budget_benchmarks(action_type)
            total = benchmarks.get('median', 5_000_000)

        # Calculate breakdown
        breakdown = {
            'total_budget': total,
            'breakdown': {
                'personnel': {
                    'amount': total * ratios['personnel'],
                    'percentage': ratios['personnel'] * 100,
                    'description': 'Salaries, social charges for project staff'
                },
                'equipment': {
                    'amount': total * ratios['equipment'],
                    'percentage': ratios['equipment'] * 100,
                    'description': 'Depreciation of equipment purchased for project'
                },
                'travel': {
                    'amount': total * ratios['travel'],
                    'percentage': ratios['travel'] * 100,
                    'description': 'Travel and subsistence for project meetings'
                },
                'subcontracting': {
                    'amount': total * ratios['subcontracting'],
                    'percentage': ratios['subcontracting'] * 100,
                    'description': 'Work carried out by third parties'
                },
                'other_direct': {
                    'amount': total * ratios['other_direct'],
                    'percentage': ratios['other_direct'] * 100,
                    'description': 'Consumables, publications, dissemination'
                },
                'indirect': {
                    'amount': total * ratios['indirect'],
                    'percentage': ratios['indirect'] * 100,
                    'description': 'Indirect costs (25% of direct costs)'
                },
            },
            'per_partner': {
                'average': total / num_partners,
                'coordinator_typical': total * 0.20,  # 20% typical for coordinator
                'partner_typical': (total * 0.80) / (num_partners - 1) if num_partners > 1 else 0,
            },
            'person_months': {
                'estimated_total': int(total * ratios['personnel'] / self._calculate_avg_pm_cost(countries)),
                'per_partner_avg': int(total * ratios['personnel'] / self._calculate_avg_pm_cost(countries) / num_partners),
            },
            'recommendations': self._generate_recommendations(action_type, total, num_partners, duration_months),
            'benchmarks': self._get_budget_benchmarks(action_type),
        }

        return breakdown

    def _calculate_avg_pm_cost(self, countries: Optional[List[str]]) -> float:
        """Calculate average person-month cost based on country mix."""
        if not countries:
            return self.PM_COSTS['default']

        total_cost = 0
        for country in countries:
            country_upper = country.upper()
            if country_upper in self.COUNTRY_TIERS['tier1']:
                total_cost += self.PM_COSTS['tier1']
            elif country_upper in self.COUNTRY_TIERS['tier2']:
                total_cost += self.PM_COSTS['tier2']
            elif country_upper in self.COUNTRY_TIERS['tier3']:
                total_cost += self.PM_COSTS['tier3']
            else:
                total_cost += self.PM_COSTS['default']

        return total_cost / len(countries)

    def _get_budget_benchmarks(self, action_type: str) -> Dict[str, float]:
        """Get budget benchmarks from funded projects."""
        # This would query the database - simplified version
        benchmarks = {
            'RIA': {'mean': 7_500_000, 'median': 6_000_000, 'min': 2_000_000, 'max': 20_000_000},
            'IA': {'mean': 12_000_000, 'median': 10_000_000, 'min': 5_000_000, 'max': 30_000_000},
            'CSA': {'mean': 3_000_000, 'median': 2_500_000, 'min': 500_000, 'max': 8_000_000},
            'ERC': {'mean': 2_000_000, 'median': 2_000_000, 'min': 1_500_000, 'max': 2_500_000},
        }
        return benchmarks.get(action_type, benchmarks['RIA'])

    def _generate_recommendations(
        self,
        action_type: str,
        total: float,
        num_partners: int,
        duration: int
    ) -> List[str]:
        """Generate budget recommendations."""
        recommendations = []

        benchmarks = self._get_budget_benchmarks(action_type)

        if total < benchmarks['min']:
            recommendations.append(f"⚠️ Budget seems low for {action_type}. Typical minimum is €{benchmarks['min']/1_000_000:.1f}M")
        elif total > benchmarks['max']:
            recommendations.append(f"⚠️ Budget seems high for {action_type}. Typical maximum is €{benchmarks['max']/1_000_000:.1f}M")
        else:
            recommendations.append(f"✅ Budget is within typical range for {action_type} projects")

        per_partner = total / num_partners
        if per_partner < 200_000:
            recommendations.append("⚠️ Average per-partner budget may be too low for meaningful contribution")

        if duration > 48:
            recommendations.append("⚠️ Projects over 48 months are uncommon - consider shorter duration")

        return recommendations


# Async wrapper for tool orchestrator
async def calculate_budget_async(**kwargs) -> Dict[str, Any]:
    """Async wrapper for budget calculator."""
    tool = BudgetCalculatorTool()
    return tool.calculate_budget(**kwargs)
```

### Tool 2: Timeline Generator

**File:** `app/services/tools/timeline_generator.py`

```python
"""
Timeline Generator Tool

Generates realistic project timelines based on patterns from funded projects.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


@dataclass
class WorkPackage:
    """Work package definition."""
    number: int
    title: str
    lead: str
    start_month: int
    end_month: int
    effort_pms: int
    deliverables: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]


class TimelineGeneratorTool:
    """Generate project timelines based on best practices."""

    # Typical WP structure by action type
    WP_TEMPLATES = {
        'RIA': [
            {'title': 'Project Management', 'effort_pct': 0.08, 'full_duration': True},
            {'title': 'Requirements & State of the Art', 'effort_pct': 0.12, 'months': (1, 12)},
            {'title': 'Core Research & Development', 'effort_pct': 0.35, 'months': (6, -6)},
            {'title': 'Integration & Validation', 'effort_pct': 0.20, 'months': (12, -3)},
            {'title': 'Dissemination & Exploitation', 'effort_pct': 0.15, 'full_duration': True},
            {'title': 'Ethics & Data Management', 'effort_pct': 0.05, 'full_duration': True},
        ],
        'IA': [
            {'title': 'Project Management', 'effort_pct': 0.08, 'full_duration': True},
            {'title': 'Market Analysis & Requirements', 'effort_pct': 0.10, 'months': (1, 9)},
            {'title': 'Technology Development', 'effort_pct': 0.30, 'months': (3, -9)},
            {'title': 'Pilot Deployment', 'effort_pct': 0.25, 'months': (12, -6)},
            {'title': 'Business Model & Scale-up', 'effort_pct': 0.12, 'months': (18, -3)},
            {'title': 'Dissemination & Exploitation', 'effort_pct': 0.15, 'full_duration': True},
        ],
        'CSA': [
            {'title': 'Project Management', 'effort_pct': 0.10, 'full_duration': True},
            {'title': 'Stakeholder Engagement', 'effort_pct': 0.25, 'full_duration': True},
            {'title': 'Analysis & Best Practices', 'effort_pct': 0.25, 'months': (1, 18)},
            {'title': 'Policy Recommendations', 'effort_pct': 0.20, 'months': (12, -3)},
            {'title': 'Communication & Outreach', 'effort_pct': 0.20, 'full_duration': True},
        ],
    }

    def generate_timeline(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: int,
        project_title: str = "Project",
        custom_wps: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate a project timeline with work packages, deliverables, and milestones.

        Args:
            action_type: RIA, IA, CSA
            duration_months: Total project duration
            num_partners: Number of partners
            total_person_months: Total effort in PMs
            project_title: Project title for naming
            custom_wps: Optional custom WP definitions

        Returns:
            Complete timeline with WPs, deliverables, milestones, Gantt data
        """
        action_type = action_type.upper()
        templates = custom_wps or self.WP_TEMPLATES.get(action_type, self.WP_TEMPLATES['RIA'])

        work_packages = []
        all_deliverables = []
        all_milestones = []

        for i, template in enumerate(templates, 1):
            # Calculate WP timing
            if template.get('full_duration'):
                start_month = 1
                end_month = duration_months
            else:
                months = template.get('months', (1, duration_months))
                start_month = months[0]
                end_month = duration_months + months[1] if months[1] < 0 else months[1]

            # Calculate effort
            effort = int(total_person_months * template['effort_pct'])

            # Generate deliverables
            wp_deliverables = self._generate_deliverables(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month,
                action_type=action_type
            )

            # Generate milestones
            wp_milestones = self._generate_milestones(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month
            )

            wp = {
                'number': i,
                'title': template['title'],
                'lead': f'Partner {(i % num_partners) + 1}',
                'start_month': start_month,
                'end_month': end_month,
                'effort_pms': effort,
                'deliverables': wp_deliverables,
                'milestones': wp_milestones,
            }

            work_packages.append(wp)
            all_deliverables.extend(wp_deliverables)
            all_milestones.extend(wp_milestones)

        # Sort deliverables and milestones by due date
        all_deliverables.sort(key=lambda d: d['due_month'])
        all_milestones.sort(key=lambda m: m['due_month'])

        # Generate Gantt chart data
        gantt_data = self._generate_gantt_data(work_packages, duration_months)

        return {
            'project_title': project_title,
            'duration_months': duration_months,
            'total_person_months': total_person_months,
            'num_partners': num_partners,
            'work_packages': work_packages,
            'deliverables': all_deliverables,
            'milestones': all_milestones,
            'gantt_data': gantt_data,
            'summary': {
                'total_wps': len(work_packages),
                'total_deliverables': len(all_deliverables),
                'total_milestones': len(all_milestones),
                'effort_distribution': {wp['title']: wp['effort_pms'] for wp in work_packages},
            },
            'recommendations': self._generate_timeline_recommendations(
                work_packages, duration_months, action_type
            )
        }

    def _generate_deliverables(
        self,
        wp_num: int,
        wp_title: str,
        start_month: int,
        end_month: int,
        action_type: str
    ) -> List[Dict]:
        """Generate typical deliverables for a WP."""
        deliverables = []
        duration = end_month - start_month

        # Every WP has at least one deliverable
        deliverable_types = {
            'Management': [('Report', 'Project management report', 'R')],
            'Requirements': [('Report', 'Requirements specification', 'R'), ('Document', 'State of the art analysis', 'R')],
            'Research': [('Report', 'Technical report', 'R'), ('Demonstrator', 'Prototype', 'DEM')],
            'Development': [('Software', 'Software release', 'OTHER'), ('Report', 'Technical documentation', 'R')],
            'Validation': [('Report', 'Validation report', 'R'), ('Demonstrator', 'Validated prototype', 'DEM')],
            'Dissemination': [('Report', 'Dissemination report', 'R'), ('Website', 'Project website', 'DEC')],
            'Pilot': [('Demonstrator', 'Pilot deployment', 'DEM'), ('Report', 'Pilot evaluation', 'R')],
        }

        # Find matching deliverable types
        for key, del_templates in deliverable_types.items():
            if key.lower() in wp_title.lower():
                for j, (del_type, del_name, del_nature) in enumerate(del_templates):
                    due = start_month + int(duration * (j + 1) / (len(del_templates) + 1))
                    deliverables.append({
                        'id': f'D{wp_num}.{j+1}',
                        'title': f'{del_name}',
                        'wp': wp_num,
                        'due_month': min(due, end_month),
                        'type': del_type,
                        'dissemination': 'PU',  # Public
                        'nature': del_nature,
                    })
                break

        # Default deliverable if no match
        if not deliverables:
            deliverables.append({
                'id': f'D{wp_num}.1',
                'title': f'{wp_title} report',
                'wp': wp_num,
                'due_month': end_month,
                'type': 'Report',
                'dissemination': 'PU',
                'nature': 'R',
            })

        return deliverables

    def _generate_milestones(
        self,
        wp_num: int,
        wp_title: str,
        start_month: int,
        end_month: int
    ) -> List[Dict]:
        """Generate milestones for a WP."""
        milestones = []

        # Key WPs get milestones
        if any(kw in wp_title.lower() for kw in ['requirement', 'development', 'validation', 'pilot']):
            milestones.append({
                'id': f'MS{wp_num}',
                'title': f'{wp_title} complete',
                'wp': wp_num,
                'due_month': end_month,
                'verification': 'Achievement of WP objectives verified by deliverable completion',
            })

        return milestones

    def _generate_gantt_data(
        self,
        work_packages: List[Dict],
        duration: int
    ) -> Dict[str, Any]:
        """Generate Gantt chart data structure."""
        months = list(range(1, duration + 1))

        gantt = {
            'months': months,
            'work_packages': []
        }

        for wp in work_packages:
            wp_gantt = {
                'wp': wp['number'],
                'title': wp['title'],
                'timeline': []
            }

            for month in months:
                if wp['start_month'] <= month <= wp['end_month']:
                    wp_gantt['timeline'].append('█')
                else:
                    wp_gantt['timeline'].append(' ')

            gantt['work_packages'].append(wp_gantt)

        return gantt

    def _generate_timeline_recommendations(
        self,
        work_packages: List[Dict],
        duration: int,
        action_type: str
    ) -> List[str]:
        """Generate timeline recommendations."""
        recommendations = []

        # Check for typical issues
        management_wp = next((wp for wp in work_packages if 'management' in wp['title'].lower()), None)
        if management_wp and management_wp['effort_pms'] / sum(wp['effort_pms'] for wp in work_packages) < 0.05:
            recommendations.append("⚠️ Management effort seems low. Recommend at least 5-8% of total effort.")

        if duration > 36 and action_type == 'RIA':
            recommendations.append("💡 For RIA > 36 months, consider intermediate review milestones")

        if len([wp for wp in work_packages if wp['start_month'] == 1]) > 3:
            recommendations.append("💡 Many WPs starting in M1 - consider staggered starts for resource management")

        return recommendations


# Async wrapper
async def generate_timeline_async(**kwargs) -> Dict[str, Any]:
    """Async wrapper for timeline generator."""
    tool = TimelineGeneratorTool()
    return tool.generate_timeline(**kwargs)
```

### Registration in ToolAwareAgent

Add to `_init_tools()`:

```python
# Budget Calculator
self.register_tool(Tool(
    name="calculate_budget",
    description="Calculate realistic budget breakdown for a Horizon Europe proposal based on action type, duration, and consortium size",
    category=ToolCategory.STATISTICS,
    parameters={
        "action_type": "Type of action (RIA, IA, CSA, ERC)",
        "duration_months": "Project duration in months",
        "num_partners": "Number of consortium partners",
        "total_person_months": "Optional: total person-months",
        "target_budget": "Optional: target total budget in EUR",
    },
    examples=[
        "calculate_budget(action_type='RIA', duration_months=36, num_partners=8)",
        "calculate_budget(action_type='IA', duration_months=48, num_partners=12, target_budget=15000000)"
    ]
))

# Timeline Generator
self.register_tool(Tool(
    name="generate_timeline",
    description="Generate a project timeline with work packages, deliverables, and milestones based on action type and duration",
    category=ToolCategory.STATISTICS,
    parameters={
        "action_type": "Type of action (RIA, IA, CSA)",
        "duration_months": "Project duration in months",
        "num_partners": "Number of consortium partners",
        "total_person_months": "Total effort in person-months",
        "project_title": "Optional: project title",
    },
    examples=[
        "generate_timeline(action_type='RIA', duration_months=36, num_partners=8, total_person_months=400)",
    ]
))
```

---

## 4. Implement Tool Usage Analytics

**Priority:** Medium | **Complexity:** Low | **Estimated Time:** 2 days

### Current State

- Basic console logging (`logger.info`) at line 954 of tool_aware_agent.py
- `ToolCall` dataclass captures timing but doesn't persist
- No historical analysis or optimization insights

### Implementation Plan

#### Step 1: Database Schema

**File:** `migration/004_tool_analytics.sql`

```sql
-- Tool usage analytics tables

CREATE TABLE IF NOT EXISTS tool_usage_analytics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    conversation_id VARCHAR(255),
    query_hash VARCHAR(64),
    tool_name VARCHAR(100) NOT NULL,
    parameters JSONB,
    execution_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    result_count INTEGER,
    result_quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tool_usage_timestamp ON tool_usage_analytics(timestamp);
CREATE INDEX idx_tool_usage_tool_name ON tool_usage_analytics(tool_name);
CREATE INDEX idx_tool_usage_success ON tool_usage_analytics(success);

-- Aggregated metrics table (updated by scheduled job)
CREATE TABLE IF NOT EXISTS tool_performance_metrics (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    avg_execution_time_ms FLOAT,
    p95_execution_time_ms FLOAT,
    avg_result_count FLOAT,
    avg_quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tool_name, period_start)
);

-- Tool combination patterns
CREATE TABLE IF NOT EXISTS tool_combination_analytics (
    id SERIAL PRIMARY KEY,
    tool_sequence TEXT[] NOT NULL,  -- Array of tools used in order
    occurrence_count INTEGER DEFAULT 1,
    avg_total_time_ms FLOAT,
    success_rate FLOAT,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tool_sequence)
);
```

#### Step 2: Analytics Service

**File:** `app/services/analytics/tool_analytics_service.py`

```python
"""
Tool Usage Analytics Service

Tracks tool usage patterns, performance, and quality metrics
for optimization and monitoring.
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ToolUsageEvent:
    """Single tool usage event."""
    tool_name: str
    parameters: Dict[str, Any]
    execution_time_ms: int
    success: bool
    error_message: Optional[str] = None
    result_count: Optional[int] = None
    result_quality_score: Optional[float] = None
    conversation_id: Optional[str] = None
    query_hash: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ToolAnalyticsService:
    """Service for tracking and analyzing tool usage."""

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.buffer: List[ToolUsageEvent] = []
        self.buffer_size = 100  # Batch write every 100 events
        self.flush_interval = 60  # Or every 60 seconds
        self.last_flush = datetime.now()

        # In-memory metrics for real-time dashboard
        self.session_metrics = defaultdict(lambda: {
            'calls': 0,
            'successes': 0,
            'total_time_ms': 0,
        })

    async def track_tool_usage(self, event: ToolUsageEvent):
        """Track a tool usage event."""
        # Update in-memory metrics
        self.session_metrics[event.tool_name]['calls'] += 1
        if event.success:
            self.session_metrics[event.tool_name]['successes'] += 1
        self.session_metrics[event.tool_name]['total_time_ms'] += event.execution_time_ms

        # Buffer for batch write
        self.buffer.append(event)

        # Flush if buffer full or interval elapsed
        if len(self.buffer) >= self.buffer_size or \
           (datetime.now() - self.last_flush).seconds >= self.flush_interval:
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush buffered events to database."""
        if not self.buffer or not self.db_pool:
            return

        events = self.buffer.copy()
        self.buffer.clear()
        self.last_flush = datetime.now()

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Batch insert
            insert_sql = """
                INSERT INTO tool_usage_analytics
                (timestamp, conversation_id, query_hash, tool_name, parameters,
                 execution_time_ms, success, error_message, result_count, result_quality_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            for event in events:
                cursor.execute(insert_sql, (
                    event.timestamp,
                    event.conversation_id,
                    event.query_hash,
                    event.tool_name,
                    json.dumps(event.parameters),
                    event.execution_time_ms,
                    event.success,
                    event.error_message,
                    event.result_count,
                    event.result_quality_score,
                ))

            conn.commit()
            logger.info(f"📊 Flushed {len(events)} tool usage events to database")

        except Exception as e:
            logger.error(f"Failed to flush analytics: {e}")
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    async def track_tool_sequence(self, tools_used: List[str], total_time_ms: int, success: bool):
        """Track a sequence of tools used together."""
        if not self.db_pool or len(tools_used) < 2:
            return

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tool_combination_analytics (tool_sequence, occurrence_count, avg_total_time_ms, success_rate, last_seen)
                VALUES (%s, 1, %s, %s, NOW())
                ON CONFLICT (tool_sequence) DO UPDATE SET
                    occurrence_count = tool_combination_analytics.occurrence_count + 1,
                    avg_total_time_ms = (tool_combination_analytics.avg_total_time_ms * tool_combination_analytics.occurrence_count + %s) / (tool_combination_analytics.occurrence_count + 1),
                    success_rate = (tool_combination_analytics.success_rate * tool_combination_analytics.occurrence_count + %s) / (tool_combination_analytics.occurrence_count + 1),
                    last_seen = NOW()
            """, (tools_used, total_time_ms, 1.0 if success else 0.0, total_time_ms, 1.0 if success else 0.0))

            conn.commit()
        except Exception as e:
            logger.error(f"Failed to track tool sequence: {e}")
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def get_session_metrics(self) -> Dict[str, Any]:
        """Get current session metrics."""
        metrics = {}
        for tool_name, data in self.session_metrics.items():
            metrics[tool_name] = {
                'calls': data['calls'],
                'success_rate': data['successes'] / data['calls'] if data['calls'] > 0 else 0,
                'avg_time_ms': data['total_time_ms'] / data['calls'] if data['calls'] > 0 else 0,
            }
        return metrics

    async def get_tool_performance_report(self, days: int = 7) -> Dict[str, Any]:
        """Get tool performance report for last N days."""
        if not self.db_pool:
            return {'error': 'Database not available'}

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    tool_name,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
                    AVG(execution_time_ms) as avg_time_ms,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_time_ms,
                    AVG(result_count) as avg_results
                FROM tool_usage_analytics
                WHERE timestamp > NOW() - INTERVAL '%s days'
                GROUP BY tool_name
                ORDER BY total_calls DESC
            """, (days,))

            rows = cursor.fetchall()

            report = {
                'period_days': days,
                'tools': []
            }

            for row in rows:
                report['tools'].append({
                    'tool_name': row[0],
                    'total_calls': row[1],
                    'success_rate': row[2] / row[1] if row[1] > 0 else 0,
                    'avg_time_ms': round(row[3], 2) if row[3] else 0,
                    'p95_time_ms': round(row[4], 2) if row[4] else 0,
                    'avg_results': round(row[5], 1) if row[5] else 0,
                })

            return report

        except Exception as e:
            logger.error(f"Failed to get performance report: {e}")
            return {'error': str(e)}
        finally:
            cursor.close()
            self.db_pool.putconn(conn)
```

#### Step 3: Integration with ToolAwareAgent

```python
# In __init__:
from ..analytics.tool_analytics_service import ToolAnalyticsService, ToolUsageEvent

def __init__(self, ...):
    # ... existing code ...
    self.analytics = ToolAnalyticsService(db_pool)

# In _execute_tool_calls:
async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[ToolCall]:
    results = []
    tools_used = []

    for tc in tool_calls:
        tool_name = tc.get('tool')
        params = tc.get('parameters', {})

        start_time = datetime.now()
        result = await self._execute_single_tool(tool_name, params)
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        success = not isinstance(result, Exception) and 'error' not in result

        # Track analytics
        await self.analytics.track_tool_usage(ToolUsageEvent(
            tool_name=tool_name,
            parameters=params,
            execution_time_ms=execution_time,
            success=success,
            error_message=str(result.get('error')) if not success else None,
            result_count=len(result.get('results', result.get('projects', result.get('calls', [])))) if success else 0,
            conversation_id=self.current_conversation_id,
        ))

        tools_used.append(tool_name)
        results.append(...)

    # Track tool sequence
    if len(tools_used) >= 2:
        await self.analytics.track_tool_sequence(tools_used, total_time, all_success)

    return results
```

---

## 5. Add User Feedback Loop

**Priority:** Medium | **Complexity:** Low | **Estimated Time:** 2 days

### Implementation Plan

#### Step 1: Database Schema

**File:** `migration/005_user_feedback.sql`

```sql
CREATE TABLE IF NOT EXISTS response_feedback (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255),
    query_text TEXT,
    response_text TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_type VARCHAR(50),  -- 'helpful', 'not_helpful', 'incorrect', 'incomplete'
    feedback_text TEXT,
    tools_used TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_conversation ON response_feedback(conversation_id);
CREATE INDEX idx_feedback_rating ON response_feedback(rating);
CREATE INDEX idx_feedback_created ON response_feedback(created_at);

-- Aggregated feedback insights
CREATE TABLE IF NOT EXISTS feedback_insights (
    id SERIAL PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_feedback INTEGER DEFAULT 0,
    avg_rating FLOAT,
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,
    top_issues JSONB,
    tool_ratings JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(period_start)
);
```

#### Step 2: Feedback Service

**File:** `app/services/feedback/feedback_service.py`

```python
"""
User Feedback Service

Collects and analyzes user feedback on responses
for continuous quality improvement.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class FeedbackSubmission:
    """User feedback submission."""
    conversation_id: str
    rating: int  # 1-5
    feedback_type: str  # helpful, not_helpful, incorrect, incomplete
    feedback_text: Optional[str] = None
    message_id: Optional[str] = None
    query_text: Optional[str] = None
    response_text: Optional[str] = None
    tools_used: Optional[List[str]] = None


class FeedbackService:
    """Service for managing user feedback."""

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    async def submit_feedback(self, feedback: FeedbackSubmission) -> bool:
        """Submit user feedback."""
        if not self.db_pool:
            logger.warning("Database not available for feedback")
            return False

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO response_feedback
                (conversation_id, message_id, query_text, response_text,
                 rating, feedback_type, feedback_text, tools_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                feedback.conversation_id,
                feedback.message_id,
                feedback.query_text,
                feedback.response_text,
                feedback.rating,
                feedback.feedback_type,
                feedback.feedback_text,
                feedback.tools_used,
            ))

            conn.commit()
            logger.info(f"✅ Feedback submitted for conversation {feedback.conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            return False
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    async def get_feedback_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback summary for last N days."""
        if not self.db_pool:
            return {'error': 'Database not available'}

        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Overall metrics
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(rating) as avg_rating,
                    SUM(CASE WHEN feedback_type = 'helpful' THEN 1 ELSE 0 END) as helpful,
                    SUM(CASE WHEN feedback_type = 'not_helpful' THEN 1 ELSE 0 END) as not_helpful,
                    SUM(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END) as incorrect,
                    SUM(CASE WHEN feedback_type = 'incomplete' THEN 1 ELSE 0 END) as incomplete
                FROM response_feedback
                WHERE created_at > NOW() - INTERVAL '%s days'
            """, (days,))

            row = cursor.fetchone()

            # Rating distribution
            cursor.execute("""
                SELECT rating, COUNT(*) as count
                FROM response_feedback
                WHERE created_at > NOW() - INTERVAL '%s days'
                GROUP BY rating
                ORDER BY rating
            """, (days,))

            rating_dist = {row[0]: row[1] for row in cursor.fetchall()}

            # Tool-specific ratings
            cursor.execute("""
                SELECT
                    unnest(tools_used) as tool,
                    AVG(rating) as avg_rating,
                    COUNT(*) as count
                FROM response_feedback
                WHERE created_at > NOW() - INTERVAL '%s days'
                  AND tools_used IS NOT NULL
                GROUP BY unnest(tools_used)
                ORDER BY count DESC
                LIMIT 10
            """, (days,))

            tool_ratings = [
                {'tool': row[0], 'avg_rating': round(row[1], 2), 'count': row[2]}
                for row in cursor.fetchall()
            ]

            return {
                'period_days': days,
                'total_feedback': row[0],
                'avg_rating': round(row[1], 2) if row[1] else None,
                'feedback_types': {
                    'helpful': row[2],
                    'not_helpful': row[3],
                    'incorrect': row[4],
                    'incomplete': row[5],
                },
                'rating_distribution': rating_dist,
                'tool_ratings': tool_ratings,
            }

        except Exception as e:
            logger.error(f"Failed to get feedback summary: {e}")
            return {'error': str(e)}
        finally:
            cursor.close()
            self.db_pool.putconn(conn)
```

#### Step 3: API Endpoints

**File:** `app/api/feedback_routes.py`

```python
"""Feedback API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    conversation_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback_type: str = Field(..., pattern="^(helpful|not_helpful|incorrect|incomplete)$")
    feedback_text: Optional[str] = None
    message_id: Optional[str] = None


@router.post("/submit")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback for a response."""
    from ..services.feedback.feedback_service import FeedbackService, FeedbackSubmission

    service = FeedbackService()  # Initialize with db_pool

    feedback = FeedbackSubmission(
        conversation_id=request.conversation_id,
        rating=request.rating,
        feedback_type=request.feedback_type,
        feedback_text=request.feedback_text,
        message_id=request.message_id,
    )

    success = await service.submit_feedback(feedback)

    if success:
        return {"status": "success", "message": "Feedback submitted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.get("/summary")
async def get_feedback_summary(days: int = 30):
    """Get feedback summary."""
    from ..services.feedback.feedback_service import FeedbackService

    service = FeedbackService()
    return await service.get_feedback_summary(days)
```

---

## 6. Incremental Embedding Updates

**Priority:** Low | **Complexity:** Medium | **Estimated Time:** 2-3 days

### Current State

- Script `scripts/generate_project_embeddings.py` handles batch embedding generation
- `project_embeddings` table tracks status with `embedding_status` column
- Script identifies projects needing embeddings via LEFT JOIN
- No automated scheduling or incremental detection

### Implementation Plan

#### Step 1: Enhanced Embedding Tracker

**File:** `app/services/embedding/incremental_embedding_service.py`

```python
"""
Incremental Embedding Update Service

Detects and processes new/modified projects that need embeddings.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class IncrementalEmbeddingService:
    """Service for incremental embedding updates."""

    def __init__(self, db_pool, embedding_service):
        self.db_pool = db_pool
        self.embedding_service = embedding_service
        self.batch_size = 50

    def get_projects_needing_embeddings(self, limit: int = 500) -> List[Dict]:
        """
        Find projects that need embeddings:
        1. New projects without embeddings
        2. Projects where content changed (objective updated)
        3. Failed embeddings to retry
        """
        conn = self.db_pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            query = """
                WITH projects_status AS (
                    SELECT
                        p.id,
                        p.title,
                        p.objective,
                        p.updated_at as project_updated,
                        pe.updated_at as embedding_updated,
                        pe.embedding_status,
                        pe.text_length as embedded_text_length,
                        LENGTH(COALESCE(p.title, '') || '. ' || COALESCE(p.objective, '')) as current_text_length
                    FROM projects p
                    LEFT JOIN project_embeddings pe ON p.id = pe.project_id
                    WHERE p.title IS NOT NULL
                      AND p.objective IS NOT NULL
                      AND LENGTH(p.title) > 10
                      AND LENGTH(p.objective) > 50
                )
                SELECT id, title, objective
                FROM projects_status
                WHERE
                    -- No embedding yet
                    embedding_status IS NULL
                    -- Or embedding failed
                    OR embedding_status = 'failed'
                    -- Or content changed (text length different)
                    OR (embedding_status = 'completed'
                        AND ABS(current_text_length - COALESCE(embedded_text_length, 0)) > 100)
                    -- Or project updated after embedding
                    OR (embedding_status = 'completed'
                        AND project_updated > embedding_updated)
                ORDER BY
                    CASE
                        WHEN embedding_status IS NULL THEN 1  -- New projects first
                        WHEN embedding_status = 'failed' THEN 2  -- Then retries
                        ELSE 3  -- Then updates
                    END,
                    id
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get current embedding statistics."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            # Total projects
            cursor.execute("""
                SELECT COUNT(*) FROM projects
                WHERE title IS NOT NULL AND objective IS NOT NULL
            """)
            total = cursor.fetchone()[0]

            # By status
            cursor.execute("""
                SELECT embedding_status, COUNT(*)
                FROM project_embeddings
                GROUP BY embedding_status
            """)
            by_status = dict(cursor.fetchall())

            # Needing update
            cursor.execute("""
                SELECT COUNT(*) FROM projects p
                LEFT JOIN project_embeddings pe ON p.id = pe.project_id
                WHERE pe.project_id IS NULL
                   OR pe.embedding_status = 'failed'
            """)
            needing_update = cursor.fetchone()[0]

            return {
                'total_projects': total,
                'embedded': by_status.get('completed', 0),
                'failed': by_status.get('failed', 0),
                'pending': by_status.get('pending', 0),
                'needing_update': needing_update,
                'coverage_pct': round(by_status.get('completed', 0) / total * 100, 1) if total > 0 else 0
            }

        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    async def run_incremental_update(self, max_projects: int = 500) -> Dict[str, Any]:
        """Run incremental embedding update."""
        start_time = datetime.now()

        projects = self.get_projects_needing_embeddings(limit=max_projects)

        if not projects:
            return {
                'status': 'no_updates_needed',
                'projects_processed': 0,
                'duration_seconds': 0
            }

        logger.info(f"🔄 Processing {len(projects)} projects for embedding update")

        success_count = 0
        fail_count = 0

        # Process in batches
        for i in range(0, len(projects), self.batch_size):
            batch = projects[i:i + self.batch_size]

            texts = [
                f"{p['title']}. {p['objective']}"[:2000]
                for p in batch
            ]

            embeddings = await asyncio.to_thread(
                self.embedding_service.generate_embeddings_batch,
                texts
            )

            # Store results
            for j, project in enumerate(batch):
                embedding = embeddings[j] if j < len(embeddings) else None
                success = self._store_embedding(
                    project['id'],
                    texts[j],
                    embedding.tolist() if embedding is not None and embedding.any() else None
                )
                if success:
                    success_count += 1
                else:
                    fail_count += 1

            # Rate limiting
            await asyncio.sleep(0.5)

        duration = (datetime.now() - start_time).total_seconds()

        return {
            'status': 'completed',
            'projects_processed': len(projects),
            'successful': success_count,
            'failed': fail_count,
            'duration_seconds': round(duration, 1)
        }

    def _store_embedding(self, project_id: int, text: str, embedding: Optional[List[float]]) -> bool:
        """Store embedding result."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            if embedding:
                cursor.execute("""
                    INSERT INTO project_embeddings
                    (project_id, combined_embedding, model_version, text_length, embedding_status, updated_at)
                    VALUES (%s, %s, 'text-embedding-004', %s, 'completed', NOW())
                    ON CONFLICT (project_id) DO UPDATE SET
                        combined_embedding = EXCLUDED.combined_embedding,
                        text_length = EXCLUDED.text_length,
                        embedding_status = 'completed',
                        error_message = NULL,
                        updated_at = NOW()
                """, (project_id, embedding, len(text)))
            else:
                cursor.execute("""
                    INSERT INTO project_embeddings
                    (project_id, embedding_status, error_message, text_length, updated_at)
                    VALUES (%s, 'failed', 'Embedding generation failed', %s, NOW())
                    ON CONFLICT (project_id) DO UPDATE SET
                        embedding_status = 'failed',
                        error_message = 'Embedding generation failed',
                        text_length = EXCLUDED.text_length,
                        updated_at = NOW()
                """, (project_id, len(text)))

            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            self.db_pool.putconn(conn)
```

#### Step 2: Celery Task for Scheduled Updates

**File:** `app/tasks/embedding_tasks.py`

```python
"""Celery tasks for embedding updates."""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name='update_embeddings_daily')
def update_embeddings_daily():
    """Daily task to update missing embeddings."""
    import asyncio
    from ..services.embedding.incremental_embedding_service import IncrementalEmbeddingService
    from ..services.embedding_service import EmbeddingService

    # Initialize services
    embedding_service = EmbeddingService()
    incremental_service = IncrementalEmbeddingService(
        db_pool=get_db_pool(),
        embedding_service=embedding_service
    )

    # Run update
    result = asyncio.run(incremental_service.run_incremental_update(max_projects=500))

    logger.info(f"📊 Daily embedding update: {result}")
    return result


@shared_task(name='update_embeddings_weekly_full')
def update_embeddings_weekly_full():
    """Weekly task to check all projects for updates."""
    # Similar but with max_projects=5000 for thorough check
    pass
```

---

## 7. V3 Project Formatter Enhancements

**Priority:** Low | **Complexity:** Low | **Estimated Time:** 1-2 days

### Current State

- `V3ResponseFormatter` in `app/services/response/v3_response_formatter.py`
- Formats: title, acronym, ID, programme, status, dates, budget, coordinator, objective
- Missing: publications, deliverables, impact metrics

### Implementation Plan

#### Step 1: Extend CordisRepository

Add methods to fetch publications and deliverables:

**File:** `app/services/data/cordis_repository.py` (additions)

```python
def get_project_publications(self, project_id: str, limit: int = 5) -> List[Dict]:
    """Get publications for a project."""
    conn = self.db_pool.getconn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT
                title,
                authors,
                journal_title as journal,
                publication_date,
                doi,
                is_open_access
            FROM cordis_processed.publications_enriched
            WHERE project_id = %s
            ORDER BY publication_date DESC
            LIMIT %s
        """, (project_id, limit))

        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to get publications: {e}")
        return []
    finally:
        cursor.close()
        self.db_pool.putconn(conn)

def get_project_deliverables(self, project_id: str, limit: int = 5) -> List[Dict]:
    """Get deliverables for a project."""
    conn = self.db_pool.getconn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT
                title,
                type,
                description,
                url
            FROM cordis_processed.deliverables_enriched
            WHERE project_id = %s
            ORDER BY title
            LIMIT %s
        """, (project_id, limit))

        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.warning(f"Failed to get deliverables: {e}")
        return []
    finally:
        cursor.close()
        self.db_pool.putconn(conn)
```

#### Step 2: Enhance V3ResponseFormatter

**File:** `app/services/response/v3_response_formatter.py` (additions)

```python
def _format_single_project(self, index: int, project: Dict) -> str:
    """Format a single project with enhanced details."""
    # ... existing formatting code ...

    # Add publications section if available
    publications = project.get('publications', [])
    if publications:
        lines.append("\n📚 **Key Publications:**")
        for pub in publications[:3]:
            title = pub.get('title', 'Untitled')[:80]
            authors = pub.get('authors', 'Unknown')
            if len(authors) > 50:
                authors = authors[:47] + "..."
            journal = pub.get('journal', '')
            doi = pub.get('doi', '')

            pub_line = f"  • {title}"
            if journal:
                pub_line += f" - *{journal}*"
            if doi:
                pub_line += f" [DOI](https://doi.org/{doi})"
            lines.append(pub_line)

    # Add deliverables section if available
    deliverables = project.get('deliverables', [])
    if deliverables:
        lines.append("\n📦 **Key Deliverables:**")
        for deliv in deliverables[:3]:
            title = deliv.get('title', 'Untitled')[:60]
            del_type = deliv.get('type', '')
            url = deliv.get('url', '')

            deliv_line = f"  • {title}"
            if del_type:
                deliv_line += f" ({del_type})"
            if url:
                deliv_line += f" [View]({url})"
            lines.append(deliv_line)

    # Add impact metrics if available
    impact = project.get('impact_metrics', {})
    if impact:
        lines.append("\n📊 **Impact:**")
        if impact.get('publications_count'):
            lines.append(f"  • Publications: {impact['publications_count']}")
        if impact.get('patents_count'):
            lines.append(f"  • Patents: {impact['patents_count']}")
        if impact.get('datasets_count'):
            lines.append(f"  • Open datasets: {impact['datasets_count']}")

    # ... rest of existing code ...
```

#### Step 3: Update Tool Handler to Fetch Additional Data

In `tool_aware_agent.py`, when returning project results:

```python
async def _tool_search_projects(self, params: Dict) -> Dict:
    """Search CORDIS projects with enhanced data."""
    # ... existing search code ...

    # Optionally enrich with publications/deliverables
    include_details = params.get('include_details', False)

    if include_details and projects:
        from ..data.cordis_repository import CordisProjectRepository
        repo = CordisProjectRepository()

        for project in projects[:5]:  # Limit enrichment to top 5
            project_id = project.get('id')
            if project_id:
                project['publications'] = repo.get_project_publications(project_id, limit=3)
                project['deliverables'] = repo.get_project_deliverables(project_id, limit=3)

    return {'projects': projects, 'count': len(projects)}
```

---

## Implementation Roadmap

| Phase | Improvements | Priority | Duration |
|-------|-------------|----------|----------|
| **Phase 1** | Plan Caching + Parallel Execution | High | Week 1 |
| **Phase 2** | Tool Analytics + User Feedback | Medium | Week 2 |
| **Phase 3** | New Tools (Budget, Timeline) | Medium | Week 3 |
| **Phase 4** | Incremental Embeddings + Formatter | Low | Week 4 |

---

## Success Metrics

| Improvement | Metric | Target |
|-------------|--------|--------|
| Plan Caching | Cache hit rate | > 30% |
| Plan Caching | Latency reduction | > 40% for repeated patterns |
| Parallel Execution | Complex query latency | < 3s (from 5s) |
| Tool Analytics | Visibility | 100% tool calls tracked |
| User Feedback | Response collection | > 5% of queries |
| Incremental Embeddings | Coverage | 99%+ projects embedded |
| V3 Formatter | User satisfaction | Positive feedback on project details |

---

## Dependencies

- **Redis**: Required for plan caching (already configured)
- **PostgreSQL**: Required for analytics tables (already available)
- **Celery**: Required for scheduled embedding updates (already configured)
- **Google Embedding API**: Required for incremental embeddings (already integrated)

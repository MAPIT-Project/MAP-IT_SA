# TASK_06: Query Planner Implementation

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_06 |
| **Day** | 4 |
| **Estimated Time** | 2 hours |
| **Dependencies** | TASK_05 (Planner prompt created) |
| **Blocks** | TASK_07 |
| **Priority** | High |

## Objective

Implement the `QueryPlanner` class that uses the Gemini LLM to analyze user queries and generate structured execution plans. This component is the "brain" of the intelligent retrieval system.

## Context

The QueryPlanner sits between the user query and the tool execution layer:

```
User Query → QueryPlanner → ExecutionPlan → ToolOrchestrator → Results
```

It uses the system prompt from TASK_05 to instruct the LLM how to classify queries and generate plans.

## Files to Create

| Action | File Path |
|--------|-----------|
| CREATE | `app/services/data_intelligence/query_planner.py` |
| MODIFY | `app/services/data_intelligence/__init__.py` |

## Implementation

### File: `app/services/data_intelligence/query_planner.py`

```python
"""
Query Planner - Generates intelligent execution plans for user queries.

Uses an LLM to analyze user questions and determine:
1. Query intent (call_lookup, eligibility, budget, etc.)
2. Which data sources to query (graph, vector, keyword)
3. What operations to perform
4. How to handle failures

Usage:
    from app.services.data_intelligence.query_planner import QueryPlanner
    
    planner = QueryPlanner()
    plan = await planner.generate_plan("What is the deadline for HORIZON-CL4-2025-DATA-01?")
    print(plan.intent_type)  # "call_lookup"
    print(plan.steps)  # [ExecutionStep(...), ...]
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import asyncio

import google.generativeai as genai

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """A single step in the execution plan."""
    step_number: int
    source: str  # "graph", "vector", "keyword"
    operation: str
    parameters: Dict[str, Any]
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "source": self.source,
            "operation": self.operation,
            "parameters": self.parameters,
            "reason": self.reason
        }


@dataclass
class ExtractedEntities:
    """Entities extracted from the query."""
    topic_codes: List[str] = field(default_factory=list)
    cluster_codes: List[str] = field(default_factory=list)
    country_codes: List[str] = field(default_factory=list)
    organization_names: List[str] = field(default_factory=list)
    action_types: List[str] = field(default_factory=list)


@dataclass
class QueryPlan:
    """Complete execution plan for a query."""
    intent_type: str
    confidence: float
    steps: List[ExecutionStep]
    need_graph: str  # "required", "maybe", "never"
    need_vector: str
    need_keyword: str
    cleaned_query: str
    extracted_entities: ExtractedEntities
    fallback_strategy: str
    raw_response: Optional[str] = None
    planning_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "steps": [s.to_dict() for s in self.steps],
            "need_graph": self.need_graph,
            "need_vector": self.need_vector,
            "need_keyword": self.need_keyword,
            "cleaned_query": self.cleaned_query,
            "extracted_entities": asdict(self.extracted_entities),
            "fallback_strategy": self.fallback_strategy,
            "planning_time_ms": self.planning_time_ms
        }


class QueryPlanner:
    """
    Generates intelligent execution plans for user queries using LLM.
    
    The planner analyzes the query intent and determines:
    - Which data sources to query
    - What operations to perform
    - Parameters for each operation
    - Fallback strategies
    """
    
    # Default model configuration
    DEFAULT_MODEL = "gemini-1.5-flash"
    DEFAULT_TEMPERATURE = 0.1
    DEFAULT_MAX_TOKENS = 1500
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_path: Optional[Path] = None
    ):
        """
        Initialize the Query Planner.
        
        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (defaults to gemini-1.5-flash)
            prompt_path: Path to system prompt file (defaults to planner_system_prompt.txt)
        """
        # Configure API
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = genai.GenerativeModel(self.model_name)
        
        # Load system prompt
        if prompt_path is None:
            prompt_path = Path(__file__).parent / "planner_system_prompt.txt"
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found: {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
        
        logger.info(f"✅ Query Planner initialized with model: {self.model_name}")
    
    async def generate_plan(
        self,
        user_query: str,
        conversation_context: str = "",
        timeout_seconds: float = 10.0
    ) -> QueryPlan:
        """
        Generate an execution plan for the user query.
        
        Args:
            user_query: The user's question
            conversation_context: Optional context from previous conversation
            timeout_seconds: Maximum time to wait for LLM response
            
        Returns:
            QueryPlan with steps and metadata
        """
        start_time = datetime.now()
        
        try:
            # Build the complete prompt
            full_prompt = self._build_prompt(user_query, conversation_context)
            
            # Call LLM with timeout
            try:
                response = await asyncio.wait_for(
                    self._call_llm(full_prompt),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"LLM timeout after {timeout_seconds}s, using fallback")
                return self._create_fallback_plan(user_query, "LLM timeout")
            
            # Parse response into QueryPlan
            plan = self._parse_response(response, user_query)
            
            # Calculate timing
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            plan.planning_time_ms = elapsed
            plan.raw_response = response
            
            logger.info(f"✅ Generated plan: {plan.intent_type} ({len(plan.steps)} steps, {elapsed:.0f}ms)")
            
            return plan
            
        except Exception as e:
            logger.error(f"❌ Plan generation failed: {e}")
            return self._create_fallback_plan(user_query, str(e))
    
    def _build_prompt(self, user_query: str, context: str = "") -> str:
        """Build the complete prompt for the LLM."""
        
        prompt_parts = [self.system_prompt]
        
        if context:
            prompt_parts.append(f"\n\nCONVERSATION CONTEXT:\n{context}")
        
        prompt_parts.append(f"\n\nUSER QUESTION:\n{user_query}")
        prompt_parts.append("\n\nGenerate the execution plan JSON:")
        
        return "\n".join(prompt_parts)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM and return the response text."""
        
        generation_config = genai.types.GenerationConfig(
            temperature=self.DEFAULT_TEMPERATURE,
            max_output_tokens=self.DEFAULT_MAX_TOKENS,
        )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(prompt, generation_config=generation_config)
        )
        
        return response.text
    
    def _parse_response(self, response_text: str, original_query: str) -> QueryPlan:
        """Parse the LLM response into a QueryPlan object."""
        
        try:
            # Extract JSON from response
            json_data = self._extract_json(response_text)
            
            if not json_data:
                raise ValueError("No valid JSON found in response")
            
            # Validate required fields
            required_fields = ["intent_type", "confidence", "plan"]
            for field in required_fields:
                if field not in json_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Parse execution steps
            steps = []
            for i, step_data in enumerate(json_data.get("plan", [])):
                step = ExecutionStep(
                    step_number=step_data.get("step", i + 1),
                    source=step_data.get("source", "vector"),
                    operation=step_data.get("operation", "semantic_search"),
                    parameters=step_data.get("parameters", {}),
                    reason=step_data.get("reason", "")
                )
                steps.append(step)
            
            # Parse extracted entities
            entities_data = json_data.get("extracted_entities", {})
            entities = ExtractedEntities(
                topic_codes=entities_data.get("topic_codes", []),
                cluster_codes=entities_data.get("cluster_codes", []),
                country_codes=entities_data.get("country_codes", []),
                organization_names=entities_data.get("organization_names", []),
                action_types=entities_data.get("action_types", [])
            )
            
            # Create QueryPlan
            plan = QueryPlan(
                intent_type=json_data.get("intent_type", "general"),
                confidence=float(json_data.get("confidence", 0.5)),
                steps=steps,
                need_graph=json_data.get("need_graph", "maybe"),
                need_vector=json_data.get("need_vector", "maybe"),
                need_keyword=json_data.get("need_keyword", "never"),
                cleaned_query=json_data.get("cleaned_query", original_query),
                extracted_entities=entities,
                fallback_strategy=json_data.get("fallback_strategy", "Use vector search as fallback")
            )
            
            # Validate and fix plan
            plan = self._validate_plan(plan, original_query)
            
            return plan
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}...")
            return self._create_fallback_plan(original_query, f"Parse error: {str(e)}")
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from text that may contain other content."""
        
        # Try to find JSON block
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # Markdown code block
            r'```\s*([\s\S]*?)\s*```',       # Generic code block
            r'(\{[\s\S]*\})',                 # Raw JSON object
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    json_str = match.group(1)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # Try parsing the entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _validate_plan(self, plan: QueryPlan, original_query: str) -> QueryPlan:
        """Validate and fix the plan if necessary."""
        
        # Ensure at least one step exists
        if not plan.steps:
            plan.steps = [
                ExecutionStep(
                    step_number=1,
                    source="vector",
                    operation="hybrid_search",
                    parameters={"query": plan.cleaned_query or original_query},
                    reason="Default fallback search"
                )
            ]
        
        # Ensure confidence is in valid range
        plan.confidence = max(0.0, min(1.0, plan.confidence))
        
        # Validate need_* values
        valid_values = {"required", "maybe", "never"}
        if plan.need_graph not in valid_values:
            plan.need_graph = "maybe"
        if plan.need_vector not in valid_values:
            plan.need_vector = "maybe"
        if plan.need_keyword not in valid_values:
            plan.need_keyword = "never"
        
        # Ensure cleaned_query is not empty
        if not plan.cleaned_query:
            plan.cleaned_query = original_query
        
        return plan
    
    def _create_fallback_plan(self, query: str, error_reason: str = "") -> QueryPlan:
        """Create a safe fallback plan when LLM planning fails."""
        
        logger.warning(f"Using fallback plan. Reason: {error_reason}")
        
        # Try to detect basic intent from query
        intent_type = "general"
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["deadline", "call", "topic", "horizon-"]):
            intent_type = "call_lookup"
        elif any(term in query_lower for term in ["eligible", "can ", "participate", "country"]):
            intent_type = "eligibility"
        elif any(term in query_lower for term in ["budget", "funding", "cost", "money"]):
            intent_type = "budget"
        elif any(term in query_lower for term in ["partner", "consortium", "countries"]):
            intent_type = "consortium"
        elif any(term in query_lower for term in ["similar", "like", "related"]):
            intent_type = "similar_calls"
        
        # Extract any topic codes
        topic_codes = re.findall(r'HORIZON-[\w-]+', query.upper())
        cluster_match = re.search(r'CLUSTER[- ]?(\d)', query.upper())
        cluster_codes = [f"CLUSTER-{cluster_match.group(1)}"] if cluster_match else []
        
        # Build fallback steps based on detected intent
        steps = []
        
        if topic_codes:
            steps.append(ExecutionStep(
                step_number=1,
                source="graph",
                operation="get_call_details",
                parameters={"identifier": topic_codes[0]},
                reason="Look up specific topic"
            ))
        
        # Always include vector search as fallback
        steps.append(ExecutionStep(
            step_number=len(steps) + 1,
            source="vector",
            operation="hybrid_search",
            parameters={"query": query, "num_results": 5},
            reason="Fallback semantic search"
        ))
        
        return QueryPlan(
            intent_type=intent_type,
            confidence=0.5,
            steps=steps,
            need_graph="maybe",
            need_vector="required",
            need_keyword="never",
            cleaned_query=query,
            extracted_entities=ExtractedEntities(
                topic_codes=topic_codes,
                cluster_codes=cluster_codes
            ),
            fallback_strategy=f"Fallback plan due to: {error_reason}"
        )
    
    def generate_plan_sync(
        self,
        user_query: str,
        conversation_context: str = ""
    ) -> QueryPlan:
        """
        Synchronous wrapper for generate_plan.
        
        Use this when calling from non-async code.
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.generate_plan(user_query, conversation_context)
            )
        finally:
            loop.close()


# Convenience function
async def plan_query(query: str, context: str = "") -> QueryPlan:
    """
    Convenience function to plan a query.
    
    Usage:
        plan = await plan_query("What is the deadline for HORIZON-CL4-2025-DATA-01?")
    """
    planner = QueryPlanner()
    return await planner.generate_plan(query, context)


# Testing
if __name__ == "__main__":
    import asyncio
    
    async def test_planner():
        print("\n=== Testing Query Planner ===\n")
        
        planner = QueryPlanner()
        
        test_queries = [
            "What is the deadline for HORIZON-CL4-2025-DATA-01?",
            "Can an SME from Switzerland participate in Cluster 4 calls?",
            "What is the maximum budget for RIA actions in Cluster 5?",
            "What is the minimum number of countries required for a CSA?",
            "Find calls similar to HORIZON-CL4-2024-HUMAN-01",
        ]
        
        for query in test_queries:
            print(f"Query: {query}")
            plan = await planner.generate_plan(query)
            print(f"  Intent: {plan.intent_type} (confidence: {plan.confidence:.2f})")
            print(f"  Steps: {len(plan.steps)}")
            for step in plan.steps:
                print(f"    {step.step_number}. [{step.source}] {step.operation}")
            print(f"  Graph: {plan.need_graph}, Vector: {plan.need_vector}")
            print(f"  Time: {plan.planning_time_ms:.0f}ms")
            print()
    
    asyncio.run(test_planner())
```

### Update: `app/services/data_intelligence/__init__.py`

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

- [ ] QueryPlanner class implemented with async generate_plan method
- [ ] Correctly loads and uses the system prompt from TASK_05
- [ ] Parses LLM JSON responses into QueryPlan objects
- [ ] Handles LLM errors gracefully with fallback plans
- [ ] Extracts entities (topic codes, countries, etc.) from queries
- [ ] Timeout handling for slow LLM responses
- [ ] All 5 test queries produce valid plans

## Verification Commands

```bash
# 1. Test the module can be imported
python -c "from app.services.data_intelligence.query_planner import QueryPlanner; print('✅ Import successful')"

# 2. Run the built-in test
cd /home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA
python app/services/data_intelligence/query_planner.py

# 3. Test with a specific query
python -c "
import asyncio
from app.services.data_intelligence.query_planner import QueryPlanner

async def test():
    planner = QueryPlanner()
    plan = await planner.generate_plan('What is the deadline for HORIZON-CL4-2025-DATA-01?')
    print(f'Intent: {plan.intent_type}')
    print(f'Confidence: {plan.confidence}')
    print(f'Steps: {len(plan.steps)}')
    for step in plan.steps:
        print(f'  - {step.source}: {step.operation}')

asyncio.run(test())
"

# 4. Test fallback behavior (with invalid API key temporarily)
python -c "
from app.services.data_intelligence.query_planner import QueryPlanner
planner = QueryPlanner()
plan = planner._create_fallback_plan('Can Switzerland participate?', 'test')
print(f'Fallback intent: {plan.intent_type}')
print(f'Fallback steps: {len(plan.steps)}')
"
```

## Notes for Agent

1. The planner uses Gemini's `gemini-1.5-flash` model by default (fast and cheap)
2. The system prompt must exist at the expected path (from TASK_05)
3. JSON extraction handles various formats (code blocks, raw JSON)
4. Fallback plans ensure the system never fails completely
5. The async pattern is important for non-blocking operation
6. Entity extraction helps the DataIntelligenceService route queries efficiently
7. Confidence scores help downstream components decide how to use results


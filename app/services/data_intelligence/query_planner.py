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

import asyncio
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """A single step in the execution plan."""
    step_number: int
    source: str  # "graph", "vector", "keyword"
    operation: str
    parameters: dict[str, Any]
    reason: str = ""
    
    def to_dict(self) -> dict[str, Any]:
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
    topic_codes: list[str] = field(default_factory=list)
    cluster_codes: list[str] = field(default_factory=list)
    country_codes: list[str] = field(default_factory=list)
    organization_names: list[str] = field(default_factory=list)
    action_types: list[str] = field(default_factory=list)


@dataclass
class QueryPlan:
    """Complete execution plan for a query."""
    intent_type: str
    confidence: float
    steps: list[ExecutionStep]
    need_graph: str  # "required", "maybe", "never"
    need_vector: str
    need_keyword: str
    cleaned_query: str
    extracted_entities: ExtractedEntities
    fallback_strategy: str
    raw_response: str | None = None
    planning_time_ms: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
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
    
    # Default model configuration - uses env var
    DEFAULT_MODEL = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
    DEFAULT_TEMPERATURE = 0.1
    DEFAULT_MAX_TOKENS = 2000
    
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        prompt_path: Path | None = None
    ):
        """
        Initialize the Query Planner.
        
        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY env var)
            model_name: Model to use (defaults to gemini-1.5-flash)
            prompt_path: Path to system prompt file (defaults to planner_system_prompt.txt)
        """
        # Configure API
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = genai.GenerativeModel(self.model_name)
        
        # Load system prompt
        if prompt_path is None:
            prompt_path = Path(__file__).parent / "planner_system_prompt.txt"
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found: {prompt_path}")
        
        with open(prompt_path, encoding='utf-8') as f:
            self.system_prompt = f.read()
        
        logger.info(f"✅ Query Planner initialized with model: {self.model_name}")
    
    async def generate_plan(
        self,
        user_query: str,
        conversation_context: str = "",
        timeout_seconds: float = 15.0
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
            except TimeoutError:
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
            for field_name in required_fields:
                if field_name not in json_data:
                    raise ValueError(f"Missing required field: {field_name}")
            
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
    
    def _extract_json(self, text: str) -> dict[str, Any] | None:
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
        elif any(term in query_lower for term in ["budget", "funding", "cost", "money", "maximum"]):
            intent_type = "budget"
        elif any(term in query_lower for term in ["partner", "consortium", "countries"]):
            intent_type = "consortium"
        elif any(term in query_lower for term in ["similar", "like", "related"]):
            intent_type = "similar_calls"
        
        # Extract any topic codes
        topic_codes = re.findall(r'HORIZON-[\w-]+', query.upper())
        cluster_match = re.search(r'CLUSTER[- ]?(\d)', query.upper())
        cluster_codes = [f"CLUSTER-{cluster_match.group(1)}"] if cluster_match else []
        
        # Extract country codes (common ones)
        country_pattern = r'\b(DE|FR|IT|ES|NL|BE|AT|CH|UK|US|PL|SE|DK|FI|NO|IE|PT|GR|CZ|HU|RO|BG)\b'
        country_codes = list(set(re.findall(country_pattern, query.upper())))
        
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
        
        if intent_type == "eligibility" and country_codes:
            steps.append(ExecutionStep(
                step_number=len(steps) + 1,
                source="graph",
                operation="check_country_eligibility",
                parameters={"country_code": country_codes[0]},
                reason="Check country eligibility"
            ))
        
        if intent_type == "budget":
            params = {}
            if cluster_codes:
                params["cluster_code"] = cluster_codes[0]
            steps.append(ExecutionStep(
                step_number=len(steps) + 1,
                source="graph",
                operation="get_budget_statistics",
                parameters=params,
                reason="Get budget statistics"
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
            need_graph="maybe" if intent_type != "general" else "never",
            need_vector="required",
            need_keyword="never",
            cleaned_query=query,
            extracted_entities=ExtractedEntities(
                topic_codes=topic_codes,
                cluster_codes=cluster_codes,
                country_codes=country_codes
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
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.generate_plan(user_query, conversation_context)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.generate_plan(user_query, conversation_context)
                )
        except RuntimeError:
            # No event loop exists
            return asyncio.run(self.generate_plan(user_query, conversation_context))


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
        logger.info("\n" + "=" * 60)
        logger.info("QUERY PLANNER TEST")
        logger.info("=" * 60)
        
        try:
            planner = QueryPlanner()
        except ValueError as e:
            logger.error(f"❌ Could not initialize planner: {e}")
            logger.info("   Make sure GEMINI_API_KEY is set in environment")
            return
        
        test_queries = [
            "What is the deadline for HORIZON-CL4-2025-DATA-01?",
            "Can an SME from Switzerland participate in Cluster 4 calls?",
            "What is the maximum budget for RIA actions in Cluster 5?",
            "What is the minimum number of countries required for a CSA?",
            "Find calls similar to HORIZON-CL4-2024-HUMAN-01",
        ]
        
        for query in test_queries:
            logger.info(f"\n📝 Query: {query}")
            plan = await planner.generate_plan(query)
            logger.info(f"   Intent: {plan.intent_type} (confidence: {plan.confidence:.2f})")
            logger.info(f"   Steps: {len(plan.steps)}")
            for step in plan.steps:
                logger.info(f"      {step.step_number}. [{step.source}] {step.operation}")
            logger.info(f"   Graph: {plan.need_graph}, Vector: {plan.need_vector}")
            logger.info(f"   Time: {plan.planning_time_ms:.0f}ms")
            if plan.extracted_entities.topic_codes:
                logger.info(f"   Topics: {plan.extracted_entities.topic_codes}")
            if plan.extracted_entities.country_codes:
                logger.info(f"   Countries: {plan.extracted_entities.country_codes}")
        
        logger.info("\n✅ Query Planner test complete!")
    
    asyncio.run(test_planner())


# Agentic Loop Implementation Plan for MAP-IT

## Executive Summary

Transform MAP-IT from a **single-pass system** to a **self-correcting agentic loop** that can:
- Evaluate its own results
- Recognize when information is insufficient
- Automatically retry with refined strategies
- Learn from failed attempts within a session

---

## Current Architecture vs. Agentic Architecture

### Current Flow (Single-Pass)
```
User Query → Intent Classification → Single Plan → Execute → Return Results
     │                                                              │
     └──────────────────── No Feedback Loop ────────────────────────┘
```

**Problems:**
- If the first plan fails, user gets bad results
- No self-correction mechanism
- No evaluation of result quality
- Cannot recover from API failures or empty results

### Proposed Agentic Flow
```
User Query → Understand → Plan → Execute → Evaluate → Sufficient?
     │                                          │           │
     │                                          │      NO   │ YES
     │                                          ↓           ↓
     │                                     Reflect →    Synthesize
     │                                          │           │
     │                                          ↓           ↓
     │                                     Replan →    Return Results
     │                                          │
     └──────────── Memory (what worked/failed) ←┘
```

---

## Core Components

### 1. Agent State Machine

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class AgentState(Enum):
    """Agent lifecycle states."""
    UNDERSTANDING = "understanding"    # Parsing user intent
    PLANNING = "planning"              # Creating execution plan
    EXECUTING = "executing"            # Running tools/searches
    EVALUATING = "evaluating"          # Checking result quality
    REFLECTING = "reflecting"          # Analyzing what went wrong
    REPLANNING = "replanning"          # Creating new plan
    SYNTHESIZING = "synthesizing"      # Building final response
    COMPLETE = "complete"              # Done

@dataclass
class AgentContext:
    """Tracks the agent's state across iterations."""
    
    # Original query
    user_query: str
    conversation_id: str
    
    # Current state
    state: AgentState = AgentState.UNDERSTANDING
    iteration: int = 0
    max_iterations: int = 3
    
    # Understanding
    intent: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    query_type: Optional[str] = None
    
    # Planning
    current_plan: Optional[Dict] = None
    plan_history: List[Dict] = field(default_factory=list)
    
    # Execution
    results: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict] = field(default_factory=list)
    
    # Evaluation
    result_quality: float = 0.0  # 0-1 score
    quality_reasons: List[str] = field(default_factory=list)
    is_sufficient: bool = False
    
    # Reflection
    failure_reasons: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # Memory of what worked/failed
    successful_strategies: List[str] = field(default_factory=list)
    failed_strategies: List[str] = field(default_factory=list)
    
    # Final output
    final_response: Optional[str] = None
    sources: List[Dict] = field(default_factory=list)
```

### 2. Result Evaluator (Critical Component)

The evaluator determines if results are "good enough" or need improvement.

```python
class ResultEvaluator:
    """
    Evaluates search results to determine if they answer the user's query.
    
    Uses both:
    1. Rule-based heuristics (fast, cheap)
    2. LLM evaluation (accurate, for edge cases)
    """
    
    # Quality thresholds
    MIN_RESULTS_FOR_FACTUAL = 3
    MIN_RESULTS_FOR_EXPLORATORY = 5
    MIN_RELEVANCE_SCORE = 0.6
    MIN_CONTENT_LENGTH = 100
    
    async def evaluate(
        self,
        query: str,
        query_type: str,
        results: Dict[str, Any],
        context: AgentContext
    ) -> EvaluationResult:
        """
        Evaluate if results sufficiently answer the query.
        
        Returns:
            EvaluationResult with score, reasons, and suggestions
        """
        
        # Phase 1: Rule-based evaluation (fast)
        rule_score, rule_reasons = self._rule_based_evaluation(
            query, query_type, results
        )
        
        # If clearly good or clearly bad, skip LLM
        if rule_score > 0.85:
            return EvaluationResult(
                score=rule_score,
                is_sufficient=True,
                reasons=rule_reasons
            )
        
        if rule_score < 0.3:
            return EvaluationResult(
                score=rule_score,
                is_sufficient=False,
                reasons=rule_reasons,
                suggestions=self._generate_improvement_suggestions(query, results)
            )
        
        # Phase 2: LLM evaluation for edge cases
        llm_eval = await self._llm_evaluation(query, query_type, results)
        
        # Combine scores
        final_score = (rule_score * 0.4) + (llm_eval.score * 0.6)
        
        return EvaluationResult(
            score=final_score,
            is_sufficient=final_score >= 0.65,
            reasons=rule_reasons + llm_eval.reasons,
            suggestions=llm_eval.suggestions
        )
    
    def _rule_based_evaluation(
        self,
        query: str,
        query_type: str,
        results: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """Fast rule-based quality check."""
        
        score = 0.0
        reasons = []
        
        # Check 1: Do we have results?
        total_results = self._count_results(results)
        if total_results == 0:
            return 0.0, ["No results found"]
        
        # Check 2: Enough results for query type?
        min_required = self.MIN_RESULTS_FOR_FACTUAL if query_type == 'factual' else self.MIN_RESULTS_FOR_EXPLORATORY
        if total_results >= min_required:
            score += 0.3
            reasons.append(f"Found {total_results} results (minimum: {min_required})")
        else:
            reasons.append(f"Only {total_results} results (need {min_required})")
        
        # Check 3: Relevance scores
        avg_relevance = self._average_relevance(results)
        if avg_relevance >= self.MIN_RELEVANCE_SCORE:
            score += 0.3
            reasons.append(f"Good relevance score: {avg_relevance:.2f}")
        else:
            reasons.append(f"Low relevance: {avg_relevance:.2f}")
        
        # Check 4: Content quality (not just titles)
        has_content = self._has_substantial_content(results)
        if has_content:
            score += 0.2
            reasons.append("Results have detailed content")
        else:
            reasons.append("Results lack detailed content")
        
        # Check 5: Query terms appear in results
        query_coverage = self._query_term_coverage(query, results)
        if query_coverage > 0.5:
            score += 0.2
            reasons.append(f"Query terms found: {query_coverage:.0%}")
        else:
            reasons.append(f"Query terms poorly covered: {query_coverage:.0%}")
        
        return score, reasons
    
    async def _llm_evaluation(
        self,
        query: str,
        query_type: str,
        results: Dict[str, Any]
    ) -> LLMEvaluationResult:
        """Use LLM to evaluate result quality."""
        
        prompt = f"""Evaluate if these search results answer the user's question.

USER QUESTION: {query}
QUERY TYPE: {query_type}

SEARCH RESULTS:
{self._format_results_for_llm(results)}

Evaluate on a scale of 0-100:
1. RELEVANCE: Do results relate to the question?
2. COMPLETENESS: Do results fully answer the question?
3. ACCURACY: Do results appear factually correct?
4. ACTIONABILITY: Can the user act on this information?

If score < 70, suggest what additional information would help.

Respond in JSON:
{{
    "relevance": 0-100,
    "completeness": 0-100,
    "accuracy": 0-100,
    "actionability": 0-100,
    "overall_score": 0-100,
    "is_sufficient": true/false,
    "reasons": ["reason1", "reason2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        # Call LLM and parse response
        response = await self.llm.generate(prompt)
        return self._parse_llm_evaluation(response)
```

### 3. Reflector (Learning from Failures)

```python
class Reflector:
    """
    Analyzes failed attempts and suggests improvements.
    
    Patterns it can identify:
    - Query too broad/narrow
    - Wrong data source selected
    - Missing context needed
    - Semantic vs keyword search mismatch
    """
    
    async def reflect(
        self,
        context: AgentContext,
        evaluation: EvaluationResult
    ) -> ReflectionResult:
        """
        Analyze why results were insufficient and suggest improvements.
        """
        
        prompt = f"""You are debugging a search system that failed to find good results.

ORIGINAL QUERY: {context.user_query}
INTENT: {context.intent}
ENTITIES: {context.entities}

PLAN THAT WAS EXECUTED:
{json.dumps(context.current_plan, indent=2)}

RESULTS OBTAINED:
{self._summarize_results(context.results)}

EVALUATION:
- Score: {evaluation.score}
- Reasons: {evaluation.reasons}

PREVIOUS FAILED STRATEGIES:
{context.failed_strategies}

Analyze what went wrong and how to fix it. Consider:
1. Was the query interpreted correctly?
2. Were the right data sources selected?
3. Were search terms too specific or too broad?
4. Is the information likely in a different format/location?
5. Would a different search strategy help?

Respond in JSON:
{{
    "failure_analysis": "What specifically went wrong",
    "root_cause": "query_too_broad|wrong_source|missing_context|semantic_mismatch|data_not_available|other",
    "improvement_strategy": {{
        "action": "refine_query|change_source|add_context|try_keyword|broaden_search|narrow_search",
        "details": "Specific changes to make",
        "new_query": "Refined query if applicable",
        "new_sources": ["source1", "source2"]
    }},
    "confidence": 0.0-1.0
}}
"""
        
        response = await self.llm.generate(prompt)
        return self._parse_reflection(response)
```

### 4. Replanner

```python
class Replanner:
    """
    Creates new execution plans based on reflection insights.
    """
    
    async def replan(
        self,
        context: AgentContext,
        reflection: ReflectionResult
    ) -> ExecutionPlan:
        """
        Generate a new plan incorporating lessons learned.
        """
        
        # Don't repeat failed strategies
        avoided_strategies = set(context.failed_strategies)
        
        prompt = f"""Create a NEW search plan based on what we learned.

ORIGINAL QUERY: {context.user_query}
WHAT FAILED: {reflection.failure_analysis}
ROOT CAUSE: {reflection.root_cause}
SUGGESTED FIX: {reflection.improvement_strategy}

STRATEGIES TO AVOID (already failed):
{list(avoided_strategies)}

STRATEGIES THAT WORKED BEFORE:
{context.successful_strategies}

Create a new execution plan that:
1. Addresses the root cause
2. Uses different strategies than before
3. Has a higher chance of success

Return plan in JSON format with steps, sources, and queries.
"""
        
        response = await self.llm.generate(prompt)
        new_plan = self._parse_plan(response)
        
        # Validate plan doesn't repeat failures
        if self._plan_overlaps_failures(new_plan, avoided_strategies):
            new_plan = self._modify_plan_to_avoid_failures(new_plan, avoided_strategies)
        
        return new_plan
```

### 5. Main Agent Loop

```python
class AgenticConversationManager:
    """
    Main agentic loop controller.
    
    Orchestrates the understand → plan → execute → evaluate → reflect cycle.
    """
    
    def __init__(self):
        self.understander = QueryUnderstandingService()
        self.planner = QueryPlanner()
        self.executor = ExecutionEngine()
        self.evaluator = ResultEvaluator()
        self.reflector = Reflector()
        self.replanner = Replanner()
        self.synthesizer = ResponseSynthesizer()
    
    async def process_query(
        self,
        query: str,
        conversation_id: str,
        conversation_history: List[Dict] = None
    ) -> AgentResponse:
        """
        Process a query through the agentic loop.
        """
        
        # Initialize context
        context = AgentContext(
            user_query=query,
            conversation_id=conversation_id,
            max_iterations=3  # Prevent infinite loops
        )
        
        try:
            # PHASE 1: UNDERSTAND
            context.state = AgentState.UNDERSTANDING
            understanding = await self.understander.understand(
                query, 
                conversation_history
            )
            context.intent = understanding.intent
            context.entities = understanding.entities
            context.query_type = understanding.query_type
            
            # Main agentic loop
            while context.iteration < context.max_iterations:
                context.iteration += 1
                
                # PHASE 2: PLAN
                context.state = AgentState.PLANNING
                if context.iteration == 1:
                    # Initial plan
                    plan = await self.planner.create_plan(
                        query=query,
                        intent=context.intent,
                        entities=context.entities
                    )
                else:
                    # Replan based on reflection
                    context.state = AgentState.REPLANNING
                    plan = await self.replanner.replan(
                        context=context,
                        reflection=context.last_reflection
                    )
                
                context.current_plan = plan
                context.plan_history.append(plan)
                
                # PHASE 3: EXECUTE
                context.state = AgentState.EXECUTING
                results = await self.executor.execute(plan)
                context.results = results
                context.tool_calls.extend(results.get('tool_calls', []))
                
                # PHASE 4: EVALUATE
                context.state = AgentState.EVALUATING
                evaluation = await self.evaluator.evaluate(
                    query=query,
                    query_type=context.query_type,
                    results=results,
                    context=context
                )
                context.result_quality = evaluation.score
                context.quality_reasons = evaluation.reasons
                context.is_sufficient = evaluation.is_sufficient
                
                # Check if we're done
                if evaluation.is_sufficient:
                    # Record successful strategy
                    context.successful_strategies.append(
                        self._describe_strategy(plan)
                    )
                    break
                
                # PHASE 5: REFLECT (if not sufficient)
                context.state = AgentState.REFLECTING
                reflection = await self.reflector.reflect(
                    context=context,
                    evaluation=evaluation
                )
                context.failure_reasons.append(reflection.failure_analysis)
                context.improvement_suggestions.extend(
                    reflection.improvement_strategy.get('details', [])
                )
                context.failed_strategies.append(
                    self._describe_strategy(plan)
                )
                context.last_reflection = reflection
                
                # Log iteration
                logger.info(
                    f"Iteration {context.iteration}: "
                    f"Score={evaluation.score:.2f}, "
                    f"Sufficient={evaluation.is_sufficient}, "
                    f"Root cause={reflection.root_cause}"
                )
            
            # PHASE 6: SYNTHESIZE
            context.state = AgentState.SYNTHESIZING
            response = await self.synthesizer.synthesize(
                query=query,
                context=context,
                results=context.results
            )
            context.final_response = response
            context.state = AgentState.COMPLETE
            
            return AgentResponse(
                response=response,
                context=context,
                iterations=context.iteration,
                final_quality=context.result_quality,
                sources=context.sources
            )
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return AgentResponse(
                response=self._generate_error_response(e, context),
                context=context,
                error=str(e)
            )
    
    def _describe_strategy(self, plan: Dict) -> str:
        """Create a string description of the strategy used."""
        sources = [s.get('source') for s in plan.get('steps', [])]
        queries = [s.get('query', '')[:30] for s in plan.get('steps', [])]
        return f"Sources: {sources}, Queries: {queries}"
```

---

## User Experience Improvements

### 1. Streaming with Progress Updates

```python
async def process_query_streaming(self, query: str, ...):
    """Stream progress updates to the user."""
    
    # Initial status
    yield StreamEvent(type="status", message="Understanding your question...")
    
    understanding = await self.understander.understand(query)
    yield StreamEvent(type="status", message=f"I see you're asking about {understanding.intent}")
    
    # Planning
    yield StreamEvent(type="status", message="Planning how to find this information...")
    plan = await self.planner.create_plan(...)
    
    # Execution with progress
    for step in plan.steps:
        yield StreamEvent(
            type="progress", 
            message=f"Searching {step.source}...",
            progress=step.index / len(plan.steps)
        )
        result = await self.executor.execute_step(step)
        
        # Show early results
        if result.has_results:
            yield StreamEvent(
                type="partial_result",
                data=self._format_partial_result(result)
            )
    
    # If replanning needed, inform user
    if not evaluation.is_sufficient:
        yield StreamEvent(
            type="status",
            message="Let me try a different approach..."
        )
    
    # Final response
    yield StreamEvent(type="response", data=final_response)
```

### 2. Transparency About Iterations

```python
def format_response_with_metadata(self, context: AgentContext) -> str:
    """Add helpful metadata about how the answer was found."""
    
    response = context.final_response
    
    # Add confidence indicator
    if context.result_quality >= 0.8:
        confidence = "🟢 High confidence"
    elif context.result_quality >= 0.6:
        confidence = "🟡 Medium confidence"
    else:
        confidence = "🟠 Lower confidence"
    
    # Add iteration info if multiple attempts
    if context.iteration > 1:
        iteration_note = f"\n\n*I refined my search {context.iteration-1} time(s) to find the best information.*"
    else:
        iteration_note = ""
    
    # Add sources
    sources = self._format_sources(context.sources)
    
    return f"{response}\n\n{confidence}{iteration_note}\n\n{sources}"
```

### 3. Graceful Degradation

```python
async def synthesize(self, context: AgentContext) -> str:
    """Generate response with appropriate caveats."""
    
    if context.result_quality >= 0.8:
        # High quality - confident answer
        return await self._generate_confident_response(context)
    
    elif context.result_quality >= 0.5:
        # Medium quality - answer with caveats
        return await self._generate_response_with_caveats(context)
    
    else:
        # Low quality - be honest about limitations
        return await self._generate_honest_response(context)
    
async def _generate_honest_response(self, context: AgentContext) -> str:
    """When results are insufficient, be transparent."""
    
    return f"""I searched for information about "{context.user_query}" but found limited results.

**What I found:**
{self._summarize_partial_results(context.results)}

**Why this might be incomplete:**
{self._format_reasons(context.failure_reasons)}

**Suggestions:**
- Try rephrasing your question
- Ask about a specific aspect of {context.entities[0] if context.entities else 'the topic'}
- Check the official EU Funding Portal for the latest information

Would you like me to try a different approach?"""
```

---

## Performance Considerations

### 1. LLM Call Optimization

| Phase | LLM Calls | Can We Reduce? |
|-------|-----------|----------------|
| Understanding | 1 | Keep (essential) |
| Planning | 1 | Keep (essential) |
| Execution | 0 | N/A (tools only) |
| Evaluation | 0-1 | Rule-based first, LLM only for edge cases |
| Reflection | 0-1 | Only when replanning needed |
| Replanning | 0-1 | Only when needed |
| Synthesis | 1 | Keep (essential) |

**Best case:** 3 LLM calls (understand + plan + synthesize)
**Worst case:** 3 + 2*(iterations-1) LLM calls

### 2. Caching Strategy

```python
@lru_cache(maxsize=1000)
def get_cached_evaluation(query_hash: str, results_hash: str) -> Optional[EvaluationResult]:
    """Cache evaluation results for identical query+results combinations."""
    pass

@lru_cache(maxsize=500)
def get_cached_plan(intent: str, entities_tuple: tuple) -> Optional[ExecutionPlan]:
    """Cache plans for similar queries."""
    pass
```

### 3. Early Exit Conditions

```python
def should_stop_early(context: AgentContext) -> bool:
    """Determine if we should stop iterating."""
    
    # Good enough results
    if context.result_quality >= 0.8:
        return True
    
    # Diminishing returns
    if context.iteration >= 2:
        prev_quality = context.quality_history[-2] if len(context.quality_history) >= 2 else 0
        if context.result_quality - prev_quality < 0.1:
            return True  # Not improving
    
    # Same failed strategy attempted
    if context.current_plan in context.failed_strategies:
        return True
    
    return False
```

---

## Implementation Phases

### Phase 1: Core Loop (Week 1)
- [ ] AgentContext dataclass
- [ ] Basic state machine
- [ ] Rule-based ResultEvaluator
- [ ] Simple Replanner (query refinement only)
- [ ] Integration with existing ConversationManager

### Phase 2: Intelligence (Week 2)
- [ ] LLM-based evaluation for edge cases
- [ ] Reflector with failure analysis
- [ ] Smarter replanning (source switching)
- [ ] Memory of successful strategies

### Phase 3: UX Polish (Week 3)
- [ ] Streaming progress updates
- [ ] Confidence indicators
- [ ] Graceful degradation
- [ ] Explain-my-reasoning feature

### Phase 4: Optimization (Week 4)
- [ ] Caching layer
- [ ] Parallel execution within iterations
- [ ] Early exit optimization
- [ ] Performance monitoring

---

## Example Scenarios

### Scenario 1: Query Refinement
```
User: "hydrogen stuff"

Iteration 1:
  - Plan: Search "hydrogen stuff" in vector DB
  - Result: 3 low-relevance results
  - Evaluation: Score 0.35 (insufficient)
  - Reflection: Query too vague, need specifics
  
Iteration 2:
  - Replan: Search "hydrogen funding" + "hydrogen projects"
  - Result: 8 relevant results
  - Evaluation: Score 0.75 (sufficient)
  
Response: "I found several hydrogen-related opportunities..."
```

### Scenario 2: Source Switching
```
User: "What's the success rate for EIC Accelerator?"

Iteration 1:
  - Plan: Search vector DB for "EIC Accelerator success rate"
  - Result: Documents about EIC, no statistics
  - Evaluation: Score 0.40 (insufficient - missing stats)
  - Reflection: Need graph DB for statistics
  
Iteration 2:
  - Replan: Query Neo4j for EIC statistics
  - Result: Success rates by year
  - Evaluation: Score 0.85 (sufficient)
  
Response: "The EIC Accelerator success rate has been..."
```

### Scenario 3: Graceful Failure
```
User: "What will Horizon Europe 2028-2034 look like?"

Iteration 1-3: No relevant information found

Final Response:
"I couldn't find information about Horizon Europe 2028-2034 because 
the current programme runs until 2027 and future programmes haven't 
been announced yet. 

For the latest updates, monitor the European Commission's website.
Would you like information about the current Horizon Europe programme instead?"
```

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `app/services/agents/__init__.py` | Create | Agent module |
| `app/services/agents/agent_context.py` | Create | State management |
| `app/services/agents/result_evaluator.py` | Create | Quality evaluation |
| `app/services/agents/reflector.py` | Create | Failure analysis |
| `app/services/agents/replanner.py` | Create | Plan modification |
| `app/services/agents/agentic_manager.py` | Create | Main loop |
| `app/services/conversation/conversation_manager.py` | Modify | Integrate agent |

---

## Decision: Do We Need This?

### Yes, if:
- Users frequently get insufficient results
- Questions often require multiple data sources
- You want best-in-class AI experience
- You're okay with slightly higher LLM costs (2-3x in worst case)

### Maybe not, if:
- Current single-pass works for 90%+ of queries
- LLM costs are a major concern
- Response time is critical (adds 2-5s per retry)
- System is simple enough that retries rarely help

### Recommendation:
**Start with Phase 1** (basic loop with rule-based evaluation). Measure:
1. How often does iteration 2 improve results?
2. What's the average quality improvement?
3. What's the latency impact?

If improvement is >20% for >10% of queries, continue to Phase 2.


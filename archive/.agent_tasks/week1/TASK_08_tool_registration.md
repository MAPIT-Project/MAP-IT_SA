# TASK_08: Register Intelligent Search Tool

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_08 |
| **Day** | 5 |
| **Estimated Time** | 1 hour |
| **Dependencies** | TASK_07 (Data Intelligence Service) |
| **Blocks** | TASK_09 |
| **Priority** | High |

## Objective

Register the new `intelligent_search` tool in the existing `ToolOrchestrator` so that the AI agent can use the Data Intelligence Service for queries requiring graph-based or hybrid retrieval.

## Context

The existing NEWMAPIT system uses a `ToolOrchestrator` that manages available tools. We need to:
1. Add a new `intelligent_search` tool that uses `DataIntelligenceService`
2. Ensure the tool follows existing patterns for consistency
3. Update the AI intent service to recognize when to use this tool

## Files to Modify

| Action | File Path |
|--------|-----------|
| MODIFY | `app/services/tools/tool_orchestrator.py` |
| MODIFY | `app/services/ai_intent_service.py` (optional enhancement) |

## Implementation

### Step 1: Add Intelligent Search Tool to ToolOrchestrator

Add this code to the `_register_builtin_tools` method in `app/services/tools/tool_orchestrator.py`:

```python
# Add this import at the top of the file (with other imports)
# Note: Add near the existing imports, around line 20

# Add to _register_builtin_tools method (around line 945, after existing tool registrations)

        # ====================================================================
        # INTELLIGENT SEARCH TOOL (Graph + Vector + Planner)
        # ====================================================================

        async def intelligent_search(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """
            Intelligent search combining graph relationships and vector similarity.
            Uses LLM-based query planning to determine the best retrieval strategy.

            This tool is best for:
            - Call/topic lookups with specific identifiers
            - Eligibility questions (countries, entity types)
            - Budget and funding questions
            - Consortium composition questions
            - Finding similar calls/topics
            - Organization relationship queries
            """
            from ..data_intelligence_service import DataIntelligenceService

            schema = {
                'query': {
                    'type': 'string',
                    'required': True,
                    'description': 'User question about Horizon Europe calls, eligibility, budgets, or projects'
                },
                'context': {
                    'type': 'string',
                    'default': '',
                    'description': 'Optional conversation context for follow-up questions'
                },
                'max_results': {
                    'type': 'integer',
                    'default': 10,
                    'min': 1,
                    'max': 50,
                    'description': 'Maximum number of results per source'
                }
            }

            try:
                # Validate parameters
                validated_params = ToolValidator.validate_parameters(params, schema)

                query = validated_params['query']
                conversation_context = validated_params.get('context', '')
                max_results = validated_params.get('max_results', 10)

                if not query or not query.strip():
                    return {
                        'success': False,
                        'error': 'Query parameter cannot be empty',
                        'error_type': 'validation_error',
                        'tool_name': 'intelligent_search',
                        'results': {}
                    }

                logger.info(f"🧠 Intelligent search: '{query[:100]}...'")

                # Initialize and execute search
                service = DataIntelligenceService()
                result = await service.search(
                    query=query,
                    context=conversation_context,
                    max_results=max_results
                )

                if not result.success:
                    return {
                        'success': False,
                        'error': result.error or 'Search failed',
                        'error_type': 'execution_error',
                        'tool_name': 'intelligent_search',
                        'query': query,
                        'results': {}
                    }

                # Format successful response
                response = {
                    'success': True,
                    'tool_name': 'intelligent_search',
                    'query': query,
                    'parameters_used': validated_params,
                    'results': {
                        'intent_type': result.intent_type,
                        'confidence': result.confidence,
                        'answer_context': result.answer_context,
                        'graph_results': result.graph_results,
                        'vector_results': result.vector_results,
                        'sources': result.sources,
                        'total_time_ms': result.total_time_ms
                    },
                    'metadata': {
                        'search_type': 'intelligent_hybrid',
                        'data_sources_used': [s['type'] for s in result.sources],
                        'plan_intent': result.intent_type,
                        'plan_confidence': result.confidence,
                        'timestamp': datetime.now().isoformat()
                    }
                }

                logger.info(f"✅ Intelligent search completed: {result.intent_type} "
                           f"({len(result.graph_results)} graph, {len(result.vector_results)} vector results)")

                return response

            except ValueError as e:
                logger.error(f"Intelligent search validation error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'validation_error',
                    'tool_name': 'intelligent_search',
                    'query': params.get('query', ''),
                    'results': {}
                }
            except Exception as e:
                logger.error(f"Intelligent search execution error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'execution_error',
                    'tool_name': 'intelligent_search',
                    'query': params.get('query', ''),
                    'results': {}
                }

        intelligent_search_tool = Tool(
            name='intelligent_search',
            description='''Intelligent search combining Neo4j graph relationships and vector similarity.
Uses LLM-based query planning to determine the optimal retrieval strategy.

Best for:
- Call/topic lookups ("What is HORIZON-CL4-2025-DATA-01?")
- Eligibility questions ("Can Switzerland participate?", "Are SMEs eligible?")
- Budget questions ("Maximum budget for RIA in Cluster 5?")
- Consortium questions ("How many partners needed?", "Country requirements?")
- Similar calls ("Find calls like HORIZON-CL4-2024-HUMAN-01")
- Organization queries ("Who has TU Delft collaborated with?")

This tool should be preferred over basic search for complex questions that:
- Involve relationships between entities
- Require structured data (budgets, statistics)
- Ask about eligibility or requirements
- Need to find similar items''',
            parameters_schema={
                'query': {
                    'type': 'string',
                    'required': True,
                    'description': 'User question about Horizon Europe',
                    'examples': [
                        'What is the deadline for HORIZON-CL4-2025-DATA-01?',
                        'Can an SME from Switzerland participate in Cluster 4?',
                        'What is the maximum budget for RIA actions?',
                        'Find calls similar to HORIZON-CL4-2024-HUMAN-01'
                    ]
                },
                'context': {
                    'type': 'string',
                    'default': '',
                    'description': 'Conversation context for follow-up questions'
                },
                'max_results': {
                    'type': 'integer',
                    'default': 10,
                    'min': 1,
                    'max': 50,
                    'description': 'Maximum results per data source'
                }
            },
            execute_func=intelligent_search,
            cache_ttl=1800,  # 30 minutes
            parallel_safe=True,
            category='data_intelligence',
            tags=['graph', 'vector', 'hybrid', 'intelligent', 'horizon_europe', 'eligibility', 'budget', 'calls'],
            usage_examples=[
                'What is the deadline for HORIZON-CL4-2025-DATA-01?',
                'Can an SME from Switzerland participate in Cluster 4 calls?',
                'What is the maximum budget for RIA actions in Cluster 5?',
                'What is the minimum number of countries required for a CSA?',
                'Find calls similar to HORIZON-CL4-2024-HUMAN-01',
                'Which organizations have collaborated with Fraunhofer?'
            ]
        )

        self.register_tool(intelligent_search_tool)
        logger.info("📊 Registered intelligent_search tool")
```

### Step 2: Update Tool Registration in create_research_orchestrator

Also add the tool to the `create_research_orchestrator` function (around line 1466):

```python
def create_research_orchestrator(cache_client = None) -> ToolOrchestrator:
    """
    Create a tool orchestrator with research-specific tools.

    Args:
        cache_client: Redis client for caching

    Returns:
        Configured ToolOrchestrator
    """
    orchestrator = ToolOrchestrator(cache_client)

    # ... existing tool registrations ...

    # Add intelligent search tool
    async def intelligent_search_exec(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intelligent search using Data Intelligence Service."""
        from ..data_intelligence_service import DataIntelligenceService

        try:
            query = params.get('query', '')
            conversation_context = params.get('context', '')
            max_results = params.get('max_results', 10)

            if not query.strip():
                return {
                    'success': False,
                    'error': 'Query cannot be empty',
                    'results': {}
                }

            service = DataIntelligenceService()
            result = await service.search(query, conversation_context, max_results)

            return {
                'success': result.success,
                'tool_name': 'intelligent_search',
                'query': query,
                'results': {
                    'intent_type': result.intent_type,
                    'confidence': result.confidence,
                    'answer_context': result.answer_context,
                    'graph_results': result.graph_results,
                    'vector_results': result.vector_results,
                    'sources': result.sources
                },
                'error': result.error
            }
        except Exception as e:
            logger.error(f"Intelligent search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': {}
            }

    intelligent_tool = Tool(
        name='intelligent_search',
        description='Intelligent search using graph + vector databases with LLM planning',
        parameters_schema={
            'query': {'type': 'string', 'required': True},
            'context': {'type': 'string', 'default': ''},
            'max_results': {'type': 'integer', 'default': 10}
        },
        execute_func=intelligent_search_exec,
        cache_ttl=1800,
        parallel_safe=True,
        category='data_intelligence',
        tags=['graph', 'vector', 'intelligent', 'horizon_europe']
    )

    orchestrator.register_tool(intelligent_tool)

    return orchestrator
```

### Step 3: (Optional) Update AI Intent Service

Optionally, update `app/services/ai_intent_service.py` to recognize when to use the intelligent_search tool. Add to the tool list in `_create_intent_analysis_prompt`:

```python
# In the available_tools list (around line 86-126), add:
{
    "name": "intelligent_search",
    "description": "Intelligent search using graph relationships and vector similarity with LLM planning. Best for eligibility, budget, consortium, and call-specific queries.",
    "parameters": {
        "query": "string (required)",
        "context": "string (optional)",
        "max_results": "integer (optional, default 10)"
    }
}
```

And update the classification rules section to mention when to use intelligent_search:

```python
# Add to the CLASSIFICATION RULES section:

# 4. "intelligent_search" - Use for complex queries requiring graph + vector
#    Patterns: eligibility checks, budget questions, consortium rules, similar calls
#    Keywords: "eligible", "can participate", "budget", "maximum", "partners", "similar to"
#    Examples: "Can Switzerland participate?", "What is the budget for RIA?", "Find similar calls"
```

## Acceptance Criteria

- [ ] `intelligent_search` tool registered in ToolOrchestrator
- [ ] Tool appears in `get_available_tools()` output
- [ ] Tool executes successfully with test query
- [ ] Tool handles errors gracefully
- [ ] Tool returns properly formatted results
- [ ] Tool is available in `create_research_orchestrator()`

## Verification Commands

```bash
# 1. Check tool is registered
python -c "
from app.services.tools.tool_orchestrator import ToolOrchestrator
orchestrator = ToolOrchestrator()
tools = orchestrator.get_available_tools()
intelligent = [t for t in tools if t['name'] == 'intelligent_search']
if intelligent:
    print('✅ intelligent_search tool registered')
    print(f'   Category: {intelligent[0][\"category\"]}')
    print(f'   Tags: {intelligent[0][\"tags\"]}')
else:
    print('❌ Tool not found')
"

# 2. Test tool execution
python -c "
import asyncio
from app.services.tools.tool_orchestrator import ToolOrchestrator, ToolCall

async def test():
    orchestrator = ToolOrchestrator()

    # Create a tool call
    call = ToolCall(
        tool_name='intelligent_search',
        parameters={'query': 'Can Switzerland participate in Cluster 4?'},
        execution_order=1
    )

    # Execute
    results = await orchestrator.execute_plan([call], conversation_id=999)

    if 'intelligent_search' in results:
        result = results['intelligent_search']
        print(f'Success: {result.success}')
        if result.success:
            print(f'Intent: {result.result.get(\"results\", {}).get(\"intent_type\")}')
        else:
            print(f'Error: {result.error_message}')
    else:
        print('Tool not executed')

asyncio.run(test())
"

# 3. Print all available tools
python -c "
from app.services.tools.tool_orchestrator import ToolOrchestrator
orchestrator = ToolOrchestrator()
orchestrator.print_available_tools()
"
```

## Notes for Agent

1. The intelligent_search tool should complement, not replace, existing tools
2. It's specifically designed for complex queries that benefit from graph + vector search
3. The tool uses async execution - ensure the orchestrator handles this correctly
4. Cache TTL is set to 30 minutes to balance freshness with performance
5. The tool is marked as `parallel_safe=True` for potential parallel execution
6. Error handling should match the pattern of existing tools
7. The metadata returned includes timing and source information for debugging

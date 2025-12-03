"""
Tool orchestration system for AI agents.
Manages tool selection, execution, and result caching.
"""

import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolCall:
    """Represents a tool call with parameters"""
    tool_name: str
    parameters: Dict[str, Any]
    execution_order: int
    depends_on: Optional[List[str]] = None  # Tool names this depends on

@dataclass
class ToolResult:
    """Represents the result of a tool execution"""
    tool_name: str
    success: bool
    result: Any
    execution_time_ms: int
    error_message: Optional[str] = None
    cached: bool = False

@dataclass
class Tool:
    """Represents a tool that can be executed"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    execute_func: Callable
    cache_ttl: int = 3600  # Cache for 1 hour by default
    parallel_safe: bool = True
    category: str = "general"  # Tool category for AI planning
    tags: List[str] = None  # Tags for tool discovery
    usage_examples: List[str] = None  # Example usage patterns
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.usage_examples is None:
            self.usage_examples = []

class ToolValidator:
    """Utility class for validating tool parameters."""
    
    @staticmethod
    def validate_parameters(params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters against schema.
        
        Args:
            params: Parameters to validate
            schema: Parameter schema
            
        Returns:
            Validated and normalized parameters
            
        Raises:
            ValueError: If validation fails
        """
        validated = {}
        errors = []
        
        for param_name, param_config in schema.items():
            param_type = param_config.get('type', 'string')
            required = param_config.get('required', False)
            default = param_config.get('default')
            min_val = param_config.get('min')
            max_val = param_config.get('max')
            
            # Check if parameter is provided
            if param_name not in params:
                if required:
                    errors.append(f"Required parameter '{param_name}' is missing")
                    continue
                elif default is not None:
                    validated[param_name] = default
                    continue
                else:
                    continue
            
            value = params[param_name]
            
            # Type validation and conversion
            try:
                if param_type == 'string':
                    validated[param_name] = str(value)
                elif param_type == 'integer':
                    validated[param_name] = int(value)
                    if min_val is not None and validated[param_name] < min_val:
                        errors.append(f"Parameter '{param_name}' must be >= {min_val}")
                    if max_val is not None and validated[param_name] > max_val:
                        errors.append(f"Parameter '{param_name}' must be <= {max_val}")
                elif param_type == 'boolean':
                    if isinstance(value, str):
                        validated[param_name] = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        validated[param_name] = bool(value)
                elif param_type == 'array':
                    if not isinstance(value, list):
                        errors.append(f"Parameter '{param_name}' must be an array")
                    else:
                        validated[param_name] = value
                else:
                    validated[param_name] = value
                    
            except (ValueError, TypeError) as e:
                errors.append(f"Parameter '{param_name}' type error: {str(e)}")
        
        if errors:
            raise ValueError(f"Parameter validation failed: {'; '.join(errors)}")
        
        return validated

# Example tool implementations for your research domain
class ResearchTools:
    """Collection of research-specific tools."""


    @staticmethod
    async def search_cordis_projects(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for research projects using LOCAL-FIRST multi-source search.
        
        NO external API calls! Uses:
        1. PostgreSQL full-text search (cordis_processed.projects_enriched)
        2. Neo4j graph queries (relationship-based discovery)
        
        Supports:
        - Natural language queries ("AI healthcare projects from Germany")
        - Implicit filter extraction (country names, programmes, funding schemes)
        - Similar project discovery
        - Organization-based project lookup
        """
        from ..local_project_search_service import LocalProjectSearchService
        
        # Define parameter schema for validation
        schema = {
            'query': {
                'type': 'string', 
                'required': True,
                'description': 'Search query for finding relevant research projects'
            },
            'max_results': {
                'type': 'integer', 
                'default': 10,
                'min': 1,
                'max': 50,
                'description': 'Maximum number of projects to return (1-50)'
            },
            'programme': {
                'type': 'string',
                'default': None,
                'description': 'Filter by programme (H2020, HORIZON, FP7)'
            },
            'countries': {
                'type': 'array',
                'default': None,
                'description': 'Filter by country codes (e.g., ["DE", "FR"])'
            },
            'status': {
                'type': 'string',
                'default': None,
                'description': 'Filter by status (SIGNED for active, CLOSED for completed)'
            },
            'include_graph': {
                'type': 'boolean',
                'default': True,
                'description': 'Include Neo4j graph-based search for relationships'
            }
        }

        try:
            # Validate parameters
            validated_params = ToolValidator.validate_parameters(params, schema)
            
            # Extract validated parameters
            query = validated_params['query']
            max_results = validated_params['max_results']
            
            # Validate query is not empty
            if not query or query.strip() == '':
                return {
                    'success': False,
                    'error': 'Query parameter cannot be empty',
                    'error_type': 'validation_error',
                    'tool_name': 'search_cordis_projects',
                    'query': query,
                    'projects_found': 0
                }

            logger.info(f"🔍 LOCAL Project Search: '{query}' (max_results: {max_results})")

            # Build filters from parameters
            filters = {}
            if validated_params.get('programme'):
                filters['programme'] = validated_params['programme']
            if validated_params.get('countries'):
                filters['countries'] = validated_params['countries']
            if validated_params.get('status'):
                filters['status'] = validated_params['status']

            # Execute LOCAL-FIRST search (no API calls!)
            search_service = LocalProjectSearchService()
            results = await search_service.search_projects(
                query=query,
                filters=filters if filters else None,
                limit=max_results,
                include_graph=validated_params.get('include_graph', True)
            )

            # Format response
            projects = results.get('projects', [])
            
            response = {
                'success': True,
                'tool_name': 'search_cordis_projects',
                'query': query,
                'parameters_used': validated_params,
                'results': {
                    'projects': projects,
                    'projects_found': results.get('total_found', len(projects)),
                    'returned': results.get('returned', len(projects)),
                    'data_source': 'local_multi_source',
                    'processing_time_ms': results.get('processing_time_ms', 0)
                },
                'metadata': {
                    'search_type': 'local_multi_source',
                    'sources_used': results.get('sources_used', []),
                    'filters_applied': results.get('filters_applied', {}),
                    'search_terms': results.get('search_terms', []),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            logger.info(f"✅ Local project search completed: {len(projects)} projects found from {results.get('sources_used', [])}")
            return response

        except ValueError as e:
            # Parameter validation error
            logger.error(f"Project search validation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'validation_error',
                'tool_name': 'search_cordis_projects',
                'query': params.get('query', ''),
                'projects_found': 0
            }
        except Exception as e:
            # Execution error
            logger.error(f"Project search execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'execution_error',
                'tool_name': 'search_cordis_projects',
                'query': params.get('query', ''),
                'projects_found': 0
            }

    # Singleton RAG service to avoid recreating it every time
    _rag_service_instance = None
    
    @staticmethod
    def _get_rag_service():
        """Get or create singleton RAG service instance."""
        if ResearchTools._rag_service_instance is None:
            from ..enhanced_rag_service import HorizonEuropeRAG
            logger.info("🔧 Creating singleton RAG service instance")
            ResearchTools._rag_service_instance = HorizonEuropeRAG()
        return ResearchTools._rag_service_instance
    
    @staticmethod
    async def search_local_database(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search local document database for conversational queries using enhanced RAG.

        This tool searches the local Horizon Europe document database to provide
        contextual answers to general questions, procedural queries, and informational requests.
        """
        # Define parameter schema for validation
        schema = {
            'query': {
                'type': 'string',
                'required': True,
                'description': 'Search query for finding relevant information in local documents'
            },
            'max_context_chunks': {
                'type': 'integer',
                'default': 5,
                'min': 1,
                'max': 10,
                'description': 'Maximum number of document chunks to use for context (1-10)'
            },
            'search_type': {
                'type': 'string',
                'default': 'hybrid',
                'description': 'Search type: semantic, keyword, or hybrid',
                'allowed_values': ['semantic', 'keyword', 'hybrid']
            },
            'similarity_threshold': {
                'type': 'float',
                'default': 0.7,
                'min': 0.1,
                'max': 1.0,
                'description': 'Similarity threshold for search results (0.1-1.0)'
            }
        }

        try:
            # Validate parameters
            validated_params = ToolValidator.validate_parameters(params, schema)

            # Extract validated parameters
            query = validated_params['query']
            max_context_chunks = validated_params['max_context_chunks']
            search_type = validated_params['search_type']
            similarity_threshold = validated_params['similarity_threshold']

            # Validate query is not empty
            if not query or query.strip() == '':
                return {
                    'success': False,
                    'error': 'Query parameter cannot be empty',
                    'error_type': 'validation_error',
                    'query': query,
                    'documents_found': 0
                }

            # Fast path for simple greetings - don't search database
            query_lower = query.lower().strip()
            logger.info(f"🔍 Checking fast path for query: '{query}' (lower: '{query_lower}', len: {len(query_lower)})")
            simple_greetings = ['hi', 'hello', 'hey', 'greeting', 'greetings', 'good morning', 'good afternoon', 'good evening']
            if query_lower in simple_greetings or len(query_lower) < 10:
                logger.info(f"⚡ FAST PATH ACTIVATED for: '{query}'")
                return {
                    'success': True,
                    'tool_name': 'search_local_database',
                    'query': query,
                    'parameters_used': validated_params,
                    'results': {
                        'answer': "Hello! I'm your Horizon Europe research funding assistant. I can help you find funding calls, search for research projects, answer questions about Horizon Europe programs, and assist with proposal writing. How can I help you today?",
                        'documents_found': 0,
                        'data_source': 'fast_path',
                        'search_type': 'greeting',
                        'confidence': 1.0
                    },
                    'metadata': {
                        'search_method': 'fast_path_greeting',
                        'timestamp': datetime.now().isoformat()
                    }
                }

            logger.info(f"🔍 Searching local database: '{query}' (type: {search_type}, chunks: {max_context_chunks})")

            # Use singleton RAG service to avoid recreating it every time
            rag_service = ResearchTools._get_rag_service()
            results = rag_service.handle_general_query(
                question=query,
                max_context_chunks=max_context_chunks,
                search_type=search_type,
                similarity_threshold=similarity_threshold
            )

            # Standardized successful response
            response = {
                'success': True,
                'tool_name': 'search_local_database',
                'query': query,
                'parameters_used': validated_params,
                'results': {
                    'answer': results.get('answer', ''),
                    'documents_found': results.get('chunks_used', 0),
                    'data_source': results.get('data_source', 'local_documents'),
                    'search_type': results.get('search_type', search_type),
                    'confidence': results.get('confidence', 0.0),
                    'sources': results.get('sources', [])
                },
                'metadata': {
                    'search_method': 'enhanced_rag',
                    'document_database': 'horizon_europe_documents',
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': results.get('processing_time', 0) * 1000
                }
            }

            logger.info(f"✅ Local database search completed: {response['results']['documents_found']} documents found")
            return response

        except ValueError as e:
            # Parameter validation error
            logger.error(f"Local database search validation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'validation_error',
                'tool_name': 'search_local_database',
                'query': params.get('query', ''),
                'documents_found': 0
            }
        except Exception as e:
            # Execution error
            logger.error(f"Local database search execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'execution_error',
                'tool_name': 'search_local_database',
                'query': params.get('query', ''),
                'documents_found': 0
            }

    @staticmethod
    async def search_conversation_memory(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search conversation memory for memory-related queries.

        This tool searches through the actual conversation history stored in Redis
        to answer questions about previous messages, conversation context, and memory queries.
        """
        from ..memory.memory_service import MemoryService

        # Define parameter schema for validation
        schema = {
            'query': {
                'type': 'string',
                'required': True,
                'description': 'Search query for finding information in conversation memory'
            },
            'conversation_id': {
                'type': 'integer',
                'required': True,
                'description': 'Conversation ID to search memory for'
            },
            'max_turns': {
                'type': 'integer',
                'default': 20,
                'min': 1,
                'max': 50,
                'description': 'Maximum number of conversation turns to search (1-50)'
            }
        }

        try:
            # Validate parameters
            validated_params = ToolValidator.validate_parameters(params, schema)

            # Extract validated parameters
            query = validated_params['query']
            conversation_id = validated_params['conversation_id']
            max_turns = validated_params['max_turns']

            # Validate query is not empty
            if not query or query.strip() == '':
                return {
                    'success': False,
                    'error': 'Query parameter cannot be empty',
                    'error_type': 'validation_error',
                    'query': query,
                    'turns_found': 0
                }

            logger.info(f"🔍 Searching conversation memory: '{query}' (conversation: {conversation_id}, max_turns: {max_turns})")

            # Initialize memory service
            memory_service = MemoryService()

            # Get recent conversation turns
            turns = memory_service.stm.get_recent_turns(conversation_id, max_turns)

            if not turns:
                return {
                    'success': True,
                    'tool_name': 'search_conversation_memory',
                    'query': query,
                    'parameters_used': validated_params,
                    'results': {
                        'answer': "I don't have any conversation history to search through yet. This appears to be the start of our conversation.",
                        'turns_found': 0,
                        'data_source': 'conversation_memory',
                        'search_type': 'memory',
                        'confidence': 1.0,
                        'sources': []
                    },
                    'metadata': {
                        'search_method': 'conversation_memory',
                        'conversation_id': conversation_id,
                        'timestamp': datetime.now().isoformat(),
                        'processing_time_ms': 0
                    }
                }

            # Search through conversation turns for relevant content
            relevant_turns = []
            search_terms = query.lower().split()

            for turn in turns:
                turn_text = turn.content.lower()
                # Check if any search terms appear in the turn
                if any(term in turn_text for term in search_terms):
                    relevant_turns.append(turn)

            # If no direct matches, return all turns for context
            if not relevant_turns:
                relevant_turns = turns

            # Format the response
            formatted_turns = []
            for i, turn in enumerate(relevant_turns, 1):
                formatted_turns.append({
                    'turn_number': i,
                    'role': turn.role,
                    'content': turn.content,
                    'timestamp': turn.timestamp.isoformat(),
                    'message_id': turn.message_id
                })

            # Create a helpful answer based on the found turns
            if relevant_turns:
                # Group turns by role for better readability
                user_turns = [t for t in relevant_turns if t.role == 'user']
                assistant_turns = [t for t in relevant_turns if t.role == 'assistant']

                answer_parts = []
                if user_turns:
                    answer_parts.append(f"**Your messages:** {len(user_turns)} found")
                    for i, turn in enumerate(user_turns, 1):
                        answer_parts.append(f"{i}. {turn.content}")

                if assistant_turns:
                    answer_parts.append(f"\n**My responses:** {len(assistant_turns)} found")
                    for i, turn in enumerate(assistant_turns, 1):
                        answer_parts.append(f"{i}. {turn.content}")

                answer = "\n".join(answer_parts)
            else:
                answer = f"I searched through our conversation history but couldn't find specific information related to '{query}'. You might want to rephrase your question or provide more details."

            # Standardized successful response
            response = {
                'success': True,
                'tool_name': 'search_conversation_memory',
                'query': query,
                'parameters_used': validated_params,
                'results': {
                    'answer': answer,
                    'turns_found': len(relevant_turns),
                    'total_turns_in_memory': len(turns),
                    'data_source': 'conversation_memory',
                    'search_type': 'memory',
                    'confidence': 0.95 if relevant_turns else 0.3,
                    'sources': formatted_turns
                },
                'metadata': {
                    'search_method': 'conversation_memory',
                    'conversation_id': conversation_id,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_ms': 0
                }
            }

            logger.info(f"✅ Conversation memory search completed: {len(relevant_turns)} relevant turns found")
            return response

        except ValueError as e:
            # Parameter validation error
            logger.error(f"Conversation memory search validation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'validation_error',
                'tool_name': 'search_conversation_memory',
                'query': params.get('query', ''),
                'turns_found': 0
            }
        except Exception as e:
            # Execution error
            logger.error(f"Conversation memory search execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'execution_error',
                'tool_name': 'search_conversation_memory',
                'query': params.get('query', ''),
                'turns_found': 0
            }

class ToolOrchestrator:
    """
    Manages tool selection and execution with caching and error handling.
    """
    
    def __init__(self, cache_client = None):
        """
        Initialize tool orchestrator.

        Args:
            cache_client: Redis client for result caching (optional)
        """
        if cache_client and not REDIS_AVAILABLE:
            logger.warning("Redis client provided but redis not available. Caching disabled.")
            self.cache = None
        else:
            self.cache = cache_client
        self.tools: Dict[str, Tool] = {}
        self.execution_log = []

        # Register built-in tools
        self._register_builtin_tools()
    
    def register_tool(self, tool: Tool):
        """
        Register a new tool.
        
        Args:
            tool: Tool object to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    async def plan_tools(self, task: str, context: str) -> List[ToolCall]:
        """
        Plan which tools to execute for a given task.
        
        Args:
            task: User task description
            context: Conversation context
            
        Returns:
            List of ToolCall objects in execution order
        """
        # For now, return empty list (no tools planned)
        # In a full implementation, this would use AI to plan tool usage
        return []
    
    async def execute_plan(self, 
                          tool_calls: List[ToolCall],
                          conversation_id: int,
                          extracted_keywords: List[str] = None) -> Dict[str, Any]:
        """
        Execute a list of tool calls.
        
        Args:
            tool_calls: List of ToolCall objects
            conversation_id: Conversation ID for logging
            extracted_keywords: AI-extracted search keywords to pass to tools
            
        Returns:
            Combined results from all tool executions
        """
        if not tool_calls:
            return {}
        
        results = {}
        
        # Group tools by execution order
        ordered_calls = sorted(tool_calls, key=lambda x: x.execution_order)
        
        for tool_call in ordered_calls:
            # Check dependencies
            if tool_call.depends_on:
                missing_deps = [dep for dep in tool_call.depends_on if dep not in results]
                if missing_deps:
                    logger.warning(f"Tool {tool_call.tool_name} missing dependencies: {missing_deps}")
                    continue
            
            # Execute tool with extracted keywords
            result = await self._execute_tool(tool_call, conversation_id, results, extracted_keywords)
            results[tool_call.tool_name] = result
        
        return results
    
    async def _execute_tool(self,
                           tool_call: ToolCall,
                           conversation_id: int,
                           previous_results: Dict[str, Any],
                           extracted_keywords: List[str] = None) -> ToolResult:
        """
        Execute a single tool.
        
        Args:
            tool_call: ToolCall to execute
            conversation_id: Conversation ID
            previous_results: Results from previous tool executions
            extracted_keywords: AI-extracted search keywords
            
        Returns:
            ToolResult object
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting execution of tool: {tool_call.tool_name} for conversation {conversation_id}")

            # Check if tool exists
            if tool_call.tool_name not in self.tools:
                error_msg = f"Tool {tool_call.tool_name} not found"
                logger.error(error_msg)
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error_message=error_msg
                )

            tool = self.tools[tool_call.tool_name]
            logger.debug(f"Tool found: {tool.name}, parameters: {tool_call.parameters}")

            # Check cache first
            if self.cache:
                cached_result = await self._get_cached_result(tool_call, conversation_id)
                if cached_result:
                    logger.info(f"Cache hit for tool: {tool_call.tool_name}")
                    return cached_result

            logger.debug(f"Executing tool: {tool_call.tool_name} with params: {tool_call.parameters}")

            # Validate parameters using tool's schema
            try:
                validated_params = ToolValidator.validate_parameters(
                    tool_call.parameters, 
                    tool.parameters_schema
                )
                logger.debug(f"Parameters validated successfully for {tool_call.tool_name}")
            except ValueError as e:
                logger.error(f"Parameter validation failed for {tool_call.tool_name}: {e}")
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error_message=f"Parameter validation error: {str(e)}"
                )

            # Build execution context with extracted keywords and previous results
            execution_context = {
                **previous_results,  # Include previous tool results
                'extracted_keywords': extracted_keywords or []  # Add AI-extracted keywords
            }
            
            # Execute tool with validated parameters and context
            result = await tool.execute_func(validated_params, execution_context)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Tool {tool_call.tool_name} executed successfully in {execution_time:.2f}ms")

            tool_result = ToolResult(
                tool_name=tool_call.tool_name,
                success=True,
                result=result,
                execution_time_ms=int(execution_time),
                cached=False
            )

            # Cache result
            if self.cache:
                await self._cache_result(tool_call, conversation_id, tool_result)
                logger.debug(f"Cached result for tool: {tool_call.tool_name}")

            # Log execution
            await self._log_execution(conversation_id, tool_call, tool_result)

            return tool_result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"{error_msg} for tool {tool_call.tool_name} in {execution_time:.2f}ms")

            error_result = ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                result=None,
                execution_time_ms=int(execution_time),
                error_message=error_msg
            )

            # Log error
            await self._log_execution(conversation_id, tool_call, error_result)

            return error_result
    
    async def _get_cached_result(self,
                                tool_call: ToolCall,
                                conversation_id: int) -> Optional[ToolResult]:
        """
        Get cached result if available.
        
        Args:
            tool_call: ToolCall to check cache for
            conversation_id: Conversation ID
            
        Returns:
            Cached ToolResult or None
        """
        try:
            cache_key = self._generate_cache_key(tool_call, conversation_id)
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return ToolResult(
                    tool_name=data['tool_name'],
                    success=data['success'],
                    result=data['result'],
                    execution_time_ms=data['execution_time_ms'],
                    error_message=data.get('error_message'),
                    cached=True
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            return None
    
    async def _cache_result(self,
                            tool_call: ToolCall,
                            conversation_id: int,
                            result: ToolResult):
        """
        Cache tool execution result.

        Args:
            tool_call: ToolCall that was executed
            conversation_id: Conversation ID
            result: ToolResult to cache
        """
        try:
            tool = self.tools[tool_call.tool_name]
            cache_key = self._generate_cache_key(tool_call, conversation_id)

            # Convert result to JSON-serializable format
            serializable_result = self._make_serializable(result.result)

            cache_data = {
                'tool_name': result.tool_name,
                'success': result.success,
                'result': serializable_result,
                'execution_time_ms': result.execution_time_ms,
                'error_message': result.error_message,
                'cached_at': datetime.now().isoformat()
            }

            self.cache.setex(
                cache_key,
                tool.cache_ttl,
                json.dumps(cache_data)
            )

        except Exception as e:
            logger.warning(f"Cache storage error: {e}")

    def _make_serializable(self, obj):
        """
        Convert complex objects to JSON-serializable format.

        Args:
            obj: Object to make serializable

        Returns:
            JSON-serializable version of the object
        """
        if obj is None:
            return None
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            # Handle dataclass objects (like EnhancedSearchResult)
            from dataclasses import asdict
            return self._make_serializable(asdict(obj))
        elif hasattr(obj, '__dict__'):
            # Convert other objects to dict
            result = {}
            for key, value in obj.__dict__.items():
                result[key] = self._make_serializable(value)
            return result
        else:
            # Try to convert to string for other types
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    def _generate_cache_key(self,
                           tool_call: ToolCall,
                           conversation_id: int) -> str:
        """
        Generate cache key for tool call.
        
        Args:
            tool_call: ToolCall to generate key for
            conversation_id: Conversation ID
            
        Returns:
            Cache key string
        """
        # Create hash of tool name and parameters
        params_str = json.dumps(tool_call.parameters, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        
        return f"tool_cache:{conversation_id}:{tool_call.tool_name}:{params_hash}"
    
    async def _log_execution(self,
                            conversation_id: int,
                            tool_call: ToolCall,
                            result: ToolResult):
        """
        Log tool execution to database.
        
        Args:
            conversation_id: Conversation ID
            tool_call: ToolCall that was executed
            result: ToolResult from execution
        """
        try:
            # In a full implementation, this would log to the database
            # For now, just log to console
            log_entry = {
                'conversation_id': conversation_id,
                'tool_name': tool_call.tool_name,
                'parameters': tool_call.parameters,
                'success': result.success,
                'execution_time_ms': result.execution_time_ms,
                'cached': result.cached,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Tool execution: {json.dumps(log_entry)}")
            self.execution_log.append(log_entry)
            
        except Exception as e:
            logger.warning(f"Execution logging error: {e}")
    
    def _register_builtin_tools(self):
        """Register built-in tools."""
        
        
        # EU Portal Search Tool
        async def eu_portal_search(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """
            Search EU Funding Portal for calls using improved direct search.
            
            This tool searches the EU Funding & Tenders Portal for funding calls,
            supporting open, closed, and forthcoming calls with simplified, reliable filtering.
            """
            from ..improved_call_search import ImprovedCallSearchService

            # Define parameter schema for validation
            schema = {
                'query': {
                    'type': 'string', 
                    'required': True,
                    'description': 'Search query for finding relevant funding calls'
                },
                'max_results': {
                    'type': 'integer', 
                    'default': 50,  # Increased default from 10 to 50
                    'min': 1,
                    'max': 100,     # Increased max from 50 to 100
                    'description': 'Maximum number of calls to return (1-100)'
                },
                'status': {
                    'type': 'string',
                    'default': 'open',
                    'description': 'Call status filter: open, closed, forthcoming, or all'
                },
                'include_closed': {
                    'type': 'boolean',
                    'default': False,
                    'description': 'Include closed calls in results'
                },
                'programme_period': {
                    'type': 'string',
                    'default': '2021 - 2027',
                    'description': 'Horizon Europe programme period'
                }
            }

            try:
                # Validate parameters
                validated_params = ToolValidator.validate_parameters(params, schema)
                
                # Extract validated parameters
                query = validated_params['query']
                max_results = min(validated_params['max_results'], 100)  # Increased limit
                include_closed = validated_params['include_closed']
                programme_period = validated_params['programme_period']
                
                # Handle status parameter
                status = validated_params.get('status', 'open')
                if status in ['closed', 'all']:
                    include_closed = True
                
                # Validate query is not empty
                if not query or query.strip() == '':
                    return {
                        'success': False,
                        'error': 'Query parameter cannot be empty',
                        'error_type': 'validation_error',
                        'query': query,
                        'calls_found': 0
                    }

                logger.info(f"🔍 Searching EU Portal calls: '{query}' (max_results: {max_results}, include_closed: {include_closed})")

                # Check if we have AI-extracted keywords from context
                extracted_keywords = context.get('extracted_keywords', [])
                
                # Use AI-extracted keywords if available, otherwise use the original query
                search_query = query
                if extracted_keywords:
                    # Join keywords with OR for better search coverage
                    search_query = " OR ".join(extracted_keywords)
                    logger.info(f"🎯 Using AI-extracted keywords: {search_query}")

                # Execute search using improved service
                search_service = ImprovedCallSearchService()
                results = search_service.search_calls_simple(
                    query=search_query,
                    max_results=max_results,
                    include_closed=include_closed,
                    programme_period=programme_period
                )

                # Check if search was successful
                if results.get('status') != 'success':
                    return {
                        'success': False,
                        'error': results.get('error', 'Search failed'),
                        'error_type': 'search_error',
                        'tool_name': 'eu_portal_search',
                        'query': query,
                        'calls_found': 0
                    }

                # Standardized successful response
                calls_data = results.get('results', [])
                response = {
                    'success': True,
                    'tool_name': 'eu_portal_search',
                    'query': query,
                    'parameters_used': validated_params,
                    'results': {
                        'calls_found': len(calls_data),
                        'calls': calls_data,
                        'search_metadata': results.get('search_metadata', {}),
                        'facets': results.get('facets', {})
                    },
                    'metadata': {
                        'search_type': 'simple_direct',
                        'data_source': 'eu_funding_portal',
                        'api_used': 'tech.ec.europa.eu',
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                logger.info(f"✅ EU Portal search completed: {len(calls_data)} calls found")
                return response

            except ValueError as e:
                # Parameter validation error
                logger.error(f"EU Portal search validation error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'validation_error',
                    'tool_name': 'eu_portal_search',
                    'query': params.get('query', ''),
                    'calls_found': 0
                }
            except Exception as e:
                # Execution error
                logger.error(f"EU Portal search execution error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'execution_error',
                    'tool_name': 'eu_portal_search',
                    'query': params.get('query', ''),
                    'calls_found': 0
                }
        
        portal_tool = Tool(
            name='eu_portal_search',
            description='Search EU Funding Portal for funding calls using advanced semantic search',
            parameters_schema={
                'query': {
                    'type': 'string', 
                    'required': True,
                    'description': 'Search query for finding relevant funding calls',
                    'examples': ['clean energy', 'artificial intelligence', 'climate change']
                },
                'max_results': {
                    'type': 'integer', 
                    'default': 10,
                    'min': 1,
                    'max': 50,
                    'description': 'Maximum number of calls to return (1-50)'
                },
                'status': {
                    'type': 'string',
                    'default': 'open',
                    'description': 'Call status filter: open, closed, forthcoming, or all',
                    'allowed_values': ['open', 'closed', 'forthcoming', 'all']
                },
                'include_closed': {
                    'type': 'boolean',
                    'default': False,
                    'description': 'Include closed calls in results'
                },
                'programme_period': {
                    'type': 'string',
                    'default': '2021 - 2027',
                    'description': 'Horizon Europe programme period'
                }
            },
            execute_func=eu_portal_search,
            cache_ttl=3600,  # 1 hour
            parallel_safe=True,
            category='research_funding',
            tags=['eu_funding', 'horizon_europe', 'calls', 'semantic_search'],
            usage_examples=[
                'Find open calls for renewable energy research',
                'Search for AI and machine learning funding opportunities',
                'Look for closed calls in digital transformation'
            ]
        )
        
        # Document Analysis Tool
        # async def analyze_document(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        #     """Analyze a document for key information."""
        #     document_id = params.get('document_id', '')
        #     analysis_type = params.get('analysis_type', 'summary')
            
        #     # Mock implementation
        #     return {
        #         'document_id': document_id,
        #         'analysis_type': analysis_type,
        #         'summary': f'Analysis of document {document_id}',
        #         'key_points': [
        #             'Key finding 1',
        #             'Key finding 2',
        #             'Key finding 3'
        #         ],
        #         'confidence': 0.85
        #     }
        
        # analysis_tool = Tool(
        #     name='analyze_document',
        #     description='Analyze documents for key information',
        #     parameters_schema={
        #         'document_id': {'type': 'string', 'required': True},
        #         'analysis_type': {'type': 'string', 'default': 'summary'}
        #     },
        #     execute_func=analyze_document,
        #     cache_ttl=7200,  # 2 hours
        #     parallel_safe=True
        # )
        
        # Conversational Database Search Tool
        async def search_local_database(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """
            Search local document database for conversational queries using enhanced RAG.

            This tool searches the local Horizon Europe document database to provide
            contextual answers to general questions, procedural queries, and informational requests.
            """
            from ..enhanced_rag_service import HorizonEuropeRAG

            # Define parameter schema for validation
            schema = {
                'query': {
                    'type': 'string',
                    'required': True,
                    'description': 'Search query for finding relevant information in local documents'
                },
                'max_context_chunks': {
                    'type': 'integer',
                    'default': 5,
                    'min': 1,
                    'max': 10,
                    'description': 'Maximum number of document chunks to use for context (1-10)'
                },
                'search_type': {
                    'type': 'string',
                    'default': 'hybrid',
                    'description': 'Search type: semantic, keyword, or hybrid',
                    'allowed_values': ['semantic', 'keyword', 'hybrid']
                },
                'similarity_threshold': {
                    'type': 'float',
                    'default': 0.7,
                    'min': 0.1,
                    'max': 1.0,
                    'description': 'Similarity threshold for search results (0.1-1.0)'
                }
            }

            try:
                # Validate parameters
                validated_params = ToolValidator.validate_parameters(params, schema)

                # Extract validated parameters
                query = validated_params['query']
                max_context_chunks = validated_params['max_context_chunks']
                search_type = validated_params['search_type']
                similarity_threshold = validated_params['similarity_threshold']

                # Validate query is not empty
                if not query or query.strip() == '':
                    return {
                        'success': False,
                        'error': 'Query parameter cannot be empty',
                        'error_type': 'validation_error',
                        'query': query,
                        'documents_found': 0
                    }

                logger.info(f"🔍 Searching local database: '{query}' (type: {search_type}, chunks: {max_context_chunks})")

                # Execute search using enhanced RAG service
                rag_service = HorizonEuropeRAG()
                results = rag_service.handle_general_query(
                    question=query,
                    max_context_chunks=max_context_chunks,
                    search_type=search_type,
                    similarity_threshold=similarity_threshold
                )

                # Standardized successful response
                response = {
                    'success': True,
                    'tool_name': 'search_local_database',
                    'query': query,
                    'parameters_used': validated_params,
                    'results': {
                        'answer': results.get('answer', ''),
                        'documents_found': results.get('chunks_used', 0),
                        'data_source': results.get('data_source', 'local_documents'),
                        'search_type': results.get('search_type', search_type),
                        'confidence': results.get('confidence', 0.0),
                        'sources': results.get('sources', [])
                    },
                    'metadata': {
                        'search_method': 'enhanced_rag',
                        'document_database': 'horizon_europe_documents',
                        'timestamp': datetime.now().isoformat(),
                        'processing_time_ms': results.get('processing_time', 0) * 1000
                    }
                }

                logger.info(f"✅ Local database search completed: {response['results']['documents_found']} documents found")
                return response

            except ValueError as e:
                # Parameter validation error
                logger.error(f"Local database search validation error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'validation_error',
                    'tool_name': 'search_local_database',
                    'query': params.get('query', ''),
                    'documents_found': 0
                }
            except Exception as e:
                # Execution error
                logger.error(f"Local database search execution error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'execution_error',
                    'tool_name': 'search_local_database',
                    'query': params.get('query', ''),
                    'documents_found': 0
                }

        database_tool = Tool(
            name='search_local_database',
            description='Search local Horizon Europe document database for conversational queries and informational requests',
            parameters_schema={
                'query': {
                    'type': 'string',
                    'required': True,
                    'description': 'Search query for finding relevant information in local documents',
                    'examples': ['How to apply for Horizon Europe funding?', 'What are the eligibility requirements?', 'Explain the evaluation process']
                },
                'max_context_chunks': {
                    'type': 'integer',
                    'default': 5,
                    'min': 1,
                    'max': 10,
                    'description': 'Maximum number of document chunks to use for context (1-10)'
                },
                'search_type': {
                    'type': 'string',
                    'default': 'hybrid',
                    'description': 'Search type: semantic, keyword, or hybrid',
                    'allowed_values': ['semantic', 'keyword', 'hybrid']
                },
                'similarity_threshold': {
                    'type': 'float',
                    'default': 0.7,
                    'min': 0.1,
                    'max': 1.0,
                    'description': 'Similarity threshold for search results (0.1-1.0)'
                }
            },
            execute_func=search_local_database,
            cache_ttl=1800,  # 30 minutes - shorter cache for conversational queries
            parallel_safe=True,
            category='conversational_search',
            tags=['local_database', 'conversational', 'documents', 'rag', 'horizon_europe'],
            usage_examples=[
                'How do I apply for Horizon Europe funding?',
                'What are the eligibility requirements for grants?',
                'Explain the proposal evaluation process',
                'What documents do I need to submit?',
                'How does the funding system work?'
            ]
        )

        # Register all tools
        self.register_tool(portal_tool)
        self.register_tool(database_tool)

        # Register memory search tool
        memory_tool = Tool(
            name='search_conversation_memory',
            description='Search conversation memory for questions about previous messages and conversation history',
            parameters_schema={
                'query': {
                    'type': 'string',
                    'required': True,
                    'description': 'Search query for finding information in conversation memory',
                    'examples': ['What was my first message?', 'What did I ask about earlier?', 'Show me our conversation history']
                },
                'conversation_id': {
                    'type': 'integer',
                    'required': True,
                    'description': 'Conversation ID to search memory for'
                },
                'max_turns': {
                    'type': 'integer',
                    'default': 20,
                    'min': 1,
                    'max': 50,
                    'description': 'Maximum number of conversation turns to search (1-50)'
                }
            },
            execute_func=ResearchTools.search_conversation_memory,
            cache_ttl=300,  # 5 minutes - shorter cache for memory queries
            parallel_safe=True,
            category='memory_search',
            tags=['conversation_memory', 'memory', 'history', 'chat_history'],
            usage_examples=[
                'What was the first message I sent you?',
                'What did I ask about renewable energy?',
                'Show me our previous conversation about Horizon Europe',
                'What topics have we discussed?',
                'Can you remind me what I said earlier?'
            ]
        )
        self.register_tool(memory_tool)
        
        # ====================================================================
        # INTELLIGENT SEARCH TOOL (Graph + Vector + Planner)
        # ====================================================================
        
        async def intelligent_search_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """
            Intelligent search combining graph relationships and vector similarity.
            Uses LLM-based query planning to determine the best retrieval strategy.
            """
            try:
                # Import here to avoid circular imports
                try:
                    from ..data_intelligence_service import DataIntelligenceService
                except ImportError:
                    from app.services.data_intelligence_service import DataIntelligenceService
                
                query = params.get('query', '')
                conversation_context = params.get('context', '')
                max_results = params.get('max_results', 10)
                
                if not query or not query.strip():
                    return {
                        'success': False,
                        'error': 'Query parameter cannot be empty',
                        'error_type': 'validation_error',
                        'tool_name': 'intelligent_search',
                        'results': {}
                    }
                
                logger.info(f"🧠 Intelligent search: '{query[:80]}...'")
                
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
                        'plan_confidence': result.confidence
                    }
                }
                
                logger.info(f"✅ Intelligent search: {result.intent_type} "
                           f"({len(result.graph_results)} graph, {len(result.vector_results)} vector)")
                
                return response
                
            except Exception as e:
                logger.error(f"Intelligent search error: {e}")
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
- Call/topic lookups ("What is HORIZON-CL4-2022-DATA-01-02?", "Tell me about ERC-2024-STG")
- Eligibility questions ("Can Switzerland participate?", "Are SMEs eligible?")
- Budget questions ("Maximum budget for RIA in Cluster 5?", "Average project funding?")
- Consortium questions ("How many partners needed?", "Typical consortium size?")
- Similar calls ("Find topics like HORIZON-CL4-2022-HUMAN-01")
- Organization queries ("Who has TU Delft collaborated with?")

This tool should be preferred over basic search for complex questions about:
- Relationships between entities (organizations, projects, countries)
- Structured data (budgets, statistics, patterns)
- Eligibility and requirements
- Finding similar items based on graph structure''',
            parameters_schema={
                'query': {
                    'type': 'string',
                    'required': True,
                    'description': 'User question about Horizon Europe funding, calls, eligibility, budgets, or projects',
                    'examples': [
                        'What is HORIZON-CL4-2022-DATA-01-02?',
                        'Can an SME from Switzerland participate in Cluster 4?',
                        'What is the maximum budget for RIA actions?',
                        'Find calls similar to HORIZON-CL4-2022-HUMAN-01'
                    ]
                },
                'context': {
                    'type': 'string',
                    'required': False,
                    'default': '',
                    'description': 'Conversation context for follow-up questions'
                },
                'max_results': {
                    'type': 'integer',
                    'required': False,
                    'default': 10,
                    'min': 1,
                    'max': 50,
                    'description': 'Maximum results per data source'
                }
            },
            execute_func=intelligent_search_execute,
            cache_ttl=1800,  # 30 minutes
            parallel_safe=True,
            category='data_intelligence',
            tags=['graph', 'vector', 'hybrid', 'intelligent', 'horizon_europe', 
                  'eligibility', 'budget', 'calls', 'topics', 'neo4j'],
            usage_examples=[
                'What is the deadline for HORIZON-CL4-2022-DATA-01-02?',
                'Can an SME from Switzerland participate in Cluster 4 calls?',
                'What is the maximum budget for RIA actions in Cluster 5?',
                'What is the minimum number of countries required for a CSA?',
                'Find calls similar to HORIZON-CL4-2022-HUMAN-01',
                'Which organizations have collaborated with Fraunhofer?',
                'What is the typical consortium size for Cluster 6?',
                'Tell me about ERC-2024-STG funding'
            ]
        )
        
        self.register_tool(intelligent_search_tool)
        logger.info("📊 Registered intelligent_search tool")
        
        # ====================================================================
        # CONSORTIUM BUILDER TOOL
        # ====================================================================
        
        async def consortium_builder_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """
            Build consortium suggestions based on track record and geographic diversity.
            """
            try:
                from ..data_intelligence.graph_service import GraphSearchService
                
                cluster_code = params.get('cluster_code', '')
                topic_code = params.get('topic_code')
                coordinator_country = params.get('coordinator_country')
                target_partners = params.get('target_partners', 5)
                
                if not cluster_code:
                    return {
                        'success': False,
                        'error': 'cluster_code is required',
                        'error_type': 'validation_error',
                        'tool_name': 'consortium_builder',
                        'results': {}
                    }
                
                logger.info(f"🏢 Building consortium for {cluster_code}")
                
                service = GraphSearchService()
                result = service.suggest_consortium_partners(
                    cluster_code=cluster_code,
                    topic_code=topic_code,
                    coordinator_country=coordinator_country,
                    target_partner_count=target_partners
                )
                
                return {
                    'success': True,
                    'tool_name': 'consortium_builder',
                    'results': result,
                    'metadata': {
                        'cluster': cluster_code,
                        'partners_suggested': len(result.get('suggestions', [])),
                        'countries_covered': len(result.get('countries_covered', []))
                    }
                }
                
            except Exception as e:
                logger.error(f"Consortium builder error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'execution_error',
                    'tool_name': 'consortium_builder',
                    'results': {}
                }
        
        consortium_builder_tool = Tool(
            name='consortium_builder',
            description='''Suggests potential consortium partners for Horizon Europe proposals.

Analyzes the Neo4j graph database to find organizations with:
- Strong track record in the target cluster/topic
- Geographic diversity (different EU countries)
- Balanced entity types (HES, REC, PRC mix)
- Prior successful collaborations

Use this tool when the user is:
- Preparing a proposal and needs partner suggestions
- Looking for organizations in a specific cluster
- Wanting to build a balanced consortium''',
            parameters_schema={
                'cluster_code': {
                    'type': 'string',
                    'required': True,
                    'description': 'Target cluster (e.g., "CLUSTER-4", "CLUSTER-5")'
                },
                'topic_code': {
                    'type': 'string',
                    'required': False,
                    'description': 'Specific topic code (optional)'
                },
                'coordinator_country': {
                    'type': 'string',
                    'required': False,
                    'description': 'Country code to exclude (e.g., "NL" if coordinator is Dutch)'
                },
                'target_partners': {
                    'type': 'integer',
                    'required': False,
                    'default': 5,
                    'min': 3,
                    'max': 15,
                    'description': 'Number of partners to suggest'
                }
            },
            execute_func=consortium_builder_execute,
            cache_ttl=3600,  # 1 hour
            parallel_safe=True,
            category='data_intelligence',
            tags=['consortium', 'partners', 'proposal', 'horizon_europe', 'collaboration'],
            usage_examples=[
                'Suggest partners for a Cluster 4 proposal',
                'Find potential consortium members for CLUSTER-5',
                'Build a consortium for digital project, coordinator from Germany'
            ]
        )
        
        self.register_tool(consortium_builder_tool)
        logger.info("🏢 Registered consortium_builder tool")
        
        # ====================================================================
        # COMPLIANCE CHECKER TOOL
        # ====================================================================
        
        async def compliance_checker_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """
            Check consortium compliance against Horizon Europe rules.
            """
            try:
                from ..data_intelligence.graph_service import GraphSearchService
                
                partners = params.get('partners', [])
                action_type = params.get('action_type', 'RIA')
                
                if not partners:
                    return {
                        'success': False,
                        'error': 'partners list is required',
                        'error_type': 'validation_error',
                        'tool_name': 'compliance_checker',
                        'results': {}
                    }
                
                logger.info(f"✅ Checking compliance for {len(partners)} partners ({action_type})")
                
                service = GraphSearchService()
                result = service.check_consortium_compliance(
                    partners=partners,
                    action_type=action_type
                )
                
                return {
                    'success': True,
                    'tool_name': 'compliance_checker',
                    'results': result,
                    'metadata': {
                        'is_compliant': result.get('is_compliant'),
                        'issues_count': len(result.get('issues', [])),
                        'warnings_count': len(result.get('warnings', []))
                    }
                }
                
            except Exception as e:
                logger.error(f"Compliance checker error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'execution_error',
                    'tool_name': 'compliance_checker',
                    'results': {}
                }
        
        compliance_checker_tool = Tool(
            name='compliance_checker',
            description='''Validates consortium composition against Horizon Europe eligibility rules.

Checks:
- Minimum partner count for action type (RIA/IA: 3, CSA: 1)
- Country diversity requirements (RIA/IA: 3 different countries)
- Coordinator eligibility (must be from EU/Associated country)
- Entity type balance recommendations

Returns issues that must be addressed and recommendations for improvement.''',
            parameters_schema={
                'partners': {
                    'type': 'array',
                    'required': True,
                    'description': 'List of partners with {country, entity_type, is_coordinator}',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'country': {'type': 'string', 'description': 'ISO country code (e.g., "DE", "NL")'},
                            'entity_type': {'type': 'string', 'description': 'Entity type (HES, REC, PRC, SME)'},
                            'is_coordinator': {'type': 'boolean', 'description': 'Is this the coordinator?'}
                        }
                    }
                },
                'action_type': {
                    'type': 'string',
                    'required': False,
                    'default': 'RIA',
                    'description': 'Action type: RIA, IA, CSA, ERC, MSCA'
                }
            },
            execute_func=compliance_checker_execute,
            cache_ttl=0,  # No caching - always check fresh
            parallel_safe=True,
            category='data_intelligence',
            tags=['compliance', 'eligibility', 'validation', 'consortium', 'horizon_europe'],
            usage_examples=[
                'Check if our 3-partner consortium is eligible for RIA',
                'Validate consortium composition for IA action',
                'Is our consortium eligible with partners from DE, NL, FR?'
            ]
        )
        
        self.register_tool(compliance_checker_tool)
        logger.info("✅ Registered compliance_checker tool")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools with their descriptions and metadata.

        Returns:
            List of tool information dictionaries with enhanced metadata
        """
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'category': tool.category,
                'tags': tool.tags,
                'parameters': tool.parameters_schema,
                'cache_ttl': tool.cache_ttl,
                'parallel_safe': tool.parallel_safe,
                'usage_examples': tool.usage_examples
            }
            for tool in self.tools.values()
        ]

    def print_available_tools(self):
        """
        Print available tools in a readable format for manual inspection.
        """
        if not self.tools:
            print("No tools registered.")
            return

        print(f"\n{'='*60}")
        print("REGISTERED TOOLS")
        print(f"{'='*60}")

        for i, tool in enumerate(self.tools.values(), 1):
            print(f"\n{i}. Tool: {tool.name}")
            print(f"   Description: {tool.description}")
            print(f"   Cache TTL: {tool.cache_ttl} seconds")
            print(f"   Parallel Safe: {tool.parallel_safe}")

            print("   Parameters:")
            for param_name, param_info in tool.parameters_schema.items():
                required = param_info.get('required', False)
                param_type = param_info.get('type', 'unknown')
                default = param_info.get('default', 'N/A')
                print(f"     - {param_name} ({param_type}) {'[required]' if required else '[optional]'} default: {default}")

        print(f"\n{'='*60}")
        print(f"Total tools: {len(self.tools)}")
        print(f"{'='*60}\n")
    
    def get_execution_stats(self, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get tool execution statistics.
        
        Args:
            conversation_id: Optional filter by conversation
            
        Returns:
            Execution statistics
        """
        if conversation_id:
            logs = [log for log in self.execution_log if log['conversation_id'] == conversation_id]
        else:
            logs = self.execution_log
        
        if not logs:
            return {'total_executions': 0}
        
        # Calculate stats
        total_executions = len(logs)
        successful_executions = len([log for log in logs if log.get('success', False)])
        cached_executions = len([log for log in logs if log.get('cached', False)])
        
        avg_execution_time = sum(log.get('execution_time_ms', 0) for log in logs) / total_executions
        
        tool_usage = {}
        for log in logs:
            tool_name = log['tool_name']
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        
        return {
            'total_executions': total_executions,
            'success_rate': successful_executions / total_executions,
            'cache_hit_rate': cached_executions / total_executions,
            'avg_execution_time_ms': avg_execution_time,
            'tool_usage': tool_usage,
            'most_used_tool': max(tool_usage.items(), key=lambda x: x[1])[0] if tool_usage else None
        }

def create_research_orchestrator(cache_client = None) -> ToolOrchestrator:
    """
    Create a tool orchestrator with research-specific tools.
    
    Args:
        cache_client: Redis client for caching
        
    Returns:
        Configured ToolOrchestrator
    """
    orchestrator = ToolOrchestrator(cache_client)
    
    # Register research tools
    
    cordis_tool = Tool(
        name='search_cordis_projects',
        description='Search for EU research projects using LOCAL database (PostgreSQL + Neo4j). No external API calls - fast and reliable!',
        parameters_schema={
            'query': {
                'type': 'string', 
                'required': True,
                'description': 'Natural language search query. Can include country names, programmes, funding schemes.',
                'examples': ['AI healthcare projects from Germany', 'renewable energy H2020', 'ERC grants in quantum computing']
            },
            'max_results': {
                'type': 'integer', 
                'default': 10,
                'min': 1,
                'max': 50,
                'description': 'Maximum number of projects to return (1-50)'
            },
            'programme': {
                'type': 'string',
                'default': None,
                'description': 'Filter by programme: H2020, HORIZON, FP7'
            },
            'countries': {
                'type': 'array',
                'default': None,
                'description': 'Filter by country codes, e.g., ["DE", "FR", "IT"]'
            },
            'status': {
                'type': 'string',
                'default': None,
                'description': 'Filter by status: SIGNED (active), CLOSED (completed)'
            },
            'include_graph': {
                'type': 'boolean',
                'default': True,
                'description': 'Include relationship-based graph search'
            }
        },
        execute_func=ResearchTools.search_cordis_projects,
        cache_ttl=3600,  # 1 hour
        parallel_safe=True,
        category='research_projects',
        tags=['cordis', 'research_projects', 'local_search', 'multi_source'],
        usage_examples=[
            'Find AI healthcare projects from German universities',
            'Search for H2020 renewable energy projects',
            'Find completed ERC grants in quantum computing',
            'Projects coordinated by Fraunhofer',
            'Active projects in climate adaptation'
        ]
    )
    
    # portfolio_tool = Tool(
    #     name='analyze_project_portfolio',
    #     description='Analyze a portfolio of research projects',
    #     parameters_schema={
    #         'project_ids': {'type': 'array', 'required': True},
    #         'analysis_type': {'type': 'string', 'default': 'overview'}
    #     },
    #     execute_func=ResearchTools.analyze_project_portfolio,
    #     cache_ttl=7200,  # 2 hours
    #     parallel_safe=False  # Requires sequential processing
    # )
    
    # Conversational Database Search Tool
    database_tool = Tool(
        name='search_local_database',
        description='Search local Horizon Europe document database for conversational queries and informational requests',
        parameters_schema={
            'query': {
                'type': 'string',
                'required': True,
                'description': 'Search query for finding relevant information in local documents',
                'examples': ['How to apply for Horizon Europe funding?', 'What are the eligibility requirements?', 'Explain the evaluation process']
            },
            'max_context_chunks': {
                'type': 'integer',
                'default': 5,
                'min': 1,
                'max': 10,
                'description': 'Maximum number of document chunks to use for context (1-10)'
            },
            'search_type': {
                'type': 'string',
                'default': 'hybrid',
                'description': 'Search type: semantic, keyword, or hybrid',
                'allowed_values': ['semantic', 'keyword', 'hybrid']
            },
            'similarity_threshold': {
                'type': 'float',
                'default': 0.7,
                'min': 0.1,
                'max': 1.0,
                'description': 'Similarity threshold for search results (0.1-1.0)'
            }
        },
        execute_func=ResearchTools.search_local_database,
        cache_ttl=1800,  # 30 minutes - shorter cache for conversational queries
        parallel_safe=True,
        category='conversational_search',
        tags=['local_database', 'conversational', 'documents', 'rag', 'horizon_europe'],
        usage_examples=[
            'How do I apply for Horizon Europe funding?',
            'What are the eligibility requirements for grants?',
            'Explain the proposal evaluation process',
            'What documents do I need to submit?',
            'How does the funding system work?'
        ]
    )

    # EU Portal Search Tool - NOW USES LOCAL DATA ONLY (no external API)
    async def eu_portal_search_exec(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for funding calls using LOCAL Work Programme documents.
        
        This tool searches your locally ingested Work Programme PDFs for funding
        opportunities. It does NOT call any external API - all data comes from
        your local vector database.
        
        By default, only shows calls from current year (2025) and future years.
        Set include_closed=True to see older calls.
        """
        from ..local_call_search_service import LocalCallSearchService
        from datetime import date
        
        try:
            query = params.get('query', '')
            max_results = params.get('max_results', 10)
            cluster = params.get('cluster')  # Optional: CL1-CL6
            action_type = params.get('action_type')  # Optional: RIA, IA, CSA, etc.
            include_closed = params.get('include_closed', False)  # Default: only open/upcoming
            year_filter = params.get('year', None)  # Optional: specific year
            
            if not query or query.strip() == '':
                return {
                    'success': False,
                    'error': 'Query parameter cannot be empty',
                    'tool_name': 'eu_portal_search',
                    'calls_found': 0
                }
            
            current_date = date.today()
            logging.getLogger(__name__).info(
                f"🔍 LOCAL Call Search: '{query}' (max: {max_results}, "
                f"include_closed: {include_closed}, year: {year_filter}, today: {current_date})"
            )
            
            # Use LOCAL search service (no external API!)
            search_service = LocalCallSearchService()
            results = search_service.search_calls(
                query=query,
                num_results=max_results,
                cluster=cluster,
                action_type=action_type,
                include_closed=include_closed,
                year_filter=year_filter
            )
            
            if not results.get('success'):
                return {
                    'success': False,
                    'error': results.get('error', 'Local search failed'),
                    'tool_name': 'eu_portal_search',
                    'query': query,
                    'calls_found': 0
                }
            
            # Format calls to match conversation_manager expectations
            calls_data = results.get('calls', [])
            formatted_calls = []
            
            for call in calls_data:
                # Determine status based on year
                call_year = None
                if call.get('topic_code'):
                    import re
                    year_match = re.search(r'20(2[0-9]|3[0-9])', call.get('topic_code', ''))
                    if year_match:
                        call_year = int(year_match.group(0))
                
                if call_year:
                    if call_year > current_date.year:
                        status = f'Upcoming ({call_year})'
                    elif call_year == current_date.year:
                        status = f'Current ({call_year})'
                    else:
                        status = f'Past ({call_year})'
                else:
                    status = 'See Work Programme'
                
                # Use the constructed URL if available, otherwise provide search link
                topic_code = call.get('topic_code')
                if call.get('url'):
                    url = call.get('url')
                elif topic_code:
                    # Construct portal URL from topic code
                    url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_code}"
                else:
                    url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"
                
                # Only show deadline if it's valid (not from wrong year)
                deadline = call.get('deadline')
                if not deadline:
                    deadline = 'Check official portal for deadline'
                
                formatted_calls.append({
                    'title': call.get('title', 'Funding Opportunity'),
                    'identifier': topic_code or 'See Work Programme',
                    'status': status,
                    'deadline': deadline,
                    'url': url,
                    'description': call.get('description', ''),
                    # Extra local-specific fields
                    'work_programme': call.get('work_programme', ''),
                    'cluster': call.get('cluster', ''),
                    'action_type': call.get('action_type', ''),
                    'budget': call.get('budget', ''),
                    'source': 'local_work_programmes',
                    'year': call_year
                })
            
            return {
                'success': True,
                'tool_name': 'eu_portal_search',
                'query': query,
                'calls_found': len(formatted_calls),
                'calls': formatted_calls,
                'current_date': current_date.isoformat(),
                'search_metadata': {
                    **results.get('search_metadata', {}),
                    'source': 'local_work_programmes',
                    'api_used': False,
                    'include_closed': include_closed,
                    'current_date': current_date.isoformat(),
                    'note': f'Results from locally ingested Work Programme documents. Showing {"all" if include_closed else "current/upcoming"} calls as of {current_date}.'
                }
            }
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Local call search error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'tool_name': 'eu_portal_search',
                'query': params.get('query', ''),
                'calls_found': 0
            }
    
    portal_tool = Tool(
        name='eu_portal_search',
        description='Search LOCAL Work Programme documents for funding calls and opportunities (no external API). By default shows only current/upcoming calls.',
        parameters_schema={
            'query': {
                'type': 'string', 
                'required': True,
                'description': 'Search query for finding relevant funding calls',
                'examples': ['clean energy', 'artificial intelligence', 'hydrogen', 'EIC Accelerator']
            },
            'max_results': {
                'type': 'integer', 
                'default': 10,
                'min': 1,
                'max': 50,
                'description': 'Maximum number of calls to return'
            },
            'cluster': {
                'type': 'string',
                'default': None,
                'description': 'Filter by Horizon Europe cluster (CL1-CL6)',
                'examples': ['CL5', 'CL4', 'CL1']
            },
            'action_type': {
                'type': 'string',
                'default': None,
                'description': 'Filter by action type (RIA, IA, CSA, ERC, EIC, MSCA)',
                'examples': ['RIA', 'EIC', 'ERC-STG']
            },
            'include_closed': {
                'type': 'boolean',
                'default': False,
                'description': 'Include calls from past years (default: only current/upcoming)'
            },
            'year': {
                'type': 'string',
                'default': None,
                'description': 'Filter to specific year (e.g., "2025", "2026")',
                'examples': ['2025', '2026']
            }
        },
        execute_func=eu_portal_search_exec,
        cache_ttl=3600,  # 1 hour
        parallel_safe=True,
        category='research_funding',
        tags=['eu_funding', 'horizon_europe', 'calls', 'opportunities', 'local_search'],
        usage_examples=[
            'Find current calls for renewable energy research',
            'Search for AI funding opportunities in Cluster 4',
            'Look for EIC Accelerator opportunities in 2026',
            'Find ERC Starting Grant information',
            'Show me past calls for clean energy (include_closed=True)'
        ]
    )

    orchestrator.register_tool(cordis_tool)
    orchestrator.register_tool(database_tool)
    orchestrator.register_tool(portal_tool)  # ✅ NOW REGISTERED!
    # orchestrator.register_tool(portfolio_tool)

    return orchestrator
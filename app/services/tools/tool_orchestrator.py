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
        Search CORDIS for research projects using AI-powered RAG.
        
        This tool searches the CORDIS database for existing research projects,
        providing AI-generated summaries and insights about relevant projects.
        """
        from ..rag_service import CordisRAG
        
        # Define parameter schema for validation
        schema = {
            'query': {
                'type': 'string', 
                'required': True,
                'description': 'Search query for finding relevant research projects'
            },
            'max_results': {
                'type': 'integer', 
                'default': 5,
                'min': 1,
                'max': 20,
                'description': 'Maximum number of projects to process (1-20)'
            },
            'include_summary': {
                'type': 'boolean',
                'default': True,
                'description': 'Include AI-generated summary of findings'
            }
        }

        try:
            # Validate parameters
            validated_params = ToolValidator.validate_parameters(params, schema)
            
            # Extract validated parameters
            query = validated_params['query']
            max_results = validated_params['max_results']
            include_summary = validated_params['include_summary']
            
            # Validate query is not empty
            if not query or query.strip() == '':
                return {
                    'success': False,
                    'error': 'Query parameter cannot be empty',
                    'error_type': 'validation_error',
                    'query': query,
                    'projects_found': 0
                }

            logger.info(f"🔍 Searching CORDIS projects: '{query}' (max_results: {max_results})")
            
            # Execute search
            rag_service = CordisRAG()
            results = rag_service.get_ai_response_with_routing(
                question=query,
                max_projects_to_process=max_results
            )

            # Standardized successful response
            response = {
                'success': True,
                'tool_name': 'search_cordis_projects',
                'query': query,
                'parameters_used': validated_params,
                'results': {
                    'answer': results.get('answer', '') if include_summary else '',
                    'projects_found': results.get('projects_found', 0),
                    'data_source': results.get('data_source', 'cordis'),
                    'processing_time_ms': results.get('processing_time', 0)
                },
                'metadata': {
                    'search_type': 'rag_search',
                    'ai_generated': True,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            logger.info(f"✅ CORDIS search completed: {response['results']['projects_found']} projects found")
            return response

        except ValueError as e:
            # Parameter validation error
            logger.error(f"CORDIS search validation error: {e}")
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
            logger.error(f"CORDIS search execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'execution_error',
                'tool_name': 'search_cordis_projects',
                'query': params.get('query', ''),
                'projects_found': 0
            }

    # @staticmethod
    # async def analyze_project_portfolio(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    #     """Analyze a portfolio of projects."""
    #     project_ids = params.get('project_ids', [])
    #     analysis_type = params.get('analysis_type', 'overview')

    #     # Mock implementation - would integrate with your project analysis
    #     return {
    #         'project_ids': project_ids,
    #         'analysis_type': analysis_type,
    #         'portfolio_size': len(project_ids),
    #         'total_budget': f'{len(project_ids) * 1.5}M EUR',
    #         'key_themes': ['Innovation', 'Sustainability', 'Digital Transformation'],
    #         'recommendations': [
    #             'Focus on cross-project synergies',
    #             'Leverage existing partnerships',
    #             'Consider follow-up funding opportunities'
    #         ]
    #     }

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
                          conversation_id: int) -> Dict[str, Any]:
        """
        Execute a list of tool calls.
        
        Args:
            tool_calls: List of ToolCall objects
            conversation_id: Conversation ID for logging
            
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
            
            # Execute tool
            result = await self._execute_tool(tool_call, conversation_id, results)
            results[tool_call.tool_name] = result
        
        return results
    
    async def _execute_tool(self,
                           tool_call: ToolCall,
                           conversation_id: int,
                           previous_results: Dict[str, Any]) -> ToolResult:
        """
        Execute a single tool.
        
        Args:
            tool_call: ToolCall to execute
            conversation_id: Conversation ID
            previous_results: Results from previous tool executions
            
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

            # Execute tool with validated parameters
            result = await tool.execute_func(validated_params, previous_results)

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
            Search EU Funding Portal for calls using enhanced semantic search.
            
            This tool searches the EU Funding & Tenders Portal for funding calls,
            supporting open, closed, and forthcoming calls with advanced filtering.
            """
            from ..enhanced_call_search import EnhancedCallSearchService

            # Define parameter schema for validation
            schema = {
                'query': {
                    'type': 'string', 
                    'required': True,
                    'description': 'Search query for finding relevant funding calls'
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
                max_results = validated_params['max_results']
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

                # Execute search
                search_service = EnhancedCallSearchService()
                results = search_service.search_calls_enhanced(
                    query=query,
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
                        'search_type': 'enhanced_semantic',
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
        
        # Register all tools
        self.register_tool(portal_tool)
        # self.register_tool(analysis_tool)
    
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
        description='Search CORDIS database for research projects using AI-powered analysis',
        parameters_schema={
            'query': {
                'type': 'string', 
                'required': True,
                'description': 'Search query for finding relevant research projects',
                'examples': ['renewable energy projects', 'AI in healthcare', 'sustainable transport']
            },
            'max_results': {
                'type': 'integer', 
                'default': 5,
                'min': 1,
                'max': 20,
                'description': 'Maximum number of projects to process (1-20)'
            },
            'include_summary': {
                'type': 'boolean',
                'default': True,
                'description': 'Include AI-generated summary of findings'
            }
        },
        execute_func=ResearchTools.search_cordis_projects,
        cache_ttl=3600,  # 1 hour
        parallel_safe=True,
        category='research_projects',
        tags=['cordis', 'research_projects', 'ai_analysis', 'rag'],
        usage_examples=[
            'Find projects related to quantum computing research',
            'Search for completed projects in biotechnology',
            'Analyze projects focused on climate adaptation'
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
    
    orchestrator.register_tool(cordis_tool)
    # orchestrator.register_tool(portfolio_tool)
    
    return orchestrator
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
import redis
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

class ToolOrchestrator:
    """
    Manages tool selection and execution with caching and error handling.
    """
    
    def __init__(self, cache_client: redis.Redis = None):
        """
        Initialize tool orchestrator.
        
        Args:
            cache_client: Redis client for result caching
        """
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
            # Check if tool exists
            if tool_call.tool_name not in self.tools:
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    error_message=f"Tool {tool_call.tool_name} not found"
                )
            
            tool = self.tools[tool_call.tool_name]
            
            # Check cache first
            if self.cache:
                cached_result = await self._get_cached_result(tool_call, conversation_id)
                if cached_result:
                    return cached_result
            
            # Execute tool
            result = await tool.execute_func(tool_call.parameters, previous_results)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
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
            
            # Log execution
            await self._log_execution(conversation_id, tool_call, tool_result)
            
            return tool_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            error_result = ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                result=None,
                execution_time_ms=int(execution_time),
                error_message=str(e)
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
            
            cache_data = {
                'tool_name': result.tool_name,
                'success': result.success,
                'result': result.result,
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
        
        # CORDIS Search Tool
        async def cordis_search(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """Search CORDIS database for projects."""
            query = params.get('query', '')
            max_results = params.get('max_results', 5)
            
            # Mock implementation - in production, this would call your existing CORDIS service
            return {
                'query': query,
                'results_found': max_results,
                'projects': [
                    {
                        'title': f'Mock Project {i}',
                        'acronym': f'MOCK{i}',
                        'budget': f'{i * 100}K EUR'
                    }
                    for i in range(1, max_results + 1)
                ]
            }
        
        cordis_tool = Tool(
            name='cordis_search',
            description='Search CORDIS database for research projects',
            parameters_schema={
                'query': {'type': 'string', 'required': True},
                'max_results': {'type': 'integer', 'default': 5}
            },
            execute_func=cordis_search,
            cache_ttl=1800,  # 30 minutes
            parallel_safe=True
        )
        
        # EU Portal Search Tool
        async def eu_portal_search(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """Search EU Funding Portal for calls."""
            query = params.get('query', '')
            status = params.get('status', 'open')
            
            # Mock implementation
            return {
                'query': query,
                'status_filter': status,
                'calls_found': 3,
                'calls': [
                    {
                        'identifier': f'HORIZON-2024-MOCK-{i}',
                        'title': f'Mock Call {i}',
                        'deadline': '2024-12-31',
                        'budget': f'{i * 500}K EUR'
                    }
                    for i in range(1, 4)
                ]
            }
        
        portal_tool = Tool(
            name='eu_portal_search',
            description='Search EU Funding Portal for open calls',
            parameters_schema={
                'query': {'type': 'string', 'required': True},
                'status': {'type': 'string', 'default': 'open'}
            },
            execute_func=eu_portal_search,
            cache_ttl=3600,  # 1 hour
            parallel_safe=True
        )
        
        # Document Analysis Tool
        async def analyze_document(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze a document for key information."""
            document_id = params.get('document_id', '')
            analysis_type = params.get('analysis_type', 'summary')
            
            # Mock implementation
            return {
                'document_id': document_id,
                'analysis_type': analysis_type,
                'summary': f'Analysis of document {document_id}',
                'key_points': [
                    'Key finding 1',
                    'Key finding 2',
                    'Key finding 3'
                ],
                'confidence': 0.85
            }
        
        analysis_tool = Tool(
            name='analyze_document',
            description='Analyze documents for key information',
            parameters_schema={
                'document_id': {'type': 'string', 'required': True},
                'analysis_type': {'type': 'string', 'default': 'summary'}
            },
            execute_func=analyze_document,
            cache_ttl=7200,  # 2 hours
            parallel_safe=True
        )
        
        # Register all tools
        self.register_tool(cordis_tool)
        self.register_tool(portal_tool)
        self.register_tool(analysis_tool)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools with their descriptions.
        
        Returns:
            List of tool information dictionaries
        """
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.parameters_schema,
                'cache_ttl': tool.cache_ttl,
                'parallel_safe': tool.parallel_safe
            }
            for tool in self.tools.values()
        ]
    
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

# Example tool implementations for your research domain
class ResearchTools:
    """Collection of research-specific tools."""
    
    @staticmethod
    async def search_horizon_calls(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search for Horizon Europe calls."""
        # This would integrate with your existing enhanced_call_search service
        from ..enhanced_call_search import EnhancedCallSearchService
        
        try:
            search_service = EnhancedCallSearchService()
            query = params.get('query', '')
            max_results = params.get('max_results', 10)
            
            results = search_service.search_calls_enhanced(
                search_query_text=query,
                max_results=max_results
            )
            
            return {
                'query': query,
                'results_found': len(results.get('results', [])),
                'calls': results.get('results', []),
                'search_metadata': results.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Horizon calls search error: {e}")
            return {
                'error': str(e),
                'query': params.get('query', ''),
                'results_found': 0
            }
    
    @staticmethod
    async def search_cordis_projects(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search CORDIS for research projects."""
        # This would integrate with your existing RAG service
        from ..rag_service import CordisRAG
        
        try:
            rag_service = CordisRAG()
            query = params.get('query', '')
            max_results = params.get('max_results', 5)
            
            results = rag_service.get_ai_response_with_routing(
                question=query,
                max_projects_to_process=max_results
            )
            
            return {
                'query': query,
                'answer': results.get('answer', ''),
                'projects_found': results.get('projects_found', 0),
                'data_source': results.get('data_source', ''),
                'processing_time': results.get('processing_time', 0)
            }
            
        except Exception as e:
            logger.error(f"CORDIS search error: {e}")
            return {
                'error': str(e),
                'query': params.get('query', ''),
                'projects_found': 0
            }
    
    @staticmethod
    async def analyze_project_portfolio(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a portfolio of projects."""
        project_ids = params.get('project_ids', [])
        analysis_type = params.get('analysis_type', 'overview')
        
        # Mock implementation - would integrate with your project analysis
        return {
            'project_ids': project_ids,
            'analysis_type': analysis_type,
            'portfolio_size': len(project_ids),
            'total_budget': f'{len(project_ids) * 1.5}M EUR',
            'key_themes': ['Innovation', 'Sustainability', 'Digital Transformation'],
            'recommendations': [
                'Focus on cross-project synergies',
                'Leverage existing partnerships',
                'Consider follow-up funding opportunities'
            ]
        }

def create_research_orchestrator(cache_client: redis.Redis = None) -> ToolOrchestrator:
    """
    Create a tool orchestrator with research-specific tools.
    
    Args:
        cache_client: Redis client for caching
        
    Returns:
        Configured ToolOrchestrator
    """
    orchestrator = ToolOrchestrator(cache_client)
    
    # Register research tools
    horizon_tool = Tool(
        name='search_horizon_calls',
        description='Search Horizon Europe funding calls',
        parameters_schema={
            'query': {'type': 'string', 'required': True},
            'max_results': {'type': 'integer', 'default': 10}
        },
        execute_func=ResearchTools.search_horizon_calls,
        cache_ttl=1800,  # 30 minutes
        parallel_safe=True
    )
    
    cordis_tool = Tool(
        name='search_cordis_projects',
        description='Search CORDIS research projects',
        parameters_schema={
            'query': {'type': 'string', 'required': True},
            'max_results': {'type': 'integer', 'default': 5}
        },
        execute_func=ResearchTools.search_cordis_projects,
        cache_ttl=3600,  # 1 hour
        parallel_safe=True
    )
    
    portfolio_tool = Tool(
        name='analyze_project_portfolio',
        description='Analyze a portfolio of research projects',
        parameters_schema={
            'project_ids': {'type': 'array', 'required': True},
            'analysis_type': {'type': 'string', 'default': 'overview'}
        },
        execute_func=ResearchTools.analyze_project_portfolio,
        cache_ttl=7200,  # 2 hours
        parallel_safe=False  # Requires sequential processing
    )
    
    orchestrator.register_tool(horizon_tool)
    orchestrator.register_tool(cordis_tool)
    orchestrator.register_tool(portfolio_tool)
    
    return orchestrator
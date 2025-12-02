"""
Agentic Loop Module

Provides self-correcting, iterative query processing that can:
- Evaluate result quality
- Reflect on failures
- Replan with improved strategies
- Learn from what worked/failed within a session
- Use multiple tools with reasoning (ReAct pattern)
- Compare and contrast results from different sources

Usage:
    from app.services.agents import AgenticManager
    
    # Simple queries (self-correcting)
    manager = AgenticManager()
    response = await manager.process_query("What are the consortium requirements?")
    
    # Complex queries (multi-tool reasoning)
    from app.services.agents import ToolAwareAgent
    
    agent = ToolAwareAgent()
    response = await agent.process_query("Compare EIC Accelerator vs ERC success rates")
"""

from .agent_context import AgentContext, AgentState
from .result_evaluator import ResultEvaluator, EvaluationResult
from .reflector import Reflector, ReflectionResult
from .replanner import Replanner
from .agentic_manager import AgenticManager
from .tool_aware_agent import ToolAwareAgent, Tool, ToolCall, ToolCategory

__all__ = [
    'AgentContext',
    'AgentState',
    'ResultEvaluator',
    'EvaluationResult',
    'Reflector',
    'ReflectionResult',
    'Replanner',
    'AgenticManager',
    'ToolAwareAgent',
    'Tool',
    'ToolCall',
    'ToolCategory',
]

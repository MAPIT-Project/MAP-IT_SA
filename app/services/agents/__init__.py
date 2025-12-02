"""
Agentic Loop Module

Provides self-correcting, iterative query processing that can:
- Evaluate result quality
- Reflect on failures
- Replan with improved strategies
- Learn from what worked/failed within a session

Usage:
    from app.services.agents import AgenticManager
    
    manager = AgenticManager()
    response = await manager.process_query("What are the consortium requirements?")
"""

from .agent_context import AgentContext, AgentState
from .result_evaluator import ResultEvaluator, EvaluationResult
from .reflector import Reflector, ReflectionResult
from .replanner import Replanner
from .agentic_manager import AgenticManager

__all__ = [
    'AgentContext',
    'AgentState',
    'ResultEvaluator',
    'EvaluationResult',
    'Reflector',
    'ReflectionResult',
    'Replanner',
    'AgenticManager',
]

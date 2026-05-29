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

    # Proposal-aware queries (proposal context injection)
    from app.services.agents import ProposalAwareAgent

    agent = ProposalAwareAgent()
    response = await agent.process_query(
        "Write the objectives section",
        proposal_context=session.get_context_for_agent()
    )
"""

from .agent_context import AgentContext, AgentState
from .proposal_aware_agent import ProposalAwareAgent
from .tool_aware_agent import ToolAwareAgent
from .tool_registry import AgentPlan, ReasoningStep, Tool, ToolCall, ToolCategory, ToolRegistryMixin

__all__ = [
    "AgentContext",
    "AgentState",
    "ToolAwareAgent",
    "Tool",
    "ToolCall",
    "ToolCategory",
    "ToolRegistryMixin",
    "AgentPlan",
    "ReasoningStep",
    "ProposalAwareAgent",
]

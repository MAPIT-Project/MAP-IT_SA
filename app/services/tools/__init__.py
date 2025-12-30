"""
Tool orchestration system for V3 agentic architecture.

V3 uses ToolAwareAgent with dedicated tools for hybrid Graph+SQL operations.
"""

from .budget_benchmark import BudgetBenchmarkTool, get_budget_benchmark_execute
from .consortium_patterns import ConsortiumPatternsTool, get_consortium_patterns_execute
from .partner_discovery import PartnerDiscoveryTool, find_experienced_partners_execute
from .similar_projects import SimilarProjectsTool, get_similar_funded_projects_execute
from .call_history import CallHistoryTool, analyze_call_history_execute
from .budget_calculator import BudgetCalculatorTool, calculate_budget_execute
from .timeline_generator import TimelineGeneratorTool, generate_timeline_execute
from .multi_programme_search import (
    MultiProgrammeSearchTool,
    search_all_programmes_execute,
    get_programme_recommendations_execute,
    get_programme_info_execute,
)

__all__ = [
    'BudgetBenchmarkTool',
    'get_budget_benchmark_execute',
    'ConsortiumPatternsTool',
    'get_consortium_patterns_execute',
    'PartnerDiscoveryTool',
    'find_experienced_partners_execute',
    'SimilarProjectsTool',
    'get_similar_funded_projects_execute',
    'CallHistoryTool',
    'analyze_call_history_execute',
    'BudgetCalculatorTool',
    'calculate_budget_execute',
    'TimelineGeneratorTool',
    'generate_timeline_execute',
    # Multi-programme tools
    'MultiProgrammeSearchTool',
    'search_all_programmes_execute',
    'get_programme_recommendations_execute',
    'get_programme_info_execute',
]

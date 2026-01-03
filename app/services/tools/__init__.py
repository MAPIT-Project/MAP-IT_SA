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
from .proposal_quality_scorer import (
    ProposalQualityScorerTool,
    score_proposal_section_execute,
    score_full_proposal_execute,
    quick_quality_check_execute,
)
from .budget_validator import (
    BudgetValidatorTool,
    validate_budget_execute,
)
# Erasmus+ specific tools
from .erasmus_eligibility import (
    ErasmusEligibilityTool,
    check_erasmus_eligibility_execute,
)
from .erasmus_budget_calculator import (
    ErasmusBudgetCalculator,
    calculate_erasmus_budget_execute,
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
    # Proposal quality tools
    'ProposalQualityScorerTool',
    'score_proposal_section_execute',
    'score_full_proposal_execute',
    'quick_quality_check_execute',
    # Budget validation tools
    'BudgetValidatorTool',
    'validate_budget_execute',
    # Erasmus+ specific tools
    'ErasmusEligibilityTool',
    'check_erasmus_eligibility_execute',
    'ErasmusBudgetCalculator',
    'calculate_erasmus_budget_execute',
]

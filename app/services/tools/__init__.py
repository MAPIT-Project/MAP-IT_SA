"""
Tool orchestration system for V3 agentic architecture.

V3 uses ToolAwareAgent with dedicated tools for hybrid Graph+SQL operations.
"""

from .budget_benchmark import BudgetBenchmarkTool, get_budget_benchmark_execute
from .budget_calculator import BudgetCalculatorTool, calculate_budget_execute
from .budget_validator import (
    BudgetValidatorTool,
    validate_budget_execute,
)
from .call_history import CallHistoryTool, analyze_call_history_execute
from .consortium_patterns import ConsortiumPatternsTool, get_consortium_patterns_execute
from .creative_europe_budget_calculator import (
    CreativeEuropeBudgetCalculator,
    calculate_creative_europe_budget_execute,
)

# Creative Europe specific tools
from .creative_europe_eligibility import (
    CreativeEuropeEligibilityTool,
    check_creative_europe_eligibility_execute,
)
from .creative_europe_template_search import (
    CreativeEuropeTemplateSearchTool,
    search_creative_europe_templates_execute,
)

# Digital Europe specific tools
from .digital_europe_eligibility import (
    DigitalEuropeEligibilityTool,
    check_digital_europe_eligibility_execute,
)
from .digital_europe_template_search import (
    DigitalEuropeTemplateSearchTool,
    search_digital_europe_templates_execute,
)
from .erasmus_budget_calculator import (
    ErasmusBudgetCalculator,
    calculate_erasmus_budget_execute,
)

# Erasmus+ specific tools
from .erasmus_eligibility import (
    ErasmusEligibilityTool,
    check_erasmus_eligibility_execute,
)
from .erasmus_template_search import (
    ErasmusTemplateSearchTool,
    search_erasmus_templates_execute,
)

# EU4Health specific tools
from .eu4health_eligibility import (
    EU4HealthEligibilityTool,
    check_eu4health_eligibility_execute,
)
from .eu4health_template_search import (
    EU4HealthTemplateSearchTool,
    search_eu4health_templates_execute,
)

# LIFE Programme specific tools
from .life_eligibility import (
    LIFEEligibilityTool,
    check_life_eligibility_execute,
)
from .life_template_search import (
    LIFETemplateSearchTool,
    search_life_templates_execute,
)
from .multi_programme_search import (
    MultiProgrammeSearchTool,
    get_programme_info_execute,
    get_programme_recommendations_execute,
    search_all_programmes_execute,
)
from .partner_discovery import PartnerDiscoveryTool, find_experienced_partners_execute
from .proposal_quality_scorer import (
    ProposalQualityScorerTool,
    quick_quality_check_execute,
    score_full_proposal_execute,
    score_proposal_section_execute,
)
from .similar_projects import SimilarProjectsTool, get_similar_funded_projects_execute
from .timeline_generator import TimelineGeneratorTool, generate_timeline_execute

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
    'ErasmusTemplateSearchTool',
    'search_erasmus_templates_execute',
    # Creative Europe specific tools
    'CreativeEuropeEligibilityTool',
    'check_creative_europe_eligibility_execute',
    'CreativeEuropeBudgetCalculator',
    'calculate_creative_europe_budget_execute',
    'CreativeEuropeTemplateSearchTool',
    'search_creative_europe_templates_execute',
    # EU4Health specific tools
    'EU4HealthEligibilityTool',
    'check_eu4health_eligibility_execute',
    'EU4HealthTemplateSearchTool',
    'search_eu4health_templates_execute',
    # Digital Europe specific tools
    'DigitalEuropeEligibilityTool',
    'check_digital_europe_eligibility_execute',
    'DigitalEuropeTemplateSearchTool',
    'search_digital_europe_templates_execute',
    # LIFE Programme specific tools
    'LIFEEligibilityTool',
    'check_life_eligibility_execute',
    'LIFETemplateSearchTool',
    'search_life_templates_execute',
]

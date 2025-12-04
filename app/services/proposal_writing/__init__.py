"""
Proposal Writing Assistant Services

This package provides AI-powered assistance for writing Horizon Europe proposals.
"""

from .template_service import ProposalTemplateService
from .draft_generator import ProposalDraftGenerator
from .criteria_matcher import EvaluationCriteriaMatcher
from .budget_assistant import BudgetAssistant
from .compliance_checker import ComplianceChecker
from .quality_improver import QualityImprover
from .official_document_processor import (
    OfficialDocumentProcessor,
    OfficialWordExporter,
    OfficialBudgetExporter
)
from .submission_exporter import SubmissionExporter
from .call_understanding_service import (
    CallUnderstandingService,
    CallUnderstanding,
    HorizonCluster,
)
from .proposal_ai_service import ProposalAIService
from .schemas import (
    CRITERIA_ANALYSIS_SCHEMA,
    QUALITY_ANALYSIS_SCHEMA,
    CALL_UNDERSTANDING_SCHEMA,
    EVALUATOR_SIMULATION_SCHEMA,
    REWRITE_SCHEMA,
    INLINE_SUGGESTIONS_SCHEMA,
)
from .ai_providers import (
    BaseAIProvider,
    ProviderConfig,
    ProviderResponse,
    ProviderStatus,
    GeminiProvider,
    OpenAIProvider,
    MultiProviderAIService,
)
from .exceptions import (
    ProposalWritingError,
    AIGenerationError,
    CallAnalysisError,
    DatabaseError,
    ValidationError,
    RateLimitError,
    ProposalTimeoutError,
    ProviderUnavailableError,
    TemplateError,
)
from .retry import (
    async_retry,
    sync_retry,
    CircuitBreaker,
    RetryConfig,
    AGGRESSIVE_RETRY,
    STANDARD_RETRY,
    GENTLE_RETRY,
)
from .proposal_learning_service import (
    ProposalLearningService,
    SimilarProject,
    SuccessPattern,
)
from .example_extractor import (
    ExampleExtractor,
    ExampleEnricher,
    ExampleType,
    ExtractedExample,
)
from .semantic_benchmarking import (
    SemanticBenchmarkingService,
    BenchmarkResult,
    BenchmarkExample,
    BenchmarkDimension,
    DimensionScore,
    BenchmarkVisualizer,
    RealTimeBenchmarker,
)
from .evaluator_simulator import (
    EvaluatorSimulator,
    EvaluationResult,
    CriterionScore,
    ScoreLevel,
)
from .score_visualizer import (
    generate_score_bar,
    generate_score_summary,
    generate_criterion_table,
    generate_section_report,
    generate_comparison_chart_data,
    generate_funding_probability_gauge,
    format_improvement_priority_list,
)
from .score_storage_service import (
    ScoreStorageService,
    StoredScore,
    ScoreHistoryEntry,
    ProposalScoreSummary,
    TriggerType,
)
from .gap_analysis_service import (
    GapAnalysisService,
    GapProgressTracker,
    GapAnalysisResult,
    Gap,
    GapSeverity,
    GapCategory,
    EffortLevel,
)
from .smart_rewriter import (
    SmartRewriter,
    RewriteResult,
    RewriteStyle,
)
from .inline_suggestions_service import (
    InlineSuggestionsService,
    RealTimeAnalyzer,
    InlineSuggestion,
    AnalysisResult,
    TextSpan,
    SuggestionCategory,
    SuggestionPriority,
)
from .realtime_quality_service import (
    RealTimeQualityService,
    StreamingQualityIndicator,
    StreamingFeedback,
    FeedbackType,
    QualityTier,
)
from .progress_tracking_service import (
    ProgressTrackingService,
    Achievement,
    UserAchievement,
    ProgressSnapshot,
    Streak,
    AchievementCategory,
    AchievementRarity,
)
from .dashboard_service import (
    DashboardService,
    DashboardData,
    SectionSummary,
    NextAction,
    ReadinessCheck,
    SectionStatus,
    ActionPriority,
)

__all__ = [
    'ProposalTemplateService',
    'ProposalDraftGenerator',
    'EvaluationCriteriaMatcher',
    'BudgetAssistant',
    'ComplianceChecker',
    'QualityImprover',
    'OfficialDocumentProcessor',
    'OfficialWordExporter',
    'OfficialBudgetExporter',
    'SubmissionExporter',
    # Call Understanding (Task 01)
    'CallUnderstandingService',
    'CallUnderstanding',
    'HorizonCluster',
    # Proposal AI Service (Task 02)
    'ProposalAIService',
    # AI Schemas (Task 02)
    'CRITERIA_ANALYSIS_SCHEMA',
    'QUALITY_ANALYSIS_SCHEMA',
    'CALL_UNDERSTANDING_SCHEMA',
    'EVALUATOR_SIMULATION_SCHEMA',
    'REWRITE_SCHEMA',
    'INLINE_SUGGESTIONS_SCHEMA',
    # Multi-Provider AI (Task 03)
    'BaseAIProvider',
    'ProviderConfig',
    'ProviderResponse',
    'ProviderStatus',
    'GeminiProvider',
    'OpenAIProvider',
    'MultiProviderAIService',
    # Error Handling (Task 04)
    'ProposalWritingError',
    'AIGenerationError',
    'CallAnalysisError',
    'DatabaseError',
    'ValidationError',
    'RateLimitError',
    'ProposalTimeoutError',
    'ProviderUnavailableError',
    'TemplateError',
    # Retry Utilities (Task 04)
    'async_retry',
    'sync_retry',
    'CircuitBreaker',
    'RetryConfig',
    'AGGRESSIVE_RETRY',
    'STANDARD_RETRY',
    'GENTLE_RETRY',
    # Learning Service (Task 05)
    'ProposalLearningService',
    'SimilarProject',
    'SuccessPattern',
    # Example Extractor (Task 06)
    'ExampleExtractor',
    'ExampleEnricher',
    'ExampleType',
    'ExtractedExample',
    # Semantic Benchmarking (Task 07)
    'SemanticBenchmarkingService',
    'BenchmarkResult',
    'BenchmarkExample',
    'BenchmarkDimension',
    'DimensionScore',
    'BenchmarkVisualizer',
    'RealTimeBenchmarker',
    # Evaluator Simulator (Task 08)
    'EvaluatorSimulator',
    'EvaluationResult',
    'CriterionScore',
    'ScoreLevel',
    # Score Visualizer (Task 08)
    'generate_score_bar',
    'generate_score_summary',
    'generate_criterion_table',
    'generate_section_report',
    'generate_comparison_chart_data',
    'generate_funding_probability_gauge',
    'format_improvement_priority_list',
    # Score Storage (Task 09)
    'ScoreStorageService',
    'StoredScore',
    'ScoreHistoryEntry',
    'ProposalScoreSummary',
    'TriggerType',
    # Gap Analysis (Task 10)
    'GapAnalysisService',
    'GapProgressTracker',
    'GapAnalysisResult',
    'Gap',
    'GapSeverity',
    'GapCategory',
    'EffortLevel',
    # Smart Rewriter (Task 11)
    'SmartRewriter',
    'RewriteResult',
    'RewriteStyle',
    # Inline Suggestions (Task 13)
    'InlineSuggestionsService',
    'RealTimeAnalyzer',
    'InlineSuggestion',
    'AnalysisResult',
    'TextSpan',
    'SuggestionCategory',
    'SuggestionPriority',
    # Real-Time Quality (Task 14)
    'RealTimeQualityService',
    'StreamingQualityIndicator',
    'StreamingFeedback',
    'FeedbackType',
    'QualityTier',
    # Progress Tracking (Task 15)
    'ProgressTrackingService',
    'Achievement',
    'UserAchievement',
    'ProgressSnapshot',
    'Streak',
    'AchievementCategory',
    'AchievementRarity',
    # Dashboard Service (Task 16)
    'DashboardService',
    'DashboardData',
    'SectionSummary',
    'NextAction',
    'ReadinessCheck',
    'SectionStatus',
    'ActionPriority',
]


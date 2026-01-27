"""
Proposal Writing Assistant Services

This package provides AI-powered assistance for writing Horizon Europe proposals.
"""

from .ai_providers import (
    BaseAIProvider,
    GeminiProvider,
    MultiProviderAIService,
    OpenAIProvider,
    ProviderConfig,
    ProviderResponse,
    ProviderStatus,
)
from .budget_assistant import BudgetAssistant
from .call_understanding_service import CallUnderstanding, CallUnderstandingService, HorizonCluster
from .compliance_checker import ComplianceChecker
from .criteria_matcher import EvaluationCriteriaMatcher
from .dashboard_service import (
    ActionPriority,
    DashboardData,
    DashboardService,
    NextAction,
    ReadinessCheck,
    SectionStatus,
    SectionSummary,
)
from .draft_generator import ProposalDraftGenerator
from .evaluator_simulator import CriterionScore, EvaluationResult, EvaluatorSimulator, ScoreLevel
from .example_extractor import ExampleEnricher, ExampleExtractor, ExampleType, ExtractedExample
from .exceptions import (
    AIGenerationError,
    CallAnalysisError,
    DatabaseError,
    ProposalTimeoutError,
    ProposalWritingError,
    ProviderUnavailableError,
    RateLimitError,
    TemplateError,
    ValidationError,
)
from .gap_analysis_service import (
    EffortLevel,
    Gap,
    GapAnalysisResult,
    GapAnalysisService,
    GapCategory,
    GapProgressTracker,
    GapSeverity,
)
from .inline_suggestions_service import (
    AnalysisResult,
    InlineSuggestion,
    InlineSuggestionsService,
    RealTimeAnalyzer,
    SuggestionCategory,
    SuggestionPriority,
    TextSpan,
)
from .official_document_processor import (
    OfficialBudgetExporter,
    OfficialDocumentProcessor,
    OfficialWordExporter,
)
from .progress_tracking_service import (
    Achievement,
    AchievementCategory,
    AchievementRarity,
    ProgressSnapshot,
    ProgressTrackingService,
    Streak,
    UserAchievement,
)
from .proposal_ai_service import ProposalAIService
from .proposal_learning_service import ProposalLearningService, SimilarProject, SuccessPattern
from .quality_improver import QualityImprover
from .realtime_quality_service import (
    FeedbackType,
    QualityTier,
    RealTimeQualityService,
    StreamingFeedback,
    StreamingQualityIndicator,
)
from .retry import (
    AGGRESSIVE_RETRY,
    GENTLE_RETRY,
    STANDARD_RETRY,
    CircuitBreaker,
    RetryConfig,
    async_retry,
    sync_retry,
)
from .schemas import (
    CALL_UNDERSTANDING_SCHEMA,
    CRITERIA_ANALYSIS_SCHEMA,
    EVALUATOR_SIMULATION_SCHEMA,
    INLINE_SUGGESTIONS_SCHEMA,
    QUALITY_ANALYSIS_SCHEMA,
    REWRITE_SCHEMA,
)
from .score_storage_service import (
    ProposalScoreSummary,
    ScoreHistoryEntry,
    ScoreStorageService,
    StoredScore,
    TriggerType,
)
from .score_visualizer import (
    format_improvement_priority_list,
    generate_comparison_chart_data,
    generate_criterion_table,
    generate_funding_probability_gauge,
    generate_score_bar,
    generate_score_summary,
    generate_section_report,
)
from .semantic_benchmarking import (
    BenchmarkDimension,
    BenchmarkExample,
    BenchmarkResult,
    BenchmarkVisualizer,
    DimensionScore,
    RealTimeBenchmarker,
    SemanticBenchmarkingService,
)
from .smart_rewriter import RewriteResult, RewriteStyle, SmartRewriter
from .submission_exporter import SubmissionExporter
from .template_service import ProposalTemplateService

__all__ = [
    "ProposalTemplateService",
    "ProposalDraftGenerator",
    "EvaluationCriteriaMatcher",
    "BudgetAssistant",
    "ComplianceChecker",
    "QualityImprover",
    "OfficialDocumentProcessor",
    "OfficialWordExporter",
    "OfficialBudgetExporter",
    "SubmissionExporter",
    # Call Understanding (Task 01)
    "CallUnderstandingService",
    "CallUnderstanding",
    "HorizonCluster",
    # Proposal AI Service (Task 02)
    "ProposalAIService",
    # AI Schemas (Task 02)
    "CRITERIA_ANALYSIS_SCHEMA",
    "QUALITY_ANALYSIS_SCHEMA",
    "CALL_UNDERSTANDING_SCHEMA",
    "EVALUATOR_SIMULATION_SCHEMA",
    "REWRITE_SCHEMA",
    "INLINE_SUGGESTIONS_SCHEMA",
    # Multi-Provider AI (Task 03)
    "BaseAIProvider",
    "ProviderConfig",
    "ProviderResponse",
    "ProviderStatus",
    "GeminiProvider",
    "OpenAIProvider",
    "MultiProviderAIService",
    # Error Handling (Task 04)
    "ProposalWritingError",
    "AIGenerationError",
    "CallAnalysisError",
    "DatabaseError",
    "ValidationError",
    "RateLimitError",
    "ProposalTimeoutError",
    "ProviderUnavailableError",
    "TemplateError",
    # Retry Utilities (Task 04)
    "async_retry",
    "sync_retry",
    "CircuitBreaker",
    "RetryConfig",
    "AGGRESSIVE_RETRY",
    "STANDARD_RETRY",
    "GENTLE_RETRY",
    # Learning Service (Task 05)
    "ProposalLearningService",
    "SimilarProject",
    "SuccessPattern",
    # Example Extractor (Task 06)
    "ExampleExtractor",
    "ExampleEnricher",
    "ExampleType",
    "ExtractedExample",
    # Semantic Benchmarking (Task 07)
    "SemanticBenchmarkingService",
    "BenchmarkResult",
    "BenchmarkExample",
    "BenchmarkDimension",
    "DimensionScore",
    "BenchmarkVisualizer",
    "RealTimeBenchmarker",
    # Evaluator Simulator (Task 08)
    "EvaluatorSimulator",
    "EvaluationResult",
    "CriterionScore",
    "ScoreLevel",
    # Score Visualizer (Task 08)
    "generate_score_bar",
    "generate_score_summary",
    "generate_criterion_table",
    "generate_section_report",
    "generate_comparison_chart_data",
    "generate_funding_probability_gauge",
    "format_improvement_priority_list",
    # Score Storage (Task 09)
    "ScoreStorageService",
    "StoredScore",
    "ScoreHistoryEntry",
    "ProposalScoreSummary",
    "TriggerType",
    # Gap Analysis (Task 10)
    "GapAnalysisService",
    "GapProgressTracker",
    "GapAnalysisResult",
    "Gap",
    "GapSeverity",
    "GapCategory",
    "EffortLevel",
    # Smart Rewriter (Task 11)
    "SmartRewriter",
    "RewriteResult",
    "RewriteStyle",
    # Inline Suggestions (Task 13)
    "InlineSuggestionsService",
    "RealTimeAnalyzer",
    "InlineSuggestion",
    "AnalysisResult",
    "TextSpan",
    "SuggestionCategory",
    "SuggestionPriority",
    # Real-Time Quality (Task 14)
    "RealTimeQualityService",
    "StreamingQualityIndicator",
    "StreamingFeedback",
    "FeedbackType",
    "QualityTier",
    # Progress Tracking (Task 15)
    "ProgressTrackingService",
    "Achievement",
    "UserAchievement",
    "ProgressSnapshot",
    "Streak",
    "AchievementCategory",
    "AchievementRarity",
    # Dashboard Service (Task 16)
    "DashboardService",
    "DashboardData",
    "SectionSummary",
    "NextAction",
    "ReadinessCheck",
    "SectionStatus",
    "ActionPriority",
]

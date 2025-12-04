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
]


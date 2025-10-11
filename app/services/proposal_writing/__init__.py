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
]


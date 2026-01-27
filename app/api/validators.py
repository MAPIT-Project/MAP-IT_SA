"""
Input Validation Schemas for MAP-IT API

Provides Pydantic models for validating API inputs with clear error messages,
pattern matching, and value constraints.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# COMMON VALIDATORS
# ============================================================================

def validate_not_empty(value: str, field_name: str) -> str:
    """Validate that a string is not empty or whitespace only."""
    if not value or not value.strip():
        raise ValueError(f'{field_name} cannot be empty or whitespace only')
    return value.strip()


def validate_max_length(value: str, max_length: int, field_name: str) -> str:
    """Validate that a string doesn't exceed max length."""
    if len(value) > max_length:
        raise ValueError(f'{field_name} cannot exceed {max_length} characters')
    return value


# ============================================================================
# CONVERSATION API VALIDATORS
# ============================================================================

class MessageRequest(BaseModel):
    """Request schema for sending a message to a conversation."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's message to process"
    )
    include_context: bool = Field(
        default=True,
        description="Whether to include conversation context"
    )
    streaming: bool = Field(
        default=True,
        description="Whether to stream the response"
    )

    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        return validate_not_empty(v, 'Message')


class ConversationIdValidator(BaseModel):
    """Validator for conversation ID format."""

    conversation_id: str = Field(
        ...,
        min_length=8,
        max_length=64,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Unique conversation identifier"
    )


# ============================================================================
# SEARCH API VALIDATORS
# ============================================================================

class SearchCallsRequest(BaseModel):
    """Request schema for searching funding calls."""

    keywords: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Search keywords for finding calls"
    )
    status: Literal['open', 'upcoming', 'closed', 'all'] | None = Field(
        default='all',
        description="Filter by call status"
    )
    cluster: str | None = Field(
        default=None,
        pattern=r'^(CL[1-6]|CLUSTER-[1-6])$',
        description="Filter by Horizon Europe cluster (CL1-CL6 or CLUSTER-1 to CLUSTER-6)"
    )
    programme: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by programme name"
    )
    year: int | None = Field(
        default=None,
        ge=2021,
        le=2030,
        description="Filter by call year"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )

    @field_validator('keywords')
    @classmethod
    def keywords_not_empty(cls, v: str) -> str:
        return validate_not_empty(v, 'Keywords')


class SearchProjectsRequest(BaseModel):
    """Request schema for searching CORDIS projects."""

    keywords: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Search keywords for finding projects"
    )
    cluster: str | None = Field(
        default=None,
        pattern=r'^(CL[1-6]|CLUSTER-[1-6])$',
        description="Filter by Horizon Europe cluster"
    )
    country: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
        description="Filter by country (name or ISO code)"
    )
    action_type: Literal['RIA', 'IA', 'CSA', 'COFUND', 'ERC', 'MSCA'] | None = Field(
        default=None,
        description="Filter by action type"
    )
    year_from: int | None = Field(
        default=None,
        ge=2014,
        le=2030,
        description="Filter projects starting from this year"
    )
    year_to: int | None = Field(
        default=None,
        ge=2014,
        le=2030,
        description="Filter projects starting up to this year"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )

    @field_validator('keywords')
    @classmethod
    def keywords_not_empty(cls, v: str) -> str:
        return validate_not_empty(v, 'Keywords')

    @model_validator(mode='after')
    def validate_year_range(self):
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError('year_from must be less than or equal to year_to')
        return self


# ============================================================================
# PROPOSAL SESSION VALIDATORS
# ============================================================================

class ProposalSessionCreateRequest(BaseModel):
    """Request schema for creating a proposal session."""

    call_id: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="The funding call ID (e.g., HORIZON-CL5-2025-D3-01)"
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Proposal title"
    )
    proposal_type: Literal['RIA', 'IA', 'CSA', 'COFUND', 'ERC', 'MSCA'] = Field(
        ...,
        description="Type of proposal"
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
        description="Brief proposal description"
    )

    @field_validator('call_id')
    @classmethod
    def validate_call_id(cls, v: str) -> str:
        v = validate_not_empty(v, 'Call ID')
        # Allow various call ID formats but ensure it looks valid
        if not re.match(r'^[A-Z0-9_-]+$', v.upper()):
            raise ValueError('Call ID contains invalid characters')
        return v.upper()

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        return validate_not_empty(v, 'Title')


class SectionGenerateRequest(BaseModel):
    """Request schema for generating a proposal section."""

    section_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Section identifier (e.g., 'excellence', 'impact', 'implementation')"
    )
    user_input: str | None = Field(
        default=None,
        max_length=10000,
        description="User-provided context for section generation"
    )
    regenerate: bool = Field(
        default=False,
        description="Whether to regenerate existing content"
    )


# ============================================================================
# TOOL PARAMETER VALIDATORS
# ============================================================================

class BudgetBenchmarkRequest(BaseModel):
    """Request schema for budget benchmark tool."""

    action_type: Literal['RIA', 'IA', 'CSA', 'COFUND', 'ERC', 'MSCA'] = Field(
        ...,
        description="Type of funding action"
    )
    cluster: str | None = Field(
        default=None,
        pattern=r'^(CL[1-6]|CLUSTER-[1-6])$',
        description="Horizon Europe cluster"
    )
    topic_keywords: str | None = Field(
        default=None,
        max_length=500,
        description="Keywords for cluster inference"
    )
    include_org_type_breakdown: bool = Field(
        default=True,
        description="Include budget breakdown by organization type"
    )
    include_country_breakdown: bool = Field(
        default=False,
        description="Include budget breakdown by country"
    )


class PartnerDiscoveryRequest(BaseModel):
    """Request schema for partner discovery tool."""

    keywords: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Keywords describing expertise area"
    )
    country: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
        description="Filter by country"
    )
    org_type: Literal['HES', 'REC', 'PRC', 'PUB', 'OTH', 'SME'] | None = Field(
        default=None,
        description="Filter by organization type"
    )
    role: Literal['coordinator', 'participant', 'any'] | None = Field(
        default='any',
        description="Filter by role in projects"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum partners to return"
    )

    @field_validator('keywords')
    @classmethod
    def keywords_not_empty(cls, v: str) -> str:
        return validate_not_empty(v, 'Keywords')


class SimilarProjectsRequest(BaseModel):
    """Request schema for similar projects tool."""

    description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Project description to find similar projects for"
    )
    cluster: str | None = Field(
        default=None,
        pattern=r'^(CL[1-6]|CLUSTER-[1-6])$',
        description="Filter by cluster"
    )
    action_type: Literal['RIA', 'IA', 'CSA', 'COFUND', 'ERC', 'MSCA'] | None = Field(
        default=None,
        description="Filter by action type"
    )
    min_budget: float | None = Field(
        default=None,
        ge=0,
        description="Minimum project budget in EUR"
    )
    max_budget: float | None = Field(
        default=None,
        description="Maximum project budget in EUR"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum projects to return"
    )

    @field_validator('description')
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        return validate_not_empty(v, 'Description')


# ============================================================================
# FEEDBACK VALIDATORS
# ============================================================================

class FeedbackRequest(BaseModel):
    """Request schema for submitting feedback."""

    conversation_id: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="Conversation ID for the feedback"
    )
    message_id: str | None = Field(
        default=None,
        max_length=64,
        description="Specific message ID if applicable"
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating from 1 (poor) to 5 (excellent)"
    )
    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional feedback comment"
    )
    tool_feedback: dict[str, int] | None = Field(
        default=None,
        description="Per-tool ratings (tool_name -> rating 1-5)"
    )

    @field_validator('tool_feedback')
    @classmethod
    def validate_tool_feedback(cls, v: dict[str, int] | None) -> dict[str, int] | None:
        if v:
            for tool_name, rating in v.items():
                if not isinstance(rating, int) or rating < 1 or rating > 5:
                    raise ValueError(f'Tool rating for {tool_name} must be an integer between 1 and 5')
        return v


# ============================================================================
# BATCH OPERATION VALIDATORS
# ============================================================================

class BatchOperation(BaseModel):
    """Single operation in a batch request."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique operation ID for result matching"
    )
    type: Literal[
        'search_calls',
        'search_projects',
        'get_statistics',
        'get_call_details',
        'get_project_details'
    ] = Field(
        ...,
        description="Type of operation to execute"
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the operation"
    )


class BatchRequest(BaseModel):
    """Request schema for batch operations."""

    operations: list[BatchOperation] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of operations to execute"
    )

    @field_validator('operations')
    @classmethod
    def validate_unique_ids(cls, v: list[BatchOperation]) -> list[BatchOperation]:
        ids = [op.id for op in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Operation IDs must be unique')
        return v


# ============================================================================
# EXPORT VALIDATORS
# ============================================================================

class ExportRequest(BaseModel):
    """Request schema for exporting proposals."""

    format: Literal['docx', 'pdf'] = Field(
        default='docx',
        description="Export format"
    )
    sections: list[str] | None = Field(
        default=None,
        description="Specific sections to export (None = all)"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include proposal metadata in export"
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_call_id_format(call_id: str) -> bool:
    """
    Validate that a call ID follows expected format.

    Common formats:
    - HORIZON-CL5-2025-D3-01
    - ERC-2024-ADG
    - MSCA-PF-2025
    """
    patterns = [
        r'^HORIZON-[A-Z0-9]+-\d{4}(-[A-Z0-9]+)+$',  # Standard Horizon format
        r'^ERC-\d{4}-[A-Z]+$',  # ERC format
        r'^MSCA-[A-Z]+-\d{4}$',  # MSCA format
    ]
    return any(re.match(pattern, call_id.upper()) for pattern in patterns)


def validate_cluster_code(cluster: str) -> str:
    """
    Validate and normalize cluster code.

    Accepts: CL1, CL5, CLUSTER-1, CLUSTER-5
    Returns: CLUSTER-N format
    """
    cluster = cluster.upper().strip()

    # Already in CLUSTER-N format
    if re.match(r'^CLUSTER-[1-6]$', cluster):
        return cluster

    # In CLN format
    if re.match(r'^CL[1-6]$', cluster):
        return f"CLUSTER-{cluster[2]}"

    raise ValueError(f"Invalid cluster code: {cluster}. Use CL1-CL6 or CLUSTER-1 to CLUSTER-6")


def sanitize_search_query(query: str) -> str:
    """
    Sanitize a search query for safe database usage.

    Removes potentially dangerous characters while preserving
    meaningful search terms.
    """
    # Remove SQL injection attempts
    dangerous_patterns = [
        r'--',
        r';',
        r"'",
        r'"',
        r'\\',
        r'DROP\s+TABLE',
        r'DELETE\s+FROM',
        r'INSERT\s+INTO',
        r'UPDATE\s+',
    ]

    sanitized = query
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

    # Remove excessive whitespace
    sanitized = ' '.join(sanitized.split())

    return sanitized.strip()

"""
Pydantic models for project-related API endpoints.
"""

from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base model for CORDIS project data."""
    id: str = Field(..., description="CORDIS project ID")
    rcn: str = Field(..., description="Record Control Number")
    title: str = Field(..., description="Project title")
    acronym: Optional[str] = Field(None, description="Project acronym")


class ProjectSearchFilters(BaseModel):
    """Filters for project search."""
    programme: Optional[str] = Field(None, description="Framework programme (e.g., 'H2020', 'HORIZON')")
    date_start: Optional[date] = Field(None, description="Minimum start date")
    date_end: Optional[date] = Field(None, description="Maximum end date")
    budget_min: Optional[float] = Field(None, ge=0, description="Minimum total cost in EUR")
    budget_max: Optional[float] = Field(None, ge=0, description="Maximum total cost in EUR")
    countries: Optional[List[str]] = Field(None, description="List of participant country codes")


class ProjectSearchRequest(BaseModel):
    """Request model for project search."""
    queries: List[str] = Field(..., min_length=1, description="Search queries")
    filters: Optional[ProjectSearchFilters] = Field(None, description="Optional filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")


class ProjectSummary(ProjectBase):
    """Summary view of a project for search results."""
    objective: str = Field(..., description="Project objective/description")
    start_date: str = Field(..., description="Project start date")
    end_date: str = Field(..., description="Project end date")
    total_cost: float = Field(..., ge=0, description="Total project cost in EUR")
    ec_max_contribution: float = Field(..., ge=0, description="Maximum EC contribution in EUR")
    status: str = Field(..., description="Project status")
    framework_programme: str = Field(..., description="Framework programme")
    participant_count: int = Field(..., ge=0, description="Number of participants")
    country_count: int = Field(..., ge=0, description="Number of countries")
    coordinator_name: Optional[str] = Field(None, description="Coordinator organization name")
    coordinator_country: Optional[str] = Field(None, description="Coordinator country code")
    relevance_score: float = Field(0.0, description="Search relevance score")


class ProjectDetail(ProjectSummary):
    """Detailed view of a project."""
    funding_scheme: str = Field(..., description="Funding scheme")
    legal_basis: str = Field(..., description="Legal basis")
    topics: str = Field(..., description="Associated topics")
    grant_doi: str = Field(..., description="Grant DOI")
    sme_count: int = Field(..., ge=0, description="Number of SME participants")
    participant_names: List[str] = Field(default_factory=list, description="Participant organization names")
    participant_countries: List[str] = Field(default_factory=list, description="Participant country codes")
    participant_cities: List[str] = Field(default_factory=list, description="Participant cities")
    total_ec_contribution: float = Field(..., ge=0, description="Total EC contribution across all participants")
    nuts_codes: List[str] = Field(default_factory=list, description="NUTS region codes")
    activity_types: List[str] = Field(default_factory=list, description="Participant activity types")


class ProjectSearchResponse(BaseModel):
    """Response model for project search."""
    projects: List[ProjectSummary] = Field(..., description="List of matching projects")
    total_count: int = Field(..., ge=0, description="Total number of matching projects")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")
    query_time_ms: float = Field(..., ge=0, description="Query execution time in milliseconds")


class Publication(BaseModel):
    """Publication associated with a project."""
    title: Optional[str] = Field(None, description="Publication title")
    authors: Optional[str] = Field(None, description="Publication authors")
    journal: Optional[str] = Field(None, description="Journal name")
    publication_date: Optional[str] = Field(None, description="Publication date")
    doi: Optional[str] = Field(None, description="DOI")
    is_open_access: Optional[bool] = Field(None, description="Whether publication is open access")
    url: Optional[str] = Field(None, description="Publication URL")


class Deliverable(BaseModel):
    """Deliverable from a project."""
    title: Optional[str] = Field(None, description="Deliverable title")
    type: Optional[str] = Field(None, description="Deliverable type")
    description: Optional[str] = Field(None, description="Deliverable description")
    url: Optional[str] = Field(None, description="Deliverable URL")


class ProjectImpactMetrics(BaseModel):
    """Impact metrics for a project."""
    publications_count: int = Field(0, ge=0, description="Number of publications")
    deliverables_count: int = Field(0, ge=0, description="Number of deliverables")


class ProjectDetailWithResults(ProjectDetail):
    """Project detail including publications and deliverables."""
    publications: List[Publication] = Field(default_factory=list, description="Project publications")
    deliverables: List[Deliverable] = Field(default_factory=list, description="Project deliverables")
    impact_metrics: ProjectImpactMetrics = Field(default_factory=ProjectImpactMetrics, description="Impact metrics")

"""Typed arguments for the existing MAPIT tool registry.

The descriptions remain in ``Tool.parameters``. This catalog adds runtime types
and required-field rules without importing tool implementations or opening their
database clients. Optional arguments are omitted when unset, so dispatcher defaults
remain the source of runtime default values.
"""

from datetime import date
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    StrictStr,
    StringConstraints,
    create_model,
)

NonEmptyText = Annotated[str, StringConstraints(strict=True, min_length=1)]
PositiveInteger = Annotated[int, Field(strict=True, ge=1)]
ResultLimit = Annotated[int, Field(strict=True, ge=1, le=1000)]
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
NonNegativeNumber = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
PositiveNumber = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
Year = Annotated[int, Field(strict=True, ge=1900, le=2200)]
Probability = Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
ProjectIdentifier = NonEmptyText | PositiveInteger


def _calendar_date(value: Any) -> Any:
    if isinstance(value, str):
        date.fromisoformat(value)
    return value


ISODate = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    BeforeValidator(_calendar_date),
    Field(json_schema_extra={"format": "date"}),
]


class ToolArguments(BaseModel):
    """Reject unknown keys and implicit string/boolean-to-number coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


# Text fields intentionally retain free-form programme/action/organisation names.
# Their accepted values differ between programme tools and are normalized by the
# existing implementations. Restricting them to one programme's enum would break
# cross-programme queries.
_TEXT_FIELDS = frozenset(
    {
        "action_type",
        "call_id",
        "check_type",
        "cluster",
        "content",
        "context",
        "country",
        "description",
        "destination_country",
        "distance_band",
        "document_type",
        "evaluation_type",
        "excellence_content",
        "guidance",
        "impact_content",
        "implementation_content",
        "key_action",
        "keywords",
        "metric",
        "objective",
        "org_type",
        "organization_name",
        "organization_type",
        "origin_country",
        "partnership_type",
        "programme",
        "programme_a",
        "programme_b",
        "project_scale",
        "project_title",
        "project_type",
        "query",
        "role",
        "role_filter",
        "section",
        "section_id",
        "section_type",
        "sector",
        "similarity_type",
        "sort_by",
        "status",
        "strand",
        "style",
        "subprogramme",
        "suggestion_types",
        "text",
        "tone",
        "topic",
        "topic_keywords",
        "topic_pattern",
    }
)
_PARAMETER_TYPES: dict[str, Any] = dict.fromkeys(_TEXT_FIELDS, StrictStr)
_PARAMETER_TYPES.update(
    {
        "action_types": list[NonEmptyText],
        "countries": list[NonEmptyText],
        "country_groups": dict[NonEmptyText, list[NonEmptyText]],
        "cost_breakdown": dict[NonEmptyText, FiniteNumber],
        "consortium": list[dict[str, JsonValue]],
        "custom_wps": list[dict[str, JsonValue]],
        "focus_areas": StrictStr | list[NonEmptyText],
        "metrics": list[NonEmptyText],
        "programmes": list[NonEmptyText],
        "exclude_widening": StrictBool,
        "expand_scope": StrictBool,
        "green_travel": StrictBool,
        "has_eche": StrictBool,
        "include_breakdown": StrictBool,
        "include_closed": StrictBool,
        "include_fixes": StrictBool,
        "include_projects": StrictBool,
        "is_coordinator": StrictBool,
        "preserve_length": StrictBool,
        "duration_days": PositiveInteger,
        "duration_months": PositiveInteger,
        "limit": ResultLimit,
        "max_results": ResultLimit,
        "min_partners": PositiveInteger,
        "min_projects": PositiveInteger,
        "num_participants": PositiveInteger,
        "num_partners": PositiveInteger,
        "top_k": ResultLimit,
        "word_target": PositiveInteger,
        "year": Year,
        "year_from": Year,
        "year_to": Year,
        "call_budget_cap": NonNegativeNumber,
        "eu_contribution": NonNegativeNumber,
        "max_budget": NonNegativeNumber,
        "min_budget": NonNegativeNumber,
        "requested_amount": NonNegativeNumber,
        "target_budget": NonNegativeNumber,
        "total_cost": NonNegativeNumber,
        "total_person_months": PositiveNumber,
        "similarity_threshold": Probability,
        "project_id": ProjectIdentifier,
        "start_date": ISODate,
    }
)

# A closed tool-name catalog prevents a new registration from accidentally getting
# a string-only or permissive schema. Extensions can supply Tool.input_model.
# Defaults for planning/calculator arguments stay in the dispatcher, including the
# established RIA / 36-month / partner-count defaults.
_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "get_programme_statistics": frozenset({"programme"}),
    "get_country_statistics": frozenset({"country"}),
    "get_budget_benchmark": frozenset(),
    "get_consortium_patterns": frozenset(),
    "analyze_geographic_diversification": frozenset(),
    "find_experienced_partners": frozenset({"topic_keywords"}),
    "get_similar_funded_projects": frozenset({"description"}),
    "analyze_call_history": frozenset(),
    "compare_programmes": frozenset({"programme_a", "programme_b"}),
    "search_documents": frozenset({"query"}),
    "search_funding_calls": frozenset(),
    "get_call_details": frozenset({"call_id"}),
    "search_projects": frozenset(),
    "get_project_details": frozenset({"project_id"}),
    "find_similar_projects": frozenset({"project_id"}),
    "find_semantically_similar_projects": frozenset({"project_id"}),
    "find_organization_projects": frozenset({"organization_name"}),
    "get_project_partners": frozenset({"project_id"}),
    "get_organization_stats": frozenset({"organization_name"}),
    "get_collaboration_network": frozenset({"organization_name"}),
    "search_by_cluster": frozenset({"cluster"}),
    "calculate_budget": frozenset(),
    "generate_timeline": frozenset(),
    "search_all_programmes": frozenset(),
    "recommend_programmes": frozenset({"description"}),
    "get_programme_info": frozenset(),
    "score_proposal_section": frozenset({"content", "section_type"}),
    "score_full_proposal": frozenset(
        {"excellence_content", "impact_content", "implementation_content"}
    ),
    "quick_quality_check": frozenset({"text"}),
    "validate_budget": frozenset({"total_cost", "eu_contribution"}),
    "check_erasmus_eligibility": frozenset({"org_type", "country"}),
    "calculate_erasmus_budget": frozenset({"action_type"}),
    "search_erasmus_templates": frozenset({"query"}),
    "check_creative_europe_eligibility": frozenset({"org_type", "country"}),
    "calculate_creative_europe_budget": frozenset({"action_type"}),
    "search_creative_europe_templates": frozenset({"query"}),
    "check_eu4health_eligibility": frozenset({"org_type", "country"}),
    "search_eu4health_templates": frozenset({"query"}),
    "check_digital_europe_eligibility": frozenset({"org_type", "country"}),
    "check_life_eligibility": frozenset({"org_type", "country"}),
    "search_life_templates": frozenset({"query"}),
    "show_cached_projects": frozenset(),
    "generate_section_draft": frozenset({"section_id", "call_id"}),
    "improve_section": frozenset({"section_id"}),
    "rewrite_section": frozenset({"section_id", "style"}),
    "evaluate_section": frozenset({"section_id"}),
    "analyze_gaps": frozenset({"section_id"}),
    "check_compliance": frozenset(),
    "get_suggestions": frozenset({"section_id"}),
    "focus_section": frozenset({"section_id"}),
    "mark_section_status": frozenset({"section_id", "status"}),
    "get_document_overview": frozenset(),
}

_FIELD_OVERRIDES: dict[tuple[str, str], Any] = {
    ("search_projects", "sort_by"): Literal[
        "relevance", "ec_contribution", "total_cost", "start_date"
    ],
    ("find_similar_projects", "similarity_type"): Literal["topic", "consortium", "cluster"],
    ("find_experienced_partners", "role_filter"): Literal["coordinator", "participant"],
    ("find_organization_projects", "role"): Literal["coordinator", "participant"],
    ("search_funding_calls", "status"): Literal["open", "upcoming", "closed"],
    ("search_all_programmes", "status"): Literal["open", "upcoming", "closed"],
    ("score_proposal_section", "section_type"): Literal["excellence", "impact", "implementation"],
    ("score_proposal_section", "content"): Annotated[
        str, StringConstraints(strict=True, min_length=50)
    ],
    ("calculate_creative_europe_budget", "project_scale"): Literal["small", "medium", "large"],
    ("generate_section_draft", "style"): Literal["formal", "technical", "accessible"],
    ("rewrite_section", "style"): Literal[
        "concise", "impactful", "eu_evaluator_friendly", "technical", "accessible"
    ],
    ("rewrite_section", "tone"): Literal["confident", "measured", "ambitious"],
    ("evaluate_section", "evaluation_type"): Literal["quick", "detailed"],
    ("check_compliance", "check_type"): Literal["mandatory", "recommended", "all"],
    ("mark_section_status", "status"): Literal["complete", "in_review", "draft", "empty"],
    # A validator tool must be able to receive invalid numerical budgets and report
    # the funding-rule violations rather than force the model to alter user data.
    ("validate_budget", "total_cost"): FiniteNumber,
    ("validate_budget", "eu_contribution"): FiniteNumber,
    ("validate_budget", "call_budget_cap"): FiniteNumber,
    ("validate_budget", "duration_months"): StrictInt,
    ("validate_budget", "num_partners"): StrictInt,
    ("analyze_call_history", "keywords"): StrictStr | list[NonEmptyText],
}

# These are already consumed by the public dispatch wrappers but omitted from the
# old prompt-only registry. Expose them rather than discard useful functionality.
_EXTRA_PARAMETERS: dict[str, dict[str, str]] = {
    "get_consortium_patterns": {"min_projects": "Minimum projects for consortium analysis."},
    "find_experienced_partners": {"limit": "Maximum number of partner results."},
    "get_similar_funded_projects": {
        "similarity_threshold": "Minimum semantic similarity between zero and one."
    },
    "analyze_call_history": {"limit": "Maximum number of historical call results."},
    "search_funding_calls": {"cluster": "Optional cluster code to filter funding calls."},
    "calculate_budget": {"include_breakdown": "Include budget categories in the result."},
    "generate_timeline": {"custom_wps": "Custom work-package definitions as JSON objects."},
    "search_all_programmes": {
        "action_type": "Optional funding action type filter.",
        "limit": "Maximum number of funding call results.",
        "include_closed": "Include closed calls in search results.",
    },
    "score_proposal_section": {"call_id": "Optional funding call identifier for evaluation."},
    "score_full_proposal": {"call_id": "Optional funding call identifier for evaluation."},
    "validate_budget": {"consortium": "Partner details as JSON objects for budget validation."},
}

_ALLOW_EMPTY_REQUIRED = frozenset(
    {
        ("score_full_proposal", "excellence_content"),
        ("score_full_proposal", "impact_content"),
        ("score_full_proposal", "implementation_content"),
        ("quick_quality_check", "text"),
    }
)


@lru_cache(maxsize=128)
def _build_model(name: str, descriptions: tuple[tuple[str, str], ...]) -> type[BaseModel]:
    if name not in _REQUIRED_FIELDS:
        raise ValueError(f"Tool {name!r} needs an explicit input_model")
    fields = {}
    required = _REQUIRED_FIELDS[name]
    parameters = dict(descriptions)
    parameters.update(_EXTRA_PARAMETERS.get(name, {}))
    missing = required - parameters.keys()
    if missing:
        raise ValueError(
            f"Tool {name!r} is missing required parameter definitions: {sorted(missing)}"
        )
    for parameter, description in parameters.items():
        annotation = _FIELD_OVERRIDES.get((name, parameter), _PARAMETER_TYPES.get(parameter))
        if annotation is None:
            raise ValueError(f"Tool {name!r} parameter {parameter!r} needs an explicit input type")
        if parameter in required:
            if annotation is StrictStr and (name, parameter) not in _ALLOW_EMPTY_REQUIRED:
                annotation = NonEmptyText
            fields[parameter] = (annotation, Field(description=description))
        else:
            fields[parameter] = (annotation | None, Field(default=None, description=description))
    model_name = "".join(part.title() for part in name.split("_")) + "Arguments"
    return create_model(model_name, __base__=ToolArguments, **fields)


def input_model_for(tool: Any) -> type[BaseModel]:
    """Return strict arguments for a registry entry or its explicit extension model."""
    override = getattr(tool, "input_model", None)
    if override is not None:
        if not isinstance(override, type) or not issubclass(override, BaseModel):
            raise TypeError(f"Tool {tool.name!r} input_model must be a Pydantic model class")
        return override
    parameters = tool.parameters
    if not isinstance(parameters, dict) or any(
        not isinstance(key, str) or not isinstance(value, str) for key, value in parameters.items()
    ):
        raise TypeError(f"Tool {tool.name!r} parameters must map names to description strings")
    return _build_model(tool.name, tuple(sorted(parameters.items())))

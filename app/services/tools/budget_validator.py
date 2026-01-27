"""
Budget Validation Tool

Validates Horizon Europe proposal budgets against EU funding rules,
action-type constraints, and best practices from funded projects.

Provides multi-level validation:
- Critical: Violations that would disqualify the proposal
- High: Likely to trigger evaluator concerns
- Medium: Suboptimal but acceptable
- Low: Suggestions for improvement
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Severity level of validation issues."""

    CRITICAL = "critical"  # Will disqualify proposal
    HIGH = "high"  # Likely evaluator concern
    MEDIUM = "medium"  # Suboptimal, may affect score
    LOW = "low"  # Suggestion for improvement


class IssueCategory(Enum):
    """Category of validation issues."""

    FUNDING_RATE = "funding_rate"
    COST_CATEGORY = "cost_category"
    CONSORTIUM = "consortium"
    BUDGET_RANGE = "budget_range"
    ENTITY_TYPE = "entity_type"
    INDIRECT_COSTS = "indirect_costs"
    DURATION = "duration"
    CALL_SPECIFIC = "call_specific"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    level: ValidationLevel
    category: IssueCategory
    message: str
    recommendation: str
    affected_value: Any | None = None
    expected_range: str | None = None


@dataclass
class ValidationResult:
    """Complete validation result."""

    valid: bool
    compliance_score: float  # 0-100
    issues: list[ValidationIssue] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    summary: str = ""

    @property
    def critical_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.CRITICAL]

    @property
    def high_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.HIGH]


class BudgetValidatorTool:
    """
    Validates Horizon Europe proposal budgets.

    Checks:
    1. Funding rate compliance by action type
    2. Cost category constraints (personnel, equipment, subcontracting, etc.)
    3. Consortium structure requirements
    4. Indirect cost calculations (25% rule)
    5. Budget range reasonableness
    6. Entity type specific rules
    """

    # Funding rates by action type and entity type
    FUNDING_RATES = {
        "RIA": {"default": 1.00, "for_profit": 1.00},
        "IA": {"default": 1.00, "for_profit": 0.70},
        "CSA": {"default": 1.00, "for_profit": 1.00},
        "ERC-STG": {"default": 1.00, "for_profit": 1.00},
        "ERC-COG": {"default": 1.00, "for_profit": 1.00},
        "ERC-ADG": {"default": 1.00, "for_profit": 1.00},
        "EIC": {"default": 0.70, "for_profit": 0.70},
        "MSCA": {"default": 1.00, "for_profit": 1.00},
    }

    # Indirect cost rate (flat rate on direct costs minus subcontracting)
    INDIRECT_COST_RATE = 0.25

    # Cost category constraints (as % of total direct costs)
    COST_CATEGORY_LIMITS = {
        "RIA": {
            "personnel": {"min": 0.40, "max": 0.70, "typical": 0.55},
            "equipment": {"min": 0.0, "max": 0.20, "typical": 0.10},
            "travel": {"min": 0.02, "max": 0.10, "typical": 0.05},
            "subcontracting": {"min": 0.0, "max": 0.20, "typical": 0.10},
            "other_direct": {"min": 0.0, "max": 0.15, "typical": 0.05},
        },
        "IA": {
            "personnel": {"min": 0.35, "max": 0.60, "typical": 0.45},
            "equipment": {"min": 0.0, "max": 0.25, "typical": 0.15},
            "travel": {"min": 0.02, "max": 0.10, "typical": 0.05},
            "subcontracting": {"min": 0.0, "max": 0.25, "typical": 0.15},
            "other_direct": {"min": 0.0, "max": 0.15, "typical": 0.05},
        },
        "CSA": {
            "personnel": {"min": 0.50, "max": 0.80, "typical": 0.65},
            "equipment": {"min": 0.0, "max": 0.10, "typical": 0.02},
            "travel": {"min": 0.05, "max": 0.15, "typical": 0.08},
            "subcontracting": {"min": 0.0, "max": 0.15, "typical": 0.08},
            "other_direct": {"min": 0.0, "max": 0.15, "typical": 0.05},
        },
    }

    # Consortium requirements by action type
    CONSORTIUM_REQUIREMENTS = {
        "RIA": {"min_partners": 3, "min_countries": 2, "max_coordinator_share": 0.40},
        "IA": {"min_partners": 3, "min_countries": 2, "max_coordinator_share": 0.40},
        "CSA": {"min_partners": 1, "min_countries": 1, "max_coordinator_share": 1.00},
        "ERC-STG": {"min_partners": 1, "min_countries": 1, "max_coordinator_share": 1.00},
        "ERC-COG": {"min_partners": 1, "min_countries": 1, "max_coordinator_share": 1.00},
        "ERC-ADG": {"min_partners": 1, "min_countries": 1, "max_coordinator_share": 1.00},
        "MSCA": {"min_partners": 1, "min_countries": 1, "max_coordinator_share": 1.00},
    }

    # Budget ranges by action type (in EUR)
    BUDGET_RANGES = {
        "RIA": {"min": 1_000_000, "max": 15_000_000, "typical": 4_000_000},
        "IA": {"min": 2_000_000, "max": 25_000_000, "typical": 8_000_000},
        "CSA": {"min": 500_000, "max": 5_000_000, "typical": 2_000_000},
        "ERC-STG": {"min": 1_000_000, "max": 1_500_000, "typical": 1_500_000},
        "ERC-COG": {"min": 1_500_000, "max": 2_000_000, "typical": 2_000_000},
        "ERC-ADG": {"min": 2_000_000, "max": 2_500_000, "typical": 2_500_000},
        "EIC": {"min": 500_000, "max": 2_500_000, "typical": 1_500_000},
        "MSCA": {"min": 100_000, "max": 500_000, "typical": 200_000},
    }

    # Duration ranges by action type (in months)
    DURATION_RANGES = {
        "RIA": {"min": 24, "max": 60, "typical": 36},
        "IA": {"min": 24, "max": 60, "typical": 42},
        "CSA": {"min": 12, "max": 48, "typical": 24},
        "ERC-STG": {"min": 48, "max": 60, "typical": 60},
        "ERC-COG": {"min": 48, "max": 60, "typical": 60},
        "ERC-ADG": {"min": 48, "max": 60, "typical": 60},
        "MSCA": {"min": 12, "max": 36, "typical": 24},
    }

    # Entity types
    ENTITY_TYPES = {
        "HES": "Higher Education Institution",
        "REC": "Research Organization",
        "PRC": "Private Company",
        "PUB": "Public Body",
        "OTH": "Other",
        "SME": "Small/Medium Enterprise",
    }

    def validate_budget(
        self,
        total_cost: float,
        eu_contribution: float,
        action_type: str = "RIA",
        duration_months: int = 36,
        num_partners: int = 3,
        cost_breakdown: dict[str, float] | None = None,
        consortium: list[dict] | None = None,
        call_budget_cap: float | None = None,
    ) -> ValidationResult:
        """
        Validate a proposal budget.

        Args:
            total_cost: Total project cost in EUR
            eu_contribution: Requested EU contribution in EUR
            action_type: RIA, IA, CSA, ERC-STG, etc.
            duration_months: Project duration
            num_partners: Number of consortium partners
            cost_breakdown: Dict with personnel, equipment, travel, etc.
            consortium: List of partner dicts with country, type, budget_share
            call_budget_cap: Optional call-specific budget cap

        Returns:
            ValidationResult with issues and recommendations
        """
        issues: list[ValidationIssue] = []
        passed_checks: list[str] = []

        # Normalize action type
        action_type = action_type.upper()
        if action_type not in self.FUNDING_RATES:
            action_type = "RIA"  # Default fallback

        # Run all validations
        self._validate_funding_rate(total_cost, eu_contribution, action_type, issues, passed_checks)
        self._validate_indirect_costs(total_cost, cost_breakdown, issues, passed_checks)
        self._validate_cost_categories(action_type, cost_breakdown, issues, passed_checks)
        self._validate_budget_range(
            eu_contribution, action_type, call_budget_cap, issues, passed_checks
        )
        self._validate_duration(duration_months, action_type, issues, passed_checks)
        self._validate_consortium(num_partners, consortium, action_type, issues, passed_checks)
        self._validate_budget_per_partner(
            eu_contribution, num_partners, duration_months, issues, passed_checks
        )

        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(issues, passed_checks)

        # Determine overall validity
        valid = len([i for i in issues if i.level == ValidationLevel.CRITICAL]) == 0

        # Generate summary
        summary = self._generate_summary(
            valid, compliance_score, issues, passed_checks, action_type
        )

        return ValidationResult(
            valid=valid,
            compliance_score=compliance_score,
            issues=issues,
            passed_checks=passed_checks,
            summary=summary,
        )

    def _validate_funding_rate(
        self,
        total_cost: float,
        eu_contribution: float,
        action_type: str,
        issues: list[ValidationIssue],
        passed: list[str],
    ):
        """Validate funding rate is correct for action type."""
        if total_cost <= 0:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category=IssueCategory.FUNDING_RATE,
                    message="Total cost must be greater than zero",
                    recommendation="Provide valid total cost figure",
                    affected_value=total_cost,
                )
            )
            return

        actual_rate = eu_contribution / total_cost
        expected_rate = self.FUNDING_RATES.get(action_type, {}).get("default", 1.0)
        for_profit_rate = self.FUNDING_RATES.get(action_type, {}).get("for_profit", expected_rate)

        # Allow small tolerance for rounding
        tolerance = 0.02

        if actual_rate > expected_rate + tolerance:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category=IssueCategory.FUNDING_RATE,
                    message=(
                        f"Funding rate ({actual_rate:.1%}) exceeds maximum "
                        f"for {action_type} ({expected_rate:.0%})"
                    ),
                    recommendation=(
                        f"Reduce EU contribution to max {expected_rate:.0%} of total cost"
                    ),
                    affected_value=f"{actual_rate:.1%}",
                    expected_range=f"0-{expected_rate:.0%}",
                )
            )
        elif action_type == "IA" and actual_rate > for_profit_rate + tolerance:
            # IA may have mixed rates depending on consortium
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category=IssueCategory.FUNDING_RATE,
                    message=(
                        f"High funding rate ({actual_rate:.1%}) for IA action. "
                        "For-profit entities should receive only 70%"
                    ),
                    recommendation="Verify that only non-profit entities claim 100% funding rate",
                    affected_value=f"{actual_rate:.1%}",
                )
            )
        else:
            passed.append(
                f"Funding rate ({actual_rate:.1%}) within acceptable range for {action_type}"
            )

    def _validate_indirect_costs(
        self,
        total_cost: float,
        cost_breakdown: dict[str, float] | None,
        issues: list[ValidationIssue],
        passed: list[str],
    ):
        """Validate indirect costs are calculated correctly (25% flat rate)."""
        if not cost_breakdown:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.LOW,
                    category=IssueCategory.INDIRECT_COSTS,
                    message="No cost breakdown provided - cannot verify indirect cost calculation",
                    recommendation="Provide detailed cost breakdown for full validation",
                )
            )
            return

        indirect = cost_breakdown.get("indirect", cost_breakdown.get("indirect_costs", 0))
        direct_total = sum(
            cost_breakdown.get(cat, 0)
            for cat in ["personnel", "equipment", "travel", "other_direct"]
        )
        # Subcontracting is excluded from indirect cost base
        cost_breakdown.get("subcontracting", 0)

        if direct_total <= 0:
            return

        expected_indirect = direct_total * self.INDIRECT_COST_RATE
        tolerance = expected_indirect * 0.05  # 5% tolerance

        if abs(indirect - expected_indirect) > tolerance:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category=IssueCategory.INDIRECT_COSTS,
                    message=(
                        f"Indirect costs (€{indirect:,.0f}) differ from "
                        f"25% flat rate (€{expected_indirect:,.0f})"
                    ),
                    recommendation=(
                        "Recalculate indirect costs as 25% of direct costs (excl. subcontracting)"
                    ),
                    affected_value=f"€{indirect:,.0f}",
                    expected_range=f"€{expected_indirect:,.0f}",
                )
            )
        else:
            passed.append(f"Indirect costs correctly calculated at 25% (€{indirect:,.0f})")

    def _validate_cost_categories(
        self,
        action_type: str,
        cost_breakdown: dict[str, float] | None,
        issues: list[ValidationIssue],
        passed: list[str],
    ):
        """Validate cost category ratios are reasonable."""
        if not cost_breakdown:
            return

        limits = self.COST_CATEGORY_LIMITS.get(action_type, self.COST_CATEGORY_LIMITS["RIA"])

        # Calculate total direct costs (excluding indirect)
        total_direct = sum(
            cost_breakdown.get(cat, 0)
            for cat in ["personnel", "equipment", "travel", "subcontracting", "other_direct"]
        )

        if total_direct <= 0:
            return

        for category, limit_config in limits.items():
            amount = cost_breakdown.get(category, 0)
            ratio = amount / total_direct if total_direct > 0 else 0

            if ratio > limit_config["max"]:
                level = (
                    ValidationLevel.HIGH
                    if ratio > limit_config["max"] * 1.5
                    else ValidationLevel.MEDIUM
                )
                issues.append(
                    ValidationIssue(
                        level=level,
                        category=IssueCategory.COST_CATEGORY,
                        message=(
                            f"{category.replace('_', ' ').title()} costs ({ratio:.1%}) "
                            f"exceed typical maximum ({limit_config['max']:.0%}) "
                            f"for {action_type}"
                        ),
                        recommendation=(
                            f"Consider reducing {category} costs or provide strong justification"
                        ),
                        affected_value=f"{ratio:.1%}",
                        expected_range=f"{limit_config['min']:.0%}-{limit_config['max']:.0%}",
                    )
                )
            elif ratio < limit_config["min"] and amount > 0:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.LOW,
                        category=IssueCategory.COST_CATEGORY,
                        message=(
                            f"{category.replace('_', ' ').title()} costs ({ratio:.1%}) "
                            f"below typical range for {action_type}"
                        ),
                        recommendation="This may be acceptable depending on project needs",
                        affected_value=f"{ratio:.1%}",
                    )
                )
            elif ratio > 0:
                passed.append(
                    f"{category.replace('_', ' ').title()} costs ({ratio:.1%}) within range"
                )

    def _validate_budget_range(
        self,
        eu_contribution: float,
        action_type: str,
        call_budget_cap: float | None,
        issues: list[ValidationIssue],
        passed: list[str],
    ):
        """Validate budget is within reasonable range for action type."""
        ranges = self.BUDGET_RANGES.get(action_type, self.BUDGET_RANGES["RIA"])

        # Check call-specific cap first
        if call_budget_cap and eu_contribution > call_budget_cap:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category=IssueCategory.BUDGET_RANGE,
                    message=(
                        f"EU contribution (€{eu_contribution:,.0f}) exceeds "
                        f"call budget cap (€{call_budget_cap:,.0f})"
                    ),
                    recommendation=f"Reduce budget to maximum €{call_budget_cap:,.0f}",
                    affected_value=f"€{eu_contribution:,.0f}",
                    expected_range=f"Max €{call_budget_cap:,.0f}",
                )
            )
            return

        if eu_contribution < ranges["min"]:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category=IssueCategory.BUDGET_RANGE,
                    message=(
                        f"Budget (€{eu_contribution:,.0f}) below typical minimum "
                        f"for {action_type} (€{ranges['min']:,.0f})"
                    ),
                    recommendation="Ensure budget adequately covers planned activities",
                    affected_value=f"€{eu_contribution:,.0f}",
                    expected_range=f"€{ranges['min']:,.0f}-€{ranges['max']:,.0f}",
                )
            )
        elif eu_contribution > ranges["max"]:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category=IssueCategory.BUDGET_RANGE,
                    message=(
                        f"Budget (€{eu_contribution:,.0f}) exceeds typical maximum "
                        f"for {action_type} (€{ranges['max']:,.0f})"
                    ),
                    recommendation=(
                        "Verify budget justification is strong or consider splitting into phases"
                    ),
                    affected_value=f"€{eu_contribution:,.0f}",
                    expected_range=f"€{ranges['min']:,.0f}-€{ranges['max']:,.0f}",
                )
            )
        else:
            passed.append(
                f"Budget (€{eu_contribution:,.0f}) within typical range for {action_type}"
            )

    def _validate_duration(
        self,
        duration_months: int,
        action_type: str,
        issues: list[ValidationIssue],
        passed: list[str],
    ):
        """Validate project duration is appropriate."""
        ranges = self.DURATION_RANGES.get(action_type, self.DURATION_RANGES["RIA"])

        if duration_months < ranges["min"]:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category=IssueCategory.DURATION,
                    message=(
                        f"Duration ({duration_months} months) below minimum "
                        f"for {action_type} ({ranges['min']} months)"
                    ),
                    recommendation=f"Extend project duration to at least {ranges['min']} months",
                    affected_value=f"{duration_months} months",
                    expected_range=f"{ranges['min']}-{ranges['max']} months",
                )
            )
        elif duration_months > ranges["max"]:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category=IssueCategory.DURATION,
                    message=(
                        f"Duration ({duration_months} months) exceeds typical maximum "
                        f"for {action_type} ({ranges['max']} months)"
                    ),
                    recommendation="Consider phased approach or verify justification",
                    affected_value=f"{duration_months} months",
                    expected_range=f"{ranges['min']}-{ranges['max']} months",
                )
            )
        else:
            passed.append(f"Duration ({duration_months} months) appropriate for {action_type}")

    def _validate_consortium(
        self,
        num_partners: int,
        consortium: list[dict] | None,
        action_type: str,
        issues: list[ValidationIssue],
        passed: list[str],
    ):
        """Validate consortium structure."""
        reqs = self.CONSORTIUM_REQUIREMENTS.get(action_type, self.CONSORTIUM_REQUIREMENTS["RIA"])

        if num_partners < reqs["min_partners"]:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category=IssueCategory.CONSORTIUM,
                    message=(
                        f"Consortium has {num_partners} partners, "
                        f"minimum {reqs['min_partners']} required for {action_type}"
                    ),
                    recommendation=(
                        f"Add at least {reqs['min_partners'] - num_partners} more partners"
                    ),
                    affected_value=str(num_partners),
                    expected_range=f"Minimum {reqs['min_partners']}",
                )
            )
        else:
            passed.append(f"Consortium size ({num_partners} partners) meets minimum requirement")

        # Check country distribution if consortium details provided
        if consortium:
            countries = set(p.get("country", "Unknown") for p in consortium)
            if len(countries) < reqs["min_countries"]:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.CRITICAL,
                        category=IssueCategory.CONSORTIUM,
                        message=(
                            f"Consortium covers {len(countries)} countries, "
                            f"minimum {reqs['min_countries']} required"
                        ),
                        recommendation=(
                            "Add partners from additional EU Member States or Associated Countries"
                        ),
                        affected_value=str(len(countries)),
                    )
                )
            else:
                passed.append(f"Geographic coverage ({len(countries)} countries) meets requirement")

            # Check coordinator budget share
            coordinator = next(
                (p for p in consortium if p.get("role", "").lower() == "coordinator"), None
            )
            if coordinator and "budget_share" in coordinator:
                coord_share = coordinator["budget_share"]
                if coord_share > reqs["max_coordinator_share"]:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.MEDIUM,
                            category=IssueCategory.CONSORTIUM,
                            message=f"Coordinator budget share ({coord_share:.0%}) may be too high",
                            recommendation=(
                                "Consider redistributing budget among partners "
                                f"(typical max: {reqs['max_coordinator_share']:.0%})"
                            ),
                            affected_value=f"{coord_share:.0%}",
                        )
                    )

    def _validate_budget_per_partner(
        self,
        eu_contribution: float,
        num_partners: int,
        duration_months: int,
        issues: list[ValidationIssue],
        passed: list[str],
    ):
        """Validate budget per partner per year is reasonable."""
        if num_partners <= 0 or duration_months <= 0:
            return

        budget_per_partner = eu_contribution / num_partners
        budget_per_partner_year = budget_per_partner / (duration_months / 12)

        # Typical ranges for budget per partner per year
        min_per_partner_year = 50_000
        max_per_partner_year = 800_000

        if budget_per_partner_year < min_per_partner_year:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category=IssueCategory.BUDGET_RANGE,
                    message=(
                        "Average budget per partner per year "
                        f"(€{budget_per_partner_year:,.0f}) is low"
                    ),
                    recommendation=(
                        "Verify partners have sufficient resources for meaningful contributions"
                    ),
                    affected_value=f"€{budget_per_partner_year:,.0f}/partner/year",
                )
            )
        elif budget_per_partner_year > max_per_partner_year:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category=IssueCategory.BUDGET_RANGE,
                    message=(
                        "Average budget per partner per year "
                        f"(€{budget_per_partner_year:,.0f}) is high"
                    ),
                    recommendation="Ensure budget distribution reflects actual work allocation",
                    affected_value=f"€{budget_per_partner_year:,.0f}/partner/year",
                )
            )
        else:
            passed.append(
                f"Budget per partner (€{budget_per_partner_year:,.0f}/year) is reasonable"
            )

    def _calculate_compliance_score(
        self,
        issues: list[ValidationIssue],
        passed: list[str],
    ) -> float:
        """Calculate overall compliance score (0-100)."""
        # Penalty weights by issue level
        penalties = {
            ValidationLevel.CRITICAL: 30,
            ValidationLevel.HIGH: 15,
            ValidationLevel.MEDIUM: 5,
            ValidationLevel.LOW: 1,
        }

        total_penalty = sum(penalties[issue.level] for issue in issues)
        base_score = 100 - total_penalty

        # Bonus for passed checks
        bonus = min(len(passed) * 2, 20)

        score = base_score + bonus
        return max(0, min(100, score))

    def _generate_summary(
        self,
        valid: bool,
        score: float,
        issues: list[ValidationIssue],
        passed: list[str],
        action_type: str,
    ) -> str:
        """Generate human-readable validation summary."""
        critical_count = len([i for i in issues if i.level == ValidationLevel.CRITICAL])
        high_count = len([i for i in issues if i.level == ValidationLevel.HIGH])
        medium_count = len([i for i in issues if i.level == ValidationLevel.MEDIUM])

        if not valid:
            return (
                f"Budget validation FAILED with {critical_count} critical issue(s). "
                f"The proposal would likely be rejected. "
                f"Fix critical issues before submission."
            )
        elif high_count > 0:
            return (
                f"Budget validation passed with concerns. Score: {score:.0f}/100. "
                f"Found {high_count} high-priority and {medium_count} medium issues. "
                f"Address these to improve evaluator reception."
            )
        elif medium_count > 0:
            return (
                f"Budget validation passed. Score: {score:.0f}/100. "
                f"Found {medium_count} minor issue(s). "
                f"Budget is compliant but could be optimized."
            )
        else:
            return (
                f"Budget validation passed with excellent compliance. Score: {score:.0f}/100. "
                f"Passed {len(passed)} checks. Budget aligns well with {action_type} requirements."
            )


# Standalone execute function for tool orchestration


def validate_budget_execute(
    total_cost: float,
    eu_contribution: float,
    action_type: str = "RIA",
    duration_months: int = 36,
    num_partners: int = 3,
    cost_breakdown: dict[str, float] | None = None,
    consortium: list[dict] | None = None,
    call_budget_cap: float | None = None,
) -> dict[str, Any]:
    """
    Execute budget validation.

    Args:
        total_cost: Total project cost in EUR
        eu_contribution: Requested EU contribution in EUR
        action_type: RIA, IA, CSA, ERC-STG, ERC-COG, ERC-ADG, EIC, MSCA
        duration_months: Project duration in months
        num_partners: Number of consortium partners
        cost_breakdown: Optional dict with personnel, equipment, travel,
            subcontracting, other_direct, indirect
        consortium: Optional list of partner dicts with country, type, budget_share, role
        call_budget_cap: Optional call-specific budget cap

    Returns:
        Validation result with issues and recommendations
    """
    validator = BudgetValidatorTool()
    result = validator.validate_budget(
        total_cost=total_cost,
        eu_contribution=eu_contribution,
        action_type=action_type,
        duration_months=duration_months,
        num_partners=num_partners,
        cost_breakdown=cost_breakdown,
        consortium=consortium,
        call_budget_cap=call_budget_cap,
    )

    # Convert to dict for JSON serialization
    return {
        "success": True,
        "valid": result.valid,
        "compliance_score": round(result.compliance_score, 1),
        "summary": result.summary,
        "issues": [
            {
                "level": issue.level.value,
                "category": issue.category.value,
                "message": issue.message,
                "recommendation": issue.recommendation,
                "affected_value": issue.affected_value,
                "expected_range": issue.expected_range,
            }
            for issue in result.issues
        ],
        "passed_checks": result.passed_checks,
        "critical_count": len(result.critical_issues),
        "high_count": len(result.high_issues),
        "action_type": action_type,
    }

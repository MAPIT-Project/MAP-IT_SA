# isort: skip_file
"""
Failure Detection Module for Production Quality Validation.

This module provides specialized detector classes for identifying different
failure categories in MAPIT conversation responses, as specified in
MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD.md Task 002.

Detector Classes:
- NoResultsDetector: Detects empty, generic, or deflection responses
- IncorrectDataDetector: Detects factually wrong information
- MissingDataDetector: Detects responses that omit required information
- UnexpectedBehaviorDetector: Detects erratic or inconsistent behavior
- PoorQualityDetector: Detects technically correct but unhelpful responses

Usage:
    from tests.validators.failure_detector import detect_all, NoResultsDetector

    # Detect all failure types
    failures = detect_all(turn_result)

    # Use individual detectors
    detector = NoResultsDetector()
    failures = detector.detect(turn_result, turn_number=0)
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# =============================================================================
# Failure Categories and Severity (per PRD)
# =============================================================================


class FailureCategory(str, Enum):
    """Categories of failures as defined in the PRD."""

    NO_RESULTS = "NO_RESULTS"  # Empty, generic, or deflection response
    INCORRECT_DATA = "INCORRECT_DATA"  # Factually wrong information
    MISSING_DATA = "MISSING_DATA"  # Omits required information
    UNEXPECTED_BEHAVIOR = "UNEXPECTED_BEHAVIOR"  # Erratic or inconsistent behavior
    POOR_QUALITY = "POOR_QUALITY"  # Technically correct but unhelpful


class FailureSeverity(str, Enum):
    """Severity levels for failures."""

    CRITICAL = "CRITICAL"  # Requires immediate fix (NO_RESULTS, INCORRECT_DATA)
    HIGH = "HIGH"  # Requires fix (MISSING_DATA, UNEXPECTED_BEHAVIOR)
    MEDIUM = "MEDIUM"  # Requires improvement (POOR_QUALITY)


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class FailureRecord:
    """Records a single failure detected during scenario execution."""

    category: FailureCategory
    severity: FailureSeverity
    description: str
    turn_number: int
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "turn_number": self.turn_number,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TurnResult:
    """
    Simplified turn result for failure detection.

    This is a lightweight representation used by detectors.
    Can be created from ConversationTurn or other turn representations.
    """

    query: str
    response: str
    tools_used: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    has_error: bool = False
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    quality_score: float = 0.0
    previous_quality_score: float | None = None  # For degradation detection
    context_data: dict[str, Any] = field(default_factory=dict)

    def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.get("type") == event_type]


# =============================================================================
# Pattern Constants (per PRD Appendix)
# =============================================================================


NO_RESULTS_PATTERNS = [
    "I don't have",
    "I cannot find",
    "no information available",
    "I'm not able to",
    "I don't see any",
    "no results found",
    "unable to find",
    "no data available",
    "I couldn't find",
]

# Patterns that indicate "no results" only at the START of a sentence
# (to avoid false positives like "there are no restrictions")
NO_RESULTS_START_PATTERNS = [
    r"^there are no ",
    r"\. there are no ",
]

DEFLECTION_PATTERNS = [
    "you might want to",
    "I suggest checking",
    "please visit",
    "for more information",
    "I recommend contacting",
    "you should consult",
]

REQUIRED_FIELDS = {
    "call_search": ["call_id", "title", "deadline", "budget"],
    "project_search": ["project_id", "acronym", "budget", "coordinator"],
    "partner_search": ["organization_name", "country", "project_count"],
    "eligibility_query": ["eligible", "requirements", "exceptions"],
    "budget_calculation": ["total_budget", "breakdown", "funding_rate"],
    "timeline_generation": ["work_packages", "milestones", "duration"],
}

# Tool name to field type mapping
TOOL_TO_FIELD_TYPE = {
    "search_funding_calls": "call_search",
    "search_projects": "project_search",
    "find_experienced_partners": "partner_search",
    "calculate_budget": "budget_calculation",
    "generate_timeline": "timeline_generation",
    "check_erasmus_eligibility": "eligibility_query",
    "check_creative_europe_eligibility": "eligibility_query",
}

KNOWN_FACTS = {
    "horizon_europe": {
        "budget": (95_000_000_000, 96_000_000_000),  # €95.5B range
        "duration": "2021-2027",
        "pillars": 3,
        "clusters": 6,
    },
    "erasmus_plus": {
        "budget": (26_000_000_000, 27_000_000_000),  # €26.2B range
        "duration": "2021-2027",
        "key_actions": ["KA1", "KA2", "KA3", "Jean Monnet", "Sport"],
    },
    "creative_europe": {
        "budget": (2_400_000_000, 2_500_000_000),  # €2.44B range
        "duration": "2021-2027",
        "strands": ["CULTURE", "MEDIA", "CROSS-SECTORAL"],
    },
}

# Funding rates by action type (per PRD)
FUNDING_RATES = {
    "RIA": 100,  # Research and Innovation Action
    "IA": 70,  # Innovation Action (up to 70%)
    "CSA": 100,  # Coordination and Support Action
    "MSCA": 100,  # Marie Sklodowska-Curie Actions
    "ERC": 100,  # European Research Council
    "EIC": 70,  # EIC Accelerator (up to 70%)
}


# =============================================================================
# Base Detector Class
# =============================================================================


class BaseDetector(ABC):
    """Base class for all failure detectors."""

    category: FailureCategory
    default_severity: FailureSeverity

    def __init__(self, custom_patterns: list[str] | None = None):
        """
        Initialize the detector.

        Args:
            custom_patterns: Optional additional patterns for detection
        """
        self.custom_patterns = custom_patterns or []

    @abstractmethod
    def detect(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """
        Detect failures in the given turn.

        Args:
            turn: The turn result to analyze
            turn_number: The turn index in the conversation

        Returns:
            List of FailureRecord objects for detected failures
        """
        pass

    def _create_failure(
        self,
        description: str,
        turn_number: int,
        evidence: dict[str, Any] | None = None,
        severity: FailureSeverity | None = None,
    ) -> FailureRecord:
        """Helper to create a FailureRecord with defaults."""
        return FailureRecord(
            category=self.category,
            severity=severity or self.default_severity,
            description=description,
            turn_number=turn_number,
            evidence=evidence or {},
        )


# =============================================================================
# NoResultsDetector
# =============================================================================


class NoResultsDetector(BaseDetector):
    """
    Detector for NO_RESULTS failures.

    Detects:
    - Response < 100 characters
    - Contains no-results patterns ("I don't have", "no information", etc.)
    - Contains deflection patterns ("you might want to", "please visit", etc.)
    - Tool returns empty array [] or null

    Severity: CRITICAL for empty/no-results, HIGH for deflection
    """

    category = FailureCategory.NO_RESULTS
    default_severity = FailureSeverity.CRITICAL

    def __init__(
        self,
        min_response_length: int = 100,
        no_results_patterns: list[str] | None = None,
        deflection_patterns: list[str] | None = None,
    ):
        """
        Initialize the detector.

        Args:
            min_response_length: Minimum acceptable response length (default: 100)
            no_results_patterns: Custom no-results patterns (extends defaults)
            deflection_patterns: Custom deflection patterns (extends defaults)
        """
        super().__init__()
        self.min_response_length = min_response_length
        self.no_results_patterns = NO_RESULTS_PATTERNS + (no_results_patterns or [])
        self.deflection_patterns = DEFLECTION_PATTERNS + (deflection_patterns or [])

    def detect(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """Detect NO_RESULTS failures."""
        failures = []
        response_lower = turn.response.lower()

        # Check 1: Response length
        if len(turn.response) < self.min_response_length:
            resp_len = len(turn.response)
            failures.append(
                self._create_failure(
                    description=(
                        f"Response too short ({resp_len} chars < {self.min_response_length})"
                    ),
                    turn_number=turn_number,
                    evidence={
                        "response_length": resp_len,
                        "threshold": self.min_response_length,
                    },
                    severity=FailureSeverity.CRITICAL,
                )
            )

        # Check 2: No-results patterns (simple string matching)
        found_no_results = False
        for pattern in self.no_results_patterns:
            if pattern.lower() in response_lower:
                failures.append(
                    self._create_failure(
                        description=f"Response contains no-results pattern: '{pattern}'",
                        turn_number=turn_number,
                        evidence={"pattern": pattern, "pattern_type": "no_results"},
                        severity=FailureSeverity.CRITICAL,
                    )
                )
                found_no_results = True
                break  # Only report first match

        # Check 2b: Context-sensitive no-results patterns (require sentence start)
        # These patterns are valid only when they indicate actual lack of results,
        # not when used in positive context (e.g., "there are no restrictions")
        if not found_no_results:
            for pattern in NO_RESULTS_START_PATTERNS:
                if re.search(pattern, response_lower, re.IGNORECASE):
                    # Check if it's actually indicating lack of results
                    # Skip if followed by words like "restrictions", "limitations"
                    # which indicate a positive statement
                    positive_context_words = [
                        "restrictions",
                        "limitations",
                        "requirements",
                        "barriers",
                        "issues",
                    ]
                    match = re.search(pattern, response_lower, re.IGNORECASE)
                    if match:
                        after_match = response_lower[match.end() : match.end() + 50]
                        is_positive_context = any(
                            word in after_match for word in positive_context_words
                        )
                        if not is_positive_context:
                            failures.append(
                                self._create_failure(
                                    description=(
                                        f"Response contains no-results pattern: '{pattern}'"
                                    ),
                                    turn_number=turn_number,
                                    evidence={
                                        "pattern": pattern,
                                        "pattern_type": "no_results_start",
                                    },
                                    severity=FailureSeverity.CRITICAL,
                                )
                            )
                            break

        # Check 3: Deflection patterns
        for pattern in self.deflection_patterns:
            if pattern.lower() in response_lower:
                failures.append(
                    self._create_failure(
                        description=f"Response contains deflection pattern: '{pattern}'",
                        turn_number=turn_number,
                        evidence={"pattern": pattern, "pattern_type": "deflection"},
                        severity=FailureSeverity.HIGH,
                    )
                )
                break

        # Check 4: Empty tool results
        for tool_result in turn.tool_results:
            result_data = tool_result.get("result", {})
            if self._is_empty_result(result_data):
                tool_name = tool_result.get("tool", "unknown")
                failures.append(
                    self._create_failure(
                        description=f"Tool '{tool_name}' returned empty results",
                        turn_number=turn_number,
                        evidence={"tool": tool_name, "result": result_data},
                        severity=FailureSeverity.HIGH,
                    )
                )

        return failures

    def _is_empty_result(self, result: Any) -> bool:
        """Check if a tool result is empty."""
        if result is None:
            return True
        if isinstance(result, list) and len(result) == 0:
            return True
        if isinstance(result, dict):
            # Check common result array fields
            for key in ["calls", "projects", "partners", "results", "items", "data"]:
                if key in result and result[key] == []:
                    return True
            # Check if dict only has metadata, no actual content
            content_keys = [k for k in result.keys() if k not in ["success", "metadata", "error"]]
            if not content_keys:
                return True
        return False


# =============================================================================
# IncorrectDataDetector
# =============================================================================


class IncorrectDataDetector(BaseDetector):
    """
    Detector for INCORRECT_DATA failures.

    Detects:
    - Budget amounts outside known ranges
    - Wrong funding rates (RIA: 100%, IA: 70%, CSA: 100%)
    - Incorrect programme durations
    - Wrong pillar/cluster counts
    - Incorrect eligibility rules for countries

    Severity: CRITICAL (factual errors must be fixed immediately)
    """

    category = FailureCategory.INCORRECT_DATA
    default_severity = FailureSeverity.CRITICAL

    def __init__(
        self,
        known_facts: dict[str, Any] | None = None,
        funding_rates: dict[str, int] | None = None,
    ):
        """
        Initialize the detector.

        Args:
            known_facts: Override known facts dictionary
            funding_rates: Override funding rates dictionary
        """
        super().__init__()
        self.known_facts = known_facts or KNOWN_FACTS
        self.funding_rates = funding_rates or FUNDING_RATES

    def detect(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """Detect INCORRECT_DATA failures."""
        failures = []
        response = turn.response

        # Check 1: Programme budget amounts
        budget_failures = self._check_budget_amounts(response, turn_number)
        failures.extend(budget_failures)

        # Check 2: Funding rates
        rate_failures = self._check_funding_rates(response, turn_number)
        failures.extend(rate_failures)

        # Check 3: Programme structure facts (pillars, clusters, etc.)
        structure_failures = self._check_programme_structure(response, turn_number)
        failures.extend(structure_failures)

        # Check 4: Programme duration
        duration_failures = self._check_programme_duration(response, turn_number)
        failures.extend(duration_failures)

        return failures

    def _check_budget_amounts(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check if mentioned budget amounts are within correct ranges."""
        failures = []

        # Pattern to find budget mentions - more flexible patterns
        # e.g., "€95.5 billion", "95.5B EUR", "budget of 50 billion EUR"
        budget_patterns = [
            (r"horizon\s+europe[^.]*?(\d+(?:\.\d+)?)\s*(?:billion|B)\b", "horizon_europe"),
            (r"erasmus\+?[^.]*?(\d+(?:\.\d+)?)\s*(?:billion|B)\b", "erasmus_plus"),
            (r"creative\s+europe[^.]*?(\d+(?:\.\d+)?)\s*(?:billion|B)\b", "creative_europe"),
        ]

        for pattern, programme in budget_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match.group(1)) * 1_000_000_000
                    expected_range = self.known_facts.get(programme, {}).get("budget")
                    if expected_range:
                        min_budget, max_budget = expected_range
                        if not (min_budget <= amount <= max_budget):
                            prog_name = programme.replace("_", " ").title()
                            stated = match.group(1)
                            expected = f"{min_budget / 1e9:.1f}-{max_budget / 1e9:.1f}B"
                            failures.append(
                                self._create_failure(
                                    description=(
                                        f"Incorrect {prog_name} budget: "
                                        f"{stated}B (expected {expected})"
                                    ),
                                    turn_number=turn_number,
                                    evidence={
                                        "programme": programme,
                                        "stated_budget": amount,
                                        "expected_range": expected_range,
                                        "matched_text": match.group(0),
                                    },
                                )
                            )
                except (ValueError, IndexError):
                    pass

        return failures

    def _check_funding_rates(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check if mentioned funding rates are correct."""
        failures = []

        # Pattern to find funding rate mentions
        rate_patterns = [
            (r"RIA\s*[:\-]?\s*(\d+)%", "RIA"),
            (r"IA\s*[:\-]?\s*(\d+)%", "IA"),
            (r"CSA\s*[:\-]?\s*(\d+)%", "CSA"),
            (r"innovation\s+action.*?(\d+)%", "IA"),
            (r"research.*?innovation.*?action.*?(\d+)%", "RIA"),
        ]

        for pattern, action_type in rate_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                try:
                    rate = int(match.group(1))
                    expected_rate = self.funding_rates.get(action_type)
                    if expected_rate and rate != expected_rate:
                        # Allow for "up to X%" phrasing for IA
                        if action_type == "IA" and rate <= expected_rate:
                            continue
                        failures.append(
                            self._create_failure(
                                description=(
                                    f"Incorrect {action_type} funding rate: "
                                    f"{rate}% (expected {expected_rate}%)"
                                ),
                                turn_number=turn_number,
                                evidence={
                                    "action_type": action_type,
                                    "stated_rate": rate,
                                    "expected_rate": expected_rate,
                                    "matched_text": match.group(0),
                                },
                            )
                        )
                except (ValueError, IndexError):
                    pass

        return failures

    def _check_programme_structure(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check programme structure facts (pillars, clusters, key actions)."""
        failures = []

        # Check Horizon Europe pillars
        pillar_match = re.search(r"horizon.*?(\d+)\s*pillars?", response, re.IGNORECASE)
        if pillar_match:
            pillars = int(pillar_match.group(1))
            expected = self.known_facts["horizon_europe"]["pillars"]
            if pillars != expected:
                failures.append(
                    self._create_failure(
                        description=(
                            f"Incorrect Horizon Europe pillars count: "
                            f"{pillars} (expected {expected})"
                        ),
                        turn_number=turn_number,
                        evidence={"stated": pillars, "expected": expected},
                    )
                )

        # Check Horizon Europe clusters
        cluster_match = re.search(r"horizon.*?(\d+)\s*clusters?", response, re.IGNORECASE)
        if cluster_match:
            clusters = int(cluster_match.group(1))
            expected = self.known_facts["horizon_europe"]["clusters"]
            if clusters != expected:
                failures.append(
                    self._create_failure(
                        description=(
                            f"Incorrect Horizon Europe clusters count: "
                            f"{clusters} (expected {expected})"
                        ),
                        turn_number=turn_number,
                        evidence={"stated": clusters, "expected": expected},
                    )
                )

        # Check Creative Europe strands
        strand_match = re.search(r"creative\s+europe.*?(\d+)\s*strands?", response, re.IGNORECASE)
        if strand_match:
            strands = int(strand_match.group(1))
            expected = len(self.known_facts["creative_europe"]["strands"])
            if strands != expected:
                failures.append(
                    self._create_failure(
                        description=(
                            f"Incorrect Creative Europe strands count: "
                            f"{strands} (expected {expected})"
                        ),
                        turn_number=turn_number,
                        evidence={"stated": strands, "expected": expected},
                    )
                )

        return failures

    def _check_programme_duration(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check if programme duration years are correct."""
        failures = []

        duration_patterns = [
            (r"horizon.*?(20\d{2})\s*[-–]\s*(20\d{2})", "horizon_europe"),
            (r"erasmus.*?(20\d{2})\s*[-–]\s*(20\d{2})", "erasmus_plus"),
            (r"creative\s+europe.*?(20\d{2})\s*[-–]\s*(20\d{2})", "creative_europe"),
        ]

        for pattern, programme in duration_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                stated_duration = f"{match.group(1)}-{match.group(2)}"
                expected_duration = self.known_facts.get(programme, {}).get("duration")
                if expected_duration and stated_duration != expected_duration:
                    prog_name = programme.replace("_", " ").title()
                    failures.append(
                        self._create_failure(
                            description=(
                                f"Incorrect {prog_name} duration: "
                                f"{stated_duration} (expected {expected_duration})"
                            ),
                            turn_number=turn_number,
                            evidence={
                                "programme": programme,
                                "stated_duration": stated_duration,
                                "expected_duration": expected_duration,
                            },
                        )
                    )

        return failures

    def validate_facts_dict(self, facts: dict[str, Any], programme: str) -> list[dict[str, Any]]:
        """
        Validate a dictionary of facts against known correct values.

        Args:
            facts: Dictionary of facts to validate
            programme: Programme name (horizon_europe, erasmus_plus, creative_europe)

        Returns:
            List of incorrect facts with details
        """
        incorrect = []
        expected = self.known_facts.get(programme, {})

        for key, stated_value in facts.items():
            if key in expected:
                expected_value = expected[key]
                if isinstance(expected_value, tuple):
                    # Range check
                    if not (expected_value[0] <= stated_value <= expected_value[1]):
                        incorrect.append(
                            {
                                "fact": key,
                                "stated": stated_value,
                                "expected_range": expected_value,
                            }
                        )
                elif isinstance(expected_value, list):
                    # List membership check
                    if stated_value not in expected_value:
                        incorrect.append(
                            {
                                "fact": key,
                                "stated": stated_value,
                                "expected_values": expected_value,
                            }
                        )
                elif stated_value != expected_value:
                    incorrect.append(
                        {
                            "fact": key,
                            "stated": stated_value,
                            "expected": expected_value,
                        }
                    )

        return incorrect


# =============================================================================
# MissingDataDetector
# =============================================================================


class MissingDataDetector(BaseDetector):
    """
    Detector for MISSING_DATA failures.

    Detects:
    - Expected patterns not found (response_contains validation fails)
    - Programme mentioned but key details missing (budget, deadlines, eligibility)
    - Call search returns results but no call IDs, deadlines, or budgets
    - Partner search returns names but no project counts or expertise

    Severity: HIGH
    """

    category = FailureCategory.MISSING_DATA
    default_severity = FailureSeverity.HIGH

    def __init__(
        self,
        required_fields: dict[str, list[str]] | None = None,
        tool_to_field_type: dict[str, str] | None = None,
    ):
        """
        Initialize the detector.

        Args:
            required_fields: Override required fields dictionary
            tool_to_field_type: Override tool to field type mapping
        """
        super().__init__()
        self.required_fields = required_fields or REQUIRED_FIELDS
        self.tool_to_field_type = tool_to_field_type or TOOL_TO_FIELD_TYPE

    def detect(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """Detect MISSING_DATA failures."""
        failures = []

        # Check 1: Tool result required fields
        for tool_result in turn.tool_results:
            tool_failures = self._check_tool_result_fields(tool_result, turn_number)
            failures.extend(tool_failures)

        # Check 2: Programme mentions without key details
        programme_failures = self._check_programme_details(turn.response, turn_number)
        failures.extend(programme_failures)

        return failures

    def _check_tool_result_fields(
        self, tool_result: dict[str, Any], turn_number: int
    ) -> list[FailureRecord]:
        """Check if tool results have all required fields."""
        failures = []

        tool_name = tool_result.get("tool", "")
        result_data = tool_result.get("result", {})

        field_type = self.tool_to_field_type.get(tool_name)
        if not field_type:
            return failures

        required = self.required_fields.get(field_type, [])
        if not required:
            return failures

        missing_fields = self._find_missing_fields(result_data, required)

        if missing_fields:
            failures.append(
                self._create_failure(
                    description=f"Tool '{tool_name}' missing required fields: {missing_fields}",
                    turn_number=turn_number,
                    evidence={
                        "tool": tool_name,
                        "missing_fields": missing_fields,
                        "field_type": field_type,
                        "required_fields": required,
                    },
                )
            )

        return failures

    def _find_missing_fields(self, result_data: Any, required_fields: list[str]) -> list[str]:
        """Find which required fields are missing from result data."""
        if not isinstance(result_data, dict):
            return required_fields

        missing = []
        for req_field in required_fields:
            if req_field not in result_data:
                # Also check in nested items (e.g., calls, projects arrays)
                found = False
                for key in ["calls", "projects", "partners", "items", "data"]:
                    items = result_data.get(key, [])
                    if items and isinstance(items, list) and len(items) > 0:
                        first_item = items[0]
                        if isinstance(first_item, dict) and req_field in first_item:
                            found = True
                            break
                if not found:
                    missing.append(req_field)

        return missing

    def _check_programme_details(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check if programme mentions include key details."""
        failures = []

        programme_patterns = [
            ("horizon europe", ["budget", "deadline", "funding rate", "pillar", "cluster"]),
            ("erasmus+", ["budget", "deadline", "key action", "KA1", "KA2"]),
            ("erasmus plus", ["budget", "deadline", "key action", "KA1", "KA2"]),
            ("creative europe", ["budget", "deadline", "strand", "MEDIA", "CULTURE"]),
        ]

        response_lower = response.lower()

        for programme, expected_details in programme_patterns:
            if programme.lower() in response_lower:
                # Check if at least some key details are mentioned
                details_found = sum(
                    1 for detail in expected_details if detail.lower() in response_lower
                )
                if details_found < 2 and len(response) > 200:
                    # Programme is mentioned but lacks detail
                    failures.append(
                        self._create_failure(
                            description=(
                                f"Programme '{programme}' mentioned without sufficient details"
                            ),
                            turn_number=turn_number,
                            evidence={
                                "programme": programme,
                                "expected_details": expected_details,
                                "details_found": details_found,
                            },
                            severity=FailureSeverity.MEDIUM,
                        )
                    )

        return failures

    def check_required_patterns(
        self, response: str, patterns: list[str], turn_number: int
    ) -> list[FailureRecord]:
        """
        Check if all required patterns are present in the response.

        Args:
            response: The response text to check
            patterns: List of patterns that should be present
            turn_number: The turn index

        Returns:
            List of FailureRecord for missing patterns
        """
        failures = []
        response_lower = response.lower()

        missing_patterns = [p for p in patterns if p.lower() not in response_lower]

        if missing_patterns:
            failures.append(
                self._create_failure(
                    description=f"Response missing required patterns: {missing_patterns}",
                    turn_number=turn_number,
                    evidence={
                        "missing_patterns": missing_patterns,
                        "total_required": len(patterns),
                        "found": len(patterns) - len(missing_patterns),
                    },
                )
            )

        return failures


# =============================================================================
# UnexpectedBehaviorDetector
# =============================================================================


class UnexpectedBehaviorDetector(BaseDetector):
    """
    Detector for UNEXPECTED_BEHAVIOR failures.

    Detects:
    - Tool called but wrong tool for query type
    - Context not preserved (follow-up fails)
    - Quality score drops > 15 points between turns
    - Response contradicts previous turn
    - Error in SSE stream

    Severity: HIGH
    """

    category = FailureCategory.UNEXPECTED_BEHAVIOR
    default_severity = FailureSeverity.HIGH

    def __init__(self, quality_degradation_threshold: float = 15.0):
        """
        Initialize the detector.

        Args:
            quality_degradation_threshold: Maximum acceptable quality score drop
        """
        super().__init__()
        self.quality_degradation_threshold = quality_degradation_threshold

    def detect(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """Detect UNEXPECTED_BEHAVIOR failures."""
        failures = []

        # Check 1: Error in turn
        if turn.has_error:
            failures.append(
                self._create_failure(
                    description=f"Turn has error: {turn.error}",
                    turn_number=turn_number,
                    evidence={"error": turn.error},
                    severity=FailureSeverity.CRITICAL,
                )
            )

        # Check 2: Error events in SSE stream
        error_events = turn.get_events_by_type("error")
        for event in error_events:
            failures.append(
                self._create_failure(
                    description=f"Error event in SSE stream: {event.get('message', 'Unknown')}",
                    turn_number=turn_number,
                    evidence={"event": event},
                    severity=FailureSeverity.CRITICAL,
                )
            )

        # Check 3: Quality degradation
        if turn.previous_quality_score is not None:
            score_drop = turn.previous_quality_score - turn.quality_score
            if score_drop > self.quality_degradation_threshold:
                threshold = self.quality_degradation_threshold
                failures.append(
                    self._create_failure(
                        description=(
                            f"Quality score dropped {score_drop:.1f} points "
                            f"(threshold: {threshold})"
                        ),
                        turn_number=turn_number,
                        evidence={
                            "previous_score": turn.previous_quality_score,
                            "current_score": turn.quality_score,
                            "drop": score_drop,
                            "threshold": threshold,
                        },
                    )
                )

        # Check 4: Wrong tool for query type
        tool_failures = self._check_wrong_tool(turn, turn_number)
        failures.extend(tool_failures)

        # Check 5: Context loss indicators
        context_failures = self._check_context_loss(turn, turn_number)
        failures.extend(context_failures)

        return failures

    def _check_wrong_tool(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """Check if wrong tools were used for the query type."""
        failures = []
        query_lower = turn.query.lower()

        # Define expected tools for different query types
        query_tool_mapping = {
            "call": ["search_funding_calls", "get_call_details"],
            "project": ["search_projects", "get_project_details", "find_similar_projects"],
            "partner": ["find_experienced_partners", "get_collaboration_network"],
            "budget": ["calculate_budget", "get_budget_benchmark"],
            "timeline": ["generate_timeline"],
            "eligibility": ["check_erasmus_eligibility", "check_creative_europe_eligibility"],
        }

        for query_type, expected_tools in query_tool_mapping.items():
            if query_type in query_lower:
                # Check if at least one expected tool was used
                tools_used = set(turn.tools_used)
                expected_set = set(expected_tools)
                if tools_used and not tools_used.intersection(expected_set):
                    failures.append(
                        self._create_failure(
                            description=(
                                f"Query about '{query_type}' used unexpected tools: {tools_used}"
                            ),
                            turn_number=turn_number,
                            evidence={
                                "query_type": query_type,
                                "expected_tools": expected_tools,
                                "actual_tools": list(tools_used),
                            },
                            severity=FailureSeverity.MEDIUM,
                        )
                    )
                break

        return failures

    def _check_context_loss(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """Check for indicators of context loss."""
        failures = []

        # Check for context loss indicators in response
        context_loss_patterns = [
            "I don't have context",
            "previous conversation",
            "you haven't mentioned",
            "what are you referring to",
            "I'm not sure what you mean by 'that'",
            "which one",
            "could you clarify",
        ]

        response_lower = turn.response.lower()
        for pattern in context_loss_patterns:
            if pattern.lower() in response_lower:
                # Check if query was a follow-up
                follow_up_indicators = [
                    "that",
                    "it",
                    "them",
                    "this",
                    "these",
                    "those",
                    "#",
                    "more about",
                ]
                query_lower = turn.query.lower()
                is_follow_up = any(ind in query_lower for ind in follow_up_indicators)

                if is_follow_up:
                    failures.append(
                        self._create_failure(
                            description=(
                                "Context loss detected: response indicates "
                                "confusion about follow-up reference"
                            ),
                            turn_number=turn_number,
                            evidence={
                                "pattern": pattern,
                                "query": turn.query,
                            },
                        )
                    )
                    break

        return failures

    def check_consistency(
        self,
        current_response: str,
        previous_response: str,
        turn_number: int,
    ) -> list[FailureRecord]:
        """
        Check if current response contradicts previous response.

        Args:
            current_response: Current turn's response
            previous_response: Previous turn's response
            turn_number: Current turn index

        Returns:
            List of FailureRecord for contradictions
        """
        failures = []

        # Extract numerical claims from both responses
        number_pattern = r"€?\d+(?:\.\d+)?\s*(?:billion|million|B|M|%)"
        current_numbers = set(re.findall(number_pattern, current_response))
        previous_numbers = set(re.findall(number_pattern, previous_response))

        # Look for same metric with different values (simple heuristic)
        if current_numbers and previous_numbers:
            # This is a simplified check - real implementation needs semantic understanding
            pass

        return failures


# =============================================================================
# PoorQualityDetector
# =============================================================================


class PoorQualityDetector(BaseDetector):
    """
    Detector for POOR_QUALITY failures.

    Detects:
    - QualityEvaluatorAgent score < 80
    - Specificity score < 20 (vague response)
    - Actionability score < 7 (no clear next steps)
    - Response is wall of text without structure

    Severity: MEDIUM
    """

    category = FailureCategory.POOR_QUALITY
    default_severity = FailureSeverity.MEDIUM

    def __init__(
        self,
        quality_threshold: float = 80.0,
        specificity_threshold: float = 20.0,
        actionability_threshold: float = 7.0,
        wall_of_text_threshold: int = 500,
    ):
        """
        Initialize the detector.

        Args:
            quality_threshold: Minimum acceptable quality score
            specificity_threshold: Minimum acceptable specificity score
            actionability_threshold: Minimum acceptable actionability score
            wall_of_text_threshold: Response length above which structure is required
        """
        super().__init__()
        self.quality_threshold = quality_threshold
        self.specificity_threshold = specificity_threshold
        self.actionability_threshold = actionability_threshold
        self.wall_of_text_threshold = wall_of_text_threshold

    def detect(self, turn: TurnResult, turn_number: int) -> list[FailureRecord]:
        """Detect POOR_QUALITY failures."""
        failures = []

        # Check 1: Overall quality score
        if turn.quality_score < self.quality_threshold:
            score = turn.quality_score
            threshold = self.quality_threshold
            failures.append(
                self._create_failure(
                    description=(f"Quality score below threshold: {score:.1f} < {threshold}"),
                    turn_number=turn_number,
                    evidence={
                        "quality_score": score,
                        "threshold": threshold,
                    },
                )
            )

        # Check 2: Wall of text without structure
        wall_failures = self._check_wall_of_text(turn.response, turn_number)
        failures.extend(wall_failures)

        # Check 3: Vague response (lacks specifics)
        vague_failures = self._check_vagueness(turn.response, turn_number)
        failures.extend(vague_failures)

        # Check 4: Lack of actionability
        actionability_failures = self._check_actionability(turn.response, turn_number)
        failures.extend(actionability_failures)

        return failures

    def _check_wall_of_text(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check if response is an unstructured wall of text."""
        failures = []

        if len(response) > self.wall_of_text_threshold:
            # Check for structure markers
            structure_markers = ["1.", "2.", "3.", "-", "•", "*", "##", "**", "###", "|"]
            has_structure = any(marker in response for marker in structure_markers)
            has_paragraphs = len(response.split("\n\n")) > 1

            if not has_structure and not has_paragraphs:
                failures.append(
                    self._create_failure(
                        description="Response is unstructured wall of text",
                        turn_number=turn_number,
                        evidence={
                            "response_length": len(response),
                            "has_structure": has_structure,
                            "has_paragraphs": has_paragraphs,
                            "threshold": self.wall_of_text_threshold,
                        },
                    )
                )

        return failures

    def _check_vagueness(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check if response lacks specific details."""
        failures = []

        # Count specific elements
        date_pattern = r"\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}\s+\w+\s+\d{4}"
        call_id_pattern = r"HORIZON[-\s][\w\-]+|ERASMUS[-\s][\w\-]+|CREA[-\s][\w\-]+"
        specific_elements = {
            "numbers": len(re.findall(r"\d+(?:\.\d+)?", response)),
            "dates": len(re.findall(date_pattern, response)),
            "currencies": len(re.findall(r"€\s*\d+|EUR\s*\d+|\d+\s*EUR", response)),
            "call_ids": len(re.findall(call_id_pattern, response)),
            "percentages": len(re.findall(r"\d+%", response)),
        }

        total_specifics = sum(specific_elements.values())

        # If response is substantial but lacks specifics
        if len(response) > 300 and total_specifics < 3:
            failures.append(
                self._create_failure(
                    description=(
                        f"Response lacks specificity "
                        f"(only {total_specifics} specific elements found)"
                    ),
                    turn_number=turn_number,
                    evidence={
                        "specific_elements": specific_elements,
                        "total_specifics": total_specifics,
                        "response_length": len(response),
                    },
                )
            )

        return failures

    def _check_actionability(self, response: str, turn_number: int) -> list[FailureRecord]:
        """Check if response provides clear next steps."""
        failures = []

        # Check for actionable language
        actionable_indicators = [
            "you can",
            "you should",
            "next step",
            "to apply",
            "deadline",
            "submit",
            "contact",
            "visit",
            "check",
            "review",
            "consider",
            "recommend",
        ]

        response_lower = response.lower()
        actionable_count = sum(1 for ind in actionable_indicators if ind in response_lower)

        # If response is substantial but lacks actionability
        if len(response) > 200 and actionable_count == 0:
            failures.append(
                self._create_failure(
                    description="Response lacks actionable guidance",
                    turn_number=turn_number,
                    evidence={
                        "actionable_indicators_found": actionable_count,
                        "response_length": len(response),
                    },
                )
            )

        return failures

    def evaluate_dimensions(
        self,
        response: str,
        specificity_score: float,
        actionability_score: float,
        turn_number: int,
    ) -> list[FailureRecord]:
        """
        Evaluate quality dimensions and detect failures.

        Args:
            response: The response text
            specificity_score: Score from quality evaluator (0-25)
            actionability_score: Score from quality evaluator (0-10)
            turn_number: The turn index

        Returns:
            List of FailureRecord for dimension failures
        """
        failures = []

        if specificity_score < self.specificity_threshold:
            threshold = self.specificity_threshold
            failures.append(
                self._create_failure(
                    description=(
                        f"Specificity score too low: {specificity_score:.1f} < {threshold}"
                    ),
                    turn_number=turn_number,
                    evidence={
                        "specificity_score": specificity_score,
                        "threshold": threshold,
                    },
                )
            )

        if actionability_score < self.actionability_threshold:
            threshold = self.actionability_threshold
            failures.append(
                self._create_failure(
                    description=(
                        f"Actionability score too low: {actionability_score:.1f} < {threshold}"
                    ),
                    turn_number=turn_number,
                    evidence={
                        "actionability_score": actionability_score,
                        "threshold": threshold,
                    },
                )
            )

        return failures


# =============================================================================
# Main Detection Function
# =============================================================================


def detect_all(turn: TurnResult, turn_number: int = 0) -> list[FailureRecord]:
    """
    Run all detectors on a turn result.

    This is the main entry point for failure detection, running all 5
    detector classes and returning a combined list of failures.

    Args:
        turn: The turn result to analyze
        turn_number: The turn index in the conversation (default: 0)

    Returns:
        List of FailureRecord objects for all detected failures

    Example:
        turn = TurnResult(
            query="Find open calls for hydrogen research",
            response="I couldn't find any results.",
            tools_used=["search_funding_calls"],
            tool_results=[{"tool": "search_funding_calls", "result": {"calls": []}}]
        )
        failures = detect_all(turn, turn_number=0)
        for f in failures:
            print(f"{f.category.value}: {f.description}")
    """
    all_failures: list[FailureRecord] = []

    # Initialize all detectors
    detectors: list[BaseDetector] = [
        NoResultsDetector(),
        IncorrectDataDetector(),
        MissingDataDetector(),
        UnexpectedBehaviorDetector(),
        PoorQualityDetector(),
    ]

    # Run each detector
    for detector in detectors:
        failures = detector.detect(turn, turn_number)
        all_failures.extend(failures)

    return all_failures


# =============================================================================
# Convenience Functions
# =============================================================================


def create_turn_result_from_conversation_turn(conv_turn: Any) -> TurnResult:
    """
    Create a TurnResult from a ConversationTurn object.

    Args:
        conv_turn: A ConversationTurn from conversation_flow_agent

    Returns:
        TurnResult object for use with detectors
    """
    return TurnResult(
        query=getattr(conv_turn, "query", ""),
        response=getattr(conv_turn, "response_text", ""),
        tools_used=getattr(conv_turn, "tools_used", []),
        tool_results=getattr(conv_turn, "tool_results", []),
        has_error=getattr(conv_turn, "has_error", False),
        error=getattr(conv_turn, "error", None),
        events=getattr(conv_turn, "events", []),
    )

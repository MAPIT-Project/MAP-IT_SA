"""
Personalization Agent for validating context learning and personalization in conversations.

This agent validates how well the system learns user context and personalizes responses:
- Context accumulation validation (profile fields extracted per turn)
- Profile building detection (organization type, sector, country, experience level)
- Personalized recommendation verification (response tailored to profile)
- Preference application checking (filters applied correctly)

Usage:
    agent = PersonalizationAgent()
    agent.add_turn(query, response)
    result = agent.validate_personalization(response, profile)
    accumulation = agent.validate_context_accumulation()
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


# Profile field definitions for EU funding domain
PROFILE_FIELDS = {
    "organization_type": {
        "patterns": [
            (r"\b(university|universities)\b", "university"),
            (r"\b(research (?:institute|organization|centre|center))\b", "research_organization"),
            (r"\bsme\b|\bsmall (?:and )?medium\b|\bstartup\b|\bstart-up\b", "sme"),
            (r"\blarge (?:company|enterprise)\b", "large_enterprise"),
            (r"\b(ngo|non-profit|nonprofit)\b", "ngo"),
            (r"\b(public (?:body|authority|organization))\b", "public_body"),
            (r"\b(museum|cultural (?:organization|institution))\b", "cultural_org"),
            (r"\b(school|college|vet|vocational)\b", "education_institution"),
            (r"\b(film|production company|broadcaster)\b", "media_company"),
            (r"\b(hospital|clinic|healthcare)\b", "healthcare"),
        ],
        "weight": 1.0,
    },
    "sector": {
        "patterns": [
            (r"\b(energy|renewable|hydrogen|solar|wind)\b", "energy"),
            (r"\b(health|medical|clinical|pharma|biotech)\b", "health"),
            (r"\b(digital|ai|artificial intelligence|ml|data|cyber)\b", "digital"),
            (r"\b(climate|environment|sustainability|green)\b", "climate"),
            (r"\b(mobility|transport|automotive|aviation)\b", "mobility"),
            (r"\b(food|agriculture|agri|bio)\b", "food_bio"),
            (r"\b(space|satellite)\b", "space"),
            (r"\b(culture|arts|creative|media)\b", "culture"),
            (r"\b(education|training|learning)\b", "education"),
            (r"\b(marine|ocean|maritime)\b", "marine"),
        ],
        "weight": 0.9,
    },
    "country": {
        "patterns": [
            (r"\b(germany|german|deutschland)\b", "DE"),
            (r"\b(france|french)\b", "FR"),
            (r"\b(spain|spanish)\b", "ES"),
            (r"\b(italy|italian)\b", "IT"),
            (r"\b(netherlands|dutch|holland)\b", "NL"),
            (r"\b(belgium|belgian)\b", "BE"),
            (r"\b(portugal|portuguese)\b", "PT"),
            (r"\b(greece|greek)\b", "GR"),
            (r"\b(poland|polish)\b", "PL"),
            (r"\b(sweden|swedish)\b", "SE"),
            (r"\b(austria|austrian)\b", "AT"),
            (r"\b(switzerland|swiss)\b", "CH"),
            (r"\b(uk|united kingdom|british)\b", "UK"),
            (r"\b(ireland|irish)\b", "IE"),
            (r"\b(denmark|danish)\b", "DK"),
            (r"\b(finland|finnish)\b", "FI"),
            (r"\b(norway|norwegian)\b", "NO"),
            (r"\b(czech|czechia)\b", "CZ"),
            (r"\b(romania|romanian)\b", "RO"),
            (r"\b(hungary|hungarian)\b", "HU"),
            (r"\b(turkey|turkish)\b", "TR"),
            (r"\b(serbia|serbian)\b", "RS"),
        ],
        "weight": 0.8,
    },
    "experience_level": {
        "patterns": [
            (r"\b(first time|never (?:applied|coordinated)|new to|beginner)\b", "newcomer"),
            (r"\b(some experience|few projects|participated before)\b", "intermediate"),
            (r"\b(experienced|many projects|coordinated before|veteran)\b", "experienced"),
            (r"\b(expert|leading|pioneer)\b", "expert"),
        ],
        "weight": 0.7,
    },
    "organization_size": {
        "patterns": [
            (r"\b(\d+)\s*employees?\b", "extract_number"),
            (r"\b(small|micro)\b", "small"),
            (r"\b(medium)\b", "medium"),
            (r"\b(large)\b", "large"),
        ],
        "weight": 0.6,
    },
    "budget_range": {
        "patterns": [
            (r"(?:revenue|turnover|budget).*?(\d+)\s*(?:million|m|M)", "extract_millions"),
            (r"(\d+)\s*(?:million|m|M).*?(?:revenue|turnover|budget)", "extract_millions"),
        ],
        "weight": 0.5,
    },
    "target_programme": {
        "patterns": [
            (r"\b(horizon europe|horizon)\b", "horizon_europe"),
            (r"\b(erasmus\+?|erasmus plus)\b", "erasmus"),
            (r"\b(creative europe)\b", "creative_europe"),
            (r"\b(eic|accelerator|pathfinder)\b", "eic"),
            (r"\b(erc)\b", "erc"),
            (r"\b(msca|marie curie|marie sk)\b", "msca"),
        ],
        "weight": 0.9,
    },
    "role_preference": {
        "patterns": [
            (r"\b(coordinator|coordinating|lead)\b", "coordinator"),
            (r"\b(partner|participating|join)\b", "partner"),
        ],
        "weight": 0.7,
    },
}


@dataclass
class UserProfile:
    """Represents a user profile built from conversation context."""

    organization_type: str | None = None
    sector: str | None = None
    country: str | None = None
    experience_level: str | None = None
    organization_size: str | None = None
    budget_range: str | None = None
    target_programme: str | None = None
    role_preference: str | None = None
    additional_context: dict[str, Any] = field(default_factory=dict)

    def get_filled_fields(self) -> list[str]:
        """Get list of fields that have been filled."""
        fields = []
        for field_name in PROFILE_FIELDS:
            if getattr(self, field_name, None) is not None:
                fields.append(field_name)
        return fields

    def completeness_score(self) -> float:
        """Calculate profile completeness score (0.0 to 1.0)."""
        total_weight = sum(config["weight"] for config in PROFILE_FIELDS.values())
        filled_weight = sum(
            PROFILE_FIELDS[field]["weight"]
            for field in PROFILE_FIELDS
            if getattr(self, field, None) is not None
        )
        return filled_weight / total_weight if total_weight > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "organization_type": self.organization_type,
            "sector": self.sector,
            "country": self.country,
            "experience_level": self.experience_level,
            "organization_size": self.organization_size,
            "budget_range": self.budget_range,
            "target_programme": self.target_programme,
            "role_preference": self.role_preference,
            "additional_context": self.additional_context,
        }


@dataclass
class TurnContext:
    """Context extracted from a single conversation turn."""

    turn_number: int
    query: str
    response: str
    extracted_fields: dict[str, str] = field(default_factory=dict)
    preferences: list[str] = field(default_factory=list)
    mentioned_entities: list[str] = field(default_factory=list)


@dataclass
class PersonalizationResult:
    """Result of personalization validation."""

    passed: bool
    score: float  # 0.0 to 1.0
    profile_fields_used: list[str] = field(default_factory=list)
    expected_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    reasoning: str = ""
    personalization_indicators: list[str] = field(default_factory=list)


@dataclass
class AccumulationResult:
    """Result of context accumulation validation."""

    passed: bool
    total_fields_accumulated: int = 0
    fields_by_turn: dict[int, list[str]] = field(default_factory=dict)
    profile_completeness: float = 0.0
    profile: UserProfile | None = None
    reasoning: str = ""


@dataclass
class ProfileUsageResult:
    """Result of profile usage validation."""

    passed: bool
    fields_used: list[str] = field(default_factory=list)
    expected_fields: list[str] = field(default_factory=list)
    usage_score: float = 0.0
    evidence: dict[str, str] = field(default_factory=dict)
    reasoning: str = ""


class PersonalizationAgent:
    """
    Agent that validates context learning and personalization in conversations.

    Features:
    - Extracts user profile information from conversation turns
    - Tracks context accumulation across the conversation
    - Validates that responses use accumulated profile information
    - Checks that preferences are applied correctly
    - LLM-based evaluation for nuanced validation

    Usage:
        agent = PersonalizationAgent()
        agent.add_turn("I'm from a German SME", "Great! As an SME from Germany...")
        result = agent.validate_personalization(response, expected_fields=["country", "org_type"])
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        use_llm: bool = True,
    ):
        """
        Initialize the personalization agent.

        Args:
            model_name: Gemini model name for LLM-based evaluation
            use_llm: Whether to use LLM for evaluation (falls back to rules)
        """
        self.model_name = model_name
        self.use_llm = use_llm and genai is not None
        self._model = None
        self._profile = UserProfile()
        self._turns: list[TurnContext] = []
        self._preferences: list[str] = []

    def _get_model(self):
        """Get or create the Gemini model."""
        if self._model is None and genai:
            try:
                self._model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                logger.warning(f"Failed to create Gemini model: {e}")
        return self._model

    def reset(self):
        """Reset the agent for a new conversation."""
        self._profile = UserProfile()
        self._turns = []
        self._preferences = []

    # =========================================================================
    # Profile Extraction
    # =========================================================================

    def _extract_field_value(self, text: str, field_name: str) -> str | None:
        """Extract a profile field value from text."""
        text_lower = text.lower()
        config = PROFILE_FIELDS.get(field_name, {})
        patterns = config.get("patterns", [])

        for pattern, value in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                if value == "extract_number":
                    # Extract the numeric value
                    num = int(match.group(1))
                    if num < 10:
                        return "micro"
                    elif num < 50:
                        return "small"
                    elif num < 250:
                        return "medium"
                    else:
                        return "large"
                elif value == "extract_millions":
                    # Extract millions value
                    try:
                        millions = int(match.group(1))
                        return f"{millions}M"
                    except (ValueError, IndexError):
                        return None
                else:
                    return value

        return None

    def _extract_preferences(self, text: str) -> list[str]:
        """Extract user preferences from text."""
        preferences = []
        text_lower = text.lower()

        preference_patterns = [
            (r"prefer\s+(.+?)(?:\.|,|$)", "prefers"),
            (r"(?:don't want|not interested in)\s+(.+?)(?:\.|,|$)", "excludes"),
            (r"only\s+(.+?)(?:\.|,|$)", "requires"),
            (r"at least\s+(.+?)(?:\.|,|$)", "minimum"),
            (r"(?:no more than|maximum)\s+(.+?)(?:\.|,|$)", "maximum"),
            (r"avoid\s+(.+?)(?:\.|,|$)", "avoids"),
        ]

        for pattern, pref_type in preference_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                if match.group(1):
                    preferences.append(f"{pref_type}: {match.group(1).strip()}")

        return preferences

    def add_turn(
        self,
        query: str,
        response: str,
    ) -> TurnContext:
        """
        Add a conversation turn and extract profile information.

        Args:
            query: The user's query
            response: The assistant's response

        Returns:
            TurnContext with extracted information
        """
        turn_number = len(self._turns) + 1
        extracted_fields = {}

        # Extract profile fields from query
        for field_name in PROFILE_FIELDS:
            value = self._extract_field_value(query, field_name)
            if value:
                extracted_fields[field_name] = value
                # Update profile
                setattr(self._profile, field_name, value)

        # Extract preferences
        preferences = self._extract_preferences(query)
        self._preferences.extend(preferences)

        # Create turn context
        turn = TurnContext(
            turn_number=turn_number,
            query=query,
            response=response,
            extracted_fields=extracted_fields,
            preferences=preferences,
        )

        self._turns.append(turn)
        return turn

    def get_profile(self) -> UserProfile:
        """Get the current accumulated profile."""
        return self._profile

    def get_turns(self) -> list[TurnContext]:
        """Get all conversation turns."""
        return self._turns

    # =========================================================================
    # Validation Methods
    # =========================================================================

    async def validate_personalization(
        self,
        response: str,
        profile: UserProfile | None = None,
    ) -> PersonalizationResult:
        """
        Validate that a response is personalized to the user's profile.

        Args:
            response: The response to validate
            profile: Optional profile to use (defaults to accumulated profile)

        Returns:
            PersonalizationResult with validation details
        """
        profile = profile or self._profile
        expected_fields = profile.get_filled_fields()

        if not expected_fields:
            return PersonalizationResult(
                passed=True,
                score=1.0,
                reasoning="No profile fields to personalize against",
            )

        # Try LLM evaluation first
        if self.use_llm:
            result = await self._validate_personalization_llm(response, profile)
            if result is not None:
                return result

        # Fall back to rule-based evaluation
        return self._validate_personalization_rules(response, profile)

    async def _validate_personalization_llm(
        self,
        response: str,
        profile: UserProfile,
    ) -> PersonalizationResult | None:
        """Validate personalization using LLM."""
        model = self._get_model()
        if not model:
            return None

        profile_dict = profile.to_dict()
        filled_fields = profile.get_filled_fields()

        prompt = f"""You are evaluating whether a response is personalized to a user's profile.

USER PROFILE:
{self._format_profile(profile_dict)}

RESPONSE TO EVALUATE:
{response[:2000]}

INSTRUCTIONS:
1. Check if the response acknowledges or uses the user's profile information
2. Look for tailored recommendations based on their organization type, sector, country, etc.
3. Check if the response would be different for a user with a different profile

OUTPUT FORMAT (use exactly this format):
PERSONALIZATION_SCORE: [0.0-1.0]
FIELDS_USED: [comma-separated list of profile fields used in response]
INDICATORS: [evidence of personalization]
REASONING: [brief explanation]

Evaluate now:"""

        try:
            result = model.generate_content(prompt)
            return self._parse_personalization_response(result.text, filled_fields)
        except Exception as e:
            logger.warning(f"LLM personalization validation failed: {e}")
            return None

    def _format_profile(self, profile_dict: dict[str, Any]) -> str:
        """Format profile for prompt."""
        lines = []
        for key, value in profile_dict.items():
            if value and key != "additional_context":
                lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "(no profile information)"

    def _parse_personalization_response(
        self,
        llm_text: str,
        expected_fields: list[str],
    ) -> PersonalizationResult:
        """Parse LLM personalization validation response."""
        score = 0.5
        fields_used = []
        indicators = []
        reasoning = ""

        # Extract score
        score_match = re.search(r"PERSONALIZATION_SCORE:\s*([\d.]+)", llm_text)
        if score_match:
            try:
                score = min(1.0, max(0.0, float(score_match.group(1))))
            except ValueError:
                pass

        # Extract fields used
        fields_match = re.search(r"FIELDS_USED:\s*(.+?)(?:\n|INDICATORS:)", llm_text)
        if fields_match:
            fields_used = [f.strip() for f in fields_match.group(1).split(",") if f.strip()]

        # Extract indicators
        indicators_match = re.search(r"INDICATORS:\s*(.+?)(?:\n|REASONING:)", llm_text)
        if indicators_match:
            indicators = [i.strip() for i in indicators_match.group(1).split(",") if i.strip()]

        # Extract reasoning
        reasoning_match = re.search(r"REASONING:\s*(.+?)$", llm_text, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()[:200]

        missing_fields = [f for f in expected_fields if f not in fields_used]
        passed = score >= 0.5 and len(missing_fields) <= len(expected_fields) // 2

        return PersonalizationResult(
            passed=passed,
            score=score,
            profile_fields_used=fields_used,
            expected_fields=expected_fields,
            missing_fields=missing_fields,
            reasoning=reasoning,
            personalization_indicators=indicators,
        )

    def _validate_personalization_rules(
        self,
        response: str,
        profile: UserProfile,
    ) -> PersonalizationResult:
        """Rule-based personalization validation."""
        response_lower = response.lower()
        expected_fields = profile.get_filled_fields()
        fields_used = []
        indicators = []

        # Check for each profile field in the response
        field_indicators = {
            "organization_type": {
                "university": ["university", "academic", "research institution"],
                "sme": ["sme", "small company", "small business", "startup"],
                "research_organization": ["research organization", "research institute"],
                "ngo": ["ngo", "non-profit", "civil society"],
                "large_enterprise": ["large enterprise", "large company", "corporation"],
            },
            "sector": {
                "energy": ["energy", "renewable", "clean energy", "hydrogen"],
                "health": ["health", "medical", "healthcare", "clinical"],
                "digital": ["digital", "ai", "technology", "data"],
                "climate": ["climate", "environment", "sustainability"],
            },
            "country": {
                "DE": ["germany", "german"],
                "FR": ["france", "french"],
                "ES": ["spain", "spanish"],
                "IT": ["italy", "italian"],
                "NL": ["netherlands", "dutch"],
                "PT": ["portugal", "portuguese"],
                "CH": ["switzerland", "swiss"],
                "UK": ["uk", "united kingdom", "british"],
            },
            "experience_level": {
                "newcomer": ["first time", "new applicant", "beginner"],
                "intermediate": ["some experience", "participated"],
                "experienced": ["experienced", "track record"],
            },
            "role_preference": {
                "coordinator": ["coordinator", "lead", "coordinating"],
                "partner": ["partner", "consortium member", "participate"],
            },
        }

        for field_name in expected_fields:
            value = getattr(profile, field_name, None)
            if value and field_name in field_indicators:
                value_indicators = field_indicators[field_name].get(value, [])
                for indicator in value_indicators:
                    if indicator in response_lower:
                        fields_used.append(field_name)
                        indicators.append(f"{field_name}:{indicator}")
                        break

        # Check for generic personalization indicators
        generic_indicators = [
            ("as a", "acknowledges_profile"),
            ("for your", "tailored_for"),
            ("given your", "considers_context"),
            ("based on your", "uses_profile"),
            ("suitable for", "matching"),
            ("recommend for", "personalized_recommendation"),
            ("your organization", "org_aware"),
            ("in your sector", "sector_aware"),
            ("in your country", "country_aware"),
        ]

        for pattern, indicator_type in generic_indicators:
            if pattern in response_lower:
                indicators.append(indicator_type)

        # Calculate score
        fields_used = list(set(fields_used))
        if expected_fields:
            field_score = len(fields_used) / len(expected_fields)
        else:
            field_score = 1.0

        indicator_score = min(1.0, len(indicators) / 5)
        score = (field_score * 0.6) + (indicator_score * 0.4)

        missing_fields = [f for f in expected_fields if f not in fields_used]
        passed = score >= 0.5

        return PersonalizationResult(
            passed=passed,
            score=score,
            profile_fields_used=fields_used,
            expected_fields=expected_fields,
            missing_fields=missing_fields,
            reasoning=f"Fields matched: {len(fields_used)}/{len(expected_fields)}, "
            f"Indicators found: {len(indicators)}",
            personalization_indicators=indicators,
        )

    def validate_context_accumulation(
        self,
        turns: list[TurnContext] | None = None,
    ) -> AccumulationResult:
        """
        Validate that context accumulates correctly across turns.

        Args:
            turns: Optional list of turns (defaults to accumulated turns)

        Returns:
            AccumulationResult with accumulation details
        """
        turns = turns or self._turns

        if not turns:
            return AccumulationResult(
                passed=True,
                total_fields_accumulated=0,
                reasoning="No turns to analyze",
            )

        fields_by_turn: dict[int, list[str]] = {}
        all_fields_accumulated: set[str] = set()

        for turn in turns:
            turn_fields = list(turn.extracted_fields.keys())
            fields_by_turn[turn.turn_number] = turn_fields
            all_fields_accumulated.update(turn_fields)

        # Check profile completeness
        profile_completeness = self._profile.completeness_score()

        # Validate accumulation pattern
        # Context should generally grow or stay stable, not shrink
        cumulative_fields: set[str] = set()

        for turn in turns:
            cumulative_fields.update(turn.extracted_fields.keys())

        passed = len(all_fields_accumulated) > 0 or len(turns) <= 1

        return AccumulationResult(
            passed=passed,
            total_fields_accumulated=len(all_fields_accumulated),
            fields_by_turn=fields_by_turn,
            profile_completeness=profile_completeness,
            profile=self._profile,
            reasoning=f"Accumulated {len(all_fields_accumulated)} fields over {len(turns)} turns",
        )

    def validate_profile_usage(
        self,
        response: str,
        expected_fields: list[str] | None = None,
    ) -> ProfileUsageResult:
        """
        Validate that expected profile fields are used in the response.

        Args:
            response: The response to validate
            expected_fields: List of profile fields that should be used

        Returns:
            ProfileUsageResult with usage details
        """
        if expected_fields is None:
            expected_fields = self._profile.get_filled_fields()

        if not expected_fields:
            return ProfileUsageResult(
                passed=True,
                usage_score=1.0,
                reasoning="No fields expected",
            )

        response_lower = response.lower()
        fields_used = []
        evidence: dict[str, str] = {}

        for field_name in expected_fields:
            value = getattr(self._profile, field_name, None)
            if value:
                # Check if the field value is referenced in response
                if self._field_value_in_response(field_name, value, response_lower):
                    fields_used.append(field_name)
                    evidence[field_name] = value

        usage_score = len(fields_used) / len(expected_fields) if expected_fields else 1.0
        passed = usage_score >= 0.5

        return ProfileUsageResult(
            passed=passed,
            fields_used=fields_used,
            expected_fields=expected_fields,
            usage_score=usage_score,
            evidence=evidence,
            reasoning=f"Used {len(fields_used)}/{len(expected_fields)} expected fields",
        )

    def _field_value_in_response(
        self,
        field: str,
        value: str,
        response_lower: str,
    ) -> bool:
        """Check if a field value is referenced in the response."""
        if value.lower() in response_lower:
            return True

        # Check for common variations
        value_variations = {
            "university": ["academic", "universities", "higher education"],
            "sme": ["small company", "startup", "small business"],
            "DE": ["germany", "german"],
            "FR": ["france", "french"],
            "energy": ["clean energy", "renewable", "power"],
            "health": ["healthcare", "medical", "clinical"],
            "newcomer": ["first time", "new to"],
            "experienced": ["track record", "previous projects"],
        }

        variations = value_variations.get(value, [])
        return any(var in response_lower for var in variations)

    # =========================================================================
    # Integration with ContextValidatorAgent
    # =========================================================================

    def get_accumulated_profile_dict(self) -> dict[str, Any]:
        """
        Get the accumulated profile as a dictionary for integration.

        Can be used with ContextValidatorAgent for full validation.
        """
        return self._profile.to_dict()

    def get_context_summary(self) -> dict[str, Any]:
        """
        Get a summary of all accumulated context for validation.

        Returns:
            Dictionary with profile, preferences, and turn summaries
        """
        return {
            "profile": self._profile.to_dict(),
            "preferences": self._preferences,
            "turns_analyzed": len(self._turns),
            "fields_accumulated": self._profile.get_filled_fields(),
            "profile_completeness": self._profile.completeness_score(),
        }

    # =========================================================================
    # Validation Helper Methods (for scenario testing)
    # =========================================================================

    async def validate_personalization_applied(
        self,
        response: str,
        min_score: float = 0.5,
    ) -> bool:
        """
        Validate that personalization is applied (for scenario testing).

        Args:
            response: Response to validate
            min_score: Minimum personalization score required

        Returns:
            True if personalization score >= min_score
        """
        result = await self.validate_personalization(response)
        return result.score >= min_score

    def validate_context_accumulated(
        self,
        min_fields: int = 1,
    ) -> bool:
        """
        Validate that context has accumulated (for scenario testing).

        Args:
            min_fields: Minimum number of profile fields expected

        Returns:
            True if accumulated fields >= min_fields
        """
        result = self.validate_context_accumulation()
        return result.total_fields_accumulated >= min_fields

    def validate_profile_used(
        self,
        response: str,
        expected_fields: list[str] | None = None,
        min_usage: float = 0.5,
    ) -> bool:
        """
        Validate that profile is used in response (for scenario testing).

        Args:
            response: Response to validate
            expected_fields: Fields that should be used
            min_usage: Minimum usage score required

        Returns:
            True if usage score >= min_usage
        """
        result = self.validate_profile_usage(response, expected_fields)
        return result.usage_score >= min_usage

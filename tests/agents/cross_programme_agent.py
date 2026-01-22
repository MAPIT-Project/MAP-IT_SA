"""
Cross-Programme Agent for validating multi-programme navigation and accuracy.

This agent validates cross-programme conversation handling:
- Multi-programme mention detection (Horizon Europe, Erasmus+, Creative Europe)
- Programme switching validation (context preserved across programme changes)
- Comparison accuracy checking (correct facts for each programme)
- Eligibility rule verification across programmes

Usage:
    agent = CrossProgrammeAgent()
    mentions = agent.check_programme_mentions(response)
    accuracy = await agent.validate_programme_facts(response, "horizon_europe")
    eligibility = await agent.validate_eligibility_rules(response, context)
"""

# isort: skip_file
import logging
import re
from dataclasses import dataclass, field
from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


# Programme definitions with key facts for validation
PROGRAMME_FACTS = {
    "horizon_europe": {
        "name": "Horizon Europe",
        "aliases": [
            "horizon europe",
            "horizon",
            "he",
            "h2020 successor",
            "framework programme",
        ],
        "budget": "€95.5 billion",
        "budget_range": (90, 100),  # billion EUR for validation
        "duration": "2021-2027",
        "pillars": ["Excellent Science", "Global Challenges", "Innovative Europe"],
        "clusters": [
            "Health",
            "Culture, Creativity",
            "Civil Security",
            "Digital, Industry, Space",
            "Climate, Energy, Mobility",
            "Food, Bioeconomy",
        ],
        "action_types": ["RIA", "IA", "CSA", "ERC", "EIC", "MSCA"],
        "funding_rates": {
            "RIA": 100,
            "IA": 70,
            "CSA": 100,
            "ERC": 100,
            "MSCA": 100,
        },
        "key_components": [
            "ERC",
            "MSCA",
            "EIC",
            "EIT",
            "Research Infrastructures",
            "Widening Participation",
        ],
        "minimum_consortium": 3,
        "coordinator_requirements": "Must be from EU member state or associated country",
    },
    "erasmus_plus": {
        "name": "Erasmus+",
        "aliases": [
            "erasmus+",
            "erasmus plus",
            "erasmus",
            "e+",
        ],
        "budget": "€26.2 billion",
        "budget_range": (24, 28),  # billion EUR for validation
        "duration": "2021-2027",
        "key_actions": [
            "KA1 - Learning Mobility",
            "KA2 - Cooperation Partnerships",
            "KA3 - Policy Support",
        ],
        "sectors": [
            "Higher Education",
            "VET",
            "Schools",
            "Adult Education",
            "Youth",
            "Sport",
        ],
        "funding_model": "Lump sum / Unit costs",
        "key_components": [
            "Student mobility",
            "Staff mobility",
            "Strategic partnerships",
            "Jean Monnet",
            "Sport actions",
        ],
        "accreditation": "Erasmus accreditation available for simplified access",
    },
    "creative_europe": {
        "name": "Creative Europe",
        "aliases": [
            "creative europe",
            "ce",
            "creative europe programme",
        ],
        "budget": "€2.44 billion",
        "budget_range": (2, 3),  # billion EUR for validation
        "duration": "2021-2027",
        "strands": [
            "CULTURE",
            "MEDIA",
            "CROSS-SECTORAL",
        ],
        "culture_actions": [
            "European Cooperation Projects",
            "European Networks",
            "European Platforms",
            "Literary Translation",
        ],
        "media_actions": [
            "Development",
            "Distribution",
            "Training",
            "Festivals",
            "Cinema Networks",
        ],
        "funding_rates": {
            "small_cooperation": 80,
            "medium_cooperation": 70,
            "large_cooperation": 60,
        },
        "key_components": [
            "Cultural cooperation",
            "Audiovisual sector support",
            "News media support",
        ],
    },
}


# Eligibility rules by country status
COUNTRY_ELIGIBILITY = {
    "eu_member_states": {
        "countries": [
            "AT",
            "BE",
            "BG",
            "HR",
            "CY",
            "CZ",
            "DK",
            "EE",
            "FI",
            "FR",
            "DE",
            "GR",
            "HU",
            "IE",
            "IT",
            "LV",
            "LT",
            "LU",
            "MT",
            "NL",
            "PL",
            "PT",
            "RO",
            "SK",
            "SI",
            "ES",
            "SE",
        ],
        "horizon_europe": {"coordinator": True, "partner": True, "full_funding": True},
        "erasmus_plus": {"coordinator": True, "partner": True, "full_funding": True},
        "creative_europe": {"coordinator": True, "partner": True, "full_funding": True},
    },
    "associated_countries": {
        "countries": [
            "NO",
            "IS",
            "LI",
            "IL",
            "TR",
            "UA",
            "MD",
            "GE",
            "AM",
            "RS",
            "ME",
            "MK",
            "AL",
            "BA",
            "XK",
        ],
        "horizon_europe": {"coordinator": True, "partner": True, "full_funding": True},
        "erasmus_plus": {"coordinator": True, "partner": True, "full_funding": True},
        "creative_europe": {"coordinator": True, "partner": True, "full_funding": True},
    },
    "special_cases": {
        "CH": {  # Switzerland
            "horizon_europe": {
                "coordinator": False,
                "partner": True,
                "full_funding": False,
                "notes": "Non-associated third country since 2021",
            },
            "erasmus_plus": {"coordinator": True, "partner": True, "full_funding": True},
            "creative_europe": {"coordinator": True, "partner": True, "full_funding": True},
        },
        "UK": {  # United Kingdom
            "horizon_europe": {
                "coordinator": False,
                "partner": True,
                "full_funding": True,
                "notes": "Associated country since 2024",
            },
            "erasmus_plus": {
                "coordinator": False,
                "partner": False,
                "full_funding": False,
                "notes": "Not participating in Erasmus+",
            },
            "creative_europe": {"coordinator": True, "partner": True, "full_funding": True},
        },
    },
    "third_countries": {
        "horizon_europe": {
            "coordinator": False,
            "partner": True,
            "full_funding": False,
            "notes": "Participation possible but typically no EU funding",
        },
        "erasmus_plus": {
            "coordinator": False,
            "partner": True,
            "full_funding": False,
            "notes": "Limited participation as partner countries",
        },
        "creative_europe": {
            "coordinator": False,
            "partner": True,
            "full_funding": False,
            "notes": "Participation possible for some actions",
        },
    },
}


@dataclass
class ProgrammeMention:
    """Represents a programme mention found in text."""

    programme: str
    programme_name: str
    mention_text: str
    position: int
    confidence: float = 1.0


@dataclass
class ProgrammeMentionResult:
    """Result of programme mention detection."""

    programmes_found: list[str] = field(default_factory=list)
    programme_names: list[str] = field(default_factory=list)
    mentions: list[ProgrammeMention] = field(default_factory=list)
    total_mentions: int = 0
    is_multi_programme: bool = False


@dataclass
class ProgrammeFactsResult:
    """Result of programme facts validation."""

    passed: bool
    score: float  # 0.0 to 1.0
    programme: str
    facts_checked: list[str] = field(default_factory=list)
    facts_correct: list[str] = field(default_factory=list)
    facts_incorrect: list[str] = field(default_factory=list)
    facts_missing: list[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class EligibilityResult:
    """Result of eligibility validation."""

    passed: bool
    score: float  # 0.0 to 1.0
    country: str | None = None
    programme: str | None = None
    rules_checked: list[str] = field(default_factory=list)
    rules_correct: list[str] = field(default_factory=list)
    rules_incorrect: list[str] = field(default_factory=list)
    eligibility_summary: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class ProgrammeSwitchResult:
    """Result of programme switching validation."""

    passed: bool
    programmes_mentioned: list[str] = field(default_factory=list)
    context_preserved: bool = True
    switch_count: int = 0
    reasoning: str = ""


class CrossProgrammeAgent:
    """
    Agent that validates cross-programme navigation and accuracy.

    Features:
    - Detects mentions of multiple EU programmes in responses
    - Validates programme-specific facts are accurate
    - Checks eligibility rules across programmes
    - Validates context preservation during programme switches
    - LLM-based evaluation for nuanced validation

    Usage:
        agent = CrossProgrammeAgent()
        mentions = agent.check_programme_mentions(response)
        accuracy = await agent.validate_programme_facts(response, "horizon_europe")
        eligibility = await agent.validate_eligibility_rules(response, {"country": "CH"})
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        use_llm: bool = True,
    ):
        """
        Initialize the cross-programme agent.

        Args:
            model_name: Gemini model name for LLM-based evaluation
            use_llm: Whether to use LLM for evaluation (falls back to rules)
        """
        self.model_name = model_name
        self.use_llm = use_llm and genai is not None
        self._model = None
        self._conversation_programmes: list[str] = []

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
        self._conversation_programmes = []

    # =========================================================================
    # Programme Mention Detection
    # =========================================================================

    def check_programme_mentions(
        self,
        response: str,
    ) -> ProgrammeMentionResult:
        """
        Check which EU funding programmes are mentioned in a response.

        Args:
            response: The response text to analyze

        Returns:
            ProgrammeMentionResult with found programmes and details
        """
        response_lower = response.lower()
        mentions: list[ProgrammeMention] = []
        programmes_found: set[str] = set()

        for programme_key, facts in PROGRAMME_FACTS.items():
            programme_name = facts["name"]
            aliases = facts["aliases"]

            for alias in aliases:
                # Find all occurrences
                pattern = r"\b" + re.escape(alias) + r"\b"
                for match in re.finditer(pattern, response_lower, re.IGNORECASE):
                    mention = ProgrammeMention(
                        programme=programme_key,
                        programme_name=programme_name,
                        mention_text=match.group(),
                        position=match.start(),
                        confidence=1.0 if alias == programme_name.lower() else 0.9,
                    )
                    mentions.append(mention)
                    programmes_found.add(programme_key)

        # Sort mentions by position
        mentions.sort(key=lambda m: m.position)

        # Get unique programme names
        programme_names = [PROGRAMME_FACTS[p]["name"] for p in programmes_found]

        # Track for conversation
        for p in programmes_found:
            if p not in self._conversation_programmes:
                self._conversation_programmes.append(p)

        return ProgrammeMentionResult(
            programmes_found=list(programmes_found),
            programme_names=programme_names,
            mentions=mentions,
            total_mentions=len(mentions),
            is_multi_programme=len(programmes_found) > 1,
        )

    # =========================================================================
    # Programme Facts Validation
    # =========================================================================

    async def validate_programme_facts(
        self,
        response: str,
        programme: str,
    ) -> ProgrammeFactsResult:
        """
        Validate that programme-specific facts in a response are accurate.

        Args:
            response: The response to validate
            programme: The programme to validate facts for

        Returns:
            ProgrammeFactsResult with validation details
        """
        if programme not in PROGRAMME_FACTS:
            return ProgrammeFactsResult(
                passed=False,
                score=0.0,
                programme=programme,
                reasoning=f"Unknown programme: {programme}",
            )

        # Try LLM evaluation first
        if self.use_llm:
            result = await self._validate_facts_llm(response, programme)
            if result is not None:
                return result

        # Fall back to rule-based evaluation
        return self._validate_facts_rules(response, programme)

    async def _validate_facts_llm(
        self,
        response: str,
        programme: str,
    ) -> ProgrammeFactsResult | None:
        """Validate programme facts using LLM."""
        model = self._get_model()
        if not model:
            return None

        facts = PROGRAMME_FACTS[programme]

        prompt = f"""You are validating the accuracy of EU funding programme information.

PROGRAMME: {facts["name"]}
KNOWN FACTS:
- Budget: {facts["budget"]}
- Duration: {facts["duration"]}
- Key components: {", ".join(facts.get("key_components", [])[:5])}
- Action types/strands: {", ".join(facts.get("action_types", facts.get("strands", []))[:5])}

RESPONSE TO VALIDATE:
{response[:2500]}

INSTRUCTIONS:
1. Check if any facts about {facts["name"]} in the response are incorrect
2. Identify facts that are correctly stated
3. Note any important facts that should have been mentioned but weren't

OUTPUT FORMAT (use exactly this format):
ACCURACY_SCORE: [0.0-1.0]
FACTS_CORRECT: [comma-separated list of correct facts found]
FACTS_INCORRECT: [comma-separated list of incorrect facts found, or "none"]
FACTS_MISSING: [important facts that should be mentioned, or "none"]
REASONING: [brief explanation]

Validate now:"""

        try:
            result = model.generate_content(prompt)
            return self._parse_facts_response(result.text, programme)
        except Exception as e:
            logger.warning(f"LLM facts validation failed: {e}")
            return None

    def _parse_facts_response(
        self,
        llm_text: str,
        programme: str,
    ) -> ProgrammeFactsResult:
        """Parse LLM facts validation response."""
        score = 0.5
        facts_correct = []
        facts_incorrect = []
        facts_missing = []
        reasoning = ""

        # Extract score
        score_match = re.search(r"ACCURACY_SCORE:\s*([\d.]+)", llm_text)
        if score_match:
            try:
                score = min(1.0, max(0.0, float(score_match.group(1))))
            except ValueError:
                pass

        # Extract correct facts
        correct_match = re.search(r"FACTS_CORRECT:\s*(.+?)(?:\n|FACTS_INCORRECT:)", llm_text)
        if correct_match:
            text = correct_match.group(1).strip()
            if text.lower() != "none":
                facts_correct = [f.strip() for f in text.split(",") if f.strip()]

        # Extract incorrect facts
        incorrect_match = re.search(r"FACTS_INCORRECT:\s*(.+?)(?:\n|FACTS_MISSING:)", llm_text)
        if incorrect_match:
            text = incorrect_match.group(1).strip()
            if text.lower() != "none":
                facts_incorrect = [f.strip() for f in text.split(",") if f.strip()]

        # Extract missing facts
        missing_match = re.search(r"FACTS_MISSING:\s*(.+?)(?:\n|REASONING:)", llm_text)
        if missing_match:
            text = missing_match.group(1).strip()
            if text.lower() != "none":
                facts_missing = [f.strip() for f in text.split(",") if f.strip()]

        # Extract reasoning
        reasoning_match = re.search(r"REASONING:\s*(.+?)$", llm_text, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()[:200]

        passed = score >= 0.7 and len(facts_incorrect) == 0

        return ProgrammeFactsResult(
            passed=passed,
            score=score,
            programme=programme,
            facts_checked=facts_correct + facts_incorrect,
            facts_correct=facts_correct,
            facts_incorrect=facts_incorrect,
            facts_missing=facts_missing,
            reasoning=reasoning,
        )

    def _validate_facts_rules(
        self,
        response: str,
        programme: str,
    ) -> ProgrammeFactsResult:
        """Rule-based programme facts validation."""
        facts = PROGRAMME_FACTS[programme]
        response_lower = response.lower()

        facts_checked = []
        facts_correct = []
        facts_incorrect = []

        # Check budget mentions
        budget_patterns = [
            (r"€\s*(\d+(?:\.\d+)?)\s*billion", "budget"),
            (r"(\d+(?:\.\d+)?)\s*billion\s*(?:euro|EUR|€)", "budget"),
        ]

        for pattern, _fact_type in budget_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                facts_checked.append("budget")
                try:
                    amount = float(match.group(1))
                    budget_min, budget_max = facts["budget_range"]
                    if budget_min <= amount <= budget_max:
                        facts_correct.append(f"budget: €{amount}B")
                    else:
                        facts_incorrect.append(
                            f"budget: stated €{amount}B but should be ~{facts['budget']}"
                        )
                except ValueError:
                    pass
                break

        # Check programme name is correct
        if facts["name"].lower() in response_lower:
            facts_checked.append("programme_name")
            facts_correct.append("programme_name")

        # Check for key components mentioned
        key_components = facts.get("key_components", [])
        components_found = [comp for comp in key_components if comp.lower() in response_lower]
        if components_found:
            facts_checked.append("key_components")
            facts_correct.append(f"components: {', '.join(components_found[:3])}")

        # Check action types/strands
        action_types = facts.get("action_types", facts.get("strands", []))
        types_found = [at for at in action_types if at.lower() in response_lower]
        if types_found:
            facts_checked.append("action_types")
            facts_correct.append(f"action_types: {', '.join(types_found[:3])}")

        # Check funding rates if mentioned
        if "funding_rates" in facts:
            for action, rate in facts["funding_rates"].items():
                rate_pattern = rf"{action}.*?(\d+)\s*%"
                match = re.search(rate_pattern, response, re.IGNORECASE)
                if match:
                    facts_checked.append(f"funding_rate_{action}")
                    stated_rate = int(match.group(1))
                    if stated_rate == rate:
                        facts_correct.append(f"{action}_rate: {rate}%")
                    else:
                        facts_incorrect.append(
                            f"{action}_rate: stated {stated_rate}% but should be {rate}%"
                        )

        # Calculate score
        if facts_checked:
            score = len(facts_correct) / len(facts_checked)
        else:
            # No specific facts to check - assume correct if programme mentioned
            score = 0.8 if facts["name"].lower() in response_lower else 0.5

        passed = score >= 0.7 and len(facts_incorrect) == 0

        return ProgrammeFactsResult(
            passed=passed,
            score=score,
            programme=programme,
            facts_checked=facts_checked,
            facts_correct=facts_correct,
            facts_incorrect=facts_incorrect,
            facts_missing=[],
            reasoning=f"Checked {len(facts_checked)} facts, "
            f"{len(facts_correct)} correct, {len(facts_incorrect)} incorrect",
        )

    # =========================================================================
    # Eligibility Rules Validation
    # =========================================================================

    async def validate_eligibility_rules(
        self,
        response: str,
        context: dict[str, Any],
    ) -> EligibilityResult:
        """
        Validate eligibility information in a response.

        Args:
            response: The response to validate
            context: Context including country, programme, organization_type

        Returns:
            EligibilityResult with validation details
        """
        country = context.get("country")
        programme = context.get("programme")

        # Try LLM evaluation first
        if self.use_llm:
            result = await self._validate_eligibility_llm(response, context)
            if result is not None:
                return result

        # Fall back to rule-based evaluation
        return self._validate_eligibility_rules(response, country, programme)

    async def _validate_eligibility_llm(
        self,
        response: str,
        context: dict[str, Any],
    ) -> EligibilityResult | None:
        """Validate eligibility using LLM."""
        model = self._get_model()
        if not model:
            return None

        country = context.get("country", "unknown")
        programme = context.get("programme", "all programmes")

        # Get expected eligibility
        expected = self._get_expected_eligibility(country, programme)

        prompt = f"""You are validating eligibility information for EU funding programmes.

CONTEXT:
- Country: {country}
- Programme: {programme}

EXPECTED ELIGIBILITY RULES:
{self._format_eligibility_rules(expected)}

RESPONSE TO VALIDATE:
{response[:2500]}

INSTRUCTIONS:
1. Check if the eligibility statements in the response are accurate
2. Verify coordinator/partner eligibility is correctly stated
3. Check if funding eligibility is correctly explained
4. Note any incorrect or misleading eligibility information

OUTPUT FORMAT (use exactly this format):
ELIGIBILITY_SCORE: [0.0-1.0]
RULES_CORRECT: [comma-separated list of correctly stated rules]
RULES_INCORRECT: [comma-separated list of incorrect rules, or "none"]
REASONING: [brief explanation]

Validate now:"""

        try:
            result = model.generate_content(prompt)
            return self._parse_eligibility_response(result.text, country, programme)
        except Exception as e:
            logger.warning(f"LLM eligibility validation failed: {e}")
            return None

    def _format_eligibility_rules(self, rules: dict[str, Any]) -> str:
        """Format eligibility rules for prompt."""
        lines = []
        for key, value in rules.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"- {key}.{k}: {v}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "(no specific rules)"

    def _get_expected_eligibility(
        self,
        country: str | None,
        programme: str | None,
    ) -> dict[str, Any]:
        """Get expected eligibility rules for a country/programme."""
        result = {}

        if not country:
            return result

        country_upper = country.upper()

        # Check special cases first
        if country_upper in COUNTRY_ELIGIBILITY["special_cases"]:
            special = COUNTRY_ELIGIBILITY["special_cases"][country_upper]
            if programme and programme in special:
                result = special[programme].copy()
            else:
                result = special.copy()
            return result

        # Check EU member states
        if country_upper in COUNTRY_ELIGIBILITY["eu_member_states"]["countries"]:
            if programme:
                result = COUNTRY_ELIGIBILITY["eu_member_states"].get(programme, {}).copy()
            else:
                result = {"status": "EU member state", "full_eligibility": True}
            return result

        # Check associated countries
        if country_upper in COUNTRY_ELIGIBILITY["associated_countries"]["countries"]:
            if programme:
                result = COUNTRY_ELIGIBILITY["associated_countries"].get(programme, {}).copy()
            else:
                result = {"status": "Associated country", "full_eligibility": True}
            return result

        # Default to third country
        if programme:
            result = COUNTRY_ELIGIBILITY["third_countries"].get(programme, {}).copy()
        else:
            result = {"status": "Third country", "limited_eligibility": True}

        return result

    def _parse_eligibility_response(
        self,
        llm_text: str,
        country: str | None,
        programme: str | None,
    ) -> EligibilityResult:
        """Parse LLM eligibility validation response."""
        score = 0.5
        rules_correct = []
        rules_incorrect = []
        reasoning = ""

        # Extract score
        score_match = re.search(r"ELIGIBILITY_SCORE:\s*([\d.]+)", llm_text)
        if score_match:
            try:
                score = min(1.0, max(0.0, float(score_match.group(1))))
            except ValueError:
                pass

        # Extract correct rules
        correct_match = re.search(r"RULES_CORRECT:\s*(.+?)(?:\n|RULES_INCORRECT:)", llm_text)
        if correct_match:
            text = correct_match.group(1).strip()
            if text.lower() != "none":
                rules_correct = [r.strip() for r in text.split(",") if r.strip()]

        # Extract incorrect rules
        incorrect_match = re.search(r"RULES_INCORRECT:\s*(.+?)(?:\n|REASONING:)", llm_text)
        if incorrect_match:
            text = incorrect_match.group(1).strip()
            if text.lower() != "none":
                rules_incorrect = [r.strip() for r in text.split(",") if r.strip()]

        # Extract reasoning
        reasoning_match = re.search(r"REASONING:\s*(.+?)$", llm_text, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()[:200]

        passed = score >= 0.7 and len(rules_incorrect) == 0

        return EligibilityResult(
            passed=passed,
            score=score,
            country=country,
            programme=programme,
            rules_checked=rules_correct + rules_incorrect,
            rules_correct=rules_correct,
            rules_incorrect=rules_incorrect,
            eligibility_summary=self._get_expected_eligibility(country, programme),
            reasoning=reasoning,
        )

    def _validate_eligibility_rules(
        self,
        response: str,
        country: str | None,
        programme: str | None,
    ) -> EligibilityResult:
        """Rule-based eligibility validation."""
        response_lower = response.lower()
        rules_checked = []
        rules_correct = []
        rules_incorrect = []

        expected = self._get_expected_eligibility(country, programme)

        if not country:
            return EligibilityResult(
                passed=True,
                score=1.0,
                reasoning="No country specified for eligibility check",
            )

        # Check coordinator eligibility
        if "coordinator" in expected:
            rules_checked.append("coordinator_eligibility")
            can_coordinate = expected["coordinator"]

            coord_patterns = [
                (r"can\s+(?:be\s+)?coordinat", True),
                (r"cannot\s+(?:be\s+)?coordinat", False),
                (r"eligible\s+(?:to\s+)?coordinat", True),
                (r"not\s+eligible\s+(?:to\s+)?coordinat", False),
            ]

            for pattern, stated_can in coord_patterns:
                if re.search(pattern, response_lower):
                    if stated_can == can_coordinate:
                        rules_correct.append("coordinator_eligibility")
                    else:
                        rules_incorrect.append(
                            f"coordinator: stated {'can' if stated_can else 'cannot'} "
                            f"but should be {'can' if can_coordinate else 'cannot'}"
                        )
                    break

        # Check partner eligibility
        if "partner" in expected:
            rules_checked.append("partner_eligibility")
            can_partner = expected["partner"]

            partner_patterns = [
                (r"can\s+(?:be\s+)?(?:a\s+)?partner", True),
                (r"cannot\s+(?:be\s+)?(?:a\s+)?partner", False),
                (r"eligible\s+(?:as\s+)?(?:a\s+)?partner", True),
                (r"not\s+eligible\s+(?:as\s+)?(?:a\s+)?partner", False),
                (r"can\s+participate", True),
                (r"cannot\s+participate", False),
            ]

            for pattern, stated_can in partner_patterns:
                if re.search(pattern, response_lower):
                    if stated_can == can_partner:
                        rules_correct.append("partner_eligibility")
                    else:
                        rules_incorrect.append(
                            f"partner: stated {'can' if stated_can else 'cannot'} "
                            f"but should be {'can' if can_partner else 'cannot'}"
                        )
                    break

        # Check funding eligibility
        if "full_funding" in expected:
            rules_checked.append("funding_eligibility")
            has_funding = expected["full_funding"]

            funding_patterns = [
                (r"(?:full|eu)\s+funding", True),
                (r"no\s+(?:eu\s+)?funding", False),
                (r"self-fund", False),
                (r"must\s+fund\s+themselves", False),
            ]

            for pattern, stated_has in funding_patterns:
                if re.search(pattern, response_lower):
                    if stated_has == has_funding:
                        rules_correct.append("funding_eligibility")
                    else:
                        rules_incorrect.append(
                            f"funding: stated {'has' if stated_has else 'no'} funding "
                            f"but should be {'has' if has_funding else 'no'} funding"
                        )
                    break

        # Calculate score
        if rules_checked:
            score = len(rules_correct) / len(rules_checked)
        else:
            score = 0.8  # Default if no specific rules to check

        passed = score >= 0.7 and len(rules_incorrect) == 0

        return EligibilityResult(
            passed=passed,
            score=score,
            country=country,
            programme=programme,
            rules_checked=rules_checked,
            rules_correct=rules_correct,
            rules_incorrect=rules_incorrect,
            eligibility_summary=expected,
            reasoning=f"Checked {len(rules_checked)} rules, "
            f"{len(rules_correct)} correct, {len(rules_incorrect)} incorrect",
        )

    # =========================================================================
    # Programme Switching Validation
    # =========================================================================

    def validate_programme_switch(
        self,
        previous_response: str,
        current_response: str,
        previous_context: dict[str, Any],
    ) -> ProgrammeSwitchResult:
        """
        Validate that context is preserved when switching between programmes.

        Args:
            previous_response: The previous response in the conversation
            current_response: The current response to validate
            previous_context: Context from previous turn

        Returns:
            ProgrammeSwitchResult with validation details
        """
        # Check programmes in both responses
        prev_mentions = self.check_programme_mentions(previous_response)
        curr_mentions = self.check_programme_mentions(current_response)

        # Identify programme switch
        prev_programmes = set(prev_mentions.programmes_found)
        curr_programmes = set(curr_mentions.programmes_found)

        all_programmes = prev_programmes.union(curr_programmes)
        is_switch = (
            len(prev_programmes) > 0
            and len(curr_programmes) > 0
            and prev_programmes != curr_programmes
        )

        # Check context preservation
        context_preserved = True
        context_checks = []

        # Check if key context elements are preserved
        for _key, value in previous_context.items():
            if value and isinstance(value, str) and len(value) > 3:
                # Check if the context element is referenced or acknowledged
                if value.lower() not in current_response.lower():
                    # It's okay if not directly mentioned, but should be contextually relevant
                    pass

        # Check for back-references
        back_reference_patterns = [
            r"as (?:you |we )?mentioned",
            r"as (?:I |we )?noted",
            r"continuing from",
            r"regarding your",
            r"for your (?:organization|project)",
        ]

        has_back_reference = any(
            re.search(pattern, current_response, re.IGNORECASE)
            for pattern in back_reference_patterns
        )

        if is_switch and not has_back_reference:
            # Check if context is implicitly preserved
            context_checks.append("no explicit back-reference during programme switch")

        return ProgrammeSwitchResult(
            passed=context_preserved,
            programmes_mentioned=list(all_programmes),
            context_preserved=context_preserved,
            switch_count=1 if is_switch else 0,
            reasoning=f"Programmes: {list(all_programmes)}, "
            f"Switch: {'yes' if is_switch else 'no'}, "
            f"Context checks: {context_checks if context_checks else 'passed'}",
        )

    # =========================================================================
    # Validation Helper Methods (for scenario testing)
    # =========================================================================

    def validate_programme_mentioned(
        self,
        response: str,
        programmes: list[str],
    ) -> bool:
        """
        Validate that specific programmes are mentioned (for scenario testing).

        Args:
            response: Response to validate
            programmes: List of programme keys that should be mentioned

        Returns:
            True if all specified programmes are mentioned
        """
        result = self.check_programme_mentions(response)
        mentioned = set(result.programmes_found)
        required = set(programmes)
        return required.issubset(mentioned)

    async def validate_programme_accurate(
        self,
        response: str,
        programme: str,
        min_score: float = 0.7,
    ) -> bool:
        """
        Validate that programme facts are accurate (for scenario testing).

        Args:
            response: Response to validate
            programme: Programme to check facts for
            min_score: Minimum accuracy score required

        Returns:
            True if accuracy score >= min_score
        """
        result = await self.validate_programme_facts(response, programme)
        return result.score >= min_score

    async def validate_eligibility_correct(
        self,
        response: str,
        context: dict[str, Any],
        min_score: float = 0.7,
    ) -> bool:
        """
        Validate that eligibility rules are correct (for scenario testing).

        Args:
            response: Response to validate
            context: Context with country and programme
            min_score: Minimum accuracy score required

        Returns:
            True if eligibility score >= min_score
        """
        result = await self.validate_eligibility_rules(response, context)
        return result.score >= min_score

    # =========================================================================
    # Integration with QualityEvaluatorAgent
    # =========================================================================

    def get_programme_coverage_summary(self) -> dict[str, Any]:
        """
        Get a summary of programme coverage in the conversation.

        Can be used with QualityEvaluatorAgent for comprehensive quality scoring.
        """
        return {
            "programmes_discussed": self._conversation_programmes,
            "num_programmes": len(self._conversation_programmes),
            "is_multi_programme": len(self._conversation_programmes) > 1,
            "programme_names": [
                PROGRAMME_FACTS[p]["name"]
                for p in self._conversation_programmes
                if p in PROGRAMME_FACTS
            ],
        }

    def get_programme_facts(self, programme: str) -> dict[str, Any] | None:
        """
        Get known facts about a programme.

        Useful for cross-referencing in quality evaluation.
        """
        return PROGRAMME_FACTS.get(programme)

    def get_eligibility_info(
        self,
        country: str,
        programme: str | None = None,
    ) -> dict[str, Any]:
        """
        Get eligibility information for a country.

        Useful for validating eligibility statements in responses.
        """
        return self._get_expected_eligibility(country, programme)

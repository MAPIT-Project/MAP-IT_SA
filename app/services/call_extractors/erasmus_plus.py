"""
Erasmus+ Programme Call Extractor

Extracts structured funding call data from Erasmus+ Programme Guide and Annual Work Programme documents.
Understands the specific format used in Erasmus+ (2021-2027).

Erasmus+ is the EU's programme for education, training, youth, and sport with a budget of €26.2 billion.
"""

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any

from .base import CallExtractor, FundingCall

logger = logging.getLogger(__name__)


class ErasmusPlusExtractor(CallExtractor):
    """
    Extractor for Erasmus+ Programme documents.

    Erasmus+ (2021-2027) supports education, training, youth, and sport.

    Programme Structure:
    - Key Action 1 (KA1): Learning Mobility of Individuals
    - Key Action 2 (KA2): Cooperation for Innovation and Exchange of Good Practices
    - Key Action 3 (KA3): Support to Policy Development and Cooperation
    - Jean Monnet Actions
    - Sport Actions

    Topic codes follow the format: ERASMUS-{ACTION}-{YEAR}-{SUBTYPE}-{NUMBER}

    Examples:
        - ERASMUS-EDU-2025-KA1-HED-DEGREE  (Higher Education Mobility)
        - ERASMUS-EDU-2025-KA2-CBHE  (Capacity Building in Higher Education)
        - ERASMUS-EDU-2025-KA3-INC-SOC  (Social Inclusion)
        - ERASMUS-SPORT-2025-SSCP  (Small-Scale Partnerships in Sport)
        - ERASMUS-JMO-2025-MODULE  (Jean Monnet Module)

    Note: Erasmus+ primarily uses lump-sum/unit cost funding model unlike Horizon Europe's
    actual cost reimbursement. Budget calculations follow standardized unit costs.
    """

    programme = "erasmus_plus"
    programme_name = "Erasmus+"

    # Topic code patterns for Erasmus+
    topic_patterns = [
        # Standard Erasmus+ format: ERASMUS-EDU-2025-KA1-HED-DEGREE
        re.compile(r"ERASMUS-EDU-\d{4}-KA\d-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Sport actions: ERASMUS-SPORT-2025-SSCP
        re.compile(r"ERASMUS-SPORT-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Jean Monnet actions: ERASMUS-JMO-2025-MODULE
        re.compile(r"ERASMUS-JMO-\d{4}-[A-Z]+(?:-[A-Z]+)*", re.IGNORECASE),
        # Youth actions: ERASMUS-YOUTH-2025-...
        re.compile(r"ERASMUS-YOUTH-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Virtual exchanges: ERASMUS-EDU-2025-VIRT-EXCH
        re.compile(r"ERASMUS-EDU-\d{4}-VIRT-[A-Z]+(?:-[A-Z]+)*", re.IGNORECASE),
        # Alternative format used in some documents: ERASMUS-2025-KA1-...
        re.compile(r"ERASMUS-\d{4}-KA\d-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Legacy/generic Erasmus format
        re.compile(r"ERASMUS(?:PLUS)?-[A-Z]{2,6}-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
    ]

    # Action types in Erasmus+
    action_types = {
        # Key Action 1 - Learning Mobility
        "KA1-HED": "Higher Education Mobility",
        "KA1-VET": "VET Learners and Staff Mobility",
        "KA1-SCH": "School Education Staff Mobility",
        "KA1-ADU": "Adult Education Staff Mobility",
        "KA1-YOU": "Youth Mobility",
        "KA1-DEGREE": "Joint Master Degree",
        "KA1-ICM": "International Credit Mobility",
        # Key Action 2 - Cooperation
        "KA2-COOP": "Cooperation Partnership",
        "KA2-SSP": "Small-Scale Partnership",
        "KA2-CBHE": "Capacity Building Higher Education",
        "KA2-CBVET": "Capacity Building VET",
        "KA2-CBYOUTH": "Capacity Building Youth",
        "KA2-VIP": "Virtual and Blended Intensive Programmes",
        "KA2-ALLIANCES": "Alliances for Innovation",
        "KA2-TEACH-ACAD": "Teacher Academies",
        "KA2-COE": "Centres of Vocational Excellence",
        "KA2-FORWARD": "Forward-Looking Projects",
        # Key Action 3 - Policy Support
        "KA3-INC-SOC": "Social Inclusion and Common Values",
        "KA3-YOUTH-TOG": "Youth Together",
        "KA3-EUYOUTH": "EU Youth Dialogue",
        "KA3-NET-EPLUS": "Networks and Partnerships",
        # Jean Monnet
        "JMO-MODULE": "Jean Monnet Module",
        "JMO-CHAIR": "Jean Monnet Chair",
        "JMO-COE": "Jean Monnet Centre of Excellence",
        "JMO-NETWORK": "Jean Monnet Network",
        "JMO-PROJECT": "Jean Monnet Project",
        # Sport
        "SPORT-COOP": "Cooperation Partnership Sport",
        "SPORT-SSCP": "Small-Scale Partnership Sport",
        "SPORT-EVENT": "Non-Profit Sport Events",
        "SPORT-EWS": "European Week of Sport",
    }

    # Key Action descriptions
    key_actions = {
        "KA1": "Learning Mobility of Individuals",
        "KA2": "Cooperation among Organisations and Institutions",
        "KA3": "Support to Policy Development and Cooperation",
        "JMO": "Jean Monnet Actions",
        "SPORT": "Sport Actions",
    }

    # Sector mappings
    sectors = {
        "HED": "Higher Education",
        "VET": "Vocational Education and Training",
        "SCH": "School Education",
        "ADU": "Adult Education",
        "YOU": "Youth",
        "SPORT": "Sport",
    }

    # Standard funding rates (Erasmus+ uses lump sums and unit costs)
    funding_model = "lump_sum"  # Key difference from Horizon Europe

    # Typical budget ranges by action type (in EUR)
    budget_ranges = {
        "KA1-HED": {"min": 60000, "max": 500000},
        "KA1-VET": {"min": 30000, "max": 200000},
        "KA1-SCH": {"min": 15000, "max": 100000},
        "KA1-ADU": {"min": 15000, "max": 100000},
        "KA1-YOU": {"min": 5000, "max": 150000},
        "KA1-DEGREE": {"min": 750000, "max": 4500000},
        "KA2-COOP": {"min": 120000, "max": 400000},
        "KA2-SSP": {"min": 30000, "max": 60000},
        "KA2-CBHE": {"min": 400000, "max": 1000000},
        "KA2-ALLIANCES": {"min": 1000000, "max": 4000000},
        "KA2-COE": {"min": 4000000, "max": 8000000},
        "JMO-MODULE": {"min": 30000, "max": 30000},
        "JMO-CHAIR": {"min": 50000, "max": 50000},
        "SPORT-COOP": {"min": 120000, "max": 400000},
        "SPORT-SSCP": {"min": 30000, "max": 60000},
    }

    # Typical project durations by action type (in months)
    duration_ranges = {
        "KA1-HED": {"min": 12, "max": 26},
        "KA1-VET": {"min": 12, "max": 24},
        "KA1-SCH": {"min": 12, "max": 24},
        "KA1-ADU": {"min": 12, "max": 24},
        "KA1-YOU": {"min": 3, "max": 24},
        "KA1-DEGREE": {"min": 48, "max": 72},
        "KA2-COOP": {"min": 12, "max": 36},
        "KA2-SSP": {"min": 6, "max": 24},
        "KA2-CBHE": {"min": 24, "max": 36},
        "KA2-ALLIANCES": {"min": 24, "max": 48},
        "KA2-COE": {"min": 48, "max": 48},
        "JMO-MODULE": {"min": 36, "max": 36},
        "JMO-CHAIR": {"min": 36, "max": 36},
        "SPORT-COOP": {"min": 12, "max": 36},
        "SPORT-SSCP": {"min": 6, "max": 24},
    }

    # Eligibility: Programme Countries vs Partner Countries
    programme_countries = [
        # EU Member States
        "Austria",
        "Belgium",
        "Bulgaria",
        "Croatia",
        "Cyprus",
        "Czech Republic",
        "Denmark",
        "Estonia",
        "Finland",
        "France",
        "Germany",
        "Greece",
        "Hungary",
        "Ireland",
        "Italy",
        "Latvia",
        "Lithuania",
        "Luxembourg",
        "Malta",
        "Netherlands",
        "Poland",
        "Portugal",
        "Romania",
        "Slovakia",
        "Slovenia",
        "Spain",
        "Sweden",
        # Associated Countries (as of 2024)
        "Iceland",
        "Liechtenstein",
        "Norway",
        "North Macedonia",
        "Serbia",
        "Turkey",
    ]

    def extract_from_content(self, content: str, document_title: str = "") -> list[FundingCall]:
        """
        Extract Erasmus+ calls from document content.

        The Erasmus+ Programme Guide and Annual Work Programmes typically have:
        - Action type and eligibility requirements
        - Deadline tables per round
        - Funding model (lump sum/unit costs)
        - Partnership requirements
        """
        calls = []

        # Find all topic codes
        topic_codes = self.find_topic_codes(content)

        for topic_code in topic_codes:
            topic_code = topic_code.upper()

            # Extract call details
            call = self._extract_single_call(content, topic_code, document_title)

            if call and call.is_valid():
                calls.append(call)

        return calls

    def _extract_single_call(
        self, content: str, topic_code: str, document_title: str
    ) -> FundingCall | None:
        """Extract details for a single Erasmus+ call."""

        # Extract basic info
        title = self._extract_title(content, topic_code)
        if not title or len(title) < 5:
            # Try to construct title from action type
            title = self._construct_title_from_code(topic_code)

        # Extract year from topic code
        call_year = self.extract_year_from_code(topic_code)

        # Determine Key Action and sector
        key_action = self._extract_key_action(topic_code)
        sector = self._extract_sector(topic_code)
        action_type = self._extract_action_type(topic_code)

        # Extract deadlines
        deadline = self._extract_deadline(content, topic_code)

        # Extract budget info (uses lump sums)
        budget_info = self._extract_budget_info(action_type)

        # Extract duration info
        duration_info = self._extract_duration_info(action_type)

        # Extract eligibility requirements
        eligibility = self._extract_eligibility(content, topic_code, key_action)

        # Extract scope/objectives
        scope = self._extract_scope(content, topic_code)

        # Build portal URL
        portal_url = self.build_portal_url(topic_code)

        return FundingCall(
            programme=self.programme,
            topic_code=topic_code,
            title=title,
            call_identifier=f"ERASMUS-{call_year}",
            programme_part=key_action,
            work_programme_year=call_year,
            action_type=action_type,
            call_year=call_year,
            deadline=deadline,
            status=self._determine_status(deadline),
            budget_per_project_min=Decimal(str(budget_info.get("min", 0))) if budget_info else None,
            budget_per_project_max=Decimal(str(budget_info.get("max", 0))) if budget_info else None,
            funding_rate=100,  # Erasmus+ typically covers 100% of eligible costs via lump sums
            scope=scope,
            eligibility=eligibility,
            cluster=sector,  # Using cluster field for sector in Erasmus+
            portal_url=portal_url,
            source_document_title=document_title,
            metadata={
                "funding_model": "lump_sum",
                "key_action": key_action,
                "key_action_name": self.key_actions.get(key_action, key_action),
                "sector": sector,
                "sector_name": self.sectors.get(sector, sector),
                "duration_months_min": duration_info.get("min") if duration_info else None,
                "duration_months_max": duration_info.get("max") if duration_info else None,
                "programme_countries_only": self._is_programme_countries_only(key_action),
            },
        )

    def _extract_title(self, content: str, topic_code: str) -> str | None:
        """Extract call title from content."""
        # Look for topic code followed by colon/dash and title
        patterns = [
            rf"{re.escape(topic_code)}\s*[:–-]\s*(.{{20,200}}?)(?:\n|$)",
            rf"{re.escape(topic_code)}\s+(.{{20,200}}?)(?:\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                title = self.clean_text(match.group(1), max_length=200)
                if title and len(title) > 10:
                    return title

        return None

    def _construct_title_from_code(self, topic_code: str) -> str:
        """Construct a meaningful title from the topic code."""
        action_type = self._extract_action_type(topic_code)
        if action_type and action_type in self.action_types:
            return self.action_types[action_type]

        # Build from parts
        parts = []
        key_action = self._extract_key_action(topic_code)
        if key_action and key_action in self.key_actions:
            parts.append(self.key_actions[key_action])

        sector = self._extract_sector(topic_code)
        if sector and sector in self.sectors:
            parts.append(f"- {self.sectors[sector]}")

        if parts:
            return " ".join(parts)

        return f"Erasmus+ Call {topic_code}"

    def _extract_key_action(self, topic_code: str) -> str | None:
        """Extract Key Action from topic code."""
        # Match KA1, KA2, KA3
        match = re.search(r"KA(\d)", topic_code, re.IGNORECASE)
        if match:
            return f"KA{match.group(1)}"

        # Check for Jean Monnet
        if "JMO" in topic_code.upper():
            return "JMO"

        # Check for Sport
        if "SPORT" in topic_code.upper():
            return "SPORT"

        return None

    def _extract_sector(self, topic_code: str) -> str | None:
        """Extract sector from topic code."""
        for sector_code in self.sectors.keys():
            if sector_code in topic_code.upper():
                return sector_code
        return None

    def _extract_action_type(self, topic_code: str) -> str | None:
        """Extract specific action type from topic code."""
        topic_upper = topic_code.upper()

        # Try to match against known action types
        for action_code in self.action_types.keys():
            # Handle compound codes like KA2-COOP, KA1-HED
            if action_code.replace("-", "") in topic_upper.replace("-", ""):
                return action_code
            # Also check if parts are present
            parts = action_code.split("-")
            if len(parts) >= 2 and all(p in topic_upper for p in parts):
                return action_code

        # Try to construct from key action and sector
        key_action = self._extract_key_action(topic_code)
        sector = self._extract_sector(topic_code)
        if key_action and sector:
            combined = f"{key_action}-{sector}"
            if combined in self.action_types:
                return combined

        return key_action

    def _extract_deadline(self, content: str, topic_code: str) -> date | None:
        """Extract deadline from content."""
        # Look for deadline patterns near the topic code
        context_pattern = rf"{re.escape(topic_code)}.{{0,1000}}"
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0)

            # Look for deadline patterns
            deadline_patterns = [
                r"deadline[:\s]+(\d{1,2}\s+\w+\s+\d{4})",
                r"(\d{1,2}\s+\w+\s+\d{4})\s*(?:at\s+\d{1,2}:\d{2})?",
                r"(\d{4}-\d{2}-\d{2})",
            ]

            for pattern in deadline_patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    parsed = self.parse_date(match.group(1))
                    if parsed:
                        return parsed

        return None

    def _extract_budget_info(self, action_type: str | None) -> dict[str, int] | None:
        """Get budget range for action type."""
        if action_type and action_type in self.budget_ranges:
            return self.budget_ranges[action_type]
        return None

    def _extract_duration_info(self, action_type: str | None) -> dict[str, int] | None:
        """Get duration range for action type."""
        if action_type and action_type in self.duration_ranges:
            return self.duration_ranges[action_type]
        return None

    def _extract_eligibility(
        self, content: str, topic_code: str, key_action: str | None
    ) -> str | None:
        """Extract eligibility requirements."""
        eligibility_parts = []

        # Add standard eligibility based on key action
        if key_action == "KA1":
            eligibility_parts.append(
                "Applicant must be an eligible organisation from a Programme Country. "
                "For Higher Education mobility, a valid Erasmus Charter for Higher Education (ECHE) is required."
            )
        elif key_action == "KA2":
            eligibility_parts.append(
                "Minimum consortium of organisations from different Programme Countries. "
                "Cooperation Partnerships: 3+ organisations from 3+ countries. "
                "Small-Scale Partnerships: 2+ organisations from 2+ countries."
            )
        elif key_action == "KA3":
            eligibility_parts.append(
                "Open to public authorities, civil society organisations, and other stakeholders. "
                "Specific requirements vary by action type."
            )
        elif key_action == "JMO":
            eligibility_parts.append(
                "Higher education institutions (HEIs) worldwide are eligible. "
                "HEIs in Programme Countries must hold a valid ECHE."
            )
        elif key_action == "SPORT":
            eligibility_parts.append(
                "Sport organisations, clubs, and public bodies involved in sport. "
                "Consortium requirements vary by action type."
            )

        # Look for additional eligibility in content
        context_pattern = rf"{re.escape(topic_code)}.{{0,2000}}"
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0)
            eligibility_patterns = [
                r"eligib(?:ility|le)[:\s]+(.{50,500}?)(?:\n\n|$)",
                r"who can apply[:\s]+(.{50,500}?)(?:\n\n|$)",
            ]

            for pattern in eligibility_patterns:
                match = re.search(pattern, context, re.IGNORECASE | re.DOTALL)
                if match:
                    additional = self.clean_text(match.group(1), max_length=500)
                    if additional and len(additional) > 20:
                        eligibility_parts.append(additional)
                        break

        return " ".join(eligibility_parts) if eligibility_parts else None

    def _extract_scope(self, content: str, topic_code: str) -> str | None:
        """Extract scope/objectives from content."""
        context_pattern = rf"{re.escape(topic_code)}.{{0,3000}}"
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0)

            scope_patterns = [
                r"(?:scope|objectives?|description)[:\s]+(.{100,1000}?)(?:\n\n|eligib|deadline)",
                r"this action (?:supports?|aims?)[:\s]*(.{100,1000}?)(?:\n\n|eligib|deadline)",
            ]

            for pattern in scope_patterns:
                match = re.search(pattern, context, re.IGNORECASE | re.DOTALL)
                if match:
                    scope = self.clean_text(match.group(1), max_length=1000)
                    if scope and len(scope) > 50:
                        return scope

        return None

    def _determine_status(self, deadline: date | None) -> str:
        """Determine call status based on deadline."""
        if not deadline:
            return "upcoming"

        today = date.today()
        if deadline < today:
            return "closed"
        elif (deadline - today).days <= 30:
            return "open"
        else:
            return "upcoming"

    def _is_programme_countries_only(self, key_action: str | None) -> bool:
        """Check if action is limited to Programme Countries only."""
        # KA1 mobility to Partner Countries, KA2 CBHE, and JMO are open worldwide
        # Most other actions require Programme Country participation
        if key_action in ["JMO"]:
            return False
        if key_action == "KA2":
            return False  # CBHE is worldwide
        return True

    def build_portal_url(self, topic_code: str) -> str:
        """Build EU portal URL for an Erasmus+ topic code."""
        # Erasmus+ calls use a different portal URL structure
        base_url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details"
        return f"{base_url}/{topic_code.lower()}"

    def get_programme_info(self) -> dict[str, Any]:
        """Return comprehensive information about the Erasmus+ programme."""
        return {
            "programme": self.programme,
            "programme_name": self.programme_name,
            "budget": "€26.2 billion (2021-2027)",
            "description": (
                "Erasmus+ is the EU's programme to support education, training, youth, "
                "and sport in Europe. It provides opportunities for students, trainees, "
                "staff, and young people to study, train, gain experience, and volunteer abroad."
            ),
            "key_actions": self.key_actions,
            "sectors": self.sectors,
            "action_types": self.action_types,
            "funding_model": "Lump sums and unit costs (not actual cost reimbursement)",
            "programme_countries": self.programme_countries,
            "website": "https://erasmus-plus.ec.europa.eu/",
            "portal": "https://ec.europa.eu/programmes/erasmus-plus/",
        }

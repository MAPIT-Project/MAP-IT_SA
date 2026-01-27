"""
Creative Europe Programme Call Extractor

Extracts structured funding call data from Creative Europe Programme Guide and Work Programme documents.
Understands the specific format used in Creative Europe (2021-2027).

Creative Europe is the EU's programme supporting the cultural and creative sectors with a budget of €2.44 billion.
"""

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any

from .base import CallExtractor, FundingCall

logger = logging.getLogger(__name__)


class CreativeEuropeExtractor(CallExtractor):
    """
    Extractor for Creative Europe Programme documents.

    Creative Europe (2021-2027) supports:
    - CULTURE strand: Support for cultural and creative sectors
    - MEDIA strand: Support for audiovisual and media industry
    - CROSS-SECTORAL strand: Cross-cutting issues

    Topic codes follow the format: CREA-{STRAND}-{YEAR}-{ACTION}-{SUBTYPE}

    Examples:
        - CREA-CULTURE-2025-COOP-1  (European Cooperation Projects - Small Scale)
        - CREA-CULTURE-2025-COOP-2  (European Cooperation Projects - Medium Scale)
        - CREA-MEDIA-2025-DEVSLATE  (Development of European Slate)
        - CREA-MEDIA-2025-TVONLINE  (TV and Online Content)
        - CREA-CROSS-2025-MEDIALITERACY  (Media Literacy)
        - CREA-CROSS-2025-CREATIVELAB  (Creative Innovation Lab)
    """

    programme = "creative_europe"
    programme_name = "Creative Europe"

    # Topic code patterns for Creative Europe
    topic_patterns = [
        # Culture strand: CREA-CULTURE-2025-COOP-1
        re.compile(r"CREA-CULTURE-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Media strand: CREA-MEDIA-2025-DEVSLATE
        re.compile(r"CREA-MEDIA-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Cross-sectoral strand: CREA-CROSS-2025-MEDIALITERACY
        re.compile(r"CREA-CROSS-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Alternative format: CREATIVE-EUROPE-2025-...
        re.compile(r"CREATIVE-EUROPE-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
        # Legacy format
        re.compile(r"CREA-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.IGNORECASE),
    ]

    # Strands and their descriptions
    strands = {
        "CULTURE": "Culture Strand",
        "MEDIA": "MEDIA Strand",
        "CROSS": "Cross-Sectoral Strand",
    }

    # Action types by strand
    action_types = {
        # CULTURE strand actions
        "CULTURE-COOP-1": "European Cooperation Projects - Small Scale",
        "CULTURE-COOP-2": "European Cooperation Projects - Medium Scale",
        "CULTURE-COOP-3": "European Cooperation Projects - Large Scale",
        "CULTURE-PLATF": "European Platforms",
        "CULTURE-NET": "European Networks",
        "CULTURE-LIT": "Literary Translation",
        "CULTURE-CIRC": "Circulation of European Literary Works",
        # MEDIA strand actions
        "MEDIA-DEVSLATE": "Development of European Slate",
        "MEDIA-DEVSINGLE": "Development of European Single Project",
        "MEDIA-DEVVG": "Development of European Video Games",
        "MEDIA-TVONLINE": "TV and Online Content",
        "MEDIA-COPRODFUNDS": "Audiovisual Co-production Funds",
        "MEDIA-INNOVBM": "Innovative Tools and Business Models",
        "MEDIA-TRAINING": "Training and Skills",
        "MEDIA-TALENTS": "Talents and Skills",
        "MEDIA-MARKET": "Markets and Networking",
        "MEDIA-FESTIV": "European Film Festivals",
        "MEDIA-FILMEU": "Films on the Move",
        "MEDIA-DISTAUDINEMA": "Distribution - Automatic Support Cinema",
        "MEDIA-DISTSEL": "Distribution - Selective Support",
        "MEDIA-AUDINET": "Audience Development and Film Education",
        # Cross-sectoral strand actions
        "CROSS-MEDIALITERACY": "Media Literacy",
        "CROSS-CREATIVELAB": "Creative Innovation Lab",
        "CROSS-NEWS": "News - Support for Production of News Content",
        "CROSS-MEDIAFREEDOM": "Media Freedom",
        "CROSS-SECTDISC": "Sectoral Discovery",
    }

    # Budget ranges by action type (in EUR)
    budget_ranges = {
        # Culture strand
        "CULTURE-COOP-1": {"min": 60000, "max": 200000, "funding_rate": 80},
        "CULTURE-COOP-2": {"min": 200000, "max": 1000000, "funding_rate": 70},
        "CULTURE-COOP-3": {"min": 1000000, "max": 2000000, "funding_rate": 60},
        "CULTURE-PLATF": {"min": 500000, "max": 2500000, "funding_rate": 80},
        "CULTURE-NET": {"min": 400000, "max": 600000, "funding_rate": 80},
        "CULTURE-LIT": {"min": 5000, "max": 320000, "funding_rate": 60},
        "CULTURE-CIRC": {"min": 100000, "max": 500000, "funding_rate": 80},
        # Media strand
        "MEDIA-DEVSLATE": {"min": 150000, "max": 250000, "funding_rate": 70},
        "MEDIA-DEVSINGLE": {"min": 30000, "max": 60000, "funding_rate": 50},
        "MEDIA-DEVVG": {"min": 150000, "max": 200000, "funding_rate": 50},
        "MEDIA-TVONLINE": {"min": 500000, "max": 2500000, "funding_rate": 20},
        "MEDIA-COPRODFUNDS": {"min": 700000, "max": 1500000, "funding_rate": 70},
        "MEDIA-TRAINING": {"min": 100000, "max": 500000, "funding_rate": 80},
        "MEDIA-FESTIV": {"min": 50000, "max": 200000, "funding_rate": 60},
        "MEDIA-FILMEU": {"min": 50000, "max": 150000, "funding_rate": 40},
        # Cross-sectoral strand
        "CROSS-MEDIALITERACY": {"min": 300000, "max": 1000000, "funding_rate": 70},
        "CROSS-CREATIVELAB": {"min": 300000, "max": 600000, "funding_rate": 60},
        "CROSS-NEWS": {"min": 500000, "max": 3000000, "funding_rate": 80},
    }

    # Consortium requirements
    consortium_requirements = {
        "CULTURE-COOP-1": {"min_partners": 3, "min_countries": 3},
        "CULTURE-COOP-2": {"min_partners": 5, "min_countries": 5},
        "CULTURE-COOP-3": {"min_partners": 10, "min_countries": 10},
        "CULTURE-PLATF": {"min_partners": 12, "min_countries": 12},
        "CULTURE-NET": {"min_partners": 15, "min_countries": 10},
        "MEDIA-COPRODFUNDS": {"min_partners": 3, "min_countries": 3},
    }

    # Duration ranges by action type (in months)
    duration_ranges = {
        "CULTURE-COOP-1": {"min": 6, "max": 48},
        "CULTURE-COOP-2": {"min": 12, "max": 48},
        "CULTURE-COOP-3": {"min": 24, "max": 48},
        "CULTURE-PLATF": {"min": 36, "max": 60},
        "CULTURE-NET": {"min": 36, "max": 60},
        "CULTURE-LIT": {"min": 12, "max": 36},
        "MEDIA-DEVSLATE": {"min": 24, "max": 36},
        "MEDIA-DEVSINGLE": {"min": 24, "max": 36},
        "MEDIA-DEVVG": {"min": 24, "max": 36},
        "MEDIA-TVONLINE": {"min": 24, "max": 36},
        "MEDIA-TRAINING": {"min": 12, "max": 36},
        "CROSS-MEDIALITERACY": {"min": 12, "max": 24},
        "CROSS-CREATIVELAB": {"min": 12, "max": 24},
    }

    # Eligible countries
    eligible_countries = [
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
        # Associated Countries
        "Iceland",
        "Liechtenstein",
        "Norway",
        # Countries with partial association (MEDIA only or CULTURE only may vary)
        "Albania",
        "Bosnia and Herzegovina",
        "Georgia",
        "Kosovo",
        "Moldova",
        "Montenegro",
        "North Macedonia",
        "Serbia",
        "Tunisia",
        "Ukraine",
    ]

    def extract_from_content(self, content: str, document_title: str = "") -> list[FundingCall]:
        """
        Extract Creative Europe calls from document content.

        Creative Europe Work Programmes typically have:
        - Action name and description
        - Eligibility requirements
        - Consortium requirements
        - Budget and funding rate information
        - Deadlines
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
        """Extract details for a single Creative Europe call."""

        # Extract basic info
        title = self._extract_title(content, topic_code)
        if not title or len(title) < 5:
            title = self._construct_title_from_code(topic_code)

        # Extract year from topic code
        call_year = self.extract_year_from_code(topic_code)

        # Determine strand and action type
        strand = self._extract_strand(topic_code)
        action_type = self._extract_action_type(topic_code)

        # Extract deadline
        deadline = self._extract_deadline(content, topic_code)

        # Get budget and funding rate info
        budget_info = self._get_budget_info(action_type)
        funding_rate = budget_info.get("funding_rate") if budget_info else None

        # Get consortium requirements
        consortium_info = self._get_consortium_requirements(action_type)

        # Get duration info
        duration_info = self._get_duration_info(action_type)

        # Extract eligibility requirements
        eligibility = self._extract_eligibility(content, topic_code, strand, action_type)

        # Extract scope/objectives
        scope = self._extract_scope(content, topic_code)

        # Build portal URL
        portal_url = self.build_portal_url(topic_code)

        return FundingCall(
            programme=self.programme,
            topic_code=topic_code,
            title=title,
            call_identifier=f"CREA-{call_year}",
            programme_part=self.strands.get(strand, strand) if strand else None,
            work_programme_year=call_year,
            action_type=action_type,
            call_year=call_year,
            deadline=deadline,
            status=self._determine_status(deadline),
            budget_per_project_min=Decimal(str(budget_info.get("min", 0))) if budget_info else None,
            budget_per_project_max=Decimal(str(budget_info.get("max", 0))) if budget_info else None,
            funding_rate=funding_rate,
            scope=scope,
            eligibility=eligibility,
            cluster=strand,  # Using cluster field for strand in Creative Europe
            portal_url=portal_url,
            source_document_title=document_title,
            metadata={
                "strand": strand,
                "strand_name": self.strands.get(strand, strand) if strand else None,
                "action_name": (
                    self.action_types.get(action_type, action_type) if action_type else None
                ),
                "min_partners": consortium_info.get("min_partners") if consortium_info else None,
                "min_countries": consortium_info.get("min_countries") if consortium_info else None,
                "duration_months_min": duration_info.get("min") if duration_info else None,
                "duration_months_max": duration_info.get("max") if duration_info else None,
                "eligible_organizations": self._get_eligible_organizations(strand, action_type),
            },
        )

    def _extract_title(self, content: str, topic_code: str) -> str | None:
        """Extract call title from content."""
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

        # Build from strand
        strand = self._extract_strand(topic_code)
        if strand and strand in self.strands:
            return f"Creative Europe - {self.strands[strand]}"

        return f"Creative Europe Call {topic_code}"

    def _extract_strand(self, topic_code: str) -> str | None:
        """Extract strand from topic code."""
        topic_upper = topic_code.upper()

        # Order matters: check CROSS first as it might contain MEDIA in action names
        if "-CROSS-" in topic_upper or topic_upper.startswith("CREA-CROSS"):
            return "CROSS"
        elif "-CULTURE-" in topic_upper or topic_upper.startswith("CREA-CULTURE"):
            return "CULTURE"
        elif "-MEDIA-" in topic_upper or topic_upper.startswith("CREA-MEDIA"):
            return "MEDIA"

        return None

    def _extract_action_type(self, topic_code: str) -> str | None:
        """Extract action type from topic code."""
        topic_upper = topic_code.upper()
        strand = self._extract_strand(topic_code)

        if not strand:
            return None

        # Try to match against known action types
        for action_key in self.action_types.keys():
            if action_key.startswith(strand):
                # Check if the action code is in the topic code
                action_suffix = action_key.replace(f"{strand}-", "")
                if action_suffix in topic_upper:
                    return action_key

        return strand  # Return strand as fallback

    def _extract_deadline(self, content: str, topic_code: str) -> date | None:
        """Extract deadline from content."""
        context_pattern = rf"{re.escape(topic_code)}.{{0,1500}}"
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0)

            deadline_patterns = [
                r"deadline[:\s]+(\d{1,2}\s+\w+\s+\d{4})",
                r"(\d{1,2}\s+\w+\s+\d{4})\s*(?:at\s+\d{1,2}:\d{2})?",
                r"(\d{4}-\d{2}-\d{2})",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ]

            for pattern in deadline_patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    parsed = self.parse_date(match.group(1))
                    if parsed:
                        return parsed

        return None

    def _get_budget_info(self, action_type: str | None) -> dict[str, Any] | None:
        """Get budget information for action type."""
        if action_type and action_type in self.budget_ranges:
            return self.budget_ranges[action_type]
        return None

    def _get_consortium_requirements(self, action_type: str | None) -> dict[str, int] | None:
        """Get consortium requirements for action type."""
        if action_type and action_type in self.consortium_requirements:
            return self.consortium_requirements[action_type]
        return None

    def _get_duration_info(self, action_type: str | None) -> dict[str, int] | None:
        """Get duration information for action type."""
        if action_type and action_type in self.duration_ranges:
            return self.duration_ranges[action_type]
        return None

    def _extract_eligibility(
        self, content: str, topic_code: str, strand: str | None, action_type: str | None
    ) -> str | None:
        """Extract eligibility requirements."""
        eligibility_parts = []

        # Standard eligibility based on strand
        if strand == "CULTURE":
            eligibility_parts.append(
                "Cultural and creative organisations based in Creative Europe countries. "
                "Includes public and private entities with legal personality in the cultural "
                "and creative sectors (arts, heritage, publishing, music, performing arts, etc.)."
            )
        elif strand == "MEDIA":
            eligibility_parts.append(
                "Audiovisual production companies, distributors, sales agents, training providers, "
                "and other audiovisual sector professionals based in MEDIA participating countries. "
                "Must have recent production track record for development actions."
            )
        elif strand == "CROSS":
            eligibility_parts.append(
                "Organisations from both cultural/creative and audiovisual sectors. "
                "News media organisations for journalism-related actions."
            )

        # Add consortium requirements if applicable
        consortium = self._get_consortium_requirements(action_type)
        if consortium:
            eligibility_parts.append(
                f"Consortium requirement: Minimum {consortium['min_partners']} partners "
                f"from {consortium['min_countries']} different countries."
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
                r"(?:this action|this call)[:\s]*(.{100,1000}?)(?:\n\n|eligib|deadline)",
            ]

            for pattern in scope_patterns:
                match = re.search(pattern, context, re.IGNORECASE | re.DOTALL)
                if match:
                    scope = self.clean_text(match.group(1), max_length=1000)
                    if scope and len(scope) > 50:
                        return scope

        return None

    def _get_eligible_organizations(self, strand: str | None, action_type: str | None) -> list[str]:
        """Get list of eligible organization types."""
        if strand == "CULTURE":
            return [
                "Cultural organizations",
                "Creative industries",
                "Art galleries and museums",
                "Theatre and performing arts",
                "Publishing houses",
                "Music organizations",
                "Heritage organizations",
                "Festivals",
                "Artists and creatives",
            ]
        elif strand == "MEDIA":
            return [
                "Production companies",
                "Distributors",
                "Sales agents",
                "Broadcasters",
                "Training providers",
                "Film festivals",
                "Cinema operators",
                "VOD platforms",
                "Video game developers",
            ]
        elif strand == "CROSS":
            return [
                "Cultural and creative organizations",
                "Audiovisual professionals",
                "News media organizations",
                "Technology companies",
                "Innovation hubs",
            ]
        return []

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

    def build_portal_url(self, topic_code: str) -> str:
        """Build EU portal URL for a Creative Europe topic code."""
        base_url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details"
        return f"{base_url}/{topic_code.lower()}"

    def get_programme_info(self) -> dict[str, Any]:
        """Return comprehensive information about the Creative Europe programme."""
        return {
            "programme": self.programme,
            "programme_name": self.programme_name,
            "budget": "€2.44 billion (2021-2027)",
            "description": (
                "Creative Europe is the European Commission's flagship programme "
                "to support the cultural and creative sectors. It consists of three strands: "
                "Culture (supporting cultural and creative projects and organisations), "
                "MEDIA (supporting the audiovisual sector), and Cross-sectoral "
                "(addressing common challenges across cultural and creative industries)."
            ),
            "strands": self.strands,
            "action_types": self.action_types,
            "key_priorities": [
                "Enhancing cultural diversity and heritage",
                "Increasing competitiveness of cultural and creative sectors",
                "Strengthening international cooperation",
                "Promoting gender equality and inclusion",
                "Supporting green and digital transition",
            ],
            "eligible_countries": self.eligible_countries,
            "website": "https://creative-europe.ec.europa.eu/",
            "portal": "https://ec.europa.eu/programmes/creative-europe/",
        }

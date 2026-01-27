"""
LIFE Programme Call Extractor

Extracts structured funding call data from LIFE Programme Work Programme documents.
LIFE (2021-2027) is the EU's funding instrument for the environment and climate action.

Topic codes follow the format: LIFE-{YEAR}-{STRAND}-{TYPE}
Examples:
    - LIFE-2024-SAP-ENV (Standard Action Projects - Environment)
    - LIFE-2024-SAP-CLIMA (Standard Action Projects - Climate)
    - LIFE-2024-SAP-NAT (Standard Action Projects - Nature)
    - LIFE-2024-CET (Clean Energy Transition)

Download Work Programmes from:
https://cinea.ec.europa.eu/programmes/life_en
"""

import logging
import re
from decimal import Decimal
from typing import Any

from .base import CallExtractor, FundingCall

logger = logging.getLogger(__name__)


class LIFEExtractor(CallExtractor):
    """
    Extractor for LIFE Programme Work Programme documents.

    LIFE Programme sub-programmes:
    - Nature and Biodiversity
    - Circular Economy and Quality of Life
    - Climate Change Mitigation and Adaptation
    - Clean Energy Transition
    """

    programme = "life"
    programme_name = "LIFE Programme"

    # Topic code patterns for LIFE
    topic_patterns = [
        # Standard format: LIFE-2024-SAP-ENV-ENVIRONMENT
        re.compile(r"LIFE-\d{4}-[A-Z]+-[A-Z]+(?:-[A-Z]+)?", re.IGNORECASE),
        # Shorter format: LIFE-2024-CET
        re.compile(r"LIFE-\d{4}-[A-Z]{2,}(?:-\d+)?", re.IGNORECASE),
    ]

    # LIFE sub-programmes and strands
    strands = {
        "SAP": "Standard Action Projects",
        "SAP-ENV": "Standard Action Projects - Environment",
        "SAP-CLIMA": "Standard Action Projects - Climate",
        "SAP-NAT": "Standard Action Projects - Nature & Biodiversity",
        "SIP": "Strategic Integrated Projects",
        "SNAP": "Strategic Nature Projects",
        "TA": "Technical Assistance",
        "CET": "Clean Energy Transition",
        "OG": "Operating Grants to NGOs",
        "PLP": "Preparatory Projects",
    }

    # Sub-programmes
    sub_programmes = {
        "ENV": "Environment",
        "CLIMA": "Climate Action",
        "NAT": "Nature and Biodiversity",
        "CIRC": "Circular Economy and Quality of Life",
        "GOV": "Environmental and Climate Governance",
        "CET": "Clean Energy Transition",
    }

    # Action types
    action_types = {
        "SAP": "Standard Action Project",
        "SIP": "Strategic Integrated Project",
        "SNAP": "Strategic Nature Project",
        "TA": "Technical Assistance",
        "OG": "Operating Grant",
        "PLP": "Preparatory Project",
    }

    def extract_from_content(self, content: str, document_title: str = "") -> list[FundingCall]:
        """
        Extract LIFE calls from document content.
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
        """Extract details for a single LIFE call."""

        title = self._extract_title(content, topic_code)
        if not title or len(title) < 5:
            return None

        call_year = self.extract_year_from_code(topic_code)
        strand = self._extract_strand(topic_code)
        sub_programme = self._extract_sub_programme(topic_code)
        action_type = self._extract_action_type_from_code(topic_code)
        expected_outcome = self._extract_expected_outcome(content, topic_code)
        scope = self._extract_scope(content, topic_code)
        budget_info = self._extract_budget_info(content, topic_code)
        deadline = self._extract_deadline(content, topic_code, call_year)

        # Determine status
        from datetime import date

        today = date.today()
        if call_year:
            if call_year > today.year:
                status = "upcoming"
            elif call_year == today.year:
                status = "open"
            else:
                status = "closed"
        else:
            status = "upcoming"

        # Combine strand and sub-programme for destination
        destination = f"{strand}"
        if sub_programme:
            destination += f" - {sub_programme}"

        return FundingCall(
            programme=self.programme,
            topic_code=topic_code,
            title=title,
            programme_part=strand,
            destination=destination,
            action_type=action_type,
            call_year=call_year,
            deadline=deadline,
            status=status,
            budget_total=budget_info.get("total"),
            budget_per_project_min=budget_info.get("min"),
            budget_per_project_max=budget_info.get("max"),
            expected_projects=budget_info.get("projects"),
            expected_outcome=expected_outcome,
            scope=scope,
            tags=self._generate_tags(title, scope, strand, sub_programme),
            source_document_title=document_title,
            portal_url=self.build_portal_url(topic_code),
        )

    def _extract_title(self, content: str, topic_code: str) -> str:
        """Extract call title from content."""
        pattern = rf"{re.escape(topic_code)}[:\s—–-]+([^\n]+)"
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            title = match.group(1).strip()
            title = re.sub(r"\s+", " ", title)
            title = re.sub(r"[:\s]+$", "", title)
            if len(title) > 10:
                return title[:200]

        # Generate title from topic code
        strand = self._extract_strand(topic_code)
        sub_prog = self._extract_sub_programme(topic_code)
        if strand or sub_prog:
            return f"LIFE {strand or ''} {sub_prog or ''} Call {topic_code}".strip()

        return topic_code

    def _extract_strand(self, topic_code: str) -> str:
        """Extract the strand from topic code."""
        for strand_code, strand_name in self.strands.items():
            if strand_code in topic_code.upper():
                return strand_name
        return "LIFE Programme"

    def _extract_sub_programme(self, topic_code: str) -> str | None:
        """Extract the sub-programme from topic code."""
        for sub_code, sub_name in self.sub_programmes.items():
            if sub_code in topic_code.upper():
                return sub_name
        return None

    def _extract_action_type_from_code(self, topic_code: str) -> str | None:
        """Extract action type from topic code."""
        for action_code, action_name in self.action_types.items():
            if action_code in topic_code.upper():
                return action_name
        return None

    def _extract_expected_outcome(self, content: str, topic_code: str) -> str | None:
        """Extract expected outcome section."""
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return None

        search_content = content[start_idx : start_idx + 6000]

        patterns = [
            r"Expected\s+(?:Outcome|Impact|Result)[s]?[:\s]+(.{50,1500}?)(?=Scope|Objective|Eligibility|$)",
            r"Objective[s]?[:\s]+(.{50,1200}?)(?=Scope|Activities|$)",
            r"(?:This\s+call|Projects)\s+(?:aims?|should|will)[:\s]+(.{50,1000}?)(?=Scope|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, search_content, re.IGNORECASE | re.DOTALL)
            if match:
                return self.clean_text(match.group(1), max_length=1500)

        return None

    def _extract_scope(self, content: str, topic_code: str) -> str | None:
        """Extract scope section."""
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return None

        search_content = content[start_idx : start_idx + 8000]

        patterns = [
            r"Scope[:\s]+(.{50,2500}?)(?=Eligibility|Expected|Budget|Deadline|$)",
            r"Activities[:\s]+(.{50,2000}?)(?=Eligibility|Budget|$)",
            r"Eligible\s+(?:actions|projects)[:\s]+(.{50,2000}?)(?=Budget|Deadline|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, search_content, re.IGNORECASE | re.DOTALL)
            if match:
                return self.clean_text(match.group(1), max_length=2500)

        return None

    def _extract_budget_info(self, content: str, topic_code: str) -> dict[str, Any]:
        """Extract budget information."""
        result = {}

        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return result

        search_content = content[max(0, start_idx - 300) : start_idx + 2000]

        # LIFE-specific budget patterns
        budget_patterns = [
            r"(?:total\s+)?budget[:\s]+(?:EUR\s*)?(\d+(?:[.,]\d+)?)\s*(?:million|M)",
            r"EUR\s*(\d+(?:[.,]\d+)?)\s*(?:million|M)",
            r"(?:maximum|up\s+to)[:\s]+(?:EUR\s*)?(\d+(?:[.,]\d+)?)\s*(?:million|M)",
        ]

        for pattern in budget_patterns:
            match = re.search(pattern, search_content, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1).replace(",", "."))
                    if 0.1 <= amount <= 500:
                        result["total"] = Decimal(str(amount * 1_000_000))
                        break
                except ValueError:
                    continue

        # Co-funding rate (LIFE typically has 60% or 75%)
        rate_patterns = [
            r"co-?funding\s+rate[:\s]+(?:up\s+to\s+)?(\d+)\s*%",
            r"(\d+)\s*%\s+(?:co-?funding|of\s+eligible)",
        ]

        for pattern in rate_patterns:
            match = re.search(pattern, search_content, re.IGNORECASE)
            if match:
                try:
                    result["rate"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        return result

    def _generate_tags(
        self, title: str, scope: str | None, strand: str, sub_programme: str | None
    ) -> list[str]:
        """Generate search tags."""
        tags = ["life", "environment"]

        # Add strand and sub-programme
        if strand:
            tags.extend(strand.lower().split())
        if sub_programme:
            tags.extend(sub_programme.lower().split())

        # Keywords from title
        keywords = re.findall(r"\b[a-zA-Z]{4,}\b", title.lower())
        tags.extend(keywords[:5])

        # LIFE-specific terms
        life_terms = [
            "biodiversity",
            "nature",
            "climate",
            "adaptation",
            "mitigation",
            "circular",
            "economy",
            "waste",
            "water",
            "air",
            "soil",
            "pollution",
            "habitat",
            "species",
            "ecosystem",
            "conservation",
            "renewable",
            "energy",
            "efficiency",
            "sustainable",
        ]
        if scope:
            for term in life_terms:
                if term in scope.lower():
                    tags.append(term)

        return list(set(tags))[:15]

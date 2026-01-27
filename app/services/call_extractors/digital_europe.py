"""
Digital Europe Programme Call Extractor

Extracts structured funding call data from Digital Europe Work Programme documents.
Digital Europe (2021-2027) focuses on deploying digital technology across the EU.

Topic codes follow the format: DIGITAL-{YEAR}-{AREA}-{NUMBER}
Examples:
    - DIGITAL-2024-CLOUD-AI-04
    - DIGITAL-2025-CYBER-SKILLS-02
    - DIGITAL-2024-DEPLOY-01

Download Work Programmes from:
https://digital-strategy.ec.europa.eu/en/activities/work-programmes-digital
"""

import logging
import re
from decimal import Decimal
from typing import Any

from .base import CallExtractor, FundingCall

logger = logging.getLogger(__name__)


class DigitalEuropeExtractor(CallExtractor):
    """
    Extractor for Digital Europe Programme Work Programme documents.

    Digital Europe supports activities in:
    - High Performance Computing
    - Artificial Intelligence
    - Cybersecurity
    - Advanced Digital Skills
    - Ensuring wide use of digital technologies (Deployment)
    - European Digital Innovation Hubs
    """

    programme = "digital_europe"
    programme_name = "Digital Europe Programme"

    # Topic code patterns for Digital Europe
    topic_patterns = [
        # Standard format: DIGITAL-2024-CLOUD-AI-04
        re.compile(r"DIGITAL-\d{4}-[A-Z]+-[A-Z0-9-]+", re.IGNORECASE),
        # Shorter format: DIGITAL-2024-AI-01
        re.compile(r"DIGITAL-\d{4}-[A-Z]{2,}-\d+", re.IGNORECASE),
    ]

    # Digital Europe areas
    areas = {
        "CLOUD": "Cloud & Data",
        "AI": "Artificial Intelligence",
        "CYBER": "Cybersecurity",
        "SKILLS": "Advanced Digital Skills",
        "DEPLOY": "Deployment/Best Use",
        "EDIH": "European Digital Innovation Hubs",
        "HPC": "High Performance Computing",
        "DATA": "Data Spaces",
        "QUANTUM": "Quantum Computing",
    }

    # Action types specific to Digital Europe
    action_types = {
        "SME": "SME Support Action",
        "SIMPLE": "Simple Grant",
        "PCP": "Pre-Commercial Procurement",
        "PPI": "Public Procurement of Innovation",
        "CSA": "Coordination and Support Action",
        "GRANT": "Grant for Identified Beneficiary",
    }

    def extract_from_content(self, content: str, document_title: str = "") -> list[FundingCall]:
        """
        Extract Digital Europe calls from document content.
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
        """Extract details for a single Digital Europe call."""

        title = self._extract_title(content, topic_code)
        if not title or len(title) < 5:
            return None

        call_year = self.extract_year_from_code(topic_code)
        area = self._extract_area(topic_code)
        action_type = self._extract_action_type(content, topic_code)
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

        return FundingCall(
            programme=self.programme,
            topic_code=topic_code,
            title=title,
            programme_part=area,
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
            tags=self._generate_tags(title, scope, area),
            source_document_title=document_title,
            portal_url=self.build_portal_url(topic_code),
        )

    def _extract_title(self, content: str, topic_code: str) -> str:
        """Extract call title from content."""
        pattern = rf"{re.escape(topic_code)}[:\s—–-]+([^\n]+)"
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            title = match.group(1).strip()
            # Clean up
            title = re.sub(r"\s+", " ", title)
            title = re.sub(r"[:\s]+$", "", title)
            if len(title) > 10:
                return title[:200]

        return topic_code

    def _extract_area(self, topic_code: str) -> str:
        """Extract the programme area from topic code."""
        for area_code, area_name in self.areas.items():
            if area_code in topic_code.upper():
                return area_name
        return "Digital Europe"

    def _extract_action_type(self, content: str, topic_code: str) -> str | None:
        """Extract action type for Digital Europe call."""
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            search_content = content
        else:
            search_content = content[max(0, start_idx - 100) : start_idx + 500]

        for action_type in self.action_types.keys():
            if re.search(rf"\b{action_type}\b", search_content, re.IGNORECASE):
                return action_type

        return None

    def _extract_expected_outcome(self, content: str, topic_code: str) -> str | None:
        """Extract expected outcome section."""
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return None

        search_content = content[start_idx : start_idx + 6000]

        patterns = [
            r"Expected\s+(?:Outcome|Impact)[s]?[:\s]+(.{50,1500}?)(?=Scope|Objective|Eligibility|$)",
            r"Objective[s]?[:\s]+(.{50,1200}?)(?=Scope|Activities|$)",
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
            r"Scope[:\s]+(.{50,2500}?)(?=Eligibility|Expected|Budget|$)",
            r"Activities[:\s]+(.{50,2000}?)(?=Eligibility|Budget|$)",
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

        # Budget patterns
        budget_patterns = [
            r"(?:budget|contribution)[:\s]+(?:EUR\s*)?(\d+(?:[.,]\d+)?)\s*(?:million|M)",
            r"EUR\s*(\d+(?:[.,]\d+)?)\s*(?:million|M)",
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

        return result

    def _generate_tags(self, title: str, scope: str | None, area: str) -> list[str]:
        """Generate search tags."""
        tags = ["digital", "europe"]

        # Add area
        if area:
            tags.extend(area.lower().split())

        # Keywords from title
        keywords = re.findall(r"\b[a-zA-Z]{4,}\b", title.lower())
        tags.extend(keywords[:5])

        # Digital-specific terms
        digital_terms = [
            "ai",
            "artificial",
            "intelligence",
            "cloud",
            "cybersecurity",
            "data",
            "hpc",
            "quantum",
            "skills",
            "training",
            "sme",
            "startup",
        ]
        if scope:
            for term in digital_terms:
                if term in scope.lower():
                    tags.append(term)

        return list(set(tags))[:15]

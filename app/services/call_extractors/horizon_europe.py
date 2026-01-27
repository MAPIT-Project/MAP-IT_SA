"""
Horizon Europe Call Extractor

Extracts structured funding call data from Horizon Europe Work Programme documents.
Understands the specific format used in HE Work Programmes (2021-2027).
"""

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any

from .base import CallExtractor, FundingCall

logger = logging.getLogger(__name__)


class HorizonEuropeExtractor(CallExtractor):
    """
    Extractor for Horizon Europe Work Programme documents.

    Horizon Europe (2021-2027) is the EU's main research and innovation programme.
    Topic codes follow the format: HORIZON-{PART}-{YEAR}-{DESTINATION}-{NUMBER}

    Examples:
        - HORIZON-CL5-2026-02-D3-14  (Cluster 5, 2026, Destination 3)
        - HORIZON-EIC-2026-ACCELERATOR-01  (EIC Accelerator)
        - HORIZON-MSCA-2025-PF-01  (Marie Skłodowska-Curie)
        - HORIZON-HLTH-2025-01-CARE-01  (Health cluster)
    """

    programme = "horizon_europe"
    programme_name = "Horizon Europe"

    # Topic code patterns
    # NOTE: All patterns must end with a word boundary or alphanumeric to prevent trailing dashes
    topic_patterns = [
        # Standard cluster format: HORIZON-CL5-2026-02-D3-14 (must end with number or letter)
        re.compile(
            r"HORIZON-CL\d+-\d{4}-\d+-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])",
            re.IGNORECASE,
        ),
        # EIC format: HORIZON-EIC-2026-ACCELERATOR-01
        re.compile(r"HORIZON-EIC-\d{4}-[A-Z]+-\d+", re.IGNORECASE),
        # ERC format: HORIZON-ERC-2026-STG-01 or ERC-2026-STG
        re.compile(r"(?:HORIZON-)?ERC-\d{4}-[A-Z]+(?:-\d+)?(?=\s|:|$|[^\w-])", re.IGNORECASE),
        # MSCA format: HORIZON-MSCA-2025-PF-01
        re.compile(r"HORIZON-MSCA-\d{4}-[A-Z]+-\d+", re.IGNORECASE),
        # Health cluster: HORIZON-HLTH-2025-... (must end with alphanumeric)
        re.compile(
            r"HORIZON-HLTH-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])", re.IGNORECASE
        ),
        # Infrastructure: HORIZON-INFRA-2025-... (must end with alphanumeric)
        re.compile(
            r"HORIZON-INFRA-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])", re.IGNORECASE
        ),
        # Widening: HORIZON-WIDERA-2025-... (must end with alphanumeric)
        re.compile(
            r"HORIZON-WIDERA-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])", re.IGNORECASE
        ),
        # EUSPA: HORIZON-EUSPA-2026-SPACE-... (must end with alphanumeric)
        re.compile(
            r"HORIZON-EUSPA-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])", re.IGNORECASE
        ),
        # Missions: HORIZON-MISS-2026-... (must end with alphanumeric)
        re.compile(
            r"HORIZON-MISS-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])", re.IGNORECASE
        ),
        # EIE: HORIZON-EIE-2026-... (must end with alphanumeric)
        re.compile(
            r"HORIZON-EIE-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])", re.IGNORECASE
        ),
        # Two-stage calls: HORIZON-CL5-2025-01-TWO-STAGE
        re.compile(r"HORIZON-CL\d+-\d{4}-\d+-TWO-STAGE", re.IGNORECASE),
        # Generic fallback (must end with alphanumeric, not dash)
        re.compile(
            r"HORIZON-[A-Z]{2,6}-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*[A-Z0-9](?=\s|:|$|[^\w-])",
            re.IGNORECASE,
        ),
    ]

    # Action types and their full names
    action_types = {
        "RIA": "Research and Innovation Action",
        "IA": "Innovation Action",
        "CSA": "Coordination and Support Action",
        "COFUND": "Co-funded Action",
        "PCP": "Pre-Commercial Procurement",
        "PPI": "Public Procurement of Innovative Solutions",
        "LUMP-SUM": "Lump Sum Grant",
        "ERC-STG": "ERC Starting Grant",
        "ERC-COG": "ERC Consolidator Grant",
        "ERC-ADG": "ERC Advanced Grant",
        "ERC-POC": "ERC Proof of Concept",
        "ERC-SYG": "ERC Synergy Grant",
        "EIC-ACCELERATOR": "EIC Accelerator",
        "EIC-PATHFINDER": "EIC Pathfinder",
        "EIC-TRANSITION": "EIC Transition",
        "MSCA-PF": "MSCA Postdoctoral Fellowship",
        "MSCA-DN": "MSCA Doctoral Network",
        "MSCA-SE": "MSCA Staff Exchange",
        "MSCA-COFUND": "MSCA COFUND",
    }

    # Cluster names
    cluster_names = {
        "CL1": "Health",
        "CL2": "Culture, Creativity and Inclusive Society",
        "CL3": "Civil Security for Society",
        "CL4": "Digital, Industry and Space",
        "CL5": "Climate, Energy and Mobility",
        "CL6": "Food, Bioeconomy, Natural Resources, Agriculture and Environment",
    }

    def extract_from_content(self, content: str, document_title: str = "") -> list[FundingCall]:
        """
        Extract Horizon Europe calls from document content.

        The HE Work Programmes typically have this structure:
        - Topic code followed by colon and title
        - "Expected Outcome:" section
        - "Scope:" section
        - Budget/timing info in tables or inline
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
        """Extract details for a single call."""

        # Extract basic info
        title = self._extract_title(content, topic_code)
        if not title or len(title) < 5:
            return None

        # Extract year and cluster from topic code
        call_year = self.extract_year_from_code(topic_code)
        cluster = self.extract_cluster_from_code(topic_code)

        # Determine programme part
        programme_part = self._determine_programme_part(topic_code)

        # Extract action type
        action_type = self._extract_action_type(content, topic_code)

        # Extract expected outcome and scope
        expected_outcome = self._extract_expected_outcome(content, topic_code)
        scope = self._extract_scope(content, topic_code)

        # Extract budget info
        budget_info = self._extract_budget_info(content, topic_code)

        # Extract deadline
        deadline = self._extract_deadline(content, topic_code, call_year)

        # Determine status based on year
        from datetime import date

        today = date.today()
        if call_year:
            if call_year > today.year:
                status = "upcoming"
            elif call_year == today.year:
                status = "open"  # Could be open or upcoming
            else:
                status = "closed"
        else:
            status = "upcoming"

        # Determine work programme year from document title
        wp_year = self._extract_wp_year(document_title)

        # Build tags
        tags = self._generate_tags(title, scope, expected_outcome, cluster)

        return FundingCall(
            programme=self.programme,
            topic_code=topic_code,
            title=title,
            programme_part=programme_part,
            work_programme_year=wp_year,
            action_type=action_type,
            call_year=call_year,
            deadline=deadline,
            status=status,
            budget_total=budget_info.get("total"),
            budget_per_project_min=budget_info.get("min"),
            budget_per_project_max=budget_info.get("max"),
            expected_projects=budget_info.get("projects"),
            funding_rate=budget_info.get("rate"),
            expected_outcome=expected_outcome,
            scope=scope,
            cluster=cluster,
            destination=self.cluster_names.get(cluster, ""),
            tags=tags,
            source_document_title=document_title,
            portal_url=self.build_portal_url(topic_code),
        )

    def _extract_title(self, content: str, topic_code: str) -> str:
        """Extract call title from content."""
        # Pattern: HORIZON-CL5-2026-02-D3-14: Title of the call
        pattern = rf"{re.escape(topic_code)}[:\s]+([^\n\.]+)"
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            title = match.group(1).strip()
            # Clean up the title
            title = self._clean_title(title)
            if len(title) > 10:
                return title

        return topic_code  # Fallback to topic code

    def _clean_title(self, title: str) -> str:
        """Clean extracted title."""
        # Remove action type at the start
        title = re.sub(r"^(RIA|IA|CSA|COFUND)\s+[\d\.]+\s*", "", title)

        # Remove "Call: Cluster..." pattern
        title = re.sub(r"\s*Call:\s*Cluster.*$", "", title, flags=re.IGNORECASE)

        # Remove budget info
        title = re.sub(r"\s*[\d\.]+\s*(Around|million|EUR).*$", "", title, flags=re.IGNORECASE)

        # Remove dots and clean
        title = re.sub(r"\.{3,}", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        title = re.sub(r"[:\s]+$", "", title)

        # Truncate if too long
        if len(title) > 150:
            title = title[:150]
            last_space = title.rfind(" ")
            if last_space > 100:
                title = title[:last_space]
            title += "..."

        return title

    def _determine_programme_part(self, topic_code: str) -> str:
        """Determine which part of HE this call belongs to."""
        code_upper = topic_code.upper()

        if "EIC" in code_upper:
            return "European Innovation Council (EIC)"
        elif "ERC" in code_upper:
            return "European Research Council (ERC)"
        elif "MSCA" in code_upper:
            return "Marie Skłodowska-Curie Actions (MSCA)"
        elif "INFRA" in code_upper:
            return "Research Infrastructures"
        elif "WIDERA" in code_upper:
            return "Widening Participation and Strengthening the ERA"
        elif "HLTH" in code_upper:
            return "Cluster 1: Health"
        elif "CL1" in code_upper:
            return "Cluster 1: Health"
        elif "CL2" in code_upper:
            return "Cluster 2: Culture, Creativity and Inclusive Society"
        elif "CL3" in code_upper:
            return "Cluster 3: Civil Security for Society"
        elif "CL4" in code_upper:
            return "Cluster 4: Digital, Industry and Space"
        elif "CL5" in code_upper:
            return "Cluster 5: Climate, Energy and Mobility"
        elif "CL6" in code_upper:
            return "Cluster 6: Food, Bioeconomy, Natural Resources"
        else:
            return "Horizon Europe"

    def _extract_action_type(self, content: str, topic_code: str) -> str | None:
        """Extract action type for a call."""
        # Look near the topic code
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            search_content = content
        else:
            search_content = content[max(0, start_idx - 100) : start_idx + 500]

        # Check for action types in order of specificity
        for action_type in [
            "ERC-STG",
            "ERC-COG",
            "ERC-ADG",
            "ERC-POC",
            "ERC-SYG",
            "EIC-ACCELERATOR",
            "EIC-PATHFINDER",
            "EIC-TRANSITION",
            "MSCA-PF",
            "MSCA-DN",
            "MSCA-SE",
            "MSCA-COFUND",
            "LUMP-SUM",
            "COFUND",
            "PCP",
            "PPI",
            "RIA",
            "IA",
            "CSA",
        ]:
            pattern = rf"\b{re.escape(action_type)}\b"
            if re.search(pattern, search_content, re.IGNORECASE):
                return action_type

        # Check topic code for hints
        if "EIC" in topic_code.upper():
            if "ACCELERATOR" in topic_code.upper():
                return "EIC-Accelerator"
            elif "PATHFINDER" in topic_code.upper():
                return "EIC-Pathfinder"
            elif "TRANSITION" in topic_code.upper():
                return "EIC-Transition"
        elif "ERC" in topic_code.upper():
            if "STG" in topic_code.upper():
                return "ERC-STG"
            elif "COG" in topic_code.upper():
                return "ERC-COG"
            elif "ADG" in topic_code.upper():
                return "ERC-ADG"
        elif "MSCA" in topic_code.upper():
            if "PF" in topic_code.upper():
                return "MSCA-PF"
            elif "DN" in topic_code.upper():
                return "MSCA-DN"

        return None

    def _extract_expected_outcome(self, content: str, topic_code: str) -> str | None:
        """
        Extract the Expected Outcome section for a call.

        Strategy: Search entire document for the topic code's detailed section,
        which may be far from the first mention (e.g., table of contents).
        """
        # Find ALL occurrences of the topic code
        topic_upper = topic_code.upper()
        content_upper = content.upper()

        # Look for the detailed section (usually after title on its own line)
        # Pattern: "HORIZON-CL5-2025-...: Title\nExpected Outcome..."
        detail_pattern = rf"{re.escape(topic_code)}[:\s]+[^\n]+\n.*?Expected\s+Outcome"
        detail_match = re.search(detail_pattern, content, re.IGNORECASE | re.DOTALL)

        if detail_match:
            start_idx = detail_match.start()
        else:
            # Fall back to first occurrence
            start_idx = content_upper.find(topic_upper)
            if start_idx == -1:
                return None

        # Search for "Expected Outcome" in this section
        search_content = content[start_idx : start_idx + 8000]

        patterns = [
            # Standard format: "Expected Outcome: ..."
            r"Expected\s+Outcome[s]?[:\s]+(.{50,2000}?)(?=Scope[:\s]|Legal\s+and|Eligibility|HORIZON-[A-Z]|$)",
            # Alternative: "Project results are expected to contribute..."
            r"Project\s+results\s+are\s+expected\s+to\s+contribute\s+to[:\s]*(.{50,1500}?)(?=Scope[:\s]|$)",
            # Bullet point format
            r"Expected\s+Outcome[s]?[:\s]*\n(.{50,2000}?)(?=Scope|Legal|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, search_content, re.IGNORECASE | re.DOTALL)
            if match:
                outcome = self.clean_text(match.group(1), max_length=1500)
                if len(outcome) > 30:
                    return outcome

        return None

    def _extract_scope(self, content: str, topic_code: str) -> str | None:
        """
        Extract the Scope section for a call.

        The Scope section describes what the project should do.
        """
        # Find ALL occurrences of the topic code
        topic_upper = topic_code.upper()
        content_upper = content.upper()

        # Look for the detailed section with Scope
        detail_pattern = rf"{re.escape(topic_code)}.*?Scope[:\s]"
        detail_match = re.search(detail_pattern, content, re.IGNORECASE | re.DOTALL)

        if detail_match:
            start_idx = detail_match.start()
        else:
            start_idx = content_upper.find(topic_upper)
            if start_idx == -1:
                return None

        # Search for "Scope:" in this section
        search_content = content[start_idx : start_idx + 10000]

        patterns = [
            # Standard format: "Scope: ..."
            r"Scope[:\s]+(.{50,3000}?)(?=Legal\s+and\s+financial|Eligibility|Specific\s+conditions|Technology\s+Readiness|HORIZON-[A-Z]|$)",
            # Alternative formats
            r"Scope[:\s]*\n(.{50,2500}?)(?=Legal|Eligibility|Technology|$)",
            # "Activities are expected to..."
            r"(?:Scope[:\s]*)?Activities\s+(?:are\s+)?expected\s+to[:\s]*(.{50,2000}?)(?=Legal|Eligibility|$)",
            # "Proposals should/must..."
            r"Proposals\s+(?:should|must|are\s+expected\s+to)[:\s]*(.{50,2000}?)(?=Legal|Eligibility|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, search_content, re.IGNORECASE | re.DOTALL)
            if match:
                scope = self.clean_text(match.group(1), max_length=2500)
                if len(scope) > 30:
                    return scope

        return None

    def _extract_budget_info(self, content: str, topic_code: str) -> dict[str, Any]:
        """
        Extract budget information for a call.

        Looks for:
        - Total budget for the topic
        - Budget per project (min/max)
        - Expected number of projects
        - Funding rate
        """
        result = {}

        # Find content around the topic code
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return result

        # Look in a wider range - budget info can be before or after
        search_start = max(0, start_idx - 500)
        search_content = content[search_start : start_idx + 3000]

        # Budget patterns - more comprehensive
        budget_patterns = [
            # "indicative budget of EUR 10.00 million"
            r"(?:indicative\s+)?budget[:\s]+(?:of\s+)?(?:EUR\s*)?(\d+(?:[.,]\d+)?)\s*(?:million|M\b)",
            # "EUR 10 million" standalone
            r"\bEUR\s*(\d+(?:[.,]\d+)?)\s*(?:million|M\b)",
            # "10.00 million EUR"
            r"(\d+(?:[.,]\d+)?)\s*(?:million|M)\s*EUR",
            # "contribution of EUR 10M"
            r"contribution[:\s]+(?:of\s+)?(?:EUR\s*)?(\d+(?:[.,]\d+)?)\s*(?:million|M\b)",
            # In tables: "10.00" followed by "million" context
            r"(\d+(?:[.,]\d+)?)\s+(?:million|M\b)",
        ]

        for pattern in budget_patterns:
            matches = re.findall(pattern, search_content, re.IGNORECASE)
            for match in matches:
                try:
                    # Handle European number format (comma as decimal)
                    amount_str = match.replace(",", ".")
                    amount = float(amount_str)
                    # Only accept reasonable budget amounts (0.5M - 500M)
                    if 0.5 <= amount <= 500:
                        result["total"] = Decimal(str(amount * 1_000_000))
                        break
                except ValueError:
                    continue
            if "total" in result:
                break

        # Budget per project patterns
        per_project_patterns = [
            r"(?:around|approximately|up\s+to)\s+(?:EUR\s*)?(\d+(?:[.,]\d+)?)\s*(?:million|M)",
            r"per\s+project[:\s]+(?:EUR\s*)?(\d+(?:[.,]\d+)?)\s*(?:million|M)",
            r"(\d+(?:[.,]\d+)?)\s+to\s+(\d+(?:[.,]\d+)?)\s*(?:million|M)",  # Range
        ]

        for pattern in per_project_patterns:
            match = re.search(pattern, search_content, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 2 and groups[1]:  # Range
                        result["min"] = Decimal(str(float(groups[0].replace(",", ".")) * 1_000_000))
                        result["max"] = Decimal(str(float(groups[1].replace(",", ".")) * 1_000_000))
                    else:
                        result["max"] = Decimal(str(float(groups[0].replace(",", ".")) * 1_000_000))
                    break
                except (ValueError, IndexError):
                    continue

        # Expected projects: "Around 2", "Expected: 3", "2-3 projects"
        projects_patterns = [
            r"Around\s+(\d+)",
            r"(?:expected|indicative)[:\s]+(\d+)\s*(?:project|grant)",
            r"(\d+)\s*(?:to|-)\s*(\d+)\s*project",
            r"number\s+of\s+projects[:\s]+(\d+)",
        ]

        for pattern in projects_patterns:
            match = re.search(pattern, search_content, re.IGNORECASE)
            if match:
                try:
                    result["projects"] = int(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue

        # Funding rate: "100%", "70%", "funding rate of 100%"
        rate_patterns = [
            r"funding\s+rate[:\s]+(?:of\s+)?(?:up\s+to\s+)?(\d+)\s*%",
            r"(\d+)\s*%\s*(?:funding|of\s+eligible\s+costs)",
            r"rate[:\s]+(\d+)\s*%",
        ]

        for pattern in rate_patterns:
            match = re.search(pattern, search_content, re.IGNORECASE)
            if match:
                try:
                    rate = int(match.group(1))
                    if 1 <= rate <= 100:
                        result["rate"] = rate
                        break
                except ValueError:
                    continue

        return result

    def _extract_deadline(
        self, content: str, topic_code: str, call_year: int | None
    ) -> date | None:
        """Extract deadline for a call."""

        # Find content near the topic code
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return None

        search_content = content[max(0, start_idx - 500) : start_idx + 2000]

        # Deadline patterns
        patterns = [
            r"[Dd]eadline\(?s?\)?[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            r"[Cc]loses?[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, search_content)
            for match in matches:
                parsed = self.parse_date(match)
                if parsed:
                    # Validate year makes sense
                    if call_year and parsed.year >= call_year - 1 and parsed.year <= call_year + 1:
                        return parsed
                    elif not call_year and parsed.year >= 2024:
                        return parsed

        return None

    def _extract_wp_year(self, document_title: str) -> int | None:
        """Extract Work Programme year from document title."""
        match = re.search(r"20(2[3-9]|3[0-9])", document_title)
        return int(match.group(0)) if match else None

    def _generate_tags(
        self, title: str, scope: str | None, outcome: str | None, cluster: str | None
    ) -> list[str]:
        """Generate search tags from call content."""
        tags = []

        # Add cluster tag
        if cluster:
            tags.append(cluster.lower())
            if cluster in self.cluster_names:
                # Add keywords from cluster name
                for word in self.cluster_names[cluster].lower().split():
                    if len(word) > 3:
                        tags.append(word)

        # Extract keywords from title
        title_words = re.findall(r"\b[a-zA-Z]{4,}\b", title.lower())
        tags.extend(title_words[:5])

        # Add some common terms if found in scope
        if scope:
            common_terms = [
                "energy",
                "climate",
                "digital",
                "health",
                "ai",
                "hydrogen",
                "battery",
                "renewable",
                "sustainable",
                "innovation",
                "transport",
                "mobility",
                "security",
                "cybersecurity",
                "agriculture",
                "food",
                "biodiversity",
                "ocean",
                "circular",
                "manufacturing",
                "space",
            ]
            for term in common_terms:
                if term in scope.lower():
                    tags.append(term)

        # Deduplicate and return
        return list(set(tags))[:15]

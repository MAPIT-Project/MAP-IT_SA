"""
Base Call Extractor

Abstract base class for extracting structured call data from Work Programme documents.
Each EU funding programme should implement its own extractor.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from re import Pattern
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FundingCall:
    """
    Represents a structured funding call extracted from a Work Programme.

    This is the common data structure for all EU funding programmes.
    Programme-specific data goes in the `metadata` field.
    """

    # Required fields
    programme: str  # 'horizon_europe', 'digital_europe', etc.
    topic_code: str  # e.g., 'HORIZON-CL5-2026-02-D3-14'
    title: str  # Call title

    # Optional identification
    call_identifier: str | None = None  # Parent call ID
    programme_part: str | None = None  # 'Cluster 5', 'Pillar II', etc.
    work_programme_year: int | None = None  # Year of Work Programme

    # Action type
    action_type: str | None = None  # 'RIA', 'IA', 'CSA', etc.

    # Dates
    call_year: int | None = None  # Year from topic code
    opening_date: date | None = None
    deadline: date | None = None
    second_stage_deadline: date | None = None

    # Status
    status: str = "upcoming"  # 'open', 'upcoming', 'closed'

    # Financial info
    budget_total: Decimal | None = None
    budget_per_project_min: Decimal | None = None
    budget_per_project_max: Decimal | None = None
    expected_projects: int | None = None
    funding_rate: int | None = None  # Percentage, e.g., 100 for RIA

    # Content
    expected_outcome: str | None = None
    scope: str | None = None
    eligibility: str | None = None

    # Classification
    cluster: str | None = None  # 'CL1', 'CL2', etc.
    destination: str | None = None
    tags: list[str] = field(default_factory=list)

    # Source tracking
    source_document_id: str | None = None
    source_document_title: str | None = None
    source_page_number: int | None = None

    # Portal URL
    portal_url: str | None = None

    # Flexible metadata for programme-specific data
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        data = asdict(self)
        # Convert date objects to strings
        for key in ["opening_date", "deadline", "second_stage_deadline"]:
            if data[key] is not None:
                data[key] = data[key].isoformat()
        # Convert Decimal to float
        for key in ["budget_total", "budget_per_project_min", "budget_per_project_max"]:
            if data[key] is not None:
                data[key] = float(data[key])
        return data

    def is_valid(self) -> bool:
        """Check if the call has minimum required data."""
        if not (self.programme and self.topic_code and self.title):
            return False

        # Title must be meaningful (not just the topic code, not garbled)
        if len(self.title) < 10:
            return False
        if self.title.upper().startswith("HORIZON-") and len(self.title) < 50:
            return False  # Title is just the topic code
        if re.match(
            r"^(Overview of|Topics Type|Proposals are|EUR\s+million|\d+\s+Proposals)",
            self.title,
            re.IGNORECASE,
        ):
            return False  # Garbled title from PDF extraction

        # Topic code must not end with a dash (incomplete)
        if self.topic_code.endswith("-"):
            return False

        # Topic code must have a year
        if not re.search(r"-\d{4}-", self.topic_code):
            return False

        return True


class CallExtractor(ABC):
    """
    Abstract base class for extracting funding calls from Work Programme documents.

    Each EU programme (Horizon Europe, Digital Europe, LIFE, etc.) should have
    its own implementation that understands the specific document format.

    Usage:
        extractor = HorizonEuropeExtractor(db_connection)
        calls = extractor.extract_from_chunks(chunks)
        extractor.save_calls(calls)
    """

    # Override these in subclasses
    programme: str = "unknown"
    programme_name: str = "Unknown Programme"

    # Topic code patterns to look for
    topic_patterns: list[Pattern] = []

    # Action types recognized by this programme
    action_types: dict[str, str] = {}

    def __init__(self, db_connection=None):
        """
        Initialize the extractor.

        Args:
            db_connection: Database connection for saving extracted calls.
                          If None, calls must be saved manually.
        """
        self.db = db_connection
        self.extracted_calls: list[FundingCall] = []
        logger.info(f"Initialized {self.programme_name} extractor")

    @abstractmethod
    def extract_from_content(self, content: str, document_title: str = "") -> list[FundingCall]:
        """
        Extract funding calls from document content.

        Args:
            content: Full text content of the document
            document_title: Title of the source document

        Returns:
            List of FundingCall objects
        """
        pass

    def extract_from_chunks(
        self, chunks: list[dict[str, Any]], document_title: str = ""
    ) -> list[FundingCall]:
        """
        Extract funding calls from a list of document chunks.

        Args:
            chunks: List of chunk dictionaries with 'content' field
            document_title: Title of the source document

        Returns:
            List of FundingCall objects
        """
        all_calls = []
        seen_codes = set()

        for chunk in chunks:
            content = chunk.get("content", "")
            page_num = chunk.get("page_number")

            calls = self.extract_from_content(content, document_title)

            for call in calls:
                # Deduplicate by topic code
                if call.topic_code in seen_codes:
                    continue
                seen_codes.add(call.topic_code)

                # Add page number if available
                if page_num and not call.source_page_number:
                    call.source_page_number = page_num

                all_calls.append(call)

        logger.info(f"Extracted {len(all_calls)} unique calls from {len(chunks)} chunks")
        self.extracted_calls = all_calls
        return all_calls

    def save_calls(self, calls: list[FundingCall] = None) -> int:
        """
        Save extracted calls to the database.

        Args:
            calls: List of calls to save. If None, uses self.extracted_calls

        Returns:
            Number of calls saved
        """
        if self.db is None:
            raise ValueError("No database connection provided")

        calls = calls or self.extracted_calls
        if not calls:
            logger.warning("No calls to save")
            return 0

        saved_count = 0
        cursor = self.db.cursor()

        for call in calls:
            if not call.is_valid():
                logger.warning(f"Skipping invalid call: {call.topic_code}")
                continue

            try:
                data = call.to_dict()

                # Build INSERT statement
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))

                # Upsert: update if topic_code exists
                query = f"""
                    INSERT INTO funding_calls ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT (topic_code) DO UPDATE SET
                        title = EXCLUDED.title,
                        action_type = EXCLUDED.action_type,
                        deadline = EXCLUDED.deadline,
                        status = EXCLUDED.status,
                        budget_total = EXCLUDED.budget_total,
                        expected_outcome = EXCLUDED.expected_outcome,
                        scope = EXCLUDED.scope,
                        updated_at = NOW()
                """

                cursor.execute(query, list(data.values()))
                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save call {call.topic_code}: {e}")
                continue

        self.db.commit()
        logger.info(f"Saved {saved_count} calls to database")
        return saved_count

    # =========================================================================
    # Helper methods for subclasses
    # =========================================================================

    def find_topic_codes(self, content: str) -> list[str]:
        """Find all topic codes in content using the programme's patterns."""
        codes = []
        for pattern in self.topic_patterns:
            matches = pattern.findall(content)
            codes.extend(matches)
        return list(set(codes))  # Deduplicate

    def extract_year_from_code(self, topic_code: str) -> int | None:
        """Extract year from topic code like HORIZON-CL5-2026-... -> 2026"""
        match = re.search(r"20(2[0-9]|3[0-9])", topic_code)
        return int(match.group(0)) if match else None

    def extract_cluster_from_code(self, topic_code: str) -> str | None:
        """Extract cluster from topic code like HORIZON-CL5-... -> CL5"""
        match = re.search(r"CL(\d+)", topic_code, re.IGNORECASE)
        return f"CL{match.group(1)}" if match else None

    def parse_date(self, date_str: str) -> date | None:
        """Parse various date formats to date object."""
        if not date_str:
            return None

        # Try different formats
        formats = [
            "%d %B %Y",  # "04 September 2025"
            "%d %b %Y",  # "04 Sep 2025"
            "%Y-%m-%d",  # "2025-09-04"
            "%d/%m/%Y",  # "04/09/2025"
            "%d.%m.%Y",  # "04.09.2025"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def parse_budget(self, budget_str: str) -> Decimal | None:
        """Parse budget string to Decimal."""
        if not budget_str:
            return None

        # Remove currency symbols and words
        clean = re.sub(r"[€$EUR]", "", budget_str, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", "", clean)

        # Handle millions/billions
        multiplier = 1
        if "million" in budget_str.lower() or "m" in clean.lower():
            multiplier = 1_000_000
            clean = re.sub(r"[mM](?:illion)?", "", clean)
        elif "billion" in budget_str.lower() or "b" in clean.lower():
            multiplier = 1_000_000_000
            clean = re.sub(r"[bB](?:illion)?", "", clean)

        # Extract number
        match = re.search(r"[\d,.]+", clean)
        if match:
            try:
                value = float(match.group().replace(",", ""))
                return Decimal(str(value * multiplier))
            except ValueError:
                pass

        return None

    def clean_text(self, text: str, max_length: int = 5000) -> str:
        """Clean extracted text."""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Remove page markers
        text = re.sub(r"\[Page \d+\]", "", text)
        text = re.sub(r"Part \d+ - Page \d+ of \d+", "", text)

        # Remove dots used for table of contents
        text = re.sub(r"\.{3,}", "", text)

        # Clean up again
        text = re.sub(r"\s+", " ", text).strip()

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text

    def build_portal_url(self, topic_code: str) -> str:
        """Build EU portal URL for a topic code."""
        base_url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details"
        return f"{base_url}/{topic_code}"

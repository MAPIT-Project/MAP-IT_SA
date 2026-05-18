# Adding New EU Funding Programmes

This guide explains how to add support for additional EU funding programmes beyond Horizon Europe.

## Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  funding_calls table (PostgreSQL)                           │
│  - Stores structured call data from ALL programmes          │
│  - Full-text search enabled                                 │
│  - Programme-agnostic design                                │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ extracts to
┌─────────────────────────────────────────────────────────────┐
│  CallExtractor (base class)                                 │
│  └── HorizonEuropeExtractor                                 │
│  └── DigitalEuropeExtractor (to be created)                │
│  └── LIFEExtractor (to be created)                         │
│  └── ... more extractors                                    │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ parses
┌─────────────────────────────────────────────────────────────┐
│  Work Programme PDFs                                        │
│  - Downloaded from official EU sources                      │
│  - Ingested into horizon_documents + document_chunks        │
└─────────────────────────────────────────────────────────────┘
```

## Supported Programmes

| Programme | Status | Extractor |
|-----------|--------|-----------|
| Horizon Europe | ✅ Implemented | `HorizonEuropeExtractor` |
| Digital Europe | 📋 Planned | `DigitalEuropeExtractor` |
| LIFE | 📋 Planned | `LIFEExtractor` |
| Creative Europe | 📋 Planned | `CreativeEuropeExtractor` |
| Erasmus+ | 📋 Planned | `ErasmusExtractor` |
| European Defence Fund | 📋 Planned | `EDFExtractor` |
| CEF (Connecting Europe) | 📋 Planned | `CEFExtractor` |
| Interreg | 📋 Planned | `InterregExtractor` |

---

## Step-by-Step: Adding a New Programme

### 1. Download Work Programme Documents

First, find and download the official Work Programme PDFs:

| Programme | Source |
|-----------|--------|
| **Digital Europe** | https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/digital |
| **LIFE** | https://cinea.ec.europa.eu/programmes/life_en |
| **Creative Europe** | https://culture.ec.europa.eu/creative-europe |
| **Erasmus+** | https://erasmus-plus.ec.europa.eu/ |
| **EDF** | https://defence-industry-space.ec.europa.eu/eu-defence-industry/european-defence-fund-edf_en |
| **CEF** | https://cinea.ec.europa.eu/programmes/connecting-europe-facility_en |

Save documents to: `data/work_programmes/{programme_name}/`

### 2. Create the Extractor Class

Create a new file: `app/services/call_extractors/{programme_name}.py`

```python
"""
{Programme Name} Call Extractor

Extracts structured funding call data from {Programme Name} Work Programme documents.
"""

import logging
import re
from typing import List, Optional

from .base import CallExtractor, FundingCall

logger = logging.getLogger(__name__)


class {ProgrammeName}Extractor(CallExtractor):
    """
    Extractor for {Programme Name} Work Programme documents.
    """

    programme = "{programme_id}"  # e.g., "digital_europe"
    programme_name = "{Programme Full Name}"  # e.g., "Digital Europe Programme"

    # Topic code patterns - CUSTOMIZE THIS
    topic_patterns = [
        re.compile(r'DIGITAL-\d{4}-[A-Z0-9-]+', re.IGNORECASE),
        # Add more patterns as needed
    ]

    # Action types for this programme
    action_types = {
        'SME': 'SME Support Action',
        'GRANT': 'Grant',
        # Add programme-specific action types
    }

    def extract_from_content(self, content: str, document_title: str = "") -> List[FundingCall]:
        """
        Extract calls from document content.

        CUSTOMIZE this method based on the document structure.
        """
        calls = []

        # Find all topic codes
        topic_codes = self.find_topic_codes(content)

        for topic_code in topic_codes:
            topic_code = topic_code.upper()

            # Extract call details (customize these methods)
            title = self._extract_title(content, topic_code)
            if not title or len(title) < 5:
                continue

            call = FundingCall(
                programme=self.programme,
                topic_code=topic_code,
                title=title,
                action_type=self._extract_action_type(content, topic_code),
                call_year=self.extract_year_from_code(topic_code),
                expected_outcome=self._extract_expected_outcome(content, topic_code),
                scope=self._extract_scope(content, topic_code),
                portal_url=self.build_portal_url(topic_code),
                source_document_title=document_title,
            )

            if call.is_valid():
                calls.append(call)

        return calls

    def _extract_title(self, content: str, topic_code: str) -> str:
        """Extract call title - CUSTOMIZE based on document format."""
        pattern = rf'{re.escape(topic_code)}[:\s]+([^\n\.]+)'
        match = re.search(pattern, content, re.IGNORECASE)
        return match.group(1).strip() if match else topic_code

    def _extract_action_type(self, content: str, topic_code: str) -> Optional[str]:
        """Extract action type - CUSTOMIZE for programme."""
        for action_type in self.action_types.keys():
            if action_type in content:
                return action_type
        return None

    def _extract_expected_outcome(self, content: str, topic_code: str) -> Optional[str]:
        """Extract expected outcome section."""
        # Similar to HorizonEuropeExtractor - adjust patterns as needed
        return None

    def _extract_scope(self, content: str, topic_code: str) -> Optional[str]:
        """Extract scope section."""
        # Similar to HorizonEuropeExtractor - adjust patterns as needed
        return None
```

### 3. Register the Extractor

Update `app/services/call_extractors/__init__.py`:

```python
from .base import CallExtractor, FundingCall
from .horizon_europe import HorizonEuropeExtractor
from .digital_europe import DigitalEuropeExtractor  # NEW

__all__ = [
    'CallExtractor',
    'FundingCall',
    'HorizonEuropeExtractor',
    'DigitalEuropeExtractor',  # NEW
]
```

### 4. Add Programme to Database Constraint

Update `scripts/create_funding_calls_table.sql`:

```sql
CONSTRAINT valid_programme CHECK (programme IN (
    'horizon_europe',
    'horizon_plus',
    'digital_europe',  -- Already included
    'life',
    'creative_europe',
    'edf',
    'euratom',
    'erasmus',
    'cef',
    'interreg',
    'your_new_programme',  -- ADD NEW ONES HERE
    'other'
)),
```

### 5. Ingest the Documents

```bash
# Ingest the Work Programme PDFs
cd NEWMAPIT/MAP-IT_SA
source venv/bin/activate

# Add documents to the database
python scripts/ingest_newdocs.py --input data/work_programmes/digital_europe/

# Extract structured calls
python scripts/extract_funding_calls.py --programme digital_europe
```

### 6. Test the New Programme

```python
from app.services.local_call_search_service import LocalCallSearchService

service = LocalCallSearchService()

# Search across all programmes
results = service.search_calls("cybersecurity", num_results=10)

# Search specific programme
results = service.search_calls(
    "AI training",
    num_results=10,
    # Add programme filter when implemented
)
```

---

## Programme-Specific Notes

### Digital Europe Programme (DIGITAL)

**Topic Code Format:** `DIGITAL-{YEAR}-{AREA}-{NUMBER}`
- Example: `DIGITAL-2024-CLOUD-AI-04`

**Areas:**
- CLOUD-AI: Cloud and AI
- CYBER: Cybersecurity
- SKILLS: Advanced Digital Skills
- DEPLOY: Deployment/Best Use
- EDIH: European Digital Innovation Hubs

**Work Programme Source:**
https://digital-strategy.ec.europa.eu/en/activities/work-programmes-digital

### LIFE Programme

**Topic Code Format:** `LIFE-{YEAR}-{STRAND}-{TYPE}`
- Example: `LIFE-2024-SAP-ENV`

**Strands:**
- SAP: Standard Action Projects
- TA: Technical Assistance
- PLP: Preparatory Projects
- SGA: Sub-grants

**Sub-programmes:**
- ENV: Environment
- CLIMA: Climate Action
- CET: Clean Energy Transition
- NAT: Nature & Biodiversity

**Work Programme Source:**
https://cinea.ec.europa.eu/programmes/life/life-calls-proposals_en

### Creative Europe

**Topic Code Format:** `CREA-{STRAND}-{YEAR}-{ACTION}`
- Example: `CREA-MEDIA-2024-TRAINING`

**Strands:**
- MEDIA: Audiovisual sector
- CULT: Culture
- CROSS: Cross-sectoral

### European Defence Fund (EDF)

**Topic Code Format:** `EDF-{YEAR}-{CATEGORY}-{NUMBER}`
- Example: `EDF-2024-RA-CYBER-DSEC`

**Categories:**
- RA: Research Actions
- DA: Development Actions

---

## Best Practices

1. **Study the Document Format First**
   - Download sample Work Programmes
   - Identify topic code patterns
   - Note section headers (Scope, Expected Outcome, Budget, etc.)

2. **Test with Sample Content**
   ```python
   extractor = YourExtractor()
   sample = "TOPIC-CODE-123: Sample Title\nScope: This is the scope..."
   calls = extractor.extract_from_content(sample, "Test Document")
   print(calls)
   ```

3. **Handle Edge Cases**
   - Multi-stage calls
   - Calls without deadlines
   - Budget ranges vs fixed amounts

4. **Validate Results**
   - Compare extracted data with official portal
   - Check for missing fields
   - Verify topic code formats

---

## Quick Reference: Files to Modify

| Task | File |
|------|------|
| New extractor class | `app/services/call_extractors/{programme}.py` |
| Register extractor | `app/services/call_extractors/__init__.py` |
| Database constraint | `scripts/create_funding_calls_table.sql` |
| Extraction script | `scripts/extract_funding_calls.py` (if needed) |

---

## Getting Help

- Check existing `HorizonEuropeExtractor` for reference implementation
- Review Work Programme PDF structure before writing patterns
- Test extraction on small samples first

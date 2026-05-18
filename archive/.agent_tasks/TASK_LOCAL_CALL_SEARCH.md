# TASK: Implement Local-Only Call Search

## Objective
Replace the external API-based call search with a local-only search that uses ingested Work Programme documents. The user explicitly does not want to rely on external APIs.

## Background

### Current State (BAD)
- `ImprovedCallSearchService` makes requests to `https://api.tech.ec.europa.eu/search-api/prod/rest/search`
- User had issues with the API not working reliably
- User wants to use local Work Programme PDFs for all call information

### Desired State (GOOD)
- All call information comes from locally ingested Work Programme documents
- No external API calls
- Fast, reliable, offline-capable search
- Comprehensive coverage of all Horizon Europe calls

## Available Local Data

The following Work Programmes are ingested into the vector database:

```
2025_work_programmes/
├── wp-1-general-introduction_horizon-2025_en.pdf
├── wp-3-research-infrastructures_horizon-2025_en.pdf
├── wp-4-health_horizon-2025_en.pdf (Cluster 1)
├── wp-5-culture-creativity-and-inclusive-society_horizon-2025_en.pdf (Cluster 2)
├── wp-6-civil-security-for-society_horizon-2025_en.pdf (Cluster 3)
├── wp-7-digital-industry-and-space_horizon-2025_en.pdf (Cluster 4)
├── wp-8-climate-energy-and-mobility_horizon-2025_en.pdf (Cluster 5)
├── wp-9-food-bioeconomy-natural-resources-agriculture-and-environment_horizon-2025_en.pdf (Cluster 6)
├── wp-10-european-innovation-ecosystems_horizon-2025_en.pdf
├── wp-11-widening-participation-and-strengthening-the-european-research-area_horizon-2025_en.pdf
├── wp-12-missions_horizon-2025_en.pdf
├── wp-13-new-european-bauhaus-facility_horizon-2025_en.pdf
└── wp-14-general-annexes_horizon-2025_en.pdf

EIC Work Programme 2026/
└── EIC-Work-Programme-2026.pdf

ERC Work Programme 2026/
├── wp_horizon-erc-2026_en.pdf
└── roc_horizon-erc-2026-pera_en.pdf
```

## Implementation Steps

### Step 1: Create LocalCallSearchService

Create `app/services/local_call_search_service.py`:

```python
"""
Local Call Search Service

Searches for funding calls using locally ingested Work Programme documents.
No external API dependency.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .vector_search_service import VectorSearchService
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class LocalCallResult:
    """Represents a call/topic found in local documents."""
    topic_code: Optional[str]
    title: str
    description: str
    source_document: str
    work_programme: str
    cluster: Optional[str]
    action_type: Optional[str]  # RIA, IA, CSA, etc.
    budget: Optional[str]
    deadline: Optional[str]
    relevance_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'topic_code': self.topic_code,
            'title': self.title,
            'description': self.description,
            'source_document': self.source_document,
            'work_programme': self.work_programme,
            'cluster': self.cluster,
            'action_type': self.action_type,
            'budget': self.budget,
            'deadline': self.deadline,
            'relevance_score': self.relevance_score
        }


class LocalCallSearchService:
    """
    Service to search for Horizon Europe calls using local Work Programme documents.
    """

    # Patterns to extract call information
    TOPIC_CODE_PATTERN = r'HORIZON-[A-Z0-9]+-\d{4}-[A-Z0-9-]+'
    ERC_CODE_PATTERN = r'ERC-\d{4}-[A-Z]+'
    EIC_CODE_PATTERN = r'HORIZON-EIC-\d{4}-[A-Z]+-\d+'

    # Action type patterns
    ACTION_TYPES = {
        'RIA': r'\bRIA\b|Research and Innovation Action',
        'IA': r'\bIA\b|Innovation Action',
        'CSA': r'\bCSA\b|Coordination and Support Action',
        'COFUND': r'\bCOFUND\b|Co-fund',
        'MSCA': r'\bMSCA\b|Marie Sk',
        'ERC': r'\bERC\b|European Research Council',
        'EIC': r'\bEIC\b|European Innovation Council',
    }

    # Cluster mapping
    CLUSTER_KEYWORDS = {
        'CL1': ['health', 'cancer', 'pandemic', 'infectious disease', 'mental health'],
        'CL2': ['culture', 'creativity', 'inclusive', 'democracy', 'heritage'],
        'CL3': ['security', 'cybersecurity', 'disaster', 'border', 'crime'],
        'CL4': ['digital', 'AI', 'data', 'industry', 'space', 'manufacturing'],
        'CL5': ['climate', 'energy', 'mobility', 'transport', 'battery', 'hydrogen'],
        'CL6': ['food', 'bioeconomy', 'agriculture', 'biodiversity', 'environment'],
    }

    def __init__(self):
        """Initialize the local call search service."""
        self.vector_service = VectorSearchService()
        logger.info("✅ LocalCallSearchService initialized (using local documents only)")

    def search_calls(
        self,
        query: str,
        num_results: int = 10,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for calls matching the query in local Work Programme documents.

        Args:
            query: Search query (e.g., "clean energy", "hydrogen", "AI healthcare")
            num_results: Maximum number of results to return
            cluster: Optional filter by cluster (CL1-CL6)
            action_type: Optional filter by action type (RIA, IA, CSA, etc.)

        Returns:
            Dict with 'calls' list and 'search_metadata'
        """
        logger.info(f"🔍 Searching local documents for: '{query}'")

        # Build enhanced query
        enhanced_query = self._enhance_query(query, cluster)

        # Search vector database
        results = self.vector_service.hybrid_search(
            query=enhanced_query,
            num_results=num_results * 3,  # Get more for filtering
            vector_weight=0.4  # Balance semantic and keyword
        )

        # Process results into call objects
        calls = []
        seen_content = set()  # Deduplicate

        for result in results:
            # Skip duplicates
            content_hash = hash(result.content[:200])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            # Extract call information
            call_info = self._extract_call_info(result)

            # Apply filters
            if cluster and call_info.cluster and cluster.upper() not in call_info.cluster.upper():
                continue
            if action_type and call_info.action_type and action_type.upper() not in call_info.action_type.upper():
                continue

            calls.append(call_info)

            if len(calls) >= num_results:
                break

        return {
            'success': True,
            'query': query,
            'calls_found': len(calls),
            'calls': [c.to_dict() for c in calls],
            'search_metadata': {
                'source': 'local_work_programmes',
                'enhanced_query': enhanced_query,
                'total_results_before_filter': len(results),
                'filters_applied': {
                    'cluster': cluster,
                    'action_type': action_type
                }
            }
        }

    def _enhance_query(self, query: str, cluster: Optional[str] = None) -> str:
        """Enhance the query with relevant context."""
        enhanced = query

        # Add Horizon Europe context
        if 'horizon' not in query.lower():
            enhanced = f"Horizon Europe {enhanced}"

        # Add cluster keywords if specified
        if cluster and cluster.upper() in self.CLUSTER_KEYWORDS:
            keywords = self.CLUSTER_KEYWORDS[cluster.upper()][:2]
            enhanced = f"{enhanced} {' '.join(keywords)}"

        # Add call-related terms
        enhanced = f"{enhanced} call topic funding"

        return enhanced

    def _extract_call_info(self, result) -> LocalCallResult:
        """Extract call information from a search result."""
        content = result.content

        # Extract topic code
        topic_code = None
        for pattern in [self.TOPIC_CODE_PATTERN, self.ERC_CODE_PATTERN, self.EIC_CODE_PATTERN]:
            matches = re.findall(pattern, content)
            if matches:
                topic_code = matches[0]
                break

        # Extract action type
        action_type = None
        for atype, pattern in self.ACTION_TYPES.items():
            if re.search(pattern, content, re.IGNORECASE):
                action_type = atype
                break

        # Detect cluster from document title or content
        cluster = None
        doc_title = result.document_title.lower() if result.document_title else ''
        for cl, keywords in self.CLUSTER_KEYWORDS.items():
            if any(kw in doc_title or kw in content.lower() for kw in keywords):
                cluster = cl
                break

        # Extract budget (look for EUR patterns)
        budget = None
        budget_match = re.search(r'EUR\s*([\d,\.]+)\s*(million|billion)?', content, re.IGNORECASE)
        if budget_match:
            budget = f"EUR {budget_match.group(1)} {budget_match.group(2) or ''}".strip()

        # Extract deadline (look for date patterns)
        deadline = None
        date_match = re.search(r'deadline[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', content, re.IGNORECASE)
        if date_match:
            deadline = date_match.group(1)

        # Generate title from first meaningful sentence
        title = topic_code or result.section_title or "Funding Opportunity"

        # Get first ~500 chars as description
        description = content[:500].strip()
        if len(content) > 500:
            description += "..."

        return LocalCallResult(
            topic_code=topic_code,
            title=title,
            description=description,
            source_document=result.document_title or "Work Programme",
            work_programme=self._get_work_programme_name(result.document_title),
            cluster=cluster,
            action_type=action_type,
            budget=budget,
            deadline=deadline,
            relevance_score=result.score
        )

    def _get_work_programme_name(self, doc_title: str) -> str:
        """Convert document title to friendly work programme name."""
        if not doc_title:
            return "Unknown Work Programme"

        title_lower = doc_title.lower()

        if 'eic' in title_lower:
            return "EIC Work Programme 2026"
        elif 'erc' in title_lower:
            return "ERC Work Programme 2026"
        elif 'health' in title_lower:
            return "Cluster 1: Health (2025)"
        elif 'culture' in title_lower or 'inclusive' in title_lower:
            return "Cluster 2: Culture, Creativity and Inclusive Society (2025)"
        elif 'security' in title_lower:
            return "Cluster 3: Civil Security for Society (2025)"
        elif 'digital' in title_lower or 'space' in title_lower:
            return "Cluster 4: Digital, Industry and Space (2025)"
        elif 'climate' in title_lower or 'energy' in title_lower:
            return "Cluster 5: Climate, Energy and Mobility (2025)"
        elif 'food' in title_lower or 'bioeconomy' in title_lower:
            return "Cluster 6: Food, Bioeconomy, Natural Resources (2025)"
        elif 'widening' in title_lower:
            return "Widening Participation (2025)"
        elif 'missions' in title_lower:
            return "Missions (2025)"
        elif 'general-annexes' in title_lower:
            return "General Annexes (2025)"
        else:
            return doc_title

    def get_call_details(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific call by its topic code.

        Args:
            topic_code: The call identifier (e.g., HORIZON-CL5-2025-D3-01-04)

        Returns:
            Detailed call information or None if not found
        """
        # Search specifically for this topic code
        results = self.vector_service.hybrid_search(
            query=topic_code,
            num_results=5,
            vector_weight=0.2  # Prioritize keyword match
        )

        # Find chunks containing the topic code
        relevant_chunks = []
        for r in results:
            if topic_code in r.content:
                relevant_chunks.append(r)

        if not relevant_chunks:
            return None

        # Combine information from all relevant chunks
        combined_content = "\n\n".join([c.content for c in relevant_chunks])

        call_info = self._extract_call_info(relevant_chunks[0])
        call_info.description = combined_content[:2000]  # Extended description

        return {
            'success': True,
            'call': call_info.to_dict(),
            'source_chunks': len(relevant_chunks),
            'source': 'local_work_programmes'
        }
```

### Step 2: Update Tool Orchestrator

Modify `app/services/tools/tool_orchestrator.py`:

1. Replace `ImprovedCallSearchService` with `LocalCallSearchService`
2. Update `eu_portal_search` tool to use local search

```python
# In _register_builtin_tools():

from ..local_call_search_service import LocalCallSearchService

# Initialize local call search
self.local_call_service = LocalCallSearchService()

# Update eu_portal_search tool
async def eu_portal_search_exec(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get('query', params.get('keywords', ''))

    if not query:
        return {
            'success': False,
            'error': 'No search query provided',
            'tool_name': 'eu_portal_search'
        }

    # Use LOCAL search
    results = self.local_call_service.search_calls(
        query=query,
        num_results=params.get('num_results', 10),
        cluster=params.get('cluster'),
        action_type=params.get('action_type')
    )

    return {
        'success': True,
        'tool_name': 'eu_portal_search',
        'query': query,
        'calls_found': results['calls_found'],
        'calls': results['calls'],
        'search_metadata': results['search_metadata']
    }
```

### Step 3: Update Response Formatter

Ensure `app/services/response/unified_formatter.py` correctly formats local call results:

The formatter should work with the new `LocalCallResult` structure which includes:
- `topic_code`
- `title`
- `description`
- `source_document`
- `work_programme`
- `cluster`
- `action_type`
- `budget`
- `deadline`
- `relevance_score`

### Step 4: Test the Implementation

Create a test script `scripts/test_local_call_search.py`:

```python
#!/usr/bin/env python3
"""Test local call search functionality."""

import asyncio
from dotenv import load_dotenv
load_dotenv('.env')

from app.services.local_call_search_service import LocalCallSearchService

async def main():
    service = LocalCallSearchService()

    test_queries = [
        "clean energy research",
        "EIC Accelerator 2026",
        "ERC Starting Grant",
        "hydrogen fuel cells",
        "AI healthcare",
        "cybersecurity",
        "sustainable food"
    ]

    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print('='*70)

        results = service.search_calls(query, num_results=3)

        print(f"Found: {results['calls_found']} calls")
        for i, call in enumerate(results['calls'], 1):
            print(f"\n[{i}] {call['title']}")
            print(f"    Source: {call['work_programme']}")
            if call['topic_code']:
                print(f"    Code: {call['topic_code']}")
            if call['action_type']:
                print(f"    Type: {call['action_type']}")
            print(f"    Score: {call['relevance_score']:.3f}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Verification Checklist

- [ ] `LocalCallSearchService` created and working
- [ ] `eu_portal_search` tool updated to use local search
- [ ] No external API calls made
- [ ] Clean energy queries return relevant Cluster 5 results
- [ ] EIC Accelerator queries return EIC WP 2026 results
- [ ] ERC grant queries return ERC WP 2026 results
- [ ] Response formatter displays local results correctly
- [ ] Test script passes all queries

## Files to Modify/Create

1. **CREATE**: `app/services/local_call_search_service.py`
2. **MODIFY**: `app/services/tools/tool_orchestrator.py`
3. **VERIFY**: `app/services/response/unified_formatter.py`
4. **CREATE**: `scripts/test_local_call_search.py`
5. **OPTIONAL DELETE**: `app/services/improved_call_search_service.py` (the API-based one)

## Success Criteria

When user asks: "Tell me about funding opportunities in clean energy research"

The system should:
1. ✅ Search local Work Programme documents
2. ✅ Find relevant Cluster 5 (Climate, Energy, Mobility) content
3. ✅ Return actual call codes (HORIZON-CL5-2025-...)
4. ✅ NOT call any external API
5. ✅ Display source as "Work Programme 2025" or similar

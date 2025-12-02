"""
Local Call Search Service

Searches for funding calls using locally ingested Work Programme documents.
No external API dependency - everything runs on your local data.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, date

from .vector_search_service import VectorSearchService

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
    
    This service:
    - Searches only locally ingested PDFs (Work Programmes, guides, etc.)
    - Extracts call codes, budgets, deadlines from document content
    - Returns structured results with source attribution
    - Works completely offline (no external API calls)
    """
    
    # Patterns to extract call information
    TOPIC_CODE_PATTERNS = [
        r'HORIZON-[A-Z0-9]+-\d{4}-[A-Z0-9-]+(?:-\d+)?',  # Standard: HORIZON-CL5-2025-D3-01-04
        r'HORIZON-EIC-\d{4}-[A-Z]+-\d+',  # EIC: HORIZON-EIC-2026-ACCELERATOR-01
        r'ERC-\d{4}-[A-Z]+',  # ERC: ERC-2026-STG
    ]
    
    # Action type patterns
    ACTION_TYPES = {
        'RIA': r'\bRIA\b|Research and Innovation Action',
        'IA': r'\bIA\b|Innovation Action[^s]',
        'CSA': r'\bCSA\b|Coordination and Support Action',
        'COFUND': r'\bCOFUND\b|Co-funded?',
        'MSCA-PF': r'MSCA.*Postdoctoral|Postdoctoral Fellowship',
        'MSCA-DN': r'MSCA.*Doctoral|Doctoral Network',
        'MSCA': r'\bMSCA\b|Marie Sk',
        'ERC-STG': r'ERC.*Starting|Starting Grant',
        'ERC-COG': r'ERC.*Consolidator|Consolidator Grant',
        'ERC-ADG': r'ERC.*Advanced|Advanced Grant',
        'ERC-POC': r'ERC.*Proof of Concept|Proof of Concept',
        'ERC': r'\bERC\b|European Research Council',
        'EIC-Accelerator': r'EIC Accelerator|Accelerator',
        'EIC-Pathfinder': r'EIC Pathfinder|Pathfinder',
        'EIC-Transition': r'EIC Transition|Transition',
        'EIC': r'\bEIC\b|European Innovation Council',
        'LUMP-SUM': r'Lump[- ]?Sum',
    }
    
    # Cluster mapping by keywords
    CLUSTER_KEYWORDS = {
        'CL1': ['health', 'cancer', 'pandemic', 'infectious disease', 'mental health', 'ageing', 'pharmaceutical'],
        'CL2': ['culture', 'creativity', 'inclusive', 'democracy', 'heritage', 'social', 'governance'],
        'CL3': ['security', 'cybersecurity', 'disaster', 'border', 'crime', 'terrorism', 'resilience'],
        'CL4': ['digital', 'AI', 'artificial intelligence', 'data', 'industry', 'space', 'manufacturing', 'robotics', 'quantum'],
        'CL5': ['climate', 'energy', 'mobility', 'transport', 'battery', 'hydrogen', 'renewable', 'clean', 'carbon', 'emission'],
        'CL6': ['food', 'bioeconomy', 'agriculture', 'biodiversity', 'environment', 'circular', 'ocean', 'soil', 'forest'],
    }
    
    # Work programme title mappings
    WP_TITLE_MAP = {
        'eic': 'EIC Work Programme 2026',
        'erc': 'ERC Work Programme 2026',
        'health': 'Cluster 1: Health',
        'culture': 'Cluster 2: Culture, Creativity & Inclusive Society',
        'inclusive': 'Cluster 2: Culture, Creativity & Inclusive Society',
        'security': 'Cluster 3: Civil Security for Society',
        'digital': 'Cluster 4: Digital, Industry and Space',
        'industry': 'Cluster 4: Digital, Industry and Space',
        'space': 'Cluster 4: Digital, Industry and Space',
        'climate': 'Cluster 5: Climate, Energy and Mobility',
        'energy': 'Cluster 5: Climate, Energy and Mobility',
        'mobility': 'Cluster 5: Climate, Energy and Mobility',
        'food': 'Cluster 6: Food, Bioeconomy & Environment',
        'bioeconomy': 'Cluster 6: Food, Bioeconomy & Environment',
        'widening': 'Widening Participation',
        'missions': 'Missions',
        'bauhaus': 'New European Bauhaus',
        'infrastructures': 'Research Infrastructures',
        'ecosystems': 'European Innovation Ecosystems',
        'general-annexes': 'General Annexes',
        'programme-guide': 'Horizon Europe Programme Guide',
    }
    
    def __init__(self):
        """Initialize the local call search service."""
        try:
            self.vector_service = VectorSearchService()
            self._available = True
            logger.info("✅ LocalCallSearchService initialized (LOCAL ONLY - no external API)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LocalCallSearchService: {e}")
            self._available = False
    
    def search_calls(
        self,
        query: str,
        num_results: int = 10,
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        include_closed: bool = False,
        year_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for calls matching the query in local Work Programme documents.
        
        Args:
            query: Search query (e.g., "clean energy", "hydrogen", "AI healthcare")
            num_results: Maximum number of results to return
            cluster: Optional filter by cluster (CL1-CL6)
            action_type: Optional filter by action type (RIA, IA, CSA, etc.)
            include_closed: If False, filter out calls from past years (default: False)
            year_filter: Only show calls from specific year (e.g., "2025", "2026")
        
        Returns:
            Dict with 'calls' list and 'search_metadata'
        """
        if not self._available:
            return {
                'success': False,
                'error': 'Local call search service not available',
                'query': query,
                'calls_found': 0,
                'calls': []
            }
        
        # Get current date dynamically (not hardcoded!)
        today = date.today()
        current_year = today.year
        logger.info(f"🔍 LOCAL SEARCH: '{query}' (cluster={cluster}, type={action_type}, include_closed={include_closed}, year={year_filter}, today={today})")
        
        # Build enhanced query for better recall
        # If not including closed calls, bias toward current/future years
        if not include_closed and not year_filter:
            enhanced_query = self._enhance_query(query, cluster, action_type, current_year=current_year)
        else:
            enhanced_query = self._enhance_query(query, cluster, action_type, current_year=None)
        
        # Search vector database
        try:
            results = self.vector_service.hybrid_search(
                query=enhanced_query,
                num_results=num_results * 6,  # Get more for filtering/dedup
                vector_weight=0.4,  # Balance semantic and keyword
                similarity_threshold=0.3  # Lower threshold for better recall
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'calls_found': 0,
                'calls': []
            }
        
        # Process results into call objects
        calls = []
        seen_codes = set()  # Deduplicate by topic code
        seen_content = set()  # Deduplicate by content hash
        
        for result in results:
            # Skip near-duplicate content
            content_hash = hash(result.content[:150])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)
            
            # Extract call information
            call_info = self._extract_call_info(result)
            
            # YEAR FILTERING - Only show current/upcoming calls by default
            if not include_closed:
                call_year = self._extract_year_from_call(call_info)
                if call_year and call_year < current_year:
                    logger.debug(f"Skipping old call {call_info.topic_code} (year={call_year})")
                    continue
            
            # Specific year filter
            if year_filter:
                call_year = self._extract_year_from_call(call_info)
                if not call_year or str(call_year) != str(year_filter):
                    continue
            
            # Skip if we've seen this topic code
            if call_info.topic_code and call_info.topic_code in seen_codes:
                continue
            if call_info.topic_code:
                seen_codes.add(call_info.topic_code)
            
            # Apply filters
            if cluster:
                if call_info.cluster and cluster.upper() not in call_info.cluster.upper():
                    continue
            
            if action_type:
                if call_info.action_type and action_type.upper() not in call_info.action_type.upper():
                    continue
            
            calls.append(call_info)
            
            if len(calls) >= num_results:
                break
        
        logger.info(f"✅ Found {len(calls)} local results for '{query}' (filtered to current/upcoming)")
        
        return {
            'success': True,
            'query': query,
            'calls_found': len(calls),
            'calls': [c.to_dict() for c in calls],
            'current_date': today.isoformat(),
            'search_metadata': {
                'source': 'local_work_programmes',
                'api_used': False,
                'enhanced_query': enhanced_query,
                'total_results_before_filter': len(results),
                'include_closed': include_closed,
                'year_filter': year_filter,
                'current_year': current_year,
                'filters_applied': {
                    'cluster': cluster,
                    'action_type': action_type
                }
            }
        }
    
    def _extract_year_from_call(self, call: LocalCallResult) -> Optional[int]:
        """Extract the year from a call's topic code or content."""
        # Try topic code first: HORIZON-CL5-2025-D3-01-04 -> 2025
        # Match any year from 2020-2039
        if call.topic_code:
            year_match = re.search(r'20(2[0-9]|3[0-9])', call.topic_code)
            if year_match:
                return int(year_match.group(0))
        
        # Try work programme name
        if call.work_programme:
            year_match = re.search(r'20(2[0-9]|3[0-9])', call.work_programme)
            if year_match:
                return int(year_match.group(0))
        
        # Try source document
        if call.source_document:
            year_match = re.search(r'20(2[0-9]|3[0-9])', call.source_document)
            if year_match:
                return int(year_match.group(0))
        
        return None
    
    def _enhance_query(
        self, 
        query: str, 
        cluster: Optional[str] = None,
        action_type: Optional[str] = None,
        current_year: Optional[int] = None
    ) -> str:
        """Enhance the query with relevant context for better search."""
        parts = [query]
        
        # Add Horizon Europe context if not present
        if 'horizon' not in query.lower() and 'erc' not in query.lower() and 'eic' not in query.lower():
            parts.append("Horizon Europe funding call")
        
        # Add cluster keywords if specified
        if cluster and cluster.upper() in self.CLUSTER_KEYWORDS:
            keywords = self.CLUSTER_KEYWORDS[cluster.upper()][:2]
            parts.extend(keywords)
        
        # Add action type context
        if action_type:
            parts.append(action_type)
        
        # Bias toward current/upcoming years
        if current_year:
            parts.append(f"{current_year}")
            parts.append(f"{current_year + 1}")
        
        return " ".join(parts)
    
    def _extract_call_info(self, result) -> LocalCallResult:
        """Extract call information from a search result."""
        content = result.content
        doc_title = result.document_title or ""
        
        # Extract topic code (try all patterns)
        topic_code = None
        for pattern in self.TOPIC_CODE_PATTERNS:
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
        cluster = self._detect_cluster(doc_title, content)
        
        # Extract budget (look for EUR patterns)
        budget = self._extract_budget(content)
        
        # Extract deadline
        deadline = self._extract_deadline(content)
        
        # Generate title
        if topic_code:
            title = topic_code
        elif result.section_title:
            title = result.section_title[:100]
        else:
            title = self._generate_title_from_content(content)
        
        # Get description (clean first ~400 chars)
        description = self._clean_description(content[:600])
        
        # Get work programme name
        work_programme = self._get_work_programme_name(doc_title)
        
        return LocalCallResult(
            topic_code=topic_code,
            title=title,
            description=description,
            source_document=doc_title,
            work_programme=work_programme,
            cluster=cluster,
            action_type=action_type,
            budget=budget,
            deadline=deadline,
            relevance_score=result.score
        )
    
    def _detect_cluster(self, doc_title: str, content: str) -> Optional[str]:
        """Detect which cluster this content belongs to."""
        combined = (doc_title + " " + content).lower()
        
        # Check document title first (most reliable)
        for cl, keywords in self.CLUSTER_KEYWORDS.items():
            for kw in keywords:
                if kw in doc_title.lower():
                    return cl
        
        # Check content
        cluster_scores = {}
        for cl, keywords in self.CLUSTER_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                cluster_scores[cl] = score
        
        if cluster_scores:
            return max(cluster_scores, key=cluster_scores.get)
        
        return None
    
    def _extract_budget(self, content: str) -> Optional[str]:
        """Extract budget information from content."""
        # Look for various budget patterns
        patterns = [
            r'EUR\s*([\d,\.]+)\s*(million|billion|M|B)?',
            r'€\s*([\d,\.]+)\s*(million|billion|M|B)?',
            r'budget[:\s]+EUR?\s*([\d,\.]+)\s*(million|billion|M|B)?',
            r'([\d,\.]+)\s*(million|billion)\s*EUR',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                unit = match.group(2) if len(match.groups()) > 1 else ''
                if unit:
                    return f"EUR {amount} {unit}"
                elif float(amount.replace('.', '')) > 1000:
                    return f"EUR {amount}"
        
        return None
    
    def _extract_deadline(self, content: str) -> Optional[str]:
        """Extract deadline information from content."""
        patterns = [
            r'deadline[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'deadline[:\s]+(\d{1,2}\s+\w+\s+\d{4})',
            r'closes?[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'closes?[:\s]+(\d{1,2}\s+\w+\s+\d{4})',
            r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _generate_title_from_content(self, content: str) -> str:
        """Generate a title from content if no topic code found."""
        # Take first sentence or meaningful phrase
        sentences = content.split('.')
        if sentences:
            first = sentences[0].strip()
            if len(first) > 10 and len(first) < 150:
                return first
        
        # Fall back to first N words
        words = content.split()[:10]
        return " ".join(words) + "..."
    
    def _clean_description(self, text: str) -> str:
        """Clean up description text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove page markers
        text = re.sub(r'\[Page \d+\]', '', text)
        
        # Truncate if needed
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text
    
    def _get_work_programme_name(self, doc_title: str) -> str:
        """Convert document title to friendly work programme name."""
        if not doc_title:
            return "Horizon Europe Work Programme"
        
        title_lower = doc_title.lower()
        
        # Check title map
        for key, name in self.WP_TITLE_MAP.items():
            if key in title_lower:
                return name
        
        # Clean up the title
        clean = doc_title.replace('_', ' ').replace('-', ' ')
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        return clean or "Horizon Europe Work Programme"
    
    def get_call_details(self, topic_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific call by its topic code.
        
        Args:
            topic_code: The call identifier (e.g., HORIZON-CL5-2025-D3-01-04)
        
        Returns:
            Detailed call information or None if not found
        """
        if not self._available:
            return None
        
        logger.info(f"🔍 Looking up call: {topic_code}")
        
        # Search specifically for this topic code
        results = self.vector_service.hybrid_search(
            query=topic_code,
            num_results=10,
            vector_weight=0.2  # Prioritize keyword match
        )
        
        # Find chunks containing the topic code
        relevant_chunks = []
        for r in results:
            if topic_code.upper() in r.content.upper():
                relevant_chunks.append(r)
        
        if not relevant_chunks:
            return {
                'success': False,
                'error': f'Call {topic_code} not found in local documents',
                'call': None
            }
        
        # Combine information from all relevant chunks
        combined_content = "\n\n---\n\n".join([c.content for c in relevant_chunks[:5]])
        
        call_info = self._extract_call_info(relevant_chunks[0])
        call_info.description = self._clean_description(combined_content[:2000])
        
        return {
            'success': True,
            'call': call_info.to_dict(),
            'source_chunks': len(relevant_chunks),
            'source': 'local_work_programmes'
        }
    
    def search_by_cluster(self, cluster: str, num_results: int = 10) -> Dict[str, Any]:
        """Search for all calls in a specific cluster."""
        cluster_names = {
            'CL1': 'health',
            'CL2': 'culture creativity inclusive society',
            'CL3': 'security cybersecurity',
            'CL4': 'digital AI industry space',
            'CL5': 'climate energy mobility transport',
            'CL6': 'food bioeconomy agriculture environment',
        }
        
        query = cluster_names.get(cluster.upper(), cluster)
        return self.search_calls(query, num_results=num_results, cluster=cluster)


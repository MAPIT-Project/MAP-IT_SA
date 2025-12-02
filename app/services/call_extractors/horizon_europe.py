"""
Horizon Europe Call Extractor

Extracts structured funding call data from Horizon Europe Work Programme documents.
Understands the specific format used in HE Work Programmes (2021-2027).
"""

import logging
import re
from typing import List, Dict, Any, Optional
from decimal import Decimal

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
    topic_patterns = [
        # Standard cluster format: HORIZON-CL5-2026-02-D3-14
        re.compile(r'HORIZON-CL\d+-\d{4}-\d+-[A-Z0-9-]+', re.IGNORECASE),
        # EIC format: HORIZON-EIC-2026-ACCELERATOR-01
        re.compile(r'HORIZON-EIC-\d{4}-[A-Z]+-\d+', re.IGNORECASE),
        # ERC format: HORIZON-ERC-2026-STG-01 or ERC-2026-STG
        re.compile(r'(?:HORIZON-)?ERC-\d{4}-[A-Z]+-?\d*', re.IGNORECASE),
        # MSCA format: HORIZON-MSCA-2025-PF-01
        re.compile(r'HORIZON-MSCA-\d{4}-[A-Z]+-\d+', re.IGNORECASE),
        # Health cluster: HORIZON-HLTH-2025-...
        re.compile(r'HORIZON-HLTH-\d{4}-[A-Z0-9-]+', re.IGNORECASE),
        # Infrastructure: HORIZON-INFRA-2025-...
        re.compile(r'HORIZON-INFRA-\d{4}-[A-Z0-9-]+', re.IGNORECASE),
        # Widening: HORIZON-WIDERA-2025-...
        re.compile(r'HORIZON-WIDERA-\d{4}-[A-Z0-9-]+', re.IGNORECASE),
        # Two-stage calls: HORIZON-CL5-2025-01-TWO-STAGE
        re.compile(r'HORIZON-CL\d+-\d{4}-\d+-TWO-STAGE', re.IGNORECASE),
        # Generic fallback
        re.compile(r'HORIZON-[A-Z0-9]+-\d{4}-[A-Z0-9-]+', re.IGNORECASE),
    ]
    
    # Action types and their full names
    action_types = {
        'RIA': 'Research and Innovation Action',
        'IA': 'Innovation Action',
        'CSA': 'Coordination and Support Action',
        'COFUND': 'Co-funded Action',
        'PCP': 'Pre-Commercial Procurement',
        'PPI': 'Public Procurement of Innovative Solutions',
        'LUMP-SUM': 'Lump Sum Grant',
        'ERC-STG': 'ERC Starting Grant',
        'ERC-COG': 'ERC Consolidator Grant',
        'ERC-ADG': 'ERC Advanced Grant',
        'ERC-POC': 'ERC Proof of Concept',
        'ERC-SYG': 'ERC Synergy Grant',
        'EIC-ACCELERATOR': 'EIC Accelerator',
        'EIC-PATHFINDER': 'EIC Pathfinder',
        'EIC-TRANSITION': 'EIC Transition',
        'MSCA-PF': 'MSCA Postdoctoral Fellowship',
        'MSCA-DN': 'MSCA Doctoral Network',
        'MSCA-SE': 'MSCA Staff Exchange',
        'MSCA-COFUND': 'MSCA COFUND',
    }
    
    # Cluster names
    cluster_names = {
        'CL1': 'Health',
        'CL2': 'Culture, Creativity and Inclusive Society',
        'CL3': 'Civil Security for Society',
        'CL4': 'Digital, Industry and Space',
        'CL5': 'Climate, Energy and Mobility',
        'CL6': 'Food, Bioeconomy, Natural Resources, Agriculture and Environment',
    }
    
    def extract_from_content(self, content: str, document_title: str = "") -> List[FundingCall]:
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
        self, 
        content: str, 
        topic_code: str,
        document_title: str
    ) -> Optional[FundingCall]:
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
                status = 'upcoming'
            elif call_year == today.year:
                status = 'open'  # Could be open or upcoming
            else:
                status = 'closed'
        else:
            status = 'upcoming'
        
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
            budget_total=budget_info.get('total'),
            budget_per_project_min=budget_info.get('min'),
            budget_per_project_max=budget_info.get('max'),
            expected_projects=budget_info.get('projects'),
            funding_rate=budget_info.get('rate'),
            expected_outcome=expected_outcome,
            scope=scope,
            cluster=cluster,
            destination=self.cluster_names.get(cluster, ''),
            tags=tags,
            source_document_title=document_title,
            portal_url=self.build_portal_url(topic_code),
        )
    
    def _extract_title(self, content: str, topic_code: str) -> str:
        """Extract call title from content."""
        # Pattern: HORIZON-CL5-2026-02-D3-14: Title of the call
        pattern = rf'{re.escape(topic_code)}[:\s]+([^\n\.]+)'
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
        title = re.sub(r'^(RIA|IA|CSA|COFUND)\s+[\d\.]+\s*', '', title)
        
        # Remove "Call: Cluster..." pattern
        title = re.sub(r'\s*Call:\s*Cluster.*$', '', title, flags=re.IGNORECASE)
        
        # Remove budget info
        title = re.sub(r'\s*[\d\.]+\s*(Around|million|EUR).*$', '', title, flags=re.IGNORECASE)
        
        # Remove dots and clean
        title = re.sub(r'\.{3,}', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        title = re.sub(r'[:\s]+$', '', title)
        
        # Truncate if too long
        if len(title) > 150:
            title = title[:150]
            last_space = title.rfind(' ')
            if last_space > 100:
                title = title[:last_space]
            title += '...'
        
        return title
    
    def _determine_programme_part(self, topic_code: str) -> str:
        """Determine which part of HE this call belongs to."""
        code_upper = topic_code.upper()
        
        if 'EIC' in code_upper:
            return 'European Innovation Council (EIC)'
        elif 'ERC' in code_upper:
            return 'European Research Council (ERC)'
        elif 'MSCA' in code_upper:
            return 'Marie Skłodowska-Curie Actions (MSCA)'
        elif 'INFRA' in code_upper:
            return 'Research Infrastructures'
        elif 'WIDERA' in code_upper:
            return 'Widening Participation and Strengthening the ERA'
        elif 'HLTH' in code_upper:
            return 'Cluster 1: Health'
        elif 'CL1' in code_upper:
            return 'Cluster 1: Health'
        elif 'CL2' in code_upper:
            return 'Cluster 2: Culture, Creativity and Inclusive Society'
        elif 'CL3' in code_upper:
            return 'Cluster 3: Civil Security for Society'
        elif 'CL4' in code_upper:
            return 'Cluster 4: Digital, Industry and Space'
        elif 'CL5' in code_upper:
            return 'Cluster 5: Climate, Energy and Mobility'
        elif 'CL6' in code_upper:
            return 'Cluster 6: Food, Bioeconomy, Natural Resources'
        else:
            return 'Horizon Europe'
    
    def _extract_action_type(self, content: str, topic_code: str) -> Optional[str]:
        """Extract action type for a call."""
        # Look near the topic code
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            search_content = content
        else:
            search_content = content[max(0, start_idx-100):start_idx+500]
        
        # Check for action types in order of specificity
        for action_type in [
            'ERC-STG', 'ERC-COG', 'ERC-ADG', 'ERC-POC', 'ERC-SYG',
            'EIC-ACCELERATOR', 'EIC-PATHFINDER', 'EIC-TRANSITION',
            'MSCA-PF', 'MSCA-DN', 'MSCA-SE', 'MSCA-COFUND',
            'LUMP-SUM', 'COFUND', 'PCP', 'PPI',
            'RIA', 'IA', 'CSA'
        ]:
            pattern = rf'\b{re.escape(action_type)}\b'
            if re.search(pattern, search_content, re.IGNORECASE):
                return action_type
        
        # Check topic code for hints
        if 'EIC' in topic_code.upper():
            if 'ACCELERATOR' in topic_code.upper():
                return 'EIC-Accelerator'
            elif 'PATHFINDER' in topic_code.upper():
                return 'EIC-Pathfinder'
            elif 'TRANSITION' in topic_code.upper():
                return 'EIC-Transition'
        elif 'ERC' in topic_code.upper():
            if 'STG' in topic_code.upper():
                return 'ERC-STG'
            elif 'COG' in topic_code.upper():
                return 'ERC-COG'
            elif 'ADG' in topic_code.upper():
                return 'ERC-ADG'
        elif 'MSCA' in topic_code.upper():
            if 'PF' in topic_code.upper():
                return 'MSCA-PF'
            elif 'DN' in topic_code.upper():
                return 'MSCA-DN'
        
        return None
    
    def _extract_expected_outcome(self, content: str, topic_code: str) -> Optional[str]:
        """Extract the Expected Outcome section for a call."""
        # Find the topic code position
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return None
        
        # Search for "Expected Outcome" after the topic code
        search_content = content[start_idx:start_idx+5000]
        
        patterns = [
            r'Expected\s+Outcome[s]?[:\s]+(.{100,1500}?)(?=Scope[:\s]|$)',
            r'Project\s+results\s+are\s+expected\s+to\s+contribute\s+to[:\s]+(.{100,1500}?)(?=Scope[:\s]|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, search_content, re.IGNORECASE | re.DOTALL)
            if match:
                outcome = self.clean_text(match.group(1), max_length=1500)
                if len(outcome) > 50:
                    return outcome
        
        return None
    
    def _extract_scope(self, content: str, topic_code: str) -> Optional[str]:
        """Extract the Scope section for a call."""
        # Find the topic code position
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return None
        
        # Search for "Scope:" after the topic code
        search_content = content[start_idx:start_idx+8000]
        
        patterns = [
            r'Scope[:\s]+(.{100,2000}?)(?=Legal\s+and\s+financial|Eligibility|Specific\s+conditions|$)',
            r'Activities\s+(?:are\s+)?expected\s+to[:\s]+(.{100,1500}?)(?=Legal|Eligibility|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, search_content, re.IGNORECASE | re.DOTALL)
            if match:
                scope = self.clean_text(match.group(1), max_length=2000)
                if len(scope) > 50:
                    return scope
        
        return None
    
    def _extract_budget_info(self, content: str, topic_code: str) -> Dict[str, Any]:
        """Extract budget information for a call."""
        result = {}
        
        # Find content near the topic code
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return result
        
        search_content = content[start_idx:start_idx+2000]
        
        # Look for budget patterns
        # "EUR 10 million", "EUR 5.00 million", "budget: EUR 15M"
        budget_patterns = [
            r'(?:budget|contribution)[:\s]+(?:EUR\s*)?(\d+(?:\.\d+)?)\s*(?:million|M)',
            r'EUR\s*(\d+(?:\.\d+)?)\s*(?:million|M)',
            r'(\d+(?:\.\d+)?)\s*(?:million|M)\s*EUR',
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, search_content, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1)) * 1_000_000
                    result['total'] = Decimal(str(amount))
                    break
                except ValueError:
                    continue
        
        # Look for expected projects
        projects_match = re.search(r'Around\s+(\d+)', search_content, re.IGNORECASE)
        if projects_match:
            try:
                result['projects'] = int(projects_match.group(1))
            except ValueError:
                pass
        
        # Look for funding rate
        rate_match = re.search(r'funding\s+rate[:\s]+(\d+)\s*%', search_content, re.IGNORECASE)
        if rate_match:
            try:
                result['rate'] = int(rate_match.group(1))
            except ValueError:
                pass
        
        return result
    
    def _extract_deadline(
        self, 
        content: str, 
        topic_code: str,
        call_year: Optional[int]
    ) -> Optional['date']:
        """Extract deadline for a call."""
        from datetime import date as date_type
        
        # Find content near the topic code
        start_idx = content.upper().find(topic_code.upper())
        if start_idx == -1:
            return None
        
        search_content = content[max(0, start_idx-500):start_idx+2000]
        
        # Deadline patterns
        patterns = [
            r'[Dd]eadline\(?s?\)?[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
            r'[Cc]loses?[:\s]+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
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
    
    def _extract_wp_year(self, document_title: str) -> Optional[int]:
        """Extract Work Programme year from document title."""
        match = re.search(r'20(2[3-9]|3[0-9])', document_title)
        return int(match.group(0)) if match else None
    
    def _generate_tags(
        self, 
        title: str, 
        scope: Optional[str], 
        outcome: Optional[str],
        cluster: Optional[str]
    ) -> List[str]:
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
        title_words = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
        tags.extend(title_words[:5])
        
        # Add some common terms if found in scope
        if scope:
            common_terms = [
                'energy', 'climate', 'digital', 'health', 'ai', 'hydrogen',
                'battery', 'renewable', 'sustainable', 'innovation', 'transport',
                'mobility', 'security', 'cybersecurity', 'agriculture', 'food',
                'biodiversity', 'ocean', 'circular', 'manufacturing', 'space'
            ]
            for term in common_terms:
                if term in scope.lower():
                    tags.append(term)
        
        # Deduplicate and return
        return list(set(tags))[:15]


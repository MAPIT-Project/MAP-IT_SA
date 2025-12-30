"""
EU4Health Programme Call Extractor

Extracts structured funding call data from EU4Health Programme and Work Programme documents.
Understands the specific format used in EU4Health (2021-2027).

EU4Health is the EU's response to COVID-19 with a budget of €5.3 billion, the largest
EU health programme ever.
"""

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .base import CallExtractor, FundingCall

logger = logging.getLogger(__name__)


class EU4HealthExtractor(CallExtractor):
    """
    Extractor for EU4Health Programme documents.

    EU4Health (2021-2027) has four general objectives:
    1. Improve and foster health in the EU (health promotion and disease prevention)
    2. Protect people from serious cross-border health threats
    3. Improve access to medicinal products, medical devices, and crisis-relevant products
    4. Strengthen health systems (resilience, resource efficiency, digital transformation)

    Topic codes follow the format: EU4H-{YEAR}-{TYPE}-{NUMBER}

    Examples:
        - EU4H-2025-PJ-01  (Project grants)
        - EU4H-2025-OA-01  (Operating grants)
        - EU4H-2025-JA-01  (Joint Actions with Member States)
        - EU4H-2025-PPI-01 (Pre-Commercial Procurement)
        - EU4H-2025-SGA-01 (Specific Grant Agreements)
    """

    programme = "eu4health"
    programme_name = "EU4Health"

    # Topic code patterns for EU4Health
    topic_patterns = [
        # Standard EU4Health format: EU4H-2025-PJ-01
        re.compile(r'EU4H-\d{4}-[A-Z]+-\d+', re.IGNORECASE),
        # Full name format: EU4HEALTH-2025-PJ-01
        re.compile(r'EU4HEALTH-\d{4}-[A-Z]+-\d+', re.IGNORECASE),
        # Alternative with year after type: EU4H-PJ-2025-01
        re.compile(r'EU4H-[A-Z]+-\d{4}-\d+', re.IGNORECASE),
        # Compact format: EU4H2025-PJ01
        re.compile(r'EU4H\d{4}-[A-Z]+\d+', re.IGNORECASE),
        # Generic EU health format
        re.compile(r'EU(?:4)?HEALTH-\d{4}-[A-Z0-9]+(?:-[A-Z0-9]+)*', re.IGNORECASE),
    ]

    # Action types in EU4Health
    action_types = {
        # Grant types
        'PJ': 'Project Grant',
        'OA': 'Operating Grant',
        'JA': 'Joint Action',
        'SGA': 'Specific Grant Agreement',
        'DA': 'Direct Award',
        'CSA': 'Coordination and Support Action',

        # Procurement types
        'PPI': 'Pre-Commercial Procurement',
        'PCP': 'Pre-Commercial Procurement',
        'FWC': 'Framework Contract',
        'SC': 'Service Contract',

        # Other types
        'PREV': 'Disease Prevention',
        'CRISIS': 'Crisis Preparedness',
        'ACCESS': 'Access to Healthcare',
        'DIGITAL': 'Digital Health',
        'CANCER': 'Cancer Action',
        'AMR': 'Antimicrobial Resistance',
        'PHARMA': 'Pharmaceutical Strategy',
        'MH': 'Mental Health',
    }

    # Priority areas (aligned with general objectives)
    priority_areas = {
        'PREVENTION': 'Disease Prevention and Health Promotion',
        'CRISIS': 'Cross-Border Health Threats and Crisis Preparedness',
        'ACCESS': 'Access to Medicinal Products and Medical Devices',
        'SYSTEMS': 'Health System Strengthening and Digital Health',
        'CANCER': 'Europe\'s Beating Cancer Plan',
        'AMR': 'Antimicrobial Resistance',
        'PHARMA': 'Pharmaceutical Strategy for Europe',
        'MENTAL': 'Mental Health',
        'HEALTH-UNION': 'European Health Union',
    }

    # Budget ranges by action type (in EUR)
    budget_ranges = {
        'PJ': {'min': 500000, 'max': 20000000, 'funding_rate': 60},
        'OA': {'min': 500000, 'max': 2000000, 'funding_rate': 60},
        'JA': {'min': 2000000, 'max': 100000000, 'funding_rate': 80},
        'SGA': {'min': 1000000, 'max': 50000000, 'funding_rate': 80},
        'DA': {'min': 1000000, 'max': 10000000, 'funding_rate': 80},
        'CSA': {'min': 500000, 'max': 5000000, 'funding_rate': 100},
        'PPI': {'min': 5000000, 'max': 50000000, 'funding_rate': 100},
        'FWC': {'min': 1000000, 'max': 20000000, 'funding_rate': 100},
    }

    # Consortium requirements
    consortium_requirements = {
        'PJ': {'min_partners': 3, 'min_countries': 3},
        'JA': {'min_partners': 0, 'min_countries': 0, 'note': 'Requires Member State participation'},
        'OA': {'min_partners': 1, 'min_countries': 1, 'note': 'EU-level networks'},
        'SGA': {'min_partners': 1, 'min_countries': 1},
    }

    # Duration ranges by action type (in months)
    duration_ranges = {
        'PJ': {'min': 12, 'max': 48},
        'OA': {'min': 12, 'max': 48},
        'JA': {'min': 24, 'max': 48},
        'SGA': {'min': 12, 'max': 36},
        'DA': {'min': 12, 'max': 24},
        'CSA': {'min': 12, 'max': 36},
        'PPI': {'min': 24, 'max': 60},
        'FWC': {'min': 24, 'max': 48},
    }

    # Eligible entities
    eligible_entities = [
        'Ministries and public authorities',
        'Public health bodies',
        'Hospitals and healthcare providers',
        'Research institutions',
        'NGOs active in health',
        'Pharmaceutical companies',
        'Medical device manufacturers',
        'Patient organizations',
        'Health insurers',
        'International health organizations',
    ]

    # Participating countries
    participating_countries = [
        # EU Member States
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
        'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
        'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta',
        'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
        'Spain', 'Sweden',
        # EEA countries
        'Iceland', 'Liechtenstein', 'Norway',
        # Third countries (subject to specific conditions)
        'Albania', 'Montenegro', 'North Macedonia', 'Serbia', 'Turkey', 'Ukraine',
        'Moldova', 'Kosovo', 'Bosnia and Herzegovina',
    ]

    def extract_from_content(self, content: str, document_title: str = "") -> List[FundingCall]:
        """
        Extract EU4Health calls from document content.

        EU4Health Work Programmes typically have:
        - Action title and description
        - Type of action (PJ, JA, OA, etc.)
        - Budget allocation
        - Eligibility criteria
        - Submission deadlines
        - Priority area alignment
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
        """Extract details for a single EU4Health call."""

        # Extract basic info
        title = self._extract_title(content, topic_code)
        if not title or len(title) < 5:
            title = self._construct_title_from_code(topic_code)

        # Extract year from topic code
        call_year = self.extract_year_from_code(topic_code)

        # Determine action type
        action_type = self._extract_action_type(topic_code)

        # Determine priority area
        priority_area = self._extract_priority_area(content, topic_code)

        # Extract deadline
        deadline = self._extract_deadline(content, topic_code)

        # Get budget and funding rate info
        budget_info = self._get_budget_info(action_type)
        funding_rate = budget_info.get('funding_rate') if budget_info else None

        # Get consortium requirements
        consortium_info = self._get_consortium_requirements(action_type)

        # Get duration info
        duration_info = self._get_duration_info(action_type)

        # Extract eligibility requirements
        eligibility = self._extract_eligibility(content, topic_code, action_type)

        # Extract scope/objectives
        scope = self._extract_scope(content, topic_code)

        # Build portal URL
        portal_url = self.build_portal_url(topic_code)

        return FundingCall(
            programme=self.programme,
            topic_code=topic_code,
            title=title,
            call_identifier=f"EU4H-{call_year}",
            programme_part=priority_area,
            work_programme_year=call_year,
            action_type=self.action_types.get(action_type, action_type) if action_type else None,
            call_year=call_year,
            deadline=deadline,
            status=self._determine_status(deadline),
            budget_per_project_min=Decimal(str(budget_info.get('min', 0))) if budget_info else None,
            budget_per_project_max=Decimal(str(budget_info.get('max', 0))) if budget_info else None,
            funding_rate=funding_rate,
            scope=scope,
            eligibility=eligibility,
            cluster=priority_area,  # Using cluster field for priority area
            portal_url=portal_url,
            source_document_title=document_title,
            metadata={
                'action_type_code': action_type,
                'action_type_name': self.action_types.get(action_type, action_type) if action_type else None,
                'priority_area': priority_area,
                'priority_area_name': self.priority_areas.get(priority_area) if priority_area else None,
                'min_partners': consortium_info.get('min_partners') if consortium_info else None,
                'min_countries': consortium_info.get('min_countries') if consortium_info else None,
                'consortium_note': consortium_info.get('note') if consortium_info else None,
                'duration_months_min': duration_info.get('min') if duration_info else None,
                'duration_months_max': duration_info.get('max') if duration_info else None,
                'eligible_entity_types': self.eligible_entities,
                'is_joint_action': action_type == 'JA',
                'requires_member_state': action_type == 'JA',
            }
        )

    def _extract_title(self, content: str, topic_code: str) -> Optional[str]:
        """Extract call title from content."""
        patterns = [
            rf'{re.escape(topic_code)}\s*[:–-]\s*(.{{20,200}}?)(?:\n|$)',
            rf'{re.escape(topic_code)}\s+(.{{20,200}}?)(?:\n|$)',
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
            return f"EU4Health {self.action_types[action_type]}"

        return f"EU4Health Call {topic_code}"

    def _extract_action_type(self, topic_code: str) -> Optional[str]:
        """Extract action type from topic code."""
        topic_upper = topic_code.upper()

        # Look for known action type codes
        for action_code in self.action_types.keys():
            # Match action code surrounded by delimiters or at end
            pattern = rf'[-_]({re.escape(action_code)})[-_\d]'
            if re.search(pattern, topic_upper):
                return action_code
            # Also check if it's at the end
            if topic_upper.endswith(f'-{action_code}') or f'-{action_code}-' in topic_upper:
                return action_code

        return None

    def _extract_priority_area(self, content: str, topic_code: str) -> Optional[str]:
        """Extract priority area from content."""
        topic_upper = topic_code.upper()

        # Check topic code for priority indicators
        for priority_code in self.priority_areas.keys():
            if priority_code in topic_upper:
                return priority_code

        # Search in content context
        context_pattern = rf'{re.escape(topic_code)}.{{0,2000}}'
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0).upper()
            for priority_code, priority_name in self.priority_areas.items():
                if priority_code in context or priority_name.upper() in context:
                    return priority_code

        return None

    def _extract_deadline(self, content: str, topic_code: str) -> Optional[date]:
        """Extract deadline from content."""
        context_pattern = rf'{re.escape(topic_code)}.{{0,1500}}'
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0)

            deadline_patterns = [
                r'deadline[:\s]+(\d{1,2}\s+\w+\s+\d{4})',
                r'submission[:\s]+(?:.*?)(\d{1,2}\s+\w+\s+\d{4})',
                r'(\d{1,2}\s+\w+\s+\d{4})\s*(?:at\s+\d{1,2}:\d{2})?',
                r'(\d{4}-\d{2}-\d{2})',
            ]

            for pattern in deadline_patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    parsed = self.parse_date(match.group(1))
                    if parsed:
                        return parsed

        return None

    def _get_budget_info(self, action_type: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get budget information for action type."""
        if action_type and action_type in self.budget_ranges:
            return self.budget_ranges[action_type]
        return None

    def _get_consortium_requirements(self, action_type: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get consortium requirements for action type."""
        if action_type and action_type in self.consortium_requirements:
            return self.consortium_requirements[action_type]
        return None

    def _get_duration_info(self, action_type: Optional[str]) -> Optional[Dict[str, int]]:
        """Get duration information for action type."""
        if action_type and action_type in self.duration_ranges:
            return self.duration_ranges[action_type]
        return None

    def _extract_eligibility(
        self,
        content: str,
        topic_code: str,
        action_type: Optional[str]
    ) -> Optional[str]:
        """Extract eligibility requirements."""
        eligibility_parts = []

        # Standard eligibility based on action type
        if action_type == 'JA':
            eligibility_parts.append(
                "Joint Actions require participation of competent authorities designated by "
                "Member States or third countries associated to the Programme. At least one "
                "Member State authority must participate. The action is co-financed at 80% "
                "with Member States providing the remaining 20%."
            )
        elif action_type == 'PJ':
            eligibility_parts.append(
                "Project grants are open to legal entities established in EU Member States, "
                "EEA countries, and associated third countries. Minimum consortium of 3 "
                "entities from 3 different eligible countries. Co-financing rate is 60%."
            )
        elif action_type == 'OA':
            eligibility_parts.append(
                "Operating grants support EU-level non-governmental health networks and "
                "organisations. Applicant must be a non-profit body active at EU level in "
                "the health field. Co-financing rate is 60%."
            )
        else:
            eligibility_parts.append(
                "Eligible applicants include public authorities, research institutions, "
                "healthcare providers, NGOs, and industry active in health. Must be "
                "established in EU Member States or associated countries."
            )

        # Look for additional eligibility in content
        context_pattern = rf'{re.escape(topic_code)}.{{0,2000}}'
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0)
            eligibility_patterns = [
                r'eligib(?:ility|le)[:\s]+(.{50,500}?)(?:\n\n|$)',
                r'who can apply[:\s]+(.{50,500}?)(?:\n\n|$)',
                r'applicant(?:s)?[:\s]+(.{50,500}?)(?:\n\n|$)',
            ]

            for pattern in eligibility_patterns:
                match = re.search(pattern, context, re.IGNORECASE | re.DOTALL)
                if match:
                    additional = self.clean_text(match.group(1), max_length=500)
                    if additional and len(additional) > 20:
                        eligibility_parts.append(additional)
                        break

        return ' '.join(eligibility_parts) if eligibility_parts else None

    def _extract_scope(self, content: str, topic_code: str) -> Optional[str]:
        """Extract scope/objectives from content."""
        context_pattern = rf'{re.escape(topic_code)}.{{0,3000}}'
        context_match = re.search(context_pattern, content, re.IGNORECASE | re.DOTALL)

        if context_match:
            context = context_match.group(0)

            scope_patterns = [
                r'(?:scope|objectives?|description|aim)[:\s]+(.{100,1000}?)(?:\n\n|eligib|deadline)',
                r'(?:this action|this call)[:\s]*(.{100,1000}?)(?:\n\n|eligib|deadline)',
            ]

            for pattern in scope_patterns:
                match = re.search(pattern, context, re.IGNORECASE | re.DOTALL)
                if match:
                    scope = self.clean_text(match.group(1), max_length=1000)
                    if scope and len(scope) > 50:
                        return scope

        return None

    def _determine_status(self, deadline: Optional[date]) -> str:
        """Determine call status based on deadline."""
        if not deadline:
            return 'upcoming'

        today = date.today()
        if deadline < today:
            return 'closed'
        elif (deadline - today).days <= 30:
            return 'open'
        else:
            return 'upcoming'

    def build_portal_url(self, topic_code: str) -> str:
        """Build EU portal URL for an EU4Health topic code."""
        base_url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details"
        return f"{base_url}/{topic_code.lower()}"

    def get_programme_info(self) -> Dict[str, Any]:
        """Return comprehensive information about the EU4Health programme."""
        return {
            'programme': self.programme,
            'programme_name': self.programme_name,
            'budget': '€5.3 billion (2021-2027)',
            'description': (
                'EU4Health is the EU\'s ambitious response to COVID-19 and the largest '
                'EU health programme ever. It aims to make EU populations healthier, '
                'strengthen health systems, and improve access to medicines and medical '
                'devices. The programme supports the European Health Union initiative.'
            ),
            'general_objectives': [
                'Improve and foster health in the EU (disease prevention, health promotion)',
                'Protect people from serious cross-border health threats',
                'Improve access to medicinal products, medical devices, and crisis-relevant products',
                'Strengthen health systems (resilience, resource efficiency, digital transformation)',
            ],
            'priority_areas': self.priority_areas,
            'action_types': self.action_types,
            'flagship_initiatives': [
                'Europe\'s Beating Cancer Plan',
                'Pharmaceutical Strategy for Europe',
                'European Health Data Space',
                'European Health Emergency Preparedness and Response Authority (HERA)',
                'Mental Health Initiative',
            ],
            'eligible_entities': self.eligible_entities,
            'participating_countries': self.participating_countries,
            'website': 'https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en',
            'portal': 'https://ec.europa.eu/info/funding-tenders/opportunities/',
        }

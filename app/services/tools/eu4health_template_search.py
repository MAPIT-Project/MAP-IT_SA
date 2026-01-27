"""
EU4Health Template and Guidance Search Tool

Searches EU4Health documents (Annual Work Programmes, Regulation)
for application guidance, eligibility criteria, and programme-specific information.

Uses the ingested EU4Health documents to provide targeted answers
about actions, requirements, and funding opportunities.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Key sections in EU4Health documents
EU4HEALTH_SECTIONS = {
    'crisis_preparedness': {
        'keywords': ['crisis', 'preparedness', 'emergency', 'resilience', 'hera', 'mcm', 'antimicrobial', 'amr'],
        'description': 'Crisis preparedness, HERA, medical countermeasures'
    },
    'disease_prevention': {
        'keywords': ['prevention', 'cancer', 'ncd', 'screening', 'vaccination', 'hiv', 'health promotion'],
        'description': 'Disease prevention, cancer plan, NCDs, health promotion'
    },
    'health_systems': {
        'keywords': ['health system', 'workforce', 'hta', 'shortage', 'medicines', 'pharmaceuticals'],
        'description': 'Health systems, workforce, HTA, medicines supply'
    },
    'digital_health': {
        'keywords': ['digital', 'ehds', 'ehealth', 'data', 'telemedicine', 'ai'],
        'description': 'Digital health, EHDS, eHealth infrastructure'
    },
    'eligibility': {
        'keywords': ['eligibility', 'eligible', 'who can apply', 'applicant', 'participating countries', 'legal entity'],
        'description': 'Eligibility criteria for organizations'
    },
    'budget': {
        'keywords': ['budget', 'funding', 'grant', 'co-financing', 'financial', 'contribution'],
        'description': 'Budget rules, grant amounts, and funding rates'
    },
    'evaluation': {
        'keywords': ['evaluation', 'criteria', 'assessment', 'award', 'scoring', 'quality', 'selection'],
        'description': 'Evaluation and selection criteria'
    },
    'action_grants': {
        'keywords': ['action grant', 'project grant', 'ag', 'pj'],
        'description': 'Action Grant requirements and procedures'
    },
    'joint_actions': {
        'keywords': ['joint action', 'ja', 'member state'],
        'description': 'Joint Action with Member States'
    },
    'operating_grants': {
        'keywords': ['operating grant', 'og', 'ngo', 'framework partnership'],
        'description': 'Operating Grants for NGOs'
    },
    'deadlines': {
        'keywords': ['deadline', 'submission', 'call', 'calendar', 'date'],
        'description': 'Application deadlines and call calendar'
    },
}


class EU4HealthTemplateSearchTool:
    """Tool for searching EU4Health guidance and templates."""

    def __init__(self):
        self.sections = EU4HEALTH_SECTIONS

    def detect_section(self, query: str) -> list[str]:
        """Detect which sections a query is likely about."""
        query_lower = query.lower()
        matching_sections = []

        for section_id, config in self.sections.items():
            for keyword in config['keywords']:
                if keyword in query_lower:
                    matching_sections.append(section_id)
                    break

        return matching_sections or ['general']

    def detect_strand(self, query: str) -> str | None:
        """Detect which strand the query is about."""
        query_lower = query.lower()

        if any(kw in query_lower for kw in ['crisis', 'emergency', 'preparedness', 'hera', 'mcm']):
            return 'CRISIS'
        elif any(kw in query_lower for kw in ['cancer', 'prevention', 'ncd', 'screening']):
            return 'PREVENTION'
        elif any(kw in query_lower for kw in ['health system', 'workforce', 'hta', 'medicines', 'shortage']):
            return 'HEALTH_SYSTEMS'
        elif any(kw in query_lower for kw in ['digital', 'ehds', 'ehealth', 'data', 'telemedicine']):
            return 'DIGITAL'

        return None

    def build_enhanced_query(
        self,
        query: str,
        strand: str | None = None,
        action_type: str | None = None,
    ) -> str:
        """Build an enhanced query with context keywords."""
        enhanced = query

        if strand:
            strand_keywords = {
                'CRISIS': 'crisis preparedness emergency health security HERA medical countermeasures',
                'PREVENTION': 'disease prevention cancer NCD screening vaccination health promotion',
                'HEALTH_SYSTEMS': 'health systems workforce HTA medicines pharmaceutical',
                'DIGITAL': 'digital health EHDS eHealth data telemedicine AI',
            }
            if strand.upper() in strand_keywords:
                enhanced = f"{strand_keywords[strand.upper()]} {enhanced}"

        if action_type:
            action_keywords = {
                'AG': 'action grant project grant application',
                'PJ': 'project grant action grant application',
                'JA': 'joint action member state authority',
                'DG': 'direct grant designated entity',
                'OG': 'operating grant NGO framework partnership',
                'PROC': 'procurement tender contract service',
            }
            action_upper = action_type.upper()
            for prefix, keywords in action_keywords.items():
                if prefix in action_upper:
                    enhanced = f"{keywords} {enhanced}"
                    break

        return enhanced


async def search_eu4health_templates_execute(
    query: str,
    strand: str | None = None,
    action_type: str | None = None,
    topic: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search EU4Health guidance documents for application information.

    Args:
        query: What to search for (e.g., "action grant eligibility")
        strand: Filter by strand (CRISIS, PREVENTION, HEALTH_SYSTEMS, DIGITAL)
        action_type: Filter by action type (AG, JA, OG, etc.)
        topic: Specific topic to focus on (e.g., 'eligibility', 'budget')
        top_k: Number of results

    Returns:
        Matching excerpts from EU4Health documents with metadata
    """
    try:
        from app.services.vector_search_service import VectorSearchService

        tool = EU4HealthTemplateSearchTool()
        service = VectorSearchService()

        # Build enhanced query
        enhanced_query = tool.build_enhanced_query(query, strand, action_type)

        # Detect relevant sections and strand
        sections = tool.detect_section(query)
        detected_strand = strand or tool.detect_strand(query)

        # Search with programme filter for EU4Health
        results = service.search(
            query=enhanced_query,
            num_results=top_k * 2,  # Get more to filter
            filters={"programme": "eu4health"},
        )

        # Format results
        formatted_results = []
        seen_content = set()

        for result in results:
            # Skip duplicates
            content_key = result.content[:100]
            if content_key in seen_content:
                continue
            seen_content.add(content_key)

            # Determine section from content
            content_lower = result.content.lower()
            matched_section = 'general'
            for section_id, config in EU4HEALTH_SECTIONS.items():
                for kw in config['keywords']:
                    if kw in content_lower:
                        matched_section = section_id
                        break

            # Determine strand from content
            content_strand = 'general'
            if any(kw in content_lower for kw in ['crisis', 'emergency', 'hera', 'preparedness']):
                content_strand = 'CRISIS'
            elif any(kw in content_lower for kw in ['cancer', 'prevention', 'ncd', 'screening']):
                content_strand = 'PREVENTION'
            elif any(kw in content_lower for kw in ['health system', 'workforce', 'hta', 'medicines']):
                content_strand = 'HEALTH_SYSTEMS'
            elif any(kw in content_lower for kw in ['digital', 'ehds', 'ehealth', 'data']):
                content_strand = 'DIGITAL'

            formatted_results.append({
                'content': result.content[:1000],  # Limit content length
                'document_title': getattr(result, 'document_title', 'EU4Health Document'),
                'section': matched_section,
                'section_description': EU4HEALTH_SECTIONS.get(matched_section, {}).get('description', ''),
                'strand': content_strand,
                'relevance_score': getattr(result, 'score', 0.0),
            })

            if len(formatted_results) >= top_k:
                break

        return {
            'success': True,
            'results': formatted_results,
            'total_found': len(formatted_results),
            'query': query,
            'enhanced_query': enhanced_query,
            'detected_sections': sections,
            'detected_strand': detected_strand,
            'filters': {
                'strand': strand,
                'action_type': action_type,
                'topic': topic,
            },
            'metadata': {
                'tool': 'search_eu4health_templates',
                'programme': 'eu4health',
                'implementing_agency': 'HaDEA',
                'note': 'Results from EU4Health Programme documents (2021-2027)'
            }
        }

    except Exception as e:
        logger.error(f"EU4Health template search error: {e}")
        return {
            'success': False,
            'error': str(e),
            'results': [],
        }

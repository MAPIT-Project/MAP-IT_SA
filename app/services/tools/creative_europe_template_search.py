"""
Creative Europe Template and Guidance Search Tool

Searches Creative Europe documents (Work Programmes, CulturEU Funding Guide,
strand overviews) for application guidance, eligibility criteria, and
programme-specific information.

Uses the ingested Creative Europe documents to provide targeted answers
about actions, requirements, and funding opportunities.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Key sections in Creative Europe documents
CREATIVE_EUROPE_SECTIONS = {
    'culture_strand': {
        'keywords': ['culture', 'cultural', 'cooperation project', 'network', 'platform', 'literary translation'],
        'description': 'CULTURE strand - European cooperation projects, networks, platforms'
    },
    'media_strand': {
        'keywords': ['media', 'audiovisual', 'film', 'development', 'distribution', 'cinema', 'festival', 'tv', 'online'],
        'description': 'MEDIA strand - audiovisual, film development, distribution, training'
    },
    'cross_sectoral': {
        'keywords': ['cross-sectoral', 'cross sectoral', 'innovation lab', 'news media', 'journalism', 'media literacy'],
        'description': 'Cross-sectoral strand - innovation labs, news media, media literacy'
    },
    'eligibility': {
        'keywords': ['eligibility', 'eligible', 'who can apply', 'applicant', 'participating countries', 'legal entity'],
        'description': 'Eligibility criteria for organizations'
    },
    'budget': {
        'keywords': ['budget', 'funding', 'grant', 'co-financing', 'financial', 'contribution', 'lump sum'],
        'description': 'Budget rules, grant amounts, and funding rates'
    },
    'evaluation': {
        'keywords': ['evaluation', 'criteria', 'assessment', 'award', 'scoring', 'quality', 'selection'],
        'description': 'Evaluation and selection criteria'
    },
    'cooperation_projects': {
        'keywords': ['cooperation', 'small scale', 'medium scale', 'large scale', 'consortium'],
        'description': 'European Cooperation Projects requirements'
    },
    'development': {
        'keywords': ['development', 'slate', 'single project', 'mini-slate', 'co-development'],
        'description': 'MEDIA development actions (film/TV/games)'
    },
    'distribution': {
        'keywords': ['distribution', 'sales agent', 'cinema', 'exhibition', 'film sales'],
        'description': 'MEDIA distribution and exhibition support'
    },
    'audience': {
        'keywords': ['audience', 'film education', 'literacy', 'festival', 'innovative'],
        'description': 'Audience development and engagement'
    },
    'green': {
        'keywords': ['green', 'sustainability', 'environmental', 'ecological', 'climate'],
        'description': 'Green and sustainability requirements'
    },
    'deadlines': {
        'keywords': ['deadline', 'submission', 'call', 'calendar', 'date'],
        'description': 'Application deadlines and call calendar'
    },
}


class CreativeEuropeTemplateSearchTool:
    """Tool for searching Creative Europe guidance and templates."""

    def __init__(self):
        self.sections = CREATIVE_EUROPE_SECTIONS

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

        if any(kw in query_lower for kw in ['media', 'film', 'audiovisual', 'tv', 'cinema']):
            return 'MEDIA'
        elif any(kw in query_lower for kw in ['culture', 'cultural', 'artistic', 'heritage']):
            return 'CULTURE'
        elif any(kw in query_lower for kw in ['cross-sectoral', 'innovation lab', 'journalism', 'news']):
            return 'CROSS-SECTORAL'

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
                'CULTURE': 'cultural cooperation artistic creative sectors',
                'MEDIA': 'audiovisual film television cinema production distribution',
                'CROSS-SECTORAL': 'cross-sectoral innovation lab news media journalism',
            }
            if strand.upper() in strand_keywords:
                enhanced = f"{strand_keywords[strand.upper()]} {enhanced}"

        if action_type:
            action_keywords = {
                'COOP': 'cooperation project consortium partners',
                'DEV': 'development slate film production script',
                'DIST': 'distribution cinema exhibition release',
                'TRAIN': 'training professional skills audiovisual',
                'FEST': 'festival film programming audience',
                'INNOV': 'innovation lab technology creative',
            }
            for prefix, keywords in action_keywords.items():
                if prefix in action_type.upper():
                    enhanced = f"{keywords} {enhanced}"
                    break

        return enhanced


async def search_creative_europe_templates_execute(
    query: str,
    strand: str | None = None,
    action_type: str | None = None,
    topic: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Search Creative Europe guidance documents for application information.

    Args:
        query: What to search for (e.g., "MEDIA development eligibility")
        strand: Filter by CULTURE, MEDIA, or CROSS-SECTORAL
        action_type: Filter by action type (e.g., 'DEVSLATE', 'COOP-SMALL')
        topic: Specific topic to focus on (e.g., 'eligibility', 'budget')
        top_k: Number of results

    Returns:
        Matching excerpts from Creative Europe documents with metadata
    """
    try:
        from app.services.vector_search_service import VectorSearchService

        tool = CreativeEuropeTemplateSearchTool()
        service = VectorSearchService()

        # Build enhanced query
        enhanced_query = tool.build_enhanced_query(query, strand, action_type)

        # Detect relevant sections and strand
        sections = tool.detect_section(query)
        detected_strand = strand or tool.detect_strand(query)

        # Search with programme filter for Creative Europe
        results = service.search(
            query=enhanced_query,
            num_results=top_k * 2,  # Get more to filter
            filters={"programme": "creative_europe"},
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
            for section_id, config in CREATIVE_EUROPE_SECTIONS.items():
                for kw in config['keywords']:
                    if kw in content_lower:
                        matched_section = section_id
                        break

            # Determine strand from content
            content_strand = 'general'
            if any(kw in content_lower for kw in ['media', 'audiovisual', 'film']):
                content_strand = 'MEDIA'
            elif any(kw in content_lower for kw in ['culture', 'cultural', 'artistic']):
                content_strand = 'CULTURE'
            elif any(kw in content_lower for kw in ['cross-sectoral', 'innovation lab', 'journalism']):
                content_strand = 'CROSS-SECTORAL'

            formatted_results.append({
                'content': result.content[:1000],  # Limit content length
                'document_title': getattr(result, 'document_title', 'Creative Europe Document'),
                'section': matched_section,
                'section_description': CREATIVE_EUROPE_SECTIONS.get(matched_section, {}).get('description', ''),
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
                'tool': 'search_creative_europe_templates',
                'programme': 'creative_europe',
                'note': 'Results from Creative Europe Programme documents (2021-2027)'
            }
        }

    except Exception as e:
        logger.error(f"Creative Europe template search error: {e}")
        return {
            'success': False,
            'error': str(e),
            'results': [],
        }

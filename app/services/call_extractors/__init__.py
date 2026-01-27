"""
Call Extractors Module

Provides structured extraction of funding call data from Work Programme documents.
Each EU funding programme has its own extractor that understands the document format.

Supported Programmes:
    - Horizon Europe (2021-2027) - Main EU R&I programme
    - Digital Europe (2021-2027) - Digital technology deployment
    - LIFE (2021-2027) - Environment and climate action
    - Erasmus+ (2021-2027) - Education, training, youth, and sport

Usage:
    from app.services.call_extractors import HorizonEuropeExtractor

    extractor = HorizonEuropeExtractor()
    calls = extractor.extract_from_content(content, "Document Title")

Adding New Programmes:
    See .agent_tasks/ADDING_NEW_FUNDING_PROGRAMMES.md
"""

from .base import CallExtractor, FundingCall
from .creative_europe import CreativeEuropeExtractor
from .digital_europe import DigitalEuropeExtractor
from .erasmus_plus import ErasmusPlusExtractor
from .eu4health import EU4HealthExtractor
from .horizon_europe import HorizonEuropeExtractor
from .life_programme import LIFEExtractor

# Map programme IDs to extractor classes
EXTRACTORS = {
    'horizon_europe': HorizonEuropeExtractor,
    'digital_europe': DigitalEuropeExtractor,
    'life': LIFEExtractor,
    'erasmus_plus': ErasmusPlusExtractor,
    'creative_europe': CreativeEuropeExtractor,
    'eu4health': EU4HealthExtractor,
}

def get_extractor(programme: str) -> CallExtractor:
    """Get the appropriate extractor for a programme."""
    if programme not in EXTRACTORS:
        raise ValueError(f"No extractor for programme: {programme}. Available: {list(EXTRACTORS.keys())}")
    return EXTRACTORS[programme]()

__all__ = [
    'CallExtractor',
    'FundingCall',
    'HorizonEuropeExtractor',
    'DigitalEuropeExtractor',
    'LIFEExtractor',
    'ErasmusPlusExtractor',
    'CreativeEuropeExtractor',
    'EU4HealthExtractor',
    'EXTRACTORS',
    'get_extractor',
]


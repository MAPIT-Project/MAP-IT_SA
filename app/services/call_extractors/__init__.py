"""
Call Extractors Module

Provides structured extraction of funding call data from Work Programme documents.
Each EU funding programme has its own extractor that understands the document format.

Usage:
    from app.services.call_extractors import HorizonEuropeExtractor
    
    extractor = HorizonEuropeExtractor(db_connection)
    calls = extractor.extract_from_document(document_id)
"""

from .base import CallExtractor, FundingCall
from .horizon_europe import HorizonEuropeExtractor

__all__ = [
    'CallExtractor',
    'FundingCall', 
    'HorizonEuropeExtractor',
]


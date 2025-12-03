"""
Intelligent Document Retrieval Service

Leverages the comprehensive document library to answer ANY question about
Horizon Europe, not just call-specific questions.

Key Features:
- Smart query classification (identifies what type of info is needed)
- Multi-document search across all 29 documents
- Prioritizes relevant document types based on question
- PostgreSQL full-text search for speed
"""

import logging
import re
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)


class IntelligentRetrieval:
    """Intelligent retrieval across comprehensive document library"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
    def classify_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify what type of information the user is looking for.
        This helps prioritize which documents to search.
        """
        query_lower = query.lower()
        
        # Initialize classification
        classification = {
            'primary_intent': 'general',
            'document_types': [],
            'clusters': [],
            'keywords': [],
            'priority_boost': {}
        }
        
        # MSCA-specific questions
        if any(term in query_lower for term in ['msca', 'marie', 'skłodowska', 'curie', 'fellowship', 'postdoc']):
            classification['primary_intent'] = 'msca'
            classification['document_types'] = ['other']  # MSCA guide is classified as "other"
            classification['keywords'] = ['msca', 'fellowship', 'marie curie']
            classification['priority_boost'] = {'msca': 2.0}
        
        # Eligibility questions
        elif any(term in query_lower for term in ['eligibility', 'eligible', 'can i apply', 'can we apply', 'participation']):
            classification['primary_intent'] = 'eligibility'
            classification['document_types'] = ['programme_guide', 'general_annexes', 'work_programme']
            classification['keywords'] = ['eligibility', 'participation', 'member states', 'associated countries']
        
        # Budget/Financial questions
        elif any(term in query_lower for term in ['budget', 'funding rate', 'funding', 'cost', 'financial', 'lump sum']):
            classification['primary_intent'] = 'financial'
            classification['document_types'] = ['programme_guide', 'other', 'general_annexes']  # AGA and lump sum guides are 'other'
            classification['keywords'] = ['budget', 'funding', 'cost', 'financial', 'lump sum', 'contribution']
        
        # Legal entity/administrative
        elif any(term in query_lower for term in ['legal entity', 'lear', 'validation', 'registration']):
            classification['primary_intent'] = 'administrative'
            classification['document_types'] = ['other', 'programme_guide']  # Legal entity rules are 'other'
            classification['keywords'] = ['legal entity', 'lear', 'validation', 'registration']
        
        # Application/submission process
        elif any(term in query_lower for term in ['how to apply', 'submit', 'proposal', 'application', 'portal']):
            classification['primary_intent'] = 'application_process'
            classification['document_types'] = ['other', 'programme_guide', 'general_annexes']  # Online Manual is classified as 'other'
            classification['keywords'] = ['application', 'submission', 'proposal', 'portal', 'submit']
        
        # Grant agreement/management
        elif any(term in query_lower for term in ['grant agreement', 'mga', 'reporting', 'amendment']):
            classification['primary_intent'] = 'grant_management'
            classification['document_types'] = ['other', 'programme_guide']  # AGA and management guides are 'other'
            classification['keywords'] = ['grant agreement', 'mga', 'reporting', 'amendment', 'management']
        
        # Cluster-specific questions (if not about specific call)
        else:
            # Check for cluster mentions
            cluster_mapping = {
                'health': ('CLUSTER-1', 'work_programme'),
                'culture': ('CLUSTER-2', 'work_programme'),
                'civil security': ('CLUSTER-3', 'work_programme'),
                'digital': ('CLUSTER-4', 'work_programme'),
                'industry': ('CLUSTER-4', 'work_programme'),
                'space': ('CLUSTER-4', 'work_programme'),
                'climate': ('CLUSTER-5', 'work_programme'),
                'energy': ('CLUSTER-5', 'work_programme'),
                'mobility': ('CLUSTER-5', 'work_programme'),
                'food': ('CLUSTER-6', 'work_programme'),
                'bioeconomy': ('CLUSTER-6', 'work_programme'),
                'agriculture': ('CLUSTER-6', 'work_programme')
            }
            
            for keyword, (cluster, doc_type) in cluster_mapping.items():
                if keyword in query_lower:
                    classification['primary_intent'] = 'cluster_specific'
                    classification['clusters'].append(cluster)
                    classification['document_types'].append(doc_type)
                    classification['keywords'].append(keyword)
                    break
            
            # Default: search all key documents
            if not classification['document_types']:
                classification['document_types'] = ['programme_guide', 'work_programme', 'general_annexes']
        
        return classification
    
    def search_documents(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:  # Increased from 15
        """
        Intelligent search across all documents based on query classification.
        
        Returns list of relevant chunks with metadata.
        """
        try:
            # Classify the query
            classification = self.classify_query_intent(query)
            logger.info(f"📊 Query classification: {classification['primary_intent']}")
            logger.info(f"   Document types: {classification['document_types']}")
            logger.info(f"   Keywords: {classification['keywords']}")
            
            # Build search query
            search_terms = ' '.join(classification['keywords']) if classification['keywords'] else query
            
            conn = self.db_pool.getconn()
            try:
                cursor = conn.cursor()
                
                # Build WHERE clause for document type filtering
                if classification['document_types']:
                    doc_type_filter = f"AND sd.document_type IN ({','.join(['%s'] * len(classification['document_types']))})"
                    query_params = classification['document_types'] + [search_terms, limit]
                else:
                    doc_type_filter = ""
                    query_params = [search_terms, limit]
                
                # Add cluster filter if specified
                cluster_filter = ""
                if classification['clusters']:
                    cluster_filter = f"AND sd.scope_identifier IN ({','.join(['%s'] * len(classification['clusters']))})"
                    query_params = classification['document_types'] + classification['clusters'] + [search_terms, limit]
                
                # Execute intelligent search with full-text ranking
                search_query = f"""
                    SELECT 
                        sdc.id as chunk_id,
                        sdc.chunk_text,
                        sdc.section_title,
                        sd.document_title,
                        sd.document_type,
                        sd.scope_identifier,
                        ts_rank(
                            to_tsvector('english', sdc.chunk_text),
                            plainto_tsquery('english', %s)
                        ) as relevance_score
                    FROM shared_document_chunks sdc
                    JOIN shared_documents sd ON sdc.document_id = sd.id
                    WHERE to_tsvector('english', sdc.chunk_text) @@ plainto_tsquery('english', %s)
                    {doc_type_filter}
                    {cluster_filter}
                    ORDER BY relevance_score DESC
                    LIMIT %s
                """
                
                # Note: For full-text search, we need the search term twice (for ranking and matching)
                final_params = []
                if classification['document_types']:
                    final_params.extend(classification['document_types'])
                if classification['clusters']:
                    final_params.extend(classification['clusters'])
                final_params.extend([search_terms, search_terms, limit])
                
                cursor.execute(search_query, tuple(final_params))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'chunk_id': row[0],
                        'content': row[1],
                        'section_title': row[2],
                        'citation': f"{row[3]}" + (f" - {row[2]}" if row[2] else ""),
                        'metadata': {
                            'source': 'intelligent_retrieval',
                            'document_type': row[4],
                            'scope_identifier': row[5],
                            'relevance_score': float(row[6]),
                            'primary_intent': classification['primary_intent']
                        }
                    })
                
                cursor.close()
                logger.info(f"✅ Found {len(results)} relevant chunks")
                
                return results
                
            finally:
                self.db_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"❌ Error in intelligent retrieval: {e}", exc_info=True)
            return []
    
    def search_by_document_type(self, query: str, document_types: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search specific document types.
        Useful when you know exactly which documents to search.
        """
        try:
            conn = self.db_pool.getconn()
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        sdc.id,
                        sdc.chunk_text,
                        sdc.section_title,
                        sd.document_title,
                        sd.document_type,
                        ts_rank(
                            to_tsvector('english', sdc.chunk_text),
                            plainto_tsquery('english', %s)
                        ) as score
                    FROM shared_document_chunks sdc
                    JOIN shared_documents sd ON sdc.document_id = sd.id
                    WHERE to_tsvector('english', sdc.chunk_text) @@ plainto_tsquery('english', %s)
                    AND sd.document_type = ANY(%s)
                    ORDER BY score DESC
                    LIMIT %s
                """, (query, query, document_types, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'chunk_id': row[0],
                        'content': row[1],
                        'section_title': row[2],
                        'citation': row[3],
                        'metadata': {
                            'document_type': row[4],
                            'relevance_score': float(row[5])
                        }
                    })
                
                cursor.close()
                return results
                
            finally:
                self.db_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error searching by document type: {e}")
            return []


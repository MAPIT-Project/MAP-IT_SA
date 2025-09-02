"""
Enhanced RAG service specifically for Horizon Europe call and topic queries.
This service leverages the comprehensive call documentation ingested into the vector database.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import logging
from datetime import datetime

from .vector_search_service import VectorSearchService, SearchResult
from .supabase_client import SupabaseVectorStore
from .embedding_service import EmbeddingService
from .rag_service import CordisRAG
from .enhanced_call_search import EnhancedCallSearchService, EnhancedSearchResult

logger = logging.getLogger(__name__)

class CallSpecificRAG:
    """Enhanced RAG system specialized for Horizon Europe call and topic queries."""
    
    def __init__(
        self,
        vector_search_service: Optional[VectorSearchService] = None,
        supabase_client: Optional[SupabaseVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        cordis_rag: Optional[CordisRAG] = None
    ):
        """Initialize the call-specific RAG system."""
        self.supabase = supabase_client or SupabaseVectorStore()
        self.embedder = embedding_service or EmbeddingService(cache_client=self.supabase)
        self.vector_search = vector_search_service or VectorSearchService(self.supabase, self.embedder)
        self.cordis_rag = cordis_rag  # Use provided instance, don't create new
        
        # Initialize enhanced call search service
        try:
            self.enhanced_search = EnhancedCallSearchService()
            logger.info("✅ Enhanced call search service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Enhanced call search not available: {e}")
            self.enhanced_search = None
        
        logger.info("✅ Call-specific RAG system initialized")
    
    def detect_call_specific_intent(self, question: str) -> Tuple[str, Optional[str], float]:
        """
        Enhanced intent detection specifically for call and topic queries.
        Returns (intent_type, call_identifier, confidence)
        """
        question_lower = question.lower()
        question_upper = question.upper()
        
        # Enhanced pattern matching for call identifiers (e.g., HORIZON-CL4-2024-DATA-01-01)
        # Calls have three parts after the cluster/year: main-topic-subtopic or main-action-number
        call_pattern = r'HORIZON[-\s]?(?:CL\d|EIC|ERC|MSCA|WIDERA)[-\s]?\d{4}[-\s]?[A-Za-z]+-[A-Za-z0-9]+-[A-Za-z0-9]+'
        call_match = re.search(call_pattern, question_upper)
        
        if call_match:
            call_id = call_match.group(0)
            logger.info(f"🎯 Detected specific call identifier: {call_id}")
            return ("SPECIFIC_CALL", call_id, 0.95)
        
        # Pattern matching for topic identifiers (e.g., HORIZON-CL4-2024-DATA-01)
        # Topics end with two digits after the main part
        topic_pattern = r'HORIZON[-\s]?(?:CL\d|EIC|ERC|MSCA|WIDERA)[-\s]?\d{4}[-\s]?[A-Za-z]+-\d{2}'
        topic_match = re.search(topic_pattern, question_upper)
        
        if topic_match:
            topic_id = topic_match.group(0)
            logger.info(f"🎯 Detected specific topic identifier: {topic_id}")
            return ("SPECIFIC_TOPIC", topic_id, 0.9)
        
        # Cluster-specific queries with more context awareness and expanded keywords
        cluster_keywords = {
            "health": ["health cluster", "medical research", "biomedical", "pharmaceutical", "disease funding", "healthcare innovation", "biotech research"],
            "digital": ["digital cluster", "industry 4.0", "space research", "ict topics", "ai call", "quantum computing", "data funding", "digital transformation", "artificial intelligence", "machine learning", "cloud computing", "cyber physical systems"],
            "climate": ["climate cluster", "energy funding", "mobility research", "renewable energy", "green deal", "carbon neutral", "clean energy", "sustainable transport", "climate action", "decarbonization", "energy transition"],
            "food": ["food cluster", "bioeconomy", "agricultural research", "environmental funding", "natural resources", "sustainable agriculture", "food security", "agri-food", "rural development"],
            "culture": ["culture cluster", "creativity funding", "inclusive society", "arts programme", "cultural heritage", "creative industries", "social sciences", "humanities research"],
            "security": ["civil security", "security research", "safety funding", "defense programme", "cybersecurity", "border security", "disaster resilience", "public safety"],
            "eic": ["eic accelerator", "innovation council", "startup grant", "sme funding", "accelerator programme", "eic pathfinder", "eic transition", "deep tech innovation"],
            "erc": ["erc grant", "research council", "frontier research", "excellent science", "erc starting grant", "erc consolidator", "erc advanced", "erc synergy"]
        }
        
        # Check for cluster-specific phrases with higher precision
        for cluster, keywords in cluster_keywords.items():
            # Check if any keyword appears as a whole word in the question
            for keyword in keywords:
                # Use word boundaries to avoid partial matches
                if re.search(rf'\b{re.escape(keyword)}\b', question_lower):
                    logger.info(f"🎯 Detected cluster-specific query: {cluster}")
                    return ("CLUSTER_SPECIFIC", cluster, 0.85)
        
        # General call/topic query with enhanced keyword detection
        call_keywords = ["open calls", "funding opportunities", "grant application", "proposal deadline", "call for proposals", "topic search", "funding call", "research grant", "calls for", "calls related to", "calls about", "available calls", "funding for"]
        general_call_indicators = ["what are some", "are there any", "show me", "list of", "find calls for", "looking for calls", "search for funding", "what calls", "which calls"]
        
        # Check for general call queries with indicators using word boundaries
        has_call_keyword = any(re.search(rf'\b{re.escape(keyword)}\b', question_lower) for keyword in call_keywords)
        has_general_indicator = any(re.search(rf'\b{re.escape(indicator)}\b', question_lower) for indicator in general_call_indicators)
        
        # CRITICAL FIX: Also check for specific patterns like "calls related to X" or "calls about X"
        call_patterns = [
            r'\bcalls?\s+(for|about|related\s+to|concerning|regarding)\s+\w+',
            r'\bopen\s+calls?\s+\w+',
            r'\bfunding\s+(for|about|related\s+to)\s+\w+',
            r'\bwhat.*calls?.*for\s+\w+',
            r'\bshow.*calls?\s+\w+',
            r'\bfind.*calls?\s+\w+'
        ]
        
        has_call_pattern = any(re.search(pattern, question_lower) for pattern in call_patterns)
        
        if has_call_keyword or has_general_indicator or has_call_pattern:
            logger.info("🎯 Detected general call/topic query")
            # Higher confidence if multiple indicators are present
            confidence = 0.95 if (has_call_keyword and has_general_indicator) or has_call_pattern else 0.85
            return ("GENERAL_CALL", None, confidence)
        
        # IMPORTANT: Check for procedural questions FIRST before keyword analysis
        # These should NOT be handled by call-specific RAG but by the general RAG with documents
        procedural_patterns = [
            r'\bhow\s+to\b',
            r'\bhow\s+do\s+i\b',
            r'\bhow\s+can\s+i\b',
            r'\bwhat\s+is\s+the\s+process\b',
            r'\bwhat\s+are\s+the\s+steps\b',
            r'\bwhat\s+are\s+the\s+requirements\b',
            r'\bwhat\s+is\s+the\s+procedure\b',
            r'\bwhat\s+are\s+the\s+criteria\b',
            r'\bhow\s+should\s+i\b',
            r'\bwhat\s+do\s+i\s+need\s+to\b'
        ]
        
        # Check if this is a procedural question - if so, defer to general RAG
        for pattern in procedural_patterns:
            if re.search(pattern, question_lower):
                logger.info("🎯 Detected procedural question - deferring to general RAG")
                return ("GENERAL_QUERY", None, 0.95)  # High confidence that this is procedural
        
        # Direct fallback analysis without calling back to CORDIS RAG to avoid circular dependency
        # Check for funding-related keywords that suggest call queries (but not procedural questions)
        funding_keywords = ["funding", "grant", "proposal", "deadline", "opportunity", "submission", "eligibility", "tender", "competition"]
        project_keywords = ["project", "research", "initiative", "development", "study", "investigation", "programme"]
        
        funding_matches = sum(1 for word in funding_keywords if re.search(rf'\b{re.escape(word)}\b', question_lower))
        project_matches = sum(1 for word in project_keywords if re.search(rf'\b{re.escape(word)}\b', question_lower))
        
        # Only proceed with call/project classification if we didn't detect procedural intent
        if funding_matches > project_matches:
            return ("GENERAL_CALL", None, min(0.8, 0.5 + funding_matches * 0.1))
        elif project_matches > funding_matches:
            return ("SEARCH_PROJECTS", None, min(0.8, 0.5 + project_matches * 0.1))
        else:
            # Default to general query for ambiguous cases
            return ("GENERAL_QUERY", None, 0.6)
    
    def handle_call_specific_query(
        self,
        question: str,
        call_identifier: Optional[str] = None,
        max_context_chunks: int = 8,
        search_type: str = "hybrid"
    ) -> Dict[str, Any]:
        """Handle queries specifically about Horizon Europe calls and topics."""
        
        logger.info(f"📋 Handling call-specific query: '{question}'")
        if call_identifier:
            logger.info(f"   Call/Topic ID: {call_identifier}")
        
        try:
            # Try enhanced search first if available
            if self.enhanced_search and not call_identifier:
                logger.info("🚀 Using enhanced call search service")
                
                enhanced_result = self.enhanced_search.search_calls_enhanced(
                    query=question,
                    max_results=max_context_chunks,
                    include_closed=True,  # Include closed calls for completeness
                    enable_facet_analysis=True
                )
                
                if enhanced_result['status'] == 'success':
                    # Use enhanced search results even if empty - it may have explanations
                    return self._process_enhanced_search_results(question, enhanced_result)
                else:
                    logger.warning("⚠️ Enhanced search failed, falling back to vector search")
            
            # Fallback to original vector search
            logger.info(f"📊 Using vector search fallback (search_type: {search_type})")
            
            # Build search filters based on call specificity
            filters = {}
            if call_identifier:
                # For specific calls/topics, search within that identifier
                filters["call_identifier"] = call_identifier
            
            # Search for relevant document chunks
            search_results = self.vector_search.search(
                query=question,
                search_type=search_type,
                num_results=max_context_chunks * 2,  # Get more for filtering
                similarity_threshold=0.65,  # Lower threshold for call-specific queries
                filters=filters,
                rerank=True
            )
            
            if not search_results:
                return self._create_no_call_results_response(question, call_identifier)
            
            # Select best chunks for context
            context_chunks = self._select_call_context_chunks(search_results, max_context_chunks, call_identifier)
            
            # Build context for LLM
            context = self._build_call_specific_context(context_chunks, call_identifier)
            
            # Generate answer using specialized prompt
            answer = self._generate_call_specific_answer(question, context, context_chunks, call_identifier)
            
            return {
                'answer': answer,
                'intent': 'CALL_SPECIFIC',
                'call_identifier': call_identifier,
                'sources': self._format_call_sources(context_chunks),
                'search_type': search_type,
                'chunks_used': len(context_chunks),
                'confidence': self._calculate_call_confidence(search_results, call_identifier),
                'data_source': 'Horizon Europe Call Documentation',
                'processing_time': 0,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ Call-specific query handling failed: {e}")
            return self._create_error_response(str(e))
    
    def _select_call_context_chunks(
        self,
        search_results: List[SearchResult],
        max_chunks: int,
        call_identifier: Optional[str] = None
    ) -> List[SearchResult]:
        """Select the best chunks for call-specific context."""
        if len(search_results) <= max_chunks:
            return search_results
        
        # Prioritize chunks from the specific call if available
        prioritized_results = []
        other_results = []
        
        for result in search_results:
            metadata = result.metadata or {}
            result_call_id = metadata.get('call_identifier') or metadata.get('identifier')
            
            if call_identifier and result_call_id and call_identifier in result_call_id:
                prioritized_results.append(result)
            else:
                other_results.append(result)
        
        # Combine prioritized results with others
        selected = prioritized_results[:max_chunks]
        remaining_slots = max_chunks - len(selected)
        
        if remaining_slots > 0:
            selected.extend(other_results[:remaining_slots])
        
        logger.info(f"📋 Selected {len(selected)} chunks ({len(prioritized_results)} from target call)")
        return selected
    
    def _build_call_specific_context(
        self,
        chunks: List[SearchResult],
        call_identifier: Optional[str] = None
    ) -> str:
        """Build specialized context for call-specific queries."""
        context_parts = []
        
        context_parts.append("OFFICIAL HORIZON EUROPE CALL DOCUMENTATION CONTEXT:")
        context_parts.append("=" * 60)
        
        if call_identifier:
            context_parts.append(f"SPECIFIC CALL/TOPIC: {call_identifier}")
            context_parts.append("=" * 60)
        
        for i, chunk in enumerate(chunks, 1):
            context_part = f"[Source {i}]"
            
            metadata = chunk.metadata or {}
            
            if metadata.get('document_type'):
                context_part += f"\nDocument Type: {metadata['document_type']}"
            
            if metadata.get('call_identifier'):
                context_part += f"\nCall ID: {metadata['call_identifier']}"
            
            if metadata.get('cluster_name'):
                context_part += f"\nCluster: {metadata['cluster_name']}"
            
            if metadata.get('programme_year'):
                context_part += f"\nProgramme Year: {metadata['programme_year']}"
            
            if metadata.get('section_title'):
                context_part += f"\nSection: {metadata['section_title']}"
            
            if metadata.get('page_number'):
                context_part += f"\nPage: {metadata['page_number']}"
            
            context_part += f"\nContent: {chunk.content}\n"
            context_parts.append(context_part)
        
        context_parts.append("=" * 60)
        context_parts.append("END OF OFFICIAL DOCUMENTATION CONTEXT")
        
        return "\n".join(context_parts)
    
    def _generate_call_specific_answer(
        self,
        question: str,
        context: str,
        chunks: List[SearchResult],
        call_identifier: Optional[str] = None
    ) -> str:
        """Generate specialized answer for call-specific queries."""
        
        # Check if specific call is mentioned in the context
        call_in_context = False
        if call_identifier:
            # Normalize the call identifier for matching (remove any spaces or variations)
            normalized_call_id = call_identifier.replace(' ', '').replace('_', '-').upper()
            context_upper = context.upper()
            call_in_context = normalized_call_id in context_upper
        
        prompt = f"""You are an expert on Horizon Europe funding calls and topics.
Based on the official Horizon Europe documentation provided, answer the user's question
with precise, accurate information about calls, topics, and funding opportunities.

OFFICIAL DOCUMENTATION CONTEXT:
{context}

USER QUESTION: {question}

IMPORTANT INSTRUCTIONS:
1. **Be extremely precise** about call details, deadlines, budgets, and requirements
2. **Reference specific call/topic identifiers** when available (e.g., HORIZON-CL4-2024-DATA-01-01)
3. **Quote exact figures** from the documentation (budgets, deadlines, eligibility criteria)
4. **Highlight key requirements** like consortium composition, evaluation criteria, submission procedures
5. **Provide actionable guidance** on how to apply and what documents are needed
6. **Mention specific clusters and programmes** (Health, Digital, Climate, EIC, ERC, etc.)
7. **Include deadlines with exact dates** and urgency indicators when relevant
8. **Reference the specific document sources** you used for your answer
9. **If information is incomplete**, acknowledge this and suggest where to find more details
10. **Use professional but accessible language** suitable for researchers and grant managers
11. **CRITICAL: If the specific call {call_identifier} is not mentioned in the context**, clearly state that the specific call details are not available in the provided documentation and provide general Horizon Europe information that might be relevant. Do not hallucinate or invent specific details for this call.

STRUCTURE YOUR ANSWER:
- Start with a clear summary answering the main question
- If specific call details are available, provide detailed information in organized sections
- If specific call is not found, acknowledge this and provide general Horizon Europe requirements
- Include specific requirements and procedures when available
- Add application guidance and next steps
- End with source references

ANSWER:"""
        
        try:
            answer = self.cordis_rag._call_llm_for_generation(
                role="Horizon Europe Call Expert",
                prompt=prompt
            )
            
            logger.info(f"✅ Generated call-specific answer ({len(answer)} chars)")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Call-specific answer generation failed: {e}")
            return f"I apologize, but I encountered an error while generating the response for this call-specific query: {str(e)}"
    
    def _format_call_sources(self, chunks: List[SearchResult]) -> List[Dict[str, str]]:
        """Format source citations for call-specific answers."""
        sources = []
        seen_docs = set()
        
        for chunk in chunks:
            metadata = chunk.metadata or {}
            doc_id = metadata.get('document_id') or metadata.get('filename')
            
            if doc_id and doc_id not in seen_docs:
                seen_docs.add(doc_id)
                source = {
                    'title': metadata.get('document_title') or metadata.get('filename'),
                    'type': metadata.get('document_type', 'Unknown'),
                    'call_identifier': metadata.get('call_identifier'),
                    'cluster': metadata.get('cluster_name'),
                    'programme_year': metadata.get('programme_year')
                }
                
                if metadata.get('section_title'):
                    source['section'] = metadata.get('section_title')
                if metadata.get('page_number'):
                    source['page'] = metadata.get('page_number')
                
                sources.append(source)
        
        return sources
    
    def _calculate_call_confidence(
        self,
        search_results: List[SearchResult],
        call_identifier: Optional[str] = None
    ) -> float:
        """Calculate confidence score for call-specific answers."""
        if not search_results:
            return 0.0
        
        # Average of top 3 scores
        top_scores = [r.score for r in search_results[:3]]
        avg_score = sum(top_scores) / len(top_scores)
        
        # Boost confidence if we have results from the specific call
        if call_identifier:
            call_specific_results = [
                r for r in search_results 
                if r.metadata and r.metadata.get('call_identifier') and call_identifier in r.metadata.get('call_identifier')
            ]
            if call_specific_results:
                avg_score = min(1.0, avg_score * 1.2)  # 20% boost for call-specific matches
        
        return avg_score
    
    def _process_enhanced_search_results(
        self,
        question: str,
        enhanced_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process enhanced search results into RAG-compatible format."""
        
        results = enhanced_result.get('results', [])
        facets = enhanced_result.get('facets', {})
        metadata = enhanced_result.get('search_metadata', {})
        
        if not results:
            # Check if this is due to filtering and we have an explanation
            filter_explanation = metadata.get('filter_explanation', '')
            if filter_explanation:
                return self._create_filtered_no_results_response(question, metadata)
            else:
                return self._create_no_call_results_response(question)
        
        # Build comprehensive answer from enhanced results
        answer_parts = []
        answer_parts.append(f"I found {len(results)} relevant funding opportunities based on your query about '*{question}*':")
        answer_parts.append("")
        
        # Add search metadata and filtering info
        if metadata.get('semantic_tags_used', 0) > 0:
            answer_parts.append(f"🏷️ **Search Enhancement:** Used {metadata['semantic_tags_used']} semantic tags for improved relevance")
            
        # Add filter information if applied
        filters_applied = metadata.get('filters_applied', [])
        filter_intention = metadata.get('filter_intention', 'all')
        if filters_applied and 'no_filters' not in filters_applied:
            filter_text = ", ".join([f.replace('status:', '').replace('temporal:', '') for f in filters_applied])
            answer_parts.append(f"🔍 **Filters Applied:** {filter_text} ({filter_intention})")
        
        # Add filter explanation if provided (critical for "open calls" with 0 results)
        filter_explanation = metadata.get('filter_explanation', '')
        if filter_explanation:
            answer_parts.append(f"ℹ️ **Filter Result:** {filter_explanation}")
            
        answer_parts.append("")
        
        # Process each result
        for i, result in enumerate(results[:5], 1):  # Limit to top 5
            answer_parts.append(f"**{i}. {result.title}**")
            
            if result.identifier != 'N/A':
                answer_parts.append(f"📋 **Call ID:** {result.identifier}")
            
            if result.status != 'Unknown':
                status_emoji = "🟢" if result.status == "Open" else "🔵" if result.status == "Forthcoming" else "🔴"
                answer_parts.append(f"{status_emoji} **Status:** {result.status}")
            
            if result.deadline != 'Not specified':
                answer_parts.append(f"⏰ **Deadline:** {result.deadline}")
            
            if result.framework_programme != 'Horizon Europe':
                answer_parts.append(f"🏛️ **Programme:** {result.framework_programme}")
            
            if result.call_identifier != 'Not specified':
                answer_parts.append(f"📞 **Call:** {result.call_identifier}")
            
            # Add enhanced description
            if result.description and result.description != 'No description available':
                # For enhanced descriptions, show more content but still limit for readability
                if len(result.description) > 400:
                    desc_preview = result.description[:400] + '...'
                else:
                    desc_preview = result.description
                answer_parts.append(f"\n**Description:** {desc_preview}")
            else:
                # Fallback description if none available
                action_type = "Research opportunity"
                if hasattr(result, 'metadata') and result.metadata:
                    types_action = result.metadata.get('typesOfAction', [''])[0] if isinstance(result.metadata.get('typesOfAction'), list) else result.metadata.get('typesOfAction', '')
                    if types_action:
                        if types_action == 'RIA':
                            action_type = "Research and Innovation Action"
                        elif types_action == 'CSA':
                            action_type = "Coordination and Support Action"
                        elif types_action == 'IA':
                            action_type = "Innovation Action"
                        else:
                            action_type = f"{types_action} opportunity"
                answer_parts.append(f"\n**Description:** {action_type} in the specified research area")
            
            # Add link
            answer_parts.append(f"\n🔗 **Apply Here:** {result.url}")
            answer_parts.append("\n")
        
        # Add facet analysis if available
        if facets:
            answer_parts.append("---")
            answer_parts.append("📊 **FACET ANALYSIS:**\n")
            
            # Show top program areas
            if 'programmeDivision' in facets:
                divisions = facets['programmeDivision'].get('values', [])[:3]
                if divisions:
                    div_text = ", ".join([f"{d['value']} ({d['count']})" for d in divisions])
                    answer_parts.append(f"🎯 **Top Program Areas:** {div_text}\n")
            
            # Show status distribution
            if 'status' in facets:
                status_dist = facets['status'].get('values', [])
                if status_dist:
                    status_text = ", ".join([f"{s['value']} ({s['count']})" for s in status_dist])
                    answer_parts.append(f"📈 **Status Distribution:** {status_text}")
            
            answer_parts.append("")
        
        # Add simple footer
        answer_parts.extend([
            "---",
            "🔗 **EU Funding Portal:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"
        ])
        
        return {
            'answer': '\n'.join(answer_parts),
            'intent': 'ENHANCED_CALL_SEARCH',
            'call_identifier': None,
            'sources': [{'title': r.title, 'url': r.url, 'status': r.status} for r in results],
            'search_type': 'enhanced_hybrid',
            'chunks_used': len(results),
            'confidence': max(0.8, min([r.score for r in results]) / max([r.score for r in results]) if results else 0.8),
            'data_source': 'EU Funding & Tenders Portal (Enhanced)',
            'facets': facets,
            'search_metadata': metadata,
            'processing_time': metadata.get('processing_time', 0),
            'success': True
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            'answer': f"I apologize, but I encountered an error while processing your call-specific query: {error_message}",
            'intent': 'ERROR',
            'call_identifier': None,
            'sources': [],
            'confidence': 0.0,
            'data_source': 'Error',
            'success': False,
            'error': error_message
        }
    
    def _create_no_call_results_response(
        self,
        question: str,
        call_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create response when no call-specific results are found."""
        if call_identifier:
            message = f"I couldn't find specific documentation for call/topic '{call_identifier}' in the available Horizon Europe documents."
        else:
            message = f"I couldn't find specific information about '{question}' in the Horizon Europe call documentation."
        
        message += "\n\nThis could mean:\n"
        message += "• The call/topic identifier might be incorrect or formatted differently\n"
        message += "• The documentation for this specific call might not be available yet\n"
        message += "• The call might be from a different funding programme\n\n"
        message += "💡 **Suggestions:**\n"
    
    def _create_filtered_no_results_response(
        self,
        question: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create specialized response when specific filters return no results."""
        
        filter_intention = metadata.get('filter_intention', 'all')
        filter_explanation = metadata.get('filter_explanation', '')
        clean_query = metadata.get('clean_query', question)
        
        message_parts = []
        
        if filter_intention == "open_only":
            message_parts.extend([
                f"🔴 **No Currently Open Calls Found** for '{clean_query}'",
                "",
                filter_explanation,
                "",
                "**This is normal** - EU funding calls follow scheduled cycles and aren't always open.",
                "",
                "💡 **What to do:**",
                "• Check **recent closed calls** to see what types of calls are typically available",
                "• Set up **EU call alerts** to be notified when new calls open",
                "• Look for **forthcoming calls** that will open soon",
                "",
                f"🔍 **Alternative search:** Try removing 'open' to see all quantum mechanics calls"
            ])
            
        elif filter_intention == "recent_only":
            message_parts.extend([
                f"📅 **No Recent Calls Found** for '{clean_query}'",
                "",
                filter_explanation,
                "",
                "This may indicate a gap between call cycles for this specific topic.",
                "",
                "💡 **What to do:**",
                "• Expand your search to include older calls to see patterns",
                "• Check the **EU call calendar** for upcoming opportunities",
                "• Consider related or broader search terms"
            ])
            
        else:
            message_parts.extend([
                f"🔍 **No Results Found** for your filtered search: '{question}'",
                "",
                filter_explanation if filter_explanation else "The specific filters you requested returned no matching calls."
            ])
        
        # Add general guidance
        message_parts.extend([
            "",
            "🔗 **Useful Resources:**",
            "• EU Funding Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            "• Call Calendar: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-calendar",
            "• Set Alerts: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/mailing-lists"
        ])
        
        return {
            'answer': '\n'.join(message_parts),
            'intent': 'FILTERED_NO_RESULTS', 
            'call_identifier': None,
            'sources': [],
            'confidence': 0.9,  # High confidence in the filtering explanation
            'data_source': 'EU Funding & Tenders Portal (Enhanced)',
            'search_metadata': metadata,
            'success': True,  # Success in explaining why no results
            'filter_applied': True
        }
        message += "• Verify the call identifier on the EU Funding Portal\n"
        message += "• Try searching with broader terms or cluster names\n"
        message += "• Check the relevant Work Programme for your research area\n"
        message += "• Visit: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"
        
        return {
            'answer': message,
            'intent': 'NO_CALL_RESULTS',
            'call_identifier': call_identifier,
            'sources': [],
            'confidence': 0.0,
            'data_source': 'No call documentation found',
            'success': False
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize the call-specific RAG system
    call_rag = CallSpecificRAG()
    
    # Test queries
    test_queries = [
        "What are the requirements for HORIZON-CL4-2024-DATA-01-01?",
        "Tell me about health cluster calls for 2024",
        "What is the deadline for EIC Accelerator grants?",
        "HORIZON-CL5-2024-CLIMATE-01 eligibility criteria",
        "Digital transformation topics in Horizon Europe"
    ]
    
    print("🧪 Testing Call-Specific RAG System...")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n📋 Query: '{query}'")
        
        # Detect intent
        intent_type, call_id, confidence = call_rag.detect_call_specific_intent(query)
        print(f"🎯 Intent: {intent_type}, Call ID: {call_id}, Confidence: {confidence:.2f}")
        
        # Handle query
        result = call_rag.handle_call_specific_query(query, call_id)
        
        if result['success']:
            print(f"✅ Success: {result['chunks_used']} chunks used")
            print(f"📊 Confidence: {result['confidence']:.2f}")
            print(f"📝 Answer preview: {result['answer'][:200]}...")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    print("\n🎉 Call-specific RAG testing completed!")
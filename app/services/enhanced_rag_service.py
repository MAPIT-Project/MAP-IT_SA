"""
Enhanced RAG service that integrates vector search with existing CORDIS search.
Includes consolidated call-specific functionality to eliminate redundancy.
"""

from typing import List, Dict, Any, Optional, Tuple
import json
import logging
import re
from datetime import datetime
from dataclasses import asdict

from .vector_search_service import VectorSearchService, SearchResult
from .rag_service import CordisRAG
from .embedding_service import EmbeddingService
from .supabase_client import SupabaseVectorStore
from .enhanced_call_search import EnhancedCallSearchService, EnhancedSearchResult
from ..core.config import settings

logger = logging.getLogger(__name__)

class HorizonEuropeRAG:
    """Enhanced RAG system integrating vector search with existing CORDIS search.
    Includes consolidated call-specific functionality."""
    
    def __init__(
        self,
        vector_search_service: Optional[VectorSearchService] = None,
        existing_cordis_rag: Optional[CordisRAG] = None,
        embedding_service: Optional[EmbeddingService] = None,
        supabase_client: Optional[SupabaseVectorStore] = None
    ):
        """Initialize the enhanced RAG system."""
        
        # Initialize services
        self.supabase = supabase_client or SupabaseVectorStore()
        
        # Only initialize embedding service if vector search is enabled and API key is available
        if settings.vector_search_enabled and settings.google_embedding_api_key:
            self.embedder = embedding_service or EmbeddingService(cache_client=self.supabase)
            self.vector_search = vector_search_service or VectorSearchService(self.supabase, self.embedder)
        else:
            logger.info("ℹ️ Vector search disabled - using keyword search only")
            self.embedder = None
            self.vector_search = None
        
        # Initialize existing CORDIS RAG
        if existing_cordis_rag:
            self.cordis_rag = existing_cordis_rag
        else:
            # Create with default settings
            self.cordis_rag = CordisRAG(
                ai_provider=settings.default_ai_provider,
                openai_model_name=settings.openai_model,
                gemini_model_name=settings.gemini_model,
                use_local_db=settings.use_local_db,
                database_url=settings.database_url
            )
        
        # Initialize enhanced call search service
        try:
            self.enhanced_search = EnhancedCallSearchService()
            logger.info("✅ Enhanced call search service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Enhanced call search not available: {e}")
            self.enhanced_search = None
        
        logger.info("✅ Enhanced Horizon Europe RAG system initialized with consolidated call functionality")

    def _rule_based_intent_fallback(self, question: str) -> Tuple[str, float]:
        """
        Final fallback intent detection using simple rule-based logic.
        Used when both primary and secondary IntentService calls fail.
        """
        question_lower = question.lower()

        # Memory query patterns
        memory_patterns = [
            'first message', 'earlier', 'before', 'previous', 'remind me',
            'recall', 'history', 'conversation', 'what did i say', 'what was my'
        ]
        if any(pattern in question_lower for pattern in memory_patterns):
            return ("conversational", 0.7)

        # Call/funding patterns
        call_patterns = [
            'open calls', 'calls for', 'funding opportunities', 'grant opportunities',
            'available calls', 'current calls', 'calls about', 'calls related to',
            'what calls', 'which calls', 'show me calls', 'find calls', 'deadline',
            'topic', 'tenders', 'funding & tenders', 'funding and tenders'
        ]
        if any(pattern in question_lower for pattern in call_patterns) or ("open" in question_lower and "call" in question_lower):
            return ("SEARCH_CALLS", 0.8)

        # Project patterns
        project_patterns = ['project', 'projects', 'acronym', 'rcn', 'case study']
        if any(pattern in question_lower for pattern in project_patterns):
            return ("SEARCH_PROJECTS", 0.8)

        # Procedural patterns
        procedural_patterns = [
            'how to', 'how do i', 'how can i', 'where can i find', 'where to find',
            'eligibility', 'application process', 'documents required', 'supporting documents',
            'ethics', 'guidelines', 'register on the portal', 'how to apply'
        ]
        if any(pattern in question_lower for pattern in procedural_patterns):
            return ("FAQ", 0.8)

        # Default to conversational for general questions
        return ("conversational", 0.6)
    
    def answer_question(
        self,
        question: str,
        max_context_chunks: int = 5,
        include_projects: bool = True,
        include_documents: bool = True,
        search_type: str = "hybrid",
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Main entry point for answering questions about Horizon Europe."""
        
        logger.info(f"🎯 Processing question: '{question}'")
        
        # Determine intent using centralized intent service with better call detection
        try:
            from .intent_service import IntentService
            intent, confidence = IntentService.determine_intent(question)

            # Override intent for call-related queries that are being misclassified
            question_lower = question.lower()
            call_indicators = [
                'open calls', 'calls for', 'funding opportunities', 'grant opportunities',
                'available calls', 'current calls', 'calls about', 'calls related to',
                'what calls', 'which calls', 'show me calls', 'find calls'
            ]

            # If question contains call indicators, force SEARCH_CALLS
            if any(indicator in question_lower for indicator in call_indicators):
                intent = "SEARCH_CALLS"
                confidence = 0.95
                logger.info(f"🎯 Override: Detected call query, forcing SEARCH_CALLS intent")

        except Exception as e:
            logger.warning(f"IntentService failed, using fallback: {e}")
            # Use IntentService static method as fallback instead of deprecated CordisRAG method
            try:
                from .intent_service import IntentService
                intent, confidence = IntentService.determine_intent(question)
                logger.info(f"✅ Fallback intent detection successful: {intent} (confidence: {confidence:.2f})")
            except Exception as fallback_error:
                logger.error(f"❌ Both primary and fallback intent detection failed: {fallback_error}")
                # Final fallback - use rule-based detection
                intent, confidence = self._rule_based_intent_fallback(question)
        
        logger.info(f"🧠 Intent determined: {intent} (confidence: {confidence:.2f})")
        
        # Route to appropriate handler based on intent and user preferences
        # NOTE: Intent labels must match those returned by CordisRAG.determine_user_intent
        if intent == "SEARCH_PROJECTS" and include_projects:
            return self.handle_project_query(question)
        elif intent == "SEARCH_CALLS":
            return self.handle_call_query(question)
        elif intent in ["GENERAL_INFO", "GENERAL_QUERY", "FAQ"]:
            if include_documents:
                logger.info(f"📚 Routing GENERAL_QUERY to vector search pipeline")
                return self.handle_general_query(question, max_context_chunks, search_type, similarity_threshold)
            elif include_projects:
                # Fallback to project search if no documents requested
                logger.info(f"📚 Routing GENERAL_QUERY to project search (no documents enabled)")
                return self.handle_project_query(question)
            else:
                return self._create_error_response("No search sources enabled")
        else:
            # Combined search for complex queries
            logger.info(f"🔀 Routing to combined search pipeline")
            return self.handle_combined_query(
                question,
                max_context_chunks,
                include_projects,
                include_documents,
                search_type,
                similarity_threshold
            )
    
    def handle_general_query(
        self,
        question: str,
        max_context_chunks: int,
        search_type: str,
        similarity_threshold: float
    ) -> Dict[str, Any]:
        """Handle general information queries using vector search."""
        
        logger.info(f"📚 Handling general query with vector search")
        
        # Capability questions should be answered directly
        try:
            if hasattr(self.cordis_rag, "_is_capability_question") and self.cordis_rag._is_capability_question(question):
                answer = self.cordis_rag._generate_capabilities_answer()
                return {
                    'answer': answer,
                    'intent': 'FAQ',
                    'sources': [],
                    'search_type': search_type,
                    'chunks_used': 0,
                    'confidence': 1.0,
                    'data_source': 'System Capabilities',
                    'processing_time': 0,
                    'success': True
                }
        except Exception:
            pass

        try:
            # Check if vector search is available
            if not self.vector_search:
                logger.warning("Vector search not available - using fallback to CORDIS RAG")
                # Use CORDIS RAG as fallback for document search
                return self.cordis_rag.get_ai_response_with_routing(question)
            
            # Search for relevant document chunks
            search_results = self.vector_search.search(
                query=question,
                search_type=search_type,
                num_results=max_context_chunks * 2,  # Get more for filtering
                similarity_threshold=similarity_threshold,
                rerank=True
            )
            
            if not search_results:
                return self._create_no_results_response(question, "documents")
            
            # Select best chunks for context
            context_chunks = self._select_context_chunks(search_results, max_context_chunks)
            
            # Build context for LLM
            context = self._build_context_from_chunks(context_chunks)
            
            # Generate answer using existing LLM infrastructure
            answer = self._generate_answer_with_context(question, context, context_chunks)
            
            return {
                'answer': answer,
                'intent': 'GENERAL_INFO',
                'sources': self._format_chunk_sources(context_chunks),
                'search_type': search_type,
                'chunks_used': len(context_chunks),
                'confidence': self._calculate_confidence(search_results),
                'data_source': 'Horizon Europe Documents',
                'processing_time': 0,  # Will be calculated by caller
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ General query handling failed: {e}")
            return self._create_error_response(str(e))
    
    def handle_project_query(self, question: str) -> Dict[str, Any]:
        """Handle project-specific queries using existing CORDIS RAG."""
        
        logger.info(f"🔬 Handling project query with CORDIS search")
        
        try:
            # Use existing CORDIS RAG system
            result = self.cordis_rag.get_ai_response_with_routing(
                question=question,
                max_projects_to_process=5
            )
            
            # Enhance with document context if relevant
            doc_context = self._get_supporting_documentation(question, max_chunks=2)
            
            if doc_context:
                result['supporting_docs'] = doc_context
                # Optionally enhance the answer with document context
                if len(doc_context) > 0:
                    enhanced_answer = self._enhance_answer_with_docs(
                        result.get('answer', ''), 
                        doc_context
                    )
                    result['answer'] = enhanced_answer
            
            # Ensure consistent response format
            if not isinstance(result, dict):
                result = {'answer': str(result), 'success': True}
            
            result['data_source'] = result.get('data_source', 'CORDIS Projects')
            result['intent'] = 'PROJECT_SEARCH'
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Project query handling failed: {e}")
            return self._create_error_response(str(e))
    
    def handle_call_query(self, question: str) -> Dict[str, Any]:
        """Handle call/funding opportunity queries with integrated call-specific functionality."""
        
        logger.info(f"📞 Handling call query with integrated call functionality")
        
        try:
            # First, detect if this is a call-specific query that should use comprehensive docs
            intent_type, call_identifier, confidence = self.detect_call_specific_intent(question)
            
            # Use call documentation ONLY for specific call/topic IDs; cluster-specific queries go to enhanced search
            if intent_type in ["SPECIFIC_CALL", "SPECIFIC_TOPIC"]:
                logger.info(f"🎯 Using comprehensive call documentation for: {intent_type}")
                
                # Use integrated call-specific handling
                result = self.handle_call_specific_query(
                    question=question,
                    call_identifier=call_identifier,
                    max_context_chunks=8,
                    search_type="hybrid"
                )
                
                # Ensure consistent response format
                result['intent'] = 'SEARCH_CALLS_ENHANCED'
                result['data_source'] = result.get('data_source', 'Horizon Europe Comprehensive Call Docs')
                
                return result
            else:
                # Use enhanced search for general call queries (GENERAL_CALL intent)
                logger.info(f"📞 Using enhanced search for general call query")
                
                # Use enhanced search service for better results
                if self.enhanced_search:
                    logger.info(f"🚀 Using enhanced call search service for general query")
                    enhanced_result = self.enhanced_search.search_calls_enhanced(
                        query=question,
                        max_results=10,
                        include_closed=False,  # Only open/forthcoming for general queries
                        enable_facet_analysis=True
                    )
                    
                    if enhanced_result['status'] == 'success':
                        result = self._process_enhanced_search_results(question, enhanced_result)
                        # Enforce open-only if user asked for open calls
                        if 'open' in question.lower() and result.get('intent') in ('ENHANCED_CALL_SEARCH', 'SEARCH_CALLS'):
                            sources = enhanced_result.get('results', [])
                            def _deadline_in_future_result(r) -> bool:
                                # Prefer raw ISO from metadata if available
                                meta = getattr(r, 'metadata', {}) or {}
                                raw = None
                                try:
                                    raw = meta.get('deadlineDate')
                                    if isinstance(raw, list) and raw:
                                        raw = raw[0]
                                except Exception:
                                    raw = None
                                # Fallback to r.deadline if no raw
                                if not raw:
                                    deadline_str = getattr(r, 'deadline', '') or ''
                                    # Strip any annotations like emojis or parentheses
                                    for marker in [' ❌', ' ⚠️', ' ⏰']:
                                        if marker in deadline_str:
                                            deadline_str = deadline_str.split(marker)[0].strip()
                                    # Try parse long month format
                                    try:
                                        dt = datetime.strptime(deadline_str, '%B %d, %Y')
                                        return dt >= datetime.now()
                                    except Exception:
                                        return True
                                # Parse ISO-like
                                try:
                                    ds = str(raw).split('T')[0]
                                    dt = datetime.strptime(ds, '%Y-%m-%d')
                                    return dt >= datetime.now()
                                except Exception:
                                    return True
                            open_only = [
                                r for r in sources
                                if getattr(r, 'status', '').lower() == 'open' and _deadline_in_future_result(r)
                            ]
                            if open_only:
                                filtered = {
                                    'results': open_only,
                                    'facets': enhanced_result.get('facets', {}),
                                    'search_metadata': enhanced_result.get('search_metadata', {}) | {'filters_applied': ['open_only_enforced']},
                                    'status': 'success'
                                }
                                result = self._process_enhanced_search_results(question, filtered)
                            else:
                                # Return a clear open-only no-results response with verification URL
                                result = self._create_filtered_no_results_response(question, enhanced_result.get('search_metadata', {}) | {
                                    'filter_explanation': 'No currently open calls found for your query after enforcing open-only filter',
                                    'filter_intention': 'open_only',
                                    'clean_query': enhanced_result.get('search_metadata', {}).get('clean_query', question)
                                })
                        # Fallback: if enhanced returned zero results, try advanced portal JSON query with cluster token injection
                        if not enhanced_result.get('results'):
                            logger.info("⚠️ Enhanced search returned 0 results, trying advanced portal JSON query fallback")
                            try:
                                from .rag_service import CordisRAG
                                portal = CordisRAG()
                                # Inject identifier token if cluster is mentioned
                                import re
                                m = re.search(r"cluster\s*(\d)", question, re.IGNORECASE)
                                # Build a clean, tokenized query for the portal text field
                                q2 = question
                                cluster_map = {
                                    '1': 'Health',
                                    '2': 'Culture, Creativity and Inclusive Society',
                                    '3': 'Civil Security for Society',
                                    '4': 'Digital, Industry and Space',
                                    '5': 'Climate, Energy and Mobility',
                                    '6': 'Food, Bioeconomy, Natural Resources, Agriculture and Environment',
                                }
                                if m:
                                    cnum = m.group(1)
                                    clabel = cluster_map.get(cnum, '')
                                    # Use cluster token with wildcard for recall; drop label to avoid over-filtering
                                    q2 = f"HORIZON-CL{cnum}*"
                                # First attempt: advanced query (open only)
                                calls_found = portal._search_with_advanced_json_query(
                                    api_url="https://api.tech.ec.europa.eu/search-api/prod/rest/search",
                                    search_text=q2,
                                    max_results=10
                                )
                                # Second attempt: basic params (keep OPEN ONLY for 'open' queries)
                                if not calls_found:
                                    calls_found = portal._search_with_basic_params(
                                        api_url="https://api.tech.ec.europa.eu/search-api/prod/rest/search",
                                        search_text=q2 + " status:31094502",
                                        max_results=10
                                    )
                                # If we found calls, convert to enhanced-style results for consistent formatting
                                if calls_found:
                                    # Import URL builder and result container
                                    from .enhanced_call_search import EnhancedSearchResult, EnhancedCallSearchService
                                    url_builder = EnhancedCallSearchService()

                                    def _normalize_status(raw_status: str) -> str:
                                        # CORRECTED status mapping to match EU API
                                        mapping = {
                                            '31094501': 'Closed',      # Closed calls
                                            '31094502': 'Open',        # Open for submission
                                            '31094503': 'Forthcoming', # Forthcoming calls
                                            'open': 'Open',
                                            'closed': 'Closed',
                                            'forthcoming': 'Forthcoming'
                                        }
                                        if raw_status is None:
                                            return 'Unknown'
                                        s = str(raw_status).strip()
                                        return mapping.get(s, mapping.get(s.lower(), 'Unknown'))

                                    def _parse_deadline(deadline_str: str):
                                        if not deadline_str or deadline_str == 'Not specified':
                                            return None
                                        try:
                                            # Handle ISO-like formats first
                                            ds = deadline_str.split('T')[0]
                                            return datetime.strptime(ds, '%Y-%m-%d')
                                        except Exception:
                                            try:
                                                # Try long month format (e.g., March 15, 2026)
                                                return datetime.strptime(deadline_str, '%B %d, %Y')
                                            except Exception:
                                                return None

                                    is_open_query = 'open' in question.lower()
                                    enhanced_results = []
                                    for c in calls_found:
                                        identifier = c.get('identifier', 'N/A')
                                        raw_url = c.get('url')
                                        built_url = url_builder._build_call_url(identifier=identifier, raw_url=raw_url)
                                        raw_deadline = c.get('deadline', 'Not specified')
                                        deadline_dt = _parse_deadline(raw_deadline)
                                        status_norm = _normalize_status(c.get('status', 'Unknown'))

                                        # Status correction by deadline: if deadline passed, mark Closed
                                        try:
                                            if deadline_dt and deadline_dt < datetime.now():
                                                status_norm = 'Closed'
                                        except Exception:
                                            pass

                                        # Enforce open-only for queries asking for open calls
                                        if is_open_query and status_norm != 'Open':
                                            continue

                                        enhanced_results.append(EnhancedSearchResult(
                                            identifier=identifier,
                                            title=c.get('title', 'Unknown Call'),
                                            description=c.get('description', 'No description available'),
                                            status=status_norm,
                                            status_code='unknown',
                                            deadline=raw_deadline,
                                            programme_period=c.get('programme_period', '2021 - 2027'),
                                            framework_programme=c.get('frameworkProgramme', 'Horizon Europe'),
                                            call_identifier=c.get('call_identifier', 'Not specified'),
                                            url=built_url,
                                            score=0.5,
                                            metadata={}
                                        ))

                                    # If enforcing open-only left nothing, return explicit filtered message
                                    if is_open_query and not enhanced_results:
                                        result = self._create_filtered_no_results_response(question, {
                                            'filter_explanation': 'No currently open calls found for your query after enforcing open-only filter',
                                            'filter_intention': 'open_only',
                                            'clean_query': q2
                                        })
                                    else:
                                        processed = self._process_enhanced_search_results(question, {
                                            'results': enhanced_results,
                                            'facets': {},
                                            'search_metadata': {
                                                'query': question,
                                                'clean_query': q2,
                                                'total_found': len(calls_found),
                                                'returned': len(enhanced_results),
                                                'processing_time': 0,
                                                'semantic_tags_used': 0,
                                                'facet_categories': 0,
                                                'search_enhanced': True,
                                                'filters_applied': ['fallback_portal'] + (['open_only_enforced'] if is_open_query else []),
                                                'filter_intention': 'open_only' if is_open_query else 'all'
                                            },
                                            'status': 'success'
                                        })
                                        processed['data_source'] = 'EU Funding & Tenders Portal (Enhanced Fallback)'
                                        result = processed
                            except Exception as fe:
                                logger.warning(f"Fallback advanced portal query failed: {fe}")
                    else:
                        logger.warning("⚠️ Enhanced search failed, falling back to CORDIS")
                        result = self.cordis_rag.search_for_calls(question, max_results=10)
                else:
                    logger.warning("⚠️ Enhanced search not available, falling back to CORDIS")
                    result = self.cordis_rag.search_for_calls(question, max_results=10)
                
                # Enhance with programme documentation from comprehensive docs
                doc_context = self._get_supporting_documentation(
                    question,
                    max_chunks=3,
                    doc_types=['work_programme', 'call_text', 'programme_guide']
                )
                
                if doc_context:
                    result['supporting_docs'] = doc_context
                    # Enhance the answer with document context
                    if result.get('answer') and len(doc_context) > 0:
                        enhanced_answer = self._enhance_answer_with_docs(
                            result['answer'],
                            doc_context
                        )
                        result['answer'] = enhanced_answer
                
                # Ensure consistent response format
                result['intent'] = 'SEARCH_CALLS'
                result['data_source'] = result.get('data_source', 'CORDIS Calls')
                
                return result
            
        except Exception as e:
            logger.error(f"❌ Call query handling failed: {e}")
            return self._create_error_response(str(e))
    
    def handle_combined_query(
        self,
        question: str,
        max_context_chunks: int,
        include_projects: bool,
        include_documents: bool,
        search_type: str,
        similarity_threshold: float
    ) -> Dict[str, Any]:
        """Handle queries requiring both project and document information."""
        
        logger.info(f"🔀 Handling combined query")
        
        try:
            results = {
                'question': question,
                'intent': 'COMBINED',
                'components': [],
                'success': True
            }
            
            # Get document context
            if include_documents:
                doc_results = self.vector_search.search(
                    query=question,
                    search_type=search_type,
                    num_results=max_context_chunks,
                    similarity_threshold=similarity_threshold
                )
                
                if doc_results:
                    results['components'].append({
                        'type': 'documents',
                        'results': doc_results,
                        'count': len(doc_results)
                    })
            
            # Get project information
            if include_projects:
                # Try to determine if it's a project or call query
                try:
                    from .intent_service import IntentService
                    intent, _ = IntentService.determine_intent(question)
                except Exception as e:
                    logger.warning(f"IntentService failed in combined query, using fallback: {e}")
                    # Use IntentService static method as fallback instead of deprecated CordisRAG method
                    try:
                        from .intent_service import IntentService
                        intent, _ = IntentService.determine_intent(question)
                        logger.info(f"✅ Fallback intent detection successful in combined query: {intent}")
                    except Exception as fallback_error:
                        logger.error(f"❌ Both primary and fallback intent detection failed in combined query: {fallback_error}")
                        # Final fallback - use rule-based detection
                        intent, _ = self._rule_based_intent_fallback(question)
                
                if intent == "SEARCH_CALLS":
                    project_results = self.cordis_rag.search_for_calls(
                        question=question,
                        max_results=5
                    )
                else:
                    project_results = self.cordis_rag.get_ai_response_with_routing(
                        question=question,
                        max_projects_to_process=3
                    )
                
                if project_results:
                    results['components'].append({
                        'type': 'projects',
                        'results': project_results,
                        'intent': intent
                    })
            
            # Generate combined answer
            if results['components']:
                combined_context = self._merge_contexts(results['components'])
                answer = self._generate_answer_with_context(question, combined_context, [])
                results['answer'] = answer
                results['confidence'] = self._calculate_combined_confidence(results['components'])
                results['data_source'] = 'Combined (Documents + Projects)'
            else:
                return self._create_no_results_response(question, "combined")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Combined query handling failed: {e}")
            return self._create_error_response(str(e))
    
    def _select_context_chunks(
        self,
        search_results: List[SearchResult],
        max_chunks: int
    ) -> List[SearchResult]:
        """Select the best chunks for context window."""
        
        if len(search_results) <= max_chunks:
            return search_results
        
        # Remove duplicate content
        seen_content = set()
        unique_results = []
        
        for result in search_results:
            content_hash = hash(result.content[:200])  # Hash first 200 chars
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        # Diversify by document
        documents_used = {}
        selected = []
        
        for result in unique_results:
            doc_id = result.document_id
            
            # Limit chunks per document (max 2 chunks per document)
            if doc_id in documents_used:
                if documents_used[doc_id] >= 2:
                    continue
                documents_used[doc_id] += 1
            else:
                documents_used[doc_id] = 1
            
            selected.append(result)
            
            if len(selected) >= max_chunks:
                break
        
        logger.info(f"📋 Selected {len(selected)} chunks from {len(unique_results)} unique results")
        return selected
    
    def _build_context_from_chunks(self, chunks: List[SearchResult]) -> str:
        """Build context string from search result chunks."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            context_part = f"[Source {i}: {chunk.document_title}]"
            
            if chunk.document_type and chunk.document_type != 'unknown':
                context_part += f"\nDocument Type: {chunk.document_type}"
            
            if chunk.section_title:
                context_part += f"\nSection: {chunk.section_title}"
            
            if chunk.page_number:
                context_part += f"\nPage: {chunk.page_number}"
            
            context_part += f"\nContent: {chunk.content}\n"
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)
    
    def _generate_answer_with_context(
        self,
        question: str,
        context: str,
        chunks: List[SearchResult]
    ) -> str:
        """Generate answer using LLM with context."""
        
        prompt = f"""You are an expert on Horizon Europe, the EU's research and innovation funding programme.

Based on the following context from official Horizon Europe documentation, answer the user's question accurately and comprehensively.

Context:
{context}

Question: {question}

Instructions:
- Provide a clear, well-structured answer based on the provided context
- Reference specific documents when possible (e.g., "According to the Work Programme...")
- Include relevant details like deadlines, requirements, procedures, or eligibility criteria
- If the context doesn't contain enough information to fully answer the question, acknowledge this
- Be precise about any specific requirements, evaluation processes, or application procedures
- Use a professional but accessible tone
- Structure your answer with clear paragraphs or bullet points when appropriate

Answer:"""
        
        # Use the existing LLM service from CORDIS RAG
        try:
            answer = self.cordis_rag._call_llm_for_generation(
                role="Horizon Europe Expert Assistant",
                prompt=prompt
            )
            
            logger.info(f"✅ Generated answer with context ({len(context)} chars)")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Answer generation failed: {e}")
            return f"I apologize, but I encountered an error while generating the response: {str(e)}"
    
    def _get_supporting_documentation(
        self,
        question: str,
        max_chunks: int = 3,
        doc_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get supporting documentation for a query."""
        
        try:
            filters = {}
            if doc_types:
                if len(doc_types) == 1:
                    filters['document_type'] = doc_types[0]
                else:
                    # Use OR filter for multiple document types
                    filters['document_type'] = doc_types
            
            results = self.vector_search.search(
                query=question,
                search_type="semantic",
                num_results=max_chunks,
                filters=filters,
                similarity_threshold=0.6  # Lower threshold for supporting docs
            )
            
            supporting_docs = []
            for result in results:
                supporting_docs.append({
                    'title': result.document_title,
                    'type': result.document_type,
                    'excerpt': result.content[:300] + '...' if len(result.content) > 300 else result.content,
                    'relevance': result.score,
                    'section': result.section_title,
                    'page': result.page_number
                })
            
            logger.info(f"📖 Found {len(supporting_docs)} supporting documents")
            return supporting_docs
            
        except Exception as e:
            logger.error(f"❌ Error getting supporting documentation: {e}")
            return []
    
    def _enhance_answer_with_docs(self, original_answer: str, doc_context: List[Dict[str, Any]]) -> str:
        """Enhance an existing answer with document context."""
        
        if not doc_context or not original_answer:
            return original_answer
        
        # Add supporting documentation section
        enhancement = "\n\n**Additional Context from Horizon Europe Documentation:**\n"
        
        for i, doc in enumerate(doc_context[:2], 1):  # Limit to 2 docs
            enhancement += f"\n{i}. **{doc['title']}** ({doc['type']})\n"
            enhancement += f"   {doc['excerpt']}\n"
        
        return original_answer + enhancement
    
    def _format_chunk_sources(self, chunks: List[SearchResult]) -> List[Dict[str, str]]:
        """Format source citations from chunks."""
        sources = []
        seen_docs = set()
        
        for chunk in chunks:
            doc_id = chunk.document_id
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                source = {
                    'title': chunk.document_title,
                    'type': chunk.document_type,
                    'id': doc_id
                }
                
                if chunk.section_title:
                    source['section'] = chunk.section_title
                if chunk.page_number:
                    source['page'] = chunk.page_number
                
                sources.append(source)
        
        return sources
    
    def _calculate_confidence(self, search_results: List[SearchResult]) -> float:
        """Calculate confidence score for the answer."""
        if not search_results:
            return 0.0
        
        # Average of top 3 scores
        top_scores = [r.score for r in search_results[:3]]
        avg_score = sum(top_scores) / len(top_scores)
        
        # Normalize to 0-1 range and apply some adjustments
        confidence = min(1.0, avg_score)
        
        # Boost confidence if we have multiple high-scoring results
        if len([s for s in top_scores if s > 0.8]) >= 2:
            confidence = min(1.0, confidence * 1.1)
        
        return confidence
    
    def _calculate_combined_confidence(self, components: List[Dict[str, Any]]) -> float:
        """Calculate confidence for combined results."""
        confidences = []
        
        for component in components:
            if component['type'] == 'documents':
                results = component.get('results', [])
                if results:
                    scores = [r.score for r in results[:3]]
                    if scores:
                        confidences.append(sum(scores) / len(scores))
            elif component['type'] == 'projects':
                # Use existing confidence from CORDIS RAG if available
                project_result = component.get('results', {})
                if isinstance(project_result, dict) and 'confidence' in project_result:
                    confidences.append(project_result['confidence'])
                else:
                    confidences.append(0.7)  # Default confidence for project results
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _merge_contexts(self, components: List[Dict[str, Any]]) -> str:
        """Merge different context types into a single context."""
        merged = []
        
        for component in components:
            if component['type'] == 'documents':
                results = component.get('results', [])
                if results:
                    doc_context = self._build_context_from_chunks(results[:3])
                    merged.append(f"=== Document Context ===\n{doc_context}")
            elif component['type'] == 'projects':
                project_result = component.get('results', {})
                if isinstance(project_result, dict) and 'answer' in project_result:
                    project_context = project_result['answer'][:1000]  # Limit length
                    merged.append(f"=== Project Information ===\n{project_context}")
        
        return "\n\n".join(merged)
    
    def _create_no_results_response(self, question: str, search_type: str) -> Dict[str, Any]:
        """Create a response when no results are found."""
        return {
            'answer': f"I couldn't find specific information to answer your question about '{question}' in the available {search_type}. You might try rephrasing your question or checking the EU Funding & Tenders Portal directly at https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            'intent': 'NO_RESULTS',
            'sources': [],
            'confidence': 0.0,
            'data_source': f'No {search_type} found',
            'success': False
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create an error response."""
        return {
            'answer': f"I apologize, but I encountered an error while processing your request: {error_message}",
            'intent': 'ERROR',
            'sources': [],
            'confidence': 0.0,
            'success': False,
            'error': error_message
        }
    
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
        # Now covering all 6 Horizon Europe clusters plus EIC and ERC
        cluster_keywords = {
            # Cluster 1: Health
            "health": ["health cluster", "medical research", "biomedical", "pharmaceutical", "disease funding", "healthcare innovation", "biotech research", "biotechnology", "genomics", "personalized medicine", "clinical trials", "health data", "medical devices", "telemedicine"],
            # Cluster 2: Culture, Creativity and Inclusive Society
            "culture": ["culture cluster", "creativity funding", "inclusive society", "arts programme", "cultural heritage", "creative industries", "social sciences", "humanities research", "social innovation", "democracy", "cultural diversity", "social inclusion", "urban development", "education research"],
            # Cluster 3: Civil Security for Society
            "security": ["civil security", "security research", "safety funding", "defense programme", "cybersecurity", "border security", "disaster resilience", "public safety", "risk management", "emergency response", "critical infrastructure", "forensic science", "law enforcement", "crisis management"],
            # Cluster 4: Digital, Industry and Space
            "digital": ["digital cluster", "industry 4.0", "space research", "ict topics", "ai call", "quantum computing", "data funding", "digital transformation", "artificial intelligence", "machine learning", "cloud computing", "cyber physical systems", "robotics", "internet of things", "iot", "blockchain", "5g", "6g", "nanotechnology", "advanced materials", "additive manufacturing", "semiconductors", "edge computing", "digital twins", "autonomous systems"],
            # Cluster 5: Climate, Energy and Mobility
            "climate": ["climate cluster", "energy funding", "mobility research", "renewable energy", "green deal", "carbon neutral", "clean energy", "sustainable transport", "climate action", "decarbonization", "energy transition", "batteries", "hydrogen", "smart grids", "electric vehicles", "public transport", "low carbon industry", "circular economy", "carbon capture"],
            # Cluster 6: Food, Bioeconomy, Natural Resources, Agriculture and Environment
            "food": ["food cluster", "bioeconomy", "agricultural research", "environmental funding", "natural resources", "sustainable agriculture", "food security", "agri-food", "rural development", "forestry", "marine resources", "water management", "biodiversity", "soil health", "precision farming", "food processing", "bio-based products"],
            # European Innovation Council (EIC)
            "eic": ["eic accelerator", "innovation council", "startup grant", "sme funding", "accelerator programme", "eic pathfinder", "eic transition", "deep tech innovation", "disruptive innovation", "high risk research", "scale-up funding", "venture capital", "tech transfer"],
            # European Research Council (ERC)
            "erc": ["erc grant", "research council", "frontier research", "excellent science", "erc starting grant", "erc consolidator", "erc advanced", "erc synergy", "blue sky research", "fundamental research", "scientific excellence", "research leadership"]
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
            r'\bfind.*calls?\s+\w+',
            r'\bare\s+there\s+any.*calls',
            r'\bany.*calls.*related\s+to',
            r'\bopen.*calls.*related'
        ]
        
        has_call_pattern = any(re.search(pattern, question_lower) for pattern in call_patterns)
        
        # Also check for simple "calls" + topic combinations
        has_calls_and_topic = 'calls' in question_lower and any(topic in question_lower for topic in ['quantum', 'ai', 'energy', 'climate', 'health', 'digital'])
        
        if has_call_keyword or has_general_indicator or has_call_pattern or has_calls_and_topic:
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

    def detect_call_intent(self, question: str) -> Tuple[str, str, float]:
        """Detect call-specific intent using the integrated system."""
        return self.detect_call_specific_intent(question)
    
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
                
                # Check if user specifically asked for open calls
                include_closed_calls = not ('open' in question.lower() and ('call' in question.lower() or 'funding' in question.lower()))
                
                enhanced_result = self.enhanced_search.search_calls_enhanced(
                    query=question,
                    max_results=max(max_context_chunks, 20),  # Use at least 20 results for better coverage
                    include_closed=include_closed_calls,  # Only include closed if not asking specifically for open
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
            answer_parts.append(f"  \n**{i}. {result.title}**")
            
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
        message += "• Verify the call identifier on the EU Funding Portal\n"
        message += "• Try searching with broader terms or cluster names\n"
        message += "• Check the relevant Work Programme for your research area\n"
        message += "• Visit: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/portal/home\n"
        return {
            'answer': message,
            'intent': 'NO_CALL_RESULTS',
            'call_identifier': call_identifier,
            'sources': [],
            'confidence': 0.0,
            'data_source': 'No call documentation found',
            'success': False
        }
    
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

    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of all integrated services."""
        return {
            'vector_search': {
                'enabled': True,
                'stats': self.vector_search.get_search_stats()
            },
            'cordis_rag': {
                'enabled': True,
                'ai_provider': self.cordis_rag.ai_provider,
                'model': self.cordis_rag.openai_model_name if self.cordis_rag.ai_provider == "openai" else self.cordis_rag.gemini_model_name
            },
            'supabase': {
                'connected': self.supabase.test_connection()
            },
            'embedding_service': {
                'stats': self.embedder.get_embedding_stats()
            }
        }
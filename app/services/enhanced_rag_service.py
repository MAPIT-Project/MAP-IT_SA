"""
Enhanced RAG service that integrates vector search with existing CORDIS search.
"""

from typing import List, Dict, Any, Optional, Tuple
import json
import logging
from datetime import datetime

from .vector_search_service import VectorSearchService, SearchResult
from .rag_service import CordisRAG
from .embedding_service import EmbeddingService
from .supabase_client import SupabaseVectorStore
# Note: CallSpecificRAG is imported locally within methods to avoid circular imports
from ..core.config import settings

logger = logging.getLogger(__name__)

class HorizonEuropeRAG:
    """Enhanced RAG system integrating vector search with existing CORDIS search."""
    
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
        self.embedder = embedding_service or EmbeddingService(cache_client=self.supabase)
        self.vector_search = vector_search_service or VectorSearchService(self.supabase, self.embedder)
        
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
        
        # Call-Specific RAG will be initialized on-demand to avoid circular imports
        self._call_specific_rag = None
        logger.info("✅ Enhanced Horizon Europe RAG system initialized")
    
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
        
        # Determine intent using existing CORDIS RAG logic
        intent, confidence = self.cordis_rag.determine_user_intent(question)
        
        logger.info(f"🧠 Intent determined: {intent} (confidence: {confidence:.2f})")
        
        # Route to appropriate handler based on intent and user preferences
        if intent == "PROJECT_SEARCH" and include_projects:
            return self.handle_project_query(question)
        elif intent == "SEARCH_CALLS" and include_projects:
            return self.handle_call_query(question)
        elif intent in ["GENERAL_INFO", "GENERAL_QUERY"]:
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
        
        try:
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
        """Handle call/funding opportunity queries with enhanced call-specific RAG."""
        
        logger.info(f"📞 Handling call query with enhanced call-specific RAG")
        
        try:
            # Import locally to avoid circular imports
            from .call_specific_rag import CallSpecificRAG
            
            # Initialize call-specific RAG on-demand
            if self._call_specific_rag is None:
                self._call_specific_rag = CallSpecificRAG(
                    vector_search_service=self.vector_search,
                    supabase_client=self.supabase,
                    embedding_service=self.embedder,
                    cordis_rag=self.cordis_rag
                )
            
            # First, detect if this is a call-specific query that should use comprehensive docs
            intent_type, call_identifier, confidence = self._call_specific_rag.detect_call_specific_intent(question)
            
            if intent_type in ["SPECIFIC_CALL", "SPECIFIC_TOPIC", "CLUSTER_SPECIFIC"]:
                logger.info(f"🎯 Using comprehensive call documentation for: {intent_type}")
                
                # Use call-specific RAG for comprehensive call documentation
                result = self._call_specific_rag.handle_call_specific_query(
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
                # Fall back to existing CORDIS call search for general call queries
                logger.info(f"📞 Falling back to CORDIS call search for general query")
                
                result = self.cordis_rag.search_for_calls(
                    question=question,
                    max_results=10
                )
                
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
                intent, _ = self.cordis_rag.determine_user_intent(question)
                
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
    
    def detect_call_intent(self, question: str) -> Tuple[str, str, float]:
        """Detect call-specific intent using the CallSpecificRAG system."""
        if self._call_specific_rag is None:
            from .call_specific_rag import CallSpecificRAG
            self._call_specific_rag = CallSpecificRAG(
                vector_search_service=self.vector_search,
                supabase_client=self.supabase,
                embedding_service=self.embedder,
                cordis_rag=self.cordis_rag
            )
        return self._call_specific_rag.detect_call_specific_intent(question)

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
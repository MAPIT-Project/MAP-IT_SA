"""
AI Agent that decides which tools/services to call based on user queries.
This is the overseeing AI that makes intelligent routing decisions.
"""

import json
import re
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

class AIAgent:
    """
    Overseeing AI agent that decides which tools/services to call.
    """
    
    def __init__(self, gemini_api_key: str = None):
        """Initialize the AI agent."""
        api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        else:
            self.model = None
    
    async def decide_action(self, 
                           user_message: str, 
                           conversation_context: str,
                           conversation_id: int) -> Dict[str, Any]:
        """
        Decide what action to take for a user message.
        
        Returns:
            {
                'action': 'search_calls' | 'search_projects' | 'search_documents' | 'direct_answer',
                'service': 'enhanced_call_search' | 'cordis_rag' | 'vector_search' | 'none',
                'parameters': {...},
                'reasoning': 'Why this decision was made'
            }
        """
        
        if not self.model:
            return self._fallback_decision(user_message)
        
        prompt = f"""You are an AI agent that decides how to answer questions about European research funding.

AVAILABLE SERVICES:
1. enhanced_call_search - For finding open/closed funding calls from EU Portal API
2. cordis_rag - For finding existing research projects from CORDIS database  
3. vector_search - For searching Horizon Europe documents and FAQs
4. direct_answer - For questions that can be answered from conversation context

USER MESSAGE: {user_message}

CONVERSATION CONTEXT: {conversation_context[:300]}...

DECISION RULES:
- "open calls", "funding opportunities", "calls for proposals" → enhanced_call_search
- "projects", "research projects", "case studies", "examples" → cordis_rag
- "how to", "process", "guidelines", "requirements" → vector_search
- Context references like "its budget", "tell me more" → check context first

Analyze the user's message and decide the best approach.

Respond in JSON format:
{{
    "action": "search_calls|search_projects|search_documents|direct_answer",
    "service": "enhanced_call_search|cordis_rag|vector_search|none",
    "parameters": {{
        "query": "cleaned query",
        "max_results": 10,
        "include_closed": false
    }},
    "reasoning": "Why this service was chosen"
}}"""

        try:
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                logger.info(f"🤖 AI Agent Decision: {decision['action']} using {decision['service']}")
                logger.info(f"   Reasoning: {decision['reasoning']}")
                return decision
                
        except Exception as e:
            logger.error(f"AI agent decision error: {e}")
        
        return self._fallback_decision(user_message)
    
    def _fallback_decision(self, user_message: str) -> Dict[str, Any]:
        """Fallback decision logic when AI is not available."""
        
        message_lower = user_message.lower()
        
        # Simple keyword-based routing
        if any(word in message_lower for word in ['open calls', 'calls for', 'funding opportunities']):
            return {
                'action': 'search_calls',
                'service': 'enhanced_call_search',
                'parameters': {'query': user_message, 'max_results': 10, 'include_closed': False},
                'reasoning': 'Detected call-related keywords'
            }
        elif any(word in message_lower for word in ['projects', 'research projects', 'case studies']):
            return {
                'action': 'search_projects', 
                'service': 'cordis_rag',
                'parameters': {'query': user_message, 'max_results': 5},
                'reasoning': 'Detected project-related keywords'
            }
        else:
            return {
                'action': 'search_documents',
                'service': 'vector_search', 
                'parameters': {'query': user_message, 'max_results': 5},
                'reasoning': 'Default to document search'
            }

class AIServiceExecutor:
    """
    Executes the AI agent's decisions by calling the appropriate services.
    """
    
    def __init__(self):
        """Initialize service executor."""
        self.services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all available services."""
        try:
            from ..enhanced_call_search import EnhancedCallSearchService
            self.services['enhanced_call_search'] = EnhancedCallSearchService()
            logger.info("✅ Enhanced call search service loaded")
        except Exception as e:
            logger.warning(f"⚠️ Enhanced call search not available: {e}")
        
        try:
            from ..rag_service import CordisRAG
            self.services['cordis_rag'] = CordisRAG()
            logger.info("✅ CORDIS RAG service loaded")
        except Exception as e:
            logger.warning(f"⚠️ CORDIS RAG not available: {e}")
        
        try:
            from ..enhanced_rag_service import HorizonEuropeRAG
            self.services['enhanced_rag'] = HorizonEuropeRAG()
            logger.info("✅ Enhanced RAG service loaded")
        except Exception as e:
            logger.warning(f"⚠️ Enhanced RAG not available: {e}")
    
    async def execute_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the AI agent's decision.
        
        Args:
            decision: Decision from AI agent
            
        Returns:
            Service execution result
        """
        
        action = decision.get('action')
        service_name = decision.get('service')
        parameters = decision.get('parameters', {})
        
        logger.info(f"🔧 Executing: {action} using {service_name}")
        
        try:
            if service_name == 'enhanced_call_search':
                return await self._execute_call_search(parameters)
            elif service_name == 'cordis_rag':
                return await self._execute_project_search(parameters)
            elif service_name == 'enhanced_rag':
                return await self._execute_enhanced_rag(parameters)
            else:
                return {'error': f'Unknown service: {service_name}', 'success': False}
                
        except Exception as e:
            logger.error(f"Service execution error: {e}")
            return {'error': str(e), 'success': False}
    
    async def _execute_call_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced call search."""
        service = self.services.get('enhanced_call_search')
        if not service:
            return {'error': 'Enhanced call search not available', 'success': False}
        
        query = params.get('query', '')
        max_results = params.get('max_results', 10)
        include_closed = params.get('include_closed', False)
        
        result = service.search_calls_enhanced(
            query=query,
            max_results=max_results,
            include_closed=include_closed
        )
        
        if result.get('status') == 'success':
            # Format for response
            calls_data = []
            for call in result.get('results', []):
                calls_data.append({
                    'identifier': call.identifier,
                    'title': call.title,
                    'status': call.status,
                    'deadline': call.deadline,
                    'url': call.url
                })
            
            return {
                'service': 'enhanced_call_search',
                'calls_found': len(calls_data),
                'calls': calls_data,
                'search_metadata': result.get('search_metadata', {}),
                'success': True
            }
        else:
            return {
                'service': 'enhanced_call_search',
                'error': 'No calls found',
                'success': False
            }
    
    async def _execute_project_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CORDIS project search."""
        service = self.services.get('cordis_rag')
        if not service:
            return {'error': 'CORDIS RAG not available', 'success': False}
        
        query = params.get('query', '')
        max_results = params.get('max_results', 5)
        
        result = service.get_ai_response_with_routing(
            question=query,
            max_projects_to_process=max_results
        )
        
        return {
            'service': 'cordis_rag',
            'answer': result.get('answer', ''),
            'projects_found': result.get('projects_found', 0),
            'data_source': result.get('data_source', ''),
            'success': True
        }
    
    async def _execute_enhanced_rag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced RAG search."""
        service = self.services.get('enhanced_rag')
        if not service:
            return {'error': 'Enhanced RAG not available', 'success': False}
        
        query = params.get('query', '')
        max_chunks = params.get('max_results', 5)
        
        result = service.answer_question(
            question=query,
            max_context_chunks=max_chunks
        )
        
        return {
            'service': 'enhanced_rag',
            'answer': result.get('answer', ''),
            'confidence': result.get('confidence', 0.0),
            'data_source': result.get('data_source', ''),
            'success': True
        }
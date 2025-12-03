"""
Unified AI-Powered Intent Classifier

Single, intelligent AI system that classifies ALL user intents:
1. Answer FAQ (general questions about Horizon Europe, procedures, eligibility)
2. Search Projects (find CORDIS research projects and case studies)
3. Search Calls (find open/closed funding opportunities)
4. Call-Specific Questions (answer questions about a specific call)
5. Proposal Writing (help draft, improve, or export proposal sections)
"""

import json
import re
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import google.generativeai as genai

logger = logging.getLogger(__name__)

@dataclass
class UnifiedIntent:
    """Unified intent classification result"""
    primary_intent: str  # "faq", "search_projects", "search_calls", "call_specific", "proposal_writing", "follow_up"
    confidence: float  # 0.0-1.0
    reasoning: str
    
    # Tool planning
    requires_tools: bool
    tool_plan: List[Dict[str, Any]]
    
    # NEW: Complexity and routing (determined by LLM, not regex!)
    complexity_type: str = "simple"  # "simple", "comparison", "analysis", "multi_source", "validation"
    requires_multi_tool: bool = False  # Should use ToolAwareAgent?
    suggested_tools: List[str] = None  # Specific tools the LLM recommends
    complexity_reasoning: str = ""  # Why this complexity level?
    
    # Context extraction
    call_id: Optional[str] = None  # For call-specific or proposal writing
    section_id: Optional[str] = None  # For proposal writing sections
    project_keywords: List[str] = None  # For project searches
    call_keywords: List[str] = None  # For call searches
    
    # Proposal-specific
    proposal_action: Optional[str] = None  # "draft", "improve", "export", "navigate"
    
    # Follow-up specific
    follow_up_type: Optional[str] = None  # "repeat", "clarify", "expand", "compare"
    
    # Additional context
    conversation_context_used: bool = False
    extracted_entities: Dict[str, Any] = None


class UnifiedIntentClassifier:
    """
    Single AI-powered classifier that handles ALL intent types with high accuracy.
    Uses a carefully designed prompt that teaches the AI to distinguish between
    the 5 main intent categories.
    """
    
    def __init__(self):
        """Initialize the unified classifier"""
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model_name = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"✅ Unified Intent Classifier initialized (model: {model_name})")
    
    async def classify_intent(
        self,
        user_message: str,
        conversation_id: int,
        recent_messages: List[Dict[str, str]] = None
    ) -> UnifiedIntent:
        """
        Classify user intent into one of 5 categories with high accuracy.
        
        Args:
            user_message: The user's current message
            conversation_id: Current conversation ID
            recent_messages: Recent conversation history for context
        
        Returns:
            UnifiedIntent with classification and tool planning
        """
        
        # Build conversation context
        conversation_context = self._build_conversation_context(recent_messages or [])
        logger.info(f"🔍 Built conversation context:")
        logger.info(f"{conversation_context}")
        
        # Create comprehensive classification prompt
        prompt = self._create_classification_prompt(user_message, conversation_context)
        
        try:
            # Get AI classification
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1000,
                )
            )
            
            # Safely get response text
            try:
                response_text = response.text
            except Exception as e:
                # Response might be blocked by safety filters
                logger.warning(f"Could not get response text: {e}")
                # Try to get partial response
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    response_text = part.text
                                    break
                else:
                    raise ValueError("No valid response from LLM")
            
            # Log raw response for debugging
            logger.debug(f"🔍 Raw LLM response:\n{response_text[:500]}")
            
            # Parse response
            intent = self._parse_classification_response(
                response_text,
                user_message,
                conversation_id
            )
            
            logger.info(f"✅ Intent classified: {intent.primary_intent} (confidence: {intent.confidence:.2f})")
            logger.info(f"   Reasoning: {intent.reasoning[:100]}...")
            
            return intent
            
        except Exception as e:
            logger.error(f"❌ Intent classification failed: {e}")
            # Return safe fallback
            return self._create_fallback_intent(user_message, conversation_id)
    
    def _create_classification_prompt(self, message: str, context: str) -> str:
        """Create the classification prompt - concise but comprehensive"""
        
        return f"""Classify this user message for a Horizon Europe funding assistant.

CONTEXT: {context}
MESSAGE: "{message}"

OUTPUT JSON:
{{
  "primary_intent": "faq|search_projects|search_calls|call_specific|proposal_writing|follow_up",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "complexity_type": "simple|comparison|analysis|multi_source|validation",
  "requires_multi_tool": true/false,
  "complexity_reasoning": "why this complexity",
  "suggested_tools": ["tool1", "tool2"],
  "requires_tools": true/false,
  "tool_plan": [],
  "call_id": null,
  "project_keywords": [],
  "call_keywords": [],
  "proposal_action": null,
  "follow_up_type": null
}}

INTENT RULES:
- follow_up: references previous message ("repeat", "again", "said", "that")
- faq: general questions about funding, eligibility, process
- search_projects: wants to find funded projects
- search_calls: wants to find funding opportunities
- call_specific: asks about specific call ID (HORIZON-XXX-...)
- proposal_writing: help writing/editing proposal

COMPLEXITY RULES:
- simple: single question, single source answers it
- comparison: comparing 2+ things (EIC vs ERC) → requires_multi_tool=true
- analysis: asking WHY or to analyze trends → requires_multi_tool=true
- multi_source: needs stats AND documents → requires_multi_tool=true
- validation: verify/confirm information → requires_multi_tool=true

TOOLS: get_programme_statistics, get_country_statistics, compare_programmes, search_documents, search_specific_topic, search_funding_calls, get_call_details, search_projects, verify_eligibility, cross_reference

Respond with ONLY the JSON, no other text."""
    
    def _build_conversation_context(self, recent_messages: List[Dict[str, str]]) -> str:
        """Build conversation context string"""
        if not recent_messages:
            return "No previous context"
        
        context_lines = []
        for msg in recent_messages[-5:]:  # Last 5 messages
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            # Show more text (200 chars) to ensure call IDs and important context are visible
            context_lines.append(f"{sender.upper()}: {text[:200]}")
        
        return "\n".join(context_lines)
    
    def _parse_classification_response(
        self,
        response_text: str,
        user_message: str,
        conversation_id: int
    ) -> UnifiedIntent:
        """Parse the AI's classification response"""
        
        try:
            # Extract JSON from response - try multiple approaches
            json_str = None
            
            # Method 1: Look for JSON in code block
            code_block_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1)
            
            # Method 2: Look for raw JSON object
            if not json_str:
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
            
            if not json_str:
                logger.error(f"No JSON found in response. Full response:\n{response_text[:800]}")
                raise ValueError("No JSON found in response")
            
            # Clean up common JSON issues
            json_str = json_str.strip()
            # Fix trailing commas before closing braces
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                # Try to fix common issues and retry
                logger.warning(f"Initial JSON parse failed: {e}, attempting fix")
                # Remove any control characters
                json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in '\n\t')
                data = json.loads(json_str)
            
            # Build tool plan - MUST be a list of dicts with valid tool_name
            tool_plan = []
            raw_tool_plan = data.get('tool_plan')
            
            if raw_tool_plan and isinstance(raw_tool_plan, list):
                # LLM provided a list - validate each item is a dict with tool_name
                tool_plan = [
                    tp for tp in raw_tool_plan 
                    if isinstance(tp, dict) and tp.get('tool_name')
                ]
            
            # If no valid tool plan, auto-generate based on intent
            if not tool_plan:
                tool_plan = self._generate_tool_plan(data, user_message, conversation_id)
            
            # Extract complexity info (NEW - LLM determines this, not regex!)
            complexity_type = data.get('complexity_type', 'simple')
            requires_multi_tool = data.get('requires_multi_tool', False)
            suggested_tools = data.get('suggested_tools', [])
            complexity_reasoning = data.get('complexity_reasoning', '')
            
            # Log complexity decision
            if requires_multi_tool:
                logger.info(f"🧠 LLM determined COMPLEX query: {complexity_type}")
                logger.info(f"   Suggested tools: {suggested_tools}")
                logger.info(f"   Reasoning: {complexity_reasoning[:100]}...")
            
            # Create unified intent
            intent = UnifiedIntent(
                primary_intent=data['primary_intent'],
                confidence=float(data['confidence']),
                reasoning=data['reasoning'],
                requires_tools=data.get('requires_tools', False),
                tool_plan=tool_plan,
                # NEW: Complexity fields
                complexity_type=complexity_type,
                requires_multi_tool=requires_multi_tool,
                suggested_tools=suggested_tools,
                complexity_reasoning=complexity_reasoning,
                # Context extraction
                call_id=data.get('call_id'),
                section_id=data.get('section_id'),
                project_keywords=data.get('project_keywords', []),
                call_keywords=data.get('call_keywords', []),
                proposal_action=data.get('proposal_action'),
                follow_up_type=data.get('follow_up_type'),
                extracted_entities={}
            )
            
            return intent
            
        except Exception as e:
            logger.error(f"Failed to parse classification: {e}")
            return self._create_fallback_intent(user_message, conversation_id)
    
    def _generate_tool_plan(
        self,
        classification: Dict[str, Any],
        user_message: str,
        conversation_id: int
    ) -> List[Dict[str, Any]]:
        """Generate appropriate tool plan based on intent"""
        
        intent = classification.get('primary_intent')
        message_lower = user_message.lower()
        
        # Follow-up intent: NO tools needed, use conversation history
        if intent == 'follow_up':
            return []  # Handled by conversation context, no tools needed
        
        # Check if query would benefit from intelligent_search (graph + LLM planning)
        intelligent_triggers = [
            'eligible', 'eligibility', 'can participate', 'allowed to',
            'budget', 'funding', 'maximum', 'minimum', 'average',
            'consortium', 'partners', 'countries required', 'how many',
            'similar', 'like', 'related to', 'find calls',
            'cluster', 'horizon-', 'who has', 'track record',
            'switzerland', 'associated', 'third country',
            'sme', 'university', 'research organization',
            'ria', 'ia', 'csa', 'erc', 'msca',
        ]
        
        if any(trigger in message_lower for trigger in intelligent_triggers):
            return [{
                'tool_name': 'intelligent_search',
                'parameters': {
                    'query': user_message,
                    'max_results': 10
                },
                'reason': 'Intelligent search using graph database and LLM planning for structured queries'
            }]
        
        if intent == 'search_projects':
            return [{
                'tool_name': 'search_cordis_projects',
                'parameters': {
                    'query': user_message,
                    'keywords': classification.get('project_keywords', []),
                    'max_results': 15
                },
                'reason': 'Search CORDIS database for research projects'
            }]
        
        elif intent == 'search_calls':
            # Extract keywords only - don't include "open", "calls for", etc.
            call_keywords = classification.get('call_keywords', [])
            # If AI provided keywords, use them; otherwise extract from message
            if call_keywords:
                query = ' '.join(call_keywords)
            else:
                # Fallback: remove common query words
                query = user_message.lower()
                remove_words = ['what', 'are', 'some', 'open', 'calls', 'for', 'show', 'me', 'find', 'search']
                for word in remove_words:
                    query = query.replace(word, '')
                query = ' '.join(query.split())  # Clean extra spaces
            
            return [{
                'tool_name': 'eu_portal_search',
                'parameters': {
                    'query': query,
                    'keywords': call_keywords,
                    'max_results': 15
                },
                'reason': 'Search EU Funding & Tenders Portal for calls'
            }]
        
        elif intent == 'call_specific':
            call_id = classification.get('call_id')
            if call_id:
                return [{
                    'tool_name': 'search_call_documents',
                    'parameters': {
                        'call_id': call_id,
                        'query': user_message,
                        'max_results': 10
                    },
                    'reason': f'Search call-specific documents for {call_id}'
                }]
            else:
                # Fallback to general search
                return [{
                    'tool_name': 'search_local_database',
                    'parameters': {
                        'query': user_message,
                        'max_context_chunks': 5
                    },
                    'reason': 'Search general knowledge base'
                }]
        
        elif intent == 'faq':
            # Use intelligent_search for FAQ - it can answer from graph + vector
            return [{
                'tool_name': 'intelligent_search',
                'parameters': {
                    'query': user_message,
                    'max_results': 10
                },
                'reason': 'Search knowledge base with intelligent graph + vector hybrid'
            }]
        
        elif intent == 'proposal_writing':
            # Proposal writing doesn't use tools - handled separately
            return []
        
        # Default fallback - use intelligent_search
        return [{
            'tool_name': 'intelligent_search',
            'parameters': {
                'query': user_message,
                'max_results': 10
            },
            'reason': 'Intelligent search for general queries'
        }]
    
    def _create_fallback_intent(
        self,
        user_message: str,
        conversation_id: int
    ) -> UnifiedIntent:
        """Create safe fallback when classification fails"""
        
        logger.warning(f"Using fallback intent for: {user_message[:50]}...")
        
        # Check if this looks like a follow-up question
        message_lower = user_message.lower()
        follow_up_triggers = ['repeat', 'again', 'said', 'mentioned', 'discussed', 
                             'earlier', 'previous', 'last', 'summarize', 'elaborate', 
                             'clarify', 'what did you', 'can you repeat', 'say that again']
        
        if any(trigger in message_lower for trigger in follow_up_triggers):
            logger.info(f"Fallback detected as follow_up intent")
            return UnifiedIntent(
                primary_intent="follow_up",
                confidence=0.7,
                reasoning="Fallback classification - detected follow-up language",
                requires_tools=False,
                tool_plan=[],
                call_id=None,
                section_id=None,
                project_keywords=[],
                call_keywords=[],
                proposal_action=None,
                follow_up_type="repeat"
            )
        
        # Default to intelligent_search for robust fallback
        return UnifiedIntent(
            primary_intent="faq",
            confidence=0.5,
            reasoning="Fallback classification - using intelligent search",
            requires_tools=True,
            tool_plan=[{
                'tool_name': 'intelligent_search',
                'parameters': {
                    'query': user_message,
                    'max_results': 10
                },
                'reason': 'Intelligent search fallback for comprehensive coverage'
            }],
            call_id=None,
            section_id=None,
            project_keywords=[],
            call_keywords=[],
            proposal_action=None,
            follow_up_type=None
        )
    
    def extract_call_id(self, text: str) -> Optional[str]:
        """Extract call ID from text"""
        # Match HORIZON-XXX-YYYY-ZZ-... pattern
        pattern = r'HORIZON-[A-Z0-9]+-\d{4}-[A-Z0-9]+-[A-Z0-9-]+'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0).upper() if match else None


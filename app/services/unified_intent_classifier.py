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
                    temperature=0.2,  # Slightly higher for better context awareness
                    max_output_tokens=800,
                )
            )
            
            # Parse response
            intent = self._parse_classification_response(
                response.text,
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
        """Create the classification prompt with clear examples"""
        
        return f"""You are an expert intent classifier for a Horizon Europe research funding assistant.
Your job is to classify the user's message into ONE of 6 intent categories with HIGH accuracy.

**THE 6 INTENT CATEGORIES:**

1. **follow_up** - User is referencing PREVIOUS conversation content (HIGHEST PRIORITY - check first!)
   Examples:
   - "Can you repeat that?"
   - "Say that again"
   - "What did you just say?"
   - "Can you explain that more?"
   - "Tell me more about that"
   - "What was the first point?"
   - "Go back to what you said about..."
   - "You mentioned X, can you elaborate?"
   - "Can you summarize what we discussed?"
   - "What were those requirements again?"
   
   **CRITICAL: If user refers to previous answer content → follow_up**
   **Keywords that trigger follow_up:** repeat, again, said, mentioned, discussed, previous, earlier, last, summarize, elaborate, clarify, more about that

2. **faq** - General questions about Horizon Europe, procedures, eligibility, documentation
   Examples:
   - "How do I apply for Horizon Europe funding?"
   - "What are the eligibility criteria?"
   - "Explain the evaluation process"
   - "What documents do I need to submit?"
   - "Tell me about Horizon Europe structure"
   - "How does consortium building work?"

3. **search_projects** - User wants to FIND specific research projects or case studies
   Examples:
   - "Show me projects about renewable energy"
   - "Find research on AI in healthcare"
   - "What projects have been funded in biotechnology?"
   - "Can you show me successful climate projects?"
   - "Search for projects led by universities in Germany"

4. **search_calls** - User wants to FIND funding calls and opportunities
   Examples:
   - "What calls are open for renewable energy?"
   - "Show me funding opportunities in AI"
   - "Are there any grants for clean technology?"
   - "Find open calls with deadline in 2025"
   - "What funding is available for SMEs?"

5. **call_specific** - Questions about a SPECIFIC call (when call ID is mentioned OR in context)
   Examples:
   - "Tell me about HORIZON-CL3-2025-02-CS-ECCC-01"
   - "What are the requirements for HORIZON-MSCA-2024-DN-01?"
   - "What is the budget for call HORIZON-CL4-2025-TWIN-01?"
   - "When is the deadline for HORIZON-HLTH-2025-01?"
   
   **Context-based examples (call ID from previous message):**
   - Context: "USER: Tell me about HORIZON-CL3-2025" → Message: "What's the deadline?" → call_specific
   - Context: "USER: HORIZON-MSCA-2024-DN-01" → Message: "What about the budget?" → call_specific  
   - Context: "AI answered about HORIZON-CL4-2025" → Message: "Can I apply?" → call_specific
   - Any question referring to "it", "that call", "the call" when call ID in context → call_specific

6. **proposal_writing** - User wants help WRITING, IMPROVING, EDITING, or EXPORTING a proposal
   Examples:
   - "Help me write a proposal for HORIZON-CL3-2025-02-CS-ECCC-01"
   - "Draft the objectives section"
   - "Move to the next section"
   - "Improve this methodology"
   - "Make the objectives more specific"
   - "Add more detail to the methodology"
   - "Edit the current section to include KPIs"
   - "Revise the impact section"
   - "Export my proposal to Word"
   - "Generate the budget table"
   - "Check compliance with call requirements"

**CONVERSATION CONTEXT:**
{context}

**USER MESSAGE:**
"{message}"

**CLASSIFICATION INSTRUCTIONS:**

1. **FIRST: Check for FOLLOW-UP intent (highest priority!)**
   - Does the message reference previous conversation? ("repeat", "again", "said", "mentioned", "that")
   - Does it ask to clarify, expand, or summarize previous content?
   - If YES → **follow_up** (determine follow_up_type: repeat/clarify/expand/summarize)

2. **SECOND: Scan conversation context for call IDs (HORIZON-XXX-YYYY-ZZ format)**
   - Look in USER messages and AI messages
   - If found, note it for step 3

3. **THEN: Analyze the current message**
   - Does it ask a question WITHOUT a new call ID?
   - Does it use "it", "that", "the call", "this call", or just direct questions like "what's the deadline?"
   - If YES + call ID found in context → **call_specific** (extract call ID from context!)
   
4. **Otherwise: Look for explicit indicators in the message itself:**
   - "find", "show", "search" + "projects" → search_projects
   - "find", "show", "search" + "calls/opportunities/grants" → search_calls
   - Call ID mentioned (HORIZON-XXX-YYYY-ZZ) + question → call_specific
   - "write", "draft", "help", "generate", "export" + "proposal" → proposal_writing
   - General questions, "how to", "what is", "explain" → faq

5. **Extract relevant information:**
   - **IMPORTANT**: If call ID present IN MESSAGE **OR CONTEXT**, extract it (format: HORIZON-XXX-YYYY-...)
   - If proposal writing: determine action (draft/improve/export/navigate)
   - If searching: extract search keywords
   - If follow_up: determine follow_up_type (repeat/clarify/expand/summarize)

6. **Provide confidence** (0.0-1.0):
   - 0.9-1.0: Very clear intent
   - 0.7-0.9: Clear intent with some ambiguity
   - 0.5-0.7: Moderate confidence
   - Below 0.5: Uncertain (default to faq)

**AVAILABLE TOOLS (use these EXACT names):**
- **eu_portal_search** - For search_calls intent (searching funding opportunities)
- **search_cordis_projects** - For search_projects intent (searching research projects)
- **search_local_database** - For faq intent (general knowledge base queries)
- **search_call_documents** - For call_specific intent (when call ID is known)

**OUTPUT FORMAT (JSON):**
```json
{{
  "primary_intent": "follow_up|faq|search_projects|search_calls|call_specific|proposal_writing",
  "confidence": 0.95,
  "reasoning": "Clear explanation of why you chose this intent",
  "requires_tools": true,
  "tool_plan": [
    {{
      "tool_name": "eu_portal_search",
      "parameters": {{"query": "user message or cleaned query"}},
      "reason": "Why this tool"
    }}
  ],
  "call_id": "HORIZON-XXX-YYYY-ZZ or null",
  "section_id": "excellence.objectives or null",
  "project_keywords": ["keyword1", "keyword2"],
  "call_keywords": ["keyword1", "keyword2"],
  "proposal_action": "draft|improve|export|navigate or null",
  "follow_up_type": "repeat|clarify|expand|summarize or null"
}}
```

**CRITICAL:** Always use the EXACT tool names from the "AVAILABLE TOOLS" list above!

**IMPORTANT RULES:**
- Be decisive - choose ONE primary intent
- **CHECK FOR FOLLOW-UP FIRST** - if user refers to previous content → follow_up
- **ALWAYS check conversation context for call IDs** when user uses "it", "that", "the call"
- If previous messages mention a call ID and current question refers to it → call_specific
- Extract call IDs from MESSAGE OR CONTEXT (format: HORIZON-XXX-YYYY-...)
- For proposal writing, identify the specific action
- For follow_up, identify the follow_up_type (repeat/clarify/expand/summarize)
- Provide clear, logical reasoning

Now classify the message above:"""
    
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
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            data = json.loads(json_match.group())
            
            # Build tool plan
            tool_plan = []
            if data.get('tool_plan'):
                tool_plan = data['tool_plan']
            else:
                # Auto-generate tool plan based on intent
                tool_plan = self._generate_tool_plan(data, user_message, conversation_id)
            
            # Create unified intent
            intent = UnifiedIntent(
                primary_intent=data['primary_intent'],
                confidence=float(data['confidence']),
                reasoning=data['reasoning'],
                requires_tools=data.get('requires_tools', False),
                tool_plan=tool_plan,
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


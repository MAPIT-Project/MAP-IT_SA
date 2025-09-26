"""
AI-only intent detection service that replaces complex rule-based systems.
Provides reliable, consistent intent analysis using a single AI model.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import os

logger = logging.getLogger(__name__)

@dataclass
class IntentAnalysis:
    """Structured intent analysis result"""
    intent_type: str  # "search_calls", "search_projects", "conversational"
    confidence: float  # 0.0-1.0
    requires_tools: bool
    tool_plan: List[Dict[str, Any]]  # List of tool specifications
    reasoning: str
    context_assessment: str
    processing_type: str  # "tool_based", "conversational", "mixed"
    extracted_keywords: List[str] = None  # AI-extracted search keywords

@dataclass
class ToolCall:
    """Tool call specification"""
    tool_name: str
    parameters: Dict[str, Any]
    execution_order: int
    reason: str

class AIIntentService:
    """
    AI-only intent detection service that provides reliable intent analysis
    without complex rule-based fallbacks.
    """

    def __init__(self):
        """Initialize the AI intent service"""
        self.model = None
        self._init_model()

    def _init_model(self):
        """Initialize the AI model for intent analysis"""
        try:
            # Import here to avoid circular imports
            from .rag.response_generator import GroundedResponseGenerator
            self.model = GroundedResponseGenerator(
                ai_provider=os.getenv('DEFAULT_AI_PROVIDER', 'gemini'),
                gemini_api_key=os.getenv('GEMINI_API_KEY'),
                openrouter_api_key=os.getenv('OPENROUTER_API_KEY')
            )
            logger.info("✅ AI Intent Service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI Intent Service: {e}")
            raise

    async def analyze_intent(self,
                            message: str,
                            conversation_context: str = "",
                            conversation_history: str = "",
                            conversation_id: int = 1) -> IntentAnalysis:
        """
        Analyze user intent using AI only - no rule-based fallbacks.

        Args:
            message: User's message
            conversation_context: Current conversation context
            conversation_history: Recent conversation turns
            conversation_id: Conversation ID for memory queries

        Returns:
            Structured intent analysis
        """
        try:

            # Get available tools for planning
            try:
                from ..tools.tool_orchestrator import create_research_orchestrator
                orchestrator = create_research_orchestrator()
                available_tools = orchestrator.get_available_tools()
            except ImportError as e:
                logger.warning(f"Could not import tool orchestrator: {e}")
                # Provide default tools if import fails
                available_tools = [
                    {
                        "name": "eu_portal_search",
                        "description": "Search for funding calls and opportunities",
                        "parameters": {
                            "query": "string",
                            "status": "string",
                            "max_results": "integer"
                        }
                    },
                    {
                        "name": "search_cordis_projects",
                        "description": "Search for research projects and case studies",
                        "parameters": {
                            "query": "string",
                            "max_results": "integer"
                        }
                    },
                    {
                        "name": "search_local_database",
                        "description": "Search local database for conversational queries",
                        "parameters": {
                            "query": "string",
                            "max_context_chunks": "integer",
                            "search_type": "string",
                            "similarity_threshold": "number"
                        }
                    },
                    {
                        "name": "search_conversation_memory",
                        "description": "Search conversation memory for questions about previous messages and conversation history",
                        "parameters": {
                            "query": "string",
                            "conversation_id": "integer",
                            "max_turns": "integer"
                        }
                    }
                ]

            # Create comprehensive prompt for AI analysis
            prompt = self._create_intent_analysis_prompt(
                message=message,
                conversation_context=conversation_context,
                conversation_history=conversation_history,
                available_tools=available_tools,
                conversation_id=conversation_id
            )

            # Make single AI call
            logger.info(f"🤖 AI Intent Analysis for: '{message[:100]}...'")
            response = self.model.model.generate_content(prompt)

            # Parse AI response
            analysis = self._parse_ai_response(response.text)

            logger.info(f"✅ Intent Analysis: {analysis.intent_type} (confidence: {analysis.confidence:.2f})")

            return analysis

        except Exception as e:
            logger.error(f"❌ AI Intent Analysis failed: {e}")
            # Return safe fallback with debugging information
            return self._create_fallback_analysis(message, str(e), conversation_id)

    def _create_intent_analysis_prompt(self,
                                       message: str,
                                       conversation_context: str,
                                       conversation_history: str,
                                       available_tools: List[Dict[str, Any]],
                                       conversation_id: int = 1) -> str:
        """
        Create comprehensive prompt for AI intent analysis with enhanced support for general questions and memory queries.
        """
        return f"""You are an expert AI assistant specializing in European research funding and innovation. Analyze this user message and determine their intent using your understanding of natural language and context.

USER MESSAGE: "{message}"

CONVERSATION CONTEXT:
{conversation_context if conversation_context else "New conversation"}

RECENT HISTORY:
{conversation_history if conversation_history else "No recent history"}

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

INTENT CATEGORIES:
- "search_calls": User wants to find funding opportunities, open calls, grants, deadlines, or funding programs
- "search_projects": User wants to find existing research projects, case studies, examples, or research initiatives  
- "conversational": General questions, greetings, help requests, discussions, procedural questions, clarification requests, informational queries, OR basic program information questions

IMPORTANT CONVERSATIONAL CLASSIFICATION:
- Questions about "What is Horizon Europe?" = CONVERSATIONAL (not search)
- Questions about "How much funding..." = CONVERSATIONAL (not search)  
- Questions about "How is X structured?" = CONVERSATIONAL (not search)
- Questions about "What are the pillars?" = CONVERSATIONAL (not search)
- Questions asking for explanations or information = CONVERSATIONAL (not search)
- Only classify as search_calls/search_projects if user explicitly wants to FIND/SEARCH specific opportunities or projects

TOOL SELECTION RULES:
- For "conversational" intent: Use search_local_database to get relevant context, then generate enhanced response
- For "search_calls": Use "eu_portal_search" for finding funding calls
- For "search_projects": Use "search_cordis_projects" for finding research projects
- For memory queries: Use "search_conversation_memory" with conversation_id: {conversation_id}

IMPORTANT: Conversational queries SHOULD use search_local_database to get relevant context from the knowledge base

CONFIDENCE SCORING:
- 0.9-1.0: Very clear intent with strong indicators
- 0.7-0.89: Clear intent but some ambiguity
- 0.5-0.69: Moderate ambiguity
- Below 0.5: Unclear intent

KEYWORD EXTRACTION:
- For search queries, extract ONLY the core search terms from the user's message
- Focus on the specific topic being searched for, NOT generic terms like "calls", "funding", "grants", "projects"
- DO NOT include generic terms that describe the search action itself
- Extract only the substantive content words that represent the search topic
- Examples:
  - "What are the open calls for renewable energy?" → ["renewable energy", "clean energy"]
  - "Show me projects about AI in healthcare" → ["AI", "healthcare"]
  - "Find grants for climate change research" → ["climate change", "environmental research"]
  - "Search for textile funding" → ["textile"] (NOT "textile funding")
  - "What are some calls about clothes?" → ["clothes", "fashion"] (NOT "calls", "funding opportunities")

RESPONSE FORMAT (JSON):
{{
    "intent_type": "search_calls|search_projects|conversational",
    "confidence": 0.85,
    "requires_tools": true/false,
    "tool_plan": [
        {{
            "tool_name": "eu_portal_search|search_cordis_projects|search_local_database|search_conversation_memory",
            "parameters": {{
                "query": "user's query",
                "max_results": 20
            }},
            "reason": "Why this tool is appropriate"
        }}
    ],
    "reasoning": "Your natural language reasoning about the user's intent",
    "context_assessment": "How this fits with the conversation context",
    "processing_type": "tool_based|conversational|mixed",
    "extracted_keywords": ["keyword1", "keyword2", "keyword3"]
}}

EXAMPLES TO GUIDE YOUR UNDERSTANDING:

SEARCH CALLS EXAMPLES:
- "What are the open calls for renewable energy?"
- "Show me funding opportunities in AI"
- "Are there any grants for clean technology?"
- "What deadlines are coming up for research funding?"

SEARCH PROJECTS EXAMPLES:
- "Can you show me projects about renewable energy?"
- "What research has been done on climate change?"
- "Find examples of successful Horizon Europe projects"
- "Show me case studies in biotechnology"

CONVERSATIONAL EXAMPLES (NO TOOLS NEEDED):
- "Hello, how can you help me?"
- "How do I apply for funding?"
- "Can you explain the process?"
- "What documents do I need?"
- "Tell me more about that"
- "What are the requirements?"
- "Tell me about Horizon Europe funding"
- "Explain the application process"
- "What are the eligibility requirements?"
- "How does the application process work?"
- "What do you mean by X?"
- "Could you elaborate on X?"
- "How does X work?"
- "What are the requirements for X?"
- "Can you explain that in more detail?"
- "Tell me more about X"
- "How much funding is available in Horizon Europe?"
- "What is the structure of Horizon Europe?"
- "What are the pillars of Horizon Europe?"
- "What is the budget for climate research?"

MEMORY QUERY EXAMPLES (use search_conversation_memory):
- "What was my first message?"
- "What did I ask about X earlier?"
- "Can you remind me what we discussed about X?"
- "What was the first thing I asked you?"
- "What did I say about X before?"
- "Can you recall what I mentioned about X?"
- "Show me our conversation history"
- "What topics have we discussed?"
- "Can you remind me what I asked about renewable energy?"

INSTRUCTIONS:
- Use your natural language understanding to determine intent
- Consider the context and conversation history  
- IMPORTANT: For informational questions, explanations, and general queries, classify as "conversational" with NO TOOLS
- Only use tools when the user explicitly wants to FIND or SEARCH for specific items
- For memory queries about conversation history, use search_conversation_memory tool
- Provide specific parameters for tool execution
- Explain your reasoning in natural language
- Be confident in your classification

CLASSIFICATION PRECEDENCE:
1. If query explicitly asks to FIND calls, funding, grants, opportunities → search_calls
2. If query explicitly asks to FIND projects, research, case studies → search_projects  
3. If query asks about conversation history → search_conversation_memory
4. All informational questions, explanations, "what is", "how much", "tell me about" → conversational (WITH search_local_database for context)
5. Everything else → conversational (WITH search_local_database for context)

IMPORTANT: Conversational queries should use search_local_database to get relevant context before generating responses

ANALYZE THE MESSAGE: "{message}" """

    def _parse_ai_response(self, response_text: str) -> IntentAnalysis:
        """
        Parse AI response into structured IntentAnalysis.
        """
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in AI response")

            data = json.loads(json_match.group())

            # Validate required fields
            required_fields = ['intent_type', 'confidence', 'requires_tools', 'reasoning']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Create tool plan from AI response
            tool_plan = []
            if data.get('tool_plan'):
                for i, tool_spec in enumerate(data['tool_plan']):
                    tool_call = ToolCall(
                        tool_name=tool_spec['tool_name'],
                        parameters=tool_spec.get('parameters', {}),
                        execution_order=i,
                        reason=tool_spec.get('reason', '')
                    )
                    tool_plan.append(tool_call)

            analysis = IntentAnalysis(
                intent_type=data['intent_type'],
                confidence=float(data['confidence']),
                requires_tools=data['requires_tools'],
                tool_plan=tool_plan,
                reasoning=data['reasoning'],
                context_assessment=data.get('context_assessment', ''),
                processing_type=data.get('processing_type', 'conversational'),
                extracted_keywords=data.get('extracted_keywords', [])
            )

            # SAFETY CHECK: Ensure conversational queries have appropriate tools
            if analysis.intent_type == 'conversational':
                # Conversational queries should have search_local_database for context
                if not analysis.tool_plan or not any(tool.tool_name == 'search_local_database' for tool in analysis.tool_plan):
                    logger.info("🔧 Adding search_local_database tool for conversational query")
                    from ..tools.tool_orchestrator import ToolCall
                    analysis.tool_plan = [ToolCall(
                        tool_name="search_local_database",
                        parameters={
                            "query": message,
                            "max_context_chunks": 5,
                            "search_type": "hybrid",  # Use hybrid instead of conversational
                            "similarity_threshold": 0.5
                        },
                        execution_order=0,
                        reason="Get relevant context for conversational query"
                    )]
                    analysis.requires_tools = True

            return analysis

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            # Return fallback analysis with debugging information
            return self._create_fallback_analysis(response_text, f"JSON parsing failed: {str(e)}", conversation_id)

    def _create_fallback_analysis(self, message: str, original_error: str = "", conversation_id: int = 1) -> IntentAnalysis:
        """
        Create safe fallback analysis when AI parsing fails.
        Default to conversational with no tools for safety.
        """
        logger.warning(f"🚨 Using fallback analysis for: '{message}' (Error: {original_error})")
        
        # For safety, always return conversational with no tools
        return IntentAnalysis(
            intent_type="conversational",
            confidence=0.5,
            requires_tools=False,
            tool_plan=[],
            reasoning=f"Fallback analysis due to parsing error: {original_error}. Defaulting to conversational for safety.",
            context_assessment="Unable to assess context due to parsing error",
            processing_type="conversational",
            extracted_keywords=[]
        )

    def get_intent_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about intent analysis performance.
        """
        return {
            "service_name": "AIIntentService",
            "model_used": "gemini-2.5-flash-lite",
            "approach": "AI-only",
            "fallback_rate": 0.0,  # Will be updated based on actual usage
            "average_confidence": 0.0,  # Will be updated based on actual usage
            "supported_intents": ["search_calls", "search_projects", "conversational"]
        }

# Test function
async def test_ai_intent_service():
    """Test the AI intent service with various queries."""
    try:
        service = AIIntentService()

        test_queries = [
            "What are some open calls for clean energy?",
            "Show me projects about AI in healthcare",
            "How do I apply for Horizon Europe funding?",
            "Hello, can you help me?",
            "Tell me more about that last project you mentioned"
        ]

        print("🧪 Testing AI Intent Service...")
        print("=" * 60)

        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}. Query: '{query}'")

            analysis = await service.analyze_intent(query)

            print(f"   Intent: {analysis.intent_type}")
            print(f"   Confidence: {analysis.confidence:.2f}")
            print(f"   Requires Tools: {analysis.requires_tools}")
            print(f"   Processing Type: {analysis.processing_type}")
            print(f"   Tools: {len(analysis.tool_plan)} planned")
            print(f"   Reasoning: {analysis.reasoning[:100]}...")

        print("\n✅ AI Intent Service test completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_intent_service())
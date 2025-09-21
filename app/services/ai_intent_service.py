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
- "conversational": General questions, greetings, help requests, discussions, procedural questions, clarification requests, or informational queries

TOOL SELECTION:
- "eu_portal_search": Use for finding funding calls, opportunities, grants, or funding programs
- "search_cordis_projects": Use for finding research projects, case studies, examples, or research initiatives
- "search_local_database": Use for conversational queries, procedural questions, informational requests, explanations, and general questions about Horizon Europe
- "search_conversation_memory": Use for memory queries about previous messages, conversation history, or what was discussed earlier. IMPORTANT: Always include conversation_id: {conversation_id} in parameters

CONFIDENCE SCORING:
- 0.9-1.0: Very clear intent with strong indicators
- 0.7-0.89: Clear intent but some ambiguity
- 0.5-0.69: Moderate ambiguity
- Below 0.5: Unclear intent

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
    "processing_type": "tool_based|conversational|mixed"
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

CONVERSATIONAL EXAMPLES:
- "Hello, how can you help me?"
- "How do I apply for funding?"
- "Can you explain the process?"
- "What documents do I need?"
- "Tell me more about that"
- "What are the requirements?"

GENERAL QUESTION EXAMPLES (use search_local_database):
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
- Choose the most appropriate tool based on the user's goal
- For general questions about Horizon Europe, use search_local_database tool
- For memory queries about conversation history, use search_conversation_memory tool
- Provide specific parameters for tool execution
- Explain your reasoning in natural language
- Be confident in your classification

CLASSIFICATION PRECEDENCE:
1. If query mentions calls, funding, grants, opportunities → search_calls
2. If query mentions projects, research, case studies, CORDIS, API, "find projects", "search for projects", "show me projects" → search_projects
3. If query is a memory query (see MEMORY QUERY EXAMPLES above) → search_conversation_memory → conversational
4. If query is a general question (see GENERAL QUESTION EXAMPLES above) → search_local_database → conversational
5. Everything else → conversational

IMPORTANT: You must analyze the user's intent using your natural language understanding, NOT keyword detection or regex patterns.

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

            return IntentAnalysis(
                intent_type=data['intent_type'],
                confidence=float(data['confidence']),
                requires_tools=data['requires_tools'],
                tool_plan=tool_plan,
                reasoning=data['reasoning'],
                context_assessment=data.get('context_assessment', ''),
                processing_type=data.get('processing_type', 'conversational')
            )

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            # Return fallback analysis with debugging information
            return self._create_fallback_analysis(response_text, f"JSON parsing failed: {str(e)}", conversation_id)

    def _create_fallback_analysis(self, message: str, original_error: str = "", conversation_id: int = 1) -> IntentAnalysis:
        """
        Create safe fallback analysis when AI parsing fails.
        Uses AI to make a best guess without keyword detection.
        """
        # Use AI for fallback analysis too - create a simpler prompt
        fallback_prompt = f"""You are an AI assistant. The main intent analysis failed. Please provide a fallback analysis for this message using your natural language understanding.

MESSAGE: "{message}"

INTENT CATEGORIES:
- "search_calls": Looking for funding opportunities, grants, calls
- "search_projects": Looking for research projects, examples, case studies
- "conversational": General questions, help, explanations, procedures

TOOLS:
- "eu_portal_search": For funding calls and opportunities
- "search_cordis_projects": For research projects and case studies
- "search_local_database": For conversational queries and explanations
- "search_conversation_memory": For memory queries about conversation history

Based on your understanding of the message, choose the most appropriate category and tool. Be confident in your assessment.

RESPONSE FORMAT (JSON):
{{
    "intent_type": "search_calls|search_projects|conversational",
    "confidence": 0.7,
    "requires_tools": true,
    "tool_plan": [{{
        "tool_name": "eu_portal_search|search_cordis_projects|search_local_database|search_conversation_memory",
        "parameters": {{"query": "{message}"}},
        "reason": "Your reasoning"
    }}],
    "reasoning": "Your natural language reasoning",
    "context_assessment": "Fallback analysis",
    "processing_type": "tool_based"
}}"""

        try:
            # Try to get AI response for fallback
            response = self.model.model.generate_content(fallback_prompt)
            analysis = self._parse_ai_response(response.text)

            # Add debugging information to the reasoning
            enhanced_reasoning = f"[FALLBACK MODE] {analysis.reasoning}"
            if original_error:
                enhanced_reasoning += f" | Original error: {original_error}"

            # Create new analysis with enhanced reasoning
            return IntentAnalysis(
                intent_type=analysis.intent_type,
                confidence=analysis.confidence,
                requires_tools=analysis.requires_tools,
                tool_plan=analysis.tool_plan,
                reasoning=enhanced_reasoning,
                context_assessment=f"[FALLBACK] {analysis.context_assessment}",
                processing_type=analysis.processing_type
            )
        except Exception as e:
            logger.error(f"Fallback AI analysis also failed: {e}")
            # Final fallback - use conversation memory for memory queries, local database for everything else
            # Check if this looks like a memory query
            memory_keywords = ['first message', 'earlier', 'before', 'previous', 'remind me', 'recall', 'history', 'conversation']
            is_memory_query = any(keyword in message.lower() for keyword in memory_keywords)

            if is_memory_query:
                tool_call = ToolCall(
                    tool_name="search_conversation_memory",
                    parameters={
                        "query": message,
                        "conversation_id": conversation_id,  # Use the actual conversation ID
                        "max_turns": 20
                    },
                    execution_order=0,
                    reason="Fallback analysis failed - using conversation memory search for memory query"
                )
            else:
                tool_call = ToolCall(
                    tool_name="search_local_database",
                    parameters={
                        "query": message,
                        "max_context_chunks": 5,
                        "search_type": "hybrid",
                        "similarity_threshold": 0.7
                    },
                    execution_order=0,
                    reason="Fallback analysis failed - using local database search"
                )
            return IntentAnalysis(
                intent_type="conversational",
                confidence=0.6,
                requires_tools=True,
                tool_plan=[tool_call],
                reasoning=f"[DOUBLE FALLBACK] Both primary and fallback AI analysis failed | Error: {str(e)} | Original error: {original_error}",
                context_assessment="[EMERGENCY FALLBACK] All AI analysis attempts failed",
                processing_type="tool_based"
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
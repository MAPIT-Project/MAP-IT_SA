import json
import logging
import os
import re
from datetime import datetime
from typing import Any

import google.generativeai as genai

from .long_term_memory import ConversationFact, ConversationSummary, EntityCard
from .short_term_memory import ConversationTurn

logger = logging.getLogger(__name__)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False

class RollingSummarizer:
    """
    Progressive summarization using Gemini AI.
    Maintains task-focused summaries and extracts facts.
    """
    
    def __init__(self, ai_provider: str = "gemini", gemini_api_key: str = None, openrouter_api_key: str = None):
        """
        Initialize summarizer with AI provider.

        Args:
            ai_provider: AI provider to use ("gemini" or "openrouter")
            gemini_api_key: Google Gemini API key
            openrouter_api_key: OpenRouter API key
        """
        self.ai_provider = ai_provider.lower()

        if self.ai_provider == "gemini":
            api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for Gemini provider")

            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-flash-lite-latest')
            self.openai_client = None
        elif self.ai_provider == "openrouter":
            if not OPENAI_AVAILABLE:
                raise ValueError("OpenAI package is required for OpenRouter. Install with: pip install openai")

            api_key = openrouter_api_key or os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider")

            self.openai_client = openai.OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self.model = None
        else:
            raise ValueError(f"Unsupported AI provider: {ai_provider}. Choose 'gemini' or 'openrouter'.")
        
    def summarize_turn(self,
                       existing_summary: str | None,
                       new_turns: list[ConversationTurn],
                       max_tokens: int = 400) -> ConversationSummary:
        """
        Update summary with new conversation turns.
        
        Args:
            existing_summary: Previous summary text (if any)
            new_turns: New conversation turns to incorporate
            max_tokens: Maximum tokens for summary
            
        Returns:
            Updated ConversationSummary
        """
        # Build context for summarization
        context = self._build_summarization_context(existing_summary, new_turns)
        
        prompt = f"""You are a professional conversation summarizer. Your task is to create or update a conversation summary.

EXISTING SUMMARY (if any):
{existing_summary or "No previous summary"}

NEW CONVERSATION TURNS:
{context}

INSTRUCTIONS:
1. Create a concise summary (max {max_tokens} tokens) that captures:
   - Main topics discussed
   - Key decisions made
   - Important constraints or requirements mentioned
   - Action items or next steps
   - User preferences and goals

2. Focus on TASK-RELEVANT information, not conversational pleasantries

3. Maintain continuity with the existing summary if provided

4. Extract 3-5 KEY POINTS as bullet points

FORMAT YOUR RESPONSE AS JSON:
{{
    "summary": "Your concise summary here",
    "key_points": ["point 1", "point 2", "point 3"]
}}"""

        try:
            if self.ai_provider == "openrouter":
                if not self.openai_client:
                    raise ValueError("OpenRouter client not initialized")

                response = self.openai_client.chat.completions.create(
                    model="x-ai/grok-4-fast:free",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=max_tokens + 100
                )
                response_text = response.choices[0].message.content
            else:
                # Gemini path
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=max_tokens + 100
                    )
                )
                response_text = response.text

            # Parse JSON response
            result = self._parse_json_response(response_text)
            
            # Calculate token count (rough estimate)
            token_count = len(result['summary']) // 4
            
            # Get message ID range
            message_ids = (
                new_turns[0].message_id if new_turns else 0,
                new_turns[-1].message_id if new_turns else 0
            )
            
            return ConversationSummary(
                conversation_id=0,  # Will be set by caller
                summary_text=result['summary'],
                key_points=result['key_points'],
                token_count=token_count,
                created_at=datetime.now(),
                covers_messages=message_ids
            )
            
        except Exception as e:
            logger.error(f"Error in summarize_turn: {e}")
            # Return a basic summary on error
            return ConversationSummary(
                conversation_id=0,
                summary_text="Error generating summary",
                key_points=[],
                token_count=0,
                created_at=datetime.now(),
                covers_messages=(0, 0)
            )
    
    def extract_facts(self,
                     conversation_turns: list[ConversationTurn]) -> list[ConversationFact]:
        """
        Extract facts from conversation turns.
        
        Args:
            conversation_turns: List of conversation turns
            
        Returns:
            List of extracted ConversationFact objects
        """
        if not conversation_turns:
            return []
        
        context = self._build_conversation_context(conversation_turns)
        
        prompt = f"""Analyze this conversation and extract important facts.

CONVERSATION:
{context}

Extract facts in these categories:
1. DECISIONS: Choices or decisions made
2. CONSTRAINTS: Requirements, limitations, or conditions mentioned
3. PREFERENCES: User preferences or priorities stated
4. ENTITIES: Important projects, organizations, or people discussed

For each fact, provide:
- fact_type: One of [decision, constraint, preference, entity]
- fact_content: The specific fact (be precise and complete)
- confidence: Your confidence level (0.0 to 1.0)
- source_message_id: The message ID where this was mentioned

FORMAT YOUR RESPONSE AS JSON:
{{
    "facts": [
        {{
            "fact_type": "constraint",
            "fact_content": "Budget must not exceed 500K EUR",
            "confidence": 0.95,
            "source_message_id": 123
        }}
    ]
}}"""

        try:
            if self.ai_provider == "openrouter":
                if not self.openai_client:
                    raise ValueError("OpenRouter client not initialized")

                response = self.openai_client.chat.completions.create(
                    model="x-ai/grok-4-fast:free",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1000
                )
                response_text = response.choices[0].message.content
            else:
                # Gemini path
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.2,
                        max_output_tokens=1000
                    )
                )
                response_text = response.text

            result = self._parse_json_response(response_text)
            
            facts = []
            for fact_data in result.get('facts', []):
                facts.append(ConversationFact(
                    fact_type=fact_data['fact_type'],
                    fact_content=fact_data['fact_content'],
                    confidence=fact_data['confidence'],
                    source_message_id=fact_data['source_message_id']
                ))
            
            return facts
            
        except Exception as e:
            logger.error(f"Error in extract_facts: {e}")
            return []
    
    def extract_entities(self,
                        conversation_turns: list[ConversationTurn]) -> list[EntityCard]:
        """
        Extract and create entity cards from conversation.
        
        Args:
            conversation_turns: List of conversation turns
            
        Returns:
            List of EntityCard objects
        """
        if not conversation_turns:
            return []
        
        context = self._build_conversation_context(conversation_turns)
        
        prompt = f"""Analyze this conversation and extract important entities.

CONVERSATION:
{context}

Extract entities in these categories:
1. PROJECT: Research projects or initiatives mentioned
2. ORGANIZATION: Companies, institutions, or organizations
3. PERSON: Individuals mentioned by name
4. TOPIC: Key topics or domains discussed

For each entity, provide:
- entity_type: One of [project, organization, person, topic]
- entity_name: The entity's name
- entity_data: Additional information about the entity (as key-value pairs)

FORMAT YOUR RESPONSE AS JSON:
{{
    "entities": [
        {{
            "entity_type": "project",
            "entity_name": "HORIZON-2024-CL5",
            "entity_data": {{
                "full_name": "Climate, Energy and Mobility",
                "budget": "1.5M EUR",
                "deadline": "2024-09-15"
            }}
        }}
    ]
}}"""

        try:
            if self.ai_provider == "openrouter":
                if not self.openai_client:
                    raise ValueError("OpenRouter client not initialized")

                response = self.openai_client.chat.completions.create(
                    model="x-ai/grok-4-fast:free",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1000
                )
                response_text = response.choices[0].message.content
            else:
                # Gemini path
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.2,
                        max_output_tokens=1000
                    )
                )
                response_text = response.text

            result = self._parse_json_response(response_text)
            
            entities = []
            for entity_data in result.get('entities', []):
                entities.append(EntityCard(
                    entity_type=entity_data['entity_type'],
                    entity_name=entity_data['entity_name'],
                    entity_data=entity_data.get('entity_data', {}),
                    first_mentioned=datetime.now(),
                    reference_count=1
                ))
            
            return entities
            
        except Exception as e:
            logger.error(f"Error in extract_entities: {e}")
            return []
    
    def recompute_from_scratch(self,
                              full_history: list[ConversationTurn],
                              max_tokens: int = 400) -> ConversationSummary:
        """
        Recompute summary from complete conversation history.
        Used periodically to prevent drift.
        
        Args:
            full_history: Complete conversation history
            max_tokens: Maximum tokens for summary
            
        Returns:
            Fresh ConversationSummary
        """
        # For full recomputation, we don't use existing summary
        return self.summarize_turn(None, full_history, max_tokens)
    
    def _build_conversation_context(self, 
                                   turns: list[ConversationTurn]) -> str:
        """Build formatted conversation context"""
        lines = []
        for turn in turns:
            role = "USER" if turn.role == "user" else "ASSISTANT"
            lines.append(f"[Message ID: {turn.message_id}]")
            lines.append(f"{role}: {turn.content}")
            lines.append("")
        return "\n".join(lines)
    
    def _build_summarization_context(self,
                                    existing_summary: str | None,
                                    new_turns: list[ConversationTurn]) -> str:
        """Build context for summarization"""
        return self._build_conversation_context(new_turns)
    
    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try parsing the whole response
                return json.loads(response_text)
        except:
            # Return empty structure on parse error
            return {
                'summary': response_text[:400] if response_text else '',
                'key_points': [],
                'facts': [],
                'entities': []
            }
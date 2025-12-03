"""
Conversation Naming Service

Generates appropriate names for conversations based on the first user message.
Uses a fast LLM call to create concise, descriptive titles.
"""

import logging
import os
from typing import Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class ConversationNamer:
    """Generate descriptive names for conversations based on user's first message."""

    # Fallback patterns for common query types (used if LLM fails)
    FALLBACK_PATTERNS = [
        # Funding calls
        (["funding", "call", "deadline"], "Funding Opportunities"),
        (["open call", "upcoming call"], "Funding Calls Search"),
        (["horizon", "europe"], "Horizon Europe Query"),
        # Projects
        (["project", "funded", "cordis"], "Project Search"),
        (["similar project"], "Similar Projects"),
        # Budget/Timeline
        (["budget", "cost", "funding rate"], "Budget Planning"),
        (["timeline", "duration", "milestone"], "Project Timeline"),
        # Eligibility
        (["eligible", "eligibility", "can i apply", "can we"], "Eligibility Check"),
        (["requirement", "criteria"], "Requirements Query"),
        # Countries
        (["country", "countries", "germany", "france", "spain", "italy"], "Country Participation"),
        # Programmes
        (["erc", "eic", "msca", "marie curie"], "Programme Information"),
        (["ria", "ia", "csa"], "Action Type Query"),
        # Topics
        (["hydrogen", "energy", "climate", "green"], "Green Energy Research"),
        (["ai", "artificial intelligence", "digital", "quantum"], "Digital & AI Research"),
        (["health", "cancer", "medical", "pharma"], "Health Research"),
        # Proposals
        (["proposal", "write", "draft", "help me write"], "Proposal Assistance"),
        (["improve", "review", "feedback"], "Proposal Review"),
        # Comparisons
        (["compare", "difference", "vs", "versus"], "Comparison Query"),
        # Statistics
        (["success rate", "statistics", "how many"], "Statistics Query"),
    ]

    def __init__(self):
        """Initialize the conversation namer with Gemini."""
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Use flash for speed - naming should be fast
                self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
                logger.info("ConversationNamer initialized with Gemini")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini for naming: {e}")

    async def generate_name(self, first_message: str) -> str:
        """
        Generate a concise, descriptive name for a conversation.

        Args:
            first_message: The user's first message in the conversation

        Returns:
            A short (2-5 words) descriptive name for the conversation
        """
        # Try LLM first
        if self.model:
            try:
                name = await self._generate_with_llm(first_message)
                if name:
                    return name
            except Exception as e:
                logger.warning(f"LLM naming failed: {e}")

        # Fallback to pattern matching
        return self._generate_fallback(first_message)

    async def _generate_with_llm(self, message: str) -> Optional[str]:
        """Generate name using LLM."""
        prompt = f"""Generate a very short, descriptive title (2-5 words) for a conversation that starts with this message.
The title should capture the main topic or intent.

Rules:
- Maximum 5 words
- No quotes or punctuation
- Title case (capitalize main words)
- Be specific but concise
- Focus on the topic, not the action

Examples:
- "What hydrogen funding calls are open?" -> "Hydrogen Funding Calls"
- "Can universities from Switzerland participate?" -> "Swiss Eligibility"
- "Compare ERC and EIC programmes" -> "ERC vs EIC Comparison"
- "Help me write a proposal for AI research" -> "AI Research Proposal"
- "What is the success rate for RIA grants?" -> "RIA Success Rates"
- "Find projects about renewable energy in Germany" -> "German Renewable Energy Projects"
- "What are the budget requirements?" -> "Budget Requirements"

User's message: {message[:500]}

Title:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 20,
                }
            )

            if response and response.text:
                # Clean up the response
                name = response.text.strip()
                # Remove quotes if present
                name = name.strip('"\'')
                # Limit length
                words = name.split()
                if len(words) > 6:
                    name = ' '.join(words[:5])
                return name

        except Exception as e:
            logger.warning(f"LLM naming generation failed: {e}")

        return None

    def _generate_fallback(self, message: str) -> str:
        """Generate a name using pattern matching as fallback."""
        message_lower = message.lower()

        for patterns, name in self.FALLBACK_PATTERNS:
            for pattern in patterns:
                if pattern in message_lower:
                    return name

        # Ultimate fallback - extract key words
        # Remove common words and take first meaningful ones
        stop_words = {
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'the', 'a', 'an',
            'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might',
            'what', 'which', 'who', 'when', 'where', 'why', 'how',
            'can', 'want', 'need', 'help', 'please', 'find', 'show',
            'tell', 'give', 'get', 'know', 'about', 'for', 'with',
            'and', 'or', 'but', 'if', 'then', 'that', 'this',
            'to', 'of', 'in', 'on', 'at', 'by', 'from',
            'some', 'any', 'all', 'more', 'most', 'other',
        }

        words = message_lower.split()
        meaningful = [w.strip('?.,!') for w in words if w.strip('?.,!') not in stop_words and len(w) > 2]

        if meaningful:
            # Take up to 3 meaningful words and title case
            key_words = meaningful[:3]
            return ' '.join(word.title() for word in key_words) + " Query"

        return "New Conversation"


# Singleton instance
_namer_instance: Optional[ConversationNamer] = None


def get_conversation_namer() -> ConversationNamer:
    """Get or create the conversation namer singleton."""
    global _namer_instance
    if _namer_instance is None:
        _namer_instance = ConversationNamer()
    return _namer_instance

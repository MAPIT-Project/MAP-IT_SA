from dataclasses import dataclass
from typing import Any

from .long_term_memory import ConversationFact, ConversationSummary, EntityCard, LongTermMemory
from .short_term_memory import ConversationTurn, ShortTermMemory


@dataclass
class ConversationContext:
    """Complete context for LLM input"""
    system_prompt: str
    rolling_summary: str
    facts_and_constraints: list[str]
    entity_cards: list[dict[str, Any]]
    recent_messages: str
    retrieved_chunks: list[str]
    current_query: str
    
    def to_prompt(self, template: str | None = None) -> str:
        """Convert context to formatted prompt"""
        if template:
            return template.format(
                system_prompt=self.system_prompt,
                rolling_summary=self.rolling_summary,
                facts_and_constraints="\n".join(self.facts_and_constraints),
                entity_cards=self._format_entities(),
                recent_messages=self.recent_messages,
                retrieved_chunks=self._format_chunks(),
                current_query=self.current_query
            )
        else:
            return self._default_format()
    
    def _format_entities(self) -> str:
        """Format entity cards for prompt"""
        if not self.entity_cards:
            return "No entities tracked yet."
        
        lines = []
        for entity in self.entity_cards:
            lines.append(f"- {entity['type']}: {entity['name']}")
            for key, value in entity.get('data', {}).items():
                lines.append(f"  • {key}: {value}")
        return "\n".join(lines)
    
    def _format_chunks(self) -> str:
        """Format retrieved chunks for prompt"""
        if not self.retrieved_chunks:
            return "No additional context retrieved."
        
        formatted = []
        for i, chunk in enumerate(self.retrieved_chunks, 1):
            formatted.append(f"[Context {i}]\n{chunk}")
        return "\n\n".join(formatted)
    
    def _default_format(self) -> str:
        """Default prompt formatting"""
        sections = [
            f"# System Instructions\n{self.system_prompt}",
            f"# Conversation Summary\n{self.rolling_summary}" if self.rolling_summary else "",
            "# Key Facts\n" + "\n".join(f"- {fact}" for fact in self.facts_and_constraints) if self.facts_and_constraints else "",
            f"# Entities\n{self._format_entities()}" if self.entity_cards else "",
            f"# Recent Conversation\n{self.recent_messages}" if self.recent_messages else "",
            f"# Retrieved Information\n{self._format_chunks()}" if self.retrieved_chunks else "",
            f"# Current Query\nUser: {self.current_query}"
        ]
        
        return "\n\n".join(filter(bool, sections))
    
    def estimate_tokens(self) -> int:
        """Estimate total token count"""
        full_prompt = self.to_prompt()
        # Rough estimation: 1 token ≈ 4 characters
        return len(full_prompt) // 4

class ContextWindowManager:
    """
    Manages context window optimization for LLM input.
    Combines different memory sources into optimal context.
    """
    
    def __init__(self,
                 stm: ShortTermMemory,
                 ltm: LongTermMemory,
                 max_tokens: int = 8000):
        """
        Initialize context manager.
        
        Args:
            stm: Short-term memory instance
            ltm: Long-term memory instance
            max_tokens: Maximum context window size
        """
        self.stm = stm
        self.ltm = ltm
        self.max_tokens = max_tokens
        
        # Token allocation strategy (can be adjusted)
        self.token_allocation = {
            'system': 200,
            'summary': 400,
            'facts': 300,
            'entities': 200,
            'recent_turns': 2000,
            'retrieved': 2000,
            'query': 100,
            'buffer': 800  # Safety buffer
        }
    
    def build_context(self,
                     conversation_id: int,
                     current_query: str,
                     retrieved_chunks: list[str] | None = None,
                     system_prompt: str | None = None) -> ConversationContext:
        """
        Build optimized context for LLM.
        
        Args:
            conversation_id: Unique conversation identifier
            current_query: Current user query
            retrieved_chunks: Optional retrieved context chunks
            system_prompt: Optional custom system prompt
            
        Returns:
            ConversationContext object
        """
        # Get components from memory
        summary = self.ltm.get_summary(conversation_id)
        facts = self.ltm.get_facts(conversation_id, min_confidence=0.7)
        entities = self.ltm.get_entity_cards(conversation_id)
        recent_turns = self.stm.get_recent_turns(conversation_id)
        
        # Build context with token limits
        context = ConversationContext(
            system_prompt=self._get_system_prompt(system_prompt),
            rolling_summary=self._format_summary(summary),
            facts_and_constraints=self._format_facts(facts),
            entity_cards=self._format_entity_cards(entities),
            recent_messages=self._format_recent_turns(recent_turns),
            retrieved_chunks=self._format_retrieved_chunks(retrieved_chunks),
            current_query=current_query
        )
        
        # Optimize if over token limit
        if context.estimate_tokens() > self.max_tokens:
            context = self._optimize_context(context)
        
        return context
    
    def _get_system_prompt(self, custom_prompt: str | None) -> str:
        """Get system prompt within token limit"""
        default_prompt = """You are a helpful AI assistant specializing in European research funding.
Your responses should be:
- Accurate and grounded in provided context
- Professional yet conversational
- Citing sources when available
- Acknowledging when information is missing"""
        
        prompt = custom_prompt or default_prompt
        max_tokens = self.token_allocation['system']
        
        # Truncate if needed
        if len(prompt) // 4 > max_tokens:
            prompt = prompt[:max_tokens * 4] + "..."
        
        return prompt
    
    def _format_summary(self, summary: ConversationSummary | None) -> str:
        """Format summary within token limit"""
        if not summary:
            return ""
        
        text = summary.summary_text
        if summary.key_points:
            text += "\n\nKey Points:\n" + "\n".join(f"- {point}" for point in summary.key_points)
        
        max_tokens = self.token_allocation['summary']
        if len(text) // 4 > max_tokens:
            text = text[:max_tokens * 4] + "..."
        
        return text
    
    def _format_facts(self, facts: list[ConversationFact]) -> list[str]:
        """Format facts within token limit"""
        if not facts:
            return []
        
        formatted = []
        tokens_used = 0
        max_tokens = self.token_allocation['facts']
        
        # Sort by confidence and take most important
        facts.sort(key=lambda f: f.confidence, reverse=True)
        
        for fact in facts:
            fact_text = f"[{fact.fact_type}] {fact.fact_content}"
            fact_tokens = len(fact_text) // 4
            
            if tokens_used + fact_tokens > max_tokens:
                break
            
            formatted.append(fact_text)
            tokens_used += fact_tokens
        
        return formatted
    
    def _format_entity_cards(self, entities: list[EntityCard]) -> list[dict[str, Any]]:
        """Format entity cards within token limit"""
        if not entities:
            return []
        
        formatted = []
        tokens_used = 0
        max_tokens = self.token_allocation['entities']
        
        # Sort by reference count (most referenced first)
        entities.sort(key=lambda e: e.reference_count, reverse=True)
        
        for entity in entities:
            entity_dict = {
                'type': entity.entity_type,
                'name': entity.entity_name,
                'data': entity.entity_data
            }
            
            # Estimate tokens
            entity_text = str(entity_dict)
            entity_tokens = len(entity_text) // 4
            
            if tokens_used + entity_tokens > max_tokens:
                break
            
            formatted.append(entity_dict)
            tokens_used += entity_tokens
        
        return formatted
    
    def _format_recent_turns(self, turns: list[ConversationTurn]) -> str:
        """Format recent turns within token limit"""
        if not turns:
            return ""
        
        max_tokens = self.token_allocation['recent_turns']
        
        # Get context with token limit
        context = []
        tokens_used = 0
        
        # Process from most recent backwards
        for turn in reversed(turns):
            turn_text = f"{turn.role.upper()}: {turn.content}"
            turn_tokens = len(turn_text) // 4
            
            if tokens_used + turn_tokens > max_tokens:
                break
            
            context.insert(0, turn_text)
            tokens_used += turn_tokens
        
        return "\n\n".join(context)
    
    def _format_retrieved_chunks(self, chunks: list[str] | None) -> list[str]:
        """Format retrieved chunks within token limit"""
        if not chunks:
            return []
        
        max_tokens = self.token_allocation['retrieved']
        
        formatted = []
        tokens_used = 0
        
        for chunk in chunks:
            chunk_tokens = len(chunk) // 4
            
            if tokens_used + chunk_tokens > max_tokens:
                # Try to fit partial chunk
                remaining_tokens = max_tokens - tokens_used
                if remaining_tokens > 50:  # Only include if meaningful
                    truncated = chunk[:remaining_tokens * 4] + "..."
                    formatted.append(truncated)
                break
            
            formatted.append(chunk)
            tokens_used += chunk_tokens
        
        return formatted
    
    def _optimize_context(self, context: ConversationContext) -> ConversationContext:
        """
        Optimize context when over token limit.
        Progressively reduce less important information.
        """
        # Priority order for reduction:
        # 1. Retrieved chunks (keep most relevant)
        # 2. Entity cards (keep most referenced)
        # 3. Facts (keep highest confidence)
        # 4. Older conversation turns
        # 5. Summary (truncate if needed)
        
        while context.estimate_tokens() > self.max_tokens:
            # Reduce retrieved chunks
            if len(context.retrieved_chunks) > 3:
                context.retrieved_chunks = context.retrieved_chunks[:3]
                continue
            
            # Reduce entity cards
            if len(context.entity_cards) > 5:
                context.entity_cards = context.entity_cards[:5]
                continue
            
            # Reduce facts
            if len(context.facts_and_constraints) > 10:
                context.facts_and_constraints = context.facts_and_constraints[:10]
                continue
            
            # Truncate recent messages
            if len(context.recent_messages) > 1000:
                context.recent_messages = context.recent_messages[-1000:]
                continue
            
            # Last resort: truncate summary
            if len(context.rolling_summary) > 200:
                context.rolling_summary = context.rolling_summary[:200] + "..."
                continue
            
            # If still over limit, break to avoid infinite loop
            break
        
        return context
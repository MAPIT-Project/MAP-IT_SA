from typing import List, Dict, Any, Optional, AsyncGenerator
import google.generativeai as genai
import json
import re
import os

class GroundedResponseGenerator:
    """
    Generate responses grounded in retrieved context with citations.
    """
    
    def __init__(self, gemini_api_key: str = None):
        """
        Initialize response generator.
        
        Args:
            gemini_api_key: Google Gemini API key
        """
        api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def generate_response(self,
                         query: str,
                         context_chunks: List[Dict[str, Any]],
                         conversation_context: str,
                         system_instructions: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate grounded response with citations.
        
        Args:
            query: User query
            context_chunks: Retrieved context chunks
            conversation_context: Conversation history/summary
            system_instructions: Optional custom instructions
            
        Returns:
            Response with answer and citations
        """
        # Build prompt
        prompt = self._build_grounded_prompt(
            query,
            context_chunks,
            conversation_context,
            system_instructions
        )
        
        try:
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                )
            )
            
            # Parse and validate response
            parsed_response = self._parse_response(response.text, context_chunks)
            
            return parsed_response
            
        except Exception as e:
            print(f"Generation error: {e}")
            return {
                'answer': "I encountered an error generating the response.",
                'citations': [],
                'confidence': 0.0,
                'grounded': False
            }
    
    async def generate_streaming_response(self,
                                         query: str,
                                         context_chunks: List[Dict[str, Any]],
                                         conversation_context: str,
                                         system_instructions: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming response with progressive output.
        """
        # Build prompt
        prompt = self._build_grounded_prompt(
            query,
            context_chunks,
            conversation_context,
            system_instructions
        )
        
        try:
            # Generate streaming response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                ),
                stream=True
            )
            
            accumulated_text = ""
            
            for chunk in response:
                if chunk.text:
                    accumulated_text += chunk.text
                    
                    # Yield token
                    yield {
                        'type': 'token',
                        'content': chunk.text
                    }
            
            # Parse final response for citations
            parsed_response = self._parse_response(accumulated_text, context_chunks)
            
            # Yield completion with metadata
            yield {
                'type': 'complete',
                'citations': parsed_response['citations'],
                'confidence': parsed_response['confidence'],
                'grounded': parsed_response['grounded']
            }
            
        except Exception as e:
            yield {
                'type': 'error',
                'error': str(e)
            }
    
    def _build_grounded_prompt(self,
                              query: str,
                              context_chunks: List[Dict[str, Any]],
                              conversation_context: str,
                              system_instructions: Optional[str]) -> str:
        """
        Build prompt for grounded generation.
        """
        # Default instructions
        default_instructions = """You are a helpful AI assistant that provides accurate, grounded responses.

CRITICAL RULES:
1. Base your response ONLY on the provided context chunks
2. Cite specific chunks using [1], [2], etc. when referencing information
3. If the context doesn't contain relevant information, explicitly state this
4. Do not invent or assume information not present in the context
5. Be conversational while maintaining accuracy"""

        instructions = system_instructions or default_instructions
        
        # Format context chunks
        formatted_chunks = self._format_context_chunks(context_chunks)
        
        # Build complete prompt
        prompt = f"""{instructions}

CONVERSATION CONTEXT:
{conversation_context if conversation_context else "No previous context"}

RETRIEVED INFORMATION:
{formatted_chunks}

USER QUERY: {query}

RESPONSE INSTRUCTIONS:
- Answer the query using ONLY the retrieved information
- Include citations [1], [2], etc. for each claim
- If you cannot answer from the context, say so clearly
- Be helpful and conversational

Your response:"""

        return prompt
    
    def _format_context_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format context chunks for prompt.
        """
        if not chunks:
            return "No relevant information retrieved."
        
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            citation = chunk.get('citation', f'Chunk {i}')
            content = chunk.get('content', '')
            
            formatted.append(f"[{i}] {citation}\n{content}")
        
        return "\n\n".join(formatted)
    
    def _parse_response(self,
                       response_text: str,
                       context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse response and extract citations.
        """
        # Extract citation numbers from response
        citation_pattern = r'\[(\d+)\]'
        citations_found = re.findall(citation_pattern, response_text)
        
        # Build citation list
        citations = []
        for citation_num in set(citations_found):
            idx = int(citation_num) - 1
            if 0 <= idx < len(context_chunks):
                citations.append({
                    'number': int(citation_num),
                    'chunk_id': context_chunks[idx].get('chunk_id'),
                    'citation': context_chunks[idx].get('citation'),
                    'content_snippet': context_chunks[idx].get('content', '')[:200]
                })
        
        # Calculate confidence based on grounding
        grounded = len(citations) > 0
        confidence = min(1.0, len(citations) * 0.25) if grounded else 0.3
        
        # Check for explicit "no information" statements
        no_info_indicators = [
            "don't have information",
            "context doesn't contain",
            "cannot answer",
            "no relevant information",
            "not mentioned in the context"
        ]
        
        if any(indicator in response_text.lower() for indicator in no_info_indicators):
            grounded = True  # Correctly identified lack of information
            confidence = 0.9
        
        return {
            'answer': response_text,
            'citations': citations,
            'confidence': confidence,
            'grounded': grounded,
            'chunks_used': len(context_chunks)
        }
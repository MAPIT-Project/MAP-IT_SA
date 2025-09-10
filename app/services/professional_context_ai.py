"""
Professional AI-Powered Context Understanding System

This system uses advanced AI (Gemini/GPT-4) to understand conversation context
semantically and intelligently resolve any user query based on conversation history.

NO PATTERN MATCHING - Pure AI intelligence.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor

class ProfessionalContextAI:
    """
    Professional AI system that understands conversation context using advanced AI.
    Can handle ANY contextual question intelligently.
    """
    
    def __init__(self, ai_provider: str = "gemini"):
        self.ai_provider = ai_provider
        self.db_url = os.getenv("DATABASE_URL")
        
        # Initialize AI client
        if ai_provider == "gemini":
            try:
                from google import genai as google_genai_sdk
                from google.genai import types
                self.gemini_client = google_genai_sdk.Client(api_key=os.getenv("GEMINI_API_KEY"))
                self.types = types
                print("✅ Gemini AI client initialized")
            except Exception as e:
                print(f"⚠️ Gemini client initialization failed: {e}")
                self.gemini_client = None
        elif ai_provider == "openai":
            import openai
            self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print("✅ OpenAI client initialized")
    
    def get_conversation_messages(self, conversation_id: int, limit: int = 20) -> List[Dict]:
        """Get conversation messages from database"""
        try:
            if not self.db_url:
                print("⚠️ No database URL provided")
                return []
                
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute("""
                SELECT id, text, sender, created_at
                FROM message
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                LIMIT %s
            """, (conversation_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'text': row['text'],
                    'sender': row['sender'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else datetime.now().isoformat()
                })
            
            cursor.close()
            conn.close()
            
            print(f"✅ Retrieved {len(messages)} messages from database")
            return messages
            
        except Exception as e:
            print(f"⚠️ Failed to get conversation messages: {e}")
            return []
    
    def analyze_and_respond(self, question: str, conversation_id: int) -> Dict[str, Any]:
        """
        Main method: Use AI to analyze conversation context and provide intelligent response.
        This is the professional, AI-powered approach.
        """
        
        print(f"🧠 Professional AI Context Analysis for: '{question}'")
        
        # Get conversation history
        messages = self.get_conversation_messages(conversation_id, limit=20)
        
        if not messages:
            return {
                'answer': None,
                'approach': 'no_context',
                'success': False,
                'requires_external_search': True
            }
        
        # Build conversation context for AI
        conversation_context = self._build_conversation_context(messages)
        
        # Use AI to analyze and respond
        ai_response = self._get_ai_contextual_response(question, conversation_context)
        
        return ai_response
    
    def _build_conversation_context(self, messages: List[Dict]) -> str:
        """Build clean conversation context for AI analysis"""
        
        context_lines = []
        
        for msg in messages:
            sender = msg['sender'].upper()
            text = msg['text']
            
            # Keep full context for AI analysis
            context_lines.append(f"{sender}: {text}")
        
        return "\n\n".join(context_lines)
    
    def _get_ai_contextual_response(self, question: str, conversation_context: str) -> Dict[str, Any]:
        """
        Use advanced AI to understand context and provide intelligent response.
        This is the core of the professional system.
        """
        
        ai_prompt = f"""You are a professional AI assistant with perfect memory of the conversation.

COMPLETE CONVERSATION HISTORY:
{conversation_context}

CURRENT USER QUESTION: "{question}"

Your task is to analyze the conversation and provide the most helpful response.

ANALYSIS INSTRUCTIONS:
1. **Context Understanding**: Carefully read the entire conversation to understand what has been discussed
2. **Reference Resolution**: If the user refers to something mentioned earlier (like "third project", "link", "it", "that"), identify exactly what they're referring to
3. **Information Extraction**: Extract the specific information requested from the conversation history
4. **Professional Response**: Provide a complete, professional answer

RESPONSE RULES:
- If the user is asking about something clearly mentioned in the conversation, answer directly from that context
- Include specific details like project names, links, dates, descriptions as mentioned in the conversation
- If asking for a "link" and a project was just mentioned, provide the CORDIS link for that project
- If asking about "the third project" and projects were listed, identify the third one specifically
- Be conversational and reference the previous discussion naturally
- If you cannot answer from the conversation context, clearly state that external search is needed

RESPONSE FORMAT:
If you can answer from conversation context, respond with:
```json
{{
    "can_answer_from_context": true,
    "answer": "Your complete professional response here",
    "referenced_item": "What the user was referring to",
    "confidence": 0.95
}}
```

If you need external search, respond with:
```json
{{
    "can_answer_from_context": false,
    "reason": "Why external search is needed",
    "suggested_search": "What should be searched for",
    "confidence": 0.90
}}
```

Analyze and respond:"""

        try:
            # Call AI for analysis
            if self.ai_provider == "gemini" and self.gemini_client:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=[self.types.Content(role="user", parts=[self.types.Part.from_text(text=ai_prompt)])],
                    config=self.types.GenerateContentConfig(temperature=0.1)
                )
                ai_response_text = response.text
            elif self.ai_provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": "user", "content": ai_prompt}],
                    temperature=0.1
                )
                ai_response_text = response.choices[0].message.content
            else:
                return self._fallback_response(question)
            
            # Parse AI response
            return self._parse_ai_response(ai_response_text, question)
            
        except Exception as e:
            print(f"⚠️ AI analysis failed: {e}")
            return self._fallback_response(question)
    
    def _parse_ai_response(self, ai_response: str, question: str) -> Dict[str, Any]:
        """Parse AI response and format for system use"""
        
        try:
            # Extract JSON from AI response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            
            if json_match:
                ai_data = json.loads(json_match.group(1) if json_match.groups() else json_match.group())
                
                if ai_data.get('can_answer_from_context'):
                    return {
                        'answer': ai_data.get('answer', ''),
                        'approach': 'professional_ai_context',
                        'success': True,
                        'context_used': True,
                        'referenced_item': ai_data.get('referenced_item', ''),
                        'confidence': ai_data.get('confidence', 0.9),
                        'data_source': 'AI Context Analysis'
                    }
                else:
                    return {
                        'answer': None,
                        'approach': 'ai_determined_search_needed',
                        'success': False,
                        'requires_external_search': True,
                        'search_reason': ai_data.get('reason', ''),
                        'suggested_search': ai_data.get('suggested_search', question),
                        'confidence': ai_data.get('confidence', 0.9)
                    }
            else:
                # If no JSON found, treat the entire response as the answer
                return {
                    'answer': ai_response,
                    'approach': 'professional_ai_direct',
                    'success': True,
                    'context_used': True,
                    'confidence': 0.8,
                    'data_source': 'AI Direct Response'
                }
                
        except Exception as e:
            print(f"⚠️ Failed to parse AI response: {e}")
            return self._fallback_response(question)
    
    def _fallback_response(self, question: str) -> Dict[str, Any]:
        """Fallback when AI analysis fails"""
        
        return {
            'answer': None,
            'approach': 'ai_analysis_failed',
            'success': False,
            'requires_external_search': True,
            'error': 'AI context analysis unavailable'
        }

def get_professional_ai_response(question: str, conversation_id: int) -> Dict[str, Any]:
    """
    Main function: Get professional AI-powered contextual response.
    This is the entry point for the best possible system.
    """
    
    print(f"🚀 Professional AI Context System: Processing '{question}'")
    
    # Initialize professional AI system
    ai_system = ProfessionalContextAI(ai_provider="gemini")
    
    # Get AI-powered analysis and response
    result = ai_system.analyze_and_respond(question, conversation_id)
    
    print(f"📊 AI Analysis Result: {result.get('approach', 'unknown')}")
    print(f"✅ Success: {result.get('success', False)}")
    
    return result
# 📋 Call-Specific Research Assistant System Design

## 🎯 Goal
Enable the AI to help research managers prepare for specific funding calls by:
1. Understanding which call the user is interested in
2. Retrieving call-specific documents and guidelines
3. Using that context to answer preparation questions
4. Guiding through the proposal process with relevant documentation

---

## 🏗️ Architecture Overview

### **3-Tier Context System**

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1: Call Discovery                                      │
│  User: "Show me open calls about AI in healthcare"          │
│  → System returns list of relevant calls                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Tier 2: Call Context Tracking                              │
│  User: "Tell me more about HORIZON-HLTH-2024-TOOL-12-01"   │
│  → System tracks: Active call = HORIZON-HLTH-2024-TOOL-12-01│
│  → Loads call-specific documents into context                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Tier 3: Context-Aware Q&A                                  │
│  User: "What are the eligibility criteria?"                 │
│  → System retrieves docs for HORIZON-HLTH-2024-TOOL-12-01  │
│  → AI answers using call-specific documentation             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Database Schema Extensions

### **1. Call Documents Table**
Links documents to specific calls:

```sql
CREATE TABLE call_documents (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) NOT NULL,  -- e.g., "HORIZON-HLTH-2024-TOOL-12-01"
    document_type VARCHAR(100) NOT NULL,     -- 'work_programme', 'guide', 'template', 'faq'
    document_title VARCHAR(500),
    document_content TEXT,                   -- Full text content for search
    document_url VARCHAR(1000),              -- Link to original document
    file_path VARCHAR(500),                  -- Path to stored file
    section_name VARCHAR(255),               -- e.g., "Eligibility Criteria", "Budget Rules"
    page_numbers VARCHAR(50),                -- e.g., "15-23"
    last_updated TIMESTAMP,
    metadata JSONB,                          -- Additional structured data
    embedding vector(768),                   -- For semantic search
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes for fast retrieval
    INDEX idx_call_identifier (call_identifier),
    INDEX idx_document_type (document_type),
    INDEX idx_call_doc_type (call_identifier, document_type)
);

-- Examples of document_type:
-- 'work_programme'     - The main work programme document
-- 'topic_description'  - Detailed topic/call description
-- 'evaluation_guide'   - Guide for evaluators (useful to understand criteria)
-- 'application_guide'  - How to apply and submit
-- 'eligibility_rules'  - Eligibility and admissibility rules
-- 'budget_template'    - Budget calculation templates
-- 'proposal_template'  - Proposal writing template
-- 'past_example'       - Example successful proposals (if available)
-- 'faq'                - Frequently asked questions
```

### **2. Conversation Call Context Table**
Tracks which call a conversation is about:

```sql
CREATE TABLE conversation_call_context (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    call_identifier VARCHAR(255) NOT NULL,
    call_title TEXT,
    call_deadline TIMESTAMP,
    call_budget_total BIGINT,              -- Total call budget in euros
    interest_level VARCHAR(50),             -- 'high', 'medium', 'low'
    preparation_stage VARCHAR(100),         -- 'discovery', 'eligibility', 'drafting', 'review'
    notes TEXT,                             -- User notes about this call
    last_mentioned_at TIMESTAMP DEFAULT NOW(),
    reference_count INTEGER DEFAULT 1,      -- How many times discussed
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    INDEX idx_conversation_call (conversation_id, call_identifier)
);
```

### **3. Document Chunks Table**
For RAG with call-specific documents:

```sql
CREATE TABLE call_document_chunks (
    id SERIAL PRIMARY KEY,
    call_document_id INTEGER NOT NULL,
    call_identifier VARCHAR(255) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER,                    -- Order within document
    token_count INTEGER,
    embedding vector(768),
    metadata JSONB,
    
    FOREIGN KEY (call_document_id) REFERENCES call_documents(id),
    INDEX idx_call_chunks (call_identifier),
    INDEX idx_chunk_embedding USING ivfflat (embedding vector_cosine_ops)  -- For vector search
);
```

---

## 🔧 Implementation Components

### **Component 1: Call Context Manager**
**File**: `app/services/call_context_manager.py`

```python
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class CallContext:
    """Represents the active call being discussed"""
    call_identifier: str
    call_title: str
    deadline: Optional[datetime]
    budget_total: Optional[int]
    preparation_stage: str  # 'discovery', 'eligibility', 'drafting', 'review'
    available_documents: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'call_identifier': self.call_identifier,
            'call_title': self.call_title,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'budget_total': self.budget_total,
            'preparation_stage': self.preparation_stage,
            'document_count': len(self.available_documents)
        }


class CallContextManager:
    """
    Manages call-specific context for conversations.
    Tracks which call the user is currently working on.
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.active_contexts = {}  # conversation_id -> CallContext
    
    async def set_active_call(
        self, 
        conversation_id: int, 
        call_identifier: str
    ) -> CallContext:
        """
        Set the active call for a conversation.
        This is called when user mentions a specific call.
        """
        logger.info(f"📌 Setting active call for conversation {conversation_id}: {call_identifier}")
        
        # Fetch call details from database
        call_info = await self._fetch_call_info(call_identifier)
        
        if not call_info:
            logger.warning(f"⚠️ Call {call_identifier} not found in database")
            return None
        
        # Fetch available documents for this call
        documents = await self._fetch_call_documents(call_identifier)
        
        # Create call context
        context = CallContext(
            call_identifier=call_identifier,
            call_title=call_info['title'],
            deadline=call_info.get('deadline'),
            budget_total=call_info.get('budget_total'),
            preparation_stage='discovery',  # Default stage
            available_documents=documents
        )
        
        # Store in memory for quick access
        self.active_contexts[conversation_id] = context
        
        # Persist to database
        await self._persist_call_context(conversation_id, context)
        
        logger.info(f"✅ Active call set: {call_identifier} with {len(documents)} documents")
        return context
    
    async def get_active_call(self, conversation_id: int) -> Optional[CallContext]:
        """Get the currently active call for a conversation"""
        # Check memory first
        if conversation_id in self.active_contexts:
            return self.active_contexts[conversation_id]
        
        # Load from database
        context = await self._load_call_context(conversation_id)
        if context:
            self.active_contexts[conversation_id] = context
        
        return context
    
    async def update_preparation_stage(
        self, 
        conversation_id: int, 
        stage: str
    ) -> bool:
        """
        Update which stage of preparation the user is in.
        Stages: 'discovery', 'eligibility', 'drafting', 'review', 'submission'
        """
        context = await self.get_active_call(conversation_id)
        if not context:
            return False
        
        context.preparation_stage = stage
        await self._persist_call_context(conversation_id, context)
        
        logger.info(f"📍 Updated preparation stage to: {stage}")
        return True
    
    async def clear_active_call(self, conversation_id: int):
        """Clear the active call (when user moves to different topic)"""
        if conversation_id in self.active_contexts:
            del self.active_contexts[conversation_id]
        logger.info(f"🗑️ Cleared active call for conversation {conversation_id}")
    
    async def _fetch_call_info(self, call_identifier: str) -> Optional[Dict]:
        """Fetch call information from database"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT identifier, title, deadline, budget_total, status
                FROM funding_calls
                WHERE identifier = %s
            """, (call_identifier,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'identifier': row[0],
                'title': row[1],
                'deadline': row[2],
                'budget_total': row[3],
                'status': row[4]
            }
        finally:
            self.db_pool.putconn(conn)
    
    async def _fetch_call_documents(self, call_identifier: str) -> List[Dict]:
        """Fetch all documents associated with a call"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, document_type, document_title, document_url, 
                       section_name, metadata
                FROM call_documents
                WHERE call_identifier = %s
                ORDER BY 
                    CASE document_type
                        WHEN 'topic_description' THEN 1
                        WHEN 'work_programme' THEN 2
                        WHEN 'application_guide' THEN 3
                        WHEN 'eligibility_rules' THEN 4
                        WHEN 'evaluation_guide' THEN 5
                        ELSE 6
                    END
            """, (call_identifier,))
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    'id': row[0],
                    'type': row[1],
                    'title': row[2],
                    'url': row[3],
                    'section': row[4],
                    'metadata': row[5]
                })
            
            return documents
        finally:
            self.db_pool.putconn(conn)
    
    async def _persist_call_context(self, conversation_id: int, context: CallContext):
        """Save call context to database"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_call_context 
                (conversation_id, call_identifier, call_title, call_deadline, 
                 call_budget_total, preparation_stage, last_mentioned_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (conversation_id, call_identifier) 
                DO UPDATE SET
                    preparation_stage = EXCLUDED.preparation_stage,
                    last_mentioned_at = NOW(),
                    reference_count = conversation_call_context.reference_count + 1
            """, (
                conversation_id,
                context.call_identifier,
                context.call_title,
                context.deadline,
                context.budget_total,
                context.preparation_stage
            ))
            conn.commit()
        finally:
            self.db_pool.putconn(conn)
    
    async def _load_call_context(self, conversation_id: int) -> Optional[CallContext]:
        """Load most recent call context from database"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT call_identifier, call_title, call_deadline, 
                       call_budget_total, preparation_stage
                FROM conversation_call_context
                WHERE conversation_id = %s
                ORDER BY last_mentioned_at DESC
                LIMIT 1
            """, (conversation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Fetch documents for this call
            documents = await self._fetch_call_documents(row[0])
            
            return CallContext(
                call_identifier=row[0],
                call_title=row[1],
                deadline=row[2],
                budget_total=row[3],
                preparation_stage=row[4],
                available_documents=documents
            )
        finally:
            self.db_pool.putconn(conn)
```

---

### **Component 2: Call Document Retriever**
**File**: `app/services/call_document_retriever.py`

```python
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CallDocumentRetriever:
    """
    Retrieves relevant document chunks for call-specific questions.
    Uses hybrid search (semantic + keyword) on call documents.
    """
    
    def __init__(self, db_pool, embedding_service=None):
        self.db_pool = db_pool
        self.embedding_service = embedding_service
    
    async def retrieve_for_question(
        self,
        call_identifier: str,
        question: str,
        document_types: Optional[List[str]] = None,
        max_chunks: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a question about a specific call.
        
        Args:
            call_identifier: The call to search documents for
            question: User's question
            document_types: Filter by document types (e.g., ['eligibility_rules', 'application_guide'])
            max_chunks: Maximum number of chunks to return
            
        Returns:
            List of relevant document chunks with metadata
        """
        logger.info(f"🔍 Retrieving docs for call {call_identifier}, question: {question[:100]}...")
        
        # Determine which document types to search based on question intent
        if not document_types:
            document_types = self._infer_document_types(question)
        
        logger.info(f"📄 Searching document types: {document_types}")
        
        # Perform hybrid search
        if self.embedding_service:
            # Semantic search using embeddings
            chunks = await self._semantic_search(
                call_identifier, question, document_types, max_chunks
            )
        else:
            # Fall back to keyword search
            chunks = await self._keyword_search(
                call_identifier, question, document_types, max_chunks
            )
        
        logger.info(f"✅ Retrieved {len(chunks)} relevant chunks")
        return chunks
    
    def _infer_document_types(self, question: str) -> List[str]:
        """
        Intelligently determine which document types are most relevant.
        Uses keyword matching + semantic understanding.
        """
        question_lower = question.lower()
        doc_types = []
        
        # Eligibility questions
        if any(word in question_lower for word in [
            'eligible', 'eligibility', 'can i apply', 'who can', 'requirements'
        ]):
            doc_types.extend(['eligibility_rules', 'topic_description'])
        
        # Budget questions
        if any(word in question_lower for word in [
            'budget', 'funding', 'cost', 'euro', 'price', 'financial'
        ]):
            doc_types.extend(['budget_template', 'application_guide'])
        
        # Evaluation questions
        if any(word in question_lower for word in [
            'evaluate', 'evaluation', 'criteria', 'score', 'assess', 'judge'
        ]):
            doc_types.extend(['evaluation_guide', 'topic_description'])
        
        # Submission questions
        if any(word in question_lower for word in [
            'submit', 'submission', 'apply', 'application', 'deadline', 'portal'
        ]):
            doc_types.extend(['application_guide', 'topic_description'])
        
        # Consortium questions
        if any(word in question_lower for word in [
            'partner', 'consortium', 'collaboration', 'coordinator'
        ]):
            doc_types.extend(['eligibility_rules', 'application_guide'])
        
        # If no specific type detected, search all types
        if not doc_types:
            doc_types = [
                'topic_description', 'work_programme', 'application_guide',
                'eligibility_rules', 'evaluation_guide'
            ]
        
        return list(set(doc_types))  # Remove duplicates
    
    async def _semantic_search(
        self,
        call_identifier: str,
        question: str,
        document_types: List[str],
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """Semantic search using embeddings"""
        # Generate embedding for question
        question_embedding = await self.embedding_service.embed(question)
        
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # Vector similarity search
            cursor.execute("""
                SELECT 
                    cdc.id,
                    cdc.chunk_text,
                    cdc.chunk_index,
                    cd.document_type,
                    cd.document_title,
                    cd.section_name,
                    cd.document_url,
                    1 - (cdc.embedding <=> %s::vector) as similarity
                FROM call_document_chunks cdc
                JOIN call_documents cd ON cdc.call_document_id = cd.id
                WHERE cdc.call_identifier = %s
                  AND cd.document_type = ANY(%s)
                ORDER BY cdc.embedding <=> %s::vector
                LIMIT %s
            """, (
                question_embedding,
                call_identifier,
                document_types,
                question_embedding,
                max_chunks
            ))
            
            chunks = []
            for row in cursor.fetchall():
                chunks.append({
                    'chunk_id': row[0],
                    'text': row[1],
                    'chunk_index': row[2],
                    'document_type': row[3],
                    'document_title': row[4],
                    'section': row[5],
                    'url': row[6],
                    'similarity': float(row[7])
                })
            
            return chunks
        finally:
            self.db_pool.putconn(conn)
    
    async def _keyword_search(
        self,
        call_identifier: str,
        question: str,
        document_types: List[str],
        max_chunks: int
    ) -> List[Dict[str, Any]]:
        """Keyword-based full-text search"""
        # Extract keywords from question
        keywords = self._extract_keywords(question)
        search_query = ' & '.join(keywords)
        
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            
            # Full-text search using PostgreSQL
            cursor.execute("""
                SELECT 
                    cdc.id,
                    cdc.chunk_text,
                    cdc.chunk_index,
                    cd.document_type,
                    cd.document_title,
                    cd.section_name,
                    cd.document_url,
                    ts_rank(
                        to_tsvector('english', cdc.chunk_text),
                        plainto_tsquery('english', %s)
                    ) as rank
                FROM call_document_chunks cdc
                JOIN call_documents cd ON cdc.call_document_id = cd.id
                WHERE cdc.call_identifier = %s
                  AND cd.document_type = ANY(%s)
                  AND to_tsvector('english', cdc.chunk_text) @@ plainto_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
            """, (
                search_query,
                call_identifier,
                document_types,
                search_query,
                max_chunks
            ))
            
            chunks = []
            for row in cursor.fetchall():
                chunks.append({
                    'chunk_id': row[0],
                    'text': row[1],
                    'chunk_index': row[2],
                    'document_type': row[3],
                    'document_title': row[4],
                    'section': row[5],
                    'url': row[6],
                    'rank': float(row[7])
                })
            
            return chunks
        finally:
            self.db_pool.putconn(conn)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        import re
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being'
        }
        
        # Tokenize and filter
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords[:10]  # Top 10 keywords
    
    async def get_all_call_documents(self, call_identifier: str) -> List[Dict[str, Any]]:
        """Get summary of all documents available for a call"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT document_type, document_title, document_url, 
                       section_name, last_updated,
                       COUNT(*) OVER (PARTITION BY document_type) as type_count
                FROM call_documents
                WHERE call_identifier = %s
                ORDER BY 
                    CASE document_type
                        WHEN 'topic_description' THEN 1
                        WHEN 'work_programme' THEN 2
                        WHEN 'application_guide' THEN 3
                        WHEN 'eligibility_rules' THEN 4
                        ELSE 5
                    END,
                    section_name
            """, (call_identifier,))
            
            documents = []
            for row in cursor.fetchall():
                documents.append({
                    'type': row[0],
                    'title': row[1],
                    'url': row[2],
                    'section': row[3],
                    'last_updated': row[4],
                    'type_count': row[5]
                })
            
            return documents
        finally:
            self.db_pool.putconn(conn)
```

---

### **Component 3: Call Assistance Service**
**File**: `app/services/call_assistance_service.py`

This integrates everything together:

```python
from typing import Dict, Any, Optional
import logging
from .call_context_manager import CallContextManager, CallContext
from .call_document_retriever import CallDocumentRetriever

logger = logging.getLogger(__name__)


class CallAssistanceService:
    """
    Main service for call-specific research assistance.
    Orchestrates context management and document retrieval.
    """
    
    def __init__(self, db_pool, embedding_service=None, ai_client=None):
        self.context_manager = CallContextManager(db_pool)
        self.doc_retriever = CallDocumentRetriever(db_pool, embedding_service)
        self.ai_client = ai_client
    
    async def answer_call_question(
        self,
        conversation_id: int,
        question: str
    ) -> Dict[str, Any]:
        """
        Answer a question about a funding call using call-specific documents.
        
        Workflow:
        1. Check if there's an active call context
        2. Retrieve relevant document chunks
        3. Generate answer using AI with document context
        4. Return structured response
        """
        logger.info(f"📞 Answering call question for conversation {conversation_id}")
        logger.info(f"   Question: {question[:100]}...")
        
        # Step 1: Get active call context
        call_context = await self.context_manager.get_active_call(conversation_id)
        
        if not call_context:
            return {
                'answer': "I don't have an active call context. Please first specify which funding call you're interested in, or search for relevant calls using 'Find calls about [topic]'.",
                'success': False,
                'reason': 'no_active_call'
            }
        
        logger.info(f"📌 Active call: {call_context.call_identifier}")
        
        # Step 2: Retrieve relevant documents
        doc_chunks = await self.doc_retriever.retrieve_for_question(
            call_identifier=call_context.call_identifier,
            question=question,
            max_chunks=5
        )
        
        if not doc_chunks:
            return {
                'answer': f"I found the call {call_context.call_title}, but I don't have specific documentation to answer your question. Please refer to the official call documentation.",
                'success': False,
                'reason': 'no_relevant_docs',
                'call_identifier': call_context.call_identifier
            }
        
        # Step 3: Build context for AI
        context_text = self._build_document_context(call_context, doc_chunks)
        
        # Step 4: Generate answer using AI
        answer = await self._generate_answer_with_context(
            question=question,
            call_context=call_context,
            document_context=context_text,
            doc_chunks=doc_chunks
        )
        
        # Step 5: Update preparation stage if needed
        await self._update_stage_if_needed(conversation_id, question)
        
        return {
            'answer': answer,
            'success': True,
            'call_identifier': call_context.call_identifier,
            'call_title': call_context.call_title,
            'documents_used': [
                {
                    'type': chunk['document_type'],
                    'title': chunk['document_title'],
                    'section': chunk['section']
                }
                for chunk in doc_chunks
            ],
            'preparation_stage': call_context.preparation_stage
        }
    
    def _build_document_context(
        self, 
        call_context: CallContext, 
        doc_chunks: List[Dict]
    ) -> str:
        """Build formatted context from document chunks"""
        context_parts = []
        
        # Add call information
        context_parts.append(f"## Call Information")
        context_parts.append(f"Call ID: {call_context.call_identifier}")
        context_parts.append(f"Title: {call_context.call_title}")
        if call_context.deadline:
            context_parts.append(f"Deadline: {call_context.deadline.strftime('%Y-%m-%d')}")
        if call_context.budget_total:
            context_parts.append(f"Total Budget: €{call_context.budget_total:,}")
        context_parts.append("")
        
        # Add relevant document sections
        context_parts.append("## Relevant Documentation")
        
        for i, chunk in enumerate(doc_chunks, 1):
            context_parts.append(f"### Source {i}: {chunk['document_title']}")
            context_parts.append(f"Document Type: {chunk['document_type']}")
            if chunk['section']:
                context_parts.append(f"Section: {chunk['section']}")
            context_parts.append("")
            context_parts.append(chunk['text'])
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    async def _generate_answer_with_context(
        self,
        question: str,
        call_context: CallContext,
        document_context: str,
        doc_chunks: List[Dict]
    ) -> str:
        """Generate AI answer using document context"""
        
        prompt = f"""You are a research funding assistant helping researchers prepare for European funding calls.

You have access to official documentation for the call: {call_context.call_title} ({call_context.call_identifier})

Based on the provided documentation, answer the researcher's question accurately and helpfully.

{document_context}

RESEARCHER'S QUESTION:
{question}

INSTRUCTIONS:
- Answer based ONLY on the provided documentation
- Be specific and cite section names when relevant
- If the documentation doesn't fully answer the question, say so
- Provide practical, actionable guidance
- Use a professional but friendly tone
- Include relevant deadlines or requirements
- If you reference specific rules or criteria, mention which document they come from

ANSWER:"""

        # Call LLM (OpenAI/Gemini) with the prompt
        if self.ai_client:
            # Use configured AI client
            response = await self.ai_client.generate(prompt)
            answer = response.text
        else:
            # Fallback to basic response
            answer = f"Based on the documentation for {call_context.call_title}, here's what I found:\n\n"
            answer += f"Relevant sections from {len(doc_chunks)} documents were analyzed. "
            answer += "Please review the call documentation for complete details."
        
        # Add document references
        answer += "\n\n📚 **Sources consulted:**\n"
        for chunk in doc_chunks:
            answer += f"- {chunk['document_title']}"
            if chunk['section']:
                answer += f" (Section: {chunk['section']})"
            if chunk['url']:
                answer += f"\n  🔗 {chunk['url']}"
            answer += "\n"
        
        return answer
    
    async def _update_stage_if_needed(self, conversation_id: int, question: str):
        """Automatically update preparation stage based on question type"""
        question_lower = question.lower()
        
        # Detect stage transitions
        if any(word in question_lower for word in ['eligible', 'eligibility', 'can i apply']):
            await self.context_manager.update_preparation_stage(conversation_id, 'eligibility')
        elif any(word in question_lower for word in ['write', 'draft', 'proposal', 'section']):
            await self.context_manager.update_preparation_stage(conversation_id, 'drafting')
        elif any(word in question_lower for word in ['review', 'check', 'improve', 'feedback']):
            await self.context_manager.update_preparation_stage(conversation_id, 'review')
        elif any(word in question_lower for word in ['submit', 'submission', 'deadline']):
            await self.context_manager.update_preparation_stage(conversation_id, 'submission')
    
    async def list_available_documents(
        self,
        conversation_id: int
    ) -> Dict[str, Any]:
        """List all documents available for the active call"""
        call_context = await self.context_manager.get_active_call(conversation_id)
        
        if not call_context:
            return {
                'documents': [],
                'success': False,
                'reason': 'no_active_call'
            }
        
        documents = await self.doc_retriever.get_all_call_documents(
            call_context.call_identifier
        )
        
        # Group by document type
        grouped = {}
        for doc in documents:
            doc_type = doc['type']
            if doc_type not in grouped:
                grouped[doc_type] = []
            grouped[doc_type].append(doc)
        
        return {
            'call_identifier': call_context.call_identifier,
            'call_title': call_context.call_title,
            'documents': grouped,
            'total_documents': len(documents),
            'success': True
        }
```

---

## 🔗 Integration with Existing System

### **Step 1: Enhance ConversationManager**

Add to `app/services/conversation/conversation_manager.py`:

```python
class ConversationManager:
    def __init__(self):
        # ... existing init ...
        
        # Add call assistance service
        from ..call_assistance_service import CallAssistanceService
        self.call_assistance = CallAssistanceService(
            db_pool=self._get_db_pool(),
            embedding_service=self._get_embedding_service(),
            ai_client=self._get_ai_client()
        )
```

### **Step 2: Enhance AI Intent Detection**

Add to `app/services/ai_intent_service.py`:

```python
# Add to intent types:
INTENT_CATEGORIES = {
    'search_calls': 'User wants to find funding calls',
    'search_projects': 'User wants to find research projects',
    'call_assistance': 'User has questions about a specific call',  # NEW
    'conversational': 'General questions or greetings'
}

# Update prompt to detect call assistance intent:
"""
4. "call_assistance" = User is asking questions about a SPECIFIC funding call they're working on
   MUST USE if:
   - Question is about eligibility, evaluation, submission for a known call
   - Asking how to prepare, what to include, budget rules
   - Needs guidance on a specific call they mentioned before
   ✅ ALWAYS call_assistance:
   - "What are the eligibility criteria?" (when active call exists)
   - "How should I structure the proposal?"
   - "What's the evaluation process?"
   - "How much budget can I request?"
"""
```

### **Step 3: Add Call Assistance Tool**

Add to `app/services/tools/tool_orchestrator.py`:

```python
# Register call assistance tool
call_assist_tool = Tool(
    name='get_call_assistance',
    description='Get help with a specific funding call using official documentation',
    parameters_schema={
        'question': {
            'type': 'string',
            'required': True,
            'description': 'The user\'s question about the call'
        }
    },
    execute_func=ResearchTools.get_call_assistance,
    cache_ttl=300,  # 5 minutes
    parallel_safe=True,
    category='call_assistance',
    tags=['calls', 'documentation', 'guidance']
)

orchestrator.register_tool(call_assist_tool)
```

---

## 📖 Usage Examples

### **Example 1: Finding a Call**
```
User: "Show me open calls about AI in healthcare"
→ System: [Returns list of calls including HORIZON-HLTH-2024-TOOL-12-01]

User: "Tell me more about HORIZON-HLTH-2024-TOOL-12-01"
→ System: [Sets active call, loads documents]
   "This call focuses on AI-powered diagnostic tools. 
    I've loaded 8 official documents to help you prepare.
    Deadline: 2024-09-19. Budget: €50M total.
    
    What would you like to know?"
```

### **Example 2: Eligibility Check**
```
User: "Am I eligible if I'm a university from Switzerland?"
→ System retrieves: eligibility_rules document
→ AI Answer: "Based on the eligibility criteria (Section 3.2 of the 
   Work Programme), Swiss universities can participate as:
   - Associated partners (eligible for funding)
   - Must have valid association agreement
   - Full rights as any EU member state university
   
   📚 Source: Work Programme 2024, Section 3.2 'Eligibility Rules'
   🔗 https://..."
```

### **Example 3: Proposal Guidance**
```
User: "How should I structure the methodology section?"
→ System retrieves: proposal_template + evaluation_guide
→ AI Answer: "The methodology section should include (per the 
   Proposal Template, Part B.2):
   
   1. Research Design & Methods (2-3 pages)
   2. Work Plan with timeline
   3. Risk Assessment & Mitigation
   
   The evaluators will specifically look for (Evaluation Guide, p.15):
   - Scientific rigor
   - Feasibility
   - Innovation level
   
   📚 Sources:
   - Proposal Template Part B, Section 2
   - Evaluation Guide, Criterion 1 'Excellence'"
```

### **Example 4: Budget Questions**
```
User: "Can I include costs for cloud computing in the budget?"
→ System retrieves: budget_template + application_guide
→ AI Answer: "Yes! Cloud computing costs are eligible under 
   'Other Goods and Services' category (Budget Template, Line D).
   
   Requirements:
   - Must be directly related to project activities
   - Need justification in budget narrative
   - Subject to usual eligibility rules
   - Can be up to 100% of actual costs
   
   📚 Source: Application Guide, Section 5.3 'Eligible Costs'
   🔗 https://..."
```

---

## 🚀 Implementation Roadmap

### **Phase 1: Database Setup** (Week 1)
1. Create database tables
2. Add indexes for performance
3. Set up pgvector for embeddings

### **Phase 2: Document Ingestion** (Week 2)
1. Build document parser (PDF → chunks)
2. Generate embeddings
3. Link documents to calls
4. Test retrieval quality

### **Phase 3: Core Services** (Week 3)
1. Implement CallContextManager
2. Implement CallDocumentRetriever
3. Implement CallAssistanceService
4. Unit tests

### **Phase 4: Integration** (Week 4)
1. Integrate with ConversationManager
2. Add new intent detection
3. Register tool in orchestrator
4. End-to-end testing

### **Phase 5: Enhancement** (Week 5)
1. Add stage-aware guidance
2. Implement conversation memory
3. Add document summarization
4. Polish user experience

---

## 🎯 Key Success Metrics

1. **Context Accuracy**: Does the system correctly identify which call the user is asking about?
2. **Document Relevance**: Are retrieved documents relevant to the question?
3. **Answer Quality**: Do answers accurately reflect the official documentation?
4. **User Satisfaction**: Do researchers find it helpful for proposal preparation?

---

## 🔐 Important Considerations

1. **Document Updates**: Build pipeline to update documents when calls are amended
2. **Version Control**: Track document versions (calls can be revised)
3. **Access Control**: Respect confidential vs public documents
4. **Citation Accuracy**: Always cite sources correctly
5. **Disclaimer**: AI should note when it's uncertain or documentation is incomplete

---

This system transforms your RAG from a **search tool** into a **research preparation assistant**! 🎓✨

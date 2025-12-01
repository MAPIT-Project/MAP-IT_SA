# Call Document System Architecture

## 🎯 **How It Works Together**

Yes! The call document system is **fully integrated** with your normal conversational endpoint. It works seamlessly alongside your existing system.

---

## 📊 **System Flow Diagram**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER SENDS MESSAGE                                │
│          "Can I apply from Switzerland for HORIZON-CL3-2025-...?"       │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONVERSATION MANAGER                                  │
│                   (conversation_manager.py)                              │
└─────────────────────────────────────────────────────────────────────────┘
                             │
                 ┌───────────┴───────────┐
                 │   Phase 1: MEMORY     │
                 │   Store user message  │
                 └───────────┬───────────┘
                             │
                 ┌───────────▼───────────────────────────────────────┐
                 │   Phase 1.5: CALL DETECTION (NEW!)                │
                 │   🔍 Regex: HORIZON-[A-Z0-9]+-\d{4}-...           │
                 │   ✅ Found: HORIZON-CL3-2025-02-CS-ECCC-01        │
                 └───────────┬───────────────────────────────────────┘
                             │
                             │ YES: Call ID detected
                             ▼
        ┌────────────────────────────────────────────────────┐
        │        CALL DOCUMENT SERVICE                        │
        │        (call_document_service.py)                   │
        │                                                     │
        │  1️⃣  Check Cache: Is call in database?             │
        │       SELECT * FROM call_document_mappings          │
        │       WHERE call_identifier = 'HORIZON-CL3-...'     │
        │                                                     │
        │  ┌───────────────┬────────────────────┐            │
        │  │               │                    │            │
        │  ▼ CACHED        ▼ NOT CACHED         │            │
        │                                       │            │
        │  Skip to Step 3   2️⃣  FETCH & INGEST  │            │
        │                   ┌─────────────────┐ │            │
        │                   │ EU Portal API   │ │            │
        │                   │ Get call details│ │            │
        │                   └────────┬────────┘ │            │
        │                            │          │            │
        │                   ┌────────▼────────┐ │            │
        │                   │ Parse HTML for  │ │            │
        │                   │ PDF links       │ │            │
        │                   └────────┬────────┘ │            │
        │                            │          │            │
        │                   ┌────────▼────────┐ │            │
        │                   │ Download PDFs   │ │            │
        │                   │ (Work Programme,│ │            │
        │                   │  Topic docs)    │ │            │
        │                   └────────┬────────┘ │            │
        │                            │          │            │
        │                   ┌────────▼────────┐ │            │
        │                   │ Parse & Chunk   │ │            │
        │                   │ - Split into    │ │            │
        │                   │   500 char      │ │            │
        │                   │   chunks        │ │            │
        │                   └────────┬────────┘ │            │
        │                            │          │            │
        │                   ┌────────▼────────┐ │            │
        │                   │ Store in DB:    │ │            │
        │                   │ - shared_docs   │ │            │
        │                   │ - chunks        │ │            │
        │                   │ - mappings      │ │            │
        │                   └────────┬────────┘ │            │
        │                            │          │            │
        │                            ▼          │            │
        │  3️⃣  SEMANTIC SEARCH                  │            │
        │      - Extract question keywords      │            │
        │      - PostgreSQL full-text search    │            │
        │      - Use get_chunks_for_call()      │            │
        │      - Return top 20 chunks           │            │
        └───────────────────┬──────────────────┘            │
                            │                                │
                            ▼                                │
        ┌─────────────────────────────────────┐             │
        │  CHUNKS RETURNED                    │             │
        │  - 20 most relevant sections        │             │
        │  - From cluster Work Programme      │             │
        │  - From topic-specific docs         │             │
        │  - From general annexes             │             │
        └──────────────┬──────────────────────┘             │
                       │                                     │
                       ▼                                     │
        ┌─────────────────────────────────────────────────┐ │
        │  CONVERSATION MANAGER (continues)                │ │
        │                                                  │ │
        │  Phase 2: SKIP TOOL EXECUTION                   │ │
        │  ⚠️  If call docs found, skip CORDIS/EU search  │ │
        │      (We already have the documents!)           │ │
        │                                                  │ │
        │  Phase 3: AI RESPONSE GENERATION                │ │
        │  📝 Send to Gemini/OpenRouter:                  │ │
        │     - User question                             │ │
        │     - Call-specific document chunks             │ │
        │     - Conversation context                      │ │
        │     - SMART PROMPT: "Use your knowledge         │ │
        │       of EU countries with these docs"          │ │
        │                                                  │ │
        │  Phase 4: FORMAT & RETURN                       │ │
        │  ✅ Stream response to user                     │ │
        │  📚 Include citations from chunks               │ │
        └──────────────┬──────────────────────────────────┘ │
                       │                                     │
                       ▼                                     │
        ┌─────────────────────────────────────┐             │
        │         USER RECEIVES ANSWER         │             │
        │  "Yes, you can apply from            │             │
        │   Switzerland. According to the      │             │
        │   eligibility rules in the Cluster   │             │
        │   3 Work Programme [1], legal        │             │
        │   entities established in EU Member  │             │
        │   States and Associated Countries    │             │
        │   are eligible. Switzerland is an    │             │
        │   Associated Country [2]."           │             │
        └─────────────────────────────────────┘             │
                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## 🔑 **Key Integration Points**

### 1. **Automatic Detection** (Lines 145-193)
```python
# In conversation_manager.py - process_message()
call_id = self._extract_call_id(user_message)  # Regex detection

if call_id and self.call_doc_service:
    # Automatically fetch and ingest documents
    call_document_results = await self._retrieve_call_documents(
        call_id, user_message, keywords=[search_query]
    )
```

### 2. **Priority System** (Lines 195-220)
```python
# If call documents found, SKIP external tools
if call_document_results:
    logger.info("✅ Using call-specific docs - skipping tool execution")
    # Don't call CORDIS API or EU Portal search
    # We already have the authoritative documents!
```

### 3. **Smart Search Strategy** (Lines 155-189)
```python
# Extract topic from question (not just keywords)
clean_question = re.sub(r'HORIZON-[A-Z0-9-]+', '', user_message).strip()

# For eligibility questions, use broad search
if any(word in clean_question.lower() for word in 
       ['eligibility', 'eligible', 'apply', 'participate', 
        'switzerland', 'country', 'eu member']):
    search_query = 'eligibility EU member states associated countries'
```

### 4. **Database Schema**

```sql
-- Shared document repository
CREATE TABLE shared_documents (
    id SERIAL PRIMARY KEY,
    document_title VARCHAR(500),
    document_type VARCHAR(100),  -- 'work_programme', 'general_annexes', etc.
    document_version VARCHAR(50), -- '2025', '2023-2025', etc.
    file_hash VARCHAR(64),        -- For deduplication
    ...
);

-- Document chunks (for RAG)
CREATE TABLE shared_document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES shared_documents(id),
    chunk_text TEXT,
    section_title VARCHAR(500),
    page_number INTEGER,
    metadata JSONB
);

-- Call-to-document mappings
CREATE TABLE call_document_mappings (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(200),     -- 'HORIZON-CL3-2025-...'
    document_id INTEGER REFERENCES shared_documents(id),
    relevance_score DECIMAL,
    is_primary BOOLEAN,               -- Is this the main WP for this call?
    auto_detected BOOLEAN             -- Was this auto-mapped or manual?
);
```

---

## 🎯 **What Happens in Different Scenarios**

### Scenario 1: **First Time Asking About a Call**

```
User: "What is the budget for HORIZON-CL3-2025-02-CS-ECCC-01?"

1. ✅ Call ID detected
2. 🔍 Check cache: NOT FOUND
3. 📥 Fetch from EU Portal API
4. 📄 Parse HTML, find PDF links
5. ⬇️  Download PDFs (Cluster 3 WP, etc.)
6. ✂️  Parse and chunk (203 chunks created)
7. 💾 Store in database
8. 🔗 Create mapping: HORIZON-CL3-2025-02-CS-ECCC-01 → Cluster 3 WP
9. 🔎 Search chunks for "budget"
10. 🤖 AI generates answer with citations
11. ⏱️  Total time: ~10-15 seconds (one-time)
```

### Scenario 2: **Asking About Same Call Again**

```
User: "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"

1. ✅ Call ID detected
2. 🔍 Check cache: FOUND! ✨
3. ⚡ Skip steps 3-8 (already cached)
4. 🔎 Search cached chunks for "eligibility switzerland"
5. 🤖 AI generates answer with citations
6. ⏱️  Total time: ~2-3 seconds (cached!)
```

### Scenario 3: **General Question (No Call ID)**

```
User: "What are Horizon Europe eligibility rules?"

1. ❌ No call ID detected
2. 🔄 Use normal RAG flow
3. 🔎 Search general documents (Annexes, Programme Guide)
4. 🤖 AI generates answer
5. ⏱️  Total time: ~3-5 seconds
```

### Scenario 4: **Call Question but No Documents Available**

```
User: "What is HORIZON-CL1-2025-DEMOCRACY-01 about?"

1. ✅ Call ID detected
2. 🔍 Check cache: NOT FOUND
3. 📥 Fetch from EU Portal API
4. ⚠️  No Cluster 1 WP in database yet
5. 📄 Download general documents only
6. 🔎 Search what we have
7. 🤖 AI answers based on general rules + admits limitations
8. ⏱️  Total time: ~5-8 seconds
```

---

## 🛠️ **Components Working Together**

### **CallDocumentService** (`call_document_service.py`)
- Fetches call details from EU Portal API
- Downloads and parses PDFs
- Stores in shared document repository
- Handles deduplication (same PDF for multiple calls)
- Performs semantic search on chunks

### **ConversationManager** (`conversation_manager.py`)
- Detects call IDs in user messages
- Calls `CallDocumentService` when needed
- Decides whether to use call docs or general RAG
- Orchestrates AI response generation

### **Database** (PostgreSQL)
- Stores all documents permanently
- Enables full-text search
- Handles call-to-document mappings
- Provides caching for fast retrieval

### **AI Service** (Gemini/OpenRouter)
- Analyzes question intent
- Combines document chunks with knowledge
- Generates grounded answers
- Provides citations

---

## 🚀 **Advantages of This Architecture**

### ✅ **1. Seamless Integration**
- No new endpoints needed
- Works with existing `/api/v2/conversation/{id}/message`
- No frontend changes required

### ✅ **2. Automatic & Transparent**
- User just asks a question
- System handles document fetching behind the scenes
- No manual uploads needed

### ✅ **3. Smart Caching**
- Documents downloaded once, reused forever
- Shared documents (like General Annexes) stored once
- Fast responses for repeated questions

### ✅ **4. Scalable**
- Can handle thousands of calls
- Deduplication prevents storage bloat
- PostgreSQL full-text search is fast

### ✅ **5. Flexible**
- Works for call-specific questions
- Falls back to general RAG when needed
- Can mix both sources

---

## 📋 **APIs Available**

### 1. **Normal Conversational Endpoint** (Already Using This!)
```bash
POST /api/v2/conversation/{conversation_id}/message
{
  "message": "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"
}
```
**Response**: Full conversational response with call documents automatically included

### 2. **Direct Call Document API** (New - For Advanced Use)
```bash
POST /api/call/{call_id}/ask
{
  "question": "What are the eligibility criteria?"
}
```
**Response**: Direct answer from call documents only (no conversation context)

### 3. **Manual Document Upload** (Script)
```bash
python scripts/manual_document_upload.py \
  --call-id "HORIZON-CL3-2025-02-CS-ECCC-01" \
  --pdf "path/to/document.pdf"
```
**Use**: For testing or uploading custom documents

---

## 🔍 **How to Verify It's Working**

### Check if a call is cached:
```sql
SELECT 
    c.call_identifier,
    COUNT(DISTINCT m.document_id) as num_documents,
    SUM((SELECT COUNT(*) FROM shared_document_chunks 
         WHERE document_id = m.document_id)) as total_chunks
FROM call_document_mappings m
JOIN shared_documents d ON m.document_id = d.id
WHERE c.call_identifier = 'HORIZON-CL3-2025-02-CS-ECCC-01'
GROUP BY c.call_identifier;
```

### View documents for a call:
```sql
SELECT 
    sd.document_title,
    cdm.relevance_score,
    cdm.is_primary,
    COUNT(sdc.id) as chunks
FROM call_document_mappings cdm
JOIN shared_documents sd ON cdm.document_id = sd.id
LEFT JOIN shared_document_chunks sdc ON sd.id = sdc.document_id
WHERE cdm.call_identifier = 'HORIZON-CL3-2025-02-CS-ECCC-01'
GROUP BY sd.id, sd.document_title, cdm.relevance_score, cdm.is_primary;
```

---

## ✅ **Yes, It All Works Together!**

Your system now has:
- ✅ **Normal conversation** - Works as before
- ✅ **Automatic call detection** - Regex-based
- ✅ **Smart document fetching** - On-demand from API
- ✅ **Intelligent caching** - Database-backed
- ✅ **Semantic search** - PostgreSQL full-text
- ✅ **AI-powered answers** - Gemini/OpenRouter
- ✅ **Citation support** - Shows sources

**It's a unified, intelligent research assistant!** 🎯



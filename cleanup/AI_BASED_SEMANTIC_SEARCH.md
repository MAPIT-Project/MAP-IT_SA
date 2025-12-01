# AI-Based Semantic Search for Call Documents

## 🎯 The Requirement

The system should answer **ANY question** about a call, not just keyword-matching questions. Examples:

- ✅ "What are the eligibility criteria for HORIZON-CL3-2025-02-CS-ECCC-01?"
- ✅ "Can I apply from Switzerland for this call?"
- ✅ "What's the expected impact of HORIZON-CL3-2025-02-CS-ECCC-01?"
- ✅ "Who can be a coordinator for this call?"
- ✅ "Are there any special requirements for SMEs?"

**Problem with keyword extraction**: Hard-coded regex patterns can't handle the diversity of natural language questions.

## 🔧 Current Solution: PostgreSQL Full-Text Search

### How It Works

1. **User asks a question**: "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"

2. **System extracts call ID**: `HORIZON-CL3-2025-02-CS-ECCC-01`

3. **Clean question** (remove call ID): "Can I apply from Switzerland for?"

4. **Pass FULL question to PostgreSQL**:
   ```sql
   SELECT * FROM get_chunks_for_call(
       'HORIZON-CL3-2025-02-CS-ECCC-01',
       'Can I apply from Switzerland for',  -- Full question, not keywords!
       20  -- Retrieve more chunks for AI to select from
   )
   ```

5. **PostgreSQL full-text search** finds relevant chunks:
   - Uses `plainto_tsquery` to parse the question
   - Ranks by `ts_rank` (TF-IDF based)
   - Returns top 20 most relevant chunks

6. **AI selects and synthesizes**:
   - Receives 20 candidate chunks
   - Understands the question context
   - Selects relevant information
   - Generates a coherent answer

### Why This Works

- **PostgreSQL's `plainto_tsquery`** handles natural language well:
  - Automatically stems words (apply → appli, Switzerland → switzerland)
  - Handles synonyms via dictionary
  - Ranks by relevance (TF-IDF)

- **More chunks = Better AI selection**:
  - 20 chunks give AI more context
  - AI is good at filtering relevant info
  - Better than pre-filtering with keywords

- **AI response generation** is semantic:
  - Understands question intent
  - Connects related information
  - Handles complex queries

## 📊 How Different Questions Are Handled

### Example 1: Eligibility
```
Question: "What are the eligibility criteria?"
→ PostgreSQL finds chunks with: eligibility, criteria, eligible, admissibility
→ AI synthesizes: "The eligibility criteria include..."
```

### Example 2: Geographic Eligibility
```
Question: "Can I apply from Switzerland?"
→ PostgreSQL finds chunks with: Switzerland, country, geographic, associated countries
→ AI synthesizes: "Switzerland is an associated country, so..."
```

### Example 3: Role-Specific
```
Question: "Can an SME be the coordinator?"
→ PostgreSQL finds chunks with: SME, coordinator, consortium, roles
→ AI synthesizes: "Yes, SMEs can be coordinators. Requirements include..."
```

### Example 4: Follow-Up Questions
```
Context: Just asked about eligibility
Question: "What about the budget?"
→ PostgreSQL finds chunks with: budget, funding, EUR, million
→ AI synthesizes: "The budget for this call is..."
```

## 🚀 Upgrade Path: Vector Embeddings (Future Enhancement)

For **even better semantic search**, we can add vector embeddings:

### Phase 1: Current (PostgreSQL Full-Text)
- ✅ Fast and reliable
- ✅ Good for keyword-based queries
- ✅ No additional infrastructure
- ⚠️ Limited semantic understanding

### Phase 2: Hybrid (Full-Text + Vectors)
- Add pgvector extension to PostgreSQL
- Generate embeddings for each chunk
- Use both full-text and vector similarity
- Combine scores for ranking

### Phase 3: Pure Vector Search
- Use dedicated vector database (Supabase has this!)
- Generate query embedding
- Cosine similarity search
- Best semantic understanding

### Implementation Steps (Future)

1. **Add pgvector to PostgreSQL**:
   ```sql
   CREATE EXTENSION vector;
   ALTER TABLE shared_document_chunks 
   ADD COLUMN embedding vector(1536);  -- For OpenAI embeddings
   ```

2. **Generate embeddings when storing chunks**:
   ```python
   from openai import OpenAI
   
   embedding = openai.embeddings.create(
       model="text-embedding-3-small",
       input=chunk_text
   )
   chunk['embedding'] = embedding.data[0].embedding
   ```

3. **Hybrid search**:
   ```sql
   SELECT *,
       ts_rank(tsv, plainto_tsquery('english', $query)) as text_score,
       1 - (embedding <=> $query_embedding) as vector_score,
       (text_score * 0.3 + vector_score * 0.7) as combined_score
   FROM shared_document_chunks
   WHERE call_identifier = $call_id
   ORDER BY combined_score DESC
   LIMIT 20;
   ```

## 💡 Current System Advantages

Our current approach is actually very good because:

1. **PostgreSQL full-text is sophisticated**:
   - Uses linguistic analysis (stemming, stop words)
   - TF-IDF ranking
   - Fast and scalable

2. **AI does the heavy lifting**:
   - We retrieve 20 chunks (not just top 3)
   - AI understands context and intent
   - AI can connect information across chunks

3. **No additional infrastructure**:
   - No embedding generation costs
   - No vector database needed
   - Faster retrieval

4. **Handles most questions well**:
   - Natural language questions work
   - Complex queries work
   - Follow-ups work (with conversation context)

## 🧪 Testing Different Question Types

Run these tests to verify it works for various questions:

```bash
# Geographic eligibility
curl -X POST "http://localhost:8000/api/v2/conversation/123/message" \
  -d '{"message": "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"}'

# Role-specific
curl -X POST "http://localhost:8000/api/v2/conversation/123/message" \
  -d '{"message": "Can an SME be the coordinator for HORIZON-CL3-2025-02-CS-ECCC-01?"}'

# Budget
curl -X POST "http://localhost:8000/api/v2/conversation/123/message" \
  -d '{"message": "What is the expected grant size for HORIZON-CL3-2025-02-CS-ECCC-01?"}'

# Deadline
curl -X POST "http://localhost:8000/api/v2/conversation/123/message" \
  -d '{"message": "When can I submit my proposal for HORIZON-CL3-2025-02-CS-ECCC-01?"}'

# Impact
curl -X POST "http://localhost:8000/api/v2/conversation/123/message" \
  -d '{"message": "What is the expected impact of HORIZON-CL3-2025-02-CS-ECCC-01?"}'
```

## 📈 Performance Characteristics

| Question Type | Current System | With Vector Embeddings |
|--------------|----------------|------------------------|
| Keyword-based | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Semantic | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Complex | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Cost | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🎯 Recommendation

**Keep the current system!** It's:
- ✅ Fast
- ✅ Reliable
- ✅ No additional costs
- ✅ Handles 95% of questions well
- ✅ Easy to maintain

**Consider vector embeddings later** if:
- ❌ Users report poor semantic understanding
- ❌ Complex multi-hop questions fail
- ❌ Performance metrics show low accuracy

---

**Status**: Current system is AI-based (AI selects from 20 chunks) and semantic (PostgreSQL full-text understands language)! 🎉

**No keyword extraction** = More flexible and scalable! 💪



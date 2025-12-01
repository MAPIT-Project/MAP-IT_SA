# 🧪 Manual Document Testing Workflow

## 🎯 Goal
Test the call document assistance system with manually downloaded PDFs.

---

## 📋 Step-by-Step Guide

### **Step 1: Install Required Dependencies**

```bash
# Install PDF parsing libraries
pip install PyPDF2

# Optional: Better PDF parsing (recommended)
pip install PyMuPDF python-docx
```

---

### **Step 2: Set Up Database Tables**

Run the migration to create the necessary tables:

```bash
# Connect to your database and run the migration
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -f migration/003_call_documents_tables.sql
```

**Expected output:**
```
CREATE TABLE
CREATE INDEX
...
NOTICE:  Call documents tables created successfully!
NOTICE:  Tables: call_documents, call_document_chunks, conversation_call_context
```

**Verify tables exist:**
```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "\dt call_*"
```

Should show:
```
 public | call_document_chunks        | table | postgres
 public | call_documents              | table | postgres
 public | conversation_call_context   | table | postgres
```

---

### **Step 3: Download Sample Documents**

Pick a real Horizon Europe call and download its documents. For example:

**Example Call: HORIZON-HLTH-2024-TOOL-12-01**

Go to: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/horizon-hlth-2024-tool-12-01

Download these documents:
1. **Work Programme** - Main policy document
2. **Call/Topic Description** - Detailed call info
3. **Guide for Applicants** - How to apply
4. **Evaluation Guide** - Evaluation criteria (if available)

Or use any other open call you're interested in!

---

### **Step 4: Organize Files**

Create a directory structure:

```bash
# Create directory for your call
mkdir -p data/manual_uploads/HORIZON-HLTH-2024-TOOL-12-01/

# Move your downloaded PDFs there
# Name them descriptively (the system will auto-detect type)
mv ~/Downloads/work_programme_2024.pdf data/manual_uploads/HORIZON-HLTH-2024-TOOL-12-01/
mv ~/Downloads/call_description.pdf data/manual_uploads/HORIZON-HLTH-2024-TOOL-12-01/
mv ~/Downloads/application_guide.pdf data/manual_uploads/HORIZON-HLTH-2024-TOOL-12-01/

# Check files are in place
ls -lh data/manual_uploads/HORIZON-HLTH-2024-TOOL-12-01/
```

**Naming tips for auto-detection:**
- Include keywords in filename for better type detection
- Examples:
  - `work_programme_2024.pdf` → detects as `work_programme`
  - `call_fiche_HLTH.pdf` → detects as `topic_description`
  - `applicant_guide.pdf` → detects as `application_guide`
  - `evaluation_criteria.pdf` → detects as `evaluation_guide`

---

### **Step 5: Run the Ingestion Script**

```bash
# Make script executable
chmod +x scripts/manual_document_upload.py

# Run ingestion
python3 scripts/manual_document_upload.py HORIZON-HLTH-2024-TOOL-12-01
```

**Expected output:**
```
🚀 Processing 3 documents for call: HORIZON-HLTH-2024-TOOL-12-01

======================================================================

📄 Processing: work_programme_2024.pdf
----------------------------------------------------------------------
  📋 Detected type: work_programme
  📖 Parsing PDF: work_programme_2024.pdf
  ✅ Parsed: 45 sections, 123 pages
  ✂️ Chunking document...
  ✅ Created: 287 chunks
  💾 Storing in database...
  ✅ Stored successfully

📄 Processing: call_description.pdf
----------------------------------------------------------------------
  📋 Detected type: topic_description
  📖 Parsing PDF: call_description.pdf
  ✅ Parsed: 12 sections, 28 pages
  ✂️ Chunking document...
  ✅ Created: 67 chunks
  💾 Storing in database...
  ✅ Stored successfully

📄 Processing: application_guide.pdf
----------------------------------------------------------------------
  📋 Detected type: application_guide
  📖 Parsing PDF: application_guide.pdf
  ✅ Parsed: 23 sections, 54 pages
  ✂️ Chunking document...
  ✅ Created: 143 chunks
  💾 Storing in database...
  ✅ Stored successfully

======================================================================
📊 PROCESSING SUMMARY
======================================================================
Call identifier: HORIZON-HLTH-2024-TOOL-12-01
Documents processed: 3/3
Sections found: 80
Chunks created: 497

✅ All documents processed successfully!
======================================================================

🔍 Verifying database storage...
  ✅ Database records:
     - Documents: 3
     - Chunks: 497
```

---

### **Step 6: Verify Data in Database**

Check what was stored:

```bash
# View documents
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT 
    id,
    call_identifier,
    document_type,
    document_title,
    LENGTH(document_content) as content_length
FROM call_documents
WHERE call_identifier = 'HORIZON-HLTH-2024-TOOL-12-01'
ORDER BY document_type;
"
```

**Expected output:**
```
 id | call_identifier              | document_type      | document_title       | content_length
----+------------------------------+--------------------+----------------------+----------------
  1 | HORIZON-HLTH-2024-TOOL-12-01 | application_guide  | application_guide    | 145230
  2 | HORIZON-HLTH-2024-TOOL-12-01 | topic_description  | call_description     | 58743
  3 | HORIZON-HLTH-2024-TOOL-12-01 | work_programme     | work_programme_2024  | 387652
```

Check chunks:

```bash
# View chunk statistics
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT 
    cd.document_type,
    COUNT(cdc.id) as chunk_count,
    AVG(cdc.token_count) as avg_tokens,
    SUM(cdc.token_count) as total_tokens
FROM call_document_chunks cdc
JOIN call_documents cd ON cdc.call_document_id = cd.id
WHERE cdc.call_identifier = 'HORIZON-HLTH-2024-TOOL-12-01'
GROUP BY cd.document_type
ORDER BY chunk_count DESC;
"
```

**Sample chunk content:**

```bash
# Look at a sample chunk
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT 
    section_title,
    LEFT(chunk_text, 200) as chunk_preview
FROM call_document_chunks
WHERE call_identifier = 'HORIZON-HLTH-2024-TOOL-12-01'
LIMIT 3;
"
```

---

### **Step 7: Test Retrieval (Simple Query)**

Create a simple test script to verify retrieval works:

```bash
cat > test_document_retrieval.py << 'EOF'
#!/usr/bin/env python3
"""Quick test of document retrieval"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def test_retrieval(call_id: str, search_term: str):
    """Test full-text search on chunks"""
    
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    # Full-text search
    cursor.execute("""
        SELECT 
            cd.document_type,
            cdc.section_title,
            LEFT(cdc.chunk_text, 300) as chunk_preview,
            ts_rank(
                to_tsvector('english', cdc.chunk_text),
                plainto_tsquery('english', %s)
            ) as rank
        FROM call_document_chunks cdc
        JOIN call_documents cd ON cdc.call_document_id = cd.id
        WHERE cdc.call_identifier = %s
          AND to_tsvector('english', cdc.chunk_text) @@ plainto_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT 3
    """, (search_term, call_id, search_term))
    
    print(f"\n🔍 Search results for: '{search_term}'")
    print("="*70)
    
    results = cursor.fetchall()
    
    if not results:
        print("❌ No results found")
    else:
        for i, (doc_type, section, preview, rank) in enumerate(results, 1):
            print(f"\n{i}. Document Type: {doc_type}")
            print(f"   Section: {section}")
            print(f"   Relevance: {rank:.4f}")
            print(f"   Preview: {preview}...")
            print("-"*70)
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python test_document_retrieval.py <CALL_ID> <SEARCH_TERM>")
        print("Example: python test_document_retrieval.py HORIZON-HLTH-2024-TOOL-12-01 eligibility")
        sys.exit(1)
    
    call_id = sys.argv[1]
    search_term = sys.argv[2]
    
    test_retrieval(call_id, search_term)
EOF

chmod +x test_document_retrieval.py
```

**Run the test:**

```bash
# Test search for "eligibility"
python3 test_document_retrieval.py HORIZON-HLTH-2024-TOOL-12-01 eligibility

# Test search for "budget"
python3 test_document_retrieval.py HORIZON-HLTH-2024-TOOL-12-01 budget

# Test search for "evaluation"
python3 test_document_retrieval.py HORIZON-HLTH-2024-TOOL-12-01 evaluation
```

**Expected output:**
```
🔍 Search results for: 'eligibility'
======================================================================

1. Document Type: eligibility_rules
   Section: ELIGIBILITY CRITERIA
   Relevance: 0.3456
   Preview: ## ELIGIBILITY CRITERIA All legal entities can participate in Horizon Europe actions. However, specific eligibility criteria and rules apply depending on the type of action. Organizations from EU Member States and associated countries are eligible...
----------------------------------------------------------------------

2. Document Type: application_guide
   Section: WHO CAN APPLY
   Relevance: 0.2987
   Preview: ## WHO CAN APPLY Legal entities established in EU Member States or Horizon Europe associated countries are eligible to participate. Third country entities may participate under certain conditions outlined in Article 22 of the Horizon Europe Regulation...
----------------------------------------------------------------------
```

---

## 🎉 Success Criteria

✅ **Database tables created** (call_documents, call_document_chunks, conversation_call_context)

✅ **Documents parsed** (sections detected, text extracted)

✅ **Chunks created** (500-1000 chunks for 3-4 documents)

✅ **Data stored** (visible in database queries)

✅ **Retrieval works** (full-text search returns relevant chunks)

---

## 🚀 Next Steps

Once this works, you can:

1. **Integrate with Call Context Manager**
   - Track which call user is asking about
   - Load relevant chunks for questions

2. **Add to Conversation Manager**
   - Detect when user asks about a call
   - Retrieve call-specific docs
   - Generate answers using doc context

3. **Test End-to-End Flow**
   ```
   User: "Tell me about HORIZON-HLTH-2024-TOOL-12-01"
   → System sets active call
   
   User: "Am I eligible as a university?"
   → System retrieves eligibility_rules chunks
   → AI generates answer using those chunks
   ```

---

## 🐛 Troubleshooting

### **Problem: PyPDF2 not found**
```bash
pip install PyPDF2
```

### **Problem: Database connection failed**
Check your `.env` file has:
```
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

### **Problem: No sections detected**
Some PDFs have no clear structure. The chunker will fall back to simple text splitting (still works fine).

### **Problem: Chunks too long/short**
Edit `manual_document_upload.py` line where `SimpleChunker` is created:
```python
chunker = SimpleChunker(max_chunk_size=1500, overlap=300)  # Adjust these
```

---

## 📚 Document Type Mapping

The system auto-detects these types from filenames:

| Filename Contains | → Type |
|------------------|--------|
| "work programme" | `work_programme` |
| "call" / "topic" / "fiche" | `topic_description` |
| "guide" / "manual" | `application_guide` |
| "evaluation" + "guide" | `evaluation_guide` |
| "template" | `proposal_template` |
| "budget" + "template" | `budget_template` |
| "eligibility" / "rules" | `eligibility_rules` |
| "faq" | `faq` |
| "mga" / "grant agreement" | `model_grant_agreement` |
| (other) | `other` |

**Tip:** Name your files descriptively for better auto-detection!

---

## 🎯 Test Checklist

- [ ] Dependencies installed (`PyPDF2`)
- [ ] Database tables created
- [ ] Directory created (`data/manual_uploads/CALL_ID/`)
- [ ] PDFs downloaded and placed in directory
- [ ] Ingestion script runs successfully
- [ ] Documents appear in `call_documents` table
- [ ] Chunks appear in `call_document_chunks` table
- [ ] Search retrieval returns relevant results

---

**You're ready to test! Start with Step 1.** 🚀


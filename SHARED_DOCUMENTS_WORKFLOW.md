# 🎯 Shared Documents Architecture - Complete Workflow

## 📚 **The Problem You Solved**

**Old approach:**
- ❌ Download "General Annexes" 100+ times (once per call)
- ❌ Store "Work Programme Cluster 6" 20+ times
- ❌ Massive disk waste and processing redundancy

**New approach:**
- ✅ Download each document **once**
- ✅ Store in **shared repository**
- ✅ **Map** calls to documents (many-to-many)
- ✅ Query: "Get all docs for CALL_ID" → returns shared docs

---

## 🏗️ **Architecture Overview**

### **Database Tables:**

```
┌─────────────────────────┐
│  shared_documents       │  ← Documents stored ONCE
│  - id                   │
│  - document_key         │  (e.g., "he_general_annexes_2023-2025")
│  - document_type        │
│  - scope (global/cluster│
│  - file_hash            │
└─────────────────────────┘
            │
            │ Referenced by
            ↓
┌─────────────────────────┐
│  shared_document_chunks │  ← Chunks for RAG
│  - document_id          │
│  - chunk_text           │
│  - section_title        │
└─────────────────────────┘

┌─────────────────────────┐
│ call_document_mappings  │  ← Many-to-many relationships
│  - call_identifier      │
│  - document_id          │
│  - relevance_score      │
│  - is_primary           │
└─────────────────────────┘
```

### **Document Scopes:**

- **Global** - Used by ALL calls (e.g., General Annexes, Programme Guide)
- **Cluster** - Used by all calls in one cluster (e.g., WP Cluster 6)
- **Call** - Specific to one call (e.g., specific call fiche)

---

## 🚀 **Complete Workflow**

### **Phase 1: Set Up Database (One Time)**

```bash
# Run migration to create tables
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres \
  -f migration/004_shared_documents_architecture.sql
```

**Expected output:**
```
CREATE TABLE
CREATE INDEX
...
NOTICE: Shared documents architecture created successfully!
```

---

### **Phase 2: Download Common Documents (One Time)**

#### **Option A: Automatic Download (Recommended)**

```bash
# Download global documents (General Annexes, Programme Guide)
python3 scripts/download_shared_documents.py

# Download specific cluster work programme
python3 scripts/download_shared_documents.py --cluster 6

# Download everything
python3 scripts/download_shared_documents.py --all
```

#### **Option B: Manual Download**

```bash
# Show instructions
python3 scripts/download_shared_documents.py --manual

# Then manually download and save to:
# data/shared_documents/general_annexes.pdf
# data/shared_documents/programme_guide.pdf
# data/shared_documents/wp_cluster_6.pdf
```

**Result:** PDFs in `data/shared_documents/`

---

### **Phase 3: Process Documents (One Time per Document)**

```bash
# Parse, chunk, and store all shared documents
python3 scripts/process_shared_documents.py
```

**What happens:**
1. Scans `data/shared_documents/` for PDFs
2. Computes file hash (avoids duplicates)
3. Parses PDF → sections
4. Chunks sections → ~500-800 chunks per doc
5. Stores in `shared_documents` and `shared_document_chunks` tables

**Expected output:**
```
📄 Processing: general_annexes.pdf
  ✅ Parsed: 67 sections, 142 pages
  ✅ Created: 453 chunks
  ✅ Stored (document ID: 1)

📄 Processing: wp_cluster_6.pdf
  ✅ Parsed: 123 sections, 287 pages
  ✅ Created: 856 chunks
  ✅ Stored (document ID: 2)

📊 PROCESSING SUMMARY
Documents processed: 3
Total chunks created: 1,542
```

**Verify in database:**
```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT document_key, document_type, scope, 
       (SELECT COUNT(*) FROM shared_document_chunks WHERE document_id = shared_documents.id) as chunks
FROM shared_documents;
"
```

---

### **Phase 4: Map Calls to Documents (Once per Call)**

For each call you want to support:

```bash
# Auto-detect and map relevant documents
python3 scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01 --auto
```

**What happens:**
1. Extracts cluster from call ID (e.g., "CL3" → CLUSTER-6)
2. Finds all relevant documents:
   - Global docs (General Annexes, Programme Guide)
   - Cluster docs (WP Cluster 6)
3. Creates mappings in `call_document_mappings`

**Expected output:**
```
🔍 Detected cluster: CLUSTER-6
  ✅ Global document: he_general_annexes_2023-2025
  ✅ Global document: he_programme_guide
  ✅ Cluster document: he_wp_cluster6_civil_security_2023-2025 (primary)

✅ Created 3 mappings

📚 MAPPED DOCUMENTS
  📄 Work Programme Cluster 6 - Civil Security [PRIMARY]
     Chunks: 856
  📄 Horizon Europe General Annexes
     Chunks: 453
  📄 Horizon Europe Programme Guide
     Chunks: 233

📊 Total chunks available for this call: 1,542
```

**Verify mappings:**
```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT call_identifier, COUNT(*) as doc_count
FROM call_document_mappings
GROUP BY call_identifier;
"
```

---

## 🧪 **Testing the System**

### **Test 1: Query Chunks for a Call**

```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT * FROM get_chunks_for_call(
    'HORIZON-CL3-2025-02-CS-ECCC-01',
    'eligibility',
    5
);
"
```

**Expected:** Returns 5 most relevant chunks about eligibility

### **Test 2: View All Chunks for a Call**

```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT 
    call_identifier,
    document_type,
    section_title,
    LEFT(chunk_text, 100) as preview
FROM call_document_chunks_view
WHERE call_identifier = 'HORIZON-CL3-2025-02-CS-ECCC-01'
LIMIT 10;
"
```

---

## 📊 **Efficiency Gains**

### **Storage Comparison:**

**Old approach (per-call storage):**
```
100 calls × 3 documents × 2 MB = 600 MB
```

**New approach (shared storage):**
```
3 shared documents × 2 MB = 6 MB
100 call mappings × 1 KB = 100 KB
Total: ~6 MB (99% reduction!)
```

### **Processing Time:**

**Old:**
- Process each call = 30 seconds × 100 calls = 50 minutes

**New:**
- Process 3 shared docs = 30 seconds × 3 = 90 seconds
- Map 100 calls = 5 seconds × 100 = 8 minutes
- **Total: ~10 minutes (80% faster!)**

---

## 🔄 **Adding More Calls**

### **For a call in an existing cluster:**

```bash
# Just map it (< 5 seconds)
python3 scripts/map_call_to_documents.py HORIZON-CL3-2025-ANOTHER-CALL --auto
```

### **For a call in a new cluster:**

```bash
# 1. Download cluster work programme
python3 scripts/download_shared_documents.py --cluster 7

# 2. Process it
python3 scripts/process_shared_documents.py

# 3. Map the call
python3 scripts/map_call_to_documents.py HORIZON-CL7-2025-EXAMPLE --auto
```

---

## 🎯 **Example: Your Call (HORIZON-CL3-2025-02-CS-ECCC-01)**

### **Quick Start:**

```bash
# 1. Set up database (if not done)
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres \
  -f migration/004_shared_documents_architecture.sql

# 2. Download documents (manual - save to data/shared_documents/)
#    - General Annexes
#    - Programme Guide  
#    - Work Programme Cluster 6

# 3. Process documents
python3 scripts/process_shared_documents.py

# 4. Map your call
python3 scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01 --auto

# 5. Test
PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -c "
SELECT COUNT(*) as total_chunks
FROM call_document_chunks_view
WHERE call_identifier = 'HORIZON-CL3-2025-02-CS-ECCC-01';
"
```

**Expected result:** ~1,500 chunks available for your call

---

## 🔌 **Integration with ConversationManager**

Update your RAG retrieval to use shared documents:

```python
# In your retrieval service
def get_call_context(call_identifier: str, question: str):
    """Get relevant chunks for a call-specific question"""
    
    cursor.execute("""
        SELECT * FROM get_chunks_for_call(%s, %s, 10)
    """, (call_identifier, question))
    
    chunks = cursor.fetchall()
    return chunks
```

---

## 💡 **Advanced: Auto-Detection from Portal**

Future enhancement - scrape call pages to auto-detect linked documents:

```python
# scripts/scrape_call_documents.py (TODO)
def scrape_call_page(call_id: str):
    """Scrape EU portal page to find linked documents"""
    url = f"https://ec.europa.eu/.../topic-details/{call_id}"
    # Parse HTML
    # Extract document links
    # Download if not already in shared_documents
    # Create mappings
```

---

## ✅ **Summary**

1. ✅ **Download documents once** to `data/shared_documents/`
2. ✅ **Process once** with `process_shared_documents.py`
3. ✅ **Map calls** with `map_call_to_documents.py`
4. ✅ **Query efficiently** using `get_chunks_for_call()` function

**Result:** 99% less storage, 80% faster processing, infinite scalability! 🚀


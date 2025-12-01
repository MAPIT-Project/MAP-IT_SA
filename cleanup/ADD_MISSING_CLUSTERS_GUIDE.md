# Guide: Add Missing Cluster Work Programmes

## 🎯 What We're Fixing

**Problem**: Cluster 3, 4, and 6 Work Programmes are missing from the database.

**Impact**: AI can't answer call-specific questions for:
- Cluster 3 (Civil Security) calls
- Cluster 4 (Digital, Industry & Space) calls  
- Cluster 6 (Food, Bioeconomy) calls

**Solution**: Download and process the missing PDFs.

---

## 📥 Quick Start

### Option 1: Automatic Download (Try This First)

```bash
cd /home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA
./download_missing_clusters.sh
```

If that works, skip to **Step 2: Process Documents**.

### Option 2: Manual Download (If URLs Changed)

**Download these PDFs manually**:

1. **Cluster 3: Civil Security for Society**
   - Search: "Horizon Europe Work Programme 2023-2024 Cluster 3 Civil Security"
   - Portal: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/horizon
   - Save as: `data/shared_documents/HE_WP_2023-2024_Cluster3_Civil_Security.pdf`

2. **Cluster 4: Digital, Industry and Space**
   - Search: "Horizon Europe Work Programme 2023-2024 Cluster 4 Digital Industry Space"
   - Also called: "Cluster 4" or sometimes in docs as "Part 7"
   - Save as: `data/shared_documents/HE_WP_2023-2024_Cluster4_Digital.pdf`

3. **Cluster 6: Food, Bioeconomy, Natural Resources**
   - Search: "Horizon Europe Work Programme 2023-2024 Cluster 6 Food Bioeconomy"
   - Also called: sometimes in docs as "Part 9"
   - Save as: `data/shared_documents/HE_WP_2023-2024_Cluster6_Food.pdf`

**Quick Links** (may expire):
- Cluster 3: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-3-civil-security-for-society_horizon-2023-2024_en.pdf
- Cluster 4: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-7-digital-industry-and-space_horizon-2023-2024_en.pdf
- Cluster 6: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-9-food-bioeconomy-natural-resources-agriculture-and-environment_horizon-2023-2024_en.pdf

---

## ⚙️ Step 2: Process Documents

Once PDFs are downloaded:

```bash
cd /home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA

# Verify files exist
ls -lh data/shared_documents/HE_WP_2023-2024_Cluster*.pdf

# Process them (parse, chunk, embed, store)
python3 scripts/process_shared_documents.py
```

**What this does**:
1. Parses each PDF
2. Chunks the text into ~500 token sections
3. Stores in `shared_documents` table
4. Creates full-text search indexes

**Expected output**:
```
Processing: HE_WP_2023-2024_Cluster3_Civil_Security.pdf
  ✅ Parsed: 156 pages
  ✅ Created: 1,234 chunks
  ✅ Stored with key: abc123...

Processing: HE_WP_2023-2024_Cluster4_Digital.pdf
  ✅ Parsed: 203 pages
  ✅ Created: 1,567 chunks
  ...
```

---

## 🔗 Step 3: Map to Call (Optional)

The system will now **automatically** map cluster WPs to calls based on call ID.

But if you want to manually verify or force a mapping:

```bash
# For your specific call
python3 scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01

# Or clear cache and let it auto-map next time
docker exec supabase_db_supabase_cli psql -U postgres -c "DELETE FROM call_document_mappings WHERE call_identifier = 'HORIZON-CL3-2025-02-CS-ECCC-01';"
```

---

## 🔄 Step 4: Restart API

```bash
docker restart $(docker ps -q -f name=map-it_sa-api)
sleep 5  # Wait for startup
```

---

## 🧪 Step 5: Test

```bash
# Test Cluster 3 (Civil Security)
curl -s -X POST "http://localhost:8000/api/v2/conversation/test123/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"}' | \
  python3 -c "import json, sys; r=json.load(sys.stdin).get('response',''); print('✅ WORKS!' if 'yes' in r.lower()[:200] and 'cluster 3' in r.lower() or 'civil security' in r.lower() else '❌ Still generic'); print(r[:400])"
```

**Expected result**:
```
✅ WORKS!
Yes, you can apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01. 
According to the Cluster 3 Work Programme [citation], Swiss entities as 
Associated Countries are eligible. This specific call does not have 
special restrictions...
```

---

## 📊 Verification Queries

### Check if documents are in database:

```sql
-- In PostgreSQL
SELECT id, document_title 
FROM shared_documents 
WHERE document_title ILIKE '%cluster%3%' 
   OR document_title ILIKE '%civil%security%';

-- Should show: HE WP ... Cluster 3 ... Civil Security
```

### Check chunk count:

```sql
SELECT 
    sd.document_title,
    COUNT(sdc.id) as chunk_count
FROM shared_documents sd
LEFT JOIN shared_document_chunks sdc ON sd.id = sdc.document_id
WHERE sd.document_title ILIKE '%cluster%3%'
GROUP BY sd.document_title;

-- Should show: ~1,200+ chunks
```

### Check call mapping:

```sql
SELECT 
    sd.document_title
FROM call_document_mappings cdm
JOIN shared_documents sd ON cdm.document_id = sd.id
WHERE cdm.call_identifier = 'HORIZON-CL3-2025-02-CS-ECCC-01'
ORDER BY sd.document_title;

-- Should now include: Cluster 3 Work Programme
```

---

## 🎉 Success Criteria

After completing all steps:

✅ 3 new PDFs in `data/shared_documents/`  
✅ 3 new documents in `shared_documents` table  
✅ ~3,000+ new chunks in `shared_document_chunks` table  
✅ Cluster 3 WP mapped to HORIZON-CL3-2025-02-CS-ECCC-01  
✅ AI gives specific answer for Switzerland eligibility  
✅ Answer cites "Cluster 3 Work Programme" or similar  

---

## 🔧 Troubleshooting

### Problem: Download script fails

**Solution**: URLs may have changed. Use manual download (Option 2).

### Problem: Processing script fails

**Error**: `File not found`  
**Solution**: Check file paths, ensure PDFs are in `data/shared_documents/`

**Error**: `PDF parse error`  
**Solution**: PDF might be corrupted, re-download

### Problem: AI still gives generic answer

**Possible causes**:
1. Documents not mapped to call
   - **Fix**: Run `python3 scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01`
   
2. Old cache still active
   - **Fix**: Delete old mapping, restart API
   
3. Wrong document downloaded
   - **Fix**: Verify PDF title matches cluster number

### Problem: Chunks not searchable

**Check**: Full-text search index
```sql
-- Should return results
SELECT COUNT(*) FROM shared_document_chunks sdc
JOIN shared_documents sd ON sdc.document_id = sd.id
WHERE sd.document_title ILIKE '%civil%'
  AND sdc.chunk_text ILIKE '%eligibility%';
```

---

## 📝 Future Prevention

To avoid this issue with future calls, consider:

1. **Pre-load all 6 cluster WPs** during system initialization
2. **Automatic cluster detection** (already implemented!)
3. **Quarterly refresh** of all Work Programmes when EU updates them

---

## 🆘 Need Help?

If issues persist:

1. Check logs: `docker logs $(docker ps -q -f name=map-it_sa-api) | tail -100`
2. Verify database connection: `docker exec supabase_db_supabase_cli psql -U postgres -c "SELECT 1"`
3. Check PDF contents: Open in PDF reader, verify it's the right document
4. Manual test: Run `test_automatic_call_documents.py` directly

---

**Time Required**: 15-30 minutes (mostly waiting for downloads and processing)

**Difficulty**: Easy (mostly automated)

**Impact**: High (enables call-specific answers for 3 major clusters!)





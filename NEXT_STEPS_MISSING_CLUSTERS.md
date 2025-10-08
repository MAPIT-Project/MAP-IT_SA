# ✅ Next Steps: Complete Missing Cluster Setup

## 📊 Current Status

**Downloaded Successfully**:
- ✅ **Cluster 4** (Digital, Industry & Space): 3.7 MB
- ✅ **Cluster 6** (Food, Bioeconomy): 4.5 MB

**Still Needed**:
- ❌ **Cluster 3** (Civil Security): URL changed (404 error)

---

## 🚀 Quick Win: Process Cluster 4 & 6 Now

You can immediately improve your system for Cluster 4 & 6 calls:

```bash
cd /home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA

# Process the downloaded PDFs
python3 scripts/process_shared_documents.py

# Restart API to use new documents
docker restart $(docker ps -q -f name=map-it_sa-api)
```

**Expected processing time**: ~5-10 minutes  
**Result**: Cluster 4 & 6 calls will now have specific eligibility info!

---

## 🔍 Find and Add Cluster 3 (For Your Current Call)

Your call **HORIZON-CL3-2025-02-CS-ECCC-01** needs the Cluster 3 Work Programme.

### Method 1: EU Funding Portal (Recommended)

1. **Go to**: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents

2. **Find**: "Horizon Europe Work Programme 2023-2024"

3. **Look for**: "Part 3: Civil Security for Society"  
   (Might be titled "Cluster 3" or "WP3")

4. **Download** the PDF

5. **Save as**: `data/shared_documents/HE_WP_2023-2024_Cluster3_Civil_Security.pdf`

6. **Process**:
   ```bash
   cd /home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA
   python3 scripts/process_shared_documents.py
   docker restart $(docker ps -q -f name=map-it_sa-api)
   ```

### Method 2: Try Alternative URL

The Work Programme might be at:
- https://commission.europa.eu/funding-tenders/find-funding/eu-funding-programmes/horizon-europe_en
- Look for "Work Programme" → "Civil Security for Society"

### Method 3: Direct Download (If you find the link)

```bash
cd /home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA/data/shared_documents

# Replace <URL> with the actual PDF link when you find it
wget -O HE_WP_2023-2024_Cluster3_Civil_Security.pdf "<URL>"

# Then process
cd ../..
python3 scripts/process_shared_documents.py
```

---

## 🧪 Test After Processing

### Test Cluster 4 (Digital, Industry & Space)

```bash
curl -s -X POST "http://localhost:8000/api/v2/conversation/test456/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Can I apply from Norway for a Cluster 4 Digital call?"}' | \
  python3 -c "import json, sys; r=json.load(sys.stdin).get('response',''); print('✅' if 'yes' in r.lower()[:200] else '❌', r[:300])"
```

### Test Cluster 6 (Food, Bioeconomy)

```bash
curl -s -X POST "http://localhost:8000/api/v2/conversation/test789/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the eligibility rules for Cluster 6 calls?"}' | \
  python3 -c "import json, sys; r=json.load(sys.stdin).get('response',''); print('✅' if 'cluster 6' in r.lower() or 'food' in r.lower() else '❌', r[:300])"
```

### Test Cluster 3 (After Adding)

```bash
curl -s -X POST "http://localhost:8000/api/v2/conversation/test321/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"}' | \
  python3 -c "import json, sys; r=json.load(sys.stdin).get('response',''); print('✅ SPECIFIC ANSWER!' if ('yes' in r.lower()[:200] and ('cluster 3' in r.lower() or 'civil security' in r.lower())) else '❌ Still generic', r[:400])"
```

---

## 📋 Verification Checklist

After processing, verify success:

### Check Database

```sql
-- Connect to database
docker exec supabase_db_supabase_cli psql -U postgres

-- Check if documents exist
SELECT id, document_title 
FROM shared_documents 
WHERE document_title ILIKE '%cluster%4%' 
   OR document_title ILIKE '%cluster%6%'
   OR document_title ILIKE '%cluster%3%'
   OR document_title ILIKE '%digital%industry%'
   OR document_title ILIKE '%food%bioeconomy%'
   OR document_title ILIKE '%civil%security%'
ORDER BY document_title;

-- Should show 2-3 new documents
```

### Check Chunk Counts

```sql
SELECT 
    sd.document_title,
    COUNT(sdc.id) as chunks
FROM shared_documents sd
LEFT JOIN shared_document_chunks sdc ON sd.id = sdc.document_id
WHERE sd.document_title ILIKE '%cluster%'
GROUP BY sd.document_title
ORDER BY sd.document_title;

-- Cluster 4: ~1,500-2,000 chunks
-- Cluster 6: ~1,800-2,500 chunks  
-- Cluster 3: ~1,200-1,600 chunks (when added)
```

---

## 🎯 Expected Results

### After Adding Cluster 4 & 6

**Before**:
> "Associated Countries can generally apply... Please check official documentation."

**After**:
> "Yes, for Cluster 4 Digital Industry calls, Associated Countries like Switzerland are eligible according to the Cluster 4 Work Programme [citation]. No special restrictions apply for this cluster."

### After Adding Cluster 3

**Your Specific Question**:
> "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"

**Expected Answer**:
> "Yes, you can apply from Switzerland. According to the Cluster 3: Civil Security for Society Work Programme [citation], Swiss entities as Associated Countries are eligible. This specific call does not impose additional restrictions on Associated Countries [citation from specific topic in CL3 WP]."

---

## ⏱️ Time Estimates

| Task | Time | Status |
|------|------|--------|
| Process Cluster 4 & 6 | 5-10 min | ⏳ Ready to do now |
| Find Cluster 3 PDF | 5-15 min | 🔍 Manual search needed |
| Process Cluster 3 | 3-5 min | ⏸️ After download |
| Test all clusters | 2 min | ⏸️ After processing |
| **Total** | **15-32 min** | |

---

## 💡 Pro Tips

1. **Process in batches**: Don't wait - process Cluster 4 & 6 now, add Cluster 3 later

2. **Bookmark the portal**: Save the EU Funding Portal link for future updates

3. **Check annually**: Work Programmes update yearly (2025-2026, 2026-2027, etc.)

4. **Use the script**: The processing script (`process_shared_documents.py`) handles everything automatically

5. **Verify with tests**: Always test after adding new documents to confirm they're working

---

## 🆘 Troubleshooting

### Problem: Processing takes too long

**Normal**: Large PDFs (200+ pages) can take 5-10 minutes  
**Solution**: Be patient, check logs for progress

### Problem: "Document already exists" error

**Cause**: PDF already processed  
**Solution**: This is OK! It means the document is already in the database

### Problem: Chunks not searchable

**Check**: 
```sql
SELECT COUNT(*) FROM shared_document_chunks sdc
JOIN shared_documents sd ON sdc.document_id = sd.id
WHERE sd.document_title ILIKE '%cluster 4%';
```

**If 0**: Document might not have processed correctly, check logs

---

## 📞 Need Help?

**Check logs**:
```bash
# Processing logs
tail -f logs/processing.log

# API logs
docker logs -f $(docker ps -q -f name=map-it_sa-api)
```

**Common issues documented in**: `ADD_MISSING_CLUSTERS_GUIDE.md`

---

## ✅ Success Criteria

You'll know it's working when:

- [ ] Cluster 4 & 6 documents show in database
- [ ] ~3,500+ new chunks added
- [ ] Test queries return cluster-specific answers
- [ ] AI cites "Cluster X Work Programme" in responses
- [ ] Switzerland question gets definitive answer (after Cluster 3)

---

**Ready to proceed? Run**:
```bash
python3 scripts/process_shared_documents.py
```

This will process Cluster 4 & 6 immediately! 🚀





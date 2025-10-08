# Database Cleanup Summary - October 2025

## 🗑️ What Was Removed

### Old 2023-2024/2023-2025 Documents Deleted

**Total Removed**: 10 documents, 9,492 chunks

1. **HE Main Work Programme 2023–2025 – 1. General Introduction** (573 chunks)
2. **HE Main Work Programme 2023–2025 – 5. Culture, creativity** (489 chunks)
3. **HE Main Work Programme 2023–2025 – 7. Digital, Industry and Space** (1,314 chunks)
4. **HE Main Work Programme 2023–2025 – 8. Climate, Energy and Mobility** (1,187 chunks)
5. **HE Main Work Programme 2023–2025 – 9. Food, Bioeconomy** (1,474 chunks)
6. **HE Main Work Programme 2023–2025 – 10. European Innovation Ecosystems** (153 chunks)
7. **HE Main Work Programme 2023–2025 – 11. Widening participation** (550 chunks)
8. **HE Main Work Programme 2023–2025 – 12. Missions** (964 chunks)
9. **HE_WP_2023-2024_Cluster4_Digital_Industry_Space** (1,314 chunks - duplicate)
10. **HE_WP_2023-2024_Cluster6_Food_Bioeconomy** (1,474 chunks - duplicate)

### Physical Files Removed
- `HE_WP_2023-2024_Cluster4_Digital_Industry_Space.pdf` (3.7 MB)
- `HE_WP_2023-2024_Cluster6_Food_Bioeconomy.pdf` (4.5 MB)

---

## ✅ What Remains (Current Database)

### 📊 Summary Stats
- **Total Documents**: 14 (down from 24)
- **Total Chunks**: 4,470 (down from 13,962)
- **Storage Saved**: ~68% reduction in chunks
- **Old Docs Remaining**: 0

### 🆕 2025 Work Programmes (Current)

1. **Horizon Europe Work Programme 2025 - Cluster 3: Civil Security for Society**
   - 203 chunks
   - 108 pages
   - Mapped to: HORIZON-CL3-2025-02-CS-ECCC-01

2. **Horizon Europe Work Programme 2025 - Cluster 4: Digital, Industry and Space**
   - 789 chunks
   - 339 pages

3. **Horizon Europe Work Programme 2025 - Cluster 6: Food, Bioeconomy**
   - 733 chunks
   - 306 pages

4. **Horizon Europe Work Programme 2025** (General)
   - 203 chunks

**Total 2025 WP chunks**: 1,928

### 📋 General Documents (Timeless - Kept)

These documents are NOT version-specific and remain relevant:

1. **Annex A** (81 chunks)
   - General eligibility conditions

2. **Horizon Europe Programme Guide** (141 chunks)
   - Overall programme rules

3. **HE MGA - Model Grant Agreement** (397 chunks)
   - Standard grant agreement template

4. **EU Grants AGA — Annotated Model Grant Agreement** (1,354 chunks)
   - Detailed grant agreement guide

5. **Funding & Tenders Portal Terms and Conditions** (104 chunks)
   - Portal usage terms

6. **Online Manual** (196 chunks)
   - How-to guide

7. **Standard application form (HE RIA, IA)** (119 chunks)
   - Application template

8. **Standard evaluation form (HE RIA, IA)** (24 chunks)
   - Evaluation criteria

9. **Decision authorising the use of lump sum contributions** (15 chunks)
   - Lump sum rules

10. **Rules for Legal Entity Validation, LEAR Appointment and Financial Capacity Assessment** (111 chunks)
    - Entity validation rules

**Total general document chunks**: 2,542

---

## 📈 Before & After Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Total Documents** | 24 | 14 | ⬇️ 10 (-42%) |
| **Total Chunks** | 13,962 | 4,470 | ⬇️ 9,492 (-68%) |
| **Old WPs (2023-2024)** | 10 | 0 | ✅ All removed |
| **Current WPs (2025)** | 3 | 4 | ✅ Up to date |
| **General Docs** | 11 | 10 | ➡️ Stable |

---

## 🎯 Why This Matters

### Benefits of Cleanup

1. **✅ Up-to-Date Information**
   - All Work Programmes are now 2025 versions
   - No risk of AI citing outdated eligibility rules

2. **⚡ Faster Searches**
   - 68% fewer chunks to search through
   - Reduced noise in search results

3. **💾 Storage Efficiency**
   - ~6 MB of PDF files removed
   - Database size reduced significantly

4. **🎯 Better AI Responses**
   - No confusion between 2023-2024 and 2025 rules
   - AI will cite current documents only

---

## 🔍 Verification Commands

### Check remaining documents
```bash
docker exec supabase_db_supabase_cli psql -U postgres -c "
SELECT COUNT(*) as total_docs FROM shared_documents;"
```

### Check for any old documents
```bash
docker exec supabase_db_supabase_cli psql -U postgres -c "
SELECT COUNT(*) as old_docs FROM shared_documents 
WHERE document_title ILIKE '%2023%2024%' OR document_title ILIKE '%2023%2025%';"
```

### Verify 2025 Work Programmes
```bash
docker exec supabase_db_supabase_cli psql -U postgres -c "
SELECT document_title FROM shared_documents 
WHERE document_title ILIKE '%2025%' 
ORDER BY document_title;"
```

---

## 📝 Notes

1. **General documents kept**: Documents like Annex A, Programme Guide, and MGA templates were kept because they contain general rules that apply across programme years.

2. **"Horizon Europe Programme Guide" version**: Although this has "2023-2025" as its document_version, it contains fundamental programme rules that remain valid. Consider updating this if a 2025-specific version becomes available.

3. **Future updates**: When 2026 Work Programmes are released, repeat this cleanup process to remove 2025 documents.

---

## ✅ Cleanup Complete!

**Date**: October 3, 2025  
**Performed by**: Automated cleanup script  
**Status**: ✅ Successful  
**Documents removed**: 10  
**Chunks removed**: 9,492  
**Database**: Clean and current for 2025

---

## 🚀 Next Steps

Your database is now clean and optimized! The AI will now:
- ✅ Only cite 2025 Work Programmes
- ✅ Give faster responses (fewer documents to search)
- ✅ Provide more accurate, up-to-date information

**Recommendation**: Restart the API to clear any in-memory caches:
```bash
docker restart $(docker ps -q -f name=map-it_sa-api)
```


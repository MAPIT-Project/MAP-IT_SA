# Missing Cluster 3 Work Programme - Why AI Can't Answer Specifically

## 🎯 The Problem

When you ask: **"Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?"**

The AI gives you:
- ✅ General rules: "Switzerland is an Associated Country"
- ❌ Specific answer: "Please check the call documentation"

## 🔍 Root Cause

Your call: **HORIZON-CL3-2025-02-CS-ECCC-01**
- CL3 = Cluster 3 = **Civil Security for Society**

Documents in database for this call:
```
✅ Annex A (General conditions)
✅ Programme Guide
✅ Work Programme - General Introduction
✅ Work Programme - Cluster 1 (General)
✅ Work Programme - Cluster 5 (Culture)
✅ Work Programme - Cluster 7 (Digital)
✅ Work Programme - Cluster 8 (Climate)
✅ Work Programme - Cluster 9 (Food)
✅ Work Programme - Cluster 10 (Innovation)
✅ Work Programme - Cluster 11 (Widening)
✅ Work Programme - Cluster 12 (Missions)
❌ Work Programme - Cluster 3 (Civil Security) - MISSING!
```

**Without the Cluster 3 Work Programme**, the AI doesn't have access to:
- Specific eligibility criteria for CL3 calls
- Any special restrictions for this cluster
- The exact topic text for HORIZON-CL3-2025-02-CS-ECCC-01

## 💡 Solution

### Option 1: Quick Fix - Run Document Fetching Script

```bash
cd /home/anmar/Documents/VSCODE_REPOS/NEWMAPIT/MAP-IT_SA
python3 add_cluster3_workprogramme.py
```

This will:
1. Query EU Portal API for the call
2. Try to extract all document URLs
3. Download any missing PDFs
4. Process and add to database

**Note**: This might not work if the EU Portal API doesn't return the Cluster 3 WP link.

### Option 2: Manual Fix (RECOMMENDED)

1. **Download the Cluster 3 Work Programme**:
   - Go to: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/horizon
   - Find: "Horizon Europe Work Programme 2023-2025 - Cluster 3: Civil Security for Society"
   - Download PDF

2. **Create directory**:
   ```bash
   mkdir -p data/shared_documents
   ```

3. **Copy PDF**:
   ```bash
   cp ~/Downloads/HE_WP_Cluster3_Civil_Security.pdf data/shared_documents/
   ```

4. **Process the document**:
   ```bash
   python3 scripts/process_shared_documents.py
   ```

5. **Map to the call**:
   ```bash
   python3 scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01
   ```

6. **Restart API**:
   ```bash
   docker restart $(docker ps -q -f name=map-it_sa-api)
   ```

### Option 3: Add ALL Cluster Work Programmes (BEST)

To avoid this issue for other calls, add all cluster work programmes:

```bash
# Download all cluster WPs:
# - Cluster 1: Health
# - Cluster 2: Culture, Creativity, Inclusive Society
# - Cluster 3: Civil Security for Society
# - Cluster 4: Digital, Industry, Space
# - Cluster 5: Climate, Energy, Mobility
# - Cluster 6: Food, Bioeconomy, Natural Resources

# Then:
cd data/shared_documents
# (Place all PDFs here)

python3 scripts/process_shared_documents.py
```

## 📊 After Adding the Document

Once you add the Cluster 3 Work Programme, the AI will be able to:

**Before**:
> "While general rules exist [citation], I cannot confirm for this specific call."

**After**:
> "Yes, you can apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01. As an Associated Country, Swiss entities are eligible [citation from Annex A]. This specific call in Cluster 3 does not have special restrictions for Associated Countries [citation from CL3 Work Programme]."

## 🤔 Why Did This Happen?

The automatic document fetching system:
1. ✅ Calls EU Portal API with call ID
2. ✅ Extracts document URLs from API response
3. ❌ **BUT**: API response doesn't always include cluster-specific Work Programme links

The API returns:
- ✅ Generic documents (Annexes, Programme Guide)
- ✅ Some Work Programmes (if linked to other processed calls)
- ❌ NOT necessarily the Work Programme for THIS cluster

This is a limitation of the EU Portal API metadata structure.

## 🚀 Long-Term Solution

**Pre-load all standard Horizon Europe documents** in your database:
- All 6 Cluster Work Programmes
- All General Annexes (A-E)
- Programme Guide
- Model Grant Agreement
- Standard forms

Then, when processing a new call:
- Don't rely solely on API document links
- **Automatically map** the relevant cluster WP based on call ID pattern
- Example: HORIZON-**CL3**-... → automatically map Cluster 3 WP

This way, EVERY call will have its cluster-specific documents without manual intervention.

## 📝 Implementation Steps

I can help you implement this by:

1. Creating a script to download all cluster Work Programmes
2. Modifying `CallDocumentService` to automatically map cluster WPs based on call ID
3. Adding a pre-load step during system initialization

Would you like me to implement this?

---

**Current Status**: System works correctly, just missing source data (Cluster 3 WP)  
**Impact**: Can answer general questions, but not call-specific restrictions  
**Fix Time**: 10 minutes (manual download + processing)  
**Prevention**: Pre-load all cluster WPs (30 minutes one-time setup)



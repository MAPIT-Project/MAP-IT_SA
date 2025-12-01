# Why "Can I apply from Switzerland?" Doesn't Work

## 🔍 Root Cause Analysis

When asked "Can I apply from Switzerland for HORIZON-CL3-2025-02-CS-ECCC-01?", the system returns:
- ❌ Only 1 chunk mentioning "Switzerland" (about WMO - irrelevant)
- ❌ No document lists Switzerland as an associated country
- ❌ AI can't answer definitively because the data isn't there

## 📊 What We Have vs What We Need

### Documents We Have:
✅ Work Programmes (19 mapped to this call)  
✅ General Annexes (Annex A)  
✅ Programme Guide  
✅ Model Grant Agreement  

### What's Missing:
❌ **List of Associated Countries** (Albania, Armenia, Bosnia, Georgia, Iceland, Israel, Moldova, Montenegro, Morocco, North Macedonia, Norway, Serbia, Tunisia, Turkey, Ukraine, **Switzerland**, UK - partially)

## 🎯 Solutions (Pick One)

### Option 1: Add Country Eligibility Document (RECOMMENDED)

Create a simple document that lists:
- EU Member States (all 27)
- Associated Countries (including Switzerland)
- Special cases (UK, Switzerland status)

**Implementation**:
1. Create `data/shared_documents/HE_Eligible_Countries_2023-2025.txt`:
   ```
   HORIZON EUROPE ELIGIBLE AND ASSOCIATED COUNTRIES (2023-2025)
   
   EU MEMBER STATES:
   Austria, Belgium, Bulgaria, Croatia, Cyprus, Czech Republic, Denmark,
   Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy,
   Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal,
   Romania, Slovakia, Slovenia, Spain, Sweden
   
   ASSOCIATED COUNTRIES:
   Albania, Armenia, Bosnia and Herzegovina, Faroe Islands, Georgia,
   Iceland, Israel, Kosovo, Moldova, Montenegro, Morocco, North Macedonia,
   Norway, Serbia, Tunisia, Turkey, Ukraine, United Kingdom (partial)
   
   SWITZERLAND: Switzerland is an associated country. Swiss entities
   can participate in most Horizon Europe calls unless specifically
   excluded in the call conditions.
   
   ELIGIBILITY RULES:
   - Legal entities from EU Member States: Fully eligible
   - Legal entities from Associated Countries: Eligible as if from EU
   - Entities from other countries: Can participate but may have restrictions
   ```

2. Process and map to ALL calls:
   ```bash
   python3 scripts/process_shared_documents.py
   python3 scripts/map_call_to_documents.py HORIZON-CL3-2025-02-CS-ECCC-01
   ```

### Option 2: Use External Knowledge API

Integrate with a live API that has country eligibility:
- EU Funding & Tenders Portal API
- CORDIS API
- Custom knowledge base

### Option 3: Improve AI System Prompt

Tell the AI to use its training data when documents don't have the answer:

```python
# In conversation_manager.py
system_prompt = """
You are a Horizon Europe funding expert. When answering questions:

1. PRIORITIZE information from the provided documents
2. If documents don't contain the specific information BUT you have
   general knowledge about Horizon Europe, you MAY use that knowledge
   with a disclaimer like: "Based on general Horizon Europe rules..."
3. ALWAYS recommend checking official sources for definitive answers

KNOWN FACTS (use if not in documents):
- Switzerland: Associated Country (can participate in most calls)
- UK: Associated Country (partial, depends on call)
- Norway, Iceland: Associated Countries (full participation)
"""
```

### Option 4: Fallback to Web Search

When documents don't have the answer, automatically search:
- funding-and-tenders.ec.europa.eu
- CORDIS
- Official EU pages

## 🚀 Recommended Implementation

**Short-term (1 hour)**:
- ✅ Option 3: Update AI prompt to use general knowledge

**Medium-term (1 day)**:
- ✅ Option 1: Add country eligibility document
- ✅ Map to all calls

**Long-term (1 week)**:
- ✅ Option 4: Integrate web search fallback
- ✅ Option 2: Connect to live APIs

## 📝 Quick Fix Right Now

The current search IS working (it found 4 relevant chunks about eligibility). The problem is the chunks don't mention Switzerland explicitly.

**The AI should be smart enough to say**: 
> "Based on the eligibility criteria which mention 'Associated Countries' [citation], and my knowledge that Switzerland is an associated country, you should generally be able to apply. However, please verify in the official call documentation for any specific restrictions."

But it's being overly cautious because it doesn't want to hallucinate.

## 🎯 Bottom Line

**Your system is working correctly** - it's a data completeness issue, not a technical issue.

**Quick wins**:
1. Add a countries list document (30 minutes)
2. Update AI prompt to be more helpful (10 minutes)
3. Consider web search fallback for unknowns (future)

The search system with topic detection (eligibility → "eligibility criteria associated countries EU member states") is actually working great! It found 4 relevant chunks. We just need better source data.



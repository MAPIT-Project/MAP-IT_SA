# Missing Procedural Documentation Plan

## Identified Gaps for Procedural Questions

Based on the analysis, the following 3 questions need enhanced FAQ handling:

1. **Question 7**: "What's the difference between 'calls' and 'topics' on the Funding & Tenders Portal?"
2. **Question 8**: "How to filter calls by budget, type of action, and expected outcomes?"
3. **Question 14**: "How to identify topics with lump-sum funding vs actual cost funding?"

## Required Missing Documentation

### 1. EU Funding & Tenders Portal User Guide
**URL**: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/faq
**Content**: Portal navigation, call vs topic explanation, filtering capabilities

### 2. Horizon Europe Programme Guide - Funding Types Section
**URL**: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf
**Content**: Lump-sum vs actual cost funding explanations

### 3. EU Grants AGA - Financial Rules
**URL**: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf  
**Content**: Budget categories, funding rates, financial rules

### 4. Portal Filtering Tutorial/Guide
**URL**: Need to scrape portal filtering interface documentation

## HTML Pages to Convert to PDF

1. **EU Portal FAQ Page** - Contains call vs topic explanations
2. **Portal User Interface Documentation** - Filtering capabilities
3. **Funding Types Comparison Page** - Lump-sum vs actual cost

## Download and Conversion Plan

### Step 1: Download Missing HTML Pages
```bash
# EU Portal FAQ Page
curl -s "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/faq" > eu_portal_faq.html

# Portal User Guide
curl -s "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/help" > portal_user_guide.html

# Funding Types Explanation
curl -s "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;freeTextSearchKeyword=lump-sum" > funding_types.html
```

### Step 2: Convert HTML to PDF
```bash
# Install required tools
sudo apt-get install -y wkhtmltopdf

# Convert HTML to PDF
wkhtmltopdf eu_portal_faq.html eu_portal_faq.pdf
wkhtmltopdf portal_user_guide.html portal_user_guide.pdf  
wkhtmltopdf funding_types.html funding_types.pdf
```

### Step 3: Add to Comprehensive Documents
Move the generated PDFs to the comprehensive documents directory:
```bash
mkdir -p downloads/horizon_europe_comprehensive/procedural_guides/
mv *.pdf downloads/horizon_europe_comprehensive/procedural_guides/
```

### Step 4: Update Processing Configuration
Add the new documents to the processing pipeline by updating the document processing scripts to include procedural guides.

## Expected Content Coverage

### For Question 7 (Call vs Topic):
- Portal structure explanation
- Call hierarchy (Work Programme → Calls → Topics)
- Navigation differences

### For Question 8 (Filtering):
- Search interface documentation
- Filter categories (budget, action type, outcomes)
- Advanced search techniques

### For Question 14 (Funding Types):
- Lump-sum funding criteria
- Actual cost funding rules
- Eligibility conditions for each type
- Reporting differences

## Implementation Timeline

1. **Download HTML pages** - 15 minutes
2. **Convert to PDF** - 10 minutes  
3. **Add to processing pipeline** - 15 minutes
4. **Re-run ingestion** - 30 minutes
5. **Test enhanced FAQ responses** - 20 minutes

## Success Metrics

- ✅ All 3 procedural questions return comprehensive answers
- ✅ FAQ intent detection accuracy improves to 100%
- ✅ System provides detailed portal navigation guidance
- ✅ Funding type explanations are clear and accurate
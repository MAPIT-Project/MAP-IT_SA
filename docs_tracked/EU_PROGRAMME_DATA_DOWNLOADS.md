# EU Programme Data Downloads Guide

This document lists all the official sources where you can download bulk data for EU funding programmes. Download these files to expand the system beyond Horizon Europe.

---

## Table of Contents

1. [Funded Projects Data (CSV/Excel)](#1-funded-projects-data)
2. [Programme Guides & Rules (PDF)](#2-programme-guides--rules)
3. [Work Programmes (PDF)](#3-work-programmes)
4. [Reference Data](#4-reference-data)
5. [Suggested Folder Structure](#5-suggested-folder-structure)

---

## 1. Funded Projects Data

These are bulk downloads of **funded projects** (not calls). Use these to find similar projects, benchmark budgets, and analyze consortiums.

### Horizon Europe (Already Downloaded)
You already have this in `/data/cordis/`

- **URL:** https://data.europa.eu/data/datasets/cordis-eu-research-projects-under-horizon-europe-2021-2027
- **Files:** project.csv, organization.csv, topics.csv, etc.
- **Format:** CSV, XML, JSON
- **Updated:** Monthly

---

### Erasmus+ Projects

- **URL:** https://erasmus-plus.ec.europa.eu/projects/projects-lists
- **What to download:**
  - Scroll down to "Download project lists"
  - Download **2021-2027** data (current period)
  - Also download **2014-2020** for historical reference
- **Format:** Excel (.xlsx)
- **Contains:** Project title, coordinator, partners, countries, grant amount, action type
- **Save to:** `data/erasmus/`

#### Direct Links (if available on page):
- KA1 - Learning Mobility
- KA2 - Cooperation Partnerships
- KA3 - Policy Support
- Jean Monnet Actions
- Sport Actions

---

### Creative Europe Projects

- **URL:** https://culture.ec.europa.eu/creative-europe/projects/projects-lists
- **What to download:**
  - CULTURE strand projects
  - MEDIA strand projects
  - Cross-sectoral projects
- **Format:** Excel (.xlsx)
- **Contains:** Project info, coordinator, EU contribution
- **Save to:** `data/creative_europe/`

#### Alternative Search Interface:
- **URL:** https://culture.ec.europa.eu/creative-europe/projects/search
- You can search and export specific results

---

### LIFE Programme Projects

- **URL:** https://life-datahub.eismea.eu/
- **What to do:**
  1. Go to the data hub
  2. Use filters to select projects
  3. Export/download the results
- **Alternative:** https://webgate.ec.europa.eu/life/publicWebsite/search
- **Format:** Excel/CSV export
- **Contains:** Environment & Climate projects
- **Save to:** `data/life/`

---

### Digital Europe Programme Projects

- **URL:** https://digital-strategy.ec.europa.eu/en/activities/digital-programme
- **Note:** This programme started in 2021, project data may be limited
- **Alternative:** Search on EU Funding Portal and export results
- **Save to:** `data/digital_europe/`

---

### EU4Health Projects

- **URL:** https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en
- **Project search:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/eu4h
- **Note:** Export search results manually
- **Save to:** `data/eu4health/`

---

### Connecting Europe Facility (CEF) Projects

- **URL:** https://cinea.ec.europa.eu/programmes/connecting-europe-facility_en
- **Project maps/data:**
  - Transport: https://ec.europa.eu/transport/infrastructure/tentec/tentec-portal/map/maps.html
  - Energy: https://energy.ec.europa.eu/topics/infrastructure_en
- **Save to:** `data/cef/`

---

### European Defence Fund Projects

- **URL:** https://defence-industry-space.ec.europa.eu/eu-defence-industry/european-defence-fund-edf_en
- **Note:** Limited public data due to defence sensitivity
- **Save to:** `data/edf/`

---

### CERV (Citizens, Equality, Rights and Values) Projects

- **URL:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/cerv
- **Note:** Search and export from portal
- **Save to:** `data/cerv/`

---

## 2. Programme Guides & Rules

These PDF documents contain eligibility rules, funding rates, consortium requirements, and application procedures. Essential for the agent's knowledge base.

### Erasmus+ Programme Guide 2025

- **URL:** https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide
- **Direct PDF:** https://erasmus-plus.ec.europa.eu/document/erasmus-programme-guide-2025
- **Pages:** ~400 pages
- **Contains:** All rules, eligibility, action types, funding rates
- **Save to:** `data/erasmus/guides/erasmus_programme_guide_2025.pdf`

---

### Creative Europe Programme Guide

- **URL:** https://culture.ec.europa.eu/creative-europe/creative-europe-programme-guide
- **Contains:** CULTURE, MEDIA, Cross-sectoral strand rules
- **Save to:** `data/creative_europe/guides/`

---

### LIFE Programme Guide

- **URL:** https://cinea.ec.europa.eu/programmes/life/life-calls-proposals_en
- **Look for:** "Guide for Applicants" or "Programme Guide"
- **Contains:** SAP, SIP, Standard Action Projects rules
- **Save to:** `data/life/guides/`

---

### Digital Europe Programme Guide

- **URL:** https://digital-strategy.ec.europa.eu/en/activities/digital-programme
- **Look for:** Work Programme and application guidance
- **Save to:** `data/digital_europe/guides/`

---

### EU4Health Programme Guide

- **URL:** https://health.ec.europa.eu/funding/eu4health-programme-2021-2027/eu4health-work-programme_en
- **Contains:** Annual work programmes with call topics
- **Save to:** `data/eu4health/guides/`

---

### Horizon Europe Programme Guide (Reference)

- **URL:** https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf
- **You may already have this**
- **Save to:** `newdocs/` (your existing docs folder)

---

## 3. Work Programmes

Work Programmes define the specific call topics, budgets, and deadlines for each year.

### Horizon Europe Work Programmes

- **URL:** https://research-and-innovation.ec.europa.eu/funding/funding-opportunities/funding-programmes-and-open-calls/horizon-europe/horizon-europe-work-programmes_en
- **Download:** 2025-2027 Work Programmes for each cluster
- **Save to:** `newdocs/work_programmes/`

---

### Erasmus+ Annual Work Programme

- **URL:** https://erasmus-plus.ec.europa.eu/resources-and-tools/key-documents
- **Look for:** "Annual Work Programme 2025"
- **Save to:** `data/erasmus/work_programmes/`

---

### LIFE Multiannual Work Programme

- **URL:** https://cinea.ec.europa.eu/programmes/life/life-calls-proposals_en
- **Contains:** 2021-2024 and 2025-2027 priorities
- **Save to:** `data/life/work_programmes/`

---

### Digital Europe Work Programme

- **URL:** https://digital-strategy.ec.europa.eu/en/activities/work-programmes-digital
- **Save to:** `data/digital_europe/work_programmes/`

---

## 4. Reference Data

### CORDIS Reference Data (All Programmes)

- **URL:** https://data.europa.eu/data/datasets/cordisref-data
- **Contains:**
  - Programme codes
  - Topic keywords
  - Funding schemes / Action types
  - Organisation types
  - Country codes
- **Format:** CSV, Excel
- **Save to:** `data/reference/`

---

### EU Funding Portal Topic List

- **URL:** https://ec.europa.eu/info/funding-tenders/opportunities/data/topic-list.html
- **Contains:** All topic codes across all programmes
- **Format:** HTML (can be scraped)
- **Note:** This is a machine-readable list of all call topics

---

## 5. Suggested Folder Structure

After downloading, organize files like this:

```
data/
├── cordis/                          # ✅ Already exists (Horizon Europe)
│   ├── project.csv
│   ├── organization.csv
│   └── topics.csv
│
├── erasmus/                         # 📥 Download these
│   ├── projects/
│   │   ├── ka1_mobility_2021-2027.xlsx
│   │   ├── ka2_partnerships_2021-2027.xlsx
│   │   └── jean_monnet_2021-2027.xlsx
│   ├── guides/
│   │   └── erasmus_programme_guide_2025.pdf
│   └── work_programmes/
│       └── annual_work_programme_2025.pdf
│
├── creative_europe/                 # 📥 Download these
│   ├── projects/
│   │   ├── culture_projects.xlsx
│   │   └── media_projects.xlsx
│   └── guides/
│       └── creative_europe_guide.pdf
│
├── life/                            # 📥 Download these
│   ├── projects/
│   │   └── life_projects_export.xlsx
│   ├── guides/
│   │   └── life_applicant_guide.pdf
│   └── work_programmes/
│       └── life_mawp_2021-2027.pdf
│
├── digital_europe/                  # 📥 Download these
│   ├── projects/
│   │   └── digital_europe_projects.xlsx
│   ├── guides/
│   │   └── digital_europe_guide.pdf
│   └── work_programmes/
│       └── digital_work_programme_2025.pdf
│
├── eu4health/                       # 📥 Download these
│   ├── projects/
│   │   └── eu4health_projects.xlsx
│   └── guides/
│       └── eu4health_guide.pdf
│
├── cef/                             # 📥 Download these
│   └── projects/
│       └── cef_projects.xlsx
│
├── cerv/                            # 📥 Download these
│   └── projects/
│       └── cerv_projects.xlsx
│
└── reference/                       # 📥 Download these
    ├── cordis_reference_data.csv
    └── programme_codes.csv
```

---

## 6. Download Checklist

Use this checklist to track your downloads:

### Priority 1 (Essential)

- [ ] **Erasmus+ Projects** - https://erasmus-plus.ec.europa.eu/projects/projects-lists
- [ ] **Erasmus+ Programme Guide 2025** - https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide
- [ ] **Creative Europe Projects** - https://culture.ec.europa.eu/creative-europe/projects/projects-lists
- [ ] **LIFE Projects** - https://life-datahub.eismea.eu/
- [ ] **LIFE Programme Guide** - https://cinea.ec.europa.eu/programmes/life/life-calls-proposals_en

### Priority 2 (Important)

- [ ] **Digital Europe Guide** - https://digital-strategy.ec.europa.eu/en/activities/digital-programme
- [ ] **EU4Health Projects & Guide** - https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en
- [ ] **CORDIS Reference Data** - https://data.europa.eu/data/datasets/cordisref-data

### Priority 3 (Nice to Have)

- [ ] **CEF Projects** - https://cinea.ec.europa.eu/programmes/connecting-europe-facility_en
- [ ] **CERV Projects** - Portal search export
- [ ] **EDF Projects** - Limited availability

---

## 7. After Downloading

Once you have the files, let me know and I can:

1. **Create ingestion scripts** to load the CSV/Excel data into the database
2. **Create PDF processing** to chunk and embed the programme guides
3. **Update the agent's knowledge** with programme-specific information
4. **Add new tools** for searching across all programmes

---

## Notes

- **File sizes:** Most Excel files are 1-50MB, PDFs are 1-20MB each
- **Updates:** CORDIS data is updated monthly, download fresh copies periodically
- **Formats:** Prefer CSV over Excel when available (faster to process)
- **Languages:** Download English versions for consistency

---

*Last updated: December 2024*

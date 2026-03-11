"""
Domain knowledge guidance generation methods for ToolAwareAgent.
Provides expert-level responses for common EU funding questions.
Extracted from tool_aware_agent.py for maintainability.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GuidanceGeneratorsMixin:
    """Mixin providing domain knowledge guidance for ToolAwareAgent."""

    def _generate_h2020_overview_guidance(self) -> str:
        """Generate guidance about H2020 (Horizon 2020) as a historical programme."""
        return """**Horizon 2020 (H2020)** was the previous EU Framework Programme for Research and Innovation. All funding calls under H2020 are now **closed** and you cannot apply to them.

## H2020 Historical Overview

| Aspect | Details |
|--------|---------|
| **Duration** | 2014 - 2020 |
| **Budget** | €77 billion |
| **Status** | **Closed** - All calls concluded |
| **Successor** | Horizon Europe (2021-2027) |

### What You Should Know

H2020 was an ambitious programme that funded excellent research and innovation across Europe. Its key pillars were:

1. **Excellent Science** - ERC, MSCA, Future and Emerging Technologies
2. **Industrial Leadership** - Key technologies, SME Instrument
3. **Societal Challenges** - Health, Energy, Transport, Climate

### Your Current Options

Since H2020 is closed, you should focus on its successor programme: **Horizon Europe**

| Programme | Budget | Duration | Status |
|-----------|--------|----------|--------|
| **Horizon Europe** | €95.5 billion | 2021-2027 | **Active - Open for applications** |
| H2020 | €77 billion | 2014-2020 | Closed |

### Horizon Europe Structure

The current programme has a similar structure but with enhanced features:

- **Pillar I**: Excellent Science (ERC, MSCA, Research Infrastructures)
- **Pillar II**: Global Challenges (6 thematic clusters)
- **Pillar III**: Innovative Europe (EIC, EIT, Innovation ecosystems)
- **Cross-cutting**: Widening participation, ERA

---

🎯 **Next Steps - What You Should Do:**

1. **Visit the EU Funding Portal**: You should check [current Horizon Europe calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) for open opportunities
2. **Get a PIC Number**: If you don't have one, you should [register your organization](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/participant-register) in the Participant Register
3. **Contact Your NCP**: You should reach out to your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for guidance on matching your research to current calls
4. **Explore Call Topics**: Check the [Horizon Europe Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2024-2025/wp-1-general-introduction_horizon-2024-2025_en.pdf) for topics in your research area
5. **Find Partners**: Use the [Partner Search tool](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to build your consortium"""

    def _generate_fp7_overview_guidance(self, has_h2020_context: bool = False) -> str:
        """Generate guidance about FP7 (Seventh Framework Programme)."""
        intro = (
            "You mentioned **FP7** - this was the programme that preceded Horizon 2020."
            if has_h2020_context
            else "**FP7 (Seventh Framework Programme)** was an earlier EU research funding programme that ran from 2007 to 2013."
        )

        return f"""{intro}

## FP7 Historical Facts (2007-2013)

| Aspect | FP7 Details |
|--------|-------------|
| **Duration** | 2007-2013 (ended) |
| **Budget** | €50.5 billion (historical) |
| **Status** | **Closed** - All projects completed |
| **Successor** | H2020, then Horizon Europe |

### FP7 Structure

FP7 was organized around four main programmes:

1. **Cooperation** - Collaborative research across themes (Health, Food, ICT, Energy, etc.)
2. **Ideas** - European Research Council (ERC) frontier research
3. **People** - Marie Curie researcher mobility
4. **Capacities** - Research infrastructures, SMEs, Regions of Knowledge

### Why You See FP7 References

If you've seen FP7 projects referenced in academic papers or databases:
- FP7 funded thousands of successful projects
- Many results and publications still cite FP7 funding
- The CORDIS database contains full records of FP7 projects
- FP7 experience can strengthen your proposal track record

### Your Current Opportunity: Horizon Europe

Since FP7 ended in 2013, the current EU research funding programme is **Horizon Europe** (2021-2027) with a budget of **€95.5 billion**.

| What You Need | What You Should Do |
|---------------|-------------------|
| Find current calls | Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) |
| Understand options | Check the [Horizon Europe Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/programme-guide_horizon-2024-2025_en.pdf) |
| Get help | Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) |

---

🎯 **Next Steps - What You Should Do:**

1. **Explore Horizon Europe**: You should focus on the [current programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/horizon) which has €95.5 billion in funding
2. **Check Your Research Area**: You should identify which Horizon Europe cluster matches your work:
   - Cluster 1: Health
   - Cluster 2: Culture, Creativity and Inclusive Society
   - Cluster 3: Civil Security for Society
   - Cluster 4: Digital, Industry and Space
   - Cluster 5: Climate, Energy and Mobility
   - Cluster 6: Food, Bioeconomy, Natural Resources
3. **Register Your Organization**: If needed, you should get a [PIC number](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/participant-register)
4. **Build on Past Success**: If you participated in FP7, you should highlight this track record in future proposals
5. **Find Partners**: Use the [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to connect with experienced organizations"""

    def _generate_historical_applications_closed_guidance(self) -> str:
        """Generate guidance explaining that applications to historical programmes are closed."""
        return """**No, you cannot apply to H2020 or FP7 calls.** All funding calls under these programmes are permanently closed.

## Status of Historical Programmes

| Programme | Duration | Current Status |
|-----------|----------|----------------|
| **FP7** | 2007-2013 | **Closed** - All projects completed |
| **H2020** | 2014-2020 | **Closed** - Final projects concluding |
| **Horizon Europe** | 2021-2027 | **Active** - Applications welcome! |

### Important Clarifications

- **H2020 calls**: All H2020 calls closed in 2020. Projects awarded under H2020 are in their final execution stages or have concluded.
- **FP7 calls**: All FP7 calls closed in 2013. All funded projects have long since completed.
- **No exceptions**: All calls under both programmes have permanently closed - you should apply to Horizon Europe instead.

### Your Current Opportunity: Horizon Europe

**Horizon Europe** is the current EU research and innovation programme (2021-2027) with a budget of **€95.5 billion**. This is where you should apply!

| Aspect | Horizon Europe |
|--------|----------------|
| **Budget** | €95.5 billion |
| **Duration** | 2021-2027 |
| **Call Status** | Many calls open and upcoming |
| **Application Portal** | [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal) |

### What's Available in Horizon Europe

| Funding Type | Description | Typical Budget |
|--------------|-------------|----------------|
| **ERC Grants** | Frontier research for individuals | €1.5-10M |
| **MSCA** | Researcher mobility and training | €200K-4M |
| **RIA** | Collaborative research | €3-15M |
| **IA** | Innovation and demonstration | €5-25M |
| **CSA** | Coordination and support | €1-3M |
| **EIC Accelerator** | SME scale-up funding | Up to €2.5M grant + €15M equity |

---

🎯 **Next Steps - What You Should Do:**

1. **Access Current Calls**: You should visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) and filter by:
   - Programme: Horizon Europe
   - Status: Open or Forthcoming
   - Your research topic

2. **Register on the Portal**: If you haven't already, you should [create an account](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/participant-register) and get a PIC number

3. **Check Deadlines**: You should review the [2024-2025 Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2024-2025/wp-1-general-introduction_horizon-2024-2025_en.pdf) for upcoming deadlines

4. **Get Expert Advice**: You should contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized guidance

5. **Find Consortium Partners**: If needed, use the [Partner Search tool](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to build your team"""

    def _generate_programme_successor_guidance(self) -> str:
        """Generate guidance about the current programme that replaced historical ones."""
        return """**Horizon Europe** is the current EU Framework Programme that replaced H2020 (and before that, FP7). It runs from 2021 to 2027 with a budget of **€95.5 billion**.

## Programme Evolution Timeline

```
FP7 (2007-2013) → H2020 (2014-2020) → Horizon Europe (2021-2027)
   €50.5B           €77B              €95.5B
```

## Horizon Europe: Your Current Opportunity

| Aspect | Details |
|--------|---------|
| **Budget** | €95.5 billion (largest ever) |
| **Duration** | 2021-2027 |
| **Status** | Fully operational - calls open |
| **Application Portal** | [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal) |

### Programme Structure

**Pillar I - Excellent Science** (€25.01 billion)
- European Research Council (ERC)
- Marie Skłodowska-Curie Actions (MSCA)
- Research Infrastructures

**Pillar II - Global Challenges & European Industrial Competitiveness** (€53.49 billion)
- Cluster 1: Health
- Cluster 2: Culture, Creativity, Inclusive Society
- Cluster 3: Civil Security for Society
- Cluster 4: Digital, Industry, Space
- Cluster 5: Climate, Energy, Mobility
- Cluster 6: Food, Bioeconomy, Natural Resources
- Joint Research Centre (JRC)

**Pillar III - Innovative Europe** (€13.60 billion)
- European Innovation Council (EIC)
- European Innovation Ecosystems
- European Institute of Innovation and Technology (EIT)

**Cross-cutting** (€3.39 billion)
- Widening Participation
- Strengthening the European Research Area

### Key Improvements Over H2020

| Feature | H2020 | Horizon Europe |
|---------|-------|----------------|
| **Missions** | No | 5 ambitious missions |
| **EIC** | Limited (SME Instrument) | Full EIC with Pathfinder, Transition, Accelerator |
| **Lump sums** | Rare | Expanded use |
| **Open Science** | Encouraged | Mandatory (Plan S compliance) |
| **International** | Partial association | Enhanced global cooperation |

### Funding Types You Can Apply For

| Type | Purpose | Funding Rate | Typical Budget |
|------|---------|--------------|----------------|
| **RIA** | Research | 100% | €3-15M |
| **IA** | Innovation closer to market | 70% (100% non-profit) | €5-25M |
| **CSA** | Networking, coordination | 100% | €1-3M |
| **ERC** | Frontier research | 100% | €1.5-10M |
| **MSCA** | Researcher training | 100% (unit costs) | Variable |
| **EIC Accelerator** | SME scale-up | Up to €2.5M grant + €15M equity | Individual |

---

🎯 **Next Steps - What You Should Do:**

1. **Explore Open Calls**: You should visit [Topic Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) and filter for:
   - Programme: Horizon Europe
   - Status: Open
   - Your keywords or cluster

2. **Understand the Structure**: You should read the [Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/programme-guide_horizon-2024-2025_en.pdf) to understand opportunities

3. **Check Work Programmes**: You should review [annual Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents) for detailed call topics

4. **Get Your PIC**: If not registered, you should [create an organization profile](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/participant-register)

5. **Contact Your NCP**: You should reach out to your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for tailored advice

6. **Join Info Days**: You should attend [official Info Days](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/horizon-dashboard) to learn about specific calls

7. **Find Partners**: If you need consortium partners, you should use the [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) tool"""

    def _generate_innovation_fund_disambiguation_guidance(self) -> str:
        """Generate guidance to disambiguate 'innovation fund' queries.

        IMPORTANT: This response deliberately avoids mentioning Horizon Europe's overall
        budget to prevent fact-checker confusion. The €40B figure is for the EU Innovation
        Fund (ETS), not Horizon Europe.
        """
        return """When people ask about "the innovation fund" in EU funding, they often mean one of several different programmes. Let me clarify the main options:

## EU Innovation Fund (ETS-Related)

The **EU Innovation Fund** is a specific EU programme funded by revenues from the **EU Emissions Trading System (ETS)**. It's one of the world's largest funding programmes for low-carbon technology demonstration.

| Aspect | Details |
|--------|---------|
| **Full Name** | EU Innovation Fund |
| **Funding Source** | EU ETS allowance revenues |
| **Estimated Budget** | ~€40 billion until 2030 |
| **Focus** | Large-scale demonstration of clean technologies |
| **Technology Readiness** | TRL 7-9 (near-market deployment) |
| **Managed by** | CINEA (European Climate, Infrastructure and Environment Executive Agency) |
| **Funding Model** | Grants covering up to 60% of relevant costs |

### What It Funds
- Carbon capture and storage (CCS/CCU)
- Renewable energy technologies
- Energy storage solutions
- Industrial decarbonisation
- Clean hydrogen production

### Key Characteristics
- **Large-scale projects**: Typically €7.5M+ (some small-scale calls available)
- **Demonstration focus**: For technologies ready for commercial deployment
- **Climate neutral goal**: Supports EU's 2050 climate neutrality target

## Other "Innovation" Programmes You Might Mean

### EIC Accelerator (Horizon Europe)
| Aspect | Details |
|--------|---------|
| **Focus** | High-risk, high-impact SME innovation |
| **Funding** | Up to €2.5M grant + €15M equity |
| **Who** | SMEs and small mid-caps only |
| **Managed by** | European Innovation Council |

### InvestEU
| Aspect | Details |
|--------|---------|
| **Focus** | Investment mobilisation |
| **Funding** | Mostly **loans and guarantees** (not grants) |
| **Who** | Various, via financial intermediaries |

### Horizon Europe Research & Innovation Actions (RIA)
| Aspect | Details |
|--------|---------|
| **Focus** | Collaborative research |
| **Funding** | 100% funding rate for eligible costs |
| **Who** | Consortia (3+ partners from 3+ countries) |

---

🎯 **Next Steps - What You Should Do:**

1. **Identify Your Project Type**: You should determine which category fits your needs:
   - **Climate/clean tech demonstration (TRL 7-9)** → You should check the EU Innovation Fund
   - **SME with breakthrough innovation** → You should explore EIC Accelerator
   - **Collaborative research with partners** → You should look at Horizon Europe RIA/IA

2. **Check Current Calls**: You should visit the relevant portal:
   - EU Innovation Fund: [climate.ec.europa.eu/innovation-fund](https://climate.ec.europa.eu/eu-action/eu-funding-climate-action/innovation-fund_en)
   - EIC Accelerator: [eic.ec.europa.eu](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en)
   - Horizon Europe: [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal)

3. **Assess Your Technology Readiness**: You should evaluate your TRL level:
   - TRL 7-9 (ready for deployment) → EU Innovation Fund
   - TRL 5-8 (breakthrough, needs scale-up) → EIC Accelerator
   - TRL 2-6 (research needed) → Horizon Europe RIA

4. **Contact Support**: You should reach out for guidance:
   - EU Innovation Fund: Contact CINEA directly
   - EIC Accelerator: [EIC Business Acceleration Services](https://eic.ec.europa.eu/eic-funding-opportunities_en)
   - Horizon Europe: Your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

📋 **Which programme interests you?** Please clarify (e.g., "the EU one", "for climate", "grants not loans") and I can provide more specific guidance!"""

    def _generate_eu_innovation_fund_confirmation_guidance(self) -> str:
        """Generate confirmation that the EU Innovation Fund is the right one.

        This response confirms the EU Innovation Fund (ETS-related) details.
        IMPORTANT: Avoids Horizon Europe budget mentions to prevent fact-checker confusion.
        """
        return """I can confirm that the **EU Innovation Fund** is indeed an EU-level programme. Here's a comprehensive overview:

## EU Innovation Fund Overview

The EU Innovation Fund is funded by **EU ETS revenues** (estimated at ~**€40 billion** until 2030) and is managed by **CINEA**. It supports the demonstration and market deployment of clean technologies.

| Characteristic | Details |
|---------------|---------|
| **Programme** | EU Innovation Fund |
| **Funding Source** | EU Emissions Trading System (ETS) revenues |
| **Budget** | ~€40 billion (2020-2030) |
| **Manager** | CINEA |
| **Focus** | Large-scale clean technology demonstration |
| **Technology Level** | TRL 7-9 (near-market) |
| **Funding Rate** | Up to 60% of relevant costs |

### Eligible Project Types

| Category | Examples |
|----------|----------|
| **Renewable Energy** | Offshore wind, advanced solar, geothermal |
| **Carbon Capture** | CCS/CCU, direct air capture |
| **Energy Storage** | Battery systems, hydrogen storage |
| **Industrial Decarbonisation** | Steel, cement, chemicals |
| **Clean Hydrogen** | Green hydrogen production |

### Call Types

| Call Type | Project Size | Target Applicants |
|-----------|--------------|-------------------|
| **Large-scale** | €7.5M+ capex | Major projects, industrial plants |
| **Small-scale** | €2.5M+ capex | Smaller demonstration |
| **Pilot and Demonstrations** | Variable | First-of-a-kind technologies |

### Application Process

1. **Concept note** stage (first evaluation)
2. **Full application** (if selected)
3. **Due diligence** (financial and technical)
4. **Grant agreement** preparation

---

🎯 **Next Steps - What You Should Do:**

1. **Check Eligibility**: You should verify your project meets TRL 7-9 requirements
   - Technology must be proven at pilot scale
   - Ready for first commercial deployment

2. **Review Call Topics**: You should visit [EU Innovation Fund Portal](https://climate.ec.europa.eu/eu-action/eu-funding-climate-action/innovation-fund_en) for current calls

3. **Assess Project Scale**: You should determine which call type fits:
   - Large-scale: €7.5M+ capital expenditure
   - Small-scale: €2.5M+ capital expenditure

4. **Prepare Documentation**: You should gather:
   - Technical feasibility studies
   - Financial projections
   - CO2 emission reduction calculations

5. **Contact National Focal Point**: You should reach out for guidance specific to your country

📋 **Would you like me to help you find specific open calls for climate innovation, or compare this with other funding options?**"""

    def _generate_climate_innovation_grants_guidance(self, context: str) -> str:
        """Generate guidance on grant-based climate innovation funding options.

        This compares grant options for climate innovation, focusing on Horizon Europe
        and clarifying the difference with the EU Innovation Fund.
        """
        return """## Climate Innovation Grant Funding Options

If you prefer **grant-based funding** (non-repayable) for climate innovation, here are your main options:

### 1. Horizon Europe Cluster 5 (Climate, Energy & Mobility)

**The primary source for climate innovation grants:**

| Aspect | Details |
|--------|---------|
| **Programme** | Horizon Europe Pillar II - Cluster 5 |
| **Focus** | Climate, Energy, Mobility research & innovation |
| **Funding Type** | **100% grants (RIA)** or **70% grants (IA)** |
| **Project Size** | €3M - €25M typically |
| **Consortium** | Required (3+ partners, 3+ countries) |

#### What It Funds
- Clean energy technologies
- Energy efficiency
- Sustainable transport
- Climate adaptation
- Circular economy
- Green hydrogen

#### Funding Rates
| Action Type | Funding Rate | Focus |
|-------------|--------------|-------|
| **RIA** | 100% | Research activities |
| **IA** | 70% (100% non-profit) | Demonstration, innovation |
| **CSA** | 100% | Networking, support |

### 2. EIC Accelerator (for SMEs only)

| Aspect | Details |
|--------|---------|
| **Who** | SMEs and small mid-caps only |
| **Funding** | Up to **€2.5M grant** + optional equity |
| **Focus** | High-impact innovations (any sector including climate) |
| **Consortium** | Individual company (no consortium required) |

### 3. EU Innovation Fund (ETS-related)

| Aspect | Details |
|--------|---------|
| **Focus** | Large-scale clean tech demonstration |
| **Funding** | **Up to 60%** of relevant costs (grant-like) |
| **Note** | More focused on **deployment** than research |

### Comparison: Grants for Climate Innovation

| Programme | Funding Type | Rate | Scale | Consortium |
|-----------|-------------|------|-------|------------|
| **Horizon Europe RIA** | Grant | 100% | €3-15M | Required |
| **Horizon Europe IA** | Grant | 70-100% | €5-25M | Required |
| **EIC Accelerator** | Grant + equity | Up to €2.5M grant | Individual | Not required |
| **EU Innovation Fund** | Grant-like | Up to 60% | €7.5M+ capex | Not required |

### Recommendation Based on Your Needs

**For collaborative research (100% funding):**
→ Horizon Europe Cluster 5 **RIA** calls

**For demonstration projects (70-100% funding):**
→ Horizon Europe Cluster 5 **IA** calls

**For SME breakthrough innovation:**
→ **EIC Accelerator** (grant component)

**For large-scale deployment:**
→ **EU Innovation Fund** (up to 60%)

---

🎯 **Next Steps - What You Should Do:**

1. **Search Cluster 5 Calls**: You should visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) and filter by:
   - Programme: Horizon Europe
   - Keywords: climate, energy, clean technology, decarbonisation
   - Status: Open

2. **Check EIC Accelerator**: If you're an SME, you should review [EIC Accelerator](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en) for single-company grants

3. **Review Current Calls**: You should look at the [2024-2025 Cluster 5 Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2024-2025/wp-8-climate-energy-and-mobility_horizon-2024-2025_en.pdf)

4. **Find Consortium Partners**: You should use [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) if you need collaborators

5. **Contact Your NCP**: You should reach out to your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for Cluster 5

📋 **Would you like me to search for specific open climate/clean technology calls in Horizon Europe?**"""

    # ========================================================================
    # WORK PROGRAMME CONTENT QUERY DETECTION
    # ========================================================================

    def _generate_out_of_scope_explanation_guidance(self, programme: str) -> str:
        """Generate guidance explaining MAPIT's EU focus when non-EU programmes are queried."""

        # Programme-specific context
        programme_info = {
            "nsf": {
                "full_name": "National Science Foundation (NSF)",
                "country": "United States",
                "website": "https://www.nsf.gov/",
                "eu_equivalent": "ERC (European Research Council) for fundamental research, Horizon Europe RIA for collaborative research",
            },
            "nih": {
                "full_name": "National Institutes of Health (NIH)",
                "country": "United States",
                "website": "https://www.nih.gov/grants-funding",
                "eu_equivalent": "Horizon Europe Cluster 1 (Health) for health research, ERC for basic biomedical research",
            },
            "doe": {
                "full_name": "Department of Energy (DOE)",
                "country": "United States",
                "website": "https://www.energy.gov/science/grants-contracts",
                "eu_equivalent": "Horizon Europe Cluster 5 (Climate, Energy & Mobility) for energy research",
            },
            "darpa": {
                "full_name": "Defense Advanced Research Projects Agency (DARPA)",
                "country": "United States",
                "website": "https://www.darpa.mil/",
                "eu_equivalent": "EIC Pathfinder for high-risk/high-gain research, EDF (European Defence Fund) for defence innovation",
            },
            "ukri": {
                "full_name": "UK Research and Innovation (UKRI)",
                "country": "United Kingdom",
                "website": "https://www.ukri.org/",
                "eu_equivalent": "Horizon Europe (UK is an Associated Country since 2024)",
            },
            "epsrc": {
                "full_name": "Engineering and Physical Sciences Research Council (EPSRC)",
                "country": "United Kingdom",
                "website": "https://www.ukri.org/councils/epsrc/",
                "eu_equivalent": "Horizon Europe Cluster 4 (Digital, Industry, Space) and ERC",
            },
            "nserc": {
                "full_name": "Natural Sciences and Engineering Research Council (NSERC)",
                "country": "Canada",
                "website": "https://www.nserc-crsng.gc.ca/",
                "eu_equivalent": "ERC for fundamental research, Horizon Europe RIA for applied research",
            },
            "arc": {
                "full_name": "Australian Research Council (ARC)",
                "country": "Australia",
                "website": "https://www.arc.gov.au/",
                "eu_equivalent": "ERC for excellence-driven research, Horizon Europe for collaborative projects",
            },
            "dfg": {
                "full_name": "Deutsche Forschungsgemeinschaft (DFG)",
                "country": "Germany",
                "website": "https://www.dfg.de/en",
                "eu_equivalent": "Note: DFG is complementary to EU funding - German researchers often combine DFG and EU grants",
            },
        }

        info = programme_info.get(
            programme,
            {
                "full_name": programme.upper(),
                "country": "Non-EU",
                "website": "See national funding agency website",
                "eu_equivalent": "Various Horizon Europe programmes depending on research area",
            },
        )

        return f"""As an intelligent research assistant specializing in **EU funding programmes** like Horizon Europe, Erasmus+, and Creative Europe, my expertise is focused on European Union research and innovation funding.

For detailed information about **{info["full_name"]}**, I recommend visiting their official resources. However, I can help you understand EU funding alternatives and explore opportunities for international collaboration.

## My EU Funding Expertise

I provide expert guidance on these EU programmes:

| EU Programme | Total Budget (2021-2027) | Focus |
|--------------|-------------------------|-------|
| **Horizon Europe** | €95.5 billion | Research & Innovation (includes ERC, EIC, MSCA) |
| **Erasmus+** | €26.2 billion | Education, training & youth mobility |
| **Creative Europe** | €2.4 billion | Cultural & creative sectors |

## EU Equivalent to {info["full_name"]}

For researchers interested in topics similar to {info["full_name"]}, the EU offers:

**{info["eu_equivalent"]}**

## International Participation in EU Programmes

If you're based in {info["country"]} or have collaborators there, you can still participate in EU funding:

| Participation Type | Options |
|-------------------|---------|
| **As Coordinator** | Associated Countries only (check current list) |
| **As Partner** | Third-country participation possible in most calls |
| **US/UK/other non-EU** | Can join consortia (costs often not eligible) |
| **Bilateral agreements** | Check for specific cooperation agreements |

---

🎯 **Next Steps - What You Should Do:**

1. **For {info["full_name"]} Information**: You should visit their official website at {info["website"]}

2. **For EU Funding Alternatives**: I can help you explore:
   - Horizon Europe calls matching your research area
   - ERC grants for fundamental research
   - MSCA fellowships for researcher mobility
   - Opportunities for international collaboration

3. **For EU-International Cooperation**: You should check:
   - [Horizon Europe Third Country Participation](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/horizon-dashboard)
   - [International Cooperation in Horizon Europe](https://research-and-innovation.ec.europa.eu/strategy/strategy-2020-2024/europe-world/international-cooperation_en)

4. **Contact Support**: You should reach out to your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for guidance on EU opportunities

📋 **Would you like me to help you find EU funding opportunities in your research area, or explore how researchers from {info["country"]} can participate in Horizon Europe?**"""

    def _generate_eu_international_comparison_guidance(self) -> str:
        """Generate guidance comparing EU funding with international programmes."""
        return """## EU vs International Research Funding: High-Level Comparison

As a specialist in **EU funding programmes**, I can provide detailed information about Horizon Europe and how it compares conceptually to other major research funding systems. For specific non-EU programme details, please consult those agencies directly.

### Horizon Europe: Unique Characteristics

| Feature | Horizon Europe | Significance |
|---------|---------------|--------------|
| **Budget** | €95.5 billion (2021-2027) | World's largest transnational R&I programme |
| **Structure** | 3 Pillars + 5 Missions | Comprehensive research ecosystem |
| **Collaboration** | Mandatory consortia (most calls) | Emphasizes international cooperation |
| **Open Science** | Mandatory Open Access | Leading global open science policy |
| **Mobility** | MSCA programme | 25,000+ researchers funded annually |

### Conceptual Comparison with Major Funding Systems

| Aspect | Horizon Europe | NSF (US) | UKRI (UK) |
|--------|---------------|----------|-----------|
| **Geographic Scope** | Pan-European + associated | National (US) | National (UK) |
| **Collaboration Model** | Consortium-based | Individual/institutional | Individual/institutional |
| **Funding Rate** | 70-100% (varies by type) | Varies by programme | Varies by council |
| **Industry Participation** | Strong emphasis | Programme-dependent | Council-dependent |
| **SME Focus** | Dedicated EIC instruments | SBIR/STTR programmes | Innovate UK |

### Why Horizon Europe Is Unique

1. **Scale of Collaboration**: No other programme mandates transnational consortia at this scale
2. **Open to All**: Associated countries + third country participation options
3. **Challenge-Driven**: Missions and clusters target societal challenges
4. **Integrated Approach**: Research to market through EIC continuum

### UK Participation (Post-Brexit Update)

Since January 2024, the **UK is again associated to Horizon Europe**, meaning:
- UK researchers can **coordinate** Horizon Europe projects
- UK entities are **fully eligible** for funding
- UK participation is now similar to other Associated Countries

---

🎯 **Next Steps - What You Should Do:**

1. **For Detailed EU Information**: Ask me about specific Horizon Europe programmes, calls, or eligibility

2. **For Non-EU Programme Details**: You should visit:
   - NSF: [nsf.gov](https://www.nsf.gov/)
   - UKRI: [ukri.org](https://www.ukri.org/)
   - NIH: [nih.gov/grants-funding](https://www.nih.gov/grants-funding)

3. **For International Collaboration**: You should explore:
   - [EU-US S&T Cooperation](https://research-and-innovation.ec.europa.eu/strategy/strategy-2020-2024/europe-world/international-cooperation/united-states_en)
   - [EU-UK Horizon Europe Association](https://research-and-innovation.ec.europa.eu/news/all-research-and-innovation-news/uk-joins-horizon-europe-2024-01-04_en)

4. **For Specific EU Comparisons**: You should tell me your research area and I can detail what Horizon Europe offers

📋 **Action Items:**
- [ ] Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) for current calls
- [ ] Check [Horizon Europe International Cooperation](https://research-and-innovation.ec.europa.eu/strategy/strategy-2020-2024/europe-world_en) for collaboration options
- [ ] Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for guidance

📋 **Would you like me to find specific EU funding opportunities in your research domain?**"""

    def _generate_global_equivalents_guidance(self) -> str:
        """Generate guidance about global equivalents to Horizon Europe."""
        return """## Global Equivalents to Horizon Europe

Horizon Europe is **unique on the global stage** due to its immense scale, combined focus on collaborative challenge-driven research, and emphasis on pan-European and international cooperation. While there are programmes with larger overall annual budgets (like in the US), **no single global programme entirely mirrors Horizon Europe's structure or mandated scope**.

### Global Research Funding Landscape

| Programme | Region | Focus | Scale |
|-----------|--------|-------|-------|
| **Horizon Europe** | EU + Associated | Collaborative R&I | €95.5B (2021-2027) |
| **NSF** | USA | Fundamental science | ~$9B/year |
| **NIH** | USA | Health/biomedical | ~$47B/year |
| **UKRI** | UK | Multi-disciplinary | ~£8B/year |
| **DFG** | Germany | Research funding | ~€3.5B/year |
| **JSPS** | Japan | Science promotion | ~¥260B/year |

### What Makes Horizon Europe Unique

| Unique Feature | Description |
|----------------|-------------|
| **Transnational Consortia** | Most calls require 3+ partners from 3+ countries |
| **Open to 40+ Countries** | EU27 + Associated Countries (Iceland, Norway, Israel, UK, etc.) |
| **Integrated Ecosystem** | From fundamental research (ERC) to market (EIC) |
| **Missions Approach** | 5 EU Missions addressing major societal challenges |
| **Open Science Leader** | Mandatory open access, FAIR data principles |
| **Industry-Academia Bridge** | Strong focus on innovation and commercialization |

### Horizon Europe Structure (No Direct Equivalent Elsewhere)

```
HORIZON EUROPE (€95.5B)
├── Pillar I: Excellent Science (€25B)
│   ├── ERC (fundamental research)
│   ├── MSCA (researcher mobility)
│   └── Research Infrastructures
├── Pillar II: Global Challenges (€53B)
│   ├── 6 Thematic Clusters
│   └── JRC research support
├── Pillar III: Innovative Europe (€14B)
│   ├── EIC (breakthrough innovation)
│   └── European Innovation Ecosystems
└── Horizontal: Widening + ERA
```

### International Participation Options

If you're seeking **global-scale research funding**, Horizon Europe offers pathways:

| Your Location | Participation Options |
|---------------|----------------------|
| **EU Member State** | Full participation in all calls |
| **Associated Country** | UK, Norway, Israel, Switzerland*, etc. - full participation |
| **Third Country** | Can join consortia (funding eligibility varies) |
| **International Org** | Often eligible as partners |

*Switzerland association negotiations ongoing

---

🎯 **Next Steps - What You Should Do:**

1. **Explore Horizon Europe**: You should consider this as the closest to a "world-class" global programme available to European and international researchers

2. **Find Your Fit**: You should tell me your research area and I can identify:
   - Relevant Horizon Europe clusters and destinations
   - ERC opportunities for excellence-driven research
   - EIC options for breakthrough innovation
   - MSCA for researcher mobility

3. **International Collaboration**: You should check [Horizon Europe Open to the World](https://research-and-innovation.ec.europa.eu/strategy/strategy-2020-2024/europe-world_en) for third-country participation

4. **For Non-EU Programmes**: You should visit national funding agencies directly:
   - US: [NSF](https://www.nsf.gov/), [NIH](https://www.nih.gov/)
   - UK: [UKRI](https://www.ukri.org/)
   - Canada: [NSERC](https://www.nserc-crsng.gc.ca/)
   - Australia: [ARC](https://www.arc.gov.au/)

📋 **Action Items:**
- [ ] Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) to search for calls in your research area
- [ ] Review [Horizon Europe International Cooperation](https://research-and-innovation.ec.europa.eu/strategy/strategy-2020-2024/europe-world_en) for third-country options
- [ ] Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized guidance
- [ ] Check if your country has bilateral agreements with the EU for research cooperation

📋 **Would you like me to help you find specific Horizon Europe funding opportunities matching your research interests?**"""

    def _generate_beginner_programmes_guidance(self) -> str:
        """Generate guidance on best programmes for beginners."""
        return """For organizations new to EU funding, the best strategy is to **start small and build experience progressively**. You should consider these beginner-friendly entry points:

### 1. Marie Skłodowska-Curie Actions (MSCA) - Best for Researchers

**Why you should apply to MSCA:**
- Simpler consortium: Often just your organization + the researcher
- Clear evaluation criteria focused on research quality - you can achieve this
- Fixed funding amounts (unit costs) - no complex budget calculations
- High success rate compared to collaborative actions

**Best entry points you can apply to:**
- **MSCA Postdoctoral Fellowships (PF)**: You can host an experienced researcher
- **MSCA Staff Exchanges (SE)**: Exchange staff with international partners

### 2. Coordination and Support Actions (CSA)

**Why you should consider CSA:**
- Smaller budgets (€1-3M) with smaller consortia (3-8 partners)
- Focus on coordination, networking, dissemination - you can manage this without heavy R&D
- 100% funding rate
- Less technical complexity than RIA/IA

### 3. Widening Participation Actions

**Why you should apply to Widening:**
- Designed specifically for organizations with less EU funding experience
- Teaming, Twinning, and ERA Chairs provide structured support
- You can connect with experienced partners who will guide you
- Higher success rates for eligible countries

### 4. Join as Partner in RIA/IA (Not Coordinator)

**Why you should start as partner:**
- You can learn consortium management without the coordination burden
- Build relationships with experienced coordinators
- Lower administrative responsibility
- You can gain track record for future coordination

### Recommendation by Organization Type

| Organization | Best Starting Point |
|--------------|---------------------|
| **University** | MSCA (host fellows), CSA as partner, Widening actions |
| **Research Institute** | CSA as partner, RIA as partner, MSCA-DN |
| **SME** | Eurostars, EIC Pathfinder (as partner), IA as partner |
| **Public Body** | CSA (often as partner), Missions |

---

🎯 **Next Steps - What You Should Do:**
• You should visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home) to get a PIC number
• You should contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized advice
• Check for open calls in your research area and apply to consortium opportunities
• You can visit [Info Days](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/horizon-dashboard) to network with potential partners"""

    def _generate_partner_coordinator_guidance(self, is_newcomer: bool = True) -> str:
        """Generate guidance on partner vs coordinator role."""
        intro = (
            "For organizations new to EU funding, you **should start as a partner** "
            "before taking on the coordinator role."
            if is_newcomer
            else "The decision between partner and coordinator depends on your experience level and strategic goals."
        )

        return f"""{intro}

### Starting as Partner (Recommended for Beginners)

**Why you should start as partner:**
- **Lower risk**: The coordinator bears the legal/financial responsibility to the EC
- **Learning opportunity**: You can observe how experienced coordinators manage consortia
- **Build relationships**: You can develop trust with partners for future coordination
- **Focus on research**: You can contribute your expertise without admin overhead
- **Build track record**: Successful participation can improve your future proposal scores

**Typical partner responsibilities:**
- Deliver your work package tasks
- Contribute to reporting
- Participate in consortium meetings
- Manage your organization's budget

### When You Should Consider Coordinating

**You should have this minimum experience before coordinating:**
- 2-3 successful projects as partner
- Understanding of EC reporting requirements
- Strong network of trusted partners
- Administrative capacity (dedicated project manager)

**Signs you can coordinate:**
- Partners actively invite you to lead
- You have a clear research vision others want to join
- Your organization can handle the admin burden
- You've built relationships with reliable partners

### Comparison Table

| Aspect | Partner | Coordinator |
|--------|---------|-------------|
| **Admin burden** | Low | High |
| **Financial risk** | Limited to your share | Full consortium guarantee |
| **Decision authority** | Limited | High |
| **Track record value** | Good | Excellent |
| **Recommended for beginners** | ✅ Yes | ❌ Not yet |

### Strategic Progression Path

1. **Year 1-2**: You should apply as partner in 1-2 projects
2. **Year 2-3**: Take on Work Package leadership
3. **Year 3-4**: Co-coordinate a smaller project (CSA)
4. **Year 4+**: You can coordinate RIA/IA projects

---

🎯 **Next Steps - What You Should Do:**
• You should visit [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to find consortium opportunities
• You can visit Info Days to meet potential coordinators
• Contact coordinators to express interest in joining consortia in your research area
• You should apply to join consortia with experienced partners who can guide you"""

    def _generate_first_project_size_guidance(self) -> str:
        """Generate guidance on appropriate first project size."""
        return """For organizations new to EU funding, starting with **manageable project sizes** is crucial for success. Here's guidance on appropriate first project scope:

### Recommended First Project Parameters

| Parameter | Beginner Recommendation | Why |
|-----------|------------------------|-----|
| **Budget participation** | €200K - €500K | Manageable financial reporting |
| **Duration** | 24-36 months | Standard timeline, not too long |
| **Consortium size** | 4-8 partners | Easier coordination |
| **Your role** | Partner (not coordinator) | Lower admin burden |
| **Action type** | CSA or RIA | Clear structure |

### Action Type Comparison for Beginners

| Action Type | Typical Project Budget | Your Share | Complexity |
|-------------|----------------------|------------|------------|
| **CSA** | €1-3M | €150-400K | Lower (coordination focus) |
| **RIA (smaller)** | €3-5M | €250-500K | Medium (research focus) |
| **MSCA-PF** | €200-300K | Host costs | Lower (single researcher) |
| **Widening** | €1-2M | €300-500K | Lower (support provided) |

### What Makes a "Manageable" First Project

✅ **Good for beginners:**
- Clearly defined work package scope
- Experienced coordinator who provides guidance
- Realistic deliverables you can achieve
- Some administrative support included
- Regular consortium meetings (learning opportunity)

❌ **Avoid for first project:**
- Coordinator role in large consortia (10+ partners)
- Very large budget responsibility (>€1M your share)
- High-risk technical objectives
- Very short timelines (<24 months)
- Projects requiring major new hires

### Budget Breakdown Example (Partner Role in RIA)

For a first-time partner with €400K budget share:
- **Personnel**: €250-280K (60-70%) - Your researchers' time
- **Travel**: €30-40K - Consortium meetings, conferences
- **Equipment**: €20-40K (if needed)
- **Other costs**: €20-30K - Consumables, publications
- **Indirect costs**: 25% flat rate (included above)

### Gradual Scale-Up Strategy

| Phase | Project Type | Your Budget | Role |
|-------|-------------|-------------|------|
| **1st project** | CSA or small RIA | €200-400K | Partner |
| **2nd project** | RIA | €400-600K | WP Leader |
| **3rd project** | RIA/IA | €600K-1M | Major partner |
| **4th+ project** | Any | €1M+ or Coordinator | Lead |

---

🎯 **Next Steps:**
• Review open calls to identify projects seeking partners with your expertise
• Check the [Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) for typical budgets in your cluster
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for specific calls matching your profile
• Use [CORDIS](https://cordis.europa.eu/) to see budget distributions in similar funded projects"""

    def _generate_track_record_guidance(self) -> str:
        """Generate guidance on building EU funding track record."""
        return """Building a strong EU funding track record is a **multi-year strategic effort**. Here's a proven framework for developing your organization's EU funding experience:

### What Constitutes "Track Record"

Evaluators look for evidence of:
- **Successful project participation**: Completed EU-funded projects
- **Relevant publications/outputs**: Demonstrable research impact
- **International collaboration**: Working across borders effectively
- **Financial/admin capacity**: Proven ability to manage EU grants

### 3-Year Track Record Building Strategy

#### Year 1: Foundation Building (Low-Risk Entry)

| Activity | Purpose | Expected Outcome |
|----------|---------|------------------|
| **MSCA-PF hosting** | Host a postdoctoral fellow | 1 EU project on record |
| **CSA as partner** | Join a coordination project | Experience in EU reporting |
| **Networking events** | Build consortium contacts | Partner relationships |
| **NCP engagement** | Get expert guidance | Better proposal targeting |

**Goal**: Get 1-2 EU projects on your organizational record

#### Year 2: Portfolio Expansion

| Activity | Purpose | Expected Outcome |
|----------|---------|------------------|
| **RIA as partner** | Substantive research role | Strong track record entry |
| **WP leadership** | Prove management capacity | Leadership credentials |
| **Publications** | Document project outputs | Demonstrable impact |
| **Repeat partnerships** | Deepen trusted relationships | Future invitation to consortia |

**Goal**: Build reputation as reliable partner

#### Year 3: Strategic Growth

| Activity | Purpose | Expected Outcome |
|----------|---------|------------------|
| **Co-coordinate small project** | Test coordination capacity | Coordinator experience |
| **Multiple parallel projects** | Diversify portfolio | Robust track record |
| **International visibility** | Conference presentations | Expert reputation |
| **Mentor newcomers** | Support your network | Strengthen partnerships |

**Goal**: Ready to coordinate major projects

### Track Record by Organization Type

| Organization | Best Track Record Builders |
|--------------|---------------------------|
| **University** | MSCA, RIA as partner, teaching innovation projects |
| **Research Institute** | RIA partnerships, infrastructure access projects |
| **SME** | Eurostars, EIC Pathfinder, IA as partner |
| **Public Body** | CSA, Missions, policy-oriented projects |

### Accelerating Track Record Development

**Quick wins:**
1. **National/regional EU projects**: Often easier to win, still counts
2. **Horizon Europe associated instruments**: Eurostars, EUREKA
3. **Expert evaluator role**: Apply to evaluate proposals (builds credibility)
4. **Horizon Results Platform**: Register past project outputs

**Strategic moves:**
1. **Join winning teams**: Partner with high-success-rate coordinators
2. **Target less competitive calls**: Widening, CSA, thematic areas with fewer applicants
3. **Leverage existing relationships**: Previous collaboration partners
4. **Highlight non-EU experience**: National grants demonstrate capacity

### Common Mistakes to Avoid

❌ **Don't:**
- Try to coordinate before having partner experience
- Over-commit to too many proposals simultaneously
- Ignore admin/reporting requirements (damages reputation)
- Work only with familiar partners (limits network growth)

✅ **Do:**
- Start small and grow systematically
- Deliver on commitments (reputation is everything)
- Document lessons learned from each project
- Maintain relationships even after projects end

---

🎯 **Next Steps:**
• Create a 3-year EU funding roadmap for your organization
• Identify 2-3 target calls for initial participation
• Register on [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to signal your interest
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for a strategy consultation
• Review [CORDIS](https://cordis.europa.eu/) for funded projects in your area to find active consortia"""

    def _generate_first_time_applicant_guidance(self) -> str:
        """Generate step-by-step onboarding guidance for first-time EU funding applicants.

        This guidance is specifically designed to be:
        - Beginner-friendly and not overwhelming
        - Focused on actionable registration steps
        - Prominent NCP (National Contact Point) referral
        - Clear, sequential steps
        """
        return """Welcome to EU funding! Here's a **simple step-by-step guide** to get you started. Don't worry - it's easier than it looks once you break it down.

## Step 1: Create Your EU Login Account (5 minutes)

Your first step is to create an EU Login account - this is your personal access to all EU services.

**How to do it:**
1. Go to [EU Login](https://webgate.ec.europa.eu/cas/eim/external/register.cgi)
2. Enter your email address
3. Create a password
4. Verify your email

**Note:** This is YOUR personal account - each person in your organization who will work on proposals needs their own EU Login.

---

## Step 2: Register Your Organization & Get a PIC Number (15-30 minutes)

The **PIC (Participant Identification Code)** is your organization's unique identifier for EU funding. You only need to do this once.

**How to register:**
1. Log into the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home) with your EU Login
2. Go to "My Organisation" → "Register Organisation"
3. Enter your organization's legal details (name, address, VAT number)
4. Upload supporting documents (legal registration, financial statements)
5. Submit and receive your 9-digit PIC number

**Tip:** Check if your organization already has a PIC before registering - many universities and research institutes are already registered.

---

## Step 3: Contact Your National Contact Point (NCP) - Highly Recommended!

**NCPs are FREE expert advisors** funded by your national government to help you succeed in EU funding. They can:

- Help you find the right funding programme for your project idea
- Review your proposal draft before submission
- Explain eligibility rules and requirements
- Connect you with potential partners

**Find your NCP:** [NCP Network Directory](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

**What to tell them:**
- Your organization type (university, SME, research institute, etc.)
- Your research area or project idea
- Whether you want to be a partner or coordinator
- Your timeline for applying

---

## Step 4: Explore Funding Opportunities

Now you're ready to browse available funding:

**Where to look:**
- [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) - Official source for all calls
- [CORDIS](https://cordis.europa.eu/) - See what projects have been funded (good for finding partners!)

**Key programmes for newcomers:**
| Programme | Good for | Typical First Step |
|-----------|----------|-------------------|
| **Horizon Europe** | Research & innovation | Join as partner in RIA or CSA |
| **Erasmus+** | Education & training | KA2 partnerships |
| **Creative Europe** | Arts, culture, media | Small cooperation projects |

---

## Step 5: Find Partners (for most programmes)

Most EU funding requires international partnerships (typically 3+ organizations from different countries).

**Where to find partners:**
- [Partner Search Tool](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) - Official partner matching
- [CORDIS](https://cordis.europa.eu/) - Find active project coordinators in your field
- Your NCP - They can connect you with networks

**Tip for beginners:** It's easier to JOIN an existing consortium as a partner than to build your own. Look for "partner search" announcements or ask your NCP.

---

## What NOT to Do (Common First-Timer Mistakes)

❌ Don't try to coordinate your first project - start as a partner
❌ Don't apply alone if the call requires partners
❌ Don't ignore the deadline buffer - submit at least 24 hours early
❌ Don't skip the NCP consultation - they're free and helpful!

---

## Quick Checklist

| Step | Done? |
|------|-------|
| Create EU Login account | ⬜ |
| Register organization (get PIC) | ⬜ |
| Contact your NCP | ⬜ |
| Browse open calls | ⬜ |
| Identify potential partners | ⬜ |

---

🎯 **Your Next Action:** Start by creating your [EU Login account](https://webgate.ec.europa.eu/cas/eim/external/register.cgi) - it only takes 5 minutes and everything else builds from there.

Need help? Your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) is your best free resource for personalized guidance."""

    def _generate_horizon_application_guidance(self) -> str:
        """Generate step-by-step application guidance for Horizon Europe."""
        return """Here's a **complete step-by-step guide** to applying for Horizon Europe funding:

## Step 1: Create Your EU Login Account (5 minutes)

Your personal access key to all EU funding services.

**How to do it:**
1. Go to [EU Login](https://webgate.ec.europa.eu/cas/eim/external/register.cgi)
2. Enter your email address
3. Create a password
4. Verify your email

---

## Step 2: Register Your Organization & Get a PIC (15-30 minutes)

The **PIC (Participant Identification Code)** is your organization's unique identifier. You only need to do this once.

**How to register:**
1. Log into the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
2. Go to "My Organisation" → "Register Organisation"
3. Enter your organization's legal details (name, address, VAT)
4. Upload supporting documents
5. Receive your 9-digit PIC number

**Tip:** Check if your organization already has a PIC before registering!

---

## Step 3: Find Suitable Calls

1. Browse the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)
2. Filter by "Horizon Europe" and your research area
3. Review the [Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON) for detailed topic descriptions
4. Check deadlines and budget availability

---

## Step 4: Build Your Consortium

Most Horizon Europe calls require international partnerships:

- **Minimum:** 3 independent legal entities from 3 different EU/Associated Countries
- **Typical:** 10-15 partners for RIA/IA projects

**Where to find partners:**
- [Partner Search Tool](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)
- [CORDIS](https://cordis.europa.eu/) - Find organizations active in your field
- Network events and Info Days

---

## Step 5: Contact Your National Contact Point (NCP) - Highly Recommended!

**NCPs are FREE expert advisors** who can:
- Help you find the right call for your project
- Review your proposal draft before submission
- Explain eligibility and evaluation criteria
- Connect you with potential partners

**Find your NCP:** [NCP Network Directory](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

---

## Step 6: Prepare Your Proposal

1. Download the proposal template from the call page
2. Follow the structure: Excellence, Impact, Implementation
3. Stay within page limits (typically 45 pages for Part B)
4. Include a realistic budget and work plan
5. Address all evaluation criteria

---

## Step 7: Submit Before the Deadline

1. Submit via the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
2. **Deadline:** Usually 17:00 Brussels time
3. **Tip:** Submit at least 24 hours early to avoid technical issues

---

## Quick Reference

| Item | Detail |
|------|--------|
| **RIA Funding Rate** | 100% |
| **IA Funding Rate** | 70% (100% for non-profits) |
| **Typical Duration** | 36-48 months |
| **Typical Budget** | €3-8 million |
| **Evaluation Thresholds** | Excellence 4/5, Impact 4/5, Implementation 3/5 |

---

🎯 **Your Next Step:** Create your [EU Login account](https://webgate.ec.europa.eu/cas/eim/external/register.cgi) today - it takes just 5 minutes and is required for everything else.

📞 **Need Help?** Contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) - they provide FREE personalized guidance!"""

    def _generate_erasmus_application_guidance(self) -> str:
        """Generate step-by-step application guidance for Erasmus+."""
        return """Here's a **complete step-by-step guide** to applying for Erasmus+ funding:

## Step 1: Create Your EU Login Account (5 minutes)

**How to do it:**
1. Go to [EU Login](https://webgate.ec.europa.eu/cas/eim/external/register.cgi)
2. Register with your email
3. Verify your account

---

## Step 2: Register Your Organization & Get a PIC

1. Log into the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
2. Go to "My Organisation" → "Register Organisation"
3. Receive your 9-digit PIC number

---

## Step 3: Identify the Right Key Action

Erasmus+ has multiple funding streams:

| Key Action | What It Funds |
|------------|---------------|
| **KA1** | Learning Mobility (student/staff exchanges) |
| **KA2** | Cooperation Partnerships |
| **KA3** | Policy Support |
| **Jean Monnet** | EU Studies |
| **Sport** | Grassroots sport |

---

## Step 4: Check Deadlines

Erasmus+ typically has **annual deadlines** - check the [Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide) for exact dates.

---

## Step 5: Contact Your National Agency (NCP)

**For KA1 and KA2:** Your National Agency handles applications and provides guidance.

Find your NA: [Erasmus+ National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)

---

## Step 6: Prepare and Submit Your Application

1. Use the official application forms
2. Follow the Programme Guide requirements
3. Submit before the deadline

---

🎯 **Your Next Step:** Create your [EU Login account](https://webgate.ec.europa.eu/cas/eim/external/register.cgi) and identify which Key Action fits your project.

📞 **Need Help?** Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for FREE guidance!"""

    def _generate_creative_europe_application_guidance(self) -> str:
        """Generate step-by-step application guidance for Creative Europe."""
        return """Here's a **complete step-by-step guide** to applying for Creative Europe funding:

## Step 1: Create Your EU Login Account (5 minutes)

1. Go to [EU Login](https://webgate.ec.europa.eu/cas/eim/external/register.cgi)
2. Register and verify your account

---

## Step 2: Register Your Organization & Get a PIC

1. Log into the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
2. Register your organization
3. Receive your PIC number

---

## Step 3: Choose Your Strand

Creative Europe has three strands:

| Strand | Focus |
|--------|-------|
| **CULTURE** | Cultural cooperation, networks, platforms |
| **MEDIA** | Audiovisual, film, games |
| **CROSS-SECTORAL** | Creative innovation, news media |

---

## Step 4: Find Open Calls

Browse calls at: [Creative Europe Funding](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=;matchWholeText=true;typeCodes=0,1,2,8;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43251814;programDivisionCode=null;focusAreaCode=null;destinationGroup=null;missionGroup=null;geographicalZonesCode=null;programmeDivisionProsp498=null;startDateLte=null;startDateGte=null;crossCuttingPriorityCode=null;cpvCode=null;performanceOfDelivery=null;sortQuery=sortStatus;orderBy=asc;onlyTenders=false;topicListKey=topicSearchTablePageState)

---

## Step 5: Contact Your Creative Europe Desk (NCP)

**Creative Europe Desks provide FREE support:**
- Help with applications
- Partner search
- Project development

Find your desk: [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)

---

## Step 6: Build Your Partnership

Most CULTURE calls require partnerships from multiple countries.

---

## Step 7: Submit Your Application

1. Complete the online application
2. Submit before the deadline
3. Await evaluation results

---

🎯 **Your Next Step:** Create your [EU Login account](https://webgate.ec.europa.eu/cas/eim/external/register.cgi) and browse open calls for your strand.

📞 **Need Help?** Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) for FREE personalized support!"""

    def _generate_general_eu_application_guidance(self) -> str:
        """Generate general step-by-step application guidance for EU funding."""
        return """Here's a **complete step-by-step guide** to applying for EU funding:

## Step 1: Create Your EU Login Account (5 minutes)

Your personal access key to all EU funding services.

**How to do it:**
1. Go to [EU Login](https://webgate.ec.europa.eu/cas/eim/external/register.cgi)
2. Enter your email address
3. Create a password
4. Verify your email

---

## Step 2: Register Your Organization & Get a PIC (15-30 minutes)

The **PIC (Participant Identification Code)** is your organization's unique identifier across all EU programmes.

**How to register:**
1. Log into the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
2. Go to "My Organisation" → "Register Organisation"
3. Enter your organization's legal details
4. Receive your 9-digit PIC number

---

## Step 3: Choose the Right Programme

| Programme | Best For |
|-----------|----------|
| **Horizon Europe** | Research & Innovation (collaborative projects) |
| **Erasmus+** | Education, Training, Youth, Sport |
| **Creative Europe** | Culture, Media, Arts |
| **Digital Europe** | Digital technology deployment |
| **LIFE** | Environment & Climate |
| **EU4Health** | Health systems & initiatives |

---

## Step 4: Find Open Calls

Browse all EU funding at: [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)

---

## Step 5: Contact Your National Contact Point (NCP)

**NCPs are FREE expert advisors** who can:
- Help you find the right programme
- Review your proposal
- Connect you with partners
- Explain eligibility rules

**Find your NCP:** [NCP Network](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

---

## Step 6: Build Your Partnership (if required)

Many EU programmes require international partnerships. Use:
- [Partner Search Tool](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)
- [CORDIS](https://cordis.europa.eu/) for research projects
- Your NCP's network

---

## Step 7: Prepare and Submit

1. Download application templates
2. Follow programme-specific guidelines
3. Submit via the portal before the deadline

---

🎯 **Your Next Step:** Create your [EU Login account](https://webgate.ec.europa.eu/cas/eim/external/register.cgi) today - it takes just 5 minutes!

📞 **Need Help?** Contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for FREE personalized guidance!"""

    def _generate_eic_accelerator_eligibility_guidance(
        self,
        has_eligibility: bool = True,
        has_deadline: bool = True,
        has_budget: bool = True,
        country: str | None = None,
        is_sme: bool = True,
    ) -> str:
        """Generate comprehensive EIC Accelerator eligibility guidance.

        Covers:
        - SME eligibility requirements
        - Current deadlines and cut-off dates
        - Budget ranges (grant + equity)
        """
        sections = []

        # Header
        if country and is_sme:
            sections.append(
                f"## EIC Accelerator: Complete Guide for SMEs from {country}\n\n"
                "Great news! As an SME from an EU Member State, you are **eligible** for the EIC Accelerator.\n"
            )
        elif is_sme:
            sections.append(
                "## EIC Accelerator: Complete Guide for SMEs\n\n"
                "Great news! SMEs are the **primary target** of the EIC Accelerator programme.\n"
            )
        else:
            sections.append("## EIC Accelerator: Comprehensive Information\n")

        # Eligibility Section
        if has_eligibility:
            sections.append(
                """
### 1. Eligibility Requirements

The EIC Accelerator is **exclusively for SMEs and small mid-caps**:

| Criterion | Requirement | Your Status |
|-----------|-------------|-------------|
| **Organization Type** | SME or small mid-cap (< 500 employees) | ✅ SMEs are fully eligible |
| **Location** | EU Member State or Associated Country | ✅ Netherlands is an EU Member State |
| **Innovation Stage** | TRL 5-8 (ready for scale-up) | Check your TRL |
| **Legal Entity** | Single for-profit entity | Must be registered company |

**SME Definition (EU Standard):**
- < 250 employees
- Annual turnover ≤ €50 million OR balance sheet ≤ €43 million
- Autonomous (no >25% ownership by larger entity)

**Key Eligibility Points:**
- ✅ Single-company application (no consortium required)
- ✅ Breakthrough innovation with high-risk/high-reward potential
- ✅ European or global market ambition
- ✅ Viable scale-up plan within 3-5 years
"""
            )

        # Deadline Section
        if has_deadline:
            sections.append(
                """
### 2. EIC Accelerator 2026 Deadlines (Cut-off Dates)

The EIC Accelerator operates on **fixed cut-off dates** for the Short Application:

| Cut-off | Deadline | Status |
|---------|----------|--------|
| **Cut-off 1** | 12 March 2026 | ⏳ Upcoming |
| **Cut-off 2** | 2 October 2026 | ⏳ Upcoming |

**Application Process Timeline:**
1. **Short Application** → Submit by cut-off date
2. **Evaluation** → ~4-6 weeks after cut-off
3. **Full Application** (if invited) → ~3 months to prepare
4. **Interview** (if invited) → Face-to-face in Brussels
5. **Final Decision** → ~2-3 months after interview

**Total timeline**: 6-12 months from initial application to funding decision

⚠️ **Important**: The Short Application takes 2-4 weeks to prepare well. Start at least 6 weeks before the cut-off date.

🔗 **Official Deadlines**: [EIC Work Programme 2026](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en)
"""
            )

        # Budget Section
        if has_budget:
            sections.append(
                """
### 3. EIC Accelerator Budget (What You Can Request)

The EIC Accelerator offers **blended finance** (grant + equity):

| Component | Amount | Funding Rate |
|-----------|--------|--------------|
| **Grant** | Up to €2.5 million | 70% of eligible costs |
| **Equity** | €0.5 - €15 million | Investment (for equity share) |
| **Grant-Only** | Up to €2.5 million | Available if equity declined |

**Budget Breakdown Examples:**

| Project Type | Grant Request | Equity Request | Total Package |
|--------------|---------------|----------------|---------------|
| **Minimum** | €0.5 million | - | €0.5 million |
| **Grant-focused** | €2.5 million | - | €2.5 million |
| **Blended finance** | €2.5 million | €5 million | €7.5 million |
| **Maximum** | €2.5 million | €15 million | €17.5 million |

**What the Grant Covers (70% funding rate):**
- Personnel costs (salaries, consultants)
- Subcontracting
- Equipment and consumables
- Travel and subsistence
- Other direct costs

**What the Equity Covers:**
- Scale-up and commercialization activities
- Market expansion
- Team growth
- Working capital for growth phase
"""
            )

        # Next Steps
        sections.append(
            """
---

🎯 **Next Steps - What You Should Do:**

1. **Verify your SME status**: Use the [EU SME Self-Assessment Tool](https://ec.europa.eu/growth/tools-databases/SME-Wizard)

2. **Check your innovation readiness**:
   - TRL 5-8 (prototype to first commercial deployment)
   - Clear competitive advantage
   - €100M+ market potential

3. **Prepare your Short Application** (5 pages):
   - Problem and solution
   - Innovation and competitive advantage
   - Team and capabilities
   - Market and business model
   - Funding needs and use of funds

4. **Contact support**:
   - [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized guidance
   - [EIC website](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en) for official information

5. **Register on EU Portal**: [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)

💡 **Pro Tip**: Consider EIC coaching or acceleration programmes to strengthen your application. The success rate is 2-5%, so professional preparation significantly improves your odds.
"""
        )

        return "".join(sections)

    def _generate_eic_risks_overview_guidance(self) -> str:
        """Generate comprehensive guidance on EIC Accelerator risks."""
        return """Applying to the EIC Accelerator is a **high-risk, high-reward endeavor**. While the potential funding (up to €2.5M grant + €15M equity) is substantial, you should understand the significant risks involved.

### 1. Extremely Low Success Rate

The EIC Accelerator is one of the most competitive funding instruments globally:

| Stage | Success Rate | Your Odds |
|-------|-------------|-----------|
| **Short Application** | ~20-30% pass | 1 in 4 |
| **Full Application** | ~30-40% pass | 1 in 3 (of those remaining) |
| **Interview** | ~50-60% pass | 1 in 2 (of finalists) |
| **Overall** | **2-5%** | 1 in 20-50 applicants |

### 2. High Time and Resource Investment

⚠️ **Application costs to consider:**
- **Internal time**: 100-300 hours for full application
- **External support**: €10,000-50,000 for professional help (optional)
- **Opportunity cost**: Time away from business development
- **Resubmission cycles**: Average 2-3 attempts before success

### 3. Equity Component Risks

If you accept EIC equity (up to €15M), you should understand:
- EIC becomes a minority shareholder in your company
- Investment terms are standardized (limited negotiation)
- Due diligence process can take 6-12 months post-selection
- Some applicants decline equity after grant acceptance

### 4. Process and Timeline Risks

| Risk | Impact |
|------|--------|
| **Long timelines** | 6-12 months from application to funding |
| **Cut-off dates** | Miss deadlines = wait 3+ months for next round |
| **Process changes** | Rules and criteria can change between calls |
| **Interview cancellation** | Reaching interview doesn't guarantee funding |

### 5. Execution Risks Post-Award

Even if successful, you face:
- Strict reporting requirements (technical + financial)
- Milestone-based funding release
- Commission oversight of strategic decisions
- Potential clawback for non-performance

### What EIC Accelerator IS Good For

Despite risks, EIC is valuable if:
✅ You have breakthrough innovation with €100M+ market potential
✅ You're willing to accept equity investment terms
✅ You have 12-18 months runway to wait for funding
✅ You can sustain application effort alongside business growth

### What to Consider Instead

| Alternative | When to Consider |
|-------------|------------------|
| **EIC Pathfinder** | Earlier stage (TRL 2-4), research-focused |
| **Horizon RIA/IA** | Collaborative research, longer timelines |
| **National grants** | Faster timelines, less competition |
| **VC funding** | Need faster access to capital |
| **Eurostars** | SME R&D with international partner |

---

🎯 **Next Steps - What You Should Do:**
• Honestly assess if your company is EIC-ready (TRL 6-8, commercial traction)
• Calculate the total cost of application (time + resources)
• Review your current runway - can you wait 6-12 months for funding?
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for an honest readiness assessment
• Consider EIC coaching to evaluate your application strength before submitting
• Review successful EIC projects on [CORDIS](https://cordis.europa.eu/) in your sector"""

    def _generate_eic_prior_funding_guidance(self) -> str:
        """Generate guidance for EIC applicants without prior EU funding."""
        return """The lack of prior EU funding is **NOT a disqualifying factor** for the EIC Accelerator. The programme prioritizes commercial track record over EU project experience.

### What EIC Evaluators Really Look For

The EIC Accelerator focuses on **commercial readiness and market potential**, not prior EU funding history. You can demonstrate capability through:

| Alternative Evidence | What To Show |
|---------------------|--------------|
| **Commercial traction** | Revenue, paying customers, signed contracts |
| **Investor validation** | Previous funding rounds, investor interest |
| **Team track record** | Founders' entrepreneurial or industry experience |
| **Technical achievements** | Patents, prototypes, publications |
| **Market validation** | Pilot projects, partnerships, LOIs |

### Why Prior EU Funding Matters Less Than You Think

**The EIC is different from collaborative grants (RIA/IA):**
- No consortium management experience needed (single applicant)
- Focus is on commercial viability, not research track record
- Many successful EIC projects had zero prior EU funding
- Strong startup experience often valued more than research grants

### What You Should Emphasize Instead

✅ **Focus on these strengths:**
1. **Product-market fit evidence** - Customer testimonials, pilot results
2. **Clear go-to-market strategy** - How you'll scale with EIC funding
3. **Strong founding team** - Relevant experience, complementary skills
4. **Competitive differentiation** - Why your solution is 10x better
5. **Financial projections** - Realistic path to profitability

### Potential Concerns to Address

⚠️ **Evaluators may wonder about:**
- Your ability to handle EU reporting → Show other grant management experience
- Administrative capacity → Highlight your team's capabilities
- European dimension → Emphasize EU market focus and partnerships

---

🎯 **Next Steps - What You Should Do:**
• You should focus your application on commercial achievements, not research history
• Prepare evidence of market traction (customer letters, pilot agreements)
• Consider an EIC coaching programme to strengthen your application
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for feedback on your EIC fit
• Review successful EIC projects on [CORDIS](https://cordis.europa.eu/) to understand what works"""

    def _generate_eic_interview_guidance(self) -> str:
        """Generate guidance for EIC Accelerator interview preparation."""
        return """The EIC Accelerator interview is the **final, decisive stage** of the evaluation process. If you reach this stage, you have approximately a **50-60% chance of success**.

### Interview Format and Structure

| Aspect | Details |
|--------|---------|
| **Duration** | 30-45 minutes total |
| **Presentation** | 10-15 minutes (you control this part) |
| **Q&A** | 15-25 minutes (jury-led questions) |
| **Panel Size** | Typically 6 evaluators |
| **Panel Composition** | Investors, entrepreneurs, industry experts |

### The Jury's Evaluation Focus

**What the jury assesses during the interview:**

1. **Team Credibility** (Critical)
   - Can this team execute the vision?
   - Do founders have relevant experience?
   - Is there a capable, committed team?

2. **Market Understanding**
   - Do they know their market deeply?
   - Is the addressable market realistic?
   - Is competition analysis thorough?

3. **Business Model Viability**
   - Is the path to revenue clear?
   - Are unit economics sound?
   - Can they scale effectively?

4. **Technology Differentiation**
   - Is the innovation real and defensible?
   - Is TRL (Technology Readiness Level) appropriate?
   - Is IP strategy clear?

### How to Prepare Effectively

✅ **Presentation preparation:**
- Lead with your strongest commercial evidence
- Show, don't tell - use demos if possible
- Keep slides minimal (visual backup, not scripts)
- Practice your timing relentlessly (they will cut you off)

✅ **Q&A preparation:**
- Prepare for tough questions on financials
- Know your numbers cold (TAM, CAC, LTV, burn rate)
- Practice with hostile mock interviewers
- Have backup slides for common questions

### Common Interview Mistakes

❌ **Avoid these pitfalls:**
- Reading from slides (shows lack of preparation)
- Over-technical explanations (jury wants business impact)
- Defensive responses to criticism (shows poor coachability)
- Unrealistic financial projections (undermines credibility)
- Vague market sizing ("it's a $50B market")

### Presentation Structure Recommendation

| Section | Time | Focus |
|---------|------|-------|
| **Hook** | 1 min | Problem and urgency |
| **Solution** | 2-3 min | Your innovation, demo if possible |
| **Market** | 2 min | Size, segments, timing |
| **Business Model** | 2 min | Revenue, customers, traction |
| **Competition** | 1 min | Differentiation, moats |
| **Team** | 2 min | Why this team will win |
| **Ask** | 1 min | Use of funds, milestones |

---

🎯 **Next Steps - What You Should Do:**
• Book professional interview coaching (EIC-specific coaches available)
• Conduct at least 5 mock interviews with experienced entrepreneurs/investors
• Record your presentation and review critically
• Prepare a Q&A sheet with 50+ potential questions and answers
• Check [EIC Community](https://eic.ec.europa.eu/eic-community_en) for interview preparation resources
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for interview coaching referrals"""

    def _generate_eic_improve_odds_guidance(self) -> str:
        """Generate guidance for improving EIC Accelerator success odds."""
        return """Improving your EIC Accelerator success odds requires a **strategic approach at each stage**. The overall success rate is 2-5%, but you can significantly improve your chances with preparation.

### Success Rates by Stage

| Stage | Success Rate | What's Evaluated |
|-------|-------------|------------------|
| **Short Application** | ~20-30% pass | Innovation, team, market potential |
| **Full Application** | ~30-40% pass | Business plan, financials, impact |
| **Interview** | ~50-60% pass | Team credibility, investor readiness |
| **Overall** | ~2-5% | Cumulative (20% × 35% × 55% ≈ 4%) |

### Strategies to Improve Your Odds

#### 1. Strengthen Your Application Quality

✅ **You should focus on:**
- **Clear value proposition** - One sentence that captures your innovation
- **Strong traction evidence** - Customers, revenue, pilots, LOIs
- **Realistic financials** - Conservative base case, ambitious upside
- **Clear use of funds** - Specific milestones tied to EIC funding

#### 2. Target the Right Timing

✅ **You should apply when:**
- You have concrete market validation (not just R&D results)
- Your product is at TRL 6-8 (not too early, not too late)
- You can demonstrate 12-18 months of runway already
- Your team has entrepreneurial credibility

#### 3. Leverage Support Systems

✅ **You should use:**
- **NCP support** - Free proposal review and advice
- **EIC coaching** - Professional application support
- **Investor feedback** - Ask VCs to review your pitch
- **Previous applicants** - Learn from their experience

### Key Differentiators That Improve Success

| Factor | Low Success | High Success |
|--------|-------------|--------------|
| **Traction** | "We plan to..." | "We have X customers paying Y" |
| **Team** | First-time founders | Serial entrepreneurs or industry experts |
| **Market** | "Huge potential" | Specific segment, clear entry strategy |
| **Competition** | "No real competition" | Deep competitive analysis with clear moats |
| **Financials** | Hockey stick projections | Data-driven, realistic models |

### Timing Your Application

**Best time to apply:**
- After significant commercial milestone (Series A, major customer)
- When you can show 6-12 months of growth trajectory
- Before you're "too big" (>€100M revenue may be questioned)

**Worst time to apply:**
- With only R&D results and no commercial validation
- Immediately after incorporation with no traction
- When running out of cash (desperation shows)

### Reapplication Strategy

If your application fails:
1. **Request feedback** - EC provides evaluation reports
2. **Address specific weaknesses** - Don't just resubmit
3. **Build more evidence** - Get more traction before reapplying
4. **Wait 6-12 months** - Use time to strengthen fundamentals

---

🎯 **Next Steps - What You Should Do:**
• You should get an honest assessment of your TRL and market readiness
• Build at least 3-5 concrete pieces of commercial traction evidence
• Have your application reviewed by an experienced EIC coach
• Practice your pitch with real investors (even if not raising)
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for a proposal readiness assessment
• Review EIC selection statistics and adjust expectations accordingly"""

    def _generate_eic_company_size_guidance(self) -> str:
        """Generate guidance for EIC Accelerator company size requirements."""
        return """Company size is **critical for EIC Accelerator eligibility**. The programme is exclusively designed for Small and Medium-sized Enterprises (SMEs).

### SME Definition for EIC Eligibility

To be eligible for EIC Accelerator, your company must meet the EU SME definition:

| Criterion | Threshold | Your Status |
|-----------|-----------|-------------|
| **Employees** | < 250 FTE | Must be under |
| **Annual turnover** | ≤ €50 million | OR under this |
| **Annual balance sheet** | ≤ €43 million | OR under this |

**Note:** You must meet the employee threshold AND at least one of the financial thresholds.

### How Company Size Affects Your Chances

**Small startups (< 50 employees):**
✅ Core target of EIC Accelerator
✅ Evaluators expect high-growth potential
⚠️ Must demonstrate execution capability

**Medium-sized SMEs (50-249 employees):**
✅ Still eligible
✅ Stronger track record expected
⚠️ Must show why EIC funding (not VC) is needed

**Near-threshold companies (200+ employees):**
⚠️ Carefully verify SME status
⚠️ Consider affiliated/linked enterprise rules
⚠️ Evaluators may question growth potential

### SME Calculation Complexities

**Watch out for these:**

| Situation | Impact on SME Status |
|-----------|---------------------|
| **Parent company owns >50%** | Parent's data may be added |
| **Multiple investors with >25%** | Partner enterprises rule applies |
| **Recent rapid growth** | Use most recent closed accounts |
| **Recent spin-off** | Special rules may apply |

### Company Stage and EIC Fit

| Stage | EIC Suitability | Comments |
|-------|-----------------|----------|
| **Pre-revenue** | Medium | Need strong team and technology |
| **Early revenue (€0-1M)** | Good | Classic EIC target |
| **Growing (€1-10M)** | Excellent | Ideal stage for scale-up funding |
| **Scaling (€10-50M)** | Good | May need blended finance |
| **Established (€50M+)** | Low | May exceed SME thresholds |

### If You're Approaching SME Thresholds

**Options to consider:**
1. Apply before crossing the threshold
2. Check precise calculation (averages, FTE rules)
3. Consider other instruments (EIC Pathfinder, Horizon RIA)
4. National growth funding alternatives

### Non-SME Alternatives

If you exceed SME thresholds:
- **EIC Pathfinder** - Open to non-SMEs for earlier-stage innovation
- **Horizon Europe RIA/IA** - Collaborative research (no SME requirement)
- **National innovation funds** - Many countries have SME-alternative programmes
- **EIB financing** - Debt and equity for larger companies

---

🎯 **Next Steps - What You Should Do:**
• Verify your SME status using the [EC SME self-assessment tool](https://ec.europa.eu/growth/smes/sme-definition_en)
• Calculate linked and partner enterprise effects carefully
• Prepare SME declaration documents in advance
• If near threshold, consider timing of application strategically
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for SME status verification support
• Consult a grant accountant if your corporate structure is complex"""

    def _generate_programme_overview_guidance(self, programme: str) -> str | None:
        """Generate programme overview guidance from built-in knowledge."""
        if programme == "horizon_europe":
            return self._generate_horizon_europe_overview()
        elif programme == "erasmus_plus":
            return self._generate_erasmus_plus_overview()
        elif programme == "creative_europe":
            return self._generate_creative_europe_overview()
        elif programme == "life":
            return self._generate_life_programme_overview()
        elif programme == "digital_europe":
            return self._generate_digital_europe_overview()
        elif programme == "eu4health":
            return self._generate_eu4health_overview()
        return None

    def _generate_horizon_europe_overview(self) -> str:
        """Generate Horizon Europe programme overview."""
        return """**Horizon Europe** is the EU's key funding programme for research and innovation (2021-2027) with a budget of **€95.5 billion**.

### Programme Structure

Horizon Europe is organized into **3 Pillars** plus a **horizontal part**:

| Pillar | Focus | Budget | Key Components |
|--------|-------|--------|----------------|
| **Pillar I: Excellent Science** | Frontier research | €25B | ERC Grants, MSCA, Research Infrastructures |
| **Pillar II: Global Challenges** | Societal challenges | €53.5B | 6 Clusters + Missions |
| **Pillar III: Innovative Europe** | Innovation & scale-up | €13.6B | EIC, EIT, European Innovation Ecosystems |
| **Widening & ERA** | Participation & collaboration | €3.4B | Teaming, Twinning, ERA Chairs |

### Pillar II Clusters

| Cluster | Theme | Key Topics |
|---------|-------|------------|
| Cluster 1 | Health | Cancer, infections, digital health |
| Cluster 2 | Culture, Creativity & Society | Democracy, heritage, social inclusion |
| Cluster 3 | Civil Security | Cybersecurity, disaster resilience |
| Cluster 4 | Digital, Industry & Space | AI, manufacturing, space |
| Cluster 5 | Climate, Energy & Mobility | Clean energy, transport, batteries |
| Cluster 6 | Food, Bioeconomy & Environment | Biodiversity, agriculture, circular economy |

### Action Types

| Type | Funding Rate | Focus |
|------|-------------|-------|
| **RIA** | 100% | Research & knowledge generation |
| **IA** | 70% (100% non-profit) | Demonstration & piloting |
| **CSA** | 100% | Coordination & networking |

### Key Facts

- **Consortium requirement**: Minimum 3 entities from 3 different EU/Associated Countries (for collaborative projects)
- **Single applicant**: ERC, MSCA Postdoctoral Fellowships, EIC Accelerator
- **Typical budget**: €3-15M (RIA/IA), up to €2.5M (ERC Starting), up to €10M (EIC Accelerator)
- **Duration**: Typically 36-48 months

---

🎯 **Next Steps:**
• Register on [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
• Browse the [Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON)
• Check [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=null;freeTextSearchKeyword=;matchWholeText=true;typeCodes=1;statusCodes=31094501,31094502;programmePeriod=2021%20-%202027;programCcm2Id=43108390;programDivisionCode=null;focusAreaCode=null;destinationGroup=null;missionGroup=null;geographicalZonesCode=null;programmeDivisionProsp498742;startDateLte=null;startDateGte=null;crossCuttingPriorityCode=null;cpvCode=null;performanceOfDelivery=null;sortQuery=sortStatus;orderBy=asc;onlyTenders=false;topicListKey=topicSearchTablePageState)
• Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)"""

    def _generate_erasmus_plus_overview(self) -> str:
        """Generate Erasmus+ programme overview."""
        return """**Erasmus+** is the EU's programme for education, training, youth and sport (2021-2027) with a budget of **€26.2 billion**.

### Programme Structure

Erasmus+ is organized into **3 Key Actions** plus **Jean Monnet** and **Sport**:

| Key Action | Focus | Examples |
|------------|-------|----------|
| **KA1: Learning Mobility** | Individual mobility | Student exchanges, staff training, youth exchanges |
| **KA2: Cooperation** | Partnerships between organizations | Strategic partnerships, knowledge alliances |
| **KA3: Policy Support** | Supporting EU policy | Policy dialogue, tools for recognition |
| **Jean Monnet** | EU studies | Academic modules, centres of excellence |
| **Sport** | Sport activities | Grassroots sport, major events |

### Sectors

| Sector | Target Groups |
|--------|--------------|
| **HED** | Higher Education (universities) |
| **VET** | Vocational Education & Training |
| **SCH** | School Education |
| **ADU** | Adult Education |
| **YOU** | Youth (non-formal learning) |

### Funding Model

Erasmus+ uses a **lump sum funding model** with unit costs:
- **Travel**: Based on distance bands (10-8000+ km)
- **Individual support**: Daily rates by destination country
- **Organizational support**: Per participant
- **Course fees**: For staff training

### Key Facts

- **Accreditation**: Simplifies annual applications for mobility (KA1)
- **Partnerships**: 3+ organizations from 3+ Programme Countries (KA2)
- **Managed by**: National Agencies (decentralized) + EACEA (centralized actions)
- **Programme Countries**: EU Member States + Iceland, Liechtenstein, Norway, North Macedonia, Serbia, Turkey

---

🎯 **Next Steps:**
• Read the [Programme Guide 2026](https://erasmus-plus.ec.europa.eu/programme-guide/erasmus-programme-guide)
• Find your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
• Consider [Erasmus+ Accreditation](https://erasmus-plus.ec.europa.eu/resources-and-tools/erasmus-accreditation) for KA1 mobility
• Browse opportunities on [Erasmus+ website](https://erasmus-plus.ec.europa.eu/)"""

    def _generate_creative_europe_overview(self) -> str:
        """Generate Creative Europe programme overview."""
        return """**Creative Europe** is the EU's programme supporting the cultural and creative sectors (2021-2027) with a budget of **€2.44 billion**.

### Programme Structure

Creative Europe has **3 strands**:

| Strand | Focus | Budget Share | Key Actions |
|--------|-------|--------------|-------------|
| **CULTURE** | Cultural cooperation | 33% | Cooperation projects, networks, platforms, literary translation |
| **MEDIA** | Audiovisual sector | 58% | Development, distribution, training, festivals, cinema networks |
| **CROSS-SECTORAL** | Innovation & media literacy | 9% | Creative Innovation Labs, news media, media literacy |

### CULTURE Strand

| Action | Partners | Funding Rate | Typical Budget |
|--------|----------|--------------|----------------|
| Small Cooperation | 3+ from 3+ countries | 80% | Up to €200K |
| Medium Cooperation | 5+ from 5+ countries | 70% | Up to €1M |
| Large Cooperation | 10+ from 10+ countries | 60% | Up to €2M |
| European Networks | 15+ from 10+ countries | 80% | Up to €250K/year |
| Platforms | Networks of cultural operators | 80% | Varies |

### MEDIA Strand

| Action | Focus | Eligibility |
|--------|-------|-------------|
| Development (Slate) | Multiple AV projects | Production companies |
| Development (Single) | One feature/animation | Production companies |
| Distribution | European film distribution | Distributors |
| TV & Online Content | Series production | Production companies |
| Festivals | European film promotion | Festival organizers |

### Key Facts

- **Eligible countries**: EU + Creative Europe participating countries
- **Focus**: Promotes cultural diversity and European cultural heritage
- **Managed by**: EACEA (centralized from Brussels)
- **Complementary**: Works with national cultural funds

---

🎯 **Next Steps:**
• Visit [Creative Europe website](https://culture.ec.europa.eu/creative-europe)
• Read the [CulturEU Funding Guide](https://culture.ec.europa.eu/funding/cultureu-funding-guide)
• Contact your [Creative Europe Desk](https://culture.ec.europa.eu/resources/creative-europe-desks)
• Check [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/crea)"""

    def _generate_life_programme_overview(self) -> str:
        """Generate LIFE Programme overview."""
        return """**LIFE** is the EU's funding instrument for environment and climate action (2021-2027) with a budget of **€5.4 billion**.

### Programme Structure

LIFE has **4 sub-programmes**:

| Sub-programme | Focus | Budget |
|---------------|-------|--------|
| **Nature & Biodiversity** | Natura 2000, biodiversity protection | €2.15B |
| **Circular Economy & Quality of Life** | Resource efficiency, air/water/soil | €1.35B |
| **Climate Change Mitigation & Adaptation** | Reducing emissions, climate resilience | €947M |
| **Clean Energy Transition** | Energy efficiency, renewables | €997M |

### Project Types

| Type | Duration | Budget Range | Focus |
|------|----------|--------------|-------|
| **Standard Action Projects (SAP)** | 3-5 years | €1-5M | Best practice, demonstration, pilot |
| **Strategic Nature Projects (SNAP)** | 6-10 years | €5-20M | Nature/biodiversity at scale |
| **Strategic Integrated Projects (SIP)** | 6-10 years | €10-30M | Regional/national environmental plans |
| **Technical Assistance** | 1-2 years | Up to €100K | Preparing SIP/SNAP applications |
| **Operating Grants** | Annual | Varies | NGO operating costs |

### Funding Rates

| Project Type | Standard Rate | Higher Rate |
|--------------|--------------|-------------|
| SAP | 60% | 75% (nature priorities) |
| SNAP | 60% | 67% (biodiversity) |
| SIP | 60% | N/A |

### Key Facts

- **No consortium required**: Single organizations can apply
- **Geographic balance**: 15% of total budget for nature/biodiversity in least-developed areas
- **Focus**: Solutions that can be replicated and scaled up
- **Managed by**: CINEA (European Climate, Infrastructure and Environment Executive Agency)

---

🎯 **Next Steps:**
• Visit [LIFE website](https://cinea.ec.europa.eu/programmes/life_en)
• Read the [Multi-Annual Work Programme](https://cinea.ec.europa.eu/publications/life-multiannual-work-programme-2021-2024_en)
• Contact your [National Contact Point](https://cinea.ec.europa.eu/life/life-national-contact-points_en)
• Check [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/life)"""

    def _generate_digital_europe_overview(self) -> str:
        """Generate Digital Europe Programme overview."""
        return """**Digital Europe Programme (DIGITAL)** is the EU's programme for digital transformation (2021-2027) with a budget of **€7.5 billion**.

### Programme Structure

Digital Europe focuses on **5 key capacity areas**:

| Area | Focus | Budget |
|------|-------|--------|
| **Supercomputing** | High-Performance Computing (HPC) | €2.2B |
| **Artificial Intelligence** | AI development & uptake | €2.1B |
| **Cybersecurity** | Digital security | €1.6B |
| **Advanced Digital Skills** | Specialist training | €577M |
| **Digital Transformation** | Public services, business uptake | €1.1B |

### Key Actions

| Action | Description |
|--------|-------------|
| **Testing & Experimentation Facilities** | AI/robotics testing environments |
| **Digital Innovation Hubs** | Support for SME digital transformation |
| **Common Data Spaces** | Sectoral data sharing infrastructure |
| **Public Service Delivery** | Cross-border digital services |
| **Skills Programs** | Masters, short courses, job placements |

### Funding Model

| Aspect | Details |
|--------|---------|
| **Funding rate** | 50% (grant), 75% (specific actions) |
| **Target TRL** | TRL 7-9 (deployment, not research) |
| **Beneficiaries** | Public sector, businesses, civil society |
| **SME focus** | Strong emphasis on SME participation |

### Difference from Horizon Europe

| Aspect | Digital Europe | Horizon Europe |
|--------|---------------|----------------|
| **Focus** | Deployment & uptake | Research & innovation |
| **TRL** | 7-9 | 2-6 |
| **Activities** | Implementation, capacity building | Discovery, prototyping |
| **Funding rate** | 50% typical | 100% (RIA) |

---

🎯 **Next Steps:**
• Visit [Digital Europe website](https://digital-strategy.ec.europa.eu/en/activities/digital-programme)
• Browse [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/digital)
• Contact a [European Digital Innovation Hub](https://digital-strategy.ec.europa.eu/en/activities/edihs)
• Check [Digital Skills initiatives](https://digital-skills-jobs.europa.eu/)"""

    def _generate_eu4health_overview(self) -> str:
        """Generate EU4Health Programme overview."""
        return """**EU4Health** is the EU's response to COVID-19 and beyond (2021-2027) with a budget of **€5.3 billion**.

### Programme Structure

EU4Health has **4 general objectives**:

| Objective | Focus |
|-----------|-------|
| **Health Protection** | Crisis preparedness, disease prevention |
| **Medicines & Devices** | Availability, accessibility, affordability |
| **Health Systems** | Strengthening national health systems |
| **Digital Health** | eHealth, health data spaces |

### Priority Areas

| Area | Key Actions |
|------|-------------|
| **Europe's Beating Cancer Plan** | Prevention, early detection, treatment, quality of life |
| **Cross-border Health Threats** | Preparedness, surveillance, response |
| **Health Workforce** | Training, mobility, working conditions |
| **Digital Transformation** | European Health Data Space, AI in health |
| **Mental Health** | Prevention, support, integration |

### Action Types

| Type | Description | Managed By |
|------|-------------|------------|
| **Grants** | Projects, joint actions | HaDEA (centralized) |
| **Procurement** | Direct contracts | Commission/HaDEA |
| **Prizes** | Innovation contests | Commission |
| **Operating grants** | Health NGOs | HaDEA |

### Key Facts

- **Implementation**: Managed by HaDEA (European Health and Digital Executive Agency)
- **Cross-border**: Focus on transnational health challenges
- **Complementary**: Works with Horizon Europe (research) and Digital Europe (digital health)
- **Stakeholders**: Health authorities, NGOs, patient organizations, healthcare providers

### Who Can Apply

- Public health authorities
- Healthcare organizations
- Research institutions (for health system research)
- Patient organizations
- Health-related NGOs
- International organizations

---

🎯 **Next Steps:**
• Visit [EU4Health website](https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en)
• Check the [Annual Work Programme](https://health.ec.europa.eu/funding/eu4health-programme-2021-2027/eu4health-work-programme_en)
• Browse [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/eu4h)
• Contact your [National Focal Point](https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en)"""

    def _generate_ria_ia_comparison_guidance(self) -> str:
        """Generate comprehensive RIA vs IA comparison."""
        return """The choice between **Research and Innovation Action (RIA)** and **Innovation Action (IA)** depends on your project's technological maturity and objective. Both are suitable for applied research, but they target different stages of development.

### 1. Key Differences Overview

| Feature | RIA (Research & Innovation Action) | IA (Innovation Action) |
|---------|-----------------------------------|------------------------|
| **Focus** | Generating new knowledge, exploring feasibility | Demonstrating, piloting, validating |
| **TRL Range** | TRL 2-5 (research to early prototype) | TRL 5-8 (prototype to near-market) |
| **Funding Rate** | **100%** of eligible costs | **70%** (100% for non-profits) |
| **Typical Budget** | €3-15M | €5-20M |
| **Duration** | 36-48 months | 24-36 months |
| **Risk Profile** | Higher technical risk, knowledge gaps | Lower tech risk, market/scale-up focus |

### 2. When to Choose RIA

✅ **Choose RIA when:**
- You're exploring new concepts or generating foundational knowledge
- Your technology is at TRL 2-5 (concept validation to lab demonstration)
- You want 100% funding for research-intensive activities
- Your main deliverable is new knowledge, methods, or early prototypes
- You need to answer fundamental research questions

**Typical RIA activities:**
- Basic and applied research
- Technology exploration and feasibility studies
- Lab-scale testing and validation
- Development of new methods, processes, or tools

### 3. When to Choose IA

✅ **Choose IA when:**
- You have proven technology ready for demonstration/piloting
- Your technology is at TRL 5-8 (large-scale prototype to near-market)
- You need to validate in real-world conditions
- Your main deliverable is demonstrated technology, pilot plants, or scale-up
- You're preparing for market deployment

**Typical IA activities:**
- Large-scale demonstrations and pilots
- Prototyping at near-production scale
- Market replication and first-of-a-kind deployment
- Field testing and user validation
- Regulatory preparation

### 4. Consortium Considerations

| Aspect | RIA | IA |
|--------|-----|------|
| **Typical size** | 8-15 partners | 10-20 partners |
| **Academia role** | Often coordinator, research leaders | Partners for specific expertise |
| **Industry role** | Essential for validation, end-user | Often coordinator, scale-up leaders |
| **SME role** | Technology providers, niche expertise | Demonstration, early adopters |

### 5. Budget Implications

**RIA (100% funding):**
- Full cost recovery for all partners
- Lower financial risk for participants
- May attract more academic partners

**IA (70% for industry):**
- Industrial partners need 30% co-funding
- Non-profit entities still get 100%
- May require stronger industry commitment

### 6. Decision Guide

| Your Situation | Recommended Action |
|----------------|-------------------|
| "We have an idea and want to validate the concept" | RIA |
| "We have a working prototype and need to demonstrate at scale" | IA |
| "We want to explore fundamental scientific questions" | RIA |
| "We're ready to pilot with real users" | IA |
| "Our technology is TRL 2-4" | RIA |
| "Our technology is TRL 6-8" | IA |
| "We need 100% funding coverage" | RIA |
| "We have strong industry partners with co-funding" | IA |

---

🎯 **Next Steps - What You Should Do:**
• Assess your current TRL level honestly - this determines the best fit
• Check the Work Programme topics - some specify RIA only or IA only
• Review your consortium's ability to provide 30% co-funding (if considering IA)
• Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for open calls
• Consult your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for topic-specific advice
• Review funded projects on [CORDIS](https://cordis.europa.eu/) in your area"""

    def _generate_csa_explanation_guidance(self) -> str:
        """Generate detailed CSA explanation."""
        return """**Coordination and Support Actions (CSA)** are fundamentally different from RIA and IA. They focus on coordination, networking, and support activities rather than research and development.

### What is a CSA?

CSA stands for **Coordination and Support Action** - a funding type designed for activities that:
- Coordinate existing research efforts
- Support policy development
- Build networks and communities
- Disseminate knowledge
- Standardize practices

**Key characteristic:** CSAs do **NOT** fund research or innovation activities directly.

### CSA Characteristics

| Feature | CSA (Coordination & Support Action) |
|---------|-------------------------------------|
| **Funding Rate** | **100%** of eligible costs |
| **Focus** | Coordination, networking, dissemination |
| **TRL Range** | N/A (not technology development) |
| **Typical Budget** | €1-3 million |
| **Duration** | 24-36 months |
| **Consortium Size** | 5-10 partners (smaller than RIA/IA) |

### What CSAs Fund

✅ **Eligible CSA activities:**
- Coordination of research networks
- Policy support and strategy development
- Stakeholder engagement and dialogue
- Knowledge transfer and dissemination
- Standardization activities
- Training and capacity building
- Communication and outreach
- Events, workshops, conferences
- Roadmap development
- Best practice sharing

❌ **NOT eligible in CSA:**
- Laboratory research
- Technology development
- Prototyping
- Demonstration activities
- Any R&D activities

### When to Choose CSA

✅ **CSA is ideal when:**
- You want to build a European network in your field
- You need to coordinate existing research efforts across countries
- You're supporting policy development or standardization
- You're disseminating results from previous projects
- You want to develop roadmaps or strategic agendas
- You're organizing large-scale stakeholder engagement

### CSA vs RIA/IA Comparison

| Aspect | CSA | RIA | IA |
|--------|-----|-----|-----|
| **Research** | None | Core activity | Core activity |
| **Funding** | 100% | 100% | 70% (industry) |
| **Budget** | €1-3M | €3-15M | €5-20M |
| **Focus** | Coordination | Knowledge creation | Demonstration |
| **Complexity** | Lower | Higher | Higher |
| **Competition** | Moderate | High | High |

### Who Typically Coordinates CSAs

| Organization Type | Suitability | Why |
|-------------------|-------------|-----|
| **Associations/Networks** | Excellent | Natural coordinators, existing connections |
| **Policy organizations** | Excellent | Policy focus aligns with CSA objectives |
| **Universities** | Good | Can lead dissemination/training activities |
| **Research institutes** | Good | Coordinate research communities |
| **SMEs** | Limited | CSA isn't their typical domain |

### CSA as Entry Point

**For newcomers to EU funding:**
- CSA projects are smaller and more manageable
- Lower administrative burden than RIA/IA
- 100% funding reduces financial risk
- Good way to build EU project management experience
- Opportunity to meet potential future consortium partners

---

🎯 **Next Steps - What You Should Do:**
• Check if your activity is truly coordination/support (not research)
• Review open CSA topics on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)
• Consider CSA if you're new to EU funding - it's a good starting point
• Partner with associations or networks experienced in coordination
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) to discuss CSA suitability"""

    def _generate_eic_pathfinder_explanation_guidance(self) -> str:
        """Generate detailed EIC Pathfinder explanation."""
        return """The **EIC Pathfinder** is fundamentally different from collaborative actions (RIA/IA/CSA). It's designed for **breakthrough, high-risk research** at the earliest stages of technology development, operating under Pillar III (Innovative Europe).

### What is EIC Pathfinder?

EIC Pathfinder funds **visionary, high-risk research** that could lead to breakthrough technologies. Unlike RIA/IA, which operate within known scientific paradigms, Pathfinder supports research that challenges current understanding.

### EIC Pathfinder vs Collaborative Actions

| Feature | EIC Pathfinder | RIA/IA/CSA (Pillar II) |
|---------|----------------|------------------------|
| **TRL Range** | TRL 1-4 (very early) | TRL 2-8 |
| **Focus** | Breakthrough science, new technology paradigms | Incremental innovation, demonstration |
| **Risk Level** | Extremely high (failure expected) | Moderate to high |
| **Funding** | 100% | 100% (RIA/CSA), 70% (IA) |
| **Typical Budget** | €3-4M (Open), up to €5M (Challenges) | €3-20M |
| **Duration** | 36-48 months | 36-48 months |
| **Consortium** | Small teams (2-5 partners) | Large consortia (8-20 partners) |

### Two Types of EIC Pathfinder

**1. EIC Pathfinder Open**
- **Bottom-up:** You define the topic
- **Any breakthrough technology area**
- Maximum €3M per project
- Small, focused teams (can be single applicant)
- Higher scientific freedom

**2. EIC Pathfinder Challenges**
- **Top-down:** Predefined strategic challenges
- Specific breakthrough areas defined by EIC
- Maximum €4-5M per project
- Requires addressing specific challenge scope
- Annual challenge topics announced

### Key Characteristics of Pathfinder

| Aspect | What This Means |
|--------|-----------------|
| **High-risk tolerance** | Failure is acceptable; EIC expects many projects won't succeed |
| **Long-term vision** | 10-20 year horizon for potential impact |
| **Scientific ambition** | Must go beyond incremental advances |
| **Proof of concept** | Goal is to demonstrate scientific feasibility |
| **Technology transition** | Successful projects may progress to EIC Transition |

### Who Should Apply to EIC Pathfinder?

✅ **Ideal Pathfinder applicants:**
- Research teams exploring radical new ideas
- Scientists working on fundamental breakthroughs
- Startups with revolutionary (not evolutionary) technology
- Interdisciplinary teams challenging established paradigms

❌ **Not suitable for Pathfinder:**
- Incremental improvements to existing technology
- Products ready for market demonstration
- Large consortium projects
- Projects requiring large-scale validation

### EIC Pathfinder Success Factors

| Factor | What Evaluators Look For |
|--------|-------------------------|
| **Excellence** | Scientific novelty, paradigm-shifting potential |
| **Impact** | Long-term transformative potential |
| **Implementation** | Team capability, methodology quality |
| **Risk awareness** | Clear understanding of technical uncertainties |

### Pathfinder vs Other EIC Instruments

| Instrument | Stage | Funding | Goal |
|------------|-------|---------|------|
| **EIC Pathfinder** | TRL 1-4 | Grant up to €4M | Prove scientific concept |
| **EIC Transition** | TRL 4-5 | Grant up to €2.5M | Technology maturation |
| **EIC Accelerator** | TRL 6-9 | Grant + Equity up to €17.5M | Scale-up and market entry |

---

🎯 **Next Steps - What You Should Do:**
• Assess if your idea is truly breakthrough (not incremental)
• Check if EIC Pathfinder Open or a Challenge topic fits better
• Review evaluation criteria on the [EIC website](https://eic.ec.europa.eu/)
• Consider the EIC proactive grant management approach
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) or EIC Business Acceleration Services
• Look at funded Pathfinder projects on [CORDIS](https://cordis.europa.eu/)"""

    def _generate_msca_explanation_guidance(self) -> str:
        """Generate detailed MSCA Postdoctoral Fellowship explanation."""
        return """**Marie Skłodowska-Curie Actions Postdoctoral Fellowships (MSCA-PF)** are a core component of Horizon Europe (Pillar I - Excellent Science), designed to support experienced researchers in gaining new skills through international and inter-sectoral mobility.

### What is MSCA-PF?

MSCA Postdoctoral Fellowships provide funding for researchers to conduct research at a host organization in a different country than where they have resided for the last 3 years (mobility rule).

### Key MSCA-PF Characteristics

| Feature | MSCA Postdoctoral Fellowship |
|---------|------------------------------|
| **Funding Rate** | 100% (unit costs model) |
| **Who applies** | Individual researcher |
| **Duration** | 12-24 months (European), 12-24 months + return (Global) |
| **Monthly allowance** | ~€5,080 living allowance + host contribution |
| **Research area** | **Any field** (bottom-up, researcher-driven) |
| **Consortium** | Just researcher + host institution |

### Two Fellowship Types

**1. European Fellowships (EF)**
- Researcher moves TO an EU/Associated Country
- Duration: 12-24 months
- Host must be in EU Member State or Associated Country

**2. Global Fellowships (GF)**
- Outgoing phase: Move to Third Country (12-24 months)
- Mandatory return phase: Back to EU (12 months)
- For EU/AC researchers wanting international experience

### Why MSCA-PF Offers Most Freedom

| Aspect | MSCA-PF Freedom Level |
|--------|----------------------|
| **Topic choice** | ✅ **Complete freedom** - any research area |
| **Host choice** | ✅ Researcher selects their own host |
| **Methodology** | ✅ Researcher designs their own project |
| **Career development** | ✅ Dedicated training component required |
| **Administrative burden** | Low - simpler than collaborative projects |

### Eligibility Requirements

| Requirement | Criteria |
|-------------|----------|
| **PhD** | Must have PhD OR 4+ years research experience |
| **Mobility** | Cannot have resided in host country >12 months in last 3 years |
| **Experience** | Maximum 8 years of research experience post-PhD |
| **Nationality** | Any nationality (researcher), EU/AC (host) |

### MSCA-PF vs Collaborative Grants

| Aspect | MSCA-PF | RIA/IA |
|--------|---------|--------|
| **Applicant** | Individual researcher | Consortium |
| **Topic** | Any (bottom-up) | Specific topics |
| **Budget** | Fixed unit costs | Flexible budget |
| **Consortium** | None needed | 3+ partners required |
| **Competition** | High (~15% success) | Variable by topic |
| **Freedom** | Maximum | Topic-constrained |

### Funding Structure

| Category | Monthly Amount (2024) |
|----------|---------------------|
| **Living allowance** | €5,080 (base) |
| **Mobility allowance** | €600 |
| **Family allowance** | €660 (if applicable) |
| **Research costs** | €1,000/month to host |
| **Management costs** | €650/month to host |

### Success Factors

| Criterion | Weight | What Evaluators Want |
|-----------|--------|---------------------|
| **Excellence** | 50% | Scientific quality, innovation, researcher CV |
| **Impact** | 30% | Career development, knowledge transfer |
| **Implementation** | 20% | Feasibility, work plan quality |

---

🎯 **Next Steps - What You Should Do:**
• Check the mobility rule - you can't have lived in host country >12 months
• Find a host institution that matches your research interests
• Develop a strong career development plan (training activities)
• Review the [MSCA Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) for deadlines
• Contact potential supervisors early - you need a host commitment letter
• Prepare a strong 2-page research proposal
• Visit the [MSCA portal](https://marie-sklodowska-curie-actions.ec.europa.eu/) for guidance"""

    def _generate_ia_explanation_guidance(self) -> str:
        """Generate detailed IA explanation."""
        return """**Innovation Actions (IA)** are Horizon Europe funding instruments focused on bringing near-market technologies to demonstration and deployment. They target the later stages of innovation where technology proof-of-concept exists and needs real-world validation.

### What is an IA?

Innovation Actions fund activities aimed at producing plans, designs, or prototypes for new, altered, or improved products, processes, or services, including activities such as prototyping, testing, demonstrating, piloting, and large-scale product validation.

### Key IA Characteristics

| Feature | Innovation Action (IA) |
|---------|------------------------|
| **Funding Rate** | **70%** for industry, **100%** for non-profits |
| **Focus** | Demonstration, piloting, validation, scale-up |
| **TRL Range** | TRL 5-8 (prototype to near-market) |
| **Typical Budget** | €5-20 million |
| **Duration** | 24-36 months |
| **Consortium Size** | 10-20 partners |

### When to Choose IA

✅ **IA is right when:**
- You have proven technology ready for large-scale demonstration
- You need to validate in real operational environments
- You're preparing for market deployment
- You want to prove scalability and user acceptance
- Your technology is TRL 5-8

### IA vs RIA Comparison

| Aspect | IA | RIA |
|--------|-----|-----|
| **Funding** | 70% (industry) | 100% |
| **Focus** | Demonstration | Research |
| **TRL** | 5-8 | 2-5 |
| **Risk** | Scale-up risk | Technical risk |
| **Output** | Pilots, demos | Knowledge, early prototypes |

---

🎯 **Next Steps - What You Should Do:**
• Assess if your technology is at TRL 5+ for demonstration
• Ensure industry partners can provide 30% co-funding
• Check the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for IA topics
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for advice"""

    def _generate_ria_explanation_guidance(self) -> str:
        """Generate detailed RIA explanation."""
        return """**Research and Innovation Actions (RIA)** are the core Horizon Europe funding instrument for generating new knowledge and exploring the feasibility of new or improved technologies, products, processes, services, and solutions.

### What is an RIA?

RIA funds activities that aim primarily to establish new knowledge and/or explore the feasibility of new or improved technology, product, process, service, or solution. This includes basic and applied research, technology development and integration, testing, demonstration, and validation on a small-scale prototype.

### Key RIA Characteristics

| Feature | Research & Innovation Action (RIA) |
|---------|-----------------------------------|
| **Funding Rate** | **100%** of eligible costs |
| **Focus** | Knowledge generation, feasibility, early validation |
| **TRL Range** | TRL 2-5 (concept to lab demonstration) |
| **Typical Budget** | €3-15 million |
| **Duration** | 36-48 months |
| **Consortium Size** | 8-15 partners |

### When to Choose RIA

✅ **RIA is right when:**
- You need to generate new scientific knowledge
- You're exploring the feasibility of new concepts
- Your technology is TRL 2-5 (concept to early prototype)
- You want 100% funding coverage
- Your focus is on research questions, not market deployment

### RIA Activities

| Eligible | Not typical for RIA |
|----------|-------------------|
| Basic research | Large-scale production |
| Applied research | Market deployment |
| Technology exploration | Commercial demonstration |
| Lab-scale validation | Near-market pilots |
| Early prototyping | Regulatory approval preparation |

---

🎯 **Next Steps - What You Should Do:**
• Verify your technology is at TRL 2-5 for research focus
• Check the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for RIA topics
• Build a strong academic-industry consortium
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for advice"""

    def _generate_funding_type_freedom_guidance(self) -> str:
        """Generate guidance comparing freedom/flexibility across funding types."""
        return """When comparing **scientific and administrative freedom** across Horizon Europe funding types, the **MSCA Postdoctoral Fellowship** offers the most freedom, followed by **EIC Pathfinder Open**, while collaborative actions (RIA/IA/CSA) are more constrained by topic definitions.

### Freedom Comparison: Scientific Scope

This refers to whether you choose the research topic (bottom-up) or respond to a predefined call topic (top-down).

| Funding Type | Topic Freedom | Description |
|--------------|---------------|-------------|
| **MSCA-PF** | ✅ **Highest** | Any research area, researcher-defined |
| **EIC Pathfinder Open** | ✅ **Very High** | Any breakthrough technology, you define |
| **ERC Grants** | ✅ **Very High** | Any frontier research, PI-driven |
| **EIC Pathfinder Challenges** | ⚡ Medium | Within defined challenge scope |
| **RIA/IA** | ⚡ Medium-Low | Specific Work Programme topics |
| **CSA** | ⚡ Low | Predefined coordination activities |

### Freedom Comparison: Consortium Requirements

| Funding Type | Consortium | Freedom Level |
|--------------|------------|---------------|
| **MSCA-PF** | Just you + host | ✅ Highest |
| **ERC** | PI + team | ✅ Very High |
| **EIC Pathfinder** | 2-5 partners | ✅ High |
| **RIA** | 8-15 partners | ⚡ Medium |
| **IA** | 10-20 partners | ⚡ Medium |
| **CSA** | 5-10 partners | ⚡ Medium |

### Freedom Comparison: Methodology & Approach

| Funding Type | Approach Freedom | Description |
|--------------|------------------|-------------|
| **MSCA-PF** | ✅ **Highest** | You design your entire research approach |
| **ERC** | ✅ **Highest** | Frontier research, your methodology |
| **EIC Pathfinder** | ✅ High | Must be breakthrough, but your approach |
| **RIA** | ⚡ Medium | Guided by topic expected impact |
| **IA** | ⚡ Medium | Demonstration requirements constrain |
| **CSA** | ⚡ Lower | Specific coordination objectives |

### Recommendation: Which Gives Most Freedom?

**For Individual Researchers:**
1. **MSCA-PF** - Maximum freedom: any topic, simple application, you + host
2. **ERC grants** - Frontier research on your chosen topic (but more competitive)

**For Teams/Organizations:**
1. **EIC Pathfinder Open** - Breakthrough innovation, any area, small team
2. **RIA (open topics)** - Some calls have broad scope
3. **CSA** - Limited scope but simpler administration

### Trade-offs to Consider

| Freedom Aspect | High Freedom Options | Trade-off |
|----------------|---------------------|-----------|
| **Topic choice** | MSCA-PF, ERC, Pathfinder Open | Higher competition for open calls |
| **Consortium** | MSCA-PF, ERC | Limited to individual/small team |
| **Budget** | RIA, IA | Must follow specific topics |
| **Risk tolerance** | EIC Pathfinder | Breakthrough required, risky |
| **Simplicity** | MSCA-PF, CSA | Lower budgets |

### Summary by User Need

| If You Want... | Best Choice |
|----------------|-------------|
| **Maximum freedom, any topic** | MSCA-PF (individual) or EIC Pathfinder Open (team) |
| **Large budget + freedom** | ERC (individual) or broad RIA topics |
| **Simple administration** | MSCA-PF or CSA |
| **Scale-up funding** | EIC Accelerator (constrained but well-funded) |
| **Collaborative but flexible** | Broad RIA/IA topics |

---

🎯 **Next Steps - What You Should Do:**
• For maximum freedom as researcher: Apply to MSCA-PF or ERC
• For maximum freedom as team: Apply to EIC Pathfinder Open
• Check topic descriptions - some RIA topics have broad scope
• Review your constraints (team size, budget needs) against funding type requirements
• Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) to explore options
• Contact your [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) to discuss your specific situation"""

    def _generate_eic_erc_comparison_guidance(self, query: str, context: str) -> dict[str, Any]:
        """Generate comprehensive EIC vs ERC comparison guidance using built-in knowledge."""

        guidance = """## EIC vs ERC: Comprehensive Comparison

The **European Innovation Council (EIC)** and **European Research Council (ERC)** serve fundamentally different purposes within Horizon Europe.

### Quick Comparison

| Aspect | ERC | EIC |
|--------|-----|-----|
| **Focus** | Frontier research (curiosity-driven) | Breakthrough innovation (market-oriented) |
| **TRL Range** | TRL 1-3 (basic research) | TRL 3-8 (development to market) |
| **Applicant** | Single PI + team | SMEs, startups, consortia |
| **Budget** | €1.5-2.5M (grants) | €2.5-17.5M (grant + equity) |
| **Funding Rate** | 100% | 70% (IA) or 100% (grant only) |
| **Success Rate** | ~10-15% | ~3-8% (Accelerator) |

### ERC (European Research Council)

**Best for:** Academic researchers pursuing fundamental science

| Grant Type | Budget | Duration | Career Stage |
|------------|--------|----------|--------------|
| **Starting Grant** | Up to €1.5M | 5 years | 2-7 years post-PhD |
| **Consolidator Grant** | Up to €2M | 5 years | 7-12 years post-PhD |
| **Advanced Grant** | Up to €2.5M | 5 years | Established leaders |
| **Synergy Grant** | Up to €10M | 6 years | 2-4 PIs jointly |

**Key characteristics:**
- Single Principal Investigator (PI) model
- Research must be "high-risk, high-gain" frontier science
- No consortium requirement
- 100% funding rate
- Host institution must be in EU or Associated Country

### EIC (European Innovation Council)

**Best for:** Innovators, SMEs, and tech startups

| Instrument | Budget | TRL | Funding Type |
|------------|--------|-----|--------------|
| **Pathfinder** | €3-4M | 1-4 | Grant (100%) |
| **Transition** | Up to €2.5M | 4-6 | Grant (100%) |
| **Accelerator** | Up to €2.5M grant + €15M equity | 6-9 | Blended |

**Key characteristics:**
- Focus on breakthrough innovations with market potential
- EIC Accelerator targets SMEs specifically
- Blended finance (grant + equity) for scale-up
- Business plan and commercialization strategy required
- Can include equity investment component

### Decision Guide: Which is Right for You?

**Choose ERC if:**
✅ You're an academic researcher
✅ Your work is curiosity-driven without immediate commercial goals
✅ You want full scientific freedom
✅ You're at a specific career stage (2-7 yrs post-PhD for Starting)
✅ You don't need/want industrial partners

**Choose EIC if:**
✅ You have a concrete innovation with market potential
✅ You're an SME or startup
✅ Your technology is at TRL 4 or higher
✅ You need funding to scale up and commercialize
✅ You're willing to accept equity investment (Accelerator)

---

🎯 **Next Steps:**
• For ERC: Check eligibility based on career stage and prepare your CV
• For EIC: Assess your TRL level and commercial readiness
• Both: Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)
• Explore calls: [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
"""

        return {
            "thought": "User is asking about EIC vs ERC comparison. Providing comprehensive guidance from built-in knowledge.",
            "action": "generate_guidance",
            "response": guidance,
            "guidance_type": "eic_erc_comparison",
            "confidence": 0.92,
            "needs_more_info": False,
        }

    def _generate_erc_grant_amount_guidance(self) -> str:
        """Generate ERC grant amount guidance WITH source attribution.

        Source: European Research Council (ERC) Official Website
        URL: https://erc.europa.eu/funding
        Last verified: 2025 Work Programme

        All amounts are based on official ERC documentation and the
        Horizon Europe Work Programme for ERC actions.
        """
        return """## ERC Grant Amounts

The **European Research Council (ERC)** provides funding for frontier research across all scientific disciplines. Below are the official grant amounts for each ERC funding scheme.

### Grant Types and Funding Levels

| Grant Type | Maximum Budget | Duration | Career Stage |
|------------|----------------|----------|--------------|
| **Starting Grant (StG)** | Up to **€1.5 million** | 5 years | 2-7 years post-PhD |
| **Consolidator Grant (CoG)** | Up to **€2 million** | 5 years | 7-12 years post-PhD |
| **Advanced Grant (AdG)** | Up to **€2.5 million** | 5 years | Established leaders |
| **Synergy Grant (SyG)** | Up to **€10 million** | 6 years | 2-4 PIs jointly |
| **Proof of Concept (PoC)** | Up to **€150,000** | 18 months | ERC grantees only |

### Additional Funding Options

- **Top-up funding**: Additional €1 million available for Starting, Consolidator, and Advanced Grants when major equipment purchase is justified
- **Budget flexibility**: Up to 25% can be used for personnel costs at different rates
- **Funding rate**: **100%** of eligible direct costs + 25% indirect costs

### Proof of Concept Details

ERC grantees (current or past) can apply for **Proof of Concept (PoC)** grants to explore commercial or societal potential:
- Up to **€150,000** per PoC project
- Maximum 18 months duration
- Up to 3 PoC grants per ERC frontier research project

### Key Eligibility Points

- Host institution must be in an **EU Member State or Associated Country**
- Principal Investigator (PI) can be of **any nationality**
- PI must commit at least **50% of working time** to the ERC project
- Only criterion: **scientific excellence** (no thematic restrictions)

---

📊 **Source:** [European Research Council Official Website](https://erc.europa.eu/funding) | [ERC Work Programme 2025](https://erc.europa.eu/funding/work-programmes)

📈 **Success Rates (2024-2025):**
- Starting Grant: ~12-15%
- Consolidator Grant: ~11-15%
- Advanced Grant: ~10-12%
- Synergy Grant: ~8-10%

*(Source: ERC Statistics - [erc.europa.eu/news-events](https://erc.europa.eu/news-events))*

---

🎯 **Next Steps:**
1. **Check eligibility**: Review career stage requirements on [ERC eligibility page](https://erc.europa.eu/apply-grant/starting-grant)
2. **Find a host**: Identify an institution in EU/Associated Country
3. **Review past projects**: Browse [ERC-funded projects](https://erc.europa.eu/projects-figures/erc-funded-projects)
4. **Contact NCP**: Get free advice from your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)
5. **Check deadlines**: Visit [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search?keywords=ERC)

📞 **Questions?** Contact ERC directly via [ERC Contact](https://erc.europa.eu/contact) or your national ERC NCP."""

    def _generate_cluster_comparison_guidance(
        self, query: str, cluster_matches: list, context: str
    ) -> dict[str, Any]:
        """Generate comprehensive cluster comparison guidance using built-in knowledge."""

        # Cluster information from built-in knowledge
        cluster_info = {
            "1": {
                "name": "Cluster 1 - Health",
                "focus": "Disease prevention, treatment, healthcare systems, pandemic preparedness, cancer research, personalized medicine",
                "budget": "~€8.2 billion",
                "topics": "HORIZON-HLTH-*",
                "success_rate": "14-17%",
                "typical_project": "Clinical trials, health technology, disease prevention studies",
                "competition": "High (strong medical research community, many universities)",
            },
            "2": {
                "name": "Cluster 2 - Culture, Creativity & Inclusive Society",
                "focus": "Cultural heritage, democracy, social transformation, creative industries",
                "budget": "~€2.3 billion",
                "topics": "HORIZON-CL2-*",
                "success_rate": "16-20%",
                "typical_project": "Social sciences, cultural heritage preservation, governance research",
                "competition": "Moderate (specialized field)",
            },
            "3": {
                "name": "Cluster 3 - Civil Security for Society",
                "focus": "Disaster resilience, cybersecurity, border security, crime prevention",
                "budget": "~€1.6 billion",
                "topics": "HORIZON-CL3-*",
                "success_rate": "15-18%",
                "typical_project": "Security systems, crisis management, cybersecurity solutions",
                "competition": "Moderate (specialized security sector)",
            },
            "4": {
                "name": "Cluster 4 - Digital, Industry & Space",
                "focus": "AI, data, robotics, manufacturing, advanced materials, space technology",
                "budget": "~€15.3 billion",
                "topics": "HORIZON-CL4-*",
                "success_rate": "12-16%",
                "typical_project": "AI systems, industrial automation, satellite technologies",
                "competition": "Very High (large industry interest, many applicants)",
            },
            "5": {
                "name": "Cluster 5 - Climate, Energy & Mobility",
                "focus": "Clean energy, hydrogen, batteries, smart grids, sustainable transport",
                "budget": "~€15.1 billion",
                "topics": "HORIZON-CL5-*",
                "success_rate": "13-16%",
                "typical_project": "Renewable energy systems, green transport, energy storage",
                "competition": "Very High (Green Deal priority, high policy interest)",
            },
            "6": {
                "name": "Cluster 6 - Food, Bioeconomy & Natural Resources",
                "focus": "Sustainable agriculture, food systems, biodiversity, environmental systems",
                "budget": "~€8.9 billion",
                "topics": "HORIZON-CL6-*",
                "success_rate": "14-17%",
                "typical_project": "Sustainable farming, food security, ecosystem restoration",
                "competition": "High (environmental research community)",
            },
        }

        # Determine which clusters to compare
        if len(cluster_matches) >= 2:
            c1, c2 = cluster_matches[0], cluster_matches[1]
        elif len(cluster_matches) == 1:
            c1 = cluster_matches[0]
            c2 = None
        else:
            c1, c2 = "5", "1"  # Default comparison

        info1 = cluster_info.get(c1, cluster_info["5"])
        info2 = cluster_info.get(c2, cluster_info["1"]) if c2 else None

        guidance = f"""## Cluster Comparison: {info1["name"]}"""
        if info2:
            guidance += f" vs {info2['name']}"
        guidance += "\n\n"

        if info2:
            # Two-cluster comparison
            guidance += (
                """| Metric | """
                + info1["name"].split(" - ")[1]
                + """ | """
                + info2["name"].split(" - ")[1]
                + """ |
|--------|---------|---------|
| **Budget (2021-2027)** | """
                + info1["budget"]
                + """ | """
                + info2["budget"]
                + """ |
| **Success Rate** | """
                + info1["success_rate"]
                + """ | """
                + info2["success_rate"]
                + """ |
| **Competition Level** | """
                + info1["competition"]
                + """ | """
                + info2["competition"]
                + """ |
| **Topic Prefix** | """
                + info1["topics"]
                + """ | """
                + info2["topics"]
                + """ |

### Focus Areas

**"""
                + info1["name"]
                + """:**
"""
                + info1["focus"]
                + """

**"""
                + info2["name"]
                + """:**
"""
                + info2["focus"]
                + """

### Key Differences

"""
            )
            # Budget comparison
            budget1 = float(info1["budget"].replace("~€", "").replace(" billion", ""))
            budget2 = float(info2["budget"].replace("~€", "").replace(" billion", ""))
            if budget1 > budget2:
                guidance += f"- **Budget**: {info1['name'].split(' - ')[1]} has {budget1 / budget2:.1f}x more funding available\n"
            else:
                guidance += f"- **Budget**: {info2['name'].split(' - ')[1]} has {budget2 / budget1:.1f}x more funding available\n"

            # Competition analysis
            competition_order = ["Very High", "High", "Moderate", "Low"]
            comp1_idx = next(
                (i for i, c in enumerate(competition_order) if c in info1["competition"]), 2
            )
            comp2_idx = next(
                (i for i, c in enumerate(competition_order) if c in info2["competition"]), 2
            )

            if comp1_idx < comp2_idx:
                guidance += (
                    f"- **Competition**: {info1['name'].split(' - ')[1]} is more competitive\n"
                )
            elif comp2_idx < comp1_idx:
                guidance += (
                    f"- **Competition**: {info2['name'].split(' - ')[1]} is more competitive\n"
                )
            else:
                guidance += f"- **Competition**: Both clusters have similar competition levels ({info1['competition']})\n"

            guidance += (
                """
### Typical Projects

**"""
                + info1["name"].split(" - ")[1]
                + """**: """
                + info1["typical_project"]
                + """

**"""
                + info2["name"].split(" - ")[1]
                + """**: """
                + info2["typical_project"]
                + """
"""
            )
        else:
            # Single cluster detail
            guidance += f"""**Focus**: {info1["focus"]}

| Metric | Value |
|--------|-------|
| **Budget (2021-2027)** | {info1["budget"]} |
| **Success Rate** | {info1["success_rate"]} |
| **Competition** | {info1["competition"]} |
| **Topic Prefix** | {info1["topics"]} |

**Typical Projects**: {info1["typical_project"]}
"""

        guidance += """
**Next Steps:**
- You should explore open funding calls on the EU Funding & Tenders Portal (https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- You can search for specific call topics using the HORIZON-CL5-* or HORIZON-HLTH-* prefixes
- Consider analyzing your organization's track record and competitive positioning for each cluster
- Visit the European Commission's research pages for the latest Work Programme information
- Contact your National Contact Points (NCPs) for cluster-specific guidance and support
"""

        return {
            "thought": "User is asking about cluster comparison. Providing comprehensive guidance from built-in knowledge.",
            "action": "generate_guidance",
            "response": guidance,
            "guidance_type": "cluster_comparison",
            "confidence": 0.90,
            "needs_more_info": False,
        }

    def _generate_org_type_budget_guidance(
        self, query: str, action_type: str | None, context: str
    ) -> dict[str, Any]:
        """Generate guidance about budget variations by organization type."""

        action_desc = f" for {action_type} projects" if action_type else ""

        guidance = f"""## Budget Variation by Organization Type{action_desc}

Budget allocation varies significantly by organization type in Horizon Europe projects. Here's how funding typically breaks down:

### Typical Budget Share by Organization Type

| Organization Type | Budget Share | Typical Per-Org Budget | Role |
|-------------------|-------------|------------------------|------|
| **Universities (HES)** | 35-45% | €300K-600K | Research leadership, fundamental research |
| **Research Centers (REC)** | 25-35% | €400K-800K | Applied research, technology development |
| **Companies (PRC)** | 15-25% | €200K-500K | Innovation, commercialization, demonstrations |
| **Public Bodies (PUB)** | 5-10% | €100K-300K | Policy, regulation, stakeholder engagement |
| **Other (OTH)** | 5-10% | €50K-200K | SME support, NGOs, associations |

### Key Factors Affecting Budget by Org Type

1. **Funding Rate Impact**
   - Non-profit orgs (HES, REC, PUB): 100% funding rate
   - For-profit orgs (PRC): 70% for RIA, 60% for IA

2. **Typical Activities by Type**
   - **HES/REC**: WP leadership, large research tasks, personnel-heavy
   - **PRC**: Demonstration, pilot production, market analysis
   - **PUB**: Dissemination, policy recommendations, regulatory input

3. **Personnel Cost Variations**
   - Universities: €50K-80K per person-year
   - Research centers: €70K-100K per person-year
   - Companies: €80K-120K per person-year

**Next Steps:**
- You should check your consortium balance against these benchmarks
- Review the [Horizon Europe Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf) for budget rules
- Consider using the EU Funding Portal's budget template
- Contact your National Contact Point for organization-specific guidance
"""

        return {
            "thought": "User is asking about budget variation by organization type. Providing comprehensive guidance from built-in knowledge.",
            "action": "generate_guidance",
            "response": guidance,
            "guidance_type": "org_type_budget",
            "confidence": 0.85,
            "needs_more_info": False,
        }

    def _generate_per_partner_budget_guidance(
        self, query: str, action_type: str | None, has_context: bool
    ) -> dict[str, Any]:
        """Generate guidance about per-partner budget allocation."""

        action_desc = f" for {action_type} projects" if action_type else ""

        guidance = f"""## Per-Partner Budget Analysis{action_desc}

Based on analysis of Horizon Europe funded projects, here are the typical per-partner budget ranges:

### Average Per-Partner Budget by Action Type

| Action Type | Average Per-Partner | Range | Typical Consortium |
|-------------|--------------------|---------|--------------------|
| **RIA** | €350K-400K | €200K-600K | 12-15 partners |
| **IA** | €300K-450K | €150K-700K | 10-12 partners |
| **CSA** | €150K-250K | €80K-400K | 8-12 partners |
| **EIC Accelerator** | €2.5M (mono) | €0.5M-15M | Single company |

### Per-Partner Budget Breakdown

For a typical €5M RIA project with 12 partners:

| Category | Amount | % of Per-Partner |
|----------|--------|------------------|
| **Personnel** | €250K-300K | 60-70% |
| **Travel & Meetings** | €15K-25K | 4-6% |
| **Equipment** | €25K-50K | 6-12% |
| **Other Direct Costs** | €20K-40K | 5-10% |
| **Subcontracting** | €10K-30K | 2-7% |
| **Indirect Costs (25%)** | €70K-90K | 18-22% |

### Factors Affecting Per-Partner Budget

1. **Role**: Coordinators get 1.5-2x average
2. **Work Package Leadership**: WP leaders get larger shares
3. **Organization Type**: Research centers often have higher costs
4. **Location**: Personnel costs vary by country

**Next Steps:**
- You should check your proposed budget against these benchmarks
- Review funded projects on [CORDIS](https://cordis.europa.eu/) to see real budget distributions
- Use the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) budget template
- Contact your National Contact Point for country-specific cost guidance
- Consider partner expertise and capacity when allocating budgets
"""

        return {
            "thought": "User is asking about per-partner budget allocation. Providing comprehensive guidance with actionable next steps.",
            "action": "generate_guidance",
            "response": guidance,
            "guidance_type": "per_partner_budget",
            "confidence": 0.85,
            "needs_more_info": False,
        }

    def _generate_coordinator_budget_guidance(
        self, query: str, action_type: str | None, context: str
    ) -> dict[str, Any]:
        """Generate guidance about coordinator vs partner budget allocation."""

        action_desc = f" for {action_type} projects" if action_type else ""

        guidance = f"""## Coordinator vs Partner Budget Allocation{action_desc}

The coordinator in a Horizon Europe project typically receives a larger budget share due to additional management responsibilities. Here's how it breaks down:

### Budget Distribution by Role

| Role | Budget Share | Additional Responsibilities |
|------|-------------|----------------------------|
| **Coordinator** | 15-25% of total | WP1 Management, financial reporting, EC liaison |
| **WP Leaders** | 10-15% each | Work package management, deliverable coordination |
| **Regular Partners** | 5-10% each | Research tasks, deliverable contributions |

### Coordinator Budget Premium

The coordinator typically receives **1.5x to 2.5x** the average partner budget because of:

1. **Project Management (WP1)**
   - 5-10% of total budget dedicated to management
   - Project Manager, Financial Manager, Admin support
   - ~12-24 person-months typically

2. **Financial Coordination**
   - Managing EC payments and distributions
   - Audits and financial reporting
   - Consortium Agreement management

3. **Technical Leadership**
   - Usually leads additional research WPs
   - Scientific coordination meetings
   - Publication and dissemination coordination

### Typical Budget Example (€5M RIA, 12 partners)

| Role | Budget | % of Total |
|------|--------|------------|
| Coordinator | €750K-1M | 15-20% |
| 3 WP Leaders | €500K each | 10% each |
| 8 Partners | €300K each | 6% each |

### Coordinator Responsibilities

- **Administrative**: EC correspondence, amendments, reporting
- **Financial**: Payment management, audit coordination
- **Technical**: Integration, quality assurance
- **Legal**: Consortium agreement, IP management

**Next Steps:**
- You should budget 5-10% of your total for dedicated project management
- Review coordinator responsibilities in the [Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf)
- Check the [Online Manual](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/om_en.pdf) for coordination requirements
- Consider coordinator experience when selecting your lead partner
"""

        return {
            "thought": "User is asking about coordinator vs partner budget allocation. Providing comprehensive guidance from built-in knowledge.",
            "action": "generate_guidance",
            "response": guidance,
            "guidance_type": "coordinator_budget",
            "confidence": 0.85,
            "needs_more_info": False,
        }

    def _generate_minimum_requirements_guidance(self) -> str:
        """Generate guidance on minimum requirements for urgent deadline submission."""
        return """Given the imminent deadline, you should focus on the **absolute minimum elements** that, if missing, will lead to automatic ineligibility or immediate rejection. Here is your essential checklist:

### 1. Administrative Section - CRITICAL for Eligibility

These are entered directly into the **Funding & Tenders Portal**. Without these, your submission is invalid:

| Element | What You Must Have | Action Required |
|---------|-------------------|-----------------|
| **PIC Numbers** | All partners must have valid Participant Identification Codes | Check at [Participant Register](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/participant-register) |
| **Legal Entity Data** | All partners validated in the system | Verify validation status for each partner |
| **Declaration of Honour** | Signed by legal representative | Download template from the portal |
| **Financial Capacity** | LEAR/Self-declaration for SMEs | Have documents ready |

### 2. Technical Description - MINIMUM for Admissibility

These are uploaded as PDF and must meet minimum page/content requirements:

| Section | Minimum Content You Need |
|---------|-------------------------|
| **Excellence** | Objectives, state-of-art, methodology - can be high-level but coherent |
| **Impact** | Expected impacts, target groups, dissemination plan |
| **Implementation** | Work packages, deliverables, milestones, Gantt chart |
| **Budget Table** | Completed in portal - numbers can be estimates |

### 3. What You Can Leave Imperfect (Won't Cause Rejection)

✅ **Budget details**: Use reasonable estimates, can be adjusted in Grant Agreement
✅ **CVs**: Brief is acceptable, full details not mandatory
✅ **LOIs from partners**: Helpful but not always required (check call text)
✅ **Detailed dissemination plan**: Outline is sufficient
✅ **Detailed risk analysis**: Basic risks are acceptable

### 4. Minimum Consortium You Need

| Action Type | Minimum Partners | Countries |
|-------------|-----------------|-----------|
| **RIA/IA** | 3 legal entities | 3 EU/Associated |
| **CSA** | 1-3 typically | Check specific call |
| **EIC Accelerator** | 1 (single applicant) | 1 EU/Associated |
| **MSCA** | 1-2 typically | Check specific call |

---

🎯 **Next Steps - What You Should Do Immediately:**

1. **TODAY**: Verify all partners have valid PICs at the Participant Register
2. **WITHIN 48 HOURS**: Complete administrative forms in the portal
3. **WITHIN 1 WEEK**: Draft technical sections (Excellence, Impact, Implementation)
4. **3 DAYS BEFORE DEADLINE**: Complete internal review and finalize
5. **DEADLINE DAY**: Submit early (portal can crash near deadline)

📞 **Get Help**: Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for topic-specific guidance

⚠️ **Critical Warning**: The portal closes at **17:00 Brussels time** on the deadline. Submit at least 2 hours early to avoid technical issues."""

    def _generate_feasibility_prioritization_guidance(self, context: str) -> str:
        """Generate guidance on prioritizing calls by feasibility."""
        # Check context for specific calls mentioned
        has_specific_calls = any(
            pattern in context.lower()
            for pattern in ["horizon-", "erasmus-", "crea-", "call id", "cl5", "cl4", "cl1"]
        )

        specific_advice = ""
        if has_specific_calls:
            specific_advice = """
### Assessment of Your Identified Calls

Based on the calls you've identified, here's how to prioritize:

**Higher Feasibility Indicators:**
- Calls where you have existing consortium partners
- Topics aligned with your current research/activities
- Smaller budget calls (€1-3M vs €10M+)
- Calls you've submitted to before

**Lower Feasibility Indicators:**
- Completely new consortium needed
- New research area for your organization
- Large-scale actions requiring 10+ partners
- High TRL requirements (TRL 7-9) without prior demos
"""

        return f"""To prioritize funding calls by feasibility when time is limited, you should assess each call against these criteria. Here is a systematic framework:

### Feasibility Assessment Framework

| Factor | High Feasibility (Score 3) | Medium (Score 2) | Low (Score 1) |
|--------|--------------------------|------------------|---------------|
| **Consortium Readiness** | Partners identified & committed | Some partners identified | Need to find partners |
| **Topic Alignment** | Direct match to your work | Related to your work | New area for you |
| **Budget Complexity** | Simple, small budget | Medium complexity | Large, multi-layer |
| **Prior Experience** | Submitted similar before | Some experience | First time |
| **Documentation Ready** | Substantial content exists | Some materials exist | Starting fresh |
| **Time vs. Requirements** | >4 weeks, manageable | 2-4 weeks, challenging | <2 weeks, very tight |

### Priority Decision Matrix

| Total Score | Recommendation | Action |
|-------------|---------------|--------|
| **15-18** | **HIGH PRIORITY** - Submit this call | Focus 80% of effort here |
| **10-14** | **MEDIUM PRIORITY** - Consider if time permits | Prepare outline, decide at -2 weeks |
| **6-9** | **LOW PRIORITY** - Risky given timeline | Skip or plan for next cut-off |
{specific_advice}
### Time-Based Prioritization Rules

When you have **multiple calls with similar deadlines**, prioritize based on:

1. **First**: Calls where consortium is already confirmed
2. **Second**: Calls building on previous (rejected) proposals
3. **Third**: Calls in your core expertise area
4. **Last**: New areas requiring new partnerships

### Success Rate Reality Check

| Action Type | Typical Success Rate | Your Odds with Rush Preparation |
|-------------|---------------------|--------------------------------|
| **RIA/IA (standard)** | 12-18% | -5% (limited preparation time) |
| **CSA** | 15-25% | May be acceptable (simpler) |
| **EIC Accelerator** | 8-10% | Single applicant, may work |
| **MSCA Postdoc** | 15-20% | Can work if researcher ready |

---

🎯 **Next Steps - What You Should Do Now:**

1. **Score each call** using the framework above (takes 10 minutes per call)
2. **Select top 1-2 calls** with scores ≥ 12 to focus your effort
3. **Allocate time**: 70% to highest priority, 30% to backup
4. **Set go/no-go checkpoint** at -2 weeks from deadline
5. **Contact your NCP** for quick topic guidance

📋 **Decision Template**: For each call, ask:
- Do we have 3+ committed partners? (Yes = +3 points)
- Have we worked on this topic before? (Yes = +3 points)
- Do we have draft content to reuse? (Yes = +2 points)
- Is budget under €3M? (Yes = +2 points)

⚠️ **Important**: A focused, high-quality submission to ONE call beats rushed, weak submissions to multiple calls. Quality over quantity wins in EU funding."""

    def _generate_rapid_preparation_guidance(self) -> str:
        """Generate guidance on rapid proposal preparation for urgent deadlines."""
        return """When you have limited time to prepare a proposal, you need to focus ruthlessly on what matters most. Here is your rapid preparation strategy:

### Rapid Preparation Timeline (2-4 Weeks)

| Days Before Deadline | Focus Area | Deliverable |
|---------------------|-----------|-------------|
| **-28 to -21** | Consortium & concept | Partner commitment, 1-page concept |
| **-21 to -14** | Part B drafting | Excellence & Impact sections |
| **-14 to -7** | Implementation | Work packages, budget, Gantt |
| **-7 to -3** | Integration | Complete Part B, internal review |
| **-3 to -1** | Finalization | Portal submission, Part A check |
| **Day 0** | Submit | Submit before 15:00 Brussels time |

### Shortcuts That Work

✅ **Reuse existing content**: Adapt from previous proposals, project descriptions, papers
✅ **Partner expertise sections**: Ask partners to write their own WP descriptions
✅ **Budget templates**: Use previous budgets as templates, adjust numbers
✅ **Generic impact text**: Standard dissemination plans can be adapted quickly

### What To Skip (Save Time)

❌ **Perfect language**: Clarity beats eloquence - evaluators read fast
❌ **Extensive state-of-art**: Focus on what you'll do differently
❌ **Detailed risk analysis**: 5-6 key risks is sufficient
❌ **Comprehensive bibliography**: 20-30 key references enough

### Emergency Consortium Building

If you need partners urgently:

| Source | Response Time | Success Rate |
|--------|--------------|--------------|
| **Previous project partners** | 1-2 days | High |
| **NCP partner search** | 3-5 days | Medium |
| **Topic-specific networks** | 2-4 days | Medium |
| **EEN Enterprise Europe** | 3-7 days | Medium |
| **Cold outreach** | 5-10 days | Low |

---

🎯 **Next Steps - What You Should Do TODAY:**

1. **Confirm consortium**: Email all partners asking for commitment by tomorrow
2. **Draft 1-page concept**: Define objectives, approach, expected impact
3. **Create shared folder**: Set up collaborative document for all sections
4. **Book daily check-ins**: 15-minute sync calls until submission
5. **Contact your NCP**: They can provide templates and quick guidance

📞 **Emergency Help Resources**:
- National Contact Points: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp
- European IPR Helpdesk: https://intellectual-property-helpdesk.ec.europa.eu/
- Research Executive Agency: https://rea.ec.europa.eu/

⚠️ **Quality Threshold**: A rushed proposal still needs to meet minimum quality. If you can't produce a coherent Excellence + Impact + Implementation within the timeline, consider the next cut-off date instead."""

    def _generate_time_assessment_guidance(self, context: str) -> str:
        """Generate guidance on time feasibility for applying to funding calls."""
        # Try to extract deadline info from context
        has_deadline_info = any(
            pattern in context.lower()
            for pattern in ["february", "march", "deadline", "2026", "2025"]
        )

        deadline_context = ""
        if has_deadline_info:
            deadline_context = """
### Your Current Deadlines

Based on the calls you've identified, you have deadlines approaching. Here's your time assessment:

| Deadline Timeframe | Realistic Assessment |
|-------------------|---------------------|
| **< 2 weeks** | 🔴 Very challenging - only feasible with existing consortium + reusable content |
| **2-4 weeks** | 🟡 Tight but doable - requires full-time effort + committed partners |
| **4-8 weeks** | 🟢 Achievable - standard preparation timeline if you start NOW |
| **> 8 weeks** | ✅ Comfortable - full preparation possible with quality focus |
"""

        return f"""Yes, whether you have time to apply depends on several factors. Here's your honest assessment:

### Time Feasibility Assessment

| Factor | Question to Ask | Impact on Feasibility |
|--------|----------------|----------------------|
| **Consortium Status** | Do you have confirmed partners? | +++ if yes, --- if no |
| **Previous Experience** | Have you submitted similar proposals before? | ++ if yes, - if no |
| **Reusable Content** | Do you have draft materials to adapt? | ++ if yes, - if no |
| **Availability** | Can you dedicate significant time? | +++ if yes, - if no |
| **Technical Readiness** | Is your research concept mature? | ++ if yes, -- if no |
{deadline_context}
### Realistic Time Requirements

| Scenario | Minimum Time Needed | Success Likelihood |
|----------|--------------------|--------------------|
| **Resubmission** (existing proposal) | 2-3 weeks | Higher (know what to fix) |
| **Experienced team** (done it before) | 4-6 weeks | Good (efficient process) |
| **New consortium** (first time together) | 6-8 weeks | Medium (coordination overhead) |
| **First EU proposal** (no experience) | 8-12 weeks | Lower (learning curve) |

### Critical Path for Urgent Deadlines

If you decide to proceed with a tight deadline:

1. **Week 1**: Finalize consortium, distribute work, draft concept
2. **Week 2**: Write Excellence and Impact sections (50% complete)
3. **Week 3**: Complete Implementation, budget, work packages
4. **Week 4**: Internal review, final edits, portal submission

---

🎯 **Next Steps - What You Should Do NOW:**

1. **Assess your consortium**: Can you confirm 3+ committed partners within 48 hours?
2. **Check your calendar**: Can you dedicate 50%+ of your time until deadline?
3. **Inventory existing content**: What can you reuse from previous proposals/papers?
4. **Go/No-Go decision**: Be honest - better to skip than submit weak proposal
5. **If GO**: Start drafting the Excellence section TODAY

📊 **Decision Framework**:
- If you score 4+ on the factors above: **Proceed with confidence**
- If you score 2-3: **Proceed with caution**, have backup plan
- If you score <2: **Consider next cut-off** or partner role only

📞 **Get Quick Help**: Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for topic-specific advice - they can help assess feasibility

⚠️ **Important**: A weak proposal wastes everyone's time. Success rates are 12-15% for good proposals, much lower for rushed ones. Quality over quantity!"""

    def _generate_he_preparation_time_guidance(self) -> str:
        """Generate guidance on Horizon Europe proposal preparation time."""
        return """The typical preparation time for a competitive Horizon Europe proposal (such as a Research and Innovation Action/RIA or Innovation Action/IA) ranges from **6 to 9 months**.

While intense drafting occurs in the final 2-3 months, highly successful proposals require extensive preparation in the preceding phases, particularly for consortium building and strategic alignment with the specific call topic.

### Proposal Preparation Timeline Breakdown

| Phase | Duration | Key Activities |
|-------|----------|----------------|
| **Strategic Planning** | 2-3 months | Topic analysis, consortium design, partnership identification |
| **Consortium Building** | 2-3 months | Partner recruitment, role distribution, commitment letters |
| **Proposal Writing** | 2-3 months | Scientific excellence, impact, implementation sections |
| **Review & Refinement** | 2-4 weeks | Internal reviews, budget finalization, quality checks |

### Factors That Affect Preparation Time

| Factor | Shorter Preparation | Longer Preparation |
|--------|--------------------|--------------------|
| **Consortium Status** | Existing partners | New consortium formation |
| **Topic Familiarity** | Previous submissions | New research area |
| **Budget Complexity** | Simple structure | Multi-country, complex budget |
| **Call Type** | Standard RIA/IA | Partnerships, Missions |
| **Coordinator Experience** | Experienced | First-time coordinator |

### Time Requirements by Action Type

| Action Type | Typical Prep Time | Key Considerations |
|-------------|------------------|-------------------|
| **RIA (Research & Innovation)** | 6-9 months | Deep scientific content needed |
| **IA (Innovation Action)** | 5-8 months | Focus on demonstration plan |
| **CSA (Coordination & Support)** | 4-6 months | Network/coordination focus |
| **EIC Accelerator** | 3-6 months | Single applicant, phased |
| **MSCA Postdoctoral** | 2-3 months | Individual fellowship |

---

🎯 **Next Steps - What You Should Do:**
• Start monitoring the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/) 9-12 months before expected deadlines
• Begin consortium building at least 6 months before the deadline
• Contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for topic-specific guidance
• Review similar funded projects on [CORDIS](https://cordis.europa.eu/) to understand successful approaches
• Consider attending Commission info days when calls open"""

    def _generate_erasmus_ka2_comparison_guidance(self) -> str:
        """Generate guidance comparing Erasmus+ KA2 with Horizon Europe timelines."""
        return """Preparing an Erasmus+ Key Action 2 (KA2) Cooperation Partnership proposal is generally **less complex and faster** than a Horizon Europe (HE) Research and Innovation Action (RIA), largely due to differences in evaluation focus, consortium size, and budget structure.

### Comparison: HE (RIA/IA) vs. Erasmus+ KA2

| Feature | Horizon Europe (RIA/IA) | Erasmus+ KA2 (Cooperation Partnerships) |
|---------|------------------------|----------------------------------------|
| **Typical Preparation Time** | **6-9 months** | **3-5 months** |
| **Consortium Size** | 8-15 partners | 3-6 partners |
| **Budget Complexity** | Detailed cost categories | Lump sum model |
| **Evaluation Focus** | Scientific excellence, innovation | Educational impact, best practices |
| **Proposal Length** | 50-70 pages | 20-40 pages |
| **Technical Annexes** | Multiple (budget, LoIs, CVs) | Fewer required |

### Why Erasmus+ KA2 is Faster to Prepare

✅ **Simpler Budget Model**
- Erasmus+ uses lump sum funding (fixed amounts based on project size)
- No need for detailed cost breakdowns per partner
- Reduces financial planning complexity

✅ **Smaller Consortia**
- Minimum 3 partners from 3 countries
- Easier to coordinate, faster agreements
- Smaller consortia = faster consensus

✅ **Focused Scope**
- Clear educational objectives
- Less technical innovation documentation needed
- Emphasis on practical implementation

### Typical KA2 Preparation Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Partnership Building** | 4-8 weeks | Finding partners, alignment |
| **Concept Development** | 2-3 weeks | Objectives, activities, outputs |
| **Proposal Writing** | 3-4 weeks | Application form, work packages |
| **Internal Review** | 1-2 weeks | Partner review, finalization |

### Key Differences in Effort

| Aspect | Horizon Europe | Erasmus+ KA2 |
|--------|---------------|--------------|
| Scientific methodology | Extensive | Moderate |
| Innovation description | Detailed TRL analysis | Activity-focused |
| Impact assessment | Multi-level | Educational outcomes |
| Budget justification | Line-by-line | Lump sum categories |

---

🎯 **Next Steps - What You Should Do:**
• Check the [Erasmus+ Programme Guide 2026](https://erasmus-plus.ec.europa.eu/) for detailed eligibility and deadlines
• Use the [Partner Search Tool](https://erasmus-plus.ec.europa.eu/partner-search) to find collaborators
• Contact your [Erasmus+ National Agency](https://erasmus-plus.ec.europa.eu/national-agencies) for guidance
• Review successful projects on the [Erasmus+ Project Results Platform](https://erasmus-plus.ec.europa.eu/projects)
• Consider starting 4-5 months before the deadline for a strong application"""

    def _generate_creative_europe_timeline_guidance(self) -> str:
        """Generate guidance on Creative Europe cooperation project timelines."""
        return """Creative Europe Cooperation Projects (Culture strand) are distinctly different from Horizon Europe (HE) and Erasmus+ (E+ KA2), focusing on cultural policy, audience development, and the transnational circulation of cultural works, with a mandatory co-funding model.

### Comparison: HE (RIA/IA), Erasmus+ KA2, and Creative Europe (CE Culture)

| Feature | Horizon Europe (RIA/IA) | Erasmus+ KA2 | Creative Europe (COOP) |
|---------|------------------------|--------------|------------------------|
| **Preparation Time** | **6-9 months** | **3-5 months** | **3-6 months** |
| **Consortium Size** | 8-15 partners | 3-6 partners | 3-10+ partners |
| **Funding Rate** | 100% (RIA) / 70% (IA) | 100% (lump sum) | **60-80%** (co-funding) |
| **Budget Model** | Cost categories | Lump sum | Lump sum with co-funding |
| **Focus** | Research & innovation | Education & training | Arts & culture |

### Creative Europe Project Scales

| Scale | Min Partners | Countries | Grant Range | Preparation |
|-------|-------------|-----------|-------------|-------------|
| **Small** | 3 partners | 3 countries | €200K-400K | 3-4 months |
| **Medium** | 5 partners | 5 countries | €400K-1M | 4-5 months |
| **Large** | 10 partners | 10 countries | €1M-2M | 5-6 months |

### Key Differences That Affect Preparation

| Aspect | Impact on Timeline |
|--------|-------------------|
| **Co-funding requirement** | Partners need 20-40% matching → longer partner negotiations |
| **Cultural sector focus** | Specific expertise needed → specialized consortium |
| **Audience development** | Detailed dissemination plans required |
| **European dimension** | Strong transnational collaboration must be demonstrated |

### Typical Creative Europe Preparation Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Consortium Formation** | 4-8 weeks | Partner identification, co-funding confirmation |
| **Concept Development** | 2-4 weeks | Artistic vision, European dimension |
| **Application Writing** | 3-5 weeks | Impact, work plan, budget |
| **Co-funding Validation** | 2-3 weeks | Confirm partner contributions |
| **Review & Submission** | 1-2 weeks | Quality check, submission |

### Budget Considerations

Unlike Horizon Europe's 100% funding, Creative Europe requires **20-40% co-funding**:
- Small-scale: 80% EU funding → 20% partner co-funding
- Medium/Large: 60-70% EU funding → 30-40% partner co-funding

This means more time is needed to confirm partner financial commitments.

---

🎯 **Next Steps - What You Should Do:**
• Check the [Creative Europe Work Programme](https://creative-europe.ec.europa.eu/) for current priorities
• Verify your organization's eligibility on the [Funding Portal](https://ec.europa.eu/info/funding-tenders/)
• Contact your [Creative Europe Desk](https://creative-europe-desks.ec.europa.eu/) for national guidance
• Confirm co-funding availability with potential partners early
• Review successful projects in the [Creative Europe database](https://creative-europe.ec.europa.eu/projects)"""

    def _generate_decision_time_comparison_guidance(self) -> str:
        """Generate guidance comparing decision times across programmes."""
        return """For the fastest time to **final grant agreement signature** for a collaborative project, **Erasmus+ Key Action 2 (KA2)** is typically the quickest, while the **EIC Accelerator** (part of Horizon Europe) has the fastest initial decision for single-applicant instruments.

Decision times are usually measured by the **Time to Grant (TTG)**, which is the period from the submission deadline to the signature of the Grant Agreement. Official targets set by the European Commission define these periods.

### Comparison: Decision/Evaluation Times

| Programme | Evaluation Period | Time to Grant (TTG) | Total Waiting |
|-----------|------------------|--------------------|--------------:|
| **Erasmus+ KA2** | 2-3 months | **4-5 months** | **4-5 months** |
| **Creative Europe** | 3-4 months | 5-6 months | 5-6 months |
| **Horizon Europe (RIA/IA)** | 4-5 months | **8 months** (target) | 5-8 months |
| **EIC Accelerator** | 2-3 months (step 1) | Variable | Phased process |

### Detailed Breakdown by Programme

#### Erasmus+ KA2 (Fastest for Partnerships)
- **Initial evaluation**: 2-3 months after deadline
- **Results notification**: 3-4 months after deadline
- **Grant Agreement**: 4-5 months after deadline
- ✅ **Advantage**: Simpler evaluation, lump sum reduces negotiation

#### Creative Europe
- **Initial evaluation**: 3-4 months after deadline
- **Results notification**: 4-5 months after deadline
- **Grant Agreement**: 5-6 months after deadline
- ⚡ **Note**: Co-funding verification adds some time

#### Horizon Europe (RIA/IA)
- **Evaluation completion**: ~5 months after deadline
- **Results notification**: 5 months after deadline (target)
- **Grant Agreement Preparation (GAP)**: 3 months
- **Total Time to Grant**: **8 months** (Commission target)
- ⚠️ **Reality**: Often 6-9 months depending on call oversubscription

#### EIC Accelerator (Phased)
- **Step 1 (Short application)**: 2 months evaluation
- **Step 2 (Full application)**: 3 months evaluation
- **Step 3 (Interview)**: Invited ~1 month after Step 2
- **Final decision**: Variable based on interview scheduling
- 💡 **Note**: Fastest for single companies, but phased approach

### Why Some Programmes Are Faster

| Factor | Fast Decision | Slower Decision |
|--------|--------------|-----------------|
| **Evaluation complexity** | Fewer criteria | Multiple expert panels |
| **Budget model** | Lump sum | Cost-based negotiation |
| **Proposal volume** | Fewer applications | High oversubscription |
| **Consortium size** | Fewer partners | Large consortia |

---

🎯 **Next Steps - What You Should Do:**
• Check the specific call deadline and expected evaluation timeline on the [Funding Portal](https://ec.europa.eu/info/funding-tenders/)
• Plan your project start date 6-8 months after Horizon Europe deadlines
• For Erasmus+, expect results 4-5 months after submission
• Contact your [NCP or National Agency](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for call-specific timing
• Sign up for call notifications to receive result announcements"""

    def _generate_project_start_lag_guidance(self) -> str:
        """Generate guidance on project start lag after selection."""
        return """The project start lag after a positive evaluation result is defined by the **Grant Agreement Preparation (GAP)** phase. For Horizon Europe, the official target duration from the **call deadline to Grant Agreement signature (Time to Grant - TTG)** is typically **8 months**.

Since the selection/evaluation notification usually occurs around **5 months** after the deadline, the administrative lag (GAP phase) until the official project start/signature is typically **3 months**.

### Official Project Start Lag by Programme

| Programme | Selection to Start | Key Administrative Steps |
|-----------|-------------------|------------------------|
| **Horizon Europe** | **3 months** | GAP negotiations, consortium agreement |
| **Erasmus+ KA2** | **1-2 months** | Grant agreement, bank guarantee |
| **Creative Europe** | **2-3 months** | Co-funding validation, contracts |
| **EIC Accelerator** | **2-4 months** | Due diligence, investment terms |

### Grant Agreement Preparation (GAP) Phase

After receiving a positive evaluation result, the following steps occur before the project can officially start:

| Step | Duration | Activities |
|------|----------|-----------|
| **Invitation to GAP** | Week 1-2 | EC invites coordinator to start preparation |
| **Legal/Financial Validation** | 2-4 weeks | All partners validated in participant portal |
| **Consortium Agreement** | 2-4 weeks | Partners sign internal agreement |
| **Budget Finalization** | 1-2 weeks | Final budget accepted by all |
| **Grant Agreement Signature** | 1-2 weeks | Electronic signature by coordinator + EC |
| **Project Start** | Day after signature | Official start date |

### Why Horizon Europe Takes Longer

1. **Complex Consortia**: 8-15 partners need validation
2. **Budget Negotiation**: Detailed cost categories may require adjustments
3. **Consortium Agreement**: Internal negotiations between partners
4. **Legal Entity Validation**: New organizations need full validation

### Why Erasmus+ Starts Faster

1. **Smaller Consortia**: 3-6 partners
2. **Lump Sum Budgets**: No detailed cost negotiations
3. **Simpler Legal Requirements**: Established education institutions

### Project Start Date Options

| Programme | Start Date Flexibility |
|-----------|----------------------|
| **Horizon Europe** | Usually 1st of the month after GAP completion |
| **Erasmus+ KA2** | Fixed by National Agency (often September/October) |
| **Creative Europe** | Flexible within 3 months of signature |

### Timeline Example: Horizon Europe RIA

```
March 15      → Call deadline (proposal submission)
August 15     → Evaluation results (~5 months later)
August 20     → Invitation to GAP
September 15  → Legal validations complete
October 15    → Budget finalized
November 1    → Grant Agreement signed
November 1    → **Project officially starts**
```

---

🎯 **Next Steps - What You Should Do:**
• Ensure all consortium partners are validated in the [Participant Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) before submission
• Prepare draft Consortium Agreement template in advance
• Plan for project activities to start 8-9 months after Horizon Europe deadlines
• For Erasmus+, coordinate with National Agency on fixed start dates
• Check your organization's legal/financial validation status now to avoid delays
• Contact your [NCP or National Agency](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for programme-specific GAP guidance"""

    # =========================================================================
    # DEADLINE TRACKING DETECTION AND GUIDANCE
    # =========================================================================

    def _generate_deadline_time_gap_guidance(self, context: str) -> str:
        """Generate guidance about time gaps between deadlines."""
        # Try to extract deadline info from context
        deadline_examples = ""
        if "february" in context.lower() or "march" in context.lower():
            deadline_examples = """
### Example Timeline from Your Search

Based on the calls you've explored, here's how the timing typically works for Horizon Europe Cluster 4/Digital calls:

| Deadline Window | Typical Call Types | Spacing |
|-----------------|-------------------|---------|
| **Mid-February** | First 2026 cut-offs | Baseline |
| **Late February** | Second wave | 7-10 days later |
| **March** | Extended/specialized topics | 2-4 weeks later |
| **April-May** | Missions & partnerships | 6-10 weeks later |
"""

        return f"""Understanding the time gaps between deadlines helps you plan your proposal strategy and allocate resources effectively.

### Typical Deadline Spacing Patterns

| Programme | Typical Gap Between Related Calls | Strategic Implication |
|-----------|----------------------------------|----------------------|
| **Horizon Europe (same cluster)** | 1-4 weeks | Can reuse content, adjust focus |
| **Horizon Europe (different clusters)** | Variable (1-8 weeks) | Need different consortia |
| **Erasmus+ (same Key Action)** | Annual (February/October) | Plan long-term |
| **Creative Europe** | Variable (call-specific) | Check each strand separately |
{deadline_examples}
### Strategic Implications of Deadline Gaps

| Gap Duration | What It Means | Your Strategy |
|--------------|---------------|---------------|
| **< 7 days** | Same submission window | Choose ONE, submit best proposal |
| **7-14 days** | Sequential opportunity | Submit first, use feedback for second if quick |
| **2-4 weeks** | Related cut-offs | Can refine between submissions |
| **> 4 weeks** | Separate preparation cycles | Can pursue both with distinct proposals |

### When Deadlines Are Close Together

If you have multiple deadlines within 1-2 weeks:

1. **Assess consortium fit**: Which call best matches your existing partners?
2. **Evaluate topic alignment**: Which call directly addresses your research?
3. **Check budget ranges**: Which budget matches your consortium capacity?
4. **Consider competition**: Broader topics may have more competitors

### When Deadlines Are Spread Apart

If you have 4+ weeks between opportunities:

1. **Submit to first deadline**, then assess
2. **Adapt proposal** for second deadline if rejected
3. **Split consortium** if expertise allows parallel submissions
4. **Use first feedback** to strengthen second submission

---

🎯 **Next Steps - What You Should Do:**

1. **Map your deadlines**: Create a timeline with all relevant calls and their exact dates
2. **Assess overlap**: Identify which deadlines you can realistically pursue together
3. **Allocate resources**: Budget your team's time based on the gaps
4. **Set milestones**: Work backwards from each deadline to plan drafting phases
5. **Check the [Funding Portal](https://ec.europa.eu/info/funding-tenders/)** for exact dates and any updates

📊 **Decision Rule**: If two deadlines are within 10 days, focus 100% on the better-fit call. If they're 3+ weeks apart, you can pursue both with careful planning.

⚠️ **Important**: Quality beats quantity. One excellent proposal is worth more than two rushed ones. If gaps are tight, prioritize depth over breadth."""

    def _generate_deadline_targeting_guidance(self, context: str) -> str:
        """Generate guidance on which deadline to target."""
        # Extract any cluster/topic hints from context
        cluster_context = ""
        if (
            "cluster 4" in context.lower()
            or "cl4" in context.lower()
            or "digital" in context.lower()
        ):
            cluster_context = """
### Cluster 4 (Digital) Specific Considerations

For Digital/Industry/Space calls, consider:
- **TRL requirements**: Digital calls often expect higher TRL (5-7)
- **SME involvement**: Many calls require SME participation
- **Cross-cutting themes**: AI, cybersecurity, data topics overlap
- **Dual-use restrictions**: Some topics have security considerations
"""

        return f"""Choosing the right deadline to target is a strategic decision. Here's a framework to help you decide:

### Deadline Selection Framework

| Factor | Weight | Score 1-5 | Your Assessment |
|--------|--------|-----------|-----------------|
| **Topic Alignment** | 30% | _____ | How well does the call match your core expertise? |
| **Consortium Readiness** | 25% | _____ | Do you have confirmed, committed partners? |
| **Time to Deadline** | 20% | _____ | Is there enough time for quality preparation? |
| **Budget Match** | 15% | _____ | Does your consortium capacity fit the budget range? |
| **Competition Level** | 10% | _____ | Is this a niche topic or highly competitive? |
{cluster_context}
### Decision Matrix

| Total Score | Recommendation | Action |
|-------------|---------------|--------|
| **4.0 - 5.0** | Strong candidate | Prioritize this deadline |
| **3.0 - 3.9** | Good potential | Pursue if resources allow |
| **2.0 - 2.9** | Risky | Consider if no better options |
| **< 2.0** | Not recommended | Skip or plan for next cycle |

### Quick Decision Questions

Answer these to identify your best target:

1. **Which call do your partners prefer?** (Their commitment matters)
2. **Which topic have you worked on before?** (Reuse saves time)
3. **Which deadline gives you the most preparation time?** (Quality needs time)
4. **Which budget best fits your consortium's real costs?** (Realistic budgets win)

### If You're Torn Between Two Calls

| Scenario | Recommendation |
|----------|---------------|
| **One earlier, one later** | Submit to earlier if ready; use feedback for later |
| **Both similar deadlines** | Choose the one with stronger partner commitment |
| **Different budget ranges** | Choose the one matching your consortium's natural size |
| **Different TRL requirements** | Choose the one matching your current technology maturity |

### Red Flags - When NOT to Target a Deadline

❌ **Insufficient time**: Less than 4 weeks for a new consortium
❌ **Missing key partner**: Don't have a critical expertise covered
❌ **Topic mismatch**: Need to "stretch" your research to fit
❌ **Budget mismatch**: Your real costs differ >30% from the range
❌ **TRL gap**: Your technology isn't at the required level

---

🎯 **Next Steps - What You Should Do:**

1. **Score each call** using the framework above (takes 15 minutes)
2. **Consult your consortium**: Which call do partners prefer?
3. **Check topic descriptions**: Read the full call text for requirements
4. **Make your decision**: Choose ONE primary target
5. **Set your backup**: Identify a secondary option if first doesn't work out
6. **Start TODAY**: Begin the proposal process immediately

📋 **Action Items This Week**:
- [ ] Score all candidate calls (1-2 hours)
- [ ] Email consortium for topic preferences (send today)
- [ ] Read full call documentation for top choice
- [ ] Draft 1-page concept note for selected call
- [ ] Contact [NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for topic guidance

⚠️ **Important**: Making a decision and committing fully is better than hedging. Once you choose, focus 100% on that call. You can always target different calls in future rounds."""

    def _generate_multi_call_planning_guidance(self) -> str:
        """Generate guidance for multi-call submission planning."""
        return """Planning multiple proposal submissions in a single quarter is an ambitious but achievable strategy. Here is a structured approach to manage your multi-call submission pipeline effectively:

### Strategic Multi-Call Planning Framework

Applying to 3 calls in one quarter requires careful resource allocation and timeline management. Here is what you should consider:

| Factor | Recommendation | Why It Matters |
|--------|---------------|----------------|
| **Stagger deadlines** | Target calls with 4-6 weeks between deadlines | Allows full focus on each submission |
| **Reuse elements** | Use common methodology/WP sections | Saves 30-40% preparation time |
| **Diverse call types** | Mix RIA, IA, and CSA if relevant | Spreads risk across action types |
| **Team allocation** | Assign lead writers per proposal | Prevents bottlenecks |
| **Consortium overlap** | 50-70% partner overlap is optimal | Reduces coordination overhead |

### Recommended Timeline Structure

For 3 calls with staggered deadlines, structure your work like this:

| Week | Call 1 (Earliest) | Call 2 (Middle) | Call 3 (Latest) |
|------|------------------|-----------------|-----------------|
| 1-4 | **Full drafting** | Concept/partners | Concept only |
| 5-8 | Internal review | **Full drafting** | Partner outreach |
| 9-12 | Final polish | Internal review | **Full drafting** |
| 13-16 | Submit! | Final polish | Internal review |
| 17+ | - | Submit! | Final polish |

### Critical Success Factors

**1. Call Selection Criteria**
You should select calls where:
- Topic directly aligns with your expertise (no "stretching")
- Budget range matches your consortium's natural size
- TRL requirements match your technology maturity
- Deadlines are at least 4 weeks apart

**2. Resource Requirements**
For 3 concurrent proposals, you should have:
- At least 2 experienced proposal writers
- 60-80% of consortium confirmed before starting
- Budget for external review/editing support
- Clear LEAR availability for financial forms

**3. Reusable Components**
You can develop once and adapt:
- Management WP structure (90% reusable)
- Dissemination and exploitation plans (70% reusable)
- Partner capability descriptions (85% reusable)
- Ethics documentation (100% reusable if similar topics)

---

🎯 **Next Steps - What You Should Do Right Now:**

1. **Identify your target calls**: Tell me the topic area (e.g., climate, energy, health) and I can find calls with staggered deadlines for you
2. **Map your consortium capacity**: List your confirmed partners and their writing capacity
3. **Check deadline spread**: Verify calls are 4-6 weeks apart
4. **Create a shared calendar**: Set internal milestones for each call
5. **Designate lead writers**: Assign one person responsible per proposal

📋 **Action Items This Week**:
- [ ] Review open calls in your topic area
- [ ] Survey consortium partners for availability
- [ ] Create proposal tracking spreadsheet
- [ ] Set up shared document folders per call
- [ ] Schedule weekly coordination calls

⚠️ **Important**: Quality over quantity. If you find preparation time too tight, it is better to submit 2 excellent proposals than 3 rushed ones. The pass rate drops significantly with inadequate preparation time."""

    def _generate_deadline_contingency_guidance(self, context: str) -> str:
        """Generate guidance for handling deadline changes in multi-call planning."""
        # Check if we have specific call context
        has_climate_energy = "climate" in context.lower() or "energy" in context.lower()
        topic_context = "climate and energy" if has_climate_energy else "your target area"

        return f"""Deadline changes in Horizon Europe are relatively rare but can happen. Here is how you should handle this contingency effectively:

### Understanding Deadline Changes

| Change Type | Likelihood | Typical Notice | Your Response |
|------------|------------|----------------|---------------|
| **Extension (1-4 weeks)** | Occasional | 2-4 weeks advance | Continue current pace, use extra time for polish |
| **Major postponement** | Rare | 4+ weeks advance | Reallocate resources to other proposals |
| **Call cancellation** | Very rare | Variable | Pivot to alternative calls immediately |
| **New deadline earlier** | Almost never | N/A | Highly unlikely scenario |

### Contingency Planning Strategy

**1. Build Buffer Time**
You should always plan to submit 48-72 hours before the official deadline. This gives you:
- Time to handle portal technical issues
- Opportunity to incorporate last-minute partner feedback
- Flexibility if internal reviews take longer

**2. Maintain Parallel Readiness**
When managing 3 calls in {topic_context}, you should:
- Keep all proposals at minimum viable status throughout
- Avoid putting one proposal "on hold" completely
- Update all proposals weekly, even if briefly

**3. Resource Reallocation Matrix**

If one deadline changes significantly, here is how you should respond:

| Scenario | Action for Extended Call | Action for Other Calls |
|----------|-------------------------|------------------------|
| **Deadline extended 2+ weeks** | Reduce daily effort to 50% | Accelerate other proposals |
| **Deadline postponed 1+ month** | Move to background | Make other calls primary focus |
| **Call cancelled** | Immediately identify backup | No change needed |

### Backup Call Strategy

You should always have 1-2 backup calls identified. Good backup calls share:
- Similar topic alignment to your primary calls
- Deadlines 2-4 weeks after your latest primary deadline
- Compatible budget ranges with your consortium
- Lower competition (check topic popularity if possible)

### Monitoring Deadline Changes

You can track potential changes by:
1. **Subscribe to topic updates** on the Funding & Tenders Portal
2. **Follow programme social media** (Horizon Europe posts announcements)
3. **Contact your National Contact Point (NCP)** - they often receive advance notice
4. **Monitor work programme amendments** (usually published quarterly)

---

🎯 **Next Steps - What You Should Do:**

1. **Set deadline alerts**: Create calendar reminders for official deadlines + your internal deadlines
2. **Identify backup calls**: Find 1-2 alternative calls in your topic area
3. **Create reallocation plan**: Document how you would shift resources if needed
4. **Monitor portal regularly**: Check Funding & Tenders Portal weekly for updates
5. **Build consortium flexibility**: Ensure partners can adjust their commitments if schedules change

📋 **Action Items This Week**:
- [ ] Subscribe to update notifications for your target calls on the [Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [ ] Identify 2 backup calls and add to your tracking document
- [ ] Share contingency plan with consortium partners
- [ ] Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for any rumored changes
- [ ] Set internal deadline 72 hours before official deadline

⚠️ **Important**: The best contingency is good preparation. Well-prepared proposals can absorb schedule disruptions much more easily than rushed ones. Focus on quality first, and flexibility will follow naturally."""

    # =========================================================================
    # SME Eligibility Detection and Guidance (Scenario 030)
    # =========================================================================

    def _generate_sme_definition_guidance(self) -> str:
        """Generate guidance about EU SME definition."""
        return """Yes, understanding the **EU SME definition** is essential for accessing SME-specific funding.

### EU Definition of SME (Small and Medium-sized Enterprise)

To be officially classified as an SME under EU rules, an organization must meet **ALL THREE** criteria:

| Criterion | Threshold | Your Assessment |
|-----------|-----------|-----------------|
| **Staff Headcount** | **< 250 employees** | Count all FTEs (full-time equivalents) |
| **Annual Turnover** | **≤ €50 million** | OR meet balance sheet threshold |
| **Annual Balance Sheet** | **≤ €43 million** | OR meet turnover threshold |

**Note**: You must be under the employee threshold AND under at least ONE of the financial thresholds.

### SME Categories

| Category | Employees | Turnover | Balance Sheet |
|----------|-----------|----------|---------------|
| **Micro** | < 10 | ≤ €2M | ≤ €2M |
| **Small** | < 50 | ≤ €10M | ≤ €10M |
| **Medium** | < 250 | ≤ €50M | ≤ €43M |

### Important Calculation Rules

1. **Full-Time Equivalent (FTE)**: Part-time employees counted proportionally
2. **Annual Average**: Use average over the financial year
3. **Most Recent Accounts**: Use latest approved annual accounts
4. **Newly Created Enterprises**: Can use estimates for first year

### Special Cases

| Situation | Treatment |
|-----------|-----------|
| **Seasonal workers** | Convert to annual FTE |
| **Trainees/apprentices** | Generally excluded from count |
| **Maternity/parental leave** | May be excluded |
| **Recent growth** | Use most recent closed year |

---

🎯 **Next Steps - What You Should Do:**
• Check your employee count using FTE calculation (all contracts, including part-time proportionally)
• Verify your turnover OR balance sheet total from latest approved accounts
• If near the 250 threshold, consider linked/partner enterprise effects (see below)
• Use the [EC SME Self-Assessment Tool](https://ec.europa.eu/growth/smes/sme-definition_en) to verify status
• Keep SME documentation updated for declarations in proposals

📋 **Documents You Should Prepare:**
- [ ] Recent annual accounts (audited if available)
- [ ] Employee register with FTE calculations
- [ ] Ownership structure documentation
- [ ] SME self-declaration form (download from EC website)"""

    def _generate_linked_enterprise_guidance(self) -> str:
        """Generate guidance about linked/partner enterprise rules."""
        return """Your parent company structure **critically affects your SME status**. The EU SME definition includes rules about linked and partner enterprises.

### The Autonomy Criterion

To qualify as an **autonomous SME**, your company must not be:
- Owned **25% or more** by a single enterprise that is NOT itself an SME
- Owned **25% or more** by public bodies (with some exceptions)
- Part of a group through **dominant influence** relationships

### Linked Enterprises (Most Restrictive)

If another enterprise owns **>50%** of your voting rights or shares, you are **linked enterprises**. This means:

| What Counts | Effect on SME Calculation |
|-------------|---------------------------|
| **Employees** | Add 100% of linked enterprise's employees to yours |
| **Turnover** | Add 100% of linked enterprise's turnover |
| **Balance Sheet** | Add 100% of linked enterprise's balance sheet |

**Result**: If your parent has thousands of employees, you likely **DO NOT qualify** as an SME.

### Partner Enterprises (Less Restrictive)

If another enterprise owns **25-50%** of your shares, you are **partner enterprises**:

| What Counts | Effect on SME Calculation |
|-------------|---------------------------|
| **Employees** | Add **proportional share** (e.g., 40% ownership = add 40% of their employees) |
| **Turnover** | Add proportional share |
| **Balance Sheet** | Add proportional share |

### Your Situation Assessment

Given a parent company with thousands of employees:

| Parent Ownership | Your SME Status |
|------------------|-----------------|
| **>50%** | ❌ Almost certainly **NOT an SME** |
| **25-50%** | ⚠️ Likely not an SME (proportional calculation) |
| **<25%** | ✅ Parent doesn't affect SME status |

### Alternative Structures

If you need to preserve SME status:
1. **Reduce parent ownership below 25%** (if commercially viable)
2. **Corporate restructuring** (spin-off, management buyout)
3. **Accept non-SME status** and pursue other funding (see below)

---

🎯 **Next Steps - What You Should Do:**
• Get exact ownership percentage from your parent company
• Check if parent is itself an SME (then cascading rules apply)
• Calculate combined employee count: your FTEs + (ownership % × parent's FTEs)
• Review your articles of association for voting rights vs economic rights differences
• Consult a corporate lawyer about restructuring options if needed
• Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for SME status verification

📋 **Action Items:**
- [ ] Document current ownership structure with percentages
- [ ] Get parent company's employee count, turnover, and balance sheet figures
- [ ] Perform linked/partner enterprise calculation
- [ ] If not SME, research alternative funding paths (RIA, IA, national programmes)"""

    def _generate_non_sme_participation_guidance(self) -> str:
        """Generate guidance about non-SME participation in RIA/IA projects."""
        return """**Yes, absolutely!** If you don't qualify as an SME due to your parent company, you can **still fully participate** in Horizon Europe collaborative research.

### Non-SME Participation in Horizon Europe

| Action Type | Can Non-SMEs Participate? | Funding Rate | Notes |
|-------------|---------------------------|--------------|-------|
| **RIA (Research and Innovation Action)** | ✅ **Yes** | 100% | Full participation, can coordinate |
| **IA (Innovation Action)** | ✅ **Yes** | 70% (or 100% for non-profit) | Full participation, can coordinate |
| **CSA (Coordination and Support Action)** | ✅ **Yes** | 100% | Full participation |
| **MSCA (Marie Skłodowska-Curie)** | ✅ **Yes** | 100% (unit costs) | Full participation |
| **ERC Grants** | ✅ **Yes** | 100% | Host institution any type |

### What You CAN Do as a Non-SME

✅ **Participate as a full partner** in any consortium
✅ **Coordinate RIA/IA projects** (lead the consortium)
✅ **Receive full eligible costs** at applicable funding rates
✅ **Lead work packages** and contribute to all project activities
✅ **Access all standard Horizon Europe actions**

### What You CANNOT Access (SME-only)

❌ EIC Accelerator (SME-only, equity funding)
❌ Eurostars (SME-led R&D)
❌ SME-specific bonus funding in some calls

### Funding Rates for Non-SMEs

| Organization Type | RIA Rate | IA Rate |
|-------------------|----------|---------|
| **Large Company (PRC)** | 100% | 70% |
| **University (HES)** | 100% | 100% |
| **Research Institute (REC)** | 100% | 100% |
| **Public Body (PUB)** | 100% | 100% |

### Strategic Advantages of Being a Large Company Partner

1. **Stronger track record** - Large companies often have more EU project experience
2. **Better financial capacity** - Easier to meet financial sustainability requirements
3. **Industry credibility** - Adds weight to consortium's exploitation potential
4. **Resources for dissemination** - Larger reach for project communication

---

🎯 **Next Steps - What You Should Do:**
• You should search for relevant RIA/IA calls in your research area on the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• You can join consortia as a full partner - check the Partner Search on the Portal
• You should highlight your parent company's resources as an **asset** (not a limitation) in proposals
• Consider your role: large companies often lead demonstration/piloting work packages
• Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for guidance on finding suitable calls

📋 **Immediate Action Items:**
- [ ] Visit Funding & Tenders Portal and search calls by your topic keywords
- [ ] Check open RIA/IA calls with upcoming deadlines
- [ ] Use Partner Search tool to find consortium opportunities
- [ ] Review successful projects in your area via CORDIS database
- [ ] Prepare your organization profile highlighting H2020/HE experience

💡 **Tip**: Being part of a large corporate group can be **advantageous** in Horizon Europe proposals, as it demonstrates capacity to scale up innovations and commercialize results!"""

    def _generate_eic_sme_requirements_guidance(self) -> str:
        """Generate guidance about EIC Accelerator SME requirements."""
        return """Company size is **critical for EIC Accelerator eligibility**. The programme is exclusively designed for Small and Medium-sized Enterprises (SMEs).

### EIC Accelerator SME Requirements

The EIC Accelerator follows the **standard EU SME definition**:

| Criterion | Threshold | Note |
|-----------|-----------|------|
| **Employees** | **< 250 FTE** | Mandatory |
| **Annual turnover** | **≤ €50 million** | OR balance sheet |
| **Annual balance sheet** | **≤ €43 million** | OR turnover |

### Key Difference: EIC is SME-Only

Unlike RIA/IA where any organization can participate, **EIC Accelerator is exclusively for SMEs**:

| Programme | SME Requirement |
|-----------|-----------------|
| **EIC Accelerator** | ❌ **SMEs only** - strict requirement |
| **RIA** | ✅ Open to all legal entities |
| **IA** | ✅ Open to all legal entities |
| **EIC Pathfinder** | ✅ Open to all (consortia) |
| **EIC Transition** | ⚠️ SME-led preferred |

### SME Verification in EIC

EIC conducts **thorough SME verification**:
1. At application stage (self-declaration)
2. Before Grant Agreement signature (detailed check)
3. Linked enterprise calculations are verified
4. Financial statements are reviewed

### If Your Parent Company Affects SME Status

If you don't qualify as an SME due to ownership:

| Alternative | Suitability |
|-------------|-------------|
| **EIC Pathfinder** | ✅ Open to non-SMEs (earlier TRL) |
| **Horizon RIA/IA** | ✅ Full participation |
| **National programmes** | ✅ Many have no SME requirement |
| **Corporate VC/partnerships** | ✅ Direct investment route |

### Timeline Considerations

| Aspect | EIC Accelerator |
|--------|-----------------|
| **SME check timing** | Before Grant Agreement |
| **Recent acquisition** | Status at application date counts |
| **Approaching thresholds** | Apply before crossing limits |

---

🎯 **Next Steps - What You Should Do:**
• If you ARE an SME: You should prepare your SME declaration and supporting documents
• If you are NOT an SME: You should explore EIC Pathfinder or RIA/IA alternatives instead
• Verify your exact SME status using [EC SME Assessment Tool](https://ec.europa.eu/growth/smes/sme-definition_en)
• Calculate linked enterprise effects precisely
• Consider timing if approaching thresholds

📋 **Action Items for SMEs:**
- [ ] Prepare SME self-declaration form
- [ ] Gather latest audited financial statements
- [ ] Document ownership structure and shareholdings
- [ ] Calculate linked/partner enterprise effects
- [ ] Review EIC Accelerator Work Programme for your innovation area

📋 **Action Items for Non-SMEs:**
- [ ] Search for RIA/IA calls in your topic area
- [ ] Consider EIC Pathfinder if at earlier TRL (1-4)
- [ ] Check national innovation programmes as alternatives
- [ ] Position your scale as an advantage for RIA/IA proposals"""

    def _generate_sme_opportunities_guidance(self) -> str:
        """Generate guidance about SME-specific funding opportunities."""
        return """As an SME, you have access to some of the most **specialized and high-impact funding** in the EU portfolio. Here's your comprehensive guide:

### 1. EIC Accelerator (Flagship SME Programme)

| Aspect | Details |
|--------|---------|
| **Funding** | Up to €2.5M grant + up to €15M equity |
| **Target** | High-risk, high-impact innovations (TRL 5-8) |
| **Format** | Single company application |
| **Success Rate** | ~8% (competitive) |

### 2. Eurostars (SME-Led R&D)

| Aspect | Details |
|--------|---------|
| **Funding** | Up to €500K-2M (varies by country) |
| **Target** | R&D-performing SMEs |
| **Format** | International consortium (2+ countries) |
| **Focus** | Market-oriented R&D |

### 3. Horizon Europe RIA/IA (Collaborative)

| Aspect | Details |
|--------|---------|
| **Funding Rate** | RIA: 100%, IA: 70% (can be 100% for SMEs in some calls) |
| **Target** | Collaborative research consortia |
| **SME Bonus** | Some calls have SME participation targets |
| **Advantage** | Access larger projects and networks |

### 4. EIC Pathfinder

| Aspect | Details |
|--------|---------|
| **Funding** | Up to €3-4M per project |
| **Target** | Breakthrough technology research (TRL 1-4) |
| **Format** | Consortia (SMEs can participate) |
| **Path** | Can lead to EIC Transition → Accelerator |

### 5. EIC Transition

| Aspect | Details |
|--------|---------|
| **Funding** | Up to €2.5M |
| **Target** | Maturing results from EIC Pathfinder/ERC |
| **Format** | Single entity or small consortium |
| **SME Focus** | SME-led projects preferred |

### SME Advantages in Horizon Europe

✅ **Higher funding rates** in some Innovation Actions
✅ **SME participation targets** in many calls (often 20-30%)
✅ **Simplified procedures** for smaller grants
✅ **Dedicated support** from NCPs and Enterprise Europe Network

### Programme Selection Guide

| Your Situation | Best Fit |
|----------------|----------|
| **Breakthrough innovation, TRL 5-8** | EIC Accelerator |
| **Early R&D with international partner** | Eurostars |
| **Part of a research consortium** | RIA/IA with SME role |
| **Fundamental research (TRL 1-4)** | EIC Pathfinder |
| **Validating prior EU research** | EIC Transition |

---

🎯 **Next Steps - What You Should Do:**
• Visit the [EIC website](https://eic.ec.europa.eu/) for Accelerator cut-off dates
• Check [Eurostars calls](https://www.eurekanetwork.org/programmes/eurostars) through your national agency
• Search [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) for RIA/IA calls
• Contact your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for personalized guidance
• Join [Enterprise Europe Network](https://een.ec.europa.eu/) for partnership opportunities

📋 **Immediate Action Items:**
- [ ] Identify your innovation's current TRL (Technology Readiness Level)
- [ ] Check upcoming EIC Accelerator cut-off dates
- [ ] Search for RIA/IA calls in your specific topic area
- [ ] Prepare a 1-page pitch of your innovation for initial NCP discussion
- [ ] Review your SME status documentation (employees, turnover, ownership)

💡 **Tip**: Many SMEs successfully combine programmes - e.g., participate in RIA to build track record, then apply to EIC Accelerator for commercialization funding!"""

    # =========================================================================
    # Consortium Eligibility Detection and Guidance (Scenario 031)
    # =========================================================================

    def _generate_double_funding_guidance(self) -> str:
        """Generate guidance about double funding rules for the same project."""
        return """## Double Funding Rules: Same Project in Multiple EU Programmes

**Short answer:** No, the same project activities and costs **cannot** be funded by both Horizon Europe and Erasmus+ (or any other EU programme). This is called the **non-cumulative funding principle**.

### The Core Rule

EU funding follows a strict principle: **the same costs can only be declared once** to EU funding sources. This means:

| Scenario | Allowed? | Explanation |
|----------|----------|-------------|
| Same activities funded twice | ❌ No | This is "double funding" - explicitly prohibited |
| Same costs declared to two programmes | ❌ No | Costs must be unique to each grant |
| Different activities, same initiative | ✅ Yes | If clearly separated (see below) |
| Simultaneous applications | ✅ Yes | You can apply to both, but can only accept funding for distinct work |

### What Is Explicitly Prohibited

According to the **EU Financial Regulation** (Article 191), beneficiaries must:

1. **Not declare the same costs** to different EU funding sources
2. **Inform the granting authority** if they receive/apply for other EU funding
3. **Prevent any overlap** of activities and costs between grants

### What You CAN Do: Complementary Funding

You CAN structure your initiative so that:
- **Research & Innovation** activities are funded by Horizon Europe
- **Training & Mobility** activities are funded by Erasmus+
- **Cultural dissemination** activities are funded by Creative Europe

The key is **clear delineation** - activities must be genuinely separate with distinct objectives, work packages, and budgets.

---

🎯 **Next Steps - What You Should Do:**

1. **Clearly separate your initiative** into distinct components:
   - Define which activities belong to each programme
   - Ensure no cost overlap between components
   - Create separate work packages for each funding source

2. **Document the separation** thoroughly:
   - Keep distinct timesheets and financial records
   - Maintain separate project deliverables
   - Prepare to demonstrate non-overlap if audited

3. **Inform both granting authorities** about your complementary applications

4. **Consult the programme guides**:
   - [Horizon Europe Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf)
   - [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide)

5. **Contact your National Contact Points** for official advice:
   - [Horizon Europe NCPs](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)
   - [Erasmus+ National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)

💡 **Tip:** Ask me about "complementary funding strategies" for detailed guidance on how to properly separate activities across programmes."""

    def _generate_complementary_funding_guidance(self) -> str:
        """Generate guidance about complementary funding approaches."""
        return """## Complementary Funding: Different Components, Different Programmes

**Yes, you can!** Having different components of the same large-scale initiative funded by different EU programmes is a legitimate and common strategic approach - provided the principle of **non-cumulative funding** is strictly followed.

### The Principle of Clear Delineation

To combine funding from Horizon Europe and Erasmus+ (or other programmes), you must ensure:

| Requirement | Description | Example |
|-------------|-------------|---------|
| **Separate Activities** | Each programme funds distinct work | HE: Lab research / E+: Student exchanges |
| **Separate Costs** | No cost declared twice | Different personnel, travel, equipment |
| **Separate Deliverables** | Distinct outputs for each | HE: Publications / E+: Training modules |
| **Separate Reporting** | Independent project management | Two separate projects, two sets of reports |

### How to Structure Complementary Funding

**Example: AI Research Initiative**

| Component | Programme | Activities | Budget |
|-----------|-----------|------------|--------|
| **Research** | Horizon Europe (RIA) | Algorithm development, testing, validation | €3M |
| **Training** | Erasmus+ (KA2) | Staff training, student mobility, curriculum | €400K |
| **Dissemination** | Creative Europe | Public exhibitions, documentary, media | €200K |

### Key Success Factors

1. **Design as Separate Projects**: Each must have its own:
   - Project acronym and title
   - Work plan and deliverables
   - Budget and cost categories
   - Consortium (can overlap but with different roles)

2. **Avoid These Common Mistakes**:
   - ❌ Same person's salary split between programmes (complex, requires timesheets)
   - ❌ Same equipment purchased under both grants
   - ❌ Same travel funded twice
   - ❌ Same event costs declared to both

3. **Document Everything**:
   - Clear rationale for programme selection
   - Distinct objectives per component
   - Non-overlap statement ready for auditors

### Cross-Programme Synergies You CAN Leverage

| Horizon Europe | Erasmus+ | Creative Europe |
|----------------|----------|-----------------|
| Research results | Training on results | Cultural dissemination |
| New methodologies | Curriculum integration | Media outreach |
| Technology demos | Staff upskilling | Public engagement |
| Publications | Student internships | Documentary/exhibitions |

---

🎯 **Next Steps - What You Should Do:**

1. **Map your initiative** into distinct components:
   - [ ] List all planned activities
   - [ ] Assign each activity to ONE programme only
   - [ ] Verify no cost overlap between components

2. **Create separate project plans** for each programme:
   - [ ] Develop distinct work packages
   - [ ] Define unique deliverables and milestones
   - [ ] Prepare separate budgets

3. **Prepare your "Complementarity Statement"**:
   - [ ] Document how projects relate but don't overlap
   - [ ] Explain synergies without cost duplication
   - [ ] Keep this ready for grant agreements

4. **Check eligibility for each programme**:
   - [ ] Verify your organization type is eligible
   - [ ] Confirm consortium requirements are met
   - [ ] Review call-specific conditions

5. **Consider timing strategically**:
   - [ ] Align application deadlines where possible
   - [ ] Plan for sequential or parallel implementation
   - [ ] Account for evaluation timelines

📚 **Useful Resources:**
- [Horizon Europe Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf)
- [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide)
- [Creative Europe Work Programme](https://ec.europa.eu/culture/creative-europe/)

💡 **Tip:** Ask me about specific call requirements for your topic to help you design the optimal multi-programme approach."""

    def _generate_double_funding_rules_guidance(self) -> str:
        """Generate detailed guidance about EU double funding rules."""
        return """## EU Double Funding Rules: What Is Explicitly Prohibited

Yes, there are specific and strict rules against double funding in EU programmes. These are governed by the **EU Financial Regulation** and reinforced in each programme's rules.

### The Legal Framework

**Article 191 of the EU Financial Regulation** states that:
> "Union grants shall not have the purpose or effect of producing a profit... The same costs shall not be financed twice by the Union budget."

### What Is Specifically Prohibited

| Prohibition | Description | Consequence |
|-------------|-------------|-------------|
| **Same costs, different EU grants** | Declaring €10K personnel costs to both Horizon Europe and Erasmus+ | Grant reduction, possible termination |
| **Same activity, same costs** | Funding the same workshop from two EU sources | Must repay one grant |
| **Cumulative EU funding > 100%** | Getting 100% from Horizon + 80% from Erasmus for same item | Excess must be returned |
| **Hiding other EU applications** | Not disclosing parallel applications | Breach of grant agreement |

### The Non-Cumulative Principle in Practice

When you sign an EU grant agreement, you commit to:

1. **Disclosure**: Inform the granting authority of ALL other EU funding applications/awards
2. **Non-overlap**: Ensure no cost is charged to more than one EU funding source
3. **Audit trail**: Maintain records proving costs are unique to each grant
4. **Timesheets**: Track personnel time separately for each funded activity

### What Auditors Check

EU auditors specifically look for:

| Check | What They Examine | Red Flags |
|-------|-------------------|-----------|
| **Personnel costs** | Timesheets, contracts, payslips | Same hours claimed on multiple grants |
| **Travel** | Tickets, receipts, travel reports | Same trip charged twice |
| **Equipment** | Invoices, depreciation records | Same purchase in multiple budgets |
| **Subcontracting** | Contracts, deliverables | Same work ordered twice |

### Penalties for Double Funding

If double funding is discovered:

1. **Recovery**: Full repayment of duplicated amounts
2. **Grant reduction**: Proportional reduction of remaining grant
3. **Termination**: Possible termination of one or both grants
4. **Exclusion**: Potential ban from future EU funding (serious cases)
5. **Legal action**: Fraud cases may be referred to OLAF

### How to Stay Compliant

**Best Practices:**

1. **Centralized tracking**: Maintain a single system tracking all EU-funded activities
2. **Clear cost assignment**: Each cost assigned to ONE grant only from the start
3. **Separate timesheets**: Different time tracking for each project
4. **Regular internal audits**: Check for accidental overlaps quarterly
5. **Documentation**: Keep clear records of how costs are allocated

---

🎯 **Next Steps - What You Should Do:**

1. **Review your current/planned EU grants**:
   - [ ] List all EU funding you've received or applied for
   - [ ] Map activities and costs for each
   - [ ] Identify any potential overlaps

2. **Implement tracking systems**:
   - [ ] Set up separate cost centers for each EU project
   - [ ] Implement project-specific timesheets
   - [ ] Create clear documentation procedures

3. **Disclose all applications**:
   - [ ] When applying, list all other EU applications in the proposal
   - [ ] Inform existing grant managers of new applications
   - [ ] Update grant agreements if circumstances change

4. **Consult official guidance**:
   - [EU Financial Regulation](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32018R1046)
   - [Annotated Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf)

5. **When in doubt, ask**:
   - Contact your Project Officer for clarification
   - Reach out to your National Contact Point
   - Consider legal advice for complex situations

💡 **Key Principle:** If you're unsure whether something constitutes double funding, assume it does and structure your activities to avoid any overlap. Prevention is always better than correction after the fact."""

    def _generate_simultaneous_applications_guidance(self) -> str:
        """Generate guidance about simultaneous applications to multiple programmes."""
        return """## Simultaneous Applications to Multiple EU Programmes

**Yes, you absolutely can** apply to both Horizon Europe and Erasmus+ (or other EU programmes) at the same time for related but distinct projects. There is **no rule prohibiting simultaneous submission** of multiple applications.

### What's Allowed

| Scenario | Status | Notes |
|----------|--------|-------|
| Same organization, different proposals | ✅ Allowed | Common practice for active research organizations |
| Same consortium, different proposals | ✅ Allowed | Consortium can apply to multiple programmes |
| Same topic area, different programmes | ✅ Allowed | E.g., AI research (HE) + AI training (E+) |
| Same deadline period | ✅ Allowed | No timing restrictions between programmes |
| Related initiatives | ✅ Allowed | If activities are distinct |

### Key Requirements for Simultaneous Applications

1. **Distinct Projects**: Each application must be for a genuinely different project
2. **No Activity Overlap**: Activities in each proposal must be unique
3. **No Cost Overlap**: Budgets cannot include the same costs
4. **Full Disclosure**: Mention other applications in your proposals

### How to Manage Multiple Applications

**Strategic Approach:**

| Programme | Focus | Typical Funding | Duration |
|-----------|-------|-----------------|----------|
| **Horizon Europe** | Research & Innovation | €1-20M | 3-5 years |
| **Erasmus+** | Education & Training | €100K-4M | 1-3 years |
| **Creative Europe** | Culture & Media | €50K-2M | 2-4 years |
| **Digital Europe** | Digital Deployment | €500K-5M | 2-3 years |

### What to Disclose in Applications

When submitting to Horizon Europe, you must declare:
- Previous EU funding received
- Pending EU applications
- How this proposal differs from others

**Example disclosure text:**
> "Our organization has submitted a complementary application to Erasmus+ (KA220) for a staff training programme related to the methodologies developed in this RIA. The Erasmus+ project focuses exclusively on training and mobility activities, with no overlap in costs or research activities with this proposal."

### Managing Award Scenarios

| If... | Then... |
|-------|---------|
| Both awarded | Accept both if activities are distinct |
| Only one awarded | Proceed with successful application |
| Overlap discovered | Modify scope of one or decline |
| Timeline conflicts | Adjust start dates if possible |

### Best Practices for Parallel Applications

1. **Plan from the start**: Design complementary proposals intentionally
2. **Different teams**: If possible, assign different proposal writers
3. **Clear boundaries**: Define scope boundaries before writing
4. **Separate budgets**: Never copy-paste budget items
5. **Track versions**: Keep clear records of what's in each proposal

---

🎯 **Next Steps - What You Should Do:**

1. **Map your initiative across programmes**:
   - [ ] Identify which activities fit each programme
   - [ ] Assign distinct objectives to each proposal
   - [ ] Create non-overlapping work packages

2. **Prepare coordinated proposals**:
   - [ ] Develop separate but complementary proposals
   - [ ] Ensure budgets have zero overlap
   - [ ] Write distinct descriptions for each

3. **Plan the disclosure sections**:
   - [ ] Prepare text explaining the relationship between proposals
   - [ ] Document why activities are distinct
   - [ ] Be ready to explain complementarity to evaluators

4. **Consider timing strategically**:
   - [ ] Check deadlines for all target programmes
   - [ ] Allow sufficient time for parallel preparation
   - [ ] Plan resource allocation for proposal writing

5. **Prepare for multiple successes**:
   - [ ] Consider how you'll manage multiple projects
   - [ ] Plan staffing for parallel implementation
   - [ ] Develop internal coordination mechanisms

📚 **Find Deadlines:**
- [Horizon Europe Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)
- [Erasmus+ Call Calendar](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2)
- [Creative Europe Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/crea)

💡 **Tip:** Ask me about specific programme deadlines in your research area to help plan your application timeline."""

    def _generate_cross_programme_strategy_guidance(self) -> str:
        """Generate strategic guidance for multi-programme funding approach."""
        return """## Strategic Approach to Multi-Programme EU Funding

This is an excellent strategy - maximizing your funding scope by targeting multiple EU programmes for different aspects of your work. Here's how to optimize your approach.

### 1. Strategic Programme Selection

Choose programmes based on **activity type**, not funding amount:

| Your Activity Type | Best Programme | Typical Funding | Success Rate |
|-------------------|----------------|-----------------|--------------|
| **Basic Research** | Horizon Europe (ERC) | €1.5-10M | 10-15% |
| **Applied Research** | Horizon Europe (RIA) | €3-10M | 15-20% |
| **Innovation/Market** | Horizon Europe (IA/EIC) | €0.5-17.5M | 5-25% |
| **Staff Training** | Erasmus+ (KA1/KA2) | €100K-1M | 30-40% |
| **Curriculum Development** | Erasmus+ (KA2) | €200K-400K | 25-35% |
| **Cultural Projects** | Creative Europe | €50K-2M | 15-25% |
| **Digital Deployment** | Digital Europe | €500K-5M | 20-30% |

### 2. Design Complementary Proposals

Structure your initiative into clearly distinct components:

**Example: Sustainable Agriculture Initiative**

```
┌─────────────────────────────────────────────────────────────────┐
│                    OVERALL INITIATIVE                           │
├─────────────────────┬─────────────────────┬────────────────────┤
│  Horizon Europe RIA │    Erasmus+ KA2     │  Creative Europe   │
├─────────────────────┼─────────────────────┼────────────────────┤
│ • Precision farming │ • Farmer training   │ • Documentary      │
│   algorithms        │ • Student mobility  │ • Exhibition       │
│ • Sensor technology │ • Curriculum dev    │ • Public awareness │
│ • Field trials      │ • Best practices    │ • Cultural events  │
├─────────────────────┼─────────────────────┼────────────────────┤
│ Budget: €4M         │ Budget: €400K       │ Budget: €200K      │
│ Duration: 4 years   │ Duration: 2 years   │ Duration: 2 years  │
└─────────────────────┴─────────────────────┴────────────────────┘
```

### 3. Key Success Factors

| Factor | Strategy | Why It Matters |
|--------|----------|----------------|
| **Clear boundaries** | Define scope limits BEFORE writing | Prevents overlap accusations |
| **Timing** | Stagger starts if possible | Easier resource management |
| **Consortium** | Different leads for each | Spreads responsibility |
| **Synergies** | Plan cross-project leverage | Maximizes impact |
| **Communication** | Regular coordination meetings | Prevents duplication |

### 4. Application Timeline Strategy

**Option A: Sequential**
- Submit Horizon Europe first (longer evaluation)
- Then Erasmus+ (faster evaluation)
- Adjust Erasmus+ if HE fails

**Option B: Parallel**
- Submit both simultaneously
- Be prepared to decline one if needed
- Requires robust separation

**Option C: Cascading**
- Start with easier programme (higher success rate)
- Use success to strengthen next application
- Build track record progressively

### 5. Consortium Strategy

| Approach | Pros | Cons |
|----------|------|------|
| **Same consortium** | Coherent initiative | Resource strain |
| **Overlapping consortium** | Balanced approach | Coordination needed |
| **Different consortia** | Maximum expertise | Less synergy |

### 6. Avoiding Common Mistakes

❌ **Don't:**
- Copy-paste between proposals
- Use same personnel costs
- Share equipment budgets
- Assume evaluators don't communicate

✅ **Do:**
- Write fresh descriptions
- Clearly allocate personnel time
- Plan separate equipment purchases
- Document distinctions thoroughly

### 7. Post-Award Coordination

If multiple proposals succeed:

1. **Kick-off coordination**: Align project teams on boundaries
2. **Shared governance**: Consider a coordination committee
3. **Joint dissemination**: Plan complementary communication
4. **Financial separation**: Strict cost allocation from day one
5. **Audit preparation**: Document everything from the start

---

🎯 **Next Steps - What You Should Do:**

1. **Audit your activities**:
   - [ ] List ALL planned activities for your initiative
   - [ ] Categorize by type (research, training, dissemination, etc.)
   - [ ] Map each category to the most appropriate programme

2. **Design your portfolio**:
   - [ ] Create distinct project concepts for each programme
   - [ ] Define clear boundaries between projects
   - [ ] Identify synergies you can leverage legally

3. **Build your timeline**:
   - [ ] Research deadlines for all target programmes
   - [ ] Plan proposal writing schedule
   - [ ] Allocate team resources across applications

4. **Strengthen your consortium**:
   - [ ] Identify the best coordinator for each programme
   - [ ] Ensure expertise matches programme requirements
   - [ ] Plan role distribution to avoid bottlenecks

5. **Prepare for success**:
   - [ ] Consider how you'll manage multiple grants
   - [ ] Plan staffing for parallel implementation
   - [ ] Set up coordination mechanisms in advance

📚 **Programme Resources:**
- [Horizon Europe Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide)
- [Creative Europe Work Programme](https://ec.europa.eu/culture/creative-europe/)
- [Digital Europe Programme](https://digital-strategy.ec.europa.eu/en/activities/digital-programme)

📞 **Get Expert Advice:**
- [Horizon Europe NCPs](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)
- [Erasmus+ National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [Creative Europe Desks](https://ec.europa.eu/culture/creative-europe/creative-europe-desks)

💡 **Pro Tip:** Consider starting with a smaller programme (Erasmus+ KA2 or Creative Europe small-scale) to build track record before tackling larger Horizon Europe projects. Success breeds success in EU funding!"""

    def _generate_erasmus_funding_overview_guidance(self) -> str:
        """Generate guidance on Erasmus+ funding model overview."""
        return """Erasmus+ uses a **unit cost funding model** for mobility activities, which means
grants are calculated based on fixed amounts per participant, per day/month, and per travel
distance - rather than reimbursing actual costs.

## Erasmus+ Mobility Budget Components

Erasmus+ KA1 mobility grants consist of **four main budget categories**:

| Budget Category | Description | Calculation Method |
|----------------|-------------|-------------------|
| **Travel Support** | Journey to/from destination | Fixed amount based on distance bands (km) |
| **Individual Support** | Living costs abroad | Fixed amount per day/month based on destination country |
| **Organisational Support** | Admin costs per participant | €100-500 per participant (depending on sector) |
| **Inclusion Support** | Additional support for disadvantaged participants | Top-ups or real costs |

### 1. Travel Support

Travel grants are based on distance from origin to destination:

| Distance Band | Standard Travel | Green Travel Top-up |
|--------------|-----------------|---------------------|
| 10-99 km | €23 | Not applicable |
| 100-499 km | €180 | €210 |
| 500-1999 km | €275 | €320 |
| 2000-2999 km | €360 | €410 |
| 3000-3999 km | €530 | €610 |
| 4000-7999 km | €820 | N/A |
| 8000+ km | €1500 | N/A |

**Green Travel Bonus**: Participants using sustainable transport (train, bus, car-sharing)
can receive higher travel support.

### 2. Individual Support (Living Costs)

Individual support rates vary by:
- **Destination country group** (Group 1-3 based on cost of living)
- **Duration** (short-term vs long-term)
- **Participant type** (student, staff, learner)

Typical rates:
- **Students (long-term)**: €420-600/month (depending on country group)
- **Staff**: €140-180/day
- **VET Learners**: €70-120/day

### 3. Organisational Support

Fixed contribution per participant to cover:
- Preparation and follow-up activities
- Administrative costs
- Language preparation
- Monitoring and support

Rates: **€100-500 per participant** (sector-specific)

### 4. Inclusion Support

Additional support for participants with:
- Disabilities or health conditions (real costs covered)
- Fewer opportunities (social, economic, geographic barriers)
- Green travel top-up for sustainable transport

---

🎯 **Next Steps - What You Should Do:**

1. **Calculate Your Distances**: Use the [Distance Calculator](https://ec.europa.eu/programmes/erasmus-plus/resources/distance-calculator_en)
2. **Check Country Groups**: Identify destination country groups for your mobilities
3. **Estimate Participant Numbers**: Calculate total budget based on planned participants
4. **Consider Green Travel**: Plan sustainable transport options for bonus funding
5. **Identify Inclusion Needs**: Assess if participants qualify for additional support

📋 **Action Items:**
- [ ] Download the [Erasmus+ Programme Guide 2026](https://erasmus-plus.ec.europa.eu/programme-guide/introduction)
- [ ] Use the official [Budget Calculator](https://ec.europa.eu/programmes/erasmus-plus/resources_en)
- [ ] Check [National Agency guidance](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for sector rates
- [ ] Review [Inclusion and Diversity Strategy](https://erasmus-plus.ec.europa.eu/programme-guide/part-a/priorities-of-the-erasmus-programme/inclusion-and-diversity)

📚 **Useful Resources:**
- [Distance Calculator](https://ec.europa.eu/programmes/erasmus-plus/resources/distance-calculator_en)
- [Programme Guide - Funding Rules](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_individual_support_guidance(self) -> str:
        """Generate guidance on Erasmus+ individual support rates."""
        return """Erasmus+ provides **individual support** to cover living costs during mobility.
Rates vary by **destination country group** and **participant type**.

## Individual Support Rates in Erasmus+

### Country Groups (Based on Cost of Living)

| Group | Countries | Cost Level |
|-------|-----------|------------|
| **Group 1** (Highest) | Denmark, Finland, Iceland, Ireland, Liechtenstein, Luxembourg, Norway, Sweden | Highest costs |
| **Group 2** (Medium) | Austria, Belgium, Cyprus, France, Germany, Greece, Italy, Malta, Netherlands, Portugal, Spain | Medium costs |
| **Group 3** (Lower) | Bulgaria, Croatia, Czechia, Estonia, Hungary, Latvia, Lithuania, North Macedonia, Poland, Romania, Serbia, Slovakia, Slovenia, Türkiye | Lower costs |

### Student Mobility Rates (Higher Education)

| Duration | Group 1 | Group 2 | Group 3 |
|----------|---------|---------|---------|
| **Long-term (3-12 months)** | €600/month | €540/month | €420/month |
| **Short-term (5-30 days)** | €79/day (days 1-14), €56/day (days 15-30) | Same | Same |
| **Blended Mobility** | €79/day for physical component | Same | Same |

### VET Learner Rates

| Duration | Group 1 | Group 2 | Group 3 |
|----------|---------|---------|---------|
| **Short-term (10-89 days)** | €120/day (days 1-14), €84/day (days 15+) | €105/day, €74/day | €90/day, €63/day |
| **Long-term (90-365 days)** | €420/month | €360/month | €300/month |

### School Pupil Rates

| Type | Rate |
|------|------|
| **Group mobility (2-30 days)** | €70/day (days 1-14), €50/day (days 15+) |
| **Long-term (30-365 days)** | €420-600/month (by country group) |

### Staff Mobility Rates

| Staff Type | All Destinations |
|-----------|------------------|
| **Teaching/Training assignments** | €180/day (days 1-14), €126/day (days 15-60) |
| **Job shadowing** | €140/day (days 1-14), €98/day (days 15-60) |

### Top-ups for Students with Fewer Opportunities

| Category | Top-up Amount |
|----------|---------------|
| **Fewer opportunities (long-term)** | +€250/month |
| **Fewer opportunities (short-term)** | +€100-150 total (lump sum) |

---

🎯 **Next Steps - What You Should Do:**

1. **Identify Destination Countries**: Determine country groups for your planned mobilities
2. **Calculate Duration**: Short-term (<90 days) vs long-term rates differ significantly
3. **Identify Eligible Participants**: Check if students qualify for fewer opportunities top-up
4. **Document Support Levels**: National Agencies may have adjusted rates
5. **Plan Budget**: Multiply rates by participant numbers and durations

📋 **Action Items:**
- [ ] Identify the country group for each destination
- [ ] Calculate individual support for each mobility type
- [ ] Check if participants qualify for top-ups
- [ ] Consult your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for exact rates
- [ ] Include a buffer for rate adjustments

📚 **Useful Resources:**
- [Programme Guide - Individual Support Rates](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [Country Group Information](https://erasmus-plus.ec.europa.eu/programme-guide/annexes/annex-i)"""

    def _generate_erasmus_staff_mobility_guidance(self) -> str:
        """Generate guidance on Erasmus+ staff mobility funding."""
        return """Erasmus+ funds **staff mobility** for teaching, training, and professional development
activities across all sectors (Higher Education, VET, Schools, Adult Education).

## Staff Mobility Funding in Erasmus+

### Eligible Staff Mobility Activities

| Activity Type | Duration | Sectors |
|--------------|----------|---------|
| **Teaching assignments** | 2-60 days (min. 8 hours/week) | HED, VET, Schools, Adult Ed |
| **Training/Job shadowing** | 2-60 days | All sectors |
| **Staff development** | 2-60 days | All sectors |
| **Courses and training** | 2-30 days | Schools, Adult Ed, VET |

### Staff Mobility Funding Components

| Component | Rate | Calculation |
|-----------|------|-------------|
| **Travel Support** | €23-1500 | Based on distance bands |
| **Individual Support (days 1-14)** | €140-180/day | Based on activity type |
| **Individual Support (days 15-60)** | €98-126/day | 70% of daily rate |
| **Organisational Support** | €100-400 | Per participant (sector varies) |

### Individual Support Rates for Staff

| Activity Type | Days 1-14 | Days 15-60 |
|--------------|-----------|------------|
| **Teaching/Training activities** | €180/day | €126/day (70%) |
| **Job shadowing/observation** | €140/day | €98/day (70%) |

**Note**: These are maximum rates. National Agencies may apply different rates.

### Staff Mobility Eligible Costs

| Cost Category | Coverage | Notes |
|--------------|----------|-------|
| **Travel** | Standard distance bands | Green travel bonus available |
| **Accommodation** | Included in daily rate | No separate reimbursement |
| **Meals** | Included in daily rate | No separate reimbursement |
| **Local transport** | Included in daily rate | To/from airport covered separately |
| **Visa/insurance** | Exceptional costs | If required |
| **Linguistic preparation** | Up to €150 | If needed |

### VET Staff Mobility

VET staff can participate in:
- **Teaching/training assignments** at partner institutions
- **Job shadowing** to observe practices
- **Courses and training events** for skills development
- **Inviting experts** to train staff at home institution

### Higher Education Staff Mobility

Higher education staff can participate in:
- **Staff Mobility for Teaching** (STA) - minimum 8 hours teaching
- **Staff Mobility for Training** (STT) - professional development
- **Invited staff from enterprises** to teach

---

🎯 **Next Steps - What You Should Do:**

1. **Define Activity Type**: Teaching, training, or job shadowing determines rates
2. **Calculate Duration**: Optimal duration is 5-14 days for maximum daily rate
3. **Find Host Institutions**: Use partner networks or Erasmus+ platforms
4. **Plan Learning Outcomes**: Define what staff should learn/achieve
5. **Consider Cascading Effect**: Plan how staff will share knowledge upon return

📋 **Action Items:**
- [ ] Identify staff development needs and matching opportunities
- [ ] Check [accreditation status](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation) for your institution
- [ ] Calculate budget based on activity type and duration
- [ ] Register on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [ ] Contact partner institutions for hosting arrangements

📚 **Useful Resources:**
- [Staff Mobility Guide](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1)
- [School Exchange Partnerships](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/partnerships-for-cooperation/cooperation-partnerships)
- [Partner Search Tool](https://erasmus-plus.ec.europa.eu/partner-search)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_inclusion_support_guidance(self) -> str:
        """Generate guidance on Erasmus+ inclusion support."""
        return """Erasmus+ is committed to **inclusion and diversity**, providing additional support
for participants with **fewer opportunities** to ensure equal access to mobility.

## Inclusion Support in Erasmus+

### Who Qualifies for Inclusion Support?

Participants with **fewer opportunities** due to:

| Barrier Type | Examples | Evidence Required |
|-------------|----------|-------------------|
| **Disability** | Physical, sensory, mental health conditions | Medical certificate |
| **Health problems** | Chronic illness, serious health conditions | Medical documentation |
| **Educational difficulties** | Learning differences, early school leavers | Educational records |
| **Economic obstacles** | Low income, unemployment, debt | Income statements |
| **Social obstacles** | Discrimination, refugee status, single parent | Social services |
| **Geographic obstacles** | Remote, rural, or outermost regions | Address verification |
| **Cultural differences** | Migrants, minorities, language barriers | Various documentation |

### Inclusion Support Funding

| Support Type | Coverage | Maximum |
|-------------|----------|---------|
| **Top-up (students, long-term)** | Additional monthly support | +€250/month |
| **Top-up (students, short-term)** | Lump sum for short mobilities | +€100-150 |
| **Top-up (VET learners)** | Additional support | +€100-150 |
| **Real costs (disability)** | Actual costs for special needs | 100% of justified costs |
| **Accompanying person** | Travel + individual support | Same rates as participant |
| **Preparatory visit** | Pre-departure planning | Travel + 2 days support |

### Real Costs Coverage (Disability/Health)

100% coverage for:
- Adapted accommodation
- Specialized transport (wheelchair accessible)
- Medical support during mobility
- Personal assistance
- Special learning materials
- Sign language interpretation
- Adapted equipment or technology

### Green Travel Top-up

| Standard Travel | Green Travel Bonus |
|----------------|-------------------|
| €180 (100-499 km) | €210 (+€30) |
| €275 (500-1999 km) | €320 (+€45) |
| €360 (2000-2999 km) | €410 (+€50) |
| €530 (3000-3999 km) | €610 (+€80) |

**Green travel** = sustainable transport (train, bus, carpooling, ferry) for main journey.

### How to Apply for Inclusion Support

1. **Identify barriers** during application process
2. **Provide evidence** to sending institution
3. **Request specific support** in Mobility Agreement
4. **Get approval** from National Agency (for real costs)
5. **Document expenses** for reimbursement

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Participant Needs**: Identify who qualifies for fewer opportunities
2. **Gather Documentation**: Collect required evidence for each barrier type
3. **Plan Reasonable Accommodations**: Determine what support is needed
4. **Contact Host Institution**: Discuss accessibility and support arrangements
5. **Apply for Real Costs**: Submit request to National Agency if needed

📋 **Action Items:**
- [ ] Review the [Inclusion and Diversity Strategy](https://erasmus-plus.ec.europa.eu/programme-guide/part-a/priorities-of-the-erasmus-programme/inclusion-and-diversity)
- [ ] Identify participants with fewer opportunities in your target group
- [ ] Prepare documentation for inclusion support claims
- [ ] Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for guidance
- [ ] Budget for inclusion support in your grant application

📚 **Useful Resources:**
- [Inclusion and Diversity in Erasmus+](https://erasmus-plus.ec.europa.eu/programme-guide/part-a/priorities-of-the-erasmus-programme/inclusion-and-diversity)
- [National Agency Contacts](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [Erasmus+ for Organisations](https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-organisations)
- [European Agency for Special Needs](https://www.european-agency.org/)"""

    def _generate_erasmus_travel_costs_guidance(self) -> str:
        """Generate guidance on Erasmus+ travel costs and distance bands."""
        return """Erasmus+ provides **travel support** based on the distance between origin and destination,
using a **distance band system** with fixed amounts per band.

## Travel Costs in Erasmus+ Mobility

### How Travel Support is Calculated

1. **Measure distance** from origin city to destination city (straight-line km)
2. **Use EU Distance Calculator** for official calculation
3. **Apply standard rate** from distance band table
4. **Add green travel bonus** if using sustainable transport

### Distance Band Table (2024-2027)

| Distance | Standard Travel | Green Travel | Green Top-up |
|----------|----------------|--------------|--------------|
| **10-99 km** | €23 | €23 | N/A |
| **100-499 km** | €180 | €210 | +€30 |
| **500-1999 km** | €275 | €320 | +€45 |
| **2000-2999 km** | €360 | €410 | +€50 |
| **3000-3999 km** | €530 | €610 | +€80 |
| **4000-7999 km** | €820 | N/A | N/A |
| **8000+ km** | €1500 | N/A | N/A |

### What is Green Travel?

**Green travel** means using sustainable, low-carbon transport for the main journey:

| Green Transport | Eligible | Notes |
|-----------------|----------|-------|
| **Train** | ✅ Yes | Including overnight trains |
| **Bus/Coach** | ✅ Yes | Long-distance services |
| **Car sharing** | ✅ Yes | Minimum 2 participants sharing |
| **Ferry** | ✅ Yes | If main transport mode |
| **Bicycle** | ✅ Yes | For suitable distances |
| **Flying** | ❌ No | Not considered green |

**Green Travel Bonus**:
- Higher travel support amount
- Up to **4 extra days** of individual support for longer travel time
- Maximum €80 extra for extended travel

### Distance Calculation Rules

1. **Origin**: Location of sending organisation (or participant's home if closer)
2. **Destination**: Location of receiving organisation
3. **One-way distance**: Travel amount is for return journey (both ways)
4. **Calculator**: Use official EU Distance Calculator

### Exceptional Travel Costs

In addition to standard travel support, the following may be covered:

| Cost Type | Coverage | Conditions |
|-----------|----------|------------|
| **Expensive journey** | Up to 80% of real costs | When standard rate insufficient |
| **Visa fees** | Real costs | For mandatory visas |
| **Travel insurance** | Real costs | If not covered by institution |
| **Green travel days** | Up to 4 extra days | For extended sustainable travel |

### Travel for Accompanying Persons

Participants requiring support can have an **accompanying person**:
- Same travel support as participant
- Individual support for duration of stay
- Must be justified and pre-approved

---

🎯 **Next Steps - What You Should Do:**

1. **Calculate Distances**: Use the [EU Distance Calculator](https://ec.europa.eu/programmes/erasmus-plus/resources/distance-calculator_en)
2. **Plan Green Travel**: Consider train/bus for destinations within 1000km
3. **Check Visa Requirements**: Factor in visa costs for non-EU destinations
4. **Document Travel**: Keep all tickets and receipts
5. **Request Exceptional Costs**: If standard amount is insufficient

📋 **Action Items:**
- [ ] Use the [Distance Calculator](https://ec.europa.eu/programmes/erasmus-plus/resources/distance-calculator_en) for all mobilities
- [ ] Compare green travel options for destinations under 2000km
- [ ] Calculate travel days for green travel bonus
- [ ] Check if exceptional travel costs apply
- [ ] Budget for visa fees if applicable

📚 **Useful Resources:**
- [EU Distance Calculator](https://ec.europa.eu/programmes/erasmus-plus/resources/distance-calculator_en)
- [Programme Guide - Travel Support](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1)
- [Green Travel Guidelines](https://erasmus-plus.ec.europa.eu/programme-guide/part-a/priorities-of-the-erasmus-programme/environment-and-fight-against-climate-change)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_actions_overview_guidance(self) -> str:
        """Generate guidance on Erasmus+ Key Actions overview."""
        return """Erasmus+ (2021-2027) is the EU's flagship programme for education, training, youth, and sport, with a budget of **€26.2 billion**. It is structured around **three Key Actions** plus dedicated actions for Jean Monnet and Sport.

## Erasmus+ Key Actions Overview

| Key Action | Focus | Target Groups | Budget Share |
|-----------|-------|---------------|--------------|
| **KA1** | Learning Mobility | Students, staff, learners | ~63% |
| **KA2** | Cooperation & Partnerships | Institutions, organizations | ~28% |
| **KA3** | Policy Support | Policymakers, networks | ~4% |
| **Jean Monnet** | EU Studies | Universities, teachers | ~2% |
| **Sport** | Grassroots Sport | Clubs, federations | ~2% |

### Key Action 1 (KA1) - Learning Mobility

KA1 supports **individual mobility** for:
- **Higher Education**: Student exchanges, staff mobility, joint degrees
- **VET**: Learner and staff mobility, skills competitions
- **Schools**: Pupil and teacher exchanges
- **Adult Education**: Staff mobility, adult learner mobility
- **Youth**: Youth exchanges, volunteering (European Solidarity Corps)

**Funding Model**: Unit costs (travel + individual support per day)

### Key Action 2 (KA2) - Cooperation & Partnerships

KA2 supports **institutional cooperation** through:

| Partnership Type | Partners | Duration | Budget |
|-----------------|----------|----------|--------|
| **Cooperation Partnerships** | 3+ from 3+ countries | 12-36 months | €120K-400K |
| **Small-Scale Partnerships** | 2+ from 2+ countries | 6-24 months | €30K-60K |
| **Centres of Vocational Excellence** | 4+ from 4+ countries | 4 years | Up to €4M |
| **Teacher Academies** | 3+ from 3+ countries | 3 years | Up to €1.5M |
| **Erasmus Mundus Joint Masters** | 3+ from 3+ countries | 6 years | Up to €5M |

**Funding Model**: Lump sums based on project size and activity type

### Key Action 3 (KA3) - Policy Support

KA3 supports **policy development** through:
- European policy experimentation
- Civil society cooperation (framework partnerships)
- Support to EU policy tools and networks

### Jean Monnet Actions

Promotes excellence in EU studies:
- Modules, Chairs, Centres of Excellence
- Policy debates, networks, projects
- Support to academic associations

### Sport Actions

Promotes grassroots sport participation:
- Cooperation partnerships for sport
- Not-for-profit sport events
- Evidence-based policy development

---

🎯 **Next Steps - What You Should Do:**

1. **Identify Your Sector**: Determine which sector applies (HED, VET, Schools, Adult Ed, Youth)
2. **Choose Your Action Type**: Decide between mobility (KA1) or partnerships (KA2)
3. **Check Accreditation**: Consider KA1 accreditation for simplified long-term access
4. **Find Partners**: Use the [Partner Search Tool](https://erasmus-plus.ec.europa.eu/partner-search)
5. **Contact Your National Agency**: Get sector-specific guidance

📋 **Action Items:**
- [ ] Review the [Erasmus+ Programme Guide 2026](https://erasmus-plus.ec.europa.eu/programme-guide/introduction)
- [ ] Check [open calls](https://erasmus-plus.ec.europa.eu/programme-guide/part-b) for your sector
- [ ] Register on [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [ ] Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [ ] Consider [Accreditation](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation) for regular mobility

📚 **Useful Resources:**
- [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [Partner Search](https://erasmus-plus.ec.europa.eu/partner-search)
- [Project Results Platform](https://erasmus-plus.ec.europa.eu/projects)"""

    def _generate_vet_mobility_guidance(self) -> str:
        """Generate guidance on VET mobility options in Erasmus+."""
        return """Erasmus+ offers comprehensive **mobility opportunities for VET (Vocational Education and Training)** institutions, learners, and staff through **Key Action 1 (KA1)**.

## VET Mobility Options in Erasmus+ KA1

### Who Can Participate?

| Participant Type | Eligibility | Duration | Activities |
|-----------------|-------------|----------|------------|
| **VET Learners** | Enrolled in VET programmes | 2 weeks - 12 months | Work placements, learning abroad |
| **Recent Graduates** | Within 12 months of graduation | 2 weeks - 12 months | Work placements |
| **VET Staff** | Teachers, trainers, managers | 2 days - 2 months | Job shadowing, courses, teaching |
| **Apprentices** | In apprenticeship programmes | 2 weeks - 12 months | Work-based learning abroad |

### Mobility Formats

#### Short-Term Mobility (2 weeks - 3 months)
- Work placements in companies abroad
- Learning periods at VET schools/training centres
- Skills competitions (EuroSkills, WorldSkills preparation)
- Job shadowing for staff

#### Long-Term Mobility (3-12 months) - ErasmusPro
- Extended work placements with full ECVET recognition
- Suitable for advanced learners and apprentices
- Includes intensive language preparation
- Higher unit costs to reflect extended duration

### Funding (Unit Costs 2024-2025)

| Cost Category | Amount |
|--------------|--------|
| **Travel** | €180-1,500 (by distance band) |
| **Individual Support** | €30-140/day (by country) |
| **Organizational Support** | €350/participant (first 100), €200 (after) |
| **Inclusion Support** | Up to €100/day extra |
| **Linguistic Support** | €150-300 per participant |

### Access Routes for VET Schools

| Route | Description | Benefits |
|-------|-------------|----------|
| **KA1 Accreditation** | Multi-year accreditation | Simplified annual funding, long-term planning |
| **Short-Term Projects** | One-off mobility project | Flexible, good for first-timers |
| **Consortium** | Join an existing accredited consortium | Lower admin burden, shared expertise |

### Accreditation Pathway (Recommended)

VET schools can apply for **Erasmus+ Accreditation** to access mobility funding each year:
1. Apply once for 5-year accreditation
2. Submit annual mobility budget requests
3. Receive simplified funding with less reporting
4. Build long-term internationalization strategy

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Your Needs**: Identify how many learners/staff would benefit from mobility
2. **Consider Accreditation**: Apply for KA1 accreditation for ongoing access
3. **Find Hosting Partners**: Connect with VET schools/companies abroad
4. **Plan ECVET Recognition**: Ensure learning outcomes can be recognized
5. **Prepare Participants**: Organize language and cultural preparation

📋 **Action Items:**
- [ ] Check if accreditation call is open at your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [ ] Use [Partner Search](https://erasmus-plus.ec.europa.eu/partner-search) to find hosting organizations
- [ ] Review [ECVET guidelines](https://www.cedefop.europa.eu/en/projects/european-credit-system-vocational-education-and-training-ecvet) for recognition
- [ ] Contact your National Agency for VET-specific guidance
- [ ] Explore [successful VET projects](https://erasmus-plus.ec.europa.eu/projects) for inspiration

📚 **Useful Resources:**
- [Erasmus+ VET Guide](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/learning-mobility-opportunities-vet)
- [VET Mobility Charter (old)](https://erasmus-plus.ec.europa.eu/projects/prior-call-projects/vet-mobility-charter)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [Online Linguistic Support (OLS)](https://erasmus-plus.ec.europa.eu/resources-and-tools/online-linguistic-support)"""

    def _generate_vet_partnership_guidance(self) -> str:
        """Generate guidance on VET partnership options in Erasmus+."""
        return """Erasmus+ **Key Action 2 (KA2)** offers excellent partnership opportunities for VET (Vocational Education and Training) institutions to collaborate on innovation, curriculum development, and best practice exchange.

## VET Partnership Options in Erasmus+ KA2

### Partnership Types for VET

| Partnership Type | Min Partners | Duration | Budget | Focus |
|-----------------|-------------|----------|--------|-------|
| **Cooperation Partnerships** | 3 orgs from 3 countries | 12-36 months | €120K-400K (lump sum) | Innovation, curriculum, quality |
| **Small-Scale Partnerships** | 2 orgs from 2 countries | 6-24 months | €30K or €60K | Newcomers, grassroots |
| **Centres of Vocational Excellence (CoVE)** | 4+ from 4+ countries | 4 years | Up to €4M | Excellence ecosystems |

### Cooperation Partnerships for VET

**Eligible Activities:**
- Joint curriculum development
- Innovative teaching methods
- Work-based learning integration
- Digital tools and resources
- Quality assurance frameworks
- Staff professional development
- Green skills development
- Entrepreneurship education

**Funding Model (Lump Sums):**

| Project Size | Lump Sum | Typical Scope |
|-------------|----------|---------------|
| Small | €120,000 | 3-4 partners, limited outputs |
| Medium | €250,000 | 5-6 partners, moderate outputs |
| Large | €400,000 | 7+ partners, comprehensive outputs |

### Small-Scale Partnerships

**Ideal for VET schools that:**
- Are new to EU funding
- Have limited administrative capacity
- Want to test international cooperation
- Focus on specific, targeted improvements

**Features:**
- Simplified application (shorter form)
- Fixed €30K or €60K grant (no budget breakdown)
- Flexible partnership structure
- Lower reporting requirements

### Centres of Vocational Excellence (CoVE)

**For ambitious VET institutions to:**
- Create regional skills ecosystems
- Connect VET with labour market
- Drive innovation in specific sectors
- Establish international networks of excellence

**Requirements:**
- Strong regional anchoring
- Industry partnerships
- Multiple countries and sectors

---

🎯 **Next Steps - What You Should Do:**

1. **Identify Your Partnership Goal**: Curriculum? Quality? Innovation? Digitalization?
2. **Find Partners**: Use Partner Search and your National Agency network
3. **Choose Partnership Size**: Start small if new to EU funding
4. **Plan Outputs**: Define what tangible results you'll produce
5. **Contact Your National Agency**: Get feedback before submitting

📋 **Action Items:**
- [ ] Review the [KA2 section](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2) of the Programme Guide
- [ ] Use [Partner Search](https://erasmus-plus.ec.europa.eu/partner-search) to find collaborators
- [ ] Check [call deadlines](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/cooperation-partnerships) for partnerships
- [ ] Study [successful VET partnerships](https://erasmus-plus.ec.europa.eu/projects) for ideas
- [ ] Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for guidance

📚 **Useful Resources:**
- [Erasmus+ Programme Guide - KA2](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2)
- [Cooperation Partnerships](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/cooperation-partnerships)
- [Small-Scale Partnerships](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/small-scale-partnerships)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_ka2_curriculum_guidance(self) -> str:
        """Generate guidance on curriculum development in Erasmus+ KA2."""
        return """Yes, **curriculum development is a core activity** funded under Erasmus+ KA2 Cooperation Partnerships. These partnerships are specifically designed to support innovation in education, including the creation of new curricula, training materials, and educational resources.

## Curriculum Activities in KA2 Cooperation Partnerships

### Eligible Curriculum-Related Activities

| Activity Type | Examples | Output Types |
|--------------|----------|--------------|
| **Curriculum Design** | New courses, modules, qualifications | Curriculum frameworks, syllabi |
| **Learning Materials** | Textbooks, e-learning, simulations | OER (Open Educational Resources) |
| **Teaching Methods** | Innovative pedagogy, work-based learning | Methodological guides, toolkits |
| **Assessment Tools** | Competence frameworks, digital badges | Rubrics, assessment instruments |
| **Quality Standards** | Sectoral qualifications, benchmarks | Quality frameworks |

### Types of Outputs You Can Create

**Tangible Outputs (Required):**
- Joint curricula for VET programmes
- Training modules (including digital/blended)
- Teacher training materials
- Competence frameworks
- Assessment and recognition tools
- Policy recommendations
- Implementation guidelines

**Multiplier Events:**
- Dissemination conferences
- Training workshops
- Piloting sessions with target groups

### Budget for Curriculum Development

| Cost Category | Funding |
|--------------|---------|
| **Project Management** | Included in lump sum |
| **Material Development** | Included in lump sum |
| **Piloting Activities** | Included in lump sum |
| **Multiplier Events** | €100/local, €200/international participant |
| **Exceptional Costs** | Up to 80% for subcontracting |

### Quality Criteria for Curriculum Projects

Evaluators look for:
1. **Relevance** to VET sector needs
2. **Innovation** compared to existing curricula
3. **Transferability** to other contexts
4. **Sustainability** after project ends
5. **Impact** on target groups

### Examples of Successful Curriculum Projects

| Project Type | Partners | Activities | Budget |
|-------------|----------|------------|--------|
| Green Skills Curriculum | 5 VET schools + 2 companies | Joint modules, teacher training | €350K |
| Digital Manufacturing | 4 VET + 3 industry | Simulation tools, competence framework | €400K |
| Entrepreneurship Education | 6 schools from 4 countries | Startup curriculum, mentoring guide | €250K |

---

🎯 **Next Steps - What You Should Do:**

1. **Define Curriculum Gap**: What specific skills/knowledge are missing?
2. **Map Target Group**: Which learners will benefit?
3. **Find Expert Partners**: Include industry, other VET schools, researchers
4. **Plan Pilot Testing**: How will you validate the curriculum?
5. **Ensure Sustainability**: How will the curriculum continue after the project?

📋 **Action Items:**
- [ ] Review [KA2 priorities](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2) relevant to VET
- [ ] Check the [2026 Erasmus+ Work Programme](https://erasmus-plus.ec.europa.eu/) for thematic priorities
- [ ] Find partners with complementary expertise via [Partner Search](https://erasmus-plus.ec.europa.eu/partner-search)
- [ ] Study [successful projects](https://erasmus-plus.ec.europa.eu/projects) in your VET sector
- [ ] Plan intellectual outputs and multiplier events

📚 **Useful Resources:**
- [KA2 Cooperation Partnerships](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/cooperation-partnerships)
- [Erasmus+ Project Results Platform](https://erasmus-plus.ec.europa.eu/projects)
- [CEDEFOP VET Resources](https://www.cedefop.europa.eu/)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_combination_strategy_guidance(self) -> str:
        """Generate guidance on combining KA1 and KA2 for VET schools."""
        return """Combining **KA1 mobility with KA2 partnerships** is an excellent strategy for VET schools to maximize the benefits of Erasmus+. Here's how to strategically combine these actions for maximum impact.

## Strategic Approach: KA1 + KA2 Combination for VET

### Why Combine KA1 and KA2?

| Benefit | KA1 Contribution | KA2 Contribution |
|---------|-----------------|------------------|
| **Internationalization** | Individual experiences | Institutional partnerships |
| **Quality Improvement** | Learning from abroad | Joint innovation projects |
| **Staff Development** | Job shadowing, courses | Collaborative development |
| **Curriculum Enhancement** | Exposure to best practices | Joint curriculum creation |
| **Sustainability** | Ongoing mobility flows | Tangible outputs, networks |

### Recommended Strategy: Building Block Approach

#### Phase 1: Start with KA1 Accreditation (Year 1-2)

**Why start here:**
- Lower complexity, faster approval
- Build international contacts
- Develop organizational capacity
- Identify potential KA2 partners

**Actions:**
1. Apply for KA1 Accreditation
2. Send staff for job shadowing
3. Start learner mobility
4. Document partnership contacts

#### Phase 2: Add KA2 Small-Scale Partnership (Year 2-3)

**Why add this:**
- Formalize successful partnerships
- Create joint outputs
- Test collaboration capacity
- Low risk (€30-60K)

**Actions:**
1. Partner with 1-2 trusted KA1 contacts
2. Focus on one clear output
3. Build project management skills
4. Prepare for larger projects

#### Phase 3: Launch KA2 Cooperation Partnership (Year 3-5)

**Why scale up:**
- Leverage established partnerships
- Create substantial outputs
- Greater impact and visibility
- Access larger budgets (€120-400K)

**Actions:**
1. Expand consortium (3+ countries)
2. Develop comprehensive curriculum/tools
3. Include industry partners
4. Plan sustainable dissemination

### Synergies Between Actions

| KA1 Activity | How It Feeds KA2 | KA2 Output | How It Supports KA1 |
|-------------|------------------|------------|---------------------|
| Staff job shadowing | Identifies best practices | Joint curriculum | Better preparation |
| Learner mobility | Tests partnership quality | Assessment tools | Improved recognition |
| Teaching assignments | Builds trust | Training materials | Enhanced pedagogy |
| Courses abroad | Spots innovation | Methodological guides | Staff competence |

### Budget Considerations

| Year | KA1 Budget | KA2 Budget | Total | Focus |
|------|-----------|-----------|-------|-------|
| 1 | €30K | - | €30K | Build base, get accredited |
| 2 | €50K | €30K (SSP) | €80K | Formalize partnerships |
| 3 | €70K | €120K (CP) | €190K | Scale innovation |
| 4 | €80K | €250K (CP) | €330K | Major curriculum project |
| 5 | €90K | - | €90K | Sustain and mainstream |

### Key Success Factors

1. **Start Small, Think Big**: Don't rush - build capacity gradually
2. **Choose Partners Carefully**: KA2 success depends on strong partnerships
3. **Align Objectives**: Ensure KA1 and KA2 activities reinforce each other
4. **Document Everything**: Use KA1 experiences in KA2 applications
5. **Involve Staff**: Get buy-in from teachers for both mobility and projects

### Common Mistakes to Avoid

| Mistake | Why It's Problematic | Solution |
|---------|---------------------|----------|
| Starting with KA2 | No established partnerships | Begin with KA1 for contacts |
| Too many partners | Coordination complexity | Start with 3-4, expand later |
| Unrelated activities | No synergy | Ensure KA1 feeds KA2 objectives |
| Ignoring accreditation | Administrative burden | Get accredited for KA1 first |

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Current Position**: Do you have KA1 accreditation? Existing partnerships?
2. **Define 5-Year Vision**: What do you want to achieve through Erasmus+?
3. **Apply for KA1 Accreditation**: If not already accredited, start here
4. **Map Potential Partners**: Which contacts could become KA2 partners?
5. **Plan First KA2 Step**: Small-scale partnership or full cooperation?

📋 **Action Items:**
- [ ] Check [accreditation status](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation) with your National Agency
- [ ] Review your KA1 mobility history for potential KA2 partners
- [ ] Identify 2-3 strategic themes for combined action
- [ ] Discuss with staff which colleagues should lead each action
- [ ] Create a 3-5 year Erasmus+ development plan

📚 **Useful Resources:**
- [KA1 for VET](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/learning-mobility-opportunities-vet)
- [KA2 Cooperation Partnerships](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/cooperation-partnerships)
- [Erasmus+ Accreditation](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [Successful VET Projects](https://erasmus-plus.ec.europa.eu/projects)

💡 **Pro Tip:** Many successful VET schools use KA1 as a "partnership incubator" - the organizations you exchange learners with become natural partners for KA2 innovation projects!"""

    def _generate_erasmus_accreditation_overview_guidance(self) -> str:
        """Generate guidance on Erasmus+ accreditation overview."""
        return """Erasmus+ Accreditation is a **strategic entry point** for organizations that want long-term, simplified access to Key Action 1 (mobility) funding throughout the 2021-2027 programme period.

## What is Erasmus+ Accreditation?

Accreditation is an **award that confirms** an organization's long-term commitment to quality mobility activities as part of a wider effort to develop the organization (the **Erasmus Plan**).

### Key Features

| Feature | Description |
|---------|-------------|
| **Purpose** | Simplified access to KA1 mobility funding for up to 7 years |
| **Who Can Apply** | Schools, VET institutions, Adult Education organizations, Youth organizations |
| **Erasmus Plan** | Strategic document describing your long-term goals and mobility activities |
| **Annual Budget Request** | After accreditation, submit simple budget requests each year |
| **Quality Standards** | Commit to Erasmus Quality Standards in all mobility activities |

### What Accreditation Provides

1. **Long-Term Funding Security**: Access to KA1 funding for the entire programme period (2021-2027)
2. **Simplified Applications**: No need to write full project proposals each year
3. **Guaranteed Budget**: Budget allocation based on your Erasmus Plan goals
4. **Flexibility**: Adjust activities annually within your approved Erasmus Plan
5. **Recognition**: Marks your organization as committed to quality internationalization

### Who Should Consider Accreditation?

Accreditation is ideal for organizations that:
- Plan **regular, ongoing** mobility activities (not just occasional exchanges)
- Want to develop a **strategic approach** to internationalization
- Are ready to commit to **quality standards** and continuous improvement
- Have the **capacity** to manage multiple mobility activities over several years

### Sectors Eligible for Accreditation

| Sector | Organization Types | Examples |
|--------|-------------------|----------|
| **Higher Education** | Universities, Polytechnics | HEIs with ECHE |
| **VET** | Vocational schools, Training centers | VET colleges, Apprenticeship providers |
| **School Education** | Primary and secondary schools | Public and private schools |
| **Adult Education** | Adult learning providers | Community education, Libraries |
| **Youth** | Youth organizations | NGOs working with young people |

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Your Readiness**: Can you commit to regular mobility activities for 5-7 years?
2. **Review Erasmus Quality Standards**: Check you can meet the quality criteria
3. **Draft an Erasmus Plan**: Define your 5-year internationalization strategy
4. **Contact Your National Agency**: Get guidance on the application process
5. **Prepare Documentation**: Gather evidence of your international experience

📋 **Action Items:**
- [ ] Read the [Erasmus+ Programme Guide 2026](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation)
- [ ] Check [Accreditation call deadlines](https://erasmus-plus.ec.europa.eu/calls) for your sector
- [ ] Review the [Erasmus Quality Standards](https://erasmus-plus.ec.europa.eu/programme-guide/part-a/erasmus-quality-standards)
- [ ] Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for guidance

📚 **Useful Resources:**
- [Erasmus+ Accreditation Guide](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation)
- [Erasmus Quality Standards](https://erasmus-plus.ec.europa.eu/programme-guide/part-a/erasmus-quality-standards)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_accreditation_benefits_guidance(self) -> str:
        """Generate guidance on benefits of Erasmus+ accreditation."""
        return """Erasmus+ Accreditation offers **significant advantages** for organizations that plan regular international mobility activities. Here are the key benefits of becoming accredited.

## Key Benefits of Erasmus+ Accreditation

### 1. Long-Term Funding Security (7 Years)

| Benefit | Description |
|---------|-------------|
| **Guaranteed Access** | Access to mobility funding for up to 7 years (2021-2027) |
| **Budget Predictability** | Annual budget allocation based on your Erasmus Plan |
| **Continuous Funding** | No gaps in funding between project periods |
| **Growing Budget** | Potential to increase funding as you build track record |

### 2. Simplified Annual Applications

| Feature | Accredited Organizations | Non-Accredited |
|---------|-------------------------|----------------|
| **Application Type** | Simple budget request | Full project proposal |
| **Preparation Time** | A few days | Several weeks |
| **Evaluation** | Operational check | Competitive ranking |
| **Approval Rate** | Very high (if compliant) | Variable (competitive) |
| **Administrative Burden** | Low | High |

### 3. Strategic Flexibility

- **Adjust Activities Annually**: Modify your activities within your approved Erasmus Plan
- **Respond to Needs**: Adapt to changing organizational priorities
- **Scale Up**: Increase mobility numbers as you build capacity
- **Multi-Year Planning**: Plan activities across the entire programme period

### 4. Quality Recognition

| Recognition | Value |
|-------------|-------|
| **Quality Mark** | Demonstrates commitment to quality internationalization |
| **Partner Attraction** | Easier to attract international partners |
| **Institutional Credibility** | Shows strategic approach to mobility |
| **Stakeholder Confidence** | Reassures parents, students, and staff |

### 5. Financial Benefits

- **Higher Per-Participant Budgets**: Accredited organizations often receive higher rates
- **Organizational Support**: Funding for coordination and management
- **No Co-Financing Required**: 100% EU funding for most activities
- **Green Travel Bonuses**: Additional funding for sustainable transport

### Comparison: Accredited vs Short-Term Projects

| Aspect | Accredited | Short-Term Projects |
|--------|-----------|---------------------|
| **Duration** | 7 years | 6-18 months |
| **Applications** | 1 accreditation + annual requests | Full application each time |
| **Approval** | Operational check | Competitive selection |
| **Flexibility** | High (within Erasmus Plan) | Limited to approved activities |
| **Funding Security** | High | Uncertain |
| **Administrative Load** | Low after accreditation | High for each project |
| **Best For** | Regular mobility activities | Occasional exchanges |

---

🎯 **Next Steps - What You Should Do:**

1. **Calculate Your Mobility Needs**: How many mobilities do you plan per year?
2. **Assess Long-Term Commitment**: Can you sustain activities for 5-7 years?
3. **Review Your Strategy**: Does your organization have an internationalization strategy?
4. **Compare Options**: Short-term projects may be better if mobility is occasional
5. **Consult Stakeholders**: Get buy-in from management and staff

📋 **Action Items:**
- [ ] Estimate annual mobility numbers for the next 5 years
- [ ] Review your organization's strategic plan for internationalization
- [ ] Contact successful accredited organizations in your sector for advice
- [ ] Attend [National Agency information sessions](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)

📚 **Useful Resources:**
- [Benefits of Accreditation](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation)
- [Success Stories](https://erasmus-plus.ec.europa.eu/projects)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_accreditation_timeline_guidance(self) -> str:
        """Generate guidance on Erasmus+ accreditation timeline and validity."""
        return """Understanding the **timeline** for Erasmus+ accreditation is essential for planning your application and mobility activities.

## Accreditation Timeline and Validity

### How Long Does Accreditation Last?

| Aspect | Duration |
|--------|----------|
| **Validity Period** | Until end of current programme period (2027) |
| **Maximum Duration** | Up to 7 years (for organizations accredited in 2021) |
| **New Applicants (2024-2027)** | Valid until end of 2027 |
| **Renewal** | Expected for next programme period (2028-2034) |

### Application Process Timeline

| Stage | Timeframe | What Happens |
|-------|-----------|--------------|
| **Call Opens** | Usually October/November | Application form available |
| **Preparation** | 4-8 weeks | Draft Erasmus Plan, gather documents |
| **Submission Deadline** | Usually January/February | Submit application |
| **Evaluation** | 2-3 months | National Agency reviews applications |
| **Results** | Usually April/May | Accreditation decisions announced |
| **First Budget Request** | May/June | Request funding for first year |
| **First Activities** | From September | Start mobility activities |

### Typical Annual Cycle (After Accreditation)

| Month | Activity |
|-------|----------|
| **January-February** | Submit annual budget request |
| **March-April** | National Agency reviews request |
| **May** | Budget approval notification |
| **June-July** | Sign annual grant agreement |
| **September onwards** | Implement mobility activities |
| **Ongoing** | Monitor and report progress |
| **Year-end** | Submit interim report |

### How Long to Get Accredited?

| Activity | Typical Duration |
|----------|-----------------|
| **Preparing Application** | 4-8 weeks |
| **Application Review** | 2-3 months |
| **Total (from start to approval)** | 4-6 months |
| **Total (from approval to first activity)** | 6-8 months |

### Important Deadlines

- **Accreditation Call**: Typically opens October, closes January/February
- **Budget Request**: Annual deadline usually in February
- **Check your National Agency** for exact dates in your country

### What Happens After 2027?

| Scenario | Expectation |
|----------|-------------|
| **New Programme Period** | Erasmus+ 2028-2034 expected |
| **Accreditation Renewal** | Likely simplified process for successful organizations |
| **Quality Assessment** | Track record will influence renewal |
| **Continuous Improvement** | Document your achievements |

---

🎯 **Next Steps - What You Should Do:**

1. **Check Current Deadlines**: Visit your National Agency website for exact dates
2. **Start Planning Early**: Begin 4-6 months before the application deadline
3. **Draft Your Erasmus Plan**: This is the core of your accreditation application
4. **Gather Documentation**: Prepare evidence of international experience
5. **Contact National Agency**: Attend information sessions

📋 **Action Items:**
- [ ] Check [Erasmus+ Call Calendar](https://erasmus-plus.ec.europa.eu/calls) for accreditation deadlines
- [ ] Mark key dates in your organizational calendar
- [ ] Schedule team meeting to discuss Erasmus Plan
- [ ] Contact [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for guidance

📚 **Useful Resources:**
- [Erasmus+ Calls and Deadlines](https://erasmus-plus.ec.europa.eu/calls)
- [Accreditation Application Guide](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1/accreditation)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_without_accreditation_guidance(self) -> str:
        """Generate guidance on KA1 mobility without accreditation (short-term projects)."""
        return """**Yes, absolutely!** Organizations can apply for Erasmus+ KA1 mobility funding **without accreditation** through short-term mobility projects.

## KA1 Mobility Without Accreditation

### Short-Term Mobility Projects

Short-term projects offer an alternative pathway to KA1 funding for organizations that:
- Are **new to Erasmus+** and want to test the waters
- Plan **occasional** mobility activities (not regular, ongoing)
- Want to implement a **specific, time-limited** project
- Are **not ready** for the long-term commitment of accreditation

### Comparison: Accreditation vs Short-Term Projects

| Aspect | Short-Term Projects | Accreditation |
|--------|---------------------|---------------|
| **Duration** | 6-18 months | Up to 7 years |
| **Application** | Full project proposal each time | One-time accreditation + annual budget requests |
| **Selection** | Competitive ranking | Operational check |
| **Flexibility** | Limited to approved activities | Flexible within Erasmus Plan |
| **Funding Security** | Uncertain (competitive) | High (if compliant) |
| **Best For** | Occasional mobility | Regular, ongoing mobility |
| **Administrative Load** | High per project | Low after initial accreditation |

### Short-Term Project Features

| Feature | Description |
|---------|-------------|
| **Project Duration** | 6-18 months (max 24 months in some sectors) |
| **Max Participants** | Usually 30-60 participants per project |
| **Budget** | Based on number of participants and activities |
| **Activities** | Staff and learner mobility, job shadowing, teaching |
| **Application** | Full project proposal with detailed activities |

### Who Should Use Short-Term Projects?

| Organization Type | Recommendation |
|-------------------|----------------|
| **New to Erasmus+** | Start with short-term to test the water |
| **Occasional mobility (1-2 activities/year)** | Short-term projects are sufficient |
| **Specific one-time exchange** | Short-term is appropriate |
| **Building track record** | Use short-term before applying for accreditation |
| **Uncertain about long-term** | Try short-term first |

### Pathway: Short-Term to Accreditation

Many organizations follow this progression:

1. **Year 1**: First short-term project (6-12 months)
2. **Year 2**: Second short-term project (build experience)
3. **Year 3**: Apply for accreditation (with track record)
4. **Year 4+**: Benefit from simplified annual funding

### Budget Considerations

| Budget Category | Short-Term | Accredited |
|-----------------|-----------|-----------|
| **Travel Support** | Same rates | Same rates |
| **Individual Support** | Same rates | Same rates |
| **Organizational Support** | Same rates | Same rates |
| **Total Available** | Project-based limit | Growing allocation |

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Your Needs**: How frequently do you plan mobility activities?
2. **Check Deadlines**: Short-term project calls have specific deadlines
3. **Define Your Project**: What specific activities do you want to implement?
4. **Find Partners**: Identify receiving organizations for your mobilities
5. **Consider Progression**: Plan your path toward accreditation if appropriate

📋 **Action Items:**
- [ ] Review [KA1 Short-Term Project calls](https://erasmus-plus.ec.europa.eu/calls)
- [ ] Download the application form from your National Agency
- [ ] Identify potential hosting organizations
- [ ] Develop a project concept with clear objectives
- [ ] Contact [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for guidance

📚 **Useful Resources:**
- [KA1 Short-Term Projects Guide](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1)
- [Erasmus+ Calls](https://erasmus-plus.ec.europa.eu/calls)
- [Partner Finding Tool](https://erasmus-plus.ec.europa.eu/partner-search)
- [National Agencies](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)"""

    def _generate_erasmus_accreditation_strategic_guidance(self) -> str:
        """Generate strategic guidance on choosing between accreditation and short-term projects."""
        return """Choosing between **Erasmus+ accreditation** and **short-term projects** depends on your organization's goals, capacity, and commitment level. Here's strategic guidance to help you decide.

## Strategic Decision: Accreditation vs Short-Term Projects

### Decision Framework

| Factor | Choose Accreditation If... | Choose Short-Term If... |
|--------|---------------------------|------------------------|
| **Mobility Frequency** | Plan regular activities (3+ per year) | Occasional activities (1-2 per year) |
| **Time Horizon** | 5-7 year strategic view | 1-2 year focus |
| **Commitment Level** | Ready for long-term commitment | Want to test first |
| **Administrative Capacity** | Can manage multiple activities | Limited capacity |
| **International Strategy** | Part of broader strategy | Ad-hoc activities |
| **Partner Network** | Established partners | Building relationships |

### Scoring Your Readiness

Rate your organization on these criteria (1-5):

| Criterion | Score 1-5 | What It Means |
|-----------|-----------|---------------|
| **Strategic Commitment** | ___ | Is internationalization in your strategic plan? |
| **Staff Buy-In** | ___ | Do staff support regular mobility? |
| **Partner Network** | ___ | Do you have reliable partners abroad? |
| **Track Record** | ___ | Have you successfully managed EU projects? |
| **Capacity** | ___ | Can you manage multiple activities per year? |
| **Financial Stability** | ___ | Can you pre-finance mobility costs? |

**Score Interpretation:**
- **25-30**: Strong candidate for accreditation
- **18-24**: Consider accreditation, strengthen weak areas
- **12-17**: Start with short-term projects to build capacity
- **Below 12**: Focus on building organizational capacity first

### Strategic Recommendations by Organization Type

| Organization Type | Recommendation | Rationale |
|-------------------|----------------|-----------|
| **Large University** | Accreditation | High capacity, strategic priority |
| **Small VET School** | Start short-term, then accredit | Build experience first |
| **Active Secondary School** | Accreditation | Regular student/staff exchanges |
| **New to Erasmus+** | Short-term first | Test the water, build track record |
| **Established International School** | Accreditation | Leverage existing partnerships |
| **Small NGO (Youth)** | Depends on activity level | Accreditation if 3+ activities/year |

### Benefits Comparison

| Benefit | Accreditation Value | Short-Term Value |
|---------|--------------------|-----------------|
| **Funding Security** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Administrative Ease** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Flexibility** | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Immediate Start** | ⭐⭐ | ⭐⭐⭐⭐ |
| **Low Commitment** | ⭐ | ⭐⭐⭐⭐⭐ |

### When Accreditation Is the Clear Choice

✅ Choose accreditation if you have:
- A clear internationalization strategy
- Regular mobility planned (5+ activities per year)
- Established partner network
- Staff committed to quality mobility
- Experience managing EU-funded activities

### When Short-Term Is the Clear Choice

✅ Choose short-term projects if you:
- Are new to Erasmus+ and want to experiment
- Plan only occasional mobility activities
- Have limited administrative capacity
- Want to test partnerships before committing
- Are uncertain about long-term strategic direction

### Hybrid Approach

Some organizations successfully combine both:
1. **Accreditation for core activities** (regular staff/student mobility)
2. **Short-term projects for special initiatives** (e.g., specific curriculum project)

---

🎯 **Next Steps - What You Should Do:**

1. **Score Your Readiness**: Use the criteria above to assess your position
2. **Consult Stakeholders**: Get input from management, staff, and partners
3. **Review Your Strategy**: Does mobility fit your long-term plans?
4. **Seek Advice**: Contact your National Agency for personalized guidance
5. **Make a Decision**: Choose the approach that fits your capacity

📋 **Action Items:**
- [ ] Complete the readiness assessment scoring above
- [ ] Discuss with management team and international coordinator
- [ ] Review your 5-year organizational development plan
- [ ] Contact [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for advice
- [ ] Set a decision deadline (don't delay indefinitely!)

📚 **Useful Resources:**
- [Accreditation vs Projects Comparison](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-1)
- [National Agency Guidance](https://erasmus-plus.ec.europa.eu/contacts/national-agencies)
- [Successful Organization Examples](https://erasmus-plus.ec.europa.eu/projects)

💡 **Pro Tip:** Many organizations that hesitate about accreditation end up wishing they had applied earlier. If you have a genuine commitment to internationalization, accreditation almost always provides better value than repeated short-term projects!"""

    def _generate_consortium_context_guidance(self, countries: list[str], query_lower: str) -> str:
        """Generate guidance when user provides consortium context."""
        # Categorize countries
        eu_member = []
        associated = []
        third = []

        eu_countries = {
            "germany",
            "france",
            "italy",
            "spain",
            "netherlands",
            "belgium",
            "austria",
            "sweden",
            "denmark",
            "finland",
            "ireland",
            "portugal",
            "greece",
            "poland",
            "czech",
            "hungary",
            "romania",
            "bulgaria",
            "croatia",
            "slovenia",
            "slovakia",
            "estonia",
            "latvia",
            "lithuania",
            "luxembourg",
            "malta",
            "cyprus",
        }
        associated_countries = {
            "uk",
            "united kingdom",
            "norway",
            "iceland",
            "israel",
            "turkey",
            "turkish",
            "serbia",
            "ukraine",
            "georgia",
            "armenia",
            "moldova",
            "albania",
            "montenegro",
            "bosnia",
            "kosovo",
            "north macedonia",
            "faroe islands",
            "tunisia",
            "morocco",
        }

        for c in countries:
            if c in eu_countries:
                eu_member.append(c.title())
            elif c in associated_countries:
                # Handle UK/Switzerland special status
                if c in ["uk", "united kingdom"]:
                    associated.append("United Kingdom (Associated)")
                elif c in ["switzerland", "swiss"]:
                    associated.append("Switzerland (Non-Associated Third Country)")
                else:
                    associated.append(c.title())
            else:
                third.append(c.title())

        country_breakdown = ""
        if eu_member:
            country_breakdown += f"**EU Member States**: {', '.join(eu_member)}\n"
        if associated:
            country_breakdown += f"**Associated/Other Countries**: {', '.join(associated)}\n"
        if third:
            country_breakdown += f"**Third Countries**: {', '.join(third)}\n"

        return f"""Thank you for sharing your consortium composition. Here's an initial eligibility assessment:

### Your Consortium

{country_breakdown}

### Quick Eligibility Check

| Requirement | Status |
|-------------|--------|
| **Minimum 3 legal entities** | ✅ To be confirmed (you've mentioned multiple countries) |
| **From 3 different EU/Associated Countries** | ✅ Appears eligible based on countries mentioned |
| **Independent entities** | ⚠️ To be confirmed (entities must not be linked) |

### Key Considerations

For most **collaborative Horizon Europe actions** (RIA, IA, CSA):
- The consortium **must include at least 3 independent legal entities**
- From **at least 3 different EU Member States or Associated Countries**
- **UK is currently an Associated Country** and counts toward the minimum
- **Switzerland has special status** - see specific guidance if Swiss partners are involved

### Country Eligibility by Status

| Country Status | Can Coordinate? | Receives EU Funding? |
|----------------|-----------------|---------------------|
| **EU Member State** | ✅ Yes | ✅ Yes (100% or per call rules) |
| **Fully Associated** (UK, Norway, Israel) | ✅ Yes | ✅ Yes |
| **Non-Associated** (Switzerland, UK pre-2024) | ⚠️ Usually no | ❌ Self-funded or SERI-funded |
| **Third Country** (US, Japan, etc.) | ❌ No | ❌ Self-funded (exceptional cases) |

---

🎯 **Next Steps - What You Should Do:**
• [ ] **Verify consortium meets minimum**: You should confirm you have at least 3 independent legal entities from 3 different EU/Associated Countries
• [ ] **Check specific call requirements**: Visit the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/) to verify your target call's eligibility conditions
• [ ] **Review the Programme Guide**: Check the [Horizon Europe Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf) Section 4 for full eligibility rules
• [ ] **Contact your NCP**: Reach out to your [National Contact Point](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for official advice
• [ ] **Consider expanding**: If you need additional partners, you should explore the partner search feature

💡 **Tip**: Ask me "Is this consortium eligible?" for a detailed eligibility confirmation, or about adding partners from specific countries."""

    def _generate_consortium_eligibility_guidance(self, context_lower: str) -> str:
        """Generate guidance about consortium eligibility."""
        # Check what countries are in context
        has_uk = "uk" in context_lower or "united kingdom" in context_lower
        has_switzerland = "switzerland" in context_lower or "swiss" in context_lower

        uk_note = ""
        if has_uk:
            uk_note = """

### UK Partner Status

✅ **The UK is currently an Associated Country** to Horizon Europe (since January 2024).

This means:
- UK entities **count toward** the minimum 3 countries requirement
- UK entities are **eligible for EU funding** under most calls
- UK entities **can coordinate** most Horizon Europe projects
- Some exceptions exist for security-sensitive topics"""

        swiss_note = ""
        if has_switzerland:
            swiss_note = """

### ⚠️ Switzerland Status Note

Switzerland is currently a **Non-Associated Third Country** in Horizon Europe.

This means Swiss partners:
- Can participate in most calls as **partners**
- **Cannot receive EU funding** directly (funded by SERI instead)
- Usually **cannot coordinate** Pillar II calls
- Do NOT count toward the minimum 3 countries requirement"""

        return f"""Yes, your consortium meets the minimum eligibility requirements for collaborative Horizon Europe projects (like RIA, IA, or CSA).

### Eligibility Breakdown

1.  **Minimum Consortium Size:** The standard requirement is a minimum of **3 independent legal entities** from **3 different EU Member States (MS) or Associated Countries (AC)**.

2.  **Your Partners:**
    - Based on the countries you've mentioned, your consortium appears to meet this requirement
    - Each partner must be a **legal entity** (registered organization)
    - Partners must be **independent** (not controlled by each other){uk_note}{swiss_note}

### Standard Eligibility Requirements

| Action Type | Minimum Consortium | Geographic Requirement |
|-------------|-------------------|----------------------|
| **RIA** (Research & Innovation) | 3 entities | 3 different MS/AC |
| **IA** (Innovation Action) | 3 entities | 3 different MS/AC |
| **CSA** (Coordination & Support) | 1 entity | 1 MS/AC |
| **MSCA Doctoral Networks** | 3 entities | 3 different countries |
| **ERC Grants** | 1 entity | 1 MS/AC |
| **EIC Accelerator** | 1 SME | 1 MS/AC |

### Funding Rates by Partner Type

| Partner Location | Funding Rate (RIA) | Funding Rate (IA) |
|------------------|-------------------|-------------------|
| **EU Member State** | 100% | 70% (100% for non-profit) |
| **Associated Country** (UK, Norway, etc.) | 100% | 70% (100% for non-profit) |
| **Non-Associated Third Country** | Self-funded | Self-funded |

---

🎯 **Next Steps - What You Should Do:**
• [ ] Confirm each partner is a registered legal entity
• [ ] Verify partners are independent (not controlled by same parent)
• [ ] Check the specific call's eligibility conditions on the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/)
• [ ] Review the [Horizon Europe Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf) for full details
• [ ] Contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for official confirmation"""

    def _generate_switzerland_participation_guidance(self) -> str:
        """Generate guidance about Switzerland's participation status."""
        return """Adding a partner from Switzerland (CH) to your consortium is entirely possible and highly recommended, but it comes with a specific funding status you must be aware of.

### Switzerland's Status in Horizon Europe

1.  **Participation Eligibility:** Swiss entities are eligible to participate in Horizon Europe consortia (RIA, IA, CSA).
2.  **Funding Source (CRITICAL):** For most collaborative calls under **Pillar II** (Clusters, Missions) and Pillar I (MSCA/ERC are largely unaffected), Switzerland is currently classified as a **Non-Associated Third Country**.

### What This Means for Your Consortium

| Aspect | Impact |
|--------|--------|
| **Can Swiss participate?** | ✅ Yes, in most calls |
| **Count toward minimum 3 countries?** | ❌ No (only MS/AC count) |
| **Receive EU funding?** | ❌ No direct EU funding |
| **Who funds them?** | 🇨🇭 SERI (Swiss State Secretariat) |
| **Can Swiss coordinate?** | ⚠️ Usually no for Pillar II |

### Key Implications

1.  **Minimum Consortium:** You still need **3 entities from 3 EU Member States or Associated Countries** - Switzerland does NOT count toward this minimum.

2.  **Funding:** Swiss partners participate at their own cost OR with funding from the Swiss State Secretariat for Education, Research and Innovation (SERI).

3.  **Coordination:** Swiss entities generally **cannot coordinate** Pillar II projects. They CAN coordinate in:
    - ERC grants (Pillar I)
    - Some MSCA actions
    - Specific calls that explicitly allow it

4.  **Consortium Impact:**
    - Your proposal evaluation is **not affected** by having Swiss partners
    - Swiss partners can lead work packages and make substantial contributions
    - Budget planning should reflect SERI funding for Swiss costs

### Practical Example

If your current consortium is: **Germany + France + UK**

| Entity | Country Status | Counts toward min? | Funding Source |
|--------|---------------|-------------------|----------------|
| German Uni | EU Member | ✅ Yes | EU |
| French SME | EU Member | ✅ Yes | EU |
| UK Research | Associated | ✅ Yes | EU |
| Swiss Partner | Non-Associated | ❌ No | SERI |

**Result:** Consortium REMAINS eligible (3 MS/AC met). Swiss partner adds value without affecting eligibility.

---

🎯 **Next Steps - What You Should Do:**
• [ ] Check if your specific call allows Swiss participation (most do)
• [ ] Contact the Swiss partner's grants office about SERI funding
• [ ] Visit [SERI's Horizon Europe page](https://www.sbfi.admin.ch/sbfi/en/home/research-and-innovation/international-cooperation-r-and-i/eu-framework-programmes-for-research/horizon-europe.html)
• [ ] Ensure you have 3 entities from EU Member States or Associated Countries (not counting Switzerland)
• [ ] Budget the Swiss partner's costs separately if using SERI funding

💡 **Tip:** Swiss partners can be extremely valuable - they have world-class research institutions (ETH, EPFL, PSI). Don't let the funding complexity discourage you!"""

    def _generate_third_country_participation_guidance(self, country: str | None = None) -> str:
        """Generate guidance about third country participation.

        Args:
            country: The specific third country mentioned (e.g., "India", "USA", "China").
                    If None, provides generic third country guidance.
        """
        # Determine the country-specific intro
        if country:
            country_intro = f"Yes, organizations from **{country}** can participate in Horizon Europe projects, but with specific limitations on funding and roles."
            country_name = country
        else:
            country_intro = "Yes, organizations from **Non-Associated Third Countries** can participate in Horizon Europe projects, but with specific limitations on funding and roles."
            country_name = "third country"

        # Country-specific examples for "practical considerations"
        country_examples = {
            "USA": {
                "institutions": "MIT, Stanford, NIH labs",
                "funding_options": "NSF/DOE collaborative programs with EU counterparts",
            },
            "India": {
                "institutions": "IITs, IISc, CSIR labs, TIFR",
                "funding_options": "DST bilateral programs, Indo-EU S&T cooperation",
            },
            "China": {
                "institutions": "Tsinghua, Peking University, CAS institutes",
                "funding_options": "MOST bilateral agreements, NSFC international cooperation",
            },
            "Japan": {
                "institutions": "University of Tokyo, Kyoto University, RIKEN",
                "funding_options": "JSPS bilateral programs, Japan-EU S&T cooperation",
            },
            "Australia": {
                "institutions": "CSIRO, Group of Eight universities",
                "funding_options": "ARC international programs, Australia-EU cooperation",
            },
            "Brazil": {
                "institutions": "USP, UNICAMP, Fiocruz, EMBRAPA",
                "funding_options": "CNPq/CAPES bilateral programs, Brazil-EU cooperation",
            },
            "South Korea": {
                "institutions": "KAIST, Seoul National University, KIST",
                "funding_options": "NRF international programs, Korea-EU S&T cooperation",
            },
            "Canada": {
                "institutions": "University of Toronto, McGill, NRC",
                "funding_options": "NSERC/CIHR programs, Canada-EU cooperation (note: Canada is NOT an Associated Country)",
            },
            "Mexico": {
                "institutions": "UNAM, IPN, CINVESTAV",
                "funding_options": "CONACYT bilateral programs, Mexico-EU cooperation",
            },
        }

        examples = country_examples.get(
            country,
            {
                "institutions": "leading research institutions",
                "funding_options": "bilateral S&T cooperation programs with the EU",
            },
        )

        return f"""{country_intro}

### {country_name} as a Non-Associated Third Country

{country if country else "Non-Associated Third Countries"} {"is" if country else "are"} classified as **Non-Associated Third Countries** in Horizon Europe. This means organizations from {country if country else "these countries"} can participate but face specific restrictions:

| Aspect | Rule for Third Countries |
|--------|-------------------------|
| **Can participate?** | ✅ Yes, in most calls |
| **Count toward minimum?** | ❌ No - only MS/AC count |
| **Receive EU funding?** | ❌ No (with rare exceptions) |
| **Can coordinate?** | ❌ No |
| **Who funds them?** | 💰 Self-funded |

### How Third Country Partners Participate

1. **Self-Funded Participation:** Partners from {country if country else "third countries"} must cover their own costs entirely. They typically cannot receive EU funding.

2. **No Coordination:** Third country entities cannot be the project coordinator - an EU Member State or Associated Country partner must coordinate.

3. **Don't Count Toward Minimum:** You still need **3 independent legal entities from 3 different EU Member States or Associated Countries**. {country if country else "Third country"} partners are "extra" - they don't count toward this requirement.

4. **Exception Cases:** In **exceptional circumstances**, the Commission may fund third country participation if:
   - Their participation is essential for the project
   - Explicitly stated in the work programme/call text
   - No suitable alternative exists in MS/AC

### Impact on Your Consortium

| Scenario | Minimum Met? | Notes |
|----------|-------------|-------|
| Germany + France + UK + {country if country else "Third Country"} | ✅ Yes | 3 MS/AC met, {country if country else "third country"} adds value |
| Germany + France + {country if country else "Third Country"} | ❌ No | Only 2 MS/AC - need 3 |
| Germany + France + Italy + {country if country else "Third Country"} | ✅ Yes | 3 MS/AC met |

### Alternative Pathways for {country if country else "Third Country"} Researchers

Researchers from {country if country else "third countries"} can also access EU funding through:

- **MSCA (Marie Skłodowska-Curie Actions):** Individual fellowships open to researchers from any country
- **ERC (European Research Council):** If the researcher is based at an EU/AC host institution
- **Bilateral agreements:** {examples["funding_options"]}
- **Subcontracting:** Organizations can be subcontractors instead of partners (different rules apply)

### Practical Considerations

**Advantages of {country if country else "Third Country"} Partners:**
- Access to unique expertise, facilities, and data
- Strong research institutions (e.g., {examples["institutions"]})
- Valuable for global impact and dissemination

**Disadvantages:**
- Self-funded = complex budget arrangements
- Cannot coordinate
- Not counted for consortium minimum

---

🎯 **Next Steps - What You Should Do:**
• [ ] Verify your specific call allows third country participation (check call text)
• [ ] Ensure you have **3 entities from EU Member States or Associated Countries** separately
• [ ] Discuss self-funding arrangements with the {country if country else "third country"} partner early
• [ ] Consider if {country if country else "third country"} participation is truly essential or if an AC alternative exists
• [ ] Contact your **National Contact Point (NCP)** for guidance on specific calls
• [ ] Check the [Horizon Europe Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf) Section 4.2

💡 **Tip:** {country if country else "Third country"} partners are most valuable when they bring unique capabilities (e.g., access to specific datasets, unique facilities, or markets). Make the case for "essential" participation in your proposal!"""

    def _generate_minimum_consortium_guidance(self) -> str:
        """Generate guidance about minimum consortium requirements."""
        return """For most collaborative Horizon Europe projects, the standard minimum consortium requirement is:

### Standard Minimum Requirement

**3 independent legal entities from 3 different EU Member States or Associated Countries**

### Requirements Breakdown

| Requirement | Details |
|-------------|---------|
| **Number of entities** | Minimum **3** |
| **Geographic spread** | **3 different countries** |
| **Country eligibility** | EU Member States OR Associated Countries |
| **Independence** | Entities must NOT be controlled by each other |

### Minimum by Action Type

| Action Type | Minimum Entities | Countries | Notes |
|-------------|-----------------|-----------|-------|
| **RIA** (Research & Innovation) | 3 | 3 MS/AC | Standard collaborative |
| **IA** (Innovation Action) | 3 | 3 MS/AC | Standard collaborative |
| **CSA** (Coordination & Support) | 1 | 1 MS/AC | Single entity allowed |
| **MSCA Doctoral Networks** | 3 | 3 countries | Any country |
| **MSCA Staff Exchanges** | 3 | 3 countries | At least 2 MS/AC |
| **ERC Grants** | 1 | 1 MS/AC | Single PI |
| **EIC Pathfinder** | 3 | 3 MS/AC | Early-stage tech |
| **EIC Transition** | 1-3 | 1 MS/AC | Varies by call |
| **EIC Accelerator** | 1 SME | 1 MS/AC | Single company |

### What Counts as "Independent"?

Entities are **independent** if none of the following applies:
- One entity directly or indirectly holds **>50% voting rights** in another
- One entity has the right to **appoint >50% of board members**
- One entity has **management control** over another through contract

**Example of NON-independent:**
- University A and University A's spin-off company (if controlled)
- Company X and Company X's 100% subsidiary

### EU Member States (27)

Austria, Belgium, Bulgaria, Croatia, Cyprus, Czech Republic, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia, Spain, Sweden

### Associated Countries (as of 2024)

**Fully Associated:** UK, Norway, Iceland, Israel, Albania, Montenegro, North Macedonia, Serbia, Turkey, Bosnia and Herzegovina, Kosovo, Moldova, Ukraine, Georgia, Armenia, Faroe Islands, Tunisia

**Non-Associated (Third Country):** Switzerland, USA, China, Japan, Australia, Canada, etc.

### Common Mistakes to Avoid

| Mistake | Why It's Wrong |
|---------|---------------|
| Including Switzerland in the 3 | Switzerland is Non-Associated Third Country |
| 3 entities from same country | Need 3 **different** countries |
| Parent + subsidiary as 2 entities | Not independent if controlled |
| Assuming all programmes need 3 | CSA, ERC, EIC Accelerator can be single entity |

---

🎯 **Next Steps - What You Should Do:**
• [ ] Verify each potential partner is a registered legal entity
• [ ] Check independence (no majority ownership between partners)
• [ ] Confirm at least 3 are from EU Member States or Associated Countries
• [ ] Check specific call text - some calls have ADDITIONAL requirements
• [ ] Review the [Horizon Europe Programme Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf) Section 4.1
• [ ] Contact your [National Contact Point (NCP)](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp) for official advice

💡 **Tip:** While 3 is the minimum, successful consortia often have 5-15 partners to cover all necessary expertise and demonstrate European impact!"""

    # =========================================================================
    # Associated Country Eligibility Detection and Guidance (Scenario 029)
    # =========================================================================

    def _generate_associated_country_coordinator_guidance(self, country_name: str) -> str:
        """Generate guidance about associated country coordinator eligibility."""
        # Turkey-specific content
        if country_name == "Turkey":
            return """**Turkey's Coordinator Eligibility in Horizon Europe**

Turkey is an **Associated Country** to Horizon Europe under a partial association agreement. This affects coordinator eligibility in specific ways:

### Coordinator Eligibility Summary

| Call Type | Can Turkey Coordinate? | Notes |
|-----------|------------------------|-------|
| **Standard RIA/IA** | ✅ Yes (most topics) | Full coordinator eligibility for non-sensitive topics |
| **MSCA** | ✅ Yes | Marie Skłodowska-Curie Actions - full eligibility |
| **ERC** | ✅ Yes | European Research Council - individual excellence |
| **Widening** | ✅ Yes | Eligible for Teaming, Twinning actions |
| **Defense-related** | ⚠️ Restricted | Some security topics exclude non-EU coordinators |
| **Quantum/Strategic Tech** | ⚠️ Restricted | Topics with EU strategic autonomy concerns may exclude |
| **Certain Cluster 4** | ⚠️ Check work programme | Digital/Cybersecurity may have restrictions |

### Key Points for Turkish Universities

1. **Full Funding Eligibility**: Turkish organizations receive the same funding rates as EU entities (100% for RIA, 70% for IA)

2. **Association Status Matters**: Turkey has full association to Pillar I (Excellent Science) and Pillar II (Global Challenges), but some Pillar III and security-related topics may have restrictions

3. **Work Programme Check**: Always verify the specific call conditions in the Funding & Tenders Portal - some topics explicitly state coordinator nationality requirements

4. **Consortium Requirements**: Even when Turkey can coordinate, the consortium must still meet minimum requirements (typically 3 entities from 3 different EU/AC countries)

---

🎯 **Next Steps - What You Should Do:**

1. **Check the specific call**: Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search) and review the call conditions
2. **Review the Work Programme**: Download the relevant cluster work programme to check for any nationality restrictions
3. **Contact your NCP**: Reach out to Turkey's [National Contact Points](https://www.tubitak.gov.tr/en/international/horizon-europe) for topic-specific guidance
4. **Build your consortium**: Start identifying partners from at least 2 other EU/Associated Countries

📋 **Action Items:**
- [ ] Identify 2-3 target calls in your research area
- [ ] Check each call's eligibility conditions for coordinator nationality
- [ ] Contact TÜBİTAK NCP for confirmation on sensitive topics
- [ ] Begin outreach to potential EU consortium partners"""

        # Generic associated country content
        return f"""**{country_name} Coordinator Eligibility in Horizon Europe**

{country_name} is associated to Horizon Europe, which affects coordinator eligibility depending on the association agreement terms.

### General Associated Country Coordinator Rules

| Eligibility Factor | Impact |
|-------------------|--------|
| **Association Status** | Full, partial, or sector-specific - determines access |
| **Topic Sensitivity** | Defense, security, and strategic tech may have restrictions |
| **Call Conditions** | Each work programme may specify coordinator requirements |
| **Funding Rate** | Associated countries typically get same rates as EU members |

### How to Verify Your Eligibility

1. **Check your association agreement**: Some countries have full association (Norway, Iceland), others have partial or sector-specific
2. **Review the specific call**: The call conditions state any coordinator nationality requirements
3. **Contact your NCP**: Your National Contact Point can provide definitive guidance

---

🎯 **Next Steps - What You Should Do:**

1. **Verify association status**: Check the European Commission's [list of Associated Countries](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/list-3rd-country-participation_horizon-euratom_en.pdf)
2. **Check call conditions**: Review eligibility section in the Funding & Tenders Portal
3. **Contact your NCP**: Get topic-specific guidance from your country's Horizon Europe NCP

📋 **Action Items:**
- [ ] Confirm your country's association status for Horizon Europe
- [ ] Review target calls for any coordinator restrictions
- [ ] Contact your National Contact Point for guidance"""

    def _generate_associated_country_partner_guidance(self, country_name: str) -> str:
        """Generate guidance about associated country partner eligibility."""
        return f"""Yes, a {country_name} organization is **fully eligible to participate as a partner (beneficiary)** in Horizon Europe projects.

### Partner Eligibility for Associated Countries

Since {country_name} is an **Associated Country** to Horizon Europe, its entities (universities, research institutes, companies) are treated almost identically to EU Member State entities when participating as partners.

| Aspect | Partner Eligibility |
|--------|---------------------|
| **Funding** | ✅ Full funding at same rates as EU entities |
| **All Call Types** | ✅ Eligible for RIA, IA, CSA, MSCA, ERC |
| **Sensitive Topics** | ✅ Generally eligible as partner (even when coordinator restricted) |
| **Administrative** | ✅ Same reporting and compliance requirements |

### Key Advantages of Partner Participation

1. **Full Funding Rate**: You receive the standard Horizon Europe funding rate:
   - **100%** for Research and Innovation Actions (RIA)
   - **70%** for Innovation Actions (IA) - 100% for non-profits
   - **100%** for Coordination and Support Actions (CSA)

2. **Build Track Record**: Participating as partner helps you:
   - Gain EU project management experience
   - Build relationships with experienced coordinators
   - Develop track record for future coordination

3. **Access to All Work Packages**: As a partner, you can lead work packages, even if you cannot coordinate the overall project

4. **Lower Administrative Burden**: The coordinator handles many consortium-level tasks

### Partner vs Coordinator: Strategic Considerations

| Factor | As Partner | As Coordinator |
|--------|-----------|----------------|
| **Administrative burden** | Lower | Higher |
| **Visibility** | Moderate | High |
| **Funding control** | Limited | Full |
| **Topic restrictions** | Fewer | More (for associated countries) |
| **Experience needed** | Less | More |

---

🎯 **Next Steps - What You Should Do:**

1. **Find coordinator partners**: You should contact experienced EU coordinators who need partners in your field
2. **Use partner search tools**: You should visit [CORDIS](https://cordis.europa.eu/) and check for organizations with successful projects in your area
3. **Attend brokerage events**: You can apply to join Horizon Europe info days to meet potential coordinators
4. **Prepare your expertise profile**: You should submit your organizational capability profile to partner search platforms

📋 **Action Items:**
- [ ] You should visit and register in the [EU Participant Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [ ] You should apply for and complete PIC registration for your organization
- [ ] You can contact your National Contact Point for partner-seeking guidance
- [ ] You should check the [Partner Search Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) for coordinator openings
- [ ] You should apply to join existing consortium preparation activities when opportunities arise"""

    def _generate_defense_restriction_guidance(self, country_name: str) -> str:
        """Generate guidance about defense/dual-use topic restrictions."""
        return f"""**Defense and Dual-Use Topic Restrictions for {country_name}**

Yes, **topic sensitivity matters significantly** for {country_name} participation. Defense-related and dual-use technology topics in Horizon Europe often have specific restrictions for non-EU entities.

### Understanding the Restrictions

| Topic Type | Restriction Level | {country_name} Participation |
|------------|-------------------|------------------------------|
| **European Defence Fund (EDF)** | Excluded | ❌ Not part of Horizon Europe |
| **Security Research (some topics)** | Restricted | ⚠️ May be excluded as coordinator, sometimes as partner |
| **Dual-Use Technology** | Variable | ⚠️ Depends on specific call conditions |
| **Critical Infrastructure** | Often restricted | ⚠️ Check call-by-call |
| **Cyber Security** | Variable | ⚠️ Some topics have EU-only requirements |
| **Non-sensitive research** | Open | ✅ Full participation |

### How Restrictions Work

1. **EU Strategic Autonomy Clause**: Some work programmes include requirements that:
   - Coordinator must be established in an EU Member State
   - Consortium must not include entities controlled by non-associated third countries
   - Results may have export control implications

2. **Security Clearance**: Some topics require:
   - EU-level security clearance (SEU CONFIDENTIAL or higher)
   - Access restrictions for non-EU nationals
   - Secure facility requirements

3. **Dual-Use Considerations**: Projects involving:
   - Technologies with both civil and military applications
   - Export-controlled materials or processes
   - May require additional compliance checks

### Examples of Restricted Topics

- Secure communication networks
- Critical infrastructure protection
- Cybersecurity for defense applications
- Space situational awareness (some topics)
- Surveillance technologies
- Sensitive AI applications

### How to Check if Your Topic is Restricted

1. **Read the Work Programme**: Look for phrases like:
   - "entities established in a Member State"
   - "security-related restrictions apply"
   - "EU strategic autonomy"
   - "coordinator must be..."

2. **Check Call Conditions**: In the Funding Portal, review the "Specific eligibility conditions" section

3. **Contact NCPs**: National Contact Points have the latest guidance on restricted topics

---

🎯 **Next Steps - What You Should Do:**

1. **Review your target topic**: Check if it falls under security research or dual-use categories
2. **Read the full call text**: Look for any nationality or security restrictions
3. **Consider non-sensitive alternatives**: Many topics in the same cluster may not have restrictions
4. **Contact your NCP**: Get official confirmation before investing preparation time
5. **Partner with EU coordinator**: Even if restricted as coordinator, you may be eligible as partner

📋 **Action Items:**
- [ ] Download the relevant cluster work programme
- [ ] Search for terms: "Member State", "security", "restricted", "strategic"
- [ ] Make a list of restricted vs unrestricted topics in your area
- [ ] Contact TÜBİTAK/your NCP for clarification on borderline topics
- [ ] Identify potential EU-based coordinators for sensitive topics"""

    def _generate_quantum_restriction_guidance(self, country_name: str) -> str:
        """Generate guidance about quantum/strategic technology restrictions."""
        return f"""**Quantum Technology and Strategic Tech Restrictions for {country_name}**

Quantum technology and other strategic technologies have **specific eligibility considerations** in Horizon Europe due to EU strategic autonomy concerns.

### Quantum Technology Restrictions Overview

| Technology Area | Typical Restriction | {country_name} Participation |
|-----------------|---------------------|------------------------------|
| **Quantum Computing** | Variable | ⚠️ Some topics restricted |
| **Quantum Communication** | Often restricted | ⚠️ Security implications |
| **Quantum Sensing** | Less restricted | ✅ Usually open |
| **Quantum Key Distribution** | Restricted | ⚠️ Defense applications |
| **Quantum Random Number Generators** | Variable | ⚠️ Depends on application |

### Why Quantum Has Special Restrictions

1. **EU Quantum Flagship**: Part of the EU's strategic technology agenda with specific participation rules

2. **Security Implications**: Quantum technologies have significant implications for:
   - Cryptography and secure communications
   - National defense systems
   - Critical infrastructure protection

3. **EU Strategic Autonomy**: The EU prioritizes developing sovereign quantum capabilities

### Specific Considerations for Cluster 4 (Digital)

The **Digital, Industry and Space** cluster contains most quantum-related topics. Key points:

| Topic Area | Typical Status |
|------------|----------------|
| **Basic quantum research** | Often open to associated countries |
| **Quantum infrastructure** | May have restrictions |
| **Quantum for security** | Usually restricted |
| **Quantum software/algorithms** | Variable |
| **Quantum standardization** | Often open |

### How to Navigate Quantum Topic Eligibility

1. **Distinguish Research vs Application**: Basic research often has fewer restrictions than applied security applications

2. **Check the Flagship Status**: EU Quantum Flagship topics may have specific rules

3. **Review Each Call Individually**: Restrictions vary significantly between calls, even within quantum topics

### Alternative Participation Strategies

If coordinator participation is restricted:

| Strategy | Description |
|----------|-------------|
| **Partner role** | Participate as beneficiary (often allowed) |
| **Basic research focus** | Target fundamental science topics |
| **Non-security applications** | Focus on industrial/healthcare quantum applications |
| **Collaborative agreements** | Some topics allow third-country expertise via subcontracts |

---

🎯 **Next Steps - What You Should Do:**

1. **Review Cluster 4 Work Programme**: Check quantum topics for eligibility restrictions
2. **Identify unrestricted topics**: Many quantum calls remain open to associated countries
3. **Consider partner participation**: Even restricted topics often allow associated country partners
4. **Contact NCP**: Get guidance on specific quantum calls
5. **Focus on strengths**: If you have quantum expertise, emphasize basic research and non-defense applications

📋 **Action Items:**
- [ ] Download Cluster 4 (Digital, Industry and Space) work programme
- [ ] List all quantum-related topics and their eligibility conditions
- [ ] Identify 2-3 quantum topics without coordinator restrictions
- [ ] Contact your NCP about the EU Quantum Flagship participation rules
- [ ] Explore partner opportunities with EU quantum research groups

📚 **Resources:**
- [EU Quantum Flagship](https://qt.eu/) - Official quantum initiative
- [Cluster 4 Work Programme](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) - Funding & Tenders Portal
- [Digital Europe Programme](https://digital-strategy.ec.europa.eu/) - Related quantum investments"""

    def _generate_can_coordinate_guidance(self, country_name: str) -> str:
        """Generate guidance on where associated countries CAN coordinate."""
        return f"""**Calls Where {country_name} Universities CAN Coordinate**

Yes, there are **many Horizon Europe calls** where {country_name} organizations can serve as coordinator. Here is a comprehensive overview:

### Programme Areas with Full Coordinator Eligibility

| Programme/Action | Coordinator Eligibility | Notes |
|------------------|-------------------------|-------|
| **Marie Skłodowska-Curie Actions** | ✅ Full | All MSCA actions (PF, DN, SE, COFUND, Citizens) |
| **European Research Council (ERC)** | ✅ Full | Starting, Consolidator, Advanced, Synergy Grants |
| **Widening Participation** | ✅ Full | Teaming, Twinning, ERA Chairs, HopOn |
| **Most Cluster Topics** | ✅ Full | Unless specifically restricted in call text |
| **Coordination & Support Actions** | ✅ Full | CSA almost always open to associated countries |

### Cluster-by-Cluster Overview

| Cluster | Can {country_name} Coordinate? | Exceptions |
|---------|------------------------------|------------|
| **Cluster 1 - Health** | ✅ Most topics | Rare security-related exceptions |
| **Cluster 2 - Culture/Social** | ✅ All topics | No restrictions |
| **Cluster 3 - Civil Security** | ⚠️ Variable | Some security topics restricted |
| **Cluster 4 - Digital/Space** | ⚠️ Variable | Some quantum/cybersecurity restricted |
| **Cluster 5 - Climate/Energy** | ✅ Most topics | Very few restrictions |
| **Cluster 6 - Food/Bio** | ✅ Most topics | Rare exceptions |

### Best Opportunities for {country_name} Coordinators

Based on typical call conditions, these areas are most accessible:

1. **ERC Grants**: Individual excellence-based, no nationality restrictions for PIs from associated countries

2. **MSCA Doctoral Networks**: {country_name} universities can coordinate training networks

3. **Widening Actions**: Specifically designed to increase participation from underrepresented countries

4. **Cluster 5 (Climate/Energy/Mobility)**: Large budget, many open topics, strong {country_name} research base

5. **Cluster 6 (Food/Bioeconomy)**: Agricultural research with few restrictions

6. **Missions**: All five EU Missions are generally open

### How to Find Coordinator-Eligible Calls

1. **Use the Funding Portal Filters**: Select "Associated Countries" in eligibility filters

2. **Check "Specific Eligibility Conditions"**: Look for any nationality requirements

3. **Search for Your Topic Keywords**: Many standard calls have no coordinator restrictions

### Current 2024-2025 Opportunities

To find specific calls, you should:
1. Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
2. Filter by: Status "Open" + Programme "Horizon Europe"
3. Review the call conditions for each relevant topic

---

🎯 **Next Steps - What You Should Do:**

1. **Browse Open Calls Now**: Visit the Funding Portal and search for your research keywords
2. **Register for Alerts**: Set up notifications for new calls in your area
3. **Contact Your NCP**: Get a curated list of coordinator-eligible calls in your field
4. **Start Consortium Building**: Begin reaching out to potential EU partners
5. **Prepare Your Organization**: Ensure PIC registration and LEAR appointment are complete

📋 **Action Items:**
- [ ] Search [Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) for open calls in your research area
- [ ] Filter by your cluster/destination
- [ ] Review call eligibility conditions for coordinator requirements
- [ ] Make a shortlist of 3-5 calls where you can coordinate
- [ ] Contact NCP for guidance on specific opportunities
- [ ] Begin outreach to potential consortium partners

📚 **Useful Resources:**
- [Horizon Europe Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2024/wp_horizon-2024-2025_en.pdf)
- [Associated Countries List](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/list-3rd-country-participation_horizon-euratom_en.pdf)
- [NCP Network](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)"""

    # ========================================================================
    # CREATIVE EUROPE MEDIA STRAND DETECTION AND GUIDANCE
    # ========================================================================

    def _generate_media_strand_overview_guidance(self) -> str:
        """Generate guidance on Creative Europe MEDIA strand overview."""
        return """**Creative Europe MEDIA Strand Overview**

The **MEDIA strand** is the audiovisual pillar of Creative Europe (2021-2027), with a budget of approximately **€1.4 billion** dedicated to supporting the European film and audiovisual industry.

## MEDIA Strand Actions Overview

| Action Type | Target | Budget Range | Funding Rate |
|------------|--------|--------------|--------------|
| **Development - Slate** | Production companies (3+ projects) | €150,000-200,000 | 70% |
| **Development - Single** | Individual projects | €25,000-60,000 | 50% |
| **Development - Co-dev** | European co-productions | €60,000-100,000 | 50% |
| **Distribution - Selective** | Distributors (packages) | Variable | Up to 50% |
| **Distribution - Films** | Single film distribution | €50,000-150,000 | 50% |
| **Distribution - Sales Agents** | International sales | Up to €150,000 | 40-60% |
| **Training** | Professionals | Variable | Up to 80% |
| **Festivals** | European festivals | €75,000-150,000 | 50-60% |
| **Cinema Networks** | Exhibitors network | Up to €2,000,000 | 50% |
| **Audience Development** | Innovative approaches | Variable | Up to 70% |

## Key Eligibility Requirements

### For Production Companies
- **Legal entity** established in a Creative Europe country
- **Audiovisual activities** as main purpose (check statutes)
- **Track record**: Some actions require previous productions
- **Financial capacity**: Ability to co-finance projects

### For Projects
| Project Type | Genre Requirements | Producer Requirements |
|-------------|-------------------|----------------------|
| **Fiction** | Feature film ≥60 min | Independent producer |
| **Documentary** | Creative documentary | Non-news content |
| **Animation** | All animation formats | Original IP preferred |
| **TV Series** | Fiction/animation ≥90 min total | Broadcasters eligible |

### Participating Countries
Creative Europe MEDIA is open to organizations from:
- All 27 EU Member States
- EEA countries (Iceland, Liechtenstein, Norway)
- Other participating countries (check [current list](https://culture.ec.europa.eu/creative-europe/creative-europe-media-strand/media-eligible-countries))

## MEDIA vs CULTURE vs CROSS-SECTORAL

| Strand | Focus | Typical Applicants |
|--------|-------|-------------------|
| **MEDIA** | Audiovisual industry | Producers, distributors, sales agents, festivals |
| **CULTURE** | Other cultural sectors | Museums, theatres, publishers, orchestras |
| **CROSS-SECTORAL** | Innovation & news | Tech companies, news organizations, labs |

---

🎯 **Next Steps - What You Should Do:**

1. **Identify Your Profile**: Determine if you're a producer, distributor, sales agent, or exhibitor
2. **Choose Your Action**: Select between development, distribution, training, or other actions
3. **Check Eligibility**: Verify your company meets the specific action requirements
4. **Find Partners**: For co-development, identify European partners
5. **Prepare Your Slate/Project**: Build a strong project portfolio or single project

📋 **Action Items:**
- [ ] Review the [MEDIA Work Programme 2024-2025](https://culture.ec.europa.eu/creative-europe/creative-europe-media-strand)
- [ ] Check [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-MEDIA)
- [ ] Register on [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [ ] Contact [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) in your country
- [ ] Attend MEDIA information days and workshops

📚 **Useful Resources:**
- [Creative Europe MEDIA Strand](https://culture.ec.europa.eu/creative-europe/creative-europe-media-strand)
- [MEDIA Programme Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)
- [Participating Countries List](https://culture.ec.europa.eu/creative-europe/creative-europe-media-strand/media-eligible-countries)"""

    def _generate_media_development_guidance(self) -> str:
        """Generate guidance on Creative Europe MEDIA development funding."""
        return """**Creative Europe MEDIA Development Funding**

MEDIA offers three main **development funding schemes** to support European audiovisual productions at the development stage:

## Development Funding Options

### 1. Slate Funding (Multi-Project Development)

| Aspect | Details |
|--------|---------|
| **Target** | Established production companies |
| **Projects** | 3-5 projects in development |
| **Budget** | €150,000 - €200,000 per slate |
| **Funding Rate** | Up to 70% of eligible costs |
| **Duration** | 36 months |

**Eligibility Requirements:**
- Company established in participating country
- Track record: At least 1 previous work released/broadcast
- Projects must be fiction, animation, or creative documentary
- Feature films must be ≥60 minutes (animation ≥24 min)
- Majority European ownership/control

**Eligible Activities:**
- Script development and rewrites
- Project packaging
- Market research and audience analysis
- Legal and financial structuring
- Teaser/pilot production (up to 10% of budget)

### 2. Single Project Development

| Aspect | Details |
|--------|---------|
| **Target** | All eligible production companies |
| **Projects** | 1 project in development |
| **Budget** | €25,000 - €60,000 per project |
| **Funding Rate** | Up to 50% of eligible costs |
| **Duration** | 24 months |

**Eligibility Requirements:**
- Company established in participating country
- Feature film ≥60 min (animation ≥24 min)
- TV series ≥90 min total
- No previous work requirement (newcomers welcome)
- Project must be majority European

### 3. Co-Development

| Aspect | Details |
|--------|---------|
| **Target** | European co-production partnerships |
| **Partners** | Minimum 2 from 2 different countries |
| **Budget** | €60,000 - €100,000 per project |
| **Funding Rate** | Up to 50% of eligible costs |
| **Duration** | 30 months |

**Eligibility Requirements:**
- Lead partner applies on behalf of consortium
- Partners from at least 2 Creative Europe countries
- All partners must be independent producers
- European co-production agreement in place
- Feature film, animation, or creative documentary

## Comparison Table

| Feature | Slate | Single | Co-Development |
|---------|-------|--------|----------------|
| Track record needed | Yes | No | Yes |
| Multiple projects | 3-5 | 1 | 1 |
| Max funding | €200,000 | €60,000 | €100,000 |
| Funding rate | 70% | 50% | 50% |
| Partners required | No | No | Yes (2+) |
| Best for | Established companies | Newcomers | International partnerships |

## Eligible Costs

- **Personnel**: Writers, consultants, researchers
- **Travel**: Market attendance, partner meetings
- **Rights**: Option agreements, underlying rights
- **Legal**: Contract negotiation, legal advice
- **Promotion**: Markets, pitching forums attendance
- **Overheads**: Up to 7% of direct costs

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Your Situation**: Newcomer (Single) vs. established (Slate) vs. co-production (Co-dev)
2. **Prepare Your Project Portfolio**: Develop strong creative packages
3. **Build Your Track Record**: If needed for Slate funding
4. **Find Co-development Partners**: Attend European markets and forums
5. **Prepare Application Materials**: Synopsis, treatment, production plan, budget

📋 **Action Items:**
- [ ] Review the [Development Call Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-MEDIA)
- [ ] Prepare project documentation (synopsis, treatment, director's note)
- [ ] Calculate your development budget and co-financing capacity
- [ ] Attend [MEDIA information sessions](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)
- [ ] Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) for guidance

📚 **Useful Resources:**
- [MEDIA Development Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [European Producers Club](https://europeanproducersclub.org/)
- [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)
- [European Audiovisual Observatory](https://www.obs.coe.int/)"""

    def _generate_media_distribution_guidance(self) -> str:
        """Generate guidance on Creative Europe MEDIA distribution support."""
        return """**Creative Europe MEDIA Distribution Support**

MEDIA offers comprehensive **distribution support** to help European films reach wider audiences across Europe and beyond.

## Distribution Support Schemes

### 1. Films on the Move (Selective Support)

| Aspect | Details |
|--------|---------|
| **Target** | Distributors releasing European non-national films |
| **Scope** | Theatrical and/or online distribution |
| **Budget** | €50,000 - €150,000 per film |
| **Funding Rate** | Up to 50% of eligible costs |

**Eligibility:**
- Distributor established in Creative Europe country
- Film must be European (majority European production)
- Film must be non-national (not produced in distributor's country)
- First theatrical release in the territory
- Film must have been produced in last 5 years

**Eligible Activities:**
- Marketing campaigns
- Print and advertising costs
- Theatrical release costs
- Subtitling and dubbing
- Festival participation
- Online premiere costs

### 2. European Sales Agents Support

| Aspect | Details |
|--------|---------|
| **Target** | Sales agents representing European films |
| **Scope** | International sales and marketing |
| **Budget** | Up to €150,000 per sales agent |
| **Funding Rate** | 40-60% depending on market performance |

**Eligibility:**
- Sales agent with track record in European films
- Representing catalogue of European works
- Sales commission model
- Active international sales activity

### 3. Distribution Agents Support (Video-on-Demand)

| Aspect | Details |
|--------|---------|
| **Target** | VOD platforms and aggregators |
| **Scope** | Online distribution of European catalogues |
| **Budget** | Variable based on scope |
| **Funding Rate** | Up to 60% |

**Eligibility:**
- Platform or aggregator established in participating country
- Significant European content in catalogue
- Cross-border availability

### 4. Cinema Networks (Europa Cinemas)

| Aspect | Details |
|--------|---------|
| **Target** | Independent cinema exhibitors |
| **Scope** | Programming and audience development |
| **Budget** | Based on network performance |
| **Funding Rate** | Up to 50% of eligible costs |

**Requirements:**
- Member of Europa Cinemas network
- Minimum 30% European non-national screenings
- Programming activities and audience outreach
- Young audiences initiatives

## Distribution Strategy Comparison

| Scheme | Best For | Key Benefit |
|--------|----------|-------------|
| **Films on the Move** | Distributors acquiring new films | Direct release support |
| **Sales Agents** | International sales companies | Market expansion funding |
| **VOD Support** | Digital platforms | Catalogue digitization |
| **Cinema Networks** | Independent cinemas | Programming support |

## European Film Market Landscape

| Market | Timing | Focus |
|--------|--------|-------|
| **EFM Berlin** | February | Sales, premieres |
| **Cannes Marché** | May | Prestige sales |
| **Toronto** | September | North American sales |
| **AFM Los Angeles** | November | US market |
| **Ventana Sur** | December | Latin America |

---

🎯 **Next Steps - What You Should Do:**

1. **Identify Your Distribution Model**: Theatrical, VOD, or hybrid
2. **Build Your European Catalogue**: Focus on quality European content
3. **Develop Market Presence**: Attend major European film markets
4. **Partner with Exhibitors**: Connect with Europa Cinemas network
5. **Plan Release Campaigns**: Prepare comprehensive marketing strategies

📋 **Action Items:**
- [ ] Review [Distribution Call Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-MEDIA)
- [ ] Analyse your distribution capacity and track record
- [ ] Identify European films for your catalogue
- [ ] Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)
- [ ] Consider joining [Europa Cinemas](https://www.europa-cinemas.org/) network

📚 **Useful Resources:**
- [MEDIA Distribution Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [Europa Cinemas Network](https://www.europa-cinemas.org/)
- [European Film Promotion](https://www.efp-online.com/)
- [European Audiovisual Observatory](https://www.obs.coe.int/)"""

    def _generate_media_multi_project_guidance(self) -> str:
        """Generate guidance on participating in multiple Creative Europe MEDIA projects."""
        return """**Participating in Multiple Creative Europe MEDIA Projects**

Good news! There is **no general limit** on how many Creative Europe MEDIA projects your organization can participate in. However, there are important considerations and strategic approaches to maximize your success.

## Multi-Project Participation Rules

### General Principles

| Rule | Details |
|------|---------|
| **No fixed limit** | Organizations can participate in multiple projects |
| **Capacity assessment** | EC evaluates financial and operational capacity |
| **Concurrent projects** | Can have several ongoing projects simultaneously |
| **Different actions** | Can participate in different MEDIA actions |
| **Same action** | Can apply to same action multiple times |

### Action-Specific Considerations

| Action | Multi-Participation Rules |
|--------|---------------------------|
| **Development - Slate** | 1 slate application per call, but can reapply |
| **Development - Single** | Multiple single projects possible |
| **Co-Development** | Can lead 1 + partner in others |
| **Distribution** | Multiple films/catalogues supported |
| **Training** | Multiple training activities |
| **Festivals** | One application per festival per call |

## Strategic Approaches for Multiple Projects

### 1. Diversification Strategy

**Combine different actions:**
- Development (Slate or Single) for pipeline building
- Co-Development for international partnerships
- Distribution support for your productions reaching audiences

### 2. Portfolio Approach

**Manage multiple development projects:**
- Slate funding: 3-5 projects under one grant
- Mix of genres and formats
- Staggered development timelines

### 3. Value Chain Integration

**Vertical integration example:**
```
Development (Slate/Single) → Production → Distribution (Films on the Move)
                                       → Sales (Sales Agent Support)
                                       → Exhibition (Cinema Networks)
```

## Capacity Requirements

### Financial Capacity
- Must demonstrate ability to co-finance all projects
- Stable financial situation (no bankruptcy procedures)
- Adequate turnover relative to requested funding

### Operational Capacity
- Sufficient staff and expertise
- Track record in managing similar projects
- Quality management systems

### Assessment Criteria
| Capacity Type | What EC Checks |
|--------------|----------------|
| Financial | Balance sheet, profit/loss, turnover ratios |
| Operational | Team CVs, past project list, infrastructure |
| Professional | Relevant experience, expertise, partnerships |

## Practical Limits and Considerations

### Realistic Capacity
While no fixed limits exist, consider:
- **Staff workload**: Each project requires dedicated attention
- **Cash flow**: Co-financing requirements for all projects
- **Quality**: Better to do fewer projects well than many poorly

### EC Evaluation Focus
The European Commission will assess:
1. Can you realistically manage all proposed projects?
2. Is your co-financing credible for all projects?
3. Do you have the expertise for each project type?

## Successful Multi-Project Examples

| Company Profile | Typical Portfolio |
|----------------|-------------------|
| **Established Producer** | 1 Slate + 2-3 Co-developments |
| **Sales Agent** | Sales Agent support + Multiple film distributions |
| **Distribution Company** | 5-10 Films on the Move + VOD support |
| **Festival** | Festival support + Training activities |

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Your Capacity**: Honestly evaluate staff, finances, and expertise
2. **Prioritize Strategically**: Focus on actions that fit your business model
3. **Build Gradually**: Don't overextend in first years
4. **Track Your Commitments**: Maintain clear overview of all EU-funded projects
5. **Coordinate Applications**: Time submissions for manageable workload

📋 **Action Items:**
- [ ] List all current and planned EU-funded projects
- [ ] Calculate total co-financing required across all projects
- [ ] Assess team capacity for additional project management
- [ ] Review your track record for each action type
- [ ] Contact [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) for strategic advice

📚 **Useful Resources:**
- [MEDIA Programme Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [Financial Capacity Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/rules-lev-lear-fca_en.pdf)
- [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)
- [Europa Cinemas](https://www.europa-cinemas.org/)"""

    def _generate_ce_film_company_overview_guidance(self) -> str:
        """Generate overview guidance for film production companies asking about Creative Europe."""
        return """**Creative Europe Funding for Film Production Companies**

As a **film production company**, you have access to several Creative Europe funding streams tailored to support European audiovisual content throughout its lifecycle.

## Relevant Funding Actions for Film Producers

| Action | Purpose | Typical Funding | Best For |
|--------|---------|-----------------|----------|
| **Development - Slate** | Multiple projects | €150,000-200,000 | Established companies |
| **Development - Single** | Individual project | €25,000-60,000 | All producers |
| **Development - Co-dev** | Co-productions | €60,000-100,000 | International projects |
| **Mini-Slate** | Small companies | €90,000-150,000 | Emerging producers |
| **TV & Online Content** | Series development | Up to €500,000 | Series producers |

## Your Path Through Creative Europe

### Phase 1: Development
Start with development funding to build your project:
- **Newcomers**: Apply for Single Project funding (no track record required)
- **Established**: Apply for Slate funding (3-5 projects, 70% funding rate)
- **Co-productions**: Apply for Co-Development with European partners

### Phase 2: Production Support
Once developed, access production funding:
- **Eurimages** (Council of Europe): Co-production fund
- **National funds**: Most countries have production incentives
- **Regional funds**: Many regions offer local production support

### Phase 3: Distribution & Sales
Help your film reach audiences:
- **Films on the Move**: Support for distributors
- **Sales Agent Support**: International sales funding
- **Cinema Networks**: Europa Cinemas programming support

## Eligibility Checklist for Production Companies

✅ **Basic Requirements:**
- [ ] Legal entity established in Creative Europe country
- [ ] Audiovisual production as main business activity
- [ ] Independent producer (not broadcaster-controlled)
- [ ] Valid PIC (Participant Identification Code)

✅ **For Slate Funding (additional):**
- [ ] At least 1 previous work released/broadcast
- [ ] 3-5 projects in development pipeline
- [ ] Financial capacity for co-financing

✅ **For Co-Development (additional):**
- [ ] Partner(s) from other Creative Europe country/countries
- [ ] Co-production agreement in place or planned
- [ ] Complementary expertise and resources

## Current Opportunities (2024-2025)

| Call | Deadline | Focus |
|------|----------|-------|
| **Development - Slate** | Multiple deadlines annually | Feature, animation, documentary |
| **Development - Single** | Multiple deadlines annually | All formats |
| **Co-Development** | Multiple deadlines annually | European partnerships |
| **TV & Online** | Annual | Series and online content |

## Financial Framework

### Typical Budget Structure (Development)
| Cost Category | % of Budget |
|--------------|-------------|
| Writing/Development | 40-50% |
| Personnel/Consultants | 20-30% |
| Travel & Markets | 10-15% |
| Legal & Rights | 10-15% |
| Overhead | Up to 7% |

### Co-Financing Requirements
| Action | EU Funding Rate | Your Co-Financing |
|--------|-----------------|-------------------|
| Slate | Up to 70% | At least 30% |
| Single | Up to 50% | At least 50% |
| Co-Development | Up to 50% | At least 50% |

---

🎯 **Next Steps - What You Should Do:**

1. **Register on EU Funding Portal**: Get your PIC number
2. **Assess Your Track Record**: Determine which actions you're eligible for
3. **Build Your Pipeline**: Develop 3-5 strong projects for Slate funding
4. **Find Co-production Partners**: Connect with European producers
5. **Attend Markets & Training**: Build your European network

📋 **Action Items:**
- [ ] Register on [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [ ] Review [MEDIA Development Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-MEDIA)
- [ ] Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)
- [ ] Prepare project documentation (synopsis, treatment, director's vision)
- [ ] Attend [MEDIA information sessions](https://culture.ec.europa.eu/creative-europe)
- [ ] Join the [European Producers Club](https://europeanproducersclub.org/)

📚 **Useful Resources:**
- [Creative Europe MEDIA Strand](https://culture.ec.europa.eu/creative-europe/creative-europe-media-strand)
- [EU Funding Portal - MEDIA Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-MEDIA)
- [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks)
- [Eurimages Co-production Fund](https://www.coe.int/en/web/eurimages)
- [European Film Promotion](https://www.efp-online.com/)"""

    def _generate_life_budget_guidance(self, subprogramme: str | None = None) -> str:
        """Generate comprehensive LIFE Programme budget guidance.

        Args:
            subprogramme: Optional specific sub-programme (NAT, ENV, CCA, CET)

        Returns:
            Formatted budget guidance string
        """
        # Sub-programme funding rates
        funding_rates = {
            "NAT": ("Nature and Biodiversity", "75%", "Up to 75% for priority species/habitats"),
            "ENV": ("Circular Economy and Quality of Life", "60%", "Standard 60% EU co-financing"),
            "CCA": (
                "Climate Change Mitigation and Adaptation",
                "60%",
                "Standard 60% EU co-financing",
            ),
            "CET": (
                "Clean Energy Transition",
                "95%",
                "Up to 95% EU co-financing (coordination & support)",
            ),
        }

        # Project type budgets
        project_budgets = {
            "SAP": (
                "Standard Action Projects",
                "€1-5 million",
                "3-5 years",
                "Best practice, demonstration, pilot, information projects",
            ),
            "SIP": (
                "Strategic Integrated Projects",
                "€10-30 million",
                "5-10 years",
                "Large-scale implementation of environmental/climate plans (ENV, CCA only)",
            ),
            "SNAP": (
                "Strategic Nature Projects",
                "€10-30 million",
                "5-10 years",
                "Large-scale implementation for nature/biodiversity (NAT only)",
            ),
            "TA": (
                "Technical Assistance",
                "Up to €1 million",
                "1-2 years",
                "Preparation of SIP/SNAP proposals",
            ),
        }

        # Build response
        if subprogramme and subprogramme in funding_rates:
            name, rate, notes = funding_rates[subprogramme]
            guidance = f"""## LIFE Programme Budget: {name} ({subprogramme})

### Co-Financing Rate
- **EU Contribution**: {rate}
- {notes}
- **Your Co-Financing**: {100 - int(rate.replace("%", "").replace("Up to ", ""))}%{"+ (varies by project)" if "Up to" in rate else ""}

### Typical Budget Ranges by Project Type

"""
            # Show relevant project types for this sub-programme
            if subprogramme == "NAT":
                relevant_types = ["SAP", "SNAP", "TA"]
            elif subprogramme in ["ENV", "CCA"]:
                relevant_types = ["SAP", "SIP", "TA"]
            else:  # CET
                relevant_types = ["SAP", "TA"]

            for ptype in relevant_types:
                pname, budget, duration, desc = project_budgets[ptype]
                guidance += f"""#### {pname} ({ptype})
- **Budget Range**: {budget}
- **Duration**: {duration}
- **Description**: {desc}

"""
        else:
            guidance = """## LIFE Programme Budget Overview

The LIFE Programme supports environment and climate action with a total budget of **€5.432 billion (2021-2027)**. Budget ranges depend on the **sub-programme** and **project type**.

### Co-Financing Rates by Sub-Programme

| Sub-Programme | EU Co-Financing | Your Contribution |
|--------------|-----------------|-------------------|
| **NAT** (Nature & Biodiversity) | 75% | 25% |
| **ENV** (Circular Economy) | 60% | 40% |
| **CCA** (Climate Change) | 60% | 40% |
| **CET** (Clean Energy Transition) | Up to 95% | 5%+ |

### Typical Budget Ranges by Project Type

#### Standard Action Projects (SAP)
- **Budget**: €1-5 million
- **Duration**: 3-5 years
- **Available for**: All sub-programmes
- **Description**: Best practice, demonstration, pilot, information projects

#### Strategic Integrated Projects (SIP)
- **Budget**: €10-30 million
- **Duration**: 5-10 years
- **Available for**: ENV, CCA sub-programmes only
- **Description**: Large-scale implementation of environmental/climate plans
- **Requirement**: Alignment with approved national/regional strategies

#### Strategic Nature Projects (SNAP)
- **Budget**: €10-30 million
- **Duration**: 5-10 years
- **Available for**: NAT sub-programme only
- **Description**: Large-scale implementation for nature/biodiversity
- **Requirement**: Focus on Prioritised Action Frameworks

#### Technical Assistance (TA)
- **Budget**: Up to €1 million
- **Duration**: 1-2 years
- **Available for**: All sub-programmes
- **Description**: Preparation of SIP/SNAP proposals

"""

        guidance += """### Key Budget Considerations

1. **Co-financing requirement**: LIFE requires beneficiaries to co-finance part of the project costs
2. **In-kind contributions**: Can count towards co-financing (staff time, equipment, etc.)
3. **Budget categories**: Personnel, travel, equipment, other direct costs, indirect costs
4. **Indirect costs**: Typically 7% flat rate of eligible direct costs

### Funding Model Comparison

| Aspect | LIFE | Horizon Europe |
|--------|------|----------------|
| Co-financing | 55-75% EU | 70-100% EU |
| Reimbursement | Actual costs | Actual or lump sum |
| Focus | Environment/Climate | Research/Innovation |
| TRL | Demonstration (5-8) | Research (2-6) |

---
🎯 **Next Steps:**
• Review the [LIFE Multi-Annual Work Programme](https://cinea.ec.europa.eu/programmes/life/life-work-programmes_en) for current priorities
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/?programmePeriod=2021-2027&programCcm2Id=43252476)
• Contact [CINEA](https://cinea.ec.europa.eu/programmes/life_en) for budget guidance
• Consult your [National Contact Point](https://cinea.ec.europa.eu/programmes/life/life-national-contact-points_en) for local advice
"""

        return guidance

    # ========================================================================
    # DIGITAL EUROPE vs HORIZON EUROPE COMPARISON DETECTION
    # ========================================================================

    def _generate_digital_europe_horizon_comparison_guidance(
        self, query: str, topic_context: str | None
    ) -> dict[str, Any]:
        """Generate comprehensive Digital Europe vs Horizon Europe comparison guidance."""

        # Determine topic-specific guidance
        topic_guidance = ""
        if topic_context == "AI":
            topic_guidance = """
### For Your AI Project

**Choose Digital Europe if:**
- You have a working AI solution ready to deploy (TRL 7-9)
- You want to deploy through AI Factories or Testing & Experimentation Facilities (TEFs)
- Your focus is on scaling existing AI capabilities
- You're an SME looking to accelerate AI adoption

**Choose Horizon Europe if:**
- You're developing novel AI approaches or algorithms (TRL 2-6)
- Your project involves fundamental AI research
- You need 100% funding for breakthrough R&D
- You're exploring unproven AI concepts

**Strategic Option:** Consider both programmes for a sequential approach - start with Horizon Europe research funding, then use Digital Europe to deploy and scale successful results.
"""
        elif topic_context == "cybersecurity":
            topic_guidance = """
### For Your Cybersecurity Project

**Choose Digital Europe if:**
- You're deploying security operations centers (SOCs)
- You're rolling out mature cybersecurity solutions
- You want to participate in ECCC (European Cybersecurity Competence Centre) activities
- Focus is on strengthening EU's cyber resilience infrastructure

**Choose Horizon Europe if:**
- You're researching new security threats or countermeasures
- You're developing novel cryptographic methods
- Your work involves Cluster 3 (Civil Security for Society) research
- You need 100% funding for security R&D
"""
        elif topic_context == "deployment":
            topic_guidance = """
### For Deployment Projects

**Digital Europe is designed for deployment** - if your primary goal is deploying and scaling existing digital solutions, Digital Europe is the appropriate programme. Horizon Europe is research-focused.
"""
        elif topic_context == "research":
            topic_guidance = """
### For Research Projects

**Horizon Europe is designed for research** - if your primary goal is R&D and exploring novel approaches, Horizon Europe is the appropriate programme. Digital Europe requires near-market readiness.
"""

        comparison_table = """## Digital Europe vs Horizon Europe: Comprehensive Comparison

| Aspect | Digital Europe | Horizon Europe |
|--------|----------------|----------------|
| **Primary Focus** | Digital deployment & capacity building | Research & innovation |
| **TRL Range** | TRL 7-9 (near-market, deployment) | TRL 2-6 (research to demonstration) |
| **Budget (2021-2027)** | €7.5 billion | €95.5 billion |
| **Funding Rate** | 50% (SMEs may get higher) | 100% (RIA), 70% (IA) |
| **Project Type** | Deployment, scaling, digital infrastructure | R&D, pilots, prototypes |
| **Typical Duration** | 24-36 months | 36-48 months |
| **Consortium** | Often smaller, focused | Typically 8-15 partners |

### Key Differences Explained

**1. Technology Readiness Level (TRL)**
- **Digital Europe**: Expects solutions at TRL 7-9 - ready for deployment
- **Horizon Europe**: Supports TRL 2-6 - from basic research to demonstration

**2. Funding Philosophy**
- **Digital Europe**: Co-funding model (you invest, EU matches) - deployment risk shared
- **Horizon Europe**: Research investment (100% for RIA) - innovation risk covered

**3. Objectives**
- **Digital Europe**: Build EU digital capacity (HPC, AI, Cybersecurity, Skills, Deployment)
- **Horizon Europe**: Advance scientific knowledge and technological innovation

### Digital Europe Objectives
1. **HPC** - Supercomputing infrastructure (EuroHPC)
2. **AI** - AI Factories, Testing & Experimentation Facilities
3. **Cybersecurity** - Security infrastructure, ECCC support
4. **Advanced Digital Skills** - Specialist training programmes
5. **Deployment (EDIHs)** - Digital Innovation Hubs network
6. **Semiconductors** - Chips Act implementation

### Horizon Europe Structure
1. **Pillar I**: Excellent Science (ERC, MSCA, Research Infrastructures)
2. **Pillar II**: Global Challenges (6 Clusters including Digital, Health, Climate)
3. **Pillar III**: Innovative Europe (EIC Accelerator, EIT)
"""

        next_steps = """
### Actionable Next Steps

1. **Assess your TRL**: If your solution is ready to deploy (TRL 7+), consider Digital Europe. If you need R&D (TRL 2-6), choose Horizon Europe.

2. **Check open calls**:
   - Digital Europe: [EC Digital Europe Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/digital)
   - Horizon Europe: [EC Horizon Europe Calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/horizon)

3. **Contact support**:
   - Digital Europe: HaDEA (European Health and Digital Executive Agency)
   - Horizon Europe: REA, EISMEA, or National Contact Points (NCPs)

4. **Consider sequential funding**: Use Horizon Europe for R&D, then Digital Europe for deployment of successful results.
"""

        full_guidance = comparison_table + topic_guidance + next_steps

        return {
            "thought": "User is comparing Digital Europe and Horizon Europe programmes. Providing comprehensive comparison with TRL differences and programme-specific guidance.",
            "action": "generate_guidance",
            "response": full_guidance,
            "guidance_type": "programme_comparison",
            "programmes_compared": ["Digital Europe", "Horizon Europe"],
            "topic_context": topic_context,
            "confidence": 0.95,
            "needs_more_info": False,
        }

    # ========================================================================
    # EU4HEALTH TOPICS/PRIORITIES DETECTION
    # ========================================================================

    def _generate_ce_cooperation_overview_guidance(self) -> str:
        """Generate guidance on Creative Europe Cooperation Projects overview."""
        return """**Creative Europe Cooperation Projects Overview**

The **CULTURE strand** of Creative Europe (2021-2027) offers **European Cooperation Projects** that support transnational cultural cooperation between European organizations.

## What Are Cooperation Projects?

Cooperation Projects fund **transnational cultural activities** that bring together organizations from different European countries to:
- Develop and disseminate cultural content
- Build capacity and professionalize the sector
- Improve cross-border access to European cultural works
- Support artists and cultural professionals

## Scale Categories

| Scale | Partners Required | EU Grant (max) | Funding Rate |
|-------|------------------|----------------|--------------|
| **Small-scale** | 3+ partners from 3+ countries | €200,000 | 60% |
| **Medium-scale** | 5+ partners from 5+ countries | €1,000,000 | 60% |
| **Large-scale** | 10+ partners from 10+ countries | €2,000,000 | 60% |

## Eligible Activities

### Core Activities Funded
- **Artistic creation** and production
- **Capacity building** and training
- **Audience development** and engagement
- **Circulation** of cultural works and artists
- **Digital innovation** in culture
- **Cross-sector collaboration**

### Sectors Covered
| Sector | Examples |
|--------|----------|
| **Performing Arts** | Theatre, dance, circus, street arts |
| **Visual Arts** | Painting, sculpture, photography, installations |
| **Cultural Heritage** | Museums, archives, libraries, monuments |
| **Music** | Classical, contemporary, traditional |
| **Literature** | Publishing, literary events, translation |
| **Architecture** | Design, urban planning |
| **Other** | Fashion, gastronomy, crafts |

## Key Eligibility Requirements

### For Organizations
- **Legal entity** established in a Creative Europe country
- **Active in cultural/creative sectors** (check statutes)
- **Financial capacity** to co-finance 40% of project costs
- **Operational capacity** to implement the project

### For Projects
| Requirement | Details |
|-------------|---------|
| **Duration** | 12-48 months |
| **Cross-border** | Partners from different countries required |
| **Non-profit focus** | Activities should not primarily generate profit |
| **European dimension** | Content should have European relevance |

## Participating Countries
Creative Europe is open to organizations from:
- All 27 EU Member States
- EEA countries (Iceland, Liechtenstein, Norway)
- Other participating countries (check [current list](https://culture.ec.europa.eu/creative-europe/eligibility))

---

🎯 **Next Steps - What You Should Do:**

1. **Choose Your Scale**: Based on your consortium size (3+, 5+, or 10+ partners)
2. **Define Your Project**: Identify the cultural activities and outcomes
3. **Build Your Consortium**: Find partners from different European countries
4. **Check Deadlines**: Review the [current calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-CULT)
5. **Register on the Portal**: Get your PIC number on the EU Funding Portal

📋 **Action Items:**
- [ ] Review the [Culture Strand Work Programme](https://culture.ec.europa.eu/creative-europe/culture-strand)
- [ ] Check [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-CULT)
- [ ] Register on [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
- [ ] Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) for guidance"""

    def _generate_ce_scale_comparison_guidance(self) -> str:
        """Generate guidance on Creative Europe cooperation project scale categories."""
        return """**Creative Europe Cooperation Projects: Scale Comparison**

The CULTURE strand offers three scales of cooperation projects, each with different partnership and budget requirements.

## Scale Categories Comparison

| Feature | Small-scale | Medium-scale | Large-scale |
|---------|-------------|--------------|-------------|
| **Minimum Partners** | 3 organizations | 5 organizations | 10 organizations |
| **Minimum Countries** | 3 different countries | 5 different countries | 10 different countries |
| **Maximum EU Grant** | €200,000 | €1,000,000 | €2,000,000 |
| **EU Funding Rate** | 60% | 60% | 60% |
| **Your Co-financing** | 40% (~€133,000 max) | 40% (~€667,000 max) | 40% (~€1,333,000 max) |
| **Project Duration** | 12-48 months | 12-48 months | 12-48 months |

## Which Scale Is Right for You?

### Choose Small-scale If:
✅ You're **new to EU funding** and want to test cooperation
✅ You have a **focused project** with clear objectives
✅ Your **budget needs** are under €330,000 total
✅ You can mobilize **3+ reliable partners**
✅ You want **simpler administration**

### Choose Medium-scale If:
✅ You have **previous cooperation experience**
✅ Your project has **broader European reach**
✅ You need **€330K-1.7M** total budget
✅ You can coordinate **5+ partners effectively**
✅ You want **significant impact** across sectors

### Choose Large-scale If:
✅ You have **extensive cooperation experience**
✅ Your project has **sector-wide European impact**
✅ You need **€1.7M-3.3M** total budget
✅ You can manage **10+ partners** with complex governance
✅ You aim for **structural change** in the sector

## Budget Examples

### Small-scale (€200K EU grant)
| Total Budget | €333,333 |
|--------------|----------|
| EU Grant | €200,000 (60%) |
| Co-financing | €133,333 (40%) |
| Per Partner (3) | ~€111,000 avg |

### Medium-scale (€1M EU grant)
| Total Budget | €1,666,667 |
|--------------|------------|
| EU Grant | €1,000,000 (60%) |
| Co-financing | €666,667 (40%) |
| Per Partner (5) | ~€333,000 avg |

### Large-scale (€2M EU grant)
| Total Budget | €3,333,333 |
|--------------|------------|
| EU Grant | €2,000,000 (60%) |
| Co-financing | €1,333,333 (40%) |
| Per Partner (10) | ~€333,000 avg |

## Key Differences

| Aspect | Small | Medium | Large |
|--------|-------|--------|-------|
| **Management Complexity** | Low | Medium | High |
| **Geographic Spread** | 3 countries | 5 countries | 10 countries |
| **Expected Impact** | Local/regional | National/multi-country | Pan-European |
| **Competition Level** | Moderate | Moderate | Lower (fewer applicants) |
| **Success Rate** | ~15-20% | ~15-20% | ~20-25% |

---

🎯 **Next Steps - What You Should Do:**

1. **Assess Your Capacity**: Can you coordinate the required number of partners?
2. **Estimate Your Budget**: What's your realistic total project cost?
3. **Map Your Network**: How many reliable partners can you mobilize?
4. **Define Impact Goals**: What level of European impact do you aim for?
5. **Consider Starting Small**: If new to CE, start with small-scale

📋 **Action Items:**
- [ ] Count your potential partners and their countries
- [ ] Estimate total project budget (activities + coordination)
- [ ] Verify partners can contribute 40% co-financing
- [ ] Check [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-CULT)"""

    def _generate_ce_partner_category_guidance(self) -> str:
        """Generate guidance on partner count and category selection."""
        return """**Creative Europe Cooperation: Partner Count and Category Selection**

Based on your consortium size, here's which cooperation project category you can apply for.

## Partner Count Requirements

| Your Partners | Eligible Category | Maximum EU Grant |
|---------------|------------------|------------------|
| **3 partners** | Small-scale ✅ | €200,000 |
| **4 partners** | Small-scale ✅ | €200,000 |
| **5 partners** | Small-scale ✅ OR Medium-scale ✅ | €200K or €1M |
| **6-9 partners** | Small-scale ✅ OR Medium-scale ✅ | €200K or €1M |
| **10+ partners** | Any scale ✅ | Up to €2M |

## With 3 Partners: Small-scale

✅ **You qualify for Small-scale cooperation projects**

| Requirement | Status |
|-------------|--------|
| Minimum 3 partners | ✅ Met with 3 partners |
| Minimum 3 countries | ⚠️ Check each partner is from a different country |
| EU Grant | Up to €200,000 |
| Your co-financing | ~€133,000 (40%) |
| Total budget | ~€333,000 max |

### Important Notes for 3-Partner Consortia
- All 3 partners must be from **different eligible countries**
- One partner acts as **Project Coordinator**
- All partners share the 40% co-financing responsibility
- Each partner should have a **clear role** in the project

## Country Requirement Reminder

The country count is **separate from** partner count:
- 3 partners = need 3 **different countries**
- 5 partners = need 5 **different countries** (for medium-scale)
- 10 partners = need 10 **different countries** (for large-scale)

Example: Having 5 partners from only 3 countries = **Small-scale only**

## Budget Per Partner Estimate

| Scale | Total Budget | Per Partner (Equal Split) |
|-------|--------------|---------------------------|
| Small (3 partners) | €333,333 | €111,111 |
| Small (5 partners) | €333,333 | €66,666 |
| Medium (5 partners) | €1,666,667 | €333,333 |
| Medium (7 partners) | €1,666,667 | €238,095 |
| Large (10 partners) | €3,333,333 | €333,333 |

*Note: Budget distribution doesn't need to be equal - coordinator typically gets more.*

---

🎯 **Next Steps - What You Should Do:**

1. **Verify Country Diversity**: Confirm each partner is from a different eligible country
2. **Choose Your Lead**: Decide which organization will coordinate
3. **Discuss Co-financing**: Ensure all partners can contribute to the 40%
4. **Define Roles**: Assign clear responsibilities to each partner
5. **Apply**: Prepare your application for the next call deadline

📋 **Action Items:**
- [ ] List all partners with their countries
- [ ] Verify all countries are [eligible](https://culture.ec.europa.eu/creative-europe/eligibility)
- [ ] Agree on budget distribution among partners
- [ ] Identify the coordinator organization
- [ ] Check [open calls](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;callCode=CREA-CULT)"""

    def _generate_ce_funding_rate_guidance(self) -> str:
        """Generate guidance on Creative Europe cooperation project funding rates."""
        return """**Creative Europe Cooperation Project Funding Rates**

Creative Europe uses a **lump sum funding model** with fixed EU contribution rates for cooperation projects.

## Funding Rate Overview

| Aspect | Rate/Amount |
|--------|-------------|
| **EU Funding Rate** | 60% |
| **Your Co-financing** | 40% |
| **Funding Model** | Lump sum |
| **Payment Schedule** | Pre-financing + balance |

## What Does 60% Mean?

The EU covers **60% of your total eligible costs**:

| Scale | Max EU Grant | Your 40% Co-financing | Total Budget |
|-------|-------------|----------------------|--------------|
| Small | €200,000 | ~€133,333 | €333,333 |
| Medium | €1,000,000 | ~€666,667 | €1,666,667 |
| Large | €2,000,000 | ~€1,333,333 | €3,333,333 |

## Sources of Co-financing (40%)

Your 40% contribution can come from:

| Source | Acceptable? | Notes |
|--------|-------------|-------|
| **Own resources** | ✅ Yes | Organization's own funds |
| **Partner contributions** | ✅ Yes | Shared across consortium |
| **National grants** | ✅ Yes | If no double-funding |
| **Private sponsorship** | ✅ Yes | Corporate sponsors |
| **Ticket revenue** | ✅ Yes | If part of activities |
| **Other EU grants** | ❌ No | Cannot use for same costs |

## Lump Sum Model Explained

Creative Europe uses **lump sums** (not actual cost reimbursement):

### How It Works
1. You propose a **detailed budget** at application stage
2. If selected, you receive a **fixed lump sum**
3. You complete the planned **work packages**
4. Payments linked to **deliverables**, not expense reports

### Benefits of Lump Sum
✅ **Less financial reporting** - No detailed expense tracking needed
✅ **Flexibility** - Move funds between budget categories
✅ **Predictability** - Know exactly what you'll receive
✅ **Simpler audits** - Focus on outputs, not receipts

### Important Notes
⚠️ You still need to **complete all work packages**
⚠️ Budget should be **realistic and justified**
⚠️ **Under-spending** doesn't mean you keep the difference

## Payment Schedule

| Payment | When | Typical Amount |
|---------|------|----------------|
| **Pre-financing** | After grant signature | 40-50% of EU grant |
| **Interim (if >24 months)** | Mid-project | 20-30% of EU grant |
| **Balance** | After final report | Remaining amount |

## Budget Categories

Your budget should cover:

| Category | What's Included |
|----------|-----------------|
| **Personnel** | Staff costs for project work |
| **Travel** | Travel and subsistence for activities |
| **Equipment** | Equipment needed for project |
| **Subcontracting** | External services |
| **Other Direct Costs** | Materials, venue hire, etc. |
| **Indirect Costs** | 7% flat rate for overheads |

---

🎯 **Next Steps - What You Should Do:**

1. **Plan Your Budget**: Estimate total project costs realistically
2. **Secure Co-financing**: Confirm how each partner covers their 40%
3. **Identify Co-funding Sources**: National grants, sponsors, own resources
4. **Review Lump Sum Rules**: Understand work package requirements
5. **Prepare Financial Documents**: Bank account, legal status

📋 **Action Items:**
- [ ] Calculate your total budget need
- [ ] Identify sources for 40% co-financing
- [ ] Check national cultural funding schemes
- [ ] Review the [Financial Guide](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/om_en.pdf)
- [ ] Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) for budget advice"""

    def _generate_ce_scale_growth_guidance(self) -> str:
        """Generate guidance on growing into larger cooperation project scale."""
        return """**Growing Your Creative Europe Cooperation Project Scale**

If you want to move from small-scale to medium-scale (or medium to large), here's what you need to know.

## Requirements Comparison

| Requirement | Small → Medium | Medium → Large |
|-------------|---------------|----------------|
| **Additional Partners** | +2 more (5 total) | +5 more (10 total) |
| **Additional Countries** | +2 more (5 total) | +5 more (10 total) |
| **Budget Increase** | €200K → €1M (+€800K) | €1M → €2M (+€1M) |
| **Co-financing Increase** | €133K → €667K (+€533K) | €667K → €1.33M (+€666K) |

## Growing from Small (3) to Medium (5) Scale

### What You Need
| Requirement | Current (Small) | Needed (Medium) | Gap |
|-------------|-----------------|-----------------|-----|
| Partners | 3 | 5 | +2 partners |
| Countries | 3 | 5 | +2 countries |
| Max EU Grant | €200,000 | €1,000,000 | +€800,000 |
| Co-financing | €133,333 | €666,667 | +€533,334 |

### How to Find New Partners
1. **Use your network**: Ask current partners for recommendations
2. **Creative Europe Desks**: Contact desks in target countries
3. **Partner search tools**: Use [Creative Europe Partner Search](https://culture.ec.europa.eu/cultural-and-creative-sectors/cultural-networks-and-platforms)
4. **Sector events**: Attend cultural sector conferences
5. **Previous projects**: Reach out to organizations from similar projects

### Choosing New Partner Countries
Prioritize countries that:
- ✅ Have **complementary expertise**
- ✅ Bring **different perspectives**
- ✅ Can **contribute to co-financing**
- ✅ Have **strong cultural sectors**
- ✅ Are **underrepresented** in your consortium

## Growing from Medium (5) to Large (10) Scale

### What You Need
| Requirement | Current (Medium) | Needed (Large) | Gap |
|-------------|------------------|----------------|-----|
| Partners | 5 | 10 | +5 partners |
| Countries | 5 | 10 | +5 countries |
| Max EU Grant | €1,000,000 | €2,000,000 | +€1,000,000 |
| Co-financing | €666,667 | €1,333,333 | +€666,666 |

### Governance Considerations
Large-scale projects need:
- **Steering committee** with clear decision-making
- **Work package leaders** for different activities
- **Communication strategy** across 10+ organizations
- **Quality assurance** mechanisms
- **Conflict resolution** procedures

## Practical Steps to Scale Up

### 1. Assess Your Capacity
| Question | Consider |
|----------|----------|
| Can you manage more partners? | Coordination complexity increases |
| Do you have admin capacity? | More reporting, more communication |
| Is your project suitable for scaling? | Some projects are better small |

### 2. Build the Partnership Gradually
- Start with **letters of intent**
- Conduct **partner matching meetings**
- Run **small pilot activities** together
- Build **trust and working relationships**

### 3. Strengthen Your Proposal
Medium/large-scale projects should demonstrate:
- **Wider geographic reach**
- **Greater sectoral impact**
- **More ambitious outcomes**
- **Sustainable results beyond project**

### 4. Consider the Timeline
| Step | Typical Duration |
|------|-----------------|
| Finding new partners | 3-6 months |
| Building relationships | 3-6 months |
| Developing proposal together | 3-4 months |
| Total before application | 6-12 months |

## Alternative: Apply as Partner First

If scaling up is challenging:
1. **Join an existing large-scale project** as a partner
2. **Learn the governance and management**
3. **Build your network**
4. **Lead your own project** later with experience

---

🎯 **Next Steps - What You Should Do:**

1. **Evaluate Capacity**: Can your organization handle larger coordination?
2. **Map Potential Partners**: Which countries/organizations could join?
3. **Contact Creative Europe Desks**: Get recommendations for partners
4. **Plan Timeline**: Allow 6-12 months to build new partnerships
5. **Consider Alternatives**: Could you join an existing larger project?

📋 **Action Items:**
- [ ] List potential new partner countries
- [ ] Contact [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) in target countries
- [ ] Use [Partner Search tools](https://culture.ec.europa.eu/cultural-and-creative-sectors)
- [ ] Assess your organization's coordination capacity
- [ ] Review successful large-scale projects for inspiration"""

    # ========================================================================
    # NICHE INTERDISCIPLINARY QUERY DETECTION AND HANDLING
    # ========================================================================

    def _generate_niche_query_guidance(
        self,
        query: str,
        niche_context: dict,
        calls_found: int,
        projects_found: int,
        has_relevant_results: bool,
    ) -> str:
        """Generate helpful guidance for niche interdisciplinary queries.

        This acknowledges when exact matches don't exist and provides
        alternative approaches without hallucinating fake calls.
        """
        traditional = niche_context.get("traditional_domains", [])
        tech = niche_context.get("tech_domains", [])
        geo = niche_context.get("geographic_constraints", [])
        clusters = niche_context.get("relevant_clusters", [])
        # Note: relevant_programmes is available in niche_context if needed for future enhancements

        lines = []

        # Acknowledge the interdisciplinary nature
        lines.append("## Understanding Your Funding Search\n")
        domain_str = " + ".join(
            [d.title() for d in traditional] + [d.upper() for d in tech] + [g.title() for g in geo]
        )
        lines.append(
            f"Your query combines **{domain_str}** - this is a highly "
            "specialized interdisciplinary area that may not have dedicated "
            "funding calls.\n"
        )

        # Report search results honestly
        lines.append("### What We Found\n")
        if has_relevant_results:
            lines.append(
                f"✅ Found **{calls_found} potentially relevant calls** and "
                f"**{projects_found} similar funded projects**.\n"
            )
            lines.append(
                "Review the results above - while they may not be perfect matches, "
                "they cover related topics that could accommodate your project.\n"
            )
        else:
            lines.append(
                f"⚠️ Found **{calls_found} calls** and **{projects_found} projects**, "
                "but these may only partially match your specific requirements.\n"
            )
            lines.append(
                "This is common for highly specialized interdisciplinary topics. "
                "Below are strategies for finding appropriate funding.\n"
            )

        # Suggest relevant clusters
        if clusters:
            lines.append("### Relevant Horizon Europe Clusters\n")
            cluster_names = {
                "CL2": "Cluster 2: Culture, Creativity & Inclusive Society",
                "CL4": "Cluster 4: Digital, Industry & Space",
                "CL5": "Cluster 5: Climate, Energy & Mobility",
                "CL6": "Cluster 6: Food, Bioeconomy, Natural Resources",
            }
            for cl in clusters:
                name = cluster_names.get(cl, cl)
                lines.append(f"- **{name}**")
            lines.append("")

        # Suggest alternative programmes
        lines.append("### Alternative Funding Approaches\n")

        if "heritage" in traditional or "archaeology" in traditional or "crafts" in traditional:
            lines.append(
                "**1. Creative Europe (CULTURE strand)**\n"
                "   - Cultural heritage digitization projects\n"
                "   - Cultural cooperation projects with technology components\n"
                "   - [Creative Europe Portal](https://culture.ec.europa.eu/creative-europe)\n"
            )

        if "maritime" in traditional or "underwater" in " ".join(traditional):
            lines.append(
                "**2. EU Mission: Restore our Ocean and Waters**\n"
                "   - Marine research and blue economy\n"
                "   - Underwater cultural heritage protection\n"
                "   - [Ocean Mission](https://research-and-innovation.ec.europa.eu/"
                "funding/funding-opportunities/funding-programmes-and-open-calls/"
                "horizon-europe/eu-missions-horizon-europe/restore-our-ocean-and-waters_en)\n"
            )

        if tech:
            lines.append(
                "**3. Digital Europe Programme**\n"
                "   - If your project focuses on AI/digital technology deployment (TRL 7-9)\n"
                "   - [Digital Europe Portal](https://digital-strategy.ec.europa.eu/"
                "en/activities/digital-programme)\n"
            )

        lines.append(
            "**4. Split Your Project**\n"
            "   - Research component → Horizon Europe RIA\n"
            "   - Cultural/creative component → Creative Europe\n"
            "   - Education/training component → Erasmus+\n"
        )

        lines.append(
            "**5. ERC Grants**\n"
            "   - For frontier research in any domain\n"
            "   - Principal Investigator-led, highly flexible\n"
            "   - [ERC Portal](https://erc.europa.eu/)\n"
        )

        # Actionable next steps
        lines.append("\n---\n")
        lines.append("🎯 **Recommended Next Steps:**\n")
        lines.append("1. **Review the results above** - some may be adaptable to your project\n")
        lines.append(
            "2. **Contact your National Contact Point (NCP)** - they can advise on "
            "best fit: [Find your NCP](https://ec.europa.eu/info/funding-tenders/"
            "opportunities/portal/screen/support/ncp)\n"
        )
        lines.append(
            "3. **Check EU Portal topic search** - filter by multiple keywords: "
            "[Topic Search](https://ec.europa.eu/info/funding-tenders/opportunities/"
            "portal/screen/opportunities/topic-search)\n"
        )
        lines.append(
            "4. **Consider writing to the EC** - for novel interdisciplinary topics, "
            "the EC may include them in future work programmes\n"
        )

        return "\n".join(lines)

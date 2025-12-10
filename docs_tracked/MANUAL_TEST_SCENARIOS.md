# Manual Test Scenarios for MAP-IT System

This document contains test questions/scenarios to manually verify all system capabilities are working correctly.

---

## 1. Funding Call Search (search_funding_calls)

### Basic Call Search
```
What are some open calls about energy?
```
**Expected**: Should return multiple calls (10+) related to energy, with clean summaries, deadlines, and apply links.

### Filtered Call Search
```
Show me open calls for hydrogen research in Cluster 5
```
**Expected**: Returns CL5 calls specifically about hydrogen.

### Status-Specific Search
```
What upcoming calls are there for AI and digital technologies?
```
**Expected**: Returns calls with "upcoming" status in digital/AI domains.

### Multiple Parallel Searches (Bug Fix Verification)
```
Find all open funding opportunities related to renewable energy
```
**Expected**: Should merge results from multiple tool calls and show ALL unique calls (not just 2-3). Verify the count matches what the agent found.

---

## 2. Project Search (search_projects)

### Basic Project Search
```
Find projects about quantum computing
```
**Expected**: Returns funded CORDIS projects with titles, IDs, budgets, and objectives.

### Semantic Project Search
```
Show me projects working on reducing carbon emissions in transportation
```
**Expected**: Should find projects even if they don't use exact keywords (semantic search).

### Organization Projects
```
What projects has Fraunhofer participated in?
```
**Expected**: Lists projects where Fraunhofer was a partner.

---

## 3. Statistics Tools

### Programme Statistics
```
What is the success rate for EIC Accelerator?
```
**Expected**: Returns success rates, funding amounts, and participation statistics.

### Country Statistics
```
How does Germany perform in Horizon Europe?
```
**Expected**: Returns Germany's participation stats, success rates, funding received.

### Cluster Statistics
```
What are the statistics for Cluster 5 (Climate, Energy, Mobility)?
```
**Expected**: Returns cluster-level statistics.

---

## 4. Comparison Tools

### Programme Comparison
```
Compare EIC Accelerator with ERC Starting Grant
```
**Expected**: Side-by-side comparison of success rates, funding, requirements.

### Country Comparison
```
Compare Germany and France participation in Horizon Europe
```
**Expected**: Comparative statistics for both countries.

---

## 5. Document Search (FAQ/Rules)

### Eligibility Questions
```
What are the consortium requirements for RIA projects?
```
**Expected**: Returns rule that minimum 3 entities from 3 different EU/Associated countries are required.

### Budget Rules
```
What is the funding rate for Innovation Actions?
```
**Expected**: Returns that IA projects typically get 70% funding rate (vs 100% for RIA).

### General FAQ
```
Can Switzerland participate in Horizon Europe?
```
**Expected**: Explains Switzerland's Associated Country status and participation rules.

---

## 6. Proposal Support Tools

### Budget Benchmark
```
What's a typical budget for a 36-month RIA project in Cluster 5 with 8 partners?
```
**Expected**: Returns min/max/average budgets, per-partner breakdown, recommendations based on real funded projects.

### Consortium Patterns
```
What does a successful consortium look like for hydrogen research projects?
```
**Expected**: Returns average partners, country distribution, org type mix, successful templates.

### Find Experienced Partners
```
Find organizations with experience in battery technology research
```
**Expected**: Returns organizations with track records in battery research, with project examples.

### Call History Analysis
```
How has funding for AI evolved over the past years in Horizon Europe?
```
**Expected**: Returns funding trends, topic evolution, year-over-year changes.

---

## 7. Proposal Planning Tools

### Budget Calculator
```
Calculate a budget for a 48-month IA project with 12 partners working on green hydrogen
```
**Expected**: Returns detailed budget breakdown by cost category (personnel, equipment, travel, etc.) with cluster-specific recommendations.

### Timeline Generator
```
Generate a project timeline for a 36-month RIA project with 8 partners and 300 person-months
```
**Expected**: Returns work packages, deliverables, milestones with Gantt-style timeline.

---

## 8. Project Discovery Tools

### Similar Projects
```
Find projects similar to SOLARX (or any known project acronym)
```
**Expected**: Returns semantically similar projects based on objectives.

### Collaboration Network
```
Show me the collaboration network for CNRS
```
**Expected**: Returns organizations that frequently partner with CNRS.

### Cluster-Based Search
```
Show me projects in the Health cluster working on cancer research
```
**Expected**: Returns CL1 projects related to cancer.

---

## 9. Conversation Memory & Follow-ups

### Multi-turn Conversation
```
Turn 1: What are open calls for energy research?
Turn 2: Tell me more about the third one
Turn 3: What's the typical budget for that type of call?
```
**Expected**: System remembers context and correctly interprets "the third one" and "that type of call".

### Context Switching
```
Turn 1: Find projects about AI in healthcare
Turn 2: Actually, show me calls instead
Turn 3: Go back to the projects - who coordinated them?
```
**Expected**: Handles topic switches while maintaining conversation coherence.

---

## 10. Complex Multi-Tool Queries

### Analysis Query
```
Why do some countries have higher success rates in Horizon Europe than others?
```
**Expected**: Uses multiple tools (country stats, document search) to provide analysis.

### Comparison + Statistics
```
Compare the success rates and typical budgets between RIA and IA projects in Cluster 4
```
**Expected**: Combines programme statistics and budget benchmarks.

### Multi-Source Query
```
I want to apply for hydrogen funding - what calls are open, what's a typical budget, and who are experienced partners?
```
**Expected**: Agent uses 3+ tools (call search, budget benchmark, partner finder) to answer comprehensively.

---

## 11. Edge Cases & Error Handling

### No Results Query
```
Find calls about underwater basket weaving
```
**Expected**: Gracefully handles no results, suggests alternatives.

### Ambiguous Query
```
Tell me about ERC
```
**Expected**: Provides overview of ERC programme (uses built-in knowledge or document search).

### Specific Call Details
```
Tell me about call HORIZON-CL5-2026-02-D3-08
```
**Expected**: Returns detailed information about the specific call.

---

## 12. Response Formatting Verification

### Call Formatting
Verify that call results include:
- [ ] Clean summary (not raw HTML or verbose scope)
- [ ] Call ID
- [ ] Status with correct icon (🟢 open, 🟡 upcoming, 🔴 closed)
- [ ] Deadline
- [ ] Programme/Cluster
- [ ] Budget (if available)
- [ ] Apply link

### Project Formatting
Verify that project results include:
- [ ] Title and acronym
- [ ] Project ID
- [ ] Programme
- [ ] Status
- [ ] Duration dates
- [ ] EU Contribution
- [ ] Coordinator
- [ ] Objective summary
- [ ] CORDIS link

---

## 13. Performance Checks

### Response Time
- Simple FAQ: < 5 seconds
- Call search: < 10 seconds
- Complex multi-tool query: < 30 seconds

### Result Completeness
- Call searches should return 10+ results when available
- Multiple tool calls should be merged (not just first result)

---

## Quick Smoke Test (5 minutes)

Run these 5 queries to quickly verify core functionality:

1. **Calls**: `What open calls are there for climate research?`
2. **Projects**: `Find projects about artificial intelligence`
3. **FAQ**: `What are the eligibility requirements for Horizon Europe?`
4. **Statistics**: `What's the success rate for EIC?`
5. **Multi-tool**: `I'm planning a hydrogen project - what calls are open and what's a typical budget?`

---

## Bug Fix Verification

### Multiple Tool Results Merge (Fixed 2024-12)
```
What are some open calls about energy?
```
**Verify**:
- Agent reasoning shows multiple tool calls
- Final response includes ALL results merged (not just from first tool call)
- Results are deduplicated by call ID

### Clean Summary Display (Fixed 2024-12)
```
Show me open calls for renewable energy
```
**Verify**:
- Summary field shows clean text (no HTML tags like `<span>`)
- No "Expected Outcome:" prefix noise
- Concise (~250 chars max) readable summary

---

## Data Quality Scripts

### Batch Enrichment & Cleanup Script
Run this script to fix calls with incomplete data:

```bash
# Dry run first to see what would be done
python scripts/batch_enrich_and_cleanup_calls.py --dry-run

# Actually run the enrichment (fetches from EU Portal API)
python scripts/batch_enrich_and_cleanup_calls.py

# With cleanup mode to remove invalid calls
python scripts/batch_enrich_and_cleanup_calls.py --cleanup

# Limit to test with fewer calls
python scripts/batch_enrich_and_cleanup_calls.py --limit 50 --verbose
```

This script will:
1. Identify calls with invalid/incomplete topic codes (e.g., ending with `-`)
2. Enrich calls with missing deadlines, titles, or scope from EU Portal API
3. Optionally remove calls that can't be found in the API (--cleanup)
4. Fix garbled titles from PDF extraction issues

### Existing Enrichment Script
```bash
# Quick enrichment of calls missing data
python scripts/enrich_calls_from_api.py --limit 100
```

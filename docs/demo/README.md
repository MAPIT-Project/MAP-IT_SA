# MAPIT evaluation demo — 9 November 2026

Use this alongside the existing Canva presentation. Aim for **two live questions**;
keep a third ready if time permits. The demo supports a roughly ten-minute speaking
slot and connects opportunity discovery to evidence of possible collaborators.
It is not a new presentation deck.

[Copy-ready question bank](questions.md) · [Recorded fallback results](recorded-results-2026-11-08.md) · [Readiness evidence](readiness-2026-11-08.md)

## Suggested live sequence

| Time | What to do | What to point out |
|---|---|---|
| 0:00–0:30 | Introduce a research manager helping a digital-health SME find opportunities and collaborators. | Frame the tool as support for R&I partnership discovery, not a funding-decision system. |
| 0:30–2:30 | Ask question 1 below. | Concrete topic IDs, links to official sources, action types, and a distinction between direct and broader matches. |
| 2:30–4:30 | Ask question 2. | An organisation is linked to a specific project and recorded role; open one CORDIS source. |
| 4:30–5:30 | If time allows, ask question 3. Otherwise use its recorded result. | Difference between the total topic budget and the expected contribution per project; two-stage deadlines. |
| Remaining time | Return to your presentation and questions. | Explain source verification, data updates and human judgement. |

The last full question-check run took **8–47 seconds per answer** (median 23 seconds).
This is an observation from selected checks, not a performance promise. While an
answer is being prepared, explain the visible tool activity and why a source is
needed. Allow extra time for browser/network conditions.

### 1. Find opportunities — tested through the real HTTPS chat proxy

> Find Horizon Europe calls for artificial intelligence in healthcare in 2027. Give three topic IDs and official source links, distinguishing direct matches from broader opportunities.

Look for TOOL-01-TWO-STAGE, TOOL-04 and TOOL-08. TOOL-08 is a coordination/support
action; do not describe it as a conventional research grant. A broader bridging
opportunity should remain separately labelled. [Recorded result](recorded-results-2026-11-08.md).

### 2. Identify partners using project evidence — tested in English

> Which three Dutch organisations have experience in Horizon Europe projects on AI in healthcare? Cite concrete project IDs, their roles and CORDIS links. Explain the date and scope of your project data.

The checked answer linked Maastricht to AIDAVA, Radboud Universiteit to AISN, and
TU Delft to HarmonicAI. Results can legitimately change order or selection. Show
one project link and role rather than treating a relevance score as proof.

The current snapshot was imported on **8 November 2026**, with source updates
through **7 November**. It has **24,471 projects**, including one existing project
retained outside the 24,470-project export, and **36,202 distinct organisations**
across 151,627 participation records. These are database counts, not user-impact KPIs.

### 3. Inspect a concrete condition — optional, tested in English

> For HORIZON-HLTH-2027-02-TOOL-01-TWO-STAGE, give the first and second deadlines and distinguish the total topic budget from the expected contribution per project. Cite the official document and page.

Open the cited work programme rather than relying only on the generated text.
[Recorded figures and source](recorded-results-2026-11-08.md). The demonstration is
about checking the source; it is not approval of anyone's funding eligibility.

## Other features to show only if useful

- **Proposal drafting:** use the fictional outline question in the question bank.
  This was tested as chat drafting assistance. It does not demonstrate the entire
  separate proposal-editor/session workflow; rehearse that UI separately before
  including it in the live slot.
- **Version-aware document retrieval:** ask which Health work-programme edition is
  used for 2027. Point to the returned version, official URL and page.
- **Limits and missing information:** the invented-call question was tested and
  declined to supply a deadline/budget. This makes a short, useful answer to
  “does it make things up?” without claiming the safeguard catches every error.
- **Language support:** Dutch and English AI/health questions were exercised.
  Use English for the evaluation unless the meeting agrees otherwise.
- **Project/partner evidence:** show the organisation and project, not just a list
  of names. Membership does not establish current availability or a specific
  technical responsibility.

## Answers to likely evaluator questions

**What is the added value?**
“MAPIT connects a research question to calls, source documents and relevant project
experience in a conversational workflow. The demonstration shows that workflow;
we have not established a quantified reduction in workload or higher grant success.”

**Is this your own trained language model?**
“The inspected implementation uses existing language models with a specialised
knowledge base and registered tools. Its domain specialisation comes from retrieval,
data and workflow design. We should not describe this implementation as evidence
that we trained an exclusive small language model.”

**How do you prevent unsupported answers?**
“Important funding facts should be checked against retrieved sources. The current
system returns provenance/version information, exposes source limitations and
replaces an answer when all attempted retrieval failed or returned empty searches.
This is a safeguard, not independent verification of every sentence.”

**How current is the data?**
“Calls, CORDIS projects and documents have separate refresh pipelines. Today's
CORDIS snapshot was imported and verified on 8 November; its newest source record
is dated 7 November. We can show the refresh procedure and audit result. That is
not a claim of instantaneous or exhaustive EU-wide coverage.”

**What did testing prove?**
“Fifteen selected research-question cases produced answers, and we checked specific
behaviours such as citing sources and handling missing information. We also tested
login and streamed chat over HTTPS. This is not a statistical accuracy estimate or
a security certification.”

**What changed between project V1 and V2?**
Use the developments already shown in your presentation and original V1 material.
The repository supports concrete examples of hybrid project search (March 2026),
visible tool progress/result handling (May), and proposal-editor development (June).
Keep these separate from November maintenance, provider changes and data refreshes.
Technical route names “V3/V4” do not define the project's “V2” deliverable.
Do not invent a user-test finding, adoption figure or before/after KPI.

**How does the extra work relate to reported effort?**
Describe the actual functionality and dated evidence. Questions about person-month
allocation, WP2 dates or cost eligibility belong with the project coordinator and
approved project/financial records; a feature demonstration does not establish them.

**What remains?**
“Priorities are broader user-based evaluation, continued source/version maintenance,
review of unresolved documents, and further access/security and UI validation.”

## Rehearse once in the actual presentation browser

1. Sign in with the intended presenter account at `https://new.mapit.work` in a
   fresh browser session. Check any accounts colleagues will use separately.
2. Open a personal conversation, not a collaboration space with unrelated content.
3. Run the first question once, verify streaming/tool progress and open a source link.
4. Keep the question bank, recorded results and one official source in separate tabs.
5. Close private messages, administration screens and credentials before screen sharing.
6. If a response stalls, use the dated recorded result and say it is recorded.
   Do not repeatedly retry in front of the audience or present the fallback as live.

The automated checks covered real HTTP/session/proxy behaviour, but not browser
clicks, visual layout or the particular presenter's account. That short rehearsal
is the remaining hands-on check.

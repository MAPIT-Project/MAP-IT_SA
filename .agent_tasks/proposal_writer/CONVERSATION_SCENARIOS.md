# AI Proposal Writer - Conversation Scenarios

This document outlines conversation scenarios the AI Proposal Writer should handle effectively. These scenarios cover the full user journey from initial proposal creation through submission readiness.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Section Writing](#2-section-writing)
3. [Quality Improvement](#3-quality-improvement)
4. [Score & Feedback](#4-score--feedback)
5. [Gap Analysis](#5-gap-analysis)
6. [Rewriting & Suggestions](#6-rewriting--suggestions)
7. [Learning from Examples](#7-learning-from-examples)
8. [Budget & Timeline](#8-budget--timeline)
9. [Compliance & Requirements](#9-compliance--requirements)
10. [Progress & Achievements](#10-progress--achievements)
11. [Dashboard & Overview](#11-dashboard--overview)
12. [Export & Submission](#12-export--submission)
13. [Error Recovery](#13-error-recovery)
14. [Multi-Turn Conversations](#14-multi-turn-conversations)
15. [Edge Cases](#15-edge-cases)

---

## 1. Getting Started

### 1.1 New User Onboarding
```
User: "I want to write a proposal for Horizon Europe. Where do I start?"

Expected: AI explains the proposal structure, asks about the call/topic,
and guides user through initial setup.
```

### 1.2 Call Selection
```
User: "I found a call about AI in healthcare. The ID is HORIZON-HLTH-2024-TOOL-11-01."

Expected: AI fetches call details, explains requirements, and suggests
which sections to prioritize.
```

### 1.3 Topic Understanding
```
User: "What exactly is this call looking for? I don't understand the technical scope."

Expected: AI analyzes the call text, extracts key requirements, and explains
in plain language what evaluators expect.
```

### 1.4 Proposal Initialization
```
User: "Let's start a new proposal for this call. Our project is about using
machine learning to predict drug interactions."

Expected: AI creates proposal structure, suggests title options, and
identifies relevant funded projects for reference.
```

### 1.5 Returning User
```
User: "I was working on my proposal yesterday. Can we continue?"

Expected: AI retrieves saved progress, shows current status, and suggests
next actions based on where user left off.
```

---

## 2. Section Writing

### 2.1 Generate First Draft - Excellence
```
User: "Write the Excellence section for my proposal about quantum computing
for drug discovery."

Expected: AI generates domain-specific content using call requirements
and similar funded projects as reference.
```

### 2.2 Generate First Draft - Impact
```
User: "Now write the Impact section. Our main stakeholders are pharmaceutical
companies and hospitals."

Expected: AI creates impact pathways, identifies target groups, and
suggests dissemination channels.
```

### 2.3 Generate First Draft - Implementation
```
User: "Generate the Implementation section. We have 5 partners from
Germany, France, Spain, Netherlands, and Italy."

Expected: AI creates work package structure, suggests timeline, and
distributes responsibilities across partners.
```

### 2.4 Partial Section Writing
```
User: "I've written the first paragraph of my objectives. Can you continue
from here?"

Expected: AI reads existing content, maintains style/tone, and continues
writing coherently.
```

### 2.5 Bullet Points to Prose
```
User: "Here are my key points:
- Novel AI algorithm
- 50% faster than state of art
- Validated on 3 datasets
Turn this into a proper paragraph."

Expected: AI expands bullets into well-structured academic prose.
```

### 2.6 Section-Specific Guidance
```
User: "What should go in the 'Methodology' subsection?"

Expected: AI explains expected content, common mistakes to avoid,
and shows examples from funded projects.
```

---

## 3. Quality Improvement

### 3.1 General Improvement Request
```
User: "This section feels weak. How can I make it stronger?"

Expected: AI analyzes content, identifies specific weaknesses, and
provides actionable improvement suggestions.
```

### 3.2 Evaluator Perspective
```
User: "What would an evaluator think of this paragraph?"

Expected: AI simulates evaluator assessment, highlights potential
concerns, and suggests how to address them.
```

### 3.3 Strengthen Specific Aspect
```
User: "The innovation part isn't convincing enough. Help me strengthen it."

Expected: AI identifies why innovation is weak and suggests specific
additions or rewrites.
```

### 3.4 Add Technical Depth
```
User: "Reviewers might think this is too superficial. Add more technical detail."

Expected: AI adds domain-appropriate technical content without
making it inaccessible.
```

### 3.5 Improve Clarity
```
User: "This paragraph is confusing. Make it clearer."

Expected: AI restructures sentences, breaks down complex ideas,
and improves readability.
```

### 3.6 Make More Concise
```
User: "This is too long. Cut it down by 30% without losing key points."

Expected: AI identifies redundancies, tightens prose, and maintains
essential information.
```

---

## 4. Score & Feedback

### 4.1 Quick Score Check
```
User: "What's my current score for this section?"

Expected: AI provides quick heuristic score with brief explanation.
```

### 4.2 Detailed Evaluation
```
User: "Give me a detailed evaluation of my Excellence section."

Expected: AI provides criterion-by-criterion breakdown with scores,
confidence levels, and specific feedback.
```

### 4.3 Score Comparison
```
User: "How does my score compare to the funding threshold?"

Expected: AI shows current score vs. threshold (3.0), explains gap,
and prioritizes improvements needed.
```

### 4.4 Track Improvement
```
User: "Has my score improved since the last version?"

Expected: AI shows score history, highlights improvements, and
identifies remaining issues.
```

### 4.5 Predict Final Score
```
User: "If I submit now, what score would I likely get?"

Expected: AI provides predicted overall score with confidence interval
and key factors affecting it.
```

### 4.6 Score Explanation
```
User: "Why did I only get 3.2? I thought this was good."

Expected: AI explains specific scoring criteria, shows where points
were lost, and provides examples of 4.0+ content.
```

### 4.7 Real-Time Feedback While Writing
```
User: [Types content in editor]

Expected: AI provides streaming feedback - suggestion counts, quick
scores, quality tier updates as user types.
```

---

## 5. Gap Analysis

### 5.1 Identify All Gaps
```
User: "What's missing from my proposal?"

Expected: AI analyzes against call requirements and evaluation criteria,
lists all gaps with severity ratings.
```

### 5.2 Critical Gaps Only
```
User: "What are the most critical things I need to fix?"

Expected: AI prioritizes gaps by impact on score, shows blocking
issues first.
```

### 5.3 Gap in Specific Area
```
User: "Is there anything missing in my methodology description?"

Expected: AI checks methodology against expected content and
identifies specific gaps.
```

### 5.4 Compare to Requirements
```
User: "Does my proposal address all the call requirements?"

Expected: AI maps proposal content to call requirements, shows
coverage percentage and missing items.
```

### 5.5 Gap Resolution Guidance
```
User: "How do I fix the gap about 'clear KPIs'?"

Expected: AI explains what KPIs are expected, provides examples,
and suggests specific additions.
```

### 5.6 Verify Gap Closure
```
User: "I added the risk assessment. Is the gap closed now?"

Expected: AI re-evaluates content, confirms if gap is addressed,
or explains what's still missing.
```

---

## 6. Rewriting & Suggestions

### 6.1 Full Section Rewrite
```
User: "Rewrite this entire section to be more compelling."

Expected: AI provides complete rewrite with tracked changes or
side-by-side comparison.
```

### 6.2 Paragraph Rewrite Options
```
User: "Give me 3 different ways to rewrite this paragraph."

Expected: AI provides multiple rewrite options with different
approaches (concise, detailed, persuasive).
```

### 6.3 Inline Suggestions
```
User: "Show me suggestions for improving this text inline."

Expected: AI provides Grammarly-style suggestions - insertions,
deletions, replacements with explanations.
```

### 6.4 Accept/Reject Suggestions
```
User: "Apply suggestion 2 but not the others."

Expected: AI applies selected suggestion and updates content.
```

### 6.5 Style Matching
```
User: "Rewrite this to match the style of my other sections."

Expected: AI analyzes existing sections and rewrites to match
tone, formality, and structure.
```

### 6.6 Targeted Rewrite
```
User: "Rewrite just the innovation claims to be more specific."

Expected: AI identifies innovation claims and rewrites only those
portions with concrete details.
```

---

## 7. Learning from Examples

### 7.1 Find Similar Projects
```
User: "Show me funded projects similar to mine."

Expected: AI finds semantically similar CORDIS projects, shows
relevance scores and key similarities.
```

### 7.2 Learn from Successful Proposal
```
User: "What can I learn from how project EXAMPLE-123 wrote their Excellence section?"

Expected: AI analyzes successful project's approach and suggests
applicable techniques.
```

### 7.3 Benchmark Against Funded Projects
```
User: "How does my proposal compare to funded projects in this area?"

Expected: AI compares content, structure, and approach to successful
projects, highlights differences.
```

### 7.4 Copy Successful Patterns
```
User: "Use a similar structure to what worked for funded AI projects."

Expected: AI identifies common structural patterns in successful
proposals and applies them.
```

### 7.5 Topic-Specific Examples
```
User: "Show me how other proposals described their consortium for digital health."

Expected: AI retrieves relevant consortium descriptions from
similar funded projects.
```

### 7.6 Budget Benchmarking
```
User: "Is my budget realistic compared to similar funded projects?"

Expected: AI compares budget breakdown to projects with similar
scope, action type, and consortium size.
```

---

## 8. Budget & Timeline

### 8.1 Generate Budget
```
User: "Create a budget for a 4-year RIA project with 8 partners
requesting €5M total."

Expected: AI generates detailed budget breakdown following HE rules,
distributed appropriately across partners.
```

### 8.2 Budget Validation
```
User: "Is my budget compliant with Horizon Europe rules?"

Expected: AI checks against HE financial rules, flags issues
(overhead rates, equipment limits, etc.).
```

### 8.3 Budget Optimization
```
User: "How can I optimize the budget distribution?"

Expected: AI suggests reallocation based on work package activities
and partner capabilities.
```

### 8.4 Generate Timeline
```
User: "Create a project timeline with work packages and milestones."

Expected: AI generates Gantt chart data, WP descriptions,
deliverables, and milestone schedule.
```

### 8.5 Timeline Validation
```
User: "Is my timeline realistic for the proposed activities?"

Expected: AI checks task dependencies, duration reasonability,
and resource allocation.
```

### 8.6 Partner-Specific Budget
```
User: "What should Partner 3's budget look like? They're a university
doing WP2 and WP4."

Expected: AI generates partner-specific budget based on their
role and activities.
```

---

## 9. Compliance & Requirements

### 9.1 Check Overall Compliance
```
User: "Is my proposal compliant with all requirements?"

Expected: AI runs full compliance check against call requirements,
eligibility, and format rules.
```

### 9.2 Consortium Eligibility
```
User: "Is our consortium eligible? We have partners from Germany,
Switzerland, and UK."

Expected: AI checks country eligibility, minimum partner requirements,
and associated country rules.
```

### 9.3 Format Compliance
```
User: "Does my proposal meet the page limits and formatting requirements?"

Expected: AI checks page counts, font sizes, section lengths against
template requirements.
```

### 9.4 Missing Mandatory Elements
```
User: "What mandatory elements am I missing?"

Expected: AI lists all required elements (ethics, gender, open science)
and their status.
```

### 9.5 Fix Compliance Issue
```
User: "Help me fix the ethics section to be compliant."

Expected: AI explains requirements and helps write compliant
ethics self-assessment.
```

### 9.6 Pre-Submission Checklist
```
User: "Give me a final checklist before submission."

Expected: AI provides comprehensive pre-submission checklist
with pass/fail status for each item.
```

---

## 10. Progress & Achievements

### 10.1 Check Progress
```
User: "How far along is my proposal?"

Expected: AI shows completion percentage, sections status,
and estimated work remaining.
```

### 10.2 View Achievements
```
User: "What achievements have I earned?"

Expected: AI shows earned achievements with points, and
upcoming achievements close to unlocking.
```

### 10.3 View Streak
```
User: "What's my writing streak?"

Expected: AI shows current streak, longest streak, and
encouragement to maintain it.
```

### 10.4 Leaderboard
```
User: "How do I compare to other proposal writers?"

Expected: AI shows anonymized leaderboard position based
on achievements and points.
```

### 10.5 Motivation
```
User: "I'm feeling stuck. Give me some motivation."

Expected: AI shows progress made, recent improvements,
upcoming milestones, and encouragement.
```

### 10.6 Session Summary
```
User: "What did I accomplish today?"

Expected: AI summarizes session activity - words written,
score improvements, gaps closed, achievements earned.
```

---

## 11. Dashboard & Overview

### 11.1 Full Dashboard
```
User: "Show me my proposal dashboard."

Expected: AI displays comprehensive dashboard with all sections,
scores, actions, and readiness status.
```

### 11.2 Quick Summary
```
User: "Give me a quick status update."

Expected: AI provides brief summary - overall completion,
average score, critical issues count.
```

### 11.3 Next Actions
```
User: "What should I work on next?"

Expected: AI prioritizes next actions based on impact,
showing estimated time and benefit.
```

### 11.4 Submission Readiness
```
User: "Am I ready to submit?"

Expected: AI runs readiness checks, shows blocking vs.
non-blocking issues, and funding probability.
```

### 11.5 Section Comparison
```
User: "Which section needs the most work?"

Expected: AI compares all sections by score, gaps, and
improvement potential.
```

### 11.6 Time to Deadline
```
User: "How much time do I have left?"

Expected: AI shows time until deadline, estimated work
remaining, and feasibility assessment.
```

---

## 12. Export & Submission

### 12.1 Export to Word
```
User: "Export my proposal to Word format."

Expected: AI generates properly formatted Word document
following HE template.
```

### 12.2 Export Budget to Excel
```
User: "Export my budget to Excel."

Expected: AI generates Excel spreadsheet with proper
formatting and formulas.
```

### 12.3 Export Full Package
```
User: "Create a complete submission package."

Expected: AI generates ZIP with all required documents
(Part A, Part B, annexes).
```

### 12.4 Final Review Mode
```
User: "Enter final review mode before submission."

Expected: AI performs comprehensive final check and
highlights any last-minute issues.
```

### 12.5 Version Comparison
```
User: "Compare my current version to last week's version."

Expected: AI shows tracked changes, score improvements,
and modifications summary.
```

### 12.6 Submission Confirmation
```
User: "I just submitted. What happens now?"

Expected: AI confirms export, provides timeline expectations,
and suggests next steps (ethics, negotiations).
```

---

## 13. Error Recovery

### 13.1 Unclear Request
```
User: "Make it better."

Expected: AI asks clarifying questions - which section?
what aspect? what's the goal?
```

### 13.2 Invalid Input
```
User: "Score: asdf1234"

Expected: AI handles gracefully, explains expected format,
asks for valid input.
```

### 13.3 Missing Context
```
User: "Continue writing."

Expected: AI asks which section, or retrieves last active
section from context.
```

### 13.4 Conflicting Instructions
```
User: "Make it shorter but add more detail about the methodology."

Expected: AI addresses conflict, suggests prioritization,
or asks which is more important.
```

### 13.5 Out of Scope Request
```
User: "Write my PhD thesis introduction."

Expected: AI politely explains scope limitation and
redirects to proposal-related tasks.
```

### 13.6 System Error Recovery
```
User: [After a timeout or error]
"What happened? Did I lose my work?"

Expected: AI reassures about auto-save, shows last saved
state, and allows continuation.
```

---

## 14. Multi-Turn Conversations

### 14.1 Iterative Refinement
```
Turn 1 - User: "Write an objectives section."
Turn 2 - User: "Make the first objective more specific."
Turn 3 - User: "Add a fourth objective about sustainability."
Turn 4 - User: "Now score this section."

Expected: AI maintains context across turns, applies
incremental changes correctly.
```

### 14.2 Topic Switching
```
Turn 1 - User: "Help with Excellence section."
Turn 2 - User: "Actually, let's work on the budget first."
Turn 3 - User: "OK back to Excellence now."

Expected: AI handles topic switches, maintains state
for both topics.
```

### 14.3 Reference Previous Content
```
User: "Use the same style as the paragraph I wrote yesterday
about consortium composition."

Expected: AI retrieves previous content, analyzes style,
and applies it.
```

### 14.4 Comparison Across Versions
```
Turn 1 - User: "Score my methodology."
Turn 2 - User: "Rewrite it."
Turn 3 - User: "Score it again. Did it improve?"

Expected: AI tracks before/after scores and explains changes.
```

### 14.5 Building on Feedback
```
Turn 1 - AI: "Your innovation claims are too vague."
Turn 2 - User: "I added more detail. Check again."
Turn 3 - AI: "Better, but still missing quantitative evidence."
Turn 4 - User: "Added numbers. How about now?"

Expected: AI provides consistent, progressive feedback.
```

### 14.6 Long Session Continuity
```
[After 50+ turns in a session]
User: "What did we decide about the dissemination strategy?"

Expected: AI recalls earlier decisions and summarizes
key points from the conversation.
```

---

## 15. Edge Cases

### 15.1 Empty Section
```
User: "Score my Impact section." [Section is empty]

Expected: AI handles gracefully, explains section needs
content before scoring.
```

### 15.2 Very Long Content
```
User: [Pastes 10,000 words] "Evaluate this."

Expected: AI handles large content, possibly processes
in chunks, provides complete feedback.
```

### 15.3 Non-English Content
```
User: "Voici mon résumé du projet..." [French text]

Expected: AI either processes in original language or
asks user to provide English version.
```

### 15.4 Highly Technical Content
```
User: [Pastes quantum physics equations and jargon]

Expected: AI acknowledges technical depth, evaluates
structure and clarity without domain expertise claims.
```

### 15.5 Copy-Pasted Requirements
```
User: [Pastes entire call text] "Write a proposal for this."

Expected: AI extracts key requirements, asks clarifying
questions about user's project, then generates content.
```

### 15.6 Contradictory Feedback Request
```
User: "My supervisor said add more theory, but you said
be more practical. What should I do?"

Expected: AI explains trade-offs, suggests balanced
approach, offers both versions.
```

### 15.7 Last-Minute Panic
```
User: "Deadline is in 2 hours! What are the most critical
things to fix?"

Expected: AI immediately prioritizes critical blocking
issues, provides rapid fixes, skips nice-to-haves.
```

### 15.8 Multiple Proposals
```
User: "I'm working on two proposals. Switch to the climate one."

Expected: AI switches context to correct proposal,
confirms switch with user.
```

### 15.9 Partial Information
```
User: "Our partner in Spain will do something related to
testing, I think around 200k budget."

Expected: AI works with vague info, creates placeholder,
marks for later refinement.
```

### 15.10 Rejected Suggestion
```
User: "I don't like your rewrite. Keep my original version."

Expected: AI accepts feedback, reverts change, asks what
specifically they didn't like for future suggestions.
```

---

## Implementation Priority

### High Priority (Core Functionality)
- Section writing (2.1-2.4)
- Quality scoring (4.1-4.3)
- Gap analysis (5.1-5.3)
- Basic rewriting (6.1-6.3)
- Compliance checking (9.1-9.4)

### Medium Priority (Enhanced Experience)
- Learning from examples (7.1-7.4)
- Budget/timeline generation (8.1-8.5)
- Progress tracking (10.1-10.3)
- Dashboard (11.1-11.4)
- Multi-turn conversations (14.1-14.4)

### Lower Priority (Polish)
- Achievements/gamification (10.4-10.6)
- Advanced export (12.3-12.5)
- Edge cases (15.1-15.10)
- Error recovery refinement (13.1-13.6)

---

## Testing Notes

Each scenario should be tested for:
1. **Accuracy** - Does the AI provide correct information?
2. **Relevance** - Is the response relevant to the request?
3. **Completeness** - Does it fully address the user's need?
4. **Tone** - Is the response appropriately professional?
5. **Actionability** - Can the user act on the response?
6. **Context Awareness** - Does it use available context?
7. **Error Handling** - Does it fail gracefully?
8. **Performance** - Does it respond in reasonable time?

---

*Last Updated: December 5, 2025*

# AI Proposal Writer - Production-Ready Improvement Plan

> **Created:** December 4, 2025
> **Status:** Planning
> **Priority:** High
> **Estimated Total Effort:** 4-6 weeks

---

## Executive Summary

Transform the existing AI Proposal Writer from a functional prototype into a production-ready, market-differentiating feature. The system currently has solid infrastructure but critical gaps that prevent it from being truly useful.

---

## Current State Assessment

### What Works Well
| Component | Status | Notes |
|-----------|--------|-------|
| Budget Assistant | ✅ Production Ready | Accurate HE rules, good calculations |
| Timeline Generator | ✅ Production Ready | Comprehensive WP/deliverable templates |
| Compliance Checker | ✅ Production Ready | Good coverage of mandatory requirements |
| Document Exporter | ✅ Production Ready | Word/Excel/ZIP exports work |
| Database Schema | ✅ Production Ready | Well-designed with triggers/views (14 tables) |
| API Endpoints | ⚠️ Mostly Ready | 20+ endpoints, minor issues |

### What Needs Work
| Component | Status | Critical Issue |
|-----------|--------|----------------|
| Draft Generator | ❌ Domain-locked | Hardcoded to cybersecurity |
| Quality Improver | ❌ Too Basic | Heuristics only, no AI |
| Criteria Matcher | ❌ Fragile | Regex parsing of LLM outputs |
| Template Service | ⚠️ Basic | No call-specific intelligence |
| Proposal Examples | ❌ Unused | Table exists but empty |
| Learning System | ❌ Missing | 13,865 projects sit unused |

---

## The Vision

### Before (Current State)
```
User: "Generate Excellence section"
System: *Generates generic cybersecurity content*
System: "Consider adding TRL information"
User: *Manually rewrites everything*
```

### After (Target State)
```
User: "Generate Excellence section"
System: *Analyzes call, extracts specific topic/cluster*
System: *Finds 5 similar funded projects*
System: *Generates context-aware draft based on call + examples*
System: "Predicted score: 3.8/5. To reach 4.5, here are 3 rewrites..."
System: *Shows actual rewritten versions with before/after*
User: *Accepts rewrite, moves to next section*
```

---

## Implementation Phases & Tasks

### Phase 0: Foundation Fixes (P0) ✅ COMPLETE
**Goal:** Remove blockers that prevent production use
**Estimated Effort:** 2 weeks

| Task | File | Status | Effort |
|------|------|--------|--------|
| [01 - Remove Domain Lock-in](./01_REMOVE_DOMAIN_LOCKIN.md) | Dynamic topic extraction | ✅ Complete | 4-6h |
| [02 - Structured LLM Outputs](./02_STRUCTURED_LLM_OUTPUTS.md) | JSON mode, schemas | ✅ Complete | 3-4h |
| [03 - Multi-Provider AI](./03_MULTI_PROVIDER_AI.md) | Fallback providers | ✅ Complete | 3-4h |
| [04 - Error Handling](./04_ERROR_HANDLING.md) | Retry, exceptions | ✅ Complete | 3-4h |

### Phase 1: Learning from Success (P1) ✅ COMPLETE
**Goal:** Leverage 13,865 funded CORDIS projects
**Estimated Effort:** 1.5 weeks

| Task | File | Status | Effort |
|------|------|--------|--------|
| [05 - Learning Service](./05_LEARNING_SERVICE.md) | Similar projects, patterns | ✅ Complete | 6-8h |
| 06 - Populate Examples | Extract from CORDIS | ✅ Complete | 4-6h |
| 07 - Semantic Benchmarking | Compare to funded | ✅ Complete | 4-6h |

### Phase 2: Evaluator Simulation (P1) ✅ COMPLETE
**Goal:** Predict what evaluators will think
**Estimated Effort:** 1 week

| Task | File | Status | Effort |
|------|------|--------|--------|
| [08 - Evaluator Simulator](./08_EVALUATOR_SIMULATOR.md) | Score prediction | ✅ Complete | 6-8h |
| 09 - Score Integration | Connect to UI | ✅ Complete | 3-4h |
| 10 - Gap Analysis | Path to threshold | ✅ Complete | 3-4h |

### Phase 3: Smart Rewriting (P1) ✅ COMPLETE
**Goal:** Provide actual rewrites, not just suggestions
**Estimated Effort:** 1 week

| Task | File | Status | Effort |
|------|------|--------|--------|
| [11 - Smart Rewriter](./11_SMART_REWRITER.md) | Multiple options | ✅ Complete | 6-8h |
| 12 - Rewrite Options | UI integration | ✅ Complete | 4-6h |
| 13 - Inline Suggestions | Grammarly-style | ✅ Complete | 6-8h |

### Phase 4: User Experience (P2) ✅ COMPLETE
**Goal:** Delight users with real-time feedback
**Estimated Effort:** 1 week

| Task | File | Status | Effort |
|------|------|--------|--------|
| 14 - Streaming Feedback | Real-time quality | ✅ Complete | 4-6h |
| 15 - Progress Tracking | Achievements | ✅ Complete | 4-6h |
| 16 - Proposal Dashboard | Overview UI | ✅ Complete | 6-8h |

---

## Priority Order

### Must Do (P0) - Production Blockers
1. **Task 01**: Remove cybersecurity lock-in
2. **Task 02**: Structured LLM outputs
3. **Task 03**: Multi-provider fallback
4. **Task 04**: Error handling

### Should Do (P1) - Core Value
5. **Task 05**: Learning service (similar projects)
6. **Task 08**: Evaluator simulator (score prediction)
7. **Task 11**: Smart rewriter (actual rewrites)

### Nice to Have (P2) - Delight
8. Rest of Phase 1-3
9. All of Phase 4

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Domain coverage | 1 (cybersecurity) | All HE clusters (9+) |
| Score prediction accuracy | N/A | ±0.5 of actual |
| Draft acceptance rate | Low (~20%) | 60%+ |
| Time to complete section | Manual (hours) | 50% reduction |
| User satisfaction | Unknown | 4.5/5 |

---

## Key New Services

| Service | Purpose | Priority |
|---------|---------|----------|
| `CallUnderstandingService` | Dynamic call analysis | P0 |
| `ProposalAIService` | Multi-provider AI | P0 |
| `ProposalLearningService` | Learn from CORDIS | P1 |
| `EvaluatorSimulator` | Predict scores | P1 |
| `SmartRewriter` | Actual rewrites | P1 |

---

## Database Changes Needed

```sql
-- Add embeddings to proposal_sections for semantic comparison
ALTER TABLE proposal_sections
ADD COLUMN section_embedding vector(768);

-- Add predicted scores
ALTER TABLE proposal_sections
ADD COLUMN predicted_evaluator_score DECIMAL(2,1),
ADD COLUMN score_confidence DECIMAL(3,2),
ADD COLUMN last_evaluated_at TIMESTAMP;

-- Enhance proposal_examples with embeddings
ALTER TABLE proposal_examples
ADD COLUMN example_embedding vector(768),
ADD COLUMN cluster VARCHAR(50),
ADD COLUMN action_type VARCHAR(20);
```

---

## File Structure

```
.agent_tasks/proposal_writer/
├── 00_OVERVIEW.md                    # This file
├── 01_REMOVE_DOMAIN_LOCKIN.md        # ✅ Created
├── 02_STRUCTURED_LLM_OUTPUTS.md      # ✅ Created
├── 03_MULTI_PROVIDER_AI.md           # ✅ Created
├── 04_ERROR_HANDLING.md              # ✅ Created
├── 05_LEARNING_SERVICE.md            # ✅ Created
├── 06_POPULATE_EXAMPLES.md           # ✅ Created
├── 07_SEMANTIC_BENCHMARKING.md       # ✅ Created
├── 08_EVALUATOR_SIMULATOR.md         # ✅ Created
├── 09_SCORE_INTEGRATION.md           # ✅ Created
├── 10_GAP_ANALYSIS.md                # ✅ Created
├── 11_SMART_REWRITER.md              # ✅ Created
├── 12_REWRITE_OPTIONS.md             # ✅ Created
├── 13_INLINE_SUGGESTIONS.md          # ✅ Created
├── 14_STREAMING_FEEDBACK.md          # ✅ Created
├── 15_PROGRESS_TRACKING.md           # ✅ Created
└── 16_PROPOSAL_DASHBOARD.md          # ✅ Created
```

---

## Dependencies

### Existing Infrastructure (Ready to Use)
- PostgreSQL with pgvector (13,865 projects with embeddings)
- Neo4j graph database
- Redis for caching
- Gemini API configured
- Supabase for documents

### New Dependencies Needed
- Gemini JSON mode (already supported)
- OpenAI API key (for fallback) - optional
- Additional database migrations

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM costs increase | Medium | Medium | Caching, smaller models |
| Score prediction inaccurate | Medium | High | Calibrate with real data |
| User adoption low | Low | High | Focus on UX |
| API rate limits | Medium | Medium | Multi-provider fallback |

---

## Getting Started

1. **Read the overview** (this file)
2. **Start with Phase 0** - These are blockers
3. **Task 01 first** - Removes domain lock-in
4. **Each task has detailed implementation steps**
5. **Track progress** in this overview

---

## Related Files

### Existing Proposal Services
- `app/services/proposal_writing/draft_generator.py`
- `app/services/proposal_writing/quality_improver.py`
- `app/services/proposal_writing/criteria_matcher.py`
- `app/services/proposal_writing/compliance_checker.py`
- `app/services/proposal_writing/budget_assistant.py`
- `app/services/proposal_writing/template_service.py`

### API Routes
- `app/api/proposal_routes.py`
- `app/api/proposal_document_routes.py`

### Tools
- `app/services/tools/budget_calculator.py`
- `app/services/tools/timeline_generator.py`
- `app/services/tools/budget_benchmark.py`

### Database
- `migration/005_proposal_writing_system.sql`

---

## Notes

- All tasks include detailed code examples
- Each task is designed to be completed independently
- Estimated efforts are for a single developer
- Tasks can be parallelized across Phase 0

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-04 | Initial plan created |
| 2025-12-04 | Tasks 01-05, 08, 11 detailed |
| 2025-12-04 | Phase 0 (Tasks 01-04) completed |
| 2025-12-04 | Phase 1 (Tasks 05-07) completed |
| 2025-12-04 | Phase 2 (Tasks 08-10) completed - Evaluator Simulator, Score Storage, Gap Analysis |
| 2025-12-04 | Phase 3 (Tasks 11-13) completed - Smart Rewriter, Rewrite Options, Inline Suggestions |
| 2025-12-04 | Phase 4 (Tasks 14-16) completed - Streaming Feedback, Progress Tracking, Dashboard |

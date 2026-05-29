# MAPIT Documentation Structure

> **Last Updated:** May 13, 2026
> **Status:** V3/V4 Architecture

## 📁 Documentation Organization

### Root Documentation
- **`CLAUDE.md`** (root) - **Primary developer guide**
  - Quick start for developers
  - Project overview, commands, architecture
  - 42 tools reference
  - Testing patterns

### docs_tracked/ - Single Source of Truth
All up-to-date, comprehensive documentation is maintained in `docs_tracked/`:

**Core Architecture:**
- `SYSTEM_ARCHITECTURE.md` (84K) - Complete system architecture
  - V3/V4 architecture overview
  - All 42 tools documented
  - Data sources and services
  - Example flows and patterns

**Stability & Testing:**
- `CONVERSATION_STABILITY_ARCHITECTURE.md` - Race condition prevention
- `MANUAL_TEST_SCENARIOS.md` - Testing procedures
- `IMPROVEMENT_ROADMAP.md` - Future improvements

**Frontend Integration:**
- `FRONTEND_STREAMING_V3_SPEC.md` - V3 streaming API
- `PROPOSAL_WRITER_FRONTEND_INTEGRATION.md` - Proposal writing UI
- `FRONTEND_INTEGRATION_PROMPT.md` - Frontend development guide

**Data & Questions:**
- `EU_PROGRAMME_DATA_DOWNLOADS.md` - Data source documentation
- `QUESTION_CATEGORIES.md` - Query type reference
- `example_questions.md` - Sample questions by category
- `ENHANCED_HORIZON_QUESTIONS_CAPABILITIES.md` - Advanced queries

**Infrastructure:**
- `README_CELERY.md` - Celery task queue documentation

### docs/ - Active PRDs & Implementation History

**`docs/prd/`** - Product Requirements Documents (Active)
- `MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD_V3.md` - Quality validation (latest)
- `MAPIT_MULTI_PROGRAMME_EXCELLENCE_PRD.md` - Multi-programme support
- `MAPIT_CONVERSATION_STABILITY_PRD.md` - Conversation stability
- `MAPIT_V3_RESPONSE_FORMATTER_PRD.md` - V3 response formatting
- `MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md` - Quality improvements
- `MAPIT_ADVANCED_CONVERSATION_FLOWS_PRD.md` - Advanced flows
- `MAPIT_STABILITY_PRD.md` - System stability
- `MAPIT_QUALITY_PRD.md` - Quality standards
- `MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD.md` - Original validation PRD

**`docs/implementation/`** - Implementation History (Erasmus+)
- `PHASE_1_ERASMUS_DOCUMENT_INGESTION.md` - Document ingestion
- `PHASE_2_ERASMUS_API_SYNC.md` - API synchronization
- `PHASE_3_ERASMUS_TOOLS.md` - Tool implementation
- `PHASE_4_ERASMUS_TEMPLATES.md` - Template system

## 🔍 Quick Reference

| Need | Location |
|------|----------|
| **Quick start** | `CLAUDE.md` (root) |
| **Full architecture** | `docs_tracked/SYSTEM_ARCHITECTURE.md` |
| **Tool reference** | `CLAUDE.md` or `docs_tracked/SYSTEM_ARCHITECTURE.md` |
| **Frontend integration** | `docs_tracked/FRONTEND_STREAMING_V3_SPEC.md` |
| **Testing** | `docs_tracked/MANUAL_TEST_SCENARIOS.md` |
| **Active features** | `docs/prd/*.md` |
| **Implementation history** | `docs/implementation/*.md` |

## 📊 Statistics

| Location | Files | Lines | Purpose |
|----------|-------|-------|---------|
| Root (`CLAUDE.md`) | 1 | 1,145 | Developer quick reference |
| `docs_tracked/` | 12 | ~5,000 | Comprehensive documentation |
| `docs/prd/` | 9 | ~2,900 | Active PRDs |
| `docs/implementation/` | 4 | ~1,000 | Implementation history |

## ✅ Maintenance Guidelines

### When updating documentation:
1. **Update `docs_tracked/` first** - Single source of truth
2. **Update `CLAUDE.md`** - If it affects developer workflows
3. **Create PRD in `docs/prd/`** - For new features
4. **Document implementation** - Add to `docs/implementation/` for major features

### What goes where:
- **`docs_tracked/`**: Finished, stable documentation
- **`docs/prd/`**: Active product requirements and specifications
- **`docs/implementation/`**: Historical implementation records
- **Root**: Only `CLAUDE.md` for developer onboarding

## 🗂️ Removed Redundancy

The following files were **consolidated into `docs_tracked/`**:
- ❌ `docs/STREAMING_FRONTEND_INTEGRATION.md` → See `docs_tracked/FRONTEND_STREAMING_V3_SPEC.md`
- ❌ `docs/technical_specification.md` + `technical_specification_part2.md` → See `docs_tracked/SYSTEM_ARCHITECTURE.md`
- ❌ `docs/AI_CAPABILITIES.md` → See `docs_tracked/SYSTEM_ARCHITECTURE.md`
- ❌ `docs/SYSTEM_USE_CASES_BPMN.md` → See `docs_tracked/SYSTEM_ARCHITECTURE.md`

**Moved to `docs_tracked/`:**
- ✅ `CONVERSATION_STABILITY_ARCHITECTURE.md`
- ✅ `EU_PROGRAMME_DATA_DOWNLOADS.md`
- ✅ `README_CELERY.md`

---

**Result:** Clean, organized documentation structure with no redundancy and clear ownership! 🎉

# MAPIT AI - Improvement Roadmap

**Version:** 1.0
**Created:** December 2024
**Status:** Active Development

## Current State Assessment

### Implemented Features
- [x] Basic RAG engine with Mistral LLM integration
- [x] CORDIS project data loading from CSV
- [x] Dgraph graph database integration
- [x] Simple Flask web chat interface
- [x] Semantic similarity search using sentence transformers
- [x] Topic-based project relationships
- [x] Conversation history tracking
- [x] CORDIS bulk data extraction API wrapper

### Gaps Identified
- [ ] No proposal writer functionality
- [ ] No consortium finder functionality
- [ ] Keyword search marked as TODO
- [ ] Minimal test coverage (~2%)
- [ ] Limited EU program support (only partial Horizon Europe)
- [ ] No error handling/logging framework
- [ ] No input validation
- [ ] No authentication/authorization
- [ ] No caching strategy
- [ ] No API rate limiting

---

## Priority 1: Core Functionality and Production Readiness

### 1.1 Complete Keyword Search Implementation
**Status:** Not Started
**Impact:** High
**Effort:** Medium

The `get_CORDIS_keywords()` method in CORDISRetriever.py is marked as TODO. This is a critical feature for accurate project retrieval.

**Tasks:**
- [ ] Implement keyword extraction from queries
- [ ] Add keyword-based Dgraph queries
- [ ] Integrate with existing similarity search
- [ ] Add fallback when semantic search fails

### 1.2 Implement Comprehensive Error Handling
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] Create custom exception hierarchy
- [ ] Add try-except blocks around all external API calls
- [ ] Implement exponential backoff for API retries
- [ ] Add user-friendly error messages
- [ ] Create error logging with proper context

### 1.3 Add Structured Logging
**Status:** Not Started
**Impact:** High
**Effort:** Low

**Tasks:**
- [ ] Configure Python logging framework
- [ ] Add log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Log all API calls with timing
- [ ] Log user queries (anonymized)
- [ ] Add request correlation IDs

### 1.4 Input Validation and Sanitization
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] Validate all user inputs
- [ ] Sanitize queries before database operations
- [ ] Limit query length
- [ ] Add rate limiting per session
- [ ] Validate file uploads (if applicable)

### 1.5 API Robustness
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] Implement retry logic with exponential backoff
- [ ] Add circuit breaker pattern for external APIs
- [ ] Create fallback LLM providers (OpenAI, Gemini)
- [ ] Add timeout handling
- [ ] Implement request queuing for burst traffic

---

## Priority 2: Program Expansion

### 2.1 Comprehensive Horizon Europe Support
**Status:** Partial
**Impact:** High
**Effort:** High

**Current:** ~500 topic mappings, primarily EIT and MSCA programs

**Tasks:**
- [ ] Add all Horizon Europe Pillars:
  - [ ] Pillar I: Excellent Science (ERC, MSCA, Research Infrastructures)
  - [ ] Pillar II: Global Challenges (6 Clusters)
  - [ ] Pillar III: Innovative Europe (EIC, EIT)
- [ ] Add accurate call deadlines and requirements
- [ ] Add budget information per program
- [ ] Add eligibility criteria

### 2.2 Erasmus+ Program Support
**Status:** Not Started
**Impact:** High
**Effort:** High

**Tasks:**
- [ ] Add Key Action 1: Learning Mobility
- [ ] Add Key Action 2: Cooperation Partnerships
- [ ] Add Key Action 3: Policy Reform Support
- [ ] Add Jean Monnet Activities
- [ ] Add Sport Actions
- [ ] Include deadlines and funding rates

### 2.3 Digital Europe Programme (DEP)
**Status:** Not Started
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Add supercomputing topics
- [ ] Add AI and cybersecurity calls
- [ ] Add digital skills topics
- [ ] Add data spaces topics
- [ ] Include SME-specific calls

### 2.4 Creative Europe
**Status:** Not Started
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Add MEDIA sub-programme
- [ ] Add Culture sub-programme
- [ ] Add Cross-Sectoral strand
- [ ] Include co-production opportunities

### 2.5 LIFE Programme
**Status:** Not Started
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Add Nature and Biodiversity
- [ ] Add Circular Economy
- [ ] Add Climate Mitigation and Adaptation
- [ ] Add Clean Energy Transition

### 2.6 Other EU Programs
**Status:** Not Started
**Impact:** Low-Medium
**Effort:** Variable

**Programs to consider:**
- [ ] Interreg (cross-border cooperation)
- [ ] COST Actions
- [ ] European Defence Fund
- [ ] CEF (Connecting Europe Facility)
- [ ] InvestEU

---

## Priority 3: Feature Enhancement

### 3.1 Proposal Writer Module
**Status:** Not Started
**Impact:** Very High
**Effort:** Very High

This is a flagship feature that would differentiate MAPIT from competitors.

**Tasks:**
- [ ] Design proposal structure templates per program
- [ ] Implement section-by-section generation:
  - [ ] Excellence/Quality section
  - [ ] Impact section
  - [ ] Implementation section
  - [ ] Consortium description
  - [ ] Budget justification
- [ ] Add proposal quality scoring
- [ ] Implement iterative refinement
- [ ] Add export to DOCX/PDF

### 3.2 Consortium Finder
**Status:** Not Started
**Impact:** Very High
**Effort:** High

**Tasks:**
- [ ] Build partner database from CORDIS data
- [ ] Implement organization profiles:
  - [ ] Expertise areas
  - [ ] Previous project participation
  - [ ] Geographic location
  - [ ] Organization type (university, SME, etc.)
- [ ] Partner matching algorithm based on:
  - [ ] Complementary expertise
  - [ ] Geographic requirements
  - [ ] Previous collaboration history
- [ ] Compatibility scoring
- [ ] Partner search filters

### 3.3 Budget Calculator
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] Implement cost category templates:
  - [ ] Personnel costs
  - [ ] Subcontracting
  - [ ] Travel and subsistence
  - [ ] Equipment
  - [ ] Other direct costs
  - [ ] Indirect costs (overhead)
- [ ] Add funding rate calculations per program
- [ ] Validate against program limits
- [ ] Generate budget tables

### 3.4 Timeline/Gantt Generator
**Status:** Not Started
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Work package structure definition
- [ ] Task and milestone creation
- [ ] Dependency management
- [ ] Export to common formats
- [ ] Visual Gantt chart rendering

### 3.5 Proposal Quality Scoring
**Status:** Not Started
**Impact:** High
**Effort:** High

**Tasks:**
- [ ] Define scoring criteria per program
- [ ] Implement automated evaluation:
  - [ ] Completeness check
  - [ ] Keyword presence
  - [ ] Budget feasibility
  - [ ] Impact clarity
- [ ] Provide improvement suggestions
- [ ] Benchmark against successful proposals

### 3.6 Document Generation
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] PDF export with proper formatting
- [ ] DOCX export for MS Word
- [ ] Template-based generation
- [ ] Include tables and charts
- [ ] Multi-language support

---

## Priority 4: Performance and Scalability

### 4.1 Database Optimization
**Status:** Not Started
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Add proper indexes to Dgraph schema
- [ ] Optimize graph queries
- [ ] Implement query caching
- [ ] Add connection pooling
- [ ] Profile and optimize slow queries

### 4.2 Caching Strategy
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] Implement Redis for session caching
- [ ] Cache embedding results
- [ ] Cache frequent Dgraph queries
- [ ] Add cache invalidation logic
- [ ] Implement LRU eviction

### 4.3 API Optimization
**Status:** Not Started
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Implement streaming for LLM responses
- [ ] Batch embedding requests
- [ ] Add request compression
- [ ] Optimize token usage
- [ ] Implement request queuing

### 4.4 Concurrent User Support
**Status:** Not Started
**Impact:** Medium
**Effort:** High

**Tasks:**
- [ ] Add session management
- [ ] Implement user isolation
- [ ] Load testing (target: 100 concurrent users)
- [ ] Add horizontal scaling support

---

## Priority 5: Testing and Stability

### 5.1 Unit Tests
**Status:** Minimal (~2%)
**Impact:** Very High
**Effort:** High

**Target:** 80% coverage

**Tasks:**
- [ ] Test CORDISRetriever methods
- [ ] Test CORDISProjectReader parsing
- [ ] Test MAPITGraphBuilder
- [ ] Test utility functions
- [ ] Add mock fixtures for external APIs

### 5.2 Integration Tests
**Status:** Not Started
**Impact:** High
**Effort:** High

**Tasks:**
- [ ] Test Flask endpoints
- [ ] Test Dgraph integration
- [ ] Test LLM integration with mocks
- [ ] Test ETL pipeline end-to-end

### 5.3 End-to-End Tests
**Status:** Not Started
**Impact:** High
**Effort:** High

**Tasks:**
- [ ] Test complete user flows
- [ ] Test error scenarios
- [ ] Test edge cases
- [ ] Automated browser testing (Playwright/Selenium)

### 5.4 CI/CD Pipeline
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] GitHub Actions workflow
- [ ] Automated testing on PR
- [ ] Code quality checks (pylint, black)
- [ ] Security scanning
- [ ] Automated deployment

### 5.5 Health Checks
**Status:** Not Started
**Impact:** Medium
**Effort:** Low

**Tasks:**
- [ ] Add `/health` endpoint
- [ ] Check database connectivity
- [ ] Check LLM API availability
- [ ] Add monitoring integration

---

## Priority 6: Security and Compliance

### 6.1 Authentication
**Status:** Not Started
**Impact:** High
**Effort:** High

**Tasks:**
- [ ] Implement user registration/login
- [ ] Add OAuth2/OIDC support
- [ ] Session management
- [ ] Password policies

### 6.2 GDPR Compliance
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] Data minimization
- [ ] User consent management
- [ ] Right to erasure implementation
- [ ] Data export capability
- [ ] Privacy policy

### 6.3 Security Hardening
**Status:** Not Started
**Impact:** High
**Effort:** Medium

**Tasks:**
- [ ] Input sanitization (XSS, injection)
- [ ] HTTPS enforcement
- [ ] API key rotation mechanism
- [ ] Rate limiting
- [ ] Security headers

---

## Priority 7: User Experience

### 7.1 Error Messages
**Status:** Not Started
**Impact:** Medium
**Effort:** Low

**Tasks:**
- [ ] User-friendly error messages
- [ ] Actionable suggestions
- [ ] Contact support option

### 7.2 Loading States
**Status:** Not Started
**Impact:** Medium
**Effort:** Low

**Tasks:**
- [ ] Add loading indicators
- [ ] Progress bars for long operations
- [ ] Skeleton screens

### 7.3 Responsive Design
**Status:** Partial
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Test on mobile devices
- [ ] Improve touch interactions
- [ ] Optimize for tablets

### 7.4 Onboarding
**Status:** Not Started
**Impact:** Medium
**Effort:** Medium

**Tasks:**
- [ ] Welcome tour
- [ ] Feature tooltips
- [ ] Sample queries
- [ ] Quick start guide

---

## Competitive Analysis

### Key Competitors

| Feature | MAPIT | Grantify | Instrumentl | OpenGrants |
|---------|-------|----------|-------------|------------|
| EU Focus | Yes | Partial | No | Partial |
| RAG/LLM | Yes | Yes | No | No |
| Proposal Writing | Planned | Yes | No | No |
| Consortium Finding | Planned | No | No | No |
| Budget Tools | Planned | Yes | Yes | No |
| CORDIS Integration | Yes | No | No | No |

### Differentiators to Develop

1. **Deep EU Expertise**: Most comprehensive EU funding database
2. **AI-Powered Writing**: Context-aware proposal generation
3. **Smart Matching**: Algorithm-based consortium formation
4. **CORDIS Native**: Direct integration with official EU data

---

## Implementation Timeline

### Phase 1: Foundation (Iterations 1-5)
- Error handling and logging
- Input validation
- Complete keyword search
- Basic testing framework
- API robustness

### Phase 2: Core Features (Iterations 6-10)
- Proposal writer MVP
- Consortium finder MVP
- Expanded program support
- Document generation

### Phase 3: Enhancement (Iterations 11-15)
- Budget calculator
- Quality scoring
- Performance optimization
- Security implementation

### Phase 4: Polish (Iterations 16-20)
- Comprehensive testing
- UX improvements
- Documentation
- Production hardening

---

## Next Steps

1. **Immediate (Iteration 1):** Implement structured logging framework
2. **Short-term:** Complete error handling and input validation
3. **Medium-term:** Build proposal writer and consortium finder
4. **Long-term:** Full program coverage and production deployment

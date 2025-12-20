# MAPIT AI - Improvement Roadmap

**Created**: December 2024
**Status**: Active Development

---

## Priority 1: Core Functionality and Production Readiness

### 1.1 API Layer Implementation [HIGH - NOT STARTED]
**Status**: `app/api/` directory is empty
**Required**:
- [ ] Create FastAPI application with proper routing
- [ ] Implement `/api/v1/projects/search` endpoint
- [ ] Implement `/api/v1/projects/{id}` endpoint
- [ ] Implement `/api/v1/proposals/generate` endpoint
- [ ] Implement `/api/v1/partners/discover` endpoint
- [ ] Add OpenAPI/Swagger documentation
- [ ] Add request/response validation with Pydantic models

### 1.2 Error Handling and Logging [HIGH - PARTIAL]
**Status**: Basic logging exists but inconsistent
**Required**:
- [ ] Standardize logging format across all modules
- [ ] Add structured logging with JSON output option
- [ ] Implement proper exception hierarchy
- [ ] Add error recovery mechanisms for database failures
- [ ] Add retry logic for external API calls (Mistral, CORDIS)
- [ ] Replace bare `except` clauses with specific exceptions

### 1.3 Input Validation and Security [HIGH - NOT STARTED]
**Status**: Minimal validation exists
**Required**:
- [ ] Add input validation for all API endpoints
- [ ] Sanitize user queries before database operations
- [ ] Implement SQL injection prevention (parameterized queries exist but need audit)
- [ ] Add XSS prevention for web responses
- [ ] Validate and sanitize file paths in ETL operations
- [ ] Add rate limiting for API endpoints

### 1.4 Configuration Management [MEDIUM - PARTIAL]
**Status**: Using .env but no validation
**Required**:
- [ ] Add configuration validation on startup
- [ ] Create config schema with defaults and required fields
- [ ] Add environment-specific configurations (dev/staging/prod)
- [ ] Remove hardcoded API keys from source code (CORDISRetriever.py line 271)

---

## Priority 2: Program Expansion

### 2.1 Horizon Europe Support [MEDIUM - PARTIAL]
**Status**: Basic CORDIS integration exists
**Required**:
- [ ] Add all Horizon Europe pillars and clusters
- [ ] Implement call deadline tracking
- [ ] Add program-specific proposal templates
- [ ] Include evaluation criteria for each call type
- [ ] Add Work Programme document integration

### 2.2 Erasmus+ Support [MEDIUM - NOT STARTED]
**Required**:
- [ ] Add Erasmus+ program data source
- [ ] Implement Key Action 1, 2, 3 support
- [ ] Add application guidelines per action
- [ ] Include budget rules and caps

### 2.3 Digital Europe Programme [LOW - NOT STARTED]
**Required**:
- [ ] Add DEP data integration
- [ ] Implement cluster-specific search
- [ ] Add DEP proposal templates

### 2.4 Other EU Programs [LOW - NOT STARTED]
- [ ] Creative Europe
- [ ] LIFE Programme
- [ ] Interreg programs
- [ ] EIT Knowledge and Innovation Communities

---

## Priority 3: Feature Enhancement

### 3.1 Improve RAG Quality [HIGH - NEEDED]
**Status**: Basic RAG exists but quality can improve
**Required**:
- [ ] Implement intelligent chunking (paragraph-aware, as noted in TODO)
- [ ] Add chunk overlap for better context
- [ ] Implement hybrid search (BM25 + semantic)
- [ ] Add cross-encoder reranking
- [ ] Improve prompt templates for better LLM responses
- [ ] Add citation/source tracking in responses

### 3.2 Budget Calculator [MEDIUM - COMPILED]
**Status**: Exists as compiled service
**Required**:
- [ ] Expose budget calculator via API
- [ ] Add EU funding rate rules per program
- [ ] Implement cost category validation
- [ ] Add partner contribution calculations
- [ ] Support multiple currency conversions

### 3.3 Timeline/Gantt Generation [MEDIUM - COMPILED]
**Status**: Exists as compiled service
**Required**:
- [ ] Expose timeline generator via API
- [ ] Add work package template generation
- [ ] Include milestone planning
- [ ] Generate exportable Gantt charts

### 3.4 Partner Matching [MEDIUM - COMPILED]
**Status**: Partner discovery exists as compiled service
**Required**:
- [ ] Expose partner matching via API
- [ ] Add compatibility scoring algorithm
- [ ] Include geographic diversity requirements
- [ ] Add expertise complementarity analysis
- [ ] Implement consortium composition recommendations

### 3.5 Proposal Quality Scoring [MEDIUM - COMPILED]
**Status**: Quality services exist as compiled
**Required**:
- [ ] Expose quality scoring via API
- [ ] Implement evaluation criteria matching
- [ ] Add improvement suggestions
- [ ] Generate readability metrics
- [ ] Add compliance checklist validation

### 3.6 Document Export [LOW - COMPILED]
**Status**: Submission exporter exists
**Required**:
- [ ] Add PDF export functionality
- [ ] Generate properly formatted proposals
- [ ] Include budget tables in export
- [ ] Add Gantt chart to export

---

## Priority 4: Performance and Scalability

### 4.1 Database Optimization [MEDIUM - PARTIAL]
**Status**: Connection pooling exists, needs tuning
**Required**:
- [ ] Add database indexes for common queries
- [ ] Implement query result caching
- [ ] Add connection pool monitoring
- [ ] Optimize JOIN queries in cordis_repository.py
- [ ] Add database query logging for slow queries

### 4.2 Caching Strategy [MEDIUM - NOT STARTED]
**Required**:
- [ ] Implement embedding cache (avoid recomputing)
- [ ] Add LLM response caching for common queries
- [ ] Implement Redis caching layer
- [ ] Add cache invalidation strategy

### 4.3 Async Processing [MEDIUM - PARTIAL]
**Status**: Celery configured but not used
**Required**:
- [ ] Implement async proposal generation
- [ ] Add background ETL processing
- [ ] Implement webhook notifications for long tasks
- [ ] Add progress tracking for async operations

### 4.4 LLM Token Management [LOW - PARTIAL]
**Status**: Basic truncation exists (line 110-112 in CORDISRetriever.py)
**Required**:
- [ ] Implement smarter context window management
- [ ] Add token counting before API calls
- [ ] Implement streaming responses
- [ ] Add cost tracking per request

---

## Priority 5: Testing and Stability

### 5.1 Unit Tests [HIGH - MINIMAL]
**Status**: Only 1 test file exists (test_ProjectLoaderTest.py)
**Required**:
- [ ] Add tests for CordisProjectRepository
- [ ] Add tests for CORDISRetriever
- [ ] Add tests for query optimization
- [ ] Add tests for ETL pipeline
- [ ] Aim for 80%+ coverage

### 5.2 Integration Tests [HIGH - NOT STARTED]
**Required**:
- [ ] Add API endpoint tests
- [ ] Add database integration tests
- [ ] Add LLM API mock tests
- [ ] Add end-to-end workflow tests

### 5.3 CI/CD Pipeline [MEDIUM - NOT STARTED]
**Required**:
- [ ] Add GitHub Actions workflow
- [ ] Implement automated testing on PR
- [ ] Add linting and type checking
- [ ] Add security scanning
- [ ] Implement automated deployment

### 5.4 Health Checks [LOW - NOT STARTED]
**Required**:
- [ ] Add `/health` endpoint
- [ ] Add `/ready` endpoint
- [ ] Implement database health check
- [ ] Implement LLM provider health check

---

## Priority 6: Security and Compliance

### 6.1 Authentication [HIGH - NOT STARTED]
**Required**:
- [ ] Implement user authentication
- [ ] Add API key management
- [ ] Implement session management
- [ ] Add role-based access control

### 6.2 GDPR Compliance [MEDIUM - NOT STARTED]
**Required**:
- [ ] Add data retention policies
- [ ] Implement user data export
- [ ] Add consent management
- [ ] Implement data deletion capability

### 6.3 API Key Security [HIGH - NEEDED NOW]
**Status**: Keys exposed in .env and hardcoded
**Required**:
- [x] Remove hardcoded API key from CORDISRetriever.py
- [ ] Implement API key encryption at rest
- [ ] Add key rotation mechanism
- [ ] Implement secret management (HashiCorp Vault or similar)

---

## Priority 7: User Experience

### 7.1 Error Messages [MEDIUM - PARTIAL]
**Required**:
- [ ] Add user-friendly error messages
- [ ] Include actionable guidance in errors
- [ ] Add error codes for programmatic handling

### 7.2 Web Interface Improvements [LOW - BASIC]
**Status**: Basic Flask template exists
**Required**:
- [ ] Add loading states and progress indicators
- [ ] Improve response formatting
- [ ] Add conversation history display
- [ ] Implement responsive design

---

## Iteration Tracking

| Iteration | Date | Focus | Status |
|-----------|------|-------|--------|
| 1 | TBD | API Layer / Security Fix | Planned |
| 2 | TBD | Error Handling | Planned |
| 3 | TBD | RAG Quality | Planned |
| 4 | TBD | Testing | Planned |
| ... | ... | ... | ... |

---

## Competitive Analysis Notes

### Competitors to Surpass:
1. **Grantify** - AI-powered grant writing
2. **Instrumentl** - Grant discovery and tracking
3. **OpenGrants** - Government grant matching
4. **Fluxx** - Grant management platform
5. **Submittable** - Application management

### MAPIT Differentiators:
- EU funding specialization (Horizon Europe focus)
- Knowledge graph for project relationships
- RAG-based intelligence from CORDIS data
- Multi-LLM provider support
- Open source potential

### Features Needed to Compete:
- [ ] Real-time call deadline notifications
- [ ] Success rate analytics by organization type
- [ ] Collaborative proposal editing
- [ ] Grant portfolio management
- [ ] Post-award project tracking

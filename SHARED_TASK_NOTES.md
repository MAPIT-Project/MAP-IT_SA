# MAPIT AI - Shared Task Notes

**Last Updated:** December 20, 2024
**Last Iteration:** 1

---

## Current State

FastAPI application foundation is complete but not tested. Core files:
- API: `app/api/main.py` (run with `uvicorn app.api.main:app --reload`)
- Config: `app/core/config.py`
- Routes: `app/api/routes/projects.py`, `app/api/routes/health.py`

Security fix applied - API keys now require environment variables.

---

## Next Priority Tasks

### Immediate (Iteration 2)
1. **Test the FastAPI endpoints** - Ensure they work with the existing database
2. **Add RAG query endpoint** - Integrate CORDISRetriever with FastAPI
3. **Add unit tests** - At minimum for health endpoints and config

### Short Term (Iterations 3-5)
- Implement proposal generation endpoints
- Add request logging middleware
- Implement proper database health check
- Add rate limiting

---

## Important Notes

1. **Environment Variables Required:**
   - `DATABASE_URL` - PostgreSQL connection
   - `MAPIT_LLM_KEY` - Mistral AI API key (for Flask app)
   - `MAPIT_BASE_INFO_DIR` - PDF directory (for Flask app)

2. **Two Web Interfaces Exist:**
   - Flask GUI: `src/gui/app.py` (port 5000/16000) - Legacy, uses Dgraph
   - FastAPI: `app/api/main.py` (port 8000) - New, uses PostgreSQL

3. **Compiled Services:** Many services in `app/services/` are only `.pyc` files

4. **Database Schema:** Tables are in `public` schema (`projects`, `organizations`), not `cordis_processed`

---

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run FastAPI (new)
uvicorn app.api.main:app --reload --port 8000

# Run Flask (legacy)
cd src/gui && python app.py
```

---

## Files to Reference

- `docs_tracked/IMPROVEMENT_ROADMAP.md` - Full roadmap with priorities
- `docs_tracked/SYSTEM_ARCHITECTURE.md` - System design
- `CLAUDE.md` - Development conventions
- `docs_tracked/IMPROVEMENT_LOG.md` - Change history

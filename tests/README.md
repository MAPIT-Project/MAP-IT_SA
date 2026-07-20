# Backend tests

## Local baseline

Install both production and development dependencies, then collect or run the suite from the
backend repository root:

```bash
make install-dev
pytest --collect-only
make test
```

Pytest is intentionally limited to `tests/` in `pyproject.toml`. This keeps collection away from
runtime and Docker volume directories such as `neo4j/import/`, whose ownership may belong to the
Neo4j container. It does not remove or skip files in the test suite.

## External dependencies

Most unit tests mock infrastructure. Integration, quality, real-tool, and live-conversation tests
can additionally require some or all of the following:

- PostgreSQL/Supabase with the project schema and pgvector data (`DATABASE_URL`, `SUPABASE_URL`,
  and `SUPABASE_KEY`);
- Redis (`REDIS_URL`);
- Neo4j with the project graph loaded (`NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`);
- a running backend (`TEST_API_URL`);
- configured LLM/embedding provider credentials for live AI scenarios.

Fixtures and modules that explicitly support missing infrastructure skip based on their relevant
environment variables. Not every historical scenario is consistently marked, so a full
`make test` run without the services can still fail or time out after successful collection.

The backend CI therefore treats lint and formatting as blocking checks and currently runs
`make test` as a non-blocking baseline. It always uploads `test-results/pytest.xml` so remaining
failures can be inspected. Promote tests to a blocking gate after the integration/live tiers have
been separated and their service/data setup is reproducible in CI.

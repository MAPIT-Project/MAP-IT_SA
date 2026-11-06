# Backend tests

Install production and development requirements, then use the guarded offline target:

```bash
make install-dev
make test
make test PYTEST_ARGS="--collect-only"
```

The offline runner uses dummy settings, disables dotenv and blocks live service
access. Model responses in these tests are mocked. CI treats test failures as
blocking and uploads its JUnit report even on failure.

The former bulk live-response tests and collection-time API probes were removed.
Their replacement is a compact matrix of 52 tool contracts and ten source-backed
questions. It checks expected facts against independent read-only funding SQL,
not an AI judge or another call to the tool under test.

```bash
make test-tools   # Actual tools against funding data, zero model requests
make test-live    # Real Codex questions with a shared 30-request ceiling
```

Run these explicit evaluation commands only when you intend to query the local
funding source or spend model usage. Missing capabilities remain blocked, and a
provider failure stops later questions. The default evaluator does not modify
existing data or connect paid embedding/API-key providers.

See [commands, budgets and limitations](../docs_tracked/TESTING.md),
[coverage and evidence](../docs_tracked/TOOL_SCENARIO_COVERAGE.md),
[actual validation results](../docs_tracked/PYDANTIC_AI_VALIDATION.md), and
[the retirement inventory](RETIRED_LIVE_TESTS.md).

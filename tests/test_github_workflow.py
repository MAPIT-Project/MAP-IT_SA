"""
Tests for GitHub Actions Workflow Configuration.

This test file verifies that the conversation-tests.yml workflow is properly
configured with all required components per PRD Task 025:
1. Service containers (postgres, redis, neo4j)
2. API server startup
3. Scenario test execution
4. Quality baseline comparison
5. Artifact upload for results

Run with: pytest tests/test_github_workflow.py -v
"""

from pathlib import Path

import pytest
import yaml


class TestGitHubWorkflowConfiguration:
    """Tests for GitHub Actions workflow configuration validation."""

    @pytest.fixture
    def workflow_path(self) -> Path:
        """Path to the conversation-tests workflow file."""
        project_root = Path(__file__).parent.parent
        return project_root / ".github" / "workflows" / "conversation-tests.yml"

    @pytest.fixture
    def workflow_config(self, workflow_path: Path) -> dict:
        """Load and parse the workflow configuration."""
        if not workflow_path.exists():
            pytest.skip(f"Workflow file not found: {workflow_path}")

        with open(workflow_path) as f:
            config = yaml.safe_load(f)

        # YAML parses 'on' as boolean True, normalize it
        if True in config and "on" not in config:
            config["on"] = config.pop(True)

        return config

    def test_workflow_file_exists(self, workflow_path: Path):
        """Verify the workflow file exists."""
        assert workflow_path.exists(), f"Workflow file not found at {workflow_path}"

    def test_workflow_name_is_set(self, workflow_config: dict):
        """Verify workflow has a descriptive name."""
        assert "name" in workflow_config
        assert "Conversation" in workflow_config["name"]

    def test_workflow_triggers_configured(self, workflow_config: dict):
        """Verify workflow triggers are properly configured."""
        assert "on" in workflow_config
        triggers = workflow_config["on"]

        # Should trigger on push to main
        assert "push" in triggers
        assert "main" in triggers["push"].get("branches", [])

        # Should trigger on pull requests
        assert "pull_request" in triggers

        # Should support manual workflow dispatch
        assert "workflow_dispatch" in triggers

    def test_workflow_has_path_filters(self, workflow_config: dict):
        """Verify workflow only triggers for relevant file changes."""
        push_config = workflow_config["on"]["push"]
        assert "paths" in push_config

        paths = push_config["paths"]
        # Should watch conversation-related files
        assert any("conversation" in p for p in paths)
        assert any("memory" in p for p in paths)
        assert any("agents" in p for p in paths)
        has_core_files = any("atomic_storage" in p for p in paths) or any(
            "conversation_lock" in p for p in paths
        )
        assert has_core_files

    def test_environment_variables_defined(self, workflow_config: dict):
        """Verify required environment variables are defined."""
        assert "env" in workflow_config
        env = workflow_config["env"]

        # Database configuration
        assert "DATABASE_URL" in env
        assert "postgres" in env["DATABASE_URL"].lower()

        # Redis configuration
        assert "REDIS_URL" in env
        assert "redis" in env["REDIS_URL"].lower()

        # Neo4j configuration
        assert "NEO4J_URI" in env

        # API configuration
        assert "TEST_API_URL" in env

        # Quality threshold
        assert "QUALITY_THRESHOLD" in env
        assert int(env["QUALITY_THRESHOLD"]) >= 75

    def test_has_required_jobs(self, workflow_config: dict):
        """Verify all required jobs are defined."""
        assert "jobs" in workflow_config
        jobs = workflow_config["jobs"]

        # Required job types
        required_job_types = ["unit", "integration", "quality", "race"]

        for job_type in required_job_types:
            matching_jobs = [name for name in jobs.keys() if job_type in name.lower()]
            assert len(matching_jobs) > 0, f"No job found for {job_type}"

    def test_integration_job_has_service_containers(self, workflow_config: dict):
        """Verify integration tests have required service containers."""
        jobs = workflow_config["jobs"]
        integration_job = jobs.get("integration-tests")

        if not integration_job:
            pytest.skip("integration-tests job not found")

        assert "services" in integration_job
        services = integration_job["services"]

        # PRD Task 025 requires: postgres, redis, neo4j
        assert "postgres" in services, "PostgreSQL service container required"
        assert "redis" in services, "Redis service container required"
        assert "neo4j" in services, "Neo4j service container required"

        # Verify service health checks
        for service_name in ["postgres", "redis", "neo4j"]:
            service = services[service_name]
            assert "options" in service or "healthcheck" in str(service).lower(), (
                f"Service {service_name} should have health check configured"
            )

    def test_postgres_service_configuration(self, workflow_config: dict):
        """Verify PostgreSQL service is properly configured."""
        services = workflow_config["jobs"]["integration-tests"]["services"]
        postgres = services["postgres"]

        # Check image version
        assert "image" in postgres
        assert "postgres" in postgres["image"]

        # Check environment
        assert "env" in postgres
        env = postgres["env"]
        assert "POSTGRES_USER" in env
        assert "POSTGRES_PASSWORD" in env
        assert "POSTGRES_DB" in env

        # Check port mapping
        assert "ports" in postgres
        assert any("5432" in str(p) for p in postgres["ports"])

    def test_redis_service_configuration(self, workflow_config: dict):
        """Verify Redis service is properly configured."""
        services = workflow_config["jobs"]["integration-tests"]["services"]
        redis = services["redis"]

        assert "image" in redis
        assert "redis" in redis["image"]

        assert "ports" in redis
        assert any("6379" in str(p) for p in redis["ports"])

    def test_neo4j_service_configuration(self, workflow_config: dict):
        """Verify Neo4j service is properly configured."""
        services = workflow_config["jobs"]["integration-tests"]["services"]
        neo4j = services["neo4j"]

        assert "image" in neo4j
        assert "neo4j" in neo4j["image"]

        # Neo4j requires authentication
        assert "env" in neo4j
        env = neo4j["env"]
        assert "NEO4J_AUTH" in env

        # Check ports (HTTP browser and Bolt protocol)
        assert "ports" in neo4j
        ports_str = str(neo4j["ports"])
        assert "7474" in ports_str or "7687" in ports_str

    def test_integration_job_has_api_server_startup(self, workflow_config: dict):
        """Verify integration job starts the API server."""
        integration_job = workflow_config["jobs"]["integration-tests"]
        steps = integration_job["steps"]

        # Find step that starts API server
        api_start_steps = [
            s
            for s in steps
            if "name" in s and ("api" in s["name"].lower() or "server" in s["name"].lower())
        ]

        assert len(api_start_steps) > 0, "Should have a step to start API server"

        # Verify the step uses uvicorn or similar
        api_step = api_start_steps[0]
        if "run" in api_step:
            run_content = api_step["run"]
            assert "uvicorn" in run_content or "main:app" in run_content, (
                "API server should be started with uvicorn"
            )

    def test_scenario_test_execution_step(self, workflow_config: dict):
        """Verify scenario tests are executed."""
        integration_job = workflow_config["jobs"]["integration-tests"]
        steps = integration_job["steps"]

        # Find step that runs scenario tests
        scenario_steps = [s for s in steps if "name" in s and "scenario" in s["name"].lower()]

        assert len(scenario_steps) > 0, "Should have a step to run scenario tests"

        # Verify pytest is used
        scenario_step = scenario_steps[0]
        if "run" in scenario_step:
            run_content = scenario_step["run"]
            assert "pytest" in run_content
            assert "test_conversation_scenarios" in run_content

    def test_quality_validation_job(self, workflow_config: dict):
        """Verify quality validation job is configured."""
        jobs = workflow_config["jobs"]

        quality_job = jobs.get("quality-validation")
        assert quality_job is not None, "quality-validation job required"

        # Should run after integration tests
        assert "needs" in quality_job
        needs = quality_job["needs"]
        if isinstance(needs, str):
            needs = [needs]
        assert "integration-tests" in needs

        # Should have quality check step
        steps = quality_job["steps"]
        quality_steps = [s for s in steps if "name" in s and "quality" in s["name"].lower()]
        assert len(quality_steps) > 0, "Should have quality check step"

    def test_artifact_upload_configured(self, workflow_config: dict):
        """Verify test results are uploaded as artifacts."""
        integration_job = workflow_config["jobs"]["integration-tests"]
        steps = integration_job["steps"]

        # Find artifact upload steps
        upload_steps = [s for s in steps if "uses" in s and "upload-artifact" in s["uses"]]

        assert len(upload_steps) > 0, "Should upload test results as artifacts"

        # Verify artifact configuration
        upload_step = upload_steps[0]
        assert "with" in upload_step
        with_config = upload_step["with"]
        assert "name" in with_config
        assert "path" in with_config

    def test_race_condition_job_exists(self, workflow_config: dict):
        """Verify dedicated race condition tests job exists."""
        jobs = workflow_config["jobs"]

        race_job = jobs.get("race-condition-tests")
        assert race_job is not None, "race-condition-tests job required"

        # Should run regression tests for Task 001
        steps = race_job["steps"]

        # Find steps that run pytest for race condition tests
        test_steps = [
            s
            for s in steps
            if "run" in s
            and "pytest" in s.get("run", "")
            and ("TestTask001" in s.get("run", "") or "race" in s.get("run", "").lower())
        ]

        assert len(test_steps) > 0, (
            "Should run pytest for race condition tests with TestTask001 or race in command"
        )

    def test_final_status_job(self, workflow_config: dict):
        """Verify final status job aggregates results."""
        jobs = workflow_config["jobs"]

        final_job = jobs.get("final-status")
        assert final_job is not None, "final-status job required"

        # Should depend on all other jobs
        assert "needs" in final_job
        needs = final_job["needs"]
        if isinstance(needs, str):
            needs = [needs]

        assert len(needs) >= 3, "Final status should depend on multiple jobs"

        # Should always run
        if_condition = final_job.get("if", "")
        assert "always()" in if_condition, "Final status should always run"

    def test_workflow_dispatch_inputs(self, workflow_config: dict):
        """Verify manual workflow dispatch has useful inputs."""
        dispatch = workflow_config["on"]["workflow_dispatch"]

        if "inputs" not in dispatch:
            pytest.skip("No workflow dispatch inputs configured")

        inputs = dispatch["inputs"]

        # Should have input to control live test execution
        live_test_input = inputs.get("run_live_tests")
        if live_test_input:
            assert "type" in live_test_input

        # Should have input to select test category
        category_input = inputs.get("test_category")
        if category_input:
            assert "options" in category_input or "type" in category_input


class TestWorkflowYAMLSyntax:
    """Tests for YAML syntax validation."""

    @pytest.fixture
    def workflow_path(self) -> Path:
        """Path to the conversation-tests workflow file."""
        project_root = Path(__file__).parent.parent
        return project_root / ".github" / "workflows" / "conversation-tests.yml"

    def test_yaml_is_valid(self, workflow_path: Path):
        """Verify YAML syntax is valid."""
        if not workflow_path.exists():
            pytest.skip(f"Workflow file not found: {workflow_path}")

        try:
            with open(workflow_path) as f:
                config = yaml.safe_load(f)
            assert config is not None
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML syntax: {e}")

    def test_no_syntax_errors_in_shell_scripts(self, workflow_path: Path):
        """Verify shell scripts in workflow don't have obvious errors."""
        if not workflow_path.exists():
            pytest.skip(f"Workflow file not found: {workflow_path}")

        with open(workflow_path) as f:
            config = yaml.safe_load(f)

        for job_name, job in config.get("jobs", {}).items():
            for i, step in enumerate(job.get("steps", [])):
                if "run" in step:
                    run_content = step["run"]
                    # Check for common shell script issues
                    assert run_content.count("$(") == run_content.count(")") or run_content.count(
                        "${"
                    ) <= run_content.count("}"), (
                        f"Possible unbalanced brackets in {job_name} step {i}"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

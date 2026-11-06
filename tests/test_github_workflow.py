"""Validate the checked-in backend workflow, including failure-result publication.

The former conversation-tests workflow and its provisioned service jobs were
removed. CI currently runs the backend Makefile targets from ci.yml.
"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow_config():
    path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    assert path.is_file(), f"Backend CI workflow missing: {path}"
    config = yaml.safe_load(path.read_text())
    # PyYAML's YAML 1.1 loader interprets the Actions `on` key as a boolean.
    if True in config:
        config["on"] = config.pop(True)
    return config


@pytest.fixture
def quality_job(workflow_config):
    job = workflow_config["jobs"]["quality"]
    assert job["runs-on"] == "ubuntu-latest"
    return job


def test_workflow_checks_main_and_pull_requests(workflow_config):
    assert workflow_config["name"]
    assert "main" in workflow_config["on"]["push"]["branches"]
    assert "pull_request" in workflow_config["on"]


def test_workflow_permissions_are_read_only(workflow_config):
    assert workflow_config["permissions"] == {"contents": "read"}


def test_quality_job_has_bounded_runtime(quality_job):
    assert 0 < quality_job["timeout-minutes"] <= 30


def test_dependencies_installed_before_checks(quality_job):
    steps = quality_job["steps"]
    checkout = next(
        i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/checkout@")
    )
    setup = next(
        i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/setup-python@")
    )
    install = next(i for i, s in enumerate(steps) if s.get("run") == "make install-dev")
    lint = next(i for i, s in enumerate(steps) if s.get("run") == "make lint")
    assert checkout < setup < install < lint
    assert steps[setup]["with"]["python-version"] == "3.11"
    assert "requirements.txt" in steps[setup]["with"]["cache-dependency-path"]
    assert "requirements-dev.txt" in steps[setup]["with"]["cache-dependency-path"]


def test_lint_is_blocking(quality_job):
    lint = next(s for s in quality_job["steps"] if s.get("run") == "make lint")
    assert not lint.get("continue-on-error", False)


def test_formatting_check_does_not_rewrite_source(quality_job):
    checks = [s["run"] for s in quality_job["steps"] if "black" in s.get("run", "")]
    assert checks
    assert all("--check" in command for command in checks)
    assert all("make format" not in s.get("run", "") for s in quality_job["steps"])


def test_pytest_produces_junit_artifact(quality_job):
    test_step = next(s for s in quality_job["steps"] if "make test" in s.get("run", ""))
    assert 'PYTEST_ARGS="--junitxml=test-results/pytest.xml"' in test_step["run"]
    assert "mkdir -p test-results" in test_step["run"]
    assert not test_step.get("continue-on-error", False)


def test_make_test_uses_guarded_runner():
    makefile = Path(__file__).resolve().parents[1] / "Makefile"
    content = makefile.read_text()
    offline_target = content.split("\ntest:\n", 1)[1].split("\n\n", 1)[0]
    assert "scripts/test_offline.py" in offline_target
    assert "$(PYTEST_ARGS)" in offline_target


def test_results_uploaded_after_failed_tests(quality_job):
    artifact = next(
        s for s in quality_job["steps"] if s.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert artifact["if"] == "always()"
    assert artifact["with"]["path"] == "test-results/"
    assert 1 <= artifact["with"]["retention-days"] <= 30
    steps = quality_job["steps"]
    test_index = next(i for i, s in enumerate(steps) if "make test" in s.get("run", ""))
    assert steps.index(artifact) > test_index

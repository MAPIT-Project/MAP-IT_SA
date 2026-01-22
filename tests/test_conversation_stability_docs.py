"""
Tests for the Conversation Stability Architecture documentation.

This module validates that the architecture documentation:
1. Exists and is readable
2. Contains all required sections
3. References correct file paths
4. Has valid YAML scenario examples
"""

from pathlib import Path

import pytest

# Path to the documentation file
DOCS_DIR = Path(__file__).parent.parent / "docs"
ARCHITECTURE_DOC = DOCS_DIR / "CONVERSATION_STABILITY_ARCHITECTURE.md"

# Required sections that must be present in the documentation
REQUIRED_SECTIONS = [
    "## Overview",
    "## Lock Manager Design",
    "## Atomic Storage Design",
    "## Test Agent Architecture",
    "## Scenario Format Specification",
    "## Integration Guide",
    "## Debugging Guide",
]

# Key files that should be referenced in the documentation
KEY_FILES = [
    "app/core/conversation_lock.py",
    "app/core/atomic_storage.py",
    "tests/agents/conversation_flow_agent.py",
    "tests/agents/context_validator_agent.py",
    "tests/agents/quality_evaluator_agent.py",
]


class TestArchitectureDocumentation:
    """Tests for the architecture documentation file."""

    def test_documentation_file_exists(self):
        """Test that the architecture documentation file exists."""
        assert (
            ARCHITECTURE_DOC.exists()
        ), f"Architecture documentation not found at {ARCHITECTURE_DOC}"

    def test_documentation_is_readable(self):
        """Test that the documentation file can be read."""
        content = ARCHITECTURE_DOC.read_text()
        assert len(content) > 1000, "Documentation appears too short"

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_section_present(self, section: str):
        """Test that each required section is present in the documentation."""
        content = ARCHITECTURE_DOC.read_text()
        assert section in content, f"Required section '{section}' not found in documentation"

    def test_has_title(self):
        """Test that the documentation has a proper title."""
        content = ARCHITECTURE_DOC.read_text()
        assert content.startswith(
            "# Conversation Stability Architecture"
        ), "Documentation should start with the title"

    def test_has_table_of_contents(self):
        """Test that the documentation has a table of contents."""
        content = ARCHITECTURE_DOC.read_text()
        assert (
            "## Table of Contents" in content or "1. [Overview]" in content
        ), "Documentation should have a table of contents"

    @pytest.mark.parametrize("file_path", KEY_FILES)
    def test_key_file_referenced(self, file_path: str):
        """Test that key implementation files are referenced."""
        content = ARCHITECTURE_DOC.read_text()
        # Check for the filename at minimum
        filename = Path(file_path).name
        assert filename in content, f"Key file '{file_path}' not referenced in documentation"

    def test_lock_manager_usage_example(self):
        """Test that lock manager has a usage example."""
        content = ARCHITECTURE_DOC.read_text()
        assert (
            "get_conversation_lock" in content
        ), "Lock manager usage example should include get_conversation_lock"
        assert (
            "async with" in content
        ), "Lock manager usage should show async context manager pattern"

    def test_atomic_storage_usage_example(self):
        """Test that atomic storage has a usage example."""
        content = ARCHITECTURE_DOC.read_text()
        assert (
            "AtomicMessageStorage" in content or "store_message" in content
        ), "Atomic storage usage example should be present"
        assert "StorageResult" in content, "StorageResult class should be documented"

    def test_test_agents_documented(self):
        """Test that all three test agents are documented."""
        content = ARCHITECTURE_DOC.read_text()

        assert "ConversationFlowAgent" in content, "ConversationFlowAgent should be documented"
        assert "ContextValidatorAgent" in content, "ContextValidatorAgent should be documented"
        assert "QualityEvaluatorAgent" in content, "QualityEvaluatorAgent should be documented"

    def test_scoring_dimensions_documented(self):
        """Test that quality scoring dimensions are documented."""
        content = ARCHITECTURE_DOC.read_text()

        assert "Query Fulfillment" in content, "Query Fulfillment dimension should be documented"
        assert "Specificity" in content, "Specificity dimension should be documented"
        assert "Factual Accuracy" in content, "Factual Accuracy dimension should be documented"
        assert "Actionability" in content, "Actionability dimension should be documented"
        assert "40" in content, "40-point allocation for Query Fulfillment should be mentioned"

    def test_yaml_scenario_format_documented(self):
        """Test that the YAML scenario format is documented."""
        content = ARCHITECTURE_DOC.read_text()

        assert "yaml" in content.lower(), "YAML format should be mentioned"
        assert "steps:" in content, "Scenario steps format should be documented"
        assert "validations:" in content, "Validations format should be documented"
        assert "final_validations:" in content, "Final validations should be documented"

    def test_validation_types_documented(self):
        """Test that validation types are documented."""
        content = ARCHITECTURE_DOC.read_text()

        validation_types = [
            "response_contains",
            "response_contains_any",
            "tools_used",
            "no_error",
            "context_integrity",
            "quality_non_degradation",
        ]

        for vtype in validation_types:
            assert vtype in content, f"Validation type '{vtype}' should be documented"

    def test_directory_structure_documented(self):
        """Test that the scenario directory structure is documented."""
        content = ARCHITECTURE_DOC.read_text()

        directories = [
            "basic_flows/",
            "follow_up/",
            "context/",
            "error_recovery/",
            "concurrent/",
        ]

        for directory in directories:
            assert directory in content, f"Scenario directory '{directory}' should be documented"

    def test_debugging_guide_content(self):
        """Test that the debugging guide has useful content."""
        content = ARCHITECTURE_DOC.read_text()

        # Should have common issues
        assert (
            "Race Condition" in content or "race condition" in content
        ), "Race condition debugging should be documented"
        assert (
            "Context Loss" in content or "context loss" in content
        ), "Context loss debugging should be documented"

    def test_integration_guide_content(self):
        """Test that the integration guide has code examples."""
        content = ARCHITECTURE_DOC.read_text()

        # Should have integration examples
        assert (
            "Integrating" in content or "integrating" in content
        ), "Integration guide should explain how to integrate modules"
        assert "```python" in content, "Integration guide should have Python code examples"


class TestReferencedFilesExist:
    """Tests that files referenced in documentation actually exist."""

    @pytest.mark.parametrize("file_path", KEY_FILES)
    def test_referenced_file_exists(self, file_path: str):
        """Test that referenced implementation files exist."""
        project_root = Path(__file__).parent.parent
        full_path = project_root / file_path
        assert full_path.exists(), f"Referenced file '{file_path}' does not exist"


class TestScenarioDirectoriesExist:
    """Tests that scenario directories referenced in docs exist."""

    SCENARIO_DIRS = [
        "tests/scenarios/basic_flows",
        "tests/scenarios/follow_up",
        "tests/scenarios/context",
        "tests/scenarios/error_recovery",
        "tests/scenarios/concurrent",
    ]

    @pytest.mark.parametrize("dir_path", SCENARIO_DIRS)
    def test_scenario_directory_exists(self, dir_path: str):
        """Test that scenario directories exist."""
        project_root = Path(__file__).parent.parent
        full_path = project_root / dir_path
        assert full_path.exists(), f"Scenario directory '{dir_path}' does not exist"
        assert full_path.is_dir(), f"'{dir_path}' should be a directory"

    def test_scenarios_have_yaml_files(self):
        """Test that scenario directories contain YAML files."""
        project_root = Path(__file__).parent.parent
        scenarios_dir = project_root / "tests" / "scenarios"

        yaml_files = list(scenarios_dir.rglob("*.yaml"))
        assert len(yaml_files) > 0, "No YAML scenario files found"

        # Should have at least 5 scenarios based on PRD
        assert len(yaml_files) >= 5, f"Expected at least 5 scenarios, found {len(yaml_files)}"

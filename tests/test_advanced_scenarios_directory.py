"""
Tests to verify the advanced scenarios directory structure is set up correctly.

This is part of Task 001 from the Advanced Conversation Flows PRD.
"""

from pathlib import Path

import pytest

# Get the project root and scenarios directory
PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "tests" / "scenarios"
ADVANCED_SCENARIOS_DIR = SCENARIOS_DIR / "advanced"


class TestAdvancedScenariosDirectory:
    """Tests for advanced scenarios directory structure."""

    def test_scenarios_directory_exists(self) -> None:
        """Test that the main scenarios directory exists."""
        assert SCENARIOS_DIR.exists(), f"Scenarios directory not found: {SCENARIOS_DIR}"
        assert SCENARIOS_DIR.is_dir(), f"Scenarios path is not a directory: {SCENARIOS_DIR}"

    def test_advanced_directory_exists(self) -> None:
        """Test that the advanced scenarios directory exists."""
        assert (
            ADVANCED_SCENARIOS_DIR.exists()
        ), f"Advanced scenarios directory not found: {ADVANCED_SCENARIOS_DIR}"
        assert (
            ADVANCED_SCENARIOS_DIR.is_dir()
        ), f"Advanced scenarios path is not a directory: {ADVANCED_SCENARIOS_DIR}"

    def test_gitkeep_exists(self) -> None:
        """Test that .gitkeep file exists to track empty directory."""
        gitkeep_path = ADVANCED_SCENARIOS_DIR / ".gitkeep"
        assert gitkeep_path.exists(), f".gitkeep file not found: {gitkeep_path}"

    def test_readme_exists(self) -> None:
        """Test that README.md exists with documentation."""
        readme_path = ADVANCED_SCENARIOS_DIR / "README.md"
        assert readme_path.exists(), f"README.md not found: {readme_path}"

        # Check README has content
        content = readme_path.read_text()
        assert len(content) > 100, "README.md should have documentation content"
        assert "Scenario Format" in content, "README.md should document scenario format"
        assert "Validation Types" in content, "README.md should document validation types"

    def test_directory_is_writable(self) -> None:
        """Test that we can create files in the directory."""
        test_file = ADVANCED_SCENARIOS_DIR / ".test_write"
        try:
            test_file.write_text("test")
            assert test_file.exists()
            test_file.unlink()  # Clean up
        except PermissionError:
            pytest.fail(f"Cannot write to directory: {ADVANCED_SCENARIOS_DIR}")

    def test_other_scenario_directories_exist(self) -> None:
        """Test that other scenario directories from Stability PRD exist."""
        expected_dirs = ["basic_flows", "follow_up", "context", "error_recovery", "concurrent"]
        for dir_name in expected_dirs:
            dir_path = SCENARIOS_DIR / dir_name
            assert dir_path.exists(), f"Expected scenario directory not found: {dir_path}"
            assert dir_path.is_dir(), f"Path is not a directory: {dir_path}"


class TestAdvancedScenariosReadme:
    """Tests for README.md content validation."""

    def test_readme_documents_yaml_format(self) -> None:
        """Test that README documents the YAML scenario format."""
        readme_path = ADVANCED_SCENARIOS_DIR / "README.md"
        content = readme_path.read_text()

        # Check for key YAML structure elements
        assert "name:" in content, "README should show name field"
        assert "description:" in content, "README should show description field"
        assert "steps:" in content, "README should show steps field"
        assert "validations:" in content, "README should show validations field"

    def test_readme_documents_validation_types(self) -> None:
        """Test that README documents all validation types."""
        readme_path = ADVANCED_SCENARIOS_DIR / "README.md"
        content = readme_path.read_text()

        # Check for key validation types
        validation_types = [
            "response_contains",
            "tools_used",
            "goal_progress",
            "context_preserved",
            "no_error",
        ]
        for validation_type in validation_types:
            assert (
                validation_type in content
            ), f"README should document validation type: {validation_type}"

    def test_readme_documents_running_tests(self) -> None:
        """Test that README shows how to run tests."""
        readme_path = ADVANCED_SCENARIOS_DIR / "README.md"
        content = readme_path.read_text()

        assert "pytest" in content, "README should show pytest commands"
        assert (
            "test_advanced_conversation_scenarios" in content
        ), "README should reference the test runner"

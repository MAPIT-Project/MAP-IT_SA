"""Keep generated evaluation reports outside the source checkout."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_report_output(request, tmp_path, monkeypatch):
    """Redirect exporter directories; recorded result input paths stay unchanged."""
    module = request.module
    original = getattr(module, "RESULTS_DIR", None)
    if not isinstance(original, Path):
        return
    output = tmp_path / "reports"
    output.mkdir()
    monkeypatch.setattr(module, "RESULTS_DIR", output)
    # Some exporters bind the destination file when the test module is imported.
    for name in ("RESULTS_FILE", "BASELINE_FILE"):
        value = getattr(module, name, None)
        if isinstance(value, Path) and value.parent == original:
            monkeypatch.setattr(module, name, output / value.name)

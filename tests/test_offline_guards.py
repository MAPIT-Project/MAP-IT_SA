"""Verify the offline runner rejects service subprocesses before they execute."""

import os
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("MAPIT_OFFLINE_TESTS") != "1", reason="Only applies to scripts/test_offline.py"
)


def test_external_subprocess_is_blocked():
    with pytest.raises(OSError, match="External subprocesses are disabled"):
        subprocess.run(["docker", "--version"], check=False)


def test_shell_is_blocked():
    with pytest.raises(OSError, match="External subprocesses are disabled"):
        os.system("true")


def test_make_test_uses_guarded_runner():
    from pathlib import Path

    makefile = Path(__file__).resolve().parents[1] / "Makefile"
    content = makefile.read_text()
    offline_target = content.split("\ntest:\n", 1)[1].split("\n\n", 1)[0]
    assert "scripts/test_offline.py" in offline_target
    assert "$(PYTEST_ARGS)" in offline_target

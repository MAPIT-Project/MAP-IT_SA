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

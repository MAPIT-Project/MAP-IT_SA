#!/usr/bin/env python3
"""Run the isolated checker and atomically save its report for the server owner."""

import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    target = Path("/home/anmar/MAPIT-openstaande-bronnen-status.json")
    result = subprocess.run(
        [
            "/usr/bin/docker",
            "exec",
            "-e",
            "PYTHONPATH=/app",
            "map-it_sa-api-1",
            "python",
            "/app/scripts/check_pending_document_sources.py",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode:
        raise SystemExit("Document source follow-up failed; previous report retained")
    report = json.loads(result.stdout)
    with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, delete=False) as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
        temporary = handle.name
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)


if __name__ == "__main__":
    main()

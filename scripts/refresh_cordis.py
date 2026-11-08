#!/usr/bin/env python3
"""Validate a DET JSON export, then optionally apply and verify a resumable refresh."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("validate", "import", "indexes", "graph", "embeddings", "verify", "cache", "snapshot")


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_manifest(directory, manifest):
    temporary = directory / "manifest.json.tmp"
    with temporary.open("w") as handle:
        os.chmod(temporary, 0o600)
        json.dump(manifest, handle, indent=2)
    temporary.replace(directory / "manifest.json")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def stage_command(stage, export, directory, batch_size, source_task_id=None):
    command = [sys.executable]
    if stage in ("validate", "import"):
        command += [str(ROOT / "scripts/import_cordis_projects.py"), str(export), "--det-json"]
        if stage == "import":
            command.append("--apply")
    elif stage in ("indexes", "cache", "snapshot"):
        command += [str(ROOT / "scripts/cordis_refresh_support.py"), stage]
        if stage == "snapshot":
            command += ["--run-dir", str(directory)]
    elif stage == "graph":
        command += [str(ROOT / "scripts/sync_cordis_graph.py"), "--apply"]
    elif stage == "embeddings":
        command += [
            str(ROOT / "scripts/refresh_project_embeddings.py"),
            "--batch-size",
            str(batch_size),
        ]
    elif stage == "verify":
        command += [
            str(ROOT / "scripts/verify_cordis_refresh.py"),
            str(export),
            "--output",
            str(directory / "verification.json"),
        ]
        if source_task_id is not None:
            command += ["--source-task-id", str(source_task_id)]
    else:
        raise ValueError("Unknown refresh stage")
    return command


def execute_refresh(directory, manifest, *, apply=False, run=subprocess.run):
    export = Path(manifest["export"])
    if digest(export) != manifest["source_sha256"]:
        raise ValueError("Export changed since this run was created; start a new run")
    if not apply and any(stage != "validate" for stage in manifest["stages"]):
        print(
            json.dumps(
                {
                    "status": manifest["status"],
                    "run_dir": str(directory),
                    "message": "Use --apply to resume mutation stages",
                }
            ),
            flush=True,
        )
        return 0 if manifest["status"] == "complete" else 1
    stages = STAGES if apply else ("validate",)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    for stage in stages:
        if manifest["stages"].get(stage, {}).get("status") == "complete":
            continue
        manifest["status"] = "running"
        entry = {"status": "running", "started_at": timestamp(), "log": f"{stage}.log"}
        manifest["stages"][stage] = entry
        write_manifest(directory, manifest)
        print(
            json.dumps({"stage": stage, "status": "running", "run_dir": str(directory)}), flush=True
        )
        # Keep earlier attempts when resuming a failed stage.
        with (directory / entry["log"]).open("ab") as log:
            os.chmod(directory / entry["log"], 0o600)
            log.write(f"\nAttempt started {entry['started_at']}\n".encode())
            try:
                result = run(
                    stage_command(
                        stage,
                        export,
                        directory,
                        manifest["batch_size"],
                        manifest.get("source_task_id"),
                    ),
                    cwd=ROOT,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                failed = result.returncode != 0
            except BaseException:
                entry["status"] = "interrupted"
                manifest["status"] = "interrupted"
                write_manifest(directory, manifest)
                raise
        if not failed and stage == "verify":
            try:
                failed = (
                    json.loads((directory / "verification.json").read_text()).get("complete")
                    is not True
                )
            except (OSError, ValueError):
                failed = True
        entry.update(status="failed" if failed else "complete", finished_at=timestamp())
        if failed:
            manifest["status"] = "failed"
            write_manifest(directory, manifest)
            print(
                json.dumps(
                    {
                        "stage": stage,
                        "status": "failed",
                        "log": str(directory / entry["log"]),
                        "resume": str(directory),
                    }
                ),
                flush=True,
            )
            return 1
        write_manifest(directory, manifest)
    manifest.update(status="complete" if apply else "validated", finished_at=timestamp())
    write_manifest(directory, manifest)
    print(json.dumps({"status": manifest["status"], "run_dir": str(directory)}), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--export", type=Path, help="Downloaded DET JSON outer ZIP")
    source.add_argument(
        "--resume", type=Path, help="Existing run directory; export digest must match"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Import, refresh indexes and verify; default only validates",
    )
    parser.add_argument(
        "--run-dir", type=Path, help="New private run directory; must not already exist"
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--source-task-id",
        type=int,
        help="Optional provenance from CORDIS; never inferred from filenames",
    )
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 100:
        parser.error("batch-size must be between 1 and 100")
    if args.source_task_id is not None and args.source_task_id <= 0:
        parser.error("source-task-id must be positive")
    if args.resume and (args.run_dir or args.source_task_id is not None):
        parser.error("--resume uses its saved run settings")
    lock_path = ROOT / "data/cordis_refresh.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(1, "Another CORDIS refresh runner is active\n")
        if args.resume:
            directory = args.resume.resolve()
            manifest = json.loads((directory / "manifest.json").read_text())
            if manifest.get("version") != 1:
                raise ValueError("Unsupported run manifest version")
        else:
            export = args.export.resolve(strict=True)
            directory = (
                args.run_dir
                or ROOT
                / "data/cordis_runs"
                / (
                    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                    + "-"
                    + uuid.uuid4().hex[:8]
                )
            ).resolve()
            directory.mkdir(parents=True, exist_ok=False, mode=0o700)
            manifest = {
                "version": 1,
                "created_at": timestamp(),
                "export": str(export),
                "source_sha256": digest(export),
                "source_task_id": args.source_task_id,
                "batch_size": args.batch_size,
                "stages": {},
            }
        return execute_refresh(directory, manifest, apply=args.apply)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError):
        raise SystemExit(
            "Refresh could not start; check the run directory, manifest and export"
        ) from None

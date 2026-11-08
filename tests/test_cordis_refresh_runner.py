"""Offline tests: ordering, safe retries, changed exports and targeted cache invalidation."""

import json
from pathlib import Path
import subprocess

import pytest

from scripts.cordis_refresh_support import invalidate_results
from scripts.refresh_cordis import STAGES, digest, execute_refresh


def run_state(tmp_path):
    export = tmp_path / "source.zip"
    export.write_bytes(b"fixed export bytes")
    directory = tmp_path / "run"
    directory.mkdir()
    manifest = {
        "export": str(export),
        "source_sha256": digest(export),
        "batch_size": 50,
        "stages": {},
    }
    return directory, manifest


def fake_runner(directory, seen, fail_stage=None, complete=True):
    def run(command, **kwargs):
        name = Path(command[1]).name
        if name == "import_cordis_projects.py":
            stage = "import" if "--apply" in command else "validate"
        elif name == "cordis_refresh_support.py":
            stage = command[2]
        else:
            stage = {
                "sync_cordis_graph.py": "graph",
                "refresh_project_embeddings.py": "embeddings",
                "verify_cordis_refresh.py": "verify",
            }[name]
        seen.append(stage)
        if stage == "verify":
            (directory / "verification.json").write_text(json.dumps({"complete": complete}))
        return subprocess.CompletedProcess(command, 1 if stage == fail_stage else 0)

    return run


def test_default_only_validates_without_writing_database(tmp_path):
    directory, manifest = run_state(tmp_path)
    seen = []
    assert execute_refresh(directory, manifest, run=fake_runner(directory, seen)) == 0
    assert seen == ["validate"] and manifest["status"] == "validated"


def test_failed_embedding_stage_resumes_without_reimport_or_second_graph_backup(tmp_path):
    directory, manifest = run_state(tmp_path)
    seen = []
    assert (
        execute_refresh(
            directory,
            manifest,
            apply=True,
            run=fake_runner(directory, seen, fail_stage="embeddings"),
        )
        == 1
    )
    assert seen == list(STAGES[:5])
    assert manifest["status"] == "failed"
    assert execute_refresh(directory, manifest, apply=True, run=fake_runner(directory, seen)) == 0
    assert seen == list(STAGES[:5]) + list(STAGES[4:])
    assert manifest["status"] == "complete"


def test_incomplete_verification_never_clears_caches_or_reports_success(tmp_path):
    directory, manifest = run_state(tmp_path)
    seen = []
    assert (
        execute_refresh(
            directory, manifest, apply=True, run=fake_runner(directory, seen, complete=False)
        )
        == 1
    )
    assert seen[-1] == "verify" and "cache" not in seen


def test_changed_source_is_rejected_before_any_resumed_stage(tmp_path):
    directory, manifest = run_state(tmp_path)
    Path(manifest["export"]).write_bytes(b"replaced export")

    def unexpected(*args, **kwargs):
        pytest.fail("No command may run for a changed export")

    with pytest.raises(ValueError, match="Export changed"):
        execute_refresh(directory, manifest, apply=True, run=unexpected)


def test_cache_invalidation_preserves_sessions_and_conversations():
    import fnmatch

    class Cache:
        keys = {
            "stm:conversation",
            "session:abc",
            "result:projects:a",
            "query_plan:hint",
            "merged_projects:abc",
            "result:documents:a",
        }

        def scan_iter(self, match, count):
            return iter([k for k in self.keys if fnmatch.fnmatch(k, match)])

        def delete(self, *keys):
            for key in keys:
                self.keys.remove(key)
            return len(keys)

    cache = Cache()
    invalidate_results(cache)
    assert cache.keys == {"stm:conversation", "session:abc", "result:documents:a"}


def test_inspecting_completed_run_does_not_downgrade_its_status(tmp_path):
    directory, manifest = run_state(tmp_path)
    seen = []
    runner = fake_runner(directory, seen)
    assert execute_refresh(directory, manifest, apply=True, run=runner) == 0
    assert execute_refresh(directory, manifest, run=runner) == 0
    assert manifest["status"] == "complete"
    assert seen == list(STAGES)

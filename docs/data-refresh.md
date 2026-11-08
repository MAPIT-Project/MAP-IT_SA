# Refreshing MAPIT's data

MAPIT has three separate data pipelines. Refreshing one does not update the
others. Run commands from the repository root, with the API container running
(`docker compose up -d`). The container loads the configured database, CORDIS,
Redis, Neo4j and embedding credentials; never put keys in command arguments or
commit `.env`, exports, backups or run logs.

| Data | Refresh command | Details |
|---|---|---|
| Horizon Europe projects and consortium organisations | `make refresh-cordis CORDIS_ARGS='--export data/cordis_exports/FILE.zip --apply'` | [CORDIS runbook](cordis-refresh.md): export, backup, PostgreSQL, graph, vectors, verification and caches |
| Open/upcoming funding calls | `docker compose exec -T -e PYTHONPATH=/app api python scripts/sync_funding_calls.py` | [Call catalogue](call-catalogue.md): official Funding & Tenders source, freshness and scheduling |
| New or revised official PDFs | Reviewed manifest, then the document commands below | [Document revision runbook](document-revision-refresh.md) and [provenance](document-provenance.md) |

## Funding calls

```bash
docker compose exec -T -e PYTHONPATH=/app api python scripts/sync_funding_calls.py --health
docker compose exec -T -e PYTHONPATH=/app api python scripts/sync_funding_calls.py
docker compose exec -T -e PYTHONPATH=/app api python scripts/reembed_funding_calls.py --limit 500 --batch-size 20
docker compose exec -T -e PYTHONPATH=/app api python scripts/sync_funding_calls.py --health
```

The embedding limit is per run. Repeat the backfill while applicable calls still
lack vectors; a successful catalogue fetch alone does not prove vector coverage.
The existing systemd unit templates are in `scripts/systemd/mapit-call-catalog.*`.
Their presence in the repository does not prove that a timer is installed or
active. Inspect `systemctl status mapit-call-catalog.timer` on the host before
claiming automatic refreshes. Do not enable a second overlapping schedule.

## Official documents

Discover and audit source versions, retain PDFs and extraction evidence, and
prepare a reviewed manifest as described in the document revision runbook.
Different PDF bytes or an HTTP modification date alone do not establish a newer
legal edition. Keep unresolved documents in the pending-review workflow.

```bash
# Replace PATH_TO_REVIEWED_MANIFEST with a path available inside the container.
docker compose exec -T -e PYTHONPATH=/app api python scripts/apply_document_refresh.py PATH_TO_REVIEWED_MANIFEST
docker compose exec -T -e PYTHONPATH=/app api python scripts/apply_document_refresh.py PATH_TO_REVIEWED_MANIFEST --apply
docker compose exec -T -e PYTHONPATH=/app api python scripts/sync_verified_document_revisions.py PATH_TO_REVIEWED_MANIFEST
```

Take the database backups specified in the document runbook before publication.
The final command mirrors verified publications into the call-specific document
store. It does not discover or approve documents. Keep previous annual editions
available for the calls they govern, and verify retrieval against the intended
programme year after publishing.

## Completion and recovery

For CORDIS, completion means the run manifest says `complete` and
`verification.json` says `complete=true`. A download or successful import is an
intermediate stage. [The CORDIS runbook](cordis-refresh.md) explains retries,
backups, logs and the precise coverage of the final checks. The final snapshot
record also makes the real import date available to project/partner answers.

For calls, retain the sync/freshness results and check the vector backlog. For
documents, retain publication results, reviewed source/version evidence and
retrieval checks. Preserve these records so the import date can be distinguished
from each source record's own update date.

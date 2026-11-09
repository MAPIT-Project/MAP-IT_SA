# Public reference document lifecycle

Normal research retrieval now requires an established origin for public-library
publications. This is a source-quality rule, separate from whether a particular
edition applies to a call or a legal question.

## States and retrieval

- **Verified and active:** eligible for ordinary reference searches. Currently
  accepted PDF-origin states are `verified_exact_bytes` and
  `verified_official_download`. Historical verified editions remain searchable
  for their own period; verification does not imply they are the latest edition.
- **Pending review:** publication dates, document identity or legal revision
  evidence still need review. These records are excluded from ordinary retrieval.
  Relevant pending cost/LIFE warnings continue to be returned separately by the
  document research tool, so lack of usable evidence is not mistaken for absence
  of a document or a new rule.
- **Quarantined:** origin could not be established. General-library records are
  archived; shared-library records carry `metadata.retrieval_status=quarantined`.
  Their original files (where available), text, vectors, metadata and call mappings
  remain retained. The dashboard includes these under Archived.
- **Superseded:** prior editions remain retained and excluded as before.

The database predicate `mapit_public_source_searchable` enforces the public-source
rule. Semantic, keyword and hybrid RPCs apply it before candidate limits; call
mapping counts, cached document lists and work-programme fallback use it too.
The existing owner distinction is preserved for documents with `created_by` set.
The inventory presents new active-but-unverified public records as Pending review,
not as searchable material. Supplying a source URL or client metadata is not
verification; both file and web ingestion keep those claims unverified.

## Install the retrieval policy

Apply `scripts/sql/20261109_verified_document_retrieval.sql` to each database
**before deploying the Python changes**. It is transactional, preserves existing
RPC signatures and can be reapplied. Back up the existing function definitions
before applying a migration in a separate environment.

The production database was migrated on 9 November 2026; its private prior
function definitions are retained with the audit artifacts.

## Routine maintenance

After importing public references, or when investigating gaps:

1. Discover candidates from official publication pages. Run
   `scripts/verify_document_origins.py` against explicit candidate URLs. Inspect
   its dry run, then use `--apply` for exact-byte matches. See
   [document provenance](document-provenance.md#verify-legacy-records-that-lack-origins).
2. Compare nonmatching editions and recover originals where possible. Publish
   reviewed replacements through the existing
   [revision refresh](document-revision-refresh.md) workflow. Never transfer a
   previous edition's verification to different bytes.
3. Preview unresolved-record quarantine:

   ```bash
   docker compose exec -T -e PYTHONPATH=/app api \
     python scripts/quarantine_unresolved_documents.py \
     --output tmp/document-maintenance/quarantine.json
   ```

4. Inspect the planned titles/IDs and repeat with `--apply`. Each run records
   original and expected post-update states in a private `.before.json` backup.
   Hash, metadata and status guards make the change atomic and reject stale
   records. Pending reviews, verified historical publications, user-owned records
   and already quarantined records are excluded. A repeat run is a no-op.
5. Check the dashboard and retrieval results. Keep unresolved pending reviews
   visible; use `scripts/check_pending_document_sources.py` for read-only follow-up.

Use a new output path for each maintenance run. Audit reports and backups must
remain outside Git and Docker images. Quarantine never deletes chunks or mappings.

New call-document downloads use separate filenames and content-specific keys.
A duplicate import preserves the existing record and chunks. An existing
unreviewed/quarantined URL is not silently re-downloaded over its retained copy.
New staged downloads stay out of reference retrieval until verified or published
through the reviewed revision workflow.

## Reconsidering a quarantined record

Recover the official original or identify a reviewed replacement first. For a
replacement, use the revision-refresh workflow and retain the old quarantined
record. If the original is recovered, select only its entries from the private
backup and preview restoration:

```bash
docker compose exec -T -e PYTHONPATH=/app api \
  python scripts/quarantine_unresolved_documents.py \
  --restore tmp/document-maintenance/selected.before.json \
  --output tmp/document-maintenance/restore.json
```

Repeat with `--apply` to restore the selected original metadata/status. Restoration
checks that the record still matches the quarantined post-state. It does not
establish provenance: normal public retrieval remains blocked until a source
verification pass establishes the matching origin. A subsequent quarantine pass
will retire a restored record if its origin is still unresolved.

To roll back retrieval policy itself, restore the saved pre-migration RPC
function definitions together with the corresponding application code. Do not
remove the shared predicate while running application code that calls it.

## Applied cleanup and validation

The 9 November cleanup quarantined 30 raw records, representing 15 combined
inventory entries: the 13 unresolved-origin entries and two unresolved historical
revision warnings. Repeated legacy imports are retained in that archive rather
than occupying ordinary search results. No existing verified publication or
pending review was retired.

After cleanup the inventory has **156 active searchable records, all with verified
origins; 69 archived entries; and six pending reviews**. These are combined
inventory entries, not necessarily unique PDFs. The earlier
[source audit](source-verification-2026-11-09.md) records why the gaps remain.

Sixty-nine focused tests passed. Live keyword retrieval returned 50 verified
active results; semantic and hybrid retrieval each returned 20 verified active
results. Health 2027 work-programme fallback remained available, and five existing
call caches returned only verified publications. Quarantine/restore and stale-row
rollback were exercised against isolated temporary database tables. A second
quarantine run planned zero changes. No model inference was required for these
checks.

The production HTTPS dashboard was also checked with a disposable account: 156
searchable records, 69 archived, six pending, verified badges in active results,
and a visible reason on a quarantined legacy guide. The account was removed.

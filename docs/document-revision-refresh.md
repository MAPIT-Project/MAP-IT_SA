# Official document revision refresh

The 8 November 2026 audit confirmed that the original Horizon PDF folders came
from the Funding & Tenders reference library. The collection lacked the main
2026–2027 work programmes, and multiple evergreen manuals and forms had newer
official downloads. Historical annual editions remain valid for their own calls.

## Publication workflow

1. Download from explicit official HTTPS hosts and retain the original files.
2. Compare PDF bytes, extracted text, document identity, edition and change history.
   Different bytes alone are not evidence of a newer substantive revision.
3. Review the manifest. Reject redirect-placeholder PDFs and unresolved current
   publication dates, such as `xx.xx.2026`. Keep unknown sources explicit.
4. Back up `horizon_documents`, `document_chunks`, `shared_documents`,
   `shared_document_chunks`, `call_document_mappings` and the search RPC definitions.
5. Run `scripts/apply_document_refresh.py MANIFEST` for a dry run, then `--apply`.
   Run inside the API environment with `PYTHONPATH=/app`.
6. Run `scripts/sync_verified_document_revisions.py MANIFEST...` to mirror the
   verified publications into the call-specific store and move same-edition
   mappings to the replacement. Old records are retained with `superseded_by`.

The reviewed manifest records the exact PDF SHA256 and extracted-page digest,
source URL, year, version evidence, original record IDs and their expected hashes.
All embeddings must validate before publishing. Publication and archival of its
same-edition predecessors occur in a single transaction; an unexpected predecessor
hash rolls back the entire document. Embedding checkpoints allow safe retry.
New annual programmes have no predecessors to archive. The importer uses a
database advisory lock and skips already-published content hashes on rerun.

The private run artifacts are under `tmp/document-refresh-20261108/` (locally
excluded from Git), including a PostgreSQL custom-format backup, comparison
evidence, approved/deferred manifests and execution logs. Original PDFs in
`newdocs/` remain available for historical reference and recovery.

## Search and call routing

Apply `scripts/sql/20261108_document_revision_search.sql`. It preserves the RPC
interfaces while matching a requested year within multi-year document editions,
returning parent provenance in semantic results, and filtering active revisions
before hybrid retrieval limits. Otherwise old archived vectors could consume the
candidate window and hide the replacement.

Document tool results include the stored source URL, edition, programme year,
verification status and page. A work-programme/topic query with one explicit year
uses that year; evergreen guidance queries remain eligible for undated manuals.

Call document keys and versions are derived from `/wp-call/YEAR/`, rather than
being hardcoded to 2023–2025. WP parts 4–9 correspond to Clusters 1–6; part 13
(New European Bauhaus) must not be classified as general annexes. The cluster
fallback requires the work programme to cover the call year and recognises HLTH
as Cluster 1. Cached mappings lacking that edition are refreshed.

## Validation and limits

Tests cover source and extraction tampering, official-host lookalikes, framework
versus document periods, WP part/cluster classification and the NEB annex error.
The live refresh also checked transaction rollback when a predecessor changed,
valid nonzero 3072-dimensional vectors, page-number coverage and retrieval of
HORIZON-HLTH-2027-03-TOOL-08 from the Health 2026–2027 programme, pages 173–175.

This is a reviewed refresh, not unattended approval of every future official
download. Placeholder dates and unresolved sources still need review. Source
provenance does not by itself prove that every generated answer claim is supported.

## Follow-up source investigation

Creative Europe 2027 and Erasmus+ 2027 were subsequently added in both stores,
bringing the PDF refresh to 76 publications. The Creative Europe site uses an
`eac-download` element with a `url` attribute, not an ordinary anchor. The pure
parsers in `app/services/document_source_discovery.py` recognise this and select
the actual Cellar PDF item from RDF metadata rather than its cover thumbnail.
All discovery results still require PDF identity and hash verification.

Erasmus+ is a multilingual publication. Only the English decision and programme
(physical PDF pages 1–7 and 18–214) were indexed; page numbers remain aligned
with the original 229-page PDF. The original PDF is retained unmodified.

Three formerly unresolved downloads were found under their correct reference
paths: the two grant-preparation forms use `common/temp-form/gap/`, and the staff
mobility decision uses `euratom/guidance/`. Both forms match the original files
exactly. The mobility decision contains the same unresolved `xx.xx.2026` date as
the other four cost decisions, so there are now five pending legal revisions.

`scripts/record_document_source_reviews.py MANIFEST [--apply]` records this
evidence. Candidate PDFs remain archived, without searchable chunks; they are
not silently approved. Relevant document searches separately return pending
source reviews and an instruction to disclose the limitation. This is context
for the answer generator, not a claim-verification guarantee.

The public Commission register confirms LIFE amendment C(2026)4323 as final on
25 June 2026. Its English attachment metadata has no downloadable `ersId`.
An initial Circabc request incorrectly used `/nodes/ID/children`, which returned
401. This was not proof that the documents were private. The website's public
route `/spaces/ID/children?guest=true` returns the library without credentials;
direct UI links returning 404 likewise do not establish document access rights.
The discovery helper now constructs and tests the correct public route and only
selects PDF entries with `currentUserHasAccess=true`. Files are downloaded from
their standard public `/sd/a/ID/FILENAME` URLs. No authentication or access-request
form is used.

All ten public LIFE PDFs were retrieved: the original multiannual programme,
three original financing annexes, three October 2025 amendment annexes and three
June 2026 amendment annexes. Nine were newly indexed in both stores; the existing
multiannual programme was verified and its year range corrected to 2025–2027.
The earlier annexes remain available because amendments replace selected clauses,
not the whole source text. The separate main text of C(2026)4323 has not been
located; the three substantive amendment annexes are available. The searchable
register notice and source warnings now distinguish this limited missing text
from the verified PDF annexes, and no longer claim that all annex text is absent.

The follow-up manifests, raw publisher metadata and execution evidence are in
`tmp/document-refresh-followup-20261108/`, excluded from Git and Docker context.

## Following up the six remaining source questions

`scripts/check_pending_document_sources.py` uses a read-only database session and
checks the five pending PDF hashes, the main LIFE document's public register
download reference, and newly listed public Circabc files. Changed bytes and new
download references are candidates for review; they never activate a revision or
prove a publication date. Checks that fail remain explicitly unavailable.

On this server the owner's crontab runs
`scripts/check_pending_document_sources_host.py` daily at 06:45 UTC. It atomically
saves a private report at `/home/anmar/MAPIT-openstaande-bronnen-status.json`.
A failed process retains the prior report. Cron's log is
`/home/anmar/MAPIT-bronnencontrole.log`; no email or access request is sent.
The previous crontab was backed up with the private audit artifacts.

The latest check found the five PDFs unchanged and no newly public main LIFE
text. A draft Commission document request covering the six exact source questions
is prepared at `/home/anmar/MAPIT-verzoek-ontbrekende-EC-documenten.txt`. It has not
been submitted. Publication dates or missing decision text must come from the
publisher; the checker does not manufacture or infer them from HTTP timestamps.

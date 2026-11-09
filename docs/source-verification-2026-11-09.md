# Legacy source verification — 9 November 2026

The dashboard exposed provenance gaps in earlier imports: an indexed PDF could
have no original download URL or verification metadata. This status is distinct
from a source being unofficial, incorrect, or the latest applicable edition.

Exact PDF SHA256 comparisons against official downloads resolved 33 raw library
records, which represent 32 combined dashboard entries. No text or embeddings
were replaced. Records were guarded by their original hash and metadata and a
private backup was saved before publication.

| Active dashboard entries | Before | After |
| --- | ---: | ---: |
| Verified PDF origins | 124 | 156 |
| Origin not yet verified | 45 | 13 |
| Revision warnings | 2 | 2 |

The six pending review entries and 54 archived entries retain their separate
states. Total active searchable entries remain 171.

Matches include historical Horizon work programmes and guidance, Creative Europe
annual programmes and strand overviews, Erasmus+ 2026 guidance, Digital Europe
work programmes, and EU4Health annual programmes. Publication pages used include
[Creative Europe documents](https://culture.ec.europa.eu/resources/document-library),
[Digital Europe work programmes](https://digital-strategy.ec.europa.eu/en/activities/work-programmes-digital),
and [EU4Health programmes](https://hadea.ec.europa.eu/programmes/eu4health/eu4health-annual-work-programmes_en).

## Remaining origin gaps

Thirteen combined entries still lack a verified origin:

- Creative Europe 2022 annual work programme: the tested official download has
  different bytes from the stored edition; a revision/content comparison is needed.
- Digital Europe October 2025 amendment decision and Erasmus+ 2026 annual work
  programme: no exact downloadable match established in this pass.
- EU4Health, Digital Europe and LIFE regulations: tested EUR-Lex PDF endpoints
  did not return a verifiable matching PDF to the checker. This does not mean
  the legislation is unavailable or unofficial.
- Horizon Europe Programme Guide and LIFE priority topics 2021–2024: no exact
  current-download match established for the stored editions.
- Five combined legacy checksum groups (Horizon regulation, programme guide and
  general introductions) use 32-character legacy identifiers rather than stored
  PDF SHA256. Their original file/content hashes need reconciliation before an
  origin can be established. These groups include repeated raw imports.

The two active revision warnings concern the stored lump-sum decision and LIFE
priority topics 2025–2027. A fresh official-source check found the five pending
cost-decision PDFs unchanged, still with unresolved publication dates. The LIFE
register still lacks the reviewed English main-text attachment. Those six reviews
remain pending rather than being approved based on download availability.

## Reproduction and validation

Use `scripts/verify_document_origins.py`; instructions are in
[document provenance](document-provenance.md#verify-legacy-records-that-lack-origins).
Private discovery evidence, candidate URLs, per-download results, update reports
and backups are under `tmp/source-verification-20261109/`, excluded from Git and
Docker images. A zero-match follow-up changed no records.

Twenty-five focused tests passed for exact matching, official-host restrictions,
non-PDF responses, pending/warning preservation, stale-record rollback, private
audit files, discovery and dashboard inventory. The dashboard reads persisted
verification metadata; use Refresh after the short API cache expires.

## Subsequent lifecycle cleanup

The counts above describe the verification pass before quarantine. The remaining
13 origin gaps and two unresolved historical revision warnings were subsequently
retained in the archive, with backups and guarded restoration. Normal retrieval
now excludes them. See [document lifecycle](document-lifecycle.md) for current
counts and validation; the six pending reviews remain separate.

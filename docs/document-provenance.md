# Document origins and verification

The manually downloaded Horizon folders closely match the categories on the
[official Reference documents page](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents?frameworkProgramme=43108390&programmePeriod=2021-2027).
This page is also referenced in the application. This is evidence for the likely
landing page, not proof of the historical origin of every local file.
Other programmes have separate sources listed in
`docs_tracked/EU_PROGRAMME_DATA_DOWNLOADS.md`.

## Reproducible source register

Run from the repository root, using an inventory containing `local_pdf_files`
and `shared_documents` (see the 2026-11-08 private inventory):

```bash
python3 scripts/audit_document_sources.py path/to/inventory.json tmp/document-sources.json --verify
```

The JSON and Excel-compatible CSV register include every local PDF, its SHA256,
indexed record matches, candidate download links and verification results.
Without `--verify`, no network requests occur. Downloads are restricted to HTTPS
on ec.europa.eu, including redirects; capped at 50 MB with two concurrent requests.
Only identical downloaded and local SHA256 values produce `verified_exact_bytes`.
Different bytes mean `different_content_or_revision`, never a confirmed source.
Unavailable links and missing source information remain explicit. No database,
document, approval or retrieval status is changed by the audit.

Application and evaluation form candidates follow official portal path patterns;
they remain guesses until their bytes match. A link currently serving a different
revision must not be treated as the source of the indexed historical text.

## New uploads

`POST /api/documents/upload` accepts an optional `source_url` query parameter,
alongside the existing upload parameters. It preserves the HTTPS link in the
document record and records `metadata.provenance.status=unverified`. Missing
origins are `source_unknown`. Client metadata cannot override this status during
file ingestion. This change does not claim that uploads are reviewed or approved.

## Limits and further work

The source register is an audit artifact, not an automatic update service or a
source-only answer policy. The reviewed 8 November refresh now retains historical
revisions and exposes source URLs, verification status, pages and versions in
document tool results; see `docs/document-revision-refresh.md`. Existing unknown
documents are not silently approved or removed. Automatic discovery/approval of
future revisions and checking whether every answer claim is supported remain
separate work. Model training, an SLM architecture, and guaranteed factual
correctness cannot be inferred from a restricted retrieval corpus.

# CORDIS refresh completed — 8 November 2026

The Horizon Europe project/consortium refresh completed and was verified at
22:25 UTC. The newest source record is dated **7 November 2026, 19:55:38**.
This source date is separate from today's import date.

| Measure | Verified result |
|---|---:|
| Projects in PostgreSQL and Neo4j | 24,471 |
| Distinct organisations | 36,202 |
| Organisation participation records | 151,627 |
| Distinct organisation–project pairs, matching across both databases | 151,333 |
| Derived collaboration links | 140,010 |
| Eligible projects with completed semantic vectors | 24,441 / 24,441 |
| New or refreshed vectors saved during this run | 18,189 |
| Regression tests passed | 58 |

The current DET JSON export (task 188653300) contains 24,470 projects and
151,619 participation records. The importer applied 24,331 project records and
preserved 139 newer source versions already held locally. It retained one
existing project outside the export and its consortium data. Stored imported
project/consortium source fields were compared against the JSON export with no
mismatches. The CSV companion was rejected because of malformed quoting; no
heuristic repair was used.

Project text changes invalidated 7,607 old vectors. Missing and invalidated
vectors were regenerated with the configured embedding model. Thirty projects
fall outside the existing title/objective length requirements for semantic
indexing; their source records remain in the database. Keyword and consortium
lookup indexes were built. Eleven cached plan hints were removed; conversations
and sessions were preserved.

Production repository lookup of newly added project 101225119 succeeded.
Keyword search, semantic search and Dutch partner discovery all returned results.
The API readiness endpoint returned HTTP 200. The final deterministic audit
reported `complete=true` and no problems.

Private PostgreSQL/vector/consortium and Neo4j backups are saved under
`data/cordis_backups/`; both compressed files passed integrity checks. Detailed
reports are under `tmp/cordis-refresh-*`, including the source digest, backup
digests, import result, graph refresh, embedding progress and verification JSON.

This refresh covers the downloaded Horizon Europe CORDIS snapshot. It does not
claim coverage of every EU programme or configure automatic future refreshes.
See [the repeatable procedure](cordis-refresh.md).

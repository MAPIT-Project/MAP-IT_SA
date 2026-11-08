# MAPIT demo readiness — checked 8 November 2026

This report records a limited, reproducible check for the 9 November evaluation.
It supports the [demo guide](README.md), not a claim of universal correctness,
completion of contractual KPIs, or a security certification.

## What was exercised

- **15 original research-question cases:** all returned answers without provider or
  transport errors using the configured Codex `gpt-6.1-sol` provider. Questions
  covered calls, dates/budgets, consortium/funding rules, country eligibility,
  projects, partners, missing information, document editions, pending revisions,
  policy-source limitations and requests for guarantees.
- **Additional exact English demo prompts:** partner discovery, topic dates/budget
  and a fictional proposal outline returned answers. The partner prompt was run
  again after the final provenance and language corrections.
- **Real public HTTPS flow:** anonymous dashboard redirect, fresh login, secure
  session cookies, protected dashboard, client profile, personal conversation,
  chat proxy, tool events and streamed answer all succeeded on `new.mapit.work`.
  Temporary accounts, profile and conversation were removed. No real user's
  password was changed. There was no browser-click or visual-layout automation.
- **Software regression suite:** 169 cases collected, **167 passed**, two isolated
  database-integration cases intentionally skipped by the offline runner; no failures
  or errors. Those database import behaviours were separately exercised during the
  CORDIS refresh. The API readiness endpoint returned HTTP 200.
- **Core document coverage:** eight selected source records remained active with
  chunks and provenance: Health work programme 2026–2027, General Annexes, AGA,
  participating-country list, Programme Guide, AI Act, EHDS and GDPR. This is a
  checked subset, not a complete corpus audit.

## Observed behaviours

| Case | Observation | Limit of the check |
|---|---|---|
| AI/health 2027, Dutch | Relevant topic IDs and official links; direct/broader relevance distinguished | Titles/keywords do not establish complete eligibility |
| AI/health 2027, English | Comparable shortlist and RIA/CSA distinction | Ranking and wording may change |
| Two-stage topic dates/budget | Both stages and topic/per-project amounts distinguished; official document/page cited | No award or individual eligibility guarantee |
| Ordinary RIA consortium | Independence/country requirements plus EU-member participation explained with source | Topic-specific restrictions still require review |
| IA funding-rate question | Commercial/non-profit distinction and eligible-cost qualification | Not an assessment of a specific applicant |
| Japan participation/financing | Participation separated from financing; transition conditions flagged | No complete country-specific legal determination |
| Project examples | Real IDs/links and refreshed snapshot figures | Local snapshot, not a live exhaustive register |
| Dutch partners | Specific project memberships/roles used, including distinctions between similarly named institutions | No proof of current partner availability |
| Invented call | No verified date or budget supplied | Failed retrieval does not prove nonexistence |
| Invented declaration | No fabricated summary or binding obligations | Nearby real documents are not substitutes for that declaration |
| Document edition | Applicable stored Health edition/version/source identified | Does not establish every referenced policy is indexed |
| Pending cost revisions | Unconfirmed dates disclosed | Five legal revisions remain unresolved |
| AI Act / EHDS | Original-publication status and incomplete applicability checks disclosed | No fully consolidated current-law claim |
| GDPR / health research | Funding not treated as automatic permission; source qualifications retained | No individual legal approval |
| Funding/completeness guarantees | Both guarantees declined | An appropriate refusal is not a model-wide accuracy estimate |

The original 15 cases took 8.2–46.7 seconds each (median 23.1 seconds), under the
conditions of this run. Successful completion and the observations above are
**not** a measured factual-accuracy percentage or a blinded evaluation.

## Fixes and evidence completed during preparation

1. Refreshed CORDIS projects and consortium data; checked source fields and
   PostgreSQL/Neo4j identities; regenerated all eligible missing/invalidated
   vectors. [Refresh report](../cordis-refresh-2026-11-08.md).
2. Added a repeatable validated refresh runner, backups, recovery guidance and
   verification. [Data refresh](../data-refresh.md).
3. Published verified snapshot provenance for answers: actual import timestamp,
   source date, export digest/count, and explanation of the retained extra project.
   Unknown or mismatched metadata does not silently establish an import date.
4. Kept English coverage notes in English during the English demo prompt.
5. Reset the model's confidence estimate when the deterministic unavailable-evidence
   safeguard replaces an unsupported answer; tested a deliberately invented answer.
6. Synced the app's separate Codex login with the user's selected account and
   successfully reran the previously quota-blocked question checks.
7. Checked the live login/proxy/stream path with disposable data and cleaned it up.

The November maintenance and refreshes must not be described as proof of which
features existed at an earlier project milestone. Repository commit dates are
implementation evidence; the V1 feedback record, signed deliverables and approved
reporting records define the project's actual development/effort narrative.

## Remaining checks and known limits

- The presenter and any colleagues participating live should log in using their
  own intended browser/account. A disposable-account test does not verify each
  named user's password, session or browser setup.
- The separate proposal-editor/session workflow, collaboration UI, exports and
  every feature in the Canva deck were not rehearsed in this check. Use the
  tested chat drafting outline if demonstrating writing assistance.
- The Canva connector required reauthentication and the shared shortlink was not
  publicly readable through the available tools. The slides were not inspected.
- Five cost-revision publication dates and the separate main text of LIFE
  C(2026)4323 remain pending. Legal originals are not consolidated-current-law
  guarantees. These limitations remain visible rather than being guessed away.
- No quantified user time savings, adoption impact, grant-success uplift or cost
  eligibility conclusion was established by this technical readiness work.

## Reproducible evidence

Private artifacts are under `tmp/readiness-final-20261108/`:
`rechecked.json`, `remaining.json`, `demo-en.json`, `demo-partners-final.json`,
`coverage.json`, `frontend-login.json`, `frontend-stream.json` and the streamed
answer. Software results are in `tmp/readiness-final-tests.xml` and its log.
Export/backup/source digests are retained with the CORDIS refresh artifacts.

Repeat selected core questions after changes or before presenting:

```bash
docker compose exec -T -e PYTHONPATH=/app api python scripts/evaluate_readiness.py \
  --case ai_health_en --case projects --case partners --case missing_call \
  --output tmp/readiness-recheck.json
```

This uses real generation and retrieval, without creating application conversations.
It requires a working selected account and embedding credentials. The separate
HTTPS smoke check above exercised application storage using disposable records.

Project context: [MAPIT, grant 101158945](https://cordis.europa.eu/project/id/101158945)
identifies conversational partnership discovery within the project's roadmapping
strand. The demo illustrates that workflow; it does not independently establish
the project's broader impact or fulfilment of all work-package obligations.

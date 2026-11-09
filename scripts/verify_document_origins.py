#!/usr/bin/env python3
"""Verify legacy PDF origins by exact official-download SHA256, without changing text.

Dry run by default. Additional candidate URLs must be a JSON list of explicit
URLs discovered on official publication pages; guessed URLs are never proof.
Only byte-identical downloads can verify an eligible stored hash. Pending legal
reviews and revision warnings are excluded, even when the PDF can be downloaded.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from app.core.config import settings
from app.services.document_source_discovery import OFFICIAL_PUBLISHERS, official_https_url
from scripts.check_pending_document_sources import fetch

UNVERIFIED = {'', 'source_not_verified', 'source_unknown', 'unverified'}
TABLES = {'horizon_documents': 'source_url', 'shared_documents': 'document_url'}


def eligible(row):
    metadata = row.get('metadata') or {}
    return (row.get('status', 'active') == 'active'
            and not metadata.get('superseded_by')
            and metadata.get('review_state') != 'pending'
            and (metadata.get('provenance') or {}).get('status', '') in UNVERIFIED
            and not (metadata.get('provenance') or {}).get('warning'))


def checked_download(url):
    try:
        body = fetch(url)  # HTTPS host/redirect allowlist, size and timeout limits.
        if not body.startswith(b'%PDF-'):
            return {'url': url, 'status': 'not_pdf'}
        return {'url': url, 'status': 'downloaded', 'sha256': hashlib.sha256(body).hexdigest()}
    except Exception as exc:
        return {'url': url, 'status': 'unavailable', 'error_type': type(exc).__name__}


def verified_updates(rows, checks, checked_at):
    by_hash = {}
    for check in checks:
        if (check.get('status') == 'downloaded'
                and official_https_url(check['url'], check['url'], OFFICIAL_PUBLISHERS)):
            by_hash.setdefault(check['sha256'], check['url'])
    updates = []
    for row in rows:
        url = by_hash.get(row.get('file_hash'))
        if not eligible(row) or not url:
            continue
        updates.append({**row, 'verified_url': url, 'provenance': {
            **((row.get('metadata') or {}).get('provenance') or {}),
            'status': 'verified_exact_bytes', 'verified_at': checked_at,
            'verification_method': 'official_https_download_sha256',
            'sha256': row['file_hash'],
            'scope': 'Exact PDF origin verified; current edition and applicability require separate checks.',
        }})
    return updates


def apply_updates(conn, updates):
    # All records update together; changed hashes/metadata roll back the run.
    with conn:
        with conn.cursor() as cursor:
            for row in updates:
                table = row['store']
                if table not in TABLES:
                    raise ValueError('Unknown document store')
                column = TABLES[table]
                active_guard = " AND status='active' AND created_by IS NULL" if table == 'horizon_documents' else ''
                cursor.execute(
                    f"UPDATE {table} SET {column}=%s,metadata=jsonb_set(COALESCE(metadata,'{{}}'::jsonb),'{{provenance}}',%s::jsonb) "
                    "WHERE id=%s AND file_hash=%s AND COALESCE(metadata,'{}'::jsonb)=%s::jsonb" + active_guard,
                    (row['verified_url'], Json(row['provenance']), row['id'], row['file_hash'], Json(row.get('metadata') or {})),
                )
                if cursor.rowcount != 1:
                    raise ValueError('Document changed after source audit; transaction rolled back')


def save_private(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with open(temporary, 'w', opener=lambda p, flags: os.open(p, flags, 0o600)) as handle:
        os.chmod(temporary, 0o600)
        json.dump(data, handle, indent=2, default=str)
        handle.write('\n')
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, help='JSON list of official candidate URLs')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    rows = []
    with closing(psycopg2.connect(settings.database_url)) as conn:
        conn.set_session(readonly=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id,title,file_hash,metadata,source_url,status FROM horizon_documents WHERE created_by IS NULL AND status='active'")
            rows.extend({**dict(r), 'store': 'horizon_documents'} for r in cursor.fetchall())
            cursor.execute("SELECT id,document_title AS title,file_hash,metadata,document_url AS source_url,'active' AS status FROM shared_documents")
            rows.extend({**dict(r), 'store': 'shared_documents'} for r in cursor.fetchall())
    rows = [r for r in rows if eligible(r)]
    urls = {r['source_url'] for r in rows if r.get('source_url')}
    if args.candidates:
        candidates = json.loads(args.candidates.read_text())
        if not isinstance(candidates, list) or not all(isinstance(u, str) for u in candidates):
            parser.error('Candidates must be a JSON list of URL strings')
        urls.update(candidates)
    if len(urls) > 250:
        parser.error('At most 250 candidate URLs per run')
    urls = sorted(u for u in urls if official_https_url(u, u, OFFICIAL_PUBLISHERS))
    with ThreadPoolExecutor(max_workers=2) as pool:
        checks = list(pool.map(checked_download, urls))
    checked_at = datetime.now(timezone.utc).isoformat()
    updates = verified_updates(rows, checks, checked_at)
    report = {'checked_at': checked_at, 'checks': checks, 'eligible_records': len(rows),
              'matched_records': len(updates), 'applied': False,
              'updates': [{k: r[k] for k in ['store', 'id', 'title', 'file_hash', 'verified_url', 'provenance']} for r in updates],
              'unmatched': [{k: r[k] for k in ['store', 'id', 'title', 'file_hash']} for r in rows if (r['store'], r['id']) not in {(u['store'], u['id']) for u in updates}]}
    save_private(args.output, report)
    if args.apply and updates:
        save_private(args.output.with_suffix('.before.json'), updates)
        conn = psycopg2.connect(settings.database_url)
        try:
            apply_updates(conn, updates)
        finally:
            conn.close()
        report['applied'] = True
        save_private(args.output, report)
    print(json.dumps({k: report[k] for k in ['eligible_records', 'matched_records', 'applied']}))


if __name__ == '__main__':
    main()

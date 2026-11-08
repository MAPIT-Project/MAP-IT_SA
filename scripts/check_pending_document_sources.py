#!/usr/bin/env python3
"""Read-only follow-up of unresolved official publications. Never approves sources."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.services.document_source_discovery import (
    OFFICIAL_PUBLISHERS,
    circabc_public_folder_url,
    extract_circabc_public_pdfs,
    official_https_url,
)

LIMIT = 20 * 1024 * 1024
LIFE_FOLDER = "ce976713-0506-4fd0-b19a-6f4dc6c23fe6"


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official_https_url(newurl, req.full_url, OFFICIAL_PUBLISHERS):
            raise ValueError("Redirect outside official HTTPS publishers")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    if not official_https_url(url, url, OFFICIAL_PUBLISHERS):
        raise ValueError("Untrusted source URL")
    request = Request(url, headers={"User-Agent": "MAPIT-source-followup/1.0"})
    with build_opener(OfficialRedirects()).open(request, timeout=20) as response:
        data = response.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError("Source exceeds size limit")
        return data


def compare_pdf(data, approved_hash):
    if not data.startswith(b"%PDF-"):
        raise ValueError("Source did not return a PDF")
    digest = hashlib.sha256(data).hexdigest()
    return {
        "status": "unchanged_pending" if digest == approved_hash else "changed_requires_review",
        "download_sha256": digest,
    }


def check_source(row):
    result = {"title": row["title"], "source_url": row["source_url"]}
    try:
        body = fetch(row["source_url"])
        if row["source_type"] == "pdf":
            result.update(compare_pdf(body, row["file_hash"]))
        else:
            register = json.loads(body)
            main = next(a for a in register["attachments"] if a.get("main"))
            ers_id = (main.get("linguisticVersions", {}).get("en") or {}).get("ersId")
            result["status"] = (
                "download_available_requires_review" if ers_id else "main_text_pending"
            )
            if ers_id:
                reference = quote(register["reference"] + "_" + str(main["sequence"]), safe="")
                result["candidate_url"] = (
                    "https://ec.europa.eu/transparency/documents-register/api/files/"
                    + reference
                    + "/"
                    + quote(str(ers_id), safe="")
                )
    except Exception as error:
        result.update(status="check_unavailable", error=str(error)[:250])
    return result


def unpublished_library_candidates(payload, known_urls):
    known_ids = {
        urlsplit(url).path.split("/")[3]
        for url in known_urls
        if urlsplit(url).path.startswith("/sd/a/")
    }
    return [
        row
        for row in extract_circabc_public_pdfs(payload)
        if "4323" in row["name"] and row["id"] not in known_ids
    ]


def main():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from app.core.config import settings

    conn = psycopg2.connect(settings.database_url, connect_timeout=5)
    try:
        conn.set_session(readonly=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""SELECT title,source_type,source_url,file_hash FROM horizon_documents
                WHERE metadata->>'review_state'='pending'
                  AND NOT metadata ? 'superseded_by' ORDER BY title""")
            rows = cursor.fetchall()
            cursor.execute(
                "SELECT source_url FROM horizon_documents WHERE status='active' AND source_url LIKE 'https://circabc.europa.eu/sd/a/%'"
            )
            known_urls = [row["source_url"] for row in cursor.fetchall()]
    finally:
        conn.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(check_source, rows))
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "sources": results}
    try:
        library = json.loads(fetch(circabc_public_folder_url(LIFE_FOLDER)))
        report["life_library_candidates"] = unpublished_library_candidates(library, known_urls)
        report["life_library_complete"] = len(library.get("data", [])) >= library.get("total", 0)
    except Exception as error:
        report["life_library_error"] = str(error)[:250]
    report["changed_sources"] = sum(
        row["status"] in ("changed_requires_review", "download_available_requires_review")
        for row in results
    ) + len(report.get("life_library_candidates", []))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

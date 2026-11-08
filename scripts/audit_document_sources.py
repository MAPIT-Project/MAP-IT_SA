#!/usr/bin/env python3
"""Build a source register from an inventory; optionally verify official PDF bytes.

Does not modify the database or infer an original URL from a filename match.
"""

import argparse
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

BASE = "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/"
REFERENCE = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents?frameworkProgramme=43108390&programmePeriod=2021-2027"
LIMIT = 50 * 1024 * 1024


def allowed(url):
    p = urlsplit(url)
    return (
        p.scheme == "https"
        and p.hostname == "ec.europa.eu"
        and p.port in (None, 443)
        and not p.username
        and not p.password
    )


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl):
            raise ValueError("Redirect outside official allowlist")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_hash(url):
    if not allowed(url):
        return {"status": "unsupported_source"}
    try:
        request = Request(url, headers={"User-Agent": "MAPIT-source-audit/1.0"})
        with build_opener(OfficialRedirects()).open(request, timeout=25) as response:
            digest = hashlib.sha256()
            size = 0
            header = b""
            while True:
                block = response.read(65536)
                if not block:
                    break
                if not header:
                    header = block[:5]
                size += len(block)
                if size > LIMIT:
                    raise ValueError("PDF exceeds audit size limit")
                digest.update(block)
            if header != b"%PDF-":
                raise ValueError("Response is not a PDF")
            return {"status": "downloaded", "sha256": digest.hexdigest(), "final_url": response.url}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)[:250]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Download official candidates, two concurrent requests",
    )
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text())
    known = {}
    for doc in inventory["shared_documents"]:
        url = doc.get("document_url")
        if url:
            known.setdefault(doc.get("file_hash"), set()).add(url)
    rows = []
    for pdf in inventory["local_pdf_files"]:
        path = Path(pdf["file"])
        candidates = set(known.get(pdf["sha256"], ()))
        evidence = "existing_shared_document_record" if candidates else ""
        if path.parent.name == "2025_work_programmes":
            candidates.add(BASE + "horizon/wp-call/2025/" + path.name)
            evidence = evidence or "official_path_pattern_candidate"
        if path.name == "programme-guide_horizon_en.pdf":
            candidates.add(BASE + "horizon/guidance/" + path.name)
            evidence = evidence or "project_download_guide"
        if path.parent.name in ("Application forms", "Evaluation forms"):
            category = "af" if path.name.startswith("af_") else "ef"
            candidates.add(BASE + "horizon/temp-form/" + category + "/" + path.name)
            evidence = evidence or "official_path_pattern_candidate"
        rows.append(
            {
                "file": str(path),
                "local_sha256": pdf["sha256"],
                "indexed_records": pdf.get("content_hash_matches", []),
                "reference_page_candidate": REFERENCE,
                "candidate_evidence": evidence,
                "candidate_urls": sorted(candidates),
                "verification_status": "unverified" if candidates else "source_unknown",
                "verified_urls": [],
                "checks": [],
            }
        )
    urls = sorted({url for row in rows for url in row["candidate_urls"]})
    results = {}
    if args.verify:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = dict(zip(urls, pool.map(download_hash, urls)))
        for row in rows:
            row["checks"] = [{"url": url, **results[url]} for url in row["candidate_urls"]]
            row["verified_urls"] = [
                url
                for url in row["candidate_urls"]
                if results[url].get("sha256") == row["local_sha256"]
            ]
            if row["verified_urls"]:
                row["verification_status"] = "verified_exact_bytes"
            elif any(check["status"] == "downloaded" for check in row["checks"]):
                row["verification_status"] = "different_content_or_revision"
            elif row["candidate_urls"]:
                row["verification_status"] = "verification_unavailable"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "documents": rows}
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    csv_path = args.output.with_suffix(".csv")
    fields = [
        "file",
        "verification_status",
        "verified_urls",
        "candidate_urls",
        "local_sha256",
        "indexed_records",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: " | ".join(row[key]) if isinstance(row[key], list) else row[key]
                    for key in fields
                }
            )
    counts = {}
    for row in rows:
        key = row["verification_status"]
        counts[key] = counts.get(key, 0) + 1
    print(json.dumps({"documents": len(rows), "candidate_urls": len(urls), "statuses": counts}))


if __name__ == "__main__":
    main()

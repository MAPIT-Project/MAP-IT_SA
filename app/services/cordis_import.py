"""Validate and upsert canonical CORDIS project CSV exports atomically.

Every project outside the supplied export is preserved. Optional validated DET
consortium rows refresh only accepted projects in the same transaction. Unknown
export schemas fail before writes.
"""

import csv
import gzip
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

FIELDS = {
    "id",
    "acronym",
    "status",
    "title",
    "startDate",
    "endDate",
    "totalCost",
    "ecMaxContribution",
    "legalBasis",
    "topics",
    "ecSignatureDate",
    "frameworkProgramme",
    "masterCall",
    "subCall",
    "fundingScheme",
    "nature",
    "objective",
    "contentUpdateDate",
    "rcn",
    "grantDoi",
}
REQUIRED = {"id", "title", "objective", "contentUpdateDate"}
DATES = {"startDate", "endDate", "ecSignatureDate"}
NUMBERS = {"totalCost", "ecMaxContribution"}


def parse_projects(path):
    path = Path(path)
    if path.stat().st_size > 250 * 1024 * 1024:
        raise ValueError("CORDIS export exceeds the import size limit")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            # DET wraps csv.zip and documentation.zip in an outer archive.
            nested = [m for m in archive.infolist() if m.filename == "csv.zip"]
            if nested:
                if len(nested) != 1 or nested[0].file_size > 250 * 1024 * 1024:
                    raise ValueError("Invalid nested CORDIS CSV archive")
                archive = zipfile.ZipFile(io.BytesIO(archive.read(nested[0])))
            members = [
                m
                for m in archive.infolist()
                if Path(m.filename).name.lower() in {"project.csv", "projects.csv"}
            ]
            if len(members) != 1 or members[0].file_size > 250 * 1024 * 1024:
                raise ValueError("Expected exactly one bounded project.csv in the export")
            data = archive.read(members[0]).decode("utf-8-sig")
    else:
        data = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(data[:8192], delimiters=";,")
    except csv.Error:
        raise ValueError("Export is not a supported CORDIS CSV") from None
    reader = csv.DictReader(io.StringIO(data), dialect=dialect, strict=True)
    if not REQUIRED.issubset(reader.fieldnames or []):
        raise ValueError("CORDIS CSV must contain id, title, objective and contentUpdateDate")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("Duplicate CSV column names")
    rows = []
    seen = set()
    for raw in reader:
        if None in raw or any(raw[k] is None for k in reader.fieldnames):
            raise ValueError("Malformed CSV row")
        row = {k: v.strip() for k, v in raw.items() if k in FIELDS and v.strip()}
        if not REQUIRED.issubset(row):
            raise ValueError("A project is missing required source fields")
        try:
            for field in ("id", "rcn"):
                if field in row:
                    row[field] = int(row[field])
                    if not 0 < row[field] <= 2147483647:
                        raise ValueError("Invalid identifier")
            for field in DATES:
                if field in row:
                    row[field] = datetime.fromisoformat(row[field]).date()
            updated = datetime.fromisoformat(row["contentUpdateDate"].replace("Z", "+00:00"))
            if updated.tzinfo:
                updated = updated.astimezone(timezone.utc).replace(tzinfo=None)
            row["contentUpdateDate"] = updated
            for field in NUMBERS:
                if field in row:
                    value = Decimal(row[field])
                    if not value.is_finite() or value < 0:
                        raise ValueError("Invalid amount")
                    row[field] = value
        except (ValueError, InvalidOperation, OverflowError):
            raise ValueError("Invalid CORDIS identifier, date or monetary value") from None
        if row["id"] in seen:
            raise ValueError("Duplicate project identifiers; export must be reviewed")
        seen.add(row["id"])
        rows.append(row)
        if len(rows) > 100000:
            raise ValueError("CORDIS import exceeds the project limit")
    if not rows:
        raise ValueError("CORDIS project export is empty")
    return rows


def import_projects(database_url, rows, backup_dir, *, organizations=None):
    """One transaction; reject older source versions and invalidate changed vectors."""
    conn = psycopg2.connect(database_url)
    backup = None
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_try_advisory_xact_lock(hashtext('mapit_cordis_project_import'))"
                )
                if not cursor.fetchone()[0]:
                    raise ValueError("Another CORDIS import is running")
                ids = [r["id"] for r in rows]
                cursor.execute("SELECT * FROM projects WHERE id=ANY(%s) FOR UPDATE", (ids,))
                names = [d[0] for d in cursor.description]
                old = {r[0]: dict(zip(names, r)) for r in cursor.fetchall()}
                cursor.execute(
                    "SELECT *,combined_embedding::text AS saved_vector FROM project_embeddings WHERE project_id=ANY(%s) FOR UPDATE",
                    (ids,),
                )
                embedding_names = [d[0] for d in cursor.description]
                embeddings = [dict(zip(embedding_names, r)) for r in cursor.fetchall()]
                old_organizations = []
                if organizations is not None:
                    allowed_ids = set(ids)
                    if any(r["projectID"] not in allowed_ids for r in organizations):
                        raise ValueError("Organization refers to a project outside the export")
                    cursor.execute(
                        'SELECT * FROM organizations WHERE "projectID"=ANY(%s) FOR UPDATE', (ids,)
                    )
                    org_names = [d[0] for d in cursor.description]
                    old_organizations = [dict(zip(org_names, r)) for r in cursor.fetchall()]
                    newest_org = {}
                    for org in old_organizations:
                        updated = org.get("contentUpdateDate")
                        if updated and updated > newest_org.get(org["projectID"], datetime.min):
                            newest_org[org["projectID"]] = updated
                directory = Path(backup_dir)
                directory.mkdir(parents=True, exist_ok=True)
                backup = directory / (
                    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                    + "-"
                    + uuid.uuid4().hex
                    + ".json.gz"
                )
                # Exclusive creation and a private mode; no backup in version control.
                with backup.open("xb") as handle:
                    backup.chmod(0o600)
                    with gzip.GzipFile(fileobj=handle, mode="wb", compresslevel=3) as archive:
                        archive.write(
                            json.dumps(
                                {
                                    "projects": list(old.values()),
                                    "project_embeddings": embeddings,
                                    "incoming_ids": ids,
                                    "organizations": old_organizations
                                    if organizations is not None
                                    else None,
                                },
                                default=str,
                            ).encode()
                        )
                applied = []
                changed = []
                for row in rows:
                    if (
                        organizations is not None
                        and newest_org.get(row["id"], datetime.min) > row["contentUpdateDate"]
                    ):
                        continue
                    fields = sorted(row)
                    update = [field for field in fields if field != "id"]
                    query = sql.SQL("""INSERT INTO projects ({columns}) VALUES ({values})
                        ON CONFLICT (id) DO UPDATE SET {updates}
                        WHERE projects."contentUpdateDate" IS NULL
                           OR EXCLUDED."contentUpdateDate">=projects."contentUpdateDate"
                        RETURNING id""").format(
                        columns=sql.SQL(",").join(map(sql.Identifier, fields)),
                        values=sql.SQL(",").join(sql.Placeholder() for _ in fields),
                        updates=sql.SQL(",").join(
                            sql.SQL("{}=EXCLUDED.{}").format(sql.Identifier(f), sql.Identifier(f))
                            for f in update
                        ),
                    )
                    cursor.execute(query, [row[f] for f in fields])
                    if cursor.fetchone():
                        applied.append(row["id"])
                        previous = old.get(row["id"])
                        if previous and (
                            previous.get("title") != row["title"]
                            or previous.get("objective") != row["objective"]
                        ):
                            changed.append(row["id"])
                cursor.execute(
                    """UPDATE project_embeddings SET title_embedding=NULL,
                    objective_embedding=NULL,combined_embedding=NULL,embedding_status='pending',
                    updated_at=now() WHERE project_id=ANY(%s)""",
                    (changed,),
                )
                organization_count = 0
                if organizations is not None:
                    from .cordis_det import ORG_FIELDS
                    from collections import defaultdict, deque

                    identities = defaultdict(deque)
                    identity_fields = ("projectID", "organisationID", "role", "order")
                    for org in old_organizations:
                        identities[tuple(org[k] for k in identity_fields)].append(org["id"])
                    accepted = set(applied)
                    incoming = []
                    for org in organizations:
                        if org["projectID"] not in accepted:
                            continue
                        key = tuple(org[k] for k in identity_fields)
                        identity = (
                            identities[key].popleft() if identities[key] else str(uuid.uuid4())
                        )
                        incoming.append([org.get(k) for k in ORG_FIELDS] + [identity])
                    # Replace only consortium rows belonging to accepted source projects.
                    # A member can have several distinct roles; do not collapse by PIC.
                    cursor.execute(
                        'DELETE FROM organizations WHERE "projectID"=ANY(%s)', (applied,)
                    )
                    if incoming:
                        query = sql.SQL("INSERT INTO organizations ({}) VALUES %s").format(
                            sql.SQL(",").join(map(sql.Identifier, ORG_FIELDS + ["id"]))
                        )
                        execute_values(cursor, query.as_string(conn), incoming, page_size=1000)
                    organization_count = len(incoming)
                return {
                    "applied": len(applied),
                    "older_versions_skipped": len(rows) - len(applied),
                    "text_embeddings_invalidated": len(changed),
                    "backup": str(backup),
                    "organizations_refreshed": organizations is not None,
                    "organization_participation_rows": organization_count,
                }
    finally:
        conn.close()

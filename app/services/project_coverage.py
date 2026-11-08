"""Observed corpus coverage, without confusing source dates with import dates."""

from datetime import date, datetime, timezone
from contextlib import closing

import json
import re
from pathlib import Path

import psycopg2

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data/cordis_snapshot.json"

PROJECT_TOOLS = frozenset(
    {
        "search_projects",
        "get_project_details",
        "find_similar_projects",
        "find_semantically_similar_projects",
        "find_organization_projects",
        "get_project_partners",
        "get_organization_stats",
        "get_collaboration_network",
        "search_by_cluster",
        "get_budget_benchmark",
        "get_consortium_patterns",
        "analyze_geographic_diversification",
        "find_experienced_partners",
        "get_similar_funded_projects",
        "analyze_call_history",
        "get_country_statistics",
    }
)


def describe_coverage(projects, organizations, latest, programmes, *, today=None):
    today = today or datetime.now(timezone.utc).date()
    source_date = latest.date() if isinstance(latest, datetime) else latest
    age = (today - source_date).days if isinstance(source_date, date) else None
    return {
        "source": "local_cordis_snapshot",
        "projects_indexed": projects,
        "organization_participation_rows": organizations,
        "programmes": programmes,
        "latest_record_source_update": latest.isoformat() if latest else None,
        "import_date": None,
        "status": "older_source_snapshot"
        if age is not None and age > 90
        else "coverage_unverified",
        "warning": (
            "This is a local CORDIS subset, not a complete live project database. "
            "The latest record source-update date is not the import date. "
            "Recent call or document updates do not refresh project/partner data. "
            "Do not claim exhaustive results, current partner availability, or current "
            "consortium experience beyond this snapshot. State the source-date limitation "
            "when presenting project or partner recommendations."
        ),
    }


def write_snapshot_provenance(report, imported_at, path=None):
    """Record only a completed source/graph/vector audit, never infer an import date."""
    if report.get("complete") is not True or report.get("problems"):
        raise ValueError("A complete successful verification report is required")
    if not re.fullmatch(r"[a-f0-9]{64}", report.get("source_sha256", "")):
        raise ValueError("Verified export digest required")
    imported = datetime.fromisoformat(imported_at)
    if imported.tzinfo is None:
        raise ValueError("Import timestamp must include its timezone")
    coverage = report["coverage"]
    metadata = {
        key: coverage[key]
        for key in (
            "projects_indexed",
            "organization_participation_rows",
            "latest_record_source_update",
        )
    }
    metadata.update(
        import_date=imported.isoformat(),
        verified_at=report["checked_at"],
        source_task_id=report.get("source_task_id"),
        source_sha256=report["source_sha256"],
        source_project_count=report["source_projects"],
        retained_projects_outside_export=coverage["projects_indexed"] - report["source_projects"],
        newer_source_versions_preserved=report.get("newer_project_versions_preserved"),
        programme="HORIZON",
        verified=True,
    )
    target = path or SNAPSHOT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    with temporary.open("w") as handle:
        temporary.chmod(0o600)
        json.dump(metadata, handle, indent=2)
    temporary.replace(target)
    return metadata


def apply_snapshot_provenance(coverage, metadata):
    """Do not attach an old audit to different observed data or claim global coverage."""
    fields = ("projects_indexed", "organization_participation_rows", "latest_record_source_update")
    if (
        metadata.get("verified") is not True
        or metadata.get("programme") != "HORIZON"
        or coverage.get("programmes") != ["HORIZON"]
        or any(coverage.get(key) != metadata.get(key) for key in fields)
    ):
        return coverage
    imported = datetime.fromisoformat(metadata["import_date"])
    if imported.tzinfo is None:
        return coverage
    result = {
        **coverage,
        "import_date": imported.isoformat(),
        "snapshot_verified_at": metadata["verified_at"],
        "source_export_sha256": metadata["source_sha256"],
        "source_export_projects": metadata["source_project_count"],
        "retained_projects_outside_export": metadata.get(
            "retained_projects_outside_export",
            coverage["projects_indexed"] - metadata["source_project_count"],
        ),
        "import_policy": "Keep existing projects outside the export and do not overwrite newer source versions. Local counts can therefore exceed the export count.",
    }
    if result["status"] != "older_source_snapshot":
        result["status"] = "verified_snapshot"
    result["warning"] = (
        "This local Horizon Europe snapshot was compared with the downloaded CORDIS export. "
        "It is not a live database or proof that every EU-funded project is present. "
        "Source update dates differ from the recorded import date; source publication delays "
        "and future changes remain possible. Project participation does not establish "
        "current partner availability. Call/document refreshes are separate pipelines."
    )
    return result


def project_database_coverage():
    from app.core.config import settings

    try:
        with closing(psycopg2.connect(settings.database_url, connect_timeout=5)) as conn:
            conn.set_session(readonly=True)
            with conn.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5000ms'")
                cursor.execute(
                    'SELECT count(*),max("contentUpdateDate"),array_agg(DISTINCT "frameworkProgramme") FROM projects'
                )
                projects, latest, programmes = cursor.fetchone()
                cursor.execute("SELECT count(*) FROM organizations")
                organizations = cursor.fetchone()[0]
        coverage = describe_coverage(projects, organizations, latest, programmes)
        try:
            return apply_snapshot_provenance(coverage, json.loads(SNAPSHOT_PATH.read_text()))
        except (OSError, ValueError, KeyError, TypeError):
            return coverage
    except (psycopg2.Error, OSError):
        return {
            "source": "local_cordis_snapshot",
            "status": "unavailable",
            "warning": "Project corpus coverage could not be checked. Do not claim current or complete project/partner coverage.",
        }


def coverage_note(coverage, *, english=False):
    latest = coverage.get("latest_record_source_update")
    if english:
        if latest and coverage.get("import_date"):
            return (
                f"*Data coverage: local CORDIS Horizon Europe snapshot imported "
                f"{coverage['import_date'][:10]}; latest source update: {latest[:10]}. "
                "No live or exhaustive coverage of all EU programmes is guaranteed.*"
            )
        if latest:
            return f"*Data coverage: local CORDIS subset; latest source update: {latest[:10]}. Current/exhaustive coverage is not established.*"
        return "*Data coverage: project/partner freshness and completeness could not be confirmed.*"
    if latest and coverage.get("import_date"):
        return (
            f"*Datadekking: lokale CORDIS Horizon Europe-snapshot, geïmporteerd op "
            f"{coverage['import_date'][:10]}; nieuwste bronupdate: {latest[:10]}. "
            "Geen live dekking of volledige dekking van alle EU-programma’s gegarandeerd.*"
        )
    if latest:
        return (
            f"*Datadekking: lokale CORDIS-selectie; nieuwste bronupdate in deze selectie: "
            f"{latest[:10]}. Geen volledige actuele project- of partnerdekking aangetoond.*"
        )
    return "*Datadekking: actualiteit en volledigheid van de lokale project- en partnergegevens konden niet worden bevestigd.*"

"""DET schema mapping and isolated transactional import regression tests."""

import copy
import io
import json
import os
import uuid
import zipfile
from datetime import datetime
from decimal import Decimal

import psycopg2
import pytest
from psycopg2 import sql
from psycopg2.extensions import make_dsn

from app.services.cordis_det import map_project, parse_det_json
from app.services.cordis_import import import_projects


def source():
    return {
        "contenttype": "project",
        "language": "en",
        "id": "101000001",
        "rcn": "12345",
        "title": "A valid research project",
        "objective": 'Research with exact source text; "quoted".',
        "contentUpdateDate": "2026-11-07 19:55:38",
        "totalCost": "1234.56",
        "relations": {
            "categories": [
                {
                    "code": "/HORIZON-RIA",
                    "attributes": {"classification": "projectFundingSchemeCategory"},
                }
            ],
            "associations": [
                {
                    "contenttype": "programme",
                    "code": "HORIZON-CL1-2025-01",
                    "frameworkProgramme": "HORIZON",
                    "attributes": {"type": "relatedTopic"},
                },
                {
                    "contenttype": "organization",
                    "id": "999123456",
                    "rcn": "123",
                    "legalName": "Example University",
                    "attributes": {
                        "source": "corda",
                        "type": "coordinator",
                        "sme": "false",
                        "terminated": "false",
                        "order": "1",
                        "ecContribution": "1234.56",
                    },
                    "address": {"country": "NL"},
                    "relations": {
                        "regions": [
                            {"nutsCode": "NL123", "attributes": {"type": "relatedNutsCode"}},
                            {"nutsCode": "DE123", "attributes": {"type": "relatedNutsCode"}},
                            {"attributes": {"type": "relatedNutsCode"}},
                        ]
                    },
                },
            ],
        },
    }


def test_json_preserves_quotes_precise_amounts_and_multiple_regions():
    project, orgs = map_project(source())
    assert project["totalCost"] == Decimal("1234.56")
    assert project["objective"].endswith('; "quoted".')
    assert project["frameworkProgramme"] == "HORIZON"
    assert project["fundingScheme"] == "HORIZON-RIA"
    assert orgs[0]["nutsCode"] == "DE123;NL123"
    assert orgs[0]["SME"] is False and orgs[0]["active"] is None
    assert orgs[0]["ecContribution"] == Decimal("1234.56")


@pytest.mark.parametrize("mutation", ["boolean", "programme", "coordinator"])
def test_unknown_contracts_fail_closed(mutation):
    data = source()
    assoc = data["relations"]["associations"]
    if mutation == "boolean":
        assoc[1]["attributes"]["sme"] = "maybe"
    elif mutation == "programme":
        assoc[0]["frameworkProgramme"] = "FP7"
    else:
        assoc[1]["attributes"]["type"] = "participant"
    with pytest.raises(ValueError):
        map_project(data)


def test_bounded_nested_archive_and_duplicate_project_rejection(tmp_path):
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("project-a.json", json.dumps(source()))
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("json.zip", nested.getvalue())
    assert len(parse_det_json(path)[0]) == 1
    with zipfile.ZipFile(nested, "a") as archive:
        archive.writestr("project-b.json", json.dumps(source()))
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("json.zip", nested.getvalue())
    with pytest.raises(ValueError, match="Duplicate project"):
        parse_det_json(path)


@pytest.fixture
def isolated_database():
    if os.getenv("MAPIT_CORDIS_IMPORT_TEST_DB") != "1":
        pytest.skip("Explicit isolated DB test opt-in required")
    from app.core.config import settings

    schema = "cordis_test_" + uuid.uuid4().hex
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    with conn.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        for table in ("projects", "organizations", "project_embeddings"):
            cursor.execute(
                sql.SQL("CREATE TABLE {}.{} (LIKE public.{} INCLUDING ALL)").format(
                    sql.Identifier(schema), sql.Identifier(table), sql.Identifier(table)
                )
            )
    try:

        class IsolatedDSN(str):
            def __repr__(self):
                return "<isolated test database>"

        yield IsolatedDSN(
            make_dsn(settings.database_url, options=f"-c search_path={schema},public")
        )
    finally:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        conn.close()


def test_atomic_import_preserves_identity_skips_older_and_rolls_back(isolated_database, tmp_path):
    dsn = isolated_database
    project, orgs = map_project(source())
    result = import_projects(dsn, [project], tmp_path, organizations=orgs)
    assert result["organization_participation_rows"] == 1
    with psycopg2.connect(dsn) as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM organizations")
        identity = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO project_embeddings (project_id,embedding_status) VALUES (%s,'completed')",
            (project["id"],),
        )
    updated = dict(project, objective="Updated objective")
    result = import_projects(dsn, [updated], tmp_path, organizations=orgs)
    assert result["text_embeddings_invalidated"] == 1
    with psycopg2.connect(dsn) as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM organizations")
        assert cursor.fetchone()[0] == identity
        cursor.execute("SELECT embedding_status FROM project_embeddings")
        assert cursor.fetchone()[0] == "pending"
    older = dict(updated, contentUpdateDate=datetime(2020, 1, 1))
    assert import_projects(dsn, [older], tmp_path, organizations=orgs)["applied"] == 0
    broken = copy.deepcopy(orgs)
    broken[0]["rcn"] = "invalid integer"
    with pytest.raises(psycopg2.Error):
        import_projects(
            dsn, [dict(updated, title="Must roll back")], tmp_path, organizations=broken
        )
    with psycopg2.connect(dsn) as conn, conn.cursor() as cursor:
        cursor.execute("SELECT title FROM projects")
        assert cursor.fetchone()[0] == project["title"]
        cursor.execute("SELECT id FROM organizations")
        assert cursor.fetchone()[0] == identity


def test_project_embedding_refresh_rejects_zero_vectors_and_incomplete_batches():
    import numpy as np
    from scripts.refresh_project_embeddings import validated_vectors
    from app.services.embedding_service import EmbeddingService

    embedder = EmbeddingService.__new__(EmbeddingService)
    embedder.embedding_dimension = 3
    with pytest.raises(ValueError):
        validated_vectors([np.zeros(3)], 1, embedder)
    with pytest.raises(ValueError):
        validated_vectors([np.ones(3)], 2, embedder)
    with pytest.raises(ValueError):
        validated_vectors([None], 1, embedder)
    assert validated_vectors([np.ones(3)], 1, embedder) == [[1.0, 1.0, 1.0]]


def test_newer_consortium_and_unrelated_projects_are_preserved(isolated_database, tmp_path):
    import gzip

    project, orgs = map_project(source())
    other = dict(project, id=101000002)
    other_orgs = [dict(orgs[0], projectID=other["id"])]
    dsn = isolated_database
    import_projects(dsn, [project, other], tmp_path, organizations=orgs + other_orgs)
    with psycopg2.connect(dsn) as conn, conn.cursor() as cursor:
        cursor.execute(
            'UPDATE organizations SET "contentUpdateDate"=%s WHERE "projectID"=%s',
            (datetime(2027, 1, 1), project["id"]),
        )
    result = import_projects(
        dsn, [dict(project, title="Must not overwrite")], tmp_path, organizations=orgs
    )
    assert result["older_versions_skipped"] == 1
    with gzip.open(result["backup"], "rt") as handle:
        backup = json.load(handle)
    assert len(backup["projects"]) == len(backup["organizations"]) == 1
    with psycopg2.connect(dsn) as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id,title FROM projects ORDER BY id")
        assert cursor.fetchall() == [
            (project["id"], project["title"]),
            (other["id"], other["title"]),
        ]
        cursor.execute("SELECT count(*) FROM organizations")
        assert cursor.fetchone()[0] == 2

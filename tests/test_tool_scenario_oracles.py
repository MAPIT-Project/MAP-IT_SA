"""Source-evidence boundaries with synthetic subprocess responses, never a database."""

import subprocess
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.tool_scenarios.oracles import (
    SOURCE_QUERIES,
    DockerPsqlReader,
    OraclePrerequisiteError,
    OracleUnavailable,
    discover_ground_truth,
    read_statement,
    require_facts,
)


@pytest.mark.parametrize("sql", SOURCE_QUERIES.values(), ids=SOURCE_QUERIES.keys())
def test_independent_source_queries_are_read_only(sql):
    assert read_statement(sql) == sql.strip().removesuffix(";")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM projects",
        "SELECT 1; DELETE FROM projects",
        "WITH removed AS (DELETE FROM projects RETURNING id) SELECT * FROM removed",
        "SELECT * INTO copied_projects FROM projects",
        "SELECT * FROM projects FOR UPDATE",
        "SELECT 1 -- commit;",
        "SELECT 1 /* commit; */",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT \"pg_read_file\"('/etc/passwd')",
        "SELECT current_setting('database_url')",
        "SELECT query_to_xml('SELECT * FROM auth.users',true,false,'')",
        "SELECT secret_function()",
        "SELECT * FROM auth.users",
        'SELECT * FROM public."conversation"',
        "SELECT * FROM projects, public.users",
        "SELECT * FROM projects JOIN message ON true",
        "SELECT * FROM (SELECT * FROM user_profiles) private_data",
        "SELECT $$unsafe$$",
        "SELECT 'unterminated",
    ],
)
def test_source_reader_rejects_writes_private_data_and_indirection(sql):
    with pytest.raises(ValueError):
        read_statement(sql)


def test_source_reader_keeps_quoted_literals_and_nested_ctes():
    sql = """
        WITH anchors AS (
          SELECT id, 'a;b''c' AS label FROM public.projects
        ) SELECT id,label,extract(year FROM p."startDate") AS year
          FROM anchors JOIN projects p ON p.id=anchors.id
    """
    assert read_statement(sql) == sql.strip()


def test_source_reader_accepts_derived_table_without_confusing_from_with_function():
    sql = """
        SELECT count(*) AS project_count,avg(partners) AS avg_partners
        FROM (
          SELECT p.id,count(DISTINCT o.name) AS partners
          FROM public.projects p JOIN public.organizations o ON o."projectID"=p.id
          GROUP BY p.id HAVING(count(DISTINCT o.name)>0)
        ) AS consortium
    """
    assert read_statement(sql) == sql.strip()


def test_psql_transport_preserves_column_order_and_decimal_money(monkeypatch):
    run = Mock(
        return_value=SimpleNamespace(
            returncode=0,
            stdout='[{"z_project_id":"101137586","a_amount":19996911.75}]',
            stderr="",
        )
    )
    monkeypatch.setattr(subprocess, "run", run)
    reader = DockerPsqlReader("funding-db-test")
    rows = reader('SELECT id AS z_project_id,"ecMaxContribution" AS a_amount FROM projects LIMIT 1')
    assert list(rows[0]) == ["z_project_id", "a_amount"]
    assert rows[0]["a_amount"] == Decimal("19996911.75")
    args, kwargs = run.call_args
    assert args[0] == [
        "docker",
        "exec",
        "-i",
        "funding-db-test",
        "psql",
        "-X",
        "-qAt",
        "-U",
        "postgres",
        "-d",
        "postgres",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    assert not kwargs.get("shell", False)
    assert "BEGIN TRANSACTION READ ONLY" in kwargs["input"]
    assert "SET LOCAL statement_timeout='10s'" in kwargs["input"]
    assert "SET LOCAL lock_timeout='2s'" in kwargs["input"]
    assert "json_agg(row_to_json(source_row))" in kwargs["input"]
    assert kwargs["input"].endswith("ROLLBACK;\n")


@pytest.mark.parametrize("payload", ["not JSON", "{}", "[1]", "null"])
def test_psql_transport_rejects_malformed_rows(monkeypatch, payload):
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout=payload,
                stderr="",
            )
        ),
    )
    with pytest.raises(OracleUnavailable):
        DockerPsqlReader()("SELECT 1")


@pytest.mark.parametrize(
    "failure",
    [
        OSError("sensitive diagnostic"),
        subprocess.TimeoutExpired(["docker"], 15),
    ],
)
def test_psql_transport_hides_raw_process_diagnostics(monkeypatch, failure):
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=failure))
    with pytest.raises(OracleUnavailable) as error:
        DockerPsqlReader()("SELECT 1")
    assert "sensitive" not in str(error.value)


def test_psql_failure_does_not_expose_server_error(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(
            return_value=SimpleNamespace(
                returncode=3,
                stdout="",
                stderr="sensitive server diagnostic",
            )
        ),
    )
    with pytest.raises(OracleUnavailable, match="exit 3") as error:
        DockerPsqlReader()("SELECT 1")
    assert "sensitive" not in str(error.value)


@pytest.mark.parametrize("container", ["bad;command", "--privileged", "a/b", ""])
def test_psql_reader_rejects_invalid_container_name(container):
    with pytest.raises(ValueError):
        DockerPsqlReader(container)


@pytest.mark.parametrize("timeout", [0, -1, 121])
def test_psql_reader_requires_bounded_timeout(timeout):
    with pytest.raises(ValueError):
        DockerPsqlReader(timeout=timeout)


def test_discovery_uses_independent_queries_without_model_or_tool_outputs():
    reader = Mock(side_effect=lambda sql: [{"source_sql": sql}])
    facts = discover_ground_truth(reader)
    assert list(facts) == list(SOURCE_QUERIES)
    assert reader.call_count == len(SOURCE_QUERIES)
    assert facts["reference_project"][0]["source_sql"] == SOURCE_QUERIES["reference_project"]


def test_discovery_identifies_failed_prerequisite_without_raw_details():
    reader = Mock(side_effect=OracleUnavailable("sensitive DB details"))
    with pytest.raises(OracleUnavailable, match="catalog_counts") as error:
        discover_ground_truth(reader)
    assert "sensitive" not in str(error.value)


def test_missing_source_anchor_fails_instead_of_accepting_empty_tool_results():
    with pytest.raises(OraclePrerequisiteError, match="reference_project"):
        require_facts({"reference_project": []}, "reference_project")
    require_facts({"reference_project": [{"project_id": "101137586"}]}, "reference_project")

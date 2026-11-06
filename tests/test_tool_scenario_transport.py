"""Pure DB-API bridge checks. Reader responses are mocked; no services or models."""

from unittest.mock import Mock

import pytest

from tests.tool_scenarios.transport import ReadConnection, ReadPool, ReadSearchClient, bind_query


def test_parameters_are_quoted_and_cannot_change_statement():
    assert (
        bind_query("SELECT %s AS name, %s AS amount", ["O'Brien", 42])
        == "SELECT 'O''Brien' AS name, 42 AS amount"
    )
    assert (
        bind_query("SELECT %s ILIKE '%%hydrogen%%'", ["sample"])
        == "SELECT 'sample' ILIKE '%hydrogen%'"
    )


@pytest.mark.parametrize("query,values", [("SELECT %s", []), ("SELECT 1", [2])])
def test_parameter_mismatches_fail(query, values):
    with pytest.raises(ValueError):
        bind_query(query, values)


def test_cursor_keeps_select_column_order_and_consumes_rows():
    reader = Mock(return_value=[{"second": 2, "first": 1}, {"second": 4, "first": 3}])
    cursor = ReadConnection(reader).cursor()
    cursor.execute("SELECT second,first FROM projects WHERE id=%s", [1])
    assert cursor.fetchone() == (2, 1)
    assert cursor.fetchall() == [(4, 3)]
    assert cursor.fetchone() is None
    assert [column.name for column in cursor.description] == ["second", "first"]
    reader.assert_called_once_with("SELECT second,first FROM projects WHERE id=1")


def test_dictionary_cursor_and_pool_ownership():
    reader = Mock(return_value=[{"project_id": "101137586"}])
    pool = ReadPool(reader)
    connection = pool.getconn()
    with connection.cursor(cursor_factory=object) as cursor:
        cursor.execute("SELECT project_id FROM projects")
        assert cursor.fetchmany(1) == [{"project_id": "101137586"}]
    pool.putconn(connection)
    assert connection.closed
    with pytest.raises(ValueError, match="read-only"):
        connection.set_session(readonly=False)


def test_search_rpc_uses_actual_read_only_function_and_quotes_text():
    from tests.tool_scenarios.oracles import read_statement

    reader = Mock(return_value=[{"chunk_id": "source-chunk"}])
    response = (
        ReadSearchClient(reader)
        .rpc(
            "keyword_search",
            {
                "query_text": "O'Brien; consortium",
                "limit_count": 10,
            },
        )
        .execute()
    )
    sql = reader.call_args.args[0]
    assert "O''Brien; consortium" in sql
    assert "public.keyword_search" in sql
    assert read_statement(sql) == sql
    assert response.data == [{"chunk_id": "source-chunk"}]


@pytest.mark.parametrize(
    "name,params",
    [
        ("delete_documents", {}),
        ("hybrid_search", {"unexpected": "value"}),
        ("search_documents", {"query_embedding": [1, 2, 3]}),
    ],
)
def test_search_bridge_rejects_unknown_rpcs_fields_and_invalid_vectors(name, params):
    from tests.tool_scenarios.oracles import OraclePrerequisiteError

    reader = Mock()
    with pytest.raises((ValueError, OraclePrerequisiteError)):
        ReadSearchClient(reader).rpc(name, params)
    reader.assert_not_called()

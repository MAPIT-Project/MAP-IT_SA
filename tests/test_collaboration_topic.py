"""Topic-scoped graph evidence for organisation collaboration questions."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.data_intelligence.graph_service import GraphSearchService
from app.services.agents.framework.tool_schemas import input_model_for
from app.services.agents.tool_registry import ToolRegistryMixin


def test_network_returns_shared_project_evidence_and_parameterizes_topic():
    graph = GraphSearchService.__new__(GraphSearchService)
    graph.db = SimpleNamespace(execute_query=Mock(return_value=[{
        'source_org': 'TNO', 'source_country': 'NL', 'partner_org': 'Partner',
        'partner_country': 'DE', 'collaboration_count': 1,
        'shared_projects': [{'id': '101000001', 'title': 'Hydrogen research', 'acronym': 'H2'}],
    }]))
    result = graph.get_organization_collaboration_network('TNO', topic=' Hydrogen ')
    query, params = graph.db.execute_query.call_args.args
    assert params['topic'] == 'hydrogen'
    assert '$topic' in query
    assert 'COUNT(DISTINCT p)' in query
    assert 'collect(DISTINCT' in query
    assert result['partners'][0]['shared_projects'][0]['cordis_url'] == 'https://cordis.europa.eu/project/id/101000001'


def test_unfiltered_network_keeps_existing_behavior():
    graph = GraphSearchService.__new__(GraphSearchService)
    graph.db = SimpleNamespace(execute_query=Mock(return_value=[]))
    result = graph.get_organization_collaboration_network('TNO')
    assert graph.db.execute_query.call_args.args[1]['topic'] == ''
    assert result['partners'] == []
    assert result['success'] is True


@pytest.mark.asyncio
async def test_network_tool_passes_topic_to_graph(monkeypatch):
    from app.services.tools.organization_tools import get_collaboration_network_execute
    method = Mock(return_value={'partners': []})
    monkeypatch.setattr(GraphSearchService, '__init__', lambda self: None)
    monkeypatch.setattr(GraphSearchService, 'get_organization_collaboration_network', method)
    await get_collaboration_network_execute('TNO', topic='hydrogen')
    assert method.call_args.kwargs['topic'] == 'hydrogen'


def test_registered_network_schema_accepts_optional_topic():
    registry = ToolRegistryMixin()
    registry.tools = {}
    registry._init_tools()
    schema = input_model_for(registry.tools['get_collaboration_network'])
    assert schema.model_validate({'organization_name': 'TNO', 'topic': 'hydrogen'}).topic == 'hydrogen'
    assert schema.model_validate({'organization_name': 'TNO'}).model_dump(exclude_unset=True) == {'organization_name': 'TNO'}

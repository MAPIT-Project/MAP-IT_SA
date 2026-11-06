"""Reject the PDF debris seen in the reported answer; no real embedding requests."""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from app.services.document_content import (
    clean_document_text,
    is_usable_document_text,
    select_document_excerpt,
)
from app.services.tools.document_search import search_documents_execute
from app.services.vector_search_service import VectorSearchService

VALID = "SMEs from France and Germany are eligible for research grants up to €50,000."
DEBRIS = ["1 \n\n\f", ".", "p.", "_" * 500, "________ ________", "\x00\f\n"]


@pytest.mark.parametrize("content", DEBRIS)
def test_pdf_debris_is_not_evidence(content):
    assert not is_usable_document_text(content)


@pytest.mark.parametrize(
    "content",
    [
        VALID,
        "Eligible countries: France, Germany, Italy.",
        "Funding rates | Research actions | 100% | Innovation actions | 70%",
        "Les petites entreprises sont éligibles aux financements européens.",
    ],
)
def test_short_funding_facts_and_tables_remain_usable(content):
    assert is_usable_document_text(content)


def test_cleaning_preserves_numbers_and_substantive_content():
    cleaned = clean_document_text("1\f\n" + VALID + "\n" + "_" * 500)
    assert VALID in cleaned
    assert "50,000" in cleaned
    assert "____" not in cleaned
    assert "\f" not in cleaned


def row(content, index=0):
    return {
        "chunk_id": f"chunk-{index}",
        "document_id": "synthetic-document",
        "content": content,
        "document_title": "Synthetic funding guide",
        "document_type": "programme_guide",
        "combined_score": 0.8,
        "similarity": 0.8,
        "score": 0.8,
        "page_number": 12,
    }


@pytest.mark.parametrize("mode", ["hybrid", "semantic", "keyword"])
def test_all_document_search_modes_reject_unreadable_chunks(mode):
    rows = [row(content, i) for i, content in enumerate([*DEBRIS, VALID])]
    source = Mock()
    source.hybrid_search.return_value = rows
    source.semantic_search.return_value = rows
    source.client.rpc.return_value.execute.return_value = SimpleNamespace(data=rows)
    embedder = Mock()
    embedder.generate_query_embedding.return_value = np.ones(3072)
    service = VectorSearchService(source, embedder)
    results = getattr(service, f"{mode}_search")("SME eligibility")
    assert len(results) == 1
    assert results[0].content == VALID
    assert results[0].page_number == 12


@pytest.mark.asyncio
@pytest.mark.parametrize("valid", [True, False])
async def test_document_tool_filters_before_limit_and_reports_only_usable_count(monkeypatch, valid):
    import app.services.vector_search_service as module

    results = [SimpleNamespace(**row(text, i)) for i, text in enumerate(DEBRIS)]
    if valid:
        results.append(SimpleNamespace(**row(VALID, 10)))
    vector = Mock()
    vector.hybrid_search.return_value = results
    monkeypatch.setattr(module, "VectorSearchService", Mock(return_value=vector))
    result = await search_documents_execute("SME eligibility", max_results=1)
    assert result["total_found"] == (1 if valid else 0)
    if valid:
        assert result["documents"][0]["content"] == VALID
        assert result["documents"][0]["page_number"] == 12
    else:
        assert result["documents"] == []
        assert "No usable" in result["message"]


def test_long_chunk_keeps_the_query_rule_instead_of_only_the_first_page_prefix():
    rule = (
        "The minimum consortium includes three independent legal entities in different countries."
    )
    content = "Unrelated administrative guidance. " * 100 + rule + " Funding details follow. " * 50
    excerpt = select_document_excerpt(
        content, "minimum consortium three independent legal entities"
    )
    assert rule in excerpt
    assert len(excerpt) <= 1500
    assert excerpt in content


@pytest.mark.asyncio
async def test_duplicate_ingestions_do_not_crowd_out_distinct_evidence(monkeypatch):
    import app.services.vector_search_service as module

    pageless = SimpleNamespace(**row(VALID, 1))
    pageless.page_number = None
    paged = SimpleNamespace(**row(VALID, 2))
    other = SimpleNamespace(
        **row("At least three independent entities must form the research consortium.", 3)
    )
    vector = Mock()
    vector.hybrid_search.return_value = [pageless, paged, other]
    monkeypatch.setattr(module, "VectorSearchService", Mock(return_value=vector))
    result = await search_documents_execute("research consortium requirements", max_results=2)
    assert result["total_found"] == 2
    assert result["documents"][0]["chunk_id"] == paged.chunk_id
    assert result["documents"][1]["chunk_id"] == other.chunk_id


def test_filtered_hybrid_search_uses_the_existing_filtered_rpc_once():
    source = Mock()
    source.semantic_search.return_value = [row(VALID)]
    embedder = Mock()
    embedder.generate_query_embedding.return_value = np.ones(3072)
    service = VectorSearchService(source, embedder)
    results = service.hybrid_search(
        "consortium guidance", filters={"document_type": "work_programme"}
    )
    assert [result.content for result in results] == [VALID]
    assert source.semantic_search.call_args.kwargs["filters"] == {"document_type": "work_programme"}
    source.hybrid_search.assert_not_called()
    embedder.generate_query_embedding.assert_called_once()

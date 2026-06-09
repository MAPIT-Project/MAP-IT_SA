from unittest.mock import MagicMock, patch

import pytest

from app.services.proposal_session.document_state_service import DocumentStateService
from app.services.proposal_session.proposal_session_manager import ProposalSessionManager
from app.services.proposal_session.session_state import ProposalSessionState, SectionStatus


def test_proposal_session_state_create_new():
    """Test that session state initializes with correct sections dynamically."""
    # Test ERC
    session_erc = ProposalSessionState.create_new(
        user_id="test-user",
        proposal_id=1,
        call_id="ERC-TEST-CALL",
        title="Test ERC Proposal",
        proposal_type="ERC",
    )
    assert len(session_erc.document.sections) == 5
    assert "excellence.synopsis" in session_erc.document.sections
    assert "excellence.cv_track" in session_erc.document.sections
    assert "excellence.scientific_proposal" in session_erc.document.sections
    assert "implementation.funding_id" in session_erc.document.sections
    assert "implementation.resources" in session_erc.document.sections
    assert (
        session_erc.document.sections["excellence.synopsis"].section_name
        == "Part B1 - Section a: Extended Synopsis"
    )

    # Test EIC Accelerator
    session_eic = ProposalSessionState.create_new(
        user_id="test-user",
        proposal_id=2,
        call_id="EIC-ACCELERATOR-TEST",
        title="Test EIC Proposal",
        proposal_type="EIC-ACCELERATOR",
    )
    assert len(session_eic.document.sections) == 12
    assert "business.description" in session_eic.document.sections
    assert "impact.broad" in session_eic.document.sections
    assert (
        session_eic.document.sections["business.description"].section_name
        == "1. Company Description"
    )


def test_document_state_service_get_standard_sections():
    """Test that DocumentStateService retrieves standard sections dynamically."""
    service = DocumentStateService()

    sections_erc = service.get_standard_sections("ERC")
    assert len(sections_erc) == 5
    assert sections_erc[0] == ("excellence.synopsis", "Part B1 - Section a: Extended Synopsis")

    sections_msca = service.get_standard_sections("MSCA-PF")
    assert len(sections_msca) == 9
    assert sections_msca[0] == ("excellence.objectives", "1.1 Research and innovation objectives")


@pytest.mark.asyncio
@patch("app.services.proposal_session.proposal_session_manager.SimpleConnectionPool")
async def test_session_manager_load_existing_sections(mock_pool_cls):
    """Test that proposal session manager clears default sections and loads from DB when rows exist."""
    # Set up mock pool and cursor
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()

    mock_pool.getconn.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    # We mock the DATABASE_URL env var
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql://mock:mock@localhost:5432/mock"}):
        manager = ProposalSessionManager(database_url="postgresql://mock:mock@localhost:5432/mock")
        manager.db_pool = mock_pool

        # Mock database rows for proposal_sections
        mock_cur.fetchall.return_value = [
            {
                "section_id": "custom.section.1",
                "section_name": "Custom Section 1",
                "section_content": "This is content 1",
                "word_count": 10,
                "quality_score": 0.8,  # 0.8 * 5 = 4.0
                "version": 2,
            },
            {
                "section_id": "custom.section.2",
                "section_name": "Custom Section 2",
                "section_content": "This is content 2",
                "word_count": 120,
                "quality_score": None,
                "version": 1,
            },
        ]

        # Create a session with default sections
        session = ProposalSessionState.create_new(
            user_id="test-user",
            proposal_id=1,
            call_id="TEST-CALL",
            title="Test Proposal",
            proposal_type="RIA",
        )
        assert "excellence.objectives" in session.document.sections

        # Load sections
        await manager._load_existing_sections(session)

        # Verify default sections were cleared and new ones loaded
        assert "excellence.objectives" not in session.document.sections
        assert len(session.document.sections) == 2

        sec1 = session.document.sections["custom.section.1"]
        assert sec1.section_name == "Custom Section 1"
        assert sec1.content == "This is content 1"
        assert sec1.word_count == 10
        assert sec1.quality_score == 4.0
        assert sec1.version == 2
        assert sec1.status == SectionStatus.DRAFT

        sec2 = session.document.sections["custom.section.2"]
        assert sec2.section_name == "Custom Section 2"
        assert sec2.content == "This is content 2"
        assert sec2.word_count == 120
        assert sec2.quality_score is None
        assert sec2.version == 1
        assert sec2.status == SectionStatus.IN_REVIEW

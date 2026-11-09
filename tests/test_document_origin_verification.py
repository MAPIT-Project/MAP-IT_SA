from unittest.mock import Mock

import pytest

from scripts.verify_document_origins import verified_updates, checked_download, apply_updates


def record(**changes):
    return {'store': 'horizon_documents', 'id': 'test-id', 'file_hash': 'a' * 64,
            'status': 'active', 'metadata': {}, **changes}


def check(**changes):
    return {'url': 'https://culture.ec.europa.eu/example.pdf', 'status': 'downloaded',
            'sha256': 'a' * 64, **changes}


def test_only_exact_official_bytes_verify():
    rows = [record()]
    assert len(verified_updates(rows, [check()], 'today')) == 1
    assert not verified_updates(rows, [check(sha256='b' * 64)], 'today')
    assert not verified_updates(rows, [check(url='https://culture.ec.europa.eu.evil.test/a.pdf')], 'today')
    assert not verified_updates(rows, [check(status='unavailable')], 'today')


@pytest.mark.parametrize('changes', [
    {'status': 'archived'}, {'metadata': {'superseded_by': 'new'}},
    {'metadata': {'review_state': 'pending'}},
    {'metadata': {'provenance': {'status': 'new_revision_requires_review'}}},
    {'metadata': {'provenance': {'status': 'verified_exact_bytes'}}},
    {'metadata': {'provenance': {'warning': 'Publication date unresolved'}}},
])
def test_existing_reviews_and_warnings_are_preserved(changes):
    assert not verified_updates([record(**changes)], [check()], 'today')


def test_non_pdf_cannot_verify(monkeypatch):
    monkeypatch.setattr('scripts.verify_document_origins.fetch', lambda u: b'<html>Download</html>')
    assert checked_download('https://culture.ec.europa.eu/example.pdf')['status'] == 'not_pdf'


def test_changed_record_aborts_transaction():
    cursor = Mock(rowcount=0)
    conn = Mock()
    conn.__enter__ = Mock(return_value=conn)
    conn.__exit__ = Mock(return_value=False)
    manager = Mock()
    manager.__enter__ = Mock(return_value=cursor)
    manager.__exit__ = Mock(return_value=False)
    conn.cursor.return_value = manager
    updates = verified_updates([record()], [check()], 'today')
    with pytest.raises(ValueError, match='changed'):
        apply_updates(conn, updates)
    assert 'file_hash=%s' in cursor.execute.call_args.args[0]
    assert conn.__exit__.call_args.args[0] is ValueError


def test_audit_artifact_is_private_and_serializable(tmp_path):
    import json
    import stat
    from scripts.verify_document_origins import save_private
    target = tmp_path / 'report.json'
    save_private(target, {'matched_records': 1})
    assert json.loads(target.read_text()) == {'matched_records': 1}
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not target.with_name(target.name + '.tmp').exists()

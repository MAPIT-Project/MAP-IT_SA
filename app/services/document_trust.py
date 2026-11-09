"""Shared-publication retrieval policy, separate from legal applicability."""

VERIFIED_ORIGINS = frozenset({"verified_exact_bytes", "verified_official_download"})


def public_source_searchable(metadata):
    metadata = metadata or {}
    return (
        (metadata.get("provenance") or {}).get("status") in VERIFIED_ORIGINS
        and not metadata.get("superseded_by")
        and metadata.get("review_state") not in {"pending", "quarantined"}
        and metadata.get("retrieval_status") != "quarantined"
    )


def quarantine_candidate(row):
    """Only unresolved active public records; pending decisions keep their own lifecycle."""
    metadata = row.get("metadata") or {}
    return (
        row.get("created_by") is None
        and row.get("status", "active") == "active"
        and not metadata.get("superseded_by")
        and metadata.get("review_state") not in {"pending", "quarantined"}
        and metadata.get("retrieval_status") != "quarantined"
        and not public_source_searchable(metadata)
    )

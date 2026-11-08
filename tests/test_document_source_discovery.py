from app.services.document_source_discovery import (
    extract_cellar_pdf_items,
    extract_official_downloads,
    circabc_public_folder_url,
    extract_circabc_public_pdfs,
)


def test_circabc_public_library_route_is_spaces_with_guest_mode():
    url = circabc_public_folder_url("ce976713-0506-4fd0-b19a-6f4dc6c23fe6")
    assert "/spaces/ce976713-0506-4fd0-b19a-6f4dc6c23fe6/children?guest=true" in url
    assert "/nodes/" not in url


def test_circabc_parser_respects_public_access_and_pdf_type():
    def node(identifier, allowed, mime):
        return {
            "id": identifier,
            "name": "Decision & Annex.PDF",
            "properties": {"currentUserHasAccess": allowed, "mimetype": mime},
        }

    result = extract_circabc_public_pdfs(
        {
            "data": [
                node("8add8eee-106e-4e6a-9481-36b06495136c", "true", "application/pdf"),
                node("332ff065-5d4d-4bcf-8695-b2540f5f4823", "false", "application/pdf"),
                node("d7ebcccb-48d3-4b7a-9542-6c7fa6f9cc67", "true", "text/html"),
            ]
        }
    )
    assert len(result) == 1
    assert result[0]["url"].endswith("/Decision%20%26%20Annex.PDF")


def test_custom_downloads_and_anchors_are_discovered_once():
    html = '<eac-download url="/files/wp2027.pdf" title="Programme"></eac-download><a href="/files/wp2027.pdf#page=2">Download</a>'
    assert extract_official_downloads(html, "https://culture.ec.europa.eu/node/4091") == [
        "https://culture.ec.europa.eu/files/wp2027.pdf"
    ]


def test_offsite_insecure_and_credential_links_are_rejected():
    html = """<eac-download url="https://culture.ec.europa.eu.evil.org/file.pdf"></eac-download>
    <a href="http://culture.ec.europa.eu/file.pdf">HTTP</a>
    <a href="https://user:password@culture.ec.europa.eu/file.pdf">Credentials</a>"""
    assert extract_official_downloads(html, "https://culture.ec.europa.eu/node/4091") == []
    assert extract_official_downloads('<a href="/fake.pdf">File</a>', "https://example.org") == []


def test_cellar_pdf_is_not_confused_with_cover_item():
    xml = """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:c="http://publications.europa.eu/ontology/cdm#"
    xmlns:m="http://publications.europa.eu/ontology/cdm/cmr#">
    <rdf:Description rdf:about="http://publications.europa.eu/resource/cellar/test/DOC_1">
      <c:item_identifier>DOC_1</c:item_identifier><m:manifestationMimeType>application/pdf</m:manifestationMimeType>
    </rdf:Description>
    <rdf:Description rdf:about="http://publications.europa.eu/resource/cellar/test/DOC_2">
      <c:item_identifier>DOC_2</c:item_identifier><m:manifestationMimeType>image/jpeg</m:manifestationMimeType>
    </rdf:Description></rdf:RDF>"""
    assert extract_cellar_pdf_items(xml) == [
        "https://publications.europa.eu/resource/cellar/test/DOC_1"
    ]

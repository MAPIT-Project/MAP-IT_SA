"""Extract download references from official HTML and Cellar metadata.

Discovery is not approval: callers must still download, identify and hash the PDF.
No network requests or document-store writes occur here.
"""

from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree
from urllib.parse import quote
from uuid import UUID

OFFICIAL_PUBLISHERS = {
    "ec.europa.eu",
    "culture.ec.europa.eu",
    "erasmus-plus.ec.europa.eu",
    "publications.europa.eu",
    "op.europa.eu",
    "cinea.ec.europa.eu",
    "environment.ec.europa.eu",
    "health.ec.europa.eu",
    "research-and-innovation.ec.europa.eu",
    "eic.ec.europa.eu",
    "cybersecurity-centre.europa.eu",
    "circabc.europa.eu",
}


def official_https_url(value, base_url, hosts):
    parsed = urlsplit(urljoin(base_url, value))
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname not in hosts
        or parsed.username
        or parsed.password
        or not valid_port
    ):
        return None
    return urlunsplit(parsed._replace(fragment=""))


def extract_official_downloads(html, page_url):
    """Include EAC custom download elements, which ordinary anchor crawlers miss."""
    hosts = {urlsplit(page_url).hostname}
    if not hosts.issubset(OFFICIAL_PUBLISHERS):
        return []
    found = set()

    class Downloads(HTMLParser):
        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            value = (
                attrs.get("href")
                if tag == "a"
                else attrs.get("url") if tag == "eac-download" else None
            )
            if not value:
                return
            url = official_https_url(value, page_url, hosts)
            if url and urlsplit(url).path.lower().endswith(".pdf"):
                found.add(url)

    Downloads().feed(html)
    return sorted(found)


def extract_cellar_pdf_items(rdf):
    """Select real PDF manifestations, not DOC_2 cover/thumbnail items."""
    cdm = "http://publications.europa.eu/ontology/cdm#"
    cmr = "http://publications.europa.eu/ontology/cdm/cmr#"
    rdf_namespace = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    found = set()
    for node in ElementTree.fromstring(rdf):
        if node.find(f"{{{cdm}}}item_identifier") is None:
            continue
        mime = node.find(f"{{{cmr}}}manifestationMimeType")
        if mime is None or mime.text != "application/pdf":
            continue
        parsed = urlsplit(node.get(f"{{{rdf_namespace}}}about", ""))
        # Cellar RDF uses HTTP resource identifiers; downloads use HTTPS.
        url = urlunsplit(parsed._replace(scheme="https"))
        normalized = official_https_url(
            url, "https://publications.europa.eu", {"publications.europa.eu"}
        )
        if normalized and parsed.path.startswith("/resource/cellar/"):
            found.add(normalized)
    return sorted(found)


def circabc_public_folder_url(folder_id):
    """Use the website's public library route, without credentials."""
    identifier = str(UUID(folder_id))
    return (
        f"https://circabc.europa.eu/service/circabc/spaces/{identifier}/children"
        "?guest=true&language=en&limit=100&page=1"
    )


def extract_circabc_public_pdfs(payload):
    """Only expose PDFs that the public response explicitly permits reading."""
    results = []
    for node in payload.get("data", []):
        properties = node.get("properties") or {}
        if properties.get("currentUserHasAccess") not in (True, "true"):
            continue
        if properties.get("mimetype") != "application/pdf":
            continue
        identifier = str(UUID(node["id"]))
        results.append(
            {
                "id": identifier,
                "name": node["name"],
                "url": f"https://circabc.europa.eu/sd/a/{identifier}/"
                + quote(node["name"], safe=""),
            }
        )
    return results

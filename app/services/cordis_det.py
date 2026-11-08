"""Explicit mapping of the CORDIS DET project JSON schema observed in November 2026."""

import io
import json
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .cordis_import import FIELDS, DATES, NUMBERS, REQUIRED

ORG_FIELDS = (
    "projectID projectAcronym organisationID vatNumber name shortName SME activityType "
    "street postCode city country nutsCode geolocation organizationURL contactForm "
    "contentUpdateDate rcn order role ecContribution netEcContribution totalCost "
    "endOfParticipation active"
).split()
ROLES = {"participant", "coordinator", "associatedPartner", "thirdParty"}


def boolean(value):
    if value in (None, ""):
        return None
    if value not in ("true", "false"):
        raise ValueError("Unknown CORDIS boolean")
    return value == "true"


def number(value):
    if value in (None, ""):
        return None
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Invalid CORDIS amount")
    return result


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.astimezone(timezone.utc).replace(tzinfo=None) if result.tzinfo else result


def map_project(source):
    if source.get("contenttype") != "project" or source.get("language") != "en":
        raise ValueError("Expected English CORDIS project")
    row = {k: v for k, v in source.items() if k in FIELDS and v not in (None, "")}
    if not REQUIRED.issubset(row):
        raise ValueError("Missing required project fields")
    for k in ("id", "rcn"):
        if k in row:
            row[k] = int(row[k])
            if not 0 < row[k] <= 2147483647:
                raise ValueError("Invalid project identifier")
    for k in DATES:
        if k in row:
            row[k] = datetime.fromisoformat(row[k]).date()
    row["contentUpdateDate"] = timestamp(row["contentUpdateDate"])
    for k in NUMBERS:
        if k in row:
            row[k] = number(row[k])
            if row[k] < 0:
                raise ValueError("Negative project amount")
    row["grantDoi"] = source.get("identifiers", {}).get("grantDoi")
    relations = source.get("relations", {})
    associations = relations.get("associations", [])
    topics, bases, programmes = [], [], set()
    for item in associations:
        kind = item.get("attributes", {}).get("type")
        if item.get("contenttype") == "programme":
            if kind in ("relatedTopic", "relatedLegalBasis"):
                programmes.add(item["frameworkProgramme"])
            if kind == "relatedTopic":
                topics.append(item["code"])
            if kind == "relatedLegalBasis":
                bases.append(item["code"])
        if item.get("contenttype") == "call":
            field = {"relatedMasterCall": "masterCall", "relatedSubCall": "subCall"}.get(kind)
            if field:
                if field in row and row[field] != item["identifier"]:
                    raise ValueError("Ambiguous CORDIS call mapping")
                row[field] = item["identifier"]
    if programmes != {"HORIZON"}:
        raise ValueError("Expected a Horizon Europe export")
    row["frameworkProgramme"] = "HORIZON"
    row["topics"] = ";".join(dict.fromkeys(topics)) or None
    row["legalBasis"] = ";".join(dict.fromkeys(bases)) or None
    schemes = {
        c["code"].removeprefix("/")
        for c in relations.get("categories", [])
        if c.get("attributes", {}).get("classification") == "projectFundingSchemeCategory"
    }
    if len(schemes) > 1:
        raise ValueError("Ambiguous funding scheme")
    row["fundingScheme"] = next(iter(schemes), None)
    organizations = []
    for item in associations:
        if item.get("contenttype") != "organization":
            continue
        attrs = item.get("attributes", {})
        if attrs.get("source") != "corda" or attrs.get("type") not in ROLES:
            raise ValueError("Unknown organization relationship")
        address = item.get("address", {})
        org = dict.fromkeys(ORG_FIELDS)
        org.update(
            projectID=row["id"],
            projectAcronym=row.get("acronym"),
            organisationID=str(item["id"]),
            name=item["legalName"],
            vatNumber=item.get("vatNumber"),
            shortName=item.get("shortName"),
            SME=boolean(attrs.get("sme")),
            role=attrs["type"],
            endOfParticipation=boolean(attrs.get("terminated")),
            active=boolean(attrs.get("active")),
            rcn=int(item["rcn"]),
            order=int(attrs["order"]) if attrs.get("order") else None,
            contentUpdateDate=row["contentUpdateDate"],
        )
        for field, key in [
            ("street", "street"),
            ("postCode", "postalCode"),
            ("city", "city"),
            ("country", "country"),
            ("geolocation", "geolocation"),
            ("organizationURL", "url"),
        ]:
            org[field] = address.get(key)
        for field in ("ecContribution", "netEcContribution", "totalCost"):
            org[field] = number(attrs.get(field))
        org_rel = item.get("relations", {})
        types = {
            c["code"].removeprefix("/")
            for c in org_rel.get("categories", [])
            if c.get("attributes", {}).get("classification") == "organizationActivityType"
        }
        nuts = {
            c["nutsCode"]
            for c in org_rel.get("regions", [])
            if c.get("attributes", {}).get("type") == "relatedNutsCode" and c.get("nutsCode")
        }
        if len(types) > 1:
            raise ValueError("Ambiguous organization classification")
        org["activityType"] = next(iter(types), None)
        org["nutsCode"] = ";".join(sorted(nuts)) or None
        if not org["organisationID"] or not org["name"]:
            raise ValueError("Missing organization identity")
        organizations.append(org)
    if not organizations or sum(o["role"] == "coordinator" for o in organizations) != 1:
        raise ValueError("Expected exactly one coordinator per project")
    return row, organizations


def parse_det_json(path):
    """Read bounded nested JSON without extracting paths or repairing malformed CSV."""
    path = Path(path)
    if path.stat().st_size > 250 * 1024**2:
        raise ValueError("Export too large")
    projects, organizations, seen = [], [], set()
    with zipfile.ZipFile(path) as outer:
        wrapped = outer.infolist()
        nested = [m for m in wrapped if m.filename == "json.zip"]
        if len(nested) != 1 or nested[0].file_size > 250 * 1024**2:
            raise ValueError("Expected bounded json.zip")
        with zipfile.ZipFile(io.BytesIO(outer.read(nested[0]))) as archive:
            members = [m for m in archive.infolist() if m.filename.endswith(".json")]
            if not 0 < len(members) <= 100000 or sum(m.file_size for m in members) > 2 * 1024**3:
                raise ValueError("Invalid project archive size")
            for member in members:
                if member.file_size > 10 * 1024**2:
                    raise ValueError("Project file too large")
                row, orgs = map_project(json.loads(archive.read(member)))
                if row["id"] in seen:
                    raise ValueError("Duplicate project")
                seen.add(row["id"])
                projects.append(row)
                organizations.extend(orgs)
    return projects, organizations

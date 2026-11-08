#!/usr/bin/env python3
"""Validate a CORDIS canonical project CSV; explicitly --apply to update MAPIT."""

import argparse
import json
import psycopg2
import zipfile
import csv

from app.core.config import settings
from app.services.cordis_import import parse_projects, import_projects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", default="data/cordis_backups")
    parser.add_argument(
        "--det-json",
        action="store_true",
        help="Import observed DET JSON project and consortium schema",
    )
    args = parser.parse_args()
    try:
        organizations = None
        if args.det_json:
            from app.services.cordis_det import parse_det_json

            rows, organizations = parse_det_json(args.export)
        else:
            rows = parse_projects(args.export)
        result = (
            import_projects(
                settings.database_url, rows, args.backup_dir, organizations=organizations
            )
            if args.apply
            else {
                "validated_projects": len(rows),
                "validated_organization_rows": len(organizations)
                if organizations is not None
                else None,
                "latest_source_update": max(r["contentUpdateDate"] for r in rows).isoformat(),
                "writes": False,
            }
        )
        print(json.dumps(result))
    except (ValueError, OSError, psycopg2.Error, zipfile.BadZipFile, csv.Error):
        parser.exit(
            1, "CORDIS export validation/import failed; inspect the input schema before retrying\n"
        )


if __name__ == "__main__":
    main()

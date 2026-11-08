#!/usr/bin/env python3
"""Refresh official open/upcoming call data; exit nonzero on incomplete refresh."""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.call_catalog import CallCatalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument(
        "--health", action="store_true", help="Check freshness without fetching or writing"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    catalog = CallCatalog(settings.database_url)
    try:
        result = catalog.health() if args.health else catalog.sync(max_pages=args.max_pages)
    except Exception:
        logging.exception("Official call catalogue refresh failed; previous data remains available")
        return 1
    print(json.dumps(result))
    return 1 if result.get("stale") else 0


if __name__ == "__main__":
    raise SystemExit(main())

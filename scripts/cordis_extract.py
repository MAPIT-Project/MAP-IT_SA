#!/usr/bin/env python3
"""Manage CORDIS DET exports without exposing credentials or cancelling tasks."""

import argparse
import json
import sys

from app.core.config import settings
from app.services.cordis_api import CordisClient, CordisError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check-key", action="store_true", help="Read the task list only")
    actions.add_argument(
        "--start", metavar="QUERY", help="Create a new extraction after checking for active tasks"
    )
    actions.add_argument("--status", type=int, metavar="TASK_ID")
    actions.add_argument("--download", type=int, metavar="TASK_ID")
    parser.add_argument(
        "--format", choices=["csv", "json", "xml", "xlsx", "summary"], default="csv"
    )
    parser.add_argument("--output", help="Destination file for --download; must not exist")
    parser.add_argument(
        "--wait", action="store_true", help="Poll a newly created extraction for up to 10 minutes"
    )
    args = parser.parse_args()
    if args.download and not args.output:
        parser.error("--download requires --output")
    if args.wait and args.start is None:
        parser.error("--wait requires --start")
    try:
        client = CordisClient(settings.cordis_api_key)
        if args.check_key:
            tasks = client.list_extractions()
            result = {"connection": "verified", "tasks": [client.safe_task(t) for t in tasks]}
        elif args.start is not None:
            task = client.create_extraction(args.start, args.format)
            print(
                "CORDIS extraction created; task ID: " + str(task["taskID"]),
                file=sys.stderr,
                flush=True,
            )
            if args.wait:
                task = client.wait(task["taskID"])
            result = client.safe_task(task)
        elif args.status is not None:
            result = client.safe_task(client.extraction_status(args.status))
        else:
            result = client.download(args.download, args.output)
        print(json.dumps(result))
    except CordisError as error:
        # CordisError messages are deliberately independent of request URLs.
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()

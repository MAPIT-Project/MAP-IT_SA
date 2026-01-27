#!/usr/bin/env python3
import argparse
import json
import os
import time
from typing import Any

import requests


def load_queries() -> list[dict[str, Any]]:
    return [
        {
            "name": "calls_clean_energy",
            "question": "Tell me about funding opportunities in clean energy research",
            "expected_route": "SEARCH_CALLS",
            "must_contain": ["portal", "call", "topic"],
            "must_not_contain": ["CORDIS database"],
        },
        {
            "name": "projects_battery",
            "question": "Show me projects on battery recycling",
            "expected_route": "SEARCH_PROJECTS",
            "must_contain": ["project", "CORDIS"],
            "must_not_contain": ["open calls"],
        },
        {
            "name": "faq_apply",
            "question": "How do I apply on the EU Funding & Tenders portal?",
            "expected_route": "FAQ",
            "must_contain": ["portal"],
            "must_not_contain": [],
        },
        {
            "name": "capabilities",
            "question": "What can you help me with?",
            "expected_route": "FAQ",
            "must_contain": ["open funding opportunities", "CORDIS", "FAQs"],
            "must_not_contain": ["creative content", "translate"],
        },
    ]


def score_response(item: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
    text = (resp.get("response") or "").lower()
    route = resp.get("routing_decision")
    data_source = resp.get("data_source")

    checks = {
        "route_ok": route == item["expected_route"],
        "contains": all(term.lower() in text for term in item["must_contain"]),
        "not_contains": all(term.lower() not in text for term in item["must_not_contain"]),
    }
    score = sum(checks.values()) / len(checks) if checks else 0.0
    return {
        "question": item["question"],
        "expected_route": item["expected_route"],
        "routing_decision": route,
        "data_source": data_source,
        "score": score,
        "checks": checks,
        "answer_preview": text[:300],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=os.getenv("API_BASE", "http://localhost:8000"))
    parser.add_argument("--conversation", type=int, default=424242)
    args = parser.parse_args()

    url = f"{args.api}/api/conversation/{args.conversation}/message"
    results = []
    queries = load_queries()

    for q in queries:
        payload = {"message": q["question"], "include_context": False}
        t0 = time.time()
        r = requests.post(url, json=payload, timeout=60)
        elapsed = time.time() - t0
        try:
            data = r.json()
        except Exception:
            data = {"error": f"non-json response: {r.text[:200]}"}
        scored = score_response(q, data if isinstance(data, dict) else {})
        scored["status_code"] = r.status_code
        scored["latency_s"] = round(elapsed, 2)
        results.append(scored)

    summary = {
        "timestamp": int(time.time()),
        "api": args.api,
        "conversation": args.conversation,
        "results": results,
        "avg_score": round(sum(x["score"] for x in results) / len(results), 3),
        "failures": [x for x in results if x["score"] < 1.0],
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

"""Keep every shortlisted call visible to the model instead of cutting JSON mid-record."""

import json


def compact_call_context(result: dict, max_chars: int) -> dict:
    key = "calls" if isinstance(result.get("calls"), list) else "results"
    if not isinstance(result.get(key), list):
        return result
    rows = result[key]
    keep = {
        "success",
        "error",
        "calls_found",
        "total_results",
        "catalogue",
        "limitations",
        "status_filter",
        "query",
        "programmes_searched",
        "programmes_with_results",
    }
    summary = {k: v for k, v in result.items() if k in keep}
    summary["details_available_via"] = "get_call_details"
    fields = {
        "call_id",
        "topic_code",
        "title",
        "programme",
        "programme_name",
        "deadline",
        "opening_date",
        "second_stage_deadline",
        "status",
        "call_year",
        "url",
        "portal_url",
        "type",
        "action_type",
        "budget",
        "cluster",
        "scope",
        "expected_outcome",
    }
    summaries = [
        {k: v for k, v in row.items() if k in fields} for row in rows if isinstance(row, dict)
    ]
    for text_limit in (600, 200, 0):
        summary[key] = [
            {
                k: (str(v)[:text_limit] if k in ("scope", "expected_outcome") else v)
                for k, v in row.items()
            }
            for row in summaries
        ]
        if len(json.dumps(summary, ensure_ascii=False, default=str)) <= max_chars:
            return summary
    while summary[key]:
        summary[key].pop()
        summary["results_omitted"] = len(rows) - len(summary[key])
        if len(json.dumps(summary, ensure_ascii=False, default=str)) <= max_chars:
            return summary
    return {
        "error": "Call summaries exceed model context budget; narrow the search.",
        "total_results": len(rows),
    }

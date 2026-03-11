"""
Response synthesis and formatting for ToolAwareAgent.
Handles converting raw tool results into human-readable responses.
Extracted from tool_aware_agent.py for maintainability.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .tool_aware_agent import AgentPlan

logger = logging.getLogger(__name__)


class ResponseSynthesizerMixin:
    """Mixin providing response synthesis and formatting for ToolAwareAgent."""

    def _is_show_more_request(self, query: str) -> bool:
        """Detect if user is asking to see more projects from a previous search."""
        patterns = [
            "show more",
            "more projects",
            "next page",
            "remaining project",
            "show the rest",
            "show more results",
            "continue showing",
            "next 20",
            "see more",
            "show additional",
            "see the remaining",
            "show next",
            "display more",
            "keep going",
            "show the other",
        ]
        lower = query.lower().strip()
        return any(p in lower for p in patterns)

    def _cache_merged_projects(self, merged_result: dict[str, Any]) -> None:
        """Cache full merged project results in Redis for pagination."""
        if not self._conversation_id or not self._redis_client:
            return
        try:
            key = f"merged_projects:{self._conversation_id}"
            self._redis_client.setex(key, 1800, json.dumps(merged_result))  # 30 min TTL
            # Reset page offset to end of first page
            page_key = f"project_page:{self._conversation_id}"
            self._redis_client.setex(page_key, 1800, str(merged_result["display_limit"]))
            logger.info(
                f"📦 Cached {len(merged_result['merged_projects'])} merged projects "
                f"for conversation {self._conversation_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to cache merged projects: {e}")

    def _handle_show_more_request(self, query: str) -> dict[str, Any] | None:
        """Handle 'show more projects' by serving next page from cached results."""
        if not self._is_show_more_request(query):
            return None

        logger.info(
            f"🔍 'Show more' detected for query: '{query}', "
            f"conversation_id={self._conversation_id}, redis={self._redis_client is not None}"
        )

        if not self._conversation_id or not self._redis_client:
            logger.warning("Cannot serve cached page: no conversation_id or redis_client")
            return None

        try:
            key = f"merged_projects:{self._conversation_id}"
            cached = self._redis_client.get(key)
            if not cached:
                logger.info(
                    f"No cached merged projects found at key '{key}' for 'show more' request"
                )
                return None

            merged_result = json.loads(cached)
            page_key = f"project_page:{self._conversation_id}"
            current_offset = int(self._redis_client.get(page_key) or 20)

            projects = merged_result["merged_projects"]
            display_limit = merged_result["display_limit"]

            # Check if there are more projects to show
            if current_offset >= len(projects):
                return {
                    "answer": (
                        f"You've already seen all **{len(projects)}** matching projects "
                        f"from the previous search for *{merged_result['query_description']}*."
                    ),
                    "success": True,
                    "reasoning_steps": [],
                    "sources_used": ["cached_results"],
                    "tool_results": {},
                    "iterations": 0,
                    "confidence": 0.95,
                    "model_used": "cached_pagination",
                }

            # Render next page using the same table format
            answer = self._render_merged_project_list(merged_result, offset=current_offset)

            # Update offset for next "show more"
            new_offset = min(current_offset + display_limit, len(projects))
            self._redis_client.setex(page_key, 1800, str(new_offset))

            logger.info(
                f"📄 Serving cached page: projects {current_offset + 1}–{new_offset} "
                f"of {len(projects)} for conversation {self._conversation_id}"
            )

            return {
                "answer": answer,
                "success": True,
                "reasoning_steps": [],
                "sources_used": ["cached_results"],
                "tool_results": {},
                "iterations": 0,
                "confidence": 0.95,
                "model_used": "cached_pagination",
            }

        except Exception as e:
            logger.warning(f"Failed to handle 'show more' request: {e}")
            return None

    def _merge_project_search_results(
        self,
        tool_results: dict[str, Any],
        query: str,
        display_limit: int = 20,
    ) -> dict[str, Any] | None:
        """Merge similar_projects and search_projects into one ranked list.

        When both semantic and keyword results exist, combines them into a single
        deduplicated, ranked list. Semantic matches keep their similarity scores;
        keyword-only matches get a lower default score.

        Returns merged result dict if both exist, None otherwise.
        """
        similar_results = []
        keyword_results = []
        query_desc = ""
        filters = {}

        for _name, r in tool_results.items():
            if not isinstance(r, dict):
                continue
            if "similar_projects" in r and isinstance(r.get("similar_projects"), list):
                similar_results.extend(r["similar_projects"])
                query_desc = r.get("query_description", query_desc)
                filters = r.get("filters_applied", filters)
            elif "projects" in r and isinstance(r.get("projects"), list):
                keyword_results.extend(r["projects"])

        # Only merge when semantic results exist — keyword-only results should be
        # left for the LLM to synthesize (e.g., org stats queries return projects
        # but the user wants counts, not a project table).
        if not similar_results:
            return None

        # Build unified list: normalize to common format, deduplicate by acronym
        merged: dict[str, dict[str, Any]] = {}

        # Add semantic results first (they have real similarity scores)
        for p in similar_results:
            acronym = (p.get("acronym") or "").strip().upper()
            if not acronym:
                continue
            pid = str(p.get("cordis_id") or p.get("id") or p.get("project_id") or "")
            consortium = p.get("consortium", {})
            merged[acronym] = {
                "acronym": p.get("acronym", "N/A"),
                "title": p.get("title", "N/A"),
                "id": pid,
                "similarity_score": p.get("similarity_score", 0),
                "eu_contribution": p.get("eu_contribution", p.get("total_cost", 0)),
                "total_cost": p.get("total_cost", 0),
                "action_type": p.get("action_type", "N/A"),
                "objective": p.get("objective") or p.get("objective_summary", ""),
                "start_date": p.get("start_date", ""),
                "end_date": p.get("end_date", ""),
                "coordinator": consortium.get("coordinator", {}).get("name", ""),
                "coordinator_country": consortium.get("coordinator", {}).get("country", ""),
                "partner_count": consortium.get("size", p.get("partner_count", 0)),
                "country_count": 0,
                "countries": [],
                "cluster": p.get("cluster", ""),
                "topics": p.get("topics", ""),
                "status": p.get("status", ""),
                "funding_scheme": p.get("action_type", ""),
                "cordis_url": p.get("cordis_url", ""),
                "source": "semantic",
            }

        # Add keyword results — enrich existing or add new (with lower score)
        for p in keyword_results:
            acronym = (p.get("acronym") or "").strip().upper()
            if not acronym:
                continue
            pid = str(p.get("cordis_id") or p.get("id") or p.get("project_id") or "")
            consortium = p.get("consortium", {})
            coord_raw = p.get("coordinator_name") or p.get("coordinator", "")
            if isinstance(coord_raw, dict):
                coord_name = coord_raw.get("name", "")
                coord_country = coord_raw.get("country", "")
            else:
                coord_name = str(coord_raw) if coord_raw else ""
                coord_country = ""

            if acronym in merged:
                # Enrich existing semantic match with keyword data
                existing = merged[acronym]
                existing["source"] = "both"
                if not existing.get("id") and pid:
                    existing["id"] = pid
                if not existing.get("total_cost"):
                    existing["total_cost"] = p.get("total_cost", 0)
                if not existing.get("eu_contribution"):
                    existing["eu_contribution"] = (
                        p.get("ec_contribution") or p.get("ecMaxContribution") or 0
                    )
                if not existing.get("coordinator") and coord_name:
                    existing["coordinator"] = coord_name
                    existing["coordinator_country"] = coord_country
                if not existing.get("country_count") and consortium:
                    existing["country_count"] = consortium.get("country_count", 0)
                    existing["countries"] = consortium.get("countries", [])
                if not existing.get("partner_count") and consortium:
                    existing["partner_count"] = consortium.get("participant_count", 0)
                if not existing.get("status"):
                    existing["status"] = p.get("status", "")
                if not existing.get("topics"):
                    existing["topics"] = p.get("topics", "")
                obj = p.get("objective") or p.get("description", "")
                if obj and len(obj) > len(existing.get("objective", "")):
                    existing["objective"] = obj
                if not existing.get("cordis_url"):
                    existing["cordis_url"] = p.get("cordis_url", "")
            else:
                # New project from keyword search only — lower default score
                merged[acronym] = {
                    "acronym": p.get("acronym", ""),
                    "title": p.get("title", ""),
                    "id": pid,
                    "similarity_score": 0.50,
                    "eu_contribution": p.get("ec_contribution") or p.get("ecMaxContribution") or 0,
                    "total_cost": p.get("total_cost", 0),
                    "action_type": p.get("funding_scheme", "N/A"),
                    "objective": p.get("objective") or p.get("description", ""),
                    "start_date": p.get("start_date", ""),
                    "end_date": p.get("end_date", ""),
                    "coordinator": coord_name,
                    "coordinator_country": coord_country,
                    "partner_count": consortium.get("participant_count", 0),
                    "country_count": consortium.get("country_count", 0),
                    "countries": consortium.get("countries", []),
                    "cluster": "",
                    "topics": p.get("topics", ""),
                    "status": p.get("status", ""),
                    "funding_scheme": p.get("funding_scheme", ""),
                    "cordis_url": p.get("cordis_url", ""),
                    "source": "keyword",
                }

        # Sort by similarity score descending
        all_projects = sorted(
            merged.values(), key=lambda x: x.get("similarity_score", 0), reverse=True
        )

        return {
            "merged_projects": all_projects,
            "total_found": len(all_projects),
            "display_limit": display_limit,
            "query_description": query_desc or query,
            "filters": filters,
        }

    def _render_merged_project_list(self, merged: dict[str, Any], offset: int = 0) -> str:
        """Render the merged project list with conversational intro + table + details.

        Args:
            merged: Merged project data from _merge_project_search_results
            offset: Starting index for pagination (0 = first page)
        """
        projects = merged["merged_projects"]
        total = merged["total_found"]
        display_limit = merged["display_limit"]
        query_desc = merged["query_description"]
        page_end = min(offset + display_limit, len(projects))
        show_projects = projects[offset:page_end]

        parts: list[str] = []

        # ── Conversational introduction ──
        action_types = {}
        coordinators = {}
        total_budget = 0
        for p in show_projects:
            at = p.get("action_type") or p.get("funding_scheme", "")
            if at:
                action_types[at] = action_types.get(at, 0) + 1
            coord_country = p.get("coordinator_country", "")
            if coord_country:
                coordinators[coord_country] = coordinators.get(coord_country, 0) + 1
            budget = p.get("eu_contribution", 0)
            if budget:
                total_budget += budget

        top_type = max(action_types, key=action_types.get) if action_types else "RIA"
        top_countries = sorted(coordinators, key=coordinators.get, reverse=True)[:3]

        if offset == 0:
            # First page — full intro
            parts.append(
                f"## Relevant Funded Projects\n\n"
                f"I found **{total} funded Horizon Europe projects** related to "
                f"*{query_desc}*. The top {min(display_limit, total)} most relevant are shown "
                f"below, ranked by semantic similarity to your query."
            )
            if total_budget > 0:
                parts.append(
                    f"\nThese projects represent a combined EU investment of "
                    f"**€{total_budget / 1_000_000:.0f}M**, predominantly funded as "
                    f"**{top_type}** actions"
                    + (
                        f", with leading coordinators from **{', '.join(top_countries)}**."
                        if top_countries
                        else "."
                    )
                )
        else:
            # Continuation page
            parts.append(
                f"## More Funded Projects (#{offset + 1}–{page_end})\n\n"
                f"Continuing results for *{query_desc}*."
            )

        parts.append("")

        # ── Summary table ──
        parts.append("| # | Project | Type | Budget | Partners | Coordinator | Duration | CORDIS |")
        parts.append("|---|---------|------|--------|----------|-------------|----------|--------|")

        for i, p in enumerate(show_projects, offset + 1):
            acronym = p.get("acronym", "N/A")
            score = p.get("similarity_score", 0)
            pid = p.get("id", "")
            budget = p.get("eu_contribution", 0)
            action_type = p.get("action_type") or p.get("funding_scheme", "N/A")
            start_date = p.get("start_date", "")
            end_date = p.get("end_date", "")
            coordinator = p.get("coordinator", "")
            coord_country = p.get("coordinator_country", "")
            partner_count = p.get("partner_count", 0)

            budget_str = f"€{budget / 1_000_000:.1f}M" if budget and budget > 0 else "—"
            score_pct = f"{score:.0%}" if score > 0 else ""
            coord_short = coordinator[:30] + "..." if len(coordinator) > 30 else coordinator
            coord_str = f"{coord_short} ({coord_country})" if coord_country else coord_short
            duration = f"{start_date[:7]}–{end_date[:7]}" if start_date and end_date else "—"
            partners_str = str(partner_count) if partner_count else "—"
            cordis_url = p.get("cordis_url") or (
                f"https://cordis.europa.eu/project/id/{pid}" if pid else ""
            )
            cordis_link = f"[Link]({cordis_url})" if cordis_url else "—"

            parts.append(
                f"| {i} | **{acronym}** ({score_pct}) | {action_type} | {budget_str} | "
                f"{partners_str} | {coord_str} | {duration} | {cordis_link} |"
            )

        parts.append("")

        # ── Project details ──
        parts.append("### Project Details\n")
        for i, p in enumerate(show_projects, offset + 1):
            acronym = p.get("acronym", "N/A")
            title = p.get("title", "N/A")
            objective = p.get("objective", "")
            topics = p.get("topics", "")

            obj_preview = objective[:250] + "..." if len(objective) > 250 else objective

            parts.append(f"**{i}. {acronym} — {title}**")
            if topics:
                parts.append(f"Topic: {topics}")
            if obj_preview:
                parts.append(f"{obj_preview}")
            parts.append("")

        # ── Show more / all shown hint ──
        remaining = len(projects) - page_end
        if remaining > 0:
            shown_label = f"top {page_end}" if offset == 0 else f"projects {offset + 1}–{page_end}"
            parts.append(
                f"---\n*Showing {shown_label} of {total} matching projects. "
                f"Ask me to **show more projects** to see the next batch.*"
            )
        else:
            parts.append(f"---\n*All {total} matching projects have been shown.*")

        return "\n".join(parts)

    def _synthesize_from_results(self, query: str, tool_results: dict[str, Any]) -> str:
        """Synthesize a coherent answer from tool results."""

        content_pieces = []

        # ── Check for pre-rendered content (e.g., from show_cached_projects) ──
        for _name, r in tool_results.items():
            if isinstance(r, dict) and "rendered_content" in r:
                return r["rendered_content"]

        # ── Pre-processing: merge similar_projects + search_projects if both exist ──
        merged_result = self._merge_project_search_results(tool_results, query)
        merged_tool_keys: set[str] = set()
        if merged_result:
            # Cache full merged results for "show more" pagination
            self._cache_merged_projects(merged_result)
            # Render the unified merged project list (first page)
            content_pieces.append(self._render_merged_project_list(merged_result))
            # Track which tool results were consumed so we skip them below
            for name, r in tool_results.items():
                if isinstance(r, dict) and (
                    "similar_projects" in r
                    or ("projects" in r and isinstance(r.get("projects"), list))
                ):
                    merged_tool_keys.add(name)

        # Pre-scan: collect detailed project data (from get_project_details)
        # keyed by project_id, so we can merge into search_projects entries
        detailed_project_data = {}
        for _name, r in tool_results.items():
            if (
                isinstance(r, dict)
                and "acronym" in r
                and "partners" in r
                and "organization" not in r
                and "project_acronym" not in r
            ):
                pid = r.get("project_id")
                if pid:
                    detailed_project_data[str(pid)] = r

        # Pre-scan: collect project IDs from search_projects results
        # so get_project_details handler can skip projects that will be merged
        search_project_ids = set()
        for _name, r in tool_results.items():
            if isinstance(r, dict) and "projects" in r and isinstance(r.get("projects"), list):
                for proj in r["projects"]:
                    pid = proj.get("id") or proj.get("project_id")
                    if pid:
                        search_project_ids.add(str(pid))

        # Pre-scan: if get_organization_stats results exist, skip verbose org project listings
        # (user asked for counts/stats, the listing is redundant)
        has_org_stats = any(
            isinstance(r, dict)
            and "project_count" in r
            and "coordinator_count" in r
            and "name" in r
            for r in tool_results.values()
        )

        for name, result in tool_results.items():
            # Skip tool results already consumed by the merge pre-processing
            if name in merged_tool_keys:
                continue

            if not isinstance(result, dict):
                continue

            # Extract documents
            if "documents" in result and isinstance(result["documents"], list):
                for doc in result["documents"][:10]:
                    content = doc.get("content", "")
                    if content and len(content) > 100:
                        content_pieces.append(content.strip())

            # Extract EU4Health template search results
            elif result.get("metadata", {}).get("tool") == "search_eu4health_templates":
                template_text = self._format_eu4health_template_search_result(result)
                if template_text:
                    content_pieces.append(template_text)

            # Extract Erasmus+ template search results (Programme Guide 2026)
            elif result.get("metadata", {}).get("tool") == "search_erasmus_templates":
                template_text = self._format_erasmus_template_search_result(result)
                if template_text:
                    content_pieces.append(template_text)

            # Extract multi-programme search results (search_all_programmes tool)
            elif "results_by_programme" in result and "programmes_searched" in result:
                multi_prog_text = self._format_multi_programme_search_result(result)
                if multi_prog_text:
                    content_pieces.append(multi_prog_text)

            # Extract calls info
            elif "calls" in result and isinstance(result["calls"], list):
                if len(result["calls"]) == 0:
                    # Only show "no calls found" if the query was actually about calls
                    # Skip this message for project searches where calls were fetched as a side-effect
                    pass
                else:
                    for call in result["calls"][:10]:
                        title = call.get("title", "")
                        call_id = call.get("topic_code", call.get("call_id", ""))
                        if title or call_id:
                            content_pieces.append(f"Call {call_id}: {title}")

            # Extract budget calculation results
            elif result.get("tool_name") == "calculate_budget" and result.get("success"):
                breakdown = result.get("breakdown", {})
                budget = result.get("calculated_budget", {})
                per_partner = result.get("per_partner", {})

                budget_text = f"""Budget Calculation Results:
- Total Budget: €{budget.get("total_cost", 0):,.0f}
- EU Contribution: €{budget.get("eu_contribution", 0):,.0f} ({budget.get("funding_rate", "100%")})

Breakdown:
- Personnel: €{breakdown.get("personnel", {}).get("amount", 0):,.0f} ({breakdown.get("personnel", {}).get("percentage", 0)}%)
- Equipment: €{breakdown.get("equipment", {}).get("amount", 0):,.0f} ({breakdown.get("equipment", {}).get("percentage", 0)}%)
- Travel: €{breakdown.get("travel", {}).get("amount", 0):,.0f} ({breakdown.get("travel", {}).get("percentage", 0)}%)
- Subcontracting: €{breakdown.get("subcontracting", {}).get("amount", 0):,.0f} ({breakdown.get("subcontracting", {}).get("percentage", 0)}%)
- Other Direct Costs: €{breakdown.get("other_direct", {}).get("amount", 0):,.0f} ({breakdown.get("other_direct", {}).get("percentage", 0)}%)
- Indirect Costs (25% flat rate): €{breakdown.get("indirect", {}).get("amount", 0):,.0f} ({breakdown.get("indirect", {}).get("percentage", 0)}%)

Per Partner Distribution:
- Average per partner: €{per_partner.get("average", 0):,.0f}
- Coordinator (typical): €{per_partner.get("coordinator_typical", 0):,.0f}
- Other partners (typical): €{per_partner.get("partner_typical", 0):,.0f}
"""
                content_pieces.append(budget_text)

            # Extract budget benchmark results (get_budget_benchmark tool)
            elif result.get("tool_name") == "get_budget_benchmark" and result.get("success"):
                stats = result.get("statistics", {})
                recommendations = result.get("recommendations", [])
                sample_projects = result.get("sample_projects", [])
                query_params = result.get("query_params", {})
                consortium_context = result.get("consortium_context", {})
                org_type_breakdown = result.get("budget_by_org_type", {})

                # Extract key statistics
                total_contribution = stats.get("total_eu_contribution", {})
                consortium_size = stats.get("consortium_size", {})
                per_partner = stats.get("budget_per_partner", {})
                projects_analyzed = stats.get("projects_analyzed", 0)

                # Build title based on query parameters
                action_type = query_params.get("action_type", "")
                cluster = query_params.get("cluster", "")
                title_parts = []
                if action_type:
                    title_parts.append(action_type)
                if cluster:
                    title_parts.append(f"Cluster {cluster.replace('CLUSTER-', '')}")
                title = " ".join(title_parts) if title_parts else "Horizon Europe"

                benchmark_parts = [f"## Budget Benchmarks: {title} Projects"]
                benchmark_parts.append(f"\n**Based on {projects_analyzed:,} funded projects**\n")

                # Total EU Contribution
                if total_contribution:
                    avg_budget = total_contribution.get("average", 0)
                    median_budget = total_contribution.get("median", 0)
                    min_budget = total_contribution.get("min", 0)
                    max_budget = total_contribution.get("max", 0)
                    p25 = total_contribution.get("percentile_25", 0)
                    p75 = total_contribution.get("percentile_75", 0)
                    p90 = total_contribution.get("percentile_90", 0)

                    benchmark_parts.append("### Total Project Budget")
                    benchmark_parts.append(f"- **Average:** €{avg_budget / 1_000_000:.1f}M")
                    benchmark_parts.append(f"- **Median:** €{median_budget / 1_000_000:.1f}M")
                    benchmark_parts.append(
                        f"- **Range:** €{min_budget / 1_000_000:.1f}M - €{max_budget / 1_000_000:.1f}M"
                    )
                    if p25 and p75:
                        benchmark_parts.append(
                            f"- **Interquartile (25th-75th):** €{p25 / 1_000_000:.1f}M - €{p75 / 1_000_000:.1f}M"
                        )
                    if p90:
                        benchmark_parts.append(f"- **90th Percentile:** €{p90 / 1_000_000:.1f}M")
                    benchmark_parts.append("")

                # Per-partner budget
                if per_partner:
                    avg_pp = per_partner.get("average", 0)
                    median_pp = per_partner.get("median", 0)
                    min_pp = per_partner.get("min", 0)
                    max_pp = per_partner.get("max", 0)

                    benchmark_parts.append("### Per-Partner Budget")
                    benchmark_parts.append(f"- **Average:** €{avg_pp:,.0f}")
                    benchmark_parts.append(f"- **Median:** €{median_pp:,.0f}")
                    benchmark_parts.append(f"- **Range:** €{min_pp:,.0f} - €{max_pp:,.0f}")
                    benchmark_parts.append("")

                # Consortium size
                if consortium_size:
                    avg_partners = consortium_size.get("average", 0)
                    median_partners = consortium_size.get("median", 0)
                    avg_countries = consortium_size.get("avg_countries", 0)

                    benchmark_parts.append("### Consortium Size")
                    benchmark_parts.append(f"- **Average Partners:** {avg_partners:.1f}")
                    benchmark_parts.append(f"- **Median Partners:** {median_partners:.0f}")
                    if avg_countries:
                        benchmark_parts.append(f"- **Average Countries:** {avg_countries:.1f}")
                    benchmark_parts.append("")

                # Organization type breakdown
                if org_type_breakdown and isinstance(org_type_breakdown, dict):
                    org_types = org_type_breakdown.get("org_types", [])
                    if org_types and isinstance(org_types, list):
                        benchmark_parts.append("### Budget by Organization Type")
                        for ot in org_types[:5]:
                            if isinstance(ot, dict):
                                org_code = ot.get("org_type", "N/A")
                                org_name = {
                                    "HES": "Universities",
                                    "REC": "Research Centers",
                                    "PRC": "Companies",
                                    "PUB": "Public Bodies",
                                    "OTH": "Other",
                                }.get(org_code, org_code)
                                avg_contrib = ot.get("avg_contribution", 0) or 0
                                share = ot.get("share_pct", 0) or 0
                                benchmark_parts.append(
                                    f"- **{org_name}:** €{avg_contrib:,.0f} avg ({share:.0f}% of funding)"
                                )
                        benchmark_parts.append("")

                # Consortium context (coordinator info)
                if consortium_context and isinstance(consortium_context, dict):
                    top_coordinators = consortium_context.get("top_coordinator_countries", [])
                    coordinator_share = consortium_context.get("coordinator_budget_share", 0) or 0
                    if top_coordinators or coordinator_share:
                        benchmark_parts.append("### Coordinator Insights")
                        if coordinator_share:
                            benchmark_parts.append(
                                f"- **Coordinator Budget Share:** {coordinator_share:.0f}% of total"
                            )
                        if top_coordinators and isinstance(top_coordinators, list):
                            top_3 = [
                                c.get("country", "N/A")
                                for c in top_coordinators[:3]
                                if isinstance(c, dict)
                            ]
                            if top_3:
                                benchmark_parts.append(
                                    f"- **Top Coordinator Countries:** {', '.join(top_3)}"
                                )
                        benchmark_parts.append("")

                # Recommendations
                if recommendations and isinstance(recommendations, list):
                    benchmark_parts.append("### Recommendations")
                    for rec in recommendations[:5]:
                        if isinstance(rec, str):
                            benchmark_parts.append(f"- {rec}")
                        elif isinstance(rec, dict):
                            rec_text = rec.get("text", rec.get("message", str(rec)))
                            benchmark_parts.append(f"- {rec_text}")
                    benchmark_parts.append("")

                # Sample projects
                if sample_projects and isinstance(sample_projects, list):
                    benchmark_parts.append("### Sample Funded Projects")
                    for proj in sample_projects[:5]:
                        if isinstance(proj, dict):
                            acronym = proj.get("acronym", "N/A")
                            title_text = proj.get("title", "")
                            title_text = (
                                title_text[:50]
                                if isinstance(title_text, str)
                                else str(title_text)[:50]
                            )
                            budget = proj.get("ec_contribution", proj.get("total_cost", 0)) or 0
                            partners = proj.get("partner_count", 0) or 0
                            benchmark_parts.append(
                                f"- **{acronym}**: {title_text}... (€{budget / 1_000_000:.1f}M, {partners} partners)"
                            )
                    benchmark_parts.append("")

                # Next steps
                benchmark_parts.append("---\n\n🎯 **Next Steps:**")
                benchmark_parts.append("• Use these benchmarks to calibrate your budget planning")
                benchmark_parts.append(
                    "• Check similar projects on [CORDIS](https://cordis.europa.eu/) for detailed breakdowns"
                )
                benchmark_parts.append(
                    "• Review open calls on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
                )

                content_pieces.append("\n".join(benchmark_parts))

            # Extract consortium patterns results (get_consortium_patterns tool)
            elif result.get("tool_name") == "get_consortium_patterns" or (
                "organization_type_distribution" in result and "consortium_size" in result
            ):
                consortium_text = self._format_consortium_patterns_result(result)
                if consortium_text:
                    content_pieces.append(consortium_text)

            # Extract call details - ENHANCED with full description
            elif result.get("call_id") and result.get("title"):
                call_parts = []
                call_parts.append(f"## Call Details: {result.get('call_id')}\n")
                call_parts.append(f"**Title:** {result.get('title')}")
                call_parts.append(f"**Status:** {result.get('status', 'Unknown')}")
                call_parts.append(f"**Type:** {result.get('type', 'N/A')}")
                call_parts.append(f"**Deadline:** {result.get('deadline', 'N/A')}")

                # Full description without truncation
                description = result.get("description", "")
                if description:
                    # Clean HTML tags if present
                    clean_desc = re.sub(r"<[^>]+>", " ", description)
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                    call_parts.append(f"\n**Description:**\n{clean_desc}")

                # Add expected outcomes if available
                expected_outcomes = result.get("expected_outcomes", [])
                if expected_outcomes:
                    call_parts.append("\n**Expected Outcomes:**")
                    for outcome in expected_outcomes[:10]:
                        call_parts.append(f"- {outcome}")

                # Add scope if available
                scope = result.get("scope", "")
                if scope and scope != description:
                    clean_scope = re.sub(r"<[^>]+>", " ", scope)
                    clean_scope = re.sub(r"\s+", " ", clean_scope).strip()
                    call_parts.append(f"\n**Scope:**\n{clean_scope}")

                content_pieces.append("\n".join(call_parts))

            # Extract statistics/benchmark results - improved formatting
            # Extract statistics/benchmark results - improved formatting
            elif result.get("statistics") or result.get("benchmark"):
                stats = result.get("statistics", result.get("benchmark", {}))
                if isinstance(stats, dict):
                    if "success_rates" in stats:
                        # EIC/ERC/MSCA format
                        programme = result.get("programme", "Programme")
                        parts = [f"**{programme} Statistics:**"]
                        if stats.get("description"):
                            parts.append(f"\n{stats['description']}")
                        parts.append("\n**Success Rates:**")
                        for key, value in stats.get("success_rates", {}).items():
                            if key != "note":
                                parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                        if stats.get("funding"):
                            parts.append("\n**Funding:**")
                            for key, value in stats["funding"].items():
                                parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                        # Add Next Steps for actionability
                        parts.append("\n---\n\n🎯 **Next Steps:**")
                        parts.append(
                            "• Review successful proposals in [CORDIS](https://cordis.europa.eu/)"
                        )
                        parts.append(
                            "• Check open calls on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
                        )
                        parts.append("• Consider working with experienced partners or consultants")
                        content_pieces.append("\n".join(parts))
                    else:
                        # Cluster statistics format
                        programme = result.get("programme", result.get("cluster_code", "Unknown"))
                        parts = [f"**{programme} Statistics:**"]
                        if "total_projects" in stats or "project_count" in stats:
                            projects = stats.get(
                                "total_projects", stats.get("project_count", "N/A")
                            )
                            parts.append(
                                f"- Total Projects: {projects:,}"
                                if isinstance(projects, int)
                                else f"- Total Projects: {projects}"
                            )
                        if "success_rate" in stats:
                            parts.append(f"- Success Rate: {stats['success_rate']}%")
                        if "avg_project_budget" in stats or "average_funding" in stats:
                            avg = stats.get("avg_project_budget", stats.get("average_funding", 0))
                            parts.append(f"- Average Budget: €{avg:,.0f}")
                        # Add Next Steps for actionability
                        parts.append("\n---\n\n🎯 **Next Steps:**")
                        parts.append(
                            "• Review open calls in this cluster on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
                        )
                        parts.append(
                            "• Study similar funded projects in [CORDIS](https://cordis.europa.eu/)"
                        )
                        content_pieces.append("\n".join(parts))
                else:
                    # Fallback for non-dict stats
                    content_pieces.append(
                        f"Statistics: {json.dumps(stats, indent=2, default=str)[:1000]}"
                    )

            # Extract timeline generation results - ENHANCED with full details
            elif result.get("tool_name") == "generate_timeline" and result.get("success"):
                wps = result.get("work_packages", [])
                deliverables = result.get("deliverables", [])
                milestones = result.get("milestones", [])
                params = result.get("parameters", {})
                gantt = result.get("gantt_data", {})
                recommendations = result.get("recommendations", [])

                timeline_parts = []
                timeline_parts.append("## Project Timeline Generated\n")
                timeline_parts.append("**Project Parameters:**")
                timeline_parts.append(f"- Duration: {params.get('duration_months', 36)} months")
                timeline_parts.append(f"- Action Type: {params.get('action_type', 'RIA')}")
                timeline_parts.append(f"- Partners: {params.get('num_partners', 8)}")
                timeline_parts.append(
                    f"- Total Effort: {params.get('total_person_months', 0)} person-months"
                )
                timeline_parts.append("")

                # Work Packages with full details
                timeline_parts.append("### Work Packages\n")
                for wp in wps:
                    wp_num = wp.get("number", 0)
                    title = wp.get("title", "")
                    lead = wp.get("lead", "P1")
                    participants = wp.get("participants", [])
                    start = wp.get("start_month", 1)
                    end = wp.get("end_month", 36)
                    effort = wp.get("effort_pms", 0)
                    objective = wp.get("objective", "")
                    tasks = wp.get("tasks", [])

                    timeline_parts.append(f"**WP{wp_num}: {title}**")
                    timeline_parts.append(
                        f"- Lead: {lead} | Participants: {', '.join(participants[:4]) if participants else 'All'}"
                    )
                    timeline_parts.append(
                        f"- Duration: M{start} - M{end} ({end - start + 1} months)"
                    )
                    timeline_parts.append(f"- Effort: {effort} person-months")
                    if objective:
                        timeline_parts.append(f"- Objective: *{objective}*")
                    if tasks:
                        timeline_parts.append(f"- Tasks: {'; '.join(tasks[:4])}")
                    timeline_parts.append("")

                # Deliverables
                if deliverables:
                    timeline_parts.append(f"### Deliverables ({len(deliverables)} total)\n")
                    for d in deliverables[:15]:
                        d_id = d.get("id", d.get("seq_id", "D?"))
                        d_title = d.get("title", "")[:60]
                        d_month = d.get("due_month", 0)
                        d_type = d.get("type", "R")
                        d_level = d.get("dissemination_level", "PU")
                        timeline_parts.append(
                            f"- **{d_id}**: {d_title} (M{d_month}, {d_type}, {d_level})"
                        )
                    if len(deliverables) > 15:
                        timeline_parts.append(
                            f"- ... and {len(deliverables) - 15} more deliverables"
                        )
                    timeline_parts.append("")

                # Milestones
                if milestones:
                    timeline_parts.append(f"### Milestones ({len(milestones)} total)\n")
                    for m in milestones:
                        m_id = m.get("id", "MS?")
                        m_title = m.get("title", "")
                        m_month = m.get("due_month", 0)
                        timeline_parts.append(f"- **{m_id}**: {m_title} (M{m_month})")
                    timeline_parts.append("")

                # ASCII Gantt Chart
                ascii_chart = gantt.get("ascii_chart", "")
                if ascii_chart:
                    timeline_parts.append("### Gantt Chart\n")
                    timeline_parts.append("```")
                    timeline_parts.append(ascii_chart)
                    timeline_parts.append("```")
                    timeline_parts.append("")

                # WP Dependencies
                dependencies = gantt.get("dependencies", [])
                if dependencies:
                    timeline_parts.append("### WP Dependencies\n")
                    for dep in dependencies[:6]:
                        timeline_parts.append(
                            f"- {dep.get('from')} → {dep.get('to')}: {dep.get('description', '')}"
                        )
                    timeline_parts.append("")

                # Recommendations
                if recommendations:
                    timeline_parts.append("### Recommendations\n")
                    for rec in recommendations[:5]:
                        timeline_parts.append(f"- {rec}")

                # Add Next Steps section for actionability
                timeline_parts.append("")
                timeline_parts.append("---")
                timeline_parts.append("")
                timeline_parts.append("🎯 **Next Steps:**")
                timeline_parts.append(
                    "• Review work package allocation with your consortium partners"
                )
                timeline_parts.append("• Adjust deliverable timing based on dependencies")
                timeline_parts.append(
                    "• Check [Horizon Europe proposal templates](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents) for formatting requirements"
                )
                timeline_parts.append(
                    "• Use the EU Portal's [Grant Agreement Preparation](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/om_en.pdf) guide for milestone definitions"
                )

                content_pieces.append("\n".join(timeline_parts))

            # Extract similar projects results - ENHANCED with full details
            elif "similar_projects" in result and isinstance(result.get("similar_projects"), list):
                projects = result["similar_projects"]
                query_desc = result.get("query_description", "")
                matches = result.get("matches_found", len(projects))
                filters = result.get("filters_applied", {})

                if not projects:
                    content_pieces.append(
                        f"## Similar Projects Search\n\nNo projects found matching: *{query_desc}*"
                    )
                else:
                    similar_parts = []
                    similar_parts.append("## Similar Funded Projects\n")
                    similar_parts.append(f"**Query:** {query_desc}")
                    if filters:
                        filter_str = ", ".join([f"{k}: {v}" for k, v in filters.items() if v])
                        if filter_str:
                            similar_parts.append(f"**Filters:** {filter_str}")
                    similar_parts.append(f"**Found:** {matches} similar projects\n")

                    for i, p in enumerate(projects[:10], 1):
                        acronym = p.get("acronym", "N/A")
                        title = p.get("title", "N/A")
                        score = p.get("similarity_score", 0)
                        budget = p.get("eu_contribution", p.get("total_cost", 0))
                        consortium = p.get("consortium", {})
                        size = consortium.get("size", p.get("partner_count", 0))
                        action_type = p.get("action_type", "N/A")
                        objective = p.get("objective", "")
                        start_date = p.get("start_date", "")
                        end_date = p.get("end_date", "")
                        coordinator = consortium.get("coordinator", {}).get("name", "")
                        cluster = p.get("cluster", "")

                        budget_str = f"€{budget / 1_000_000:.1f}M" if budget > 0 else "N/A"

                        similar_parts.append(f"### {i}. {acronym} [{score:.0%} match]")
                        similar_parts.append(f"**{title}**")
                        similar_parts.append(
                            f"- Type: {action_type} | Budget: {budget_str} | Partners: {size}"
                        )
                        if cluster:
                            similar_parts.append(f"- Cluster: {cluster}")
                        if start_date and end_date:
                            similar_parts.append(f"- Duration: {start_date[:7]} to {end_date[:7]}")
                        if coordinator:
                            similar_parts.append(f"- Coordinator: {coordinator}")
                        if objective:
                            obj_preview = (
                                objective[:300] + "..." if len(objective) > 300 else objective
                            )
                            similar_parts.append(f"- Objective: *{obj_preview}*")
                        similar_parts.append("")

                    # Add insights
                    insights = result.get("insights", [])
                    if insights:
                        similar_parts.append("**Key Insights:**")
                        for insight in insights[:5]:
                            similar_parts.append(f"- {insight}")

                    content_pieces.append("\n".join(similar_parts))

            # Extract project details results (get_project_details)
            # Has "acronym" + "partners" but NOT "project_acronym" or "organization"
            # Skip if this project is already in a search_projects result (will be merged there)
            elif (
                "acronym" in result
                and "partners" in result
                and isinstance(result.get("partners"), list)
                and "organization" not in result
                and "project_acronym" not in result
            ):
                pid_check = result.get("project_id")
                if pid_check and str(pid_check) in search_project_ids:
                    continue  # Will be merged into the search_projects listing
                acronym = result.get("acronym", "Unknown")
                title = result.get("title", "")
                pid = result.get("project_id", "")
                status = result.get("status", "")
                objective = result.get("objective", "")
                partners = result.get("partners", [])
                ec_contribution = result.get(
                    "ec_max_contribution", result.get("eu_contribution", 0)
                )
                total_cost = result.get("total_cost", 0)
                start_date = result.get("start_date", "")
                end_date = result.get("end_date", "")
                coordinator_raw = result.get("coordinator", "")
                coordinator = (
                    coordinator_raw.get("name", str(coordinator_raw))
                    if isinstance(coordinator_raw, dict)
                    else str(coordinator_raw)
                )
                programme = result.get("programme", "")
                call_id = result.get("call_id", result.get("call", ""))

                parts = [f"### {acronym}: {title}"]
                if pid:
                    parts.append(f"- **Project ID:** {pid}")
                if status:
                    parts.append(f"- **Status:** {status}")
                if coordinator:
                    parts.append(f"- **Coordinator:** {coordinator}")
                if ec_contribution:
                    parts.append(f"- **EC Contribution:** €{ec_contribution / 1_000_000:.1f}M")
                if total_cost:
                    parts.append(f"- **Total Cost:** €{total_cost / 1_000_000:.1f}M")
                if start_date:
                    parts.append(
                        f"- **Duration:** {str(start_date)[:10]} to {str(end_date)[:10] if end_date else 'ongoing'}"
                    )
                if programme:
                    parts.append(f"- **Programme:** {programme}")
                if call_id:
                    parts.append(f"- **Call:** {call_id}")
                if objective:
                    obj_preview = objective[:400] + "..." if len(objective) > 400 else objective
                    parts.append(f"\n**Objective:** {obj_preview}")
                if partners:
                    parts.append(f"\n**Partners ({len(partners)}):**")
                    parts.append("| Name | Country | Role |")
                    parts.append("|------|---------|------|")
                    for p in partners:
                        pname = p.get("name", "Unknown")
                        pcountry = p.get("country", "")
                        prole = p.get("role", "participant")
                        parts.append(f"| {pname} | {pcountry} | {prole} |")
                cordis_url = f"https://cordis.europa.eu/project/id/{pid}" if pid else ""
                if cordis_url:
                    parts.append(f"\n[View on CORDIS]({cordis_url})")

                content_pieces.append("\n".join(parts))

            # Extract collaboration network results (get_collaboration_network)
            # Requires "organization" key (specific to collaboration network results)
            # Skip if result has "project_acronym" (that's get_project_partners)
            # Also skip if result has "error" (failed get_project_partners returns partners: [])
            elif (
                "partners" in result
                and isinstance(result.get("partners"), list)
                and "organization" in result
                and "project_acronym" not in result
                and "error" not in result
            ):
                org_name = result.get("organization", "Unknown Organization")
                org_country = result.get("country", "")
                partners = result.get("partners", [])
                total_partners = result.get("total_partners", len(partners))

                if not partners:
                    network_text = f"""## Collaboration Network: {org_name}

No collaboration partners found for this organization in the database.

**Suggestions:**
- Check the organization name spelling
- Try searching with a shorter name (e.g., "Fraunhofer" instead of full name)
- The organization may not have participated in Horizon Europe projects"""
                else:
                    network_text = f"""## Collaboration Network: {org_name}
**Location:** {org_country}
**Total Collaborating Organizations:** {total_partners}

### Top Collaborating Partners

| Partner | Country | Type | Joint Projects |
|---------|---------|------|----------------|
"""
                    for p in partners[:15]:
                        p_name = p.get("name", "Unknown")[:50]
                        p_country = p.get("country", "N/A")
                        p_type = p.get("type", "N/A")
                        p_type_desc = {
                            "HES": "University",
                            "REC": "Research",
                            "PRC": "Company",
                            "PUB": "Public",
                            "OTH": "Other",
                        }.get(p_type, p_type or "N/A")
                        collabs = p.get("collaborations", 0)
                        network_text += f"| {p_name} | {p_country} | {p_type_desc} | {collabs} |\n"

                    if total_partners > 15:
                        network_text += f"\n*...and {total_partners - 15} more partners*\n"

                    # Add insights
                    countries = set(p.get("country") for p in partners if p.get("country"))
                    types = [p.get("type") for p in partners if p.get("type")]
                    type_counts = {}
                    for t in types:
                        type_counts[t] = type_counts.get(t, 0) + 1
                    top_type = max(type_counts, key=type_counts.get) if type_counts else "N/A"
                    top_type_desc = {
                        "HES": "Universities",
                        "REC": "Research Centers",
                        "PRC": "Companies",
                        "PUB": "Public Bodies",
                        "OTH": "Other Organizations",
                    }.get(top_type, top_type)

                    network_text += f"""
### Network Insights
- **Geographic Reach:** {len(countries)} countries
- **Most Common Partner Type:** {top_type_desc}
- **Strongest Collaboration:** {partners[0].get("name", "N/A")} ({partners[0].get("collaborations", 0)} joint projects)

**Next Steps:**
- Explore specific partners' project histories
- Search CORDIS for joint project details
- Contact organizations through EU Partner Search
"""
                content_pieces.append(network_text)

            # Extract organization projects results (find_organization_projects)
            # Skip verbose listing when org stats are already present (user wants counts)
            elif (
                "organization" in result
                and "projects" in result
                and "count" in result
                and not has_org_stats
            ):
                org_name = result.get("organization", "Unknown")
                projects = result.get("projects", [])
                # Use total_project_count (true total) over count (display-limited)
                total_count = result.get("total_project_count") or result.get(
                    "count", len(projects)
                )
                coord_count = result.get("coordinator_count")
                count = total_count
                role_filter = result.get("role_filter")
                display_note = result.get("note")  # e.g. "Showing 50 of 219 total projects"

                if not projects:
                    org_text = f"""## Projects for {org_name}

No projects found for this organization in the database.

**Suggestions:**
- Check the organization name spelling
- Try searching with a shorter name
- The organization may not have participated in Horizon Europe yet"""
                else:
                    role_desc = f" (as {role_filter})" if role_filter else ""
                    note_line = f"\n*{display_note}*\n" if display_note else ""
                    org_text = f"""## Projects by {org_name}{role_desc}
**Total Projects Found:** {count}{note_line}

"""
                    coordinated = [p for p in projects if p.get("role") == "coordinator"]
                    participated = [p for p in projects if p.get("role") != "coordinator"]

                    if coordinated:
                        org_text += f"### Coordinated Projects ({len(coordinated)})\n\n"
                        for p in coordinated[:10]:
                            acronym = p.get("acronym", "N/A")
                            title = p.get("title", "N/A")[:60]
                            budget = p.get("budget", 0)
                            status = p.get("status", "N/A")
                            scheme = p.get("funding_scheme", "N/A")
                            start = p.get("start_date", "")[:10] if p.get("start_date") else "N/A"
                            url = p.get("cordis_url", "")

                            budget_str = f"€{budget / 1_000_000:.1f}M" if budget else "N/A"
                            org_text += f"- **{acronym}**: {title}\n"
                            org_text += (
                                f"  - Budget: {budget_str} | Type: {scheme} | Status: {status}\n"
                            )
                            if url:
                                org_text += f"  - [View on CORDIS]({url})\n"
                            org_text += "\n"

                    if participated:
                        org_text += f"### As Participant ({len(participated)})\n\n"
                        for p in participated[:10]:
                            acronym = p.get("acronym", "N/A")
                            title = p.get("title", "N/A")[:60]
                            budget = p.get("budget", 0)
                            scheme = p.get("funding_scheme", "N/A")
                            url = p.get("cordis_url", "")

                            budget_str = f"€{budget / 1_000_000:.1f}M" if budget else "N/A"
                            org_text += f"- **{acronym}**: {title} ({scheme}, {budget_str})\n"

                    # Add insights
                    total_budget = sum(p.get("budget", 0) or 0 for p in projects)
                    funding_schemes = set(
                        p.get("funding_scheme") for p in projects if p.get("funding_scheme")
                    )

                    # Use true coordinator count from aggregate query if available
                    coordinator_display = (
                        coord_count if coord_count is not None else len(coordinated)
                    )
                    org_text += f"""
### Summary
- **Total Projects:** {count}
- **As Coordinator:** {coordinator_display}
- **Total Budget Involved:** €{total_budget / 1_000_000:.1f}M
- **Funding Types:** {", ".join(funding_schemes) if funding_schemes else "N/A"}

**Next Steps:**
- Explore specific project details on CORDIS
- Search for collaboration partners
- Analyze the organization's research focus areas
"""
                content_pieces.append(org_text)

            # Extract project results (generic fallback for other project queries)
            # Note: if both similar_projects AND projects existed, they were already
            # merged and rendered above — this handler is skipped via merged_tool_keys
            elif "projects" in result and isinstance(result["projects"], list):
                projects = result["projects"]
                total_found = result.get("total_found", len(projects))
                project_parts = [f"## Project Search Results\n**Found {total_found} projects:**\n"]
                rendered_pids = set()
                project_count = 0
                for _i, proj in enumerate(projects[:10], 1):
                    acronym = proj.get("acronym", "")
                    title = proj.get("title", "")
                    pid = proj.get("id") or proj.get("project_id", "")

                    if not (acronym or title):
                        continue

                    if str(pid) in rendered_pids:
                        continue
                    rendered_pids.add(str(pid))
                    project_count += 1

                    # Merge with detailed data from get_project_details if available
                    detail = detailed_project_data.get(str(pid), {})

                    ec = (
                        detail.get("ec_max_contribution")
                        or detail.get("eu_contribution")
                        or proj.get("ec_contribution")
                        or proj.get("ecMaxContribution")
                        or 0
                    )
                    total_cost = detail.get("total_cost") or proj.get("total_cost") or 0
                    coordinator_raw = (
                        detail.get("coordinator")
                        or proj.get("coordinator_name")
                        or proj.get("coordinator", "")
                    )
                    coordinator = (
                        coordinator_raw.get("name", str(coordinator_raw))
                        if isinstance(coordinator_raw, dict)
                        else str(coordinator_raw)
                    )
                    coord_country = ""
                    if isinstance(coordinator_raw, dict):
                        coord_country = coordinator_raw.get("country", "")
                    # Use longer objective from detailed data if available
                    detail_obj = detail.get("objective", "")
                    search_obj = proj.get("objective") or proj.get("description") or ""
                    objective = detail_obj if len(detail_obj) > len(search_obj) else search_obj
                    obj_preview = objective[:400] + "..." if len(objective) > 400 else objective

                    status = detail.get("status") or proj.get("status", "")
                    start_date = detail.get("start_date") or proj.get("start_date", "")
                    end_date = detail.get("end_date") or proj.get("end_date", "")
                    funding_scheme = detail.get("funding_scheme") or proj.get("funding_scheme", "")
                    topics = detail.get("topics") or proj.get("topics", "")
                    # Prefer partners from detailed data (complete list)
                    partners = detail.get("partners") or proj.get("partners", [])
                    # Consortium info from search_projects
                    consortium = proj.get("consortium", {})
                    partner_count = consortium.get("participant_count", 0) or len(partners)
                    country_count = consortium.get("country_count", 0)
                    countries = consortium.get("countries", [])
                    # URLs
                    cordis_url = (
                        proj.get("cordis_url")
                        or detail.get("cordis_url")
                        or (f"https://cordis.europa.eu/project/id/{pid}" if pid else "")
                    )

                    ec_str = f"€{float(ec) / 1_000_000:.1f}M" if ec else ""
                    total_str = f"€{float(total_cost) / 1_000_000:.1f}M" if total_cost else ""
                    coord_str = f"{coordinator} ({coord_country})" if coord_country else coordinator
                    parts = [f"### {project_count}. {acronym}: {title}"]
                    if pid:
                        parts.append(f"- **Project ID:** {pid}")
                    if status:
                        parts.append(f"- **Status:** {status}")
                    if funding_scheme:
                        parts.append(f"- **Action Type:** {funding_scheme}")
                    if ec_str:
                        parts.append(f"- **EC Contribution:** {ec_str}")
                    if total_str and total_str != ec_str:
                        parts.append(f"- **Total Cost:** {total_str}")
                    if coordinator:
                        parts.append(f"- **Coordinator:** {coord_str}")
                    if start_date:
                        parts.append(
                            f"- **Duration:** {str(start_date)[:10]} to {str(end_date)[:10] if end_date else 'ongoing'}"
                        )
                    if partner_count:
                        consortium_str = f"- **Consortium:** {partner_count} partners"
                        if country_count:
                            consortium_str += f" from {country_count} countries"
                        if countries:
                            consortium_str += f" ({', '.join(countries[:8])})"
                        parts.append(consortium_str)
                    if topics:
                        parts.append(f"- **Topic:** {topics}")
                    if obj_preview:
                        parts.append(f"- **Objective:** {obj_preview}")

                    # Include partners if available (from get_project_details merge)
                    if partners:
                        parts.append(f"\n**Partners ({len(partners)}):**")
                        parts.append("| Name | Country | Role |")
                        parts.append("|------|---------|------|")
                        for p in partners:
                            pname = p.get("name", "Unknown")
                            pcountry = p.get("country", "")
                            prole = p.get("role", "participant")
                            parts.append(f"| {pname} | {pcountry} | {prole} |")

                    # Add CORDIS link
                    if cordis_url:
                        parts.append(f"\n[View on CORDIS]({cordis_url})")

                    project_parts.append("\n".join(parts))

                if project_count > 0:
                    content_pieces.append("\n\n".join(project_parts))

            # Extract project partner results (get_project_partners)
            elif "partners" in result and "project_acronym" in result:
                acronym = result.get("project_acronym", "Unknown")
                title = result.get("project_title", "")
                pid = result.get("project_id", "")
                coordinator = result.get("coordinator", "")
                partners = result.get("partners", [])

                parts = [f"### {acronym}: {title}"]
                if pid:
                    parts.append(f"- **Project ID:** {pid}")
                if coordinator:
                    parts.append(f"- **Coordinator:** {coordinator}")
                parts.append(f"\n**Partners ({len(partners)}):**")
                parts.append("| Name | Country | Role |")
                parts.append("|------|---------|------|")
                for p in partners:
                    pname = p.get("name", "Unknown")
                    pcountry = p.get("country", "")
                    prole = p.get("role", "participant")
                    parts.append(f"| {pname} | {pcountry} | {prole} |")

                content_pieces.append("\n".join(parts))

            # Extract organization statistics results (get_organization_stats)
            elif "project_count" in result and "coordinator_count" in result and "name" in result:
                org_name = result.get("name", "Unknown Organization")
                short_name = result.get("short_name", "")
                country = result.get("country", "")
                proj_count = result.get("project_count", 0)
                coord_count = result.get("coordinator_count", 0)
                participant_count = proj_count - coord_count
                total_funding = result.get("total_funding", 0)
                entity_type = result.get("entity_type_name") or result.get("entity_type", "")
                active_clusters = result.get("active_clusters", [])

                # Build header
                name_display = f"{org_name} ({short_name})" if short_name else org_name
                org_parts = [f"## Organization Statistics: {name_display}\n"]

                # Key metrics table
                org_parts.append("| Metric | Value |")
                org_parts.append("|---|---|")
                org_parts.append(f"| **Total Projects** | {proj_count:,} |")
                org_parts.append(
                    f"| **As Coordinator** | {coord_count:,} ({coord_count/max(proj_count,1)*100:.0f}%) |"
                )
                org_parts.append(
                    f"| **As Participant** | {participant_count:,} ({participant_count/max(proj_count,1)*100:.0f}%) |"
                )
                org_parts.append(f"| **Total EC Funding** | €{total_funding/1_000_000:,.1f}M |")
                org_parts.append(f"| **Country** | {country} |")
                if entity_type:
                    org_parts.append(f"| **Organization Type** | {entity_type} |")
                org_parts.append("")

                # Active clusters with readable names
                if active_clusters:
                    cluster_names = {
                        "CLUSTER-1": "Health",
                        "CLUSTER-2": "Culture, Creativity & Inclusive Society",
                        "CLUSTER-3": "Civil Security for Society",
                        "CLUSTER-4": "Digital, Industry & Space",
                        "CLUSTER-5": "Climate, Energy & Mobility",
                        "CLUSTER-6": "Food, Bioeconomy & Natural Resources",
                    }
                    org_parts.append("**Active Research Areas:**")
                    for c in active_clusters[:6]:
                        label = cluster_names.get(c, c)
                        org_parts.append(f"- {c}: {label}")

                content_pieces.append("\n".join(org_parts))

            # Extract country statistics results
            elif "country_code" in result and "eligibility" in result:
                country = result.get("country", result.get("country_code", "Unknown"))
                eligibility = result.get("eligibility", {})
                top_orgs = result.get("top_organizations", [])

                # Get participation history from eligibility
                participation = eligibility.get("participation_history", {})
                org_count = participation.get(
                    "organization_count", result.get("organization_count", 0)
                )
                proj_count = participation.get("project_count", 0)
                total_funding = participation.get("total_funding_received", 0)

                # Build clear eligibility answer first
                is_eligible = eligibility.get("is_eligible", False)
                eligibility_status = eligibility.get("eligibility_status", "Unknown")

                country_text = f"""Country: {country}
**Can participate in Horizon Europe: {"YES" if is_eligible else "NO"}**
- Status: {eligibility_status}"""

                # Add notes if available
                notes = eligibility.get("notes", [])
                if notes:
                    country_text += f"\n- {notes[0]}"

                # Add participation stats
                if proj_count > 0:
                    country_text += f"""

Participation Statistics:
- Organizations Participating: {org_count:,}
- Projects Involved: {proj_count:,}
- Total Funding Received: €{total_funding:,.0f}"""

                if top_orgs:
                    country_text += f"\n\nTop Organizations ({len(top_orgs)} shown):"
                    for org in top_orgs[:10]:
                        org_name = org.get("name", org.get("organization_name", "Unknown"))
                        org_projects = org.get("project_count", org.get("projects", 0))
                        org_funding = org.get("total_funding", org.get("funding", 0))
                        country_text += (
                            f"\n- {org_name}: {org_projects} projects, €{org_funding:,.0f}"
                        )

                content_pieces.append(country_text)

            # Handle get_programme_info results (actionable programme information)
            elif "programme" in result and "actionable_guidance" in result:
                prog_name = result.get("info", {}).get("name", result.get("programme", ""))
                info = result.get("info", {})

                prog_text = f"## {prog_name}\n\n"

                # Add budget and focus
                if info.get("budget"):
                    prog_text += f"**Budget**: {info['budget']}\n"
                if info.get("focus"):
                    prog_text += f"**Focus**: {info['focus']}\n\n"

                # Add actionable guidance
                guidance = result.get("actionable_guidance", "")
                if guidance:
                    prog_text += f"{guidance}\n\n"

                # Add official resources
                resources = result.get("official_resources", {})
                if resources:
                    prog_text += "**Official Resources:**\n"
                    for resource_name, url in resources.items():
                        # Format resource name nicely
                        nice_name = resource_name.replace("_", " ").title()
                        prog_text += f"- [{nice_name}]({url})\n"

                # Add official website
                if result.get("official_website"):
                    prog_text += f"\n**Official Website**: {result['official_website']}\n"

                content_pieces.append(prog_text)

            # Handle compare_programmes results (cluster/programme comparison)
            elif "comparison" in result and isinstance(result.get("comparison"), dict):
                comparison = result["comparison"]

                # Build comparison table
                comparison_text = "## Programme/Cluster Comparison\n\n"
                comparison_text += "| Metric | "

                # Get programme names and build header
                prog_names = list(comparison.keys())
                comparison_text += " | ".join(prog_names) + " |\n"
                comparison_text += "|" + "|".join(["---"] * (len(prog_names) + 1)) + "|\n"

                # Gather metrics from all programmes
                all_metrics = set()
                for _prog_name, prog_data in comparison.items():
                    stats = prog_data.get("statistics") or {}
                    all_metrics.update(stats.keys())

                # Display comparison rows
                metric_names = {
                    "total_projects": "Total Projects",
                    "total_funding": "Total Funding",
                    "total_budget": "Total Funding",
                    "avg_project_budget": "Avg Project Budget",
                    "average_funding": "Avg Project Budget",
                    "success_rate": "Success Rate",
                    "median_budget": "Median Budget",
                    "top_coordinators": "Top Coordinators",
                    "countries_participating": "Countries",
                }

                for metric in [
                    "total_projects",
                    "total_funding",
                    "total_budget",
                    "avg_project_budget",
                    "average_funding",
                    "success_rate",
                ]:
                    if metric in all_metrics or metric.replace("_", "") in [
                        m.replace("_", "") for m in all_metrics
                    ]:
                        row = f"| {metric_names.get(metric, metric.replace('_', ' ').title())} |"
                        for prog_name in prog_names:
                            stats = comparison.get(prog_name, {}).get("statistics") or {}
                            value = stats.get(metric)
                            if value is None:
                                # Try alternative key names
                                if metric == "total_funding":
                                    value = stats.get("total_budget")
                                elif metric == "avg_project_budget":
                                    value = stats.get("average_funding")

                            if value is not None:
                                if "budget" in metric or "funding" in metric:
                                    if isinstance(value, int | float):
                                        if value >= 1_000_000_000:
                                            row += f" €{value / 1_000_000_000:.1f}B |"
                                        elif value >= 1_000_000:
                                            row += f" €{value / 1_000_000:.1f}M |"
                                        else:
                                            row += f" €{value:,.0f} |"
                                    else:
                                        row += f" {value} |"
                                elif "rate" in metric:
                                    row += f" {value}% |"
                                elif "projects" in metric:
                                    row += (
                                        f" {value:,} |" if isinstance(value, int) else f" {value} |"
                                    )
                                else:
                                    row += f" {value} |"
                            else:
                                row += " N/A |"
                        comparison_text += row + "\n"

                # Add cluster codes if available
                cluster_codes = []
                for prog_name, prog_data in comparison.items():
                    code = prog_data.get("cluster_code")
                    if code:
                        cluster_codes.append(f"{prog_name}: {code}")
                if cluster_codes:
                    comparison_text += f"\n*Cluster Codes: {', '.join(cluster_codes)}*\n"

                comparison_text += """
**Next Steps:**
- Use `get_programme_statistics` for detailed statistics on a specific cluster
- Search for funding calls in your preferred cluster
- Analyze historical trends with `analyze_call_history`
"""
                content_pieces.append(comparison_text)

            # Extract programme/cluster statistics results
            elif "cluster_code" in result or ("programme" in result and "statistics" in result):
                programme = result.get("programme", result.get("cluster_code", "Unknown"))
                programme_type = result.get("programme_type", "")
                stats = result.get("statistics", {})
                budget = result.get("budget_details", {})

                programme_text = f"""Programme Statistics for {programme}:"""
                if programme_type:
                    programme_text += f"\n({programme_type})"

                # Handle EIC/ERC/MSCA format with success_rates dict
                if "success_rates" in stats:
                    success_rates = stats["success_rates"]
                    programme_text += f"\n\n{stats.get('description', '')}\n"
                    programme_text += "\nSuccess Rates:"
                    for key, value in success_rates.items():
                        if key != "note":
                            programme_text += f"\n- {key.replace('_', ' ').title()}: {value}"
                    if success_rates.get("note"):
                        programme_text += f"\n\nNote: {success_rates['note']}"

                    # Add funding info
                    if "funding" in stats:
                        programme_text += "\n\nFunding Available:"
                        for key, value in stats["funding"].items():
                            programme_text += f"\n- {key.replace('_', ' ').title()}: {value}"

                    # Add eligibility
                    if stats.get("eligibility"):
                        programme_text += f"\n\nEligibility: {stats['eligibility']}"

                    if stats.get("trl_range"):
                        programme_text += f"\nTRL Range: {stats['trl_range']}"

                    # Add evaluation criteria
                    if stats.get("evaluation_criteria"):
                        programme_text += "\n\nEvaluation Criteria:"
                        for criterion in stats["evaluation_criteria"]:
                            programme_text += f"\n- {criterion}"
                else:
                    # Standard cluster statistics format
                    if stats:
                        total_projects = stats.get(
                            "total_projects", stats.get("project_count", "N/A")
                        )
                        total_funding = stats.get("total_funding", stats.get("total_budget", 0))
                        avg_budget = stats.get(
                            "avg_project_budget", stats.get("average_funding", 0)
                        )

                        programme_text += (
                            f"""
- Total Projects: {total_projects:,}"""
                            if isinstance(total_projects, int)
                            else f"""
- Total Projects: {total_projects}"""
                        )
                        programme_text += f"""
- Total Funding: €{total_funding:,.0f}
- Success Rate: {stats.get("success_rate", "N/A")}%
- Average Project Budget: €{avg_budget:,.0f}"""

                    if budget:
                        programme_text += f"""

Budget Breakdown:
- Min Budget: €{budget.get("min_budget", 0):,.0f}
- Max Budget: €{budget.get("max_budget", 0):,.0f}
- Median Budget: €{budget.get("median_budget", 0):,.0f}"""

                content_pieces.append(programme_text)

            # Extract call history analysis results
            elif result.get("tool_name") == "analyze_call_history" or (
                "timeline" in result and "trends" in result
            ):
                query_params = result.get("query_params", {})
                keywords = query_params.get("keywords", "specified criteria")
                cluster = query_params.get("cluster", "")

                calls_analyzed = result.get("calls_analyzed", 0)
                projects_funded = result.get("projects_funded", 0)
                total_funding = result.get("total_funding_allocated", 0)
                timeline = result.get("timeline", {})
                trends = result.get("trends", {})
                top_topics = result.get("top_funded_topics", [])
                sample_projects = result.get("sample_funded_projects", [])
                recommendations = result.get("recommendations", [])

                # Build header
                search_desc = (
                    keywords
                    if keywords
                    else (f"Cluster {cluster}" if cluster else "Horizon Europe")
                )

                # Skip rendering if no meaningful data (0 projects funded, ≤1 call)
                if projects_funded == 0 and calls_analyzed <= 1:
                    continue

                history_text = f"""## Funding History Analysis: {search_desc}

**Overview:**
- Calls Analyzed: {calls_analyzed}
- Projects Funded: {projects_funded:,}
- Total Funding: €{total_funding / 1_000_000_000:.2f} billion
"""

                # Add trend info
                funding_trend = trends.get("funding_trend", "unknown")
                yoy_growth = trends.get("year_over_year_funding_growth", 0)
                if funding_trend and funding_trend != "insufficient_data":
                    history_text += f"- Funding Trend: {funding_trend.replace('_', ' ').title()} ({yoy_growth:+.1f}% YoY)\n"

                # Add timeline
                if timeline:
                    history_text += "\n**Funding by Year:**\n"
                    sorted_years = sorted(timeline.keys(), reverse=True)
                    for year in sorted_years[:5]:
                        data = timeline[year]
                        year_projects = data.get("projects_funded", 0)
                        year_funding = data.get("total_funding", 0)
                        avg_budget = data.get("avg_project_budget", 0)
                        history_text += f"- **{year}**: {year_projects:,} projects, €{year_funding / 1_000_000:.0f}M total (avg €{avg_budget / 1_000_000:.1f}M/project)\n"

                # Add top topics
                if top_topics:
                    history_text += "\n**Top Funded Topics:**\n"
                    for topic in top_topics[:5]:
                        topic_name = topic.get("topic", topic.get("name", "N/A"))
                        topic_projects = topic.get("projects", topic.get("count", 0))
                        topic_funding = topic.get("total_funding", 0)
                        if topic_funding > 0:
                            history_text += f"- {topic_name}: {topic_projects} projects, €{topic_funding / 1_000_000:.0f}M\n"
                        else:
                            history_text += f"- {topic_name}: {topic_projects} projects\n"

                # Add sample projects
                if sample_projects:
                    history_text += "\n**Sample Funded Projects:**\n"
                    for proj in sample_projects[:5]:
                        acronym = proj.get("acronym", "N/A")
                        title = proj.get("title", "")[:60]
                        budget = proj.get("budget", proj.get("ec_contribution", 0))
                        history_text += (
                            f"- **{acronym}**: {title}... (€{budget / 1_000_000:.1f}M)\n"
                        )

                # Add recommendations
                if recommendations:
                    history_text += "\n**Recommendations:**\n"
                    for rec in recommendations[:3]:
                        history_text += f"- {rec}\n"

                content_pieces.append(history_text)

            # Extract geographic diversification results
            elif (
                result.get("tool_name") == "analyze_geographic_diversification"
                or "group_representation" in result
            ):
                query_params = result.get("query_params", {})
                cluster = query_params.get("cluster", "All Horizon Europe")
                total_projects = result.get("total_projects_analyzed", 0)
                country_groups = result.get("country_groups", {})
                group_stats = result.get("group_representation", [])
                coverage_stats = result.get("coverage_statistics", {})
                at_least_stats = result.get("at_least_coverage", {})
                insights = result.get("insights", {})
                recommendations = result.get("recommendations", {})
                exclude_widening = query_params.get("exclude_widening", True)

                # Build comprehensive output
                geo_text = f"""## Geographic Diversification Analysis: {cluster}

**Analysis Parameters:**
- Projects Analyzed: {total_projects:,}
- Widening Calls: {"Excluded" if exclude_widening else "Included"}
- Country Groups Defined: {len(country_groups)}

**Country Group Definitions:**
"""
                for group_name, countries in country_groups.items():
                    geo_text += f"- **{group_name}**: {', '.join(countries)}\n"

                geo_text += (
                    "\n**Group Representation (% of projects with at least one partner):**\n"
                )
                geo_text += "| Country Group | Projects | Share (%) |\n"
                geo_text += "|---------------|----------|----------|\n"
                for stat in group_stats:
                    group_name = stat.get("group", "Unknown")
                    projects = stat.get("projects_with_partner", 0)
                    share = stat.get("share_percentage", 0)
                    geo_text += f"| {group_name} | {projects:,} | {share}% |\n"

                geo_text += "\n**Coverage Distribution (number of groups per project):**\n"
                geo_text += "| Coverage | Projects | Share (%) |\n"
                geo_text += "|----------|----------|----------|\n"
                for coverage_key, coverage_data in coverage_stats.items():
                    if isinstance(coverage_data, dict):
                        count = coverage_data.get("count", 0)
                        share = coverage_data.get("share_percentage", 0)
                        label = coverage_key.replace("_", " ").title()
                        geo_text += f"| {label} | {count:,} | {share}% |\n"

                geo_text += "\n**Cumulative Coverage (projects with at least N groups):**\n"
                for coverage_key, coverage_data in at_least_stats.items():
                    if isinstance(coverage_data, dict):
                        share = coverage_data.get("share_percentage", 0)
                        label = coverage_key.replace("_", " ").replace("at least", "At least")
                        geo_text += f"- {label}: {share}%\n"

                geo_text += "\n**Key Insights:**\n"
                typical = insights.get("typical_coverage", "N/A")
                avg_presence = insights.get("avg_group_presence", 0)
                well_rep = insights.get("well_represented_groups", [])
                under_rep = insights.get("underrepresented_groups", [])

                geo_text += f"- Typical consortium covers: {typical}\n"
                geo_text += f"- Average group presence: {avg_presence}%\n"
                if well_rep:
                    geo_text += f"- Well-represented groups: {', '.join(well_rep)}\n"
                if under_rep:
                    geo_text += f"- Underrepresented groups: {', '.join(under_rep)}\n"

                geo_text += "\n**Recommendations:**\n"
                if recommendations.get("consortium_building"):
                    geo_text += f"- {recommendations['consortium_building']}\n"
                if recommendations.get("evaluation_note"):
                    geo_text += f"- {recommendations['evaluation_note']}\n"

                geo_text += """
**Resources:**
- **CORDIS Database**: https://cordis.europa.eu
- **EU Partner Search**: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search
"""
                content_pieces.append(geo_text)

            # Extract Erasmus+ eligibility results
            elif result.get("metadata", {}).get("tool") == "check_erasmus_eligibility":
                eligibility_text = self._format_erasmus_eligibility_result(result)
                if eligibility_text:
                    content_pieces.append(eligibility_text)

            # Extract Creative Europe eligibility results
            elif result.get("metadata", {}).get("tool") == "check_creative_europe_eligibility":
                eligibility_text = self._format_creative_europe_eligibility_result(result)
                if eligibility_text:
                    content_pieces.append(eligibility_text)

            # Extract EU4Health eligibility results
            elif result.get("metadata", {}).get("tool") == "check_eu4health_eligibility":
                eligibility_text = self._format_eu4health_eligibility_result(result)
                if eligibility_text:
                    content_pieces.append(eligibility_text)

            # Extract Digital Europe eligibility results
            elif result.get("metadata", {}).get("tool") == "check_digital_europe_eligibility":
                eligibility_text = self._format_digital_europe_eligibility_result(result)
                if eligibility_text:
                    content_pieces.append(eligibility_text)

            # Extract LIFE Programme eligibility results
            elif result.get("metadata", {}).get("tool") == "check_life_eligibility":
                eligibility_text = self._format_life_eligibility_result(result)
                if eligibility_text:
                    content_pieces.append(eligibility_text)

            # Extract EU4Health template search results
            elif result.get("metadata", {}).get("tool") == "search_eu4health_templates":
                template_text = self._format_eu4health_template_search_result(result)
                if template_text:
                    content_pieces.append(template_text)

            # Extract programme recommendations results
            elif "recommendations" in result and result.get("total_programmes"):
                recs = result.get("recommendations", [])
                if recs:
                    rec_text = "## EU Funding Programme Recommendations\n\n"
                    rec_text += "Based on your profile, here are the most relevant EU funding programmes:\n\n"
                    for i, rec in enumerate(recs, 1):
                        icon = rec.get("programme_icon", "🇪🇺")
                        name = rec.get("programme_name", rec.get("programme", ""))
                        budget = rec.get("budget", "")
                        focus = rec.get("focus", "")
                        reasons = rec.get("reasons", [])
                        website = rec.get("website", "")

                        rec_text += f"### {i}. {icon} **{name}**\n"
                        rec_text += f"- **Budget**: {budget}\n"
                        rec_text += f"- **Focus**: {focus}\n"
                        if reasons:
                            rec_text += f"- **Why it fits**: {'; '.join(reasons)}\n"
                        if website:
                            rec_text += f"- **Learn more**: {website}\n"
                        rec_text += "\n"

                    # Check if we have profile info from reasons to provide personalized next steps
                    # Look for indicators of SME, health sector, or specific profile details
                    has_specific_profile = False
                    for r in recs:
                        reasons_str = " ".join(r.get("reasons", []))
                        if "SME" in reasons_str or "health" in reasons_str.lower():
                            has_specific_profile = True
                            break

                    rec_text += "---\n\n🎯 **Next Steps:**\n"
                    if has_specific_profile:
                        # User has provided profile info - give actionable next steps
                        rec_text += (
                            "• Ask me to **find specific open calls** matching your profile\n"
                        )
                        rec_text += "• Ask about **consortium building** and partner requirements\n"
                        rec_text += "• Request **budget benchmarks** from similar funded projects\n"
                        rec_text += "• Learn about the **application process** and deadlines\n"
                    else:
                        rec_text += (
                            "• Tell me more about your research area so I can find specific calls\n"
                        )
                        rec_text += "• Share your organization's experience level (first-time applicant, or experienced?)\n"
                        rec_text += "• Let me know your sector (health, energy, digital, etc.) for targeted recommendations\n"

                    content_pieces.append(rec_text)
                else:
                    # No specific matches - provide general guidance
                    rec_text = """## EU Funding Programmes Overview

I can help you find the right EU funding programme! To give you personalized recommendations, please tell me:

1. **Your organization type**: University, SME, NGO, research institute?
2. **Your research area**: What topics do you work on?
3. **Your goals**: Research, training/mobility, cultural projects?

**Main EU Funding Programmes:**

🔬 **Horizon Europe** (€95.5B) - Research & Innovation
🎓 **Erasmus+** (€26.2B) - Education, Training, Youth, Sport
🎨 **Creative Europe** (€2.44B) - Culture & Media
🏥 **EU4Health** (€5.3B) - Health & Crisis Preparedness
💻 **Digital Europe** (€7.5B) - Digital Transformation
🌍 **LIFE Programme** (€5.4B) - Environment & Climate

---

🎯 **Next Steps:**
• Share your organization type and research area
• I'll recommend the best programme and find open calls for you
"""
                    content_pieces.append(rec_text)

            # Extract partner discovery results
            elif (
                result.get("tool_name") == "find_experienced_partners"
                or "experienced_partners" in result
            ):
                partners = result.get("experienced_partners", [])
                total_found = result.get("total_found", 0)
                query_params = result.get("query_params", {})
                keywords = query_params.get("topic_keywords", "specified criteria")

                if not partners and total_found == 0:
                    partner_text = f"""Partner Search Results for '{keywords}':
No organizations found matching your criteria.

Suggestions:
- Try broader keywords (e.g., "energy storage" instead of "solid-state battery")
- Remove the cluster filter to search across all Horizon Europe
- Reduce the minimum projects requirement
- Try searching for related topics"""
                    content_pieces.append(partner_text)
                else:
                    partner_text = f"""## Top Organizations with Experience in '{keywords}'

Found **{total_found} organizations** with relevant track records:

"""
                    for i, p in enumerate(partners[:10], 1):
                        # Prefer full name over short_name for better recognition
                        full_name = p.get("name", "Unknown")
                        short_name = p.get("short_name", "")
                        # Use full name if available, otherwise use short_name
                        name = full_name if len(full_name) > 5 else (short_name or full_name)
                        country = p.get("country", "N/A")
                        org_type = p.get("type", "N/A")
                        org_type_desc = {
                            "HES": "Higher Education",
                            "REC": "Research Center",
                            "PRC": "Private Company",
                            "PUB": "Public Body",
                            "OTH": "Other",
                        }.get(org_type, org_type)
                        track = p.get("track_record", {})
                        relevant = track.get("relevant_projects", 0)
                        coord = track.get("as_coordinator", 0)
                        # Use funding_in_relevant (actual field) with fallback to total_funding
                        total_funding = track.get(
                            "funding_in_relevant", track.get("total_funding", 0)
                        )
                        # Get project examples (list of dicts with acronym, title, role)
                        project_examples = p.get("relevant_projects", [])

                        partner_text += f"### {i}. **{name}** ({country})\n"
                        partner_text += f"- **Organization Type**: {org_type} ({org_type_desc})\n"
                        partner_text += f"- **Relevant Projects**: {relevant}"
                        if coord > 0:
                            partner_text += f" (coordinated **{coord}** projects)"
                        partner_text += f"\n- **Total Funding**: €{total_funding:,.0f}\n"

                        # Add project examples if available (shows municipal/testbed evidence)
                        if project_examples and isinstance(project_examples, list):
                            partner_text += "- **Example Projects**: "
                            examples = []
                            for proj in project_examples[:3]:  # Max 3 examples
                                if isinstance(proj, dict):
                                    acronym = proj.get("acronym", "")
                                    role = proj.get("role", "participant")
                                    if acronym:
                                        examples.append(f"{acronym} ({role})")
                            if examples:
                                partner_text += ", ".join(examples) + "\n"

                        partner_text += "\n"

                    # Add insights if available
                    insights = result.get("aggregated_insights", {})
                    if insights.get("top_countries_in_topic"):
                        partner_text += f"\n**Top countries for this topic**: {', '.join(insights['top_countries_in_topic'][:5])}\n"
                    if insights.get("top_org_types"):
                        partner_text += f"**Common organization types**: {', '.join(insights['top_org_types'][:3])}\n"

                    # Add actionability section with country-specific resources
                    country_filter = query_params.get("country", "")
                    partner_text += """
---

### How to Verify & Contact Partners

- **CORDIS Database**: Search for specific projects at https://cordis.europa.eu
- **EU Funding Portal**: https://ec.europa.eu/info/funding-tenders/
- **Partner Search**: Use the EU Partner Search tool to find and contact organizations
- **Verify Municipal Networks**: Check organizations' websites for urban/city partnerships, living labs, or pilot site descriptions
"""
                    # Add Spain-specific resource for municipal networks
                    if country_filter and country_filter.upper() in ["ES", "SPAIN"]:
                        partner_text += "- **FEMP (Spanish Federation of Municipalities)**: http://www.femp.es - Contact for municipal network verification\n"
                    content_pieces.append(partner_text)

        if not content_pieces:
            return "I found some information but couldn't extract specific details. Please try a more specific question."

        # Combine and deduplicate content
        unique_content = []
        seen = set()
        for piece in content_pieces:
            key = piece[:100].lower()
            if key not in seen:
                seen.add(key)
                unique_content.append(piece)

        # Build a structured response
        # Check for special formatted outputs that should bypass the "Finding X:" wrapper
        # These are detailed outputs that should be returned directly without truncation

        # Markers for detailed content types - prioritize similar projects over call details
        # (since user wants similar projects, not just call info)
        direct_output_markers_priority = [
            "## Relevant Funded Projects",  # Highest priority — merged semantic+keyword results
            "## More Funded Projects",  # Pagination — continuation of merged results
            "## Similar Funded Projects",  # Semantic-only results (when no merge)
            "## Similar Projects Search",
            "## Project Search Results",  # Keyword-only results (when no merge)
            "## Collaboration Network:",  # Network exploration results
            "## Projects by ",  # Organization project results
            "## Projects for ",  # Organization project results (no results case)
            "## Organization Statistics:",  # Organization aggregate stats
            "## Project Timeline Generated",
            "## Funding History Analysis:",
            "## Geographic Diversification Analysis:",  # Country group analysis
            "**Programme Statistics:**",  # Programme/cluster statistics
            "Programme Statistics for",  # Alternative statistics format
            "**EIC Accelerator Statistics:**",  # Specific programme stats
            "**ERC Statistics:**",  # Specific programme stats
            "**MSCA Statistics:**",  # Specific programme stats
            "## Call Details:",  # Lower priority - context, not main answer
            "## Common ",  # Cross-analysis: common partners, organizations
            "## Comparison",  # Cross-analysis: comparing results
            "## Cross-Analysis",  # Cross-analysis: generic
            "## Partner",  # Cross-analysis: partner-related
        ]

        # Collect ALL content pieces with direct output markers
        direct_outputs = []
        regular_content = []

        for content in unique_content:
            is_direct = False
            for marker in direct_output_markers_priority:
                if marker in content:
                    direct_outputs.append((marker, content))
                    is_direct = True
                    break
            if not is_direct:
                regular_content.append(content)

        # If we have direct outputs, combine them (prioritizing similar projects)
        if direct_outputs:
            # Sort by priority (lower index = higher priority)
            direct_outputs.sort(
                key=lambda x: (
                    direct_output_markers_priority.index(x[0])
                    if x[0] in direct_output_markers_priority
                    else 999
                )
            )

            # Combine all direct outputs
            combined_parts = []
            for _marker, content in direct_outputs:
                combined_parts.append(content)

            # Also include substantial regular content (e.g. project lists, details)
            # so tool results aren't silently dropped when a direct output exists
            for rc in regular_content:
                if len(rc) > 200:
                    combined_parts.append(rc)

            return "\n\n---\n\n".join(combined_parts)

        intro = f"Based on my search for information about '{query}', here's what I found:\n\n"

        # Take top pieces and format
        body_parts = []
        for i, content in enumerate(unique_content[:5], 1):
            # Truncate long pieces (use higher limit for statistics and detailed results)
            is_detailed = any(
                k in content.lower()
                for k in [
                    "statistics",
                    "eligibility",
                    "organizations",
                    "funding",
                    "timeline",
                    "work package",
                    "deliverable",
                    "milestone",
                    "gantt",
                    "similar",
                    "call details",
                    "budget",
                    "partner",
                    "consortium",
                    "coordinator",
                    "project id",
                    "ec contribution",
                ]
            )
            max_len = 8000 if is_detailed else 1500
            if len(content) > max_len:
                content = content[:max_len] + "..."
            body_parts.append(f"**Finding {i}:**\n{content}")

        return intro + "\n\n".join(body_parts)

    def _summarize_tool_results(self, tool_calls: list) -> str:
        """Summarize results from tool calls in a human-readable format."""
        summaries = []

        for tc in tool_calls:
            if tc.success:
                result = tc.result
                summary = self._format_tool_result_summary(tc.tool_name, result)
                summaries.append(summary)
            else:
                summaries.append(f"{tc.tool_name}: Failed - {tc.error}")

        return "\n".join(summaries)

    def _format_erasmus_eligibility_result(self, result: dict) -> str:
        """Format Erasmus+ eligibility check result into readable text."""
        if not result.get("success"):
            return ""

        metadata = result.get("metadata", {})
        query_type = metadata.get("query_type", "")

        # Single action eligibility check
        if query_type == "specific_action" and "result" in result:
            check_result = result["result"]
            action_type = check_result.get("action_type", "Unknown")
            action_name = check_result.get("action_name", "Unknown Action")
            eligible = check_result.get("eligible", False)
            requirements_met = check_result.get("requirements_met", [])
            requirements_missing = check_result.get("requirements_missing", [])
            warnings = check_result.get("warnings", [])
            recommendations = check_result.get("recommendations", [])

            # Get country and org type from metadata
            check_metadata = check_result.get("metadata", {})
            country = check_metadata.get("country", "Unknown")
            org_type = check_metadata.get("org_type", "Unknown")
            is_programme_country = check_metadata.get("is_programme_country", False)
            accreditation_info = check_metadata.get("accreditation_info")

            eligibility_text = f"""## Erasmus+ Eligibility Check: {action_name} ({action_type})

**Organization**: {org_type} from {country}
**Country Status**: {"Programme Country ✅" if is_programme_country else "Partner Country (Third Country)"}
**Eligibility**: {"✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"}

"""
            if requirements_met:
                eligibility_text += "**Requirements Met:**\n"
                for req in requirements_met:
                    eligibility_text += f"- ✅ {req}\n"
                eligibility_text += "\n"

            if requirements_missing:
                eligibility_text += "**Requirements Not Met:**\n"
                for req in requirements_missing:
                    eligibility_text += f"- ❌ {req}\n"
                eligibility_text += "\n"

            if warnings:
                eligibility_text += "**Warnings:**\n"
                for warning in warnings:
                    eligibility_text += f"- ⚠️ {warning}\n"
                eligibility_text += "\n"

            if recommendations:
                eligibility_text += "**Recommendations & Requirements:**\n"
                for rec in recommendations:
                    eligibility_text += f"- {rec}\n"
                eligibility_text += "\n"

            # Add accreditation information if available
            if accreditation_info and eligible:
                accred_type = accreditation_info.get("accreditation_type", "")
                benefits = accreditation_info.get("benefits", [])
                alternative = accreditation_info.get("alternative")
                apply_url = accreditation_info.get("apply_url", "")

                eligibility_text += f"**📋 Accreditation: {accred_type}**\n\n"

                if benefits:
                    eligibility_text += "Benefits of accreditation:\n"
                    for benefit in benefits:
                        eligibility_text += f"- {benefit}\n"
                    eligibility_text += "\n"

                if alternative:
                    eligibility_text += f"💡 **Alternative pathway**: {alternative}\n\n"

                if apply_url:
                    eligibility_text += f"📌 Learn more about accreditation: {apply_url}\n\n"

            eligibility_text += """
---
🎯 **Next Steps:**
• Check the [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide) for detailed eligibility criteria
• Register on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for country-specific guidance
"""
            return eligibility_text

        # All eligible actions check
        elif query_type == "all_actions" and "eligible_actions" in result:
            eligible_actions = result.get("eligible_actions", [])
            total_eligible = result.get("total_eligible", len(eligible_actions))
            country = metadata.get("country", "Unknown")
            org_type = metadata.get("org_type", "Unknown")

            if total_eligible == 0:
                eligibility_text = f"""## Erasmus+ Eligibility Check for {org_type} from {country}

**Eligibility**: ❌ No eligible actions found

This may be because:
- {country} is a Partner/Third Country with limited participation options
- The organization type ({org_type}) has specific restrictions

**Recommendations:**
- Check if your country has bilateral agreements for specific actions
- Consider participation as a partner rather than coordinator
- Contact your National Agency for specific opportunities
"""
            else:
                eligibility_text = f"""## Erasmus+ Eligibility Check for {org_type} from {country}

**Total Eligible Actions**: {total_eligible}

**Eligible Actions:**
"""
                for action in eligible_actions:
                    action_type = action.get("action_type", "")
                    action_name = action.get("action_name", "")
                    warnings = action.get("warnings", [])
                    notes = action.get("notes", [])

                    eligibility_text += f"\n### {action_name} ({action_type})\n"
                    if warnings:
                        for w in warnings:
                            eligibility_text += f"- ⚠️ {w}\n"
                    if notes:
                        for n in notes:
                            eligibility_text += f"- {n}\n"

                eligibility_text += """
---
🎯 **Next Steps:**
• Review the [Erasmus+ Programme Guide](https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide) for detailed requirements
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact your [National Agency](https://erasmus-plus.ec.europa.eu/contacts/national-agencies) for support
"""

            return eligibility_text

        return ""

    def _format_creative_europe_eligibility_result(self, result: dict) -> str:
        """Format Creative Europe eligibility check result into readable text."""
        if not result.get("success"):
            return ""

        metadata = result.get("metadata", {})
        query_type = metadata.get("query_type", "")

        # Single action eligibility check
        if query_type == "specific_action" and "result" in result:
            check_result = result["result"]
            action_type = check_result.get("action_type", "Unknown")
            action_name = check_result.get("action_name", "Unknown Action")
            strand = check_result.get("strand", "Unknown")
            eligible = check_result.get("eligible", False)
            requirements_met = check_result.get("requirements_met", [])
            requirements_missing = check_result.get("requirements_missing", [])
            warnings = check_result.get("warnings", [])
            recommendations = check_result.get("recommendations", [])

            # Get country and org type from metadata
            check_metadata = check_result.get("metadata", {})
            country = check_metadata.get("country", "Unknown")
            org_type = check_metadata.get("org_type", "Unknown")
            is_eligible_country = check_metadata.get("is_eligible_country", True)

            eligibility_text = f"""## Creative Europe Eligibility Check: {action_name} ({action_type})

**Strand**: {strand}
**Organization**: {org_type} from {country}
**Country Status**: {"Eligible Country ✅" if is_eligible_country else "Third Country (restrictions may apply)"}
**Eligibility**: {"✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"}

"""
            if requirements_met:
                eligibility_text += "**Requirements Met:**\n"
                for req in requirements_met:
                    eligibility_text += f"- ✅ {req}\n"
                eligibility_text += "\n"

            if requirements_missing:
                eligibility_text += "**Requirements Not Met:**\n"
                for req in requirements_missing:
                    eligibility_text += f"- ❌ {req}\n"
                eligibility_text += "\n"

            if warnings:
                eligibility_text += "**Warnings:**\n"
                for warning in warnings:
                    eligibility_text += f"- ⚠️ {warning}\n"
                eligibility_text += "\n"

            if recommendations:
                eligibility_text += "**Recommendations & Requirements:**\n"
                for rec in recommendations:
                    eligibility_text += f"- {rec}\n"
                eligibility_text += "\n"

            eligibility_text += """
---
🎯 **Next Steps:**
• Check the [CulturEU Funding Guide](https://culture.ec.europa.eu/funding/cultureu-funding-guide) for programme details
• Review calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact the [Creative Europe Desks](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) in your country
"""
            return eligibility_text

        # All eligible actions (by strand)
        elif query_type == "all_actions" and "eligible_actions" in result:
            eligible_actions = result.get("eligible_actions", [])
            total_eligible = result.get("total_eligible", len(eligible_actions))
            country = metadata.get("country", "Unknown")
            org_type = metadata.get("org_type", "Unknown")
            strand = metadata.get("strand", "All Strands")

            if total_eligible == 0:
                eligibility_text = f"""## Creative Europe Eligibility Check for {org_type} from {country}

**Strand**: {strand}
**Eligibility**: ❌ No eligible actions found

This may be because:
- The organization type ({org_type}) is not eligible for {strand} actions
- {country} may have restrictions for certain Creative Europe actions

**Recommendations:**
- Check if your organization qualifies under a different category
- Review the CulturEU Funding Guide for alternative opportunities
- Contact your Creative Europe Desk for guidance
"""
            else:
                eligibility_text = f"""## Creative Europe Eligibility Check for {org_type} from {country}

**Strand**: {strand}
**Total Eligible Actions**: {total_eligible}

**Eligible Actions:**
"""
                for action in eligible_actions:
                    action_type = action.get("action_type", "")
                    action_name = action.get("action_name", "")
                    action_strand = action.get("strand", "")
                    warnings = action.get("warnings", [])
                    notes = action.get("notes", [])

                    eligibility_text += f"\n### {action_name} ({action_type}) - {action_strand}\n"
                    if warnings:
                        for w in warnings:
                            eligibility_text += f"- ⚠️ {w}\n"
                    if notes:
                        for n in notes:
                            eligibility_text += f"- {n}\n"

                eligibility_text += """
---
🎯 **Next Steps:**
• Review the [CulturEU Funding Guide](https://culture.ec.europa.eu/funding/cultureu-funding-guide) for detailed requirements
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact your [Creative Europe Desk](https://culture.ec.europa.eu/creative-europe/creative-europe-desks) for support
"""

            return eligibility_text

        return ""

    def _format_eu4health_eligibility_result(self, result: dict) -> str:
        """Format EU4Health eligibility check result into readable text."""
        if not result.get("success"):
            return ""

        metadata = result.get("metadata", {})
        query_type = metadata.get("query_type", "")

        # Single action eligibility check
        if query_type == "specific_action" and "result" in result:
            check_result = result["result"]
            action_type = check_result.get("action_type", "Unknown")
            action_name = check_result.get("action_name", "Unknown Action")
            eligible = check_result.get("eligible", False)
            requirements_met = check_result.get("requirements_met", [])
            requirements_missing = check_result.get("requirements_missing", [])
            warnings = check_result.get("warnings", [])
            recommendations = check_result.get("recommendations", [])

            # Get country and org type from metadata
            check_metadata = check_result.get("metadata", {})
            country = check_metadata.get("country", "Unknown")
            org_type = check_metadata.get("org_type", "Unknown")
            is_eu_member = check_metadata.get("is_eu_member", False)
            is_associated = check_metadata.get("is_associated", False)

            country_status = (
                "EU Member State ✅"
                if is_eu_member
                else ("Associated Country" if is_associated else "Participating Country")
            )

            eligibility_text = f"""## EU4Health Eligibility Check: {action_name} ({action_type})

**Organization**: {org_type.replace("_", " ").title()} from {country}
**Country Status**: {country_status}
**Eligibility**: {"✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"}

"""
            if requirements_met:
                eligibility_text += "**Requirements Met:**\n"
                for req in requirements_met:
                    eligibility_text += f"- ✅ {req}\n"
                eligibility_text += "\n"

            if requirements_missing:
                eligibility_text += "**Requirements Not Met:**\n"
                for req in requirements_missing:
                    eligibility_text += f"- ❌ {req}\n"
                eligibility_text += "\n"

            if warnings:
                eligibility_text += "**Warnings:**\n"
                for warning in warnings:
                    eligibility_text += f"- ⚠️ {warning}\n"
                eligibility_text += "\n"

            if recommendations:
                eligibility_text += "**Key Information:**\n"
                for rec in recommendations:
                    eligibility_text += f"- {rec}\n"
                eligibility_text += "\n"

            eligibility_text += """
---
🎯 **Next Steps:**
• Check the [EU4Health Programme](https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en) for programme details
• Review calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact [HaDEA](https://hadea.ec.europa.eu/programmes/eu4health_en) (Health and Digital Executive Agency) for support
"""
            return eligibility_text

        # All eligible actions check
        elif query_type == "all_actions" and "eligible_actions" in result:
            eligible_actions = result.get("eligible_actions", [])
            total_eligible = result.get("total_eligible", len(eligible_actions))
            country = metadata.get("country", "Unknown")
            org_type = metadata.get("org_type", "Unknown")

            if total_eligible == 0:
                eligibility_text = f"""## EU4Health Eligibility Check for {org_type.replace("_", " ").title()} from {country}

**Eligibility**: ❌ No eligible actions found

This may be because:
- {country} is not a participating country in EU4Health
- The organization type ({org_type.replace("_", " ")}) has restrictions for EU4Health actions
- Joint Actions (JA) are only for Member State public authorities

**Recommendations:**
- Check if your organization qualifies under a different category
- Consider partnership with eligible entities
- Contact HaDEA for guidance on specific opportunities
"""
            else:
                eligibility_text = f"""## EU4Health Eligibility Check for {org_type.replace("_", " ").title()} from {country}

**Total Eligible Actions**: {total_eligible}

**Available Funding Options:**
"""
                for action in eligible_actions:
                    action_type = action.get("action_type", "")
                    action_name = action.get("action_name", "")
                    description = action.get("description", "")
                    co_financing = action.get("co_financing", "")
                    warnings = action.get("warnings", [])
                    notes = action.get("notes", [])

                    eligibility_text += f"\n### {action_name} ({action_type})\n"
                    if description:
                        eligibility_text += f"{description}\n\n"
                    if co_financing:
                        eligibility_text += f"- **EU Co-financing**: {co_financing}\n"
                    if warnings:
                        for w in warnings:
                            eligibility_text += f"- ⚠️ {w}\n"
                    if notes:
                        for n in notes:
                            eligibility_text += f"- {n}\n"

                # Add strands information if available
                strands = result.get("strands", {})
                if strands:
                    eligibility_text += "\n### EU4Health Thematic Strands\n"
                    for strand_code, strand_info in strands.items():
                        strand_name = strand_info.get("name", strand_code)
                        strand_desc = strand_info.get("description", "")
                        eligibility_text += f"- **{strand_name}**: {strand_desc}\n"

                eligibility_text += """
---
🎯 **Next Steps:**
• Review the [EU4Health Annual Work Programme](https://health.ec.europa.eu/funding/eu4health-programme-2021-2027/annual-work-programmes_en) for current priorities
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)
• Contact [HaDEA](https://hadea.ec.europa.eu/programmes/eu4health_en) for guidance and support
"""

            return eligibility_text

        return ""

    def _format_eu4health_template_search_result(self, result: dict) -> str:
        """Format EU4Health template search results into readable text.

        This method formats results from search_eu4health_templates tool,
        presenting EU4Health programme information including priorities,
        cancer plan details, and other thematic content.
        """
        if not result.get("success"):
            return ""

        results = result.get("results", [])
        if not results:
            return ""

        query = result.get("query", "")
        detected_strand = result.get("detected_strand", "")
        total_found = result.get("total_found", len(results))

        # Build the formatted output
        parts = []

        # Header based on detected strand
        strand_headers = {
            "PREVENTION": "## EU4Health Disease Prevention & Cancer Priorities",
            "CRISIS": "## EU4Health Crisis Preparedness & Health Security",
            "HEALTH_SYSTEMS": "## EU4Health Health Systems & Workforce",
            "DIGITAL": "## EU4Health Digital Health & EHDS",
        }
        header = strand_headers.get(detected_strand, "## EU4Health Programme Information")
        parts.append(header)
        parts.append("")

        # Add strand context if detected
        strand_descriptions = {
            "PREVENTION": (
                "The EU4Health programme supports disease prevention through "
                "**Europe's Beating Cancer Plan**, non-communicable disease (NCD) "
                "prevention, vaccination programs, screening initiatives, and health "
                "promotion activities."
            ),
            "CRISIS": (
                "EU4Health supports **crisis preparedness** through HERA (Health "
                "Emergency Preparedness and Response Authority), medical countermeasures "
                "(MCM) stockpiling, and antimicrobial resistance (AMR) actions."
            ),
            "HEALTH_SYSTEMS": (
                "EU4Health strengthens health systems through healthcare workforce "
                "support, Health Technology Assessment (HTA), medicines supply, and "
                "pharmaceutical strategy implementation."
            ),
            "DIGITAL": (
                "EU4Health advances digital health through the **European Health "
                "Data Space (EHDS)**, eHealth infrastructure, telemedicine support, "
                "and AI applications in healthcare."
            ),
        }
        if detected_strand and detected_strand in strand_descriptions:
            parts.append(f"**Overview:** {strand_descriptions[detected_strand]}")
            parts.append("")

        # Add relevant content from search results
        parts.append(f"### Key Information (from {total_found} relevant sources)")
        parts.append("")

        for i, item in enumerate(results[:5], 1):
            content = item.get("content", "")
            section = item.get("section", "general")
            section_desc = item.get("section_description", "")

            if content:
                # Clean and format content
                content = content.strip()
                # Remove page references like [Page 23] that trigger quality checks
                content = re.sub(r"\[Page\s*\d+\]", "", content)
                content = re.sub(r"\s{2,}", " ", content)  # Clean up extra whitespace
                # Truncate if too long but keep meaningful content
                if len(content) > 800:
                    content = content[:800] + "..."

                section_label = section_desc if section_desc else section.replace("_", " ").title()
                parts.append(f"**{i}. {section_label}**")
                parts.append(content)
                parts.append("")

        # Add Europe's Beating Cancer Plan context if cancer-related query
        query_lower = query.lower()
        if "cancer" in query_lower:
            parts.append("### Europe's Beating Cancer Plan")
            parts.append(
                "The EU4Health programme is a key funding source for implementing "
                "**Europe's Beating Cancer Plan**, with priorities including:"
            )
            parts.append("- Cancer screening and early detection programmes")
            parts.append("- Cancer prevention through lifestyle interventions")
            parts.append("- Quality of life for cancer survivors")
            parts.append("- Addressing inequalities in cancer care")
            parts.append("- Cancer research and data sharing")
            parts.append("")

        # Add actionable next steps
        parts.append("---")
        parts.append("")
        parts.append("🎯 **Next Steps:**")
        parts.append(
            "• Review the [EU4Health Annual Work Programmes]"
            "(https://health.ec.europa.eu/funding/eu4health-programme-2021-2027/"
            "annual-work-programmes_en) for current priorities"
        )
        parts.append(
            "• Check open calls on the [EU Funding & Tenders Portal]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
            "?programmePeriod=2021-2027&programCcm2Id=43332851)"
        )
        if "cancer" in query_lower:
            parts.append(
                "• Learn about [Europe's Beating Cancer Plan]"
                "(https://ec.europa.eu/health/document/download/"
                "7b3bb1b5-7791-4965-9b47-5e270c9f1c69)"
            )
        parts.append(
            "• Contact [HaDEA](https://hadea.ec.europa.eu/programmes/eu4health_en) "
            "for guidance and support"
        )

        return "\n".join(parts)

    def _format_consortium_patterns_result(self, result: dict) -> str:
        """Format consortium patterns results into a rich, readable response."""
        query_params = result.get("query_params", {})
        projects_analyzed = result.get("projects_analyzed", 0)
        consortium = result.get("consortium_size", {})
        org_dist = result.get("organization_type_distribution", {})
        country_patterns = result.get("country_patterns", {})
        coordinator_profile = result.get("coordinator_profile", {})
        recommendations = result.get("recommendations", {})
        sample_consortia = result.get("sample_consortia", [])
        successful_templates = result.get("successful_templates", [])
        coordinator_analysis = result.get("coordinator_analysis", {})

        # Build title from query params
        action_type = query_params.get("action_type", "")
        cluster = query_params.get("cluster", "")
        keywords = query_params.get("topic_keywords", "")
        title_parts = []
        if action_type:
            title_parts.append(action_type)
        if cluster:
            title_parts.append(f"Cluster {cluster.replace('CLUSTER-', '')}")
        if keywords and not title_parts:
            title_parts.append(keywords[:50])
        title = " ".join(title_parts) if title_parts else "Horizon Europe"

        parts = [f"## Consortium Patterns: {title} Projects"]
        parts.append(f"\n**Based on {projects_analyzed:,} funded projects**\n")

        # Consortium size
        if consortium:
            avg = consortium.get("average", 0)
            median = consortium.get("median", 0)
            min_size = consortium.get("min", 0)
            max_size = consortium.get("max", 0)
            recommended = consortium.get("recommended", "")

            parts.append("### Consortium Size")
            parts.append(f"- **Average:** {avg:.1f} partners")
            parts.append(f"- **Median:** {median:.0f} partners")
            if min_size and max_size:
                parts.append(f"- **Range:** {min_size} - {max_size} partners")
            if recommended:
                parts.append(f"- **Recommended:** {recommended}")
            parts.append("")

        # Geographic diversity
        geo = country_patterns.get("geographic_diversity", {})
        if geo:
            avg_countries = geo.get("avg_countries", 0)
            if avg_countries:
                parts.append(f"- **Average Countries per Project:** {avg_countries:.1f}")
                parts.append("")

        # Organization type distribution
        if org_dist:
            org_type_names = {
                "HES": "Higher Education (Universities)",
                "REC": "Research Organizations",
                "PRC": "Private Companies",
                "SME": "Small & Medium Enterprises",
                "PUB": "Public Bodies",
                "OTH": "Other Organizations",
            }
            parts.append("### Organization Type Distribution\n")
            parts.append("| Type | Share | Avg per Project |")
            parts.append("|------|-------|-----------------|")
            for org_type, data in sorted(
                org_dist.items(), key=lambda x: x[1].get("percentage", 0), reverse=True
            ):
                if isinstance(data, dict):
                    pct = data.get("percentage", 0)
                    avg_count = data.get("avg_per_project", "")
                    type_name = org_type_names.get(org_type, org_type)
                    avg_str = f"{avg_count:.1f}" if isinstance(avg_count, int | float) else "-"
                    parts.append(f"| {type_name} | {pct:.0f}% | {avg_str} |")
            parts.append("")

        # Top participating countries
        top_countries = country_patterns.get("top_participating", [])
        if top_countries:
            parts.append("### Top Participating Countries\n")
            parts.append("| Country | Projects | As Coordinator |")
            parts.append("|---------|----------|----------------|")
            for c in top_countries[:10]:
                country = c.get("country", "N/A")
                count = c.get("count", c.get("projects", 0))
                coord = c.get("as_coordinator", c.get("coordinator_count", "-"))
                parts.append(f"| {country} | {count:,} | {coord} |")
            parts.append("")

        # Coordinator profile
        if coordinator_profile:
            parts.append("### Typical Coordinator Profile")
            top_coord_types = coordinator_profile.get("top_types", [])
            top_coord_countries = coordinator_profile.get("top_countries", [])
            if top_coord_types:
                types_str = ", ".join(
                    f"{t.get('type', '?')} ({t.get('percentage', 0):.0f}%)"
                    for t in top_coord_types[:3]
                )
                parts.append(f"- **Most Common Types:** {types_str}")
            if top_coord_countries:
                countries_str = ", ".join(
                    f"{c.get('country', '?')} ({c.get('count', 0)})"
                    for c in top_coord_countries[:5]
                )
                parts.append(f"- **Top Coordinator Countries:** {countries_str}")
            parts.append("")

        # Coordinator analysis (from graph data)
        if coordinator_analysis:
            top_coordinators = coordinator_analysis.get("top_coordinators", [])
            if top_coordinators:
                parts.append("### Most Active Coordinators\n")
                for i, coord in enumerate(top_coordinators[:5], 1):
                    name = coord.get("name", coord.get("organization", "Unknown"))
                    count = coord.get("projects_coordinated", coord.get("count", 0))
                    country = coord.get("country", "")
                    country_str = f" ({country})" if country else ""
                    parts.append(f"{i}. **{name}**{country_str}: {count} projects coordinated")
                parts.append("")

        # Successful consortium templates
        if successful_templates:
            parts.append("### Example Successful Consortia\n")
            for i, template in enumerate(successful_templates[:3], 1):
                acronym = template.get("acronym", template.get("project", "N/A"))
                title_t = template.get("title", "")
                partner_count = template.get("partner_count", template.get("partners", 0))
                country_count = template.get("country_count", template.get("countries", 0))
                budget = template.get("budget", template.get("ec_contribution", 0))
                budget_str = f"€{budget / 1_000_000:.1f}M" if budget else ""
                parts.append(f"**{i}. {acronym}**" + (f": {title_t}" if title_t else ""))
                detail_items = []
                if partner_count:
                    detail_items.append(f"{partner_count} partners")
                if country_count:
                    detail_items.append(f"{country_count} countries")
                if budget_str:
                    detail_items.append(budget_str)
                if detail_items:
                    parts.append(f"- {' | '.join(detail_items)}")

                # Show org type composition if available
                composition = template.get("org_types", template.get("composition", {}))
                if composition and isinstance(composition, dict):
                    comp_parts = [f"{k}: {v}" for k, v in composition.items() if v]
                    if comp_parts:
                        parts.append(f"- Composition: {', '.join(comp_parts[:4])}")
                parts.append("")

        # Sample consortia (from SQL)
        elif sample_consortia:
            parts.append("### Example Funded Consortia\n")
            for i, sample in enumerate(sample_consortia[:3], 1):
                acronym = sample.get("acronym", "N/A")
                partner_count = sample.get("partner_count", sample.get("partners", 0))
                budget = sample.get("budget", sample.get("ec_contribution", 0))
                budget_str = f"€{budget / 1_000_000:.1f}M" if budget else ""
                parts.append(
                    f"**{i}. {acronym}**: {partner_count} partners"
                    + (f", {budget_str}" if budget_str else "")
                )
            parts.append("")

        # Recommendations
        if recommendations:
            parts.append("### Recommendations\n")
            if isinstance(recommendations, dict):
                ideal = recommendations.get("ideal_composition", [])
                if ideal:
                    for item in ideal[:4]:
                        parts.append(f"- {item}")
                suggested_size = recommendations.get("suggested_consortium_size", "")
                if suggested_size:
                    parts.append(f"- **Suggested Size:** {suggested_size}")
                key_advice = recommendations.get("key_advice", recommendations.get("tips", []))
                if isinstance(key_advice, list):
                    for tip in key_advice[:3]:
                        parts.append(f"- {tip}")
                elif isinstance(key_advice, str) and key_advice:
                    parts.append(f"- {key_advice}")
            elif isinstance(recommendations, list):
                for rec in recommendations[:5]:
                    parts.append(f"- {rec}")
            parts.append("")

        # Next steps
        parts.append("---\n")
        parts.append("**Next Steps:**")
        parts.append("- Review similar funded projects on [CORDIS](https://cordis.europa.eu/)")
        parts.append(
            "- Find partners on the [EU Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)"
        )
        parts.append(
            "- Check open calls on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
        )

        return "\n".join(parts)

    def _format_erasmus_template_search_result(self, result: dict) -> str:
        """Format Erasmus+ template search results into readable text.

        This method formats results from search_erasmus_templates tool,
        presenting Erasmus+ Programme Guide 2026 content including quality
        criteria, evaluation criteria, eligibility rules, and other guidance.

        The 2025/2026 Programme Guide is the authoritative source for all
        Erasmus+ application requirements and evaluation criteria.
        """
        if not result.get("success"):
            return ""

        results = result.get("results", [])
        if not results:
            return ""

        query = result.get("query", "")
        total_found = result.get("total_found", len(results))
        filters = result.get("filters", {})

        # Build the formatted output
        parts = []

        # Header based on query content
        query_lower = query.lower()
        if "quality" in query_lower or "criteria" in query_lower or "evaluat" in query_lower:
            parts.append("## Erasmus+ Quality & Evaluation Criteria")
        elif "eligibility" in query_lower:
            parts.append("## Erasmus+ Eligibility Requirements")
        elif "budget" in query_lower or "funding" in query_lower:
            parts.append("## Erasmus+ Funding & Budget Rules")
        else:
            parts.append("## Erasmus+ Programme Guide Information")
        parts.append("")

        # Add Programme Guide 2026 context
        parts.append(
            "📚 **Source:** Erasmus+ Programme Guide 2026 "
            "(Official European Commission publication)"
        )
        parts.append("")

        # Add Key Action context if detected
        key_action = filters.get("key_action")
        if key_action:
            ka_descriptions = {
                "KA1": "Key Action 1 (Learning Mobility of Individuals)",
                "KA2": "Key Action 2 (Cooperation Among Organisations)",
                "KA3": "Key Action 3 (Policy Support)",
                "JMO": "Jean Monnet Actions",
                "SPORT": "Sport Actions",
            }
            ka_desc = ka_descriptions.get(key_action, key_action)
            parts.append(f"**Key Action:** {ka_desc}")
            parts.append("")

        # Add relevant content from search results
        parts.append(f"### Key Information (from {total_found} relevant sources)")
        parts.append("")

        for i, item in enumerate(results[:6], 1):
            content = item.get("content", "")
            section = item.get("section", "general")
            section_desc = item.get("section_description", "")
            doc_title = item.get("document_title", "Erasmus+ Programme Guide")

            if content:
                # Clean and format content
                content = content.strip()
                # Remove page references like [Page 23] that trigger quality checks
                content = re.sub(r"\[Page\s*\d+\]", "", content)
                content = re.sub(r"\s{2,}", " ", content)  # Clean up extra whitespace
                # Truncate if too long but keep meaningful content
                if len(content) > 800:
                    content = content[:800] + "..."

                section_label = section_desc if section_desc else section.replace("_", " ").title()

                # Note the 2026 guide explicitly
                if "2026" in doc_title or "programme guide" in doc_title.lower():
                    doc_note = " (Programme Guide 2026)"
                else:
                    doc_note = ""

                parts.append(f"**{i}. {section_label}{doc_note}**")
                parts.append(content)
                parts.append("")

        # Add quality criteria summary if this is a quality/evaluation query
        if "quality" in query_lower or "criteria" in query_lower:
            parts.append("### Standard Erasmus+ Award Criteria")
            parts.append("Erasmus+ applications are evaluated on four main award criteria:")
            parts.append(
                "1. **Relevance of the project** (max 30 points) - Addresses programme objectives"
            )
            parts.append(
                "2. **Quality of project design and implementation** (max 40 points) - "
                "Work plan clarity, methodology, resource allocation"
            )
            parts.append(
                "3. **Quality of partnership and cooperation** (max 20 points) - "
                "Partner complementarity, commitment, role distribution"
            )
            parts.append(
                "4. **Impact and dissemination** (max 10 points) - "
                "Sustainability, reach, multiplier effect"
            )
            parts.append("")
            parts.append(
                "**Minimum threshold:** Projects must score at least 60 points overall, "
                "with a minimum of 50% in each criterion."
            )
            parts.append("")

        # Add actionable next steps
        parts.append("---")
        parts.append("")
        parts.append("🎯 **Next Steps:**")
        parts.append(
            "• Download the full [Erasmus+ Programme Guide 2026]"
            "(https://erasmus-plus.ec.europa.eu/programme-guide/erasmusplus-programme-guide)"
        )
        parts.append(
            "• Check [open Erasmus+ calls]"
            "(https://erasmus-plus.ec.europa.eu/programme-guide/part-b) for your sector"
        )
        parts.append(
            "• Contact your [National Agency]"
            "(https://erasmus-plus.ec.europa.eu/contacts/national-agencies) "
            "for guidance and support"
        )
        parts.append(
            "• Review [successful project examples]"
            "(https://erasmus-plus.ec.europa.eu/projects) on the results platform"
        )

        return "\n".join(parts)

    def _format_multi_programme_search_result(self, result: dict) -> str:
        """Format multi-programme search results into readable text."""
        if not result.get("success"):
            return ""

        total_results = result.get("total_results", 0)
        results_by_programme = result.get("results_by_programme", {})
        programmes_searched = result.get("programmes_searched", [])
        programmes_with_results = result.get("programmes_with_results", [])
        query = result.get("query", "")

        parts = []

        # Header
        parts.append("## Cross-Programme Funding Search Results")
        parts.append("")

        # Summary
        if total_results > 0:
            num_programmes = len(programmes_with_results)
            parts.append(
                f"**Found {total_results} funding opportunit{'y' if total_results == 1 else 'ies'} "
                f"across {num_programmes} programme{'s' if num_programmes != 1 else ''}** "
                f"for your search: *{query}*"
            )
        else:
            parts.append(f"**No open funding calls found** matching your search: *{query}*")
            parts.append("")
            parts.append("This could mean:")
            parts.append("- There are currently no open calls in this specific topic area")
            parts.append("- Relevant calls may have recently closed")
            parts.append("- Upcoming calls may not yet be announced")
            parts.append("")
            parts.append("**💡 Suggestions:**")
            parts.append("- Try broader keywords")
            parts.append("- Check individual programme portals for announcements")
            parts.append(
                "- Sign up for call alerts at the "
                "[EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/)"
            )
            return "\n".join(parts)

        parts.append("")

        # Programme icons and info for display
        programme_info = {
            "horizon_europe": ("🔬", "Horizon Europe", "Research & Innovation"),
            "erasmus_plus": ("🎓", "Erasmus+", "Education & Training"),
            "creative_europe": ("🎨", "Creative Europe", "Culture & Media"),
            "eu4health": ("🏥", "EU4Health", "Health & Crisis Preparedness"),
            "digital_europe": ("💻", "Digital Europe", "Digital Transformation"),
            "life": ("🌍", "LIFE Programme", "Environment & Climate"),
        }

        # Display results grouped by programme
        for programme_key in programmes_with_results:
            prog_results = results_by_programme.get(programme_key, [])
            if not prog_results:
                continue

            icon, name, focus = programme_info.get(
                programme_key, ("📋", programme_key.replace("_", " ").title(), "")
            )

            parts.append(f"### {icon} {name}")
            if focus:
                parts.append(f"*{focus}*")
            parts.append("")

            # List calls for this programme
            for i, call in enumerate(prog_results[:5], 1):
                topic_code = call.get("topic_code", "N/A")
                title = call.get("title", "Untitled")
                status = call.get("status", "unknown")
                deadline = call.get("deadline")
                budget_max = call.get("budget_max")
                portal_url = call.get("portal_url", "")

                # Format status with emoji
                status_emoji = {"open": "🟢", "upcoming": "🔵", "closed": "🔴"}.get(status, "⚪")

                # Build call line
                parts.append(f"**{i}. {title}** ({topic_code})")

                # Details line
                details = [f"Status: {status_emoji} {status.title()}"]
                if deadline:
                    details.append(f"Deadline: {deadline}")
                if budget_max:
                    budget_str = (
                        f"€{budget_max / 1_000_000:.1f}M"
                        if budget_max >= 1_000_000
                        else f"€{budget_max:,.0f}"
                    )
                    details.append(f"Budget: up to {budget_str}")

                parts.append(f"   {' | '.join(details)}")

                # Add portal link if available
                if portal_url:
                    parts.append(f"   🔗 [View on EU Portal]({portal_url})")

                parts.append("")

            # Show if there are more results
            if len(prog_results) > 5:
                parts.append(f"   *... and {len(prog_results) - 5} more {name} calls*")
                parts.append("")

        # Programme coverage note
        parts.append("---")
        parts.append(
            "**Programmes searched:** "
            + ", ".join(
                programme_info.get(p, (None, p.replace("_", " ").title()))[1]
                for p in programmes_searched
            )
        )
        parts.append("")

        # Next steps
        parts.append("🎯 **Next Steps:**")
        parts.append(
            "• Review call details on the [EU Funding & Tenders Portal]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/)"
        )
        parts.append("• Check eligibility requirements for your organization type")
        parts.append("• Find partners using the Partner Search tool")
        parts.append("• Register your organization in the EU Participant Portal")

        return "\n".join(parts)

    def _format_digital_europe_eligibility_result(self, result: dict) -> str:
        """Format Digital Europe eligibility check result into readable text."""
        if not result.get("success"):
            return ""

        metadata = result.get("metadata", {})
        query_type = metadata.get("query_type", "")

        # Single objective eligibility check
        if query_type == "specific_objective" and "result" in result:
            check_result = result["result"]
            objective = check_result.get("objective", "Unknown")
            objective_name = check_result.get("objective_name", "Unknown Objective")
            eligible = check_result.get("eligible", False)
            requirements_met = check_result.get("requirements_met", [])
            requirements_missing = check_result.get("requirements_missing", [])
            warnings = check_result.get("warnings", [])
            recommendations = check_result.get("recommendations", [])

            # Get country and org type from metadata
            check_metadata = check_result.get("metadata", {})
            country = check_metadata.get("country", "Unknown")
            org_type = check_metadata.get("org_type", "Unknown")
            is_eu_member = check_metadata.get("is_eu_member", False)
            is_eea = check_metadata.get("is_eea", False)
            is_associated = check_metadata.get("is_associated", False)

            if is_eu_member:
                country_status = "EU Member State ✅"
            elif is_eea:
                country_status = "EEA Country ✅"
            elif is_associated:
                country_status = "Associated Country"
            else:
                country_status = "Participating Country"

            eligibility_text = f"""## Digital Europe Eligibility Check: {objective_name} ({objective})

**Organization**: {org_type.replace("_", " ").title()} from {country}
**Country Status**: {country_status}
**Eligibility**: {"✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"}

"""
            if requirements_met:
                eligibility_text += "**Requirements Met:**\n"
                for req in requirements_met:
                    eligibility_text += f"- ✅ {req}\n"
                eligibility_text += "\n"

            if requirements_missing:
                eligibility_text += "**Requirements Not Met:**\n"
                for req in requirements_missing:
                    eligibility_text += f"- ❌ {req}\n"
                eligibility_text += "\n"

            if warnings:
                eligibility_text += "**Warnings:**\n"
                for warning in warnings:
                    eligibility_text += f"- ⚠️ {warning}\n"
                eligibility_text += "\n"

            if recommendations:
                eligibility_text += "**Key Information:**\n"
                for rec in recommendations:
                    eligibility_text += f"- {rec}\n"
                eligibility_text += "\n"

            eligibility_text += """
---
🎯 **Next Steps:**
• Check the [Digital Europe Programme](https://digital-strategy.ec.europa.eu/en/activities/digital-programme) for programme details
• Review calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/?programmePeriod=2021-2027&programCcm2Id=43152860)
• Contact [HaDEA](https://hadea.ec.europa.eu/programmes/digital-europe-programme_en) (Health and Digital Executive Agency) for support
"""
            return eligibility_text

        # All eligible objectives check
        elif query_type == "all_objectives" and "eligible_objectives" in result:
            eligible_objectives = result.get("eligible_objectives", [])
            total_eligible = result.get("total_eligible", len(eligible_objectives))
            country = metadata.get("country", "Unknown")
            org_type = metadata.get("org_type", "Unknown")
            objectives_info = result.get("objectives", {})

            if total_eligible == 0:
                eligibility_text = f"""## Digital Europe Eligibility Check for {org_type.replace("_", " ").title()} from {country}

**Eligibility**: ❌ No eligible objectives found

This may be because:
- {country} is not a participating country in Digital Europe
- The organization type ({org_type.replace("_", " ")}) has restrictions for Digital Europe objectives
- Switzerland only participates in HPC and AI objectives

**Recommendations:**
- Check if your organization qualifies under a different category
- Consider partnership with eligible entities from EU Member States
- Contact HaDEA for guidance on specific opportunities
"""
            else:
                eligibility_text = f"""## Digital Europe Eligibility Check for {org_type.replace("_", " ").title()} from {country}

**Total Eligible Objectives**: {total_eligible}

**Available Funding Options:**
"""
                for obj in eligible_objectives:
                    obj_code = obj.get("objective", "")
                    obj_name = obj.get("objective_name", "")
                    eligible = obj.get("eligible", False)
                    warnings = obj.get("warnings", [])
                    recommendations = obj.get("recommendations", [])

                    # Get additional objective info
                    obj_details = objectives_info.get(obj_code, {})
                    budget = obj_details.get("budget", "")
                    funding_rate = obj_details.get("funding_rate", "")
                    description = obj_details.get("description", "")

                    if eligible:
                        eligibility_text += f"\n### {obj_name} ({obj_code}) ✅\n"
                        if description:
                            eligibility_text += f"{description}\n\n"
                        if budget:
                            eligibility_text += f"- **Budget**: {budget}\n"
                        if funding_rate:
                            eligibility_text += f"- **Funding Rate**: {funding_rate}\n"
                        if warnings:
                            for w in warnings:
                                eligibility_text += f"- ⚠️ {w}\n"
                        if recommendations:
                            for r in recommendations:
                                eligibility_text += f"- {r}\n"

                # Add Digital Europe objectives overview
                eligibility_text += "\n### Digital Europe Specific Objectives Overview\n"
                eligibility_text += "The Digital Europe Programme covers 6 strategic objectives:\n"
                eligibility_text += "- **HPC**: High Performance Computing (€2.227B)\n"
                eligibility_text += "- **AI**: Artificial Intelligence (€2.062B)\n"
                eligibility_text += "- **Cybersecurity**: Cybersecurity and Trust (€1.650B)\n"
                eligibility_text += "- **Skills**: Advanced Digital Skills (€577M)\n"
                eligibility_text += "- **Deployment**: EDIHs and Best Use (€1.072B)\n"
                eligibility_text += "- **Semiconductors**: Chips Act initiatives\n"

                eligibility_text += """
---
🎯 **Next Steps:**
• Review the [Digital Europe Work Programmes](https://digital-strategy.ec.europa.eu/en/activities/digital-programme) for current priorities
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/?programmePeriod=2021-2027&programCcm2Id=43152860)
• Contact [HaDEA](https://hadea.ec.europa.eu/programmes/digital-europe-programme_en) for guidance and support
• For EDIHs, check the [EDIH Network](https://european-digital-innovation-hubs.ec.europa.eu/)
"""

            return eligibility_text

        return ""

    def _format_life_eligibility_result(self, result: dict) -> str:
        """Format LIFE Programme eligibility check result into readable text."""
        if not result.get("success"):
            return ""

        metadata = result.get("metadata", {})
        query_type = metadata.get("query_type", "")

        # Single sub-programme eligibility check
        if query_type == "specific_subprogramme" and "result" in result:
            check_result = result["result"]
            subprogramme = check_result.get("subprogramme", "Unknown")
            subprogramme_name = check_result.get("subprogramme_name", "Unknown Sub-programme")
            eligible = check_result.get("eligible", False)
            requirements_met = check_result.get("requirements_met", [])
            requirements_missing = check_result.get("requirements_missing", [])
            warnings = check_result.get("warnings", [])
            recommendations = check_result.get("recommendations", [])

            # Get country and org type from metadata
            check_metadata = check_result.get("metadata", {})
            country = check_metadata.get("country", "Unknown")
            org_type = check_metadata.get("org_type", "Unknown")
            is_eu_member = check_metadata.get("is_eu_member", False)
            is_eea = check_metadata.get("is_eea", False)
            is_associated = check_metadata.get("is_associated", False)
            funding_rate = check_metadata.get("funding_rate", "")

            if is_eu_member:
                country_status = "EU Member State ✅"
            elif is_eea:
                country_status = "EEA Country ✅"
            elif is_associated:
                country_status = "Associated Country"
            else:
                country_status = "Participating Country"

            eligibility_text = f"""## LIFE Programme Eligibility Check: {subprogramme_name} ({subprogramme})

**Organization**: {org_type.replace("_", " ").title()} from {country}
**Country Status**: {country_status}
**Eligibility**: {"✅ ELIGIBLE" if eligible else "❌ NOT ELIGIBLE"}
"""
            if funding_rate:
                eligibility_text += f"**EU Co-financing Rate**: {funding_rate}%\n"

            eligibility_text += "\n"

            if requirements_met:
                eligibility_text += "**Requirements Met:**\n"
                for req in requirements_met:
                    eligibility_text += f"- ✅ {req}\n"
                eligibility_text += "\n"

            if requirements_missing:
                eligibility_text += "**Requirements Not Met:**\n"
                for req in requirements_missing:
                    eligibility_text += f"- ❌ {req}\n"
                eligibility_text += "\n"

            if warnings:
                eligibility_text += "**Warnings:**\n"
                for warning in warnings:
                    eligibility_text += f"- ⚠️ {warning}\n"
                eligibility_text += "\n"

            if recommendations:
                eligibility_text += "**Key Information:**\n"
                for rec in recommendations:
                    eligibility_text += f"- {rec}\n"
                eligibility_text += "\n"

            eligibility_text += """
---
🎯 **Next Steps:**
• Check the [LIFE Programme](https://cinea.ec.europa.eu/programmes/life_en) for programme details
• Review calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/?programmePeriod=2021-2027&programCcm2Id=43252476)
• Contact [CINEA](https://cinea.ec.europa.eu/programmes/life_en) (European Climate, Infrastructure and Environment Executive Agency) for support
• Consult your [National Contact Point](https://cinea.ec.europa.eu/programmes/life/life-national-contact-points_en) for local guidance
"""
            return eligibility_text

        # All eligible sub-programmes check
        elif query_type == "all_subprogrammes" and "eligible_subprogrammes" in result:
            eligible_subprogs = result.get("eligible_subprogrammes", [])
            total_eligible = result.get("total_eligible", len(eligible_subprogs))
            country = metadata.get("country", "Unknown")
            org_type = metadata.get("org_type", "Unknown")

            if total_eligible == 0:
                eligibility_text = f"""## LIFE Programme Eligibility Check for {org_type.replace("_", " ").title()} from {country}

**Eligibility**: ❌ No eligible sub-programmes found

This may be because:
- {country} is not a LIFE participating country
- The organization type ({org_type.replace("_", " ")}) has restrictions for LIFE sub-programmes

**Recommendations:**
- Check if your organization qualifies under a different category
- Consider partnership with eligible entities from EU Member States
- Contact CINEA for guidance on specific opportunities
"""
            else:
                eligibility_text = f"""## LIFE Programme Eligibility Check for {org_type.replace("_", " ").title()} from {country}

**Total Eligible Sub-programmes**: {total_eligible}

**Available Funding Options:**
"""
                for subprog in eligible_subprogs:
                    subprog_code = subprog.get("subprogramme", "")
                    subprog_name = subprog.get("subprogramme_name", "")
                    description = subprog.get("description", "")
                    funding_rate = subprog.get("funding_rate", "")
                    priorities = subprog.get("priorities", [])
                    warnings = subprog.get("warnings", [])
                    notes = subprog.get("notes", [])

                    eligibility_text += f"\n### {subprog_name} ({subprog_code}) ✅\n"
                    if description:
                        eligibility_text += f"{description}\n\n"
                    if funding_rate:
                        eligibility_text += f"- **EU Co-financing Rate**: {funding_rate}%\n"
                    if priorities:
                        eligibility_text += f"- **Priority Areas**: {', '.join(priorities[:4])}\n"
                    if warnings:
                        for w in warnings:
                            eligibility_text += f"- ⚠️ {w}\n"
                    if notes:
                        for n in notes:
                            eligibility_text += f"- {n}\n"

                # Add LIFE sub-programmes overview
                eligibility_text += "\n### LIFE Programme Sub-programmes Overview\n"
                eligibility_text += "The LIFE Programme supports environment and climate action through 4 sub-programmes:\n"
                eligibility_text += "- **NAT**: Nature and Biodiversity (75% co-financing)\n"
                eligibility_text += (
                    "- **ENV**: Circular Economy and Quality of Life (60% co-financing)\n"
                )
                eligibility_text += (
                    "- **CCA**: Climate Change Mitigation and Adaptation (60% co-financing)\n"
                )
                eligibility_text += "- **CET**: Clean Energy Transition (up to 95% co-financing)\n"

                # Add project types overview
                eligibility_text += "\n### LIFE Project Types\n"
                eligibility_text += (
                    "- **SAP**: Standard Action Projects (best practice, demonstration, pilot)\n"
                )
                eligibility_text += (
                    "- **SIP**: Strategic Integrated Projects (large-scale implementation)\n"
                )
                eligibility_text += (
                    "- **SNAP**: Strategic Nature Projects (nature/biodiversity implementation)\n"
                )
                eligibility_text += "- **TA**: Technical Assistance (preparation for SIP/SNAP)\n"
                eligibility_text += "- **OG**: Operating Grants (NGO support)\n"

                eligibility_text += """
---
🎯 **Next Steps:**
• Review the [LIFE Multi-Annual Work Programme](https://cinea.ec.europa.eu/programmes/life/life-work-programmes_en) for current priorities
• Check open calls on the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/?programmePeriod=2021-2027&programCcm2Id=43252476)
• Contact [CINEA](https://cinea.ec.europa.eu/programmes/life_en) for guidance and support
• Consult your [National Contact Point](https://cinea.ec.europa.eu/programmes/life/life-national-contact-points_en) for local advice
• For nature projects, check alignment with [Natura 2000](https://ec.europa.eu/environment/nature/natura2000/index_en.htm)
"""

            return eligibility_text

        return ""

    def _format_tool_result_summary(self, tool_name: str, result: Any) -> str:
        """Format a single tool result into a readable summary."""
        if not isinstance(result, dict):
            return f"{tool_name}: {str(result)[:500]}"

        # Handle project partner results
        if "partners" in result and "project_acronym" in result:
            acronym = result.get("project_acronym", "Unknown")
            partners = result.get("partners", [])
            coordinator = result.get("coordinator", "")
            parts = [f"Project {acronym}: {len(partners)} partners, Coordinator: {coordinator}"]
            for p in partners:
                parts.append(
                    f"  - {p.get('name', 'Unknown')} ({p.get('country', '')}) [{p.get('role', '')}]"
                )
            return "\n".join(parts)

        # Handle organization statistics results
        if "project_count" in result and "coordinator_count" in result and "name" in result:
            name = result.get("name", "Unknown")
            return (
                f"Organization: {name} ({result.get('country', '')})\n"
                f"- Total projects: {result['project_count']}\n"
                f"- As coordinator: {result['coordinator_count']}\n"
                f"- Total funding: €{result.get('total_funding', 0):,.0f}"
            )

        # Handle document search results
        if "documents" in result and isinstance(result["documents"], list):
            docs = result["documents"]
            if not docs:
                return f"{tool_name}: No documents found"

            # Extract actual content from documents
            content_parts = []
            for doc in docs[:8]:  # Increased from 3 to 8
                content = doc.get("content", "")
                source = doc.get("source", doc.get("title", "Unknown"))
                if content:
                    # Clean up the content
                    content = content.strip()[:800]  # Increased from 400
                    content_parts.append(f"From {source}: {content}")

            if content_parts:
                return f"Found {len(docs)} relevant document(s):\n" + "\n\n".join(content_parts)
            return f"{tool_name}: Found {len(docs)} documents (no content extracted)"

        # Handle funding call results
        if "calls" in result and isinstance(result["calls"], list):
            calls = result["calls"]
            if not calls:
                return f"{tool_name}: No funding calls found"
            return f"Found {len(calls)} funding call(s)"

        # Handle project results
        if "projects" in result and isinstance(result["projects"], list):
            projects = result["projects"]
            if not projects:
                return f"{tool_name}: No projects found"

            parts = [f"Found {len(projects)} project(s):"]
            for i, p in enumerate(projects[:10]):
                acronym = p.get("acronym", "Unknown")
                title = p.get("title", "")[:120]
                pid = p.get("id") or p.get("project_id", "")
                ec = p.get("ec_contribution") or p.get("ecMaxContribution") or 0
                coordinator_raw = p.get("coordinator_name") or p.get("coordinator", "")
                coordinator = (
                    coordinator_raw.get("name", str(coordinator_raw))
                    if isinstance(coordinator_raw, dict)
                    else str(coordinator_raw)
                )
                ec_str = f"€{float(ec) / 1_000_000:.1f}M" if ec else ""

                parts.append(f"\n**{i + 1}. {acronym}** (ID: {pid}) - {title}")
                if ec_str:
                    parts.append(f"   EC Contribution: {ec_str}")
                if coordinator:
                    parts.append(f"   Coordinator: {coordinator}")

                # Include partners if available
                partners = p.get("partners", [])
                if partners:
                    parts.append(f"   Partners ({len(partners)}):")
                    for partner in partners[:30]:
                        name = partner.get("name", "Unknown")
                        country = partner.get("country", "")
                        role = partner.get("role", "participant")
                        parts.append(f"   - {name} ({country}) [{role}]")

            return "\n".join(parts)

        # Handle call details
        if "call_id" in result or "topic_code" in result:
            call_id = result.get("call_id") or result.get("topic_code")
            title = result.get("title", "Unknown")
            if call_id and title:
                desc = result.get("description", "")[:200] if result.get("description") else ""
                return f"Call {call_id}: {title}\n{desc}" if desc else f"Call {call_id}: {title}"
            elif result.get("message"):
                return result["message"]

        # Handle budget benchmark results
        if "statistics" in result and "total_eu_contribution" in result.get("statistics", {}):
            stats = result["statistics"]
            contrib = stats.get("total_eu_contribution", {})
            consortium = stats.get("consortium_size", {})
            recs = result.get("recommendations", {})

            parts = [
                f"Budget Benchmark Analysis ({stats.get('projects_analyzed', 'N/A')} projects):"
            ]

            if contrib:
                avg = contrib.get("average", 0)
                median = contrib.get("median", 0)
                parts.append(
                    f"- EU Contribution: €{median / 1_000_000:.1f}M median, €{avg / 1_000_000:.1f}M average"
                )
                parts.append(
                    f"- Range: €{contrib.get('min', 0) / 1_000_000:.1f}M - €{contrib.get('max', 0) / 1_000_000:.1f}M"
                )

            if consortium:
                parts.append(
                    f"- Consortium Size: {consortium.get('median', 0):.0f} partners (avg: {consortium.get('average', 0):.1f})"
                )

            if recs:
                parts.append(f"- Recommended Budget: {recs.get('suggested_budget_range', 'N/A')}")
                parts.append(
                    f"- Recommended Partners: {recs.get('suggested_consortium_size', 'N/A')}"
                )

            return "\n".join(parts)

        # Handle consortium patterns results
        if "organization_type_distribution" in result and "consortium_size" in result:
            projects = result.get("projects_analyzed", "N/A")
            consortium = result.get("consortium_size", {})
            org_dist = result.get("organization_type_distribution", {})
            country_patterns = result.get("country_patterns", {})
            recs = result.get("recommendations", {})

            parts = [f"Consortium Patterns Analysis ({projects} projects):"]

            # Consortium size
            if consortium:
                parts.append(
                    f"- Consortium Size: {consortium.get('median', 0):.0f} partners (avg: {consortium.get('average', 0):.1f})"
                )
                parts.append(f"- Recommended: {consortium.get('recommended', 'N/A')}")

            # Org type distribution
            if org_dist:
                type_parts = []
                for org_type, data in sorted(
                    org_dist.items(), key=lambda x: x[1].get("percentage", 0), reverse=True
                )[:4]:
                    pct = data.get("percentage", 0)
                    type_parts.append(f"{org_type}: {pct:.0f}%")
                parts.append(f"- Organization Mix: {', '.join(type_parts)}")

            # Top countries
            top_countries = country_patterns.get("top_participating", [])[:5]
            if top_countries:
                countries = [c["country"] for c in top_countries]
                parts.append(f"- Top Countries: {', '.join(countries)}")

            # Geographic diversity
            geo = country_patterns.get("geographic_diversity", {})
            if geo:
                parts.append(f"- Avg Countries per Project: {geo.get('avg_countries', 'N/A')}")

            # Recommendations
            if recs.get("ideal_composition"):
                parts.append(f"- Ideal Mix: {'; '.join(recs['ideal_composition'][:3])}")

            return "\n".join(parts)

        # Handle partner discovery results
        if "experienced_partners" in result:
            partners = result.get("experienced_partners", [])
            total = result.get("total_found", 0)
            query = result.get("query_params", {})

            if not partners:
                return f"Partner Discovery: No organizations found matching '{query.get('topic_keywords', '')}'"

            # Use abbreviated keywords for header (first 60 chars) to save space
            keywords = query.get("topic_keywords", "")
            keywords_abbrev = keywords[:60] + "..." if len(keywords) > 60 else keywords
            parts = [f"Found {total} experienced partners for '{keywords_abbrev}':"]

            # Include ALL partners (up to 15) with compact format for observation
            # This ensures the agent sees all partners to present multiple in response
            for i, p in enumerate(partners[:15], 1):
                name = p.get("short_name") or p.get("name", "Unknown")
                country = p.get("country", "")
                org_type = p.get("type", "")
                track = p.get("track_record", {})
                relevant = track.get("relevant_projects", 0)
                coord = track.get("as_coordinator", 0)
                funding = track.get("funding_in_relevant", track.get("total_funding", 0))

                # Compact format: "1. NAME (CC, TYPE): Xp, Yc, €ZM"
                coord_str = f", {coord}c" if coord > 0 else ""
                funding_mil = funding / 1_000_000 if funding > 0 else 0
                funding_str = f", €{funding_mil:.1f}M" if funding > 0 else ""
                parts.append(
                    f"{i}. {name} ({country}, {org_type}): {relevant}p{coord_str}{funding_str}"
                )

            # Skip insights to save space - partners list is more important

            return "\n".join(parts)

        # Handle similar projects results - ENHANCED with full details
        if "similar_projects" in result and isinstance(result["similar_projects"], list):
            projects = result["similar_projects"]
            query_desc = result.get("query_description", "")
            matches = result.get("matches_found", len(projects))
            filters = result.get("filters_applied", {})

            if not projects:
                return f"## Similar Projects Search\n\nNo projects found matching: *{query_desc}*"

            parts = []
            parts.append("## Similar Funded Projects\n")
            parts.append(f"**Query:** {query_desc}")
            if filters:
                filter_str = ", ".join([f"{k}: {v}" for k, v in filters.items() if v])
                if filter_str:
                    parts.append(f"**Filters:** {filter_str}")
            parts.append(f"**Found:** {matches} similar projects\n")

            for i, p in enumerate(projects[:10], 1):
                acronym = p.get("acronym", "N/A")
                title = p.get("title", "N/A")
                score = p.get("similarity_score", 0)
                budget = p.get("eu_contribution", p.get("total_cost", 0))
                consortium = p.get("consortium", {})
                size = consortium.get("size", p.get("partner_count", 0))
                action_type = p.get("action_type", "N/A")
                objective = p.get("objective", "")
                start_date = p.get("start_date", "")
                end_date = p.get("end_date", "")
                coordinator = consortium.get("coordinator", {}).get("name", "")
                cluster = p.get("cluster", "")

                budget_str = f"€{budget / 1_000_000:.1f}M" if budget > 0 else "N/A"

                parts.append(f"### {i}. {acronym} [{score:.0%} match]")
                parts.append(f"**{title}**")
                parts.append(f"- Type: {action_type} | Budget: {budget_str} | Partners: {size}")
                if cluster:
                    parts.append(f"- Cluster: {cluster}")
                if start_date and end_date:
                    parts.append(f"- Duration: {start_date[:7]} to {end_date[:7]}")
                if coordinator:
                    parts.append(f"- Coordinator: {coordinator}")
                if objective:
                    # Show first 300 chars of objective
                    obj_preview = objective[:300] + "..." if len(objective) > 300 else objective
                    parts.append(f"- Objective: *{obj_preview}*")
                parts.append("")

            # Add insights
            insights = result.get("insights", [])
            if insights:
                parts.append("**Key Insights:**")
                for insight in insights[:5]:
                    parts.append(f"- {insight}")

            return "\n".join(parts)

        # Handle timeline generator results
        if "work_packages" in result and "deliverables" in result and "milestones" in result:
            wps = result.get("work_packages", [])
            deliverables = result.get("deliverables", [])
            milestones = result.get("milestones", [])
            params = result.get("parameters", {})
            _summary = result.get("summary", {})  # noqa: F841 - may be used in future
            gantt = result.get("gantt_data", {})

            parts = []
            parts.append("**Project Timeline Generated**")
            parts.append(f"- Duration: {params.get('duration_months', 36)} months")
            parts.append(f"- Action Type: {params.get('action_type', 'RIA')}")
            parts.append(f"- Partners: {params.get('num_partners', 8)}")
            parts.append(f"- Total Effort: {params.get('total_person_months', 0)} person-months")
            parts.append("")

            # Work Packages Summary
            parts.append("**Work Packages:**")
            for wp in wps:
                wp_num = wp.get("number", 0)
                title = wp.get("title", "")
                lead = wp.get("lead", "P1")
                start = wp.get("start_month", 1)
                end = wp.get("end_month", 36)
                effort = wp.get("effort_pms", 0)
                objective = wp.get("objective", "")

                parts.append(f"\n**WP{wp_num}: {title}** (Lead: {lead})")
                parts.append(f"  M{start}-M{end} | {effort} PMs")
                if objective:
                    parts.append(f"  *{objective[:100]}*")

                # Show tasks
                tasks = wp.get("tasks", [])
                if tasks:
                    parts.append(f"  Tasks: {'; '.join(tasks[:3])}")

            # Deliverables
            parts.append("")
            parts.append(f"**Deliverables ({len(deliverables)} total):**")
            for d in deliverables[:10]:  # Show first 10
                d_id = d.get("id", "D?")
                d_title = d.get("title", "")[:50]
                d_month = d.get("due_month", 0)
                d_type = d.get("type", "R")
                d_level = d.get("dissemination_level", "PU")
                parts.append(f"  {d_id}: {d_title} (M{d_month}, {d_type}, {d_level})")

            if len(deliverables) > 10:
                parts.append(f"  ... and {len(deliverables) - 10} more")

            # Milestones
            parts.append("")
            parts.append(f"**Milestones ({len(milestones)} total):**")
            for m in milestones:
                m_id = m.get("id", "MS?")
                m_title = m.get("title", "")
                m_month = m.get("due_month", 0)
                parts.append(f"  {m_id}: {m_title} (M{m_month})")

            # ASCII Gantt Chart
            ascii_chart = gantt.get("ascii_chart", "")
            if ascii_chart:
                parts.append("")
                parts.append("**Gantt Chart:**")
                parts.append("```")
                parts.append(ascii_chart)
                parts.append("```")

            # Dependencies
            dependencies = gantt.get("dependencies", [])
            if dependencies:
                parts.append("")
                parts.append("**WP Dependencies:**")
                for dep in dependencies[:5]:
                    parts.append(
                        f"  {dep.get('from')} → {dep.get('to')}: {dep.get('description', '')}"
                    )

            # Recommendations
            recommendations = result.get("recommendations", [])
            if recommendations:
                parts.append("")
                parts.append("**Recommendations:**")
                for rec in recommendations[:4]:
                    parts.append(f"  - {rec}")

            return "\n".join(parts)

        # Handle call history analysis results
        if "timeline" in result and "trends" in result:
            calls = result.get("calls_analyzed", 0)
            projects = result.get("projects_funded", 0)
            total_funding = result.get("total_funding_allocated", 0)
            trends = result.get("trends", {})

            parts = [f"Call History Analysis: {calls} calls, {projects} projects funded"]

            if total_funding > 0:
                parts.append(f"Total funding: €{total_funding / 1_000_000_000:.1f}B")

            # Trend info
            trend = trends.get("funding_trend", "unknown")
            growth = trends.get("year_over_year_funding_growth", 0)
            if trend != "insufficient_data":
                parts.append(f"Trend: {trend.replace('_', ' ')} ({growth:+.1f}% YoY)")

            # Timeline summary
            timeline = result.get("timeline", {})
            if timeline:
                years = sorted(timeline.keys(), reverse=True)[:3]
                for year in years:
                    data = timeline[year]
                    parts.append(
                        f"  {year}: {data.get('projects_funded', 0)} projects, €{data.get('total_funding', 0) / 1_000_000:.0f}M"
                    )

            # Top topics
            top_topics = result.get("top_funded_topics", [])[:3]
            if top_topics:
                parts.append("\nTop topics:")
                for t in top_topics:
                    parts.append(f"  - {t.get('topic', 'N/A')}: {t.get('projects', 0)} projects")

            # Recommendations
            recommendations = result.get("recommendations", [])[:2]
            if recommendations:
                parts.append(f"\nRecommendations: {'; '.join(recommendations)}")

            return "\n".join(parts)

        # Handle country statistics results
        if "country_code" in result and "eligibility" in result:
            country = result.get("country", result.get("country_code", "Unknown"))
            eligibility = result.get("eligibility", {})
            top_orgs = result.get("top_organizations", [])

            # Get participation history from eligibility
            participation = eligibility.get("participation_history", {})
            org_count = participation.get("organization_count", result.get("organization_count", 0))
            proj_count = participation.get("project_count", 0)
            total_funding = participation.get("total_funding_received", 0)

            # Build clear eligibility answer first
            is_eligible = eligibility.get("is_eligible", False)
            eligibility_status = eligibility.get("eligibility_status", "Unknown")

            parts = [f"Country: {country}"]
            parts.append(f"**Can participate in Horizon Europe: {'YES' if is_eligible else 'NO'}**")
            parts.append(f"- Status: {eligibility_status}")

            # Add notes if available
            notes = eligibility.get("notes", [])
            if notes:
                parts.append(f"- {notes[0]}")

            if proj_count > 0:
                parts.append("\nParticipation Statistics:")
                parts.append(f"- Organizations: {org_count:,}")
                parts.append(f"- Projects: {proj_count:,}")
                parts.append(f"- Total Funding: €{total_funding:,.0f}")

            if top_orgs:
                parts.append(f"\nTop {min(len(top_orgs), 10)} Organizations:")
                for org in top_orgs[:10]:
                    org_name = org.get("name", org.get("organization_name", "Unknown"))
                    org_projects = org.get("project_count", org.get("projects", 0))
                    org_funding = org.get("total_funding", org.get("funding", 0))
                    parts.append(f"- {org_name}: {org_projects} projects, €{org_funding:,.0f}")

            return "\n".join(parts)

        # Handle programme/cluster statistics results
        if "cluster_code" in result or ("programme" in result and "statistics" in result):
            programme = result.get("programme", result.get("cluster_code", "Unknown"))
            programme_type = result.get("programme_type", "")
            stats = result.get("statistics", {})
            # Ensure stats is a dict, not a list
            if isinstance(stats, list):
                stats = stats[0] if stats else {}
            budget = result.get("budget_details", {})
            # Ensure budget is a dict, not a list
            if isinstance(budget, list):
                budget = budget[0] if budget else {}

            parts = [f"Programme Statistics for {programme}:"]
            if programme_type:
                parts.append(f"({programme_type})")

            # Handle EIC/ERC/MSCA format with success_rates dict
            if "success_rates" in stats:
                success_rates = stats["success_rates"]
                if stats.get("description"):
                    parts.append(f"\n{stats['description']}")
                parts.append("\nSuccess Rates:")
                for key, value in success_rates.items():
                    if key != "note":
                        parts.append(f"- {key.replace('_', ' ').title()}: {value}")
                if success_rates.get("note"):
                    parts.append(f"\nNote: {success_rates['note']}")

                # Add funding info
                if "funding" in stats:
                    parts.append("\nFunding Available:")
                    for key, value in stats["funding"].items():
                        parts.append(f"- {key.replace('_', ' ').title()}: {value}")

                if stats.get("eligibility"):
                    parts.append(f"\nEligibility: {stats['eligibility']}")

                if stats.get("trl_range"):
                    parts.append(f"TRL Range: {stats['trl_range']}")

                # Add actionable Next Steps
                parts.append("\n---\n\n🎯 **Next Steps:**")
                parts.append(
                    "• Carefully review your innovation for market readiness (EIC) or scientific excellence (ERC)"
                )
                parts.append(
                    "• Study successful proposals in your domain via [CORDIS](https://cordis.europa.eu/)"
                )
                parts.append(
                    "• Consider working with a consultant or experienced coordinator to improve odds"
                )
                parts.append(
                    "• Check the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for current call details"
                )

            else:
                # Standard cluster statistics format
                if stats:
                    total_projects = stats.get("total_projects", stats.get("project_count", "N/A"))
                    total_funding = stats.get("total_funding", stats.get("total_budget", 0))
                    success_rate = stats.get("success_rate", "N/A")
                    avg_budget = stats.get("avg_project_budget", stats.get("average_funding", 0))

                    parts.append(
                        f"- Total Projects: {total_projects:,}"
                        if isinstance(total_projects, int)
                        else f"- Total Projects: {total_projects}"
                    )
                    # IMPORTANT: Clarify this is projects funded, not programme budget
                    parts.append(
                        f"- Total Funding Awarded to Projects: €{total_funding:,.0f} (Note: This is the sum of project awards in this area, NOT the overall Horizon Europe budget of €95.5 billion)"
                    )
                    parts.append(f"- Success Rate: {success_rate}%")
                    parts.append(f"- Average Project Budget: €{avg_budget:,.0f}")

                if budget:
                    parts.append("\nBudget Breakdown:")
                    parts.append(f"- Min Budget: €{budget.get('min_budget', 0):,.0f}")
                    parts.append(f"- Max Budget: €{budget.get('max_budget', 0):,.0f}")
                    parts.append(f"- Median Budget: €{budget.get('median_budget', 0):,.0f}")

                # Add actionable Next Steps for cluster statistics
                parts.append("\n---\n\n🎯 **Next Steps:**")
                parts.append(
                    "• Review open calls in this cluster on the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)"
                )
                parts.append(
                    "• Study similar funded projects in [CORDIS](https://cordis.europa.eu/) to understand successful approaches"
                )
                parts.append("• Connect with experienced partners or consultants in this domain")
                parts.append("• Consider starting as a partner before taking a coordinator role")

            return "\n".join(parts)

        # Handle error messages
        if "error" in result:
            return f"{tool_name}: Error - {result['error']}"

        if "message" in result:
            return f"{tool_name}: {result['message']}"

        # Default: truncated string representation
        return f"{tool_name}: {str(result)[:500]}"

    def _build_fallback_answer(self, plan: AgentPlan) -> str:
        """Build a fallback answer from collected information."""

        if not plan.reasoning_steps:
            return ""  # Return empty to trigger synthesis

        # Collect all tool results from steps (use unique keys for duplicate tool names)
        all_results = {}
        call_idx = 0
        for step in plan.reasoning_steps:
            for tc in step.tool_calls:
                if tc.success and tc.result:
                    key = tc.tool_name
                    if key in all_results:
                        key = f"{tc.tool_name}_{call_idx}"
                    all_results[key] = tc.result
                    call_idx += 1

        # If we have tool results, synthesize from them
        if all_results:
            return self._synthesize_from_results(plan.query, all_results)

        # Collect meaningful observations (skip raw tool results)
        meaningful_content = []

        for step in plan.reasoning_steps:
            if step.observation:
                obs = step.observation

                # Skip if it looks like raw JSON
                if obs.startswith("{") or obs.startswith("search_") or obs.startswith("get_"):
                    continue

                # Check if this is formatted document content
                if "Found " in obs and "relevant document" in obs:
                    # Extract the actual content from "From source: content" lines
                    lines = obs.split("\n")
                    for line in lines:
                        if line.startswith("From ") and ":" in line:
                            # Extract content after "From Source:"
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                content = parts[1].strip()
                                # Check content quality - skip truncated/malformed text
                                if self._is_quality_content(content):
                                    meaningful_content.append(content)
                elif self._is_quality_content(obs):
                    meaningful_content.append(obs)

        # Only return if we have quality content
        if meaningful_content:
            # Deduplicate similar content
            unique_content = self._deduplicate_content(meaningful_content)
            if unique_content:
                # Format as a proper answer
                intro = f"Based on the information I found about '{plan.query}':\n\n"
                formatted_content = []
                for _i, content in enumerate(unique_content[:5], 1):
                    if len(content) > 500:
                        content = content[:500] + "..."
                    formatted_content.append(f"{content}")
                return intro + "\n\n".join(formatted_content)

        # Return empty to trigger LLM synthesis
        return ""

    def _is_quality_content(self, text: str) -> bool:
        """Check if text is quality content suitable for display."""
        if not text or len(text) < 50:
            return False

        # Check for truncated/malformed text patterns
        bad_patterns = [
            # Truncated words at start
            text[:20].count("  ") > 2,  # Multiple spaces
            text.startswith("rmance"),  # Cut-off word
            text.startswith("tion"),
            text.startswith("ing "),
            # Raw data patterns
            "{'documents'" in text,
            '{"documents"' in text,
            "'content':" in text,
            "'score':" in text,
            # Meta/structural content
            "Table of Contents" in text,
            "Page " in text and " of " in text,
        ]

        if any(bad_patterns):
            return False

        # Check for reasonable word structure
        words = text.split()
        if len(words) < 10:
            return False

        # Check that content has actual sentences (periods, capitals)
        if "." not in text and "?" not in text:
            return False

        return True

    def _deduplicate_content(self, contents: list) -> list:
        """Remove duplicate or very similar content."""
        if not contents:
            return []

        unique = []
        for content in contents:
            # Check if this content is similar to any existing
            is_duplicate = False
            content_start = content[:100].lower()
            for existing in unique:
                existing_start = existing[:100].lower()
                if content_start == existing_start:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(content)

        return unique

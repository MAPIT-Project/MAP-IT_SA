"""
Tool executor methods for ToolAwareAgent.
Each method delegates to a dedicated tool module in app/services/tools/.
Extracted from tool_aware_agent.py for maintainability.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolExecutorsMixin:
    """Mixin providing tool execution implementations for ToolAwareAgent.

    All methods delegate to standalone tool modules in app/services/tools/.
    Only _tool_show_cached_projects contains inline logic (it depends on
    self._render_merged_project_list from ResponseSynthesizerMixin).
    """

    def _extract_cluster_param(self, params: dict) -> str | None:
        """
        Extract cluster parameter from tool params with fallback alternatives.
        LLM might use different names for the cluster parameter.
        """
        cluster = (
            params.get("cluster")
            or params.get("cluster_code")
            or params.get("cluster_id")
            or params.get("pillar")  # Sometimes LLM confuses pillar with cluster
        )
        if cluster:
            logger.debug(f"_extract_cluster_param: extracted '{cluster}' from params")
        return cluster

    # =========================================================================
    # Cached Projects (inline - depends on self._render_merged_project_list)
    # =========================================================================

    def _tool_show_cached_projects(self) -> dict[str, Any]:
        """Tool handler: show next page of cached project results."""
        if not self._conversation_id or not self._redis_client:
            return {"error": "No cached results available. Try searching for projects first."}

        try:
            key = f"merged_projects:{self._conversation_id}"
            cached = self._redis_client.get(key)
            if not cached:
                return {
                    "error": "No cached project results found. "
                    "Please search for projects first, then ask to see more."
                }

            merged_result = json.loads(cached)
            page_key = f"project_page:{self._conversation_id}"
            current_offset = int(self._redis_client.get(page_key) or 20)

            projects = merged_result["merged_projects"]
            display_limit = merged_result["display_limit"]

            if current_offset >= len(projects):
                return {
                    "message": (
                        f"All **{len(projects)}** matching projects from the previous search "
                        f"for *{merged_result['query_description']}* have already been shown."
                    ),
                    "all_shown": True,
                }

            # Render the next page
            rendered = self._render_merged_project_list(merged_result, offset=current_offset)

            # Advance the page offset
            new_offset = min(current_offset + display_limit, len(projects))
            self._redis_client.setex(page_key, 1800, str(new_offset))

            logger.info(
                f"📄 Serving cached page: projects {current_offset + 1}–{new_offset} "
                f"of {len(projects)} for conversation {self._conversation_id}"
            )

            return {
                "rendered_content": rendered,
                "page_start": current_offset + 1,
                "page_end": new_offset,
                "total_projects": len(projects),
                "remaining": len(projects) - new_offset,
            }

        except Exception as e:
            logger.warning(f"Failed to show cached projects: {e}")
            return {"error": f"Failed to retrieve cached results: {e}"}

    # =========================================================================
    # Programme Statistics & Comparison
    # =========================================================================

    async def _tool_get_programme_stats(self, params: dict) -> dict:
        """Get programme/cluster statistics from graph DB."""
        try:
            from ..tools.programme_statistics import get_programme_statistics_execute

            return await get_programme_statistics_execute(
                programme=params.get("programme", ""),
            )
        except Exception as e:
            logger.error(f"Programme stats error: {e}")
            return {"error": str(e)}

    async def _tool_compare_programmes(self, params: dict) -> dict:
        """Compare two programmes/clusters."""
        try:
            from ..tools.programme_statistics import compare_programmes_execute

            return await compare_programmes_execute(
                programme_a=params.get("programme_a", ""),
                programme_b=params.get("programme_b", ""),
            )
        except Exception as e:
            logger.error(f"Compare programmes error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Country Statistics
    # =========================================================================

    async def _tool_get_country_stats(self, params: dict) -> dict:
        """Get country statistics with graceful degradation."""
        try:
            from ..tools.country_statistics import get_country_statistics_execute

            return await get_country_statistics_execute(
                country=params.get("country", ""),
            )
        except Exception as e:
            logger.error(f"Country stats error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Document Search
    # =========================================================================

    async def _tool_search_documents(self, params: dict) -> dict:
        """Search documents using vector search with rich metadata for citations."""
        try:
            from ..tools.document_search import search_documents_execute

            return await search_documents_execute(
                query=params.get("query", ""),
                max_results=params.get("max_results", 15),
                document_type=params.get("document_type"),
            )
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # Call Search & Details
    # =========================================================================

    async def _tool_search_funding_calls(self, params: dict) -> dict:
        """Search funding calls."""
        try:
            from ..tools.call_search import search_funding_calls_execute

            return await search_funding_calls_execute(
                keywords=params.get("keywords", ""),
                status=params.get("status", "open"),
                year=params.get("year"),
                cluster=params.get("cluster"),
            )
        except Exception as e:
            logger.error(f"Funding calls search error: {e}")
            return {"error": str(e), "calls": []}

    async def _tool_get_call_details(self, params: dict) -> dict:
        """Get details for a specific call."""
        try:
            from ..tools.call_search import get_call_details_execute

            call_id = params.get("call_id", "")
            if not call_id:
                return {"error": "call_id is required"}

            return await get_call_details_execute(call_id=call_id)
        except Exception as e:
            logger.error(f"Get call details error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Project Search
    # =========================================================================

    async def _tool_search_projects(self, params: dict) -> dict:
        """Search CORDIS projects using LOCAL database."""
        try:
            from ..tools.project_search_executor import search_projects_execute

            user_query = (
                (self._current_query or "").lower() if hasattr(self, "_current_query") else ""
            )

            return await search_projects_execute(
                keywords=params.get("keywords", ""),
                country=params.get("country"),
                programme=params.get("programme"),
                sort_by=params.get("sort_by"),
                limit=params.get("limit", 100),
                user_query=user_query,
            )
        except Exception as e:
            logger.error(f"Project search error: {e}")
            return {"error": str(e), "projects": []}

    # =========================================================================
    # Project Details & Partners
    # =========================================================================

    async def _tool_get_project_details(self, params: dict) -> dict:
        """Get detailed information about a specific project by ID or acronym."""
        try:
            from ..tools.project_details import get_project_details_execute

            project_id = params.get("project_id", "")
            if not project_id:
                return {"error": "project_id is required", "project": None}

            return await get_project_details_execute(project_id=str(project_id))
        except Exception as e:
            logger.error(f"Get project details error: {e}")
            return {"error": str(e), "project": None}

    async def _tool_get_project_partners(self, params: dict) -> dict:
        """Get all partner organizations for a specific project."""
        try:
            from ..tools.project_details import get_project_partners_execute

            project_id = params.get("project_id", "")
            if not project_id:
                return {"error": "project_id is required", "partners": []}

            return await get_project_partners_execute(project_id=str(project_id))
        except Exception as e:
            logger.error(f"Get project partners error: {e}")
            return {"error": str(e), "partners": []}

    # =========================================================================
    # Project Discovery (Similar, Semantic, Cluster)
    # =========================================================================

    async def _tool_find_similar_projects(self, params: dict) -> dict:
        """Find projects similar to a given project."""
        try:
            from ..tools.project_discovery import find_similar_projects_execute

            project_id = params.get("project_id", "")
            if not project_id:
                return {"error": "project_id is required", "projects": []}

            return await find_similar_projects_execute(
                project_id=project_id,
                similarity_type=params.get("similarity_type", "topic"),
            )
        except Exception as e:
            logger.error(f"Similar projects search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_find_semantically_similar_projects(self, params: dict) -> dict:
        """Find semantically similar projects using vector embeddings."""
        try:
            from ..tools.project_discovery import find_semantically_similar_execute

            project_id = params.get("project_id", "")
            if not project_id:
                return {"error": "project_id is required", "projects": []}

            return await find_semantically_similar_execute(
                project_id=project_id,
                limit=params.get("limit", 10),
            )
        except Exception as e:
            logger.error(f"Semantic similarity search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_search_by_cluster(self, params: dict) -> dict:
        """Search projects in a specific cluster."""
        try:
            from ..tools.project_discovery import search_by_cluster_execute

            cluster = self._extract_cluster_param(params) or ""
            if not cluster:
                return {"error": "cluster parameter is required", "projects": []}

            return await search_by_cluster_execute(cluster=cluster)
        except Exception as e:
            logger.error(f"Cluster search error: {e}")
            return {"error": str(e), "projects": []}

    # =========================================================================
    # Organization Tools
    # =========================================================================

    async def _tool_find_organization_projects(self, params: dict) -> dict:
        """Find projects by organization."""
        try:
            from ..tools.organization_tools import find_organization_projects_execute

            org_name = params.get("organization_name", "")
            if not org_name:
                return {"error": "organization_name is required", "projects": []}

            return await find_organization_projects_execute(
                org_name=org_name,
                role=params.get("role"),
            )
        except Exception as e:
            logger.error(f"Organization projects search error: {e}")
            return {"error": str(e), "projects": []}

    async def _tool_get_organization_stats(self, params: dict) -> dict:
        """Get aggregate statistics for an organization."""
        try:
            from ..tools.organization_tools import get_organization_stats_execute

            org_name = params.get("organization_name", "")
            if not org_name:
                return {"error": "organization_name is required"}

            return await get_organization_stats_execute(org_name=org_name)
        except Exception as e:
            logger.error(f"Get organization stats error: {e}")
            return {"error": str(e)}

    async def _tool_get_collaboration_network(self, params: dict) -> dict:
        """Get collaboration network for an organization."""
        try:
            from ..tools.organization_tools import get_collaboration_network_execute

            org_name = params.get("organization_name", "")
            if not org_name:
                return {"error": "organization_name is required", "partners": []}

            return await get_collaboration_network_execute(org_name=org_name)
        except Exception as e:
            logger.error(f"Collaboration network error: {e}")
            return {"error": str(e), "partners": []}

    # =========================================================================
    # Budget & Consortium Tools (already delegating to app/services/tools/)
    # =========================================================================

    async def _tool_get_budget_benchmark(self, params: dict) -> dict:
        """Get budget benchmarks from funded Horizon Europe projects."""
        try:
            from ..tools.budget_benchmark import BudgetBenchmarkTool

            logger.info(f"_tool_get_budget_benchmark called with params: {params}")
            cluster_param = self._extract_cluster_param(params)
            logger.info(f"_tool_get_budget_benchmark: cluster param = {cluster_param!r}")

            tool = BudgetBenchmarkTool()
            result = tool.get_benchmark(
                cluster=cluster_param,
                action_type=params.get("action_type"),
                topic_keywords=params.get("topic_keywords"),
                year=params.get("year"),
            )

            return result

        except Exception as e:
            logger.error(f"Budget benchmark error: {e}")
            return {"error": str(e)}

    async def _tool_get_consortium_patterns(self, params: dict) -> dict:
        """Get consortium composition patterns from funded projects."""
        try:
            from ..tools.consortium_patterns import ConsortiumPatternsTool

            cluster_param = self._extract_cluster_param(params)

            tool = ConsortiumPatternsTool()
            result = tool.get_patterns(
                cluster=cluster_param,
                action_type=params.get("action_type"),
                topic_keywords=params.get("topic_keywords"),
                min_projects=params.get("min_projects", 10),
            )

            return result

        except Exception as e:
            logger.error(f"Consortium patterns error: {e}")
            return {"error": str(e)}

    async def _tool_analyze_geographic_diversification(self, params: dict) -> dict:
        """Analyze geographic diversification of country partners by country groups."""
        try:
            from ..tools.consortium_patterns import GeographicDiversificationTool

            cluster_param = self._extract_cluster_param(params)

            tool = GeographicDiversificationTool()
            result = tool.analyze_geographic_diversification(
                cluster=cluster_param,
                country_groups=params.get("country_groups"),
                exclude_widening=params.get("exclude_widening", True),
                min_partners=params.get("min_partners", 3),
            )

            return result

        except Exception as e:
            logger.error(f"Geographic diversification error: {e}")
            return {"error": str(e)}

    async def _tool_find_experienced_partners(self, params: dict) -> dict:
        """Find experienced partners for consortium building."""
        try:
            from ..tools.partner_discovery import PartnerDiscoveryTool

            cluster_param = self._extract_cluster_param(params)

            tool = PartnerDiscoveryTool()
            result = tool.find_partners(
                topic_keywords=params.get("topic_keywords", params.get("keywords", "")),
                country=params.get("country"),
                organization_type=params.get("organization_type"),
                cluster=cluster_param,
                min_projects=params.get("min_projects", 2),
                role_filter=params.get("role_filter"),
                limit=params.get("limit", 20),
            )

            return result

        except Exception as e:
            logger.error(f"Partner discovery error: {e}")
            return {"error": str(e)}

    async def _tool_get_similar_funded_projects(self, params: dict) -> dict:
        """Find funded projects semantically similar to a description."""
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

            from ..tools.similar_projects import SimilarProjectsTool

            cluster_param = self._extract_cluster_param(params)

            tool = SimilarProjectsTool()
            fetch_limit = max(params.get("limit", 100), 100)

            def _execute():
                return tool.find_similar(
                    description=params.get("description", ""),
                    cluster=cluster_param,
                    action_type=params.get("action_type"),
                    min_budget=params.get("min_budget"),
                    max_budget=params.get("max_budget"),
                    year_from=params.get("year_from"),
                    limit=fetch_limit,
                    similarity_threshold=params.get("similarity_threshold", 0.3),
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_execute)
                try:
                    result = future.result(timeout=60)
                    return result
                except FuturesTimeoutError:
                    logger.warning("Similar projects tool timed out at agent level (60s)")
                    return tool._get_keyword_fallback(
                        description=params.get("description", ""),
                        cluster=cluster_param,
                        action_type=params.get("action_type"),
                        limit=fetch_limit,
                        fallback_reason="agent_level_timeout",
                    )

        except Exception as e:
            logger.error(f"Similar projects error: {e}")
            return {
                "success": False,
                "tool_name": "get_similar_funded_projects",
                "error": str(e),
                "message": "Search failed. Please try again with different parameters.",
                "metadata": {"degraded": True, "fallback_reason": f"error: {type(e).__name__}"},
            }

    async def _tool_analyze_call_history(self, params: dict) -> dict:
        """Analyze historical funding patterns for Horizon Europe topics."""
        try:
            from ..tools.call_history import CallHistoryTool

            cluster_param = self._extract_cluster_param(params)

            tool = CallHistoryTool()
            result = tool.analyze_history(
                topic_pattern=params.get("topic_pattern"),
                cluster=cluster_param,
                keywords=params.get("keywords"),
                year_from=params.get("year_from"),
                year_to=params.get("year_to"),
                action_types=params.get("action_types"),
                include_projects=params.get("include_projects", True),
                expand_scope=params.get("expand_scope", False),
                limit=params.get("limit", 50),
            )

            return result

        except Exception as e:
            logger.error(f"Call history analysis error: {e}")
            return {"error": str(e)}

    async def _tool_calculate_budget(self, params: dict) -> dict:
        """Calculate budget breakdown for a Horizon Europe proposal."""
        try:
            from ..tools.budget_calculator import BudgetCalculatorTool

            tool = BudgetCalculatorTool()
            result = tool.calculate_budget(
                action_type=params.get("action_type", "RIA"),
                duration_months=params.get("duration_months", 36),
                num_partners=params.get("num_partners", 8),
                total_person_months=params.get("total_person_months"),
                target_budget=params.get("target_budget"),
                countries=params.get("countries"),
                include_breakdown=params.get("include_breakdown", True),
            )

            return result

        except Exception as e:
            logger.error(f"Budget calculator error: {e}")
            return {"error": str(e)}

    async def _tool_generate_timeline(self, params: dict) -> dict:
        """Generate project timeline with work packages, deliverables, and milestones."""
        try:
            from ..tools.timeline_generator import TimelineGeneratorTool

            tool = TimelineGeneratorTool()
            result = tool.generate_timeline(
                action_type=params.get("action_type", "RIA"),
                duration_months=params.get("duration_months", 36),
                num_partners=params.get("num_partners", 8),
                total_person_months=params.get("total_person_months", 300),
                project_title=params.get("project_title", "Project"),
                custom_wps=params.get("custom_wps"),
                start_date=params.get("start_date"),
            )

            return result

        except Exception as e:
            logger.error(f"Timeline generator error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Multi-Programme Tools
    # =========================================================================

    async def _tool_search_all_programmes(self, params: dict) -> dict:
        """Search across all EU funding programmes."""
        try:
            from ..tools.multi_programme_search import search_all_programmes_execute

            result = search_all_programmes_execute(
                keywords=params.get("keywords", ""),
                programmes=params.get("programmes"),
                status=params.get("status"),
                year=params.get("year"),
                action_type=params.get("action_type"),
                limit=params.get("limit", 20),
                include_closed=params.get("include_closed", False),
            )

            return result

        except Exception as e:
            logger.error(f"Multi-programme search error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_recommend_programmes(self, params: dict) -> dict:
        """Recommend EU funding programmes based on project/activity description."""
        try:
            from ..tools.multi_programme_search import get_programme_recommendations_execute

            result = get_programme_recommendations_execute(
                description=params.get("description", ""),
                organization_type=params.get("organization_type"),
                sector=params.get("sector"),
            )

            return result

        except Exception as e:
            logger.error(f"Programme recommendations error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_get_programme_info(self, params: dict) -> dict:
        """Get detailed information about EU funding programmes."""
        try:
            from ..tools.multi_programme_search import get_programme_info_execute

            result = get_programme_info_execute(
                programme=params.get("programme"),
            )

            return result

        except Exception as e:
            logger.error(f"Programme info error: {e}")
            return {"error": str(e), "success": False}

    # =========================================================================
    # Proposal Quality Scoring
    # =========================================================================

    async def _tool_score_proposal_section(self, params: dict) -> dict:
        """Score a proposal section using EU Horizon Europe evaluation criteria."""
        try:
            from ..tools.proposal_quality_scorer import score_proposal_section_execute

            result = await score_proposal_section_execute(
                content=params.get("content", ""),
                section_type=params.get("section_type", "excellence"),
                section_id=params.get("section_id"),
                action_type=params.get("action_type", "RIA"),
                call_id=params.get("call_id"),
            )

            return result

        except Exception as e:
            logger.error(f"Proposal section scoring error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_score_full_proposal(self, params: dict) -> dict:
        """Score a complete proposal with all three main sections."""
        try:
            from ..tools.proposal_quality_scorer import score_full_proposal_execute

            result = await score_full_proposal_execute(
                excellence_content=params.get("excellence_content", ""),
                impact_content=params.get("impact_content", ""),
                implementation_content=params.get("implementation_content", ""),
                action_type=params.get("action_type", "RIA"),
                call_id=params.get("call_id"),
            )

            return result

        except Exception as e:
            logger.error(f"Full proposal scoring error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_quick_quality_check(self, params: dict) -> dict:
        """Quick quality check for draft proposal text."""
        try:
            from ..tools.proposal_quality_scorer import quick_quality_check_execute

            result = await quick_quality_check_execute(
                text=params.get("text", ""),
                context=params.get("context", "general"),
            )

            return result

        except Exception as e:
            logger.error(f"Quick quality check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_validate_budget(self, params: dict) -> dict:
        """Validate proposal budget against EU Horizon Europe funding rules."""
        try:
            from ..tools.budget_validator import validate_budget_execute

            result = validate_budget_execute(
                total_cost=params.get("total_cost", 0),
                eu_contribution=params.get("eu_contribution", 0),
                action_type=params.get("action_type", "RIA"),
                duration_months=params.get("duration_months", 36),
                num_partners=params.get("num_partners", 3),
                cost_breakdown=params.get("cost_breakdown"),
                consortium=params.get("consortium"),
                call_budget_cap=params.get("call_budget_cap"),
            )

            return result

        except Exception as e:
            logger.error(f"Budget validation error: {e}")
            return {"error": str(e), "success": False}

    # =========================================================================
    # Erasmus+ Tools
    # =========================================================================

    async def _tool_check_erasmus_eligibility(self, params: dict) -> dict:
        """Check Erasmus+ eligibility for an organization."""
        try:
            from ..tools.erasmus_eligibility import check_erasmus_eligibility_execute

            result = await check_erasmus_eligibility_execute(
                org_type=params.get("org_type", "HEI"),
                country=params.get("country", "Germany"),
                action_type=params.get("action_type"),
                has_eche=params.get("has_eche", False),
                is_coordinator=params.get("is_coordinator", True),
            )

            return result

        except Exception as e:
            logger.error(f"Erasmus+ eligibility check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_calculate_erasmus_budget(self, params: dict) -> dict:
        """Calculate Erasmus+ lump sum budget."""
        try:
            from ..tools.erasmus_budget_calculator import calculate_erasmus_budget_execute

            # Handle alternative parameter names LLMs might use
            num_participants = params.get("num_participants") or params.get("participants", 10)
            num_partners = params.get("num_partners") or params.get("partners", 3)

            # Get action type to determine if it's a mobility action
            action_type = params.get("action_type", "partnership")
            action_upper = action_type.upper()
            mobility_keywords = [
                "MOBILITY",
                "KA1",
                "STUDENT",
                "STAFF",
                "TRAINEE",
                "YOUTH",
                "VET_MOBILITY",
                "HED_MOBILITY",
                "KA1-HED",
                "KA1-VET",
            ]
            is_mobility = any(kw in action_upper for kw in mobility_keywords)

            # Handle duration conversion for mobility actions
            duration_days = params.get("duration_days", 14)
            duration_months = params.get("duration_months") or params.get("duration", 24)

            if is_mobility:
                if "duration_days" not in params and (
                    "duration_months" in params or "duration" in params
                ):
                    duration_days = int(duration_months) * 30
                elif "duration_days" not in params and "duration_months" not in params:
                    duration_days = 14

            result = await calculate_erasmus_budget_execute(
                action_type=action_type,
                num_participants=int(num_participants),
                duration_days=int(duration_days),
                duration_months=int(duration_months) if duration_months else 24,
                num_partners=int(num_partners),
                destination_country=params.get("destination_country", "Germany"),
                origin_country=params.get("origin_country", "Spain"),
                partnership_type=params.get("partnership_type", "cooperation"),
                distance_band=params.get("distance_band", "500-1999km"),
                green_travel=params.get("green_travel", False),
                target_budget=params.get("target_budget"),
            )

            return result

        except Exception as e:
            logger.error(f"Erasmus+ budget calculation error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_search_erasmus_templates(self, params: dict) -> dict:
        """Search Erasmus+ Programme Guide for application guidance."""
        try:
            from ..tools.erasmus_template_search import search_erasmus_templates_execute

            result = await search_erasmus_templates_execute(
                query=params.get("query", ""),
                key_action=params.get("key_action"),
                sector=params.get("sector"),
                document_type=params.get("document_type"),
                top_k=params.get("top_k", 5),
            )

            return result

        except Exception as e:
            logger.error(f"Erasmus+ template search error: {e}")
            return {"error": str(e), "success": False}

    # =========================================================================
    # Creative Europe Tools
    # =========================================================================

    async def _tool_check_creative_europe_eligibility(self, params: dict) -> dict:
        """Check Creative Europe eligibility for an organization."""
        try:
            from ..tools.creative_europe_eligibility import (
                check_creative_europe_eligibility_execute,
            )

            result = await check_creative_europe_eligibility_execute(
                org_type=params.get("org_type", "CULTURAL_ORG"),
                country=params.get("country", "Germany"),
                action_type=params.get("action_type"),
                strand=params.get("strand"),
                is_coordinator=params.get("is_coordinator", True),
            )

            return result

        except Exception as e:
            logger.error(f"Creative Europe eligibility check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_calculate_creative_europe_budget(self, params: dict) -> dict:
        """Calculate Creative Europe grant budget."""
        try:
            from ..tools.creative_europe_budget_calculator import (
                calculate_creative_europe_budget_execute,
            )

            result = await calculate_creative_europe_budget_execute(
                action_type=params.get("action_type", "COOP-SMALL"),
                requested_amount=params.get("requested_amount"),
                project_scale=params.get("project_scale", "medium"),
                num_partners=params.get("num_partners", 3),
                duration_months=params.get("duration_months"),
                strand=params.get("strand"),
            )

            return result

        except Exception as e:
            logger.error(f"Creative Europe budget calculation error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_search_creative_europe_templates(self, params: dict) -> dict:
        """Search Creative Europe documents for application guidance."""
        try:
            from ..tools.creative_europe_template_search import (
                search_creative_europe_templates_execute,
            )

            result = await search_creative_europe_templates_execute(
                query=params.get("query", ""),
                strand=params.get("strand"),
                action_type=params.get("action_type"),
                topic=params.get("topic"),
                top_k=params.get("top_k", 5),
            )

            return result

        except Exception as e:
            logger.error(f"Creative Europe template search error: {e}")
            return {"error": str(e), "success": False}

    # =========================================================================
    # EU4Health Tools
    # =========================================================================

    async def _tool_check_eu4health_eligibility(self, params: dict) -> dict:
        """Check EU4Health eligibility for an organization."""
        try:
            from ..tools.eu4health_eligibility import check_eu4health_eligibility_execute

            result = await check_eu4health_eligibility_execute(
                org_type=params.get("org_type", "HEALTHCARE_PROVIDER"),
                country=params.get("country", "Germany"),
                action_type=params.get("action_type"),
                strand=params.get("strand"),
            )

            return result

        except Exception as e:
            logger.error(f"EU4Health eligibility check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_search_eu4health_templates(self, params: dict) -> dict:
        """Search EU4Health documents for application guidance."""
        try:
            from ..tools.eu4health_template_search import (
                search_eu4health_templates_execute,
            )

            result = await search_eu4health_templates_execute(
                query=params.get("query", ""),
                strand=params.get("strand"),
                action_type=params.get("action_type"),
                topic=params.get("topic"),
                top_k=params.get("top_k", 5),
            )

            return result

        except Exception as e:
            logger.error(f"EU4Health template search error: {e}")
            return {"error": str(e), "success": False}

    # =========================================================================
    # Digital Europe Tools
    # =========================================================================

    async def _tool_check_digital_europe_eligibility(self, params: dict) -> dict:
        """Check Digital Europe eligibility for an organization."""
        try:
            from ..tools.digital_europe_eligibility import (
                check_digital_europe_eligibility_execute,
            )

            result = await check_digital_europe_eligibility_execute(
                org_type=params.get("org_type", "SME"),
                country=params.get("country", "Germany"),
                objective=params.get("objective"),
                action_type=params.get("action_type"),
            )

            return result

        except Exception as e:
            logger.error(f"Digital Europe eligibility check error: {e}")
            return {"error": str(e), "success": False}

    # =========================================================================
    # LIFE Programme Tools
    # =========================================================================

    async def _tool_check_life_eligibility(self, params: dict) -> dict:
        """Check LIFE Programme eligibility for an organization."""
        try:
            from ..tools.life_eligibility import check_life_eligibility_execute

            result = await check_life_eligibility_execute(
                org_type=params.get("org_type", "NGO"),
                country=params.get("country", "Germany"),
                subprogramme=params.get("subprogramme"),
                project_type=params.get("project_type"),
            )

            return result

        except Exception as e:
            logger.error(f"LIFE eligibility check error: {e}")
            return {"error": str(e), "success": False}

    async def _tool_search_life_templates(self, params: dict) -> dict:
        """Search LIFE Programme documents for application guidance."""
        try:
            from ..tools.life_template_search import search_life_templates_execute

            result = await search_life_templates_execute(
                query=params.get("query", ""),
                subprogramme=params.get("subprogramme"),
                section=params.get("section"),
                top_k=params.get("top_k", 5),
            )

            return result

        except Exception as e:
            logger.error(f"LIFE template search error: {e}")
            return {"error": str(e), "success": False}

"""
Query type detection methods for ToolAwareAgent.
Detects query patterns to provide tool hints and pre-routing guidance.
Extracted from tool_aware_agent.py for maintainability.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class QueryDetectorsMixin:
    """Mixin providing query type detection methods for ToolAwareAgent."""

    def _detect_query_type_for_tool_selection(
        self, query: str, context: str = ""
    ) -> dict[str, Any] | None:
        """Detect query type and return appropriate tool configuration.

        Returns None if no special handling needed (falls through to default behavior).
        """
        query_lower = query.lower()

        # FIRST: Check for PERSONALIZED CALL RECOMMENDATION queries
        # These use accumulated context (org type, sector, country) to search for calls
        personalized_result = self._detect_personalized_call_query(query, context)
        if personalized_result:
            return personalized_result

        # Check for STRATEGIC PLANNING / FUNDING STRATEGY queries
        # These are multi-year planning queries that benefit from programme recommendations
        strategic_result = self._detect_strategic_planning_query(query, context)
        if strategic_result:
            return strategic_result

        # Check for HISTORICAL PROGRAMME queries (H2020, FP7, FP6, etc.)
        # These are questions about outdated/closed programmes that need redirection to current options
        # e.g., "Tell me about H2020 calls", "What about FP7?", "Can I apply to Horizon 2020?"
        # IMPORTANT: Must come early to catch historical references before other patterns
        historical_result = self._detect_historical_programme_query(query, context)
        if historical_result:
            return historical_result

        # Check for AMBIGUOUS PROGRAMME queries (Innovation Fund, etc.)
        # These are questions about programmes with ambiguous names that could refer to multiple things
        # e.g., "Tell me about the innovation fund", "The EU one", "The one for climate"
        # IMPORTANT: Must come early to handle disambiguation properly
        ambiguous_result = self._detect_ambiguous_programme_query(query, context)
        if ambiguous_result:
            return ambiguous_result

        # Check for WORK PROGRAMME CONTENT queries
        # These are questions about work programme document content (topics, priorities, structure)
        # e.g., "What topics are in the Horizon Europe digital work programme?"
        # e.g., "What are the 2025 work programme priorities for Cluster 5?"
        # IMPORTANT: Must come BEFORE call search patterns to route to document search
        work_programme_result = self._detect_work_programme_content_query(query, context)
        if work_programme_result:
            return work_programme_result

        # Check for OUT-OF-SCOPE queries (non-EU funding programmes)
        # These are questions about NSF, UKRI, EPSRC, NIH, and other non-EU programmes
        # e.g., "Tell me about NSF grants", "What about UK Research Council?",
        # "How does Horizon Europe compare to NSF?", "Global equivalents to Horizon Europe?"
        # IMPORTANT: Must come early to prevent these from matching other patterns
        out_of_scope_result = self._detect_out_of_scope_query(query, context)
        if out_of_scope_result:
            return out_of_scope_result

        # Check for CAPACITY BUILDING / NEWCOMER GUIDANCE queries
        # These are questions from organizations new to EU funding about getting started
        capacity_result = self._detect_capacity_building_query(query, context)
        if capacity_result:
            return capacity_result

        # Check for APPLICATION PROCESS queries
        # These are questions about how to apply for EU funding programmes
        # e.g., "How do I apply for Horizon Europe?", "What's the application process?"
        # IMPORTANT: Must provide actionable step-by-step guidance with NCP referral
        application_process_result = self._detect_application_process_query(query, context)
        if application_process_result:
            return application_process_result

        # Check for EIC ACCELERATOR ELIGIBILITY queries (multi-part questions)
        # These are questions about EIC Accelerator eligibility, deadlines, and budget
        # e.g., "Am I eligible for EIC Accelerator? What's the deadline? What budget?"
        # "Can an SME from Netherlands apply for EIC Accelerator?"
        # IMPORTANT: Must come BEFORE EIC risk assessment to catch eligibility questions first
        eic_accelerator_eligibility_result = self._detect_eic_accelerator_eligibility_query(
            query, context
        )
        if eic_accelerator_eligibility_result:
            return eic_accelerator_eligibility_result

        # Check for EIC ACCELERATOR RISK ASSESSMENT queries
        # These are questions about EIC risks, interview stage, improving success odds
        eic_risk_result = self._detect_eic_risk_assessment_query(query, context)
        if eic_risk_result:
            return eic_risk_result

        # Check for FUNDING TYPE EXPLANATION queries
        # These are questions about action types (RIA, IA, CSA, MSCA, EIC Pathfinder)
        # and their characteristics, comparisons, and which provides most freedom
        funding_type_result = self._detect_funding_type_query(query, context)
        if funding_type_result:
            return funding_type_result

        # Check for ERC GRANT AMOUNT queries (Scenario 061: Source Attribution)
        # These are questions about ERC grant budgets/amounts with source attribution
        # e.g., "What are the ERC grant amounts?", "How much funding does ERC provide?"
        # IMPORTANT: Responses must include source attribution (erc.europa.eu)
        erc_grant_amount_result = self._detect_erc_grant_amount_query(query, context)
        if erc_grant_amount_result:
            return erc_grant_amount_result

        # Check for SIMPLE PROGRAMME OVERVIEW queries
        # These are basic questions about EU funding programmes (Horizon Europe, Erasmus+, etc.)
        # that can be answered from built-in knowledge without tool calls
        # e.g., "What is Horizon Europe?", "Tell me about Erasmus+", "Explain LIFE programme"
        # IMPORTANT: Must be fast (<2s) for simple FAQ queries to meet performance targets
        simple_programme_result = self._detect_simple_programme_overview_query(query, context)
        if simple_programme_result:
            return simple_programme_result

        # Check for ASSOCIATED COUNTRY ELIGIBILITY queries (Turkey, Switzerland, etc.)
        # These are questions about coordinator/partner eligibility for associated countries
        # e.g., "Can a Turkish university coordinate?", "What about defense topics?"
        # IMPORTANT: This must come BEFORE timeline comparison to prevent false matches
        associated_country_result = self._detect_associated_country_eligibility_query(
            query, context
        )
        if associated_country_result:
            return associated_country_result

        # Check for ERASMUS+ PROGRAMME GUIDE CONTENT queries
        # These are questions about Erasmus+ Programme Guide content (quality criteria,
        # evaluation criteria, award criteria, application requirements, programme rules)
        # e.g., "What are the Erasmus+ quality criteria?", "How are applications evaluated?",
        # "What are the award criteria for Erasmus+?", "What does the Programme Guide say about..."
        # IMPORTANT: Must come BEFORE erasmus_accreditation to route to document search
        erasmus_guide_result = self._detect_erasmus_programme_guide_query(query, context)
        if erasmus_guide_result:
            return erasmus_guide_result

        # Check for ERASMUS+ ACCREDITATION queries
        # These are questions about Erasmus+ accreditation vs short-term projects,
        # accreditation benefits, timeline, KA1 without accreditation, and strategic advice
        # e.g., "Should we get Erasmus accreditation?", "What are the benefits?",
        # "How long does accreditation last?", "Can we apply without accreditation?"
        # IMPORTANT: Must come BEFORE erasmus_budget to prevent "rate" in "strategic" matching
        erasmus_accreditation_result = self._detect_erasmus_accreditation_query(query, context)
        if erasmus_accreditation_result:
            return erasmus_accreditation_result

        # Check for ERASMUS+ ACTION SELECTION queries
        # These are questions about Erasmus+ Key Actions (KA1, KA2, KA3), sector-specific options,
        # mobility programmes, VET partnerships, curriculum development, and action combination strategy
        # e.g., "What Erasmus+ actions are there?", "VET mobility options?", "KA1 + KA2 strategy?"
        # IMPORTANT: Must come BEFORE SME eligibility to prevent false matches on "can we still"
        erasmus_action_result = self._detect_erasmus_action_query(query, context)
        if erasmus_action_result:
            return erasmus_action_result

        # Check for ERASMUS+ BUDGET CALCULATION queries
        # These are questions about Erasmus+ funding, unit costs, travel bands, individual support,
        # staff mobility funding, and inclusion support
        # e.g., "How does Erasmus+ fund student mobility?", "What are individual support rates?",
        # "How are travel costs calculated?", "What is inclusion support?"
        # IMPORTANT: Must come AFTER accreditation to avoid "rate" in "strategic" false matches
        erasmus_budget_result = self._detect_erasmus_budget_query(query, context)
        if erasmus_budget_result:
            return erasmus_budget_result

        # Check for CREATIVE EUROPE ELIGIBILITY queries
        # These are questions about Creative Europe eligibility for cultural organizations
        # e.g., "Can a theater company apply for Creative Europe?", "Is a museum eligible?"
        # "Can a small theater company from Italy apply for Creative Europe funding?"
        # IMPORTANT: Must come BEFORE cooperation/media queries to catch general eligibility
        ce_eligibility_result = self._detect_creative_europe_eligibility_query(query, context)
        if ce_eligibility_result:
            return ce_eligibility_result

        # Check for EU4HEALTH ELIGIBILITY queries
        # e.g., "What EU4Health funding options are available for a hospital consortium?"
        # "Can a public health body participate in Joint Actions?"
        # "Is a hospital eligible for EU4Health grants?"
        # IMPORTANT: Must catch EU4Health eligibility before general health queries
        eu4health_eligibility_result = self._detect_eu4health_eligibility_query(query, context)
        if eu4health_eligibility_result:
            return eu4health_eligibility_result

        # Check for DIGITAL EUROPE ELIGIBILITY queries
        # e.g., "Can a cybersecurity startup apply to Digital Europe?"
        # "Is an SME eligible for Digital Europe AI funding?"
        # "What Digital Europe opportunities are available for an EDIH?"
        # IMPORTANT: Must catch Digital Europe eligibility before general digital queries
        digital_europe_eligibility_result = self._detect_digital_europe_eligibility_query(
            query, context
        )
        if digital_europe_eligibility_result:
            return digital_europe_eligibility_result

        # Check for LIFE PROGRAMME BUDGET queries
        # e.g., "What budget range for a LIFE climate adaptation project?"
        # "How much funding for LIFE nature project?"
        # "What is the typical LIFE project budget?"
        # IMPORTANT: Must catch LIFE budget queries BEFORE eligibility to prioritize budget-specific answers
        life_budget_result = self._detect_life_budget_query(query, context)
        if life_budget_result:
            return life_budget_result

        # Check for LIFE PROGRAMME ELIGIBILITY queries
        # e.g., "What LIFE programme options exist for biodiversity conservation NGO?"
        # "Can an environmental NGO apply for LIFE Nature funding?"
        # "Is my organization eligible for LIFE climate action projects?"
        # IMPORTANT: Must catch LIFE eligibility before general environment/climate queries
        life_eligibility_result = self._detect_life_eligibility_query(query, context)
        if life_eligibility_result:
            return life_eligibility_result

        # Check for DIGITAL EUROPE vs HORIZON EUROPE COMPARISON queries
        # e.g., "Should I apply to Digital Europe or Horizon Europe for an AI project?"
        # "Compare Digital Europe and Horizon Europe for deployment projects"
        # "What's the difference between Digital Europe and Horizon Europe?"
        # IMPORTANT: Must come AFTER eligibility check, BEFORE EU4Health
        digital_europe_horizon_comparison_result = (
            self._detect_digital_europe_vs_horizon_comparison_query(query, context)
        )
        if digital_europe_horizon_comparison_result:
            return digital_europe_horizon_comparison_result

        # Check for EU4HEALTH TOPICS/PRIORITIES queries
        # e.g., "What EU4Health priorities focus on cancer?"
        # "Tell me about EU4Health disease prevention activities"
        # "What is Europe's Beating Cancer Plan under EU4Health?"
        # IMPORTANT: Must come AFTER eligibility check to prioritize eligibility questions
        eu4health_topics_result = self._detect_eu4health_topics_query(query, context)
        if eu4health_topics_result:
            return eu4health_topics_result

        # Check for CREATIVE EUROPE CALL SEARCH queries
        # These are explicit requests to find/search/list open or upcoming Creative Europe calls
        # e.g., "Find open Creative Europe MEDIA calls for film distribution"
        # e.g., "Show me upcoming Creative Europe calls", "What CREA calls are open?"
        # IMPORTANT: Must come BEFORE cooperation/media guidance to prioritize actual search
        ce_call_search_result = self._detect_creative_europe_call_search_query(query, context)
        if ce_call_search_result:
            return ce_call_search_result

        # Check for CREATIVE EUROPE COOPERATION PROJECT queries (CULTURE strand)
        # These are questions about cooperation projects (small/medium/large scale),
        # partnership requirements, funding rates, and scale selection
        # e.g., "What are Creative Europe cooperation projects?", "Small vs medium vs large?",
        # "We have 3 partners - which category?", "What's the funding rate?"
        # IMPORTANT: Must come BEFORE MEDIA strand to catch CULTURE cooperation questions
        ce_cooperation_result = self._detect_creative_europe_cooperation_query(query, context)
        if ce_cooperation_result:
            return ce_cooperation_result

        # Check for CREATIVE EUROPE MEDIA STRAND queries
        # These are questions about Creative Europe MEDIA strand, development funding,
        # distribution support, and multi-project participation for audiovisual sector
        # e.g., "Tell me about the MEDIA strand", "What development funding is available?",
        # "What about distribution support?", "How many projects can we participate in?"
        # IMPORTANT: Must come BEFORE SME eligibility to prevent false matches
        ce_media_result = self._detect_creative_europe_media_query(query, context)
        if ce_media_result:
            return ce_media_result

        # Check for SME ELIGIBILITY queries
        # These are questions about SME definition, ownership rules, and non-SME participation
        # e.g., "We have 200 employees - still SME?", "Parent company affects SME status?",
        # "Can we still participate in RIA if not SME?"
        # IMPORTANT: Must come BEFORE urgent_deadline to prevent "can we still" false matches
        sme_eligibility_result = self._detect_sme_eligibility_query(query, context)
        if sme_eligibility_result:
            return sme_eligibility_result

        # Check for CONSORTIUM ELIGIBILITY queries
        # These are questions about consortium requirements, third country participation,
        # and associated country status (Switzerland, UK, US, etc.)
        # e.g., "We have partners from Germany, France, UK", "Is this consortium eligible?",
        # "Can we add a Swiss partner?", "Can American organizations participate?"
        # IMPORTANT: Must come BEFORE timeline comparison to prevent false matches
        consortium_eligibility_result = self._detect_consortium_eligibility_query(query, context)
        if consortium_eligibility_result:
            return consortium_eligibility_result

        # Check for CROSS-PROGRAMME ELIGIBILITY queries (double funding, multiple programmes)
        # These are questions about participating in multiple EU programmes simultaneously
        # e.g., "Can we have the same project funded by both Horizon Europe and Erasmus+?"
        # e.g., "What about double funding rules?", "Simultaneous applications?"
        # IMPORTANT: Must come BEFORE timeline comparison to prevent false matches
        cross_programme_result = self._detect_cross_programme_eligibility_query(query, context)
        if cross_programme_result:
            return cross_programme_result

        # Check for TIMELINE COMPARISON queries
        # These are questions about proposal preparation times, decision times, and project start lags
        # e.g., "How long to prepare a proposal?", "Compare with Erasmus+ KA2", "Decision time?"
        timeline_result = self._detect_timeline_comparison_query(query, context)
        if timeline_result:
            return timeline_result

        # Check for URGENT DEADLINE / PREPARATION REQUIREMENTS queries
        # These are questions about minimum requirements for imminent deadlines, feasibility prioritization
        # e.g., "What's the minimum we need ready?", "Can you prioritize by feasibility?"
        urgent_deadline_result = self._detect_urgent_deadline_query(query, context)
        if urgent_deadline_result:
            return urgent_deadline_result

        # Check for MULTI-CALL TIMELINE queries (planning multiple submissions)
        # These are questions about planning multiple proposal submissions in a quarter
        # e.g., "I want to apply to 3 calls this quarter", "What if one call deadline changes?"
        multi_call_timeline_result = self._detect_multi_call_timeline_query(query, context)
        if multi_call_timeline_result:
            return multi_call_timeline_result

        # Check for DEADLINE TRACKING queries (time gap between calls, which to target)
        # These are follow-up questions after viewing deadline lists
        # e.g., "How much time between them?", "Which one should I target?"
        deadline_tracking_result = self._detect_deadline_tracking_query(query, context)
        if deadline_tracking_result:
            return deadline_tracking_result

        # Check for CONTEXT RECALL queries (e.g., "I mentioned earlier I work on hydrogen")
        # These reference earlier conversation context to find calls
        context_recall_result = self._detect_context_recall_query(query, context)
        if context_recall_result:
            return context_recall_result

        # Check for TOPIC REFINEMENT queries (e.g., "Actually, I'm interested in AI for healthcare")
        # These are follow-ups that refine a previous search with more specific keywords
        # e.g., Turn 1: "Find AI funding opportunities"
        #       Turn 2: "Actually, I'm interested in AI for healthcare specifically"
        # Should combine original topic with refinement keywords
        # IMPORTANT: Must come before other call search patterns to handle refinements first
        logger.info(f"🔍 Checking topic refinement for query: {query[:50]}")
        topic_refinement_result = self._detect_topic_refinement_query(query, context)
        if topic_refinement_result:
            logger.info(
                f"🎯 Topic refinement detected! Combined keywords: "
                f"{topic_refinement_result.get('tool_calls', [{}])[0].get('parameters', {}).get('keywords', 'unknown')}"
            )
            return topic_refinement_result
        logger.debug("🔍 No topic refinement detected")

        # Organization queries are handled by the LLM with tool descriptions:
        # - get_organization_stats: for counts, stats, funding totals
        # - find_organization_projects: for listing actual projects
        # The LLM picks the right tool based on the query intent.

        # Check for SEMANTIC SIMILARITY PROJECT queries (must come before general project search!)
        # These are queries asking for projects "similar to" a concept, description, or idea
        # e.g., "Find projects similar to developing sustainable aviation fuels"
        # e.g., "Show me projects like AI for cancer detection"
        # These should use semantic embeddings, NOT keyword search
        semantic_project_result = self._detect_semantic_project_query(query, context)
        if semantic_project_result:
            return semantic_project_result

        # Partner/organization discovery patterns
        partner_patterns = [
            "find partner",
            "find organization",
            "find organisations",
            "organizations experienced",
            "organisations experienced",
            "partner search",
            "experienced in",
            "who has experience",
            "companies working on",
            "universities working on",
            "sme partner",
            "sme from",
            "research organization",
            "research organisation",
            "need a partner",
            "need an sme",
            "precision farming",
            "find a research",
        ]

        # Check for partner discovery queries
        if any(pattern in query_lower for pattern in partner_patterns):
            # Extract topic keywords from query
            topic_keywords = self._extract_topic_keywords(query)
            country = self._extract_country(query)
            org_type = self._extract_org_type(query)

            params = {"topic_keywords": topic_keywords}
            if country:
                params["country"] = country
            if org_type:
                params["organization_type"] = org_type

            return {
                "thought": f"User is looking for partners/organizations. Using find_experienced_partners with keywords: {topic_keywords}",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "find_experienced_partners",
                        "parameters": params,
                        "reasoning": "Finding organizations with relevant EU funding experience",
                    }
                ],
                "needs_more_info": True,
            }

        # Check for "tell me more about that" follow-up queries about programmes/recommendations
        tell_more_result = self._detect_tell_me_more_query(query, context)
        if tell_more_result:
            return tell_more_result

        # Check for partner search REFINEMENT queries (e.g., "Show only universities" after partner search)
        refinement_result = self._detect_partner_search_refinement(query, context)
        if refinement_result:
            return refinement_result

        # Check for organization DEEP-DIVE queries BEFORE partner comparison
        # Organization deep-dive queries (follow-ups about an org) are handled by the LLM.

        # Check for cluster/programme COMPARISON queries BEFORE partner comparison
        # e.g., "How does Cluster 5 compare to Cluster 1?", "Compare EIC and ERC"
        cluster_comparison_result = self._detect_cluster_comparison_query(query, context)
        if cluster_comparison_result:
            return cluster_comparison_result

        # Check for BUDGET TREND / HISTORICAL ANALYSIS queries
        # e.g., "Show budget trends over 2021-2024", "How has funding changed?"
        budget_trend_result = self._detect_budget_trend_query(query, context)
        if budget_trend_result:
            return budget_trend_result

        # Check for BUDGET VARIATION queries (follow-up to budget questions)
        # e.g., "How does this vary by organization type?", "What about coordinator vs partner?"
        budget_variation_result = self._detect_budget_variation_query(query, context)
        if budget_variation_result:
            return budget_variation_result

        # Check for PER-PARTNER BUDGET queries (follow-up to budget comparisons)
        # e.g., "What's the average per-partner budget?", "How much per partner?"
        per_partner_result = self._detect_per_partner_budget_query(query, context)
        if per_partner_result:
            return per_partner_result

        # Check for partner COMPARISON/ANALYSIS queries (e.g., "Compare the top 3", "Which has most funding?")
        # Only reached if context doesn't have organization-specific indicators
        comparison_result = self._detect_partner_comparison_query(query, context)
        if comparison_result:
            return comparison_result

        # Consortium size/patterns queries
        consortium_patterns = [
            "typical consortium",
            "consortium size",
            "how many partners",
            "consortium composition",
            "consortium pattern",
            "ideal partners",
            "partner types",
            "typical number of partners",
        ]

        if any(pattern in query_lower for pattern in consortium_patterns):
            topic_keywords = self._extract_topic_keywords(query)
            return {
                "thought": "User is asking about consortium patterns. Using get_consortium_patterns tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "get_consortium_patterns",
                        "parameters": {"topic_keywords": topic_keywords} if topic_keywords else {},
                        "reasoning": "Getting consortium composition patterns from funded projects",
                    }
                ],
                "needs_more_info": True,
            }

        # Check for NICHE INTERDISCIPLINARY queries
        # These are highly specialized queries combining multiple domains (e.g., archaeology + AI)
        # that may not have dedicated funding calls - we need to provide helpful guidance
        niche_result = self._detect_niche_interdisciplinary_query(query, context)
        if niche_result:
            return niche_result

        return None

    def _detect_initial_organization_profile_query(self, query: str) -> dict[str, Any] | None:
        """Detect if query asks about a SPECIFIC named organization's funding/projects.

        This handles INITIAL queries (no context needed) like:
        - "Tell me about Technical University of Munich's EU funding history"
        - "What has Fraunhofer done in Horizon Europe?"
        - "Show TUM's projects"
        - "CNRS funding track record"

        These should use find_organization_projects, NOT find_experienced_partners.

        Key distinction:
        - "Find partners for AI research" -> find_experienced_partners (searching MANY orgs)
        - "Tell me about TUM's funding" -> find_organization_projects (asking about ONE org)
        """
        query_lower = query.lower()

        # Known organization names/aliases (common forms users might use)
        # NOTE: Short patterns like "tum" need word boundary matching to avoid
        # false positives (e.g., "quantum" contains "tum")
        known_org_patterns = {
            # German Universities
            "technical university of munich": "Technical University of Munich",
            "tu munich": "TU Munich",
            "tum's": "TUM",
            # "tum " removed - causes false positives with "quantum". Use regex matching below.
            "technische universitaet muenchen": "Technische Universitaet Muenchen",
            "technical university of berlin": "Technical University of Berlin",
            "tu berlin": "TU Berlin",
            "rwth aachen": "RWTH Aachen",
            "tu dortmund": "TU Dortmund",
            "tu dresden": "TU Dresden",
            # German Research Orgs
            "fraunhofer": "Fraunhofer",
            "max planck": "Max Planck",
            "helmholtz": "Helmholtz",
            "leibniz": "Leibniz",
            # Dutch Universities
            "tu delft": "TU Delft",
            "delft university": "TU Delft",
            "tu eindhoven": "TU Eindhoven",
            "eindhoven university": "TU Eindhoven",
            # Austrian Universities
            "tu vienna": "TU Vienna",
            "tu wien": "TU Wien",
            "tu graz": "TU Graz",
            # French institutions
            "cnrs": "CNRS",
            "inria": "INRIA",
            # "cea " removed - handled by regex with word boundary
            "inserm": "INSERM",
            # UK institutions
            "imperial college": "Imperial College London",
            # "ucl " removed - handled by regex with word boundary
            "university college london": "UCL",
            "oxford university": "Oxford University",
            "university of oxford": "University of Oxford",
            "cambridge university": "Cambridge University",
            "university of cambridge": "University of Cambridge",
            # Swiss institutions
            "eth zurich": "ETH Zurich",
            "epfl": "EPFL",
            # Italian institutions
            "politecnico di milano": "Politecnico di Milano",
            "polimi": "Politecnico di Milano",
            "sapienza": "Sapienza",
            "universita di bologna": "Universita di Bologna",
            # Spanish institutions
            "csic": "CSIC",
            # Belgian institutions
            "ku leuven": "KU Leuven",
            "imec": "IMEC",
            "universiteit gent": "Universiteit Gent",
            # Nordic institutions
            "dtu": "DTU",
            "danmarks tekniske": "DTU",
            "chalmers": "Chalmers",
            "kth": "KTH",
            "sintef": "SINTEF",
            "vtt": "VTT",
            # Other major institutions
            "cern": "CERN",
            # "esa " removed - handled by regex with word boundary
        }

        # Patterns indicating stats/count queries → route to get_organization_stats
        org_stats_patterns = [
            "how many projects",
            "how many of them",
            "number of projects",
            "count of projects",
            "coordinator role",
            "coordinator count",
            "total funding",
            "stats for",
            "statistics for",
        ]
        is_stats_query = any(pattern in query_lower for pattern in org_stats_patterns)

        # Patterns indicating asking ABOUT an organization (not searching for partners)
        org_profile_patterns = [
            "'s eu funding",
            "'s funding history",
            "'s eu projects",
            "'s projects",
            "'s track record",
            "'s horizon",
            "tell me about",
            "what has",
            "show me",
            "funding history",
            "project history",
            "eu funding track",
            "what projects has",
            "projects by",
            "projects from",
        ]

        # Check if query has an organization profile indicator
        has_profile_pattern = any(pattern in query_lower for pattern in org_profile_patterns)

        # Short org patterns that need word-boundary matching to avoid false positives
        # e.g., "tum" should not match within "quantum"
        import re

        short_org_patterns_regex = {
            r"\btum\b": "TUM",  # Technical University of Munich
            r"\bcea\b": "CEA",  # Commissariat à l'énergie atomique
            r"\bucl\b": "UCL",  # University College London
            r"\besa\b": "ESA",  # European Space Agency
            r"\bdtu\b": "DTU",  # Danmarks Tekniske Universitet
            r"\bkth\b": "KTH",  # Kungliga Tekniska högskolan
            r"\bvtt\b": "VTT",  # Technical Research Centre of Finland
        }

        # Find if a known organization is mentioned
        found_org = None

        # First check regex patterns (short names that need word boundaries)
        for pattern, org_name in short_org_patterns_regex.items():
            if re.search(pattern, query_lower):
                found_org = org_name
                break

        # Then check simple substring patterns (longer names safe from false positives)
        if not found_org:
            for org_pattern, org_name in known_org_patterns.items():
                if org_pattern in query_lower:
                    found_org = org_name
                    break

        # Stats/count queries → route to get_organization_stats (fast, aggregate counts)
        if found_org and is_stats_query:
            logger.info(f"📊 Detected organization STATS query for: {found_org}")
            return {
                "thought": f"User is asking for statistics/counts about {found_org}. "
                f"Using get_organization_stats for aggregate data.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "get_organization_stats",
                        "parameters": {"organization_name": found_org},
                        "reasoning": f"Getting aggregate statistics (project count, coordinator count, funding) for {found_org}",
                    }
                ],
                "needs_more_info": False,
            }

        # If we found a known org AND a profile-asking pattern, use find_organization_projects
        if found_org and has_profile_pattern:
            logger.info(f"🏢 Detected organization profile query for: {found_org}")
            return {
                "thought": f"User is asking specifically about {found_org}'s EU funding profile. "
                f"Using find_organization_projects (not find_experienced_partners).",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "find_organization_projects",
                        "parameters": {"organization_name": found_org},
                        "reasoning": f"Getting {found_org}'s project portfolio from database",
                    }
                ],
                "needs_more_info": True,
            }

        # Even without profile pattern, if query ONLY mentions one known org,
        # it's likely asking about that specific org
        if found_org:
            # Check if it's not a "find partners FOR" query
            partner_search_indicators = [
                "find partner",
                "need partner",
                "looking for partner",
                "experienced in",
                "organizations working on",
                "who has experience",
            ]
            is_partner_search = any(ind in query_lower for ind in partner_search_indicators)

            if not is_partner_search:
                logger.info(f"🏢 Detected organization-focused query for: {found_org}")
                return {
                    "thought": f"User is asking about {found_org}. Using find_organization_projects.",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": "find_organization_projects",
                            "parameters": {"organization_name": found_org},
                            "reasoning": f"Getting {found_org}'s project portfolio from database",
                        }
                    ],
                    "needs_more_info": True,
                }

        return None

    def _detect_semantic_project_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query asks for semantically similar projects.

        This handles queries asking for projects "similar to" a concept/description:
        - "Find projects similar to developing sustainable aviation fuels"
        - "Show me projects like AI for cancer detection"
        - "Projects related to green hydrogen production"
        - "Find funded projects matching this idea: [description]"

        These should use get_similar_funded_projects (semantic embeddings),
        NOT search_projects (keyword matching).

        Key distinction:
        - "Find projects about AI" -> search_projects (keyword search)
        - "Find projects similar to AI-powered cancer detection" -> get_similar_funded_projects (semantic)
        """
        query_lower = query.lower()

        # Semantic similarity patterns - indicates user wants conceptually related projects
        semantic_patterns = [
            "similar to",
            "projects like",
            "projects matching",
            "projects related to",
            "semantically similar",
            "conceptually related",
            "find similar projects",
            "find projects similar",
            "show me similar",
            "similar funded projects",
            "projects with similar",
        ]

        # Check if query contains semantic similarity language
        has_semantic_pattern = any(pattern in query_lower for pattern in semantic_patterns)

        # Also detect LONG DESCRIPTIVE project queries where keyword search would fail
        # e.g., "What are the most relevant projects about Improved reliability and
        #        optimised operations and maintenance for wind energy systems?"
        # These should use semantic search because keyword search matches individual words
        # (like "reliability", "maintenance") against unrelated projects
        project_query_patterns = [
            "relevant projects about",
            "projects about",
            "projects related to",
            "projects on",
            "projects for",
            "projects in the area of",
            "projects in the field of",
            "projects addressing",
            "projects focusing on",
            "projects dealing with",
            "funded projects about",
            "funded projects on",
        ]
        has_project_pattern = any(pattern in query_lower for pattern in project_query_patterns)
        if has_project_pattern and not has_semantic_pattern:
            # Extract the description part after the pattern
            import re

            description = query
            for pattern in project_query_patterns:
                if pattern in query_lower:
                    idx = query_lower.find(pattern)
                    description = query[idx + len(pattern) :].strip().rstrip("?. ")
                    break
            # Only route to semantic search if the description is long enough
            # Short queries like "projects about AI" → keyword search
            # Long queries like "projects about improved reliability and optimised operations
            #   and maintenance for wind energy systems" → semantic search
            word_count = len(description.split())
            if word_count >= 6 and len(description) >= 30:
                logger.info(
                    f"🧬 Detected long descriptive project query ({word_count} words): '{description}'"
                )
                # Extract key terms for keyword search (shorter phrases work better)
                key_terms = " ".join(
                    w
                    for w in description.split()
                    if len(w) >= 3
                    and w.lower()
                    not in {
                        "the",
                        "and",
                        "for",
                        "with",
                        "from",
                        "that",
                        "this",
                        "are",
                        "was",
                        "were",
                    }
                )[:80]
                return {
                    "thought": f"User is asking for projects about '{description}'. "
                    "Running BOTH semantic search (conceptual matching) AND keyword search "
                    "(exact term matching) with higher limits, then merging into one ranked list.",
                    "action": "call_tools_and_format",
                    "tool_calls": [
                        {
                            "tool": "get_similar_funded_projects",
                            "parameters": {"description": description, "limit": 100},
                            "reasoning": "Semantic search — fetch large pool for best ranking after merge",
                        },
                        {
                            "tool": "search_projects",
                            "parameters": {"keywords": key_terms, "limit": 100},
                            "reasoning": "Keyword search complement — large pool catches projects semantic search may miss",
                        },
                    ],
                }

        if has_semantic_pattern:
            # Extract the description part (what comes after the semantic pattern)
            description = query

            # Try to extract the concept being searched for
            for pattern in semantic_patterns:
                if pattern in query_lower:
                    # Find where the pattern ends and extract the rest as description
                    idx = query_lower.find(pattern)
                    if idx >= 0:
                        description = query[idx + len(pattern) :].strip()
                        # Clean up common prefixes
                        if description.lower().startswith("to "):
                            description = description[3:]
                        if description.lower().startswith("developing "):
                            description = description[11:]
                        break

            # If we couldn't extract a description, use the whole query
            if not description or len(description) < 10:
                # Fall back to extracting key content words
                import re

                # Remove common verbs and query words
                clean_query = re.sub(
                    r"\b(find|show|me|projects?|similar|to|like|matching|funded|related|semantically|conceptually)\b",
                    "",
                    query_lower,
                    flags=re.IGNORECASE,
                )
                description = " ".join(clean_query.split())

            # Ensure description is meaningful (at least 10 chars)
            if len(description) >= 10:
                logger.info(f"🧬 Detected semantic project search: '{description}'")
                return {
                    "thought": f"User is asking for projects semantically similar to '{description}'. "
                    "Using get_similar_funded_projects (AI embeddings) for semantic matching, "
                    "not search_projects (keyword matching).",
                    "action": "call_tools_and_format",
                    "tool_calls": [
                        {
                            "tool": "get_similar_funded_projects",
                            "parameters": {"description": description, "limit": 100},
                            "reasoning": "Finding projects using semantic similarity (AI embeddings) to match concepts, not just keywords",
                        }
                    ],
                }

        return None

    def _detect_partner_search_refinement(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is a refinement of a previous partner search.

        This handles short queries like "Show only universities", "From EU15 countries only"
        that follow a partner search and should continue using find_experienced_partners.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates a recent partner search
        partner_search_indicators = [
            "find_experienced_partners",
            "experienced partners",
            "organizations with experience",
            "partner discovery",
            "top organizations",
            "organization type",
            "relevant projects",
            "total funding",
        ]

        has_partner_context = any(
            indicator in context_lower for indicator in partner_search_indicators
        )

        if not has_partner_context:
            return None

        # Partner refinement patterns - short queries that filter results
        refinement_patterns = {
            # Organization type filters
            "only universities": {"organization_type": "HES"},
            "show only universities": {"organization_type": "HES"},
            "universities only": {"organization_type": "HES"},
            "only hes": {"organization_type": "HES"},
            "higher education": {"organization_type": "HES"},
            "only smes": {"organization_type": "SME"},
            "smes only": {"organization_type": "SME"},
            "only research": {"organization_type": "REC"},
            "research only": {"organization_type": "REC"},
            "only private": {"organization_type": "PRC"},
            "companies only": {"organization_type": "PRC"},
            # Role filters
            "experience coordinating": {"role_filter": "coordinator"},
            "coordinating projects": {"role_filter": "coordinator"},
            "as coordinator": {"role_filter": "coordinator"},
            "who have coordinated": {"role_filter": "coordinator"},
            "coordination experience": {"role_filter": "coordinator"},
            # Country/region filters
            "eu15 countries": {"country_group": "EU15"},
            "from eu15": {"country_group": "EU15"},
            "eu15 only": {"country_group": "EU15"},
            "eu13 countries": {"country_group": "EU13"},
            "from eu13": {"country_group": "EU13"},
            "southern europe": {"country_group": "SOUTHERN"},
            "northern europe": {"country_group": "NORTHERN"},
            "western europe": {"country_group": "WESTERN"},
            "eastern europe": {"country_group": "EASTERN"},
        }

        # Check for refinement patterns
        matched_params = {}
        for pattern, params in refinement_patterns.items():
            if pattern in query_lower:
                matched_params.update(params)

        # Also check for organization type via standard extraction
        org_type = self._extract_org_type(query)
        if org_type:
            matched_params["organization_type"] = org_type

        # Check for country extraction
        country = self._extract_country(query)
        if country:
            matched_params["country"] = country

        # Check for topic refinement (e.g., "who have worked on quantum communication")
        topic_refinement_patterns = [
            "worked on",
            "have worked on",
            "who have worked",
            "experience in",
            "experience with",
            "specialized in",
            "focus on",
        ]
        if any(p in query_lower for p in topic_refinement_patterns):
            # Extract topic from the query
            new_topic = self._extract_topic_keywords(query)
            if new_topic:
                matched_params["topic_keywords"] = new_topic

        if not matched_params:
            return None

        # Extract original topic from context if available
        original_topic = self._extract_topic_from_context(context)
        if original_topic and "topic_keywords" not in matched_params:
            matched_params["topic_keywords"] = original_topic

        # Convert country_group to actual country list
        if "country_group" in matched_params:
            country_group = matched_params.pop("country_group")
            countries = self._get_countries_for_group(country_group)
            if countries:
                # For now, use the first country - the tool may need enhancement to accept multiple
                matched_params["country"] = countries[0]

        return {
            "thought": f"User is refining previous partner search with filters: {matched_params}. Using find_experienced_partners with refinement.",
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "find_experienced_partners",
                    "parameters": matched_params,
                    "reasoning": "Refining partner search based on user's filter criteria",
                }
            ],
            "needs_more_info": True,
        }

    def _detect_personalized_call_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is asking for call recommendations using accumulated context.

        This handles queries like:
        - "What calls should we apply to?"
        - "What about as a partner?"
        - "What funding is available for us?"
        - "Which opportunities fit our profile?"

        These should use search_funding_calls with keywords extracted from conversation context.
        """
        if not context:
            return None

        query_lower = query.lower()

        # Patterns that indicate user wants personalized call/opportunity recommendations
        personalized_patterns = [
            "what calls should",
            "what calls can",
            "calls should we apply",
            "calls can we apply",
            "what about as a partner",
            "as a participant",
            "for our organization",
            "for our university",
            "for us",
            "opportunities for",
            "which opportunities",
            "what funding is available",
            "suitable calls",
            "relevant calls",
            "matching calls",
            # Profile-based recommendation queries
            "best option",
            "our best option",
            "what's our best",
            "what is our best",
            "what should we",
            "what do you recommend",
            "what would you recommend",
            "recommend for us",
            "which programme",
            "which program",
            "best programme",
            "best program",
            "best fit",
            "best match",
            "right programme",
            "right program",
        ]

        if not any(pattern in query_lower for pattern in personalized_patterns):
            return None

        # Extract context from conversation (org type, sector, country, experience level)
        context_lower = context.lower()

        # Extract research sector/topic from context
        sector_keywords = []
        sector_patterns = [
            # Medical/Healthcare - more specific patterns first
            ("ai diagnostics", "AI diagnostics artificial intelligence medical devices health"),
            ("medical devices", "medical devices health clinical diagnostics"),
            ("medical device", "medical devices health clinical diagnostics"),
            ("diagnostics", "diagnostics medical devices health clinical"),
            ("healthcare sector", "health medical clinical healthcare"),
            ("healthcare", "health medical clinical"),
            ("health", "health medical clinical"),
            # Marine/Ocean
            ("marine biology", "marine biology ocean aquatic"),
            ("marine", "marine ocean aquatic"),
            ("ocean", "marine ocean aquatic"),
            # Energy/Climate
            ("energy", "energy renewable climate"),
            ("climate", "climate environment sustainability"),
            # AI/Digital
            ("ai", "artificial intelligence AI digital"),
            ("artificial intelligence", "artificial intelligence AI digital"),
            ("digital", "digital AI technology"),
            # Agriculture/Food
            ("agriculture", "agriculture food bioeconomy"),
            ("food", "food agriculture bioeconomy"),
        ]

        for pattern, keywords in sector_patterns:
            if pattern in context_lower:
                sector_keywords = keywords.split()
                break

        # Extract country from context
        country = None
        country_patterns = {
            "portugal": "PT",
            "portuguese": "PT",
            "germany": "DE",
            "german": "DE",
            "spain": "ES",
            "spanish": "ES",
            "italy": "IT",
            "italian": "IT",
            "france": "FR",
            "french": "FR",
            "netherlands": "NL",
            "dutch": "NL",
        }
        for pattern, code in country_patterns.items():
            if pattern in context_lower:
                country = code
                break

        # Check for experience level indicators
        is_beginner = any(
            pattern in context_lower
            for pattern in [
                "never coordinated",
                "first time",
                "new to",
                "beginner",
                "no experience",
                "never done eu funding",
                "never applied",
                "never submitted",
            ]
        )

        # Check for organization type
        org_type = None
        if any(
            x in context_lower
            for x in ["university", "universities", "academic", "higher education"]
        ):
            org_type = "HES"
        elif any(x in context_lower for x in ["sme", "startup", "small business"]):
            org_type = "SME"
        elif any(
            x in context_lower
            for x in ["research center", "research institute", "research organisation"]
        ):
            org_type = "REC"

        # Build search parameters
        if not sector_keywords:
            # No specific sector found, can't personalize enough
            return None

        search_keywords = " ".join(sector_keywords[:4])

        # Build thought that shows personalization
        thought_parts = [f"User has a profile: {', '.join(sector_keywords[:3])} research"]
        if country:
            thought_parts.append(f"from {country}")
        if org_type:
            thought_parts.append(f"({org_type})")
        if is_beginner:
            thought_parts.append("(beginner, recommend partner role)")
        thought = " ".join(thought_parts) + ". Searching for matching calls."

        # Build conclusion that uses context
        conclusion_parts = []

        # Check if user is asking about partner role specifically
        if "as a partner" in query_lower or "as a participant" in query_lower:
            if is_beginner:
                conclusion_parts.append(
                    f"Given your background in {', '.join(sector_keywords[:2])} research "
                    "and no prior coordination experience, participating as a **partner** is a great strategy "
                    "to build your EU funding track record.\n\n"
                    "**Recommended Approach:**\n"
                    "1. **Join existing consortia** - Look for projects seeking partners in your area\n"
                    "2. **Use Partner Search** - Register on the EU Funding Portal Partner Search\n"
                    "3. **Target Widening calls** - These have extra support for organizations like yours\n"
                    "4. **Consider MSCA** - Marie Curie actions are great for building experience\n\n"
                )
            else:
                conclusion_parts.append(
                    f"Here are opportunities in {', '.join(sector_keywords[:2])} where you could participate as a partner:\n\n"
                )

        # Check if this is a "best option/programme recommendation" query vs "find calls" query
        is_programme_recommendation = any(
            pattern in query_lower
            for pattern in [
                "best option",
                "best programme",
                "best program",
                "which programme",
                "which program",
                "recommend for us",
                "what do you recommend",
                "what would you recommend",
                "right programme",
                "right program",
            ]
        )

        if is_programme_recommendation:
            # Build a comprehensive description from accumulated profile for recommend_programmes
            # Include all relevant context for better programme matching
            profile_parts = []
            if org_type:
                org_type_names = {"SME": "SME", "HES": "university", "REC": "research center"}
                profile_parts.append(org_type_names.get(org_type, org_type))

            # Build comprehensive sector description with all relevant keywords
            sector_desc_parts = []
            if sector_keywords:
                # Include all sector keywords for comprehensive matching
                sector_desc_parts.extend(sector_keywords)

            # Also check for specific domain keywords in context to enhance description
            # These patterns should match various ways users describe their domains
            domain_keywords = []
            # Health/Healthcare patterns (for EU4Health matching)
            if any(p in context_lower for p in ["healthcare", "health sector", "health "]):
                domain_keywords.append("health")
                domain_keywords.append("healthcare")
            # Medical device patterns (important for EU4Health)
            if any(
                p in context_lower
                for p in ["medical device", "medical devices", "medtech", "medicaldevice"]
            ):
                domain_keywords.append("medical device")
            # AI/Digital patterns
            if any(
                p in context_lower
                for p in ["ai ", " ai", "artificial intelligence", "machine learning"]
            ):
                domain_keywords.append("AI")
            # Diagnostics patterns
            if any(p in context_lower for p in ["diagnostics", "diagnostic", "diagnosis"]):
                domain_keywords.append("diagnostics")

            # Combine sector and domain keywords (deduplicated)
            all_keywords = []
            seen = set()
            for kw in sector_desc_parts + domain_keywords:
                kw_lower = kw.lower()
                if kw_lower not in seen:
                    seen.add(kw_lower)
                    all_keywords.append(kw)

            if all_keywords:
                profile_parts.append(f"working in {', '.join(all_keywords[:8])}")

            if country:
                country_names = {
                    "DE": "Germany",
                    "PT": "Portugal",
                    "ES": "Spain",
                    "IT": "Italy",
                    "FR": "France",
                    "NL": "Netherlands",
                }
                profile_parts.append(f"based in {country_names.get(country, country)}")
            if is_beginner:
                profile_parts.append("new to EU funding")

            description = ", ".join(profile_parts) if profile_parts else search_keywords

            # Determine the primary sector for the sector parameter
            primary_sector = None
            if "health" in context_lower or "healthcare" in context_lower:
                primary_sector = "health"
            elif "medical" in context_lower:
                primary_sector = "health"
            elif sector_keywords:
                primary_sector = sector_keywords[0]

            return {
                "thought": thought + " Using recommend_programmes for best option query.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "recommend_programmes",
                        "parameters": {
                            "description": description,
                            "organization_type": org_type.lower() if org_type else None,
                            "sector": primary_sector,
                        },
                        "reasoning": f"Recommending best programmes based on profile: {description}",
                    }
                ],
                "needs_more_info": True,
            }

        return {
            "thought": thought,
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "search_funding_calls",
                    "parameters": {"keywords": search_keywords, "status": "open", "limit": 10},
                    "reasoning": f"Finding open calls for {search_keywords} based on accumulated user context",
                }
            ],
            "needs_more_info": True,
        }

    def _detect_tell_me_more_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect follow-up queries like 'Tell me more about that option'.

        This handles queries like:
        - "Tell me more about that option"
        - "Tell me more about that programme"
        - "More details on that"
        - "Elaborate on that recommendation"

        These should use get_programme_info with the programme from context.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Patterns that indicate user wants more info about something from context
        tell_more_patterns = [
            "tell me more",
            "more about that",
            "more details",
            "elaborate on",
            "explain more",
            "can you explain",
            "what else",
            "more information",
            "more info",
        ]

        if not any(pattern in query_lower for pattern in tell_more_patterns):
            return None

        # Look for programme names in context to understand what "that" refers to
        programme_mentions = {
            "horizon europe": ("horizon_europe", "Horizon Europe"),
            "eu4health": ("eu4health", "EU4Health"),
            "erasmus+": ("erasmus_plus", "Erasmus+"),
            "erasmus plus": ("erasmus_plus", "Erasmus+"),
            "creative europe": ("creative_europe", "Creative Europe"),
            "digital europe": ("digital_europe", "Digital Europe"),
            "life programme": ("life", "LIFE Programme"),
        }

        # Check which programme was mentioned in context (most recent first)
        detected_programme = None
        detected_programme_name = None

        for pattern, (prog_id, prog_name) in programme_mentions.items():
            if pattern in context_lower:
                detected_programme = prog_id
                detected_programme_name = prog_name
                break

        if not detected_programme:
            # No specific programme found, can't provide more info
            return None

        # Build profile from context for personalized response
        profile_parts = []

        # Extract org type from context
        if "sme" in context_lower:
            profile_parts.append("SME")
        elif "university" in context_lower or "academic" in context_lower:
            profile_parts.append("university")

        # Extract sector from context
        sector_map = {
            "healthcare": "healthcare",
            "medical device": "medical devices",
            "ai diagnostics": "AI diagnostics",
            "health": "health",
            "energy": "energy",
            "digital": "digital",
        }
        for pattern, sector in sector_map.items():
            if pattern in context_lower:
                profile_parts.append(sector)
                break

        # Extract country from context
        country_map = {
            "germany": "Germany",
            "german": "Germany",
            "france": "France",
            "spain": "Spain",
            "italy": "Italy",
        }
        for pattern, country in country_map.items():
            if pattern in context_lower:
                profile_parts.append(f"based in {country}")
                break

        profile_summary = ", ".join(profile_parts) if profile_parts else "your profile"

        return {
            "thought": f"User wants more details about {detected_programme_name}. Using get_programme_info with context: {profile_summary}.",
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "get_programme_info",
                    "parameters": {"programme": detected_programme},
                    "reasoning": f"Getting detailed info about {detected_programme_name} for {profile_summary}",
                }
            ],
            "needs_more_info": True,
            "context_summary": f"Based on your profile ({profile_summary}), here's more about {detected_programme_name}:",
        }

    def _detect_historical_programme_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect historical/outdated programme queries (H2020, FP7, FP6, etc.).

        These are questions about EU funding programmes that are no longer active.
        The system should:
        1. Recognize references to historical programmes
        2. Provide appropriate historical context
        3. Explain that applications are no longer possible
        4. Guide users to current alternatives (Horizon Europe)

        Examples:
        - "Tell me about H2020 calls"
        - "What about FP7?"
        - "Can I still apply to Horizon 2020?"
        - "What programme replaced H2020?"
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Pattern 1: H2020 / Horizon 2020 overview queries
        # e.g., "Tell me about H2020", "What is Horizon 2020?", "H2020 opportunities"
        h2020_overview_patterns = [
            "tell me about h2020",
            "what is h2020",
            "what was h2020",
            "h2020 calls",
            "h2020 funding",
            "h2020 opportunities",
            "horizon 2020 calls",
            "horizon 2020 funding",
            "horizon 2020 opportunities",
            "tell me about horizon 2020",
            "what is horizon 2020",
            "what was horizon 2020",
            "h2020 programme",
            "h2020 program",
            "horizon 2020 programme",
            "horizon 2020 program",
            "about h2020",
            "about horizon 2020",
        ]

        # Pattern 2: FP7 / Framework Programme 7 queries
        # e.g., "What about FP7?", "FP7 projects", "Seventh Framework Programme"
        fp7_patterns = [
            "fp7",
            "fp-7",
            "framework programme 7",
            "framework program 7",
            "seventh framework",
            "7th framework",
            "fp 7",
        ]

        # Pattern 3: Can I still apply? (to historical programmes)
        # e.g., "Can I apply to H2020?", "Are H2020 calls still open?"
        can_apply_patterns = [
            "can i still apply to h2020",
            "can i apply to h2020",
            "can we apply to h2020",
            "can i still apply to horizon 2020",
            "can i apply to horizon 2020",
            "can we apply to horizon 2020",
            "can i still apply to fp7",
            "can i apply to fp7",
            "can we apply to fp7",
            "apply to h2020 or fp7",
            "apply to fp7 or h2020",
            "h2020 or fp7 calls",
            "fp7 or h2020 calls",
            "h2020 still open",
            "h2020 calls open",
            "horizon 2020 still open",
            "horizon 2020 calls open",
            "fp7 still open",
            "fp7 calls open",
            "any h2020 calls",
            "any horizon 2020 calls",
            "any fp7 calls",
            "still accepting h2020",
            "still accepting horizon 2020",
            "still open",  # Combined with programme context
            "any still open",
        ]

        # Pattern 4: Programme replacement queries
        # e.g., "What replaced H2020?", "Successor to FP7?"
        replacement_patterns = [
            "what replaced h2020",
            "what replaced horizon 2020",
            "what replaced fp7",
            "successor to h2020",
            "successor to horizon 2020",
            "successor to fp7",
            "what comes after h2020",
            "what came after h2020",
            "after h2020",
            "after horizon 2020",
            "after fp7",
            "h2020 replacement",
            "horizon 2020 replacement",
            "fp7 replacement",
            "what should i apply to now",
            "what should we apply to now",
            "current programme",
            "current program",
            "what is current",
        ]

        # IMPORTANT: Check "can I still apply" queries FIRST, before FP7 simple check
        # This prevents "Can I apply to H2020 or FP7?" from matching FP7 overview
        if any(pattern in query_lower for pattern in can_apply_patterns):
            return {
                "thought": "User is asking if they can still apply to historical programmes. Clearly explaining that applications are closed.",
                "action": "generate_guidance",
                "guidance_type": "historical_applications_closed",
                "response": self._generate_historical_applications_closed_guidance(),
            }

        # Check for replacement/successor queries BEFORE overview queries
        # This prevents "what should I apply to now" from being missed
        if any(pattern in query_lower for pattern in replacement_patterns):
            return {
                "thought": "User is asking about what replaced historical programmes. Guiding to Horizon Europe.",
                "action": "generate_guidance",
                "guidance_type": "programme_successor",
                "response": self._generate_programme_successor_guidance(),
            }

        # Check for H2020 overview query
        if any(pattern in query_lower for pattern in h2020_overview_patterns):
            return {
                "thought": "User is asking about H2020 (Horizon 2020), a historical programme. Providing context and guiding to current alternatives.",
                "action": "generate_guidance",
                "guidance_type": "h2020_overview",
                "response": self._generate_h2020_overview_guidance(),
            }

        # Check for FP7 queries (general pattern - should come last)
        if any(pattern in query_lower for pattern in fp7_patterns):
            # Check if this is in context of H2020 discussion
            has_h2020_context = any(
                p in context_lower for p in ["h2020", "horizon 2020", "2014", "2020"]
            )
            return {
                "thought": "User is asking about FP7 (Framework Programme 7), an older historical programme. Providing context and timeline.",
                "action": "generate_guidance",
                "guidance_type": "fp7_overview",
                "response": self._generate_fp7_overview_guidance(has_h2020_context),
            }

        return None

    def _detect_ambiguous_programme_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect ambiguous programme queries that need disambiguation.

        This handles queries like:
        - "Tell me about the innovation fund"
        - "I mean the EU one"
        - "The one for climate"
        - "With grants not loans"

        The EU Innovation Fund (ETS-based) is often confused with:
        - EIC Accelerator (innovation focus, grants + equity)
        - Horizon Europe general (research & innovation)
        - InvestEU (innovation financing, mostly loans/guarantees)

        This method detects these ambiguous queries and provides proper disambiguation.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Pattern 1: Initial ambiguous "innovation fund" query
        # e.g., "Tell me about the innovation fund", "What is the innovation fund?"
        innovation_fund_initial_patterns = [
            "tell me about the innovation fund",
            "tell me about innovation fund",
            "what is the innovation fund",
            "what is innovation fund",
            "about the innovation fund",
            "about innovation fund",
            "innovation fund overview",
            "the innovation fund",
            "explain the innovation fund",
            "explain innovation fund",
        ]

        # Pattern 2: EU clarification follow-up
        # e.g., "I mean the EU one", "The European one", "EU innovation fund"
        eu_clarification_patterns = [
            "i mean the eu one",
            "the eu one",
            "the european one",
            "european innovation fund",
            "eu innovation fund",
            "mean the eu",
            "the eu's innovation",
            "the european",
        ]

        # Pattern 3: Climate/ETS clarification follow-up
        # e.g., "The one for climate", "For decarbonization", "ETS related"
        climate_clarification_patterns = [
            "the one for climate",
            "one for climate",
            "for climate",
            "for decarbonisation",
            "for decarbonization",
            "ets related",
            "ets-related",
            "emissions trading",
            "carbon",
            "low-carbon",
            "low carbon",
            "clean technology",
            "clean tech",
            "net-zero",
            "net zero",
            "green tech",
            "climate tech",
        ]

        # Pattern 4: Grants vs loans clarification
        # e.g., "With grants not loans", "Grant-based", "Non-repayable"
        grants_clarification_patterns = [
            "grants not loans",
            "grant not loan",
            "grants instead of loans",
            "grant-based",
            "grant based",
            "non-repayable",
            "non repayable",
            "not loans",
            "not a loan",
            "with grants",
            "only grants",
            "prefer grants",
        ]

        # Check for context from previous turns about innovation fund
        has_innovation_fund_context = any(
            p in context_lower
            for p in [
                "innovation fund",
                "ets",
                "emissions trading",
                "eu innovation",
                "cinea",
                "decarbonisation",
                "decarbonization",
                "low-carbon",
                "clean technology",
            ]
        )

        # Pattern 1: Initial ambiguous query
        if any(pattern in query_lower for pattern in innovation_fund_initial_patterns):
            return {
                "thought": "User is asking about 'the innovation fund' which is ambiguous. Providing overview of EU Innovation Fund (ETS) and clarifying it's different from Horizon Europe innovation funding.",
                "action": "generate_guidance",
                "guidance_type": "innovation_fund_disambiguation",
                "response": self._generate_innovation_fund_disambiguation_guidance(),
            }

        # Pattern 2: EU clarification with innovation fund context
        if has_innovation_fund_context and any(
            pattern in query_lower for pattern in eu_clarification_patterns
        ):
            return {
                "thought": "User is clarifying they want the EU Innovation Fund. Confirming the EU Innovation Fund (ETS-related) information.",
                "action": "generate_guidance",
                "guidance_type": "eu_innovation_fund_confirmation",
                "response": self._generate_eu_innovation_fund_confirmation_guidance(),
            }

        # Pattern 3: Climate clarification with innovation fund context
        if (has_innovation_fund_context or "innovation" in query_lower) and any(
            pattern in query_lower for pattern in climate_clarification_patterns
        ):
            # This should route to search_funding_calls for climate innovation
            return {
                "thought": "User wants climate/clean technology innovation funding. Searching for Horizon Europe Cluster 5 (Climate, Energy, Mobility) calls.",
                "action": "use_tool",
                "tool": "search_funding_calls",
                "args": {
                    "keywords": "climate innovation clean technology decarbonisation low-carbon",
                    "status": "open",
                    "programme": "horizon_europe",
                },
            }

        # Pattern 4: Grants clarification with innovation/climate context
        if (
            has_innovation_fund_context
            or "climate" in context_lower
            or "innovation" in context_lower
        ) and any(pattern in query_lower for pattern in grants_clarification_patterns):
            return {
                "thought": "User wants grant-based climate innovation funding (not loans). Providing guidance on Horizon Europe Cluster 5 grant options vs EU Innovation Fund.",
                "action": "generate_guidance",
                "guidance_type": "climate_innovation_grants",
                "response": self._generate_climate_innovation_grants_guidance(context_lower),
            }

        return None

    def _detect_work_programme_content_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect queries about work programme document content (topics, priorities, structure).

        This handles queries like:
        - "What topics are in the Horizon Europe digital work programme?"
        - "What are the 2025 work programme priorities for Cluster 5?"
        - "What does the work programme say about AI?"
        - "What areas are covered in the digital work programme?"

        These queries should use search_documents to find work programme content,
        NOT search_funding_calls (which finds open calls).

        The 2025 Work Programmes (WP-1 through WP-14) are indexed in the system.
        """
        query_lower = query.lower()

        # Pattern 1: Explicit work programme + content query
        # e.g., "What topics are in the work programme?", "What does the work programme say about...?"
        work_programme_patterns = [
            "work programme",
            "work-programme",
            "workprogramme",
            "wp-",  # e.g., "WP-7" for Digital cluster
        ]

        content_patterns = [
            "topic",
            "topics",
            "priorit",  # priorities, priority
            "cover",  # covers, covered, coverage
            "area",
            "focus",
            "say about",
            "says about",
            "include",
            "contain",
            "mention",
            "address",
            "structure",
            "overview",
            "destination",  # Horizon Europe destinations
            "main areas",
            "key areas",
            "research areas",
            "funding areas",
            "theme",
        ]

        # Must have work programme reference AND content-seeking pattern
        has_wp_reference = any(pattern in query_lower for pattern in work_programme_patterns)
        has_content_pattern = any(pattern in query_lower for pattern in content_patterns)

        if has_wp_reference and has_content_pattern:
            # Extract cluster/programme context for search
            cluster_context = self._extract_cluster_from_query(query_lower)
            year_context = self._extract_year_from_query(query_lower)

            # Build search query
            search_query = self._build_work_programme_search_query(
                query, cluster_context, year_context
            )

            return {
                "thought": f"User is asking about work programme content (topics/priorities). Using search_documents to find relevant work programme sections. Search: '{search_query}'",
                "action": "call_tools_and_format",
                "tool_calls": [
                    {
                        "tool": "search_documents",
                        "parameters": {
                            "query": search_query,
                            "document_type": "work_programme",
                            "max_results": 10,
                        },
                        "reasoning": "Searching work programme documents for topics and priorities",
                    }
                ],
                "needs_more_info": True,
                "format_type": "documents",
            }

        # Pattern 2: Cluster-specific work programme queries without explicit "work programme"
        # e.g., "What are Cluster 4 priorities?", "What does Cluster 5 focus on?"
        cluster_priority_patterns = [
            (r"cluster\s*[1-6]\s*(priorit|focus|topic|area)", "cluster"),
            (r"cl[1-6]\s*(priorit|focus|topic|area)", "cluster"),
            (
                r"(digital|health|climate|food|security|culture)\s*cluster.*(priorit|focus|topic)",
                "domain",
            ),
            (r"(2024|2025|2026)\s*(priorit|topic|focus).*(horizon|cluster)", "year_first"),
        ]

        import re

        for pattern, _pattern_type in cluster_priority_patterns:
            if re.search(pattern, query_lower):
                cluster_context = self._extract_cluster_from_query(query_lower)
                year_context = self._extract_year_from_query(query_lower)
                search_query = self._build_work_programme_search_query(
                    query, cluster_context, year_context
                )

                return {
                    "thought": f"User is asking about cluster priorities/topics. Using search_documents to find work programme content. Search: '{search_query}'",
                    "action": "call_tools_and_format",
                    "tool_calls": [
                        {
                            "tool": "search_documents",
                            "parameters": {
                                "query": search_query,
                                "document_type": "work_programme",
                                "max_results": 10,
                            },
                            "reasoning": "Searching work programme documents for cluster priorities",
                        }
                    ],
                    "needs_more_info": True,
                    "format_type": "documents",
                }

        return None

    def _extract_cluster_from_query(self, query_lower: str) -> str | None:
        """Extract cluster reference from query."""
        import re

        # Direct cluster number references
        cluster_match = re.search(r"cluster\s*([1-6])", query_lower)
        if cluster_match:
            return f"Cluster {cluster_match.group(1)}"

        cl_match = re.search(r"\bcl([1-6])\b", query_lower)
        if cl_match:
            return f"Cluster {cl_match.group(1)}"

        # Domain-based cluster mapping
        domain_cluster_map = {
            "health": "Cluster 1 Health",
            "medical": "Cluster 1 Health",
            "clinical": "Cluster 1 Health",
            "culture": "Cluster 2 Culture Creativity",
            "creative": "Cluster 2 Culture Creativity",
            "social": "Cluster 2 Culture Creativity",
            "democracy": "Cluster 2 Culture Creativity",
            "security": "Cluster 3 Civil Security",
            "cybersecurity": "Cluster 3 Civil Security",
            "disaster": "Cluster 3 Civil Security",
            "digital": "Cluster 4 Digital Industry Space",
            "ai": "Cluster 4 Digital Industry Space",
            "artificial intelligence": "Cluster 4 Digital Industry Space",
            "robotics": "Cluster 4 Digital Industry Space",
            "manufacturing": "Cluster 4 Digital Industry Space",
            "industry": "Cluster 4 Digital Industry Space",
            "space": "Cluster 4 Digital Industry Space",
            "quantum": "Cluster 4 Digital Industry Space",
            "semiconductor": "Cluster 4 Digital Industry Space",
            "climate": "Cluster 5 Climate Energy Mobility",
            "energy": "Cluster 5 Climate Energy Mobility",
            "hydrogen": "Cluster 5 Climate Energy Mobility",
            "transport": "Cluster 5 Climate Energy Mobility",
            "mobility": "Cluster 5 Climate Energy Mobility",
            "battery": "Cluster 5 Climate Energy Mobility",
            "renewable": "Cluster 5 Climate Energy Mobility",
            "food": "Cluster 6 Food Bioeconomy",
            "agriculture": "Cluster 6 Food Bioeconomy",
            "bioeconomy": "Cluster 6 Food Bioeconomy",
            "biodiversity": "Cluster 6 Food Bioeconomy",
            "environment": "Cluster 6 Food Bioeconomy",
            "soil": "Cluster 6 Food Bioeconomy",
            "water": "Cluster 6 Food Bioeconomy",
            "ocean": "Cluster 6 Food Bioeconomy",
        }

        for domain, cluster in domain_cluster_map.items():
            if domain in query_lower:
                return cluster

        return None

    def _extract_year_from_query(self, query_lower: str) -> str | None:
        """Extract year reference from query."""
        import re

        year_match = re.search(r"(2023|2024|2025|2026|2027)", query_lower)
        if year_match:
            return year_match.group(1)
        return None

    def _build_work_programme_search_query(
        self, original_query: str, cluster_context: str | None, year_context: str | None
    ) -> str:
        """Build an effective search query for work programme documents."""
        # Start with core terms
        search_terms = []

        # Add cluster context if available
        if cluster_context:
            search_terms.append(cluster_context)

        # Add year context - default to 2025 if not specified (latest WP)
        year = year_context or "2025"
        search_terms.append(f"{year} work programme")

        # Extract key topic terms from original query
        # Remove common words and focus on content-specific terms
        query_lower = original_query.lower()
        noise_words = {
            "what",
            "are",
            "the",
            "in",
            "for",
            "about",
            "does",
            "say",
            "says",
            "tell",
            "me",
            "show",
            "find",
            "list",
            "horizon",
            "europe",
            "work",
            "programme",
            "program",
            "topics",
            "priorities",
            "areas",
            "covered",
            "include",
            "contain",
            "mention",
            "overview",
            "structure",
            "focus",
        }

        words = query_lower.split()
        topic_terms = [w for w in words if w not in noise_words and len(w) > 2]

        # Add up to 3 topic-specific terms
        for term in topic_terms[:3]:
            if term not in " ".join(search_terms).lower():
                search_terms.append(term)

        # Add "topics priorities destinations" to improve semantic search
        search_terms.append("topics priorities destinations")

        return " ".join(search_terms)

    # ========================================================================
    # OUT-OF-SCOPE QUERY DETECTION AND GUIDANCE (NON-EU FUNDING PROGRAMMES)
    # ========================================================================

    def _detect_out_of_scope_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect queries about non-EU funding programmes (out of MAPIT's scope).

        These are questions about:
        - US funding programmes (NSF, NIH, DOE, DARPA, etc.)
        - UK funding programmes (UKRI, EPSRC, AHRC, MRC, BBSRC, etc.)
        - Other international programmes (Canadian NSERC, Australian ARC, etc.)
        - Comparisons between EU and non-EU programmes
        - Global equivalents to Horizon Europe

        The system should:
        1. Gracefully explain its EU funding specialization
        2. NOT make up detailed information about non-EU programmes
        3. Offer to help with EU funding comparisons where relevant
        4. Redirect users to appropriate resources
        5. Highlight similarities with EU programmes when discussing comparisons

        IMPORTANT: These queries should NOT trigger tool calls since we don't have
        authoritative data on non-EU programmes.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Track if out-of-scope programme context is present from previous turns
        has_out_of_scope_context = any(
            ind in context_lower
            for ind in [
                "nsf",
                "national science foundation",
                "ukri",
                "uk research",
                "epsrc",
                "engineering and physical sciences",
                "nih",
                "national institutes of health",
                "us funding",
                "us grants",
                "uk funding",
                "uk grants",
                "american funding",
                "british funding",
                "international programmes",
                "international funding",
                "global equivalents",
                "non-eu",
                "outside the eu",
                "out of scope",
            ]
        )

        # Non-EU funding programmes we should detect
        non_eu_programmes = {
            # US programmes
            "nsf": ["nsf", "national science foundation", "us nsf"],
            "nih": ["nih", "national institutes of health", "us nih"],
            "doe": ["doe ", "department of energy", "us doe"],
            "darpa": ["darpa", "defense advanced research"],
            "arpa": ["arpa-e", "arpa-h", "arpa"],
            "nasa": ["nasa research", "nasa grant", "nasa funding"],
            # UK programmes
            "ukri": ["ukri", "uk research and innovation"],
            "epsrc": ["epsrc", "engineering and physical sciences research council"],
            "ahrc": ["ahrc", "arts and humanities research council"],
            "mrc": ["mrc ", " mrc", "medical research council uk"],
            "bbsrc": ["bbsrc", "biotechnology and biological sciences"],
            "nerc": ["nerc", "natural environment research council"],
            "stfc": ["stfc", "science and technology facilities council"],
            "esrc": ["esrc", "economic and social research council"],
            "innovate_uk": ["innovate uk", "innovate-uk", "uk innovate"],
            # Other international
            "nserc": ["nserc", "natural sciences and engineering research council"],
            "cihr": ["cihr", "canadian institutes of health research"],
            "arc": ["arc australia", "australian research council"],
            "dfg": ["dfg", "deutsche forschungsgemeinschaft", "german research foundation"],
            "anr": ["anr ", "agence nationale de la recherche"],
            "jsps": ["jsps", "japan society for the promotion of science"],
        }

        # === Pattern 1: Direct questions about non-EU programmes ===
        # e.g., "Tell me about NSF grants", "What about UK Research Council funding?"
        detected_programme = None
        for prog_key, patterns in non_eu_programmes.items():
            if any(p in query_lower for p in patterns):
                detected_programme = prog_key
                break

        # Check for UK/US research council patterns
        uk_research_patterns = [
            "uk research council",
            "uk research councils",
            "british research council",
            "epsrc",
            "the old epsrc",
        ]
        us_research_patterns = [
            "us research",
            "american research funding",
            "american grants",
            "us grants",
            "usa funding",
        ]

        if any(p in query_lower for p in uk_research_patterns):
            detected_programme = "ukri"
        elif any(p in query_lower for p in us_research_patterns):
            detected_programme = "nsf"

        # If a non-EU programme is mentioned in the query
        if detected_programme:
            guidance = self._generate_out_of_scope_explanation_guidance(detected_programme)
            return {
                "thought": f"User is asking about {detected_programme.upper()}, a non-EU programme outside MAPIT's scope. Explaining EU focus and offering EU alternatives.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "out_of_scope_explanation",
                "detected_programme": detected_programme,
                "confidence": 0.95,
                "needs_more_info": False,
            }

        # === Pattern 2: Comparison with EU programmes (follow-up in context) ===
        # e.g., "Can you compare these international programmes with EU funding?"
        # e.g., "How does Horizon Europe stack up?"
        comparison_patterns = [
            "compare these",
            "compare international",
            "compare with eu",
            "how does horizon europe compare",
            "how does he compare",
            "how does eu compare",
            "stack up",
            "versus horizon",
            "vs horizon",
            "compared to horizon",
            "difference between",
            "differences from",
        ]

        # Check for comparison queries when we have out-of-scope context
        if has_out_of_scope_context and any(p in query_lower for p in comparison_patterns):
            guidance = self._generate_eu_international_comparison_guidance()
            return {
                "thought": "User is asking to compare international programmes with EU funding. Providing high-level comparison with Horizon Europe.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "eu_international_comparison",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Global equivalents to Horizon Europe ===
        # e.g., "What international research programmes are similar to Horizon Europe?"
        # e.g., "Are there any global equivalents?"
        equivalents_patterns = [
            "global equivalent",
            "global equivalents",
            "international equivalent",
            "international equivalents",
            "similar to horizon europe",
            "similar international",
            "international research programmes similar",
            "programmes are similar to horizon",
            "programmes similar to horizon",
            "like horizon europe",
            "comparable to horizon",
            "comparable programmes",
            "worldwide equivalent",
            "world equivalent",
        ]

        if any(p in query_lower for p in equivalents_patterns):
            guidance = self._generate_global_equivalents_guidance()
            return {
                "thought": "User is asking about global equivalents to Horizon Europe. Providing overview of MAPIT's EU focus and high-level comparison.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "global_equivalents",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_strategic_planning_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect strategic planning / funding strategy queries.

        This handles queries like:
        - "Help me plan our research funding strategy for the next 3 years"
        - "We're a university department focusing on cybersecurity" (context building)
        - "What Horizon Europe options do we have?"
        - "How should we sequence our applications?"

        Strategic queries benefit from programme recommendations and context-aware responses.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Patterns for strategic planning queries
        strategic_patterns = [
            "funding strategy",
            "funding plan",
            "multi-year plan",
            "3 year plan",
            "3-year plan",
            "next 3 years",
            "next three years",
            "strategic plan",
            "plan our research",
            "plan our funding",
            "sequence our applications",
            "sequencing applications",
            "application strategy",
            "what options do we have",
            "options for us",
        ]

        # Context-building patterns (organization + research focus)
        context_building_patterns = [
            "we're a ",
            "we are a ",
            "our department",
            "our organization",
            "our organisation",
            "our university",
            "our institute",
            "i work at",
            "we work on",
            "we focus on",
            "focusing on",
            "our research area",
            "our research areas",  # Added: plural form
            "our areas are",  # Added: "Our research areas are:"
            "our team",
        ]

        # Domain/sector patterns
        domain_patterns = {
            "cybersecurity": ["cybersecurity", "cyber security", "cyber-security"],
            "ai_robotics": [
                "artificial intelligence",
                "machine learning",
                " ai ",
                "ai/ml",
                "robotics",
                "robot",
                "human-machine",
                "human machine",
                "hmi",
                "hci",
                "automation",
                "autonomous",
            ],  # Combined AI + Robotics + HMI
            "ai": ["artificial intelligence", "machine learning", " ai ", "ai/ml"],
            "healthcare": ["healthcare", "health care", "medical", "health sector"],
            "energy": ["clean energy", "renewable energy", "energy transition"],
            "climate": ["climate", "sustainability", "environment"],
            "digital": ["digital transformation", "digitalization", "digitization"],
            "biotech": ["biotechnology", "biotech", "life sciences"],
            "quantum": ["quantum computing", "quantum technology"],
        }

        is_strategic_query = any(pattern in query_lower for pattern in strategic_patterns)
        is_context_building = any(pattern in query_lower for pattern in context_building_patterns)

        # Detect research domain from query
        detected_domain = None
        for domain, patterns in domain_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                detected_domain = domain
                break

        # If context building with a research domain, provide strategic guidance + search calls
        if is_context_building and detected_domain:
            # Extract organization type description
            org_type_desc = ""
            if any(x in query_lower for x in ["university", "department", "academic"]):
                org_type_desc = "university/academic institution"
            elif any(x in query_lower for x in ["sme", "startup", "company"]):
                org_type_desc = "SME/company"
            elif any(x in query_lower for x in ["institute", "research center", "research centre"]):
                org_type_desc = "research institute"

            # Build strategic context response
            strategic_intro = (
                f"As a {org_type_desc or 'organization'} focusing on **{detected_domain}**, "
            )

            if detected_domain == "cybersecurity":
                cluster_info = "you align well with **Cluster 3** (Civil Security for Society) and **Cluster 4** (Digital, Industry and Space)"
                search_keywords = "cybersecurity digital security"
            elif detected_domain == "ai_robotics":
                cluster_info = "you align with **Cluster 4** (Digital, Industry and Space) covering AI, Robotics, and Human-Machine Interaction. This is a highly strategic area in Horizon Europe"
                search_keywords = "AI robotics human machine interaction autonomous"
            elif detected_domain == "ai":
                cluster_info = "you align with **Cluster 4** (Digital, Industry and Space) and cross-cutting AI initiatives"
                search_keywords = "artificial intelligence AI digital"
            elif detected_domain == "healthcare":
                cluster_info = (
                    "you align with **Cluster 1** (Health) and digital health initiatives"
                )
                search_keywords = "health medical clinical"
            elif detected_domain == "energy":
                cluster_info = "you align with **Cluster 5** (Climate, Energy and Mobility)"
                search_keywords = "energy renewable clean energy"
            elif detected_domain == "climate":
                cluster_info = "you align with **Cluster 5** (Climate, Energy and Mobility) and **Cluster 6** (Food, Bioeconomy)"
                search_keywords = "climate sustainability environment"
            else:
                cluster_info = "you have multiple relevant Horizon Europe clusters to explore"
                search_keywords = detected_domain

            return {
                "thought": f"User is providing context about their organization ({org_type_desc or 'organization'}) with focus on {detected_domain}. Searching for relevant calls to provide concrete options.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "search_funding_calls",
                        "parameters": {"keywords": search_keywords, "status": "open"},
                        "reasoning": f"Finding open calls relevant to {detected_domain} for strategic planning",
                    }
                ],
                "needs_more_info": True,
                "context_prefix": f"{strategic_intro}{cluster_info}.\n\nHere are currently open funding opportunities relevant to your focus:\n\n",
                "context_suffix": "\n\n---\n\n🎯 **Next Steps:**\n• Review the calls above and identify 2-3 that match your capabilities\n• Check [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/) for full call details\n• Consider your role preference: coordinator vs partner (universities often start as partners)\n• Share more details about your specific research focus for tailored recommendations",
            }

        # If asking about strategic planning (without domain context), recommend programmes
        if is_strategic_query:
            return {
                "thought": "User is asking about strategic funding planning. Using recommend_programmes to provide an overview of options.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "recommend_programmes",
                        "parameters": {},
                        "reasoning": "Providing strategic overview of EU funding programmes for multi-year planning",
                    }
                ],
                "needs_more_info": True,
                "context_suffix": "\n\n---\n\n🎯 **Next Steps:**\n• Share your organization type (university, SME, research institute)\n• Tell me your research focus area for personalized recommendations\n• Indicate your experience level with EU funding (first-time vs experienced)\n• Let me know your preferred role: coordinator or participant",
            }

        # Check if context has strategic planning context and query asks about options
        options_patterns = [
            "what options",
            "which options",
            "horizon europe options",
            "our options",
            "available for us",
        ]

        if any(pattern in query_lower for pattern in options_patterns):
            # Check context for research domain
            for domain, patterns in domain_patterns.items():
                if any(pattern in context_lower for pattern in patterns):
                    detected_domain = domain
                    break

            if detected_domain:
                if detected_domain == "cybersecurity":
                    search_keywords = "cybersecurity digital security"
                elif detected_domain == "ai":
                    search_keywords = "artificial intelligence AI"
                elif detected_domain == "healthcare":
                    search_keywords = "health medical"
                else:
                    search_keywords = detected_domain

                return {
                    "thought": f"User is asking about Horizon Europe options. Context indicates {detected_domain} focus. Searching for relevant calls.",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": "search_funding_calls",
                            "parameters": {"keywords": search_keywords, "status": "open"},
                            "reasoning": f"Finding Horizon Europe options for {detected_domain}",
                        }
                    ],
                    "needs_more_info": True,
                }

        return None

    def _detect_capacity_building_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect capacity building / newcomer guidance queries.

        These are questions from organizations NEW to EU funding who need guidance on:
        - Best programmes for beginners
        - Partner vs coordinator role
        - First project size recommendations
        - Building track record
        - How to get started

        These queries should provide structured guidance with Next Steps, not tool calls.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Detect if the user is new to EU funding (from context or query)
        is_newcomer = any(
            pattern in query_lower or pattern in context_lower
            for pattern in [
                "new to eu funding",
                "new to eu",
                "first time",
                "we're new",
                "we are new",
                "never applied",
                "never submitted",
                "no experience",
                "beginner",
                "getting started",
                "how do we get started",
                "how do i get started",
                "new to horizon",
            ]
        )

        # Query patterns for specific capacity building guidance
        beginner_programme_patterns = [
            "best for beginners",
            "best for beginner",
            "programme for beginners",
            "programs for beginners",
            "programmes for beginners",
            "which programme is best",
            "which program is best",
            "easiest programme",
            "easiest program",
            "simpler programme",
            "beginner friendly",
            "beginner-friendly",
            "entry point",
            "where to start",
            "good starting point",
            "first programme",
            "first program",
        ]

        partner_vs_coordinator_patterns = [
            "partner or coordinator",
            "coordinator or partner",
            "start as partner",
            "start as coordinator",
            "should we coordinate",
            "should we be coordinator",
            "should we lead",
            "should we be partner",
            "participant or leader",
            "begin as partner",
            "begin as coordinator",
            "first project coordinator",
            "first project partner",
        ]

        first_project_size_patterns = [
            "first project size",
            "good first project",
            "appropriate size",
            "project size for beginners",
            "beginner project size",
            "starting project size",
            "small project to start",
            "what size project",
            "how big should first",
            "manageable first project",
        ]

        track_record_patterns = [
            "build track record",
            "building track record",
            "develop track record",
            "establish track record",
            "how do we build",
            "how to build track",
            "gain track record",
            "create track record",
            "track record strategy",
            "track record advice",
            "build experience",
            "build our experience",
        ]

        # First-time applicant "where do I start" / "how do I start" patterns
        first_time_applicant_patterns = [
            "where do i start",
            "where should i start",
            "where do we start",
            "where should we start",
            "how do i start",
            "how should i start",
            "how do we start",
            "how should we start",
            "how do i begin",
            "how do we begin",
            "where do i begin",
            "where do we begin",
            "what should i do first",
            "what should we do first",
            "first steps",
            "getting started",
            "how to begin",
            "how to start",
        ]

        # Check for first-time applicant "where do I start" type queries
        # These need step-by-step onboarding guidance, not programme recommendations
        is_first_time_applicant = is_newcomer and any(
            pattern in query_lower for pattern in first_time_applicant_patterns
        )

        if is_first_time_applicant:
            return {
                "thought": "User is a first-time applicant asking where to start. Providing step-by-step onboarding guidance.",
                "action": "generate_guidance",
                "guidance_type": "first_time_applicant",
                "response": self._generate_first_time_applicant_guidance(),
            }

        # Check for beginner-friendly programme query
        if any(pattern in query_lower for pattern in beginner_programme_patterns) or (
            is_newcomer
            and any(
                p in query_lower
                for p in [
                    "which programme",
                    "which program",
                    "best programme",
                    "best program",
                    "recommend",
                ]
            )
        ):
            return {
                "thought": "User is asking about beginner-friendly programmes. Providing structured guidance from built-in knowledge.",
                "action": "generate_guidance",
                "guidance_type": "beginner_programmes",
                "response": self._generate_beginner_programmes_guidance(),
            }

        # Check for partner vs coordinator query
        if any(pattern in query_lower for pattern in partner_vs_coordinator_patterns):
            return {
                "thought": "User is asking about partner vs coordinator role for newcomers. Providing capacity building guidance.",
                "action": "generate_guidance",
                "guidance_type": "partner_vs_coordinator",
                "response": self._generate_partner_coordinator_guidance(is_newcomer),
            }

        # Check for first project size query
        if any(pattern in query_lower for pattern in first_project_size_patterns) or (
            is_newcomer and any(p in query_lower for p in ["project size", "how big", "size"])
        ):
            return {
                "thought": "User is asking about appropriate first project size. Providing beginner-appropriate guidance.",
                "action": "generate_guidance",
                "guidance_type": "first_project_size",
                "response": self._generate_first_project_size_guidance(),
            }

        # Check for track record building query
        if any(pattern in query_lower for pattern in track_record_patterns):
            return {
                "thought": "User is asking about building track record. Providing strategic guidance.",
                "action": "generate_guidance",
                "guidance_type": "track_record",
                "response": self._generate_track_record_guidance(),
            }

        return None

    def _detect_application_process_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect application process queries for EU funding programmes.

        These are questions about HOW to apply for EU funding, requesting step-by-step
        guidance with actionable steps and links.

        Examples:
        - "How do I apply for Horizon Europe?"
        - "What are the steps to apply for EU funding?"
        - "Can you explain the Horizon Europe application process?"
        - "How can I apply to Erasmus+?"
        - "What's the application process for Creative Europe?"

        Note: These are DIFFERENT from first-time applicant queries ("where do I start")
        because they are more action-oriented and may come from users who already
        know they want to apply.
        """
        query_lower = query.lower()
        logger.info(f"🔍 _detect_application_process_query called with: {query[:80]}")

        # Application process patterns - more action-oriented than "where do I start"
        application_patterns = [
            r"how\s+(?:do\s+i|can\s+i|to)\s+apply",
            r"what\s+(?:are|is)\s+the\s+(?:application\s+)?(?:steps|process)",
            r"explain\s+(?:the\s+)?application\s+process",
            r"application\s+process\s+for",
            r"process\s+(?:of\s+)?apply",
            r"steps\s+to\s+apply",
            r"how\s+(?:do|can)\s+(?:we|i)\s+submit",
        ]

        # Programme mentions
        programme_patterns = [
            ("horizon europe", "horizon"),
            ("erasmus", "erasmus"),
            ("creative europe", "creative_europe"),
            ("digital europe", "digital_europe"),
            ("eu4health", "eu4health"),
            ("life programme", "life"),
            ("eu funding", "general"),
            ("european funding", "general"),
        ]

        import re

        # Check for application process pattern
        has_application_pattern = any(re.search(pat, query_lower) for pat in application_patterns)

        if not has_application_pattern:
            return None

        # Determine which programme is mentioned
        detected_programme = None
        for prog_pattern, prog_key in programme_patterns:
            if prog_pattern in query_lower:
                detected_programme = prog_key
                break

        # Default to general EU funding if no specific programme mentioned
        if detected_programme is None:
            # Check for generic application process query
            if "eu" in query_lower or "european" in query_lower:
                detected_programme = "general"
            else:
                # Not an EU funding application query
                return None

        # Generate appropriate guidance
        if detected_programme == "horizon":
            guidance = self._generate_horizon_application_guidance()
        elif detected_programme == "erasmus":
            guidance = self._generate_erasmus_application_guidance()
        elif detected_programme == "creative_europe":
            guidance = self._generate_creative_europe_application_guidance()
        else:
            # General EU funding guidance (covers all programmes)
            guidance = self._generate_general_eu_application_guidance()

        return {
            "thought": f"User is asking about the application process for {detected_programme}. Providing step-by-step actionable guidance.",
            "action": "generate_guidance",
            "guidance_type": "application_process",
            "programme": detected_programme,
            "response": guidance,
        }

    def _detect_eic_accelerator_eligibility_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect EIC Accelerator eligibility queries (including multi-part questions).

        These are questions about:
        - EIC Accelerator eligibility for SMEs
        - EIC Accelerator deadlines and cut-off dates
        - EIC Accelerator budget ranges (grant and equity)
        - Combined questions asking about eligibility + deadlines + budget

        Examples:
        - "Am I eligible for EIC Accelerator? What's the deadline? What budget?"
        - "Can an SME from Netherlands apply for EIC Accelerator?"
        - "I'm an SME - am I eligible for EIC Accelerator?"
        - "What are the EIC Accelerator requirements for SMEs?"
        """
        query_lower = query.lower()

        # Must mention EIC Accelerator specifically
        has_eic_accelerator = any(
            pattern in query_lower
            for pattern in [
                "eic accelerator",
                "eic-accelerator",
                "european innovation council accelerator",
            ]
        )

        if not has_eic_accelerator:
            return None

        # Check if this is an eligibility-related question
        eligibility_indicators = [
            "eligible",
            "eligibility",
            "can i",
            "can we",
            "am i",
            "are we",
            "can an sme",
            "can a company",
            "can my company",
            "requirements",
            "apply for",
            "apply to",
            "participate",
        ]
        has_eligibility_question = any(ind in query_lower for ind in eligibility_indicators)

        # Check if this is asking about deadlines
        deadline_indicators = [
            "deadline",
            "when",
            "cut-off",
            "cutoff",
            "closing date",
            "submission date",
        ]
        has_deadline_question = any(ind in query_lower for ind in deadline_indicators)

        # Check if this is asking about budget
        budget_indicators = [
            "budget",
            "how much",
            "funding",
            "grant amount",
            "grant size",
            "can i request",
            "can we request",
            "money",
            "million",
        ]
        has_budget_question = any(ind in query_lower for ind in budget_indicators)

        # Check if this is a multi-part question (at least 2 of 3 parts)
        is_multi_part = (
            sum([has_eligibility_question, has_deadline_question, has_budget_question]) >= 2
        )

        # Check if user mentions being an SME
        mentions_sme = any(
            pattern in query_lower
            for pattern in ["sme", "small", "medium", "startup", "company", "enterprise"]
        )

        # Extract country if mentioned
        country = None
        eu_countries = [
            "austria",
            "belgium",
            "bulgaria",
            "croatia",
            "cyprus",
            "czech republic",
            "denmark",
            "estonia",
            "finland",
            "france",
            "germany",
            "greece",
            "hungary",
            "ireland",
            "italy",
            "latvia",
            "lithuania",
            "luxembourg",
            "malta",
            "netherlands",
            "poland",
            "portugal",
            "romania",
            "slovakia",
            "slovenia",
            "spain",
            "sweden",
        ]
        associated_countries = [
            "iceland",
            "liechtenstein",
            "norway",
            "north macedonia",
            "serbia",
            "turkey",
            "israel",
            "switzerland",
            "uk",
            "united kingdom",
        ]
        for c in eu_countries + associated_countries:
            if c in query_lower:
                country = c.title()
                break

        # Only trigger if this is asking about EIC Accelerator eligibility/deadline/budget
        if (
            has_eligibility_question
            or has_deadline_question
            or has_budget_question
            or is_multi_part
        ):
            # Build thought message dynamically
            thought_parts = ["User is asking about EIC Accelerator"]
            if has_eligibility_question:
                thought_parts.append(" eligibility")
            if has_deadline_question:
                thought_parts.append(", deadline")
            if has_budget_question:
                thought_parts.append(", and budget")
            if mentions_sme:
                thought_parts.append(" for an SME")
            if country:
                thought_parts.append(f" from {country}")
            thought_parts.append(". Providing comprehensive EIC Accelerator guidance.")
            thought_message = "".join(thought_parts)

            return {
                "thought": thought_message,
                "action": "generate_guidance",
                "guidance_type": "eic_accelerator_eligibility",
                "response": self._generate_eic_accelerator_eligibility_guidance(
                    has_eligibility=has_eligibility_question or is_multi_part,
                    has_deadline=has_deadline_question or is_multi_part,
                    has_budget=has_budget_question or is_multi_part,
                    country=country,
                    is_sme=mentions_sme,
                ),
            }

        return None

    def _detect_eic_risk_assessment_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect EIC Accelerator risk assessment queries.

        These are questions about:
        - Risks of applying to EIC Accelerator
        - Impact of prior EU funding on EIC chances
        - Company size requirements and impact
        - The interview stage and how to prepare
        - Strategies to improve success odds

        These queries should provide structured guidance with Next Steps, not tool calls.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Check if context is about EIC Accelerator (from previous turns)
        is_eic_context = any(
            pattern in context_lower
            for pattern in [
                "eic accelerator",
                "eic",
                "accelerator",
                "european innovation council",
                "risks of applying",
                "improve our odds",
            ]
        )

        # Prior funding impact patterns
        prior_funding_patterns = [
            "don't have prior",
            "no prior funding",
            "without prior funding",
            "lack prior",
            "haven't had eu funding",
            "no eu funding",
            "no previous funding",
            "what if we don't have",
            "if we don't have prior",
            "without eu funding",
            "no track record",
            "no eu experience",
            "first time applying",
        ]

        # Interview stage patterns
        interview_patterns = [
            "interview stage",
            "about the interview",
            "interview process",
            "eic interview",
            "what about the interview",
            "pitch stage",
            "pitch preparation",
            "jury interview",
            "panel interview",
            "face to face",
            "face-to-face",
            "final stage",
            "how to prepare for interview",
            "interview preparation",
        ]

        # Improve odds/success patterns
        improve_odds_patterns = [
            "improve our odds",
            "improve my odds",
            "improve our chances",
            "improve my chances",
            "increase our chances",
            "increase our odds",
            "better our chances",
            "how can we improve",
            "what can we do to improve",
            "how to succeed",
            "how to be successful",
            "tips for success",
            "strategies to improve",
            "boost our chances",
            "maximize chances",
            "success strategies",
        ]

        # Company size patterns (in EIC context)
        company_size_patterns = [
            "company size",
            "our company size",
            "how does size affect",
            "does company size",
            "size affect chances",
            "sme requirements",
            "sme eligibility",
            "too small",
            "too large",
            "employee count",
            "startup size",
        ]

        # Initial EIC risk assessment patterns (first query about EIC risks)
        eic_risk_patterns = [
            "risks of applying to eic",
            "eic accelerator risks",
            "risks of eic",
            "what are the risks of eic",
            "risks associated with eic",
            "challenges of eic",
            "eic accelerator challenges",
            "difficulties of eic",
            "risks of applying to the eic",
            "downsides of eic",
        ]

        # Check for initial EIC risk assessment query (doesn't need context)
        if any(pattern in query_lower for pattern in eic_risk_patterns) or (
            "eic" in query_lower
            and "accelerator" in query_lower
            and any(
                w in query_lower for w in ["risk", "risks", "challenge", "challenges", "difficult"]
            )
        ):
            return {
                "thought": "User is asking about risks of EIC Accelerator. Providing comprehensive risk assessment guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_risks_overview",
                "response": self._generate_eic_risks_overview_guidance(),
            }

        # Check for prior funding impact query (in EIC context)
        if any(pattern in query_lower for pattern in prior_funding_patterns) and is_eic_context:
            return {
                "thought": "User is asking about EIC Accelerator with no prior EU funding. Providing EIC-specific guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_prior_funding",
                "response": self._generate_eic_prior_funding_guidance(),
            }

        # Check for interview stage query (in EIC context or explicitly about interview)
        if any(pattern in query_lower for pattern in interview_patterns) or (
            is_eic_context and "interview" in query_lower
        ):
            return {
                "thought": "User is asking about EIC Accelerator interview stage. Providing interview preparation guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_interview",
                "response": self._generate_eic_interview_guidance(),
            }

        # Check for improve odds query (in EIC context)
        if any(pattern in query_lower for pattern in improve_odds_patterns) and is_eic_context:
            return {
                "thought": "User is asking how to improve EIC Accelerator success odds. Providing strategic guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_improve_odds",
                "response": self._generate_eic_improve_odds_guidance(),
            }

        # Check for company size query in EIC context
        if any(pattern in query_lower for pattern in company_size_patterns) and is_eic_context:
            return {
                "thought": "User is asking about company size impact on EIC Accelerator. Providing eligibility and impact guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_company_size",
                "response": self._generate_eic_company_size_guidance(),
            }

        return None

    def _detect_funding_type_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect funding type explanation queries.

        These are questions about Horizon Europe action types:
        - RIA (Research and Innovation Action)
        - IA (Innovation Action)
        - CSA (Coordination and Support Action)
        - MSCA (Marie Skłodowska-Curie Actions)
        - EIC Pathfinder
        - ERC (European Research Council)

        Covers:
        - Direct explanations: "What is CSA?", "Explain RIA"
        - Comparisons: "Compare RIA vs IA", "Difference between RIA and IA"
        - Follow-ups in funding type context: "What about CSA?", "How does X differ?"
        - Freedom/flexibility questions: "Which gives most freedom?"

        These should use built-in knowledge, NOT tool calls.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Check if context is about funding type comparison (from previous turns)
        is_funding_type_context = any(
            pattern in context_lower
            for pattern in [
                "compare ria",
                "compare ia",
                "ria vs ia",
                "ia vs ria",
                "funding type",
                "action type",
                "research and innovation action",
                "innovation action",
                "coordination and support",
                "msca postdoctoral",
                "eic pathfinder",
                "100% funding",
                "70% funding",
            ]
        )

        # Direct funding type explanation patterns
        # Note: Many patterns now use non-greedy word matching to capture variations like
        # "What is RIA funding?", "What does RIA stand for?", "RIA meaning", etc.
        funding_type_explain_patterns = [
            r"what is (?:a |an )?(?:ria|ia|csa)(?:\s+\w+)?(?:\?|$|\s|\.)",
            r"what are (?:ria|ia|csa)s?(?:\?|$|\s|\.)",
            r"explain (?:ria|ia|csa)\b",
            r"tell me about (?:ria|ia|csa)\b",
            r"what does (?:ria|ia|csa) (?:stand for|mean)",
            r"what is (?:a )?research and innovation action",
            r"what is (?:an )?innovation action",
            r"what is (?:a )?coordination and support",
            r"(?:ria|ia|csa) (?:meaning|definition|explanation)",
            r"define (?:ria|ia|csa)\b",
        ]

        # RIA vs IA comparison patterns
        ria_ia_comparison_patterns = [
            "ria vs ia",
            "ia vs ria",
            "compare ria",
            "compare ia",
            "ria and ia",
            "ia and ria",
            "difference between ria and ia",
            "difference between ia and ria",
            "ria or ia",
            "ia or ria",
            "ria versus ia",
            "ia versus ria",
        ]

        # CSA follow-up patterns (when in funding type context)
        csa_followup_patterns = [
            "what about csa",
            "and csa",
            "how about csa",
            "tell me about csa",
            "what is csa",
            "explain csa",
            "coordination and support",
        ]

        # EIC Pathfinder patterns
        eic_pathfinder_patterns = [
            "eic pathfinder",
            "pathfinder differ",
            "how does pathfinder",
            "what is pathfinder",
            "about pathfinder",
            "pathfinder vs",
            "vs pathfinder",
        ]

        # MSCA patterns
        msca_patterns = [
            "msca postdoctoral",
            "msca fellowship",
            "marie curie",
            "marie sklodowska",
            "postdoctoral fellowship",
            "what about msca",
            "msca-pf",
        ]

        # Freedom/flexibility question patterns (when in funding type context)
        freedom_patterns = [
            "which gives the most freedom",
            "which has most freedom",
            "which offers most freedom",
            "most flexible",
            "most flexibility",
            "most autonomy",
            "most independence",
            "most freedom",
            "greatest freedom",
            "which is most open",
            "which allows most",
            "bottom-up",
            "researcher-driven",
        ]

        # Check for RIA vs IA comparison
        if any(pattern in query_lower for pattern in ria_ia_comparison_patterns):
            return {
                "thought": "User is asking to compare RIA vs IA action types. Providing comprehensive comparison from built-in knowledge.",
                "action": "generate_guidance",
                "guidance_type": "ria_ia_comparison",
                "response": self._generate_ria_ia_comparison_guidance(),
            }

        # Check for CSA explanation/follow-up
        if any(pattern in query_lower for pattern in csa_followup_patterns) or (
            is_funding_type_context and "csa" in query_lower
        ):
            return {
                "thought": "User is asking about CSA (Coordination and Support Actions). Providing detailed CSA explanation.",
                "action": "generate_guidance",
                "guidance_type": "csa_explanation",
                "response": self._generate_csa_explanation_guidance(),
            }

        # Check for EIC Pathfinder explanation
        if any(pattern in query_lower for pattern in eic_pathfinder_patterns) or (
            is_funding_type_context and "pathfinder" in query_lower
        ):
            return {
                "thought": "User is asking about EIC Pathfinder. Providing detailed EIC Pathfinder explanation.",
                "action": "generate_guidance",
                "guidance_type": "eic_pathfinder_explanation",
                "response": self._generate_eic_pathfinder_explanation_guidance(),
            }

        # Check for MSCA explanation
        if any(pattern in query_lower for pattern in msca_patterns) or (
            is_funding_type_context and ("msca" in query_lower or "postdoctoral" in query_lower)
        ):
            return {
                "thought": "User is asking about MSCA Postdoctoral Fellowships. Providing detailed MSCA-PF explanation.",
                "action": "generate_guidance",
                "guidance_type": "msca_explanation",
                "response": self._generate_msca_explanation_guidance(),
            }

        # Check for freedom/flexibility question (in funding type context)
        if any(pattern in query_lower for pattern in freedom_patterns) and is_funding_type_context:
            return {
                "thought": "User is asking which funding type offers most freedom. Providing freedom comparison.",
                "action": "generate_guidance",
                "guidance_type": "funding_type_freedom",
                "response": self._generate_funding_type_freedom_guidance(),
            }

        # Check for generic funding type explanation using regex
        import re

        for pattern in funding_type_explain_patterns:
            if re.search(pattern, query_lower):
                # Determine which funding type
                if "csa" in query_lower or "coordination" in query_lower:
                    return {
                        "thought": "User is asking about CSA. Providing CSA explanation.",
                        "action": "generate_guidance",
                        "guidance_type": "csa_explanation",
                        "response": self._generate_csa_explanation_guidance(),
                    }
                elif "ia" in query_lower and "ria" not in query_lower:
                    return {
                        "thought": "User is asking about IA. Providing IA explanation.",
                        "action": "generate_guidance",
                        "guidance_type": "ia_explanation",
                        "response": self._generate_ia_explanation_guidance(),
                    }
                elif "ria" in query_lower:
                    return {
                        "thought": "User is asking about RIA. Providing RIA explanation.",
                        "action": "generate_guidance",
                        "guidance_type": "ria_explanation",
                        "response": self._generate_ria_explanation_guidance(),
                    }

        return None

    def _detect_simple_programme_overview_query(
        self, query: str, context: str = ""
    ) -> dict[str, Any] | None:
        """Detect simple FAQ queries about EU funding programmes.

        These are basic overview questions that can be answered from built-in knowledge
        without tool calls to ensure fast response times (<2s first token, <5s complete).

        Patterns:
        - "What is Horizon Europe?"
        - "Tell me about Erasmus+"
        - "Explain the LIFE programme"
        - "What is Creative Europe?"
        - "What is Digital Europe Programme?"
        - "What is EU4Health?"
        """
        query_lower = query.lower().strip()

        # Programme overview patterns - these ask about what a programme IS (not calls/eligibility)
        programme_overview_patterns = [
            # Horizon Europe
            (r"what is horizon europe\??", "horizon_europe"),
            (r"what'?s horizon europe\??", "horizon_europe"),
            (r"tell me about horizon europe", "horizon_europe"),
            (r"explain horizon europe", "horizon_europe"),
            (r"horizon europe overview", "horizon_europe"),
            (r"describe horizon europe", "horizon_europe"),
            # Erasmus+
            (r"what is erasmus\+?\??", "erasmus_plus"),
            (r"what'?s erasmus\+?\??", "erasmus_plus"),
            (r"tell me about erasmus\+?", "erasmus_plus"),
            (r"explain erasmus\+?", "erasmus_plus"),
            (r"erasmus\+? overview", "erasmus_plus"),
            # Creative Europe
            (r"what is creative europe\??", "creative_europe"),
            (r"tell me about creative europe", "creative_europe"),
            (r"explain creative europe", "creative_europe"),
            # LIFE Programme
            (r"what is (?:the )?life programme\??", "life"),
            (r"tell me about (?:the )?life programme", "life"),
            (r"explain (?:the )?life programme", "life"),
            # Digital Europe
            (r"what is (?:the )?digital europe(?:\s+programme)?\??", "digital_europe"),
            (r"tell me about (?:the )?digital europe", "digital_europe"),
            (r"explain (?:the )?digital europe", "digital_europe"),
            # EU4Health
            (r"what is eu4health\??", "eu4health"),
            (r"tell me about eu4health", "eu4health"),
            (r"explain eu4health", "eu4health"),
        ]

        for pattern, programme in programme_overview_patterns:
            if re.search(pattern, query_lower):
                guidance = self._generate_programme_overview_guidance(programme)
                if guidance:
                    return {
                        "thought": f"User is asking about {programme.replace('_', ' ').title()}. Providing programme overview from built-in knowledge.",
                        "action": "generate_guidance",
                        "guidance_type": f"{programme}_overview",
                        "response": guidance,
                    }

        return None

    def _detect_context_recall_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query references earlier conversation context to find calls.

        This handles queries like:
        - "I mentioned earlier I work on hydrogen - any new calls open right now?"
        - "As I said before, I'm in healthcare - what calls are available?"
        - "Remember I work on AI? Are there any open calls?"
        - "Going back to my hydrogen research, any funding?"
        - "Any new [topic] calls" (where topic was mentioned earlier)

        These should recall context from earlier and use search_funding_calls.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Patterns that indicate user is referencing earlier conversation
        recall_patterns = [
            "i mentioned earlier",
            "as i said",
            "as i mentioned",
            "remember i",
            "i said before",
            "i told you",
            "going back to",
            "back to my",
            "you know i work on",
            "you know i'm working on",
            "earlier i said",
            "my earlier",
            "i previously mentioned",
        ]

        # Check if query contains recall pattern
        has_recall_pattern = any(pattern in query_lower for pattern in recall_patterns)

        # Also check for "any [topic] calls" pattern where topic might be from context
        any_calls_match = re.search(
            r"any\s+(?:new\s+)?(\w+(?:\s+\w+)?)\s+calls?",
            query_lower,
        )

        # Check for "[topic] calls open" pattern
        calls_open_match = re.search(
            r"(\w+(?:\s+\w+)?)\s+calls?\s+(?:open|available)",
            query_lower,
        )

        if not has_recall_pattern and not any_calls_match and not calls_open_match:
            return None

        # Extract topic from query
        topic_from_query = None

        # First try to extract topic from query patterns
        topic_patterns = [
            r"work\s+on\s+(\w+(?:\s+\w+)?)",
            r"working\s+on\s+(\w+(?:\s+\w+)?)",
            r"research\s+(?:in|on)\s+(\w+(?:\s+\w+)?)",
            r"any\s+(?:new\s+)?(\w+(?:\s+\w+)?)\s+calls?",
            r"(\w+(?:\s+\w+)?)\s+calls?\s+(?:open|available)",
        ]

        for pattern in topic_patterns:
            match = re.search(pattern, query_lower)
            if match:
                extracted = match.group(1).strip()
                # Filter out generic words
                if extracted not in ["new", "any", "open", "funding", "more", "the", "some"]:
                    topic_from_query = extracted
                    break

        # If no topic in query, try to extract from context
        topic_from_context = None
        if not topic_from_query:
            # Look for research topics in context
            context_topic_patterns = [
                r"hydrogen\s*(?:storage|technology|research)?",
                r"marine\s+biology",
                r"artificial\s+intelligence",
                r"machine\s+learning",
                r"renewable\s+energy",
                r"solar\s+(?:energy|power)",
                r"climate\s+(?:change|research)",
                r"healthcare\s*(?:technology)?",
                r"quantum\s+(?:computing|technology)",
                r"battery\s+(?:technology|storage)",
                r"energy\s+storage",
                r"clean\s+energy",
                r"digital\s+(?:health|transformation)",
                r"sustainable\s+(?:transport|mobility)",
            ]

            for pattern in context_topic_patterns:
                match = re.search(pattern, context_lower)
                if match:
                    topic_from_context = match.group(0).strip()
                    break

        # Combine: prefer query topic, fall back to context topic
        search_topic = topic_from_query or topic_from_context

        if not search_topic:
            return None

        # Extract additional context (country, org type)
        country = None
        country_patterns = {
            "germany": "DE",
            "german": "DE",
            "portugal": "PT",
            "portuguese": "PT",
            "spain": "ES",
            "italy": "IT",
            "france": "FR",
            "netherlands": "NL",
        }
        for pattern, code in country_patterns.items():
            if pattern in context_lower:
                country = code
                break

        # Build thought showing context recall
        thought_parts = [f"User is referencing earlier context about '{search_topic}'"]
        if country:
            thought_parts.append(f"(from {country})")
        thought = " ".join(thought_parts) + ". Searching for open calls."

        return {
            "thought": thought,
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "search_funding_calls",
                    "parameters": {"keywords": search_topic, "status": "open", "limit": 10},
                    "reasoning": f"Recalling earlier context and finding open calls for {search_topic}",
                }
            ],
            "needs_more_info": True,
        }

    def _detect_topic_refinement_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is a topic refinement of a previous search.

        This handles queries like:
        - "Actually, I'm interested in AI for healthcare specifically"
        - "More specifically, I want renewable energy for transportation"
        - "Actually, focus on hydrogen for shipping"
        - "But specifically for medical applications"
        - "I meant AI in the healthcare domain"

        These should combine the original topic from context with the refinement.
        """
        if not context:
            logger.debug("🔍 Topic refinement: No context available")
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Refinement patterns that indicate user is narrowing down a previous search
        refinement_patterns = [
            "actually",
            "specifically",
            "more specifically",
            "in particular",
            "focus on",
            "more interested in",
            "particularly interested",
            "i meant",
            "i mean",
            "but for",
            "particularly for",
            "narrow it down to",
            "narrowing down to",
            "let me refine",
            "refine to",
            "instead of",
            "rather than",
            "instead show",
            "instead,",
            "show me instead",
        ]

        # Check if query contains a refinement pattern
        has_refinement = any(pattern in query_lower for pattern in refinement_patterns)

        if not has_refinement:
            logger.debug(f"🔍 Topic refinement: No refinement pattern in query: {query[:50]}")
            return None

        logger.info(f"🔍 Topic refinement: Detected refinement pattern in query: {query[:50]}")

        # Check if context indicates a recent call/project/funding search
        # Context format is:
        # PREVIOUS CONVERSATION:
        # ----------------------------------------
        # USER: Find AI funding opportunities
        # ASSISTANT: I found **5 funding opportunities**...
        search_indicators = [
            # Tool mentions
            "search_funding_calls",
            "search_projects",
            # Response content patterns
            "funding opportunities",
            "funding opportunity",
            "open calls",
            "funding calls",
            "calls found",
            "projects found",
            "i found",
            "found **",
            "call id:",
            "horizon-",
            "erasmus+",
            "creative europe",
            "digital europe",
            "eu4health",
            "life programme",
            # User query patterns
            "user: find",
            "user: show",
            "user: search",
            "user: what",
        ]

        has_search_context = any(indicator in context_lower for indicator in search_indicators)

        if not has_search_context:
            logger.debug(
                f"🔍 Topic refinement: No search context found. Context start: {context[:200]}"
            )
            return None

        logger.info("🔍 Topic refinement: Found search context in conversation")

        # Extract original topic from context
        original_topic = None

        # Extract from USER: lines in context (the previous user query)
        # Pattern: USER: Find/Search/Show [topic] funding/calls/opportunities
        user_query_patterns = [
            # "USER: Find AI funding opportunities"
            r"user:\s*(?:find|search|show|what\s+are)[^a-z]*([a-z]+(?:\s+[a-z]+)?)\s+(?:funding|calls|opportunities|projects)",
            # "USER: Find funding for AI"
            r"user:\s*find\s+(?:funding|calls)\s+for\s+([a-z]+(?:\s+[a-z]+)?)",
            # "USER: Search hydrogen projects"
            r"user:\s*search[^a-z]*([a-z]+(?:\s+[a-z]+)?)\s+(?:projects|funding|calls)",
        ]

        for pattern in user_query_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                original_topic = match.group(1).strip()
                if len(original_topic) > 2 and original_topic not in [
                    "the",
                    "for",
                    "and",
                    "all",
                    "open",
                    "some",
                    "more",
                ]:
                    break
                else:
                    original_topic = None

        # If no topic found via user query patterns, look for topic keywords in context
        if not original_topic:
            # Look for common research topics that appear in context
            topic_keyword_patterns = [
                (r"\b(ai)\b", "ai"),
                (r"\b(artificial intelligence)\b", "artificial intelligence"),
                (r"\b(hydrogen)\b", "hydrogen"),
                (r"\b(renewable energy)\b", "renewable energy"),
                (r"\b(quantum)\b", "quantum"),
                (r"\b(climate)\b", "climate"),
                (r"\b(digital)\b", "digital"),
                (r"\b(energy)\b", "energy"),
                (r"\b(robotics)\b", "robotics"),
                (r"\b(cybersecurity)\b", "cybersecurity"),
                (r"\b(biodiversity)\b", "biodiversity"),
                (r"\b(sustainability)\b", "sustainability"),
            ]
            for pattern, topic in topic_keyword_patterns:
                # Look in the USER: part of context specifically
                user_section = re.search(r"user:\s*([^\n]+)", context_lower)
                if user_section:
                    user_text = user_section.group(1)
                    if re.search(pattern, user_text):
                        original_topic = topic
                        logger.info(
                            f"🔍 Topic refinement: Found original topic '{topic}' in user query"
                        )
                        break

        if original_topic:
            logger.info(f"🔍 Topic refinement: Original topic extracted: '{original_topic}'")
        else:
            logger.debug("🔍 Topic refinement: Could not extract original topic from context")

        # Extract refinement topic from current query
        refinement_topic = None

        # Domain/sector keywords that map to Horizon Europe clusters
        # These are the primary refinement targets
        # Uses CL1-CL6 to match database values in funding_calls.cluster
        domain_to_cluster = {
            # CLUSTER-1: Health (database uses "CL1")
            "healthcare": "CL1",
            "health": "CL1",
            "medical": "CL1",
            "clinical": "CL1",
            "pharma": "CL1",
            "pharmaceutical": "CL1",
            "biotech": "CL1",
            "biotechnology": "CL1",
            "cancer": "CL1",
            "disease": "CL1",
            "patient": "CL1",
            "hospital": "CL1",
            "therapy": "CL1",
            "diagnosis": "CL1",
            # CLUSTER-2: Culture, Creativity
            "cultural": "CL2",
            "creative": "CL2",
            "media": "CL2",
            "heritage": "CL2",
            "society": "CL2",
            "social": "CL2",
            "democracy": "CL2",
            # CLUSTER-3: Security
            "security": "CL3",
            "cybersecurity": "CL3",
            "defense": "CL3",
            "border": "CL3",
            "disaster": "CL3",
            # CLUSTER-4: Digital, Industry
            "digital": "CL4",
            "robotics": "CL4",
            "automation": "CL4",
            "manufacturing": "CL4",
            "industry": "CL4",
            "industrial": "CL4",
            "space": "CL4",
            "semiconductor": "CL4",
            "electronics": "CL4",
            # CLUSTER-5: Climate, Energy, Mobility
            "transportation": "CL5",
            "transport": "CL5",
            "shipping": "CL5",
            "automotive": "CL5",
            "aviation": "CL5",
            "maritime": "CL5",
            "mobility": "CL5",
            "climate": "CL5",
            "energy": "CL5",
            "hydrogen": "CL5",
            "battery": "CL5",
            "renewable": "CL5",
            "green": "CL5",
            # CLUSTER-6: Food, Bioeconomy, Environment
            "agriculture": "CL6",
            "agricultural": "CL6",
            "food": "CL6",
            "farming": "CL6",
            "environment": "CL6",
            "environmental": "CL6",
            "biodiversity": "CL6",
            "sustainability": "CL6",
            "marine": "CL6",
            "ocean": "CL6",
            "water": "CL6",
            "bioeconomy": "CL6",
        }

        # Refinement extraction patterns
        refinement_extraction_patterns = [
            # "interested in X for Y" patterns
            r"interested\s+in\s+\w+\s+for\s+(\w+(?:\s+\w+)?)",
            # "specifically/particularly for X"
            r"(?:specifically|particularly)\s+(?:for\s+)?(\w+(?:\s+\w+)?)",
            # "focus on X"
            r"focus\s+(?:on\s+)?(\w+(?:\s+\w+)?)",
            # "for X applications/domain/sector/use" (covers "agricultural use")
            r"for\s+(\w+(?:\s+\w+)?)\s+(?:applications?|domain|sector|area|field|use)",
            # "in the X sector/domain/area"
            r"in\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:sector|domain|area|field)",
            # "X specifically" - extract BEFORE "specifically"
            r"(\w+(?:\s+\w+)?)\s+specifically",
            # General fallback: extract nouns after refinement keywords
            r"actually[,\s]+(?:i'?m\s+)?(?:interested\s+in\s+)?(?:\w+\s+)?(?:for\s+)?(\w+(?:\s+\w+)?)",
        ]

        # Words to remove from extracted topics
        noise_words = [
            "the",
            "a",
            "an",
            "in",
            "on",
            "for",
            "to",
            "of",
            "and",
            "or",
            "but",
            "it",
            "is",
            "i",
            "we",
            "my",
            "more",
            "that",
            "this",
            "specifically",
            "particularly",
            "especially",
            "really",
            "actually",
            "interested",
        ]

        for pattern in refinement_extraction_patterns:
            match = re.search(pattern, query_lower)
            if match:
                extracted = match.group(1).strip()
                # Clean the extracted topic by removing noise words
                cleaned_words = [
                    w for w in extracted.split() if w not in noise_words and len(w) > 2
                ]
                if cleaned_words:
                    extracted = " ".join(cleaned_words)
                    refinement_topic = extracted
                    break

        # If we still don't have a refinement topic, try simpler extraction
        if not refinement_topic:
            # Look for domain/sector keywords in the query
            for keyword in domain_to_cluster:
                if keyword in query_lower:
                    refinement_topic = keyword
                    break

        # Infer cluster from refinement topic for better filtering
        # Use word boundary matching to avoid false positives (e.g., "cultural" in "agricultural")
        inferred_cluster = None
        if refinement_topic:
            refinement_lower = refinement_topic.lower()
            # Check exact word matches first (handles "agricultural" vs "cultural")
            refinement_words = set(refinement_lower.split())
            for domain, cluster in domain_to_cluster.items():
                # Exact match with refinement topic words
                if domain in refinement_words:
                    inferred_cluster = cluster
                    logger.info(
                        f"🔍 Topic refinement: Inferred cluster '{cluster}' from "
                        f"refinement topic '{refinement_topic}' (exact word match)"
                    )
                    break
            # If no exact match, check if domain equals the refinement topic
            if not inferred_cluster and refinement_lower in domain_to_cluster:
                inferred_cluster = domain_to_cluster[refinement_lower]
                logger.info(
                    f"🔍 Topic refinement: Inferred cluster '{inferred_cluster}' from "
                    f"refinement topic '{refinement_topic}' (exact match)"
                )

        # If we have both original topic and refinement, combine them
        if original_topic and refinement_topic:
            # Extract core technology from original topic (e.g., "ai" from "ai funding")
            original_core = original_topic
            # Remove common words from original topic
            for word in ["funding", "calls", "opportunities", "projects", "grants"]:
                original_core = original_core.replace(word, "").strip()
            if not original_core:
                original_core = original_topic

            # Combine topics: core original + refinement
            combined_keywords = f"{original_core} {refinement_topic}"

            # Build the search parameters
            search_params = {
                "keywords": combined_keywords,
                "status": "open",
                "limit": 15,
            }

            # Add cluster filter if we inferred one
            if inferred_cluster:
                search_params["cluster"] = inferred_cluster

            thought = (
                f"User is refining previous search from '{original_topic}' to focus on "
                f"'{refinement_topic}'. Searching with combined keywords: '{combined_keywords}'"
            )
            if inferred_cluster:
                thought += f" and filtering by cluster {inferred_cluster}."
            else:
                thought += "."

            return {
                "thought": thought,
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "search_funding_calls",
                        "parameters": search_params,
                        "reasoning": f"Refined search combining '{original_core}' with '{refinement_topic}'"
                        + (f" (cluster: {inferred_cluster})" if inferred_cluster else ""),
                    }
                ],
                "needs_more_info": True,
            }

        # If we only have refinement topic but can infer original from context
        if refinement_topic and not original_topic:
            # Build the search parameters
            search_params = {
                "keywords": refinement_topic,
                "status": "open",
                "limit": 15,
            }

            # Add cluster filter if we inferred one
            if inferred_cluster:
                search_params["cluster"] = inferred_cluster

            thought = (
                f"User is refining search to focus on '{refinement_topic}'. "
                f"Searching for calls matching this refined topic"
            )
            if inferred_cluster:
                thought += f" in cluster {inferred_cluster}."
            else:
                thought += "."

            return {
                "thought": thought,
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "search_funding_calls",
                        "parameters": search_params,
                        "reasoning": f"Refined search for '{refinement_topic}'"
                        + (f" (cluster: {inferred_cluster})" if inferred_cluster else ""),
                    }
                ],
                "needs_more_info": True,
            }

        return None

    def _detect_partner_comparison_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is a comparison/analysis of partners from a previous search.

        This handles follow-up queries like:
        - "Compare the top 3 organizations"
        - "Which has the most EU funding?"
        - "Which has the most diverse collaboration network?"
        - "Recommend the best fit for a coordination role"

        These should either use context directly or use get_collaboration_network for network questions.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates partner search data is available
        # These indicators cover both original partner search results AND
        # our context synthesis responses (which also contain organization data)
        partner_context_indicators = [
            "find_experienced_partners",
            "top organizations",
            "organization type",
            "relevant projects",
            "total funding",
            "coordinated",
            "example projects",
            # Indicators from our synthesis responses
            "partner comparison",
            "partner funding comparison",
            "network diversity",
            "coordination experience",
            "projects coordinated",
            "network score",
            "highest funding",
            "most coordination",
            # Additional patterns from comparison table
            "| organization |",
            "| country |",
            "total projects",
            "most diverse collaboration",
            "highest funded",
            "eu funding",
            "key insights",
        ]

        # Need at least 2 indicators to confirm partner data is in context
        indicator_count = sum(1 for ind in partner_context_indicators if ind in context_lower)
        if indicator_count < 2:
            return None

        # Extract organization names from context for use in conclusions
        org_names = self._extract_organization_names_from_context(context)

        # Check for collaboration network queries
        # Use context data (coordination counts) as proxy for network diversity
        # since calling get_collaboration_network for multiple orgs is expensive
        network_patterns = [
            "collaboration network",
            "diverse network",
            "most diverse",
            "network diversity",
            "collaboration history",
            "who do they work with",
            "their partners",
        ]

        if any(pattern in query_lower for pattern in network_patterns):
            # For network diversity, use coordination count as proxy
            # Organizations that coordinate more projects have more diverse networks
            conclusion = self._build_network_diversity_conclusion(context, org_names)
            return {
                "thought": "User is asking about collaboration network diversity. Using coordination data from partner context as proxy for network diversity. Higher coordination = more collaboration experience.",
                "action": "conclude",
                "conclusion": conclusion,
                "confidence": 0.80,
                "needs_more_info": False,
            }

        # Comparison/analysis patterns that can be answered from context
        # Note: More specific patterns (e.g., "coordination role") should come BEFORE
        # generic patterns (e.g., "recommend") to ensure correct classification
        context_synthesis_patterns = [
            # Coordinator recommendations (most specific - check first)
            ("coordination role", "coordinator recommendation"),
            ("as coordinator", "coordinator recommendation"),
            ("should coordinate", "coordinator recommendation"),
            ("who should lead", "coordinator recommendation"),
            ("best coordinator", "coordinator recommendation"),
            ("recommend.*coordinator", "coordinator recommendation"),
            # Funding comparisons
            ("most eu funding", "funding comparison"),
            ("most funding", "funding comparison"),
            ("highest funding", "funding comparison"),
            # Organization comparisons
            ("compare", "comparison request"),
            ("top 3", "comparing top organizations"),
            ("top three", "comparing top organizations"),
            ("top 5", "comparing top organizations"),
            ("top five", "comparing top organizations"),
            # Ranking by attribute
            ("which has the most", "ranking by attribute"),
            ("which one has", "ranking by attribute"),
            ("most projects", "project count comparison"),
            ("most experience", "experience comparison"),
            # Generic recommendations (check after specific patterns)
            ("recommend", "recommendation request"),
            ("best fit", "recommendation request"),
            # Ranking requests
            ("rank these", "ranking request"),
            ("sort by", "ranking request"),
        ]

        matched_pattern = None
        pattern_type = None
        for pattern, ptype in context_synthesis_patterns:
            if pattern in query_lower:
                matched_pattern = pattern
                pattern_type = ptype
                break

        if not matched_pattern:
            return None

        # Build context-aware conclusion
        conclusion = self._build_partner_comparison_conclusion(
            query, context, org_names, pattern_type
        )

        return {
            "thought": f"User is asking for {pattern_type}. Partner search data is already in context with organizations: {', '.join(org_names[:3]) if org_names else 'available'}. Synthesizing answer from context.",
            "action": "conclude",
            "conclusion": conclusion,
            "confidence": 0.85,
            "needs_more_info": False,
        }

    def _detect_cluster_comparison_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is comparing Horizon Europe clusters or programmes.

        This handles queries like:
        - "How does Cluster 5 compare to Cluster 1?"
        - "Cluster 4 vs Cluster 6"

        For EIC/ERC comparison queries, this only handles SIMPLE comparisons.
        Multi-step queries (with "find calls", "recommend", "TRL", etc.) should
        use tools for comprehensive answers.

        These should use compare_programmes, NOT partner comparison.
        """
        query_lower = query.lower()

        import re

        # Check if this is a multi-step query that needs tool execution
        # These complex queries should NOT be short-circuited to built-in guidance
        multi_step_indicators = [
            r"find.*calls?",
            r"search.*calls?",
            r"open\s+calls?",
            r"recommend",
            r"which\s+(?:is\s+)?(?:better|best|suited)",
            r"trl\s*\d",
            r"suit[s]?\s+(?:a|my|our)",
            r"should\s+(?:i|we)",
            r"what.*budget",
            r"deadline",
        ]
        is_multi_step = any(re.search(pattern, query_lower) for pattern in multi_step_indicators)

        # Check if this is an EIC/ERC/MSCA programme comparison
        programme_comparison_pattern = r"(?:eic|erc|msca).*(?:compare|vs|versus).*(?:eic|erc|msca)"
        is_programme_comparison = re.search(programme_comparison_pattern, query_lower)

        # Also check for "compare EIC and ERC" pattern
        compare_programme_pattern = (
            r"compare\s+(?:eic|erc|msca)\s+(?:and|with|to)\s+(?:eic|erc|msca)"
        )
        is_compare_programme = re.search(compare_programme_pattern, query_lower)

        # For multi-step EIC/ERC queries, let the agent use tools
        if (is_programme_comparison or is_compare_programme) and is_multi_step:
            return None  # Let the agent handle with tools

        # For simple EIC/ERC comparison, use built-in guidance
        if is_programme_comparison or is_compare_programme:
            return self._generate_eic_erc_comparison_guidance(query, context)

        # Check for cluster comparison patterns (not EIC/ERC)
        cluster_patterns = [
            r"cluster\s*5.*(?:compare|vs|versus).*cluster\s*1",
            r"cluster\s*1.*(?:compare|vs|versus).*cluster\s*5",
            r"cluster\s*\d.*(?:compare|vs|versus).*cluster\s*\d",
            r"(?:compare|vs|versus).*cluster\s*\d",
            r"how\s+does\s+cluster\s*\d+\s+compare",
            r"compare\s+(?:the\s+)?(?:success\s+rates?\s+)?(?:of\s+)?cluster",
        ]

        is_cluster_comparison = any(re.search(pattern, query_lower) for pattern in cluster_patterns)

        if not is_cluster_comparison:
            return None

        # For multi-step cluster queries, let the agent use tools
        if is_multi_step:
            return None

        # Extract cluster numbers for the guidance generator
        cluster_matches = re.findall(r"cluster\s*(\d+)", query_lower)

        # Use built-in guidance for simple cluster comparisons - provides better actionability
        # and more comprehensive responses than raw tool output
        return self._generate_cluster_comparison_guidance(query, cluster_matches, context)

    def _detect_erc_grant_amount_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect ERC grant amount queries (Scenario 061: Source Attribution).

        These are questions about ERC grant budgets/amounts:
        - "What are the ERC grant amounts?"
        - "How much funding does ERC provide?"
        - "What's the budget for ERC Starting Grant?"
        - "ERC funding levels"

        Responses MUST include source attribution to erc.europa.eu
        to ensure traceability to official data sources.
        """
        query_lower = query.lower()

        # ERC grant amount patterns
        erc_grant_amount_patterns = [
            # Direct grant amount questions
            r"(?:what|how much).*erc.*(?:grant|fund|budget|amount)",
            r"erc.*(?:grant|funding).*(?:amount|level|budget|size)",
            r"(?:budget|funding|amount).*erc.*grant",
            r"erc\s+(?:starting|consolidator|advanced|synergy).*(?:budget|amount|funding|grant)",
            r"how much.*(?:is|does).*erc.*(?:starting|consolidator|advanced|synergy)",
            # Funding limit questions
            r"(?:maximum|max|up to).*erc.*(?:grant|funding)",
            r"erc.*(?:maximum|max|funding limit|budget limit)",
            # Specific grant type amounts
            r"(?:starting|consolidator|advanced|synergy).*grant.*(?:amount|budget|funding|level)",
            r"(?:what|how much).*(?:starting|consolidator|advanced|synergy)\s+grant",
            # Simple ERC funding/budget patterns (must be ERC-specific)
            r"^erc\s+funding\s+level",  # "ERC funding levels"
            r"^erc\s+(?:grant\s+)?budget",  # "ERC budget" or "ERC grant budget"
            r"^erc\s+(?:grant\s+)?amount",  # "ERC amount" or "ERC grant amount"
        ]

        # Check for ERC grant amount patterns
        import re

        for pattern in erc_grant_amount_patterns:
            if re.search(pattern, query_lower):
                return {
                    "thought": "User is asking about ERC grant amounts. Providing detailed funding information with source attribution.",
                    "action": "generate_guidance",
                    "guidance_type": "erc_grant_amounts",
                    "response": self._generate_erc_grant_amount_guidance(),
                }

        # Also match simple "ERC grants" + amount/budget context
        if "erc" in query_lower and any(
            term in query_lower
            for term in [
                "amount",
                "budget",
                "how much",
                "funding level",
                "grant size",
                "maximum",
                "funding",
            ]
        ):
            # Avoid false positives for comparison queries or eligibility
            if not any(
                term in query_lower
                for term in ["vs", "versus", "compare", "eligible", "eligibility", "apply"]
            ):
                return {
                    "thought": "User is asking about ERC grant amounts. Providing detailed funding information with source attribution.",
                    "action": "generate_guidance",
                    "guidance_type": "erc_grant_amounts",
                    "response": self._generate_erc_grant_amount_guidance(),
                }

        return None

    def _detect_budget_trend_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is asking for budget/funding trends or historical analysis.

        This handles queries like:
        - "Show budget trends over 2021-2024"
        - "How has funding changed over time?"
        - "Budget evolution by year"
        - "Funding trends for RIA projects"
        - "What were the budgets in previous years?"

        These should use analyze_call_history tool with year filtering.
        """
        query_lower = query.lower()

        # Budget trend patterns
        trend_patterns = [
            "budget trend",
            "budget trends",
            "funding trend",
            "funding trends",
            "over time",
            "over years",
            "2021-2024",
            "2021-2027",
            "by year",
            "each year",
            "annual budget",
            "yearly funding",
            "evolution",
            "how has funding changed",
            "how has budget changed",
            "budget history",
            "funding history",
            "historical funding",
            "historical budget",
            "previous years",
            "year over year",
            "year-over-year",
            "budget over",
            "funding over",
        ]

        is_trend_query = any(pattern in query_lower for pattern in trend_patterns)

        if not is_trend_query:
            return None

        # Extract action type from query or context
        action_type = None
        if "ria" in query_lower:
            action_type = "RIA"
        elif "ia" in query_lower and "eia" not in query_lower:
            action_type = "IA"
        elif "csa" in query_lower:
            action_type = "CSA"
        elif "eic" in query_lower:
            action_type = "EIC"

        # Extract action type from context if not in query
        if not action_type and context:
            context_lower = context.lower()
            if "ria" in context_lower or "research and innovation action" in context_lower:
                action_type = "RIA"
            elif "ia" in context_lower or "innovation action" in context_lower:
                action_type = "IA"
            elif "eic" in context_lower or "european innovation council" in context_lower:
                action_type = "EIC"

        # Extract topic keywords from query
        topic_keywords = self._extract_topic_keywords(query)

        # Also check context for budget comparison context
        if not topic_keywords and context:
            # Check if this is a follow-up to budget comparison
            if "budget" in context.lower() and any(
                t in context.lower() for t in ["ria", "ia", "eic"]
            ):
                # Use accumulated context
                pass

        # Build tool call parameters
        params = {
            "expand_scope": True,  # Get comprehensive analysis
        }
        if action_type:
            params["action_types"] = [action_type]
        if topic_keywords:
            params["keywords"] = topic_keywords

        return {
            "thought": f"User is asking for budget/funding trends over time. Using analyze_call_history to get historical data. Action type: {action_type or 'all'}, Keywords: {topic_keywords or 'none'}",
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "analyze_call_history",
                    "parameters": params,
                    "reasoning": "Getting historical funding trends and budget evolution over time",
                }
            ],
            "needs_more_info": True,
        }

    def _detect_budget_variation_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is asking about budget variations (follow-up to budget questions).

        This handles follow-up queries like:
        - "How does this vary by organization type?"
        - "What about coordinator vs partner budgets?"
        - "Break it down by organization"
        - "Coordinator share?"

        These should use get_budget_benchmark with appropriate breakdown options.
        """
        query_lower = query.lower()

        # Check if this is a follow-up to budget discussion
        if not context:
            return None

        context_lower = context.lower()
        has_budget_context = any(
            t in context_lower
            for t in ["budget", "per-partner", "per partner", "€", "million", "benchmark"]
        )

        if not has_budget_context:
            return None

        # Budget variation patterns
        org_type_patterns = [
            "by organization type",
            "vary by organization",
            "organization type",
            "org type",
            "universities vs",
            "companies vs",
            "research vs",
            "by type",
            "different types",
            "breakdown by type",
        ]

        coordinator_patterns = [
            "coordinator vs partner",
            "coordinator versus partner",
            "coordinator budgets",
            "partner budgets",
            "coordinator share",
            "coordinator portion",
            "vs partner",
            "versus partner",
            "coordinator or partner",
        ]

        # Detect query type
        is_org_type_query = any(pattern in query_lower for pattern in org_type_patterns)
        is_coordinator_query = any(pattern in query_lower for pattern in coordinator_patterns)

        if not is_org_type_query and not is_coordinator_query:
            return None

        # Extract action type from context
        action_type = None
        if "ria" in context_lower or "research and innovation action" in context_lower:
            action_type = "RIA"
        elif "ia" in context_lower or "innovation action" in context_lower:
            action_type = "IA"
        elif "eic" in context_lower or "european innovation council" in context_lower:
            action_type = "EIC"

        if is_org_type_query:
            # Generate guidance about organization type budgets
            return self._generate_org_type_budget_guidance(query, action_type, context)
        elif is_coordinator_query:
            # Generate guidance about coordinator vs partner budgets
            return self._generate_coordinator_budget_guidance(query, action_type, context)

        return None

    def _detect_per_partner_budget_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect if query is asking about per-partner budgets.

        This handles queries like:
        - "What's the average per-partner budget?"
        - "How much does each partner get?"
        - "Budget per partner?"

        These should generate guidance with actionable next steps.
        """
        query_lower = query.lower()

        # Per-partner budget patterns
        per_partner_patterns = [
            "per-partner budget",
            "per partner budget",
            "per-partner",
            "per partner",
            "each partner",
            "budget per partner",
            "average partner budget",
            "partner allocation",
            "how much per partner",
        ]

        is_per_partner_query = any(pattern in query_lower for pattern in per_partner_patterns)

        if not is_per_partner_query:
            return None

        # Check if this is a follow-up to budget comparison
        has_budget_context = context and any(
            t in context.lower() for t in ["ria", "ia", "eic", "budget", "€"]
        )

        # Extract action type from context
        action_type = None
        if context:
            context_lower = context.lower()
            if "ria" in context_lower or "research and innovation action" in context_lower:
                action_type = "RIA"
            elif "ia" in context_lower or "innovation action" in context_lower:
                action_type = "IA"
            elif "eic" in context_lower:
                action_type = "EIC"

        return self._generate_per_partner_budget_guidance(query, action_type, has_budget_context)

    def _detect_organization_deepdive_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect if query is a follow-up about a specific organization.

        This handles follow-up queries like:
        - "What topics do they focus on?" (after asking about TUM's funding history)
        - "Show their recent projects"
        - "Who are their preferred partners?"
        - "What's their success rate as coordinator?"

        These should use find_organization_projects or get_collaboration_network.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates a specific organization is being discussed
        # Look for patterns like "## Projects for/by <org>" or organization names mentioned
        org_context_indicators = [
            "## projects for ",
            "## projects by ",
            "## collaboration network",
            "find_organization_projects",
            "organization's eu funding",
            "'s funding history",
            "technical university of munich",
            "technische universit",
            "technische universitaet muenchen",  # German spelling
            "fraunhofer",
            "university of ",
            "cnrs",
            "max planck",
            "tu delft",
            "tu munich",
            "eth zurich",
            "epfl",
            " eu funding history",
            "total projects found",  # Response pattern from find_organization_projects
        ]

        has_org_context = any(indicator in context_lower for indicator in org_context_indicators)

        if not has_org_context:
            return None

        # Extract the organization name from context
        org_name = self._extract_org_from_context(context)

        if not org_name:
            return None

        # Queries about collaboration/partners - use get_collaboration_network
        partner_query_patterns = [
            "who are their partners",
            "their preferred partners",
            "who do they partner with",
            "who do they work with",
            "collaboration network",
            "typically partner with",
            "partner with",
            "collaborators",
        ]

        if any(pattern in query_lower for pattern in partner_query_patterns):
            return {
                "thought": f"User is asking about {org_name}'s collaboration partners. Using get_collaboration_network.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "get_collaboration_network",
                        "parameters": {"organization_name": org_name},
                        "reasoning": f"Getting collaboration network for {org_name}",
                    }
                ],
                "needs_more_info": True,
            }

        # Queries about projects/focus/topics - use find_organization_projects
        project_query_patterns = [
            "their projects",
            "their recent projects",
            "show projects",
            "what topics",
            "research focus",
            "focus areas",
            "topics do they",
            "what do they work on",
            "what are they working",
            "success rate as coordinator",
            "coordinated projects",
            "as coordinator",
            "projects they coordinated",
            "coordinator success",
        ]

        if any(pattern in query_lower for pattern in project_query_patterns):
            # Check if query specifically asks about coordinator role
            # BUT: For success rate queries, don't filter by role - we need all projects
            # to compute statistics (even if they ask about coordinator success rate)
            role = None
            is_success_rate_query = "success rate" in query_lower
            if not is_success_rate_query and any(
                kw in query_lower for kw in ["coordinator", "coordinated", "lead", "leading"]
            ):
                role = "coordinator"

            thought = f"User is asking about {org_name}'s projects."
            if is_success_rate_query:
                thought += " Fetching all projects to analyze coordinator statistics."
            thought += " Using find_organization_projects."

            return {
                "thought": thought,
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "find_organization_projects",
                        "parameters": {
                            "organization_name": org_name,
                            **({"role": role} if role else {}),
                        },
                        "reasoning": f"Finding projects for {org_name}"
                        + (f" (as {role})" if role else " (all roles for statistics)"),
                    }
                ],
                "needs_more_info": True,
            }

        return None

    def _extract_org_from_context(self, context: str) -> str | None:
        """Extract the most recently discussed organization name from context.

        Looks for patterns like:
        - "## Projects for Technical University of Munich"
        - "Technical University of Munich's EU funding history"
        - Previous tool calls with organization_name parameter
        """
        import re

        context_lines = context.split("\n")

        # Pattern 1: Look for "Projects for <org>" or "Projects by <org>" headers
        for line in context_lines:
            match = re.search(r"## Projects (?:for|by) (.+)", line, re.IGNORECASE)
            if match:
                org_name = match.group(1).strip()
                # Clean up any markdown or parenthetical info
                org_name = re.sub(r"\s*\([^)]+\)\s*$", "", org_name)
                if org_name and len(org_name) > 3:
                    return org_name

        # Pattern 2: Look for "Collaboration Network" for/of organization (colon format)
        # e.g., "## Collaboration Network: TECHNISCHE UNIVERSITAET MUENCHEN"
        for line in context_lines:
            match = re.search(r"## Collaboration Network[:\s]+(.+)", line, re.IGNORECASE)
            if match:
                org_name = match.group(1).strip()
                # Clean up any markdown or extra text
                org_name = re.sub(r"\s*\([^)]+\)\s*$", "", org_name)
                if org_name and len(org_name) > 3:
                    return org_name

        # Pattern 3: Look for "<org>'s EU funding history" or similar
        funding_history_patterns = [
            r"([A-Za-z\s\-']+(?:University|Institute|College|Centre|Center|GmbH|AG|Ltd).*?)'s (?:EU|funding|project)",
            r"about ([A-Za-z\s\-']+(?:University|Institute|College|Centre|Center))",
            r"Tell me about ([A-Za-z\s\-']+)'s",
        ]

        for pattern in funding_history_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                org_name = match.group(1).strip()
                if len(org_name) > 3 and org_name.lower() not in ["the", "their", "this"]:
                    return org_name

        # Pattern 4: Look for major university/institution names in context
        major_institutions = {
            "technical university of munich": "Technical University of Munich",
            "technische universitaet muenchen": "Technical University of Munich",
            "tum": "Technical University of Munich",
            "fraunhofer": "Fraunhofer",
            "max planck": "Max Planck",
            "cnrs": "CNRS",
            "tu delft": "TU Delft",
            "eth zurich": "ETH Zurich",
            "epfl": "EPFL",
            "imperial college": "Imperial College London",
            "university of oxford": "University of Oxford",
            "university of cambridge": "University of Cambridge",
        }

        context_lower = context.lower()
        for search_term, display_name in major_institutions.items():
            if search_term in context_lower:
                return display_name

        return None

    def _extract_organization_names_from_context(self, context: str) -> list[str]:
        """Extract organization names from partner search context."""
        import re

        org_names = []

        # Pattern 1: Look for bold organization names (markdown format)
        # e.g., "**FRAUNHOFER GESELLSCHAFT ZUR FORDERUNG DER ANGEWANDTEN FORSCHUNG EV**"
        bold_pattern = re.findall(r"\*\*([A-Z][A-Z0-9\s\-&']+?)\*\*", context)
        for name in bold_pattern:
            name = name.strip()
            # Filter out section headers and keep actual organization names
            if len(name) > 5 and not name.startswith(("Finding", "How to", "Top")):
                org_names.append(name)

        # Pattern 2: Look for numbered list entries with organization names
        # e.g., "### 1. **ORG NAME** (DE)"
        numbered_pattern = re.findall(r"###\s*\d+\.\s*\*\*([^*]+)\*\*", context)
        for name in numbered_pattern:
            name = name.strip()
            if name not in org_names and len(name) > 5:
                org_names.append(name)

        # Deduplicate while preserving order
        seen = set()
        unique_orgs = []
        for org in org_names:
            if org not in seen:
                seen.add(org)
                unique_orgs.append(org)

        return unique_orgs[:10]  # Return top 10 organizations

    def _extract_topic_from_context(self, context: str) -> str | None:
        """Extract the original topic keywords from conversation context."""
        # Look for common patterns that indicate a topic was searched
        import re

        # Pattern 1: "topic_keywords='...'"
        match = re.search(r"topic_keywords[=:]\s*['\"]?([^'\"]+)['\"]?", context, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Pattern 2: "for ... research" or "partners for ..."
        match = re.search(
            r"(?:partners? for|find.*for|experience in|experienced in)\s+([a-z\s]+?)(?:\s+research|\s+project|\s*$)",
            context.lower(),
        )
        if match:
            topic = match.group(1).strip()
            if len(topic) > 3:
                return topic

        # Pattern 3: Look for capitalized technical terms
        match = re.search(
            r"(?:quantum|hydrogen|ai|machine learning|renewable|solar|climate)\s*\w*",
            context.lower(),
        )
        if match:
            return match.group(0).strip()

        return None

    def _get_countries_for_group(self, group: str) -> list[str]:
        """Get list of countries for a regional group."""
        country_groups = {
            "EU15": [
                "Germany",
                "France",
                "Italy",
                "Spain",
                "Netherlands",
                "Belgium",
                "Austria",
                "Sweden",
                "Denmark",
                "Finland",
                "Ireland",
                "Portugal",
                "Greece",
                "Luxembourg",
            ],
            "EU13": [
                "Poland",
                "Czech Republic",
                "Hungary",
                "Romania",
                "Bulgaria",
                "Slovakia",
                "Slovenia",
                "Lithuania",
                "Latvia",
                "Estonia",
                "Croatia",
                "Cyprus",
                "Malta",
            ],
            "SOUTHERN": ["Spain", "Italy", "Portugal", "Greece", "Malta", "Cyprus"],
            "NORTHERN": ["Sweden", "Denmark", "Finland", "Norway", "Iceland"],
            "WESTERN": [
                "Germany",
                "France",
                "Netherlands",
                "Belgium",
                "Austria",
                "Ireland",
                "Luxembourg",
            ],
            "EASTERN": [
                "Poland",
                "Czech Republic",
                "Hungary",
                "Romania",
                "Bulgaria",
                "Slovakia",
            ],
        }
        return country_groups.get(group.upper(), [])

    def _extract_topic_keywords(self, query: str) -> str:
        """Extract topic keywords from a query for tool parameters."""
        # Remove common query words
        stopwords = [
            "find",
            "search",
            "look",
            "for",
            "in",
            "from",
            "with",
            "the",
            "a",
            "an",
            "we",
            "need",
            "want",
            "partner",
            "partners",
            "organization",
            "organizations",
            "organisation",
            "organisations",
            "sme",
            "research",
            "experienced",
            "typical",
            "consortium",
            "size",
            "how",
            "many",
            "what",
            "is",
            "are",
            "show",
            "our",
            "proposed",
            "to",
            "me",
            "can",
            "you",
            "please",
            "help",
            "about",
        ]
        words = query.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return " ".join(keywords[:5]) if keywords else query

    def _extract_country(self, query: str) -> str | None:
        """Extract country from query if mentioned.

        Uses word boundaries for short country codes to avoid false positives
        like 'fit' matching 'it' (Italy) or 'before' matching 'be' (Belgium).
        """
        import re

        query_lower = query.lower()

        # Two-letter codes require word boundaries to avoid false positives
        short_codes = {
            r"\bde\b": "Germany",
            r"\bfr\b": "France",
            r"\bit\b": "Italy",
            r"\bes\b": "Spain",
            r"\bpt\b": "Portugal",
            r"\bel\b": "Greece",
            r"\bnl\b": "Netherlands",
            r"\bbe\b": "Belgium",
        }

        # Full country names and adjectives (safe for substring match)
        full_names = {
            "germany": "Germany",
            "german": "Germany",
            "france": "France",
            "french": "France",
            "italy": "Italy",
            "italian": "Italy",
            "spain": "Spain",
            "spanish": "Spain",
            "portugal": "Portugal",
            "portuguese": "Portugal",
            "greece": "Greece",
            "greek": "Greece",
            "netherlands": "Netherlands",
            "dutch": "Netherlands",
            "belgium": "Belgium",
            "belgian": "Belgium",
            "southern europe": "Spain",  # Default to Spain for Southern Europe
        }

        # Check short codes with word boundaries first
        for pattern, country in short_codes.items():
            if re.search(pattern, query_lower):
                return country

        # Check full names (substring match is safe for these)
        for pattern, country in full_names.items():
            if pattern in query_lower:
                return country

        return None

    def _extract_org_type(self, query: str) -> str | None:
        """Extract organization type from query if mentioned.

        Uses word boundaries to avoid false positives like 'recommend' matching 'rec'.
        """
        import re

        query_lower = query.lower()

        # SME patterns - "sme" as word or "small" in context of business
        if re.search(r"\bsme\b|\bsmes\b|\bsmall\s+(company|business|enterprise)", query_lower):
            return "SME"

        # REC patterns - "research" as word or "rec" as standalone abbreviation
        # Don't match "rec" inside other words like "recommend"
        if re.search(r"\bresearch\b|\brec\b", query_lower):
            return "REC"

        # HES patterns - universities, higher education
        if re.search(r"\buniversity\b|\buniversities\b|\bhes\b|\bhigher education\b", query_lower):
            return "HES"

        # PRC patterns - private companies
        if re.search(r"\bprivate\b|\bcompany\b|\bcompanies\b|\bprc\b", query_lower):
            return "PRC"

        return None

    def _get_tool_hint(self, query: str, context: str = "") -> str | None:
        """Get a tool hint for specific query types to guide LLM tool selection.

        Returns a hint string to be injected into the context, or None if no hint needed.
        """
        query_lower = query.lower()

        # Partner/organization discovery patterns - MUST use find_experienced_partners
        partner_patterns = [
            "find partner",
            "find organization",
            "find organisations",
            "find a research",
            "organizations experienced",
            "organisations experienced",
            "experienced in",
            "partner search",
            "who has experience",
            "companies working on",
            "universities working on",
            "sme partner",
            "sme from",
            "need a partner",
            "need an sme",
            "precision farming",
            "research organization",
            "research organisation",
            "partner from",
            "find organizations",
        ]

        if any(pattern in query_lower for pattern in partner_patterns):
            # Extract specific context for the hint
            topic = self._extract_topic_keywords(query)
            country = self._extract_country(query)
            org_type = self._extract_org_type(query)

            hint_parts = [
                "MANDATORY: This is a PARTNER DISCOVERY query.",
                "You MUST use find_experienced_partners tool - DO NOT use search_documents!",
                f"Use parameters: topic_keywords='{topic}'",
            ]
            if country:
                hint_parts.append(f", country='{country}'")
            if org_type:
                hint_parts.append(f", organization_type='{org_type}'")

            return " ".join(hint_parts)

        # Check for partner search REFINEMENT hints
        refinement_hint = self._get_partner_refinement_hint(query, context)
        if refinement_hint:
            return refinement_hint

        # Consortium size/patterns queries - MUST use get_consortium_patterns
        consortium_patterns = [
            "typical consortium",
            "consortium size",
            "how many partners",
            "consortium composition",
            "consortium pattern",
            "ideal partners",
            "partner types",
            "typical number of partners",
        ]

        if any(pattern in query_lower for pattern in consortium_patterns):
            return (
                "This is a CONSORTIUM PATTERNS query. You MUST use get_consortium_patterns tool "
                "(NOT search_documents). This tool provides consortium size statistics from funded projects."
            )

        # Budget queries - use calculate_budget or get_budget_benchmark
        budget_patterns = [
            "calculate budget",
            "budget breakdown",
            "budget for",
            "help me plan",
            "recalculate",
            "adjust budget",
            "increase personnel",
        ]

        if any(pattern in query_lower for pattern in budget_patterns):
            return (
                "This is a BUDGET query. You MUST use calculate_budget or get_budget_benchmark tool "
                "(NOT search_documents)."
            )

        # Timeline queries - use generate_timeline
        timeline_patterns = [
            "generate timeline",
            "project timeline",
            "work packages",
            "add wp",
            "add a clinical",
            "add buffer",
            "milestones",
        ]

        if any(pattern in query_lower for pattern in timeline_patterns):
            return (
                "This is a TIMELINE query. You MUST use generate_timeline tool "
                "(NOT search_documents)."
            )

        # Context synthesis queries - should synthesize from conversation, NOT search
        synthesis_patterns = [
            "show our proposed",
            "show the proposed",
            "our consortium",
            "proposed consortium",
            "consortium summary",
            "summarize the partners",
            "list the partners",
            "what partners have we",
            "partners we found",
        ]

        if any(pattern in query_lower for pattern in synthesis_patterns):
            return (
                "This is a CONTEXT SYNTHESIS query. Do NOT use search_documents. "
                "Instead, synthesize the partners/information from the PREVIOUS CONVERSATION turns. "
                "List and summarize the organizations already discovered in this conversation."
            )

        return None

    def _get_partner_refinement_hint(self, query: str, context: str) -> str | None:
        """Get a hint for partner search refinement queries.

        Detects when a short query is refining a previous partner search.
        """
        if not context:
            return None

        query_lower = query.lower()
        context_lower = context.lower()

        # Check if context indicates a recent partner search
        partner_search_indicators = [
            "find_experienced_partners",
            "experienced partners",
            "organizations with experience",
            "partner discovery",
            "top organizations",
            "organization type",
            "relevant projects",
            "total funding",
        ]

        has_partner_context = any(
            indicator in context_lower for indicator in partner_search_indicators
        )

        if not has_partner_context:
            return None

        # Partner refinement patterns
        refinement_indicators = [
            # Org type refinements
            "only universities",
            "show only universities",
            "universities only",
            "only hes",
            "higher education",
            "only smes",
            "smes only",
            "only research",
            "research only",
            "only private",
            "companies only",
            # Role refinements
            "experience coordinating",
            "coordinating projects",
            "as coordinator",
            "who have coordinated",
            "coordination experience",
            # Country/region refinements
            "eu15 countries",
            "from eu15",
            "eu15 only",
            "eu13 countries",
            "from eu13",
            "southern europe",
            "northern europe",
            "western europe",
            "eastern europe",
            # Topic refinements
            "worked on",
            "have worked on",
            "who have worked",
        ]

        if any(indicator in query_lower for indicator in refinement_indicators):
            # Detect specific filter type for better hint
            org_type = self._extract_org_type(query)
            country = self._extract_country(query)

            hint = (
                "MANDATORY: This is a PARTNER SEARCH REFINEMENT query. "
                "The user is refining the previous partner search. "
                "You MUST use find_experienced_partners tool (NOT search_documents!) "
                "with filters based on their refinement request."
            )

            if org_type:
                hint += f" Use organization_type='{org_type}'."
            if country:
                hint += f" Use country='{country}'."

            # Get original topic from context
            original_topic = self._extract_topic_from_context(context)
            if original_topic:
                hint += f" Use topic_keywords from the previous search: '{original_topic}'."

            return hint

        return None

    def _detect_timeline_comparison_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect queries about proposal preparation timelines, decision times, and project start lags.

        This handles queries like:
        - "How long does a Horizon Europe proposal take to prepare?"
        - "Compare with Erasmus+ KA2"
        - "What about Creative Europe cooperation projects?"
        - "Which has the fastest decision time?"
        - "What's the project start lag after selection?"
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # === Pattern 1: Horizon Europe proposal preparation time ===
        he_prep_patterns = [
            ("how long", "horizon", "proposal"),
            ("how long", "horizon", "prepare"),
            ("preparation time", "horizon"),
            ("typical", "horizon", "proposal", "take"),
            ("horizon europe proposal", "time"),
            ("horizon europe", "preparation"),
            ("how many months", "horizon"),
            ("time to prepare", "horizon"),
            ("prepare a horizon",),
            ("preparing a horizon",),
        ]

        for patterns in he_prep_patterns:
            if all(p in query_lower for p in patterns):
                guidance = self._generate_he_preparation_time_guidance()
                return {
                    "thought": "User is asking about Horizon Europe proposal preparation time. Using built-in guidance.",
                    "action": "generate_guidance",
                    "response": guidance,
                    "guidance_type": "he_preparation_time",
                    "confidence": 0.90,
                    "needs_more_info": False,
                }

        # === Pattern 2: Compare with Erasmus+ KA2 (follow-up) ===
        erasmus_comparison_patterns = [
            "compare with erasmus",
            "compare to erasmus",
            "compared to erasmus",
            "erasmus+ ka2",
            "erasmus ka2",
            "vs erasmus",
            "versus erasmus",
            "what about erasmus",
            "and erasmus",
        ]

        # Check if timeline context exists (from previous HE preparation question)
        timeline_context = any(
            ind in context_lower
            for ind in [
                "proposal preparation",
                "preparation time",
                "months",
                "horizon europe proposal",
                "typical preparation",
            ]
        )

        if timeline_context and any(p in query_lower for p in erasmus_comparison_patterns):
            guidance = self._generate_erasmus_ka2_comparison_guidance()
            return {
                "thought": "User is comparing Erasmus+ KA2 timelines with Horizon Europe. Using built-in guidance.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_ka2_comparison",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Creative Europe cooperation projects (follow-up) ===
        ce_patterns = [
            "creative europe",
            "what about creative",
            "creative cooperation",
            "ce cooperation",
        ]

        # Check if timeline comparison context exists
        comparison_context = any(
            ind in context_lower
            for ind in [
                "erasmus",
                "horizon europe",
                "preparation time",
                "compare",
                "months",
            ]
        )

        if comparison_context and any(p in query_lower for p in ce_patterns):
            guidance = self._generate_creative_europe_timeline_guidance()
            return {
                "thought": "User is asking about Creative Europe cooperation project timelines. Using built-in guidance.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "creative_europe_timeline",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: Decision time comparison ===
        decision_patterns = [
            "decision time",
            "fastest decision",
            "quickest decision",
            "evaluation time",
            "time to decision",
            "which is fastest",
            "which has fastest",
            "fastest to hear back",
            "how long for decision",
            "decision period",
            "time to grant",
        ]

        # Check for timeline/programme context
        programme_context = any(
            ind in context_lower
            for ind in ["horizon", "erasmus", "creative europe", "preparation", "months"]
        )

        if programme_context and any(p in query_lower for p in decision_patterns):
            guidance = self._generate_decision_time_comparison_guidance()
            return {
                "thought": "User is asking about decision times across programmes. Using built-in guidance.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "decision_time_comparison",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: Project start lag after selection ===
        start_lag_patterns = [
            "start lag",
            "project start",
            "after selection",
            "after approval",
            "after decision",
            "when does project start",
            "time between selection",
            "gap preparation",
            "grant agreement",
            "time to start",
            "project kick-off",
            "kickoff lag",
        ]

        # Check for timeline context
        if programme_context and any(p in query_lower for p in start_lag_patterns):
            guidance = self._generate_project_start_lag_guidance()
            return {
                "thought": "User is asking about project start lag after selection. Using built-in guidance.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "project_start_lag",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_urgent_deadline_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect urgent deadline / preparation requirements queries.

        These are questions about:
        - Minimum requirements for urgent deadlines
        - Feasibility assessment for imminent submissions
        - Prioritizing calls by feasibility given time constraints
        - Emergency proposal preparation guidance
        - Calls closing very soon (this week, next few days)

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # FIRST: Check for "calls closing this week/soon" type queries
        # These need to actually search for calls AND provide realistic assessment
        imminent_deadline_search_patterns = [
            "closing this week",
            "closing soon",
            "due this week",
            "deadline this week",
            "deadlines this week",
            "calls this week",
            "ending this week",
            "due soon",
            "close soon",
            "closes soon",
            "closing in the next few days",
            "closing in the next week",
            "deadline in the next few days",
            "next few days",
            "in a few days",
            "within days",
            "within a week",
            "before next week",
            "by end of week",
            "by the end of this week",
            "before friday",
            "before the weekend",
        ]

        # Check if query is asking about imminent calls/deadlines (wanting to find and apply)
        is_asking_for_imminent_calls = any(
            pattern in query_lower for pattern in imminent_deadline_search_patterns
        ) and any(
            indicator in query_lower
            for indicator in ["call", "apply", "funding", "deadline", "could", "can i"]
        )

        if is_asking_for_imminent_calls:
            return {
                "thought": "User is asking about calls closing very soon (this week). Will search for imminent deadlines but MUST provide realistic assessment that 1 week is NOT enough time for most EU proposals.",
                "action": "search_imminent_calls_with_warning",
                "guidance_type": "imminent_deadline_search",
            }

        # Check if there's urgent deadline context (calls closing soon, imminent deadlines)
        has_deadline_context = any(
            pattern in context_lower
            for pattern in [
                "deadline",
                "closing",
                "30 days",
                "next month",
                "february",
                "march",
                "imminent",
                "urgent",
                "time to apply",
                "still time",
            ]
        )

        # Minimum requirements patterns
        minimum_requirement_patterns = [
            "minimum we need",
            "minimum required",
            "minimum requirements",
            "what do we need ready",
            "what's needed",
            "what is needed",
            "bare minimum",
            "essential requirements",
            "must have ready",
            "need to have ready",
            "minimum to submit",
            "minimum for submission",
            "what must we have",
            "what do we absolutely need",
            "minimum elements",
            "critical requirements",
            "essential elements",
            "need ready",
            "minimum preparation",
        ]

        # Feasibility prioritization patterns
        feasibility_patterns = [
            "prioritize by feasibility",
            "prioritise by feasibility",
            "prioritize by likelihood",
            "prioritise by likelihood",
            "which is most feasible",
            "which are most feasible",
            "rank by feasibility",
            "order by feasibility",
            "most realistic",
            "most achievable",
            "best chance",
            "which should we focus",
            "which to focus on",
            "which call should we",
            "prioritize these",
            "prioritise these",
            "priority order",
            "which is easiest",
            "most manageable",
        ]

        # Rapid preparation / emergency patterns
        rapid_prep_patterns = [
            "short time",
            "limited time",
            "few weeks",
            "can we still",
            "is it possible to",
            "realistic to apply",
            "enough time to",
            "rush submission",
            "fast track",
            "quick submission",
            "emergency preparation",
            "last minute",
        ]

        # Time assessment patterns (is there still time?)
        time_assessment_patterns = [
            "still time to apply",
            "still time",
            "is there time",
            "is there still time",
            "enough time",
            "time left",
            "too late",
            "can we make it",
            "do we have time",
            "have time to",
        ]

        # Check for time assessment query (need to be early to catch "Is there still time to apply?")
        if any(pattern in query_lower for pattern in time_assessment_patterns):
            return {
                "thought": "User is asking about time feasibility for applying. Providing time assessment guidance with actionable next steps.",
                "action": "generate_guidance",
                "guidance_type": "time_assessment",
                "response": self._generate_time_assessment_guidance(context),
            }

        # Check for minimum requirements query
        if any(pattern in query_lower for pattern in minimum_requirement_patterns) or (
            has_deadline_context
            and any(p in query_lower for p in ["minimum", "need ready", "must have", "required"])
        ):
            return {
                "thought": "User is asking about minimum requirements for urgent deadline submission. Providing actionable preparation checklist.",
                "action": "generate_guidance",
                "guidance_type": "minimum_requirements",
                "response": self._generate_minimum_requirements_guidance(),
            }

        # Check for feasibility prioritization query
        if any(pattern in query_lower for pattern in feasibility_patterns) or (
            has_deadline_context
            and any(
                p in query_lower for p in ["prioritize", "prioritise", "rank", "order", "which"]
            )
        ):
            return {
                "thought": "User is asking to prioritize calls by feasibility. Providing feasibility assessment framework.",
                "action": "generate_guidance",
                "guidance_type": "feasibility_prioritization",
                "response": self._generate_feasibility_prioritization_guidance(context),
            }

        # Check for rapid preparation query
        if any(pattern in query_lower for pattern in rapid_prep_patterns):
            return {
                "thought": "User is asking about rapid proposal preparation. Providing emergency preparation guidance.",
                "action": "generate_guidance",
                "guidance_type": "rapid_preparation",
                "response": self._generate_rapid_preparation_guidance(),
            }

        return None

    def _detect_deadline_tracking_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect queries about deadline tracking - time gaps between calls, targeting decisions.

        This handles follow-up queries after users have viewed a list of deadlines:
        - "How much time between them?" - Time gap between deadlines
        - "Which one should I target?" - Targeting recommendation
        - "What's the gap between deadlines?" - Time interval queries
        - "Which deadline should I prioritize?" - Strategic deadline selection

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Check if there's deadline/call listing context (multiple calls with dates)
        has_deadline_listing_context = any(
            pattern in context_lower
            for pattern in [
                "deadline",
                "february",
                "march",
                "april",
                "january",
                "2026",
                "2025",
                "cluster",
                "cl4",
                "cl5",
                "cl6",
                "digital",
                "funding opportunities",
                "calls",
                "open",
                "upcoming",
            ]
        )

        # Time gap between deadlines patterns
        time_gap_patterns = [
            "how much time between",
            "time between them",
            "time between the",
            "gap between",
            "interval between",
            "days between",
            "weeks between",
            "months between",
            "difference between",
            "how far apart",
            "how long between",
            "spacing between",
            "time apart",
        ]

        # Which to target patterns
        targeting_patterns = [
            "which one should i target",
            "which should i target",
            "which one to target",
            "which to target",
            "which should i focus",
            "which one should i focus",
            "which deadline should i",
            "which call should i",
            "which one to go for",
            "which to prioritize",
            "which to prioritise",
            "what should i aim for",
            "which one is best",
            "which is better",
            "should i go for",
        ]

        # Check for time gap query
        if has_deadline_listing_context and any(p in query_lower for p in time_gap_patterns):
            return {
                "thought": "User is asking about time gaps between deadlines they've seen. Providing deadline timing analysis with strategic guidance.",
                "action": "generate_guidance",
                "guidance_type": "deadline_time_gap",
                "response": self._generate_deadline_time_gap_guidance(context),
            }

        # Check for targeting query
        if has_deadline_listing_context and any(p in query_lower for p in targeting_patterns):
            return {
                "thought": "User is asking which deadline to target from the list. Providing targeting recommendation framework.",
                "action": "generate_guidance",
                "guidance_type": "deadline_targeting",
                "response": self._generate_deadline_targeting_guidance(context),
            }

        return None

    def _detect_multi_call_timeline_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect multi-call timeline planning queries.

        These are questions about:
        - Planning multiple proposal submissions in a quarter/period
        - Managing staggered deadlines across multiple calls
        - Contingency planning when deadlines change
        - Backup call identification

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Check for multi-call planning context
        has_multi_call_context = any(
            pattern in context_lower
            for pattern in [
                "3 calls",
                "three calls",
                "multiple calls",
                "several calls",
                "this quarter",
                "staggered",
                "climate",
                "energy",
                "backup",
                "alternative",
            ]
        )

        # Multi-call planning intro patterns (Turn 1: "I want to apply to 3 calls this quarter")
        multi_call_planning_patterns = [
            "apply to 3 calls",
            "apply to three calls",
            "apply to multiple calls",
            "apply to several calls",
            "submit 3 proposals",
            "submit three proposals",
            "submit multiple proposals",
            "submit several proposals",
            "want to apply to 3",
            "want to apply to three",
            "want to apply to multiple",
            "plan to apply to 3",
            "plan to apply to three",
            "planning 3 submissions",
            "planning three submissions",
            "3 calls this quarter",
            "three calls this quarter",
            "multiple submissions",
            "several submissions",
            "manage multiple proposals",
            "multiple proposals",
            "3 proposals",
            "three proposals",
        ]

        # Deadline change / contingency patterns (Turn 4: "What if one call deadline changes?")
        deadline_change_patterns = [
            "deadline changes",
            "deadline change",
            "if one deadline changes",
            "if a deadline changes",
            "if the deadline changes",
            "what if deadline",
            "what if one call deadline",
            "what if a call deadline",
            "deadline shifts",
            "deadline moves",
            "deadline is moved",
            "deadline gets extended",
            "deadline postponed",
            "if deadline is postponed",
            "if they extend",
            "if they move",
            "if they change the deadline",
            "contingency",
            "contingency plan",
            "backup plan",
            "plan b",
            "what happens if",
        ]

        # Backup/alternative call patterns (Turn 5: "Show alternative calls as backup")
        # NOTE: This should use tool-based search, so we don't intercept it

        # Check for multi-call planning intro query
        if any(pattern in query_lower for pattern in multi_call_planning_patterns):
            return {
                "thought": "User wants to plan multiple proposal submissions. Providing strategic multi-call planning guidance with actionable next steps.",
                "action": "generate_guidance",
                "guidance_type": "multi_call_planning",
                "response": self._generate_multi_call_planning_guidance(),
            }

        # Check for deadline change / contingency query
        if any(pattern in query_lower for pattern in deadline_change_patterns) or (
            has_multi_call_context
            and any(p in query_lower for p in ["what if", "change", "contingency", "backup"])
        ):
            return {
                "thought": "User is asking about deadline changes and contingency planning. Providing deadline contingency guidance.",
                "action": "generate_guidance",
                "guidance_type": "deadline_contingency",
                "response": self._generate_deadline_contingency_guidance(context),
            }

        return None

    def _detect_sme_eligibility_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect SME eligibility queries.

        These are questions about:
        - EU SME definition (employees, turnover, balance sheet)
        - Linked/partner enterprise rules (parent company effects)
        - Non-SME participation in RIA/IA
        - SME-specific funding opportunities

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Check if there's SME context from earlier in conversation
        has_sme_context = any(
            pattern in context_lower
            for pattern in [
                "sme",
                "small",
                "medium",
                "employee",
                "200 employee",
                "parent company",
                "ownership",
                "linked enterprise",
            ]
        )

        # SME definition / employee count patterns
        sme_definition_patterns = [
            "what is an sme",
            "what's an sme",
            "sme definition",
            "sme criteria",
            "sme requirements",
            "employees",
            "headcount",
            "staff count",
            "250 employees",
            "50 million",
            "43 million",
            "turnover",
            "balance sheet",
            "eu definition of sme",
            "qualify as sme",
            "qualify as an sme",
            "considered an sme",
            "still an sme",
            "still sme",
            "count as sme",
            "still considered",
        ]

        # Linked enterprise / ownership patterns
        ownership_patterns = [
            "parent company",
            "parent corporation",
            "ownership",
            "owned by",
            "subsidiary",
            "linked enterprise",
            "partner enterprise",
            "affiliated",
            "affiliate",
            "majority shareholder",
            "majority owner",
            "controlling stake",
            "25%",
            "50%",
            "autonomous",
            "affect our sme",
            "affect sme status",
            "disqualify",
            "lose sme status",
        ]

        # Non-SME participation patterns (RIA/IA without SME status)
        non_sme_participation_patterns = [
            "don't qualify as sme",
            "don't qualify as an sme",
            "not an sme",
            "not sme",
            "if we're not sme",
            "if we are not sme",
            "if not sme",
            "without sme status",
            "non-sme",
            "large company",
            "large enterprise",
            "regular ria",
            "regular ia",
            "normal ria",
            "still participate",
            "still take part",
            "can we still",
            "participate in ria",
            "participate in ia",
            "join ria",
            "join ia",
        ]

        # SME funding opportunities patterns - ONLY explicit SME mentions
        # NOTE: "what's available" removed - too generic, matches project searches
        sme_opportunities_patterns = [
            "sme funding",
            "funding for sme",
            "sme opportunities",
            "sme programmes",
            "sme programs",
            "specifically for sme",
            "sme-specific",
            "dedicated to sme",
            "available for sme",
            "we're an sme",
            "we are an sme",
            "as an sme",
            "i'm an sme",
            "i am an sme",
        ]
        # Generic availability patterns that need SME context
        availability_with_sme_patterns = [
            "what's available",
            "what is available",
        ]

        # EIC-specific SME patterns (for follow-up in SME context)
        eic_sme_patterns = [
            "eic accelerator",
            "eic sme",
            "sme eic",
            "accelerator requirements",
            "sme requirements different",
            "different sme requirements",
            "different there",
        ]

        # Check if this is a follow-up about non-SME participation in RIA
        # Context contains parent company discussion AND query asks about participation
        if has_sme_context and any(
            p in query_lower for p in ["don't qualify", "can we still", "still participate"]
        ):
            # Check if the query is about RIA/IA participation (not urgent deadline)
            if any(p in query_lower for p in ["ria", "ia", "project", "participate"]):
                return {
                    "thought": "User is asking about participating in RIA/IA without SME status. Providing guidance on non-SME participation options.",
                    "action": "generate_guidance",
                    "guidance_type": "non_sme_participation",
                    "response": self._generate_non_sme_participation_guidance(),
                }

        # Check for non-SME participation query (most specific - check first)
        if any(pattern in query_lower for pattern in non_sme_participation_patterns):
            # Only match if context or query suggests RIA/IA/project participation
            if any(
                p in query_lower or p in context_lower
                for p in ["ria", "ia", "project", "participate", "horizon"]
            ):
                return {
                    "thought": "User asking about non-SME participation in RIA/IA projects. Providing guidance on participation options.",
                    "action": "generate_guidance",
                    "guidance_type": "non_sme_participation",
                    "response": self._generate_non_sme_participation_guidance(),
                }

        # Check for EIC SME requirements query (when in SME context)
        if has_sme_context and any(pattern in query_lower for pattern in eic_sme_patterns):
            return {
                "thought": "User asking about EIC Accelerator SME requirements specifically. Providing EIC SME guidance.",
                "action": "generate_guidance",
                "guidance_type": "eic_sme_requirements",
                "response": self._generate_eic_sme_requirements_guidance(),
            }

        # Check for linked enterprise / ownership query
        if any(pattern in query_lower for pattern in ownership_patterns):
            return {
                "thought": "User asking about how parent company/ownership affects SME status. Providing linked enterprise guidance.",
                "action": "generate_guidance",
                "guidance_type": "linked_enterprise",
                "response": self._generate_linked_enterprise_guidance(),
            }

        # Check for SME definition / employee count query
        if any(pattern in query_lower for pattern in sme_definition_patterns):
            return {
                "thought": "User asking about SME definition/criteria. Providing EU SME definition guidance.",
                "action": "generate_guidance",
                "guidance_type": "sme_definition",
                "response": self._generate_sme_definition_guidance(),
            }

        # Check for SME funding opportunities query - explicit SME mentions
        if any(pattern in query_lower for pattern in sme_opportunities_patterns):
            return {
                "thought": "User asking about funding opportunities for SMEs. Providing SME funding overview with actionable next steps.",
                "action": "generate_guidance",
                "guidance_type": "sme_opportunities",
                "response": self._generate_sme_opportunities_guidance(),
            }

        # Check for availability patterns ONLY when there's SME context
        # This prevents "what's available for X" from triggering SME guidance
        # when user is asking about project/call availability for a topic
        if has_sme_context and any(
            pattern in query_lower for pattern in availability_with_sme_patterns
        ):
            return {
                "thought": "User asking what's available (in SME context). Providing SME funding overview with actionable next steps.",
                "action": "generate_guidance",
                "guidance_type": "sme_opportunities",
                "response": self._generate_sme_opportunities_guidance(),
            }

        return None

    def _detect_consortium_eligibility_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect consortium eligibility queries.

        These are questions about:
        - Consortium composition (partners from multiple countries)
        - Minimum consortium requirements (3 entities from 3 countries)
        - Third country participation (US, Japan, China, etc.)
        - Associated country status (Switzerland, UK, Norway, etc.)
        - Eligibility for specific consortium configurations

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # === Pattern 1: Context-setting with consortium countries ===
        # e.g., "We have partners from Germany, France, and UK for a Horizon Europe project"
        # e.g., "Our consortium includes Spain, Italy, and Greece"
        consortium_context_patterns = [
            "have partners from",
            "partners from",
            "our consortium",
            "consortium includes",
            "consortium with",
            "we have a consortium",
            "partners in our consortium",
            "our partners are from",
            "we're coordinating with",
            "we are coordinating with",
        ]

        # Check if this is context-setting about a consortium
        has_consortium_context = any(p in query_lower for p in consortium_context_patterns)

        # Check if multiple countries are mentioned
        eu_countries = [
            "germany",
            "france",
            "italy",
            "spain",
            "netherlands",
            "belgium",
            "austria",
            "sweden",
            "denmark",
            "finland",
            "ireland",
            "portugal",
            "greece",
            "poland",
            "czech",
            "hungary",
            "romania",
            "bulgaria",
            "croatia",
            "slovenia",
            "slovakia",
            "estonia",
            "latvia",
            "lithuania",
            "luxembourg",
            "malta",
            "cyprus",
        ]
        associated_countries = [
            "uk",
            "united kingdom",
            "switzerland",
            "swiss",
            "norway",
            "iceland",
            "israel",
            "turkey",
            "turkish",
            "serbia",
            "ukraine",
            "georgia",
            "armenia",
            "moldova",
            "albania",
            "montenegro",
            "bosnia",
            "kosovo",
            "north macedonia",
            "faroe islands",
            "tunisia",
            "morocco",
            # Note: Canada is NOT an associated country - it's a third country
        ]
        third_countries = [
            "us",
            "usa",
            "united states",
            "american",
            "canada",  # Canada is a third country, not associated
            "canadian",
            "china",
            "chinese",
            "japan",
            "japanese",
            "australia",
            "australian",
            "india",
            "indian",
            "brazil",
            "brazilian",
            "south korea",
            "korean",
            "mexico",
            "mexican",
        ]

        countries_mentioned = []
        for country in eu_countries + associated_countries:
            if country in query_lower:
                countries_mentioned.append(country)

        # If context-setting with consortium/partners, acknowledge and provide guidance
        if has_consortium_context and len(countries_mentioned) >= 2:
            guidance = self._generate_consortium_context_guidance(countries_mentioned, query_lower)
            return {
                "thought": f"User is providing consortium context with partners from {', '.join(countries_mentioned)}. Acknowledging and providing eligibility overview.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "consortium_context",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 2: Minimum consortium requirements ===
        # IMPORTANT: Check this BEFORE generic eligibility to prevent "minimum...eligible" matching eligibility
        # e.g., "What's the minimum consortium?", "Minimum requirements for consortium?"
        minimum_patterns = [
            "minimum consortium",
            "minimum requirements",
            "minimum number of partners",
            "how many partners",
            "how many countries",
            "minimum entities",
            "minimum legal entities",
            "smallest consortium",
            "least partners",
            "at least how many",
            "minimum to apply",
            "minimum to be eligible",
            "consortium minimum",
            "required consortium",
        ]

        if any(p in query_lower for p in minimum_patterns):
            guidance = self._generate_minimum_consortium_guidance()
            return {
                "thought": "User is asking about minimum consortium requirements. Providing standard consortium eligibility rules.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "minimum_consortium",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Is consortium eligible? ===
        # e.g., "Is this consortium eligible?", "Are we eligible?"
        eligibility_check_patterns = [
            "is this consortium eligible",
            "is our consortium eligible",
            "are we eligible",
            "does this consortium meet",
            "do we meet the requirements",
            "eligible for horizon",
            "eligible for funding",
            "consortium eligible",
            "we eligible",
            "eligibility of our consortium",
        ]

        # Check if there's consortium context from previous turns
        has_previous_consortium_context = any(
            ind in context_lower
            for ind in [
                "partners from",
                "consortium",
                "germany",
                "france",
                "uk",
                "united kingdom",
                "our partners",
            ]
        )

        if any(p in query_lower for p in eligibility_check_patterns) or (
            "eligible" in query_lower and has_previous_consortium_context
        ):
            guidance = self._generate_consortium_eligibility_guidance(context_lower)
            return {
                "thought": "User is asking about consortium eligibility. Providing eligibility criteria and confirming their consortium meets requirements.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "consortium_eligibility",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: Adding Swiss partner ===
        # e.g., "What if we add a Swiss partner?", "Can we include Switzerland?"
        swiss_patterns = [
            "swiss partner",
            "switzerland partner",
            "add a swiss",
            "adding a swiss",
            "include switzerland",
            "swiss organization",
            "swiss university",
            "partner from switzerland",
            "what about switzerland",
            "what about swiss",
            "including swiss",
        ]

        if any(p in query_lower for p in swiss_patterns):
            guidance = self._generate_switzerland_participation_guidance()
            return {
                "thought": "User is asking about adding a Swiss partner. Providing Switzerland's current participation status in Horizon Europe.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "switzerland_participation",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: US/Third country partner participation ===
        # e.g., "Can American organizations participate?", "What about a US partner?"
        us_third_country_patterns = [
            "us partner",
            "usa partner",
            "american partner",
            "american organization",
            "american university",
            "united states partner",
            "what about us",
            "what about a us",
            "can american",
            "can us",
            "third country partner",
            "third country participation",
            "non-eu partner",
            "non-eu organization",
            "partner from us",
            "partner from usa",
            "from united states",
        ]

        # Check for third country context
        has_third_country_question = any(p in query_lower for p in us_third_country_patterns)

        # Also catch generic "can X participate" for known third countries
        # NOTE: Use word boundary regex to avoid false positives like "us" matching inside "Erasmus"
        import re

        third_country_participate = False
        detected_third_country = None  # Track which specific third country was mentioned

        # Map third country terms to their display names
        third_country_display_names = {
            "us": "USA",
            "usa": "USA",
            "united states": "USA",
            "american": "USA",
            "china": "China",
            "chinese": "China",
            "japan": "Japan",
            "japanese": "Japan",
            "australia": "Australia",
            "australian": "Australia",
            "india": "India",
            "indian": "India",
            "brazil": "Brazil",
            "brazilian": "Brazil",
            "south korea": "South Korea",
            "korean": "South Korea",
            "mexico": "Mexico",
            "mexican": "Mexico",
            "canada": "Canada",
            "canadian": "Canada",
        }

        for tc in third_countries:
            # Use word boundary for short country codes like "us" to avoid matching "Erasmus"
            if len(tc) <= 3:
                # Use regex word boundary for short strings
                if re.search(rf"\b{re.escape(tc)}\b", query_lower) and (
                    "participat" in query_lower
                    or "join" in query_lower
                    or "partner" in query_lower
                    or "eligible" in query_lower
                    or "eu funding" in query_lower
                ):
                    third_country_participate = True
                    detected_third_country = third_country_display_names.get(tc, tc.title())
                    break
            elif tc in query_lower and (
                "participat" in query_lower
                or "join" in query_lower
                or "partner" in query_lower
                or "eligible" in query_lower
                or "eu funding" in query_lower
            ):
                third_country_participate = True
                detected_third_country = third_country_display_names.get(tc, tc.title())
                break

        if has_third_country_question or third_country_participate:
            guidance = self._generate_third_country_participation_guidance(
                country=detected_third_country
            )
            country_desc = detected_third_country if detected_third_country else "non-EU"
            return {
                "thought": f"User is asking about {country_desc} (third country) participation in EU funding. Providing third country participation rules.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "third_country_participation",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_cross_programme_eligibility_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect cross-programme eligibility queries.

        These are questions about:
        - Double funding rules (same project in multiple EU programmes)
        - Complementary funding (different components of same initiative)
        - Simultaneous applications to multiple programmes
        - Best strategy for multi-programme funding approach
        - Non-cumulative funding principle

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # === Pattern 1: Double funding / same project in multiple programmes ===
        # e.g., "Can we have the same project funded by both Horizon Europe and Erasmus+?"
        # e.g., "Is it allowed to get funding from both programmes?"
        double_funding_patterns = [
            "same project funded by both",
            "same project in both",
            "same project from both",
            "funded by both horizon",
            "funded by both eu",
            "both horizon europe and erasmus",
            "both erasmus and horizon",
            "both horizon and creative",
            "both creative europe and",
            "horizon europe and erasmus",
            "horizon and erasmus",
            "erasmus and horizon",
            "creative europe and horizon",
            "horizon and creative",
            "double funded",
            "duplicate funding",
            "funding from both",
            "funding from multiple",
            "apply to both programmes",
            "apply for both programmes",
            "funded twice",
            "fund the same",
        ]

        # Check if asking about double funding of same project
        if any(p in query_lower for p in double_funding_patterns):
            guidance = self._generate_double_funding_guidance()
            return {
                "thought": "User is asking about double funding rules - whether the same project can be funded by multiple EU programmes. Providing guidance on the non-cumulative funding principle.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "double_funding_rules",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 2: Complementary funding / different components ===
        # e.g., "What about different components of the same initiative?"
        # e.g., "Can research be funded by Horizon Europe and training by Erasmus+?"
        complementary_patterns = [
            "different components",
            "different parts of",
            "research funded by horizon",
            "training funded by erasmus",
            "training by erasmus",
            "research by horizon",
            "separate components",
            "separate activities",
            "different activities",
            "complementary funding",
            "complementary approach",
            "split the funding",
            "split between programmes",
            "divide between",
            "one part horizon",
            "one part erasmus",
            "research component",
            "training component",
            "education component",
        ]

        if any(p in query_lower for p in complementary_patterns):
            guidance = self._generate_complementary_funding_guidance()
            return {
                "thought": "User is asking about complementary funding - different components of an initiative funded by different programmes. Providing guidance on how to properly separate activities.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "complementary_funding",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Specific double funding rules / what is prohibited ===
        # e.g., "Are there specific rules against double funding?"
        # e.g., "What exactly is prohibited?"
        rules_patterns = [
            "double funding rule",
            "double-funding rule",
            "rules against double",
            "what is prohibited",
            "what's prohibited",
            "exactly is prohibited",
            "specific rules",
            "non-cumulative funding",
            "cumulative funding",
            "funding overlap",
            "overlap of funding",
            "overlap in funding",
            "eu funding rules",
            "financial regulation",
            "double financing",
            "declaring costs",
            "same costs",
        ]

        # Check if context mentions cross-programme or double funding
        has_cross_programme_context = any(
            ind in context_lower
            for ind in [
                "horizon europe and erasmus",
                "both programmes",
                "double funding",
                "same project",
                "multiple programmes",
            ]
        )

        if any(p in query_lower for p in rules_patterns) or (
            "prohibited" in query_lower and has_cross_programme_context
        ):
            guidance = self._generate_double_funding_rules_guidance()
            return {
                "thought": "User is asking about specific EU double funding rules and what is prohibited. Providing detailed guidance on the EU Financial Regulation.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "double_funding_rules_detailed",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: Simultaneous applications ===
        # e.g., "Can we apply to both at the same time?"
        # e.g., "Simultaneous applications to Horizon and Erasmus?"
        simultaneous_patterns = [
            "simultaneous application",
            "simultaneous submission",
            "apply to both at the same time",
            "submit to both at the same time",
            "at the same time for related",
            "at the same time for different",
            "parallel application",
            "parallel submission",
            "multiple applications",
            "apply simultaneously",
            "submit simultaneously",
            "same deadline",
            "same time period",
        ]

        if any(p in query_lower for p in simultaneous_patterns):
            guidance = self._generate_simultaneous_applications_guidance()
            return {
                "thought": "User is asking about submitting simultaneous applications to multiple EU programmes. Providing guidance on parallel applications.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "simultaneous_applications",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: Strategy for multi-programme approach ===
        # e.g., "What's the best strategy for maximizing our chances across both programmes?"
        # e.g., "How to approach multiple EU programmes?"
        strategy_patterns = [
            "strategy for maximizing",
            "strategy for both",
            "strategy across both",
            "strategy across programmes",
            "maximize chances across",
            "maximizing our chances",
            "best approach for both",
            "how to approach multiple",
            "multi-programme strategy",
            "multi-programme approach",
            "portfolio strategy",
            "funding portfolio",
            "diversify funding",
            "spread across programmes",
            "optimize our applications",
        ]

        # Also catch strategic follow-up questions in cross-programme context
        strategic_follow_up = (
            "best strategy" in query_lower
            or "maximize" in query_lower
            or "maximizing" in query_lower
        ) and has_cross_programme_context

        if any(p in query_lower for p in strategy_patterns) or strategic_follow_up:
            guidance = self._generate_cross_programme_strategy_guidance()
            return {
                "thought": "User is asking about strategic approach to applying for multiple EU programmes. Providing comprehensive multi-programme strategy guidance.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "cross_programme_strategy",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_erasmus_programme_guide_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect queries about Erasmus+ Programme Guide content.

        This handles queries like:
        - "What are the Erasmus+ quality criteria?"
        - "How are Erasmus+ applications evaluated?"
        - "What are the award criteria for Erasmus+?"
        - "What does the Erasmus+ Programme Guide say about..."
        - "Erasmus+ evaluation process"

        These queries should use search_erasmus_templates to find Programme Guide 2026 content,
        NOT provide generic hardcoded guidance.

        The system has Programme Guide 2026 and AWP 2026 indexed.
        """
        query_lower = query.lower()

        # Pattern 1: Explicit Erasmus+ reference + Programme Guide content query
        erasmus_patterns = [
            "erasmus+",
            "erasmus plus",
            "erasmus ",
        ]

        # Content patterns that indicate seeking Programme Guide content
        guide_content_patterns = [
            "quality criteria",
            "quality assessment",
            "award criteria",
            "evaluation criteria",
            "selection criteria",
            "how are.*evaluated",
            "how.*assess",
            "assessment criteria",
            "scoring criteria",
            "marking criteria",
            "points criteria",
            "programme guide say",
            "programme guide",
            "what criteria",
            "eligibility criteria",
            "exclusion criteria",
            "relevance criteria",
            "impact criteria",
            "quality of.*design",
            "quality of.*implementation",
        ]

        import re

        has_erasmus_reference = any(pattern in query_lower for pattern in erasmus_patterns)

        # Check for guide content patterns (some are regex)
        has_guide_content = False
        for pattern in guide_content_patterns:
            if ".*" in pattern:
                # It's a regex pattern
                if re.search(pattern, query_lower):
                    has_guide_content = True
                    break
            elif pattern in query_lower:
                has_guide_content = True
                break

        if has_erasmus_reference and has_guide_content:
            # Determine the search query based on detected content
            search_query = self._build_erasmus_guide_search_query(query_lower)

            # Detect Key Action context if present
            key_action = None
            if "ka1" in query_lower or "mobility" in query_lower:
                key_action = "KA1"
            elif (
                "ka2" in query_lower or "partnership" in query_lower or "cooperation" in query_lower
            ):
                key_action = "KA2"
            elif "ka3" in query_lower or "policy" in query_lower:
                key_action = "KA3"
            elif "jean monnet" in query_lower:
                key_action = "JMO"
            elif "sport" in query_lower:
                key_action = "SPORT"

            return {
                "thought": f"User is asking about Erasmus+ Programme Guide content (quality criteria, evaluation). Using search_erasmus_templates to find relevant sections from Programme Guide 2026. Search: '{search_query}'",
                "action": "call_tools_and_format",
                "tool_calls": [
                    {
                        "tool": "search_erasmus_templates",
                        "parameters": {
                            "query": search_query,
                            "key_action": key_action,
                            "document_type": "quality_criteria",
                            "top_k": 8,
                        },
                        "reasoning": "Searching Erasmus+ Programme Guide 2026 for quality/evaluation criteria",
                    }
                ],
                "needs_more_info": True,
                "format_type": "erasmus_guide",
            }

        # Pattern 2: Generic Programme Guide queries
        # e.g., "Tell me about the Erasmus+ Programme Guide", "What's in the 2026 guide?"
        programme_guide_patterns = [
            r"erasmus.*programme\s*guide",
            r"erasmus.*guide\s*2026",
            r"erasmus.*2026\s*guide",
            r"erasmus.*guide.*say",
        ]

        for pattern in programme_guide_patterns:
            if re.search(pattern, query_lower):
                search_query = self._build_erasmus_guide_search_query(query_lower)

                return {
                    "thought": f"User is asking about Erasmus+ Programme Guide content. Using search_erasmus_templates to find relevant sections. Search: '{search_query}'",
                    "action": "call_tools_and_format",
                    "tool_calls": [
                        {
                            "tool": "search_erasmus_templates",
                            "parameters": {
                                "query": search_query,
                                "top_k": 8,
                            },
                            "reasoning": "Searching Erasmus+ Programme Guide 2026 for content",
                        }
                    ],
                    "needs_more_info": True,
                    "format_type": "erasmus_guide",
                }

        return None

    def _detect_erasmus_action_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect Erasmus+ action selection and sector-specific queries.

        These are questions about:
        - Erasmus+ Key Actions overview (KA1, KA2, KA3, Jean Monnet, Sport)
        - Sector-specific mobility options (VET, HED, SCH, ADU, YOU)
        - VET partnerships and cooperation
        - KA2 Cooperation Partnerships and curriculum development
        - Strategy for combining KA1 mobility with KA2 partnerships

        These queries should provide structured guidance with actionable Next Steps.

        IMPORTANT: When a query mentions a SPECIFIC COUNTRY (e.g., "Poland", "Germany"),
        we should NOT use hardcoded guidance. Instead, return None to let the agent
        use the check_erasmus_eligibility tool which can provide country-specific info.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # List of countries that should trigger tool usage instead of hardcoded guidance
        # This enables country-specific eligibility checks with National Agency info
        eu_countries = [
            "austria",
            "belgium",
            "bulgaria",
            "croatia",
            "cyprus",
            "czech republic",
            "denmark",
            "estonia",
            "finland",
            "france",
            "germany",
            "greece",
            "hungary",
            "ireland",
            "italy",
            "latvia",
            "lithuania",
            "luxembourg",
            "malta",
            "netherlands",
            "poland",
            "portugal",
            "romania",
            "slovakia",
            "slovenia",
            "spain",
            "sweden",
        ]
        associated_countries = [
            "iceland",
            "liechtenstein",
            "norway",
            "north macedonia",
            "serbia",
            "turkey",
        ]
        partner_countries = [
            "albania",
            "bosnia and herzegovina",
            "kosovo",
            "montenegro",
            "armenia",
            "azerbaijan",
            "belarus",
            "georgia",
            "moldova",
            "ukraine",
            "algeria",
            "egypt",
            "israel",
            "jordan",
            "lebanon",
            "libya",
            "morocco",
            "palestine",
            "syria",
            "tunisia",
        ]
        all_countries = eu_countries + associated_countries + partner_countries

        # Check if a specific country is mentioned
        country_mentioned = None
        for country in all_countries:
            if country in query_lower:
                country_mentioned = country
                break

        # Eligibility indicator patterns
        eligibility_patterns = [
            "can participate",
            "participate in",
            "eligible",
            "eligibility",
            "can apply",
            "able to apply",
            "can a ",
            "can an ",
            "can our",
            "is eligible",
            "are eligible",
            "qualify for",
            "qualifies for",
        ]
        has_eligibility_question = any(p in query_lower for p in eligibility_patterns)

        # Skip if query explicitly mentions another programme (Creative Europe, EU4Health, etc.)
        # to allow programme-specific detection methods to handle them
        other_programmes = [
            "creative europe",
            "creative-europe",
            "eu4health",
            "digital europe",
            "life programme",
            # Horizon Europe programmes - skip to let EIC/ERC handlers process them
            "horizon europe",
            "horizon-europe",
            "eic accelerator",
            "eic pathfinder",
            "eic transition",
            "erc grant",
            "erc starting",
            "erc consolidator",
            "erc advanced",
            "erc synergy",
            "ria grant",
            "ia grant",
            "csa grant",
            "msca",
            "marie curie",
        ]
        if any(prog in query_lower for prog in other_programmes):
            return None

        # If a specific country is mentioned AND it's an eligibility question,
        # call check_erasmus_eligibility tool with properly extracted parameters
        if country_mentioned and has_eligibility_question:
            # Detect organization type from query
            org_type = "HEI"  # default
            if any(
                kw in query_lower
                for kw in ["vocational", "vet school", "vet provider", "vet institution"]
            ):
                org_type = "VET_PROVIDER"
            elif any(kw in query_lower for kw in ["school", "primary school", "secondary school"]):
                org_type = "SCHOOL"
            elif any(kw in query_lower for kw in ["university", "higher education", "college"]):
                org_type = "HEI"
            elif any(kw in query_lower for kw in ["adult education", "adult learning"]):
                org_type = "ADULT_ED"
            elif any(
                kw in query_lower for kw in ["youth organization", "youth org", "youth group"]
            ):
                org_type = "YOUTH_ORG"
            elif any(kw in query_lower for kw in ["ngo", "non-governmental", "non-profit"]):
                org_type = "NGO"
            elif any(kw in query_lower for kw in ["public body", "municipality", "government"]):
                org_type = "PUBLIC_BODY"
            elif any(kw in query_lower for kw in ["enterprise", "company", "business", "sme"]):
                org_type = "ENTERPRISE"
            elif any(kw in query_lower for kw in ["sport", "sports organization"]):
                org_type = "SPORT_ORG"

            # Detect action type from query
            action_type = None
            if "mobility" in query_lower:
                # Map org type to appropriate mobility action
                action_type_map = {
                    "VET_PROVIDER": "KA1-VET",
                    "SCHOOL": "KA1-SCH",
                    "HEI": "KA1-HED",
                    "ADULT_ED": "KA1-ADU",
                    "YOUTH_ORG": "KA1-YOU",
                }
                action_type = action_type_map.get(org_type, "KA1-VET")
            elif "partnership" in query_lower or "cooperation" in query_lower:
                action_type = "KA2-COOP"

            # Capitalize country name properly
            country_name = country_mentioned.title()

            # Return tool call configuration
            return {
                "thought": f"User is asking about Erasmus+ eligibility for a {org_type.replace('_', ' ')} from {country_name}. Calling check_erasmus_eligibility tool with specific parameters.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_erasmus_eligibility",
                        "parameters": {
                            "org_type": org_type,
                            "country": country_name,
                            "action_type": action_type,
                            "has_eche": False,
                            "is_coordinator": True,
                        },
                        "reasoning": f"Checking Erasmus+ KA1 VET mobility eligibility for vocational school from {country_name}",
                    }
                ],
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # Track if VET/sector context is present
        has_vet_context = any(
            ind in context_lower for ind in ["vet", "vocational", "vet school", "vet institution"]
        )
        has_mobility_context = any(
            ind in context_lower for ind in ["mobility", "ka1", "key action 1"]
        )
        has_partnership_context = any(
            ind in context_lower for ind in ["partnership", "ka2", "key action 2", "cooperation"]
        )

        # === Pattern 1: Erasmus+ actions overview ===
        # e.g., "What Erasmus+ actions are there?", "Explain Erasmus+ Key Actions"
        actions_overview_patterns = [
            "erasmus+ actions",
            "erasmus actions",
            "erasmus+ key action",
            "erasmus key action",
            "what are the erasmus",
            "what erasmus actions",
            "which erasmus actions",
            "explain erasmus+",
            "overview of erasmus+",
            "erasmus+ programme structure",
            "erasmus programme structure",
            "types of erasmus+",
            "types of erasmus",
            "erasmus+ options",
            "erasmus options",
            "ka1, ka2, ka3",
            "ka1 ka2 ka3",
        ]

        if any(p in query_lower for p in actions_overview_patterns):
            guidance = self._generate_erasmus_actions_overview_guidance()
            return {
                "thought": "User is asking about Erasmus+ actions overview. Providing comprehensive guidance on Key Actions (KA1, KA2, KA3), Jean Monnet, and Sport.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_actions_overview",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 2: VET mobility options ===
        # e.g., "What Erasmus+ mobility options are available for VET schools?"
        vet_mobility_patterns = [
            "vet mobility",
            "vet school mobility",
            "vet institution mobility",
            "vocational mobility",
            "vocational education mobility",
            "vocational training mobility",
            "mobility for vet",
            "mobility options for vet",
            "vet students abroad",
            "vet staff abroad",
            "vet exchange",
            "vet international",
            "vet learner mobility",
        ]

        # Check for VET + mobility combination in query
        has_vet_in_query = any(
            p in query_lower
            for p in ["vet", "vocational", "vocational education", "vocational training"]
        )
        has_mobility_in_query = any(
            p in query_lower for p in ["mobility", "abroad", "exchange", "international"]
        )

        if any(p in query_lower for p in vet_mobility_patterns) or (
            has_vet_in_query and has_mobility_in_query
        ):
            guidance = self._generate_vet_mobility_guidance()
            return {
                "thought": "User is asking about VET mobility options in Erasmus+. Providing guidance on KA1 mobility for VET sector.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "vet_mobility",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: VET partnerships / long-term cooperation ===
        # e.g., "What are the options for long-term partnerships between VET institutions?"
        vet_partnership_patterns = [
            "vet partnership",
            "vet institution partnership",
            "vet school partnership",
            "vocational partnership",
            "partnership between vet",
            "partnerships between vet",
            "vet cooperation",
            "vet collaboration",
            "long-term partnership",
            "long term partnership",
        ]

        # Check for VET + partnership combination
        has_partnership_in_query = any(
            p in query_lower for p in ["partnership", "cooperation", "collaboration", "long-term"]
        )

        if (
            any(p in query_lower for p in vet_partnership_patterns)
            or (has_vet_in_query and has_partnership_in_query)
            or (has_vet_context and has_partnership_in_query)
        ):
            guidance = self._generate_vet_partnership_guidance()
            return {
                "thought": "User is asking about VET partnership options in Erasmus+. Providing guidance on KA2 Cooperation Partnerships for VET sector.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "vet_partnership",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: KA2 curriculum development ===
        # e.g., "What curriculum-related activities are funded under Erasmus+ KA2?"
        curriculum_patterns = [
            "curriculum development",
            "curriculum-related",
            "curriculum activities",
            "develop curriculum",
            "developing curriculum",
            "new curriculum",
            "curriculum innovation",
            "ka2 curriculum",
            "cooperation partnership curriculum",
            "training materials",
            "educational resources",
            "joint curriculum",
            "curriculum design",
            "course development",
        ]

        # Check for KA2/partnership context + curriculum
        has_ka2_context = any(
            p in query_lower or p in context_lower
            for p in ["ka2", "key action 2", "cooperation partnership"]
        )
        has_curriculum_in_query = any(p in query_lower for p in curriculum_patterns)

        if has_curriculum_in_query and (
            has_ka2_context or has_vet_context or has_partnership_context
        ):
            guidance = self._generate_ka2_curriculum_guidance()
            return {
                "thought": "User is asking about curriculum development in Erasmus+ KA2. Providing guidance on Cooperation Partnerships and eligible activities.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "ka2_curriculum",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: KA1 + KA2 combination strategy ===
        # e.g., "How should a VET school combine KA1 mobility with KA2 partnerships?"
        combination_patterns = [
            "combine ka1",
            "combine ka2",
            "ka1 and ka2",
            "ka1 with ka2",
            "ka2 with ka1",
            "mobility and partnership",
            "mobility with partnership",
            "partnership and mobility",
            "combine mobility",
            "combine erasmus",
            "maximum benefit",
            "best combination",
            "strategy for vet",
            "vet school strategy",
            "vet action combination",
            "both ka1 and ka2",
        ]

        # Check for combination/strategy context
        has_combination_intent = any(
            p in query_lower
            for p in ["combine", "combination", "both", "together", "strategy", "maximum benefit"]
        )
        has_ka1_ka2_context = (has_mobility_context or "ka1" in query_lower) and (
            has_partnership_context or "ka2" in query_lower
        )

        if (
            any(p in query_lower for p in combination_patterns)
            or (has_vet_context and has_combination_intent and has_ka1_ka2_context)
            or (has_vet_in_query and has_combination_intent)
        ):
            guidance = self._generate_erasmus_combination_strategy_guidance()
            return {
                "thought": "User is asking about combining Erasmus+ KA1 and KA2 for VET. Providing strategic guidance on action combination.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_combination_strategy",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_erasmus_budget_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect Erasmus+ budget calculation and funding queries.

        These are questions about:
        - Erasmus+ funding model and budget components
        - Individual support rates and country groups
        - Staff mobility funding
        - Inclusion support and top-ups
        - Travel costs and distance bands

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Track if mobility context is present
        has_mobility_context = any(
            ind in context_lower
            for ind in ["mobility", "ka1", "student", "exchange", "staff", "travel"]
        )
        has_erasmus_context = any(
            ind in context_lower for ind in ["erasmus", "erasmus+", "ka1", "ka2"]
        )

        # === Pattern 1: Student mobility funding / budget components ===
        # e.g., "How does Erasmus+ fund student mobility activities?"
        # e.g., "What budget components are involved in Erasmus+?"
        funding_overview_patterns = [
            "erasmus+ fund",
            "erasmus fund",
            "erasmus+ funding",
            "erasmus funding",
            "budget component",
            "budget category",
            "funding model",
            "how is erasmus funded",
            "how does erasmus fund",
            "erasmus+ budget",
            "erasmus budget",
            "mobility funding",
            "student mobility funding",
            "learner mobility funding",
        ]

        has_funding_question = any(
            p in query_lower
            for p in [
                "fund",
                "budget",
                "cost",
                "grant",
                "finance",
                "money",
                "component",
            ]
        )
        has_erasmus_in_query = "erasmus" in query_lower
        has_mobility_in_query = any(
            p in query_lower for p in ["mobility", "student", "learner", "exchange"]
        )

        if any(p in query_lower for p in funding_overview_patterns) or (
            has_erasmus_in_query and has_mobility_in_query and has_funding_question
        ):
            guidance = self._generate_erasmus_funding_overview_guidance()
            return {
                "thought": "User is asking about Erasmus+ funding model and budget components. "
                "Providing comprehensive overview of unit costs, individual support, travel, "
                "and organisational support.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_funding_overview",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 2: Individual support rates ===
        # e.g., "What are the individual support rates in Erasmus+?"
        # e.g., "How much do students receive per day/month?"
        individual_support_patterns = [
            "individual support",
            "individual support rate",
            "support rate",
            "per day",
            "per month",
            "daily rate",
            "monthly rate",
            "subsistence",
            "living cost",
            "living allowance",
            "country group",
            "destination country rate",
            "how much do student",
            "student receive",
            "learner receive",
        ]

        has_rate_question = any(
            p in query_lower
            for p in ["rate", "how much", "receive", "amount", "per day", "per month"]
        )

        if any(p in query_lower for p in individual_support_patterns) or (
            has_erasmus_context and has_rate_question
        ):
            guidance = self._generate_erasmus_individual_support_guidance()
            return {
                "thought": "User is asking about Erasmus+ individual support rates. "
                "Providing detailed country groups and rate tables.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_individual_support",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Staff mobility funding ===
        # e.g., "What about staff mobility in Erasmus+?"
        # e.g., "How is staff training funded?"
        staff_mobility_patterns = [
            "staff mobility",
            "staff training",
            "teacher mobility",
            "trainer mobility",
            "staff exchange",
            "teaching assignment",
            "teaching staff",
            "staff fund",
            "staff funding",
            "staff grant",
            "staff travel",
            "professional development",
            "job shadow",
        ]

        has_staff_question = any(
            p in query_lower for p in ["staff", "teacher", "trainer", "teaching", "professional"]
        )
        has_funding_in_query = any(
            p in query_lower for p in ["fund", "grant", "support", "finance", "paid"]
        )

        if any(p in query_lower for p in staff_mobility_patterns) or (
            has_mobility_context
            and has_staff_question
            and (has_funding_in_query or has_erasmus_in_query)
        ):
            guidance = self._generate_erasmus_staff_mobility_guidance()
            return {
                "thought": "User is asking about Erasmus+ staff mobility funding. "
                "Providing detailed information on staff mobility rates and activities.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_staff_mobility",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: Inclusion support ===
        # e.g., "What is inclusion support in Erasmus+ mobility projects?"
        # e.g., "Funding for participants with disabilities?"
        inclusion_patterns = [
            "inclusion support",
            "fewer opportunities",
            "disability",
            "disabilities",
            "special needs",
            "top-up",
            "top up",
            "additional support",
            "disadvantaged",
            "barrier",
            "accessibility",
            "exceptional cost",
            "real cost",
            "actual cost",
            "green travel",
            "sustainable travel",
        ]

        has_inclusion_question = any(
            p in query_lower
            for p in [
                "inclusion",
                "disability",
                "special",
                "additional",
                "fewer",
                "disadvantaged",
            ]
        )

        if any(p in query_lower for p in inclusion_patterns) or (
            has_mobility_context and has_inclusion_question
        ):
            guidance = self._generate_erasmus_inclusion_support_guidance()
            return {
                "thought": "User is asking about Erasmus+ inclusion support and top-ups. "
                "Providing information on support for participants with fewer opportunities.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_inclusion_support",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: Travel costs / distance bands ===
        # e.g., "How are travel costs calculated in Erasmus+ mobility?"
        # e.g., "What are the travel distance bands?"
        travel_patterns = [
            "travel cost",
            "travel support",
            "travel grant",
            "travel funding",
            "travel band",
            "distance band",
            "travel contribution",
            "travel allowance",
            "km",
            "kilometer",
            "kilometre",
            "flight",
            "train travel",
            "green travel",
            "sustainable travel",
            "travel calculation",
            "travel calculate",
        ]

        has_travel_question = any(
            p in query_lower
            for p in [
                "travel",
                "distance",
                "transport",
                "flight",
                "train",
                "km",
                "kilometer",
            ]
        )
        has_calculation_question = any(
            p in query_lower for p in ["calculate", "how much", "cost", "rate"]
        )

        if any(p in query_lower for p in travel_patterns) or (
            has_mobility_context
            and has_travel_question
            and (has_calculation_question or has_erasmus_in_query)
        ):
            guidance = self._generate_erasmus_travel_costs_guidance()
            return {
                "thought": "User is asking about Erasmus+ travel costs and distance bands. "
                "Providing detailed information on travel support calculations.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_travel_costs",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_erasmus_accreditation_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect Erasmus+ accreditation and short-term project queries.

        These are questions about:
        - Benefits of accreditation
        - Timeline and validity period
        - KA1 mobility without accreditation (short-term projects)
        - Strategic choice between accreditation and short-term projects
        - Erasmus+ accreditation concept and overview (general - checked LAST)

        IMPORTANT: More specific patterns (benefits, timeline, without, strategic)
        must be checked BEFORE the general overview pattern.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Track if accreditation context is present
        has_accreditation_context = any(
            ind in context_lower
            for ind in ["accreditation", "accredited", "erasmus plan", "long-term"]
        )
        has_erasmus_context = any(
            ind in context_lower for ind in ["erasmus", "erasmus+", "ka1", "mobility"]
        )
        has_short_term_context = any(
            ind in context_lower for ind in ["short-term", "short term", "project"]
        )

        # === Pattern 1: Benefits of accreditation (SPECIFIC - check first) ===
        # e.g., "What are the benefits of having Erasmus accreditation?"
        benefits_patterns = [
            "benefits of erasmus accreditation",
            "benefits of accreditation",
            "benefits of having",
            "advantage of accreditation",
            "advantages of accreditation",
            "why get accreditation",
            "why accreditation",
            "accreditation benefit",
            "accreditation advantage",
            "accreditation worth",
            "is accreditation worth",
            "value of accreditation",
        ]

        has_benefits_question = any(
            p in query_lower for p in ["benefit", "advantage", "worth", "value"]
        )

        if any(p in query_lower for p in benefits_patterns) or (
            has_accreditation_context and has_benefits_question
        ):
            guidance = self._generate_erasmus_accreditation_benefits_guidance()
            return {
                "thought": "User is asking about benefits of Erasmus+ accreditation. Providing detailed "
                "information on advantages, funding security, and simplified applications.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_accreditation_benefits",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 2: Timeline and validity (SPECIFIC - check before overview) ===
        # e.g., "How long does it take to get Erasmus accreditation and how long does it last?"
        timeline_patterns = [
            "how long does accreditation",
            "how long accreditation",
            "how long does it take",
            "how long does it last",
            "accreditation timeline",
            "accreditation valid",
            "accreditation validity",
            "accreditation last",
            "accreditation duration",
            "get accreditation take",
            "apply for accreditation timeline",
            "accreditation process time",
            "accreditation period",
            "when to apply accreditation",
        ]

        has_timeline_question = any(
            p in query_lower
            for p in [
                "how long",
                "timeline",
                "valid",
                "validity",
                "last",
                "duration",
                "period",
                "take",
            ]
        )

        if any(p in query_lower for p in timeline_patterns) or (
            has_accreditation_context and has_timeline_question
        ):
            guidance = self._generate_erasmus_accreditation_timeline_guidance()
            return {
                "thought": "User is asking about Erasmus+ accreditation timeline and validity. Providing "
                "information on application process, timeline, and validity period.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_accreditation_timeline",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Strategic choice between accreditation and short-term ===
        # e.g., "Should we pursue accreditation or stick with short-term projects?"
        # IMPORTANT: Check BEFORE "without accreditation" to prevent false matches on "short-term"
        strategic_patterns = [
            "strategic choice",
            "pursue accreditation",
            "accreditation or short-term",
            "accreditation vs short-term",
            "accreditation versus short-term",
            "accreditation or project",
            "accreditation vs project",
            "choose accreditation",
            "choose short-term",
            "which is better accreditation",
            "better accreditation or",
            "recommend accreditation",
            "stick with short-term",
            "stick with projects",
            "strategic decision",
            "strategic recommendation",
        ]

        has_strategic_question = any(
            p in query_lower
            for p in [
                "strategic",
                "pursue",
                "recommend",
                "better",
                "choose",
                "which",
                "vs",
                "versus",
                "stick",
            ]
        )
        has_comparison = any(
            p in query_lower for p in ["short-term", "project", "vs", "or", "versus"]
        )

        if any(p in query_lower for p in strategic_patterns) or (
            has_accreditation_context
            and has_strategic_question
            and (has_comparison or has_short_term_context)
        ):
            guidance = self._generate_erasmus_accreditation_strategic_guidance()
            return {
                "thought": "User is asking for strategic advice on accreditation vs short-term projects. "
                "Providing guidance on choosing the right approach based on organization needs.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_accreditation_strategic",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: KA1 without accreditation / short-term projects ===
        # e.g., "Can we still apply to Erasmus+ KA1 mobility without accreditation?"
        without_accreditation_patterns = [
            "without accreditation",
            "not accredited",
            "non-accredited",
            "non accredited",
            "ka1 without",
            "mobility without",
            "apply without accreditation",
            "short-term mobility",
            "short term mobility",
            "one-off project",
            "single project",
            "can we still apply",
            "alternative to accreditation",
        ]

        has_without_question = any(
            p in query_lower for p in ["without", "not", "alternative", "still", "non-accredited"]
        )
        has_ka1_question = any(p in query_lower for p in ["ka1", "mobility", "key action 1"])

        if any(p in query_lower for p in without_accreditation_patterns) or (
            (has_accreditation_context or has_erasmus_context)
            and has_without_question
            and has_ka1_question
        ):
            guidance = self._generate_erasmus_without_accreditation_guidance()
            return {
                "thought": "User is asking about Erasmus+ KA1 mobility without accreditation. Providing "
                "information on short-term project option as alternative.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_without_accreditation",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: Accreditation overview / what is it? (GENERAL - check LAST) ===
        # e.g., "Should we get Erasmus accreditation? What is it?"
        # e.g., "What is Erasmus+ accreditation?"
        # IMPORTANT: This catches broad patterns so it must be checked AFTER more specific patterns
        accreditation_overview_patterns = [
            "what is erasmus accreditation",
            "what is erasmus+ accreditation",
            "what's erasmus accreditation",
            "should we get erasmus accreditation",
            "should we get accreditation",
            "apply for accreditation",
            "get accredited",
            "become accredited",
            "erasmus plan",
            "what is accreditation",
            "accreditation explained",
            "accreditation overview",
        ]

        has_accreditation_question = any(
            p in query_lower for p in ["accreditation", "accredited", "erasmus plan"]
        )
        has_what_question = any(p in query_lower for p in ["what", "should", "is"])

        # Only match overview if the query contains accreditation AND none of the specific patterns matched
        if any(p in query_lower for p in accreditation_overview_patterns):
            guidance = self._generate_erasmus_accreditation_overview_guidance()
            return {
                "thought": "User is asking about Erasmus+ accreditation. Providing comprehensive overview "
                "of what accreditation is, its purpose, and key features.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_accreditation_overview",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # Fallback for general accreditation questions (from context)
        if has_accreditation_question and has_what_question and not has_benefits_question:
            guidance = self._generate_erasmus_accreditation_overview_guidance()
            return {
                "thought": "User is asking about Erasmus+ accreditation. Providing comprehensive overview "
                "of what accreditation is, its purpose, and key features.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "erasmus_accreditation_overview",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_associated_country_eligibility_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect associated country eligibility queries.

        These are questions about eligibility for organizations from Associated Countries
        (Turkey, Switzerland, Israel, Norway, etc.) including:
        - Coordinator eligibility (varies by country and topic)
        - Partner/beneficiary eligibility
        - Topic-specific restrictions (defense, quantum, space)
        - Where they CAN coordinate

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Associated countries with partial or full association
        associated_countries = [
            "turkey",
            "turkish",
            "switzerland",
            "swiss",
            "israel",
            "israeli",
            "norway",
            "norwegian",
            "iceland",
            "icelandic",
            "serbia",
            "serbian",
            "albania",
            "albanian",
            "montenegro",
            "north macedonia",
            "macedonian",
            "bosnia",
            "bosnian",
            "georgia",
            "georgian",
            "moldova",
            "moldovan",
            "ukraine",
            "ukrainian",
            "tunisia",
            "tunisian",
            "morocco",
            "moroccan",
            "armenia",
            "armenian",
            "faroe islands",
            "faroese",
            "uk",
            "united kingdom",
            "british",
            "associated country",
            "associated countries",
            "third country",
            "non-eu",
            "non-member",
        ]

        # Check if query involves associated country
        is_associated_country_query = any(
            country in query_lower for country in associated_countries
        ) or any(country in context_lower for country in associated_countries)

        # Extract which country is being discussed
        country_name = None
        for country in ["turkey", "turkish"]:
            if country in query_lower or country in context_lower:
                country_name = "Turkey"
                break
        for country in ["switzerland", "swiss"]:
            if country in query_lower or country in context_lower:
                country_name = "Switzerland"
                break
        for country in ["israel", "israeli"]:
            if country in query_lower or country in context_lower:
                country_name = "Israel"
                break
        for country in ["norway", "norwegian"]:
            if country in query_lower or country in context_lower:
                country_name = "Norway"
                break
        if not country_name:
            country_name = "associated country"

        # Coordinator eligibility patterns
        coordinator_patterns = [
            "can coordinate",
            "coordinate a horizon",
            "serve as coordinator",
            "be coordinator",
            "be a coordinator",
            "act as coordinator",
            "lead a project",
            "lead a consortium",
            "coordinate horizon",
            "coordinating entity",
            "coordinating organization",
            "can a turkish university coordinate",
            "can turkey coordinate",
            "can turkish coordinate",
            "can swiss coordinate",
            "can switzerland coordinate",
            "eligible to coordinate",
            "coordinator eligibility",
            "coordination eligibility",
        ]

        # Partner eligibility patterns
        partner_patterns = [
            "as a partner",
            "partner instead",
            "participate as partner",
            "participating as partner",
            "beneficiary",
            "partner role",
            "as participant",
            "join as partner",
            "partner eligibility",
            "can participate",
            "participation eligibility",
            "instead of coordinator",
        ]

        # Defense/dual-use restriction patterns
        defense_patterns = [
            "defense",
            "defence",
            "dual-use",
            "dual use",
            "military",
            "security",
            "sensitive topic",
            "sensitive research",
            "restricted topic",
            "classified",
            "strategic autonomy",
            "edf",
            "european defence fund",
            "defense research",
            "defence research",
            "security research",
        ]

        # Quantum/advanced technology restriction patterns
        quantum_patterns = [
            "quantum",
            "quantum technology",
            "quantum computing",
            "quantum communication",
            "space",
            "satellite",
            "advanced technology",
            "critical technology",
            "strategic technology",
            "chip",
            "semiconductor",
            "ai security",
            "artificial intelligence security",
        ]

        # Calls where associated countries CAN coordinate patterns
        can_coordinate_patterns = [
            "where can",
            "which calls can",
            "any calls where",
            "calls where",
            "where they can",
            "where we can",
            "eligible to coordinate",
            "allowed to coordinate",
            "can serve as coordinator",
            "can be coordinator",
            "topics where",
            "programmes where",
        ]

        # Check for coordinator eligibility query (initial question)
        if any(pattern in query_lower for pattern in coordinator_patterns):
            return {
                "thought": f"User asking about {country_name} coordinator eligibility in Horizon Europe. Providing structured eligibility guidance.",
                "action": "generate_guidance",
                "guidance_type": "associated_country_coordinator",
                "response": self._generate_associated_country_coordinator_guidance(country_name),
            }

        # Check for partner eligibility query (follow-up about partner role)
        if any(pattern in query_lower for pattern in partner_patterns) and (
            is_associated_country_query
            or "coordinator" in context_lower
            or "coordinate" in context_lower
        ):
            return {
                "thought": f"User asking about {country_name} partner eligibility. Clarifying partner vs coordinator rules.",
                "action": "generate_guidance",
                "guidance_type": "associated_country_partner",
                "response": self._generate_associated_country_partner_guidance(country_name),
            }

        # Check for defense/dual-use restriction query
        if any(pattern in query_lower for pattern in defense_patterns) and (
            is_associated_country_query
            or any(p in context_lower for p in ["turkey", "turkish", "associated", "coordinate"])
        ):
            return {
                "thought": f"User asking about defense/dual-use restrictions for {country_name}. Explaining topic-specific restrictions.",
                "action": "generate_guidance",
                "guidance_type": "defense_restrictions",
                "response": self._generate_defense_restriction_guidance(country_name),
            }

        # Check for quantum/advanced technology restriction query
        if any(pattern in query_lower for pattern in quantum_patterns) and (
            is_associated_country_query
            or any(
                p in context_lower
                for p in ["turkey", "turkish", "associated", "defense", "defence"]
            )
        ):
            return {
                "thought": f"User asking about quantum/advanced technology restrictions for {country_name}. Explaining strategic technology restrictions.",
                "action": "generate_guidance",
                "guidance_type": "quantum_restrictions",
                "response": self._generate_quantum_restriction_guidance(country_name),
            }

        # Check for "where CAN they coordinate" query
        if any(pattern in query_lower for pattern in can_coordinate_patterns) and (
            "coordinator" in query_lower
            or "coordinate" in query_lower
            or is_associated_country_query
            or any(p in context_lower for p in ["turkey", "turkish", "coordinator"])
        ):
            return {
                "thought": f"User asking where {country_name} organizations CAN coordinate. Listing eligible programmes/topics.",
                "action": "generate_guidance",
                "guidance_type": "can_coordinate",
                "response": self._generate_can_coordinate_guidance(country_name),
            }

        return None

    def _detect_creative_europe_media_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect Creative Europe MEDIA strand queries.

        These are questions about:
        - MEDIA strand overview and actions
        - Development funding (slate, single, co-development)
        - Distribution support (selective, automatic)
        - Training and skills development
        - Festivals and cinema networks
        - Multi-project participation rules

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Track if Creative Europe/MEDIA context is present
        has_ce_context = any(
            ind in context_lower
            for ind in [
                "creative europe",
                "media strand",
                "media programme",
                "film production",
                "audiovisual",
                "cinema",
            ]
        )
        has_media_context = any(
            ind in context_lower
            for ind in [
                "media",
                "media strand",
                "development funding",
                "distribution",
                "film",
            ]
        )
        has_film_context = any(
            ind in context_lower for ind in ["film", "cinema", "audiovisual", "production company"]
        )

        # === Pattern 1: MEDIA strand overview ===
        # e.g., "Tell me about the Creative Europe MEDIA strand"
        # e.g., "What is the MEDIA programme?"
        media_overview_patterns = [
            "media strand",
            "about media",
            "what is media",
            "the media programme",
            "media programme",
            "tell me about media",
            "explain media",
            "overview of media",
            "media actions",
            "media support",
            "creative europe media",
            "media sub-programme",
            "media subprogramme",
        ]

        if any(p in query_lower for p in media_overview_patterns):
            guidance = self._generate_media_strand_overview_guidance()
            return {
                "thought": "User is asking about Creative Europe MEDIA strand overview. Providing comprehensive guidance on MEDIA actions and support.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "media_strand_overview",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 2: Development funding ===
        # e.g., "What Creative Europe MEDIA development funding options are available?"
        # e.g., "Tell me about development support"
        development_patterns = [
            "development funding",
            "development support",
            "development options",
            "media development",
            "development grant",
            "slate funding",
            "slate development",
            "single project development",
            "co-development",
            "codevelopment",
            "script development",
            "screenplay funding",
            "content development",
            "project development",
        ]

        # Check for development + MEDIA/film context
        has_development_in_query = any(p in query_lower for p in development_patterns)
        has_media_in_query = any(
            p in query_lower for p in ["media", "creative europe", "film", "audiovisual"]
        )

        if has_development_in_query and (has_media_in_query or has_ce_context or has_film_context):
            guidance = self._generate_media_development_guidance()
            return {
                "thought": "User is asking about Creative Europe MEDIA development funding. Providing guidance on slate, single project, and co-development options.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "media_development",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Distribution support ===
        # e.g., "What about Creative Europe MEDIA distribution support?"
        # e.g., "Distribution funding for films"
        distribution_patterns = [
            "distribution support",
            "distribution funding",
            "distribution grant",
            "media distribution",
            "film distribution",
            "theatrical distribution",
            "cinema release",
            "sales agent",
            "film sales",
            "international distribution",
            "european distribution",
            "selective scheme",
            "automatic scheme",
            "distribution scheme",
        ]

        # Check for distribution + MEDIA/film context
        has_distribution_in_query = any(p in query_lower for p in distribution_patterns)

        # "what about distribution" follow-up pattern
        is_distribution_followup = (
            ("what about" in query_lower or "how about" in query_lower or "and" in query_lower)
            and "distribution" in query_lower
            and (has_ce_context or has_media_context)
        )

        if (
            has_distribution_in_query and (has_media_in_query or has_ce_context or has_film_context)
        ) or is_distribution_followup:
            guidance = self._generate_media_distribution_guidance()
            return {
                "thought": "User is asking about Creative Europe MEDIA distribution support. Providing guidance on selective and automatic schemes.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "media_distribution",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: Multi-project participation ===
        # e.g., "How many Creative Europe MEDIA projects can our organization participate in?"
        # e.g., "Can we apply to multiple MEDIA actions?"
        multi_project_patterns = [
            "how many projects",
            "how many media projects",
            "multiple projects",
            "multiple actions",
            "participate in multiple",
            "apply to multiple",
            "apply to both",
            "several projects",
            "various actions",
            "more than one",
            "limit on projects",
            "restriction on projects",
            "number of projects",
            "participation limit",
            "can we apply to more",
        ]

        # Check for multi-project + MEDIA/film context
        has_multi_project_in_query = any(p in query_lower for p in multi_project_patterns)

        if has_multi_project_in_query and (
            has_media_in_query or has_ce_context or has_film_context or has_media_context
        ):
            guidance = self._generate_media_multi_project_guidance()
            return {
                "thought": "User is asking about participating in multiple Creative Europe MEDIA projects. Providing guidance on multi-action strategy.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "media_multi_project",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: Film company asking about funding options ===
        # e.g., "We're a film production company - what Creative Europe funding is available?"
        film_company_patterns = [
            "film production company",
            "production company",
            "audiovisual company",
            "film producer",
            "cinema production",
            "film studio",
            "audiovisual producer",
            "independent producer",
            "film funding",
            "audiovisual funding",
        ]

        # Check for Creative Europe + film company pattern
        has_film_company_in_query = any(p in query_lower for p in film_company_patterns)
        has_ce_funding_query = any(
            p in query_lower
            for p in ["creative europe", "what funding", "funding available", "funding options"]
        )

        if has_film_company_in_query and has_ce_funding_query:
            guidance = self._generate_ce_film_company_overview_guidance()
            return {
                "thought": "Film production company asking about Creative Europe funding. Providing comprehensive overview of relevant actions.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "ce_film_company_overview",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_creative_europe_eligibility_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect Creative Europe eligibility queries.

        These are questions about:
        - Whether an organization can apply for Creative Europe
        - Eligibility for cultural organizations (theaters, museums, arts organizations)
        - Creative Europe funding options for cultural/creative sector entities
        - Country eligibility for Creative Europe

        Examples:
        - "Can a small theater company from Italy apply for Creative Europe funding?"
        - "Is a museum eligible for Creative Europe?"
        - "Can we apply for Creative Europe as a cultural organization?"
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Must explicitly mention Creative Europe
        creative_europe_indicators = [
            "creative europe",
            "creative-europe",
            "creativeeurope",
        ]

        has_creative_europe = any(ind in query_lower for ind in creative_europe_indicators)

        # If Creative Europe not mentioned, check for cultural organization types
        # that strongly suggest Creative Europe (not Horizon Europe or Erasmus+)
        cultural_org_types = [
            "theater company",
            "theatre company",
            "theater",
            "theatre",
            "opera",
            "ballet",
            "orchestra",
            "symphony",
            "museum",
            "gallery",
            "art gallery",
            "cultural organization",
            "cultural organisation",
            "cultural center",
            "cultural centre",
            "arts organization",
            "arts organisation",
            "performing arts",
            "dance company",
            "circus",
            "street arts",
            "visual arts",
            "literary organization",
            "publisher",
            "publishing house",
            "film company",
            "film production",
            "audiovisual company",
            "audiovisual production",
            "media company",
            "broadcaster",
            "cinema",
            "festival organizer",
            "festival organiser",
            "cultural heritage",
            "heritage organization",
            "heritage organisation",
        ]

        # Eligibility patterns
        eligibility_patterns = [
            "can apply",
            "eligible",
            "eligibility",
            "can we apply",
            "am i eligible",
            "are we eligible",
            "is eligible",
            "qualify for",
            "apply for funding",
            "apply for creative",
            "funding options",
            "funding available",
            "can participate",
            "participate in creative",
        ]

        # Check if it's a cultural organization asking about eligibility
        has_cultural_org = any(org in query_lower for org in cultural_org_types)
        has_eligibility = any(p in query_lower for p in eligibility_patterns)

        # Extract country if mentioned
        eu_countries = [
            "austria",
            "belgian",
            "belgium",
            "bulgaria",
            "croatian",
            "croatia",
            "cyprus",
            "czech",
            "denmark",
            "danish",
            "estonia",
            "estonian",
            "finland",
            "finnish",
            "france",
            "french",
            "germany",
            "german",
            "greece",
            "greek",
            "hungary",
            "hungarian",
            "ireland",
            "irish",
            "italy",
            "italian",
            "latvia",
            "latvian",
            "lithuania",
            "lithuanian",
            "luxembourg",
            "malta",
            "maltese",
            "netherlands",
            "dutch",
            "poland",
            "polish",
            "portugal",
            "portuguese",
            "romania",
            "romanian",
            "slovakia",
            "slovak",
            "slovenia",
            "slovenian",
            "spain",
            "spanish",
            "sweden",
            "swedish",
        ]

        country = None
        for c in eu_countries:
            if c in query_lower:
                # Normalize to country name
                country_map = {
                    "belgian": "Belgium",
                    "belgium": "Belgium",
                    "danish": "Denmark",
                    "denmark": "Denmark",
                    "estonian": "Estonia",
                    "estonia": "Estonia",
                    "finnish": "Finland",
                    "finland": "Finland",
                    "french": "France",
                    "france": "France",
                    "german": "Germany",
                    "germany": "Germany",
                    "greek": "Greece",
                    "greece": "Greece",
                    "hungarian": "Hungary",
                    "hungary": "Hungary",
                    "irish": "Ireland",
                    "ireland": "Ireland",
                    "italian": "Italy",
                    "italy": "Italy",
                    "latvian": "Latvia",
                    "latvia": "Latvia",
                    "lithuanian": "Lithuania",
                    "lithuania": "Lithuania",
                    "maltese": "Malta",
                    "malta": "Malta",
                    "dutch": "Netherlands",
                    "netherlands": "Netherlands",
                    "polish": "Poland",
                    "poland": "Poland",
                    "portuguese": "Portugal",
                    "portugal": "Portugal",
                    "romanian": "Romania",
                    "romania": "Romania",
                    "slovak": "Slovakia",
                    "slovakia": "Slovakia",
                    "slovenian": "Slovenia",
                    "slovenia": "Slovenia",
                    "spanish": "Spain",
                    "spain": "Spain",
                    "swedish": "Sweden",
                    "sweden": "Sweden",
                    "austrian": "Austria",
                    "austria": "Austria",
                    "bulgarian": "Bulgaria",
                    "bulgaria": "Bulgaria",
                    "croatian": "Croatia",
                    "croatia": "Croatia",
                    "cyprus": "Cyprus",
                    "czech": "Czech Republic",
                    "luxembourg": "Luxembourg",
                }
                country = country_map.get(c, c.title())
                break

        # Detect organization type from query
        org_type = "CULTURAL_ORG"  # Default
        org_type_map = {
            "theater": "CULTURAL_ORG",
            "theatre": "CULTURAL_ORG",
            "opera": "CULTURAL_ORG",
            "ballet": "CULTURAL_ORG",
            "orchestra": "CULTURAL_ORG",
            "museum": "CULTURAL_ORG",
            "gallery": "CULTURAL_ORG",
            "cultural": "CULTURAL_ORG",
            "performing arts": "CULTURAL_ORG",
            "dance": "CULTURAL_ORG",
            "circus": "CULTURAL_ORG",
            "visual arts": "CULTURAL_ORG",
            "publisher": "CULTURAL_ORG",
            "literary": "CULTURAL_ORG",
            "film": "PRODUCTION",
            "production": "PRODUCTION",
            "audiovisual": "AUDIOVISUAL",
            "media company": "AUDIOVISUAL",
            "broadcaster": "BROADCASTER",
            "cinema": "CINEMA",
            "festival": "FESTIVAL",
            "heritage": "CULTURAL_ORG",
            "ngo": "NGO",
            "association": "NGO",
        }

        for key, value in org_type_map.items():
            if key in query_lower:
                org_type = value
                break

        # Route to check_creative_europe_eligibility tool
        # Pattern 1: Creative Europe explicitly mentioned + eligibility question
        if has_creative_europe and has_eligibility:
            params = {
                "org_type": org_type,
                "country": country or "Italy",  # Default to Italy if not specified
            }
            # Add strand for CULTURE organizations
            if org_type == "CULTURAL_ORG":
                params["strand"] = "CULTURE"

            return {
                "thought": f"User is asking about Creative Europe eligibility for a {org_type} from {country or 'an EU country'}. Calling check_creative_europe_eligibility tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_creative_europe_eligibility",
                        "parameters": params,
                        "reasoning": f"Checking Creative Europe CULTURE strand eligibility for {org_type} from {country or 'Italy'}",
                    }
                ],
                "confidence": 0.95,
                "needs_more_info": False,
            }

        # Pattern 2: Cultural organization type + eligibility (without explicit Creative Europe mention)
        # Only if query clearly seems about funding eligibility for cultural sector
        if (
            has_cultural_org
            and has_eligibility
            and "horizon" not in query_lower
            and "erasmus" not in query_lower
        ):
            # Check if context has Creative Europe indication
            ce_in_context = any(ind in context_lower for ind in creative_europe_indicators)

            # Only route if Creative Europe is in context OR query seems cultural-sector focused
            cultural_focus_indicators = [
                "cultural",
                "culture",
                "arts",
                "artistic",
                "creative sector",
                "cultural sector",
                "creative industries",
            ]
            has_cultural_focus = (
                any(ind in query_lower for ind in cultural_focus_indicators) or ce_in_context
            )

            if has_cultural_focus:
                params = {
                    "org_type": org_type,
                    "country": country or "Italy",
                    "strand": "CULTURE",
                }
                return {
                    "thought": f"User is asking about eligibility for a cultural organization ({org_type}) from {country or 'an EU country'}. This appears to be a Creative Europe question. Calling check_creative_europe_eligibility tool.",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": "check_creative_europe_eligibility",
                            "parameters": params,
                            "reasoning": f"Checking Creative Europe CULTURE strand eligibility for cultural organization from {country or 'Italy'}",
                        }
                    ],
                    "confidence": 0.90,
                    "needs_more_info": False,
                }

        # Pattern 3: Creative Europe mentioned + funding/options question (not strict eligibility)
        funding_patterns = [
            "funding options",
            "funding available",
            "what funding",
            "which funding",
            "apply for funding",
            "get funding",
        ]
        if has_creative_europe and any(p in query_lower for p in funding_patterns):
            params = {
                "org_type": org_type,
                "country": country or "Italy",
            }
            return {
                "thought": f"User is asking about Creative Europe funding options for a {org_type} from {country or 'an EU country'}. Calling check_creative_europe_eligibility tool to show available actions.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_creative_europe_eligibility",
                        "parameters": params,
                        "reasoning": f"Finding all Creative Europe funding options available to {org_type} from {country or 'Italy'}",
                    }
                ],
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    # ========================================================================
    # EU4HEALTH ELIGIBILITY DETECTION
    # ========================================================================

    def _detect_eu4health_eligibility_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect EU4Health eligibility queries.

        These are questions about:
        - EU4Health eligibility for organizations (hospitals, research, NGOs, etc.)
        - Action types (Action Grants, Joint Actions, Operating Grants)
        - Consortium/partnership requirements
        - EU4Health funding options for health entities

        Examples:
        - "What EU4Health funding options are available for a hospital consortium?"
        - "Can a public health authority participate in Joint Actions?"
        - "Is a patient organization eligible for EU4Health operating grants?"
        - "EU4Health eligibility for a healthcare provider from Germany"
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # EU4Health indicators
        eu4health_indicators = [
            "eu4health",
            "eu 4 health",
            "eu-4-health",
            "eu4h",
            "eu 4health",
        ]
        has_eu4health = any(ind in query_lower for ind in eu4health_indicators)

        # Skip if query explicitly mentions another programme
        other_programmes = [
            "erasmus",
            "creative europe",
            "horizon europe",
            "horizon 2020",
            "digital europe",
            "life programme",
        ]
        if any(prog in query_lower for prog in other_programmes):
            return None

        # Eligibility indicators
        eligibility_indicators = [
            "eligible",
            "eligibility",
            "can we",
            "can a",
            "can i",
            "can our",
            "can my",
            "participate",
            "apply",
            "funding options",
            "funding available",
            "what options",
            "what grants",
            "what actions",
        ]
        has_eligibility = any(ind in query_lower for ind in eligibility_indicators)

        # Health organization type indicators
        health_org_indicators = {
            "hospital": "HEALTHCARE_PROVIDER",
            "healthcare provider": "HEALTHCARE_PROVIDER",
            "health provider": "HEALTHCARE_PROVIDER",
            "clinic": "HEALTHCARE_PROVIDER",
            "medical center": "HEALTHCARE_PROVIDER",
            "medical centre": "HEALTHCARE_PROVIDER",
            "research": "RESEARCH",
            "research institution": "RESEARCH",
            "research organization": "RESEARCH",
            "research centre": "RESEARCH",
            "research center": "RESEARCH",
            "university": "UNIVERSITY",
            "higher education": "UNIVERSITY",
            "academic": "UNIVERSITY",
            "public authority": "PUBLIC_AUTHORITY",
            "public health": "PUBLIC_AUTHORITY",
            "government": "PUBLIC_AUTHORITY",
            "ministry": "PUBLIC_AUTHORITY",
            "ngo": "NGO",
            "non-governmental": "NGO",
            "health ngo": "NGO",
            "patient organization": "PATIENT_ORG",
            "patient organisation": "PATIENT_ORG",
            "patient group": "PATIENT_ORG",
            "patient association": "PATIENT_ORG",
            "professional organization": "PROFESSIONAL_ORG",
            "professional organisation": "PROFESSIONAL_ORG",
            "professional association": "PROFESSIONAL_ORG",
            "healthcare professional": "PROFESSIONAL_ORG",
            "enterprise": "ENTERPRISE",
            "company": "ENTERPRISE",
            "private": "ENTERPRISE",
            "sme": "SME",
            "small business": "SME",
            "startup": "SME",
            "international organization": "INTERNATIONAL_ORG",
            "international organisation": "INTERNATIONAL_ORG",
            "who": "INTERNATIONAL_ORG",
        }

        # Detect organization type from query
        org_type = "HEALTHCARE_PROVIDER"  # Default for health context
        for pattern, org_value in health_org_indicators.items():
            if pattern in query_lower:
                org_type = org_value
                break

        # Detect country from query
        country = None
        countries = [
            "Austria",
            "Belgium",
            "Bulgaria",
            "Croatia",
            "Cyprus",
            "Czech Republic",
            "Denmark",
            "Estonia",
            "Finland",
            "France",
            "Germany",
            "Greece",
            "Hungary",
            "Ireland",
            "Italy",
            "Latvia",
            "Lithuania",
            "Luxembourg",
            "Malta",
            "Netherlands",
            "Poland",
            "Portugal",
            "Romania",
            "Slovakia",
            "Slovenia",
            "Spain",
            "Sweden",
            "Iceland",
            "Norway",
            "Ukraine",
            "Moldova",
            "Montenegro",
            "Bosnia",
            "Serbia",
        ]
        for c in countries:
            if c.lower() in query_lower:
                country = c
                break

        # Action type indicators
        action_indicators = {
            "joint action": "JA",
            "joint actions": "JA",
            "action grant": "AG",
            "action grants": "AG",
            "project grant": "PJ",
            "operating grant": "OG",
            "operating grants": "OG",
            "procurement": "PROC",
            "direct grant": "DG",
        }
        action_type = None
        for pattern, action_value in action_indicators.items():
            if pattern in query_lower:
                action_type = action_value
                break

        # Strand indicators
        strand_indicators = {
            "crisis": "CRISIS",
            "emergency": "CRISIS",
            "preparedness": "CRISIS",
            "hera": "CRISIS",
            "cancer": "PREVENTION",
            "prevention": "PREVENTION",
            "ncd": "PREVENTION",
            "screening": "PREVENTION",
            "health system": "HEALTH_SYSTEMS",
            "workforce": "HEALTH_SYSTEMS",
            "hta": "HEALTH_SYSTEMS",
            "medicines": "HEALTH_SYSTEMS",
            "digital health": "DIGITAL",
            "ehds": "DIGITAL",
            "ehealth": "DIGITAL",
        }
        strand = None
        for pattern, strand_value in strand_indicators.items():
            if pattern in query_lower:
                strand = strand_value
                break

        # Route to check_eu4health_eligibility tool if EU4Health + eligibility
        if has_eu4health and has_eligibility:
            params = {
                "org_type": org_type,
                "country": country or "Germany",  # Default if not specified
            }
            if action_type:
                params["action_type"] = action_type
            if strand:
                params["strand"] = strand

            return {
                "thought": f"User is asking about EU4Health eligibility for a {org_type.replace('_', ' ')} from {country or 'an EU country'}. Calling check_eu4health_eligibility tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_eu4health_eligibility",
                        "parameters": params,
                        "reasoning": f"Checking EU4Health eligibility for {org_type} from {country or 'Germany'}",
                    }
                ],
                "confidence": 0.95,
                "needs_more_info": False,
            }

        # Pattern: Health consortium/hospital + eligibility + EU funding context (without explicit EU4Health)
        # Only if clearly health-focused and asking about EU funding
        health_context_indicators = [
            "hospital consortium",
            "health consortium",
            "healthcare consortium",
            "hospital network",
            "health network",
            "public health body",
            "health entity",
            "health entities",
        ]
        has_health_consortium = any(ind in query_lower for ind in health_context_indicators)

        eu_funding_context = any(
            ind in query_lower
            for ind in ["eu funding", "european funding", "eu grants", "european grants"]
        ) or any(ind in context_lower for ind in eu4health_indicators)

        if has_health_consortium and has_eligibility and eu_funding_context:
            params = {
                "org_type": org_type,
                "country": country or "Germany",
            }

            return {
                "thought": "User is asking about EU funding eligibility for a health consortium. This appears to be an EU4Health question. Calling check_eu4health_eligibility tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_eu4health_eligibility",
                        "parameters": params,
                        "reasoning": f"Checking EU4Health funding options for healthcare consortium from {country or 'Germany'}",
                    }
                ],
                "confidence": 0.85,
                "needs_more_info": False,
            }

        return None

    # ========================================================================
    # DIGITAL EUROPE ELIGIBILITY DETECTION
    # ========================================================================

    def _detect_digital_europe_eligibility_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect Digital Europe eligibility queries.

        These are questions about Digital Europe programme eligibility, covering:
        - HPC (High Performance Computing)
        - AI (Artificial Intelligence)
        - Cybersecurity
        - Skills (Advanced Digital Skills)
        - Deployment (EDIHs)
        - Semiconductors (Chips Act)

        Examples:
        - "Can a cybersecurity startup apply to Digital Europe?"
        - "Is an SME eligible for Digital Europe AI funding?"
        - "What Digital Europe opportunities are available for an EDIH?"
        - "Can our research institution apply for Digital Europe HPC calls?"
        - "Is Switzerland eligible for Digital Europe?"
        """
        query_lower = query.lower()
        # Note: context not currently used but kept for future enhancement
        _ = context  # Mark as intentionally unused

        # Digital Europe indicators
        digital_europe_indicators = [
            "digital europe",
            "digital-europe",
            "digitaleurope",
            "dep programme",  # Digital Europe Programme
            "digital europe programme",
        ]
        has_digital_europe = any(ind in query_lower for ind in digital_europe_indicators)

        # Skip if query explicitly mentions another programme
        other_programmes = [
            "erasmus",
            "creative europe",
            "horizon europe",
            "horizon 2020",
            "eu4health",
            "life programme",
        ]
        if any(prog in query_lower for prog in other_programmes):
            return None

        # Eligibility indicators
        eligibility_indicators = [
            "eligible",
            "eligibility",
            "can we apply",
            "can i apply",
            "can a",
            "can an",
            "can our",
            "can my",
            "participate",
            "apply to",
            "apply for",
            "funding options",
            "funding opportunities",
            "is a ",
            "am i eligible",
            "are we eligible",
        ]
        has_eligibility = any(ind in query_lower for ind in eligibility_indicators)

        # Digital Europe specific topic indicators (can help detect even without explicit programme mention)
        dep_topic_indicators = [
            "edih",
            "digital innovation hub",
            "hpc ",
            "high performance computing",
            "supercomputing",
            "eurohpc",
            "ai factories",
            "digital skills",
            "advanced skills",
            "cybersecurity",
            "cyber security",
            "chips act",
            "semiconductors",
            "eccc",  # European Cybersecurity Competence Centre
        ]
        has_dep_topic = any(ind in query_lower for ind in dep_topic_indicators)

        # Also check for generic digital + eligibility context
        generic_digital_context = (
            ("digital" in query_lower or "digitalization" in query_lower)
            and has_eligibility
            and "europe" in query_lower
        )

        # Organization type detection
        org_type_patterns = {
            "SME": ["sme", "small enterprise", "small business", "medium enterprise"],
            "STARTUP": ["startup", "start-up", "scaleup", "scale-up"],
            "LARGE_ENTERPRISE": ["large enterprise", "large company", "corporation"],
            "RESEARCH": [
                "research institution",
                "research center",
                "research centre",
                "research org",
            ],
            "UNIVERSITY": ["university", "higher education", "academia", "academic"],
            "PUBLIC_AUTHORITY": [
                "public authority",
                "government",
                "public body",
                "public sector",
                "municipality",
            ],
            "EDIH": ["edih", "digital innovation hub", "innovation hub"],
            "HPC_CENTER": ["hpc center", "hpc centre", "supercomputing center"],
            "NGO": ["ngo", "non-profit", "nonprofit", "non-governmental"],
            "COMPETENCE_CENTER": ["competence center", "competence centre"],
            "HEALTHCARE": ["hospital", "healthcare", "health provider"],
            "EDUCATION_PROVIDER": ["training provider", "education provider", "training center"],
        }
        org_type = "SME"  # Default
        for ot, patterns in org_type_patterns.items():
            if any(p in query_lower for p in patterns):
                org_type = ot
                break

        # Country detection
        countries = [
            "Germany",
            "France",
            "Italy",
            "Spain",
            "Netherlands",
            "Belgium",
            "Poland",
            "Austria",
            "Sweden",
            "Denmark",
            "Finland",
            "Ireland",
            "Portugal",
            "Greece",
            "Czech Republic",
            "Romania",
            "Hungary",
            "Bulgaria",
            "Slovakia",
            "Slovenia",
            "Croatia",
            "Lithuania",
            "Latvia",
            "Estonia",
            "Luxembourg",
            "Malta",
            "Cyprus",
            "Norway",
            "Iceland",
            "Liechtenstein",
            "Switzerland",
            "Ukraine",
            "Moldova",
            "Montenegro",
            "Serbia",
            "Albania",
            "North Macedonia",
            "Kosovo",
            "Türkiye",
            "Turkey",
            "Bosnia",
        ]
        country = None
        for c in countries:
            if c.lower() in query_lower:
                country = c if c != "Turkey" else "Türkiye"
                break

        # Objective detection
        objective_patterns = {
            "HPC": ["hpc", "high performance computing", "supercomputing", "eurohpc"],
            "AI": [
                "artificial intelligence",
                " ai ",
                "ai funding",
                "ai project",
                "machine learning",
                "ai factories",
            ],
            "CYBERSECURITY": ["cybersecurity", "cyber security", "cyber-security", "eccc", "soc "],
            "SKILLS": ["digital skills", "advanced skills", "training", "skills programme"],
            "DEPLOYMENT": ["deployment", "edih", "digital innovation hub", "best use"],
            "SEMICONDUCTORS": ["semiconductor", "chips act", "chip design", "pilot line"],
        }
        objective = None
        for obj, patterns in objective_patterns.items():
            if any(p in query_lower for p in patterns):
                objective = obj
                break

        # Route to check_digital_europe_eligibility tool if Digital Europe + eligibility
        if has_digital_europe and has_eligibility:
            params = {
                "org_type": org_type,
                "country": country or "Germany",  # Default if not specified
            }
            if objective:
                params["objective"] = objective

            return {
                "thought": f"User is asking about Digital Europe eligibility for a {org_type.replace('_', ' ')} from {country or 'an EU country'}. Calling check_digital_europe_eligibility tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_digital_europe_eligibility",
                        "parameters": params,
                        "reasoning": f"Checking Digital Europe eligibility for {org_type} from {country or 'Germany'}",
                    }
                ],
                "confidence": 0.95,
                "needs_more_info": False,
            }

        # Pattern: Digital Europe topic indicators + eligibility (even without explicit Digital Europe mention)
        if (
            has_dep_topic
            and has_eligibility
            and not any(prog in query_lower for prog in other_programmes)
        ):
            params = {
                "org_type": org_type,
                "country": country or "Germany",
            }
            if objective:
                params["objective"] = objective

            return {
                "thought": f"User is asking about eligibility for Digital Europe-related topics ({objective or 'digital'}). Routing to Digital Europe eligibility check.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_digital_europe_eligibility",
                        "parameters": params,
                        "reasoning": f"Checking Digital Europe eligibility for {org_type} interested in {objective or 'digital technologies'}",
                    }
                ],
                "confidence": 0.85,
                "needs_more_info": False,
            }

        # Pattern: Generic digital + Europe + eligibility context
        if generic_digital_context and not any(prog in query_lower for prog in other_programmes):
            params = {
                "org_type": org_type,
                "country": country or "Germany",
            }

            return {
                "thought": "User is asking about digital-related EU funding eligibility. This appears to be a Digital Europe question. Calling check_digital_europe_eligibility tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_digital_europe_eligibility",
                        "parameters": params,
                        "reasoning": f"Checking Digital Europe funding options for {org_type} from {country or 'Germany'}",
                    }
                ],
                "confidence": 0.80,
                "needs_more_info": False,
            }

        return None

    # ========================================================================
    # LIFE PROGRAMME ELIGIBILITY DETECTION
    # ========================================================================

    def _detect_life_eligibility_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect LIFE Programme eligibility queries.

        These are questions about LIFE Programme eligibility, covering:
        - NAT: Nature and Biodiversity
        - ENV: Circular Economy and Quality of Life
        - CCA: Climate Change Mitigation and Adaptation
        - CET: Clean Energy Transition

        Examples:
        - "What LIFE programme options exist for biodiversity conservation NGO?"
        - "Can an environmental NGO apply for LIFE Nature funding?"
        - "Is my organization eligible for LIFE climate action projects?"
        - "What LIFE sub-programmes are available for a local authority?"
        - "Can a research institution apply for LIFE clean energy transition?"
        """
        query_lower = query.lower()
        # Note: context not currently used but kept for future enhancement
        _ = context  # Mark as intentionally unused

        # LIFE Programme indicators
        life_indicators = [
            "life programme",
            "life program",
            "life-programme",
            "life funding",
            "life grant",
            "life sub-programme",
            "life subprogramme",
        ]
        has_life = any(ind in query_lower for ind in life_indicators)

        # Skip if query explicitly mentions another programme
        other_programmes = [
            "erasmus",
            "creative europe",
            "horizon europe",
            "horizon 2020",
            "eu4health",
            "digital europe",
        ]
        if any(prog in query_lower for prog in other_programmes):
            return None

        # Eligibility indicators
        eligibility_indicators = [
            "eligible",
            "eligibility",
            "can we apply",
            "can i apply",
            "can a",
            "can an",
            "can our",
            "can my",
            "participate",
            "apply to",
            "apply for",
            "funding options",
            "funding opportunities",
            "options exist",
            "options available",
            "what options",
            "is a ",
            "am i eligible",
            "are we eligible",
        ]
        has_eligibility = any(ind in query_lower for ind in eligibility_indicators)

        # LIFE-specific topic indicators (can help detect even without explicit programme mention)
        life_topic_indicators = [
            "biodiversity",
            "nature conservation",
            "natura 2000",
            "wildlife protection",
            "habitat restoration",
            "species protection",
            "invasive species",
            "circular economy",
            "waste management",
            "water management",
            "air quality",
            "soil protection",
            "climate mitigation",
            "climate adaptation",
            "climate action",
            "clean energy transition",
            "energy transition",
            "environmental protection",
            "environmental project",
            "nature project",
        ]
        has_life_topic = any(ind in query_lower for ind in life_topic_indicators)

        # Organization type detection
        org_type_patterns = {
            "NGO": ["ngo", "non-governmental", "nonprofit", "non-profit"],
            "ENVIRONMENTAL_NGO": [
                "environmental ngo",
                "environmental organization",
                "environmental organisation",
                "conservation ngo",
                "nature ngo",
                "wildlife ngo",
            ],
            "PUBLIC_AUTHORITY": [
                "public authority",
                "government",
                "ministry",
                "public body",
            ],
            "LOCAL_AUTHORITY": [
                "local authority",
                "municipality",
                "city",
                "region",
                "regional authority",
                "local government",
            ],
            "RESEARCH": [
                "research institution",
                "research center",
                "research centre",
                "research org",
            ],
            "UNIVERSITY": ["university", "higher education", "academia", "academic"],
            "SME": ["sme", "small enterprise", "small business", "medium enterprise"],
            "LARGE_ENTERPRISE": ["large enterprise", "large company", "corporation"],
            "PARK_AUTHORITY": [
                "nature park",
                "national park",
                "protected area",
                "nature reserve",
                "park authority",
            ],
            "ASSOCIATION": ["association", "network", "federation"],
            "FOUNDATION": ["foundation"],
            "INTERNATIONAL_ORG": [
                "international organization",
                "international organisation",
            ],
        }
        org_type = "NGO"  # Default for LIFE (most common applicant type)
        for ot, patterns in org_type_patterns.items():
            if any(p in query_lower for p in patterns):
                org_type = ot
                break

        # Country detection
        countries = [
            "Germany",
            "France",
            "Italy",
            "Spain",
            "Netherlands",
            "Belgium",
            "Poland",
            "Austria",
            "Sweden",
            "Denmark",
            "Finland",
            "Ireland",
            "Portugal",
            "Greece",
            "Czech Republic",
            "Romania",
            "Hungary",
            "Bulgaria",
            "Slovakia",
            "Slovenia",
            "Croatia",
            "Lithuania",
            "Latvia",
            "Estonia",
            "Luxembourg",
            "Malta",
            "Cyprus",
            "Norway",
            "Iceland",
            "Liechtenstein",
            "Ukraine",
            "Moldova",
            "Montenegro",
            "Serbia",
            "Albania",
            "North Macedonia",
            "Kosovo",
            "Türkiye",
            "Turkey",
            "Bosnia",
        ]
        country = None
        for c in countries:
            if c.lower() in query_lower:
                country = c if c != "Turkey" else "Türkiye"
                break

        # Sub-programme detection
        subprog_patterns = {
            "NAT": [
                "nature",
                "biodiversity",
                "natura 2000",
                "species",
                "habitat",
                "wildlife",
                "conservation",
            ],
            "ENV": [
                "circular economy",
                "waste",
                "water",
                "air quality",
                "soil",
                "chemicals",
                "resource efficiency",
                "pollution",
            ],
            "CCA": [
                "climate change",
                "climate mitigation",
                "climate adaptation",
                "greenhouse gas",
                "ghg",
                "climate action",
                "urban adaptation",
            ],
            "CET": [
                "clean energy",
                "energy transition",
                "renewable energy",
                "energy efficiency",
                "building renovation",
                "energy poverty",
            ],
        }
        subprogramme = None
        for sp, patterns in subprog_patterns.items():
            if any(p in query_lower for p in patterns):
                subprogramme = sp
                break

        # Project type detection
        project_type_patterns = {
            "SAP": [
                "standard action",
                "demonstration project",
                "pilot project",
                "best practice",
            ],
            "SIP": ["strategic integrated", "large-scale implementation", "sip "],
            "SNAP": ["strategic nature", "snap "],
            "TA": ["technical assistance"],
            "OG": ["operating grant", "operating grants"],
        }
        project_type = None
        for pt, patterns in project_type_patterns.items():
            if any(p in query_lower for p in patterns):
                project_type = pt
                break

        # Check if query is asking for broad options (not a specific sub-programme)
        broad_options_indicators = [
            "what options",
            "options exist",
            "options available",
            "what are the options",
            "which options",
            "funding options",
            "all options",
            "what sub-programmes",
            "what subprogrammes",
            "which sub-programmes",
            "all sub-programmes",
        ]
        wants_broad_options = any(ind in query_lower for ind in broad_options_indicators)

        # Route to check_life_eligibility tool if LIFE + eligibility
        if has_life and has_eligibility:
            params = {
                "org_type": org_type,
                "country": country or "Germany",  # Default if not specified
            }
            # Only include subprogramme if NOT asking for broad options
            if subprogramme and not wants_broad_options:
                params["subprogramme"] = subprogramme
            if project_type:
                params["project_type"] = project_type

            return {
                "thought": f"User is asking about LIFE Programme eligibility for a {org_type.replace('_', ' ')} from {country or 'an EU country'}. Calling check_life_eligibility tool.",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "tool": "check_life_eligibility",
                        "parameters": params,
                        "reasoning": f"Checking LIFE Programme eligibility for {org_type} from {country or 'Germany'}",
                    }
                ],
                "confidence": 0.95,
                "needs_more_info": False,
            }

        # Pattern: LIFE topic indicators + eligibility (even without explicit LIFE mention)
        # But only if clearly environmental/climate focused
        if (
            has_life_topic
            and has_eligibility
            and not any(prog in query_lower for prog in other_programmes)
        ):
            # Check for environmental/climate context words to avoid false positives
            env_context = any(
                w in query_lower
                for w in [
                    "environment",
                    "climate",
                    "nature",
                    "biodiversity",
                    "conservation",
                    "ecological",
                    "green",
                ]
            )
            if env_context:
                params = {
                    "org_type": org_type,
                    "country": country or "Germany",
                }
                # Only include subprogramme if NOT asking for broad options
                if subprogramme and not wants_broad_options:
                    params["subprogramme"] = subprogramme
                if project_type:
                    params["project_type"] = project_type

                return {
                    "thought": f"User is asking about eligibility for LIFE-related topics ({subprogramme or 'environment/climate'}). Routing to LIFE Programme eligibility check.",
                    "action": "call_tools",
                    "tool_calls": [
                        {
                            "tool": "check_life_eligibility",
                            "parameters": params,
                            "reasoning": f"Checking LIFE Programme eligibility for {org_type} interested in {subprogramme or 'environmental/climate projects'}",
                        }
                    ],
                    "confidence": 0.85,
                    "needs_more_info": False,
                }

        return None

    # ========================================================================
    # LIFE PROGRAMME BUDGET DETECTION
    # ========================================================================

    def _detect_life_budget_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect LIFE Programme budget queries.

        These are questions about LIFE Programme budget ranges, funding rates,
        and co-financing for the different sub-programmes:
        - NAT: Nature and Biodiversity (75% co-financing)
        - ENV: Circular Economy and Quality of Life (60% co-financing)
        - CCA: Climate Change Mitigation and Adaptation (60% co-financing)
        - CET: Clean Energy Transition (up to 95% co-financing)

        Examples:
        - "What budget range for a LIFE climate adaptation project?"
        - "How much funding for LIFE nature conservation?"
        - "What is the typical LIFE project budget?"
        - "LIFE programme co-financing rates"
        - "What budget should I plan for LIFE environmental project?"
        """
        query_lower = query.lower()
        # Note: context not currently used but kept for future enhancement
        _ = context  # Mark as intentionally unused

        # LIFE Programme indicators
        life_indicators = [
            "life programme",
            "life program",
            "life project",
            "life funding",
            "life grant",
        ]
        has_life = any(ind in query_lower for ind in life_indicators)

        # Budget indicators
        budget_indicators = [
            "budget",
            "funding",
            "cost",
            "co-financing",
            "cofinancing",
            "co financing",
            "funding rate",
            "how much",
            "typical amount",
            "expected grant",
            "grant size",
            "project size",
            "financial",
            "money",
            "eur",
            "euro",
            "million",
        ]
        has_budget = any(ind in query_lower for ind in budget_indicators)

        # LIFE-specific topic indicators that suggest LIFE even without explicit mention
        life_topic_indicators = [
            "climate adaptation",
            "climate mitigation",
            "nature conservation",
            "biodiversity",
            "natura 2000",
            "circular economy",
            "clean energy transition",
            "environmental protection",
        ]
        has_life_topic = any(ind in query_lower for ind in life_topic_indicators)

        # Sub-programme detection
        subprogramme = None
        if any(
            ind in query_lower
            for ind in [
                "climate adaptation",
                "climate mitigation",
                "climate change",
                "cca",
                "climate action",
                "ghg",
                "greenhouse",
            ]
        ):
            subprogramme = "CCA"
        elif any(
            ind in query_lower
            for ind in [
                "nature",
                "biodiversity",
                "natura 2000",
                "species",
                "habitat",
                "nat",
            ]
        ):
            subprogramme = "NAT"
        elif any(
            ind in query_lower
            for ind in [
                "circular economy",
                "waste",
                "water",
                "air quality",
                "soil",
                "env",
                "environment",
            ]
        ):
            subprogramme = "ENV"
        elif any(
            ind in query_lower
            for ind in [
                "clean energy",
                "energy transition",
                "renewable",
                "energy efficiency",
                "cet",
            ]
        ):
            subprogramme = "CET"

        # Route to LIFE budget guidance if:
        # 1. LIFE mentioned + budget question
        # 2. LIFE topic + budget question (implies LIFE)
        if (has_life and has_budget) or (has_life_topic and has_budget and not has_life):
            # Only route if clearly a budget question (not eligibility)
            eligibility_indicators = [
                "eligible",
                "eligibility",
                "can apply",
                "can participate",
                "who can",
                "requirements",
            ]
            is_eligibility = any(ind in query_lower for ind in eligibility_indicators)
            if is_eligibility:
                return None  # Let eligibility detection handle this

            return {
                "thought": f"User is asking about LIFE Programme budget ranges{' for ' + subprogramme + ' sub-programme' if subprogramme else ''}. Providing LIFE-specific budget guidance with SAP/SIP typical budgets and co-financing rates.",
                "action": "generate_guidance",
                "response": self._generate_life_budget_guidance(subprogramme),
                "guidance_type": "life_budget",
                "programme": "LIFE",
                "subprogramme": subprogramme,
                "confidence": 0.95,
                "needs_more_info": False,
            }

        return None

    def _detect_digital_europe_vs_horizon_comparison_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect Digital Europe vs Horizon Europe comparison queries.

        These are questions comparing the two programmes, typically for deciding
        which programme to apply to. Key differentiation:
        - Digital Europe: Deployment focus (TRL 7-9), near-market solutions
        - Horizon Europe: Research & innovation (TRL 2-6), novel approaches

        Examples:
        - "Should I apply to Digital Europe or Horizon Europe for an AI project?"
        - "Compare Digital Europe and Horizon Europe for deployment projects"
        - "What's the difference between Digital Europe and Horizon Europe?"
        - "Digital Europe vs Horizon Europe - which is better for my AI startup?"
        - "Which programme should I choose for deploying AI solutions?"
        """
        query_lower = query.lower()
        # Note: context not currently used but kept for future enhancement
        _ = context  # Mark as intentionally unused

        # Must have both programmes mentioned or implied
        has_digital_europe = any(
            ind in query_lower
            for ind in ["digital europe", "digital-europe", "digitaleurope", "dep programme"]
        )
        has_horizon_europe = any(
            ind in query_lower
            for ind in [
                "horizon europe",
                "horizon-europe",
                "horizoneurope",
                "horizon 2020",
                "h2020",
                "he programme",
            ]
        )

        # Comparison indicators
        comparison_indicators = [
            "compare",
            "comparison",
            "vs",
            "versus",
            "difference",
            "different",
            "or ",  # "Digital Europe or Horizon Europe"
            "which",
            "should i",
            "should we",
            "better for",
            "choose",
            "between",
        ]
        has_comparison = any(ind in query_lower for ind in comparison_indicators)

        # Topic indicators that could clarify the comparison context
        topic_context = None
        if " ai " in query_lower or "artificial intelligence" in query_lower:
            topic_context = "AI"
        elif "cybersecurity" in query_lower or "cyber security" in query_lower:
            topic_context = "cybersecurity"
        elif "hpc" in query_lower or "high performance" in query_lower:
            topic_context = "HPC"
        elif "deploy" in query_lower or "deployment" in query_lower:
            topic_context = "deployment"
        elif "research" in query_lower:
            topic_context = "research"
        elif "digital" in query_lower:
            topic_context = "digital transformation"

        # Pattern 1: Both programmes + comparison
        if has_digital_europe and has_horizon_europe and has_comparison:
            return self._generate_digital_europe_horizon_comparison_guidance(query, topic_context)

        # Pattern 2: "Digital Europe or Horizon" style question
        if has_digital_europe and has_horizon_europe:
            return self._generate_digital_europe_horizon_comparison_guidance(query, topic_context)

        # Pattern 3: Implicit comparison - "which programme for AI deployment"
        # Only if explicitly mentions programme choice + deployment context
        if (
            has_comparison
            and ("programme" in query_lower or "program" in query_lower)
            and ("deploy" in query_lower or "market" in query_lower or "scale" in query_lower)
            and (" ai " in query_lower or "digital" in query_lower or "cyber" in query_lower)
        ):
            # This could be a DE vs HE question - return comparison
            return self._generate_digital_europe_horizon_comparison_guidance(query, topic_context)

        return None

    def _detect_eu4health_topics_query(self, query: str, context: str) -> dict[str, Any] | None:
        """Detect EU4Health topic and priority queries.

        These are questions about EU4Health programme priorities, thematic areas,
        cancer plan, disease prevention, and other programme content (NOT eligibility).

        Examples:
        - "What EU4Health priorities focus on cancer?"
        - "What are the EU4Health programme strands?"
        - "Tell me about EU4Health disease prevention activities"
        - "What EU4Health actions support mental health?"
        - "What is Europe's Beating Cancer Plan under EU4Health?"
        """
        query_lower = query.lower()

        # EU4Health indicators
        eu4health_indicators = [
            "eu4health",
            "eu 4 health",
            "eu-4-health",
            "eu4h",
            "eu 4health",
        ]
        has_eu4health = any(ind in query_lower for ind in eu4health_indicators)

        # Skip if query explicitly mentions another programme
        other_programmes = [
            "erasmus",
            "creative europe",
            "horizon europe",
            "horizon 2020",
            "digital europe",
            "life programme",
        ]
        if any(prog in query_lower for prog in other_programmes):
            return None

        # Skip if this is an eligibility question (handled by eligibility detector)
        eligibility_indicators = [
            "eligible",
            "eligibility",
            "can we apply",
            "can a hospital",
            "can we participate",
            "can my organization",
            "can our organization",
        ]
        if any(ind in query_lower for ind in eligibility_indicators):
            return None

        # Topic/priority indicators
        topic_indicators = [
            "priorities",
            "priority",
            "focus on",
            "focuses on",
            "topics",
            "topic",
            "strands",
            "strand",
            "thematic",
            "areas",
            "activities",
            "actions support",
            "what does",
            "what are the",
            "tell me about",
            "explain",
            "objectives",
            "goals",
        ]
        has_topic_question = any(ind in query_lower for ind in topic_indicators)

        # Health topic indicators (specific content areas)
        health_topics = {
            "cancer": "PREVENTION",
            "beating cancer": "PREVENTION",
            "cancer plan": "PREVENTION",
            "prevention": "PREVENTION",
            "ncd": "PREVENTION",
            "screening": "PREVENTION",
            "vaccination": "PREVENTION",
            "health promotion": "PREVENTION",
            "crisis": "CRISIS",
            "emergency": "CRISIS",
            "preparedness": "CRISIS",
            "hera": "CRISIS",
            "medical countermeasures": "CRISIS",
            "amr": "CRISIS",
            "antimicrobial": "CRISIS",
            "health system": "HEALTH_SYSTEMS",
            "workforce": "HEALTH_SYSTEMS",
            "hta": "HEALTH_SYSTEMS",
            "health technology": "HEALTH_SYSTEMS",
            "medicines": "HEALTH_SYSTEMS",
            "pharmaceutical": "HEALTH_SYSTEMS",
            "digital health": "DIGITAL",
            "ehds": "DIGITAL",
            "ehealth": "DIGITAL",
            "health data": "DIGITAL",
            "telemedicine": "DIGITAL",
            "mental health": "PREVENTION",
        }

        # Detect specific strand from health topic mentioned
        strand = None
        topic_keyword = None
        for topic, strand_value in health_topics.items():
            if topic in query_lower:
                strand = strand_value
                topic_keyword = topic
                break

        # Route to search_eu4health_templates if EU4Health + topic/priority question
        if has_eu4health and (has_topic_question or topic_keyword):
            # Build search query
            search_query = query
            if topic_keyword:
                # Enhance query with the topic
                search_query = f"{topic_keyword} {query}"

            params = {
                "query": search_query,
                "top_k": 5,
            }
            if strand:
                params["strand"] = strand

            reasoning = (
                f"Searching EU4Health documents for {topic_keyword or 'programme priorities'}"
            )
            if strand:
                reasoning += f" in {strand} strand"

            # Use call_tools_and_format to bypass LLM response generation
            # and use our structured formatter instead
            return {
                "thought": f"User is asking about EU4Health programme priorities/topics ({topic_keyword or 'general'}). Calling search_eu4health_templates and formatting results directly.",
                "action": "call_tools_and_format",
                "tool_calls": [
                    {
                        "tool": "search_eu4health_templates",
                        "parameters": params,
                        "reasoning": reasoning,
                    }
                ],
                "confidence": 0.95,
                "needs_more_info": False,
            }

        return None

    # ========================================================================
    # CREATIVE EUROPE CALL SEARCH DETECTION
    # ========================================================================

    def _detect_creative_europe_call_search_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect Creative Europe call search queries.

        These are queries explicitly asking to FIND/SEARCH/LIST open or upcoming
        Creative Europe calls. These should trigger a search_funding_calls tool
        call rather than returning static guidance.

        Examples:
        - "Find open Creative Europe MEDIA calls for film distribution"
        - "Show me upcoming Creative Europe calls"
        - "Search for Creative Europe CULTURE calls"
        - "List open CREA calls for audiovisual projects"
        - "What Creative Europe calls are open now?"
        """
        query_lower = query.lower()

        # Check for Creative Europe indicators
        ce_indicators = [
            "creative europe",
            "creative-europe",
            "creativeeurope",
            "crea-media",
            "crea-cult",
            "crea-cross",
            "crea calls",
            "crea programme",
        ]
        has_creative_europe = any(ind in query_lower for ind in ce_indicators)

        # Check for strand-specific indicators
        media_indicators = [
            "media strand",
            "media calls",
            "media programme",
            "audiovisual",
            "film distribution",
            "film production",
            "film development",
            "film festival",
            "cinema network",
            "sales agent",
            "distribution call",
            "development call",
        ]
        has_media_indicator = any(ind in query_lower for ind in media_indicators)

        culture_indicators = [
            "culture strand",
            "culture calls",
            "culture programme",
            "cooperation project",
            "literary translation",
            "european network",
            "european platform",
        ]
        has_culture_indicator = any(ind in query_lower for ind in culture_indicators)

        cross_sectoral_indicators = [
            "cross-sectoral",
            "cross sectoral",
            "innovation lab",
            "news media",
            "media literacy",
        ]
        has_cross_sectoral_indicator = any(ind in query_lower for ind in cross_sectoral_indicators)

        # Check for EXPLICIT call search patterns
        # These patterns indicate the user wants to SEARCH for calls, not get general info
        call_search_patterns = [
            "find calls",
            "find open calls",
            "find upcoming calls",
            "find all calls",
            "find media calls",
            "search for calls",
            "search calls",
            "show me calls",
            "show me all calls",
            "show me the calls",
            "show open calls",
            "show upcoming calls",
            "show all calls",
            "list calls",
            "list open calls",
            "list upcoming calls",
            "list all calls",
            "what calls are open",
            "what calls are available",
            "which calls are open",
            "open calls for",
            "upcoming calls for",
            "available calls for",
            "current calls for",
            "calls closing",
            "calls with deadline",
            "calls for film",
            "calls for audiovisual",
            "calls for distribution",
            "calls for development",
            "distribution calls",
            "development calls",
            "festival calls",
            "training calls",
            "media calls",
            "culture calls",
        ]

        # Check for call search intent
        has_call_search_intent = False
        for pattern in call_search_patterns:
            if pattern in query_lower:
                has_call_search_intent = True
                break

        # Additional check: "open" or "upcoming" combined with Creative Europe context
        status_indicators = ["open", "upcoming", "available", "current", "active"]
        has_status_indicator = any(ind in query_lower for ind in status_indicators)

        # "what ... calls" pattern
        if "what" in query_lower and "calls" in query_lower and has_creative_europe:
            has_call_search_intent = True

        # "calls for ..." pattern combined with Creative Europe
        if "calls for" in query_lower and (has_creative_europe or has_media_indicator):
            has_call_search_intent = True

        # "show me ... calls" pattern (e.g., "Show me all Creative Europe MEDIA calls")
        import re

        if re.search(r"show\s+me\s+.*\s*calls", query_lower) and (
            has_creative_europe or has_media_indicator
        ):
            has_call_search_intent = True

        # "find ... calls" pattern (e.g., "Find all MEDIA calls")
        if re.search(r"find\s+.*\s*calls", query_lower) and (
            has_creative_europe or has_media_indicator
        ):
            has_call_search_intent = True

        # "list ... calls" pattern
        if re.search(r"list\s+.*\s*calls", query_lower) and (
            has_creative_europe or has_media_indicator
        ):
            has_call_search_intent = True

        # "search ... calls" pattern
        if re.search(r"search\s+.*\s*calls", query_lower) and (
            has_creative_europe or has_media_indicator
        ):
            has_call_search_intent = True

        # Determine if this is a call search query
        is_call_search = (
            has_creative_europe
            and (has_call_search_intent or (has_status_indicator and "call" in query_lower))
        ) or (
            has_call_search_intent
            and (has_media_indicator or has_culture_indicator or has_cross_sectoral_indicator)
        )

        if not is_call_search:
            return None

        # Determine search keywords based on strand and topic
        keywords = []
        status = "open"  # Default to open calls

        # Determine strand
        strand = None
        if has_media_indicator or "media" in query_lower:
            strand = "MEDIA"
            keywords.append("CREA-MEDIA")
        elif has_culture_indicator or "culture" in query_lower:
            strand = "CULTURE"
            keywords.append("CREA-CULT")
        elif has_cross_sectoral_indicator or "cross" in query_lower:
            strand = "CROSS-SECTORAL"
            keywords.append("CREA-CROSS")
        else:
            # Generic Creative Europe search
            keywords.append("Creative Europe")

        # Add topic-specific keywords
        topic_keywords = []
        if "distribution" in query_lower or "film distribution" in query_lower:
            topic_keywords.extend(["distribution", "films on the move", "sales agent"])
        if "development" in query_lower or "film development" in query_lower:
            topic_keywords.extend(["development", "slate", "co-development"])
        if "festival" in query_lower:
            topic_keywords.append("festival")
        if "training" in query_lower:
            topic_keywords.append("training")
        if "network" in query_lower or "cinema network" in query_lower:
            topic_keywords.extend(["network", "cinema"])
        if "cooperation" in query_lower:
            topic_keywords.append("cooperation")
        if "literary" in query_lower or "translation" in query_lower:
            topic_keywords.extend(["literary", "translation"])

        if topic_keywords:
            keywords.extend(topic_keywords)

        # Determine status
        if "upcoming" in query_lower:
            status = "upcoming"
        elif "closed" in query_lower:
            status = "closed"
        else:
            status = "open"

        # Build search query string
        search_query = " ".join(keywords[:5])  # Limit to 5 keywords

        return {
            "thought": f"User is searching for {status} Creative Europe {strand or ''} calls. Using search_funding_calls tool to find actual calls.",
            "action": "call_tools",
            "tool_calls": [
                {
                    "tool": "search_funding_calls",
                    "parameters": {
                        "keywords": search_query,
                        "status": status,
                    },
                    "reasoning": f"Searching for {status} Creative Europe {strand or 'all strand'} calls matching: {search_query}",
                }
            ],
            "confidence": 0.95,
            "needs_more_info": False,
        }

    # ========================================================================
    # CREATIVE EUROPE COOPERATION PROJECTS (CULTURE STRAND) DETECTION AND GUIDANCE
    # ========================================================================

    def _detect_creative_europe_cooperation_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect Creative Europe Cooperation Projects (CULTURE strand) queries.

        These are questions about:
        - Cooperation projects overview and how they work
        - Scale categories (small, medium, large)
        - Partnership requirements and partner counts
        - Funding rates and co-financing
        - Scale selection based on consortium size

        These queries should provide structured guidance with actionable Next Steps.
        """
        query_lower = query.lower()
        context_lower = context.lower() if context else ""

        # Track if Creative Europe/CULTURE/cooperation context is present
        has_ce_context = any(
            ind in context_lower
            for ind in [
                "creative europe",
                "culture strand",
                "cultural sector",
                "cooperation project",
                "european cooperation",
            ]
        )
        has_cooperation_context = any(
            ind in context_lower
            for ind in [
                "cooperation",
                "cooperation project",
                "small-scale",
                "medium-scale",
                "large-scale",
                "partner",
                "consortium",
            ]
        )

        # === Pattern 1: Cooperation projects overview ===
        # e.g., "What are Creative Europe cooperation projects and how do they work?"
        # e.g., "Tell me about Creative Europe cooperation projects"
        overview_patterns = [
            "creative europe cooperation",
            "cooperation projects",
            "what are cooperation",
            "about cooperation project",
            "european cooperation project",
            "how do cooperation project",
            "how do they work",
            "tell me about cooperation",
            "explain cooperation project",
            "overview of cooperation",
            "culture cooperation",
            "culture strand cooperation",
            "creative europe culture cooperation",
        ]

        if any(p in query_lower for p in overview_patterns):
            guidance = self._generate_ce_cooperation_overview_guidance()
            return {
                "thought": "User is asking about Creative Europe Cooperation Projects overview. Providing comprehensive guidance on cooperation projects in the CULTURE strand.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "ce_cooperation_overview",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 2: Scale categories (small/medium/large) ===
        # e.g., "What's the difference between small, medium, and large-scale Creative Europe cooperation projects?"
        # e.g., "Small vs medium vs large scale projects"
        # Note: We use inline pattern checks below instead of a pattern list

        # Check for scale comparison in query
        has_scale_in_query = any(p in query_lower for p in ["small", "medium", "large", "scale"])
        has_comparison_keywords = any(
            p in query_lower
            for p in [
                "difference",
                "vs",
                "versus",
                "compare",
                "between",
                "categories",
                "types",
                "options",
            ]
        )

        # Match scale comparison with CE or cooperation context
        if (has_scale_in_query and has_comparison_keywords) and (
            "creative europe" in query_lower
            or "cooperation" in query_lower
            or has_ce_context
            or has_cooperation_context
        ):
            guidance = self._generate_ce_scale_comparison_guidance()
            return {
                "thought": "User is asking about Creative Europe cooperation project scale categories. Providing detailed comparison of small, medium, and large-scale options.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "ce_scale_comparison",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 3: Partner count category selection ===
        # e.g., "We have 3 partners in our consortium - which Creative Europe cooperation project category fits us?"
        # e.g., "3 partners - which category?"
        # Note: We use inline pattern checks below instead of a pattern list

        # Check for partner count questions with CE or cooperation context
        has_partner_in_query = "partner" in query_lower
        has_count_or_category = any(
            p in query_lower
            for p in [
                "how many",
                "which category",
                "which.*fit",
                "qualify",
                "eligible",
                "minimum",
                "requirement",
                "3 ",
                "4 ",
                "5 ",
                "6 ",
                "10 ",
                "three",
                "four",
                "five",
                "six",
                "ten",
            ]
        )

        if (
            has_partner_in_query
            and has_count_or_category
            and (
                "creative europe" in query_lower
                or "cooperation" in query_lower
                or has_ce_context
                or has_cooperation_context
            )
        ):
            guidance = self._generate_ce_partner_category_guidance()
            return {
                "thought": "User is asking about which Creative Europe cooperation project category fits their partner count. Providing guidance on scale selection based on consortium size.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "ce_partner_category",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 4: Funding rate / co-financing ===
        # e.g., "What is the Creative Europe cooperation project funding rate - how much does the EU cover?"
        # e.g., "What percentage does Creative Europe fund?"
        # Note: We use inline pattern checks below instead of a pattern list

        # Check for funding rate with CE or cooperation context
        has_funding_in_query = any(
            p in query_lower
            for p in [
                "funding",
                "rate",
                "cover",
                "contribution",
                "percentage",
                "grant",
                "co-financing",
                "cofinancing",
                "match",
            ]
        )

        if has_funding_in_query and (
            "creative europe" in query_lower
            or "cooperation" in query_lower
            or has_ce_context
            or has_cooperation_context
        ):
            guidance = self._generate_ce_funding_rate_guidance()
            return {
                "thought": "User is asking about Creative Europe cooperation project funding rates. Providing detailed information on co-financing requirements.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "ce_funding_rate",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        # === Pattern 5: Growing into medium/large scale ===
        # e.g., "If we want to grow into a medium-scale Creative Europe cooperation project, what would we need?"
        # e.g., "How to move from small to medium scale?"
        # Note: We use inline pattern checks below instead of a pattern list

        # Check for scale growth with CE or cooperation context
        has_growth_in_query = any(
            p in query_lower
            for p in [
                "grow",
                "move",
                "upgrade",
                "expand",
                "transition",
                "from small",
                "from medium",
                "need",
            ]
        )
        has_scale_target = any(p in query_lower for p in ["medium", "large"])

        if (
            has_growth_in_query
            and has_scale_target
            and (
                "creative europe" in query_lower
                or "cooperation" in query_lower
                or has_ce_context
                or has_cooperation_context
            )
        ):
            guidance = self._generate_ce_scale_growth_guidance()
            return {
                "thought": "User is asking about growing into a larger Creative Europe cooperation project scale. Providing guidance on scaling up requirements.",
                "action": "generate_guidance",
                "response": guidance,
                "guidance_type": "ce_scale_growth",
                "confidence": 0.90,
                "needs_more_info": False,
            }

        return None

    def _detect_niche_interdisciplinary_query(
        self, query: str, context: str
    ) -> dict[str, Any] | None:
        """Detect very specific niche queries that span multiple domains.

        These are queries that combine:
        - Multiple specialized fields (e.g., archaeology + AI + marine)
        - Specific geographic constraints (e.g., Mediterranean, Arctic)
        - Unusual technology applications in traditional fields
        - Cross-cutting themes that don't fit neatly into one cluster

        The goal is to:
        1. Acknowledge the interdisciplinary nature of the query
        2. Search across multiple relevant programmes/clusters
        3. Provide helpful guidance when exact matches don't exist
        4. NOT hallucinate specific calls - be honest about what exists

        Examples:
        - "Funding for underwater archaeology using AI in the Mediterranean"
        - "Grants for traditional crafts preservation using blockchain"
        - "Support for indigenous language revitalization with NLP"
        """
        query_lower = query.lower()

        # Domain indicators - traditional/specialized fields
        traditional_domains = {
            "archaeology": ["archaeolog", "excavation", "artifact", "antiquit"],
            "heritage": ["heritage", "cultural preservation", "monument", "restoration"],
            "linguistics": ["linguistic", "language revitalization", "endangered language"],
            "crafts": ["traditional craft", "artisan", "handicraft", "folk art"],
            "ethnography": ["ethnograph", "indigenous", "tribal", "folk culture"],
            "maritime": ["underwater", "maritime", "shipwreck", "marine archaeology"],
            "restoration": ["restoration", "conservation", "preserv"],
        }

        # Technology indicators - modern tech applications
        technology_domains = {
            "ai": ["ai", "artificial intelligence", "machine learning", "deep learning"],
            "digital": ["digital", "digitiz", "digitalis", "3d scanning", "virtual reality"],
            "blockchain": ["blockchain", "nft", "decentralized"],
            "nlp": ["nlp", "natural language processing", "text mining"],
            "robotics": ["robot", "autonomous", "drone", "uav"],
            "imaging": ["imaging", "photogrammetry", "lidar", "remote sensing"],
        }

        # Geographic constraints
        geographic_constraints = [
            "mediterranean",
            "arctic",
            "baltic",
            "alpine",
            "sahara",
            "amazon",
            "pacific",
            "atlantic",
            "caribbean",
            "black sea",
            "adriatic",
            "aegean",
        ]

        # Detect domain combinations
        detected_traditional = []
        detected_tech = []
        detected_geo = []

        for domain, patterns in traditional_domains.items():
            if any(p in query_lower for p in patterns):
                detected_traditional.append(domain)

        for domain, patterns in technology_domains.items():
            if any(p in query_lower for p in patterns):
                detected_tech.append(domain)

        for geo in geographic_constraints:
            if geo in query_lower:
                detected_geo.append(geo)

        # This is a niche interdisciplinary query if:
        # 1. Combines traditional domain with technology domain
        # 2. OR has geographic constraint with specialized field
        # 3. AND is asking for funding/calls/grants
        is_funding_query = any(
            term in query_lower
            for term in [
                "funding",
                "grant",
                "call",
                "support",
                "finance",
                "money",
                "programme",
                "program",
            ]
        )

        is_niche = is_funding_query and (
            (len(detected_traditional) >= 1 and len(detected_tech) >= 1)
            or (len(detected_traditional) >= 1 and len(detected_geo) >= 1)
            or (len(detected_tech) >= 1 and len(detected_geo) >= 1)
        )

        if not is_niche:
            return None

        # Determine relevant clusters and programmes
        relevant_clusters = []
        relevant_programmes = []

        # Map domains to Horizon Europe clusters
        if any(
            d in detected_traditional
            for d in [
                "heritage",
                "archaeology",
                "linguistics",
                "crafts",
                "ethnography",
                "restoration",
            ]
        ):
            relevant_clusters.append("CL2")  # Culture, Creativity, Inclusive Society
            relevant_programmes.append("Creative Europe")

        if any(d in detected_traditional for d in ["maritime"]):
            relevant_clusters.append("CL6")  # Food, Bioeconomy, Natural Resources
            relevant_programmes.append("Mission Restore our Ocean and Waters")

        if any(d in detected_tech for d in ["ai", "digital", "nlp", "imaging"]):
            relevant_clusters.append("CL4")  # Digital, Industry, Space

        if any(d in detected_tech for d in ["robotics"]):
            relevant_clusters.append("CL4")

        # Deduplicate
        relevant_clusters = list(set(relevant_clusters))
        relevant_programmes = list(set(relevant_programmes))

        logger.info(
            f"🔬 Detected niche interdisciplinary query: "
            f"traditional={detected_traditional}, tech={detected_tech}, "
            f"geo={detected_geo}, clusters={relevant_clusters}"
        )

        # Build search keywords - combine domain terms
        search_terms = []
        if detected_traditional:
            search_terms.extend(detected_traditional)
        if detected_tech:
            search_terms.extend(detected_tech)
        if detected_geo:
            search_terms.extend(detected_geo)

        # Create multi-faceted search approach
        tool_calls = []

        # 1. Search for funding calls with combined keywords
        tool_calls.append(
            {
                "tool": "search_funding_calls",
                "parameters": {
                    "keywords": " ".join(search_terms[:3]),  # Top 3 terms
                    "status": "open",
                },
                "reasoning": "Search for funding calls matching the interdisciplinary topic",
            }
        )

        # 2. Search for similar funded projects (semantic search)
        tool_calls.append(
            {
                "tool": "get_similar_funded_projects",
                "parameters": {
                    "description": query,  # Use full query for semantic matching
                    "limit": 10,
                },
                "reasoning": "Find semantically similar projects using AI embeddings",
            }
        )

        # 3. Search documents for relevant programme information
        tool_calls.append(
            {
                "tool": "search_documents",
                "parameters": {
                    "query": " ".join(search_terms[:3]),
                    "limit": 5,
                },
                "reasoning": "Search work programmes for relevant topic areas",
            }
        )

        return {
            "thought": (
                f"This is a highly specialized interdisciplinary query combining "
                f"{', '.join(detected_traditional or ['traditional field'])} with "
                f"{', '.join(detected_tech or ['technology'])}. "
                f"Relevant clusters: {', '.join(relevant_clusters)}. "
                f"Will search across multiple sources and provide guidance on "
                f"alternative funding approaches if exact matches don't exist."
            ),
            "action": "call_tools_with_niche_guidance",
            "tool_calls": tool_calls,
            "niche_query_context": {
                "traditional_domains": detected_traditional,
                "tech_domains": detected_tech,
                "geographic_constraints": detected_geo,
                "relevant_clusters": relevant_clusters,
                "relevant_programmes": relevant_programmes,
                "search_terms": search_terms,
            },
            "needs_more_info": True,
        }

"""
V3 Response Formatter

Formats tool results into beautifully structured responses for the user.
This is a post-processor that takes raw tool results and formats them consistently.
"""

from datetime import datetime
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class V3ResponseFormatter:
    """Formats V3 agent responses with consistent styling."""

    # Type icons - only valid action types
    TYPE_ICONS = {
        "RIA": "🔬",
        "IA": "🚀",
        "CSA": "🤝",
        "COFUND": "💱",
        "ERC": "🎓",
        "MSCA": "👨‍🔬",
        "LUMP-SUM": "📦",
        "PCP": "🔧",
        "PPI": "🛒",
        "default": "📄",
    }

    # Valid action types (to filter out numeric IDs)
    VALID_ACTION_TYPES = {
        "RIA",
        "IA",
        "CSA",
        "COFUND",
        "ERC",
        "MSCA",
        "LUMP-SUM",
        "PCP",
        "PPI",
        "ERC-STG",
        "ERC-COG",
        "ERC-ADG",
        "ERC-POC",
        "MSCA-PF",
        "MSCA-DN",
        "MSCA-SE",
        "MSCA-COFUND",
    }

    # Status icons
    STATUS_ICONS = {"open": "🟢", "upcoming": "🟡", "closed": "🔴", "default": "📊"}

    def format_funding_calls(self, calls: list[dict], query: str = "") -> str:
        """Format a list of funding calls into a rich response."""
        if not calls:
            return "No funding calls found matching your search criteria."

        lines = [f"I found **{len(calls)} funding opportunities** for your query:\n"]

        for i, call in enumerate(calls, 1):
            lines.append(self._format_single_call(i, call))
            lines.append("")  # Empty line between calls

        # Add helpful footer
        lines.append("---\n")
        lines.append(self._get_application_guidance())

        return "\n".join(lines)

    def _format_single_call(self, index: int, call: dict) -> str:
        """Format a single funding call."""
        title = call.get("title", "Untitled Call") or "Untitled Call"
        call_id = (
            call.get("call_id")
            or call.get("topic_code")
            or call.get("topic_id")
            or call.get("identifier", "")
        )
        call_type = call.get("type") or call.get("action_type") or ""
        status = (call.get("status") or "open").lower()
        deadline = call.get("deadline") or call.get("application_deadline") or ""
        cluster = call.get("cluster") or call.get("programme") or call.get("work_programme") or ""
        budget = call.get("budget") or call.get("estimated_budget") or ""
        url = call.get("url") or call.get("portal_url") or ""

        # Get call summary - prioritize description/expected_outcome over scope (which is often verbose)
        summary = self._get_call_summary(call)

        # Validate and clean call_type - filter out numeric IDs and invalid types
        call_type_upper = call_type.upper() if call_type else ""
        is_valid_type = call_type_upper in self.VALID_ACTION_TYPES

        # Get icons - only if valid type
        type_icon = (
            self.TYPE_ICONS.get(call_type_upper, self.TYPE_ICONS["default"])
            if is_valid_type
            else None
        )
        status_icon = self.STATUS_ICONS.get(status, self.STATUS_ICONS["default"])

        # Format deadline
        deadline_str = self._format_deadline(deadline)

        # Format budget
        budget_str = self._format_budget(budget)

        # Build the formatted entry
        lines = [f"**{index}. {title}**"]

        if call_id:
            lines.append(f"📋 **Call ID:** {call_id}")

        # Only show type if it's a valid action type (not numeric ID)
        if call_type and is_valid_type:
            lines.append(f"{type_icon} **Type:** {call_type_upper}")

        lines.append(f"{status_icon} **Status:** {status.capitalize()}")

        if deadline_str:
            lines.append(f"⏰ **Deadline:** {deadline_str}")

        if cluster:
            lines.append(
                f"🏛️ **Programme:** Cluster {cluster}"
                if cluster.startswith("CL")
                else f"🏛️ **Programme:** {cluster}"
            )

        if budget_str:
            lines.append(f"💰 **Budget:** {budget_str}")

        if summary:
            lines.append(f"\n📝 **Summary:** {summary}")

        # Add apply link - use provided URL or generate from call_id
        if url:
            lines.append(f"\n🔗 **Apply:** {url}")
        elif call_id and call_id.startswith("HORIZON"):
            portal_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id}"
            lines.append(f"\n🔗 **Apply:** {portal_url}")

        lines.append("\n---")

        return "\n".join(lines)

    def _get_call_summary(self, call: dict) -> str:
        """
        Extract a clean, concise summary from call data.

        Prioritizes:
        1. description field (if clean and concise)
        2. expected_outcome (usually has clear bullet points)
        3. scope (as fallback, cleaned up)
        """
        # Try description first (often already a good summary)
        description = call.get("description", "")
        if description:
            cleaned = self._clean_html_and_extract_summary(description)
            if cleaned and len(cleaned) >= 50:
                return cleaned

        # Try expected_outcome (usually more structured)
        expected_outcome = call.get("expected_outcome", "")
        if expected_outcome:
            cleaned = self._clean_html_and_extract_summary(expected_outcome)
            if cleaned and len(cleaned) >= 50:
                return cleaned

        # Fall back to scope
        scope = call.get("scope", "")
        if scope:
            cleaned = self._clean_html_and_extract_summary(scope)
            if cleaned:
                return cleaned

        # Try objective as last resort
        objective = call.get("objective", "")
        if objective:
            cleaned = self._clean_html_and_extract_summary(objective)
            if cleaned:
                return cleaned

        return ""

    def _clean_html_and_extract_summary(self, text: str) -> str:
        """
        Clean HTML tags and extract a readable summary from call text.

        Returns a clean, concise summary (max ~250 chars).
        """
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Remove HTML entities
        text = re.sub(r"&[a-zA-Z]+;", " ", text)
        text = re.sub(r"&#\d+;", " ", text)

        # Remove common noise patterns at the start
        noise_prefixes = [
            r"^Expected Outcome:?\s*",
            r"^Scope:?\s*",
            r"^Description:?\s*",
            r"^Objective:?\s*",
            r"^\s*Project results are expected to contribute to (all of )?the following (expected )?outcomes?:?\s*",
        ]
        for pattern in noise_prefixes:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove document noise
        noise_patterns = [
            r"The Director-General responsible.*?$",
            r"All deadlines are at.*?$",
            r"Legal and financial.*?$",
            r"\[?\d+\]",  # Reference numbers like [1]
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, "", text, flags=re.MULTILINE)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # If text is too short after cleaning, return empty
        if len(text) < 30:
            return ""

        # Extract first meaningful sentence or first ~250 chars
        # Try to end at a sentence boundary
        max_len = 250
        if len(text) <= max_len:
            return text

        # Find a good break point (end of sentence)
        truncated = text[:max_len]

        # Look for sentence end (.!?) followed by space or end
        sentence_end = -1
        for i in range(len(truncated) - 1, max(len(truncated) - 100, 0), -1):
            if truncated[i] in ".!?" and (i == len(truncated) - 1 or truncated[i + 1] == " "):
                sentence_end = i + 1
                break

        if sentence_end > 100:  # Found a reasonable sentence break
            return truncated[:sentence_end].strip()
        else:
            # No good sentence break, truncate at word boundary
            last_space = truncated.rfind(" ")
            if last_space > 150:
                return truncated[:last_space].strip() + "..."
            else:
                return truncated.strip() + "..."

    def _clean_scope_text(self, scope: str) -> str:
        """Clean up scope text to remove document fragments and noise."""
        if not scope:
            return ""

        # Remove common document fragment patterns
        noise_patterns = [
            "The Director-General responsible may delay",
            "All deadlines are at 17.00.00 Brussels",
            "Legal and financial The rules are described",
            "General Annex",
            "Expected EU The Commission estimates",
            "contribution per project",
            "Nonetheless, this does not preclude submission",
            "Opening:",
            "Deadline(s):",
            "Overview of this call",
            "Proposals are invited against",
            "Topics Type Budgets",
            "EUR million",
            "indicative budget",
        ]

        # Check if scope starts with noise (first 100 chars contain noise patterns)
        scope_start = scope[:150].lower()
        for pattern in noise_patterns:
            if pattern.lower() in scope_start:
                # Try to find where actual content starts
                # Look for "Project results are expected" or similar
                content_markers = [
                    "Project results are expected",
                    "The action should",
                    "This topic",
                    "Proposals should",
                    "The objective",
                    "Activities should",
                ]
                for marker in content_markers:
                    idx = scope.find(marker)
                    if idx > 0 and idx < 500:
                        scope = scope[idx:]
                        break
                break

        # Remove repeated whitespace
        scope = re.sub(r"\s+", " ", scope).strip()

        # If scope is too short after cleaning, return empty
        if len(scope) < 30:
            return ""

        return scope

    def _format_deadline(self, deadline: Any) -> str:
        """Format deadline to human-readable string."""
        if not deadline:
            return "Check official portal for deadline"

        if isinstance(deadline, datetime):
            return deadline.strftime("%d %b %Y")

        if isinstance(deadline, str):
            # Try to parse common formats
            try:
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        dt = datetime.strptime(deadline.split("T")[0], fmt.split("T")[0])
                        return dt.strftime("%d %b %Y")
                    except ValueError:
                        continue
                return deadline  # Return as-is if parsing fails
            except Exception:
                return deadline

        return str(deadline)

    def _format_budget(self, budget: Any) -> str:
        """Format budget to readable string."""
        if not budget:
            return ""

        if isinstance(budget, int | float):
            if budget >= 1_000_000:
                return f"EUR {budget / 1_000_000:.2f} million"
            elif budget >= 1_000:
                return f"EUR {budget / 1_000:.0f}K"
            else:
                return f"EUR {budget:,.0f}"

        if isinstance(budget, str):
            # Clean up existing string
            budget = budget.strip()
            if budget.lower().startswith("eur"):
                return budget
            if any(c.isdigit() for c in budget):
                return f"EUR {budget}"
            return budget

        return str(budget)

    def _get_application_guidance(self) -> str:
        """Return helpful application guidance footer."""
        return """💡 **How to Apply:**
• **Register** on the EU Funding & Tenders Portal if you haven't already
• **Check eligibility** criteria carefully for each call
• **Prepare partnerships** - many calls require consortium applications
• **Review evaluation criteria** and weightings in the call documentation
• **Submit well before** the deadline - the portal can be busy near deadlines

📚 **Useful Resources:**
• [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home)
• [How to Participate Guide](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)

🎯 **Next Steps:**
• Click on the 'Apply' links above for full call details
• Download the call documentation and work programme
• Start building your consortium if partnerships are required"""

    def format_projects(self, projects: list[dict], query: str = "") -> str:
        """Format a list of CORDIS projects."""
        if not projects:
            return "No projects found matching your search criteria."

        lines = [f"I found **{len(projects)} funded projects** related to your query:\n"]

        for i, project in enumerate(projects, 1):
            lines.append(self._format_single_project(i, project))
            lines.append("")

        # Add helpful footer with next steps
        lines.append("---\n")
        lines.append(self._get_project_guidance(query))

        return "\n".join(lines)

    def _get_project_guidance(self, query: str = "") -> str:
        """Return helpful guidance footer for project searches."""
        return """💡 **How to Use These Projects:**
• **Learn from success:** Study project objectives and methodologies that match your ideas
• **Find partners:** Explore consortium members who have relevant experience
• **Understand budgets:** Use project budgets as benchmarks for your proposal
• **Track outputs:** Check CORDIS for publications, deliverables, and results

📚 **Useful Resources:**
• [CORDIS Database](https://cordis.europa.eu/) - Full project database with publications and results
• [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) - Find potential consortium partners
• [Success Stories](https://ec.europa.eu/research/horizon-europe/success-stories/) - Inspiring examples from funded projects

🎯 **Next Steps:**
• Click on the 'Details' links above to view full project information on CORDIS
• Contact project coordinators if you're interested in collaboration
• Use similar project budgets and consortium sizes as benchmarks for your proposal
• Search for related publications to understand the state of the art"""

    def _format_single_project(self, index: int, project: dict) -> str:
        """Format a single project with optional publications and deliverables."""
        title = project.get("title", project.get("acronym", "Untitled Project"))
        acronym = project.get("acronym", "")
        project_id = project.get("id", project.get("project_id", ""))
        programme = project.get("programme", project.get("frameworkProgramme", ""))
        status = project.get("status", "")
        start_date = project.get("startDate", project.get("start_date", ""))
        end_date = project.get("endDate", project.get("end_date", ""))
        _total_cost = project.get("totalCost", project.get("total_cost", ""))  # noqa: F841
        eu_contribution = project.get("ecMaxContribution", project.get("eu_contribution", ""))
        objective = project.get("objective", project.get("description", ""))
        coordinator = project.get("coordinator", "")

        # Optional enhanced data
        publications = project.get("publications", [])
        deliverables = project.get("deliverables", [])
        impact_metrics = project.get("impact_metrics", {})

        lines = []

        # Title with acronym
        if acronym and acronym != title:
            lines.append(f"**{index}. {acronym}: {title}**")
        else:
            lines.append(f"**{index}. {title}**")

        if project_id:
            lines.append(f"🔢 **Project ID:** {project_id}")

        if programme:
            lines.append(f"🏛️ **Programme:** {programme}")

        if status:
            status_icon = (
                "🟢"
                if status.lower() == "ongoing"
                else "✅"
                if status.lower() == "closed"
                else "📊"
            )
            lines.append(f"{status_icon} **Status:** {status}")

        if start_date or end_date:
            date_range = f"{start_date or '?'} → {end_date or '?'}"
            lines.append(f"📅 **Duration:** {date_range}")

        if eu_contribution:
            lines.append(f"💰 **EU Contribution:** {self._format_budget(eu_contribution)}")

        if coordinator:
            lines.append(f"🏢 **Coordinator:** {coordinator}")

        if objective:
            obj_text = objective[:400] + "..." if len(objective) > 400 else objective
            lines.append(f"\n**Objective:** {obj_text}")

        # Publications section (if available)
        if publications:
            lines.append("\n📚 **Key Publications:**")
            for pub in publications[:3]:
                pub_title = pub.get("title", "Untitled")
                if len(pub_title) > 80:
                    pub_title = pub_title[:77] + "..."
                authors = pub.get("authors", "")
                if len(authors) > 50:
                    authors = authors[:47] + "..."
                journal = pub.get("journal", "")
                doi = pub.get("doi", "")

                pub_line = f"  • {pub_title}"
                if authors:
                    pub_line += f" - *{authors}*"
                if journal:
                    pub_line += f" ({journal})"
                if doi:
                    pub_line += f" [DOI](https://doi.org/{doi})"
                lines.append(pub_line)

        # Deliverables section (if available)
        if deliverables:
            lines.append("\n📦 **Key Deliverables:**")
            for deliv in deliverables[:3]:
                deliv_title = deliv.get("title", "Untitled")
                if len(deliv_title) > 60:
                    deliv_title = deliv_title[:57] + "..."
                deliv_type = deliv.get("type", "")
                url = deliv.get("url", "")

                deliv_line = f"  • {deliv_title}"
                if deliv_type:
                    deliv_line += f" ({deliv_type})"
                if url:
                    deliv_line += f" [View]({url})"
                lines.append(deliv_line)

        # Impact metrics section (if available)
        if impact_metrics:
            impact_parts = []
            if impact_metrics.get("publications_count"):
                impact_parts.append(f"{impact_metrics['publications_count']} publications")
            if impact_metrics.get("deliverables_count"):
                impact_parts.append(f"{impact_metrics['deliverables_count']} deliverables")
            if impact_metrics.get("patents_count"):
                impact_parts.append(f"{impact_metrics['patents_count']} patents")
            if impact_metrics.get("datasets_count"):
                impact_parts.append(f"{impact_metrics['datasets_count']} datasets")

            if impact_parts:
                lines.append(f"\n📊 **Impact:** {', '.join(impact_parts)}")

        # CORDIS link
        if project_id:
            cordis_url = f"https://cordis.europa.eu/project/id/{project_id}"
            lines.append(f"\n🔗 **Details:** {cordis_url}")

        lines.append("\n---")

        return "\n".join(lines)

    def format_from_tool_results(self, tool_results: dict[str, Any], query: str = "") -> str | None:
        """
        Detect the type of results and format appropriately.
        Merges results from multiple tool calls and deduplicates.
        Returns None if no formattable results found.
        """
        # Collect ALL calls and projects from ALL tool results
        all_calls = []
        all_projects = []
        all_documents = []
        seen_call_ids = set()
        seen_project_ids = set()
        seen_chunk_ids = set()

        # Track organization-specific results for special formatting
        org_projects_result = None
        collaboration_network_result = None
        budget_calculation_result = None

        for _tool_name, result in tool_results.items():
            if not isinstance(result, dict):
                continue

            # Check for budget calculation results (from calculate_budget)
            # These have "calculated_budget", "breakdown", and "tool_name": "calculate_budget"
            if (
                "calculated_budget" in result
                and "breakdown" in result
                and result.get("tool_name") == "calculate_budget"
            ):
                budget_calculation_result = result
                continue  # Don't add these to generic results

            # Check for collaboration network results (from get_collaboration_network)
            # These have "organization", "partners", and "total_partners" fields
            if (
                "organization" in result
                and "partners" in result
                and "total_partners" in result
                and "get_collaboration_network" in _tool_name
            ):
                collaboration_network_result = result
                continue  # Don't add these to generic results

            # Check for organization-specific project results (from find_organization_projects)
            # These have "organization", "projects", and "count" fields
            if (
                "organization" in result
                and "projects" in result
                and "count" in result
                and "find_organization_projects" in _tool_name
            ):
                org_projects_result = result
                continue  # Don't add these to generic projects

            # Check for document search results (from search_documents)
            # These have "documents" field with content, source, section
            if "documents" in result and isinstance(result["documents"], list):
                docs = result["documents"]
                if docs and all(
                    isinstance(d, dict) and "content" in d and "source" in d for d in docs[:3]
                ):
                    # Collect documents with deduplication
                    for doc in docs:
                        chunk_id = doc.get("chunk_id", "")
                        if chunk_id and chunk_id not in seen_chunk_ids:
                            seen_chunk_ids.add(chunk_id)
                            all_documents.append(doc)
                        elif not chunk_id:
                            all_documents.append(doc)
                    continue

            # Collect funding calls from this tool result
            if "calls" in result and isinstance(result["calls"], list):
                for call in result["calls"]:
                    # Deduplicate by call_id
                    call_id = (
                        call.get("call_id")
                        or call.get("topic_code")
                        or call.get("topic_id")
                        or call.get("identifier", "")
                    )
                    if call_id and call_id not in seen_call_ids:
                        seen_call_ids.add(call_id)
                        all_calls.append(call)
                    elif not call_id:
                        # No ID, include but might be duplicate
                        all_calls.append(call)

            # Collect projects from this tool result
            if "projects" in result and isinstance(result["projects"], list):
                for project in result["projects"]:
                    # Deduplicate by project_id
                    project_id = project.get("id") or project.get("project_id", "")
                    if project_id and project_id not in seen_project_ids:
                        seen_project_ids.add(project_id)
                        all_projects.append(project)
                    elif not project_id:
                        # No ID, include but might be duplicate
                        all_projects.append(project)

        # Format budget calculation results if available (highest priority)
        if budget_calculation_result:
            logger.info("📋 Formatting budget calculation results")
            return self.format_budget_calculation(budget_calculation_result, query)

        # Format collaboration network results if available
        if collaboration_network_result:
            logger.info(
                f"📋 Formatting collaboration network for '{collaboration_network_result.get('organization')}'"
            )
            return self.format_collaboration_network(collaboration_network_result, query)

        # Format organization-specific results if available (takes priority)
        if org_projects_result:
            logger.info(
                f"📋 Formatting organization projects for '{org_projects_result.get('organization')}'"
            )
            return self.format_organization_projects(org_projects_result, query)

        # Format document search results if available
        if all_documents:
            logger.info(f"📋 Formatting {len(all_documents)} document excerpts")
            return self.format_documents(all_documents, query)

        # Format the merged results (prefer calls over projects if both present)
        if all_calls:
            logger.info(
                f"📋 Formatting {len(all_calls)} merged funding calls (deduplicated from {len(seen_call_ids)} unique IDs)"
            )
            return self.format_funding_calls(all_calls, query)

        if all_projects:
            logger.info(
                f"📋 Formatting {len(all_projects)} merged projects (deduplicated from {len(seen_project_ids)} unique IDs)"
            )
            return self.format_projects(all_projects, query)

        return None

    def format_organization_projects(self, result: dict[str, Any], query: str = "") -> str:
        """Format organization-specific project results with richer context."""
        org_name = result.get("organization", "Unknown Organization")
        projects = result.get("projects", [])
        count = result.get("count", len(projects))
        role_filter = result.get("role_filter")

        if not projects:
            return f"""## Projects for {org_name}

No projects found for this organization in the database.

**Suggestions:**
- Check the organization name spelling
- Try searching with a shorter name (e.g., "TUM" instead of "Technical University of Munich")
- The organization may not have participated in Horizon Europe yet"""

        role_desc = f" (as {role_filter})" if role_filter else ""
        lines = [f"## Projects by {org_name}{role_desc}", f"**Total Projects Found:** {count}\n"]

        # Separate by role
        coordinated = [p for p in projects if p.get("role") == "coordinator"]
        participated = [p for p in projects if p.get("role") != "coordinator"]

        if coordinated:
            lines.append(f"### 🎯 Coordinated Projects ({len(coordinated)})\n")
            for p in coordinated[:10]:
                lines.append(self._format_org_project(p, is_coordinator=True))
        elif count > 0:
            # No coordinator projects but has participant projects - note this
            lines.append("### 🎯 Coordinated Projects (0)\n")
            lines.append(
                "No projects coordinated by this organization found in the database.\n"
                "The organization participates in projects but hasn't coordinated any "
                "in the current dataset.\n"
            )

        if participated:
            lines.append(f"\n### 🤝 As Participant ({len(participated)})\n")
            for p in participated[:10]:
                lines.append(self._format_org_project(p, is_coordinator=False))

        # Add summary insights
        total_budget = sum(p.get("budget", 0) or 0 for p in projects)
        funding_schemes = set(p.get("funding_scheme") for p in projects if p.get("funding_scheme"))

        lines.append(
            f"""
### 📊 Summary
- **Total Projects:** {count}
- **As Coordinator:** {len(coordinated)}
- **Total Budget Involved:** €{total_budget / 1_000_000:.1f}M
- **Funding Types:** {", ".join(funding_schemes) if funding_schemes else "N/A"}

**Next Steps:**
• Explore specific project details on CORDIS
• Search for collaboration partners
• Analyze the organization's research focus areas
• Use `get_collaboration_network` to see their key partners"""
        )

        return "\n".join(lines)

    def _format_org_project(self, project: dict, is_coordinator: bool = False) -> str:
        """Format a single project for organization results."""
        acronym = project.get("acronym", "N/A")
        title = project.get("title", "N/A")
        if title and len(title) > 60:
            title = title[:60] + "..."
        budget = project.get("budget", 0)
        scheme = project.get("funding_scheme", "N/A")
        status = project.get("status", "N/A")
        url = project.get("cordis_url", "")
        start = project.get("start_date", "")
        if start:
            start = str(start)[:10]

        budget_str = f"€{budget / 1_000_000:.1f}M" if budget else "N/A"

        if is_coordinator:
            line = f"- **{acronym}**: {title}\n"
            line += f"  - Budget: {budget_str} | Type: {scheme} | Status: {status}"
            if start:
                line += f" | Started: {start}"
            line += "\n"
            if url:
                line += f"  - [View on CORDIS]({url})\n"
        else:
            line = f"- **{acronym}**: {title} ({scheme}, {budget_str})"
            if url:
                line += f" [→]({url})"
            line += "\n"

        return line

    def format_collaboration_network(self, result: dict[str, Any], query: str = "") -> str:
        """Format collaboration network results showing an organization's partners."""
        org_name = result.get("organization", "Unknown Organization")
        org_country = result.get("country", "")
        partners = result.get("partners", [])
        total_partners = result.get("total_partners", len(partners))

        if not partners:
            return f"""## Collaboration Network for {org_name}

No collaboration partners found for this organization in the database.

**Suggestions:**
- Check the organization name spelling
- Try searching with a shorter name (e.g., "Fraunhofer" instead of "Fraunhofer Society")
- The organization may not have participated in collaborative EU projects yet
- Try using `find_organization_projects` to see their project history first"""

        # Build header
        country_str = f" ({org_country})" if org_country else ""
        lines = [
            f"## Collaboration Network for {org_name}{country_str}",
            f"**Total Partners Found:** {total_partners}\n",
        ]

        # Group partners by collaboration intensity
        high_collab = [p for p in partners if p.get("collaborations", 0) >= 5]
        medium_collab = [p for p in partners if 2 <= p.get("collaborations", 0) < 5]
        low_collab = [p for p in partners if p.get("collaborations", 0) == 1]

        # Top collaborators section
        if high_collab:
            lines.append("### 🌟 Key Partners (5+ shared projects)\n")
            for partner in high_collab[:10]:
                lines.append(self._format_partner(partner, highlight=True))
            lines.append("")

        if medium_collab:
            lines.append("### 🤝 Regular Partners (2-4 shared projects)\n")
            for partner in medium_collab[:10]:
                lines.append(self._format_partner(partner, highlight=False))
            lines.append("")

        if low_collab and len(high_collab) + len(medium_collab) < 10:
            lines.append("### 📋 Other Partners (1 shared project)\n")
            for partner in low_collab[:5]:
                lines.append(self._format_partner(partner, highlight=False))
            lines.append("")

        # Summary by organization type
        org_types = {}
        for p in partners:
            org_type = p.get("type", "Unknown")
            org_types[org_type] = org_types.get(org_type, 0) + 1

        # Summary by country
        countries = {}
        for p in partners:
            country = p.get("country", "Unknown")
            countries[country] = countries.get(country, 0) + 1

        # Sort by count
        top_types = sorted(org_types.items(), key=lambda x: -x[1])[:5]
        top_countries = sorted(countries.items(), key=lambda x: -x[1])[:8]

        lines.append("### 📊 Network Summary\n")
        lines.append(f"**Total Unique Partners:** {total_partners}")
        lines.append(f"**Partner Countries:** {len(countries)}")
        lines.append(
            f"**Most Active Collaborations:** {high_collab[0]['name'] if high_collab else 'N/A'} "
            f"({high_collab[0].get('collaborations', 0)} projects)"
            if high_collab
            else ""
        )

        # Organization types breakdown
        if top_types:
            type_breakdown = ", ".join([f"{self._get_org_type_name(t)}: {c}" for t, c in top_types])
            lines.append(f"\n**Partner Types:** {type_breakdown}")

        # Country breakdown
        if top_countries:
            country_breakdown = ", ".join([f"{c}: {n}" for c, n in top_countries])
            lines.append(f"**Top Countries:** {country_breakdown}")

        # Actionable guidance
        lines.append(
            f"""
---

🎯 **Next Steps:**
• Contact key partners for future consortium building
• Use [Partner Search](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) to find complementary organizations
• Analyze shared projects on [CORDIS](https://cordis.europa.eu/search?q={org_name.replace(" ", "%20")}) for collaboration patterns
• Consider geographic diversity when building new consortia
• Use `find_organization_projects` to see detailed project history"""
        )

        return "\n".join(lines)

    def _format_partner(self, partner: dict, highlight: bool = False) -> str:
        """Format a single partner in the collaboration network."""
        name = partner.get("name", "Unknown")
        country = partner.get("country", "")
        org_type = partner.get("type", "")
        is_sme = partner.get("is_sme", False)
        collaborations = partner.get("collaborations", 0)

        # Build partner line
        country_str = f" ({country})" if country else ""
        type_str = f" [{self._get_org_type_name(org_type)}]" if org_type else ""
        sme_str = " 🏢 SME" if is_sme else ""

        if highlight:
            line = f"- **{name}**{country_str}{type_str}{sme_str}\n"
            line += f"  - 📊 **{collaborations} shared projects**\n"
        else:
            line = f"- {name}{country_str}{type_str}{sme_str} — {collaborations} project(s)\n"

        return line

    def _get_org_type_name(self, org_type: str) -> str:
        """Get human-readable name for organization type code."""
        type_names = {
            "HES": "University",
            "REC": "Research",
            "PRC": "Private",
            "PUB": "Public",
            "OTH": "Other",
            "SME": "SME",
        }
        return type_names.get(org_type, org_type)

    def format_budget_calculation(self, result: dict[str, Any], query: str = "") -> str:
        """Format budget calculation results into a structured response."""
        if not result.get("success"):
            return "Budget calculation failed. Please try again with different parameters."

        input_params = result.get("input_parameters", {})
        calculated_budget = result.get("calculated_budget", {})
        breakdown = result.get("breakdown", {})
        per_partner = result.get("per_partner", {})
        effort_summary = result.get("effort_summary", {})
        benchmarks = result.get("benchmarks", {})
        recommendations = result.get("recommendations", [])
        cluster_context = result.get("cluster_context", {})
        similar_projects = result.get("similar_projects", [])

        # Build header
        action_type = input_params.get("action_type", "RIA")
        duration = input_params.get("duration_months", 36)
        num_partners = input_params.get("num_partners", 8)
        cluster = input_params.get("cluster") or result.get("metadata", {}).get("cluster_used", "")

        lines = [
            "## Budget Calculation Results\n",
            f"**Project Parameters:** {action_type} project, {duration} months, {num_partners} partners",
        ]

        if cluster:
            lines.append(f"**Research Cluster:** {cluster}")
        lines.append("")

        # Main budget summary
        total_cost = calculated_budget.get("total_cost", 0)
        eu_contribution = calculated_budget.get("eu_contribution", 0)
        funding_rate = calculated_budget.get("funding_rate", "100%")

        lines.append("### 💰 Budget Summary\n")
        lines.append("| **Category** | **Amount** |")
        lines.append("|--------------|------------|")
        lines.append(f"| Total Project Cost | **€{total_cost / 1_000_000:.2f}M** |")
        lines.append(f"| EU Contribution | **€{eu_contribution / 1_000_000:.2f}M** |")
        lines.append(f"| Funding Rate | {funding_rate} |")
        lines.append("")

        # Cost breakdown
        if breakdown:
            lines.append("### 📊 Cost Breakdown by Category\n")
            lines.append("| **Category** | **Amount** | **%** | **Description** |")
            lines.append("|--------------|------------|-------|-----------------|")

            category_order = [
                "personnel",
                "equipment",
                "travel",
                "subcontracting",
                "other_direct",
                "indirect",
            ]
            category_names = {
                "personnel": "👥 Personnel",
                "equipment": "🖥️ Equipment",
                "travel": "✈️ Travel",
                "subcontracting": "📋 Subcontracting",
                "other_direct": "📦 Other Direct",
                "indirect": "🏢 Indirect Costs",
            }

            for cat in category_order:
                if cat in breakdown:
                    cat_data = breakdown[cat]
                    amount = cat_data.get("amount", 0)
                    pct = cat_data.get("percentage", 0)
                    desc = cat_data.get("description", "")
                    cat_name = category_names.get(cat, cat.title())
                    lines.append(f"| {cat_name} | €{amount / 1_000:,.0f}K | {pct}% | {desc} |")

            lines.append("")

        # Per-partner distribution
        if per_partner:
            lines.append("### 🤝 Per-Partner Distribution\n")
            avg_budget = per_partner.get("average", 0)
            coord_budget = per_partner.get("coordinator_typical", 0)
            partner_budget = per_partner.get("partner_typical", 0)
            pms_per_partner = per_partner.get("pms_per_partner", 0)

            lines.append(f"- **Average per partner:** €{avg_budget / 1_000:,.0f}K")
            lines.append(
                f"- **Coordinator (typical):** €{coord_budget / 1_000:,.0f}K (20% of total)"
            )
            lines.append(f"- **Other partners (typical):** €{partner_budget / 1_000:,.0f}K each")
            lines.append(f"- **Person-months per partner:** ~{pms_per_partner:.0f} PM")
            lines.append("")

        # Effort summary
        if effort_summary:
            lines.append("### ⏱️ Effort Summary\n")
            total_pms = effort_summary.get("total_person_months", 0)
            pm_cost = effort_summary.get("avg_pm_cost_used", 0)
            pm_per_month = effort_summary.get("pm_per_month", 0)

            lines.append(f"- **Total Person-Months:** {total_pms} PM")
            lines.append(f"- **Average PM Cost Used:** €{pm_cost:,.0f}")
            lines.append(f"- **PM per Project Month:** {pm_per_month:.1f}")
            lines.append("")

        # Benchmarks
        if benchmarks:
            lines.append("### 📈 How This Compares\n")
            typical_range = benchmarks.get("typical_range", "N/A")
            median = benchmarks.get("median", "N/A")
            comparison = benchmarks.get("your_budget_vs_median", "within range")
            sample_size = benchmarks.get("sample_size", "N/A")

            lines.append(f"- **Typical {action_type} Budget Range:** {typical_range}")
            lines.append(f"- **Median Budget:** {median}")
            lines.append(f"- **Your Budget:** {comparison.replace('_', ' ').title()}")
            if sample_size and sample_size != "N/A":
                lines.append(f"- **Based on:** {sample_size} funded projects")
            lines.append("")

        # Cluster context (if available)
        if cluster_context:
            lines.append("### 🔬 Cluster Context\n")
            avg_partners = cluster_context.get("avg_partners")
            avg_countries = cluster_context.get("avg_countries")
            top_coordinators = cluster_context.get("top_coordinator_countries", [])

            if avg_partners:
                lines.append(f"- **Typical consortium size:** {avg_partners:.0f} partners")
            if avg_countries:
                lines.append(f"- **Typical country coverage:** {avg_countries:.0f} countries")
            if top_coordinators:
                lines.append(f"- **Top coordinator countries:** {', '.join(top_coordinators[:3])}")
            lines.append("")

        # Similar projects
        if similar_projects:
            lines.append("### 📋 Similar Funded Projects\n")
            for proj in similar_projects[:5]:
                acronym = proj.get("acronym", "N/A")
                title = proj.get("title", "")
                if title and len(title) > 50:
                    title = title[:50] + "..."
                budget = proj.get("budget", 0)
                partners = proj.get("partners")

                proj_line = f"- **{acronym}**: €{budget / 1_000_000:.1f}M"
                if partners:
                    proj_line += f" ({partners} partners)"
                if title:
                    proj_line += f"\n  *{title}*"
                lines.append(proj_line)
            lines.append("")

        # Recommendations
        if recommendations:
            lines.append("### 💡 Recommendations\n")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        # Actionable guidance
        lines.append(
            """---

🎯 **Next Steps:**
• Review the Work Programme for budget ceilings specific to your call
• Use the [Annotated Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf) for eligible cost rules
• Prepare partner budget sheets with the EU template format
• Check co-financing requirements for any non-100% funding rates
• Contact your finance department for institutional overhead rates

📚 **Useful Resources:**
• [Budget Guidance](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/how-to-participate/1)
• [Cost Categories Explained](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf)
• [CORDIS](https://cordis.europa.eu/) - View budgets of similar funded projects"""
        )

        return "\n".join(lines)

    def format_documents(self, documents: list[dict], query: str = "") -> str:
        """Format document search results with proper citations and source attribution."""
        if not documents:
            return "No documents found matching your search criteria."

        lines = [f"I found **{len(documents)} relevant document excerpts** for your query:\n"]

        # Group documents by source for better organization
        docs_by_source: dict[str, list[dict]] = {}
        for doc in documents:
            source = doc.get("source", doc.get("title", "Unknown Source"))
            if source not in docs_by_source:
                docs_by_source[source] = []
            docs_by_source[source].append(doc)

        # Format documents grouped by source
        doc_index = 1
        for source, source_docs in docs_by_source.items():
            # Add source header
            lines.append(f"### 📄 {source}\n")

            for doc in source_docs:
                lines.append(self._format_single_document(doc_index, doc))
                lines.append("")
                doc_index += 1

        # Add helpful footer with guidance
        lines.append("---\n")
        lines.append(self._get_document_guidance(query))

        return "\n".join(lines)

    def _format_single_document(self, index: int, doc: dict) -> str:
        """Format a single document excerpt with citation information."""
        content = doc.get("content", "")
        # source is already used in the group header (format_documents groups by source)
        section = doc.get("section", doc.get("section_title", ""))
        page_number = doc.get("page_number")
        document_type = doc.get("document_type", "")
        score = doc.get("score", 0)
        document_id = doc.get("document_id", "")
        chunk_id = doc.get("chunk_id", "")

        # Build citation reference
        citation_parts = []
        if section:
            citation_parts.append(f"Section: {section}")
        if page_number:
            citation_parts.append(f"Page {page_number}")
        if document_type:
            type_display = document_type.replace("_", " ").title()
            citation_parts.append(f"Type: {type_display}")

        citation = " | ".join(citation_parts) if citation_parts else ""

        # Clean and format the content
        content_formatted = self._format_document_content(content)

        # Build the formatted entry
        lines = [f"**{index}. Excerpt**"]

        if citation:
            lines.append(f"📑 *{citation}*")

        # Add relevance indicator for high-scoring results
        if score >= 0.8:
            lines.append("⭐ **Highly relevant**")
        elif score >= 0.6:
            lines.append("✅ **Relevant**")

        # Add the quoted content
        lines.append(f"\n> {content_formatted}")

        # Add reference ID for traceability
        if chunk_id or document_id:
            ref_id = chunk_id[:8] if chunk_id else document_id[:8]
            lines.append(f"\n*Ref: {ref_id}*")

        return "\n".join(lines)

    def _format_document_content(self, content: str) -> str:
        """Format document content for display with proper quoting."""
        if not content:
            return "*No content available*"

        # Clean the content
        content = content.strip()

        # Remove excessive whitespace
        content = re.sub(r"\s+", " ", content)

        # Truncate if too long, but try to end at a sentence
        max_length = 800
        if len(content) > max_length:
            truncated = content[:max_length]
            # Find last sentence boundary
            last_period = max(
                truncated.rfind(". "),
                truncated.rfind(".\n"),
                truncated.rfind("? "),
                truncated.rfind("! "),
            )
            if last_period > max_length * 0.6:
                content = truncated[: last_period + 1] + "..."
            else:
                # Find last word boundary
                last_space = truncated.rfind(" ")
                if last_space > max_length * 0.8:
                    content = truncated[:last_space] + "..."
                else:
                    content = truncated + "..."

        # Format for blockquote display (handle newlines)
        content = content.replace("\n", "\n> ")

        return content

    def _get_document_guidance(self, query: str = "") -> str:
        """Return helpful guidance footer for document searches."""
        return """💡 **About These Sources:**
• The excerpts above are from **official EU documents** including work programmes, regulations, and guidance materials
• Each excerpt includes a citation reference to help you locate the full text
• Always verify details against the latest official documents on the EU Portal

📚 **Official Resources:**
• [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) - Latest documents and calls
• [Horizon Europe Work Programmes](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents) - Annual work programmes
• [Programme Guides](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf) - Comprehensive programme guidance

🎯 **Next Steps:**
• Download the full work programme for your cluster of interest
• Check the EU Portal for the latest version of these documents
• Consult your National Contact Point (NCP) for interpretation guidance
• Use document references when preparing your proposal"""

    def get_query_aware_guidance(self, query: str, response_type: str = "general") -> str:
        """
        Generate context-aware actionable guidance based on query type.

        Args:
            query: The user's query
            response_type: Type of response (general, partner, budget, timeline, eligibility, comparison)

        Returns:
            Formatted guidance string with Next Steps section
        """
        query_lower = query.lower()

        # Detect query type from keywords
        if response_type == "general":
            if any(
                term in query_lower
                for term in ["partner", "consortium", "collaborat", "organization"]
            ):
                response_type = "partner"
            elif any(
                term in query_lower for term in ["budget", "cost", "fund", "money", "euro", "€"]
            ):
                response_type = "budget"
            elif any(
                term in query_lower
                for term in ["timeline", "duration", "schedule", "month", "year", "milestone"]
            ):
                response_type = "timeline"
            elif any(
                term in query_lower for term in ["eligib", "can we", "can i", "qualify", "require"]
            ):
                response_type = "eligibility"
            elif any(
                term in query_lower for term in ["compar", "versus", "vs", "differ", "between"]
            ):
                response_type = "comparison"

        guidance_map = {
            "partner": self._get_partner_guidance(),
            "budget": self._get_budget_guidance(),
            "timeline": self._get_timeline_guidance(),
            "eligibility": self._get_eligibility_guidance(),
            "comparison": self._get_comparison_guidance(),
            "general": self._get_general_guidance(),
        }

        return guidance_map.get(response_type, self._get_general_guidance())

    def _get_partner_guidance(self) -> str:
        """Guidance for partner/consortium queries."""
        return """
---

🎯 **Next Steps:**
• Use the [Partner Search Tool](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search) on the EU Portal
• Contact organizations directly through their project websites on CORDIS
• Attend EU funding events and brokerage sessions to meet potential partners
• Check LEAR (Legal Entity Appointed Representative) status for organizations you want to partner with
• Draft a Letter of Intent (LoI) template to send to potential partners"""

    def _get_budget_guidance(self) -> str:
        """Guidance for budget queries."""
        return """
---

🎯 **Next Steps:**
• Review the call Work Programme for budget ceilings and funding rates
• Use funded project budgets on CORDIS as benchmarks for your proposal
• Prepare a draft budget breakdown using the EU template (Personnel, Equipment, Travel, Other)
• Check the [Annotated Model Grant Agreement](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf) for eligible costs
• Consult your organization's finance department about co-financing requirements"""

    def _get_timeline_guidance(self) -> str:
        """Guidance for timeline queries."""
        return """
---

🎯 **Next Steps:**
• Align your project duration with similar funded projects (typically 36-48 months for RIA)
• Plan work packages with clear deliverables and milestones at Month 12, 24, 36
• Allow buffer time (10-15%) for unexpected delays
• Schedule consortium meetings and reporting periods according to EU guidelines
• Use project management templates from previous successful proposals"""

    def _get_eligibility_guidance(self) -> str:
        """Guidance for eligibility queries."""
        return """
---

🎯 **Next Steps:**
• Verify your organization type in the EU Participant Register
• Check the specific call conditions for any additional eligibility requirements
• Ensure your organization has a valid PIC (Participant Identification Code)
• Review consortium composition rules (minimum 3 partners from 3 countries for most calls)
• Contact your National Contact Point (NCP) for eligibility clarification"""

    def _get_comparison_guidance(self) -> str:
        """Guidance for comparison queries."""
        return """
---

🎯 **Next Steps:**
• Review the official programme guides for detailed information on each option
• Consider your organization's strengths and experience when choosing
• Talk to your National Contact Point (NCP) for personalized advice
• Look at success rates and funding amounts to make an informed decision
• Read success stories from similar organizations that have received funding"""

    def _get_general_guidance(self) -> str:
        """General guidance for EU funding queries."""
        return """
---

🎯 **Next Steps:**
• Check the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) for the latest opportunities
• Contact your National Contact Point (NCP) for personalized guidance
• Register your organization in the Participant Register if not already done
• Download relevant work programmes and call documents
• Consider attending EU funding information days and webinars"""


# Singleton instance
_formatter = None


def get_formatter() -> V3ResponseFormatter:
    """Get the singleton formatter instance."""
    global _formatter
    if _formatter is None:
        _formatter = V3ResponseFormatter()
    return _formatter

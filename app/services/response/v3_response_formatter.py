"""
V3 Response Formatter

Formats tool results into beautifully structured responses for the user.
This is a post-processor that takes raw tool results and formats them consistently.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class V3ResponseFormatter:
    """Formats V3 agent responses with consistent styling."""

    # Type icons
    TYPE_ICONS = {
        'RIA': '🔬',
        'IA': '🚀',
        'CSA': '🤝',
        'COFUND': '💱',
        'ERC': '🎓',
        'MSCA': '👨‍🔬',
        'default': '📄'
    }

    # Status icons
    STATUS_ICONS = {
        'open': '🟢',
        'upcoming': '🟡',
        'closed': '🔴',
        'default': '📊'
    }

    def format_funding_calls(self, calls: List[Dict], query: str = "") -> str:
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

    def _format_single_call(self, index: int, call: Dict) -> str:
        """Format a single funding call."""
        title = call.get('title', 'Untitled Call') or 'Untitled Call'
        call_id = call.get('call_id') or call.get('topic_code') or call.get('topic_id') or call.get('identifier', '')
        call_type = call.get('type') or call.get('action_type') or ''
        status = (call.get('status') or 'open').lower()
        deadline = call.get('deadline') or call.get('application_deadline') or ''
        cluster = call.get('cluster') or call.get('programme') or call.get('work_programme') or ''
        budget = call.get('budget') or call.get('estimated_budget') or ''
        scope = call.get('scope') or call.get('description') or call.get('objective') or call.get('expected_outcome') or ''
        url = call.get('url') or call.get('portal_url') or ''

        # Get icons - handle None/empty call_type
        type_icon = self.TYPE_ICONS.get(call_type.upper() if call_type else '', self.TYPE_ICONS['default'])
        status_icon = self.STATUS_ICONS.get(status, self.STATUS_ICONS['default'])

        # Format deadline
        deadline_str = self._format_deadline(deadline)

        # Format budget
        budget_str = self._format_budget(budget)

        # Build the formatted entry
        lines = [f"**{index}. {title}**"]

        if call_id:
            lines.append(f"📋 **Call ID:** {call_id}")

        if call_type:
            lines.append(f"{type_icon} **Type:** {call_type}")

        lines.append(f"{status_icon} **Status:** {status.capitalize()}")

        if deadline_str:
            lines.append(f"⏰ **Deadline:** {deadline_str}")

        if cluster:
            lines.append(f"🏛️ **Programme:** Cluster {cluster}" if cluster.startswith('CL') else f"🏛️ **Programme:** {cluster}")

        if budget_str:
            lines.append(f"💰 **Budget:** {budget_str}")

        if scope:
            # Truncate scope to reasonable length
            scope_text = scope[:300] + "..." if len(scope) > 300 else scope
            lines.append(f"\n**Scope:** {scope_text}")

        # Add apply link - use provided URL or generate from call_id
        if url:
            lines.append(f"\n🔗 **Apply:** {url}")
        elif call_id and call_id.startswith('HORIZON'):
            portal_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{call_id}"
            lines.append(f"\n🔗 **Apply:** {portal_url}")

        lines.append("\n---")

        return "\n".join(lines)

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
                        dt = datetime.strptime(deadline.split('T')[0], fmt.split('T')[0])
                        return dt.strftime("%d %b %Y")
                    except ValueError:
                        continue
                return deadline  # Return as-is if parsing fails
            except:
                return deadline

        return str(deadline)

    def _format_budget(self, budget: Any) -> str:
        """Format budget to readable string."""
        if not budget:
            return ""

        if isinstance(budget, (int, float)):
            if budget >= 1_000_000:
                return f"EUR {budget/1_000_000:.2f} million"
            elif budget >= 1_000:
                return f"EUR {budget/1_000:.0f}K"
            else:
                return f"EUR {budget:,.0f}"

        if isinstance(budget, str):
            # Clean up existing string
            budget = budget.strip()
            if budget.lower().startswith('eur'):
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

    def format_projects(self, projects: List[Dict], query: str = "") -> str:
        """Format a list of CORDIS projects."""
        if not projects:
            return "No projects found matching your search criteria."

        lines = [f"I found **{len(projects)} funded projects** related to your query:\n"]

        for i, project in enumerate(projects, 1):
            lines.append(self._format_single_project(i, project))
            lines.append("")

        return "\n".join(lines)

    def _format_single_project(self, index: int, project: Dict) -> str:
        """Format a single project."""
        title = project.get('title', project.get('acronym', 'Untitled Project'))
        acronym = project.get('acronym', '')
        project_id = project.get('id', project.get('project_id', ''))
        programme = project.get('programme', project.get('frameworkProgramme', ''))
        status = project.get('status', '')
        start_date = project.get('startDate', project.get('start_date', ''))
        end_date = project.get('endDate', project.get('end_date', ''))
        total_cost = project.get('totalCost', project.get('total_cost', ''))
        eu_contribution = project.get('ecMaxContribution', project.get('eu_contribution', ''))
        objective = project.get('objective', project.get('description', ''))
        coordinator = project.get('coordinator', '')

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
            status_icon = '🟢' if status.lower() == 'ongoing' else '✅' if status.lower() == 'closed' else '📊'
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

        # CORDIS link
        if project_id:
            cordis_url = f"https://cordis.europa.eu/project/id/{project_id}"
            lines.append(f"\n🔗 **Details:** {cordis_url}")

        lines.append("\n---")

        return "\n".join(lines)

    def format_from_tool_results(self, tool_results: Dict[str, Any], query: str = "") -> Optional[str]:
        """
        Detect the type of results and format appropriately.
        Returns None if no formattable results found.
        """
        for tool_name, result in tool_results.items():
            if not isinstance(result, dict):
                continue

            # Funding calls
            if 'calls' in result and isinstance(result['calls'], list):
                calls = result['calls']
                if calls:
                    return self.format_funding_calls(calls, query)

            # Projects
            if 'projects' in result and isinstance(result['projects'], list):
                projects = result['projects']
                if projects:
                    return self.format_projects(projects, query)

        return None


# Singleton instance
_formatter = None


def get_formatter() -> V3ResponseFormatter:
    """Get the singleton formatter instance."""
    global _formatter
    if _formatter is None:
        _formatter = V3ResponseFormatter()
    return _formatter

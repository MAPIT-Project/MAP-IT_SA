"""
Conclusion builder methods for partner comparisons and network diversity analysis.
Extracted from tool_aware_agent.py for maintainability.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class ConclusionBuildersMixin:
    """Mixin providing conclusion builder methods for partner analysis responses."""

    def _build_partner_comparison_conclusion(
        self, query: str, context: str, org_names: list[str], pattern_type: str
    ) -> str:
        """Build a structured comparison/recommendation based on partner context."""

        # Extract funding data from context
        # Format: **Total Funding**: €75,951,578 or Total Funding: €75,951,578
        funding_data = {}
        for org in org_names[:5]:
            # Look for funding info near the org name
            org_escaped = re.escape(org)
            # Match patterns like: **Total Funding**: €75,951,578 or Total Funding: €75,951,578
            funding_match = re.search(
                rf"{org_escaped}.*?\*?\*?Total Funding\*?\*?[:\s]*€?([\d,]+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if funding_match:
                funding_str = funding_match.group(1).replace(",", "")
                try:
                    funding_data[org] = int(funding_str)
                except ValueError:
                    pass

        # Extract project counts
        # Format: **Relevant Projects**: 93 or Relevant Projects: 93
        project_data = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            project_match = re.search(
                rf"{org_escaped}.*?\*?\*?Relevant Projects\*?\*?[:\s]*(\d+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if project_match:
                try:
                    project_data[org] = int(project_match.group(1))
                except ValueError:
                    pass

        # Extract coordination counts
        # Format: (coordinated **14** projects) or coordinated 14 projects
        coordination_data = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            coord_match = re.search(
                rf"{org_escaped}.*?coordinated\s*\**(\d+)\**",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if coord_match:
                try:
                    coordination_data[org] = int(coord_match.group(1))
                except ValueError:
                    pass

        # Extract organization types
        # Format: **Organization Type**: REC (Research Center) or Organization Type: REC
        org_types = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            type_match = re.search(
                rf"{org_escaped}.*?\*?\*?Organization Type\*?\*?[:\s]*([A-Z]+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if type_match:
                org_types[org] = type_match.group(1)

        # Extract countries
        # Format: **ORG NAME** (DE) or ORG NAME (DE)
        countries = {}
        for org in org_names[:5]:
            org_escaped = re.escape(org)
            # Match: **ORG NAME** (DE) or ORG NAME (DE)
            country_match = re.search(rf"{org_escaped}\*?\*?\s*\(([A-Z]{{2}})\)", context)
            if country_match:
                countries[org] = country_match.group(1)

        # Build response based on pattern type
        top_3 = org_names[:3]

        if pattern_type == "funding comparison" or "funding" in query.lower():
            # Sort by funding and present
            sorted_by_funding = sorted(
                [(org, funding_data.get(org, 0)) for org in top_3],
                key=lambda x: x[1],
                reverse=True,
            )
            result = "## Partner Funding Comparison\n\n"
            result += "Based on the partner search results, here's the funding comparison:\n\n"
            for i, (org, funding) in enumerate(sorted_by_funding, 1):
                country = countries.get(org, "")
                org_type = org_types.get(org, "")
                result += f"### {i}. {org}"
                if country:
                    result += f" ({country})"
                result += "\n"
                result += f"- **Total EU Funding**: €{funding:,}\n"
                result += f"- **Organization Type**: {org_type}\n"
                projects = project_data.get(org, "N/A")
                result += f"- **Relevant Projects**: {projects}\n\n"

            if sorted_by_funding:
                winner = sorted_by_funding[0]
                result += (
                    f"\n**Highest Funded**: {winner[0]} with €{winner[1]:,} in total EU funding.\n"
                )

        elif pattern_type == "coordinator recommendation":
            # Sort by coordination experience
            sorted_by_coord = sorted(
                [(org, coordination_data.get(org, 0)) for org in top_3],
                key=lambda x: x[1],
                reverse=True,
            )
            result = "## Coordinator Recommendation\n\n"
            result += "Based on coordination experience from the partner search:\n\n"
            for i, (org, coord_count) in enumerate(sorted_by_coord, 1):
                country = countries.get(org, "")
                org_type = org_types.get(org, "")
                funding = funding_data.get(org, 0)
                result += f"### {i}. {org}"
                if country:
                    result += f" ({country})"
                result += "\n"
                result += f"- **Projects Coordinated**: {coord_count}\n"
                result += f"- **Organization Type**: {org_type}\n"
                result += f"- **Total Funding**: €{funding:,}\n\n"

            if sorted_by_coord and sorted_by_coord[0][1] > 0:
                winner = sorted_by_coord[0]
                result += f"\n**Recommended Coordinator**: {winner[0]} has the most coordination experience with {winner[1]} projects coordinated.\n"
            result += "\n**Next Steps:**\n"
            result += "- Contact the recommended organization via CORDIS or their website\n"
            result += "- Verify their availability and interest in your project topic\n"
            result += "- Discuss consortium composition and roles\n"

        elif pattern_type == "comparison request" or pattern_type == "comparing top organizations":
            result = "## Partner Comparison\n\n"
            result += f"Comparing the top {len(top_3)} organizations from the partner search:\n\n"
            result += "| Organization | Country | Type | Projects | Coordinated | Total Funding |\n"
            result += "|-------------|---------|------|----------|-------------|---------------|\n"
            for org in top_3:
                country = countries.get(org, "-")
                org_type = org_types.get(org, "-")
                projects = project_data.get(org, "-")
                coord = coordination_data.get(org, "-")
                funding = funding_data.get(org, 0)
                funding_str = f"€{funding:,}" if funding else "-"
                # Truncate long org names for table
                short_name = org[:40] + "..." if len(org) > 40 else org
                result += f"| {short_name} | {country} | {org_type} | {projects} | {coord} | {funding_str} |\n"

            result += "\n### Key Insights:\n"
            # Funding leader
            if funding_data:
                funding_leader = max(funding_data.items(), key=lambda x: x[1])
                result += f"- **Highest Funding**: {funding_leader[0]} (€{funding_leader[1]:,})\n"
            # Coordination leader
            if coordination_data:
                coord_leader = max(coordination_data.items(), key=lambda x: x[1])
                result += f"- **Most Coordination Experience**: {coord_leader[0]} ({coord_leader[1]} projects)\n"
            # Project leader
            if project_data:
                project_leader = max(project_data.items(), key=lambda x: x[1])
                result += f"- **Most Relevant Projects**: {project_leader[0]} ({project_leader[1]} projects)\n"

        else:
            # Generic comparison
            result = "## Partner Analysis\n\n"
            result += (
                f"Based on the partner search, here are the top {len(top_3)} organizations:\n\n"
            )
            for i, org in enumerate(top_3, 1):
                country = countries.get(org, "")
                org_type = org_types.get(org, "")
                projects = project_data.get(org, "N/A")
                coord = coordination_data.get(org, "N/A")
                funding = funding_data.get(org, 0)
                result += f"### {i}. {org}"
                if country:
                    result += f" ({country})"
                result += "\n"
                result += f"- **Organization Type**: {org_type}\n"
                result += f"- **Relevant Projects**: {projects}\n"
                result += f"- **Coordinated Projects**: {coord}\n"
                result += f"- **Total Funding**: €{funding:,}\n\n"

        result += "\n**Next Steps:**\n"
        result += "- Search CORDIS for detailed project information\n"
        result += "- Use the EU Partner Search tool to contact organizations\n"
        result += "- Verify current availability and interest\n"

        return result

    def _build_network_diversity_conclusion(self, context: str, org_names: list[str]) -> str:
        """Build a network diversity analysis from partner context.

        Uses coordination count as a proxy for network diversity:
        Organizations that coordinate more projects have collaborated with more partners.
        """

        # Extract coordination counts for top organizations
        coordination_data = {}
        project_data = {}
        countries = {}
        org_types = {}

        for org in org_names[:5]:
            org_escaped = re.escape(org)

            # Coordination count
            coord_match = re.search(
                rf"{org_escaped}.*?coordinated\s*\**(\d+)\**",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if coord_match:
                try:
                    coordination_data[org] = int(coord_match.group(1))
                except ValueError:
                    pass

            # Project count
            project_match = re.search(
                rf"{org_escaped}.*?\*?\*?Relevant Projects\*?\*?[:\s]*(\d+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if project_match:
                try:
                    project_data[org] = int(project_match.group(1))
                except ValueError:
                    pass

            # Country
            country_match = re.search(rf"{org_escaped}\*?\*?\s*\(([A-Z]{{2}})\)", context)
            if country_match:
                countries[org] = country_match.group(1)

            # Org type
            type_match = re.search(
                rf"{org_escaped}.*?\*?\*?Organization Type\*?\*?[:\s]*([A-Z]+)",
                context,
                re.IGNORECASE | re.DOTALL,
            )
            if type_match:
                org_types[org] = type_match.group(1)

        # Sort by coordination count (more coordinated = more diverse network)
        sorted_orgs = sorted(
            [
                (org, coordination_data.get(org, 0), project_data.get(org, 0))
                for org in org_names[:5]
            ],
            key=lambda x: (x[1], x[2]),  # Sort by coord count, then project count
            reverse=True,
        )

        result = "## Collaboration Network Diversity Analysis\n\n"
        result += "Organizations that coordinate more projects have built more diverse collaboration networks, "
        result += "as coordinators must assemble consortia from multiple countries and organization types.\n\n"

        result += "### Network Diversity Ranking (by coordination experience)\n\n"
        result += "| Organization | Country | Type | Projects Coordinated | Total Projects | Network Score |\n"
        result += "|--------------|---------|------|---------------------|----------------|---------------|\n"

        for org, coord_count, proj_count in sorted_orgs[:5]:
            country = countries.get(org, "-")
            org_type = org_types.get(org, "-")
            # Network score: weighted combination of coordination and participation
            network_score = coord_count * 3 + proj_count  # Coordination weighted 3x
            short_name = org[:40] + "..." if len(org) > 40 else org
            result += f"| {short_name} | {country} | {org_type} | {coord_count} | {proj_count} | {network_score} |\n"

        if sorted_orgs:
            winner = sorted_orgs[0]
            result += "\n### Most Diverse Collaboration Network\n\n"
            result += f"**{winner[0]}** has the most diverse collaboration network based on:\n"
            result += f"- **{winner[1]} projects coordinated** - Each coordinated project requires building a consortium\n"
            result += (
                f"- **{winner[2]} total projects** - Broad participation across many consortia\n"
            )
            result += f"- **Country**: {countries.get(winner[0], 'N/A')}\n"
            result += f"- **Organization Type**: {org_types.get(winner[0], 'N/A')}\n"

        result += "\n**Note**: Actual network diversity can be verified via CORDIS by examining "
        result += "consortium compositions of coordinated projects.\n"

        result += "\n**Next Steps:**\n"
        result += "- Search CORDIS for the organization's project list\n"
        result += "- Review consortium compositions to understand collaboration patterns\n"
        result += "- Contact organizations for specific collaboration opportunities\n"

        return result

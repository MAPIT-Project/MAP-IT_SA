"""
Timeline Generator Tool for Horizon Europe Proposals.

Generates realistic project timelines with work packages, deliverables,
and milestones based on best practices from funded projects.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TimelineGeneratorTool:
    """Generate project timelines based on Horizon Europe best practices."""

    # Typical WP structure by action type
    WP_TEMPLATES = {
        'RIA': [
            {'title': 'Project Management', 'effort_pct': 0.08, 'full_duration': True},
            {'title': 'Requirements & State of the Art', 'effort_pct': 0.12, 'months': (1, 12)},
            {'title': 'Core Research & Development', 'effort_pct': 0.35, 'months': (6, -6)},
            {'title': 'Integration & Validation', 'effort_pct': 0.20, 'months': (12, -3)},
            {'title': 'Dissemination & Exploitation', 'effort_pct': 0.15, 'full_duration': True},
            {'title': 'Ethics & Data Management', 'effort_pct': 0.10, 'full_duration': True},
        ],
        'IA': [
            {'title': 'Project Management', 'effort_pct': 0.08, 'full_duration': True},
            {'title': 'Market Analysis & Requirements', 'effort_pct': 0.10, 'months': (1, 9)},
            {'title': 'Technology Development', 'effort_pct': 0.30, 'months': (3, -9)},
            {'title': 'Pilot Deployment', 'effort_pct': 0.25, 'months': (12, -6)},
            {'title': 'Business Model & Scale-up', 'effort_pct': 0.12, 'months': (18, -3)},
            {'title': 'Dissemination & Exploitation', 'effort_pct': 0.15, 'full_duration': True},
        ],
        'CSA': [
            {'title': 'Project Management', 'effort_pct': 0.10, 'full_duration': True},
            {'title': 'Stakeholder Engagement', 'effort_pct': 0.25, 'full_duration': True},
            {'title': 'Analysis & Best Practices', 'effort_pct': 0.25, 'months': (1, 18)},
            {'title': 'Policy Recommendations', 'effort_pct': 0.20, 'months': (12, -3)},
            {'title': 'Communication & Outreach', 'effort_pct': 0.20, 'full_duration': True},
        ],
        'ERC': [
            {'title': 'Research Direction 1', 'effort_pct': 0.35, 'full_duration': True},
            {'title': 'Research Direction 2', 'effort_pct': 0.30, 'full_duration': True},
            {'title': 'Cross-cutting Activities', 'effort_pct': 0.20, 'full_duration': True},
            {'title': 'Scientific Coordination', 'effort_pct': 0.15, 'full_duration': True},
        ],
    }

    # Deliverable types
    DELIVERABLE_TYPES = {
        'R': 'Document, report',
        'DEM': 'Demonstrator, pilot, prototype',
        'DEC': 'Websites, patents, press releases',
        'DATA': 'Data sets, microdata, etc.',
        'DMP': 'Data management plan',
        'ETHICS': 'Ethics deliverables',
        'OTHER': 'Software, technical diagram, etc.',
    }

    # Dissemination levels
    DISSEMINATION_LEVELS = {
        'PU': 'Public',
        'SEN': 'Sensitive',
        'CO': 'Confidential',
    }

    def generate_timeline(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: int,
        project_title: str = "Project",
        custom_wps: Optional[List[Dict]] = None,
        start_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a project timeline with work packages, deliverables, and milestones.

        Args:
            action_type: RIA, IA, CSA, ERC
            duration_months: Total project duration
            num_partners: Number of partners
            total_person_months: Total effort in PMs
            project_title: Project title for naming
            custom_wps: Optional custom WP definitions
            start_date: Optional start date (YYYY-MM-DD)

        Returns:
            Complete timeline with WPs, deliverables, milestones, Gantt data
        """
        action_type = action_type.upper()
        if action_type.startswith('ERC'):
            action_type = 'ERC'

        templates = custom_wps or self.WP_TEMPLATES.get(action_type, self.WP_TEMPLATES['RIA'])

        work_packages = []
        all_deliverables = []
        all_milestones = []
        deliverable_counter = 1
        milestone_counter = 1

        for i, template in enumerate(templates, 1):
            # Calculate WP timing
            if template.get('full_duration'):
                start_month = 1
                end_month = duration_months
            else:
                months = template.get('months', (1, duration_months))
                start_month = months[0]
                # Handle negative values (months from end)
                end_month = duration_months + months[1] if months[1] < 0 else months[1]
                end_month = min(end_month, duration_months)

            # Calculate effort
            effort = int(total_person_months * template['effort_pct'])

            # Generate deliverables
            wp_deliverables, deliverable_counter = self._generate_deliverables(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month,
                action_type=action_type,
                counter_start=deliverable_counter
            )

            # Generate milestones
            wp_milestones, milestone_counter = self._generate_milestones(
                wp_num=i,
                wp_title=template['title'],
                start_month=start_month,
                end_month=end_month,
                counter_start=milestone_counter
            )

            wp = {
                'number': i,
                'title': template['title'],
                'lead': f'Partner {((i - 1) % num_partners) + 1}',
                'start_month': start_month,
                'end_month': end_month,
                'duration_months': end_month - start_month + 1,
                'effort_pms': effort,
                'effort_percentage': round(template['effort_pct'] * 100, 1),
                'deliverables': wp_deliverables,
                'milestones': wp_milestones,
            }

            work_packages.append(wp)
            all_deliverables.extend(wp_deliverables)
            all_milestones.extend(wp_milestones)

        # Sort deliverables and milestones by due date
        all_deliverables.sort(key=lambda d: (d['due_month'], d['wp']))
        all_milestones.sort(key=lambda m: m['due_month'])

        # Deduplicate milestones (same title at same month)
        seen_milestones = set()
        unique_milestones = []
        for m in all_milestones:
            key = (m['title'], m['due_month'])
            if key not in seen_milestones:
                seen_milestones.add(key)
                unique_milestones.append(m)
        all_milestones = unique_milestones

        # Renumber milestones sequentially
        for i, m in enumerate(all_milestones, 1):
            m['id'] = f'MS{i}'

        # Renumber deliverables sequentially for cleaner output
        # Keep WP association but use sequential numbering
        for i, d in enumerate(all_deliverables, 1):
            d['seq_id'] = f'D{i}'  # Add sequential ID for easy reference

        # Generate Gantt chart data
        gantt_data = self._generate_gantt_data(work_packages, duration_months)

        # Calculate effort distribution
        effort_distribution = {wp['title']: wp['effort_pms'] for wp in work_packages}

        return {
            "success": True,
            "tool_name": "generate_timeline",
            "project_title": project_title,
            "parameters": {
                "action_type": action_type,
                "duration_months": duration_months,
                "num_partners": num_partners,
                "total_person_months": total_person_months,
                "start_date": start_date
            },
            "work_packages": work_packages,
            "deliverables": all_deliverables,
            "milestones": all_milestones,
            "gantt_data": gantt_data,
            "summary": {
                "total_wps": len(work_packages),
                "total_deliverables": len(all_deliverables),
                "total_milestones": len(all_milestones),
                "effort_distribution": effort_distribution,
                "deliverables_by_type": self._count_by_type(all_deliverables),
            },
            "recommendations": self._generate_timeline_recommendations(
                work_packages, duration_months, action_type, num_partners
            ),
            "timestamp": datetime.now().isoformat()
        }

    def _generate_deliverables(
        self,
        wp_num: int,
        wp_title: str,
        start_month: int,
        end_month: int,
        action_type: str,
        counter_start: int
    ) -> tuple[List[Dict], int]:
        """Generate typical deliverables for a WP."""
        deliverables = []
        duration = end_month - start_month
        counter = counter_start

        # Deliverable templates by WP type
        wp_type = self._classify_wp_type(wp_title)

        deliverable_templates = {
            'management': [
                {'title': 'Project Management Report', 'type': 'R', 'level': 'CO', 'timing': 'periodic'},
                {'title': 'Quality Assurance Plan', 'type': 'R', 'level': 'CO', 'timing': 'early'},
            ],
            'requirements': [
                {'title': 'Requirements Specification', 'type': 'R', 'level': 'PU', 'timing': 'early'},
                {'title': 'State of the Art Report', 'type': 'R', 'level': 'PU', 'timing': 'early'},
            ],
            'research': [
                {'title': 'Technical Report', 'type': 'R', 'level': 'PU', 'timing': 'mid'},
                {'title': 'Prototype', 'type': 'DEM', 'level': 'CO', 'timing': 'late'},
            ],
            'development': [
                {'title': 'Software Release', 'type': 'OTHER', 'level': 'PU', 'timing': 'mid'},
                {'title': 'Technical Documentation', 'type': 'R', 'level': 'PU', 'timing': 'late'},
            ],
            'validation': [
                {'title': 'Validation Report', 'type': 'R', 'level': 'PU', 'timing': 'late'},
                {'title': 'Validated Prototype', 'type': 'DEM', 'level': 'CO', 'timing': 'late'},
            ],
            'pilot': [
                {'title': 'Pilot Setup Report', 'type': 'R', 'level': 'CO', 'timing': 'mid'},
                {'title': 'Pilot Evaluation Report', 'type': 'R', 'level': 'PU', 'timing': 'late'},
            ],
            'dissemination': [
                {'title': 'Dissemination and Exploitation Plan', 'type': 'R', 'level': 'PU', 'timing': 'early'},
                {'title': 'Final Dissemination Report', 'type': 'R', 'level': 'PU', 'timing': 'final'},
            ],
            'communication': [
                {'title': 'Project Website', 'type': 'DEC', 'level': 'PU', 'timing': 'early'},
                {'title': 'Communication Materials', 'type': 'DEC', 'level': 'PU', 'timing': 'mid'},
            ],
            'ethics': [
                {'title': 'Ethics Requirements Report', 'type': 'ETHICS', 'level': 'CO', 'timing': 'early'},
                {'title': 'Data Management Plan', 'type': 'DMP', 'level': 'PU', 'timing': 'early'},
            ],
            'default': [
                {'title': 'Report', 'type': 'R', 'level': 'PU', 'timing': 'late'},
            ],
        }

        templates = deliverable_templates.get(wp_type, deliverable_templates['default'])

        for template in templates:
            # Calculate due month based on timing
            if template['timing'] == 'early':
                due_month = start_month + max(duration // 4, 3)
            elif template['timing'] == 'mid':
                due_month = start_month + duration // 2
            elif template['timing'] == 'late':
                due_month = end_month - max(duration // 6, 2)
            elif template['timing'] == 'final':
                due_month = end_month
            elif template['timing'] == 'periodic':
                # Add periodic reports (every 12 months if long enough)
                for period in range(12, duration + 1, 12):
                    deliverables.append({
                        'id': f'D{wp_num}.{counter}',
                        'title': f"{template['title']} (M{start_month + period})",
                        'wp': wp_num,
                        'type': template['type'],
                        'type_description': self.DELIVERABLE_TYPES.get(template['type'], 'Report'),
                        'dissemination_level': template['level'],
                        'due_month': start_month + period,
                    })
                    counter += 1
                continue
            else:
                due_month = end_month

            due_month = min(due_month, end_month)

            deliverables.append({
                'id': f'D{wp_num}.{counter}',
                'title': template['title'],
                'wp': wp_num,
                'type': template['type'],
                'type_description': self.DELIVERABLE_TYPES.get(template['type'], 'Report'),
                'dissemination_level': template['level'],
                'due_month': due_month,
            })
            counter += 1

        return deliverables, counter

    def _generate_milestones(
        self,
        wp_num: int,
        wp_title: str,
        start_month: int,
        end_month: int,
        counter_start: int
    ) -> tuple[List[Dict], int]:
        """Generate milestones for a WP."""
        milestones = []
        duration = end_month - start_month
        counter = counter_start

        wp_type = self._classify_wp_type(wp_title)

        milestone_templates = {
            'management': [
                {'title': 'Project Kickoff', 'timing': 'start'},
            ],
            'requirements': [
                {'title': 'Requirements Frozen', 'timing': 'end'},
            ],
            'research': [
                {'title': 'Research Phase Completed', 'timing': 'end'},
            ],
            'development': [
                {'title': 'Development Phase Completed', 'timing': 'end'},
            ],
            'validation': [
                {'title': 'Validation Completed', 'timing': 'end'},
            ],
            'pilot': [
                {'title': 'Pilot Operational', 'timing': 'mid'},
                {'title': 'Pilot Evaluation Completed', 'timing': 'end'},
            ],
            'dissemination': [],  # Usually no specific milestones
            'default': [],
        }

        templates = milestone_templates.get(wp_type, milestone_templates['default'])

        for template in templates:
            if template['timing'] == 'start':
                due_month = start_month
            elif template['timing'] == 'mid':
                due_month = start_month + duration // 2
            elif template['timing'] == 'end':
                due_month = end_month
            else:
                due_month = end_month

            milestones.append({
                'id': f'MS{counter}',
                'title': template['title'],
                'related_wp': wp_num,
                'due_month': due_month,
                'verification_means': 'Deliverable submission / Review meeting',
            })
            counter += 1

        return milestones, counter

    def _classify_wp_type(self, wp_title: str) -> str:
        """Classify WP type based on title.

        Order matters - more specific patterns checked first.
        """
        title_lower = wp_title.lower()

        # Check specific patterns first (before generic 'management')
        if 'ethics' in title_lower or 'data management' in title_lower:
            return 'ethics'
        elif 'project management' in title_lower or 'coordination' in title_lower:
            return 'management'
        elif 'requirement' in title_lower or 'state of the art' in title_lower:
            return 'requirements'
        elif 'validation' in title_lower or 'integration' in title_lower or 'testing' in title_lower:
            return 'validation'
        elif 'pilot' in title_lower or 'deployment' in title_lower or 'demonstration' in title_lower:
            return 'pilot'
        elif 'research' in title_lower or 'development' in title_lower or 'core' in title_lower:
            return 'research'
        elif 'dissemination' in title_lower or 'exploitation' in title_lower:
            return 'dissemination'
        elif 'communication' in title_lower or 'outreach' in title_lower or 'stakeholder' in title_lower:
            return 'communication'
        elif 'market' in title_lower or 'business' in title_lower or 'scale' in title_lower:
            return 'pilot'  # Business/market activities treated like pilot
        else:
            return 'default'

    def _generate_gantt_data(self, work_packages: List[Dict], duration: int) -> Dict[str, Any]:
        """Generate Gantt chart data for visualization."""
        gantt_rows = []

        for wp in work_packages:
            # Create a row for each WP
            row = {
                'id': f'WP{wp["number"]}',
                'label': f'WP{wp["number"]}: {wp["title"]}',
                'start_month': wp['start_month'],
                'end_month': wp['end_month'],
                'effort': wp['effort_pms'],
                # Create a visual bar representation
                'bar': self._create_text_bar(wp['start_month'], wp['end_month'], duration)
            }
            gantt_rows.append(row)

        return {
            'rows': gantt_rows,
            'total_months': duration,
            'phases': self._identify_phases(work_packages, duration)
        }

    def _create_text_bar(self, start: int, end: int, total: int) -> str:
        """Create a simple text representation of a Gantt bar."""
        bar = []
        for m in range(1, total + 1):
            if start <= m <= end:
                bar.append('█')
            else:
                bar.append('░')
        return ''.join(bar)

    def _identify_phases(self, work_packages: List[Dict], duration: int) -> List[Dict]:
        """Identify project phases based on WP overlap patterns."""
        phases = []

        # Simple phase detection based on typical project structure
        if duration >= 36:
            phases = [
                {'name': 'Phase 1: Foundation', 'start': 1, 'end': 12},
                {'name': 'Phase 2: Core Development', 'start': 7, 'end': duration - 12},
                {'name': 'Phase 3: Consolidation', 'start': duration - 12, 'end': duration},
            ]
        elif duration >= 24:
            phases = [
                {'name': 'Phase 1: Setup & Analysis', 'start': 1, 'end': 9},
                {'name': 'Phase 2: Implementation', 'start': 6, 'end': duration - 6},
                {'name': 'Phase 3: Finalization', 'start': duration - 9, 'end': duration},
            ]
        else:
            phases = [
                {'name': 'Phase 1: Execution', 'start': 1, 'end': duration},
            ]

        return phases

    def _count_by_type(self, deliverables: List[Dict]) -> Dict[str, int]:
        """Count deliverables by type."""
        counts = {}
        for d in deliverables:
            d_type = d.get('type', 'OTHER')
            counts[d_type] = counts.get(d_type, 0) + 1
        return counts

    def _generate_timeline_recommendations(
        self,
        work_packages: List[Dict],
        duration: int,
        action_type: str,
        num_partners: int
    ) -> List[str]:
        """Generate recommendations for the timeline."""
        recommendations = []

        # Check WP count
        wp_count = len(work_packages)
        if wp_count < 4:
            recommendations.append(
                f"Consider adding more work packages (currently {wp_count}). "
                "Typical projects have 5-7 WPs for better task organization"
            )
        elif wp_count > 10:
            recommendations.append(
                f"High number of work packages ({wp_count}). "
                "Consider consolidating for easier management"
            )

        # Check duration alignment
        typical_durations = {'RIA': (36, 48), 'IA': (36, 48), 'CSA': (24, 36), 'ERC': (60, 60)}
        typical = typical_durations.get(action_type, (36, 48))

        if duration < typical[0]:
            recommendations.append(
                f"Duration ({duration} months) is shorter than typical for {action_type} "
                f"({typical[0]}-{typical[1]} months). Ensure scope is achievable"
            )
        elif duration > typical[1]:
            recommendations.append(
                f"Duration ({duration} months) exceeds typical for {action_type}. "
                "Strong justification may be needed"
            )

        # Check for WP overlap
        research_wps = [wp for wp in work_packages if 'research' in wp['title'].lower() or 'development' in wp['title'].lower()]
        if research_wps:
            avg_start = sum(wp['start_month'] for wp in research_wps) / len(research_wps)
            if avg_start < 3:
                recommendations.append(
                    "Research/development activities start very early. "
                    "Consider allowing time for requirements analysis first"
                )

        # Check deliverable distribution
        total_dels = sum(len(wp['deliverables']) for wp in work_packages)
        dels_per_year = total_dels / (duration / 12)
        if dels_per_year > 15:
            recommendations.append(
                f"High deliverable density ({dels_per_year:.1f}/year). "
                "Consider consolidating or spacing deliverables"
            )
        elif dels_per_year < 5:
            recommendations.append(
                f"Low deliverable density ({dels_per_year:.1f}/year). "
                "Consider adding intermediate deliverables for progress tracking"
            )

        # Partner involvement
        if num_partners > wp_count:
            recommendations.append(
                f"More partners ({num_partners}) than WPs ({wp_count}). "
                "Ensure all partners have meaningful roles in WP leadership"
            )

        return recommendations


# Async wrapper for tool orchestrator compatibility
async def generate_timeline_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute timeline generator tool.

    This tool generates project timelines with work packages, deliverables,
    and milestones for Horizon Europe proposals.
    """
    tool = TimelineGeneratorTool()

    return tool.generate_timeline(
        action_type=params.get('action_type', 'RIA'),
        duration_months=params.get('duration_months', 36),
        num_partners=params.get('num_partners', 8),
        total_person_months=params.get('total_person_months', 300),
        project_title=params.get('project_title', 'Project'),
        custom_wps=params.get('custom_wps'),
        start_date=params.get('start_date')
    )

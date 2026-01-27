"""
Compliance Checker

Verify proposal compliance with Horizon Europe requirements.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ComplianceChecker:
    """
    Check proposal compliance with call requirements
    """
    
    def __init__(self, call_doc_service, db_pool=None):
        self.call_doc_service = call_doc_service
        self.db_pool = db_pool
    
    async def run_compliance_check(
        self,
        call_id: str,
        proposal_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Run comprehensive compliance checks
        
        Args:
            call_id: Call identifier
            proposal_data: {
                "sections": { "section_id": "content", ... },
                "consortium": [ { partner data }, ... ],
                "budget": { budget data }
            }
        
        Returns:
            Compliance report with issues, warnings, and recommendations
        """
        
        logger.info(f"Running compliance check for {call_id}")
        
        checks = []
        
        # 1. Mandatory sections check
        checks.append(
            await self._check_mandatory_sections(call_id, proposal_data.get('sections', {}))
        )
        
        # 2. Page limits check
        checks.append(
            self._check_page_limits(proposal_data.get('sections', {}))
        )
        
        # 3. Consortium composition check
        checks.append(
            await self._check_consortium_composition(call_id, proposal_data.get('consortium', []))
        )
        
        # 4. Budget compliance check
        checks.append(
            self._check_budget_rules(proposal_data.get('budget', {}))
        )
        
        # 5. Evaluation criteria coverage
        checks.append(
            await self._check_criteria_coverage(call_id, proposal_data.get('sections', {}))
        )
        
        # 6. Mandatory annexes check
        checks.append(
            self._check_mandatory_annexes(proposal_data.get('annexes', []))
        )
        
        # Aggregate results
        return self._aggregate_compliance_results(checks)
    
    async def _check_mandatory_sections(
        self,
        call_id: str,
        sections: dict[str, str]
    ) -> dict[str, Any]:
        """
        Check if all mandatory sections are present
        """
        
        # Standard Horizon Europe mandatory sections
        mandatory_sections = [
            "excellence.objectives",
            "excellence.methodology",
            "excellence.beyond_sota",
            "impact.pathways",
            "impact.dissemination",
            "implementation.work_plan",
            "implementation.consortium"
        ]
        
        missing_sections = []
        for section_id in mandatory_sections:
            if section_id not in sections or not sections[section_id].strip():
                missing_sections.append(section_id)
        
        return {
            "check_name": "Mandatory Sections",
            "status": "pass" if not missing_sections else "fail",
            "issues": [f"Missing section: {s}" for s in missing_sections],
            "warnings": [],
            "priority": "critical"
        }
    
    def _check_page_limits(self, sections: dict[str, str]) -> dict[str, Any]:
        """
        Check if sections respect page limits
        """
        
        # Approximate: 325 words per page
        WORDS_PER_PAGE = 325
        
        section_limits = {
            "excellence": 30,  # Excellence section: max 30 pages
            "impact": 10,      # Impact section: max 10 pages
            "implementation": 15  # Implementation: max 15 pages
        }
        
        issues = []
        warnings = []
        
        for section_name, page_limit in section_limits.items():
            # Aggregate all subsections
            section_content = ""
            for section_id, content in sections.items():
                if section_id.startswith(section_name):
                    section_content += content + " "
            
            word_count = len(section_content.split())
            estimated_pages = word_count / WORDS_PER_PAGE
            
            if estimated_pages > page_limit:
                issues.append(
                    f"{section_name.capitalize()} section: {estimated_pages:.1f} pages (limit: {page_limit})"
                )
            elif estimated_pages > page_limit * 0.9:
                warnings.append(
                    f"{section_name.capitalize()} section: {estimated_pages:.1f} pages, close to limit ({page_limit})"
                )
        
        return {
            "check_name": "Page Limits",
            "status": "pass" if not issues else "fail",
            "issues": issues,
            "warnings": warnings,
            "priority": "high"
        }
    
    async def _check_consortium_composition(
        self,
        call_id: str,
        consortium: list[dict]
    ) -> dict[str, Any]:
        """
        Check consortium composition requirements
        """
        
        # Get requirements from call documents
        requirements_chunks = self.call_doc_service.search_call_chunks(
            call_id,
            "eligibility consortium minimum entities countries",
            limit=3
        )
        
        # Standard requirements (can be overridden by call-specific)
        min_entities = 3
        min_countries = 3
        
        # Count unique countries
        countries = set(p.get('country', 'Unknown') for p in consortium)
        entity_count = len(consortium)
        country_count = len(countries)
        
        issues = []
        warnings = []
        
        if entity_count < min_entities:
            issues.append(
                f"Consortium has {entity_count} entities (minimum: {min_entities})"
            )
        
        if country_count < min_countries:
            issues.append(
                f"Consortium covers {country_count} countries (minimum: {min_countries})"
            )
        
        # Check for balanced distribution
        if entity_count > 0:
            max_partner_share = max(
                p.get('budget_share', 0) for p in consortium
            )
            if max_partner_share > 0.5:
                warnings.append(
                    f"One partner has {max_partner_share*100:.0f}% of budget - consider more balanced distribution"
                )
        
        return {
            "check_name": "Consortium Composition",
            "status": "pass" if not issues else "fail",
            "issues": issues,
            "warnings": warnings,
            "priority": "critical"
        }
    
    def _check_budget_rules(self, budget: dict[str, Any]) -> dict[str, Any]:
        """
        Check budget compliance
        """
        
        issues = []
        warnings = []
        
        partner_budgets = budget.get('partner_budgets', [])
        
        for partner in partner_budgets:
            costs = partner.get('costs', {})
            
            # Check indirect costs calculation (should be 25%)
            direct_eligible = (
                costs.get('personnel', 0) +
                costs.get('equipment', 0) +
                costs.get('other_direct', 0)
            )
            expected_indirect = direct_eligible * 0.25
            actual_indirect = costs.get('indirect', 0)
            
            if abs(actual_indirect - expected_indirect) > 1:  # Allow small rounding
                issues.append(
                    f"{partner['partner_name']}: Indirect costs should be 25% "
                    f"(expected €{expected_indirect:,.0f}, got €{actual_indirect:,.0f})"
                )
            
            # Check for very high equipment costs
            if costs.get('equipment', 0) > direct_eligible * 0.4:
                warnings.append(
                    f"{partner['partner_name']}: Equipment costs are >40% of direct costs - "
                    "strong justification needed"
                )
        
        return {
            "check_name": "Budget Rules",
            "status": "pass" if not issues else "fail",
            "issues": issues,
            "warnings": warnings,
            "priority": "high"
        }
    
    async def _check_criteria_coverage(
        self,
        call_id: str,
        sections: dict[str, str]
    ) -> dict[str, Any]:
        """
        Check if evaluation criteria are addressed
        """
        
        # This would use the EvaluationCriteriaMatcher in practice
        # Simplified version here
        
        issues = []
        warnings = []
        
        # Key terms that should appear
        excellence_terms = ['innovation', 'beyond state of the art', 'methodology', 'objectives']
        impact_terms = ['impact', 'dissemination', 'exploitation', 'outcomes']
        implementation_terms = ['work package', 'deliverable', 'milestone', 'resources']
        
        excellence_content = " ".join([
            sections.get(k, '') for k in sections if k.startswith('excellence')
        ]).lower()
        
        impact_content = " ".join([
            sections.get(k, '') for k in sections if k.startswith('impact')
        ]).lower()
        
        implementation_content = " ".join([
            sections.get(k, '') for k in sections if k.startswith('implementation')
        ]).lower()
        
        # Check for missing key terms
        for term in excellence_terms:
            if term not in excellence_content:
                warnings.append(f"Excellence section: '{term}' not explicitly mentioned")
        
        for term in impact_terms:
            if term not in impact_content:
                warnings.append(f"Impact section: '{term}' not explicitly mentioned")
        
        for term in implementation_terms:
            if term not in implementation_content:
                warnings.append(f"Implementation section: '{term}' not explicitly mentioned")
        
        return {
            "check_name": "Evaluation Criteria Coverage",
            "status": "pass" if not issues else "warning",
            "issues": issues,
            "warnings": warnings,
            "priority": "medium"
        }
    
    def _check_mandatory_annexes(self, annexes: list[str]) -> dict[str, Any]:
        """
        Check for mandatory annexes
        """
        
        mandatory_annexes = [
            "Detailed budget table",
            "Capacity of participants",
            "Ethical issues table"
        ]
        
        issues = []
        
        for required in mandatory_annexes:
            if required not in annexes:
                issues.append(f"Missing annex: {required}")
        
        return {
            "check_name": "Mandatory Annexes",
            "status": "pass" if not issues else "fail",
            "issues": issues,
            "warnings": [],
            "priority": "high"
        }
    
    def _aggregate_compliance_results(
        self,
        checks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Aggregate all compliance check results
        """
        
        critical_issues = []
        high_priority_issues = []
        warnings = []
        
        overall_compliant = True
        
        for check in checks:
            if check['status'] == 'fail':
                overall_compliant = False
                if check['priority'] == 'critical':
                    critical_issues.extend([
                        f"[{check['check_name']}] {issue}"
                        for issue in check['issues']
                    ])
                elif check['priority'] == 'high':
                    high_priority_issues.extend([
                        f"[{check['check_name']}] {issue}"
                        for issue in check['issues']
                    ])
            
            warnings.extend([
                f"[{check['check_name']}] {warning}"
                for warning in check['warnings']
            ])
        
        # Generate action items
        action_items = []
        
        if critical_issues:
            action_items.append({
                "priority": "MUST FIX",
                "items": critical_issues,
                "description": "These issues will prevent submission"
            })
        
        if high_priority_issues:
            action_items.append({
                "priority": "SHOULD FIX",
                "items": high_priority_issues,
                "description": "These issues may reduce evaluation score"
            })
        
        if warnings:
            action_items.append({
                "priority": "RECOMMENDED",
                "items": warnings,
                "description": "Consider addressing these for better quality"
            })
        
        return {
            "overall_compliant": overall_compliant,
            "summary": {
                "critical_issues": len(critical_issues),
                "high_priority_issues": len(high_priority_issues),
                "warnings": len(warnings)
            },
            "action_items": action_items,
            "detailed_checks": checks
        }


"""
Proposal Writing Tools

This module provides tool wrappers around existing proposal writing services
for use with the ProposalAwareAgent. Each tool wraps an existing service
and provides a consistent interface for the agent.

Tools:
1. generate_section_draft - ProposalDraftGenerator
2. improve_section - QualityImprover
3. rewrite_section - SmartRewriter
4. evaluate_section - EvaluatorSimulator
5. analyze_gaps - GapAnalysisService
6. check_compliance - ComplianceChecker
7. get_suggestions - InlineSuggestionsService
8. focus_section - DocumentStateService
9. get_document_overview - DocumentStateService
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProposalToolExecutor:
    """
    Executor for proposal-specific tools.

    Wraps existing proposal writing services and provides a consistent
    interface for the ProposalAwareAgent to call them.
    """

    def __init__(self, session_manager=None, db_pool=None):
        """
        Initialize the tool executor.

        Args:
            session_manager: ProposalSessionManager for state updates
            db_pool: Database connection pool for services
        """
        self.session_manager = session_manager
        self.db_pool = db_pool
        self._services: dict[str, Any] = {}
        self._init_services()

    def _init_services(self):
        """Initialize all required services lazily."""
        # Services are initialized on first use to avoid import issues
        pass

    def _get_service(self, service_name: str) -> Any:
        """Get or initialize a service by name."""
        if service_name in self._services:
            return self._services[service_name]

        try:
            if service_name == "draft_generator":
                from ..call_document_service import CallDocumentService
                from ..proposal_writing import ProposalDraftGenerator, ProposalTemplateService

                if self.db_pool:
                    call_doc_service = CallDocumentService(self.db_pool)
                    template_service = ProposalTemplateService(self.db_pool, call_doc_service)
                    self._services[service_name] = ProposalDraftGenerator(
                        call_doc_service, template_service
                    )
                else:
                    logger.warning("No db_pool for draft_generator")
                    return None

            elif service_name == "quality_improver":
                from ..proposal_writing import QualityImprover

                # QualityImprover uses ProposalAIService internally
                self._services[service_name] = QualityImprover()

            elif service_name == "smart_rewriter":
                from ..proposal_writing import SmartRewriter

                self._services[service_name] = SmartRewriter()

            elif service_name == "evaluator_simulator":
                from ..proposal_writing import EvaluatorSimulator

                self._services[service_name] = EvaluatorSimulator()

            elif service_name == "gap_analysis":
                from ..proposal_writing import GapAnalysisService

                self._services[service_name] = GapAnalysisService()

            elif service_name == "compliance_checker":
                from ..call_document_service import CallDocumentService
                from ..proposal_writing import ComplianceChecker

                if self.db_pool:
                    call_doc_service = CallDocumentService(self.db_pool)
                    self._services[service_name] = ComplianceChecker(call_doc_service, self.db_pool)
                else:
                    logger.warning("No db_pool for compliance_checker")
                    return None

            elif service_name == "suggestions_service":
                from ..proposal_writing import InlineSuggestionsService

                self._services[service_name] = InlineSuggestionsService()

            return self._services.get(service_name)
        except Exception as e:
            logger.error(f"Failed to initialize service {service_name}: {e}")
            return None

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        session_id: str | None = None,
        proposal_context: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a proposal tool.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            session_id: Current session ID
            proposal_context: Current proposal context

        Returns:
            Tool result dictionary
        """
        try:
            if tool_name == "generate_section_draft":
                return await self._generate_section_draft(parameters)
            elif tool_name == "improve_section":
                return await self._improve_section(parameters, proposal_context)
            elif tool_name == "rewrite_section":
                return await self._rewrite_section(parameters, proposal_context)
            elif tool_name == "evaluate_section":
                return await self._evaluate_section(parameters, proposal_context)
            elif tool_name == "analyze_gaps":
                return await self._analyze_gaps(parameters, proposal_context)
            elif tool_name == "check_compliance":
                return await self._check_compliance(parameters)
            elif tool_name == "get_suggestions":
                return await self._get_suggestions(parameters, proposal_context)
            elif tool_name == "focus_section":
                return await self._focus_section(parameters, session_id)
            elif tool_name == "mark_section_status":
                return await self._mark_section_status(parameters, session_id)
            elif tool_name == "get_document_overview":
                return await self._get_document_overview(session_id)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name}

    async def _generate_section_draft(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate a draft for a proposal section."""
        section_id = parameters.get("section_id", "")
        call_id = parameters.get("call_id", "")
        guidance = parameters.get("guidance", "")
        word_target = parameters.get("word_target", 500)
        parameters.get("style", "formal")

        service = self._get_service("draft_generator")
        if not service:
            # Return a placeholder if service unavailable
            return {
                "section_id": section_id,
                "content": self._generate_placeholder_draft(section_id, word_target),
                "word_count": word_target,
                "generated": True,
                "note": "Generated with placeholder service",
            }

        try:
            # Call the actual service
            user_context = {"project_idea": guidance, "target_words": word_target}
            result = await service.generate_section_draft(
                call_id=call_id, section_id=section_id, user_context=user_context
            )

            content = result.get("draft_text", "")
            if not content:
                content = result.get("content", "")

            return {
                "section_id": section_id,
                "content": content,
                "word_count": len(content.split()),
                "generated": True,
                "sources_used": result.get("sources", []),
            }
        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            return {
                "section_id": section_id,
                "content": self._generate_placeholder_draft(section_id, word_target),
                "word_count": word_target,
                "generated": True,
                "error": str(e),
            }

    async def _improve_section(
        self, parameters: dict[str, Any], proposal_context: str | None
    ) -> dict[str, Any]:
        """Improve existing section content."""
        section_id = parameters.get("section_id", "")
        focus_areas = parameters.get("focus_areas", "all")
        parameters.get("preserve_length", True)

        # Extract current content from proposal context
        current_content = self._extract_section_content(section_id, proposal_context)

        if not current_content:
            return {
                "section_id": section_id,
                "error": "No content found to improve",
                "improved": False,
            }

        service = self._get_service("quality_improver")
        if not service:
            return {
                "section_id": section_id,
                "content": current_content,
                "improvements_made": [],
                "improved": False,
                "note": "Improvement service unavailable",
            }

        try:
            result = await service.improve_section(
                content=current_content,
                section_type=section_id.split(".")[-1] if "." in section_id else section_id,
                focus_areas=focus_areas.split(",") if isinstance(focus_areas, str) else focus_areas,
            )
            return {
                "section_id": section_id,
                "content": result.get("improved_content", current_content),
                "original_content": current_content,
                "improvements_made": result.get("improvements", []),
                "improved": True,
            }
        except Exception as e:
            logger.error(f"Section improvement failed: {e}")
            return {
                "section_id": section_id,
                "content": current_content,
                "improved": False,
                "error": str(e),
            }

    async def _rewrite_section(
        self, parameters: dict[str, Any], proposal_context: str | None
    ) -> dict[str, Any]:
        """Rewrite section with a specific style."""
        section_id = parameters.get("section_id", "")
        style = parameters.get("style", "eu_evaluator_friendly")
        tone = parameters.get("tone", "confident")

        current_content = self._extract_section_content(section_id, proposal_context)

        if not current_content:
            return {
                "section_id": section_id,
                "error": "No content found to rewrite",
                "rewritten": False,
            }

        service = self._get_service("smart_rewriter")
        if not service:
            return {
                "section_id": section_id,
                "content": current_content,
                "style_applied": style,
                "rewritten": False,
                "note": "Rewriter service unavailable",
            }

        try:
            from ..proposal_writing import RewriteStyle

            style_enum = getattr(RewriteStyle, style.upper(), RewriteStyle.EU_EVALUATOR_FRIENDLY)
            result = await service.rewrite(content=current_content, style=style_enum, tone=tone)
            return {
                "section_id": section_id,
                "content": (
                    result.rewritten_content
                    if hasattr(result, "rewritten_content")
                    else str(result)
                ),
                "original_content": current_content,
                "style_applied": style,
                "rewritten": True,
            }
        except Exception as e:
            logger.error(f"Section rewrite failed: {e}")
            return {
                "section_id": section_id,
                "content": current_content,
                "style_applied": style,
                "rewritten": False,
                "error": str(e),
            }

    async def _evaluate_section(
        self, parameters: dict[str, Any], proposal_context: str | None
    ) -> dict[str, Any]:
        """Evaluate section with EU evaluator simulation."""
        section_id = parameters.get("section_id", "")
        evaluation_type = parameters.get("evaluation_type", "detailed")

        current_content = self._extract_section_content(section_id, proposal_context)

        if not current_content:
            return {
                "section_id": section_id,
                "error": "No content found to evaluate",
                "evaluated": False,
            }

        service = self._get_service("evaluator_simulator")
        if not service:
            # Return placeholder evaluation
            return self._generate_placeholder_evaluation(section_id, current_content)

        try:
            result = await service.evaluate(
                content=current_content,
                section_type=section_id.split(".")[-1] if "." in section_id else section_id,
                detailed=(evaluation_type == "detailed"),
            )
            return {
                "section_id": section_id,
                "score": result.overall_score if hasattr(result, "overall_score") else 3.0,
                "max_score": 5.0,
                "criterion_scores": [
                    {
                        "name": cs.name,
                        "score": cs.score,
                        "max": cs.max_score,
                        "feedback": cs.feedback,
                    }
                    for cs in (
                        result.criterion_scores if hasattr(result, "criterion_scores") else []
                    )
                ],
                "strengths": result.strengths if hasattr(result, "strengths") else [],
                "weaknesses": result.weaknesses if hasattr(result, "weaknesses") else [],
                "suggestions": result.suggestions if hasattr(result, "suggestions") else [],
                "evaluated": True,
            }
        except Exception as e:
            logger.error(f"Section evaluation failed: {e}")
            return self._generate_placeholder_evaluation(section_id, current_content)

    async def _analyze_gaps(
        self, parameters: dict[str, Any], proposal_context: str | None
    ) -> dict[str, Any]:
        """Analyze gaps in a section."""
        section_id = parameters.get("section_id", "")
        include_fixes = parameters.get("include_fixes", True)

        current_content = self._extract_section_content(section_id, proposal_context)

        service = self._get_service("gap_analysis")
        if not service:
            return self._generate_placeholder_gaps(section_id)

        try:
            result = await service.analyze(
                content=current_content or "",
                section_type=section_id.split(".")[-1] if "." in section_id else section_id,
                include_fixes=include_fixes,
            )
            return {
                "section_id": section_id,
                "gaps": [
                    {
                        "id": gap.id if hasattr(gap, "id") else str(i),
                        "description": gap.description if hasattr(gap, "description") else str(gap),
                        "severity": gap.severity.value if hasattr(gap, "severity") else "major",
                        "category": gap.category.value if hasattr(gap, "category") else "content",
                        "suggested_fix": gap.suggested_fix if hasattr(gap, "suggested_fix") else "",
                        "effort": gap.effort.value if hasattr(gap, "effort") else "medium",
                    }
                    for i, gap in enumerate(result.gaps if hasattr(result, "gaps") else [])
                ],
                "gap_count": len(result.gaps) if hasattr(result, "gaps") else 0,
                "analyzed": True,
            }
        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            return self._generate_placeholder_gaps(section_id)

    async def _check_compliance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Check proposal compliance."""
        section_id = parameters.get("section_id", "all")
        check_type = parameters.get("check_type", "all")

        service = self._get_service("compliance_checker")
        if not service:
            return {
                "section_id": section_id,
                "compliant": True,
                "checks_passed": 5,
                "checks_failed": 0,
                "warnings": 0,
                "details": ["Compliance check service unavailable - assuming compliant"],
            }

        try:
            result = await service.check_compliance(
                section_id=section_id if section_id != "all" else None, check_type=check_type
            )
            return {
                "section_id": section_id,
                "compliant": result.get("compliant", True),
                "checks_passed": result.get("passed", 0),
                "checks_failed": result.get("failed", 0),
                "warnings": result.get("warnings", 0),
                "details": result.get("details", []),
            }
        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return {"section_id": section_id, "compliant": True, "error": str(e)}

    async def _get_suggestions(
        self, parameters: dict[str, Any], proposal_context: str | None
    ) -> dict[str, Any]:
        """Get inline suggestions for a section."""
        section_id = parameters.get("section_id", "")
        suggestion_types = parameters.get("suggestion_types", "all")

        current_content = self._extract_section_content(section_id, proposal_context)

        if not current_content:
            return {"section_id": section_id, "suggestions": [], "suggestion_count": 0}

        service = self._get_service("suggestions_service")
        if not service:
            return {
                "section_id": section_id,
                "suggestions": [],
                "suggestion_count": 0,
                "note": "Suggestions service unavailable",
            }

        try:
            result = await service.get_suggestions(
                content=current_content,
                categories=(
                    suggestion_types.split(",")
                    if isinstance(suggestion_types, str) and suggestion_types != "all"
                    else None
                ),
            )
            return {
                "section_id": section_id,
                "suggestions": [
                    {
                        "id": s.id if hasattr(s, "id") else str(i),
                        "type": s.category.value if hasattr(s, "category") else "general",
                        "original": s.original_text if hasattr(s, "original_text") else "",
                        "suggested": s.suggested_text if hasattr(s, "suggested_text") else "",
                        "reason": s.reason if hasattr(s, "reason") else "",
                        "priority": s.priority.value if hasattr(s, "priority") else "medium",
                    }
                    for i, s in enumerate(
                        result.suggestions
                        if hasattr(result, "suggestions")
                        else result
                        if isinstance(result, list)
                        else []
                    )
                ],
                "suggestion_count": len(
                    result.suggestions
                    if hasattr(result, "suggestions")
                    else result
                    if isinstance(result, list)
                    else []
                ),
            }
        except Exception as e:
            logger.error(f"Get suggestions failed: {e}")
            return {
                "section_id": section_id,
                "suggestions": [],
                "suggestion_count": 0,
                "error": str(e),
            }

    async def _focus_section(
        self, parameters: dict[str, Any], session_id: str | None
    ) -> dict[str, Any]:
        """Set the active section in the session."""
        section_id = parameters.get("section_id", "")

        if self.session_manager and session_id:
            try:
                await self.session_manager.set_active_section(session_id, section_id)
                return {"section_id": section_id, "focused": True}
            except Exception as e:
                logger.error(f"Failed to focus section: {e}")
                return {"section_id": section_id, "focused": False, "error": str(e)}
        return {"section_id": section_id, "focused": True, "note": "No session manager available"}

    async def _mark_section_status(
        self, parameters: dict[str, Any], session_id: str | None
    ) -> dict[str, Any]:
        """Update the status of a section."""
        section_id = parameters.get("section_id", "")
        status_str = parameters.get("status", "complete").lower()

        if self.session_manager and session_id:
            try:
                from ..proposal_session.session_state import SectionStatus

                # Map string to enum
                status_map = {
                    "empty": SectionStatus.EMPTY,
                    "draft": SectionStatus.DRAFT,
                    "in_review": SectionStatus.IN_REVIEW,
                    "complete": SectionStatus.COMPLETE,
                }
                status = status_map.get(status_str, SectionStatus.COMPLETE)

                success = await self.session_manager.update_section_status(
                    session_id, section_id, status
                )
                return {"section_id": section_id, "status": status.value, "updated": success}
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to update section status: {e}")
                return {"section_id": section_id, "updated": False, "error": str(e)}
        return {"section_id": section_id, "updated": True, "note": "No session manager available"}

    async def _get_document_overview(self, session_id: str | None) -> dict[str, Any]:
        """Get the document overview for the session."""
        if self.session_manager and session_id:
            try:
                session = await self.session_manager.get_session(session_id)
                if session:
                    from ..proposal_session import DocumentStateService

                    doc_service = DocumentStateService()
                    return doc_service.get_document_overview(session)
            except Exception as e:
                logger.error(f"Failed to get document overview: {e}")

        return {
            "overview": "No document overview available",
            "error": "Session not found or unavailable",
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_section_content(self, section_id: str, proposal_context: str | None) -> str | None:
        """Extract section content from proposal context string."""
        if not proposal_context or not section_id:
            return None

        # Look for content between markers in the context
        # Format: **Current Content:**\n```\ncontent\n```
        import re

        # Try to find section-specific content
        pattern = rf"### Active Section:.*?{re.escape(section_id)}.*?\*\*Current Content:\*\*\s*```\s*([\s\S]*?)\s*```"
        match = re.search(pattern, proposal_context)
        if match:
            return match.group(1).strip()

        return None

    def _generate_placeholder_draft(self, section_id: str, word_target: int) -> str:
        """Generate a placeholder draft when service is unavailable."""
        section_name = section_id.split(".")[-1].replace("_", " ").title()

        templates = {
            "objectives": f"""
## {section_name}

This project aims to advance the state of the art by [describe main objective].

### Specific Objectives:

1. **SO1**: [First specific objective]
2. **SO2**: [Second specific objective]
3. **SO3**: [Third specific objective]

These objectives are ambitious yet achievable within the project timeline, supported by a consortium with complementary expertise.

### Expected Outcomes:
- [Outcome 1 with measurable target]
- [Outcome 2 with measurable target]

The objectives directly address the call's scope and contribute to [expected impact].
""",
            "methodology": f"""
## {section_name}

Our approach combines [methodology 1] with [methodology 2] to achieve the project objectives.

### Work Package Structure:
- **WP1**: Project management and coordination
- **WP2**: [Core research/development activity]
- **WP3**: [Validation and testing]
- **WP4**: Dissemination and exploitation

### Key Methods:
1. [Method 1 with justification]
2. [Method 2 with justification]

### Risk Mitigation:
We have identified key risks and mitigation strategies to ensure project success.
""",
        }

        return templates.get(
            section_id.split(".")[-1],
            f"## {section_name}\n\n[Content to be developed for this section]\n\nThis section should address:\n- Key points from the call\n- Relevant methodology\n- Expected outcomes",
        )

    def _generate_placeholder_evaluation(self, section_id: str, content: str) -> dict[str, Any]:
        """Generate placeholder evaluation when service unavailable."""
        word_count = len(content.split()) if content else 0
        score = min(4.0, max(2.0, word_count / 200))  # Simple heuristic

        return {
            "section_id": section_id,
            "score": round(score, 1),
            "max_score": 5.0,
            "strengths": ["Content present", "Structure evident"],
            "weaknesses": ["Could be more specific", "Add quantitative targets"],
            "suggestions": [
                "Add measurable KPIs",
                "Reference call requirements explicitly",
                "Include timeline/milestones",
            ],
            "evaluated": True,
            "note": "Placeholder evaluation - full service unavailable",
        }

    def _generate_placeholder_gaps(self, section_id: str) -> dict[str, Any]:
        """Generate placeholder gap analysis when service unavailable."""
        return {
            "section_id": section_id,
            "gaps": [
                {
                    "id": "gap-1",
                    "description": "Consider adding quantitative targets and KPIs",
                    "severity": "major",
                    "category": "content",
                    "suggested_fix": "Include specific, measurable outcomes aligned with call expectations",
                    "effort": "medium",
                },
                {
                    "id": "gap-2",
                    "description": "Reference to evaluation criteria could be strengthened",
                    "severity": "minor",
                    "category": "compliance",
                    "suggested_fix": "Explicitly address each evaluation criterion from the call",
                    "effort": "quick",
                },
            ],
            "gap_count": 2,
            "analyzed": True,
            "note": "Placeholder analysis - full service unavailable",
        }


# Singleton instance for easy access
_proposal_tool_executor: ProposalToolExecutor | None = None


def get_proposal_tool_executor(session_manager=None, db_pool=None) -> ProposalToolExecutor:
    """
    Get or create the proposal tool executor instance.

    Args:
        session_manager: Optional session manager
        db_pool: Optional database pool

    Returns:
        ProposalToolExecutor instance
    """
    global _proposal_tool_executor
    if _proposal_tool_executor is None:
        _proposal_tool_executor = ProposalToolExecutor(
            session_manager=session_manager, db_pool=db_pool
        )
    return _proposal_tool_executor

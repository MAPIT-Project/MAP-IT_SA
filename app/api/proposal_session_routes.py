"""
V4 Proposal Session Routes

API routes for the unified AI Proposal Writer that bridges:
- Chat-driven proposal writing (SSE streaming)
- Document state management
- Section locking during AI generation
- Real-time quality feedback

This is the V4 API - uses ProposalAwareAgent with proposal context injection.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v4/proposal-session", tags=["proposal-session-v4"])

# Lazy initialization of services
_session_manager = None
_proposal_agent = None


def get_session_manager():
    """Get or create the session manager instance."""
    global _session_manager
    if _session_manager is None:
        try:
            from ..services.proposal_session import ProposalSessionManager
            _session_manager = ProposalSessionManager()
            logger.info("✅ ProposalSessionManager initialized for V4 routes")
        except Exception as e:
            logger.error(f"Failed to initialize ProposalSessionManager: {e}")
            raise
    return _session_manager


def get_proposal_agent():
    """Get or create the proposal-aware agent instance."""
    global _proposal_agent
    if _proposal_agent is None:
        try:
            from ..services.agents import ProposalAwareAgent
            _proposal_agent = ProposalAwareAgent(
                max_iterations=5,
                session_manager=get_session_manager()
            )
            logger.info("✅ ProposalAwareAgent initialized for V4 routes")
        except Exception as e:
            logger.error(f"Failed to initialize ProposalAwareAgent: {e}")
            raise
    return _proposal_agent


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new proposal session."""
    proposal_id: int = Field(..., description="Database ID of the proposal")
    call_id: str = Field(..., description="Funding call identifier")
    title: str = Field(..., description="Proposal title")
    proposal_type: str = Field(default="RIA", description="Proposal type (RIA, IA, CSA, ERC)")
    conversation_id: int | None = Field(default=None, description="Existing conversation ID")


class SessionResponse(BaseModel):
    """Response with session details."""
    session_id: str
    proposal_id: int
    call_id: str
    title: str
    status: str
    active_section_id: str | None
    completion_percentage: float
    total_words: int
    sections: dict[str, Any]
    created_at: str


class MessageRequest(BaseModel):
    """Request to send a message in a proposal session."""
    message: str = Field(..., description="User message")
    section_context: str | None = Field(
        default=None,
        description="Optional section ID to focus on"
    )


class SectionUpdateRequest(BaseModel):
    """Request to update section content."""
    content: str = Field(..., description="New section content")


class SectionGenerateRequest(BaseModel):
    """Request to generate section content via AI."""
    guidance: str | None = Field(default=None, description="Guidance for generation")
    word_target: int = Field(default=500, description="Target word count")
    style: str = Field(default="formal", description="Writing style")


# =============================================================================
# Helper Functions
# =============================================================================

async def _ensure_proposal_exists(
    manager,
    proposal_id: int,
    call_id: str,
    title: str,
    proposal_type: str,
    user_id: str
) -> int:
    """
    Ensure a proposal exists in the database, creating it if needed.

    Args:
        manager: ProposalSessionManager instance
        proposal_id: Requested proposal ID
        call_id: Funding call identifier
        title: Proposal title
        proposal_type: Type of proposal (RIA, IA, CSA, etc.)
        user_id: User identifier

    Returns:
        The actual proposal_id to use (may be different if auto-created)
    """
    conn = manager.db_pool.getconn()
    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if proposal exists
            cur.execute(
                "SELECT id FROM proposals WHERE id = %s",
                (proposal_id,)
            )
            existing = cur.fetchone()

            if existing:
                logger.info(f"✅ Found existing proposal: {proposal_id}")
                return proposal_id

            # Proposal doesn't exist - create it
            logger.info(f"📝 Creating new proposal (requested id={proposal_id})")
            cur.execute(
                """
                INSERT INTO proposals (
                    call_identifier, proposal_title, proposal_type,
                    status, user_id, created_at, updated_at
                ) VALUES (%s, %s, %s, 'draft', %s, NOW(), NOW())
                RETURNING id
                """,
                (call_id, title, proposal_type, user_id)
            )
            new_row = cur.fetchone()
            conn.commit()

            new_id = new_row["id"]
            logger.info(f"✅ Created new proposal with id={new_id}")
            return new_id

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Failed to ensure proposal exists: {e}")
        raise
    finally:
        manager.db_pool.putconn(conn)


# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.post("/create", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    user_id: str = Query(default="default-user", description="User identifier")
):
    """
    Create a new proposal writing session.

    This creates a unified session that tracks both:
    - Conversation state (chat history, agent context)
    - Document state (sections, scores, suggestions)

    If the proposal doesn't exist, it will be auto-created.
    """
    try:
        manager = get_session_manager()

        # Ensure proposal exists in database (auto-create if needed)
        proposal_id = await _ensure_proposal_exists(
            manager=manager,
            proposal_id=request.proposal_id,
            call_id=request.call_id,
            title=request.title,
            proposal_type=request.proposal_type,
            user_id=user_id
        )

        session = await manager.create_session(
            user_id=user_id,
            proposal_id=proposal_id,
            call_id=request.call_id,
            title=request.title,
            proposal_type=request.proposal_type,
            conversation_id=request.conversation_id
        )

        return SessionResponse(
            session_id=session.session_id,
            proposal_id=session.document.proposal_id,
            call_id=session.document.call_id,
            title=session.document.title,
            status=session.status.value,
            active_section_id=session.active_section_id,
            completion_percentage=session.document.completion_percentage,
            total_words=session.document.total_words,
            sections={k: v.to_dict() for k, v in session.document.sections.items()},
            created_at=session.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get session details including document state.
    """
    try:
        manager = get_session_manager()
        session = await manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            session_id=session.session_id,
            proposal_id=session.document.proposal_id,
            call_id=session.document.call_id,
            title=session.document.title,
            status=session.status.value,
            active_section_id=session.active_section_id,
            completion_percentage=session.document.completion_percentage,
            total_words=session.document.total_words,
            sections={k: v.to_dict() for k, v in session.document.sections.items()},
            created_at=session.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a proposal session.
    """
    try:
        manager = get_session_manager()
        success = await manager.delete_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"success": True, "message": "Session deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Chat Endpoints (SSE Streaming)
# =============================================================================

@router.post("/{session_id}/message/stream")
async def send_message_stream(session_id: str, request: MessageRequest):
    """
    Send a message and stream the response using the ProposalAwareAgent.

    This is the main chat endpoint. The agent has full awareness of:
    - Current document state (sections, scores, gaps)
    - Active section context
    - Conversation history

    Event types emitted:
    - status: Processing stages
    - agent_thinking: Agent's reasoning at each iteration
    - tool_call: When a proposal tool is being called
    - tool_result: Tool execution result
    - section_update: When section content is generated/modified
    - token: Streaming response text
    - complete: Final metadata
    - error: Error information
    """
    async def generate_stream():
        try:
            manager = get_session_manager()
            agent = get_proposal_agent()

            # Get current session state
            session = await manager.get_session(session_id)
            if not session:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Session not found'})}\n\n"
                return

            # Update active section if provided
            if request.section_context:
                await manager.set_active_section(session_id, request.section_context)
                session.active_section_id = request.section_context

            # Get proposal context for agent injection
            proposal_context = session.get_context_for_agent()

            # Get conversation context
            conversation_context = session.conversation.get_context_for_agent(max_chars=4000)

            logger.info(f"[V4] Processing message for session {session_id}")

            # Add user message to conversation
            await manager.add_message(
                session_id=session_id,
                role="user",
                content=request.message
            )

            yield f"data: {json.dumps({'type': 'status', 'stage': 'processing', 'message': 'Processing your request...'})}\n\n"

            # Process with streaming agent
            sections_affected = []
            final_answer = ""

            async for event in agent.process_query_streaming(
                query=request.message,
                context=conversation_context,
                proposal_context=proposal_context,
                session_id=session_id
            ):
                event_type = event.get('type', '')

                # Handle section updates specially
                if event_type == 'section_update':
                    section_id = event.get('section_id')
                    content = event.get('content', '')
                    if section_id and content:
                        # Lock section during update
                        await manager.lock_section(session_id, section_id)
                        # Update section content
                        await manager.update_section_content(
                            session_id=session_id,
                            section_id=section_id,
                            content=content,
                            source="ai"
                        )
                        # Unlock section
                        await manager.unlock_section(session_id, section_id)
                        sections_affected.append(section_id)

                # Capture final answer
                if event_type == 'agent_complete':
                    final_answer = event.get('result', {}).get('answer', '')

                # Yield all events
                yield f"data: {json.dumps(event)}\n\n"

            # Add assistant message to conversation
            if final_answer:
                await manager.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=final_answer,
                    sections_affected=sections_affected
                )

            # Yield completion with updated session state
            updated_session = await manager.get_session(session_id)
            yield f"data: {json.dumps({'type': 'session_state', 'completion_percentage': updated_session.document.completion_percentage, 'total_words': updated_session.document.total_words, 'sections_affected': sections_affected})}\n\n"

        except Exception as e:
            logger.error(f"[V4] Error in streaming: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{session_id}/message")
async def send_message(session_id: str, request: MessageRequest):
    """
    Send a message and get a response (non-streaming).
    """
    try:
        manager = get_session_manager()
        agent = get_proposal_agent()

        session = await manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update active section if provided
        if request.section_context:
            await manager.set_active_section(session_id, request.section_context)

        # Get contexts
        proposal_context = session.get_context_for_agent()
        conversation_context = session.conversation.get_context_for_agent(max_chars=4000)

        # Add user message
        await manager.add_message(session_id, "user", request.message)

        # Process query
        result = await agent.process_query(
            query=request.message,
            context=conversation_context,
            proposal_context=proposal_context,
            session_id=session_id
        )

        # Add assistant message
        await manager.add_message(
            session_id,
            "assistant",
            result.get('answer', ''),
            sections_affected=result.get('sections_affected', [])
        )

        return {
            "response": result.get('answer', ''),
            "sections_affected": result.get('sections_affected', []),
            "tools_used": result.get('sources_used', []),
            "confidence": result.get('confidence', 0),
            "metadata": {
                "architecture": "proposal_aware_v4",
                "iterations": result.get('iterations', 0),
                "proposal_intent": result.get('proposal_intent')
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[V4] Error in send_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Section Endpoints
# =============================================================================

@router.patch("/{session_id}/section/{section_id}")
async def update_section(
    session_id: str,
    section_id: str,
    request: SectionUpdateRequest
):
    """
    Update section content directly (user edit).

    Returns quality analysis of the updated content.
    """
    try:
        manager = get_session_manager()

        section = await manager.update_section_content(
            session_id=session_id,
            section_id=section_id,
            content=request.content,
            source="user"
        )

        if not section:
            raise HTTPException(
                status_code=400,
                detail="Failed to update section (may be locked)"
            )

        return {
            "success": True,
            "section_id": section_id,
            "word_count": section.word_count,
            "status": section.status.value,
            "quality_score": section.quality_score
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/section/{section_id}/generate")
async def generate_section(
    session_id: str,
    section_id: str,
    request: SectionGenerateRequest
):
    """
    Generate AI content for a section (SSE streaming).

    Locks the section during generation to prevent conflicts.
    """
    async def generate_stream():
        manager = get_session_manager()
        agent = get_proposal_agent()

        try:
            session = await manager.get_session(session_id)
            if not session:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Session not found'})}\n\n"
                return

            # Lock section
            locked = await manager.lock_section(session_id, section_id)
            if not locked:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Section is already locked'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating content...', 'section_id': section_id})}\n\n"

            try:
                # Use the agent's tool directly
                from ..services.tools.proposal_tools import get_proposal_tool_executor
                executor = get_proposal_tool_executor(session_manager=manager)

                result = await executor.execute_tool(
                    tool_name="generate_section_draft",
                    parameters={
                        "section_id": section_id,
                        "call_id": session.document.call_id,
                        "guidance": request.guidance,
                        "word_target": request.word_target,
                        "style": request.style
                    },
                    session_id=session_id,
                    proposal_context=session.get_context_for_agent()
                )

                content = result.get("content", "")

                # Update section with generated content
                await manager.update_section_content(
                    session_id=session_id,
                    section_id=section_id,
                    content=content,
                    source="ai"
                )

                yield f"data: {json.dumps({'type': 'content', 'section_id': section_id, 'content': content})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'section_id': section_id, 'word_count': result.get('word_count', 0)})}\n\n"

            finally:
                # Always unlock
                await manager.unlock_section(session_id, section_id)

        except Exception as e:
            logger.error(f"Section generation failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            # Ensure unlock on error
            try:
                await manager.unlock_section(session_id, section_id)
            except:
                pass

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{session_id}/section/{section_id}/evaluate")
async def evaluate_section(session_id: str, section_id: str):
    """
    Evaluate a section with EU evaluator simulation.

    Returns score (0-5) with detailed feedback.
    """
    try:
        manager = get_session_manager()

        session = await manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        from ..services.tools.proposal_tools import get_proposal_tool_executor
        executor = get_proposal_tool_executor(session_manager=manager)

        result = await executor.execute_tool(
            tool_name="evaluate_section",
            parameters={"section_id": section_id, "evaluation_type": "detailed"},
            session_id=session_id,
            proposal_context=session.get_context_for_agent()
        )

        # Update section score in session
        if result.get("evaluated") and result.get("score") is not None:
            await manager.update_section_score(
                session_id=session_id,
                section_id=section_id,
                score=result["score"]
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Section evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/section/{section_id}/analyze-gaps")
async def analyze_section_gaps(session_id: str, section_id: str):
    """
    Analyze gaps in a section and suggest fixes.
    """
    try:
        manager = get_session_manager()

        session = await manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        from ..services.tools.proposal_tools import get_proposal_tool_executor
        executor = get_proposal_tool_executor(session_manager=manager)

        result = await executor.execute_tool(
            tool_name="analyze_gaps",
            parameters={"section_id": section_id, "include_fixes": True},
            session_id=session_id,
            proposal_context=session.get_context_for_agent()
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gap analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Navigation & Focus
# =============================================================================

@router.post("/{session_id}/focus/{section_id}")
async def focus_section(session_id: str, section_id: str):
    """
    Set the active section focus.

    This updates the agent's context to focus on the specified section.
    """
    try:
        manager = get_session_manager()

        success = await manager.set_active_section(session_id, section_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session or section not found")

        return {"success": True, "active_section_id": section_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to focus section: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health_check():
    """
    Health check for the V4 proposal session system.
    """
    components = {
        "session_manager": False,
        "proposal_agent": False,
        "database": False
    }
    errors = {}

    # Test session manager
    try:
        manager = get_session_manager()
        components["session_manager"] = manager is not None
    except Exception as e:
        errors["session_manager"] = str(e)

    # Test proposal agent
    try:
        agent = get_proposal_agent()
        components["proposal_agent"] = agent is not None
    except Exception as e:
        errors["proposal_agent"] = str(e)

    # Test database (via session manager)
    try:
        if components["session_manager"]:
            manager = get_session_manager()
            if manager.db_pool:
                conn = manager.db_pool.getconn()
                manager.db_pool.putconn(conn)
                components["database"] = True
    except Exception as e:
        errors["database"] = str(e)

    healthy = all(components.values())

    return {
        "status": "healthy" if healthy else "degraded",
        "architecture": "proposal_aware_v4",
        "components": components,
        "errors": errors if errors else None,
        "timestamp": datetime.now(UTC).isoformat()
    }

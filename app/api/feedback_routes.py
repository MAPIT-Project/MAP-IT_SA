"""
Feedback API Routes

Endpoints for submitting and retrieving user feedback on AI responses.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.feedback import FeedbackSubmission, get_feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    conversation_id: str = Field(..., description="Conversation ID")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_type: str = Field(
        ...,
        description="Type: 'helpful', 'not_helpful', 'incorrect', 'incomplete', 'other'"
    )
    feedback_text: str | None = Field(None, description="Optional detailed feedback")
    message_id: str | None = Field(None, description="Specific message ID")
    query_text: str | None = Field(None, description="The user's query")
    response_text: str | None = Field(None, description="The AI response (first 500 chars)")
    tools_used: list[str] | None = Field(None, description="Tools used in response")
    query_type: str | None = Field(None, description="Query type classification")
    response_time_ms: int | None = Field(None, description="Response time in ms")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    success: bool
    feedback_id: int | None = None
    message: str | None = None
    error: str | None = None


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback for a conversation response.

    Rate responses from 1-5 and provide feedback type:
    - 'helpful': The response was helpful and accurate
    - 'not_helpful': The response wasn't useful
    - 'incorrect': The response contained errors
    - 'incomplete': The response was missing information
    - 'other': Other feedback
    """
    try:
        service = get_feedback_service()

        submission = FeedbackSubmission(
            conversation_id=request.conversation_id,
            rating=request.rating,
            feedback_type=request.feedback_type,
            feedback_text=request.feedback_text,
            message_id=request.message_id,
            query_text=request.query_text,
            response_text=request.response_text[:500] if request.response_text else None,
            tools_used=request.tools_used,
            query_type=request.query_type,
            response_time_ms=request.response_time_ms
        )

        result = await service.submit_feedback(submission)
        return FeedbackResponse(**result)

    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_feedback_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize")
):
    """
    Get feedback summary for the specified period.

    Returns aggregated metrics including:
    - Total feedback count
    - Average rating
    - Satisfaction rate
    - Breakdown by feedback type
    - Tool-specific feedback
    - Recent low-rated responses
    """
    try:
        service = get_feedback_service()
        return await service.get_feedback_summary(days)
    except Exception as e:
        logger.error(f"Feedback summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}")
async def get_conversation_feedback(conversation_id: str):
    """
    Get all feedback for a specific conversation.
    """
    try:
        service = get_feedback_service()
        feedback = await service.get_conversation_feedback(conversation_id)
        return {
            "conversation_id": conversation_id,
            "feedback": feedback,
            "count": len(feedback)
        }
    except Exception as e:
        logger.error(f"Conversation feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_improvement_suggestions():
    """
    Get AI-generated improvement suggestions based on feedback analysis.

    Analyzes feedback patterns to identify:
    - Underperforming tools
    - Common issues
    - Areas for improvement
    """
    try:
        service = get_feedback_service()
        return await service.get_improvement_suggestions()
    except Exception as e:
        logger.error(f"Improvement suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def feedback_health():
    """Check feedback service health."""
    service = get_feedback_service()
    return {
        "status": "healthy" if service.enabled else "degraded",
        "enabled": service.enabled,
        "message": "Feedback service is operational" if service.enabled else "Database not available"
    }

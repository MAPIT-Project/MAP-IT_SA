"""
Proposal Session Manager

Central orchestrator for AI-assisted proposal writing sessions. Manages:
- Session lifecycle (create, load, save, expire)
- State synchronization between conversation and document
- Database persistence with Redis caching
- Section locking for AI generation
"""

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from .session_state import (
    ConversationState,
    Gap,
    InlineSuggestion,
    ProposalDocument,
    ProposalSessionState,
    SectionLockStatus,
    SectionState,
    SectionStatus,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class ProposalSessionManager:
    """
    Core orchestrator for proposal writing sessions.

    Bridges conversation state with document state for seamless AI-assisted
    proposal writing. Provides:
    - Session CRUD operations with database persistence
    - Redis caching for active sessions
    - Section locking during AI generation
    - State synchronization between chat and document

    Usage:
        manager = ProposalSessionManager()
        session = await manager.create_session(user_id, proposal_id, call_id, title)
        session = await manager.get_session(session_id)
        await manager.update_section(session_id, section_id, content)
        await manager.save_session(session)
    """

    # Session expiration time (24 hours of inactivity)
    SESSION_EXPIRY_HOURS = 24

    # Redis cache TTL (1 hour, refreshed on access)
    CACHE_TTL_SECONDS = 3600

    def __init__(self, database_url: str | None = None, redis_client=None):
        """
        Initialize the session manager.

        Args:
            database_url: PostgreSQL connection URL (defaults to DATABASE_URL env var)
            redis_client: Optional Redis client for caching
        """
        self.db_url = database_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL required for ProposalSessionManager")

        # Initialize database connection pool
        try:
            min_conn = int(os.getenv("DB_MIN_CONNECTIONS", "2"))
            max_conn = int(os.getenv("DB_MAX_CONNECTIONS", "10"))
            self.db_pool = SimpleConnectionPool(min_conn, max_conn, self.db_url)
            logger.info("✅ ProposalSessionManager: Database pool established")
        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            raise

        # Redis client for caching (optional)
        self.redis_client = redis_client
        if redis_client:
            logger.info("✅ ProposalSessionManager: Redis caching enabled")

        # In-memory session cache (fallback if no Redis)
        self._session_cache: dict[str, ProposalSessionState] = {}

    # =========================================================================
    # Session CRUD Operations
    # =========================================================================

    async def create_session(
        self,
        user_id: str,
        proposal_id: int,
        call_id: str,
        title: str,
        proposal_type: str = "RIA",
        conversation_id: int | None = None,
    ) -> ProposalSessionState:
        """
        Create a new proposal session.

        Args:
            user_id: User identifier
            proposal_id: Proposal database ID
            call_id: Funding call identifier
            title: Proposal title
            proposal_type: Type of proposal (RIA, IA, CSA, etc.)
            conversation_id: Optional existing conversation ID

        Returns:
            New ProposalSessionState instance
        """
        # Fetch actual proposal details (type, title, call_id) from the database if they exist
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT proposal_type, proposal_title, call_identifier FROM proposals WHERE id = %s",
                    (proposal_id,),
                )
                row = cur.fetchone()
                if row:
                    if row.get("proposal_type"):
                        proposal_type = row["proposal_type"]
                    if row.get("proposal_title"):
                        title = row["proposal_title"]
                    if row.get("call_identifier"):
                        call_id = row["call_identifier"]
        except Exception as e:
            logger.warning(f"Could not load proposal info from db: {e}")
        finally:
            self.db_pool.putconn(conn)

        # Create session with default structure
        session = ProposalSessionState.create_new(
            user_id=user_id,
            proposal_id=proposal_id,
            call_id=call_id,
            title=title,
            proposal_type=proposal_type,
            conversation_id=conversation_id or 0,
        )

        # Load existing sections from database if proposal exists
        await self._load_existing_sections(session)

        # Persist to database
        await self._persist_session(session)

        # Cache the session
        self._cache_session(session)

        logger.info(f"✅ Created proposal session: {session.session_id} for proposal {proposal_id}")
        return session

    async def get_session(self, session_id: str) -> ProposalSessionState | None:
        """
        Get a session by ID.

        Args:
            session_id: Session UUID

        Returns:
            ProposalSessionState if found, None otherwise
        """
        # Check cache first
        session = self._get_cached_session(session_id)
        if session:
            session.update_activity()
            return session

        # Load from database
        session = await self._load_session_from_db(session_id)
        if session:
            self._cache_session(session)
            session.update_activity()

        return session

    async def get_session_by_proposal(
        self, proposal_id: int, user_id: str
    ) -> ProposalSessionState | None:
        """
        Get active session for a proposal and user.

        Args:
            proposal_id: Proposal database ID
            user_id: User identifier

        Returns:
            Active ProposalSessionState if found, None otherwise
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT session_id FROM proposal_sessions
                    WHERE proposal_id = %s AND user_id = %s
                    AND status = 'active'
                    ORDER BY last_activity_at DESC
                    LIMIT 1
                    """,
                    (proposal_id, user_id),
                )
                row = cur.fetchone()
                if row:
                    return await self.get_session(row["session_id"])
                return None
        finally:
            self.db_pool.putconn(conn)

    async def save_session(self, session: ProposalSessionState) -> bool:
        """
        Save session state to database.

        Args:
            session: Session to save

        Returns:
            True if saved successfully
        """
        session.update_activity()
        await self._persist_session(session)
        self._cache_session(session)
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session UUID to delete

        Returns:
            True if deleted successfully
        """
        # Remove from cache
        self._remove_from_cache(session_id)

        # Delete from database
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM proposal_sessions WHERE session_id = %s",
                    (session_id,),
                )
                conn.commit()
                deleted = cur.rowcount > 0
                if deleted:
                    logger.info(f"✅ Deleted session: {session_id}")
                return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to delete session {session_id}: {e}")
            return False
        finally:
            self.db_pool.putconn(conn)

    # =========================================================================
    # Section Operations
    # =========================================================================

    async def update_section_content(
        self,
        session_id: str,
        section_id: str,
        content: str,
        source: str = "user",
    ) -> SectionState | None:
        """
        Update section content.

        Args:
            session_id: Session UUID
            section_id: Section identifier
            content: New content
            source: Source of update ('user', 'ai')

        Returns:
            Updated SectionState if successful
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None

        # Check if section is locked by another source
        section = session.document.get_section(section_id)
        if section and section.lock_status != SectionLockStatus.UNLOCKED:
            if source == "user" and section.lock_status == SectionLockStatus.LOCKED_BY_AI:
                logger.warning(f"Section {section_id} is locked by AI, cannot update")
                return None
            if source == "ai" and section.lock_status == SectionLockStatus.LOCKED_BY_USER:
                logger.warning(f"Section {section_id} is locked by user, cannot update")
                return None

        # Update the section
        session.document.update_section(section_id, content)

        # Persist changes
        await self._persist_section(session, section_id)
        self._cache_session(session)

        return session.document.get_section(section_id)

    async def lock_section(
        self,
        session_id: str,
        section_id: str,
        lock_type: SectionLockStatus = SectionLockStatus.LOCKED_BY_AI,
    ) -> bool:
        """
        Lock a section for AI generation.

        Args:
            session_id: Session UUID
            section_id: Section to lock
            lock_type: Type of lock to apply

        Returns:
            True if locked successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        success = session.lock_section(section_id, lock_type)
        if success:
            self._cache_session(session)
            logger.info(f"🔒 Locked section {section_id} ({lock_type.value})")
        return success

    async def unlock_section(self, session_id: str, section_id: str) -> bool:
        """
        Unlock a section after AI generation completes.

        Args:
            session_id: Session UUID
            section_id: Section to unlock

        Returns:
            True if unlocked successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        success = session.unlock_section(section_id)
        if success:
            self._cache_session(session)
            logger.info(f"🔓 Unlocked section {section_id}")
        return success

    async def set_active_section(self, session_id: str, section_id: str | None) -> bool:
        """
        Set the currently active section (user focus).

        Args:
            session_id: Session UUID
            section_id: Section to focus on (None to clear)

        Returns:
            True if set successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        session.active_section_id = section_id
        session.conversation.active_section_context = section_id
        self._cache_session(session)
        return True

    async def add_suggestion(
        self,
        session_id: str,
        section_id: str,
        suggestion: InlineSuggestion,
    ) -> bool:
        """
        Add an inline suggestion to a section.

        Args:
            session_id: Session UUID
            section_id: Target section
            suggestion: Suggestion to add

        Returns:
            True if added successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        section = session.document.get_section(section_id)
        if not section:
            return False

        section.suggestions.append(suggestion)
        self._cache_session(session)
        return True

    async def add_gap(
        self,
        session_id: str,
        section_id: str,
        gap: Gap,
    ) -> bool:
        """
        Add an identified gap to a section.

        Args:
            session_id: Session UUID
            section_id: Target section
            gap: Gap to add

        Returns:
            True if added successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        section = session.document.get_section(section_id)
        if not section:
            return False

        section.gaps.append(gap)
        self._cache_session(session)
        return True

    async def update_section_score(
        self,
        session_id: str,
        section_id: str,
        score: float,
    ) -> bool:
        """
        Update the quality score for a section.

        Args:
            session_id: Session UUID
            section_id: Target section
            score: Quality score (0-5)

        Returns:
            True if updated successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        section = session.document.get_section(section_id)
        if not section:
            return False

        section.quality_score = max(0.0, min(5.0, score))
        session.document._recalculate_totals()
        self._cache_session(session)
        return True

    # =========================================================================
    # Conversation Operations
    # =========================================================================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tools_used: list[str] | None = None,
        sections_affected: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Add a message to the session conversation.

        Args:
            session_id: Session UUID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            tools_used: List of tools used in this response
            sections_affected: Sections modified by this message
            metadata: Additional metadata

        Returns:
            True if added successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        session.conversation.add_message(
            role=role,
            content=content,
            tools_used=tools_used,
            sections_affected=sections_affected,
            metadata=metadata,
        )
        session.update_activity()
        self._cache_session(session)
        return True

    def get_context_for_agent(self, session: ProposalSessionState) -> str:
        """
        Get formatted context string for agent injection.

        Args:
            session: Current session state

        Returns:
            Formatted context string
        """
        return session.get_context_for_agent()

    # =========================================================================
    # Private: Database Operations
    # =========================================================================

    async def _persist_session(self, session: ProposalSessionState) -> None:
        """Persist session state to database."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Serialize session state
                session_state_json = json.dumps(
                    {
                        "document": session.document.to_dict(),
                        "conversation_messages": [
                            {
                                "message_id": m.message_id,
                                "role": m.role,
                                "content": m.content,
                                "timestamp": m.timestamp.isoformat(),
                                "metadata": m.metadata,
                                "tools_used": m.tools_used,
                                "sections_affected": m.sections_affected,
                            }
                            for m in session.conversation.messages
                        ],
                        "active_section_context": session.conversation.active_section_context,
                    }
                )

                # Upsert session record
                cur.execute(
                    """
                    INSERT INTO proposal_sessions (
                        session_id, proposal_id, conversation_id, user_id,
                        active_section_id, session_state, status,
                        created_at, last_activity_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET
                        active_section_id = EXCLUDED.active_section_id,
                        session_state = EXCLUDED.session_state,
                        status = EXCLUDED.status,
                        last_activity_at = EXCLUDED.last_activity_at
                    """,
                    (
                        session.session_id,
                        session.document.proposal_id,
                        session.conversation.conversation_id,
                        session.user_id,
                        session.active_section_id,
                        session_state_json,
                        session.status.value,
                        session.created_at,
                        session.last_activity_at,
                    ),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to persist session {session.session_id}: {e}")
            raise
        finally:
            self.db_pool.putconn(conn)

    async def _load_session_from_db(self, session_id: str) -> ProposalSessionState | None:
        """Load session from database."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT session_id, proposal_id, conversation_id, user_id,
                           active_section_id, session_state, status,
                           created_at, last_activity_at
                    FROM proposal_sessions
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                # Deserialize session state
                state_data = row["session_state"] or {}

                # Reconstruct document
                doc_data = state_data.get("document", {})
                document = ProposalDocument(
                    proposal_id=row["proposal_id"],
                    call_id=doc_data.get("call_id", ""),
                    title=doc_data.get("title", ""),
                    acronym=doc_data.get("acronym"),
                    proposal_type=doc_data.get("proposal_type", "RIA"),
                    status=doc_data.get("status", "draft"),
                )

                # Reconstruct sections
                for section_id, section_data in doc_data.get("sections", {}).items():
                    section = SectionState(
                        section_id=section_id,
                        section_name=section_data.get("section_name", ""),
                        content=section_data.get("content", ""),
                        word_count=section_data.get("word_count", 0),
                        quality_score=section_data.get("quality_score"),
                        status=SectionStatus(section_data.get("status", SectionStatus.EMPTY.value)),
                        lock_status=SectionLockStatus(
                            section_data.get("lock_status", SectionLockStatus.UNLOCKED.value)
                        ),
                        version=section_data.get("version", 1),
                    )
                    document.sections[section_id] = section

                # Reconstruct conversation
                conversation = ConversationState(
                    conversation_id=row["conversation_id"] or 0,
                    active_section_context=state_data.get("active_section_context"),
                )
                # Note: messages are loaded separately for performance

                # Create session object
                session = ProposalSessionState(
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    document=document,
                    conversation=conversation,
                    status=SessionStatus(row["status"]),
                    active_section_id=row["active_section_id"],
                    created_at=row["created_at"],
                    last_activity_at=row["last_activity_at"],
                )

                return session
        except Exception as e:
            logger.error(f"❌ Failed to load session {session_id}: {e}")
            return None
        finally:
            self.db_pool.putconn(conn)

    async def _load_existing_sections(self, session: ProposalSessionState) -> None:
        """Load existing section content from proposal_sections table."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT section_id, section_name, section_content, word_count,
                           quality_score, version
                    FROM proposal_sections
                    WHERE proposal_id = %s AND is_current = TRUE
                    ORDER BY section_order
                    """,
                    (session.document.proposal_id,),
                )
                rows = cur.fetchall()

                if rows:
                    session.document.sections.clear()
                    for row in rows:
                        section_id = row["section_id"]
                        section = SectionState(
                            section_id=section_id,
                            section_name=row["section_name"] or "",
                            content=row["section_content"] or "",
                            word_count=row["word_count"] or 0,
                            quality_score=(
                                float(row["quality_score"]) * 5 if row["quality_score"] else None
                            ),  # Convert 0-1 to 0-5
                            version=row["version"] or 1,
                        )

                        # Update status based on content
                        if section.word_count >= 100:
                            section.status = SectionStatus.IN_REVIEW
                        elif section.word_count >= 10:
                            section.status = SectionStatus.DRAFT
                        else:
                            section.status = SectionStatus.EMPTY

                        session.document.sections[section_id] = section

                session.document._recalculate_totals()
                logger.info(
                    f"✅ Loaded {len(rows)} existing sections for proposal "
                    f"{session.document.proposal_id}"
                )
        except Exception as e:
            logger.warning(f"Could not load existing sections: {e}")
        finally:
            self.db_pool.putconn(conn)

    async def _persist_section(self, session: ProposalSessionState, section_id: str) -> None:
        """Persist a single section to the proposal_sections table."""
        section = session.document.get_section(section_id)
        if not section:
            return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Mark previous versions as not current
                cur.execute(
                    """
                    UPDATE proposal_sections
                    SET is_current = FALSE
                    WHERE proposal_id = %s AND section_id = %s AND is_current = TRUE
                    """,
                    (session.document.proposal_id, section_id),
                )

                # Insert new version
                cur.execute(
                    """
                    INSERT INTO proposal_sections (
                        proposal_id, section_id, section_name, section_content,
                        word_count, version, is_current, quality_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
                    """,
                    (
                        session.document.proposal_id,
                        section_id,
                        section.section_name,
                        section.content,
                        section.word_count,
                        section.version + 1,
                        section.quality_score / 5 if section.quality_score else None,
                    ),
                )
                conn.commit()

                # Update version in memory
                section.version += 1
                section.is_dirty = False
                section.last_updated = datetime.now(UTC)
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to persist section {section_id}: {e}")
            raise
        finally:
            self.db_pool.putconn(conn)

    # =========================================================================
    # Private: Caching Operations
    # =========================================================================

    def _cache_session(self, session: ProposalSessionState) -> None:
        """Cache session in Redis or memory."""
        cache_key = f"proposal_session:{session.session_id}"

        if self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    self.CACHE_TTL_SECONDS,
                    json.dumps(session.to_dict()),
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
                # Fallback to memory cache
                self._session_cache[session.session_id] = session
        else:
            self._session_cache[session.session_id] = session

    def _get_cached_session(self, session_id: str) -> ProposalSessionState | None:
        """Get session from cache."""
        cache_key = f"proposal_session:{session_id}"

        if self.redis_client:
            try:
                data = self.redis_client.get(cache_key)
                if data:
                    # For now, return from memory cache if available
                    # Full deserialization can be added later
                    return self._session_cache.get(session_id)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        return self._session_cache.get(session_id)

    def _remove_from_cache(self, session_id: str) -> None:
        """Remove session from cache."""
        cache_key = f"proposal_session:{session_id}"

        if self.redis_client:
            try:
                self.redis_client.delete(cache_key)
            except Exception:
                pass

        self._session_cache.pop(session_id, None)

    # =========================================================================
    # Session Cleanup
    # =========================================================================

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expiry_threshold = datetime.now(UTC) - timedelta(hours=self.SESSION_EXPIRY_HOURS)

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE proposal_sessions
                    SET status = 'expired'
                    WHERE status = 'active'
                    AND last_activity_at < %s
                    """,
                    (expiry_threshold,),
                )
                expired_count = cur.rowcount
                conn.commit()

                if expired_count > 0:
                    logger.info(f"✅ Expired {expired_count} inactive sessions")
                return expired_count
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Session cleanup failed: {e}")
            return 0
        finally:
            self.db_pool.putconn(conn)

    def close(self) -> None:
        """Close database connections."""
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("✅ ProposalSessionManager: Database pool closed")

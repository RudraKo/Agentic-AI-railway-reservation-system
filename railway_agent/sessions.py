"""
sessions.py - In-memory session store for conversation history management.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session store  {session_id: {"history": [...], "created_at": datetime, "user_data": {...}}}
# ---------------------------------------------------------------------------
sessions: dict = {}

SESSION_TTL_HOURS = 2


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cleanup_old_sessions() -> None:
    """Remove sessions older than SESSION_TTL_HOURS. Call on every request."""
    cutoff = _now() - timedelta(hours=SESSION_TTL_HOURS)
    expired = [
        sid for sid, data in sessions.items()
        if data["created_at"] < cutoff
    ]
    for sid in expired:
        del sessions[sid]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired session(s).")


def create_session() -> str:
    """
    Generate a new UUID session, initialise empty history, and return the
    session_id string.
    """
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "history": [],
        "created_at": _now(),
        "user_data": {}  # Store user-specific data like passenger_name
    }
    logger.info(f"Created session: {session_id}")
    return session_id


def get_history(session_id: str) -> list:
    """
    Return the conversation history for a session.
    Returns an empty list if the session_id is unknown or expired.
    """
    cleanup_old_sessions()
    return sessions.get(session_id, {}).get("history", [])


def get_user_data(session_id: str) -> Dict[str, Any]:
    """Return the user_data dictionary for a session."""
    cleanup_old_sessions()
    return sessions.get(session_id, {}).get("user_data", {})


def update_history(session_id: str, history: list) -> None:
    """
    Overwrite the conversation history for an existing session.
    No-op if the session doesn't exist (e.g. was already cleaned up).
    """
    if session_id in sessions:
        sessions[session_id]["history"] = history
    else:
        logger.warning(f"update_history called on unknown session: {session_id}")


def update_user_data(session_id: str, key: str, value: Any) -> None:
    """Update a specific key in the session's user_data."""
    if session_id in sessions:
        sessions[session_id]["user_data"][key] = value
    else:
        logger.warning(f"update_user_data called on unknown session: {session_id}")


def session_exists(session_id: str) -> bool:
    """Return True if the session is present and not yet expired."""
    cleanup_old_sessions()
    return session_id in sessions
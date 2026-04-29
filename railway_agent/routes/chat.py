"""
routes/chat.py - Chat endpoint for conversational AI agent interaction.

Session management is handled server-side via sessions.py.
The frontend only needs to store and pass back the session_id.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import jwt

from database import get_db
from agent import run_agent
from models import User
from sessions import (
    cleanup_old_sessions,
    create_session,
    get_history,
    update_history,
    session_exists,
    get_user_data,
    update_user_data,
)

from config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None       # omit on first message; server creates one
    passenger_name: Optional[str] = ""
    token: Optional[str] = None            # JWT token for authenticated user
    user_name: Optional[str] = ""


class ChatResponse(BaseModel):
    response: str
    session_id: str                         # always returned so frontend can persist it
    conversation_history: list              # still returned for debugging / optional use
    user_id: int
    user_name: str


def _sanitize_username(raw_name: str | None, session_id: str) -> str:
    if raw_name and raw_name.strip():
        return raw_name.strip()
    return f"guest-{session_id[:8]}"


def _get_or_create_user(db: Session, user_name: str) -> User:
    user = db.query(User).filter(func.lower(User.name) == user_name.lower()).first()
    if user:
        return user
    user = User(name=user_name, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    POST /api/chat

    First message  → omit session_id (or send null). A new session is created
                      and returned in the response.
    Follow-up msgs → pass the session_id from the previous response. History
                      is loaded from the server automatically.
    """
    # ── Extract user_id if token provided ────────────────────────────────
    user_id = None
    if request.token:
        try:
            payload = jwt.decode(request.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = int(payload.get("sub"))
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    # ── Session resolution ────────────────────────────────────────────────
    cleanup_old_sessions()
    if request.session_id and session_exists(request.session_id):
        session_id = request.session_id
        history = get_history(session_id)
        if not request.passenger_name:
            # Try to get passenger_name from session user_data
            user_data = get_user_data(session_id)
            request.passenger_name = user_data.get("passenger_name", "")
    else:
        # Create a new session for new conversations or unknown/expired IDs
        session_id = create_session()
        history = []
        if user_id:
            # Store user_id in session for later use
            update_user_data(session_id, "user_id", user_id)

    # ── User resolution ──────────────────────────────────────────────────
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        # Resolve username for guest
        user_name = _sanitize_username(request.passenger_name or request.user_name, session_id)
        # Note: In a real app, you might not want to create a full User model for every guest
        # But for this prototype, we'll ensure we have a user record for the foreign key.
        # We'll use a unique identifier for guest
        guest_email = f"guest_{session_id[:8]}@local.host"
        user = db.query(User).filter(User.email == guest_email).first()
        if not user:
            user = User(name=user_name, email=guest_email, hashed_password="guest_session")
            db.add(user)
            db.commit()
            db.refresh(user)
    
    user_id = user.id
    user_name = user.name

    # ── Message composition ───────────────────────────────────────────────
    user_message = request.message
    if request.passenger_name:
        if f"[Passenger name: {request.passenger_name}]" not in user_message:
            user_message = f"[Passenger name: {request.passenger_name}] {user_message}"
        # Store passenger_name in session
        update_user_data(session_id, "passenger_name", request.passenger_name)

    # ── Agent call ────────────────────────────────────────────────────────
    result = run_agent(
        user_message=user_message,
        conversation_history=history,
        db=db,
        user_id=user_id,
        session_id=session_id,
    )

    # ── Persist updated history ───────────────────────────────────────────
    update_history(session_id, result["conversation_history"])

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        conversation_history=result["conversation_history"],
        user_id=user_id,
        user_name=user_name,
    )

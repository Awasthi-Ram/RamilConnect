"""
Companion routes — AI chat with SSE streaming, history, mood, stats, persona switching.

This is the main interaction endpoint. Integrates:
- RAC Engine (4-layer context)
- Psychology Engine (background trait extraction)
- User Summary Engine (living profile updates)
- Multi-provider AI streaming (Gemini/OpenAI/Claude)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_db_context
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.companion import CompanionMessage, CompanionSession
from app.models.personality import PersonalityProfile
from app.schemas.companion import (
    SendMessageRequest,
    ChatHistoryResponse,
    CompanionMessageResponse,
    SwitchPersonaRequest,
    MoodResponse,
    CompanionStatsResponse,
)
from app.services.ai_provider import AIConfig, stream_conversation, complete_json
from app.services.rac_engine import RACEngine
from app.services.psychology_engine import PsychologyEngine
from app.services.user_summary_engine import UserSummaryEngine
from app.services.prompt_builder import build_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/companion", tags=["Companion"])

# Session idle timeout (4 hours)
SESSION_IDLE_TIMEOUT = timedelta(hours=4)


async def _get_or_create_session(
    db: AsyncSession, user_id: int, persona: str
) -> CompanionSession:
    """Get active session or create a new one."""
    result = await db.execute(
        select(CompanionSession)
        .where(
            CompanionSession.user_id == user_id,
            CompanionSession.is_active == True,
        )
        .order_by(desc(CompanionSession.started_at))
        .limit(1)
    )
    session = result.scalar_one_or_none()

    # Check if session exists and is still active (not idle too long)
    if session:
        if session.last_message_at:
            idle_time = datetime.utcnow() - session.last_message_at.replace(tzinfo=None)
            if idle_time > SESSION_IDLE_TIMEOUT:
                session.is_active = False
                session = None
        if session and session.persona != persona:
            session.is_active = False
            session = None

    if not session:
        session = CompanionSession(
            user_id=user_id,
            persona=persona,
        )
        db.add(session)
        await db.flush()

    return session


# ── Background task handlers ─────────────────────────────────

async def _run_background_tasks(user_id: int, message_id: int, content: str, role: str):
    """Run post-message background tasks: RAC embedding, psychology, summary."""
    async with get_db_context() as db:
        config = await AIConfig.load(db)

        # 1. Embed message for RAC
        rac = RACEngine(db)
        await rac.embed_and_store(user_id, message_id, content, role)

        # 2. Psychology extraction (every 5 user messages)
        if role == "user":
            psych = PsychologyEngine(db)
            if await psych.should_extract(user_id):
                await psych.extract_and_update(user_id, config)

            # 3. User summary update (every 10 user messages)
            summary_engine = UserSummaryEngine(db)
            if await summary_engine.should_update(user_id):
                await summary_engine.generate_or_update(user_id, config)


# ── Chat History ─────────────────────────────────────────────

@router.get("/history", response_model=ChatHistoryResponse)
async def get_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent companion chat history (last 50 messages)."""
    result = await db.execute(
        select(CompanionMessage)
        .where(CompanionMessage.user_id == user.id)
        .order_by(desc(CompanionMessage.created_at))
        .limit(50)
    )
    messages = list(reversed(result.scalars().all()))

    formatted = [
        CompanionMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            emotion_tags=m.emotion_tags or [],
        )
        for m in messages
    ]

    return ChatHistoryResponse(messages=formatted, total=len(formatted))


# ── SSE Streaming Chat ───────────────────────────────────────

@router.post("/message")
async def send_message(
    req: SendMessageRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to the AI companion and receive SSE-streamed response.

    This endpoint:
    1. Saves the user message
    2. Assembles RAC context (4 layers)
    3. Builds the system prompt with persona + context
    4. Streams the AI response via SSE
    5. Saves the assistant response
    6. Triggers background tasks (embedding, psychology, summary)
    """
    content = req.content.strip()

    # Get or create session
    session = await _get_or_create_session(db, user.id, user.companion_persona)

    # Save user message
    user_msg = CompanionMessage(
        user_id=user.id,
        session_id=session.id,
        role="user",
        content=content,
        emotion_tags=[],
    )
    db.add(user_msg)
    session.message_count += 1
    session.last_message_at = datetime.utcnow()
    await db.flush()

    user_msg_id = user_msg.id

    # Get personality profile
    profile_result = await db.execute(
        select(PersonalityProfile).where(PersonalityProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()

    # Assemble RAC context
    rac = RACEngine(db)
    rac_context = await rac.assemble_context(
        user_id=user.id,
        current_message=content,
        session_id=session.id,
    )

    # Load AI config
    ai_config = await AIConfig.load(db)
    prompt_override = ai_config.prompt_overrides.get(user.companion_persona, "")

    # Build system prompt
    system_prompt = build_system_prompt(
        user=user,
        profile=profile,
        rac_context=rac_context,
        prompt_override=prompt_override,
    )

    # Get recent chat history for the AI
    history_result = await db.execute(
        select(CompanionMessage)
        .where(CompanionMessage.user_id == user.id)
        .order_by(desc(CompanionMessage.created_at))
        .limit(21)
    )
    history_msgs = list(reversed(history_result.scalars().all()))

    # Build chat messages (exclude the just-saved message, then add it back)
    chat_messages = [
        {"role": m.role, "content": m.content}
        for m in history_msgs[:-1]  # exclude last (the one we just saved)
    ]
    chat_messages.append({"role": "user", "content": content})

    # We need to commit the user message before streaming starts
    await db.commit()

    # Create SSE streaming response
    async def event_stream():
        full_response = ""
        try:
            async for token in _stream_with_provider(system_prompt, chat_messages, ai_config):
                full_response += token
                yield f"data: {json.dumps({'content': token})}\n\n"

            # Save assistant response
            async with get_db_context() as save_db:
                assistant_msg = CompanionMessage(
                    user_id=user.id,
                    session_id=session.id,
                    role="assistant",
                    content=full_response,
                    emotion_tags=[],
                )
                save_db.add(assistant_msg)
                await save_db.flush()
                assistant_msg_id = assistant_msg.id
                await save_db.commit()

            # Schedule background tasks for BOTH messages
            # We can't use FastAPI BackgroundTasks inside a generator,
            # so we run them inline after streaming completes
            try:
                await _run_background_tasks(user.id, user_msg_id, content, "user")
                await _run_background_tasks(user.id, assistant_msg_id, full_response, "assistant")
            except Exception as bg_err:
                logger.error(f"Background task error: {bg_err}")

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': 'Stream error'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


async def _stream_with_provider(
    system_prompt: str,
    messages: list[dict],
    config: AIConfig,
):
    """Select and stream from the correct AI provider."""
    model = config.model

    if model.startswith("gemini"):
        from app.services.ai_provider import _stream_gemini
        async for token in _stream_gemini(system_prompt, messages, config):
            yield token
    elif model.startswith("claude"):
        from app.services.ai_provider import _stream_anthropic
        async for token in _stream_anthropic(system_prompt, messages, config):
            yield token
    else:
        from app.services.ai_provider import _stream_openai
        async for token in _stream_openai(system_prompt, messages, config):
            yield token


# ── Persona Switch ───────────────────────────────────────────

@router.put("/persona")
async def switch_persona(
    req: SwitchPersonaRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch the companion persona."""
    from app.services.prompt_builder import DEFAULT_NAMES

    user.companion_persona = req.persona
    user.companion_name = req.name or DEFAULT_NAMES.get(req.persona, "Mia")

    await db.commit()
    return {"success": True, "message": f"Switched to {req.persona}"}


# ── Mood Analysis ────────────────────────────────────────────

@router.get("/mood", response_model=MoodResponse)
async def get_mood(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze the user's current mood from recent messages."""
    result = await db.execute(
        select(CompanionMessage)
        .where(
            CompanionMessage.user_id == user.id,
            CompanionMessage.role == "user",
        )
        .order_by(desc(CompanionMessage.created_at))
        .limit(5)
    )
    messages = result.scalars().all()

    if not messages:
        return MoodResponse(mood="neutral", confidence=0.5)

    user_text = " ".join(m.content for m in messages)

    try:
        config = await AIConfig.load(db)
        response = await complete_json(
            system_prompt='Analyze the emotional tone. Reply ONLY with JSON: {"mood": "happy|neutral|stressed|curious|sad", "confidence": 0-1}',
            user_prompt=user_text,
            config=config,
            max_tokens=50,
        )
        data = json.loads(response)
        return MoodResponse(
            mood=data.get("mood", "neutral"),
            confidence=data.get("confidence", 0.5),
        )
    except Exception:
        return MoodResponse(mood="neutral", confidence=0.5)


# ── Stats ────────────────────────────────────────────────────

@router.get("/stats", response_model=CompanionStatsResponse)
async def get_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get companion interaction statistics."""
    # Total user messages
    count_result = await db.execute(
        select(sqlfunc.count())
        .select_from(CompanionMessage)
        .where(
            CompanionMessage.user_id == user.id,
            CompanionMessage.role == "user",
        )
    )
    total_messages = count_result.scalar() or 0

    # Get all message dates for streak calculation
    dates_result = await db.execute(
        select(CompanionMessage.created_at)
        .where(CompanionMessage.user_id == user.id)
        .order_by(desc(CompanionMessage.created_at))
    )
    all_dates = [row[0] for row in dates_result.fetchall()]

    # Calculate streak
    streak_days = 0
    last_chat_date = None
    if all_dates:
        unique_dates = sorted(set(d.strftime("%Y-%m-%d") for d in all_dates), reverse=True)
        last_chat_date = unique_dates[0] if unique_dates else None

        today = datetime.utcnow().strftime("%Y-%m-%d")
        check_date = today
        for date_str in unique_dates:
            if date_str == check_date:
                streak_days += 1
                d = datetime.strptime(check_date, "%Y-%m-%d")
                d -= timedelta(days=1)
                check_date = d.strftime("%Y-%m-%d")
            else:
                break

    # Personality confidence
    profile_result = await db.execute(
        select(PersonalityProfile).where(PersonalityProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()

    return CompanionStatsResponse(
        total_messages=total_messages,
        streak_days=streak_days,
        last_chat_date=last_chat_date,
        personality_confidence=profile.confidence_score if profile else 0.0,
    )

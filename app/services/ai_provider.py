"""
Multi-provider AI abstraction — Gemini, OpenAI, and Anthropic.

Provides a unified streaming interface for companion chat, trait extraction,
summary generation, and mood analysis.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Callable, Awaitable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.admin import AdminConfig

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────

ChatMessage = dict  # {"role": "user"|"assistant"|"system", "content": str}


# ── Config Loader ────────────────────────────────────────────

class AIConfig:
    """AI configuration loaded from admin_config table."""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key_openai: str = "",
        api_key_gemini: str = "",
        api_key_anthropic: str = "",
        prompt_overrides: dict[str, str] | None = None,
    ):
        self.model = model
        self.api_key_openai = api_key_openai
        self.api_key_gemini = api_key_gemini
        self.api_key_anthropic = api_key_anthropic
        self.prompt_overrides = prompt_overrides or {}

    @classmethod
    async def load(cls, db: AsyncSession) -> AIConfig:
        """Load AI config from the database admin_config table."""
        settings = get_settings()
        try:
            result = await db.execute(select(AdminConfig))
            rows = result.scalars().all()
            cfg = {r.key: r.value for r in rows}
            return cls(
                model=cfg.get("model", settings.default_ai_model),
                api_key_openai=cfg.get("api_key_openai", settings.openai_api_key),
                api_key_gemini=cfg.get("api_key_gemini", settings.gemini_api_key),
                api_key_anthropic=cfg.get("api_key_anthropic", settings.anthropic_api_key),
                prompt_overrides={
                    "girlfriend": cfg.get("prompt_girlfriend", ""),
                    "boyfriend": cfg.get("prompt_boyfriend", ""),
                    "friend": cfg.get("prompt_friend", ""),
                    "relationship_guru": cfg.get("prompt_relationship_guru", ""),
                },
            )
        except Exception:
            return cls(
                model=settings.default_ai_model,
                api_key_openai=settings.openai_api_key,
                api_key_gemini=settings.gemini_api_key,
                api_key_anthropic=settings.anthropic_api_key,
            )


# ── Streaming Providers ─────────────────────────────────────

async def _stream_gemini(
    system_prompt: str,
    messages: list[ChatMessage],
    config: AIConfig,
) -> AsyncIterator[str]:
    """Stream via Google Gemini."""
    import google.generativeai as genai

    if not config.api_key_gemini:
        raise ValueError("Gemini API key not configured. Add it in Admin → API Keys.")

    genai.configure(api_key=config.api_key_gemini)
    model = genai.GenerativeModel(config.model, system_instruction=system_prompt)

    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    response = model.generate_content(contents, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text


async def _stream_openai(
    system_prompt: str,
    messages: list[ChatMessage],
    config: AIConfig,
) -> AsyncIterator[str]:
    """Stream via OpenAI."""
    import openai

    if not config.api_key_openai:
        raise ValueError("OpenAI API key not configured. Add it in Admin → API Keys.")

    client = openai.AsyncOpenAI(api_key=config.api_key_openai)

    full_messages = [{"role": "system", "content": system_prompt}]
    full_messages.extend(messages)

    stream = await client.chat.completions.create(
        model=config.model,
        messages=full_messages,
        stream=True,
        max_completion_tokens=512,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices[0].delta else None
        if delta:
            yield delta


async def _stream_anthropic(
    system_prompt: str,
    messages: list[ChatMessage],
    config: AIConfig,
) -> AsyncIterator[str]:
    """Stream via Anthropic Claude."""
    import anthropic

    if not config.api_key_anthropic:
        raise ValueError("Anthropic API key not configured. Add it in Admin → API Keys.")

    client = anthropic.AsyncAnthropic(api_key=config.api_key_anthropic)

    chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    async with client.messages.stream(
        model=config.model,
        system=system_prompt,
        messages=chat_messages,
        max_tokens=512,
    ) as stream:
        async for text in stream.text_stream:
            yield text


# ── Unified Interface ────────────────────────────────────────

async def stream_conversation(
    system_prompt: str,
    messages: list[ChatMessage],
    config: AIConfig,
    on_token: Callable[[str], Awaitable[None]] | None = None,
) -> str:
    """
    Stream a conversation with the configured AI provider.

    Args:
        system_prompt: System prompt for the AI.
        messages: Chat history as list of {"role": ..., "content": ...}.
        config: AI provider configuration.
        on_token: Optional async callback for each streamed token.

    Returns:
        The full response text.
    """
    model = config.model
    full_response = ""

    # Select provider based on model prefix
    if model.startswith("gemini"):
        provider = _stream_gemini
    elif model.startswith("claude"):
        provider = _stream_anthropic
    else:
        provider = _stream_openai

    async for token in provider(system_prompt, messages, config):
        full_response += token
        if on_token:
            await on_token(token)

    return full_response


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    config: AIConfig,
    max_tokens: int = 500,
) -> str:
    """
    Non-streaming completion for JSON extraction tasks (trait extraction, mood, summaries).

    Returns the raw response text (expected to be valid JSON).
    """
    model = config.model

    if model.startswith("gemini"):
        import google.generativeai as genai
        genai.configure(api_key=config.api_key_gemini)
        gmodel = genai.GenerativeModel(model, system_instruction=system_prompt)
        response = gmodel.generate_content(user_prompt)
        return response.text or "{}"

    elif model.startswith("claude"):
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=config.api_key_anthropic)
        response = await client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text if response.content else "{}"

    else:
        import openai
        client = openai.AsyncOpenAI(api_key=config.api_key_openai)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=max_tokens,
        )
        return response.choices[0].message.content or "{}"

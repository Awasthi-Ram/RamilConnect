"""
Embedding utilities — convert text to vector embeddings for RAC.

Supports OpenAI text-embedding-3-small and Google Gemini embeddings.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIM = 1536


async def get_embedding_openai(text: str) -> List[float]:
    """Get embedding via OpenAI text-embedding-3-small."""
    import openai

    settings = get_settings()
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding


async def get_embedding_gemini(text: str) -> List[float]:
    """Get embedding via Google Gemini embedding model."""
    import google.generativeai as genai

    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)

    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",
    )
    embedding = result["embedding"]

    # Pad or truncate to match our standard dimension (1536)
    if len(embedding) < EMBEDDING_DIM:
        embedding = embedding + [0.0] * (EMBEDDING_DIM - len(embedding))
    elif len(embedding) > EMBEDDING_DIM:
        embedding = embedding[:EMBEDDING_DIM]

    return embedding


async def get_embedding(text: str) -> List[float]:
    """
    Get embedding using the best available provider.

    Priority: OpenAI → Gemini → Zero vector fallback.
    """
    settings = get_settings()

    # Truncate very long texts to prevent token overflow
    if len(text) > 8000:
        text = text[:8000]

    try:
        if settings.openai_api_key:
            return await get_embedding_openai(text)
        elif settings.gemini_api_key:
            return await get_embedding_gemini(text)
        else:
            logger.warning("No embedding API key configured — returning zero vector")
            return [0.0] * EMBEDDING_DIM
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return [0.0] * EMBEDDING_DIM


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(dot / norm)

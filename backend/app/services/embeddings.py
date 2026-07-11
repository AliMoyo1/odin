from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI, RateLimitError, APIStatusError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import EmbeddingConfig

logger = logging.getLogger(__name__)

_MAX_BATCH = 100
_MAX_RETRIES = 3


async def get_active_config(session: AsyncSession) -> EmbeddingConfig | None:
    result = await session.execute(
        select(EmbeddingConfig).where(EmbeddingConfig.is_active == True)
    )
    return result.scalar_one_or_none()


async def embed_texts(
    texts: list[str],
    config: EmbeddingConfig,
) -> list[list[float]]:
    """Embed `texts` using the active config. Returns one vector per text."""
    if not texts:
        return []

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set; cannot embed")

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    all_vectors: list[list[float]] = []

    for batch_start in range(0, len(texts), _MAX_BATCH):
        batch = texts[batch_start : batch_start + _MAX_BATCH]

        for attempt in range(_MAX_RETRIES):
            try:
                response = await client.embeddings.create(
                    model=config.model_name,
                    input=batch,
                )
                break
            except (RateLimitError, APIStatusError) as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise
                wait = 2 ** attempt
                logger.warning("Embedding API error (attempt %d): %s; retrying in %ds", attempt + 1, exc, wait)
                await asyncio.sleep(wait)

        for item in response.data:
            vec = item.embedding
            if len(vec) != config.dimensions:
                raise ValueError(
                    f"Dimension mismatch: expected {config.dimensions}, got {len(vec)} "
                    f"from model {config.model_name}. "
                    "Update the embedding_config table if the model changed."
                )
            all_vectors.append(vec)

    return all_vectors


async def embed_chunks(
    texts: list[str],
    config: EmbeddingConfig,
) -> list[list[float]]:
    """Convenience wrapper used by the indexing task."""
    return await embed_texts(texts, config)


async def embed_query(query: str, config: EmbeddingConfig) -> list[float]:
    """Embed a single search query string."""
    vectors = await embed_texts([query], config)
    return vectors[0]

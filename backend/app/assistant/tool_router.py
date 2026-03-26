"""Embedding-based tool routing — hybrid keyword + semantic similarity."""

from __future__ import annotations

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded cache for tool embeddings
_tool_embeddings: list[list[float]] | None = None
_tool_names: list[str] = []
_tool_descriptions: list[str] = []


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors (pure Python, no numpy)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _build_tool_embeddings(
    tools: list[dict[str, Any]],
) -> tuple[list[list[float]], list[str], list[str]]:
    """Embed all tool descriptions once (cached at module level)."""
    from app.assistant.rag.embeddings import OllamaEmbeddings

    embedder = OllamaEmbeddings()
    names: list[str] = []
    descriptions: list[str] = []
    for t in tools:
        fn = t.get("function", {})
        name = fn.get("name", "")
        desc = fn.get("description", "")
        names.append(name)
        # Build a richer text for embedding: name + description + param names
        params = fn.get("parameters", {}).get("properties", {})
        param_text = " ".join(params.keys()) if params else ""
        descriptions.append(f"{name}: {desc} {param_text}")

    embeddings = await embedder.embed_batch(descriptions)
    return embeddings, names, descriptions


async def embedding_route(
    message: str,
    all_tools: list[dict[str, Any]],
    top_k: int = 10,
    min_score: float = 0.25,
) -> set[str]:
    """Return tool names ranked by embedding similarity to the user message."""
    global _tool_embeddings, _tool_names, _tool_descriptions

    try:
        from app.assistant.rag.embeddings import OllamaEmbeddings

        # Build cache on first call
        if _tool_embeddings is None or len(_tool_names) != len(all_tools):
            _tool_embeddings, _tool_names, _tool_descriptions = (
                await _build_tool_embeddings(all_tools)
            )

        embedder = OllamaEmbeddings()
        msg_embedding = await embedder.embed_text(message)

        # Score each tool
        scores: list[tuple[str, float]] = []
        for i, tool_emb in enumerate(_tool_embeddings):
            sim = _cosine_similarity(msg_embedding, tool_emb)
            scores.append((_tool_names[i], sim))

        scores.sort(key=lambda x: x[1], reverse=True)

        selected = {name for name, score in scores[:top_k] if score >= min_score}
        return selected

    except Exception:  # policy: LOSSY — routing heuristics can fall back to the safe default tool set
        logger.warning("Embedding routing failed, returning empty set", exc_info=True)
        return set()


def invalidate_cache() -> None:
    """Reset the cached embeddings (call when tools change)."""
    global _tool_embeddings, _tool_names, _tool_descriptions
    _tool_embeddings = None
    _tool_names = []
    _tool_descriptions = []

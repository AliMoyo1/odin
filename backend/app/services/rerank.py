from __future__ import annotations

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(_MODEL_NAME)
    return _model


def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Re-score `chunks` against `query` using a cross-encoder. Returns top_k by score."""
    model = _get_model()
    pairs = [(query, c["content"]) for c in chunks]
    scores: list[float] = model.predict(pairs).tolist()
    scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

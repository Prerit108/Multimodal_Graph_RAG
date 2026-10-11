"""Cross-encoder reranker (CPU-safe) + BM25 hybrid retrieval, via LangChain only.

GPU VRAM (~1GB free, rest held by LM Studio) -> force CPU for the reranker.
Chain: dense (Chroma) + BM25 (rank-bm25, in-memory over collection) -> union
-> cross-encoder rerank on CPU -> top-k. Graceful fallback to keyword overlap
if torch/sentence-transformers weights can't load offline.
"""
from __future__ import annotations
import re
from functools import lru_cache
from langchain_core.documents import Document
from src.config.settings import get_settings

_tok = lambda t: re.findall(r"\w+", t.lower())


@lru_cache(maxsize=1)
def get_reranker():
    """CrossEncoder on CPU. Returns None if deps/weights unavailable (offline-safe)."""
    try:
        from sentence_transformers import CrossEncoder
        s = get_settings()
        return CrossEncoder(s.RERANKER_MODEL, device=s.RERANKER_DEVICE)
    except Exception as e:
        print(f"[rerank] cross-encoder unavailable ({e}); using keyword fallback")
        return None


def bm25_search(query: str, docs: list[Document], k: int) -> list[Document]:
    """In-memory BM25 over the collection snapshot (rank-bm25 is already a dep)."""
    if not docs:
        return []
    try:
        from rank_bm25 import BM25Okapi
        corpus = [_tok(d.page_content) for d in docs]
        scores = BM25Okapi(corpus).get_scores(_tok(query))
        ranked = sorted(zip(scores, docs), key=lambda x: -x[0])
        return [d for sc, d in ranked[:k] if sc > 0] or [d for _, d in ranked[:k]]
    except Exception:
        return docs[:k]


def rerank(query: str, docs: list[Document], k: int) -> list[Document]:
    """Cross-encoder rerank on CPU; keyword-overlap fallback."""
    if not docs:
        return []
    ce = get_reranker()
    if ce is not None:
        try:
            scores = ce.predict([(query, d.page_content[:2000]) for d in docs])
            ranked = sorted(zip(scores, docs), key=lambda x: -x[0])
            return [d for _, d in ranked[:k]]
        except Exception as e:
            print(f"[rerank] predict failed ({e}); keyword fallback")
    qset = set(_tok(query))

    def score(d: Document) -> float:
        return len(qset & set(_tok(d.page_content))) / max(1, len(qset))
    ranked = sorted(docs, key=score, reverse=True)
    return ranked[:k] if ranked and score(ranked[0]) > 0 else docs[:k]

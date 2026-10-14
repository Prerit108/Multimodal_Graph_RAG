"""Vector store via LangChain only. Chroma default (installed); Qdrant optional."""
from __future__ import annotations
import shutil
import sqlite3
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from src.chains.models import get_embeddings
from src.config.settings import get_settings

_store = None


def _reset_if_corrupt(dirpath: str) -> bool:
    """Drop a Chroma directory whose sqlite file was left without its schema.

    An interrupted run (Ctrl+C during first init, a killed process, a version
    change) can leave a 0-byte `chroma.sqlite3`. Chroma then fails on every
    later call with `no such table: collections` and retrying never recovers,
    because the file is created on open but the schema write never committed.
    Wiping it lets Chroma rebuild cleanly.

    Guarded: this only fires when the `collections` table is genuinely absent,
    so a real index is never destroyed.
    """
    db = Path(dirpath) / "chroma.sqlite3"
    if not db.exists():
        return False
    try:
        con = sqlite3.connect(db)
        try:
            rows = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='collections'"
            ).fetchall()
        finally:
            con.close()
        if rows:
            return False
        print(f"[chroma] {db} has no metadata tables (corrupt); rebuilding vector store")
    except sqlite3.DatabaseError:
        print(f"[chroma] {db} is unreadable; rebuilding vector store")
    shutil.rmtree(dirpath, ignore_errors=True)
    return True


def get_store():
    global _store
    if _store is not None:
        return _store
    s = get_settings()
    if s.VECTOR_BACKEND == "qdrant":
        from langchain_qdrant import QdrantVectorStore  # optional dep
        _store = QdrantVectorStore.from_existing_collection(
            embedding=get_embeddings(), collection_name=s.COLLECTION, url=s.QDRANT_URL)
    else:
        _reset_if_corrupt(s.CHROMA_DIR)
        _store = Chroma(collection_name=s.COLLECTION,
                        embedding_function=get_embeddings(),
                        persist_directory=s.CHROMA_DIR)
    return _store


def add_documents(docs: list[Document]) -> list[str]:
    return get_store().add_documents(docs)


def hybrid_search(query: str, k: int = 6, topic: str | None = None) -> list[Document]:
    """Dense (Chroma) + BM25 (in-memory) -> cross-encoder rerank on CPU -> top-k."""
    from src.chains.reranker import bm25_search, rerank
    s = get_settings()
    if s.VECTOR_BACKEND != "qdrant" and not Path(s.CHROMA_DIR).exists():
        return []

    store = get_store()
    filt = {"topic": topic} if topic else None
    dense: list[Document] = []
    try:
        dense = store.similarity_search(query, k=max(s.RERANKER_TOPN, k * 2), filter=filt)
    except Exception:
        dense = []
    corpus: list[Document] = dense
    if not corpus:
        # corpus snapshot fallback (also feeds BM25)
        try:
            snap = store.get()
            all_docs = snap.get("documents", []) or []
            metas = snap.get("metadatas", []) or []
            corpus = [Document(page_content=t, metadata=m or {}) for t, m in zip(all_docs, metas)]
            if topic:
                corpus = [d for d in corpus if d.metadata.get("topic") == topic]
        except Exception:
            return []
    if not corpus:
        return []
    cands = list(dense)
    if s.USE_BM25:
        for d in bm25_search(query, corpus, s.RERANKER_TOPN):
            if all(d.page_content != c.page_content for c in cands):
                cands.append(d)
    return rerank(query, cands, k)


def _rerank(query: str, docs: list[Document], k: int) -> list[Document]:
    import re
    qtok = set(re.findall(r"\w+", query.lower()))
    def score(d: Document) -> float:
        dtok = set(re.findall(r"\w+", d.page_content.lower()))
        return len(qtok & dtok) / max(1, len(qtok))
    ranked = sorted(docs, key=score, reverse=True)
    return ranked[:k] if ranked and score(ranked[0]) > 0 else docs[:k]

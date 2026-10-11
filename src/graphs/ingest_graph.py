"""G0 IngestionGraph: load -> split -> tag -> embed_upsert -> graph edges."""
from __future__ import annotations
import os, hashlib
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.config.settings import get_settings


class IngestState(TypedDict):
    file: str
    kind: str                      # pdf | slides | video_txt
    raw_docs: list
    units: list                    # list[dict citation payload + text]
    errors: list


def _kind(path: str) -> str:
    p = path.lower()
    if p.endswith((".pptx", ".ppt")):
        return "slides"
    if p.endswith((".txt", ".srt", ".vtt")):
        return "video_txt"
    return "pdf"


def n_load(state: IngestState) -> IngestState:
    path = state["file"]
    kind = _kind(path)
    state["kind"] = kind
    docs: list[Document] = []
    try:
        if kind == "slides":
            from pptx import Presentation
            prs = Presentation(path)
            for i, s in enumerate(prs.slides, 1):
                text = "\n".join(sh.text for sh in s.shapes if hasattr(sh, "text"))
                docs.append(Document(page_content=f"Slide {i}: {text}",
                                     metadata={"source_file": os.path.basename(path),
                                               "slide": i, "content_type": "slide"}))
        elif kind == "video_txt":
            txt = open(path, encoding="utf-8", errors="ignore").read()
            docs.append(Document(page_content=txt,
                                 metadata={"source_file": os.path.basename(path),
                                           "content_type": "video", "t_start": 0.0}))
        else:  # pdf via Docling (primary)
            try:
                from langchain_docling import DoclingLoader
                loader = DoclingLoader(file_path=path)
                docs = loader.load()
                for d in docs:
                    d.metadata.setdefault("source_file", os.path.basename(path))
                    d.metadata.setdefault("content_type", "textbook")
                    if "page" not in d.metadata and "page_number" in d.metadata:
                        d.metadata["page"] = d.metadata.pop("page_number")
            except Exception:
                from pypdf import PdfReader
                r = PdfReader(path)
                for i, pg in enumerate(r.pages, 1):
                    docs.append(Document(page_content=pg.extract_text() or "",
                                         metadata={"source_file": os.path.basename(path),
                                                   "page": i, "content_type": "textbook"}))
    except Exception as e:
        state["errors"].append(str(e))
    state["raw_docs"] = docs
    return state


def n_split(state: IngestState) -> IngestState:
    s = get_settings()
    if state["kind"] == "slides":      # 1 slide = 1 unit, no further split
        state["units"] = [{"text": d.page_content, **d.metadata, "topic": "general"}
                          for d in state["raw_docs"]]
        return state
    sp = RecursiveCharacterTextSplitter(chunk_size=s.CHUNK_SIZE, chunk_overlap=s.CHUNK_OVERLAP)
    chunks = sp.split_documents(state["raw_docs"])
    state["units"] = [{"text": c.page_content, **c.metadata, "topic": c.metadata.get("topic", "general")}
                      for c in chunks]
    return state


def n_tag(state: IngestState) -> IngestState:
    """Heuristic tagger (offline-safe). LLM tag_chain used when API keys exist."""
    s = get_settings()
    use_llm = bool(s.GOOGLE_API_KEY or s.OPENAI_API_KEY)
    if use_llm:
        try:
            from src.chains.prompts import get_tag_chain
            chain = get_tag_chain()
            for u in state["units"][:50]:  # cap LLM cost
                try:
                    cu = chain.invoke({"source_file": u.get("source_file", ""),
                                       "page": u.get("page"), "slide": u.get("slide"),
                                       "t_start": u.get("t_start"), "t_end": u.get("t_end"),
                                       "content": u["text"][:2000]})
                    u.update(cu.model_dump(exclude_none=True))
                except Exception:
                    pass
            return state
        except Exception:
            pass
    for u in state["units"]:  # fallback tags
        u.setdefault("difficulty", "medium")
        u.setdefault("subtopic", "")
        u.setdefault("concept", u.get("topic", "general"))
    return state


def n_upsert(state: IngestState) -> IngestState:
    from src.stores.vector import add_documents
    docs = [Document(page_content=u["text"],
                     metadata={k: v for k, v in u.items() if k != "text" and v is not None})
            for u in state["units"] if u.get("text", "").strip()]
    if docs:
        add_documents(docs)
    return state


def n_graph(state: IngestState) -> IngestState:
    from src.stores.graph import add_topic_edge
    for u in state["units"]:
        if u.get("concept"):
            add_topic_edge(u["concept"], prereq=u.get("subtopic", ""),
                           topic=u.get("topic", "general"))
    return state


def build_ingest_graph():
    g = StateGraph(IngestState)
    g.add_node("load", n_load); g.add_node("split", n_split)
    g.add_node("tag", n_tag); g.add_node("upsert", n_upsert); g.add_node("graph", n_graph)
    g.set_entry_point("load")
    g.add_edge("load", "split"); g.add_edge("split", "tag")
    g.add_edge("tag", "upsert"); g.add_edge("upsert", "graph"); g.add_edge("graph", END)
    return g.compile()


def ingest_file(path: str) -> dict:
    return build_ingest_graph().invoke({"file": path, "kind": "", "raw_docs": [], "units": [], "errors": []})

"""G0 IngestionGraph: load -> split -> tag -> embed_upsert -> graph edges."""
from __future__ import annotations
import os, hashlib, re
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


def _clean_text(text: str) -> str:
    """Strip headers/footers, TOC lines, URLs, table signatures from raw text."""
    # Remove very common header/footer patterns
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip pure URL lines
        if re.match(r"^https?://\S+", stripped, re.I):
            continue
        # Skip lines that are just page numbers or TOC entries
        if re.match(r"^\s*page\s*\d+|\d+/\d+|contents|table of contents", stripped, re.I):
            continue
        # Skip lines with table signatures like "Name Type Description..."
        if re.match(r"^(Name|ID|Score|Type|Description|CreationDate|DateTime)\s", stripped, re.I):
            continue
        # Skip lines with .com/qa or .com: patterns that are doc references
        if re.search(r"\.com(?:/qa)?:", stripped, re.I):
            continue
        # Skip very short lines (likely artifacts)
        if len(stripped) < 3:
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)


def _parse_video_timestamps(txt: str) -> list[dict]:
    """Parse SRT/VTT timestamps into 30-60s windows."""
    windows = []
    # Simple parsing - split into segments based on typical SRT format
    # Each segment: number, timestamp (-->), text
    segments = re.split(r"\d{2}:\d{2}:\d{2}[\s,]*-->\s*\d{2}:\d{2}:\d{2}[,\s]\d+", txt)
    current_time = 0.0
    window_size = 45  # seconds
    
    # Find all timestamp lines
    timestamp_pattern = r"\d{2}:\d{2}:\d{2}[,\s]\d+"
    positions = [m.start() for m in re.finditer(timestamp_pattern, txt)]
    
    for i, pos in enumerate(positions):
        if i + 1 < len(positions):
            start_txt = txt[pos:positions[i+1]]
        else:
            start_txt = txt[pos:]
        
        # Extract the actual time
        ts_match = re.match(r"(\d{2}:\d{2}:\d{2}[,\s]\d+)", start_txt)
        if ts_match:
            time_str = ts_match.group(1)
            # Parse HH:MM:SS,ms
            parts = re.split(r'[:,]', time_str)
            h, m, s_ms = int(parts[0]), int(parts[1]), int(parts[2])
            start_sec = h * 3600 + m * 60 + s_ms / 1000
            
            # Find the text after the timestamp until next timestamp or end
            text_start = start_txt[ts_match.end():]
            next_ts = positions[i+1] if i + 1 < len(positions) else len(txt)
            text_segment = txt[next_ts - len(text_start):next_ts] if len(text_start) < 200 else text_start[:200]
            
            windows.append({
                "t_start": start_sec,
                "t_end": start_sec + window_size,
                "text": text_segment
            })
    
    return windows


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
                # Clean the text
                text = _clean_text(text)
                docs.append(Document(page_content=f"Slide {i}: {text}",
                                     metadata={"source_file": os.path.basename(path),
                                               "slide": i, "content_type": "slide"}))
        elif kind == "video_txt":
            txt = open(path, encoding="utf-8", errors="ignore").read()
            # Parse into timestamp windows
            windows = _parse_video_timestamps(txt)
            if windows:
                for w in windows[:20]:  # cap at 20 windows
                    docs.append(Document(page_content=w["text"],
                                        metadata={"source_file": os.path.basename(path),
                                                  "content_type": "video", "t_start": w["t_start"],
                                                  "t_end": w["t_end"]}))
            else:
                # Fallback: whole transcript
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
                # Clean each doc's text
                for d in docs:
                    d.page_content = _clean_text(d.page_content)
            except Exception:
                from pypdf import PdfReader
                r = PdfReader(path)
                for i, pg in enumerate(r.pages, 1):
                    txt = _clean_text(pg.extract_text() or "")
                    docs.append(Document(page_content=txt,
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
    # Per-page splitting for PDFs, with junk filtering
    if state["kind"] == "pdf":
        sp = RecursiveCharacterTextSplitter(chunk_size=s.CHUNK_SIZE, chunk_overlap=s.CHUNK_OVERLAP)
        chunks = sp.split_documents(state["raw_docs"])
        # Post-process: drop chunks that are pure table headers or <200 chars
        cleaned_units = []
        for c in chunks:
            meta = dict(c.metadata)
            # Drop chunks that are likely table headers
            if re.match(r"^(Name|ID|Score|Type|Description|CreationDate|DateTime)\s", c.page_content.strip(), re.I):
                continue
            if len(c.page_content.strip()) < 200:
                continue
            # Ensure page is preserved
            if "page" not in meta:
                meta["page"] = c.metadata.get("page", "unknown")
            cleaned_units.append({"text": c.page_content, **meta, "topic": meta.get("topic", "general")})
        state["units"] = cleaned_units
        return state
    # For video_txt, create units from timestamp windows
    if state["kind"] == "video_txt":
        state["units"] = [{"text": u["text"], **u, "topic": "video_content"}
                          for u in state["raw_docs"] if isinstance(u, dict) and u.get("text", "").strip()]
        return state
    # Generic fallback
    sp = RecursiveCharacterTextSplitter(chunk_size=s.CHUNK_SIZE, chunk_overlap=s.CHUNK_OVERLAP)
    chunks = sp.split_documents(state["raw_docs"])
    state["units"] = [{"text": c.page_content, **c.metadata, "topic": c.metadata.get("topic", "general")}
                      for c in chunks]
    return state


def _vlm_caption_image(image_data: bytes, image_format: str, topic_hint: str = "") -> str:
    """Generate a VLM caption for an image. Falls back to basic description if model unavailable."""
    try:
        from src.chains.prompts import get_vlm_caption_chain
        # Prepare base64 image
        import base64
        b64 = base64.b64encode(image_data).decode()
        
        # Use the VLM chain
        chain = get_vlm_caption_chain()
        result = chain.invoke({
            "content_type": "slide",
            "topic": topic_hint,
            "image_b64": b64,
            "image_format": image_format
        })
        # Extract just the caption text
        if isinstance(result, str):
            # Look for "CAPTION:" prefix
            if "CAPTION:" in result.upper():
                idx = result.upper().index("CAPTION:")
                return result[idx + 8:].strip()
            return result.strip()
        return str(result).strip()
    except Exception:
        # Fallback: basic description
        if "chart" in topic_hint.lower() or "graph" in topic_hint.lower():
            return "Educational chart/diagram"
        return "Illustration from course material"


def n_tag(state: IngestState) -> IngestState:
    """Heuristic tagger (offline-safe). LLM tag_chain used when API keys exist."""
    s = get_settings()
    use_llm = bool(s.GOOGLE_API_KEY or s.OPENAI_API_KEY)
    if use_llm:
        try:
            from src.chains.prompts import get_tag_chain
            chain = get_tag_chain()
            # Tag all units, but cap at reasonable number for cost
            for u in state["units"][:80]:
                try:
                    cu = chain.invoke({"source_file": u.get("source_file", ""),
                                       "page": u.get("page"), "slide": u.get("slide"),
                                       "t_start": u.get("t_start"), "t_end": u.get("t_end"),
                                       "content": u["text"][:3000]})
                    u.update(cu.model_dump(exclude_none=True))
                except Exception:
                    pass
            return state
        except Exception:
            pass
    for u in state["units"]:
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

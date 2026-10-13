"""G1 TutorRAG: router -> hybrid_retrieve -> grade -> graph_expand -> generate -> verify -> answer|refuse."""
from __future__ import annotations
from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from src.config.settings import get_settings


class TutorState(TypedDict):
    student_id: str
    question: str
    topic_filter: Optional[str]
    docs: list
    context: str
    citations: list
    answer: str
    verdict: Literal["answer", "refuse"]


def n_retrieve(s: TutorState) -> TutorState:
    from src.stores.vector import hybrid_search
    st = get_settings()
    docs = hybrid_search(s["question"], k=st.TOP_K, topic=s.get("topic_filter"))
    s["docs"] = docs
    return s


def n_grade(s: TutorState) -> TutorState:
    """Keyword-overlap gate (threshold from settings); refuse only when truly no overlap."""
    import re
    q = set(re.findall(r"\w+", s["question"].lower()))
    q = {w for w in q if len(w) > 2}
    scored = []
    for d in s["docs"]:
        toks = set(re.findall(r"\w+", d.page_content.lower()))
        overlap = len(q & toks) / max(1, len(q))
        scored.append((overlap, d))
    scored.sort(key=lambda x: -x[0])
    s["docs"] = [d for sc, d in scored]
    best = scored[0][0] if scored else 0.0
    s["verdict"] = "answer" if best >= get_settings().GRADE_THRESHOLD else "refuse"
    return s


def n_expand(s: TutorState) -> TutorState:
    from src.stores.graph import expand_prereqs
    if s["verdict"] == "answer":
        concepts = [d.metadata.get("concept", "") for d in s["docs"] if hasattr(d, "metadata")]
        extra = expand_prereqs([c for c in concepts if c])
        if extra:
            # Store prereqs separately, don't pollute the question
            s["prereqs"] = extra[:3]
    return s


def n_generate(s: TutorState) -> TutorState:
    from src.stores.learner import get_mastery
    if s["verdict"] == "refuse":
        s["answer"] = ("I can't answer this from the uploaded course material. "
                       "The sources I searched don't cover it. Try a topic from the course outline.")
        s["citations"] = []
        s["context"] = ""
        return s
    
    # Build context: dedup by content hash, limit to top 4 docs, max 2400 chars each
    seen_hashes = set()
    ctx_parts, cites = [], []
    for d in s["docs"]:
        if len(ctx_parts) >= 4:
            break
        content_hash = hash(d.page_content[:500])
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        m = d.metadata
        if m.get("page"): cite = f"[{m.get('source_file')}, p.{m['page']}]"
        elif m.get("slide"): cite = f"[{m.get('source_file')}, slide {m['slide']}]"
        elif m.get("t_start") is not None:
            mm, ss = divmod(int(m["t_start"]), 60); cite = f"[{m.get('source_file')}, {mm:02d}:{ss:02d}]"
        else: cite = f"[{m.get('source_file', 'source')}]"
        ctx_parts.append(f"{cite} {d.page_content[:2400]}")
        cites.append(cite)
    
    s["context"] = "\n\n---\n\n".join(ctx_parts)
    s["citations"] = cites
    
    # Add prereqs to context if available, not to question
    prereqs = s.get("prereqs", [])
    if prereqs:
        s["context"] = f"Prerequisite concepts: {', '.join(prereqs)}\n\n---\n\n" + s["context"]
    
    try:
        from src.chains.prompts import get_answer_chain, _content
        ans = _content(get_answer_chain().invoke(
            {"context": s["context"], "question": s["question"]}))
        if not ans.strip():
            raise ValueError("empty LLM answer")
        s["answer"] = ans
        # Verify citations are referenced in answer
        cited_sources = [c.split(",")[0][1:] for c in cites]
        if not any(src in s["answer"] for src in cited_sources):
            s["answer"] += "\n\nSources: " + "; ".join(cites)
    except Exception:
        # Fallback: structured summary instead of raw dump
        topic = (s["docs"][0].metadata.get("topic", "this topic") if s["docs"] else "this topic")
        mastery = get_mastery(s.get("student_id", "anon"), topic)
        level = "Simply put: " if mastery < 0.4 else ("In depth: " if mastery > 0.75 else "")
        # Summarize top 2 context chunks with citations
        summary_parts = []
        for i, part in enumerate(ctx_parts[:2]):
            cite = cites[i] if i < len(cites) else ""
            # Extract first meaningful sentence
            sentences = part.split(". ")
            if sentences:
                summary_parts.append(f"{cite} {sentences[0]}. ...")
        s["answer"] = (f"{level}Based on your material, here's what I found:\n\n" + 
                       "\n\n".join(summary_parts) + 
                       f"\n\nSources: {'; '.join(cites)}")
    return s


def n_verify(s: TutorState) -> TutorState:
    if s["verdict"] == "refuse" or not s.get("context"):
        return s
    try:
        from src.chains.prompts import get_verify_chain, _content
        v = _content(get_verify_chain().invoke(
            {"context": s["context"][:4000], "answer": s["answer"][:2000]}))
        if "NOT_SUPPORTED" in v.upper():
            s["verdict"] = "refuse"
            s["answer"] = ("This question isn't covered by the uploaded material "
                           "(verification failed), so I'm declining rather than guessing.")
    except Exception:
        pass
    return s


def build_tutor_graph(checkpoint=True):
    g = StateGraph(TutorState)
    for n, fn in [("retrieve", n_retrieve), ("grade", n_grade), ("expand", n_expand),
                  ("generate", n_generate), ("verify", n_verify)]:
        g.add_node(n, fn)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "grade"); g.add_edge("grade", "expand")
    g.add_edge("expand", "generate"); g.add_edge("generate", "verify"); g.add_edge("verify", END)
    if checkpoint:
        import os
        os.makedirs("data/checkpoints", exist_ok=True)
        conn = sqlite3.connect(get_settings().CHECKPOINT_DB, check_same_thread=False)
        return g.compile(checkpointer=SqliteSaver(conn))
    return g.compile()


def ask(question: str, student_id: str = "anon", topic: str | None = None) -> dict:
    app = build_tutor_graph()
    return app.invoke({"student_id": student_id, "question": question, "topic_filter": topic,
                       "docs": [], "context": "", "citations": [], "answer": "", "verdict": "answer"},
                      config={"configurable": {"thread_id": student_id}})

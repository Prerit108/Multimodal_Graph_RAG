"""G1 TutorRAG: router -> hybrid_retrieve -> grade -> graph_expand -> generate -> verify -> answer|refuse."""
from __future__ import annotations
import re
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
    """Keyword-overlap gate (threshold from settings); refuse only when truly no overlap.

    Common words are dropped first — otherwise filler like "the/won/world" in ordinary
    book prose can clear the threshold for an off-topic question.
    """
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "what", "which",
            "who", "whom", "whose", "how", "why", "when", "where", "are", "was", "were",
            "does", "did", "can", "could", "would", "should", "have", "has", "had",
            "you", "your", "our", "their", "they", "them", "its", "his", "her"}
    q = {w for w in re.findall(r"\w+", s["question"].lower()) if len(w) > 2 and w not in stop}
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
            s["question"] = s["question"] + f" (prereqs: {', '.join(extra[:3])})"
    return s


def _citation(doc) -> str:
    """Precise audit citation, e.g. '[notes.pdf, p.12]' (kept out of the answer body)."""
    m = doc.metadata
    if m.get("page"): return f"[{m.get('source_file')}, p.{m['page']}]"
    if m.get("slide"): return f"[{m.get('source_file')}, slide {m['slide']}]"
    if m.get("t_start") is not None:
        mm, ss = divmod(int(m["t_start"]), 60)
        return f"[{m.get('source_file')}, {mm:02d}:{ss:02d}]"
    return f"[{m.get('source_file', 'source')}]"


def _source_names(cites: list[str]) -> list[str]:
    """Distinct source filenames from audit citations, order preserved."""
    names, seen = [], set()
    for c in cites:
        name = re.sub(r"^\[|\]$", "", c).split(",")[0].strip() or "source"
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _source_note(cites: list[str]) -> str:
    """Compact, readable note: 'notes.pdf; book.pdf' — no page/slide clutter."""
    return "; ".join(_source_names(cites))


def _strip_inline_cites(ans: str, cites: list[str]) -> str:
    """Drop '[file.pdf, p.12]' style markers the model may still emit, keep prose clean."""
    names = _source_names(cites)
    if not names:
        return ans
    alt = "|".join(re.escape(n) for n in names)
    ans = re.sub(rf"\s*[\[(]\s*(?:{alt})[^\])]*[\])]", "", ans, flags=re.I)
    ans = re.sub(r"[ \t]{2,}", " ", ans)
    ans = re.sub(r"\s+([.,;:!?])", r"\1", ans)       # " ." -> "."
    ans = re.sub(r"([(\[])\s+", r"\1", ans)
    return ans.strip()


def _readable(text: str) -> str:
    """Collapse the hard line-wraps and column padding that PDF chunks carry."""
    return " ".join(text.split())


def n_generate(s: TutorState) -> TutorState:
    from src.stores.learner import get_mastery
    if s["verdict"] == "refuse":
        s["answer"] = ("I can't answer this from the uploaded course material. "
                       "The sources I searched don't cover it. Try a topic from the course outline.")
        s["citations"] = []
        s["context"] = ""
        return s
    docs = s["docs"][:6]
    cites = [_citation(d) for d in docs]
    # Context is fed WITHOUT citation markers — inline '[file, p.N]' prefixes are what
    # used to leak into the middle of every sentence and made answers unreadable.
    s["context"] = "\n\n---\n\n".join(d.page_content[:1200] for d in docs)
    s["citations"] = cites
    note = _source_note(cites)
    try:
        from src.chains.prompts import get_answer_chain, _content
        ans = _content(get_answer_chain().invoke(
            {"context": s["context"], "question": s["question"]}))
        if not ans.strip():
            raise ValueError("empty LLM answer")
        ans = _strip_inline_cites(ans, cites)
        if note:
            ans = f"{ans}\n\nSources: {note}"
        s["answer"] = ans
    except Exception:
        topic = (s["docs"][0].metadata.get("topic", "this topic") if s["docs"] else "this topic")
        mastery = get_mastery(s.get("student_id", "anon"), topic)
        level = "Simply put: " if mastery < 0.4 else ("In depth: " if mastery > 0.75 else "")
        # dedupe near-identical chunks, then flatten the PDF line-wrapping
        body, seen_txt = [], set()
        for d in docs[:3]:
            flat = _readable(d.page_content)
            if not flat or flat in seen_txt:
                continue
            seen_txt.add(flat)
            body.append(flat)
        s["answer"] = (f"{level}" + "\n\n".join(body)
                       + (f"\n\nSources: {note}" if note else ""))
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

"""Durable per-student session history: tutor turns, quiz attempts, uploads.

Streamlit's `st.session_state` dies with the browser session, so every
interaction has to be written here as it happens. The store is a single JSONL
file per student — append-only, human-readable, and cheap to tail.

Schema (one JSON object per line). `type` is the event name; note that an
upload event also carries a document `kind`, which is a *different* field:
    {"type": "chat",    "ts": <epoch>, "question": str, "answer": str,
                        "verdict": str, "citations": [str], "topic": str|None}
    {"type": "quiz",    "ts": <epoch>, "quiz_id": str, "scope": str,
                        "requested": int, "generated": int,
                        "questions": [{"stem","answer_key","source","difficulty","qhash"}]}
    {"type": "grade",   "ts": <epoch>, "quiz_id": str, "scope": str,
                        "score": "2/3", "correct": int, "total": int,
                        "weak_topics": [str], "details": [ {...} ]}
    {"type": "upload",  "ts": <epoch>, "file": str, "kind": "pdf|slides|image",
                        "units": int, "errors": [str]}
"""
from __future__ import annotations
import json, os, time, uuid
from typing import Any

MAX_DETAIL_CHARS = 20000   # hard cap so one runaway answer can't bloat the file
PREVIEW_CHARS = 400         # compact preview length, applied at render time only


def _dir() -> str:
    return "data/checkpoints/history"


def _path(student: str) -> str:
    safe = "".join(c for c in (student or "anon") if c.isalnum() or c in "-_.") or "anon"
    return os.path.join(_dir(), f"{safe}.jsonl")


def _trim(obj: dict) -> dict:
    """Cap pathological values only.

    Answers are stored in full — truncation happens when rendering, so the
    'full transcript' view can always show the complete text.
    """
    for k in ("answer",):
        if isinstance(obj.get(k), str) and len(obj[k]) > MAX_DETAIL_CHARS:
            obj[k] = obj[k][:MAX_DETAIL_CHARS] + "…"
    if isinstance(obj.get("questions"), list):
        for q in obj["questions"]:
            if isinstance(q, dict):
                for k in ("answer_key", "stem"):
                    if isinstance(q.get(k), str) and len(q[k]) > MAX_DETAIL_CHARS:
                        q[k] = q[k][:MAX_DETAIL_CHARS] + "…"
    if isinstance(obj.get("details"), list):
        for d in obj["details"]:
            if isinstance(d, dict):
                for k in ("key", "given", "feedback"):
                    if isinstance(d.get(k), str) and len(d[k]) > MAX_DETAIL_CHARS:
                        d[k] = d[k][:MAX_DETAIL_CHARS] + "…"
    return obj


def preview(text: str, limit: int = PREVIEW_CHARS) -> str:
    """Shorten for a compact card; returns the input untouched when it fits."""
    t = text or ""
    return t if len(t) <= limit else t[:limit].rstrip() + " …"


def append(student: str, event: str, **fields: Any) -> dict:
    """Record one event. Never raises — history must not break a study session.

    The event type is stored under `type`, never `kind`: ingestion events carry a
    document `kind` of their own ("pdf", "slides"), and collapsing both onto one
    key either raises a TypeError (duplicate keyword argument) or silently
    overwrites the event type so the reader filters never match.
    """
    rec = _trim({"type": event, "ts": time.time(), **fields})
    try:
        os.makedirs(_dir(), exist_ok=True)
        with open(_path(student), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass
    return rec


def new_quiz_id() -> str:
    return uuid.uuid4().hex[:10]


def read(student: str) -> list[dict]:
    """All events for a student, oldest first. Corrupt lines are skipped."""
    p = _path(student)
    out: list[dict] = []
    try:
        if not os.path.exists(p):
            return out
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return out
    return out


def chats(student: str, limit: int | None = None) -> list[dict]:
    rows = [r for r in read(student) if r.get("type") == "chat"]
    return rows[-limit:] if limit else rows


def quizzes(student: str, limit: int | None = None) -> list[dict]:
    rows = [r for r in read(student) if r.get("type") == "quiz"]
    return rows[-limit:] if limit else rows


def grades(student: str, limit: int | None = None) -> list[dict]:
    rows = [r for r in read(student) if r.get("type") == "grade"]
    return rows[-limit:] if limit else rows


def uploads(student: str, limit: int | None = None) -> list[dict]:
    rows = [r for r in read(student) if r.get("type") == "upload"]
    return rows[-limit:] if limit else rows


def clear(student: str) -> None:
    try:
        p = _path(student)
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass
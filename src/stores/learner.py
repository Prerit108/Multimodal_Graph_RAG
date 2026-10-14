"""Custom BKT learner model (no pyBKT dep in env): per-student x topic mastery."""
from __future__ import annotations
import json, os, math, time
from src.config.settings import get_settings

P_INIT, P_LEARN, P_SLIP, P_GUESS, DECAY = 0.30, 0.25, 0.10, 0.20, 0.995
_state: dict = {}
_loaded = False


def _path() -> str:
    return get_settings().BKT_DB


def _norm_topic(topic: str) -> str:
    """Canonical topic key.

    The quiz scope is free text, so 'positional encodings' and
    'positional encodings,' (trailing comma from the UI) were being tracked as two
    different topics — the student saw a duplicate row and mastery was split
    across both instead of accumulating.
    """
    t = " ".join(str(topic or "").split()).strip().strip(".,;:!?-—\"'()[]")
    return t.lower() or "general"


def _load():
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        if os.path.exists(_path()):
            raw = json.load(open(_path()))
            # migrate pre-normalisation keys ("Foo," / "Foo" were separate topics)
            for student, topics in raw.items():
                merged = {}
                for topic, val in (topics or {}).items():
                    k = _norm_topic(topic)
                    if k in merged:
                        prev = merged[k]
                        # keep the strongest estimate so migration never loses progress
                        merged[k] = {"p": max(prev.get("p", P_INIT), val.get("p", P_INIT)),
                                     "t": max(prev.get("t", 0), val.get("t", 0))}
                    else:
                        merged[k] = val
                _state[student] = merged
            _save()
    except Exception:
        pass


def _save():
    try:
        os.makedirs(os.path.dirname(_path()), exist_ok=True)
        json.dump(_state, open(_path(), "w"))
    except Exception:
        pass


def get_mastery(student: str, topic: str) -> float:
    _load()
    return float(_state.get(student, {}).get(_norm_topic(topic), {}).get("p", P_INIT))


def update(student: str, topic: str, correct: bool) -> float:
    """Standard BKT update + time-decay forgetting."""
    _load()
    s = _state.setdefault(student, {}).setdefault(
        _norm_topic(topic), {"p": P_INIT, "t": time.time()})
    p = s["p"] * (DECAY ** max(0, (time.time() - s.get("t", time.time())) / 86400))
    # posterior given observation
    p_obs = (p * (1 - P_SLIP)) / (p * (1 - P_SLIP) + (1 - p) * P_GUESS) if correct else \
            (p * P_SLIP) / (p * P_SLIP + (1 - p) * (1 - P_GUESS))
    s["p"] = p_obs + (1 - p_obs) * P_LEARN
    s["t"] = time.time()
    _save()
    return s["p"]


def all_mastery(student: str) -> dict[str, float]:
    _load()
    return {_norm_topic(t): v["p"] for t, v in _state.get(student, {}).items()}


def difficulty_for(student: str, topic: str) -> str:
    p = get_mastery(student, topic)
    return "easy" if p < 0.4 else ("hard" if p > 0.75 else "medium")

"""Custom BKT learner model (no pyBKT dep in env): per-student x topic mastery."""
from __future__ import annotations
import json, os, math, time
from src.config.settings import get_settings

P_INIT, P_LEARN, P_SLIP, P_GUESS, DECAY = 0.30, 0.25, 0.10, 0.20, 0.995
_state: dict = {}
_loaded = False


def _path() -> str:
    return get_settings().BKT_DB


def _load():
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        if os.path.exists(_path()):
            _state.update(json.load(open(_path())))
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
    return float(_state.get(student, {}).get(topic, {}).get("p", P_INIT))


def update(student: str, topic: str, correct: bool) -> float:
    """Standard BKT update + time-decay forgetting."""
    _load()
    s = _state.setdefault(student, {}).setdefault(topic, {"p": P_INIT, "t": time.time()})
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
    return {t: v["p"] for t, v in _state.get(student, {}).items()}


def difficulty_for(student: str, topic: str) -> str:
    p = get_mastery(student, topic)
    return "easy" if p < 0.4 else ("hard" if p > 0.75 else "medium")

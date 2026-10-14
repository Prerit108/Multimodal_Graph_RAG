"""G2 QuizGraph: scope -> retrieve -> generate -> verify -> dedup -> feedback -> BKT -> report."""
from __future__ import annotations
import hashlib, json, os, re
from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.config.settings import get_settings
from src.schemas.models import QuizQuestion


class QuizState(TypedDict):
    student_id: str
    scope: str
    difficulty_target: str
    n_questions: int
    questions: list
    pool: list                 # leftover candidates kept for top-up after verify/dedup
    results: list
    weak_topics: list
    requested: int             # what the student asked for
    generated: int             # what we could actually build
    shortfall: int             # generated - requested (negative when short)
    shortfall_reason: str      # human-readable explanation when short
    dupes_dropped: int


def n_scope(s: QuizState) -> QuizState:
    from src.stores.learner import difficulty_for
    if s["difficulty_target"] == "auto":
        s["difficulty_target"] = difficulty_for(s["student_id"], s["scope"])
    return s


def _source_link(m: dict) -> str:
    return f"{m.get('source_file','')}" + (f"#page={m['page']}" if m.get("page") else "")


_STEM_PREFIX = re.compile(r"^\s*Q\s*\d+\s*(?:\(\s*[^)]*\s*\)\s*)?[.):]?\s*", re.I)


def _norm_stem(stem: str) -> str:
    """Stem without its 'Qn (difficulty).' prefix and without the trailing
    ': explain in your own words.' boilerplate — the part that actually
    identifies the question."""
    s = _STEM_PREFIX.sub("", (stem or "").strip()).lower()
    s = re.sub(r"\s*:\s*explain in your own words\.?\s*$", "", s)
    return " ".join(s.split())


def _norm_key(key: str) -> str:
    return " ".join((key or "").lower().split())


def _degenerate(concept: str) -> bool:
    """Reject junk concepts produced from formulas/fragments ('n', 'x = 5',
    '[ 13 ]'). These make questions that read as nonsense to a student."""
    c = (concept or "").strip()
    if len(c) < 3 or len(c.split()) < 2:
        return True
    letters = sum(ch.isalpha() for ch in c)
    if letters / max(1, len(c)) < 0.6:      # mostly digits/punctuation
        return True
    if re.fullmatch(r"[\W_\d]+", c):        # pure non-word
        return True
    return False


def _fallback_candidates(docs: list, scope: str, difficulty: str, n: int) -> list:
    """Offline question mining: one per DEFINITIONAL sentence (filtered).

    Raw chapter text contains URLs, fragments, mid-paragraph continuations
    ("Therefore, ...", "com: This Q&A site...") — never quiz those. Relaxes the
    filter once rather than returning nothing when nothing strict qualifies.
    """
    import random
    cand: list = []
    shuffled = list(docs)
    random.shuffle(shuffled)
    seen: set = set()

    def _add(sent: str, d) -> bool:
        concept = _extract_concept(sent)
        if _degenerate(concept):
            return False
        key = _norm_key(sent)
        if key in seen:            # same source sentence mined twice
            return False
        seen.add(key)
        m = d.metadata
        link = _source_link(m)
        cand.append(QuizQuestion(
            qtype="short",
            stem=f"{concept}: explain in your own words.",
            answer_key=sent, topic=m.get("topic", scope), source=link, difficulty=difficulty,
            explanation=f"Key point: {sent[:200]} (See {link})"))
        return len(cand) >= n

    for d in shuffled:
        for sent in _quiz_worthy_sentences(d.page_content):
            if _add(sent, d):
                return cand

    for i, d in enumerate(shuffled):  # relaxed pass: longer sentences, any subject
        sents = [x.strip() for x in d.page_content.split(".") if 60 <= len(x.strip()) <= 300]
        if not sents:
            continue
        sent = " ".join(sents[i % len(sents)].split())[:300]
        if _add(sent, d):
            return cand
    return cand


def _hash(q) -> str:
    """Identity of a question for dedup: normalised stem plus the answer key.

    Hashing the raw stem was the bug that let the same question through twice —
    'Q1 (easy). n: explain…' and 'Q2 (easy). n: explain…' differ only in the
    numbering, so they hashed differently while being the same question.
    """
    basis = _norm_stem(getattr(q, "stem", "") if not isinstance(q, dict) else q["stem"])
    key = getattr(q, "answer_key", "") if not isinstance(q, dict) else q["answer_key"]
    return hashlib.sha256((basis + "||" + _norm_key(key)).encode()).hexdigest()[:12]


def _top_up(s: QuizState, extra: list) -> None:
    """Pad questions back to n_questions. Without this, an under-delivering LLM,
    dedup, and the verifier each shaved the quiz down to an arbitrary length."""
    need = s["n_questions"] - len(s["questions"])
    if need <= 0:
        s["questions"] = s["questions"][:s["n_questions"]]
        return
    have = {q["qhash"] for q in s["questions"]}
    have |= {q.get("qhash") for q in extra if q.get("qhash")}
    for q in extra:  # pool first (unused LLM candidates), then fresh mined ones
        if need <= 0:
            break
        if q.get("qhash"):
            if q["qhash"] in have:
                continue
            have.add(q["qhash"])
        s["questions"].append(q)
        need -= 1


def n_generate(s: QuizState) -> QuizState:
    from src.stores.vector import hybrid_search
    s.setdefault("pool", [])
    n = s["n_questions"]
    # Widen the window with n: a fixed k=6 starves the offline miner, which is what
    # made the returned question count drift below what the student asked for.
    docs = hybrid_search(f"{s['scope']} {s['difficulty_target']} questions",
                         k=max(6, n * 3), topic=None)
    src = docs[0].metadata.get("source_file", "") if docs else ""
    used_llm = False
    pool: list = []
    try:
        from src.chains.prompts import get_quiz_chain, _content
        out = _content(get_quiz_chain().invoke(
            {"n": n, "types": "MCQ/short/numerical",
             "scope": s["scope"], "difficulty": s["difficulty_target"],
             "context": "\n".join(d.page_content[:800] for d in docs)}))
        # parse the whole response; slicing to n here would discard usable questions
        all_cand = _parse_quiz_text(out, scope=s["scope"], difficulty=s["difficulty_target"],
                                    source=src, n=10 ** 6)
        if not all_cand:
            if not out.strip():
                raise ValueError("empty LLM quiz output")  # -> offline fallback
            all_cand = [QuizQuestion(qtype="short", stem=out[:500], answer_key="see context",
                                    topic=s["scope"], source=src, difficulty=s["difficulty_target"],
                                    explanation="Generated from retrieved context.")]
        used_llm = True
    except Exception:
        all_cand = _fallback_candidates(docs, s["scope"], s["difficulty_target"], n * 6)

    # LLM path is authoritative: keep whatever it produced even if hash-seen
    # (dedup bank only gates the deterministic offline fallback).
    seen = set() if used_llm else _load_hashes()
    fresh, dupes = [], 0
    in_run: set = set()            # catch repeats within this same quiz
    for q in all_cand:
        h = _hash(q)
        q.qhash = h
        d = q.model_dump()
        d["qhash"] = h
        if h in in_run:
            dupes += 1
            continue                # never show the same question twice in one quiz
        if h in seen:
            pool.append(d)          # already served before -> reuse as top-up filler
        else:
            seen.add(h)
            in_run.add(h)
            fresh.append(d)
    if not used_llm:
        _save_hashes(seen)
    s["questions"] = fresh[:n]
    pool.extend(fresh[n:])
    s["pool"] = pool
    if len(s["questions"]) < n:
        _top_up(s, list(pool) + [
            {**q.model_dump(), "qhash": _hash(q)}
            for q in _fallback_candidates(docs, s["scope"], s["difficulty_target"], n * 6)
        ])
    s["requested"] = n
    s["generated"] = len(s["questions"])
    s["shortfall"] = max(0, n - len(s["questions"]))
    s["dupes_dropped"] = dupes
    if s["shortfall"]:
        s["shortfall_reason"] = (
            f"Only {s['generated']} distinct question(s) could be built from the "
            f"material retrieved for '{s['scope']}'. Ingest more content on this "
            f"topic, narrow the scope, or lower the count."
            + (f" {dupes} duplicate(s) were discarded." if dupes else "")
        )
    else:
        s["shortfall_reason"] = ""
    return s


def _parse_quiz_text(out: str, scope: str, difficulty: str, source: str, n: int) -> list:
    """Parse 'Q: ... A: ...' (possibly numbered) blocks into QuizQuestions."""
    import re
    cand = []
    blocks = re.split(r"(?m)^\s*(?:\d+[.)]\s*)?Q\s*:", out)
    for b in blocks[1:]:
        parts = re.split(r"(?m)^\s*A\s*:", b, maxsplit=1)
        stem = parts[0].strip()[:400]
        key = parts[1].strip().splitlines()[0][:300] if len(parts) > 1 else "see context"
        if len(stem) < 10:
            continue
        cand.append(QuizQuestion(qtype="short", stem=stem, answer_key=key, topic=scope,
                                 source=source, difficulty=difficulty,
                                 explanation=f"See {source}"))
        if len(cand) >= n:
            break
    return cand


def _quiz_worthy_sentences(text: str) -> list[str]:
    """Yield sentences that make sane quiz prompts. Rejects URLs, fragments,
    discourse continuations (Therefore/Then/However...), questions, code."""
    import re
    _bad_start = ("therefore", "then", "however", "moreover", "furthermore", "also",
                  "but ", "and ", "or ", "so ", "thus", "hence", "meanwhile", "next,",
                  "finally,", "first,", "second,", "third,", "for example", "for instance",
                  "in addition", "on the other hand", "as a result", "in contrast",
                  "alternatively", "nevertheless", "nonetheless", "instead",
                  "com:", "http", "www.", "see figure", "as shown", "note that",
                  "it is important", "keep in mind", "getting started")
    _definitional = (" is ", " are ", " refers to", " means ", " involves ",
                     " consists of", " defines ", " describes ", " enables ",
                     " allows ", " provides ", " uses ", " relies on")
    _bad_subj = ("it", "this", "that", "these", "those", "they", "them",
                 "he", "she", "we", "you", "if", "when", "while", "the",
                 "chapter", "section", "getting", "alternatively", "maybe")
    out = []
    for raw in re.split(r"(?<=[.!?])\s+", text):
        s = " ".join(raw.split())
        low = s.lower()
        if not (60 <= len(s) <= 300):
            continue
        if any(tok in low for tok in ("http", "www.", "#", ".com", ".org", "freenode",
                                      "irc", "://", "```", ">>>", "import ",
                                      "def ", "    ", "\t", "[", "]")):
            continue
        if low.startswith(_bad_start) or s.endswith(("?", ":", ";")):
            continue
        if not any(pat in low for pat in _definitional):
            continue
        # reject sentences whose SUBJECT is a pronoun/chapter-ref — the extracted
        # concept would be meaningless ("The complexity...", "Chapter 11...")
        import re as _re
        subj = _re.split(r"\s+(?:is|are|refers to|means|involves|consists of)\s+",
                         s, maxsplit=1, flags=_re.I)[0].lower()
        words = subj.split()
        if not words or words[0] in _bad_subj or len(words) > 6:
            continue
        out.append(s)
    return out


def _extract_concept(sent: str) -> str:
    """Short concept label = subject before 'is/are/refers to' (<=8 words)."""
    import re
    m = re.split(r"\s+(?:is|are|refers to|means|involves|consists of)\s+",
                 sent, maxsplit=1, flags=re.I)
    subj = m[0].strip().rstrip(",;:") if m else sent
    words = subj.split()
    return " ".join(words[:8]) if words else "This concept"


def _load_hashes() -> set:
    p = get_settings().QUESTION_BANK
    if os.path.exists(p):
        try:
            return {json.loads(l).get("qhash") for l in open(p) if l.strip()}
        except Exception:
            return set()
    return set()


def _save_hashes(seen: set):
    # deprecated: hashes persist in n_feedback (per graded question). Kept for compat.
    return


def reset_bank() -> None:
    """Clear the dedup bank (used by tests/simulator for isolation)."""
    try:
        if os.path.exists(get_settings().QUESTION_BANK):
            os.remove(get_settings().QUESTION_BANK)
    except Exception:
        pass


def n_verify(s: QuizState) -> QuizState:
    """Blind re-answer check for short/numerical; MCQ key sanity; sympy for numerical.
    Drops questions the verifier marks NOT_SUPPORTED (unless verifier errors -> keep),
    then tops the quiz back up so the student still gets n_questions."""
    s.setdefault("pool", [])
    s.setdefault("shortfall_reason", "")
    try:
        from src.chains.prompts import get_verify_chain, _content
        chain = get_verify_chain()
        keep = []
        for q in s["questions"]:
            if q.get("qtype") == "numerical":
                try:
                    import sympy
                    sympy.sympify(q["answer_key"])  # must parse
                    keep.append(q)
                except Exception:
                    q["verify_note"] = "dropped: answer_key not parseable"
                continue
            try:
                v = _content(chain.invoke(
                    {"context": (q.get("explanation", "") + " | source: "
                                 + q.get("source", ""))[:500],
                     "answer": q["answer_key"][:500]}))
                if "NOT_SUPPORTED" in (v or "").upper():
                    q["verify_note"] = f"dropped: verifier said NOT_SUPPORTED ({v[:120]})"
                    continue
            except Exception:
                pass  # verifier down -> keep (offline-safe)
            keep.append(q)
        s["questions"] = keep
    except Exception:
        pass
    if len(s["questions"]) < s["n_questions"]:
        used = {q["qhash"] for q in s["questions"]}
        s["pool"] = [q for q in s["pool"] if q.get("qhash") not in used]
        _top_up(s, s["pool"])
    # verification can drop questions after generate, so recompute the final count
    s["generated"] = len(s["questions"])
    s["shortfall"] = max(0, s["n_questions"] - s["generated"])
    if s["shortfall"] and not s["shortfall_reason"]:
        s["shortfall_reason"] = (
            f"Only {s['generated']} of {s['n_questions']} questions survived "
            f"answer verification. Ingest more material on '{s['scope']}' to widen the pool."
        )
    elif not s["shortfall"]:
        s["shortfall_reason"] = ""
    return s


def n_feedback(s: QuizState, answers: dict | None = None) -> QuizState:
    """Grade + BKT update + weak-topic report. Pass answers={qhash: student_ans}.

    Grading (no LLM needed, fully verifiable):
      1. exact/overlap: your answer contained in the key sentence (or vice versa)
      2. keyword check: >=60% of the key's content words (len>3) appear in yours
    Each result carries the key sentence + source page so you can verify by
    opening the cited page and comparing. LLM semantic grading is layered on
    top when available (ornith), but never overrides a keyword pass.
    """
    from src.stores.learner import update
    from collections import Counter
    import re
    res, wrong = [], Counter()
    bank_lines = []
    for q in s["questions"]:
        given = (answers or {}).get(q["qhash"], "")
        topic = q.get("topic") or s["scope"]
        if topic == "general":
            topic = s["scope"]
        key = q["answer_key"]
        ok, method = _grade_short(given, key)
        if not ok and given.strip():
            # LLM semantic second opinion (e.g. paraphrase the key accepts)
            verdict = _llm_grade(given, key, q.get("source", ""))
            if verdict:
                ok, method = True, "llm-semantic"
        update(s["student_id"], topic, bool(ok))
        if not ok:
            wrong[topic] += 1
        res.append({"qhash": q["qhash"], "correct": ok, "method": method,
                    "given": given, "key": key, "source": q.get("source", ""),
                    "verify": (f"Open {q.get('source','')} and check the key sentence. "
                               f"Keyword overlap graded ({method})."),
                    "feedback": f"{'Correct.' if ok else 'Not quite — review ' + q.get('source','') + '. '} {q.get('explanation','')}"})
        bank_lines.append(json.dumps({"qhash": q["qhash"], "stem": q["stem"]}))
    s["results"] = res
    s["weak_topics"] = [t for t, _ in wrong.most_common(3)]
    try:
        os.makedirs(os.path.dirname(get_settings().QUESTION_BANK), exist_ok=True)
        open(get_settings().QUESTION_BANK, "a").write("\n".join(bank_lines) + ("\n" if bank_lines else ""))
    except Exception:
        pass
    return s


def _grade_short(given: str, key: str) -> tuple[bool, str]:
    """Deterministic short-answer grading. Returns (correct, method)."""
    import re
    g, k = (given or "").strip().lower(), (key or "").strip().lower()
    if not g:
        return False, "blank"
    if g in k or k in g:
        return True, "exact-overlap"
    stop = {"the", "and", "for", "with", "that", "this", "from", "into",
            "your", "own", "words", "explain"}
    kw = [w for w in re.findall(r"\w+", k) if len(w) > 3 and w not in stop]
    if not kw:
        return False, "no-keywords"
    hit = sum(1 for w in kw if w in g)
    return (hit / len(kw) >= 0.6), f"keyword-{hit}/{len(kw)}"


def _llm_grade(given: str, key: str, source: str) -> bool:
    """Semantic second opinion via verifier LLM. True=accept, False/None=reject.
    Never raises (offline-safe)."""
    try:
        from src.chains.prompts import get_verify_chain, _content
        v = _content(get_verify_chain().invoke(
            {"context": f"Expected answer (from {source}): {key}",
             "answer": f"Student answer: {given}. "
                       "Is the student answer semantically equivalent?"}))
        return "SUPPORTED" in (v or "").upper() and "NOT_SUPPORTED" not in (v or "").upper()
    except Exception:
        return False


def build_quiz_graph():
    g = StateGraph(QuizState)
    g.add_node("scope", n_scope); g.add_node("generate", n_generate); g.add_node("verify", n_verify)
    g.set_entry_point("scope")
    g.add_edge("scope", "generate"); g.add_edge("generate", "verify"); g.add_edge("verify", END)
    return g.compile()

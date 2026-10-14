"""Streamlit UI: Upload(G0) | Tutor(G1) | Quiz(G2) | Dashboard(G3) | History."""
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root (for `src.*`)
import streamlit as st
import pandas as pd
from src.config.paths import upload_path
from src.graphs.ingest_graph import ingest_file
from src.graphs.tutor_graph import ask
from src.graphs.quiz_graph import build_quiz_graph, n_feedback
from src.stores.learner import all_mastery
from src.stores import history as hist

ALLOWED = ["pdf", "pptx", "ppt", "txt", "srt", "vtt", "jpg", "jpeg", "png"]


def read_bytes(f) -> bytes:
    """Streamlit's UploadedFile.getbuffer() can raise UnsupportedOperation on some
    builds (the 'clipboard' read error). Try the safe APIs before falling back."""
    for getter in ("getvalue", "getbuffer"):
        fn = getattr(f, getter, None)
        if fn is None:
            continue
        try:
            data = fn()
            return data if isinstance(data, bytes) else bytes(data)
        except Exception:
            continue
    try:
        f.seek(0)
        return f.read()
    except Exception:
        return b""


def ingest_one(f) -> tuple[str, dict]:
    dest = upload_path(f.name)
    data = read_bytes(f)
    if not data:
        raise OSError(f"{f.name}: file was empty or could not be read")
    Path(dest).write_bytes(data)
    return dest, ingest_file(dest)


def reset_quiz_state():
    for k in ("quiz", "quiz_meta", "quiz_results", "quiz_graded", "answers"):
        st.session_state.pop(k, None)


def _fmt_ts(ts: float) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%d %b %H:%M")
    except Exception:
        return ""


st.set_page_config(page_title="Learning Companion", layout="wide")
st.title("📚 Learning Companion — LangGraph RAG")
sid = st.sidebar.text_input("student_id", "demo-student")
st.sidebar.caption(f"History file: data/checkpoints/history/{sid}.jsonl")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Upload", "Tutor Chat", "Quiz", "Dashboard", "History"])

# ---------------------------------------------------------------- Upload
with tab1:
    files = st.file_uploader("PDF / slides / transcript / images", type=ALLOWED,
                             accept_multiple_files=True)
    st.caption(f"{len(files)} file(s) selected — all of them are ingested in one go.")
    if files and st.button("Ingest", type="primary"):
        total_units, rows, failed = 0, [], False
        progress = st.progress(0.0, text="Starting…")
        for i, f in enumerate(files, 1):
            progress.progress(i / len(files), text=f"Ingesting {f.name} ({i}/{len(files)})")
            try:
                dest, out = ingest_one(f)
            except Exception as e:
                rows.append({"file": f.name, "kind": "-", "units": 0, "errors": str(e)[:120]})
                hist.append(sid, "upload", file=f.name, kind="-", units=0, errors=[str(e)[:200]])
                failed = True
                continue
            total_units += len(out["units"])
            errs = out["errors"]
            rows.append({"file": f.name, "kind": out["kind"], "units": len(out["units"]),
                         "errors": "; ".join(errs)[:120] or "-"})
            hist.append(sid, "upload", file=f.name, kind=out["kind"],
                        units=len(out["units"]), errors=errs)
            failed = failed or bool(errs) or not out["units"]
        progress.empty()
        st.dataframe(rows, width="stretch", hide_index=True)
        if total_units:
            st.success(f"Ingested {len(files) - sum(1 for r in rows if r['errors'] != '-')}"
                       f"/{len(files)} file(s), {total_units} units total.")
        if failed:
            st.warning("Some files had errors or produced no readable content — see the table above.")

# ---------------------------------------------------------------- Tutor
with tab2:
    if "chat" not in st.session_state:
        st.session_state["chat"] = []
    # Rendered above the chat widgets on purpose: a control created after
    # st.chat_input loses its value when the input triggers a rerun.
    show_full = st.checkbox("📜 Full transcript", value=False, key="show_transcript",
                            help="Every question and answer in this session, in full — no truncation.")
    chat_col, side_col = st.columns([3, 1])
    with chat_col:
        for m in st.session_state["chat"]:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m["role"] == "assistant" and m.get("citations"):
                    st.caption("📍 " + " · ".join(m["citations"]))
        prompt = st.chat_input("Ask from your material…")
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state["chat"].append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    r = ask(prompt, student_id=sid)
                st.markdown(r["answer"])
                if r["citations"]:
                    st.caption("📍 " + " · ".join(r["citations"]))
            st.session_state["chat"].append({
                "role": "assistant", "content": r["answer"],
                "citations": r["citations"], "verdict": r["verdict"]})
            hist.append(sid, "chat", question=prompt, answer=r["answer"],
                        verdict=r["verdict"], citations=r["citations"])
            st.rerun()
    with side_col:
        st.metric("Turns", len(st.session_state["chat"]) // 2)
        st.metric("Refusals", sum(1 for m in st.session_state["chat"]
                                  if m.get("verdict") == "refuse"))
        if st.button("Clear chat", disabled=not st.session_state["chat"]):
            st.session_state["chat"] = []
            st.rerun()
        st.caption("Every turn is also appended to your history file and "
                   "survives a restart.")

    if show_full:
        st.divider()
        st.subheader("📜 Full chat transcript")
        if not st.session_state["chat"]:
            st.info("No messages in this session yet.")
        else:
            for i, m in enumerate(st.session_state["chat"]):
                who = "You" if m["role"] == "user" else "Tutor"
                with st.container(border=True):
                    st.caption(f"**{who}** · turn {i // 2 + 1}")
                    st.markdown(m["content"])
                    if m.get("citations"):
                        st.caption("📍 " + " · ".join(m["citations"]))
                    if m.get("verdict") == "refuse":
                        st.warning("Refused — not covered by the material.")
        saved = hist.chats(sid)
        if saved:
            st.divider()
            st.caption(f"{len(saved)} earlier question(s) stored for `{sid}` — see the "
                       "History tab for the full back-catalogue.")

# ---------------------------------------------------------------- Quiz
with tab3:
    scope = st.text_input("Quiz scope/topic", "attention")
    n = st.slider("questions", 1, 8, 3)
    gen_col, clr_col = st.columns(2)
    if gen_col.button("Generate quiz", type="primary"):
        with st.spinner("Building quiz…"):
            r = build_quiz_graph().invoke(
                {"student_id": sid, "scope": scope, "difficulty_target": "auto",
                 "n_questions": n, "questions": [], "pool": [], "results": [], "weak_topics": []})
        qid = hist.new_quiz_id()
        st.session_state["quiz"] = r["questions"]
        st.session_state["quiz_meta"] = {
            "quiz_id": qid, "requested": r.get("requested", n),
            "generated": r.get("generated", len(r["questions"])),
            "shortfall": r.get("shortfall", 0), "reason": r.get("shortfall_reason", ""),
            "dupes": r.get("dupes_dropped", 0), "scope": scope,
            "at": datetime.now().strftime("%H:%M")}
        st.session_state.pop("quiz_results", None)
        st.session_state.pop("quiz_graded", None)
        hist.append(sid, "quiz", quiz_id=qid, scope=scope,
                    requested=r.get("requested", n), generated=r.get("generated", len(r["questions"])),
                    questions=[{k: q.get(k) for k in ("stem", "answer_key", "source", "difficulty", "qhash")}
                               for q in r["questions"]])
    if clr_col.button("Clear", disabled="quiz" not in st.session_state):
        reset_quiz_state()
        st.rerun()

    quiz = st.session_state.get("quiz", [])
    meta = st.session_state.get("quiz_meta", {})
    if quiz:
        st.caption(f"{meta.get('generated', len(quiz))} question(s) · generated {meta.get('at', '')}")
        if meta.get("shortfall"):
            st.warning(f"Requested {meta.get('requested')}, could only build "
                       f"{meta.get('generated')}. {meta.get('reason', '')}")
        if meta.get("dupes"):
            st.caption(f"{meta['dupes']} duplicate question(s) were discarded.")
        if st.checkbox("Show answer keys", key="show_keys",
                       help="Reveal the expected answer before you attempt the quiz."):
            for qd in quiz:
                st.caption(f"Key — {qd['answer_key'][:160]}")

        answers = {}
        for i, qd in enumerate(quiz, 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {qd['stem']}**")
                st.caption(f"`{qd['difficulty']}` · source: {qd['source']}")
                answers[qd["qhash"]] = st.text_input(
                    "your answer", key=f"ans_{qd['qhash']}", label_visibility="collapsed")
        if st.button("Verify answers", type="primary"):
            with st.spinner("Grading…"):
                fb = n_feedback({"student_id": sid, "scope": meta.get("scope", scope),
                                 "difficulty_target": quiz[0].get("difficulty", "auto"),
                                 "n_questions": len(quiz), "questions": quiz,
                                 "pool": [], "results": [], "weak_topics": []},
                                answers=answers)
            right = sum(1 for r in fb["results"] if r["correct"])
            st.session_state["quiz_graded"] = {
                "weak": fb["weak_topics"], "scope": meta.get("scope", scope),
                "by_qhash": {r["qhash"]: r for r in fb["results"]}}
            hist.append(sid, "grade", quiz_id=meta.get("quiz_id", ""),
                        scope=meta.get("scope", scope),
                        score=f"{right}/{len(fb['results'])}",
                        correct=right, total=len(fb["results"]),
                        weak_topics=fb["weak_topics"],
                        details=[{k: r.get(k) for k in ("qhash", "correct", "method", "given",
                                                         "key", "source", "feedback")}
                                 for r in fb["results"]])
    else:
        st.info("No quiz yet — set a scope and press **Generate quiz**.")

    graded = st.session_state.get("quiz_graded")
    if graded:
        results = graded["by_qhash"]
        right = sum(1 for r in results.values() if r["correct"])
        st.divider()
        st.subheader(f"Result: {right}/{len(results)} correct")
        for i, qd in enumerate(quiz, 1):
            r = results.get(qd["qhash"])
            if not r:
                continue
            with st.container(border=True):
                st.markdown(f"{'✅' if r['correct'] else '❌'} **Q{i}** — {r['method']}")
                if not r["correct"]:
                    st.markdown(f"**Expected answer:** {r['key']}")
                st.caption(f"Source: {r['source']}")
                st.caption(r["feedback"])
        if graded["weak"]:
            st.warning("Weak topics to revise: " + ", ".join(graded["weak"]))

# ---------------------------------------------------------------- Dashboard
with tab4:
    m = all_mastery(sid)
    if not m:
        st.info("No mastery data yet. Take a quiz or ask the tutor something — "
                "every answer updates your per-topic mastery.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Mastery per topic (BKT)")
            # ProgressColumn's `format` is printf on the raw value: "%.0f%%" of 0.29
            # renders "0%", so the bar has to carry a 0-100 scale.
            rows = sorted(({"topic": t, "mastery": round(v * 100, 1)} for t, v in m.items()),
                          key=lambda x: x["mastery"])
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True,
                         column_config={"mastery": st.column_config.ProgressColumn(
                             "Mastery", format="%.0f%%", min_value=0, max_value=100)})
        with c2:
            st.subheader("Band")
            for t, v in sorted(m.items(), key=lambda x: -x[1]):
                band = ("🟢 strong" if v > 0.75 else
                        "🟡 medium" if v > 0.4 else "🔴 weak")
                st.markdown(f"{band} — **{v:.0%}** {t}")
            weak = [t for t, v in m.items() if v < 0.4]
            if weak:
                st.warning("Start with: " + ", ".join(weak))
        gs = hist.grades(sid, limit=50)
        if gs:
            st.divider()
            st.subheader("Recent quizzes")
            st.dataframe(pd.DataFrame(
                [{"when": _fmt_ts(g["ts"]), "scope": g.get("scope", ""),
                  "score": g.get("score", ""),
                  "weak topics": ", ".join(g.get("weak_topics", [])) or "—"}
                 for g in reversed(gs)]),
                width="stretch", hide_index=True)
        ch = hist.chats(sid, limit=50)
        if ch:
            st.divider()
            st.subheader("Study activity")
            c_a, c_b, c_c = st.columns(3)
            c_a.metric("Questions asked", len(ch))
            c_b.metric("Quizzes taken", len(gs))
            c_c.metric("Documents ingested", len(hist.uploads(sid)))

# ---------------------------------------------------------------- History
with tab5:
    st.subheader("Saved history")
    st.caption("Every question, answer, quiz and grade is appended to "
               f"`data/checkpoints/history/{sid}.jsonl` — it survives restarts and "
               "is ready to feed a full-stack backend.")
    h1, h2 = st.columns(2)
    full_text = st.checkbox("Show complete answers (untruncated)", value=False,
                            key="hist_full",
                            help="Answers are stored in full; this renders all of it.")
    with h1:
        st.markdown("**Tutor conversations**")
        rows = hist.chats(sid)
        if rows:
            for r in reversed(rows):
                q = r.get("question", "")
                label = q if len(q) <= 70 else q[:70] + "…"
                with st.expander(f"❓ {label}  ·  {_fmt_ts(r['ts'])}"):
                    st.markdown(f"**Q — {q}**")
                    st.markdown(r.get("answer", ""))
                    if r.get("citations"):
                        st.caption("📍 " + " · ".join(r["citations"]))
                    if r.get("verdict") == "refuse":
                        st.warning("Refused — not covered by the material.")
        else:
            st.caption("No conversations yet.")
    with h2:
        st.markdown("**Quiz attempts**")
        gs = hist.grades(sid)
        if gs:
            for g in reversed(gs):
                with st.expander(f"📝 {g.get('scope','')} — {g.get('score','')}  ·  {_fmt_ts(g['ts'])}"):
                    for d in g.get("details", []):
                        st.markdown(f"{'✅' if d.get('correct') else '❌'} {d.get('method','')}")
                        if not d.get("correct"):
                            st.caption("Expected: "
                                       + (str(d.get("key", "")) if full_text
                                          else hist.preview(str(d.get("key", "")), 200)))
        else:
            st.caption("No quizzes yet.")

    up = hist.uploads(sid)
    if up:
        st.markdown("**Documents ingested**")
        st.dataframe(pd.DataFrame(
            [{"when": _fmt_ts(u["ts"]), "file": u.get("file", ""), "type": u.get("kind", ""),
              "units": u.get("units", 0),
              "errors": "; ".join(u.get("errors", [])) or "—"}
             for u in reversed(up)]),
            width="stretch", hide_index=True)
    if st.button("Delete my history", type="secondary"):
        hist.clear(sid)
        st.session_state["chat"] = []
        reset_quiz_state()
        st.rerun()
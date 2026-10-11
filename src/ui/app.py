"""Streamlit UI: Upload(G0) | Tutor(G1) | Quiz(G2) | Dashboard(G3)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root (for `src.*`)
import streamlit as st
from src.graphs.ingest_graph import ingest_file
from src.graphs.tutor_graph import ask
from src.graphs.quiz_graph import build_quiz_graph, n_feedback
from src.stores.learner import all_mastery

st.set_page_config(page_title="Learning Companion", layout="wide")
st.title("📚 Learning Companion — LangGraph RAG")
sid = st.sidebar.text_input("student_id", "demo-student")
tab1, tab2, tab3, tab4 = st.tabs(["Upload", "Tutor Chat", "Quiz", "Dashboard"])

with tab1:
    f = st.file_uploader("PDF / PPTX / transcript TXT", type=["pdf", "pptx", "ppt", "txt"])
    if f and st.button("Ingest"):
        open(f"data/uploads/{f.name}", "wb").write(f.getbuffer())
        with st.spinner("G0 ingestion running..."):
            out = ingest_file(f"data/uploads/{f.name}")
        st.success(f"{out['kind']}: {len(out['units'])} units. errors={out['errors']}")

with tab2:
    q = st.text_input("Ask from your material")
    topic = st.text_input("topic filter (optional)") or None
    if q and st.button("Ask"):
        r = ask(q, student_id=sid, topic=topic)
        st.write(r["answer"])
        st.caption(f"verdict={r['verdict']} | cites={r['citations']}")

with tab3:
    scope = st.text_input("Quiz scope/topic", "photosynthesis")
    n = st.slider("questions", 1, 8, 3)
    if st.button("Generate quiz"):
        r = build_quiz_graph().invoke({"student_id": sid, "scope": scope,
                                       "difficulty_target": "auto", "n_questions": n,
                                       "questions": [], "results": [], "weak_topics": []})
        st.session_state["quiz"] = r["questions"]
    for qd in st.session_state.get("quiz", []):
        st.markdown(f"**{qd['stem']}**  `[{qd['difficulty']}] {qd['source']}`")
        st.text_input("your answer", key=qd["qhash"])

with tab4:
    m = all_mastery(sid)
    st.subheader("Mastery per topic (BKT)")
    st.json(m or {"hint": "take a quiz or chat first"})

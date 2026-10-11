"""Offline smoke test: ingest TXT -> G1 ask -> G2 quiz -> BKT -> simulator. No API keys needed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root (for `src.*`)
from src.graphs.ingest_graph import ingest_file
from src.graphs.tutor_graph import ask
from src.graphs.quiz_graph import build_quiz_graph, n_feedback
from src.stores.learner import all_mastery
from src.eval.evaluate import simulate

open("data/uploads/sample.txt", "w").write(
    "Photosynthesis converts light energy into chemical energy in chloroplasts. "
    "Chlorophyll absorbs red and blue light. The Calvin cycle fixes carbon dioxide into glucose.")
print("INGEST:", {k: (len(v) if isinstance(v, list) else v)
                  for k, v in ingest_file("data/uploads/sample.txt").items() if k in ("kind", "units", "errors")})
r = ask("What is photosynthesis?", student_id="smoke")
print("ASK:", r["verdict"], "|", r["answer"][:200], "|", r["citations"])
r2 = ask("Who won the 2026 football world cup?", student_id="smoke")
print("REFUSE-TEST:", r2["verdict"])
q = build_quiz_graph().invoke({"student_id": "smoke", "scope": "photosynthesis",
                               "difficulty_target": "easy", "n_questions": 2,
                               "questions": [], "results": [], "weak_topics": []})
print("QUIZ:", len(q["questions"]), "questions")
fb = n_feedback({**q, "student_id": "smoke", "scope": "photosynthesis"},
                answers={q["questions"][0]["qhash"]: q["questions"][0]["answer_key"]} if q["questions"] else {})
print("FEEDBACK:", fb["results"], "weak:", fb["weak_topics"])
print("MASTERY:", all_mastery("smoke"))
print("SIM:", simulate(sessions=2))
print("SMOKE OK")

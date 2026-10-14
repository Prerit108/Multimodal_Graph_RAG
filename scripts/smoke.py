"""Offline smoke test: ingest a TXT -> G1 ask -> G2 quiz -> BKT -> simulator.

Uses a scratch document so the test never depends on what the student has
already ingested. The scope strings match that scratch text.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root (for `src.*`)
from src.config.paths import upload_path
from src.graphs.ingest_graph import ingest_file
from src.graphs.tutor_graph import ask
from src.graphs.quiz_graph import build_quiz_graph, n_feedback
from src.stores.learner import all_mastery
from src.eval.evaluate import simulate

SCRATCH = upload_path("_smoke_fixture.txt")
TOPIC = "self-attention"
Path(SCRATCH).write_text(
    "Self-attention is a mechanism that relates different positions of a single sequence "
    "in order to compute a representation of the sequence. The scaled dot-product attention "
    "function computes attention weights by scaling the dot product of queries and keys by "
    "the square root of the model dimension. Multi-head attention runs several attention "
    "layers in parallel so the model can attend to different representations at once.")
print("INGEST:", {k: (len(v) if isinstance(v, list) else v)
                  for k, v in ingest_file(SCRATCH).items() if k in ("kind", "units", "errors")})
r = ask("What is self-attention?", student_id="smoke")
print("ASK:", r["verdict"], "|", r["answer"][:200], "|", r["citations"])
r2 = ask("Who won the 2026 football world cup?", student_id="smoke")
print("REFUSE-TEST:", r2["verdict"])
q = build_quiz_graph().invoke({"student_id": "smoke", "scope": TOPIC,
                               "difficulty_target": "easy", "n_questions": 2,
                               "questions": [], "pool": [], "results": [], "weak_topics": []})
print("QUIZ:", len(q["questions"]), "questions")
fb = n_feedback({**q, "student_id": "smoke", "scope": TOPIC},
                answers={q["questions"][0]["qhash"]: q["questions"][0]["answer_key"]} if q["questions"] else {})
print("FEEDBACK:", fb["results"], "weak:", fb["weak_topics"])
print("MASTERY:", all_mastery("smoke"))
print("SIM:", simulate(sessions=2, scope=TOPIC))
print("SMOKE OK")
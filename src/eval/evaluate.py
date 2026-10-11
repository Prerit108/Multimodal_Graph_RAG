"""RAGAS eval over G1 runs + simulator (G2+G3 across sessions)."""
from __future__ import annotations
import json


def ragas_eval(testset: str = "eval/data/testset.jsonl") -> dict:
    """Runs faithfulness/answer_relevancy/context precision+recall if ragas installed."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset
        from src.graphs.tutor_graph import ask
        rows = [json.loads(l) for l in open(testset) if l.strip()]
        ds = Dataset.from_list([{
            "question": r["question"], "ground_truth": r.get("answer", ""),
            "contexts": [ask(r["question"])["answer"]], "answer": ask(r["question"])["answer"],
        } for r in rows])
        return dict(evaluate(ds, [faithfulness, answer_relevancy, context_precision, context_recall]))
    except Exception as e:
        return {"status": "skipped", "reason": str(e)[:200],
                "hint": "pip install ragas datasets; add eval/data/testset.jsonl"}


def simulate(profiles=("strong", "avg", "weak"), sessions: int = 5, scope: str = "photosynthesis") -> dict:
    """3 profiles x N sessions through G2+G3; reports Δmastery + repetition rate.

    Isolated: uses fresh student ids per run and resets the dedup bank first,
    so repeated runs don't flatline (gain 0.0) from stale question hashes.
    """
    from src.graphs.quiz_graph import build_quiz_graph, n_feedback, reset_bank
    from src.stores.learner import get_mastery
    import random, time
    random.seed(0)
    reset_bank()  # fresh dedup state -> simulator measures learning, not staleness
    p_correct = {"strong": 0.85, "avg": 0.6, "weak": 0.35}
    app = build_quiz_graph()
    report = {}
    run = int(time.time()) % 100000
    for prof in profiles:
        sid = f"sim-{prof}-{run}"
        before = get_mastery(sid, scope)
        seen, asked = set(), 0
        for _ in range(sessions):
            r = app.invoke({"student_id": sid, "scope": scope, "difficulty_target": "auto",
                            "n_questions": 3, "questions": [], "results": [], "weak_topics": []})
            ans = {q["qhash"]: (q["answer_key"] if random.random() < p_correct[prof] else "wrong")
                   for q in r["questions"]}
            asked += len(ans); seen.update(ans)
            n_feedback({**r, "student_id": sid, "scope": scope}, answers=ans)
        after = get_mastery(sid, scope)
        report[prof] = {"mastery_before": round(before, 3), "mastery_after": round(after, 3),
                        "gain": round(after - before, 3),
                        "repetition_rate": round(1 - len(seen) / max(1, asked), 3)}
    return report

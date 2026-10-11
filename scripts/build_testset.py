"""Build eval testset with the local testing LLM (ornith-1.0-9b via LM Studio).

Usage:
    python scripts/build_testset.py            # uses data/test_corpus/scidocs_*.jsonl
    python scripts/build_testset.py --n 30     # grounded rows to generate

Output: eval/data/testset.jsonl rows:
  {question, answer, kind: grounded|off-material|numerical|multi-hop, source}
Kind coverage: grounded (from corpus), off-material (fixed set, expect REFUSE),
numerical (fixed set), multi-hop (pairs of corpus docs).
"""
import sys, json, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OFF_MATERIAL = [
    ("Who won the 2026 football world cup final?", "REFUSE - off-material"),
    ("What is the capital of Atlantis?", "REFUSE - off-material"),
    ("Who directed the movie Inception 3?", "REFUSE - off-material"),
    ("What is the phone number of Albert Einstein?", "REFUSE - off-material"),
    ("When will the next solar eclipse destroy the moon?", "REFUSE - off-material"),
]
NUMERICAL = [
    ("What is 17 multiplied by 23?", "391", "numerical"),
    ("What is the square root of 144?", "12", "numerical"),
    ("If a train travels 120 km in 2 hours, what is its speed in km/h?", "60", "numerical"),
    ("What is 15% of 200?", "30", "numerical"),
    ("Solve for x: 3x + 7 = 22.", "5", "numerical"),
]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="grounded rows to generate")
    ap.add_argument("--corpus", default="data/test_corpus/scidocs_corpus.jsonl")
    args = ap.parse_args()
    random.seed(42)

    from src.chains.models import get_generator
    llm = get_generator()
    rows = [json.loads(l) for l in open(args.corpus) if l.strip()]
    out = []
    for r in random.sample(rows, min(args.n, len(rows))):
        ctx = f"{r.get('title','')} {r.get('text','')}"[:1500]
        try:
            resp = llm.invoke(
                "From the passage below, write ONE factual question and its short answer "
                "(under 25 words), grounded ONLY in the passage.\n"
                f"PASSAGE: {ctx}\n"
                "Reply exactly as:\nQ: <question>\nA: <answer>").content
            q = a = ""
            for line in resp.splitlines():
                if line.strip().startswith("Q:"):
                    q = line.split("Q:", 1)[1].strip()
                elif line.strip().startswith("A:"):
                    a = line.split("A:", 1)[1].strip()
            if q and a:
                out.append({"question": q, "answer": a, "kind": "grounded",
                            "source": str(r.get("title", ""))[:120]})
                continue
        except Exception as e:
            print("LLM row failed, extractive fallback:", str(e)[:100])
        sent = (r.get("text", "") or "").split(".")[0].strip()[:200]
        out.append({"question": f"What does the paper '{r.get('title','')[:60]}' state?",
                    "answer": sent, "kind": "grounded",
                    "source": str(r.get("title", ""))[:120]})
    # multi-hop: pair two docs, ask a comparison question
    for a, b in zip(random.sample(rows, 4), random.sample(rows, 4)):
        if a["_id"] == b["_id"]:
            continue
        out.append({"question": f"How does '{str(a.get('title',''))[:50]}' differ in topic "
                                f"from '{str(b.get('title',''))[:50]}'?",
                    "answer": f"A is about {str(a.get('title',''))[:80]}; "
                              f"B is about {str(b.get('title',''))[:80]}.",
                    "kind": "multi-hop", "source": "scidocs-pair"})
    for q, a in OFF_MATERIAL:
        out.append({"question": q, "answer": a, "kind": "off-material", "source": ""})
    for q, a, k in NUMERICAL:
        out.append({"question": q, "answer": a, "kind": k, "source": ""})
    dest = Path("eval/data/testset.jsonl")
    dest.write_text("\n".join(json.dumps(r) for r in out) + "\n")
    kinds = {}
    for r in out:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"wrote {len(out)} rows -> {dest} {kinds}")


if __name__ == "__main__":
    main()

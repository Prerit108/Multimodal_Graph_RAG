"""FastAPI: thin wrappers invoking LangGraph graphs."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root (for `src.*`)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil

app = FastAPI(title="Learning Companion (LangGraph RAG)")
app.add_middleware(
    CORSMiddleware,
    # 5173 = Vite/React dev server, 8501 = Streamlit, 3000 = production preview
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:8501", "http://127.0.0.1:8501",
                   "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


class ChatIn(BaseModel):
    question: str
    student_id: str = "anon"
    topic: str | None = None


class QuizIn(BaseModel):
    scope: str
    student_id: str = "anon"
    difficulty: str = "auto"
    n: int = 5


@app.post("/ingest")
async def ingest(files: list[UploadFile] | None = File(None),
                 file: UploadFile | None = File(None)):
    """Ingest one or many documents.

    Accepts the original singular `file` field (README curl examples) and the new
    `files` field for batches:
        curl -F "file=@a.pdf"  .../ingest
        curl -F "files=@a.pdf" -F "files=@b.pptx" .../ingest
    """
    from src.graphs.ingest_graph import ingest_file
    from src.config.paths import upload_path

    uploads = list(files or [])
    if file is not None:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=422,
                            detail="Send at least one file as 'file' or 'files'.")

    supported = {".pdf", ".ppt", ".pptx", ".txt", ".srt", ".vtt", ".jpg", ".jpeg", ".png"}
    results, errors = [], []
    for upload in uploads:
        filename = Path(upload.filename or "upload").name
        if Path(filename).suffix.lower() not in supported:
            errors.append(f"{filename}: supported types are "
                          f"{', '.join(sorted(supported))}")
            continue
        dest = upload_path(filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        out = ingest_file(dest)
        if out["errors"]:
            errors.extend(f"{filename}: {e}" for e in out["errors"])
        if not out["units"]:
            errors.append(f"{filename}: no readable content was found")
            continue
        results.append({"file": filename, "kind": out["kind"],
                        "units": len(out["units"]), "errors": out["errors"]})
    if not results:
        raise HTTPException(status_code=422, detail="; ".join(errors) or "No files were uploaded.")
    return {"ingested": len(results), "units": sum(r["units"] for r in results),
            "files": results, "errors": errors}


@app.get("/health")
def health():
    from src.config.settings import get_settings
    from src.stores.graph import get_graph

    settings = get_settings()
    vector_backend = settings.VECTOR_BACKEND.lower()
    if vector_backend == "chroma":
        storage_state = "directory present · contents unverified" if Path(settings.CHROMA_DIR).exists() else "awaiting first document"
    else:
        storage_state = "URL configured" if settings.QDRANT_URL else "not configured"
    return {
        "graph_backend": "NetworkX",
        "graph_nodes": get_graph().number_of_nodes(),
        "vector_backend": vector_backend,
        "vector_storage_state": storage_state,
        "retrieval_mode": "Hybrid · semantic + BM25 + graph context",
    }


@app.post("/chat")
def chat(inp: ChatIn):
    from src.graphs.tutor_graph import ask
    from src.stores import history as hist
    r = ask(inp.question, student_id=inp.student_id, topic=inp.topic)
    hist.append(inp.student_id, "chat", question=inp.question, answer=r["answer"],
                verdict=r["verdict"], citations=r["citations"], topic=inp.topic)
    return {"answer": r["answer"], "verdict": r["verdict"], "citations": r["citations"]}


class QuizSubmit(BaseModel):
    student_id: str = "anon"
    scope: str = ""
    quiz_id: str = ""
    difficulty: str = "auto"
    questions: list = []
    answers: dict[str, str] = {}


@app.post("/quiz")
def quiz(inp: QuizIn):
    from src.graphs.quiz_graph import build_quiz_graph
    from src.stores import history as hist
    r = build_quiz_graph().invoke({"student_id": inp.student_id, "scope": inp.scope,
                                   "difficulty_target": inp.difficulty, "n_questions": inp.n,
                                   "questions": [], "pool": [], "results": [], "weak_topics": []})
    qid = hist.new_quiz_id()
    hist.append(inp.student_id, "quiz", quiz_id=qid, scope=inp.scope,
                requested=r.get("requested", inp.n), generated=r.get("generated", len(r["questions"])),
                questions=[{k: q.get(k) for k in ("stem", "answer_key", "source", "difficulty", "qhash")}
                           for q in r["questions"]])
    return {"quiz_id": qid, "questions": r["questions"],
            "requested": r.get("requested", inp.n), "generated": r.get("generated", len(r["questions"])),
            "shortfall": r.get("shortfall", 0), "reason": r.get("shortfall_reason", ""),
            "dupes_dropped": r.get("dupes_dropped", 0)}


@app.post("/quiz/grade")
def quiz_grade(sub: QuizSubmit):
    """Grade a submitted quiz, update BKT mastery, persist the attempt."""
    from src.graphs.quiz_graph import n_feedback
    from src.stores import history as hist
    if not sub.questions:
        raise HTTPException(status_code=422, detail="No questions supplied to grade.")
    fb = n_feedback({"student_id": sub.student_id, "scope": sub.scope,
                     "difficulty_target": sub.difficulty, "n_questions": len(sub.questions),
                     "questions": sub.questions, "pool": [], "results": [], "weak_topics": []},
                    answers=sub.answers)
    correct = sum(1 for r in fb["results"] if r["correct"])
    hist.append(sub.student_id, "grade", quiz_id=sub.quiz_id, scope=sub.scope,
                score=f"{correct}/{len(fb['results'])}", correct=correct,
                total=len(fb["results"]), weak_topics=fb["weak_topics"],
                details=[{k: r.get(k) for k in ("qhash", "correct", "method", "given",
                                                 "key", "source", "feedback")}
                         for r in fb["results"]])
    return {"results": fb["results"], "correct": correct, "total": len(fb["results"]),
            "weak_topics": fb["weak_topics"]}


@app.get("/mastery/{student_id}")
def mastery(student_id: str):
    from src.stores.learner import all_mastery
    return all_mastery(student_id)


@app.get("/history/{student_id}")
def history(student_id: str, limit: int = 200):
    """Full saved history: chats, quizzes, grades and uploads."""
    from src.stores import history as hist
    chats = hist.chats(student_id, limit=limit)
    return {
        "student_id": student_id,
        "chats": chats,
        "quizzes": hist.quizzes(student_id, limit=limit),
        "grades": hist.grades(student_id, limit=limit),
        "uploads": hist.uploads(student_id, limit=limit),
        "counts": {"chats": len(chats),
                   "quizzes": len(hist.quizzes(student_id, limit=limit)),
                   "grades": len(hist.grades(student_id, limit=limit)),
                   "uploads": len(hist.uploads(student_id, limit=limit))},
    }


@app.delete("/history/{student_id}")
def clear_history(student_id: str):
    from src.stores import history as hist
    hist.clear(student_id)
    return {"cleared": student_id}

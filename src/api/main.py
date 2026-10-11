"""FastAPI: thin wrappers invoking LangGraph graphs."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root (for `src.*`)
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import shutil, os

app = FastAPI(title="Learning Companion (LangGraph RAG)")

DATA = "data/uploads"
os.makedirs(DATA, exist_ok=True)


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
async def ingest(file: UploadFile = File(...)):
    from src.graphs.ingest_graph import ingest_file
    dest = os.path.join(DATA, file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    out = ingest_file(dest)
    return {"file": file.filename, "kind": out["kind"],
            "units": len(out["units"]), "errors": out["errors"]}


@app.post("/chat")
def chat(inp: ChatIn):
    from src.graphs.tutor_graph import ask
    r = ask(inp.question, student_id=inp.student_id, topic=inp.topic)
    return {"answer": r["answer"], "verdict": r["verdict"], "citations": r["citations"]}


@app.post("/quiz")
def quiz(inp: QuizIn):
    from src.graphs.quiz_graph import build_quiz_graph
    r = build_quiz_graph().invoke({"student_id": inp.student_id, "scope": inp.scope,
                                   "difficulty_target": inp.difficulty, "n_questions": inp.n,
                                   "questions": [], "results": [], "weak_topics": []})
    return {"questions": r["questions"]}


@app.get("/mastery/{student_id}")
def mastery(student_id: str):
    from src.stores.learner import all_mastery
    return all_mastery(student_id)

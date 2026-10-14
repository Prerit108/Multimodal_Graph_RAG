# 📚 Learning Companion — Personalized Tutoring & Adaptive Learning

**Track D · Multimodal AI Hackathon 2026 · LangChain + LangGraph edition**

A source-grounded AI study companion that unifies lecture videos, textbooks, and slides
into a cited knowledge base, then runs adaptive quizzes and personalized tutoring on top.

> **Stack principle:** LangChain = every model / embedding / vector call.
> LangGraph = every multi-step RAG flow (typed State + checkpointer).
> No raw SDK calls, no hand-rolled orchestration.

---

## ✨ What it does

| Capability | How |
|---|---|
| 📥 Multimodal ingestion (G0) | PDF (Docling) + slides (1 slide = 1 doc) + video transcripts → `CitationUnit` chunks in Chroma |
| 💬 Grounded tutor chat (G1) | `retrieve → grade → expand → generate → verify`, inline citations, refusal gate for off-material questions |
| 📝 Adaptive quizzes (G2) | Scope-aware generation, hash dedup, sympy check for numerical, cited feedback |
| 🧠 Learner model (G3) | Custom BKT per student × topic + forgetting decay → difficulty adaptation + revision queue |
| 📊 Evaluation | 3-profile simulator (strong/avg/weak) + RAGAS (faithfulness, relevancy, precision, recall) |
| 🖥️ Serving | FastAPI (`/ingest /chat /quiz /quiz/grade /mastery /history`) + React web UI (Upload \| Tutor \| Quiz \| Dashboard \| History) |

---

## 🏗️ Architecture

```text
G0 INGESTION (LangGraph)                  KNOWLEDGE BASE (LangChain)
 DoclingLoader (PDF/textbook)              Chroma (MiniLM-L6-v2) + keyword re-rank
 SlideLoader (1 slide = 1 doc)             + metadata [topic, difficulty, type]
 VideoLoader (transcript windows)          Concept graph (NetworkX)
  │ split (RecursiveCharacterTextSplitter) Citation payload: file + page | slide | t_start/t_end
  │ tag   (CitationUnit, LLM or heuristic)
  ▼ embed + upsert

G1 TUTOR GRAPH ──▶ G2 QUIZ GRAPH ──▶ G3 LEARNER LOOP
(checkpointed)      (verify+dedup)     (BKT + scheduler)
thread_id=student_id                   diagnostic / auto difficulty
```

**Graphs & states** (`src/graphs/`):

- `ingest_graph.py` — `IngestState{file, kind, raw_docs, units, errors}` · `load → split → tag → upsert → graph`
- `tutor_graph.py` — `TutorState{student_id, question, topic_filter, docs, context, citations, answer, verdict}` · `retrieve → grade → expand → generate → verify`
- `quiz_graph.py` — `QuizState{student_id, scope, difficulty_target, n_questions, questions, results, weak_topics}` · `scope → generate → verify` (+ `n_feedback` for grading/BKT)

**Key files:**

```text
src/config/settings.py    central Settings (models, TOP_K, paths) — secrets from .env
src/config/paths.py       UPLOAD_DIR helpers — creates the dir, sanitises filenames
src/stores/history.py     append-only per-student JSONL: chats, quizzes, grades, uploads
src/schemas/models.py     CitationUnit, QuizQuestion, TutorState/QuizState
src/chains/models.py      ONLY place that builds LLMs/embeddings (generator/verifier/embeddings)
src/chains/prompts.py     TAG / ANSWER / VERIFY / QUIZ ChatPromptTemplates
src/stores/vector.py      Chroma store + hybrid_search + keyword re-rank
src/stores/graph.py       NetworkX concept/prereq graph
src/stores/learner.py     BKT: P_INIT=0.30 LEARN=0.25 SLIP=0.10 GUESS=0.20 DECAY=0.995/day
src/eval/evaluate.py      ragas_eval() + simulate()
src/api/main.py           FastAPI thin wrappers over the graphs
src/ui/app.py             Streamlit UI
scripts/smoke.py          offline end-to-end smoke test (no keys needed)
workflow_walkthrough.ipynb  executable tour of the whole workflow
```

---

## 🚀 Quickstart

### 1. Environment

```bash
# Python 3.11 with the project env
/home/preritubuntu/miniconda3/envs/langchain_env/bin/python -m pip install -r requirements.txt
```

### 2. Configure (optional — works offline without keys)

```bash
cp .env.example .env   # if present, else create .env:
```

```env
GOOGLE_API_KEY=...        # generator (gemini-2.5-flash)
OPENAI_API_KEY=...        # verifier  (gpt-4o-mini)
NVIDIA_NIM=...            # alt verifier via NIM
GENERATOR_PROVIDER=google
VERIFIER_PROVIDER=openai
```

Without keys every LLM step falls back to offline heuristics (extractive answers, sentence-based quiz) — the full pipeline still runs.

> **No `PYTHONPATH` needed.** `src/api/main.py`, `src/ui/app.py`, and `scripts/smoke.py`
> each bootstrap `sys.path` to the project root on startup, so `streamlit run`,
> `uvicorn`, and `python scripts/smoke.py` work directly. Just run from the project root.

---

## ▶️ How to run everything

All commands assume `cd /home/preritubuntu/Multimodal_hack_proj`.
Use the project interpreter `PY=/home/preritubuntu/miniconda3/envs/langchain_env/bin/python`
(Python 3.11, has langchain/langgraph/chroma/streamlit/fastapi/jupyter).

```bash
export PY=/home/preritubuntu/miniconda3/envs/langchain_env/bin/python
cd /home/preritubuntu/Multimodal_hack_proj
```

### 0. Smoke test (fastest check — no keys needed)

Runs ingest → ask → refuse-test → quiz → feedback → BKT → simulator:

```bash
$PY scripts/smoke.py
# INGEST: {'kind': ..., 'units': N, 'errors': []}
# ASK: answer | ...   REFUSE-TEST: refuse
# QUIZ: N questions   FEEDBACK: ...   MASTERY: {...}   SIM: {...}
# SMOKE OK
```

### 1. Backend — FastAPI (port 8000)

On Windows, create a project-local Conda environment using Python 3.11
(the checked-in `.conda` folder in this workspace is an empty Python 3.14 environment):

```powershell
& "$env:USERPROFILE\anaconda3\Scripts\conda.exe" create --prefix .backend-env python=3.11 pip -y
.\.backend-env\python.exe -m pip install --upgrade pip
.\.backend-env\python.exe -m pip install -r requirements.txt
.\.backend-env\python.exe -m uvicorn src.api.main:app --reload --reload-dir src --port 8050
```

Then confirm the backend at `http://localhost:8050/health` before submitting a query.
Keep this terminal running while using the UI.

```bash
$PY -m uvicorn src.api.main:app --reload --reload-dir src --port 8000
# docs: http://localhost:8000/docs
```

| Endpoint | Example |
|---|---|
| `POST /ingest` (one file → G0) | `curl -F "file=@data/uploads/my_material.pdf" http://localhost:8000/ingest` |
| `POST /ingest` (batch → G0) | `curl -F "files=@a.pdf" -F "files=@b.pptx" http://localhost:8000/ingest` |
| `POST /chat` (G1 tutor) | `curl -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{"question":"What is multi-head attention?","student_id":"demo"}'` |
| `POST /quiz` (G2 quiz) | `curl -X POST localhost:8000/quiz -H 'Content-Type: application/json' -d '{"scope":"attention","student_id":"demo","difficulty":"auto","n":3}'` |
| `GET /mastery/{student_id}` (G3) | `curl http://localhost:8000/mastery/demo` |
| `GET /history/{student_id}` | `curl http://localhost:8000/history/demo` |
| `POST /quiz/grade` | `{"student_id":"demo","scope":"attention","quiz_id":"…","questions":[…],"answers":{"<qhash>":"…"}}` |
| `DELETE /history/{student_id}` | wipes one student's saved history |

`/ingest` accepts both the singular `file` field and a repeated `files` field, and
returns a per-file summary. Files are processed independently, so one unreadable
document does not fail the batch — its error is reported in `errors`.

Python equivalent (no server):

```python
from src.graphs.ingest_graph import ingest_file
from src.graphs.tutor_graph import ask
from src.graphs.quiz_graph import build_quiz_graph, n_feedback

ingest_file("data/uploads/my_material.pdf")
ask("What is multi-head attention?", student_id="demo")
```

### 2. Web UI — React (port 5173)

The primary interface. Run the API first, then the dev server:

```bash
# terminal 1 — backend
$PY -m uvicorn src.api.main:app --reload --port 8000
# terminal 2 — frontend
cd frontend && npm install && npm run dev
# open http://localhost:5173
```


Vite proxies `/api/*` to `http://localhost:8000`, so the browser stays same-origin in
dev. Point it elsewhere with `VITE_API_BASE_URL`. Production build: `npm run build`
→ `frontend/dist/`.

Tabs: **Upload** · **Tutor** · **Quiz** · **Dashboard** · **History**, with a student
selector in the header (LangGraph `thread_id` + BKT key) and a live API health dot.

- **Upload** — drag-and-drop, multi-file. Per-file results table; one unreadable file
  never aborts the batch. Images run Docling OCR, then a **VLM** description, then a
  filename stub.
- **Tutor** — streaming-style chat bubbles. Answers are clean prose: `p.N` citations
  are kept out of the sentence flow and the exact locations appear as a citation
  strip under each bubble. A **Full transcript** drawer shows every turn untruncated.
- **Quiz** — generate, answer, then **Verify answers** for per-question ✅/❌, the
  grading method, the expected answer when you miss, the source page, and weak
  topics. If fewer questions can be built than requested you get an explicit
  shortfall banner explaining why instead of a silently short quiz.
- **Dashboard** — BKT mastery as labelled bars (percentage scale), topic bands,
  activity counts and a recent-quiz table.
- **History** — every stored conversation and quiz attempt, with a
  *complete answers* toggle and a delete button.

### 3. Streamlit UI (port 8501) — optional

The same graphs behind a lighter UI; useful for evaluation runs and quick checks.

```bash
$PY -m streamlit run src/ui/app.py --server.port 8501
# open http://localhost:8501
```

Same five tabs plus a **Full transcript** checkbox in Tutor Chat. Uploads are written
to `UPLOAD_DIR` (`data/uploads`), created on demand by `src/config/paths.py`.

### 4. Notebook — guided walkthrough (26 cells)

```bash
$PY -m jupyter lab   # open workflow_walkthrough.ipynb, kernel: langchain_env, Run All
# or headless:
$PY -m jupyter nbconvert --to notebook --execute workflow_walkthrough.ipynb \
  --output /tmp/executed_walkthrough.ipynb --allow-errors
```

Covers: setup → project map → CitationUnit → prompts → G0 ingest → Chroma/graph
→ G1 ask + refusal → G2 quiz + feedback → BKT → simulator → API routes.

### 5. Eval

```bash
$PY -c "from src.eval.evaluate import simulate; import json; print(json.dumps(simulate(sessions=2), indent=2))"
# RAGAS needs keys + eval/data/testset.jsonl:
$PY -c "from src.eval.evaluate import ragas_eval; print(ragas_eval())"
```

---

## 🔧 Configuration

`src/config/settings.py` (`Settings`, `.env`-driven) — the knobs that matter:

| Key | Default | Meaning |
|---|---|---|
| `GENERATOR_PROVIDER/MODEL` | `google / gemini-2.5-flash` | answering quiz-generation LLM |
| `VERIFIER_PROVIDER/MODEL` | `openai / gpt-4o-mini` | must differ from generator (cross-vendor check) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Chroma embeddings (downloads on first run) |
| `VECTOR_BACKEND / CHROMA_DIR` | `chroma / data/chroma_db` | vector store location |
| `UPLOAD_DIR` | `data/uploads` | where Streamlit/FastAPI uploads land (auto-created) |
| `ENABLE_VLM / VISION_PROVIDER / VISION_MODEL` | `true / (generator) / (generator)` | image & diagram descriptions; blank reuses the generator model. The loaded model must be multimodal — a text-only model silently falls back to the filename stub |
| `TOP_K / CHUNK_SIZE / OVERLAP` | `6 / 900 / 135` | retrieval + chunking |
| `CHECKPOINT_DB / BKT_DB / QUESTION_BANK` | `data/checkpoints/...` | chat memory / mastery / dedup bank |

---

## 🩺 Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: src` | run from project root, or `sys.path.insert(0, ROOT)` (notebook does this) |
| Wrong python (3.14 system) | always use `$PY` = `langchain_env/bin/python` (3.11) |
| First-run embedding download slow | `MiniLM-L6-v2` pulls once, then cached; offline fallback still works |
| Chroma locked / stale | stop other processes, or wipe `data/chroma_db/` to re-ingest fresh |
| `FileNotFoundError: data/uploads/...` | fixed — `src/config/paths.py` creates `UPLOAD_DIR` on demand; check `UPLOAD_DIR` isn't pointing somewhere unwritable |
| `ValueError: Expected metadata value to be a str/int/... got dict` | Docling nested metadata; `ingest_graph._clean_meta` strips it — re-ingest if you edited the loader |
| RAGAS returns `skipped` | expected offline — `pip install ragas datasets`, add keys + `eval/data/testset.jsonl` |
| Streamlit reuses mastery | change `student_id` in sidebar; mastery lives in `data/checkpoints/bkt.json` |
| Image ingested but reads `Image: x.png (no description available)` | no multimodal model loaded — set `VISION_MODEL` to a vision-capable model, or enable Docling OCR for that file |
| `no such table: collections` | corrupt Chroma file (interrupted run). `src/stores/vector.py` rebuilds it automatically on the next call; to force it, `rm -rf data/chroma_db` |
| React shows "API unreachable" | uvicorn isn't running on :8000, or `VITE_API_BASE_URL` points elsewhere |
| Progress bar shows `0%` for a mastered topic | fixed — the bar is 0–100 scaled; `ProgressColumn`'s `format` is printf on the raw value |
| Mastery splits across near-identical topics | fixed — topic keys are normalised (`"attention,"` and `"attention"` merge); existing keys migrate on load |
| Quiz returns fewer than requested | the corpus genuinely lacks enough distinct quiz-worthy sentences; ingest more material (the graph tops up automatically otherwise) |
| Off-topic question is answered instead of refused | the keyword gate still finds generic overlap (`won`, `world`) in your material; lower `GRADE_THRESHOLD` in `.env` to be stricter |

---

## 📌 Notes & next steps

- Offline-first: every LLM call is wrapped in try/except with a heuristic fallback, so the demo never blocks on keys.
- Add `GOOGLE_API_KEY` + `OPENAI_API_KEY` to `.env` to enable LLM tagging / cited answering / verification.
- Suggested extensions: prereq concept-map UI, flashcards for weak topics, forgetting-curve revision scheduler.

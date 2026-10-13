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
| 🖥️ Serving | FastAPI (`/ingest /chat /quiz /mastery`) + Streamlit (Upload \| Tutor \| Quiz \| Dashboard) |

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

Then confirm the backend at `http://localhost:8050/health` before submitting a query
from the React page. Keep this terminal running while using the frontend.

```bash
$PY -m uvicorn src.api.main:app --reload --reload-dir src --port 8000
# docs: http://localhost:8000/docs
```

| Endpoint | Example |
|---|---|
| `POST /ingest` (file upload → G0) | `curl -F "file=@data/uploads/sample.txt" http://localhost:8000/ingest` |
| `POST /chat` (G1 tutor) | `curl -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{"question":"What is photosynthesis?","student_id":"demo"}'` |
| `POST /quiz` (G2 quiz) | `curl -X POST localhost:8000/quiz -H 'Content-Type: application/json' -d '{"scope":"photosynthesis","student_id":"demo","difficulty":"auto","n":3}'` |
| `GET /mastery/{student_id}` (G3) | `curl http://localhost:8000/mastery/demo` |

Python equivalent (no server):

```python
from src.graphs.ingest_graph import ingest_file
from src.graphs.tutor_graph import ask
from src.graphs.quiz_graph import build_quiz_graph, n_feedback

ingest_file("data/uploads/sample.txt")
ask("What is photosynthesis?", student_id="demo")
```

### 2. Frontend — Streamlit (port 8501)

```bash
$PY -m streamlit run src/ui/app.py --server.port 8501
# open http://localhost:8501
```

Tabs: **Upload** (G0 ingest PDF/PPTX/TXT/images) → **Tutor Chat** (G1, verdict + citations)
→ **Quiz** (G2, scope + auto difficulty) → **Dashboard** (G3 BKT mastery JSON).
Set `student_id` in the sidebar (used as LangGraph `thread_id` + BKT key).

### 3. Layout studies — React + Tailwind

The Phase 6 concepts use the tokens in `design-tokens.json`. Install the frontend
dependencies and start the Vite preview:

```bash
npm install
npm run dev
```

Open `http://localhost:5173/` for the editorial hero page, or `/compare` to review
both layout concepts side by side. Visit `/variants/variant-a` (Bento Grid) and
`/variants/variant-b` (Asymmetric Editorial) for their standalone views. Run
`npm run build` to type-check and create a production build in `dist/`.

The hero query card uploads documents through FastAPI `/ingest` and asks questions
through `/chat`. The local Vite origins are enabled in FastAPI CORS; set
`VITE_API_BASE_URL` if the API is hosted elsewhere. PDF, slides, text transcripts,
and Docling-supported JPG/PNG images can be attached.

Run the React frontend with the backend (two terminals):

```bash
# terminal 1 — backend
.\.backend-env\python.exe -m uvicorn src.api.main:app --reload --reload-dir src --port 8000
# terminal 2 — React frontend
npm run dev
```

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
| RAGAS returns `skipped` | expected offline — `pip install ragas datasets`, add keys + `eval/data/testset.jsonl` |
| Streamlit reuses mastery | change `student_id` in sidebar; mastery lives in `data/checkpoints/bkt.json` |

---

## 📌 Notes & next steps

- Offline-first: every LLM call is wrapped in try/except with a heuristic fallback, so the demo never blocks on keys.
- Add `GOOGLE_API_KEY` + `OPENAI_API_KEY` to `.env` to enable LLM tagging / cited answering / verification.
- Suggested extensions: prereq concept-map UI, flashcards for weak topics, forgetting-curve revision scheduler.

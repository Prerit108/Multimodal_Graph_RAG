# Learning Companion - Project Plan (LangChain + LangGraph Edition)

**Track D: Personalized Tutoring & Adaptive Learning - Multimodal AI Hackathon 2026**

> **Stack principle: LangChain = every model/embedding/vector call. LangGraph = every multi-step RAG flow (state + checkpointer). No raw SDK calls, no hand-rolled orchestration.**

A source-grounded AI study companion that unifies lecture videos, textbooks, and slides into a cited knowledge base, and uses it to run adaptive assessments and personalized tutoring.

---

## 1. Problem & Vision

Students study from lecture videos, textbooks, and slides scattered everywhere, and general chatbots answer without grounding in the course material or the student's knowledge state. We build a companion that:

- Ingests **videos, PDFs/textbooks, and slides** without manual preprocessing
- Answers questions with **exact citations** (page, slide number, video timestamp) as deep links
- **Declines/flags** queries the material does not cover
- Generates **adaptive quizzes** and tracks a **per-topic mastery model**
- Personalizes tutoring and revision as more student data accumulates

---

## 2. Core Architecture: LangGraph-Orchestrated Multimodal GraphRAG

Hybrid multimodal GraphRAG. LangChain wrappers for all LLM/embedding/vector calls; LangGraph graphs (typed State + checkpointer per student) for all flows.

```
G0 INGESTION (LangGraph)                    KNOWLEDGE BASE (LangChain)
 DoclingLoader (PDF/textbook)                QdrantVectorStore (bge-m3 + BM25
 SlideLoader (1 slide = 1 doc)                 via EnsembleRetriever) + payload
 VideoLoader (faster-whisper 30-60s            indexes [topic, difficulty, type]
   windows + keyframe VLM captions)          Knowledge graph (NetworkX via
  │ split (RecursiveCharacterTextSplitter)     LLMGraphTransformer)
  │ caption (VLM ChatModel)                    Citation payload: file + page |
  │ tag (structured CitationUnit)              slide | t_start/t_end
  ▼ embed+upsert                             Question-hash + BKT stores

G1 TUTOR GRAPH ──▶ G2 QUIZ GRAPH ──▶ G3 LEARNER LOOP
(checkpointed)      (verify+dedup)     (BKT + scheduler)
thread_id=student_id                   diagnostic subgraph (cold start)
```

### LangChain model layer (only way to call models)
| Purpose | Class |
|---|---|
| Generator/tutor | `ChatOpenAI` (GPT-4o-mini) or `ChatGoogleGenerativeAI` (Gemini 2.5 Flash) |
| Verifier (different vendor) | the other one; alt: NIM via `ChatOpenAI(base_url=NIM)` |
| VLM captions | vision `ChatGoogleGenerativeAI` / GPT-4o-mini |
| Embeddings | `HuggingFaceEmbeddings(bge-m3)`; alt `OpenAIEmbeddings` |
| Vector | `QdrantVectorStore`, `EnsembleRetriever` (dense+BM25) |
| Chunking | `RecursiveCharacterTextSplitter` |
| Prompts | `ChatPromptTemplate` in `prompts/` |

### CitationUnit (every chunk, via `with_structured_output`)
`course, topic, subtopic, concept, content_type[textbook|slide|video|figure], source_file, page?, slide?, t_start?, t_end?, difficulty, figure_caption?`. Deep links: PDF `#page=n`, slides `#slide=n`, video `?t=t_start`.

---

## 3. Workstreams

### WS1 - G0 IngestionGraph (LangGraph)
Nodes: `load → split → caption_figures → tag_units → embed_upsert → extract_graph_edges`. State: `IngestState{file, kind, raw_docs, units, errors}`.
- **Textbooks/PDFs:** `DoclingLoader` primary (layout-aware, page nos); PyMuPDF fallback only. ~900 tok chunks.
- **Slides:** 1 slide = 1 Document (title + body + VLM image description); `slide` preserved.
- **Videos:** `faster-whisper` 30–60s windows + keyframe VLM captions; `{t_start,t_end}` preserved.
- **Tagging:** one `tag_chain` (`ChatPromptTemplate + with_structured_output(CitationUnit)`) fills course→topic→subtopic→concept + difficulty.

### WS2 - Knowledge Base (LangChain stores)
- **Vector:** `QdrantVectorStore` + `EnsembleRetriever` (dense + BM25) + metadata filter on `topic, difficulty, content_type` for quiz scoping.
- **Graph:** `LLMGraphTransformer` → NetworkX concept/prerequisite edges; used for flow map, `graph_expand` retrieval node, scaffolding.
- **Stores:** citation payload = deep link; question-hash store; BKT store (`langgraph-checkpoint-sqlite`).

### WS3 - G1 TutorRAG Graph (Source-Grounded Chat, 20%)
Nodes: `router → hybrid_retrieve → grade_docs → graph_expand → generate(cited) → verify_grounding → [answer | refuse]`. State: `TutorState{messages, student_id, topic_filter, docs, citations, verdict}` + `SqliteSaver(thread_id=student_id)`.
- Answer **only** from `docs`; inline `[source, page 34]` / `[video, 12:35]`.
- **Refusal = explicit edge:** low `grade_docs` score or `verify_grounding → Answerable=False` routes to `refuse` node (decline/flag, outside knowledge separated).
- Prerequisite-aware via `graph_expand`.

### WS4 - G2 QuizGraph (Adaptive Assessment, 15%)
Nodes: `scope_parse → retrieve_context → generate_questions → verify → dedup → grade_feedback → update_learner → report`. State: `QuizState{scope, difficulty_target, questions, hashes, results, weak_topics}`.
- Types MCQ/short/**numerical**, each tagged topic+source+difficulty.
- **Verify:** blind re-answer by different-vendor verifier must match key; **numerical** also checked by calculator/sympy tool node.
- **Dedup:** SHA hash of normalized stem; reject repeats (feeds repetition-rate metric).
- Cited feedback per item + report (weak topics, misconceptions).

### WS5 - G3 Learner Loop (20%)
- **BKT node** (pyBKT wrapped as graph node) per topic, called from G1 (chat signals) + G2 (graded answers); IRT-style difficulty matching + forgetting-curve scheduler → revision queue.
- **Cold start:** `diagnostic_subgraph` (8–10 mixed-difficulty Qs) or intake chat → seed BKT priors.
- Weak topics → easier Qs, prereq expansion, more scaffolding; spaced revision triggers.

### WS6 - Evaluation (15%): RAGAS over LangSmith-traced G1 runs
- Metrics: **faithfulness, answer_relevancy, context_precision, context_recall**; refusal accuracy on off-material set.
- Test set **60–80 items**: 30 grounded (known page/slide/ts), 15 off-material, 10 numerical, 10–15 multi-hop/prereq.
- **Simulator:** 3 profiles (strong/avg/weak) × 5 sessions via G2+G3; report Δmastery + repetition rate.

### WS7 - App & Dashboard
- FastAPI thin wrappers invoking graphs: `/ingest→G0, /chat→G1, /quiz→G2, /mastery→G3`.
- Dashboard: mastery heatmap per topic, weak-topic list, study history, citation deep links.

### WS8 - Optional Enhancements (pick 2–3 if time allows)
1. Visual course flow map from the concept graph (high value, cheap) ✅ priority
2. Revision material for weak topics (flashcards, audio briefs)
3. Study schedule from forgetting curves + exam date
4. Hindi/mixed-language support
5. Audio tutoring sessions

---

## 4. Tech Stack

| Component | Choice |
|---|---|
| Ingestion | DoclingLoader (primary), faster-whisper, VLM `ChatGoogleGenerativeAI` |
| Embeddings | `HuggingFaceEmbeddings(bge-m3)` / `OpenAIEmbeddings` |
| Vector DB | `QdrantVectorStore` + `EnsembleRetriever` (dense+BM25) |
| Graph | NetworkX via `LLMGraphTransformer` |
| LLMs | All via LangChain: `ChatOpenAI` / `ChatGoogleGenerativeAI` (+NIM verifier) |
| Learner model | pyBKT as LangGraph node + scheduler |
| Eval | RAGAS over LangSmith traces (+ DeepEval backup) |
| Backend | FastAPI invoking LangGraph graphs |
| Frontend | Streamlit (fast) or React |
| Source material | MIT OCW / NPTEL course |

---

## 5. Judging Criteria Alignment

| Criterion | Weight | Our answer |
|---|---|---|
| Knowledge Base & Grounding | 20% | Multimodal extraction + VLM figures, citation deep links, refusal gate |
| Personalization | 20% | BKT mastery model, measurable gains in simulated runs |
| Assessment Quality | 15% | Verified + deduped questions, tagged, cited feedback reports |
| UX & Demo | 15% | Clean dashboard, 3–10 min demo video |
| System Evaluation | 15% | RAGAS metrics, honest test set, simulated students |
| Technical Implementation | 15% | Typed States, checkpointed graphs, LangChain-only model access |

---

## 6. Milestones (hackathon sprint)

1. **M1 - G0 ingestion:** PDF + slides + video → `CitationUnit`s in Qdrant with deep links
2. **M2 - G1 chat:** hybrid retrieve, citations, refusal edge, checkpointed chat
3. **M3 - G2 quiz:** generation, blind + symbolic verify, dedup, cited feedback
4. **M4 - G3 learner:** BKT + diagnostic + dashboard + personalization loop
5. **M5 - Eval:** RAGAS 4 metrics + simulator (Δmastery, repetition rate) report
6. **M6 - Polish:** concept map, UI polish, demo video, documentation

---

## 7. Deliverables

- Web prototype (G0 upload, G1 chat, G2 assessment, G3 dashboard)
- Docs: graphs + states, grounding (retrieve→grade→verify→refuse), learner model (BKT + forgetting)
- Evaluation results (RAGAS + simulated students)
- 3–10 min demo video (upload workflow → grounded chat → assessment → architecture)

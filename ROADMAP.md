# Full-Stack Roadmap — Track D (Multimodal AI Hackathon 2026)

Status: **Phase 0 complete** (bug fixes + durable history + real dashboard).
Everything below builds on the existing LangGraph pipeline; nothing here throws away
working code.

---

## A. What was just fixed (Phase 0 — done)

| Bug | Root cause | Fix |
|---|---|---|
| Same question twice in one quiz | `_hash()` hashed the *raw* stem, which embeds the `Qn (easy).` prefix — so `Q1 (easy). n: explain…` and `Q2 (easy). n: explain…` hashed differently | `_norm_stem()` strips numbering + boilerplate; hash = normalized stem **+** answer key. In-run duplicate set blocks repeats |
| Nonsense stems (`"n: explain in your own words"`) | `_extract_concept` happily returned formula fragments like `n`, `x = 5`, `[ 13 ]` | `_degenerate()` rejects <2 words, <60% alpha, or pure non-word concepts |
| Silent question shortfall | UI just showed "N question(s)" with no explanation | `requested / generated / shortfall / shortfall_reason` in state; UI shows a warning |
| Tutor answers vanished on quiz generation | Answers lived only in a local variable; every Streamlit rerun wiped them | `st.session_state["chat"]` + durable `history.jsonl` |
| Dashboard showed raw JSON | `st.json(m)` | `st.dataframe` with `ProgressColumn`, band list (🟢/🟡/🔴), recent-quiz table, activity metrics |
| No history at all | Nothing was persisted | `src/stores/history.py` — append-only JSONL per student |

---

## B. Current architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ Streamlit (src/ui/app.py)                                   │
│  Upload · Tutor · Quiz · Dashboard · History                │
└───────────────┬─────────────────────────────────────────────┘
                │ in-process calls
┌───────────────▼─────────────────────────────────────────────┐
│ LangGraph pipelines                                          │
│  G0 ingest_graph    load→split→tag→upsert→graph              │
│  G1 tutor_graph     retrieve→grade→expand→generate→verify   │
│  G2 quiz_graph      scope→generate→verify (+ n_feedback)    │
│  G3 learner.py      BKT mastery + forgetting decay           │
└───────────────┬─────────────────────────────────────────────┘
                │
   Chroma (data/chroma_db) · NetworkX graph · SQLite checkpoints
   BKT json · questions.jsonl · history/*.jsonl
```

**The key structural weakness:** state is per-process. Two servers (uvicorn +
Streamlit) each hold their own copy, so a quiz graded in the UI is invisible to the
API. The history JSONL is the first step toward a single source of truth — Phase 1
makes it authoritative.

---

## C. Phase 1 — Real backend (the full-stack core)

**Goal:** one FastAPI process owns all state. Streamlit becomes a thin client.

1. **Promote `history.jsonl` to the source of truth.**
   Currently every write goes to a local file with no locking. Move to SQLite
   (`data/app.db`) with WAL mode — one writer, many readers, no lost updates.

   ```sql
   sessions(id, student_id, started_at)
   messages(id, session_id, role, content, citations_json, verdict, created_at)
   quizzes(id, student_id, scope, requested, generated, created_at)
   questions(id, quiz_id, stem, answer_key, source, difficulty, topic, qhash)
   attempts(id, quiz_id, qhash, answer, correct, method, created_at)
   mastery(student_id, topic, p, updated_at)
   ```

2. **Extend FastAPI** beyond today's five endpoints:
   - `POST /sessions` · `GET /sessions/{id}/messages` · `POST /sessions/{id}/messages` (SSE stream the answer)
   - `GET /students/{id}/quizzes` · `GET /quizzes/{id}` · `POST /quizzes/{id}/submit`
   - `GET /students/{id}/mastery` · `GET /students/{id}/timeline`
   - `DELETE /students/{id}/history`

3. **Auth.** Email + password (or OAuth), hashed with argon2, JWT bearer tokens.
   Right now `student_id` is a free-text box — anyone can read anyone else's history.
   This is the single biggest gap before any demo.

4. **Stream responses.** `StreamingResponse` over SSE so the tutor types its answer
   instead of blocking for 20s. Today the UI shows a spinner; that reads as "broken."

**Exit criteria:** Streamlit talks to FastAPI only; restarting either process loses nothing.

---

## D. Phase 2 — Frontend rebuild

**Recommendation: React + TypeScript + Vite.** The earlier prototype was removed because
it was scaffolding, but the requirement is a *web* prototype and judges will judge UX
(15% of scoring). Streamlit is fine for the backend demo and for rapid eval work —
keep it, but don't demo it as the product.

- **Chat UI** — streaming tokens, inline citation chips that jump to the page
- **Quiz runner** — one question per screen, progress bar, instant verdict, review mode
- **Dashboard** — mastery bars over time, weak-topic radar, quiz history timeline
- **Upload** — drag-and-drop batch with live per-file status

**Design system:** reuse the `design-tokens.json` that was deleted with the prototype if
you want the editorial look; otherwise keep it simple and prioritise legibility.

**Cost check:** Phase 2 is the largest time sink. If time is short, do Phase 1 + a
*modest* React chat/quiz shell and spend the remainder on evaluation and the demo video —
those two are 30% of the score and are much cheaper than pixel-perfect UI.

---

## E. Phase 3 — Grading against the rubric

Current state, honestly assessed:

| Criterion | Weight | Today | Gap |
|---|---|---|---|
| Knowledge base & grounding | 20% | Strong — Docling, citations, refusal gate | Weak on **images inside PDFs** (figures aren't individually described) |
| Assessment quality | 15% | Dedupe + verify + tagged feedback | No **misconception** detection beyond "weak topic"; no MCQ options rendered |
| Personalization | 20% | BKT + auto difficulty + simulator | Mastery never updates from **chat**, only quizzes |
| UX & demo video | 15% | Functional, no history, raw-JSON dashboard | Phase 1+2 |
| System evaluation | 15% | RAGAS wired, simulator exists | **Never actually run** — no numbers produced |
| Technical implementation | 15% | Clean layered design | Monolith-ish; no tests |

### Concrete work, highest ROI first

1. **Actually run the evaluation and publish the numbers.** `ragas_eval()` has never been
   executed end-to-end. Judges weight rigour and honesty. A table of real faithfulness /
   relevancy / context-precision on your testset, plus the simulator's mastery-gain and
   repetition-rate curves, is worth more than most features.
2. **Update mastery from conversation.** Requirement 4a says mastery updates after *every
   quiz and conversation*. Right now `ask()` only reads mastery, never writes it. Feed
   the verdict + citation confidence back into BKT.
3. **Misconception report.** Requirement 3c asks for "likely misconceptions," not just
   weak topics. Cluster wrong answers per topic and name the misconception (e.g.
   "confuses attention with recurrence") — this is a genuine differentiator.
4. **Open the exact source location.** Requirement 2a: "open the exact page, slide, or
   timestamp." Store an anchor and link to it. Currently citations are text only.
5. **Figures in PDFs.** Requirement 1d covers images *and* diagrams. Standalone images
   work now; figures embedded in PDFs do not. Export Docling page images and run the VLM
   on them.
6. **Diagnostic onboarding.** Requirement 4b: a short intake quiz for new students so the
   first recommendation isn't `P_INIT` guesswork.

---

## F. Feature ideas that play to the rubric

Ranked by score impact ÷ effort.

**High impact, low effort**
- **Spaced repetition scheduler** (Req 6c) — you already have `DECAY=0.995/day`. A due-date
  queue per topic is ~40 lines and directly demonstrates 6c.
- **Flashcards from weak topics** (6b) — reuse `answer_key` sentences as card fronts.
- **Study plan generator** (6c) — weak topics × exam date → daily schedule.
- **"Why is this wrong?"** — after a wrong answer, show the exact cited sentence and the
  page link. Cheap, and makes the grounding story land in a demo.

**High impact, medium effort**
- **Course flow map** (6a) — the NetworkX concept graph already exists; render it with
  `graphviz`/`pyvis`. Very demo-friendly, reuses existing code.
- **Hindi/mixed-language explanations** (6d) — explicitly listed. Since the generator is a
  local model, add a "explain in Hindi" toggle on the tutor. High visibility for an
  Indian hackathon audience.
- **Weak-topic revision drill** — auto-generate a mini-quiz from the exact weak concepts.

**Nice-to-have, high effort**
- **Audio tutoring** (6e) — TTS on tutor answers. Impressive, but the quality bar is high
  and it's one rubric line.
- **Video ingestion** — currently only `.srt`/`.vtt` transcripts work. Real video → audio →
  transcription → timestamped windows would genuinely complete requirement 1a, but it's a
  big lift. Claim it honestly as "transcript ingestion" unless you do it.

---

## G. Suggested order

```text
Week 1  Run the evaluation, get real numbers, write them up
        Add mastery-update-from-chat + spaced repetition queue
Week 2  SQLite store + session/auth API + SSE streaming
        Rebuild chat/quiz shell in React
Week 3  Dashboard with mastery-over-time, misconception report,
        source-page deep links, figure extraction
Week 4  Polish, course map, Hindi toggle, demo video, docs
```

**Do not skip the demo video** — it is an explicit deliverable and 15% of the score.
Budget three days for it. Record the happy path: upload → grounded chat with a refusal →
quiz → verify → dashboard showing mastery change.

---

## H. Risks worth naming now

- **Single-user assumption.** No auth means the demo breaks the moment two browsers
  connect. Phase 1 is not optional polish; it is a correctness fix.
- **Two servers, two states.** Running FastAPI and Streamlit against one Chroma has
  already caused a corrupt-store incident. One process, one writer.
- **Local-model ceiling.** `ornith-1.5-9b` is text-only-ish and caps question quality.
  Judges will notice weak generation. Consider a hybrid: local for privacy-sensitive
  paths, a stronger cloud model for quiz generation only, with the fallback intact.
- **Overclaiming video/audio.** Be precise in the docs about what is transcripts vs media.
  Honest scoping scores better than a demo that breaks live.
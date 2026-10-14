import { useEffect, useRef, useState } from "react";
import { api, type ChatTurn, type GradeResult, type Question } from "../api";

/* ============================================================== Upload */
export function Upload({ student }: { student: string }) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const run = async () => {
    if (!files.length) return;
    setBusy(true); setErr(null); setRows([]);
    try {
      const r = await api.ingest(files);
      setRows(r.files);
      setErr(r.errors.length ? r.errors.join(" · ") : null);
    } catch (e: any) {
      setErr(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="card">
        <h2 className="section">Upload material</h2>
        <div
          className={`drop${over ? " over" : ""}`}
          onClick={() => input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setOver(true); }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => {
            e.preventDefault(); setOver(false);
            setFiles(Array.from(e.dataTransfer.files));
          }}
        >
          <strong>Drop files here or click to browse</strong>
          <span>PDF · PPTX · TXT · SRT · VTT · JPG · PNG — select as many as you like</span>
          <input
            ref={input} type="file" multiple hidden
            accept=".pdf,.pptx,.ppt,.txt,.srt,.vtt,.jpg,.jpeg,.png"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          />
        </div>

        {files.length > 0 && (
          <>
            <div className="caption">{files.length} file(s) selected</div>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="btn" onClick={run} disabled={busy}>
                {busy ? "Ingesting…" : "Ingest"}
              </button>
              <button className="btn ghost sm" onClick={() => setFiles([])} disabled={busy}>
                Clear
              </button>
            </div>
          </>
        )}
      </div>

      {err && <div className="banner bad">{err}</div>}
      {rows.length > 0 && (
        <div className="card pad0">
          <table>
            <thead>
              <tr><th>File</th><th>Type</th><th style={{ textAlign: "right" }}>Units</th><th>Errors</th></tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>{r.file}</td>
                  <td><span className="chip">{r.kind}</span></td>
                  <td className="num">{r.units}</td>
                  <td style={{ color: r.errors?.length ? "var(--accent)" : "var(--text-faint)" }}>
                    {r.errors?.length ? r.errors.join("; ") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="caption">
        Student <b>{student}</b> · images are described by a vision model and fall back to OCR.
      </p>
    </>
  );
}

/* ============================================================== Tutor */
export function Tutor({ student }: { student: string }) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [text, setText] = useState("");
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, busy]);

  const send = async () => {
    const q = text.trim();
    if (!q || busy) return;
    setTurns((t) => [...t, { role: "user", content: q }]);
    setText("");
    setBusy(true);
    try {
      const r = await api.ask(q, student, topic || null);
      setTurns((t) => [...t, { role: "assistant", content: r.answer, citations: r.citations, verdict: r.verdict }]);
    } catch (e: any) {
      setTurns((t) => [...t, { role: "assistant", content: `Error: ${e.message}`, verdict: "error" }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="grid2">
        <div className="card pad0 mb0">
          <div className="chat-log" style={{ maxHeight: 560, overflowY: "auto" }}>
            {turns.length === 0 && (
              <div className="empty">
                Ask anything from your uploaded material. Questions the material does not cover are
                declined rather than guessed.
              </div>
            )}
            {turns.map((m, i) => (
              <div key={i} className={`bubble ${m.role === "user" ? "user" : "bot"}${m.verdict === "refuse" ? " refuse" : ""}`}>
                {m.content}
                {m.citations && m.citations.length > 0 && (
                  <span className="cites">📍 {m.citations.join(" · ")}</span>
                )}
              </div>
            ))}
            {busy && <div className="typing"><span /><span /><span /></div>}
            <div ref={endRef} />
          </div>
          <div className="composer">
            <input
              value={text}
              placeholder="Ask from your material…"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            />
            <button className="btn" onClick={send} disabled={busy || !text.trim()}>
              {busy ? "…" : "Ask"}
            </button>
          </div>
        </div>

        <div>
          <div className="card">
            <h3 className="sub">Filter</h3>
            <input value={topic} placeholder="topic (optional)" onChange={(e) => setTopic(e.target.value)} />
            <div className="caption">Restrict retrieval to one topic.</div>
          </div>
          <div className="card">
            <h3 className="sub">This session</h3>
            <div className="metrics">
              <div className="metric"><b>{Math.floor(turns.length / 2)}</b><span>Questions</span></div>
              <div className="metric"><b>{turns.filter((t) => t.verdict === "refuse").length}</b><span>Refusals</span></div>
            </div>
          </div>
          <details className="acc">
            <summary>Full transcript ({turns.length} messages)</summary>
            <div className="acc-body">
              {turns.length === 0 && <div className="empty">Nothing yet.</div>}
              {turns.map((m, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <div className="caption">
                    <b>{m.role === "user" ? "You" : "Tutor"}</b> · turn {Math.floor(i / 2) + 1}
                  </div>
                  <div className="pre" style={{ fontSize: 13.5 }}>{m.content}</div>
                  {m.citations?.length ? <div className="caption">📍 {m.citations.join(" · ")}</div> : null}
                </div>
              ))}
            </div>
          </details>
        </div>
      </div>
    </>
  );
}

/* ============================================================== Quiz */
export function Quiz({ student }: { student: string }) {
  const [scope, setScope] = useState("photosynthesis");
  const [n, setN] = useState(3);
  const [busy, setBusy] = useState(false);
  const [quiz, setQuiz] = useState<{ id: string; qs: Question[]; shortfall: number; reason: string; dupes: number } | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [results, setResults] = useState<{ rows: GradeResult[]; correct: number; total: number; weak: string[] } | null>(null);

  const generate = async () => {
    setBusy(true); setResults(null); setAnswers({});
    try {
      const r = await api.quiz(scope, student, n);
      setQuiz({ id: r.quiz_id, qs: r.questions, shortfall: r.shortfall, reason: r.reason, dupes: r.dupes_dropped });
    } catch (e: any) {
      setQuiz({ id: "", qs: [], shortfall: n, reason: e.message, dupes: 0 });
    } finally { setBusy(false); }
  };

  const verify = async () => {
    if (!quiz) return;
    setBusy(true);
    try {
      const r = await api.grade({
        student_id: student, scope, quiz_id: quiz.id,
        difficulty: quiz.qs[0]?.difficulty ?? "auto", questions: quiz.qs, answers,
      });
      setResults({ rows: r.results, correct: r.correct, total: r.total, weak: r.weak_topics });
    } catch (e: any) {
      setResults({ rows: [], correct: 0, total: quiz.qs.length, weak: [`Error: ${e.message}`] });
    } finally { setBusy(false); }
  };

  const gradeOf = (qh: string) => results?.rows.find((r) => r.qhash === qh);

  return (
    <>
      <div className="card">
        <h2 className="section">Adaptive assessment</h2>
        <div className="row">
          <input className="grow" value={scope} placeholder="Quiz scope / topic"
            onChange={(e) => setScope(e.target.value)} />
          <div style={{ width: 190 }}>
            <div className="caption" style={{ margin: "0 0 4px" }}>{n} question(s)</div>
            <input type="range" min={1} max={8} value={n} onChange={(e) => setN(Number(e.target.value))} />
          </div>
          <button className="btn" onClick={generate} disabled={busy}>Generate</button>
          {quiz && <button className="btn ghost sm" onClick={() => { setQuiz(null); setResults(null); setAnswers({}); }}>Clear</button>}
        </div>
      </div>

      {quiz?.shortfall ? (
        <div className="banner warn">
          Requested {quiz.qs.length + quiz.shortfall}, could only build {quiz.qs.length}. {quiz.reason}
          {quiz.dupes ? ` ${quiz.dupes} duplicate(s) discarded.` : ""}
        </div>
      ) : null}

      {results && (
        <div className="card">
          <div className="scoreboard" style={{ padding: 0, border: 0 }}>
            <div className="score-num">{results.correct}/{results.total}</div>
            <div>
              <div style={{ fontWeight: 600 }}>
                {results.correct === results.total ? "Full marks" : "Keep going"}
              </div>
              <div className="caption">Mastery updated for every topic you answered.</div>
            </div>
          </div>
          {results.weak.length > 0 && (
            <div className="banner warn" style={{ marginTop: 14, marginBottom: 0 }}>
              Weak topics to revise: {results.weak.join(", ")}
            </div>
          )}
        </div>
      )}

      {quiz && quiz.qs.length > 0 && (
        <div className="card pad0 mb0">
          {quiz.qs.map((q, i) => {
            const g = gradeOf(q.qhash);
            return (
              <div className="q" key={q.qhash}>
                {g && (
                  <div className={`verdict ${g.correct ? "ok" : "no"}`}>
                    {g.correct ? "✓ Correct" : "✗ Incorrect"} · <span style={{ fontWeight: 400, fontSize: 12, color: "var(--text-faint)" }}>{g.method}</span>
                  </div>
                )}
                <div className="stem">{i + 1}. {q.stem}</div>
                <div className="meta"><code>{q.difficulty}</code> · source: {q.source}</div>
                {!g && (
                  <textarea
                    rows={2} placeholder="your answer…"
                    value={answers[q.qhash] ?? ""}
                    onChange={(e) => setAnswers((a) => ({ ...a, [q.qhash]: e.target.value }))}
                  />
                )}
                {g && !g.correct && (
                  <>
                    <div className="caption" style={{ marginTop: 10 }}>Your answer</div>
                    <div className="pre" style={{ fontSize: 13.5 }}>{g.given || "(blank)"}</div>
                    <div className="caption" style={{ marginTop: 10 }}>Expected answer</div>
                    <div className="answer-key pre">{g.key}</div>
                  </>
                )}
                {g && <div className="caption">{g.feedback}</div>}
              </div>
            );
          })}
        </div>
      )}

      {quiz && quiz.qs.length > 0 && !results && (
        <button className="btn" style={{ marginTop: 14 }} onClick={verify} disabled={busy}>
          Verify answers
        </button>
      )}
      {!quiz && <div className="banner info">Set a scope and press Generate to build a quiz.</div>}
    </>
  );
}
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type ChatTurn, type GradeResult, type Question } from "../api";
import { Banner, Card, Empty, Field, Ring, useToast } from "./ui";
import {
  IconBook, IconChart, IconChat, IconCheck, IconClock, IconDoc, IconPin,
  IconQuiz, IconSpark, IconUpload, IconWarn, IconX,
} from "./Icons";

/* ========================================================== Upload */
export function Upload({ student }: { student: string }) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [errs, setErrs] = useState<string[]>([]);
  const [over, setOver] = useState(false);
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);

  const totalUnits = useMemo(() => rows.reduce((a, r) => a + (r.units || 0), 0), [rows]);

  const run = async () => {
    if (!files.length) return;
    setBusy(true); setRows([]); setErrs([]);
    try {
      const r = await api.ingest(files);
      setRows(r.files);
      setErrs(r.errors ?? []);
      toast(`Ingested ${r.ingested} file(s) · ${r.units} units`, r.errors?.length ? "bad" : "ok");
    } catch (e: any) {
      toast(e.message ?? String(e), "bad");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Card>
        <p className="eyebrow">Ingest</p>
        <h2 className="title">Add course material</h2>
        <p className="muted" style={{ margin: "0 0 16px" }}>
          PDFs, slide decks, transcripts and images. Every file is parsed, embedded and
          linked back to its exact page, slide or timestamp.
        </p>

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
          <div className="drop-ico"><IconUpload size={30} /></div>
          <strong>Drop files here, or click to browse</strong>
          <span>PDF · PPTX · TXT · SRT · VTT · JPG · PNG — select as many as you like</span>
          <input
            ref={input} type="file" multiple hidden
            accept=".pdf,.pptx,.ppt,.txt,.srt,.vtt,.jpg,.jpeg,.png"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          />
        </div>

        {files.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div className="row" style={{ marginBottom: 10 }}>
              <span className="muted">{files.length} file(s) staged</span>
              <span className="grow" />
              <button className="btn ghost sm" onClick={() => setFiles([])} disabled={busy}>Clear</button>
              <button className="btn" onClick={run} disabled={busy}>
                {busy ? "Ingesting…" : "Ingest material"}
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              {files.map((f, i) => (
                <div className="file-pill" key={i}>
                  <IconDoc size={15} />
                  <span className="fname">{f.name}</span>
                  <span className="muted">{(f.size / 1024 / 1024).toFixed(2)} MB</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {errs.length > 0 && (
        <Banner tone="warn">
          {errs.slice(0, 3).join(" · ")}
          {errs.length > 3 && ` (+${errs.length - 3} more)`}
        </Banner>
      )}

      {rows.length > 0 && (
        <Card pad0>
          <table>
            <thead>
              <tr>
                <th>File</th><th>Type</th><th className="num">Units</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 500 }}>{r.file}</td>
                  <td><span className="chip">{r.kind}</span></td>
                  <td className="num">{r.units}</td>
                  <td>
                    {r.errors?.length
                      ? <span style={{ color: "var(--danger)", fontSize: 12.5 }}>{r.errors.join("; ")}</span>
                      : <span style={{ color: "var(--success)", fontSize: 12.5, display: "inline-flex", gap: 5, alignItems: "center" }}><IconCheck size={13} /> indexed</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {rows.length > 0 && (
        <div className="grid3">
          <div className="metric"><b>{rows.length}</b><span>Documents</span></div>
          <div className="metric"><b>{totalUnits}</b><span>Chunks indexed</span></div>
          <div className="metric"><b>{rows.filter((r) => !r.errors?.length).length}</b><span>Clean</span></div>
        </div>
      )}

      <p className="muted" style={{ marginTop: 18 }}>
        Ingesting as <b style={{ color: "var(--text-dim)" }}>{student}</b>. Images are described by a
        vision model, with OCR as the fallback and a filename stub as the last resort.
      </p>
    </>
  );
}

/* ========================================================== Tutor */
export function Tutor({ student }: { student: string }) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [text, setText] = useState("");
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [full, setFull] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const toast = useToast();

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, busy]);

  const send = async () => {
    const q = text.trim();
    if (!q || busy) return;
    setTurns((t) => [...t, { role: "user", content: q }]);
    setText("");
    setBusy(true);
    try {
      const r = await api.ask(q, student, topic || null);
      setTurns((t) => [...t, { role: "assistant", content: r.answer, citations: r.citations, verdict: r.verdict }]);
      if (r.verdict === "refuse") toast("Not covered by your material — declined rather than guessed.", "info");
    } catch (e: any) {
      toast(e.message ?? String(e), "bad");
      setTurns((t) => [...t, { role: "assistant", content: `Something went wrong: ${e.message}`, verdict: "error" }]);
    } finally { setBusy(false); }
  };

  const shown = full ? turns : turns.slice(-4);
  const refusals = turns.filter((t) => t.verdict === "refuse").length;

  return (
    <div className="grid2">
      <Card pad0 className="mb0">
        <div className="chat-shell">
          <div className="chat-log">
            {turns.length === 0 && (
              <Empty
                icon={<IconChat size={34} />}
                title="Ask anything from your material"
                hint="Answers are grounded in what you uploaded and cite the exact source. Anything the material does not cover is declined instead of guessed."
              />
            )}
            {shown.map((m, i) => (
              <div className={`msg ${m.role === "user" ? "me" : "bot"}${m.verdict === "refuse" ? " refuse" : ""}`} key={i}>
                <div className={`avatar ${m.role === "user" ? "user" : "bot"}`}>
                  {m.role === "user" ? "You" : <IconSpark size={15} />}
                </div>
                <div className="bubble">
                  {m.content}
                  {!!m.citations?.length && (
                    <div className="cites">
                      {m.citations.map((c, j) => <span className="cite" key={j}><IconPin size={11} /> {c}</span>)}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="typing"><span /><span /><span /></div>}
            <div ref={end} />
          </div>
          <div className="composer">
            <input
              className="input"
              value={text}
              placeholder="Ask from your material…"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            />
            <button className="btn" onClick={send} disabled={busy || !text.trim()}>
              {busy ? "Thinking…" : "Ask"}
            </button>
          </div>
        </div>
      </Card>

      <div>
        <Card>
          <p className="eyebrow">Retrieval</p>
          <Field label="Topic filter (optional)">
            <input className="input" value={topic} placeholder="e.g. multi-head attention"
              onChange={(e) => setTopic(e.target.value)} />
          </Field>
          <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
            Narrows the search to a single topic. Leave blank to search everything.
          </p>
        </Card>

        <Card>
          <p className="eyebrow">This session</p>
          <div className="grid3" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div className="metric"><b>{Math.floor(turns.length / 2)}</b><span>Questions</span></div>
            <div className="metric"><b>{refusals}</b><span>Refusals</span></div>
          </div>
        </Card>

        <details className="acc">
          <summary>Full transcript ({turns.length} messages)</summary>
          <div className="acc-body">
            {turns.length === 0 && <div className="muted">Nothing yet.</div>}
            {turns.map((m, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                <div className="muted" style={{ marginBottom: 4 }}>
                  <b style={{ color: "var(--text-dim)" }}>{m.role === "user" ? "You" : "Tutor"}</b> · turn {Math.floor(i / 2) + 1}
                </div>
                <div className="pre" style={{ fontSize: 13.5 }}>{m.content}</div>
                {!!m.citations?.length && (
                  <div className="muted" style={{ marginTop: 6 }}>
                    {[...new Set(m.citations)].join(" · ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        </details>
      </div>
    </div>
  );
}

/* ========================================================== Quiz */
export function Quiz({ student }: { student: string }) {
  const [scope, setScope] = useState("attention");
  const [n, setN] = useState(3);
  const [busy, setBusy] = useState(false);
  const [quiz, setQuiz] = useState<{ id: string; qs: Question[]; requested: number; shortfall: number; reason: string; dupes: number } | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [res, setRes] = useState<{ rows: GradeResult[]; correct: number; total: number; weak: string[] } | null>(null);
  const toast = useToast();

  const generate = async () => {
    setBusy(true); setRes(null); setAnswers({});
    try {
      const r = await api.quiz(scope, student, n);
      setQuiz({ id: r.quiz_id, qs: r.questions, requested: r.requested, shortfall: r.shortfall, reason: r.reason, dupes: r.dupes_dropped });
      toast(`Built ${r.generated} of ${r.requested} question(s)`, r.shortfall ? "bad" : "ok");
    } catch (e: any) {
      setQuiz({ id: "", qs: [], requested: n, shortfall: n, reason: e.message, dupes: 0 });
      toast(e.message ?? String(e), "bad");
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
      setRes({ rows: r.results, correct: r.correct, total: r.total, weak: r.weak_topics });
      toast(`Scored ${r.correct}/${r.total}`, r.correct === r.total ? "ok" : "info");
    } catch (e: any) {
      toast(e.message ?? String(e), "bad");
    } finally { setBusy(false); }
  };

  const gradeOf = (qh: string) => res?.rows.find((r) => r.qhash === qh);
  const pct = res ? res.correct / Math.max(1, res.total) : 0;

  return (
    <>
      <Card>
        <p className="eyebrow">Adaptive assessment</p>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="grow" style={{ minWidth: 220 }}>
            <Field label="Scope">
              <input className="input" value={scope} placeholder="Topic to be quizzed on"
                onChange={(e) => setScope(e.target.value)} />
            </Field>
          </div>
          <div style={{ width: 170 }}>
            <span className="field-label">Questions · {n}</span>
            <input type="range" min={1} max={8} value={n} onChange={(e) => setN(Number(e.target.value))} />
          </div>
          <button className="btn" onClick={generate} disabled={busy}>
            <IconQuiz size={16} /> {busy && !res ? "Building…" : "Generate quiz"}
          </button>
          {quiz && (
            <button className="btn ghost" onClick={() => { setQuiz(null); setRes(null); setAnswers({}); }}>
              Reset
            </button>
          )}
        </div>
        <p className="muted" style={{ margin: "12px 0 0" }}>
          Difficulty adapts to your mastery. Questions are verified against the source and
          never repeat a stem you have already been served.
        </p>
      </Card>

      {quiz && quiz.shortfall > 0 && (
        <Banner tone="warn">
          <b>{quiz.reason}</b>
          {quiz.dupes ? ` ${quiz.dupes} duplicate question(s) were discarded.` : ""}
        </Banner>
      )}

      {!quiz && (
        <Card>
          <Empty icon={<IconQuiz size={34} />} title="No quiz yet"
            hint="Pick a scope and generate. Questions are mined from the exact passages you uploaded." />
        </Card>
      )}

      {quiz && quiz.qs.length === 0 && !busy && (
        <Card><Empty icon={<IconWarn size={32} />} title="Nothing to quiz on that scope"
          hint="Try a broader topic, or ingest more material first." /></Card>
      )}

      {quiz && quiz.qs.length > 0 && (
        <Card pad0>
          {res && (
            <div className="score">
              <div className="score-ring">
                <Ring value={pct} size={66} stroke={6} />
                <span>{res.correct}/{res.total}</span>
              </div>
              <div>
                <div style={{ fontWeight: 620, fontSize: 15 }}>
                  {pct === 1 ? "Full marks" : pct >= 0.6 ? "Good progress" : "Worth another pass"}
                </div>
                <div className="muted">Mastery updated for every topic you answered.</div>
              </div>
              <span className="grow" />
              {res.weak.length > 0 && (
                <span className="chip weak"><IconWarn size={12} /> {res.weak.join(", ")}</span>
              )}
            </div>
          )}

          <div className="q-list">
            {quiz.qs.map((q, i) => {
              const g = gradeOf(q.qhash);
              return (
                <div className="q" key={q.qhash}>
                  {g && (
                    <div className={`verdict ${g.correct ? "ok" : "no"}`} style={{ marginBottom: 8 }}>
                      {g.correct ? <IconCheck size={14} /> : <IconX size={14} />}
                      {g.correct ? "Correct" : "Incorrect"}
                      <span className="vtag">· {g.method}</span>
                    </div>
                  )}
                  <div className="q-top">
                    <span className="q-num">Q{i + 1}</span>
                    <span className="q-stem">{q.stem}</span>
                  </div>
                  <div className="q-meta">
                    <span className="chip">{q.difficulty}</span>
                    <span><IconBook size={12} /> {q.source}</span>
                  </div>

                  {!g ? (
                    <textarea
                      className="textarea" rows={2} placeholder="Write your answer…"
                      value={answers[q.qhash] ?? ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [q.qhash]: e.target.value }))}
                    />
                  ) : (
                    <>
                      <div className="q-meta" style={{ marginTop: 12 }}>Your answer</div>
                      <div className={`answer-key mine pre`}>{g.given || "(left blank)"}</div>
                      {!g.correct && (
                        <>
                          <div className="q-meta" style={{ marginTop: 12 }}>Expected answer</div>
                          <div className="answer-key pre">{g.key}</div>
                        </>
                      )}
                      <div className="muted" style={{ marginTop: 10 }}>{g.feedback}</div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {quiz && quiz.qs.length > 0 && !res && (
        <div className="row" style={{ marginTop: 14 }}>
          <button className="btn lg" onClick={verify} disabled={busy}>
            <IconCheck size={16} /> {busy ? "Grading…" : "Verify answers"}
          </button>
          <span className="muted">Grading is deterministic — keyword overlap plus a cross-model check.</span>
        </div>
      )}
    </>
  );
}

/* ========================================================== Dashboard */
export function Dashboard({ student }: { student: string }) {
  const [mastery, setMastery] = useState<Record<string, number>>({});
  const [hist, setHist] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [m, h] = await Promise.all([api.mastery(student), api.history(student)]);
        if (alive) { setMastery(m); setHist(h); }
      } finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [student]);

  const rows = Object.entries(mastery).sort((a, b) => a[1] - b[1]);
  const avg = rows.length ? rows.reduce((a, [, v]) => a + v, 0) / rows.length : 0;
  const weak = rows.filter(([, v]) => v <= 0.4);
  const strong = rows.filter(([, v]) => v > 0.75);

  if (loading) {
    return (
      <div className="overview">
        <Card><div className="skel" style={{ height: 210 }} /></Card>
        <Card><div className="skel" style={{ height: 130 }} /></Card>
      </div>
    );
  }

  return (
    <>
      <div className="grid3" style={{ marginBottom: 18 }}>
        <div className="metric"><b>{Math.round(avg * 100)}%</b><span>Average mastery</span></div>
        <div className="metric"><b>{hist?.counts.chats ?? 0}</b><span>Questions asked</span></div>
        <div className="metric"><b>{hist?.counts.quizzes ?? 0}</b><span>Quizzes taken</span></div>
      </div>

      <div className="overview">
        <Card>
          <p className="eyebrow">Learner model</p>
          <h2 className="title">Mastery by topic</h2>
          <p className="muted" style={{ margin: "4px 0 18px" }}>
            Bayesian Knowledge Tracing — updated after every graded answer and decayed daily.
          </p>

          {rows.length === 0 ? (
            <Empty icon={<IconChart size={30} />} title="No mastery recorded yet"
              hint="Take a quiz or ask the tutor something — mastery builds from your answers." />
          ) : rows.map(([topic, v]) => (
            <div className="ring-card" key={topic}>
              <div className="ring-wrap">
                <Ring value={v} />
                <span>{Math.round(v * 100)}%</span>
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 520, fontSize: 14 }}>{topic}</div>
                <div className="muted">
                  {v > 0.75 ? "Strong — move on" : v > 0.4 ? "Developing" : "Needs revision"}
                </div>
              </div>
            </div>
          ))}
        </Card>

        <div>
          <Card>
            <p className="eyebrow">Where to focus</p>
            {rows.length === 0 ? <div className="muted">No data yet.</div> : (
              <>
                <div className="chips" style={{ marginBottom: 14 }}>
                  {weak.length > 0 && weak.map(([t]) => <span className="chip weak" key={t}>{t}</span>)}
                  {weak.length === 0 && <span className="chip strong">All topics healthy</span>}
                </div>
                {strong.length > 0 && (
                  <>
                    <div className="muted" style={{ marginBottom: 7 }}>Mastered</div>
                    <div className="chips">
                      {strong.map(([t, v]) => <span className="chip strong" key={t}>{t} · {Math.round(v * 100)}%</span>)}
                    </div>
                  </>
                )}
              </>
            )}
          </Card>

          <Card>
            <p className="eyebrow">Library</p>
            <div className="grid3" style={{ gridTemplateColumns: "1fr 1fr" }}>
              <div className="metric"><b>{hist?.counts.uploads ?? 0}</b><span>Documents</span></div>
              <div className="metric"><b>{rows.length}</b><span>Topics</span></div>
            </div>
          </Card>
        </div>
      </div>

      {!!hist?.grades.length && (
        <Card pad0>
          <table>
            <thead><tr><th>When</th><th>Scope</th><th>Score</th><th>Weak topics</th></tr></thead>
            <tbody>
              {[...hist.grades].reverse().map((g: any, i: number) => (
                <tr key={i}>
                  <td className="muted"><IconClock size={12} /> {new Date(g.ts * 1000).toLocaleString()}</td>
                  <td style={{ fontWeight: 500 }}>{g.scope}</td>
                  <td><b>{g.score}</b></td>
                  <td className="dim">{g.weak_topics?.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
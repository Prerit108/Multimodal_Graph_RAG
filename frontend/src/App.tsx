import { useCallback, useEffect, useState } from "react";
import { api, type HistoryBundle } from "./api";
import { Quiz, Tutor, Upload } from "./components/views";

/* ============================================================== Dashboard */
function Dashboard({ student }: { student: string }) {
  const [mastery, setMastery] = useState<Record<string, number>>({});
  const [hist, setHist] = useState<HistoryBundle | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, h] = await Promise.all([api.mastery(student), api.history(student)]);
      setMastery(m); setHist(h); setErr(null);
    } catch (e: any) { setErr(e.message ?? String(e)); }
  }, [student]);

  useEffect(() => { load(); }, [load, student]);

  const rows = Object.entries(mastery).sort((a, b) => a[1] - b[1]);
  const band = (v: number) => (v > 0.75 ? "strong" : v > 0.4 ? "medium" : "weak");

  return (
    <>
      {err && <div className="banner bad">{err}</div>}
      <div className="grid2">
        <div className="card">
          <h2 className="section">Mastery per topic <span style={{ color: "var(--text-faint)", fontWeight: 400, fontSize: 13 }}>(Bayesian Knowledge Tracing)</span></h2>
          {rows.length === 0 && <div className="empty">No mastery yet — take a quiz or ask the tutor something.</div>}
          {rows.map(([topic, v]) => (
            <div className="mrow" key={topic}>
              <div className="mtop"><b>{topic}</b><span>{Math.round(v * 100)}%</span></div>
              <div className="bar"><i className={band(v)} style={{ width: `${Math.max(2, Math.round(v * 100))}%` }} /></div>
            </div>
          ))}
        </div>

        <div>
          <div className="card">
            <h3 className="sub">Study activity</h3>
            <div className="metrics">
              <div className="metric"><b>{hist?.counts.chats ?? 0}</b><span>Questions</span></div>
              <div className="metric"><b>{hist?.counts.quizzes ?? 0}</b><span>Quizzes</span></div>
              <div className="metric"><b>{hist?.counts.uploads ?? 0}</b><span>Documents</span></div>
            </div>
          </div>
          <div className="card">
            <h3 className="sub">Bands</h3>
            <div className="chips">
              {rows.length === 0 && <span className="empty">—</span>}
              {rows.map(([t, v]) => (
                <span className={`chip ${band(v)}`} key={t}>{t} · {Math.round(v * 100)}%</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {!!hist?.grades.length && (
        <div className="card pad0">
          <table>
            <thead><tr><th>When</th><th>Scope</th><th>Score</th><th>Weak topics</th></tr></thead>
            <tbody>
              {[...hist.grades].reverse().map((g, i) => (
                <tr key={i}>
                  <td>{new Date((g.ts as number) * 1000).toLocaleString()}</td>
                  <td>{g.scope}</td>
                  <td><b>{g.score}</b></td>
                  <td style={{ color: "var(--text-dim)" }}>
                    {(g.weak_topics as string[])?.join(", ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ============================================================== History */
function History({ student, onChange }: { student: string; onChange: () => void }) {
  const [h, setH] = useState<HistoryBundle | null>(null);
  const [full, setFull] = useState(false);

  const load = useCallback(async () => {
    try { setH(await api.history(student)); } catch { /* ignore */ }
  }, [student]);

  useEffect(() => { load(); }, [load]);

  const clear = async () => {
    await api.clearHistory(student);
    await load(); onChange();
  };

  return (
    <>
      <div className="card">
        <div className="row">
          <h2 className="section mb0 grow">Saved history — <b>{student}</b></h2>
          <label className="row tight" style={{ fontSize: 13, color: "var(--text-dim)" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={full} onChange={(e) => setFull(e.target.checked)} />
            complete answers
          </label>
          <button className="btn ghost sm" onClick={clear}>Delete history</button>
        </div>
        <div className="caption">Stored on the server in data/checkpoints/history/{student}.jsonl — survives restarts.</div>
      </div>

      <div className="grid2">
        <div>
          <h3 className="sub">Tutor conversations ({h?.chats.length ?? 0})</h3>
          {!h?.chats.length && <div className="empty">No conversations yet.</div>}
          {[...h?.chats ?? []].reverse().map((c, i) => {
            const q = String(c.question ?? "");
            return (
              <details className="acc" key={i}>
                <summary>{q.length > 68 ? q.slice(0, 68) + "…" : q}</summary>
                <div className="acc-body">
                  <div className="caption">{new Date((c.ts as number) * 1000).toLocaleString()}</div>
                  <div className="pre" style={{ fontSize: 14, marginTop: 8 }}>
                    {full ? String(c.answer ?? "") : String(c.answer ?? "").slice(0, 400) + "…"}
                  </div>
                  {!!(c.citations as string[])?.length && (
                    <div className="caption">📍 {(c.citations as string[]).join(" · ")}</div>
                  )}
                  {c.verdict === "refuse" && <div className="banner warn" style={{ marginTop: 10, marginBottom: 0 }}>Refused — not covered by the material.</div>}
                </div>
              </details>
            );
          })}
        </div>

        <div>
          <h3 className="sub">Quiz attempts ({h?.grades.length ?? 0})</h3>
          {!h?.grades.length && <div className="empty">No quizzes yet.</div>}
          {[...h?.grades ?? []].reverse().map((g, i) => (
            <details className="acc" key={i}>
              <summary>{g.scope} — <b>{g.score}</b></summary>
              <div className="acc-body">
                <div className="caption">{new Date((g.ts as number) * 1000).toLocaleString()}</div>
                {(g.details as any[] ?? []).map((d, j) => (
                  <div key={j} style={{ marginTop: 10 }}>
                    <div className={`verdict ${d.correct ? "ok" : "no"}`}>
                      {d.correct ? "✓" : "✗"} <span style={{ fontWeight: 400, fontSize: 12 }}>{d.method}</span>
                    </div>
                    {!d.correct && (
                      <div className="answer-key pre" style={{ fontSize: 13 }}>
                        {full ? d.key : String(d.key ?? "").slice(0, 200) + "…"}
                      </div>
                    )}
                  </div>
                ))}
                {!!(g.weak_topics as string[])?.length && (
                  <div className="banner warn" style={{ marginTop: 12, marginBottom: 0 }}>
                    Weak: {(g.weak_topics as string[]).join(", ")}
                  </div>
                )}
              </div>
            </details>
          ))}

          {!!h?.uploads.length && (
            <>
              <h3 className="sub" style={{ marginTop: 20 }}>Documents ingested ({h.uploads.length})</h3>
              <div className="card pad0">
                <table>
                  <thead><tr><th>File</th><th>Type</th><th style={{ textAlign: "right" }}>Units</th></tr></thead>
                  <tbody>
                    {[...h.uploads].reverse().map((u, i) => (
                      <tr key={i}>
                        <td>{u.file}</td>
                        <td><span className="chip">{u.kind}</span></td>
                        <td className="num">{u.units}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

/* ============================================================== App */
const TABS = ["Upload", "Tutor", "Quiz", "Dashboard", "History"] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [tab, setTab] = useState<Tab>("Upload");
  const [student, setStudent] = useState("demo-student");
  const [health, setHealth] = useState<"checking" | "ok" | "bad">("checking");
  const [, bump] = useState(0);

  useEffect(() => {
    api.health().then(() => setHealth("ok")).catch(() => setHealth("bad"));
  }, []);

  const refresh = () => bump((n) => n + 1);

  return (
    <div className="app">
      <header className="masthead">
        <h1>📚 Learning Companion</h1>
        <span className="sub">source-grounded tutoring · adaptive assessment · BKT mastery</span>
      </header>

      <div className="controls">
        <label htmlFor="sid">Student</label>
        <input id="sid" type="text" value={student} style={{ width: 200 }}
          onChange={(e) => setStudent(e.target.value)} />
        <div className="health">
          <span className={`dot ${health === "ok" ? "ok" : health === "bad" ? "bad" : ""}`} />
          {health === "ok" ? "API connected" : health === "bad" ? "API unreachable — is uvicorn running?" : "checking…"}
        </div>
      </div>

      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t} className={`tab${tab === t ? " active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </nav>

      {tab === "Upload" && <Upload student={student} />}
      {tab === "Tutor" && <Tutor student={student} />}
      {tab === "Quiz" && <Quiz student={student} />}
      {tab === "Dashboard" && <Dashboard student={student} key={student} />}
      {tab === "History" && <History student={student} onChange={refresh} />}
    </div>
  );
}
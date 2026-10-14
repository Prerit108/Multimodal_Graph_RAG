import { useCallback, useEffect, useState } from "react";
import { api, type HistoryBundle } from "./api";
import { Dashboard, Quiz, Tutor, Upload } from "./components/views";
import { Card, Empty, ToastHost, useToast } from "./components/ui";
import {
  IconChart, IconChat, IconCheck, IconClock, IconDoc, IconQuiz,
  IconSpark, IconTrash, IconUpload, IconWarn,
} from "./components/Icons";

/* ========================================================== History */
function History({ student, bump }: { student: string; bump: () => void }) {
  const [h, setH] = useState<HistoryBundle | null>(null);
  const [full, setFull] = useState(false);
  const toast = useToast();

  const load = useCallback(async () => {
    try { setH(await api.history(student)); } catch { /* ignore */ }
  }, [student]);

  useEffect(() => { load(); }, [load]);

  const wipe = async () => {
    if (!confirm(`Delete all saved history for "${student}"? This cannot be undone.`)) return;
    await api.clearHistory(student);
    await load(); bump();
    toast(`History cleared for ${student}`, "ok");
  };

  return (
    <>
      <Card>
        <div className="row">
          <div className="grow">
            <p className="eyebrow">Archive</p>
            <h2 className="title">Saved history · {student}</h2>
          </div>
          <label className="check">
            <input type="checkbox" checked={full} onChange={(e) => setFull(e.target.checked)} />
            complete answers
          </label>
          <button className="btn danger sm" onClick={wipe}>
            <IconTrash size={14} /> Delete all
          </button>
        </div>
        <p className="muted" style={{ margin: "10px 0 0" }}>
          Every question, answer, quiz and grade is appended to
          <code style={{ margin: "0 5px" }}>data/checkpoints/history/{student}.jsonl</code>
          on the server — it survives restarts and is available across sessions.
        </p>
      </Card>

      <div className="grid2">
        <div>
          <p className="eyebrow">Tutor · {h?.chats.length ?? 0} conversations</p>
          {!h?.chats.length && <Card><Empty icon={<IconChat size={28} />} title="Nothing yet" /></Card>}
          {[...h?.chats ?? []].reverse().map((c: any, i: number) => (
            <details className="acc" key={i}>
              <summary>{String(c.question ?? "").slice(0, 74)}</summary>
              <div className="acc-body">
                <div className="muted" style={{ marginBottom: 10 }}>
                  <IconClock size={11} /> {new Date(c.ts * 1000).toLocaleString()}
                </div>
                <div className="pre" style={{ fontSize: 14 }}>
                  {full ? String(c.answer ?? "") : String(c.answer ?? "").slice(0, 420) + "…"}
                </div>
                {!!c.citations?.length && (
                  <div className="chips" style={{ marginTop: 11 }}>
                    {[...new Set(c.citations as string[])].map((x, j) => <span className="chip" key={j}>{x}</span>)}
                  </div>
                )}
                {c.verdict === "refuse" && (
                  <div className="banner warn" style={{ margin: "12px 0 0" }}>
                    Refused — not covered by the material.
                  </div>
                )}
              </div>
            </details>
          ))}
        </div>

        <div>
          <p className="eyebrow">Assessments · {h?.grades.length ?? 0}</p>
          {!h?.grades.length && <Card><Empty icon={<IconQuiz size={28} />} title="No quizzes yet" /></Card>}
          {[...h?.grades ?? []].reverse().map((g: any, i: number) => (
            <details className="acc" key={i}>
              <summary>{g.scope} — <b>{g.score}</b></summary>
              <div className="acc-body">
                <div className="muted" style={{ marginBottom: 10 }}>
                  <IconClock size={11} /> {new Date(g.ts * 1000).toLocaleString()}
                </div>
                {(g.details ?? []).map((d: any, j: number) => (
                  <div key={j} style={{ marginTop: 11 }}>
                    <div className={`verdict ${d.correct ? "ok" : "no"}`}>
                      {d.correct ? <IconCheck size={13} /> : <IconWarn size={13} />}
                      {d.correct ? "Correct" : "Incorrect"}<span className="vtag">· {d.method}</span>
                    </div>
                    {!d.correct && (
                      <div className="answer-key pre" style={{ marginTop: 7, fontSize: 13 }}>
                        {full ? d.key : String(d.key ?? "").slice(0, 220) + "…"}
                      </div>
                    )}
                  </div>
                ))}
                {!!g.weak_topics?.length && (
                  <div className="chips" style={{ marginTop: 13 }}>
                    {g.weak_topics.map((w: string, j: number) => <span className="chip weak" key={j}>{w}</span>)}
                  </div>
                )}
              </div>
            </details>
          ))}

          {!!h?.uploads.length && (
            <>
              <p className="eyebrow" style={{ marginTop: 22 }}>Library · {h.uploads.length} documents</p>
              <Card pad0>
                <table>
                  <thead><tr><th>File</th><th>Type</th><th className="num">Units</th></tr></thead>
                  <tbody>
                    {[...h.uploads].reverse().map((u: any, i: number) => (
                      <tr key={i}>
                        <td><IconDoc size={13} /> {u.file}</td>
                        <td><span className="chip">{u.kind}</span></td>
                        <td className="num">{u.units}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </>
          )}
        </div>
      </div>
    </>
  );
}

/* ========================================================== App shell */
const NAV = [
  { id: "upload", label: "Library", icon: <IconUpload size={17} />, blurb: "Add course material" },
  { id: "tutor", label: "Tutor", icon: <IconChat size={17} />, blurb: "Grounded Q&A with citations" },
  { id: "quiz", label: "Assess", icon: <IconQuiz size={17} />, blurb: "Adaptive quizzes" },
  { id: "dashboard", label: "Mastery", icon: <IconChart size={17} />, blurb: "Progress and weak topics" },
  { id: "history", label: "History", icon: <IconClock size={17} />, blurb: "Past sessions" },
] as const;

type TabId = (typeof NAV)[number]["id"];

function Shell() {
  const [tab, setTab] = useState<TabId>("upload");
  const [student, setStudent] = useState("demo-student");
  const [health, setHealth] = useState<"checking" | "ok" | "bad">("checking");
  const [, setTick] = useState(0);

  useEffect(() => {
    api.health().then(() => setHealth("ok")).catch(() => setHealth("bad"));
  }, []);

  const bump = () => setTick((n) => n + 1);
  const active = NAV.find((n) => n.id === tab)!;

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <div className="brand-mark"><IconSpark size={18} /></div>
          <div style={{ minWidth: 0 }}>
            <div className="brand-name">Learning Companion</div>
            <div className="brand-sub">LangGraph RAG</div>
          </div>
        </div>

        <nav className="nav">
          {NAV.map((n) => (
            <button
              key={n.id}
              className={`nav-item${tab === n.id ? " active" : ""}`}
              onClick={() => setTab(n.id)}
            >
              <span className="nav-ico">{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>

        <div className="rail-foot">
          <label className="field">
            <span className="field-label">Student</span>
            <input
              className="input" value={student}
              onChange={(e) => setStudent(e.target.value)}
              placeholder="your id"
            />
          </label>
          <div className="status" style={{ marginTop: 12 }}>
            <span className={`dot ${health === "ok" ? "ok" : health === "bad" ? "bad" : ""}`} />
            {health === "ok" ? "API connected" : health === "bad" ? "API unreachable" : "connecting…"}
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{active.label}</h1>
            <div className="crumb">{active.blurb}</div>
          </div>
          <div className="topbar-right">
            <span className="chip">{student}</span>
          </div>
        </header>

        <div className="content">
          {tab === "upload" && <Upload student={student} />}
          {tab === "tutor" && <Tutor student={student} />}
          {tab === "quiz" && <Quiz student={student} />}
          {tab === "dashboard" && <Dashboard student={student} key={student} />}
          {tab === "history" && <History student={student} bump={bump} />}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ToastHost>
      <Shell />
    </ToastHost>
  );
}
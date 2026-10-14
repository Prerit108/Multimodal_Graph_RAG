// Thin API client. All calls go through the Vite dev proxy (/api -> FastAPI).
const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function json<T>(res: Response | Promise<Response>): Promise<T> {
  const r = await res;
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return r.json();
}

const post = <T,>(url: string, body: unknown) =>
  json<T>(fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }));

export interface IngestRow {
  file: string;
  kind: string;
  units: number;
  errors: string[];
}

export interface Question {
  stem: string;
  answer_key: string;
  source: string;
  difficulty: string;
  qhash: string;
  topic?: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  verdict?: string;
}

export interface GradeResult {
  qhash: string;
  correct: boolean;
  method: string;
  given: string;
  key: string;
  source: string;
  feedback: string;
}

export interface HistoryBundle {
  chats: Array<Record<string, any>>;
  quizzes: Array<Record<string, any>>;
  grades: Array<Record<string, any>>;
  uploads: Array<Record<string, any>>;
  counts: { chats: number; quizzes: number; grades: number; uploads: number };
}

export const api = {
  base: BASE,

  health: () => fetch(`${BASE}/health`).then(json<Record<string, any>>),

  ingest: async (files: File[]): Promise<{ ingested: number; units: number; files: IngestRow[]; errors: string[] }> => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return json(await fetch(`${BASE}/ingest`, { method: "POST", body: fd }));
  },

  ask: (question: string, studentId: string, topic?: string | null) =>
    post<{ answer: string; verdict: string; citations: string[] }>(`${BASE}/chat`, {
      question, student_id: studentId, topic: topic || null,
    }),

  quiz: (scope: string, studentId: string, n: number) =>
    post<{ quiz_id: string; questions: Question[]; requested: number; generated: number; shortfall: number; reason: string; dupes_dropped: number }>(
      `${BASE}/quiz`, { scope, student_id: studentId, difficulty: "auto", n },
    ),

  grade: (payload: {
    student_id: string;
    scope: string;
    quiz_id: string;
    difficulty: string;
    questions: Question[];
    answers: Record<string, string>;
  }) => post<{ results: GradeResult[]; correct: number; total: number; weak_topics: string[] }>(`${BASE}/quiz/grade`, payload),

  mastery: (studentId: string) =>
    json<Record<string, number>>(fetch(`${BASE}/mastery/${encodeURIComponent(studentId)}`)),

  history: (studentId: string) =>
    json<HistoryBundle>(fetch(`${BASE}/history/${encodeURIComponent(studentId)}`)),

  clearHistory: (studentId: string) =>
    json<{ cleared: string }>(fetch(`${BASE}/history/${encodeURIComponent(studentId)}`, { method: "DELETE" })),
};
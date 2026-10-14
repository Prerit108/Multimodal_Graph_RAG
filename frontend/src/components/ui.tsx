import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { IconCheck, IconWarn, IconX } from "./Icons";

/* ---------------------------------------------------------------- toasts */
type Toast = { id: number; text: string; tone: "ok" | "bad" | "info" };
type ToastCtx = (text: string, tone?: Toast["tone"]) => void;

const Ctx = createContext<ToastCtx>(() => {});
export const useToast = () => useContext(Ctx);

export function ToastHost({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);

  const push = useCallback<ToastCtx>((text, tone = "info") => {
    const id = Date.now() + Math.random();
    setItems((t) => [...t, { id, text, tone }]);
    setTimeout(() => setItems((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  const value = useMemo(() => push, [push]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="toast-wrap">
        {items.map((t) => (
          <div key={t.id} className={`toast ${t.tone}`}>
            <span style={{ display: "flex", gap: 9, alignItems: "flex-start" }}>
              <span style={{ marginTop: 2, flex: "none" }}>
                {t.tone === "ok" ? <IconCheck size={15} /> : t.tone === "bad" ? <IconX size={15} /> : <IconWarn size={15} />}
              </span>
              <span>{t.text}</span>
            </span>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

/* ---------------------------------------------------------------- bits */
export function Banner({ tone = "info", children }: { tone?: "info" | "ok" | "warn" | "bad"; children: ReactNode }) {
  return (
    <div className={`banner ${tone}`}>
      <span className="bico">{tone === "ok" ? <IconCheck size={15} /> : tone === "bad" ? <IconX size={15} /> : <IconWarn size={15} />}</span>
      <span>{children}</span>
    </div>
  );
}

export function Empty({ icon, title, hint }: { icon?: ReactNode; title: string; hint?: string }) {
  return (
    <div className="empty">
      {icon && <div className="empty-ico">{icon}</div>}
      <div style={{ fontWeight: 550, color: "var(--text-dim)", marginBottom: 4 }}>{title}</div>
      {hint && <div style={{ fontSize: 13, maxWidth: 380, margin: "0 auto" }}>{hint}</div>}
    </div>
  );
}

/** Animated mastery donut. 0–1 value. */
export function Ring({ value, size = 46, stroke = 5, tone }: { value: number; size?: number; stroke?: number; tone?: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value));
  const band = tone ?? (pct > 0.75 ? "var(--success)" : pct > 0.4 ? "var(--warn)" : "var(--danger)");
  return (
    <svg className="ring" viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-3)" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none" stroke={band} strokeWidth={stroke}
        strokeLinecap="round" strokeDasharray={c}
        strokeDashoffset={c - pct * c}
        style={{ transition: "stroke-dashoffset 0.7s cubic-bezier(0.22,1,0.36,1)" }}
      />
    </svg>
  );
}

export function Card({ children, className = "", pad0, hover }: { children: ReactNode; className?: string; pad0?: boolean; hover?: boolean }) {
  return <div className={`card${pad0 ? " pad0" : ""}${hover ? " hover" : ""} ${className}`}>{children}</div>;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}
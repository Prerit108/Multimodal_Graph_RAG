import { useState } from "react";

export function PageAssessment() {
  const [scope, setScope] = useState("");
  const [count, setCount] = useState(5);
  const [generated, setGenerated] = useState(false);

  return (
    <>
      <div className="mt-6 grid gap-4 rounded-xl border border-white/10 bg-black/20 p-4 sm:grid-cols-[minmax(0,1fr)_220px] sm:items-end">
        <label className="block text-xs text-warm-cream/65">
          Scope / topic
          <input className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-warm-cream outline-none focus:border-ember/60" onChange={(event) => setScope(event.target.value)} value={scope} />
        </label>
        <label className="block text-xs text-warm-cream/65">
          <span className="flex justify-between">Questions <span className="font-mono text-ember">{count}</span></span>
          <input className="mt-3 w-full accent-[#E38343]" max={8} min={1} onChange={(event) => setCount(Number(event.target.value))} type="range" value={count} />
          <span className="mt-1 flex justify-between font-mono text-[9px] text-warm-cream/35"><span>1</span><span>8</span></span>
        </label>
        <button className="rounded-lg bg-ember px-4 py-3 text-xs font-semibold text-deep-ink transition hover:brightness-110 sm:col-span-2" onClick={() => setGenerated(true)} type="button">
          Generate Quiz
        </button>
      </div>
      {generated && <p aria-live="polite" className="mt-4 font-mono text-[10px] uppercase tracking-wider text-warm-cream/55">Quiz generation is not connected.</p>}
      <div className="mt-5 rounded-xl border border-white/10 bg-black/20 px-4 py-8 text-center text-xs text-warm-cream/40">
        No questions to display.
      </div>
    </>
  );
}

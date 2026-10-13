const currentState = {
  student_id: "demo-student",
  model: "Bayesian Knowledge Tracing",
  topics: {},
};

export function PageMastery() {
  return (
    <>
      <p className="mt-3 text-sm text-warm-cream/60">Mastery data will appear here when available.</p>
      <div className="mt-7 rounded-xl border border-white/10 bg-black/20 px-4 py-8 text-center text-xs text-warm-cream/40">
        No mastery data available.
      </div>
      <div className="mt-8">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-display text-xl text-warm-cream">Notebook state</h2>
          <span className="font-mono text-[9px] uppercase tracking-widest text-warm-cream/35">Current state</span>
        </div>
        <pre className="overflow-x-auto rounded-xl border border-white/10 bg-black/35 p-4 font-mono text-[10px] leading-5 text-[#e5b487] sm:text-xs"><code>{JSON.stringify(currentState, null, 2)}</code></pre>
      </div>
    </>
  );
}

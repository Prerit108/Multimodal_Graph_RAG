import { Icon } from "../../components/ui/Icons";
import { CorkboardPanel } from "../../components/variants/CorkboardPanel";
import { HeroCard } from "../../components/variants/HeroCard";
import { VariantANav } from "../../components/variants/VariantANav";

export default function VariantAPage() {
  return (
    <div className="min-h-screen bg-ink-base text-paper-primary md:flex">
      <VariantANav />
      <main className="mx-auto w-full max-w-workspace px-5 py-7 sm:px-8 lg:px-10" id="workspace">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <a className="text-xs text-paper-muted transition hover:text-accent-candleglow" href="/">← Compare concepts</a>
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-ink-raised px-3 py-2 text-xs text-paper-secondary">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-sage shadow-[0_0_10px_rgba(122,158,126,0.7)]" /> Your library is in a good place
          </div>
        </header>
        <section aria-labelledby="greeting-heading" className="mb-7 fade-in-up">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-amber">Tuesday, October 13</p>
          <h1 className="mt-2 font-display text-3xl sm:text-4xl" id="greeting-heading">Good evening, Alex.</h1>
          <p className="mt-2 text-sm text-paper-muted">Make a little room for what you’re curious about.</p>
        </section>
        <div className="grid gap-5 lg:grid-cols-12">
          <div className="lg:col-span-8"><HeroCard /></div>
          <aside aria-label="Study momentum" className="flex flex-col gap-5 lg:col-span-4">
            <section className="flex flex-1 flex-col justify-between rounded-2xl border border-white/10 bg-ink-raised p-5 shadow-inner-glow">
              <div className="flex items-center justify-between">
                <div><p className="text-xs text-paper-muted">This week</p><h2 className="mt-1 font-display text-xl">A steady rhythm</h2></div>
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-amber/10 text-accent-amber"><Icon className="h-4 w-4" name="spark" /></span>
              </div>
              <div className="mt-8 flex items-end gap-2">
                <span className="font-display text-5xl">4</span><span className="mb-1 text-sm text-paper-secondary">days in a row</span>
              </div>
              <div className="mt-5 flex items-end gap-2" aria-label="Study activity: 4 of 7 days">
                {[48, 72, 56, 92, 34, 18, 10].map((height, index) => (
                  <div className="flex flex-1 flex-col items-center gap-2" key={index}>
                    <span className={`w-full rounded-full ${index < 4 ? "bg-accent-amber/80" : "bg-white/10"}`} style={{ height: `${height}px` }} />
                    <span className="font-mono text-[9px] text-paper-muted">{["M", "T", "W", "T", "F", "S", "S"][index]}</span>
                  </div>
                ))}
              </div>
            </section>
            <section className="rounded-2xl border border-white/10 bg-ambient-surface p-5">
              <p className="text-xs text-paper-muted">Up next in your library</p>
              <div className="mt-4 flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-rose/10 text-accent-rose"><Icon className="h-5 w-5" name="book" /></span>
                <div><h2 className="text-sm font-medium">The living cell</h2><p className="mt-1 text-xs text-paper-muted">Biology · 3 saved notes</p></div>
              </div>
            </section>
          </aside>
          <div className="lg:col-span-12"><CorkboardPanel /></div>
        </div>
        <footer className="mt-7 flex items-center justify-between border-t border-white/10 pt-4 text-xs text-paper-muted">
          <span>A kinder kind of progress.</span><span className="font-mono">STUDY SPACE · 06</span>
        </footer>
      </main>
    </div>
  );
}

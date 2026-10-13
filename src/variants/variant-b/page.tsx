import { Icon } from "../../components/ui/Icons";
import { AmbientBackdrop } from "../../components/variants/AmbientBackdrop";
import { DigitalClockDisplay } from "../../components/variants/DigitalClockDisplay";
import { ShelfRow } from "../../components/variants/ShelfRow";

export default function VariantBPage() {
  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-ink-base text-paper-primary">
      <AmbientBackdrop />
      <main className="mx-auto max-w-workspace px-6 py-7 sm:px-10 lg:px-14">
        <header className="mb-14 flex items-center justify-between">
          <a className="flex items-center gap-2 font-display text-lg" href="/"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-golden-hour text-sm text-ink-base">L</span> The study room</a>
          <a className="text-xs text-paper-muted transition hover:text-accent-candleglow" href="/">← Compare concepts</a>
        </header>
        <section className="grid items-end gap-12 lg:grid-cols-12 lg:gap-8">
          <div className="fade-in-up lg:col-span-7">
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-accent-candleglow">A note to begin with · No. 06</p>
            <h1 className="mt-5 max-w-3xl font-display text-5xl leading-[1.05] tracking-[-0.035em] sm:text-6xl lg:text-7xl">Make room<br />{" "}<span className="italic text-paper-secondary">for deep work.</span></h1>
            <div className="mt-8 flex max-w-lg items-start gap-4 border-l border-accent-amber/50 pl-4">
              <span className="mt-1 text-accent-amber"><Icon className="h-4 w-4" name="spark" /></span>
              <p className="font-display text-lg leading-relaxed text-paper-secondary">“The secret of getting ahead is getting started.” <span className="font-body text-xs text-paper-muted">— Mark Twain</span></p>
            </div>
            <a className="mt-8 inline-flex items-center gap-3 text-sm text-accent-candleglow transition hover:gap-4" href="#reading">
              Find your thread <Icon className="h-4 w-4" name="arrow" />
            </a>
          </div>
          <div className="lg:col-span-5 lg:pb-2">
            <DigitalClockDisplay />
            <div className="mt-4 flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div><p className="text-xs text-paper-muted">The next small step</p><p className="mt-1 text-sm">Revisit your chapter notes</p></div>
              <span className="font-mono text-xs text-accent-sage">12 MIN</span>
            </div>
          </div>
        </section>
        <div className="my-12 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />
        <section aria-label="Current learning path" className="grid gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8" id="reading"><ShelfRow /></div>
          <aside className="rounded-2xl border border-white/10 bg-ambient-surface p-5 lg:col-span-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-paper-muted">A little field note</p>
            <p className="mt-4 font-handwritten text-3xl leading-8 text-pastel-yellow">Follow the question, not the clock.</p>
            <div className="mt-5 flex items-center gap-2 border-t border-white/10 pt-4 text-xs text-paper-muted"><Icon className="h-4 w-4 text-accent-amber" name="book" /> Saved from your journal</div>
          </aside>
        </section>
        <footer className="mt-14 flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-paper-muted">
          <span>A place for thoughtful progress</span><span>Independent study · Est. 2026</span>
        </footer>
      </main>
    </div>
  );
}

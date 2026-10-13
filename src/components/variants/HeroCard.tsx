import { Icon } from "../ui/Icons";

export function HeroCard() {
  return (
    <article className="group relative isolate flex min-h-[340px] flex-col justify-between overflow-hidden rounded-2xl border border-white/10 bg-ambient-surface p-6 shadow-elevation-2 transition duration-500 ease-editorial hover:-translate-y-1 hover:shadow-lamp-glow sm:p-8">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -right-8 top-0 h-64 w-64 rounded-full bg-accent-amber/20 blur-3xl transition duration-700 group-hover:scale-110" />
        <div className="absolute -right-1 bottom-[-7rem] h-64 w-64 rounded-full bg-accent-sunset/20 blur-3xl" />
        <div className="absolute inset-0 bg-warm-vignette opacity-80" />
        <div className="absolute bottom-0 right-[14%] h-32 w-24 rounded-t-[48%] border border-accent-candleglow/20 bg-white/[0.04] shadow-candle-flicker" />
      </div>
      <div className="flex items-center justify-between gap-4">
        <span className="rounded-full border border-accent-candleglow/20 bg-black/20 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-accent-candleglow">Today’s focus</span>
        <span className="font-mono text-xs text-paper-muted">01 / 03</span>
      </div>
      <div className="mt-12 max-w-lg">
        <p className="mb-3 text-sm text-paper-secondary">A little progress, held gently.</p>
        <h2 className="font-display text-3xl leading-tight text-paper-primary sm:text-4xl">Build a better map of the mind.</h2>
        <p className="mt-3 max-w-md text-sm leading-6 text-paper-secondary">Pick up where you left off in neural pathways, then let the ideas find their own connections.</p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <a className="inline-flex items-center gap-2 rounded-full bg-accent-amber px-4 py-2.5 text-sm font-semibold text-ink-base transition duration-300 hover:-translate-y-0.5 hover:bg-accent-candleglow" href="#continue">
            Continue learning <Icon className="h-4 w-4" name="arrow" />
          </a>
          <span className="text-xs text-paper-muted">12 min · Chapter 04</span>
        </div>
      </div>
    </article>
  );
}

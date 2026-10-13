import { Icon, type IconName } from "../ui/Icons";

const items: { label: string; icon: IconName; active?: boolean }[] = [
  { label: "Overview", icon: "grid", active: true },
  { label: "My library", icon: "book" },
  { label: "Focus room", icon: "spark" },
  { label: "Study plan", icon: "clock" },
];

export function VariantANav() {
  return (
    <aside className="flex w-full flex-col border-b border-white/10 bg-ink-raised px-4 py-4 md:sticky md:top-0 md:h-screen md:w-[76px] md:shrink-0 md:items-center md:border-b-0 md:border-r md:px-3 md:py-6">
      <a aria-label="Learning Companion home" className="flex h-11 w-11 items-center justify-center rounded-xl bg-golden-hour font-display text-xl text-ink-base shadow-lamp-glow" href="/">
        L
      </a>
      <nav aria-label="Main navigation" className="mt-6 flex flex-1 gap-2 overflow-x-auto md:mt-12 md:flex-col md:overflow-visible">
        {items.map(({ label, icon, active }) => (
          <a
            aria-current={active ? "page" : undefined}
            aria-label={label}
            className={`group relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-all duration-300 hover:-translate-y-0.5 hover:bg-white/5 hover:text-accent-candleglow ${active ? "bg-white/5 text-accent-amber" : "text-paper-muted"}`}
            href="#workspace"
            key={label}
            title={label}
          >
            {active && <span className="absolute -left-3 h-5 w-0.5 rounded-full bg-accent-amber md:-left-3" />}
            <Icon className="h-5 w-5" name={icon} />
          </a>
        ))}
      </nav>
      <button aria-label="Your profile" className="mt-5 hidden h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-ink-surface font-display text-sm text-paper-secondary transition hover:border-accent-amber/50 md:flex">
        AM
      </button>
    </aside>
  );
}

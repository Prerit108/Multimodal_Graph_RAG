import { Icon } from "../ui/Icons";

const books = [
  { title: "The living cell", detail: "Biology · 8 notes", tone: "from-accent-sage/20 to-ink-raised", label: "01" },
  { title: "A brief history of time", detail: "Physics · 4 notes", tone: "from-accent-sunset/20 to-ink-raised", label: "02" },
  { title: "Patterns in nature", detail: "Study guide · 6 notes", tone: "from-accent-rose/20 to-ink-raised", label: "03" },
  { title: "The quiet algorithm", detail: "Computer science · 2 notes", tone: "from-accent-amber/20 to-ink-raised", label: "04" },
];

export function ShelfRow() {
  return (
    <section aria-labelledby="shelf-heading">
      <div className="mb-4 flex items-end justify-between">
        <div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent-candleglow">Within arm’s reach</p><h2 className="mt-1 font-display text-2xl" id="shelf-heading">Your open books</h2></div>
        <a className="hidden items-center gap-2 text-xs text-paper-secondary transition hover:text-accent-candleglow sm:inline-flex" href="#library">All books <Icon className="h-3.5 w-3.5" name="arrow" /></a>
      </div>
      <div className="relative -mx-1 overflow-x-auto px-1 pb-5 pt-2">
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-10 bg-shelf-glow" />
        <div className="relative flex min-w-max gap-3">
          {books.map(({ title, detail, tone, label }) => (
            <a className={`group w-48 rounded-sm border border-white/10 bg-gradient-to-br ${tone} p-4 shadow-elevation-1 transition duration-300 hover:-translate-y-1 hover:border-accent-candleglow/30 hover:shadow-lamp-glow`} href="#library" key={title}>
              <div className="flex items-center justify-between"><span className="font-mono text-[10px] text-paper-muted">{label} / FIELD NOTES</span><Icon className="h-4 w-4 text-accent-candleglow opacity-0 transition group-hover:opacity-100" name="arrow" /></div>
              <p className="mt-9 font-display text-lg leading-tight">{title}</p>
              <p className="mt-2 text-[11px] text-paper-muted">{detail}</p>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

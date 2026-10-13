import { Icon } from "../ui/Icons";

const notes = [
  { title: "Review cell\nmembranes", meta: "BIOLOGY · 10 MIN", color: "bg-pastel-yellow text-ink-raised", tilt: "-rotate-1" },
  { title: "Ask why the\nmodel matters", meta: "A QUESTION TO KEEP", color: "bg-pastel-pink text-ink-raised", tilt: "rotate-1" },
  { title: "One page of\nquiet reading", meta: "LATER TODAY", color: "bg-pastel-green text-ink-raised", tilt: "-rotate-[0.5deg]" },
];

export function CorkboardPanel() {
  return (
    <section aria-labelledby="corkboard-heading" className="cork-texture rounded-xl p-5 shadow-elevation-2 sm:p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-raised/65">Pinned for later</p>
          <h2 className="mt-1 font-display text-xl text-ink-raised" id="corkboard-heading">A few loose threads</h2>
        </div>
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-raised/10 text-ink-raised"><Icon className="h-4 w-4" name="pin" /></span>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {notes.map(({ title, meta, color, tilt }, index) => (
          <article className={`relative min-h-36 rounded-md p-4 shadow-elevation-1 transition duration-300 ease-spring hover:z-10 hover:rotate-0 hover:-translate-y-1 hover:scale-[1.02] ${color} ${tilt}`} key={title}>
            <span aria-hidden="true" className="absolute -top-1 left-1/2 h-3 w-3 -translate-x-1/2 rounded-full border-2 border-white/60 bg-accent-sunset shadow" />
            <p className="font-handwritten text-2xl leading-6 whitespace-pre-line">{title}</p>
            <p className="mt-5 font-mono text-[9px] tracking-[0.12em] opacity-65">{meta}</p>
            {index === 0 && <span className="absolute bottom-3 right-3 flex h-5 w-5 items-center justify-center rounded-full bg-ink-raised/10"><Icon className="h-3 w-3" name="check" /></span>}
          </article>
        ))}
      </div>
    </section>
  );
}

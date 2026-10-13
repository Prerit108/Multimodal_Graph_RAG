import type { ReactNode } from "react";

interface NarrativeSectionProps {
  id: string;
  index: number;
  eyebrow: string;
  title: string;
  label: string;
  children: ReactNode;
  isLast?: boolean;
}

export function NarrativeSection({
  id,
  index,
  eyebrow,
  title,
  label,
  children,
  isLast = false,
}: NarrativeSectionProps) {
  const nextSection = index === 1 ? "assessment" : "mastery";

  return (
    <section
      aria-labelledby={`${id}-title`}
      className="flex min-h-screen snap-start flex-col items-center justify-center gap-6 px-5 py-12 sm:px-8 sm:py-14 md:px-16"
      data-scroll-section
      data-section-index={index}
      id={id}
    >
      <article className="w-full max-w-4xl rounded-2xl border border-white/10 bg-black/40 p-5 shadow-[0_24px_90px_rgba(0,0,0,0.38)] backdrop-blur-xl sm:p-8 md:p-10">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-ember sm:text-xs">{eyebrow}</p>
          <span className="font-mono text-[9px] uppercase tracking-widest text-warm-cream/40">0{index + 1} / 04</span>
        </div>
        <h2 className="mb-6 font-display text-3xl leading-tight tracking-[-0.025em] text-warm-cream sm:text-4xl md:text-5xl" id={`${id}-title`}>
          {title}
        </h2>
        {children}
      </article>
      {!isLast && <ScrollIndicator target={nextSection} label={label} />}
    </section>
  );
}

function ScrollIndicator({ target, label }: { target: string; label: string }) {
  return (
    <a
      className="flex flex-col items-center gap-1 font-mono text-[9px] uppercase tracking-[0.16em] text-warm-cream/55 transition-colors hover:text-ember sm:text-[10px]"
      href={`#${target}`}
      onClick={(event) => {
        event.preventDefault();
        document.getElementById(target)?.scrollIntoView({ behavior: "smooth" });
      }}
    >
      {label} <span aria-hidden="true" className="animate-bounce text-base text-ember">↓</span>
    </a>
  );
}

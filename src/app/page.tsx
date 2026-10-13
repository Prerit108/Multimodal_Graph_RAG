import { useEffect, useRef, useState } from "react";
import { HeroIngestionCard } from "../components/book/HeroIngestionCard";
import { NarrativeSection } from "../components/book/NarrativeSection";
import { PageAssessment } from "../components/book/PageAssessment";
import { PageMastery } from "../components/book/PageMastery";
import { PageTutor } from "../components/book/PageTutor";

const backgrounds = [
  new URL("../../inspo/Experiencias en Londres.jpg", import.meta.url).href,
  new URL("../../inspo/last 24 hours.jpg", import.meta.url).href,
  new URL("../../inspo/Study Corner Ideas for Small Bedrooms.jpg", import.meta.url).href,
  new URL("../../inspo/Library Style Workspace 📖.jpg", import.meta.url).href,
];

const sectionLabels = [
  "Scroll down to enter Tutor Chat",
  "Scroll down for Knowledge Assessment",
  "Scroll down for Mastery Index",
];

export default function Page() {
  const scrollRoot = useRef<HTMLDivElement>(null);
  const [activeBackground, setActiveBackground] = useState(0);

  useEffect(() => {
    const root = scrollRoot.current;
    if (!root) return;
    const sections = root.querySelectorAll<HTMLElement>("[data-scroll-section]");
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        const index = visible ? Number((visible.target as HTMLElement).dataset.sectionIndex) : NaN;
        if (Number.isInteger(index)) setActiveBackground(index);
      },
      { root, threshold: [0.25, 0.5, 0.7] },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="relative isolate h-screen overflow-hidden bg-deep-ink text-warm-cream">
      <div aria-hidden="true" className="fixed inset-0 -z-10 overflow-hidden">
        {backgrounds.map((src, index) => (
          <img
            alt=""
            className={`absolute inset-0 h-full w-full object-cover object-center transition-opacity duration-1000 ease-in-out ${
              activeBackground === index ? "opacity-100" : "opacity-0"
            }`}
            key={src}
            src={src}
          />
        ))}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0F0C09]/90 via-[#0F0C09]/50 to-black/30" />
        <div className="noise-overlay absolute inset-0 opacity-[0.12]" />
      </div>

      <div
        className="h-screen snap-y snap-mandatory overflow-y-auto scroll-smooth"
        ref={scrollRoot}
      >
        <section
          aria-labelledby="hero-title"
          className="relative flex min-h-screen snap-start flex-col justify-between px-5 py-7 sm:px-8 sm:py-10 md:px-16 md:py-12"
          data-scroll-section
          data-section-index="0"
          id="hero"
        >
          <header className="relative z-10 flex items-center justify-between gap-3">
            <p className="inline-flex rounded-full border border-ember/30 bg-deep-ink/30 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-ember backdrop-blur-md sm:text-xs">
              A note to begin with <span aria-hidden="true" className="mx-2 text-warm-cream/40">·</span> No. 06
            </p>
            <span className="rounded-full border border-white/15 bg-black/30 px-3 py-1.5 font-mono text-[9px] tracking-wide text-warm-cream/75 backdrop-blur-md sm:text-[10px]">
              student_id: demo-student
            </span>
          </header>

          <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-col items-start py-10">
            <p className="mb-4 font-mono text-[10px] uppercase tracking-[0.24em] text-warm-cream/60 sm:text-xs">A quieter kind of ambition</p>
            <h1 className="max-w-4xl font-display text-5xl leading-[1.04] tracking-[-0.035em] text-warm-cream sm:text-6xl md:text-7xl lg:text-8xl" id="hero-title">
              Make room
              <br />
              <span className="italic text-warm-cream/90">for deep work.</span>
            </h1>
            <blockquote className="mt-6 flex max-w-xl items-start gap-4 rounded-r-lg border-l-2 border-ember bg-black/30 p-4 backdrop-blur-md sm:mt-8 sm:p-5">
              <span aria-hidden="true" className="mt-0.5 text-ember">✧</span>
              <p className="font-display text-base leading-relaxed text-warm-cream/90 sm:text-lg">
                “The secret of getting ahead is getting started.”
                <cite className="mt-2 block font-body text-xs not-italic tracking-wide text-warm-cream/55">— Mark Twain</cite>
              </p>
            </blockquote>
            <HeroIngestionCard />
          </div>

          <ScrollIndicator target="tutor" label={sectionLabels[0]} />
        </section>

        <NarrativeSection
          id="tutor"
          index={1}
          label={sectionLabels[1]}
          title="Tutor Chat & Query Engine"
          eyebrow="Interactive Study Room"
        >
          <PageTutor />
        </NarrativeSection>

        <NarrativeSection
          id="assessment"
          index={2}
          label={sectionLabels[2]}
          title="Test Your Mastery"
          eyebrow="Assessment Deck"
        >
          <PageAssessment />
        </NarrativeSection>

        <NarrativeSection
          id="mastery"
          index={3}
          label="You’ve reached the end of this study session"
          title="Mastery Per Topic (BKT)"
          eyebrow="Bayesian Knowledge Tracing"
          isLast
        >
          <PageMastery />
        </NarrativeSection>
      </div>
    </main>
  );
}

function ScrollIndicator({ target, label }: { target: string; label: string }) {
  return (
    <a
      className="relative z-10 mx-auto flex flex-col items-center gap-2 pb-1 font-mono text-[9px] uppercase tracking-[0.16em] text-warm-cream/55 transition-colors hover:text-ember sm:text-[10px]"
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

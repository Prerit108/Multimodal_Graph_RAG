import { useEffect, useState } from "react";
import { Icon } from "../ui/Icons";

function formatTime(date: Date) {
  return new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit", hour12: true }).format(date);
}

export function DigitalClockDisplay() {
  const [time, setTime] = useState(() => formatTime(new Date()));

  useEffect(() => {
    const timer = window.setInterval(() => setTime(formatTime(new Date())), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section aria-label={`Local time ${time}`} className="relative overflow-hidden rounded-2xl border border-white/10 bg-ink-base p-5 shadow-inner-glow sm:p-6">
      <div aria-hidden="true" className="absolute -right-10 -top-12 h-40 w-40 rounded-full bg-accent-amber/10 blur-3xl" />
      <div className="relative flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-paper-muted">Your local time</p>
        <span className="text-accent-candleglow"><Icon className="h-4 w-4" name="sun" /></span>
      </div>
      <p className="relative mt-5 font-mono text-4xl font-bold tracking-[-0.06em] text-paper-primary sm:text-5xl">{time}</p>
      <div className="relative mt-4 flex items-center gap-2 text-xs text-paper-secondary">
        <span className="h-1.5 w-1.5 rounded-full bg-accent-sage" /> A good hour to begin again
      </div>
    </section>
  );
}

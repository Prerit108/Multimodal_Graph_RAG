export function AmbientBackdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -right-40 -top-48 h-[34rem] w-[34rem] rounded-full bg-golden-hour opacity-[0.16] blur-[100px] candle-flicker" />
      <div className="absolute -bottom-56 -left-48 h-[34rem] w-[34rem] rounded-full bg-accent-rose/10 blur-[110px]" />
      <div className="absolute inset-0 bg-warm-vignette opacity-80" />
    </div>
  );
}

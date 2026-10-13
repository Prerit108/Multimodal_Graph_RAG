import VariantAPage from "./variants/variant-a/page";
import VariantBPage from "./variants/variant-b/page";
import Page from "./app/page";

function ComparisonPage() {
  return (
    <main className="min-h-screen bg-ink-base px-4 py-8 text-paper-primary sm:px-8">
      <header className="mx-auto mb-7 flex max-w-workspace flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent-amber">Learning companion · layout studies</p>
          <h1 className="mt-2 font-display text-3xl">Two ways into focus.</h1>
        </div>
        <p className="text-sm text-paper-muted">Phase 06 / Iterative build</p>
      </header>
      <section aria-label="Compare layout variants" className="mx-auto grid max-w-workspace gap-5 xl:grid-cols-2">
        <article className="overflow-hidden rounded-2xl border border-white/10 bg-ink-raised shadow-elevation-3">
          <header className="flex items-center justify-between border-b border-white/10 px-5 py-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-amber">Variant A</p>
              <h2 className="mt-1 font-display text-xl">Bento grid</h2>
            </div>
            <a className="text-xs text-paper-secondary transition-colors hover:text-accent-candleglow" href="/variants/variant-a">Open full view ↗</a>
          </header>
          <iframe className="h-[720px] w-full bg-ink-base" src="/variants/variant-a" title="Bento grid layout preview" />
        </article>
        <article className="overflow-hidden rounded-2xl border border-white/10 bg-ink-raised shadow-elevation-3">
          <header className="flex items-center justify-between border-b border-white/10 px-5 py-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-rose">Variant B</p>
              <h2 className="mt-1 font-display text-xl">Asymmetric editorial</h2>
            </div>
            <a className="text-xs text-paper-secondary transition-colors hover:text-accent-candleglow" href="/variants/variant-b">Open full view ↗</a>
          </header>
          <iframe className="h-[720px] w-full bg-ink-base" src="/variants/variant-b" title="Asymmetric editorial layout preview" />
        </article>
      </section>
    </main>
  );
}

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, "");

  if (path === "/variants/variant-a") return <VariantAPage />;
  if (path === "/variants/variant-b") return <VariantBPage />;
  if (path === "/compare") return <ComparisonPage />;
  return <Page />;
}

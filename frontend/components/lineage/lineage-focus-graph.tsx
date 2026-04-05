export function LineageFocusGraph({
  items,
}: {
  items: Array<{ label: string; detail: string }>;
}) {
  return (
    <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Lineage</p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {items.map((item, index) => (
          <div key={`${item.label}-${index}`} className="flex items-center gap-3">
            <div className="rounded-2xl border border-subtle bg-app px-4 py-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{item.label}</p>
              <p className="mt-1 text-sm font-medium text-strong">{item.detail}</p>
            </div>
            {index < items.length - 1 ? <span className="text-muted">→</span> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

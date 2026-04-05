import Link from "next/link";

export function EmptyState({
  title,
  description,
  actionHref,
  actionLabel,
}: {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <section className="rounded-card border border-dashed border-subtle bg-elevated/70 p-8 text-left shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Empty</p>
      <h2 className="mt-3 font-serif text-3xl text-strong">{title}</h2>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-muted">{description}</p>
      {actionHref && actionLabel ? (
        <Link
          className="mt-6 inline-flex rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90"
          href={actionHref}
        >
          {actionLabel}
        </Link>
      ) : null}
    </section>
  );
}

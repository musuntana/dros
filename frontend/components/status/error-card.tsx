export function ErrorCard({
  title = "Unable to load data",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <section className="rounded-card border border-danger/20 bg-danger/5 p-6 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-danger">Error</p>
      <h2 className="mt-2 font-serif text-2xl text-strong">{title}</h2>
      <p className="mt-3 text-sm leading-7 text-danger">{message}</p>
    </section>
  );
}

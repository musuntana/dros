export function LoadingSurface({
  title = "Loading workspace",
  lines = 4,
}: {
  title?: string;
  lines?: number;
}) {
  return (
    <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
      <div className="h-4 w-32 animate-pulse rounded-full bg-app" />
      <div className="mt-4 h-8 w-64 animate-pulse rounded-full bg-app" />
      <div className="mt-6 space-y-3">
        {Array.from({ length: lines }).map((_, index) => (
          <div key={`${title}-${index}`} className="h-4 animate-pulse rounded-full bg-app" />
        ))}
      </div>
    </section>
  );
}

import { StatusBadge } from "@/components/status/status-badge";

export function BlockingSummary({
  blocked,
  reasons,
  title = "Gate Summary",
}: {
  blocked: boolean;
  reasons: string[];
  title?: string;
}) {
  return (
    <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">{title}</p>
          <h3 className="mt-2 font-serif text-2xl text-strong">
            {blocked ? "Action is blocked" : "No blocking reasons recorded"}
          </h3>
        </div>
        <StatusBadge label={blocked ? "blocked" : "ready"} />
      </div>
      <ul className="mt-4 space-y-2 text-sm text-muted">
        {reasons.length > 0 ? (
          reasons.map((reason) => (
            <li
              key={reason}
              className="rounded-2xl border border-danger/20 bg-danger/5 px-4 py-3 text-danger"
            >
              {reason}
            </li>
          ))
        ) : (
          <li className="rounded-2xl border border-subtle bg-app px-4 py-3">
            Current object can continue to the next stage if downstream checks pass.
          </li>
        )}
      </ul>
    </section>
  );
}

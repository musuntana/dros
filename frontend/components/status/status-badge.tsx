import { cn } from "@/lib/utils";

const semanticClassName: Record<string, string> = {
  approved: "border-success/25 bg-success/10 text-success",
  blocked: "border-danger/25 bg-danger/10 text-danger",
  completed: "border-success/25 bg-success/10 text-success",
  created: "border-info/25 bg-info/10 text-info",
  exported: "border-success/25 bg-success/10 text-success",
  failed: "border-danger/25 bg-danger/10 text-danger",
  needs_human: "border-warning/25 bg-warning/10 text-warning",
  pending: "border-warning/25 bg-warning/10 text-warning",
  queued: "border-info/25 bg-info/10 text-info",
  ready: "border-success/25 bg-success/10 text-success",
  running: "border-info/25 bg-info/10 text-info",
  verified: "border-success/25 bg-success/10 text-success",
  warning: "border-warning/25 bg-warning/10 text-warning",
};

function normalizeLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export function StatusBadge({ label }: { label: string }) {
  const token = label.toLowerCase();
  const className = semanticClassName[token] ?? "border-subtle bg-app text-strong";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]",
        className,
      )}
    >
      {normalizeLabel(label)}
    </span>
  );
}

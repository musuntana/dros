import type { ProjectDetailResponse } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";

export function ProjectHeader({ detail }: { detail: ProjectDetailResponse }) {
  const { project, active_manuscript, latest_snapshot, review_summary_scope } = detail;
  const reviewSummary = detail.review_summary ?? {};
  const reviewScopeLabel =
    review_summary_scope?.label && review_summary_scope.target_version_no
      ? `${review_summary_scope.label} v${review_summary_scope.target_version_no}`
      : review_summary_scope?.label ?? active_manuscript?.title ?? null;
  const reviewSummaryLabel =
    Object.keys(reviewSummary).length > 0
      ? Object.entries(reviewSummary)
          .map(([key, value]) => `${key}:${value}`)
          .join(" · ")
      : review_summary_scope
        ? "No current-version reviews"
        : "No active manuscript";
  const reviewSummaryNote = reviewScopeLabel
    ? `Scoped to ${reviewScopeLabel}.`
    : "Select an active manuscript to track review state on the current chain.";

  return (
    <header className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Research Canvas</p>
          <h1 className="mt-3 font-serif text-4xl text-strong">{project.name}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
            Project-scoped workspace rooted in Control Plane objects. Blocks, evidence, review, and export stay
            traceable from assertion back to artifact and workflow.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge label={project.status} />
          <StatusBadge label={project.compliance_level} />
          <StatusBadge label={project.project_type} />
        </div>
      </div>
      <dl className="mt-6 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-subtle bg-app px-4 py-3">
          <dt className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Latest Snapshot</dt>
          <dd className="mt-2 text-sm font-medium text-strong">
            {latest_snapshot ? `#${latest_snapshot.snapshot_no}` : "No snapshot"}
          </dd>
          <p className="mt-1 text-xs text-muted">
            {latest_snapshot ? formatDateTime(latest_snapshot.created_at) : "Create a dataset snapshot to enter workflow."}
          </p>
        </div>
        <div className="rounded-2xl border border-subtle bg-app px-4 py-3">
          <dt className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Active Manuscript</dt>
          <dd className="mt-2 text-sm font-medium text-strong">
            {active_manuscript ? active_manuscript.title : "Not selected"}
          </dd>
          <p className="mt-1 text-xs text-muted">
            {active_manuscript ? active_manuscript.manuscript_type : "Assertion-backed writing begins here."}
          </p>
        </div>
        <div className="rounded-2xl border border-subtle bg-app px-4 py-3">
          <dt className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Review Summary</dt>
          <dd className="mt-2 text-sm font-medium text-strong" data-testid="project-header-review-summary">
            {reviewSummaryLabel}
          </dd>
          <p className="mt-1 text-xs text-muted" data-testid="project-header-review-scope">
            {reviewSummaryNote}
          </p>
        </div>
      </dl>
    </header>
  );
}

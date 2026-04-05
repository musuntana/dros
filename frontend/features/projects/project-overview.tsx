import type { ReactNode } from "react";

import type { ProjectDetailResponse, ProjectMemberRead } from "@/lib/api/generated/control-plane";

import { LineageFocusGraph } from "@/components/lineage/lineage-focus-graph";
import { BlockingSummary } from "@/components/status/blocking-summary";
import { StatusBadge } from "@/components/status/status-badge";
import { formatDateTime } from "@/lib/format/date";

function reviewSummaryLines(summary: Record<string, number>): string[] {
  const entries = Object.entries(summary);
  if (entries.length === 0) {
    return ["No review state is recorded yet."];
  }

  return entries.map(([state, count]) => `${state}: ${count}`);
}

export function ProjectOverview({
  detail,
  members,
}: {
  detail: ProjectDetailResponse;
  members: ProjectMemberRead[];
}) {
  const activeWorkflows = detail.active_workflows ?? [];
  const reviewSummary = detail.review_summary ?? {};

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          eyebrow="Active Workflows"
          value={activeWorkflows.length.toString()}
          note={
            activeWorkflows[0]
              ? `Current step: ${activeWorkflows[0].current_step ?? "queued"}`
              : "No workflow in flight"
          }
        />
        <MetricCard
          eyebrow="Latest Snapshot"
          value={detail.latest_snapshot ? `#${detail.latest_snapshot.snapshot_no}` : "None"}
          note={detail.latest_snapshot ? formatDateTime(detail.latest_snapshot.created_at) : "Dataset intake pending"}
        />
        <MetricCard
          eyebrow="Active Manuscript"
          value={detail.active_manuscript?.title ?? "None"}
          note={detail.active_manuscript?.state ?? "Writing has not started"}
        />
        <MetricCard
          eyebrow="Members"
          value={members.length.toString()}
          note={members.length > 0 ? members.map((member) => member.role).join(" · ") : "No membership recorded"}
        />
      </section>

      <LineageFocusGraph
        items={[
          { label: "Project", detail: detail.project.name },
          { label: "Snapshot", detail: detail.latest_snapshot ? `#${detail.latest_snapshot.snapshot_no}` : "pending" },
          { label: "Workflow", detail: activeWorkflows[0]?.state ?? "pending" },
          { label: "Artifact", detail: "assertion-backed only" },
          { label: "Review", detail: Object.keys(reviewSummary).length > 0 ? "tracked" : "pending" },
        ]}
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Overview</p>
          <div className="mt-4 space-y-4">
            <InfoRow
              label="Project status"
              value={<StatusBadge label={detail.project.status} />}
              note="Project scope is the immutable front-end workspace boundary."
            />
            <InfoRow
              label="Latest snapshot gate"
              value={
                detail.latest_snapshot ? (
                  <StatusBadge label={detail.latest_snapshot.deid_status} />
                ) : (
                  <span className="text-sm text-muted">No snapshot</span>
                )
              }
              note={
                detail.latest_snapshot
                  ? `PHI scan: ${detail.latest_snapshot.phi_scan_status}`
                  : "Dataset intake has not produced a snapshot yet."
              }
            />
            <InfoRow
              label="Review summary"
              value={<span className="text-sm text-strong">{reviewSummaryLines(reviewSummary).join(" · ")}</span>}
              note="Review and verify stay explicit before export."
            />
          </div>
        </div>

        <BlockingSummary
          blocked={!detail.latest_snapshot}
          reasons={
            detail.latest_snapshot
              ? []
              : ["No dataset_snapshot exists. Workflow and analysis cannot start until a snapshot is created."]
          }
          title="Workspace readiness"
        />
      </section>
    </div>
  );
}

function MetricCard({
  eyebrow,
  value,
  note,
}: {
  eyebrow: string;
  value: string;
  note: string;
}) {
  return (
    <article className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{eyebrow}</p>
      <p className="mt-4 font-serif text-3xl text-strong">{value}</p>
      <p className="mt-3 text-sm leading-7 text-muted">{note}</p>
    </article>
  );
}

function InfoRow({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note: string;
}) {
  return (
    <div className="rounded-2xl border border-subtle bg-app px-4 py-4">
      <div className="flex items-center justify-between gap-4">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</p>
        <div>{value}</div>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">{note}</p>
    </div>
  );
}

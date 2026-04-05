import Link from "next/link";

import type { AnalysisRunRead, WorkflowInstanceRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { EntityTable, TableStatusCell } from "@/components/tables/entity-table";
import { StatusBadge } from "@/components/status/status-badge";

export function WorkflowList({
  projectId,
  workflows,
}: {
  projectId: string;
  workflows: WorkflowInstanceRead[];
}) {
  return (
    <EntityTable
      columns={[
        {
          key: "workflow_type",
          label: "Workflow",
          render: (workflow) => workflow.workflow_type,
        },
        {
          key: "state",
          label: "State",
          render: (workflow) => <TableStatusCell value={workflow.state} />,
        },
        {
          key: "current_step",
          label: "Current Step",
          render: (workflow) => workflow.current_step ?? "pending",
        },
        {
          key: "runtime_backend",
          label: "Backend",
          render: (workflow) => workflow.runtime_backend,
        },
        {
          key: "started_at",
          label: "Started",
          render: (workflow) => formatDateTime(workflow.started_at),
        },
      ]}
      emptyMessage="No workflow instance exists yet. Create a plan-backed workflow or start an explicit deterministic workflow."
      getHref={(workflow) => `/projects/${projectId}/workflows/${workflow.id}`}
      rows={workflows}
    />
  );
}

export function AnalysisRunIndex({
  projectId,
  runs,
}: {
  projectId: string;
  runs: AnalysisRunRead[];
}) {
  if (runs.length === 0) {
    return (
      <div className="rounded-card border border-subtle bg-surface p-5 text-sm text-muted shadow-soft">
        No analysis run has been requested yet.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {runs.map((run) => (
        <article key={run.id} className="rounded-card border border-subtle bg-surface p-4 shadow-soft">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Analysis Run</p>
              <Link
                className="mt-2 block text-lg font-semibold text-primary hover:text-primary/80"
                href={`/projects/${projectId}/analysis-runs/${run.id}`}
              >
                {run.id}
              </Link>
              <p className="mt-2 text-sm text-muted">
                Template {run.template_id} on snapshot {run.snapshot_id.slice(0, 8)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusBadge label={run.state} />
              {run.workflow_instance_id ? <StatusBadge label="workflow-bound" /> : null}
            </div>
          </div>
          <dl className="mt-4 grid gap-3 md:grid-cols-3">
            <InfoCell label="Requested" value={formatDateTime(run.created_at)} />
            <InfoCell label="Seed" value={run.random_seed.toString()} />
            <InfoCell label="Repro" value={run.repro_fingerprint.slice(0, 12)} mono />
          </dl>
        </article>
      ))}
    </div>
  );
}

function InfoCell({
  label,
  mono = false,
  value,
}: {
  label: string;
  mono?: boolean;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-subtle bg-app px-4 py-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</p>
      <p className={`mt-2 text-sm text-strong ${mono ? "font-mono break-all" : ""}`}>{value}</p>
    </div>
  );
}

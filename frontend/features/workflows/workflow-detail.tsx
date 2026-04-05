import Link from "next/link";

import type {
  AnalysisRunRead,
  AnalysisTemplateRead,
  GateEvaluationRead,
  WorkflowTaskRead,
} from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { BlockingSummary } from "@/components/status/blocking-summary";
import { StatusBadge } from "@/components/status/status-badge";
import { AnalysisRunRequestPanel, WorkflowControlPanel } from "@/features/workflows/panels";
import type { WorkflowDetailViewModel } from "@/features/workflows/server";
import type { WorkflowSnapshotOption } from "@/features/workflows/types";

export function WorkflowDetail({
  detail,
  projectId,
  relatedRuns,
  snapshots,
  templates,
}: {
  detail: WorkflowDetailViewModel;
  projectId: string;
  relatedRuns: AnalysisRunRead[];
  snapshots: WorkflowSnapshotOption[];
  templates: AnalysisTemplateRead[];
}) {
  const latestTaskId = detail.tasks.at(-1)?.id;
  const blockingGateCount = detail.gateEvaluations.filter((gate) => gate.status !== "passed").length;

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Workflow Instance</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{detail.workflow.workflow_type}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
              Workflow pages stay deterministic: state transition, task trail, gate trail, and any downstream analysis
              run all remain explicit and project-scoped.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={detail.workflow.state} />
            <StatusBadge label={detail.workflow.runtime_backend} />
            {detail.workflow.parent_workflow_id ? <StatusBadge label="child-workflow" /> : null}
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Workflow ID"
            note={detail.workflow.id.slice(0, 8)}
            value={formatDateTime(detail.workflow.started_at)}
          />
          <MetricCard
            label="Current Step"
            note={detail.workflow.current_step ?? "pending"}
            value={detail.tasks.length > 0 ? `${detail.tasks.length} task(s)` : "No task trail"}
          />
          <MetricCard
            label="Gate Trail"
            note={detail.gateEvaluations.length.toString()}
            value={blockingGateCount > 0 ? `${blockingGateCount} gate(s) pending attention` : "All gates passed"}
          />
          <MetricCard
            label="Related Runs"
            note={relatedRuns.length.toString()}
            value={relatedRuns[0] ? relatedRuns[0].template_id : "No analysis run"}
          />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Task Trail</p>
              <h2 className="mt-2 font-serif text-2xl text-strong">Workflow tasks</h2>
            </div>
            <Link
              className="rounded-pill border border-subtle bg-app px-4 py-2 text-sm font-semibold text-strong"
              href={`/projects/${projectId}/audit`}
            >
              Audit trail
            </Link>
          </div>
          <div className="mt-5 space-y-4">
            {detail.tasks.length > 0 ? (
              detail.tasks.map((task) => <TaskCard key={task.id} task={task} />)
            ) : (
              <p className="text-sm text-muted">No task trail is available for this workflow.</p>
            )}
          </div>
        </div>

        <BlockingSummary
          blocked={blockingGateCount > 0}
          reasons={
            blockingGateCount > 0
              ? detail.gateEvaluations
                  .filter((gate) => gate.status !== "passed")
                  .map((gate) => `${gate.gate_name}: ${gate.status}`)
              : ["No blocking gate is currently attached to this workflow."]
          }
          title="Gate posture"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Gate Trail</p>
              <h2 className="mt-2 font-serif text-2xl text-strong">Evidence Control Plane results</h2>
            </div>
            <Link
              className="rounded-pill border border-subtle bg-app px-4 py-2 text-sm font-semibold text-strong"
              href={`/projects/${projectId}/reviews`}
            >
              Go to reviews
            </Link>
          </div>
          <div className="mt-5 space-y-4">
            {detail.gateEvaluations.length > 0 ? (
              detail.gateEvaluations.map((gate) => <GateCard key={`${gate.gate_name}-${gate.target_id}`} gate={gate} />)
            ) : (
              <p className="text-sm text-muted">No gate evaluation has been recorded for this workflow yet.</p>
            )}
          </div>
        </div>

        <WorkflowControlPanel latestTaskId={latestTaskId} projectId={projectId} workflow={detail.workflow} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Related Runs</p>
              <h2 className="mt-2 font-serif text-2xl text-strong">Workflow-bound analysis runs</h2>
            </div>
            <Link
              className="rounded-pill border border-subtle bg-app px-4 py-2 text-sm font-semibold text-strong"
              href={`/projects/${projectId}/artifacts`}
            >
              Browse artifacts
            </Link>
          </div>
          <div className="mt-5 space-y-4">
            {relatedRuns.length > 0 ? (
              relatedRuns.map((run) => (
                <article key={run.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Analysis Run</p>
                      <Link
                        className="mt-2 block text-sm font-semibold text-primary hover:text-primary/80"
                        href={`/projects/${projectId}/analysis-runs/${run.id}`}
                      >
                        {run.id}
                      </Link>
                    </div>
                    <StatusBadge label={run.state} />
                  </div>
                  <p className="mt-3 text-sm text-muted">
                    Template {run.template_id} on snapshot {run.snapshot_id.slice(0, 8)}
                  </p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No analysis run is currently attached to this workflow.</p>
            )}
          </div>
        </div>

        <AnalysisRunRequestPanel
          projectId={projectId}
          snapshotOptions={snapshots}
          templateOptions={templates}
          workflowId={detail.workflow.id}
        />
      </section>
    </div>
  );
}

function MetricCard({
  label,
  note,
  value,
}: {
  label: string;
  note: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-subtle bg-app px-4 py-4">
      <dt className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</dt>
      <dd className="mt-2 text-sm font-medium text-strong">{note}</dd>
      <p className="mt-1 text-xs text-muted">{value}</p>
    </div>
  );
}

function TaskCard({ task }: { task: WorkflowTaskRead }) {
  return (
    <article className="rounded-2xl border border-subtle bg-app px-4 py-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{task.task_key}</p>
          <p className="mt-2 text-sm font-medium text-strong">{task.task_type}</p>
          <p className="mt-2 text-xs text-muted">{formatDateTime(task.created_at)}</p>
        </div>
        <StatusBadge label={task.state} />
      </div>
      <dl className="mt-4 grid gap-3 md:grid-cols-2">
        <InfoRow label="Input" value={JSON.stringify(task.input_payload_json)} />
        <InfoRow label="Output" value={JSON.stringify(task.output_payload_json)} />
      </dl>
    </article>
  );
}

function GateCard({ gate }: { gate: GateEvaluationRead }) {
  return (
    <article className="rounded-2xl border border-subtle bg-app px-4 py-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{gate.gate_name}</p>
          <p className="mt-2 text-sm font-medium text-strong">
            {gate.target_kind} · {gate.target_id.slice(0, 8)}
          </p>
          <p className="mt-2 text-xs text-muted">{formatDateTime(gate.evaluated_at)}</p>
        </div>
        <StatusBadge label={gate.status} />
      </div>
      <InfoRow label="Details" value={JSON.stringify(gate.details_json ?? {})} />
    </article>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-subtle bg-white/70 px-3 py-3">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</p>
      <p className="mt-2 break-all font-mono text-xs text-strong">{value}</p>
    </div>
  );
}

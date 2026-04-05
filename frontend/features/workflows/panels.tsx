"use client";

import { useActionState } from "react";

import type {
  AnalysisTemplateRead,
  WorkflowInstanceRead,
} from "@/lib/api/generated/control-plane";
import { cn } from "@/lib/utils";

import {
  advanceWorkflowAction,
  cancelWorkflowAction,
  createAnalysisPlanAction,
  createAnalysisRunAction,
  createWorkflowAction,
} from "@/features/workflows/actions";
import type { WorkflowSnapshotOption } from "@/features/workflows/types";

const initialWorkflowActionState = {
  message: null,
  status: "idle" as const,
};

function ActionMessage({
  className,
  message,
}: {
  className?: string;
  message: string | null;
}) {
  if (!message) {
    return null;
  }

  return <p className={cn("mt-3 text-sm text-danger", className)}>{message}</p>;
}

export function AnalysisPlanPanel({
  projectId,
  snapshotOptions,
}: {
  projectId: string;
  snapshotOptions: WorkflowSnapshotOption[];
}) {
  const [state, action, pending] = useActionState(
    createAnalysisPlanAction.bind(null, projectId),
    initialWorkflowActionState,
  );

  return (
    <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Planning</p>
      <h2 className="mt-3 font-serif text-2xl text-strong">Create an analysis plan</h2>
      <p className="mt-3 text-sm leading-7 text-muted">
        Planning is a one-shot workflow record. The plan result is not stored as a separate object, so this form
        immediately creates a workflow instance and returns the selected template plus parameter draft.
      </p>
      <div className="mt-5 grid gap-4">
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Study Goal</span>
          <textarea
            className="min-h-28 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="Evaluate overall survival stratification with a template-backed Cox workflow."
            name="study_goal"
            required
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Dataset IDs</span>
          <textarea
            className="min-h-24 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            defaultValue={snapshotOptions.map((snapshot) => snapshot.datasetId).join("\n")}
            name="dataset_ids"
            placeholder="One dataset_id per line"
            required
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Candidate Templates</span>
          <textarea
            className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            defaultValue="survival.cox.v1"
            name="candidate_templates"
            placeholder="Optional template ids"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Assumptions</span>
          <textarea
            className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="os_time and os_event are already mapped."
            name="assumptions"
            placeholder="Optional assumptions"
          />
        </label>
      </div>
      <button
        className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending}
        type="submit"
      >
        {pending ? "Planning..." : "Create analysis plan"}
      </button>
      <ActionMessage message={state.message} />
    </form>
  );
}

export function WorkflowCreationPanel({ projectId }: { projectId: string }) {
  const [state, action, pending] = useActionState(
    createWorkflowAction.bind(null, projectId),
    initialWorkflowActionState,
  );

  return (
    <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Workflow</p>
      <h2 className="mt-3 font-serif text-2xl text-strong">Start a project-scoped workflow</h2>
      <p className="mt-3 text-sm leading-7 text-muted">
        Use this for explicit state-machine work that does not need a planning step first.
      </p>
      <div className="mt-5 grid gap-4">
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Workflow Type</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="manuscript_verification"
            name="workflow_type"
            required
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Runtime Backend</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="queue_workers"
            name="runtime_backend"
          >
            <option value="queue_workers">queue_workers</option>
            <option value="temporal">temporal</option>
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Started By</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            name="started_by"
            placeholder="Optional actor id override"
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Parent Workflow ID</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            name="parent_workflow_id"
            placeholder="Optional workflow_instance id"
            type="text"
          />
        </label>
      </div>
      <button
        className="mt-5 rounded-pill bg-secondary px-5 py-3 text-sm font-semibold text-white transition hover:bg-secondary/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending}
        type="submit"
      >
        {pending ? "Starting..." : "Create workflow"}
      </button>
      <ActionMessage message={state.message} />
    </form>
  );
}

export function AnalysisRunRequestPanel({
  projectId,
  snapshotOptions,
  templateOptions,
  workflowId,
}: {
  projectId: string;
  snapshotOptions: WorkflowSnapshotOption[];
  templateOptions: AnalysisTemplateRead[];
  workflowId?: string;
}) {
  const [state, action, pending] = useActionState(
    createAnalysisRunAction.bind(null, projectId, workflowId ?? null),
    initialWorkflowActionState,
  );

  return (
    <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Analysis Run</p>
      <h2 className="mt-3 font-serif text-2xl text-strong">Request a template-backed run</h2>
      <p className="mt-3 text-sm leading-7 text-muted">
        Runs stay bound to `dataset_snapshot` and approved templates. If you leave workflow binding blank here, the run
        is still project-scoped but not attached to a specific workflow instance.
      </p>
      <div className="mt-5 grid gap-4">
        {!workflowId ? (
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Workflow Instance</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
              name="workflow_instance_id"
              placeholder="Optional workflow_instance id"
              type="text"
            />
          </label>
        ) : null}
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Snapshot</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue={snapshotOptions[0]?.snapshotId ?? ""}
            name="snapshot_id"
            required
          >
            {snapshotOptions.length > 0 ? null : <option value="">No current snapshot</option>}
            {snapshotOptions.map((snapshot) => (
              <option key={snapshot.snapshotId} value={snapshot.snapshotId}>
                {snapshot.datasetName} · #{snapshot.snapshotNo} · {snapshot.deidStatus}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Template</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue={templateOptions[0]?.id ?? ""}
            name="template_id"
            required
          >
            {templateOptions.map((template) => (
              <option key={template.id} value={template.id}>
                {template.code} · v{template.version}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Params JSON</span>
          <textarea
            className="min-h-28 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue={'{"time_column":"os_time","event_column":"os_event","group_column":"risk_group"}'}
            name="params_json"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Random Seed</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="42"
            min="0"
            name="random_seed"
            type="number"
          />
        </label>
      </div>
      <button
        className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending || snapshotOptions.length === 0 || templateOptions.length === 0}
        type="submit"
      >
        {pending ? "Requesting..." : "Create analysis run"}
      </button>
      <ActionMessage message={state.message} />
    </form>
  );
}

export function WorkflowControlPanel({
  latestTaskId,
  projectId,
  workflow,
}: {
  latestTaskId?: string;
  projectId: string;
  workflow: WorkflowInstanceRead;
}) {
  const [advanceState, advanceAction, advancePending] = useActionState(
    advanceWorkflowAction.bind(null, projectId, workflow.id),
    initialWorkflowActionState,
  );
  const [cancelState, cancelAction, cancelPending] = useActionState(
    cancelWorkflowAction.bind(null, projectId, workflow.id),
    initialWorkflowActionState,
  );

  return (
    <div className="space-y-6">
      <form action={advanceAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">State Machine</p>
        <h3 className="mt-3 font-serif text-2xl text-strong">Advance workflow</h3>
        <p className="mt-3 text-sm leading-7 text-muted">
          Only the Workflow Service changes the persistent state. This form submits a deterministic action request to
          the control plane.
        </p>
        <input name="task_id" type="hidden" value={latestTaskId ?? ""} />
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Action</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue=""
              name="action"
            >
              <option value="">Default next state</option>
              <option value="needs_human">needs_human</option>
              <option value="block">block</option>
              <option value="verify">verify</option>
              <option value="approve">approve</option>
              <option value="export">export</option>
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Comments</span>
            <textarea
              className="min-h-24 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue=""
              name="comments"
              placeholder="Optional operator note"
            />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={advancePending}
          type="submit"
        >
          {advancePending ? "Advancing..." : "Submit action"}
        </button>
        <ActionMessage message={advanceState.message} />
      </form>

      <form action={cancelAction} className="rounded-card border border-danger/20 bg-danger/5 p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-danger">Cancel</p>
        <h3 className="mt-3 font-serif text-2xl text-strong">Stop this workflow</h3>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Reason</span>
            <textarea
              className="min-h-24 rounded-2xl border border-danger/20 bg-white/70 px-4 py-3 text-sm text-strong outline-none"
              defaultValue=""
              name="reason"
              placeholder="Why this workflow should be canceled"
              required
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Requested By</span>
            <input
              className="rounded-2xl border border-danger/20 bg-white/70 px-4 py-3 text-sm text-strong outline-none"
              name="requested_by"
              placeholder="Optional actor id"
              type="text"
            />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-danger px-5 py-3 text-sm font-semibold text-white transition hover:bg-danger/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={cancelPending}
          type="submit"
        >
          {cancelPending ? "Canceling..." : "Cancel workflow"}
        </button>
        <ActionMessage className="text-danger" message={cancelState.message} />
      </form>
    </div>
  );
}

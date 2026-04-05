"use client";

import { useActionState } from "react";

import { createSnapshotAction } from "@/features/datasets/actions";

const initialDatasetActionState = {
  message: null,
  status: "idle" as const,
};

export function SnapshotCreationPanel({
  datasetId,
  projectId,
}: {
  datasetId: string;
  projectId: string;
}) {
  const [state, action, pending] = useActionState(
    createSnapshotAction.bind(null, projectId, datasetId),
    initialDatasetActionState,
  );

  return (
    <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Snapshot</p>
      <h3 className="mt-3 font-serif text-2xl text-strong">Create a new dataset_snapshot</h3>
      <p className="mt-3 text-sm leading-7 text-muted">
        Snapshots remain immutable. If `input_hash_sha256` is left blank, the form derives a deterministic hash from
        `object_uri` for local development.
      </p>
      <div className="mt-5 grid gap-4">
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Object URI</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0"
            defaultValue="object://dataset/snapshot.csv"
            name="object_uri"
            placeholder="object://dataset/snapshot.csv"
            required
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Input Hash SHA256</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0"
            name="input_hash_sha256"
            placeholder="Optional in local flow"
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Row Count</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0"
            defaultValue="120"
            min="0"
            name="row_count"
            type="number"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Column Schema JSON</span>
          <textarea
            className="min-h-32 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0"
            defaultValue={'{"columns":["sample_id","os_time","os_event"]}'}
            name="column_schema_json"
          />
        </label>
      </div>
      <button
        className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending}
        type="submit"
      >
        {pending ? "Creating..." : "Create snapshot"}
      </button>
      {state.message ? <p className="mt-3 text-sm text-danger">{state.message}</p> : null}
    </form>
  );
}

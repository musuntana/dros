"use client";

import { useActionState } from "react";

import type { AnalysisRunRead } from "@/lib/api/generated/control-plane";

import { createArtifactAction } from "@/features/artifacts/actions";

const initialArtifactActionState = {
  message: null,
  status: "idle" as const,
};

export function ArtifactCreationPanel({
  analysisRuns,
  projectId,
}: {
  analysisRuns: AnalysisRunRead[];
  projectId: string;
}) {
  const [state, action, pending] = useActionState(
    createArtifactAction.bind(null, projectId),
    initialArtifactActionState,
  );

  return (
    <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Artifact</p>
      <h2 className="mt-3 font-serif text-2xl text-strong">Register a result artifact</h2>
      <p className="mt-3 text-sm leading-7 text-muted">
        Artifact creation stays explicit. If a run is selected, the control plane records the
        {" "}
        <code>analysis_run -&gt; emits -&gt; artifact</code>
        {" "}
        lineage edge for you.
      </p>
      <div className="mt-5 grid gap-4">
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Artifact Type</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="result_json"
            name="artifact_type"
          >
            <option value="result_json">result_json</option>
            <option value="table">table</option>
            <option value="figure">figure</option>
            <option value="manifest">manifest</option>
            <option value="log">log</option>
            <option value="docx">docx</option>
            <option value="pdf">pdf</option>
            <option value="zip">zip</option>
            <option value="evidence_attachment">evidence_attachment</option>
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Storage URI</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="object://analysis/result.json"
            name="storage_uri"
            required
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Analysis Run</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            defaultValue=""
            name="run_id"
          >
            <option value="">None</option>
            {analysisRuns.map((run) => (
              <option key={run.id} value={run.id}>
                {run.id.slice(0, 8)} · {run.template_id}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">MIME Type</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="application/json"
            name="mime_type"
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">SHA256</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            name="sha256"
            placeholder="Optional; derived from type + URI if blank"
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Size Bytes</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="128"
            min="0"
            name="size_bytes"
            type="number"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Metadata JSON</span>
          <textarea
            className="min-h-24 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue={'{"label":"cox_summary"}'}
            name="metadata_json"
          />
        </label>
      </div>
      <button
        className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending}
        type="submit"
      >
        {pending ? "Creating..." : "Create artifact"}
      </button>
      {state.message ? <p className="mt-3 text-sm text-danger">{state.message}</p> : null}
    </form>
  );
}

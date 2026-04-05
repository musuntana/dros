"use client";

import { useActionState } from "react";

import type { AnalysisRunRead, ArtifactRead } from "@/lib/api/generated/control-plane";

import { createAssertionAction } from "@/features/assertions/actions";

const initialAssertionActionState = {
  message: null,
  status: "idle" as const,
};

export function AssertionCreationPanel({
  analysisRuns,
  artifacts,
  projectId,
}: {
  analysisRuns: AnalysisRunRead[];
  artifacts: ArtifactRead[];
  projectId: string;
}) {
  const [state, action, pending] = useActionState(
    createAssertionAction.bind(null, projectId),
    initialAssertionActionState,
  );

  return (
    <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Assertion</p>
      <h2 className="mt-3 font-serif text-2xl text-strong">Extract a traceable claim</h2>
      <p className="mt-3 text-sm leading-7 text-muted">
        Assertions are the only writing input. Every numeric field and every claim must point back to an artifact or
        run source span.
      </p>
      <div className="mt-5 grid gap-4">
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Assertion Type</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="result"
            name="assertion_type"
          >
            <option value="background">background</option>
            <option value="method">method</option>
            <option value="result">result</option>
            <option value="limitation">limitation</option>
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Text Norm</span>
          <textarea
            className="min-h-28 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="cox regression showed the marker was associated with overall survival"
            name="text_norm"
            required
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Source Artifact</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            defaultValue=""
            name="source_artifact_id"
          >
            <option value="">None</option>
            {artifacts.map((artifact) => (
              <option key={artifact.id} value={artifact.id}>
                {artifact.id.slice(0, 8)} · {artifact.artifact_type}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Source Run</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            defaultValue=""
            name="source_run_id"
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
          <span className="text-sm font-medium text-strong">Numeric Payload JSON</span>
          <textarea
            className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue={'{"hr":0.65,"ci_low":0.48,"ci_high":0.89,"p_value":0.03}'}
            name="numeric_payload_json"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Source Span JSON</span>
          <textarea
            className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue={'{"artifact_key":"cox_summary","field":"overall_survival"}'}
            name="source_span_json"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Claim Hash</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            name="claim_hash"
            placeholder="Optional; derived from text_norm if blank"
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Supersedes Assertion</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            name="supersedes_assertion_id"
            placeholder="Optional assertion id"
            type="text"
          />
        </label>
      </div>
      <button
        className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending}
        type="submit"
      >
        {pending ? "Creating..." : "Create assertion"}
      </button>
      {state.message ? <p className="mt-3 text-sm text-danger">{state.message}</p> : null}
    </form>
  );
}

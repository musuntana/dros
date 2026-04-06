"use client";

import Link from "next/link";
import { useActionState } from "react";

import type { ArtifactRead, ExportJobRead, ManuscriptRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { createExportJobAction } from "@/features/exports/actions";

const initialExportActionState = {
  message: null,
  status: "idle" as const,
};

export function ExportsDashboard({
  exportArtifacts,
  exportJobs,
  manuscripts,
  projectId,
}: {
  exportArtifacts: ArtifactRead[];
  exportJobs: ExportJobRead[];
  manuscripts: ManuscriptRead[];
  projectId: string;
}) {
  const [state, action, pending] = useActionState(
    createExportJobAction.bind(null, projectId),
    initialExportActionState,
  );

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Exports</p>
        <h1 className="mt-3 font-serif text-4xl text-strong">Gate-bound manuscript export</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
          Export history now comes from project-scoped `export_job` records. Output artifacts remain visible here, while
          deeper event-chain inspection still belongs in the audit workspace.
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Export Job</p>
          <h2 className="mt-3 font-serif text-2xl text-strong">Request an export</h2>
          <div className="mt-5 grid gap-4">
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Manuscript</span>
              <select
                className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
                defaultValue={manuscripts[0]?.id ?? ""}
                name="manuscript_id"
              >
                {manuscripts.map((manuscript) => (
                  <option key={manuscript.id} value={manuscript.id}>
                    {manuscript.title} · {manuscript.state}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Format</span>
              <select
                className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
                defaultValue="docx"
                name="format"
              >
                <option value="docx">docx</option>
                <option value="pdf">pdf</option>
                <option value="zip">zip</option>
              </select>
            </label>
          </div>
          <button
            className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={pending || manuscripts.length === 0}
            type="submit"
          >
            {pending ? "Requesting..." : "Create export job"}
          </button>
          {state.message ? <p className="mt-3 text-sm text-danger">{state.message}</p> : null}
        </form>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Export Targets</p>
          <div className="mt-4 space-y-4">
            {manuscripts.length > 0 ? (
              manuscripts.map((manuscript) => (
                <article key={manuscript.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                    {manuscript.manuscript_type}
                  </p>
                  <p className="mt-2 text-sm font-medium text-strong">{manuscript.title}</p>
                  <p className="mt-2 text-xs text-muted">
                    state {manuscript.state} · version {manuscript.current_version_no}
                  </p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No manuscript is available for export.</p>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Export Jobs</p>
          <div className="mt-4 space-y-4">
            {exportJobs.length > 0 ? (
              exportJobs.map((job) => (
                <article key={job.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                        {job.format}
                      </p>
                      <Link
                        className="mt-2 block break-all text-sm font-medium text-primary"
                        href={`/projects/${projectId}/exports/${job.id}`}
                      >
                        {job.id}
                      </Link>
                      <p className="mt-2 text-xs text-muted">
                        requested {formatDateTime(job.requested_at)}
                        {job.completed_at ? ` · completed ${formatDateTime(job.completed_at)}` : ""}
                      </p>
                    </div>
                    <span className="rounded-pill border border-subtle bg-white/70 px-3 py-1 text-xs font-semibold text-strong">
                      {job.state}
                    </span>
                  </div>
                  <p className="mt-3 break-all text-xs text-muted">
                    manuscript {job.manuscript_id} · output {job.output_artifact_id ?? "none"}
                  </p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No export job has been created yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Output Artifacts</p>
          <div className="mt-4 space-y-4">
            {exportArtifacts.length > 0 ? (
              exportArtifacts.map((artifact) => (
                <article key={artifact.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{artifact.artifact_type}</p>
                  <Link
                    className="mt-2 block break-all text-sm font-medium text-primary"
                    href={`/projects/${projectId}/artifacts/${artifact.id}`}
                  >
                    {artifact.storage_uri}
                  </Link>
                  <p className="mt-2 text-xs text-muted">{formatDateTime(artifact.created_at)}</p>
                  <p className="mt-2 break-all font-mono text-xs text-strong">{artifact.id}</p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No export artifact has been created yet.</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

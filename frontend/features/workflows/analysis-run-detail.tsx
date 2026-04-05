import Link from "next/link";

import type { AnalysisRunRead, ArtifactRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";

export function AnalysisRunDetail({
  artifacts,
  projectId,
  run,
}: {
  artifacts: ArtifactRead[];
  projectId: string;
  run: AnalysisRunRead;
}) {
  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Analysis Run</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{run.template_id}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
              Run detail shows only template-backed execution metadata and emitted artifacts. Narrative results still
              have to route through assertions before writing.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={run.state} />
            {run.workflow_instance_id ? <StatusBadge label="workflow-bound" /> : <StatusBadge label="project-scoped" />}
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <InfoCard label="Run ID" note={run.id.slice(0, 8)} value={formatDateTime(run.created_at)} />
          <InfoCard label="Snapshot" note={run.snapshot_id.slice(0, 8)} value={run.param_hash.slice(0, 12)} />
          <InfoCard label="Seed" note={run.random_seed.toString()} value={run.container_image_digest} />
          <InfoCard label="Workflow" note={run.workflow_instance_id?.slice(0, 8) ?? "Unbound"} value={run.job_ref ?? "n/a"} />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Runtime</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <JsonCell label="Params JSON" value={run.params_json} />
            <JsonCell label="Runtime Manifest" value={run.runtime_manifest_json} />
            <JsonCell label="Input Manifest" value={run.input_artifact_manifest_json} />
            <JsonCell label="Execution State" value={{ exit_code: run.exit_code, started_at: run.started_at, finished_at: run.finished_at }} />
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Next Action</p>
          <h2 className="mt-3 font-serif text-2xl text-strong">Trace forward into artifacts</h2>
          <p className="mt-3 text-sm leading-7 text-muted">
            The run itself is not a writing source. Move forward into emitted artifacts, then assertions, then verified
            manuscript blocks.
          </p>
          <div className="mt-5 space-y-3">
            {run.workflow_instance_id ? (
              <Link
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                href={`/projects/${projectId}/workflows/${run.workflow_instance_id}`}
              >
                Open workflow instance
              </Link>
            ) : null}
            <Link
              className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
              href={`/projects/${projectId}/artifacts`}
            >
              Browse project artifacts
            </Link>
          </div>
        </div>
      </section>

      <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Emitted Artifacts</p>
            <h2 className="mt-2 font-serif text-2xl text-strong">Artifact outputs attached to this run</h2>
          </div>
          <Link
            className="rounded-pill border border-subtle bg-app px-4 py-2 text-sm font-semibold text-strong"
            href={`/projects/${projectId}/assertions`}
          >
            Go to assertions
          </Link>
        </div>
        <div className="mt-5 space-y-4">
          {artifacts.length > 0 ? (
            artifacts.map((artifact) => (
              <article key={artifact.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{artifact.artifact_type}</p>
                    <Link
                      className="mt-2 block text-sm font-semibold text-primary hover:text-primary/80"
                      href={`/projects/${projectId}/artifacts/${artifact.id}`}
                    >
                      {artifact.id}
                    </Link>
                    <p className="mt-2 text-xs text-muted">{artifact.storage_uri}</p>
                  </div>
                  <StatusBadge label={artifact.mime_type ?? "no-mime"} />
                </div>
              </article>
            ))
          ) : (
            <p className="text-sm text-muted">No artifact has been emitted for this run yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function InfoCard({
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
      <dd className="mt-2 break-all text-sm font-medium text-strong">{note}</dd>
      <p className="mt-1 break-all text-xs text-muted">{value}</p>
    </div>
  );
}

function JsonCell({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  return (
    <div className="rounded-2xl border border-subtle bg-app px-4 py-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</p>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs text-strong">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

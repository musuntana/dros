"use client";

import Link from "next/link";

import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function ExportJobDetailLive({
  exportJobId,
  projectId,
}: {
  exportJobId: string;
  projectId: string;
}) {
  const { projection } = useWorkspaceData();
  const exportJob = projection.exports.find((job) => job.id === exportJobId) ?? null;

  if (!exportJob) {
    return (
      <div className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="text-sm text-muted">
          Export job <code className="font-mono text-xs">{exportJobId.slice(0, 8)}</code> was not found in the workspace
          projection.
        </p>
      </div>
    );
  }

  const manuscript = projection.manuscripts.find((item) => item.id === exportJob.manuscript_id) ?? null;
  const outputArtifact = exportJob.output_artifact_id
    ? projection.artifacts.find((item) => item.id === exportJob.output_artifact_id) ?? null
    : null;

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Export Job</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{exportJob.format}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
              Export stays gate-bound to the manuscript chain. This object records delivery intent and, when successful,
              the produced output artifact.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={exportJob.state} />
            {outputArtifact ? <StatusBadge label="artifact-ready" /> : <StatusBadge label="no-output" />}
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <InfoCard label="Export ID" note={exportJob.id.slice(0, 8)} value={formatDateTime(exportJob.requested_at)} />
          <InfoCard label="Manuscript" note={exportJob.manuscript_id.slice(0, 8)} value={manuscript?.title ?? "Unknown manuscript"} />
          <InfoCard label="Requested By" note={exportJob.requested_by ?? "Unknown"} value={exportJob.state} />
          <InfoCard label="Output" note={exportJob.output_artifact_id?.slice(0, 8) ?? "None"} value={exportJob.completed_at ? formatDateTime(exportJob.completed_at) : "Not completed"} />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Delivery Chain</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <RelationCard
              description={manuscript ? `${manuscript.state} · version ${manuscript.current_version_no}` : "No manuscript found"}
              href={manuscript ? `/projects/${projectId}/manuscripts/${manuscript.id}` : null}
              label="Source Manuscript"
              value={manuscript?.title ?? exportJob.manuscript_id}
            />
            <RelationCard
              description={outputArtifact ? outputArtifact.artifact_type : "No output artifact yet"}
              href={outputArtifact ? `/projects/${projectId}/artifacts/${outputArtifact.id}` : null}
              label="Output Artifact"
              value={outputArtifact?.storage_uri ?? "Unassigned"}
            />
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Actions</p>
          <div className="mt-4 space-y-3">
            {manuscript ? (
              <Link
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                href={`/projects/${projectId}/manuscripts/${manuscript.id}`}
              >
                Open manuscript
              </Link>
            ) : null}
            {outputArtifact ? (
              <Link
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                href={`/projects/${projectId}/artifacts/${outputArtifact.id}`}
              >
                Open output artifact
              </Link>
            ) : null}
            <Link
              className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
              href={`/projects/${projectId}/exports`}
            >
              Back to export jobs
            </Link>
          </div>
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

function RelationCard({
  description,
  href,
  label,
  value,
}: {
  description: string;
  href: string | null;
  label: string;
  value: string;
}) {
  const content = (
    <>
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</p>
      <p className="mt-2 break-all text-sm font-medium text-strong">{value}</p>
      <p className="mt-2 text-xs text-muted">{description}</p>
    </>
  );

  if (!href) {
    return <div className="rounded-2xl border border-subtle bg-app px-4 py-4">{content}</div>;
  }

  return (
    <Link
      className="block rounded-2xl border border-subtle bg-app px-4 py-4 transition hover:border-primary/20 hover:bg-primary/5"
      href={href}
    >
      {content}
    </Link>
  );
}

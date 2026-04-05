import Link from "next/link";

import type {
  AnalysisRunRead,
  ArtifactDetailResponse,
  ArtifactRead,
  AssertionRead,
  LineageEdgeRead,
} from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";

export function ArtifactDetail({
  detail,
  downloadReady,
  emittingRun,
  projectId,
  relatedAssertions,
  relatedEdges,
  supersededBy,
}: {
  detail: ArtifactDetailResponse;
  downloadReady: boolean;
  emittingRun: AnalysisRunRead | null;
  projectId: string;
  relatedAssertions: AssertionRead[];
  relatedEdges: LineageEdgeRead[];
  supersededBy: ArtifactRead | null;
}) {
  const { artifact } = detail;

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Artifact</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{artifact.artifact_type}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
              Artifact detail is the last raw-results stop before assertion extraction. Writing surfaces must not quote
              this object directly.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={artifact.mime_type ?? "no-mime"} />
            {artifact.superseded_by ? <StatusBadge label="superseded" /> : <StatusBadge label="active" />}
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Artifact ID" note={artifact.id.slice(0, 8)} value={formatDateTime(artifact.created_at)} />
          <MetricCard label="Storage" note={artifact.storage_uri} value={artifact.sha256.slice(0, 12)} />
          <MetricCard label="Run" note={artifact.run_id?.slice(0, 8) ?? "Manual"} value={artifact.mime_type ?? "n/a"} />
          <MetricCard label="Superseded By" note={artifact.superseded_by?.slice(0, 8) ?? "None"} value={artifact.size_bytes?.toString() ?? "Unknown size"} />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Metadata</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <JsonCell label="Metadata JSON" value={artifact.metadata_json} />
            <JsonCell label="Lineage Summary" value={{ run_id: artifact.run_id, superseded_by: artifact.superseded_by }} />
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Trace</p>
          <div className="mt-4 space-y-3">
            {downloadReady ? (
              <a
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                data-testid="artifact-download-link"
                download
                href={`/api/projects/${projectId}/artifacts/${artifact.id}/download`}
              >
                Download artifact payload
              </a>
            ) : (
              <div className="rounded-2xl border border-dashed border-subtle bg-app px-4 py-3 text-sm text-muted">
                No downloadable payload is currently registered for this artifact.
              </div>
            )}
            {emittingRun ? (
              <Link
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                href={`/projects/${projectId}/analysis-runs/${emittingRun.id}`}
              >
                Open emitting analysis run
              </Link>
            ) : null}
            {supersededBy ? (
              <Link
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                href={`/projects/${projectId}/artifacts/${supersededBy.id}`}
              >
                Open replacement artifact
              </Link>
            ) : null}
            <Link
              className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
              href={`/projects/${projectId}/assertions`}
            >
              Go to assertions
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Derived Assertions</p>
          <div className="mt-4 space-y-4">
            {relatedAssertions.length > 0 ? (
              relatedAssertions.map((assertion) => (
                <article key={assertion.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                        {assertion.assertion_type}
                      </p>
                      <Link
                        className="mt-2 block text-sm font-semibold text-primary"
                        href={`/projects/${projectId}/assertions/${assertion.id}`}
                      >
                        {assertion.id}
                      </Link>
                    </div>
                    <StatusBadge label={assertion.state} />
                  </div>
                  <p className="mt-3 text-sm text-muted">{assertion.text_norm}</p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No assertion currently cites this artifact as its source artifact.</p>
            )}
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Lineage Edges</p>
          <div className="mt-4 space-y-4">
            {relatedEdges.length > 0 ? (
              relatedEdges.map((edge) => (
                <article key={edge.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{edge.edge_type}</p>
                  <p className="mt-2 text-sm text-strong">
                    {edge.from_kind}:{edge.from_id.slice(0, 8)} → {edge.to_kind}:{edge.to_id.slice(0, 8)}
                  </p>
                  <p className="mt-2 text-xs text-muted">{formatDateTime(edge.created_at)}</p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No lineage edge currently references this artifact.</p>
            )}
          </div>
        </div>
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

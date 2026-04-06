import Link from "next/link";

import type {
  AnalysisRunRead,
  ArtifactRead,
  AssertionDetailResponse,
  BlockAssertionLinkRead,
  EvidenceLinkRead,
} from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";

export function AssertionDetail({
  blockLinks,
  detail,
  evidenceLinks,
  projectId,
  sourceArtifact,
  sourceRun,
}: {
  blockLinks: BlockAssertionLinkRead[];
  detail: AssertionDetailResponse;
  evidenceLinks: EvidenceLinkRead[];
  projectId: string;
  sourceArtifact: ArtifactRead | null;
  sourceRun: AnalysisRunRead | null;
}) {
  const { assertion } = detail;

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Assertion</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{assertion.assertion_type}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">{assertion.text_norm}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={assertion.state} />
            {sourceArtifact ? <StatusBadge label="artifact-backed" /> : null}
            {sourceRun ? <StatusBadge label="run-backed" /> : null}
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Assertion ID" note={assertion.id.slice(0, 8)} value={formatDateTime(assertion.created_at)} />
          <MetricCard label="Claim Hash" note={assertion.claim_hash.slice(0, 12)} value={assertion.state} />
          <MetricCard label="Source Artifact" note={assertion.source_artifact_id?.slice(0, 8) ?? "None"} value={sourceArtifact?.artifact_type ?? "n/a"} />
          <MetricCard label="Source Run" note={assertion.source_run_id?.slice(0, 8) ?? "None"} value={sourceRun?.template_id ?? "n/a"} />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Payload</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <JsonCell label="Numeric Payload" value={assertion.numeric_payload_json} />
            <JsonCell label="Source Span" value={assertion.source_span_json} />
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Trace</p>
          <div className="mt-4 space-y-3">
            {sourceArtifact ? (
              <Link
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                href={`/projects/${projectId}/artifacts/${sourceArtifact.id}`}
              >
                Open source artifact
              </Link>
            ) : null}
            {sourceRun ? (
              <Link
                className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
                href={`/projects/${projectId}/analysis-runs/${sourceRun.id}`}
              >
                Open source run
              </Link>
            ) : null}
            <Link
              className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
              href={`/projects/${projectId}/evidence`}
            >
              Go to evidence links
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Evidence Links</p>
          <div className="mt-4 space-y-4">
            {evidenceLinks.length > 0 ? (
              evidenceLinks.map((link) => (
                <article key={link.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                        {link.relation_type}
                      </p>
                      <Link
                        className="mt-2 block break-all text-sm font-medium text-primary"
                        href={`/projects/${projectId}/evidence-links/${link.id}`}
                      >
                        {link.evidence_source_id}
                      </Link>
                    </div>
                    <StatusBadge label={link.verifier_status} />
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No evidence link is attached to this assertion yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Block Links</p>
          <div className="mt-4 space-y-4">
            {blockLinks.length > 0 ? (
              blockLinks.map((link) => (
                <article key={`${link.block_id}-${link.assertion_id}`} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{link.render_role}</p>
                  <p className="mt-2 break-all text-sm text-strong">{link.block_id}</p>
                  <p className="mt-2 text-xs text-muted">Display order {link.display_order}</p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No manuscript block currently consumes this assertion.</p>
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

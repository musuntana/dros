import Link from "next/link";

import type {
  AnalysisRunRead,
  ArtifactRead,
  EvidenceChunkRead,
  EvidenceLinkRead,
  EvidenceSourceRead,
  ManuscriptBlockRead,
  ManuscriptRead,
} from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";
import { verifyEvidenceLinkAction } from "@/features/evidence/actions";
import { buildEvidencePreview } from "@/features/evidence/evidence-preview";

export function EvidenceLinkDetail({
  assertionText,
  consumerBlocks,
  consumerManuscripts,
  evidenceLink,
  evidenceSource,
  projectId,
  sourceChunk,
  sourceArtifact,
  sourceRun,
}: {
  assertionText: string;
  consumerBlocks: ManuscriptBlockRead[];
  consumerManuscripts: ManuscriptRead[];
  evidenceLink: EvidenceLinkRead;
  evidenceSource: EvidenceSourceRead;
  projectId: string;
  sourceChunk: EvidenceChunkRead | null;
  sourceArtifact: ArtifactRead | null;
  sourceRun: AnalysisRunRead | null;
}) {
  const returnPath = `/projects/${projectId}/evidence-links/${evidenceLink.id}`;
  const preview = buildEvidencePreview(evidenceLink, evidenceSource, sourceChunk);

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Evidence Link</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{evidenceLink.relation_type}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
              This object binds one assertion to one evidence source. Writing still has to route through the assertion;
              the link is traceable grounding, not manuscript truth by itself.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={evidenceLink.verifier_status} />
            <StatusBadge label={evidenceSource.license_class} />
            {evidenceSource.oa_subset_flag ? <StatusBadge label="oa_subset" /> : null}
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Link ID" note={evidenceLink.id.slice(0, 8)} value={formatDateTime(evidenceLink.created_at)} />
          <MetricCard label="Assertion" note={evidenceLink.assertion_id.slice(0, 8)} value={assertionText} />
          <MetricCard label="Source" note={evidenceSource.id.slice(0, 8)} value={evidenceSource.title} />
          <MetricCard
            label="Confidence"
            note={evidenceLink.confidence?.toFixed(2) ?? "N/A"}
            value={evidenceLink.source_chunk_id?.slice(0, 8) ?? "full source"}
          />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Source</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-subtle bg-app px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Inline Preview</p>
                <div className="flex flex-wrap items-center gap-2">
                  {preview.sourceLabel ? (
                    <span className="rounded-pill border border-subtle bg-surface px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-strong">
                      {preview.sourceLabel}
                    </span>
                  ) : null}
                  <span className="rounded-pill border border-subtle bg-surface px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-strong">
                    {preview.spanLabel}
                  </span>
                </div>
              </div>
              {preview.displayText ? (
                <blockquote
                  className="mt-4 rounded-2xl border border-subtle bg-surface px-4 py-4 text-sm leading-7 text-strong"
                  data-testid="evidence-link-preview"
                >
                  {preview.segments.map((segment, index) =>
                    segment.emphasized ? (
                      <mark
                        key={`preview:${index}`}
                        className="rounded-sm bg-primary/15 px-1 py-0.5 text-primary"
                        data-testid="evidence-link-highlight"
                      >
                        {segment.text}
                      </mark>
                    ) : (
                      <span key={`preview:${index}`}>{segment.text}</span>
                    ),
                  )}
                </blockquote>
              ) : (
                <p className="mt-4 text-sm leading-7 text-muted">
                  No inline source preview is available yet. This evidence link still records traceable span coordinates,
                  but the source metadata does not currently expose preview text.
                </p>
              )}
            </div>
            <JsonCell
              label="Source Metadata"
              value={{
                doi_norm: evidenceSource.doi_norm,
                external_id_norm: evidenceSource.external_id_norm,
                journal: evidenceSource.journal,
                metadata_json: evidenceSource.metadata_json,
                oa_subset_flag: evidenceSource.oa_subset_flag,
                pmcid: evidenceSource.pmcid,
                pmid: evidenceSource.pmid,
                pub_year: evidenceSource.pub_year,
                source_type: evidenceSource.source_type,
              }}
            />
            <JsonCell
              label="Link Span"
              value={{
                excerpt_hash: evidenceLink.excerpt_hash,
                resolved_chunk_id: sourceChunk?.id ?? null,
                source_chunk_id: evidenceLink.source_chunk_id,
                source_span_end: evidenceLink.source_span_end,
                source_span_start: evidenceLink.source_span_start,
              }}
            />
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Trace</p>
          <div className="mt-4 space-y-3">
            <form action={verifyEvidenceLinkAction.bind(null, projectId, evidenceLink.id, returnPath)}>
              <button
                className="block w-full rounded-2xl border border-subtle bg-app px-4 py-3 text-left text-sm font-semibold text-primary"
                data-testid="evidence-link-verify-submit"
                type="submit"
              >
                Verify evidence link
              </button>
            </form>
            <Link
              className="block rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-semibold text-primary"
              href={`/projects/${projectId}/assertions/${evidenceLink.assertion_id}`}
            >
              Open assertion
            </Link>
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
              Back to evidence registry
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Evidence Source</p>
          <article className="mt-4 rounded-2xl border border-subtle bg-app px-4 py-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{evidenceSource.source_type}</p>
            <p className="mt-2 text-sm font-medium text-strong" data-testid="evidence-link-source-title">{evidenceSource.title}</p>
            <p className="mt-2 text-xs text-muted">
              {evidenceSource.pmid ?? evidenceSource.pmcid ?? evidenceSource.doi_norm ?? evidenceSource.external_id_norm}
            </p>
            <p className="mt-2 text-xs text-muted">
              {evidenceSource.journal ?? "Unknown journal"}
              {evidenceSource.pub_year ? ` · ${evidenceSource.pub_year}` : ""}
            </p>
          </article>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Evidence Chunk</p>
          <div className="mt-4 space-y-4">
            {sourceChunk ? (
              <article className="rounded-2xl border border-subtle bg-app px-4 py-4" data-testid="evidence-link-source-chunk">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                  {sourceChunk.section_label ?? `chunk ${sourceChunk.chunk_no}`}
                </p>
                <p className="mt-2 text-sm font-medium text-strong">
                  chars {sourceChunk.char_start}-{sourceChunk.char_end} · {sourceChunk.token_count} token(s)
                </p>
                <p className="mt-2 text-xs leading-6 text-muted">
                  Chunk {sourceChunk.chunk_no} · {sourceChunk.id.slice(0, 8)}
                </p>
              </article>
            ) : (
              <p className="text-sm text-muted">
                This evidence link does not yet resolve to a persisted evidence chunk. Preview falls back to source metadata.
              </p>
            )}
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Consumers</p>
          <div className="mt-4 space-y-4">
            {consumerManuscripts.length > 0 ? (
              consumerManuscripts.map((manuscript) => {
                const blockCount = consumerBlocks.filter((block) => block.manuscript_id === manuscript.id).length;
                return (
                  <article key={manuscript.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                    <Link
                      className="text-sm font-medium text-primary"
                      href={`/projects/${projectId}/manuscripts/${manuscript.id}`}
                    >
                      {manuscript.title}
                    </Link>
                    <p className="mt-2 text-xs text-muted">
                      {manuscript.state} · version {manuscript.current_version_no} · {blockCount} block(s)
                    </p>
                  </article>
                );
              })
            ) : (
              <p className="text-sm text-muted">No manuscript block currently consumes the linked assertion.</p>
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

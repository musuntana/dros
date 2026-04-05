import Link from "next/link";

import type { AssertionRead, ManuscriptBlockRead, ManuscriptRead, RenderManuscriptResponse } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";
import { ManuscriptBlockPanel } from "@/features/manuscripts/manuscript-panels";

export function ManuscriptDetail({
  blocks,
  manuscript,
  preview,
  projectId,
  verifiedAssertions,
}: {
  blocks: ManuscriptBlockRead[];
  manuscript: ManuscriptRead;
  preview: RenderManuscriptResponse;
  projectId: string;
  verifiedAssertions: AssertionRead[];
}) {
  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Manuscript</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{manuscript.title}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
              Manuscript blocks remain assertion-backed. Render preview is derived from current verified assertions and
              block state, not from raw run outputs.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={manuscript.state} />
            <StatusBadge label={manuscript.manuscript_type} />
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Current Version" note={`v${manuscript.current_version_no}`} value={formatDateTime(manuscript.updated_at ?? manuscript.created_at)} />
          <MetricCard label="Created By" note={manuscript.created_by ?? "system"} value={formatDateTime(manuscript.created_at)} />
          <MetricCard label="Target Journal" note={manuscript.target_journal ?? "None"} value={manuscript.id.slice(0, 8)} />
          <MetricCard label="Verified Assertions" note={verifiedAssertions.length.toString()} value={`${blocks.length} block(s)`} />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Current Blocks</p>
              <h2 className="mt-2 font-serif text-2xl text-strong">Block list for the active version</h2>
            </div>
            <Link
              className="rounded-pill border border-subtle bg-app px-4 py-2 text-sm font-semibold text-strong"
              href={`/projects/${projectId}/reviews`}
            >
              Verify & review
            </Link>
          </div>
          <div className="mt-5 space-y-4">
            {blocks.length > 0 ? (
              blocks.map((block) => (
                <article key={block.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                        {block.section_key} · {block.block_type}
                      </p>
                      <p className="mt-2 text-sm font-medium text-strong">{block.content_md}</p>
                    </div>
                    <StatusBadge label={block.status} />
                  </div>
                  <p className="mt-3 text-xs text-muted">
                    order {block.block_order} · assertions {block.assertion_ids?.join(", ") || "none"}
                  </p>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No block exists yet for the current manuscript version.</p>
            )}
          </div>
        </div>

        <ManuscriptBlockPanel manuscript={manuscript} projectId={projectId} verifiedAssertions={verifiedAssertions} />
      </section>

      <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Render Preview</p>
        <h2 className="mt-2 font-serif text-2xl text-strong">Current rendered manuscript blocks</h2>
        {preview.warnings?.length ? (
          <div className="mt-4 rounded-2xl border border-warning/30 bg-warning/5 px-4 py-4 text-sm text-warning">
            {preview.warnings.join(" · ")}
          </div>
        ) : null}
        <div className="mt-5 space-y-4">
          {preview.blocks.length > 0 ? (
            preview.blocks.map((block) => (
              <article key={block.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                  {block.section_key} · render preview
                </p>
                <p className="mt-3 text-sm leading-7 text-strong">{block.content_md}</p>
              </article>
            ))
          ) : (
            <p className="text-sm text-muted">Render preview has no content yet.</p>
          )}
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

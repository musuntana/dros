import { formatDateTime } from "@/lib/format/date";

import { StatusBadge } from "@/components/status/status-badge";
import { verifyEvidenceLinkAction } from "@/features/evidence/actions";
import { EvidenceControlPanels } from "@/features/evidence/evidence-panels";
import type { EvidenceLinkRecord } from "@/features/evidence/types";
import type { AssertionRead, EvidenceSourceRead } from "@/lib/api/generated/control-plane";

export function EvidenceDashboard({
  assertions,
  linkRecords,
  projectId,
  sources,
}: {
  assertions: AssertionRead[];
  linkRecords: EvidenceLinkRecord[];
  projectId: string;
  sources: EvidenceSourceRead[];
}) {
  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Evidence</p>
        <h1 className="mt-3 font-serif text-4xl text-strong">Sources, search, and assertion grounding</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
          Search and resolve stay source-centric. Project-level evidence links are aggregated from real assertion detail
          responses because the control plane does not expose a dedicated link list route yet.
        </p>
      </section>

      <EvidenceControlPanels assertions={assertions} projectId={projectId} sources={sources} />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Evidence Sources</p>
          <div className="mt-4 space-y-4">
            {sources.length > 0 ? (
              sources.map((source) => (
                <article key={source.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                        {source.source_type}
                      </p>
                      <p className="mt-2 text-sm font-medium text-strong">{source.title}</p>
                      <p className="mt-2 text-xs text-muted">
                        {source.pmid ?? source.pmcid ?? source.doi_norm ?? source.external_id_norm}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge label={source.license_class} />
                      {source.oa_subset_flag ? <StatusBadge label="oa_subset" /> : null}
                    </div>
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No evidence source is attached to this project yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Evidence Links</p>
          <div className="mt-4 space-y-4">
            {linkRecords.length > 0 ? (
              linkRecords.map((record) => (
                <article key={record.link.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                        {record.link.relation_type}
                      </p>
                      <p className="mt-2 text-sm font-medium text-strong">{record.assertion.text_norm}</p>
                      <p className="mt-2 text-xs text-muted">
                        {record.source?.title ?? record.link.evidence_source_id} · {formatDateTime(record.link.created_at)}
                      </p>
                    </div>
                    <div className="flex flex-col items-start gap-2">
                      <StatusBadge label={record.link.verifier_status} />
                      <form action={verifyEvidenceLinkAction.bind(null, projectId, record.link.id)}>
                        <button
                          className="rounded-pill border border-subtle bg-white/70 px-3 py-2 text-xs font-semibold text-strong transition hover:border-primary/20 hover:text-primary"
                          type="submit"
                        >
                          Verify link
                        </button>
                      </form>
                    </div>
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No evidence link has been created yet.</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

import Link from "next/link";

import type {
  DatasetDetailResponse,
  DatasetPolicyCheckResponse,
  DatasetSnapshotRead,
} from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { BlockingSummary } from "@/components/status/blocking-summary";
import { StatusBadge } from "@/components/status/status-badge";
import { SnapshotCreationPanel } from "@/features/datasets/snapshot-creation-panel";

function rowCountLabel(rowCount?: number | null): string {
  if (rowCount === null || rowCount === undefined) {
    return "Unknown";
  }

  return rowCount.toLocaleString("en-US");
}

function policyReasons(policyCheck: DatasetPolicyCheckResponse | null): string[] {
  if (!policyCheck) {
    return ["No policy check result is available yet."];
  }

  if (policyCheck.blocking_reasons && policyCheck.blocking_reasons.length > 0) {
    return policyCheck.blocking_reasons;
  }

  return [];
}

export function DatasetDetail({
  detail,
  policyCheck,
  snapshots,
}: {
  detail: DatasetDetailResponse;
  policyCheck: DatasetPolicyCheckResponse | null;
  snapshots: DatasetSnapshotRead[];
}) {
  const { dataset, current_snapshot: currentSnapshot } = detail;

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Dataset</p>
            <h1 className="mt-3 font-serif text-4xl text-strong">{dataset.display_name}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
              Dataset detail remains project-scoped. The current view keeps `dataset`, `dataset_snapshot`, and policy
              gate state visible before workflow initiation.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={dataset.source_kind} />
            <StatusBadge label={dataset.pii_level} />
            <StatusBadge label={dataset.license_class} />
          </div>
        </div>
        <dl className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Current Snapshot"
            note={currentSnapshot ? `#${currentSnapshot.snapshot_no}` : "None"}
            value={currentSnapshot ? formatDateTime(currentSnapshot.created_at) : "Create snapshot"}
          />
          <MetricCard
            label="Policy Check"
            note={policyCheck ? (policyCheck.allowed ? "allowed" : "blocked") : "not run"}
            value={policyCheck ? `${policyCheck.phi_scan_status} / ${policyCheck.deid_status}` : "No result"}
          />
          <MetricCard
            label="Source Ref"
            note={dataset.source_ref ?? "None"}
            noteTestId="dataset-source-ref"
            value={dataset.source_kind}
          />
          <MetricCard
            label="Last Updated"
            note={formatDateTime(dataset.updated_at ?? dataset.created_at)}
            value={dataset.id.slice(0, 8)}
          />
        </dl>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Current Snapshot</p>
          {currentSnapshot ? (
            <div className="mt-4 space-y-4">
              <InfoRow label="Snapshot Number" value={`#${currentSnapshot.snapshot_no}`} />
              <InfoRow label="Object URI" value={currentSnapshot.object_uri} mono />
              <InfoRow label="Input Hash" value={currentSnapshot.input_hash_sha256} mono />
              <InfoRow label="Row Count" value={rowCountLabel(currentSnapshot.row_count)} />
              <InfoRow label="Column Schema" value={JSON.stringify(currentSnapshot.column_schema_json)} mono />
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted">No current snapshot is recorded for this dataset.</p>
          )}
        </div>

        <BlockingSummary
          blocked={policyCheck ? !policyCheck.allowed : true}
          reasons={policyReasons(policyCheck)}
          title="Policy readiness"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Snapshot History</p>
              <h2 className="mt-2 font-serif text-2xl text-strong">Immutable dataset_snapshot list</h2>
            </div>
            <Link
              className="rounded-pill border border-subtle bg-app px-4 py-2 text-sm font-semibold text-strong"
              href={`/projects/${dataset.project_id}/workflows`}
            >
              Go to workflows
            </Link>
          </div>
          <div className="mt-5 space-y-4">
            {snapshots.length > 0 ? (
              snapshots.map((snapshot) => (
                <article key={snapshot.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                        dataset_snapshot #{snapshot.snapshot_no}
                      </p>
                      <p className="mt-2 text-sm font-medium text-strong">{snapshot.object_uri}</p>
                      <p className="mt-2 text-xs text-muted">{formatDateTime(snapshot.created_at)}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge label={snapshot.phi_scan_status} />
                      <StatusBadge label={snapshot.deid_status} />
                    </div>
                  </div>
                  <dl className="mt-4 grid gap-3 md:grid-cols-2">
                    <InfoRow label="Row Count" value={rowCountLabel(snapshot.row_count)} compact />
                    <InfoRow label="Input Hash" value={snapshot.input_hash_sha256} compact mono />
                  </dl>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted">No snapshot history exists yet.</p>
            )}
          </div>
        </div>

        <SnapshotCreationPanel datasetId={dataset.id} projectId={dataset.project_id} />
      </section>
    </div>
  );
}

function MetricCard({
  label,
  note,
  noteTestId,
  value,
}: {
  label: string;
  note: string;
  noteTestId?: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-subtle bg-app px-4 py-4">
      <dt className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</dt>
      <dd className="mt-2 text-sm font-medium text-strong" data-testid={noteTestId}>
        {note}
      </dd>
      <p className="mt-1 text-xs text-muted">{value}</p>
    </div>
  );
}

function InfoRow({
  compact = false,
  label,
  mono = false,
  value,
}: {
  compact?: boolean;
  label: string;
  mono?: boolean;
  value: string;
}) {
  return (
    <div className={`rounded-2xl border border-subtle bg-app ${compact ? "px-3 py-3" : "px-4 py-4"}`}>
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{label}</p>
      <p className={`mt-2 text-sm text-strong ${mono ? "font-mono break-all" : ""}`}>{value}</p>
    </div>
  );
}

import type { DatasetRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { EntityTable, TableStatusCell } from "@/components/tables/entity-table";

export function DatasetList({ datasets }: { datasets: DatasetRead[] }) {
  return (
    <EntityTable
      columns={[
        {
          key: "display_name",
          label: "Dataset",
          render: (dataset) => dataset.display_name,
        },
        {
          key: "source_kind",
          label: "Source",
          render: (dataset) => dataset.source_kind,
        },
        {
          key: "pii_level",
          label: "PII",
          render: (dataset) => dataset.pii_level,
        },
        {
          key: "license_class",
          label: "License",
          render: (dataset) => dataset.license_class,
        },
        {
          key: "snapshot",
          label: "Current Snapshot",
          render: (dataset) =>
            dataset.current_snapshot_id ? (
              <span className="font-mono text-xs text-strong">{dataset.current_snapshot_id.slice(0, 8)}</span>
            ) : (
              <TableStatusCell value="pending" />
            ),
        },
        {
          key: "updated_at",
          label: "Updated",
          render: (dataset) => formatDateTime(dataset.updated_at ?? dataset.created_at),
        },
      ]}
      emptyMessage="No dataset exists yet. Register a public accession or an upload placeholder to create the first dataset_snapshot."
      getHref={(dataset) => `/projects/${dataset.project_id}/datasets/${dataset.id}`}
      rows={datasets}
    />
  );
}

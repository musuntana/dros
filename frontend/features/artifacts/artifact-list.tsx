import type { ArtifactRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { EntityTable } from "@/components/tables/entity-table";

export function ArtifactList({
  artifacts,
  projectId,
}: {
  artifacts: ArtifactRead[];
  projectId: string;
}) {
  return (
    <EntityTable
      columns={[
        {
          key: "artifact_type",
          label: "Artifact",
          render: (artifact) => artifact.artifact_type,
        },
        {
          key: "run_id",
          label: "Run",
          render: (artifact) => (artifact.run_id ? artifact.run_id.slice(0, 8) : "Manual"),
        },
        {
          key: "storage_uri",
          label: "Storage URI",
          render: (artifact) => (
            <span className="font-mono text-xs text-strong">{artifact.storage_uri}</span>
          ),
        },
        {
          key: "mime_type",
          label: "MIME",
          render: (artifact) => artifact.mime_type ?? "n/a",
        },
        {
          key: "created_at",
          label: "Created",
          render: (artifact) => formatDateTime(artifact.created_at),
        },
      ]}
      emptyMessage="No artifact is registered yet. Create a result artifact after an analysis run or for export outputs."
      getHref={(artifact) => `/projects/${projectId}/artifacts/${artifact.id}`}
      rows={artifacts}
    />
  );
}

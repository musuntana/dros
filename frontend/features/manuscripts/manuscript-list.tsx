import type { ManuscriptRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { EntityTable, TableStatusCell } from "@/components/tables/entity-table";

export function ManuscriptList({
  manuscripts,
  projectId,
}: {
  manuscripts: ManuscriptRead[];
  projectId: string;
}) {
  return (
    <EntityTable
      columns={[
        {
          key: "title",
          label: "Manuscript",
          render: (manuscript) => manuscript.title,
        },
        {
          key: "state",
          label: "State",
          render: (manuscript) => <TableStatusCell value={manuscript.state} />,
        },
        {
          key: "type",
          label: "Type",
          render: (manuscript) => manuscript.manuscript_type,
        },
        {
          key: "version",
          label: "Current Version",
          render: (manuscript) => manuscript.current_version_no,
        },
        {
          key: "updated_at",
          label: "Updated",
          render: (manuscript) => formatDateTime(manuscript.updated_at ?? manuscript.created_at),
        },
      ]}
      emptyMessage="No manuscript exists yet. Create one after assertions are ready to be written into blocks."
      getHref={(manuscript) => `/projects/${projectId}/manuscripts/${manuscript.id}`}
      rows={manuscripts}
    />
  );
}

import type { AssertionRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { EntityTable, TableStatusCell } from "@/components/tables/entity-table";

export function AssertionList({
  assertions,
  projectId,
}: {
  assertions: AssertionRead[];
  projectId: string;
}) {
  return (
    <EntityTable
      columns={[
        {
          key: "assertion_type",
          label: "Assertion",
          render: (assertion) => assertion.assertion_type,
        },
        {
          key: "state",
          label: "State",
          render: (assertion) => <TableStatusCell value={assertion.state} />,
        },
        {
          key: "source",
          label: "Source",
          render: (assertion) =>
            assertion.source_artifact_id?.slice(0, 8) ??
            assertion.source_run_id?.slice(0, 8) ??
            "Missing source",
        },
        {
          key: "text_norm",
          label: "Text",
          render: (assertion) => assertion.text_norm,
        },
        {
          key: "created_at",
          label: "Created",
          render: (assertion) => formatDateTime(assertion.created_at),
        },
      ]}
      emptyMessage="No assertion exists yet. Extract a source-backed claim from an artifact or analysis run."
      getHref={(assertion) => `/projects/${projectId}/assertions/${assertion.id}`}
      rows={assertions}
    />
  );
}

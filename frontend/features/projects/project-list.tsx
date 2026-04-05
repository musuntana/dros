import type { ProjectRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { EntityTable, TableStatusCell } from "@/components/tables/entity-table";

export function ProjectList({ projects }: { projects: ProjectRead[] }) {
  return (
    <EntityTable
      columns={[
        {
          key: "name",
          label: "Project",
          render: (project) => project.name,
        },
        {
          key: "type",
          label: "Type",
          render: (project) => project.project_type,
        },
        {
          key: "compliance",
          label: "Compliance",
          render: (project) => project.compliance_level,
        },
        {
          key: "status",
          label: "Status",
          render: (project) => <TableStatusCell value={project.status} />,
        },
        {
          key: "created",
          label: "Created",
          render: (project) => formatDateTime(project.created_at),
        },
      ]}
      emptyMessage="No project exists yet. Create one through the control plane before the workspace can bind downstream objects."
      getHref={(project) => `/projects/${project.id}`}
      rows={projects}
    />
  );
}

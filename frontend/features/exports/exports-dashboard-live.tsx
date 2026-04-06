"use client";

import { ExportsDashboard } from "@/features/exports/exports-dashboard";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function ExportsDashboardLive({ projectId }: { projectId: string }) {
  const { projection } = useWorkspaceData();

  return (
    <ExportsDashboard
      exportArtifacts={projection.artifacts.filter((artifact) =>
        ["docx", "pdf", "zip"].includes(artifact.artifact_type),
      )}
      exportJobs={projection.exports}
      manuscripts={projection.manuscripts}
      projectId={projectId}
    />
  );
}

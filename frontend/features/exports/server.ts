import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type { ArtifactRead, ExportJobRead, ManuscriptRead } from "@/lib/api/generated/control-plane";

export async function getExportsPageData(projectId: string): Promise<{
  exportArtifacts: ArtifactRead[];
  exportJobs: ExportJobRead[];
  manuscripts: ManuscriptRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [manuscriptsResponse, exportJobResponse, artifactResponse] = await Promise.all([
    client.listManuscripts(projectId),
    client.listExportJobs(projectId, { limit: 100, offset: 0 }),
    client.listArtifacts(projectId, { limit: 100, offset: 0 }),
  ]);

  return {
    exportArtifacts: artifactResponse.items.items.filter((artifact) =>
      ["docx", "pdf", "zip"].includes(artifact.artifact_type),
    ),
    exportJobs: exportJobResponse.items.items,
    manuscripts: manuscriptsResponse.items,
  };
}

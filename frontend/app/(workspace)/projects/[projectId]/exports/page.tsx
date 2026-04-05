import { ErrorCard } from "@/components/status/error-card";
import { ExportsDashboard } from "@/features/exports/exports-dashboard";
import { getExportsPageData } from "@/features/exports/server";

export default async function ExportsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { exportArtifacts, exportJobs, manuscripts } = await getExportsPageData(projectId);

    return (
      <ExportsDashboard
        exportArtifacts={exportArtifacts}
        exportJobs={exportJobs}
        manuscripts={manuscripts}
        projectId={projectId}
      />
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Exports failed to load" />;
  }
}

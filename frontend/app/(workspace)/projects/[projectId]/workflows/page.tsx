import { ErrorCard } from "@/components/status/error-card";
import { getWorkflowSupportData } from "@/features/workflows/server";
import { WorkflowsPageLive } from "@/features/workflows/workflows-page-live";

export default async function WorkflowsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { snapshots, templates } = await getWorkflowSupportData(projectId);

    return <WorkflowsPageLive projectId={projectId} snapshotOptions={snapshots} templateOptions={templates} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Workflows failed to load" />;
  }
}

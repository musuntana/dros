import { ErrorCard } from "@/components/status/error-card";
import { WorkflowDetail } from "@/features/workflows/workflow-detail";
import { getWorkflowDetailPageData, toWorkflowDetailViewModel } from "@/features/workflows/server";

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; workflowInstanceId: string }>;
}) {
  try {
    const { projectId, workflowInstanceId } = await params;
    const { detail, relatedRuns, snapshots, templates } = await getWorkflowDetailPageData(
      projectId,
      workflowInstanceId,
    );

    return (
      <WorkflowDetail
        detail={toWorkflowDetailViewModel(detail)}
        projectId={projectId}
        relatedRuns={relatedRuns}
        snapshots={snapshots}
        templates={templates}
      />
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Workflow detail failed to load" />;
  }
}

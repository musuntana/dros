import { WorkflowDetailLive } from "@/features/workflows/workflow-detail-live";

export default async function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; workflowInstanceId: string }>;
}) {
  const { projectId, workflowInstanceId } = await params;
  return <WorkflowDetailLive projectId={projectId} workflowInstanceId={workflowInstanceId} />;
}

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type {
  AnalysisRunRead,
  AnalysisTemplateRead,
  ArtifactRead,
  WorkflowDetailResponse,
  WorkflowInstanceRead,
} from "@/lib/api/generated/control-plane";
import { toWorkflowDetailViewModel, type WorkflowDetailViewModel, type WorkflowSnapshotOption } from "@/features/workflows/types";

async function getWorkflowSnapshotOptions(projectId: string): Promise<WorkflowSnapshotOption[]> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const datasets = (await client.listDatasets(projectId, { limit: 50, offset: 0 })).items.items;
  const datasetDetails = await Promise.all(
    datasets
      .filter((dataset) => dataset.current_snapshot_id)
      .map(async (dataset) => ({
        dataset,
        detail: await client.getDataset(projectId, dataset.id),
      })),
  );

  return datasetDetails
    .flatMap(({ dataset, detail }) =>
      detail.current_snapshot
        ? [
            {
              datasetId: dataset.id,
              datasetName: dataset.display_name,
              deidStatus: detail.current_snapshot.deid_status,
              phiScanStatus: detail.current_snapshot.phi_scan_status,
              snapshotId: detail.current_snapshot.id,
              snapshotNo: detail.current_snapshot.snapshot_no,
            },
          ]
        : [],
    )
    .sort((left, right) => left.datasetName.localeCompare(right.datasetName));
}

function sortNewestFirst<T extends { created_at?: string | null; started_at?: string | null }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftValue = left.started_at ?? left.created_at ?? "";
    const rightValue = right.started_at ?? right.created_at ?? "";
    return rightValue.localeCompare(leftValue);
  });
}

export async function getWorkflowsPageData(projectId: string): Promise<{
  analysisRuns: AnalysisRunRead[];
  snapshots: WorkflowSnapshotOption[];
  templates: AnalysisTemplateRead[];
  workflows: WorkflowInstanceRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [workflowResponse, runResponse, templateResponse, snapshots] = await Promise.all([
    client.listWorkflows(projectId, { limit: 50, offset: 0 }),
    client.listAnalysisRuns(projectId, { limit: 100, offset: 0 }),
    client.listTemplates(),
    getWorkflowSnapshotOptions(projectId),
  ]);

  return {
    analysisRuns: sortNewestFirst(runResponse.items.items),
    snapshots,
    templates: templateResponse.items,
    workflows: workflowResponse.items.items,
  };
}

export async function getWorkflowDetailPageData(
  projectId: string,
  workflowId: string,
): Promise<{
  detail: WorkflowDetailResponse;
  relatedRuns: AnalysisRunRead[];
  snapshots: WorkflowSnapshotOption[];
  templates: AnalysisTemplateRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [detail, runResponse, templateResponse, snapshots] = await Promise.all([
    client.getWorkflow(projectId, workflowId),
    client.listAnalysisRuns(projectId, { limit: 100, offset: 0 }),
    client.listTemplates(),
    getWorkflowSnapshotOptions(projectId),
  ]);

  return {
    detail,
    relatedRuns: sortNewestFirst(runResponse.items.items.filter((run) => run.workflow_instance_id === workflowId)),
    snapshots,
    templates: templateResponse.items,
  };
}

export async function getAnalysisRunDetailPageData(
  projectId: string,
  runId: string,
): Promise<{
  detail: {
    analysisRun: AnalysisRunRead;
    artifacts: ArtifactRead[];
  };
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const response = await client.getAnalysisRun(projectId, runId);

  return {
    detail: {
      analysisRun: response.analysis_run,
      artifacts: response.artifacts ?? [],
    },
  };
}

export { toWorkflowDetailViewModel, type WorkflowDetailViewModel } from "@/features/workflows/types";

export async function getWorkflowSupportData(projectId: string): Promise<{
  analysisRuns: AnalysisRunRead[];
  snapshots: WorkflowSnapshotOption[];
  templates: AnalysisTemplateRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [runs, templates, snapshots] = await Promise.all([
    client.listAnalysisRuns(projectId, { limit: 100, offset: 0 }),
    client.listTemplates(),
    getWorkflowSnapshotOptions(projectId),
  ]);

  return {
    analysisRuns: sortNewestFirst(runs.items.items),
    snapshots,
    templates: templates.items,
  };
}

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type {
  DatasetDetailResponse,
  DatasetListResponse,
  DatasetPolicyCheckResponse,
  DatasetSnapshotListResponse,
} from "@/lib/api/generated/control-plane";

export async function getDatasetsPageData(projectId: string): Promise<{
  datasets: DatasetListResponse["items"]["items"];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const response = await client.listDatasets(projectId, { limit: 50, offset: 0 });

  return {
    datasets: response.items.items,
  };
}

export async function getDatasetDetailPageData(
  projectId: string,
  datasetId: string,
): Promise<{
  detail: DatasetDetailResponse;
  policyCheck: DatasetPolicyCheckResponse | null;
  snapshots: DatasetSnapshotListResponse["items"];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [detail, snapshots, policyCheck] = await Promise.all([
    client.getDataset(projectId, datasetId),
    client.listDatasetSnapshots(projectId, datasetId),
    client.runDatasetPolicyChecks(projectId, datasetId).catch(() => null),
  ]);

  return {
    detail,
    policyCheck,
    snapshots: snapshots.items,
  };
}

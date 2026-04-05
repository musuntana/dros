import { ErrorCard } from "@/components/status/error-card";
import { DatasetDetail } from "@/features/datasets/dataset-detail";
import { getDatasetDetailPageData } from "@/features/datasets/server";

export default async function DatasetDetailPage({
  params,
}: {
  params: Promise<{ datasetId: string; projectId: string }>;
}) {
  try {
    const { projectId, datasetId } = await params;
    const { detail, policyCheck, snapshots } = await getDatasetDetailPageData(projectId, datasetId);

    return <DatasetDetail detail={detail} policyCheck={policyCheck} snapshots={snapshots} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Dataset detail failed to load" />;
  }
}

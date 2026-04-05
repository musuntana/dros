import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import { createServerGatewayClient } from "@/lib/api/gateway/server";
import type {
  AnalysisRunRead,
  ArtifactDetailResponse,
  ArtifactRead,
  AssertionRead,
  LineageEdgeRead,
} from "@/lib/api/generated/control-plane";

export async function getArtifactsPageData(projectId: string): Promise<{
  analysisRuns: AnalysisRunRead[];
  artifacts: ArtifactRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [artifactResponse, lineage] = await Promise.all([
    client.listArtifacts(projectId, { limit: 100, offset: 0 }),
    client.getLineage(projectId),
  ]);

  return {
    analysisRuns: (lineage.analysis_runs ?? []).sort((left, right) => right.created_at.localeCompare(left.created_at)),
    artifacts: artifactResponse.items.items,
  };
}

export async function getArtifactDetailPageData(
  projectId: string,
  artifactId: string,
): Promise<{
  downloadReady: boolean;
  detail: ArtifactDetailResponse;
  emittingRun: AnalysisRunRead | null;
  relatedAssertions: AssertionRead[];
  relatedEdges: LineageEdgeRead[];
  supersededBy: ArtifactRead | null;
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [detail, lineage] = await Promise.all([client.getArtifact(projectId, artifactId), client.getLineage(projectId)]);
  let downloadReady = false;

  try {
    const gateway = await createServerGatewayClient();
    await gateway.getArtifactDownloadUrl(projectId, artifactId);
    downloadReady = true;
  } catch {
    downloadReady = false;
  }

  return {
    downloadReady,
    detail,
    emittingRun: (lineage.analysis_runs ?? []).find((run) => run.id === detail.artifact.run_id) ?? null,
    relatedAssertions: (lineage.assertions ?? []).filter((assertion) => assertion.source_artifact_id === artifactId),
    relatedEdges: (lineage.edges ?? []).filter((edge) => edge.from_id === artifactId || edge.to_id === artifactId),
    supersededBy: (lineage.artifacts ?? []).find((artifact) => artifact.id === detail.artifact.superseded_by) ?? null,
  };
}

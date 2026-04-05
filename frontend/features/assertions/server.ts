import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type {
  AnalysisRunRead,
  ArtifactRead,
  AssertionDetailResponse,
  AssertionRead,
  BlockAssertionLinkRead,
  EvidenceLinkRead,
} from "@/lib/api/generated/control-plane";

export async function getAssertionsPageData(projectId: string): Promise<{
  analysisRuns: AnalysisRunRead[];
  artifacts: ArtifactRead[];
  assertions: AssertionRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [assertionResponse, artifactResponse, lineage] = await Promise.all([
    client.listAssertions(projectId, { limit: 100, offset: 0 }),
    client.listArtifacts(projectId, { limit: 100, offset: 0 }),
    client.getLineage(projectId),
  ]);

  return {
    analysisRuns: (lineage.analysis_runs ?? []).sort((left, right) => right.created_at.localeCompare(left.created_at)),
    artifacts: artifactResponse.items.items,
    assertions: assertionResponse.items.items,
  };
}

export async function getAssertionDetailPageData(
  projectId: string,
  assertionId: string,
): Promise<{
  blockLinks: BlockAssertionLinkRead[];
  detail: AssertionDetailResponse;
  evidenceLinks: EvidenceLinkRead[];
  sourceArtifact: ArtifactRead | null;
  sourceRun: AnalysisRunRead | null;
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [detail, lineage] = await Promise.all([client.getAssertion(projectId, assertionId), client.getLineage(projectId)]);

  return {
    blockLinks: detail.block_links ?? [],
    detail,
    evidenceLinks: detail.evidence_links ?? [],
    sourceArtifact: (lineage.artifacts ?? []).find((artifact) => artifact.id === detail.assertion.source_artifact_id) ?? null,
    sourceRun: (lineage.analysis_runs ?? []).find((run) => run.id === detail.assertion.source_run_id) ?? null,
  };
}

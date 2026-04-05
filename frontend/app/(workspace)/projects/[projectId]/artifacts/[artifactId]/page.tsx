import { ErrorCard } from "@/components/status/error-card";
import { ArtifactDetail } from "@/features/artifacts/artifact-detail";
import { getArtifactDetailPageData } from "@/features/artifacts/server";

export default async function ArtifactDetailPage({
  params,
}: {
  params: Promise<{ artifactId: string; projectId: string }>;
}) {
  try {
    const { projectId, artifactId } = await params;
    const { detail, downloadReady, emittingRun, relatedAssertions, relatedEdges, supersededBy } =
      await getArtifactDetailPageData(
      projectId,
      artifactId,
      );

    return (
      <ArtifactDetail
        detail={detail}
        downloadReady={downloadReady}
        emittingRun={emittingRun}
        projectId={projectId}
        relatedAssertions={relatedAssertions}
        relatedEdges={relatedEdges}
        supersededBy={supersededBy}
      />
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Artifact detail failed to load" />;
  }
}

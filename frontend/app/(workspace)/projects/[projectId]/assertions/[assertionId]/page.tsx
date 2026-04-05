import { ErrorCard } from "@/components/status/error-card";
import { AssertionDetail } from "@/features/assertions/assertion-detail";
import { getAssertionDetailPageData } from "@/features/assertions/server";

export default async function AssertionDetailPage({
  params,
}: {
  params: Promise<{ assertionId: string; projectId: string }>;
}) {
  try {
    const { projectId, assertionId } = await params;
    const { blockLinks, detail, evidenceLinks, sourceArtifact, sourceRun } = await getAssertionDetailPageData(
      projectId,
      assertionId,
    );

    return (
      <AssertionDetail
        blockLinks={blockLinks}
        detail={detail}
        evidenceLinks={evidenceLinks}
        projectId={projectId}
        sourceArtifact={sourceArtifact}
        sourceRun={sourceRun}
      />
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Assertion detail failed to load" />;
  }
}

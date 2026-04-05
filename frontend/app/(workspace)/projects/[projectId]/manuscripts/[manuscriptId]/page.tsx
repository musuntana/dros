import { ErrorCard } from "@/components/status/error-card";
import { ManuscriptDetail } from "@/features/manuscripts/manuscript-detail";
import { getManuscriptDetailPageData } from "@/features/manuscripts/server";

export default async function ManuscriptDetailPage({
  params,
}: {
  params: Promise<{ manuscriptId: string; projectId: string }>;
}) {
  try {
    const { projectId, manuscriptId } = await params;
    const { blocks, manuscript, preview, verifiedAssertions } = await getManuscriptDetailPageData(
      projectId,
      manuscriptId,
    );

    return (
      <ManuscriptDetail
        blocks={blocks}
        manuscript={manuscript}
        preview={preview}
        projectId={projectId}
        verifiedAssertions={verifiedAssertions}
      />
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Manuscript detail failed to load" />;
  }
}

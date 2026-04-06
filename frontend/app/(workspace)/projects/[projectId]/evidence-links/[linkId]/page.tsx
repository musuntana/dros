import { ErrorCard } from "@/components/status/error-card";
import { EvidenceLinkDetailLive } from "@/features/evidence/evidence-link-detail-live";
import { getEvidenceLinkDetailPageData } from "@/features/evidence/server";

export default async function EvidenceLinkDetailPage({
  params,
}: {
  params: Promise<{ linkId: string; projectId: string }>;
}) {
  try {
    const { projectId, linkId } = await params;
    const detail = await getEvidenceLinkDetailPageData(projectId, linkId);

    return <EvidenceLinkDetailLive initialDetail={detail} linkId={linkId} projectId={projectId} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Evidence link detail failed to load" />;
  }
}

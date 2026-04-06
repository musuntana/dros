import { ManuscriptDetailLive } from "@/features/manuscripts/manuscript-detail-live";

export default async function ManuscriptDetailPage({
  params,
}: {
  params: Promise<{ manuscriptId: string; projectId: string }>;
}) {
  const { projectId, manuscriptId } = await params;
  return <ManuscriptDetailLive manuscriptId={manuscriptId} projectId={projectId} />;
}

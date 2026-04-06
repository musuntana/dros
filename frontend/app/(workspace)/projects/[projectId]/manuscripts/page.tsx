import { ManuscriptsPageLive } from "@/features/manuscripts/manuscripts-page-live";

export default async function ManuscriptsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <ManuscriptsPageLive projectId={projectId} />;
}

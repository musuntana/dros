import { ExportsDashboardLive } from "@/features/exports/exports-dashboard-live";

export default async function ExportsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <ExportsDashboardLive projectId={projectId} />;
}

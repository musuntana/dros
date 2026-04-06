import { ExportJobDetailLive } from "@/features/exports/export-job-detail";

export default async function ExportJobDetailPage({
  params,
}: {
  params: Promise<{ exportJobId: string; projectId: string }>;
}) {
  const { projectId, exportJobId } = await params;
  return <ExportJobDetailLive exportJobId={exportJobId} projectId={projectId} />;
}

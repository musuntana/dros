import { ErrorCard } from "@/components/status/error-card";
import { AnalysisRunDetail } from "@/features/workflows/analysis-run-detail";
import { getAnalysisRunDetailPageData } from "@/features/workflows/server";

export default async function AnalysisRunDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; runId: string }>;
}) {
  try {
    const { projectId, runId } = await params;
    const { detail } = await getAnalysisRunDetailPageData(projectId, runId);

    return <AnalysisRunDetail artifacts={detail.artifacts} projectId={projectId} run={detail.analysisRun} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Analysis run detail failed to load" />;
  }
}

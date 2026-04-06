import { ErrorCard } from "@/components/status/error-card";
import { EvidenceDashboardLive } from "@/features/evidence/evidence-dashboard-live";

export default async function EvidencePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    return <EvidenceDashboardLive projectId={projectId} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Evidence failed to load" />;
  }
}

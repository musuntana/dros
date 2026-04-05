import { ErrorCard } from "@/components/status/error-card";
import { EvidenceDashboard } from "@/features/evidence/evidence-dashboard";
import { getEvidencePageData } from "@/features/evidence/server";

export default async function EvidencePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { assertions, linkRecords, sources } = await getEvidencePageData(projectId);

    return (
      <EvidenceDashboard
        assertions={assertions}
        linkRecords={linkRecords}
        projectId={projectId}
        sources={sources}
      />
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Evidence failed to load" />;
  }
}

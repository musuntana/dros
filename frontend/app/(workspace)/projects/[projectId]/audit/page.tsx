import { ErrorCard } from "@/components/status/error-card";
import { AuditDashboard } from "@/features/audit/audit-dashboard";
import { getAuditPageData } from "@/features/audit/server";

export default async function AuditPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { events } = await getAuditPageData(projectId);

    return <AuditDashboard events={events} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Audit failed to load" />;
  }
}

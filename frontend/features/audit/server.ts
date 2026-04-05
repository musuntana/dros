import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type { AuditEventRead } from "@/lib/api/generated/control-plane";

export async function getAuditPageData(projectId: string): Promise<{
  events: AuditEventRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const response = await client.listAuditEvents(projectId, { limit: 100, offset: 0 });

  return {
    events: response.events.items,
  };
}

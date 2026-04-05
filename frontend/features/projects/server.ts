import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type { AuditEventRead } from "@/lib/api/generated/control-plane";
import type { ProjectEvent } from "@/lib/api/gateway";
import { createServerGatewayClient } from "@/lib/api/gateway/server";

function toProjectEventSeed(event: AuditEventRead): ProjectEvent {
  return {
    event_id: event.id,
    event_name: event.event_type,
    schema_version: "1.0.0",
    produced_by: "audit.seed",
    trace_id: event.trace_id ?? `audit:${event.id}`,
    request_id: event.request_id ?? event.id,
    tenant_id: event.tenant_id,
    project_id: event.project_id ?? "",
    idempotency_key: event.event_hash,
    occurred_at: event.created_at,
    payload: event.payload_json,
  };
}

export async function getProjectsIndex() {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  return client.listProjects({ limit: 20, offset: 0 });
}

export async function getProjectWorkspaceData(projectId: string) {
  const [client, gateway] = await Promise.all([
    createServerControlPlaneClient({ cache: "no-store" }),
    createServerGatewayClient(),
  ]);
  const [detail, members, session, auditEvents] = await Promise.all([
    client.getProject(projectId),
    client.listProjectMembers(projectId),
    gateway.getSession(),
    client.listAuditEvents(projectId, { limit: 6, offset: 0 }),
  ]);

  return {
    detail,
    initialEvents: auditEvents.events.items.map(toProjectEventSeed),
    members: members.items,
    session,
  };
}

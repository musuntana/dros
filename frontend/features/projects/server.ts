import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type { AuditEventRead, ProjectDetailResponse, ProjectMemberRead } from "@/lib/api/generated/control-plane";
import type { ProjectEvent } from "@/lib/api/gateway";
import type { SessionRead } from "@/lib/api/gateway";
import { createServerGatewayClient } from "@/lib/api/gateway/server";
import type { ProjectWorkspaceProjection } from "@/features/projects/workspace-projection";

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

export interface ProjectWorkspaceData {
  detail: ProjectDetailResponse;
  initialEvents: ProjectEvent[];
  members: ProjectMemberRead[];
  projection: ProjectWorkspaceProjection;
  session: SessionRead | null;
}

export async function getProjectWorkspaceData(projectId: string) {
  const [client, gateway] = await Promise.all([
    createServerControlPlaneClient({ cache: "no-store" }),
    createServerGatewayClient(),
  ]);
  const [detail, members, session, auditEvents, workflows, lineage, evidenceLinks, evidenceSources, reviews, exports, manuscripts] = await Promise.all([
    client.getProject(projectId),
    client.listProjectMembers(projectId),
    gateway.getSession(),
    client.listAuditEvents(projectId, { limit: 12, offset: 0 }),
    client.listWorkflows(projectId, { limit: 20, offset: 0 }),
    client.getLineage(projectId),
    client.listEvidenceLinks(projectId, { limit: 100, offset: 0 }),
    client.listEvidenceSources(projectId, { limit: 100, offset: 0 }),
    client.listReviews(projectId, { limit: 50, offset: 0 }),
    client.listExportJobs(projectId, { limit: 100, offset: 0 }),
    client.listManuscripts(projectId),
  ]);
  const manuscriptBlocks = (
    await Promise.all(
      manuscripts.items.map(async (manuscript) => (await client.listManuscriptBlocks(projectId, manuscript.id)).items),
    )
  ).flatMap((blocks) => blocks);

  const projection: ProjectWorkspaceProjection = {
    analysisRuns: [...(lineage.analysis_runs ?? [])].sort((left, right) => right.created_at.localeCompare(left.created_at)),
    artifacts: [...(lineage.artifacts ?? [])].sort((left, right) => right.created_at.localeCompare(left.created_at)),
    assertions: [...(lineage.assertions ?? [])].sort((left, right) => right.created_at.localeCompare(left.created_at)),
    edges: lineage.edges ?? [],
    evidenceLinks: [...evidenceLinks.items.items].sort((left, right) => right.created_at.localeCompare(left.created_at)),
    evidenceSources: [...evidenceSources.items.items].sort((left, right) => right.cached_at.localeCompare(left.cached_at)),
    exports: [...exports.items.items].sort((left, right) => right.requested_at.localeCompare(left.requested_at)),
    manuscriptBlocks: [...manuscriptBlocks].sort((left, right) => right.created_at.localeCompare(left.created_at)),
    manuscripts: [...manuscripts.items].sort((left, right) => right.created_at.localeCompare(left.created_at)),
    reviews: [...reviews.items.items].sort((left, right) => right.created_at.localeCompare(left.created_at)),
    workflows: [...workflows.items.items].sort((left, right) => right.started_at.localeCompare(left.started_at)),
  };

  return {
    detail,
    initialEvents: auditEvents.events.items.map(toProjectEventSeed),
    members: members.items,
    projection,
    session,
  } satisfies ProjectWorkspaceData;
}

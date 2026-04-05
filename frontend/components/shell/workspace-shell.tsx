import type { ReactNode } from "react";

import type { ProjectDetailResponse } from "@/lib/api/generated/control-plane";
import type { ProjectEvent, SessionRead } from "@/lib/api/gateway";

import type { InspectorSection } from "@/components/shell/inspector-panel";
import { ProjectHeader } from "@/components/shell/project-header";
import { WorkspaceSidebar } from "@/components/shell/workspace-sidebar";

function buildInspectorSections(detail: ProjectDetailResponse, session: SessionRead | null): InspectorSection[] {
  const activeWorkflows = detail.active_workflows ?? [];
  const scopeTokens = Array.isArray(session?.scopes_json?.scope_tokens)
    ? session.scopes_json.scope_tokens.map((scope) => String(scope))
    : [];
  const truth = [
    { label: "Project Status", value: detail.project.status },
    { label: "Compliance Level", value: detail.project.compliance_level },
    {
      label: "Latest Snapshot",
      value: detail.latest_snapshot
        ? `#${detail.latest_snapshot.snapshot_no} is available`
        : "No dataset snapshot is available yet",
    },
  ];

  const lineage = [
    { label: "Boundary", value: "Project scope controls all downstream objects." },
    {
      label: "Active Workflows",
      value:
        activeWorkflows.length > 0
          ? `${activeWorkflows.length} active workflow instance(s) can produce artifacts.`
          : "No active workflow is running.",
    },
    {
      label: "Writing Target",
      value: detail.active_manuscript
        ? `Current manuscript is ${detail.active_manuscript.title}.`
        : "No manuscript is selected as the active writing target.",
    },
  ];

  const nextAction = [
    {
      label: "Immediate Step",
      value: detail.latest_snapshot
        ? "Advance into workflow planning or analysis run creation."
        : "Register a dataset and create a snapshot before entering workflow.",
    },
    {
      label: "Writing Rule",
      value: "Writing pages must stay assertion-backed and consume verified sources only.",
    },
    {
      label: "Gate Rule",
      value: "Verify and export remain disabled until gate results pass.",
    },
  ];

  return [
    {
      title: "Session",
      items: [
        { label: "Tenant", value: session?.tenant_id ?? "No tenant context" },
        { label: "Actor", value: session?.actor_id ?? "No actor context" },
        { label: "Role", value: String(session?.scopes_json?.project_role ?? "unknown") },
        { label: "Auth Source", value: String(session?.scopes_json?.auth_source ?? "unknown") },
        {
          label: "Scopes",
          value: scopeTokens.length > 0 ? scopeTokens.join(", ") : "No explicit scopes forwarded",
        },
      ],
    },
    { title: "Truth", items: truth },
    { title: "Lineage", items: lineage },
    { title: "Next Action", items: nextAction },
  ];
}

export function WorkspaceShell({
  detail,
  children,
  initialEvents,
  session,
}: {
  detail: ProjectDetailResponse;
  children: ReactNode;
  initialEvents: ProjectEvent[];
  session: SessionRead | null;
}) {
  return (
    <div className="space-y-6">
      <ProjectHeader detail={detail} />
      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
        <WorkspaceSidebar detail={detail} initialEvents={initialEvents} sections={buildInspectorSections(detail, session)} />
        <main className="min-w-0 space-y-6">{children}</main>
      </div>
    </div>
  );
}

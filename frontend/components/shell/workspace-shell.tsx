"use client";

import type { ReactNode } from "react";
import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { ProjectDetailResponse, ProjectMemberRead } from "@/lib/api/generated/control-plane";
import type { ProjectEvent, SessionRead } from "@/lib/api/gateway";
import { createGatewayClient } from "@/lib/api/gateway";

import type { InspectorSection } from "@/components/shell/inspector-panel";
import {
  MAX_PROJECT_EVENTS,
  mergeProjectEventSnapshot,
  mergeProjectEvents,
} from "@/components/shell/project-event-utils";
import { WorkspaceChrome } from "@/components/shell/workspace-chrome";
import { ProjectHeader } from "@/components/shell/project-header";
import type { ProjectWorkspaceProjection } from "@/features/projects/workspace-projection";
import { WorkspaceDataProvider } from "@/features/projects/workspace-context";

interface WorkspaceSnapshotResponse {
  detail: ProjectDetailResponse;
  initialEvents: ProjectEvent[];
  members: ProjectMemberRead[];
  projection: ProjectWorkspaceProjection;
  session: SessionRead | null;
}

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
    {
      label: "Review Scope",
      value: detail.review_summary_scope
        ? `Review summary is scoped to ${detail.review_summary_scope.label ?? detail.review_summary_scope.target_id} v${detail.review_summary_scope.target_version_no ?? "n/a"}.`
        : "Review summary is not scoped because no active manuscript is selected.",
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

function shouldRefreshWorkspaceForEvent(event: ProjectEvent): boolean {
  return (
    event.event_name === "project.created" ||
    event.event_name.startsWith("project.") ||
    event.event_name.startsWith("dataset.") ||
    event.event_name.startsWith("workflow.") ||
    event.event_name.startsWith("analysis.run") ||
    event.event_name.startsWith("artifact.") ||
    event.event_name.startsWith("assertion.") ||
    event.event_name.startsWith("evidence.") ||
    event.event_name.startsWith("review.") ||
    event.event_name.startsWith("verify.") ||
    event.event_name.startsWith("verification.") ||
    event.event_name.startsWith("export.") ||
    event.event_name.startsWith("manuscript.")
  );
}

async function fetchWorkspaceSnapshot(projectId: string, signal?: AbortSignal): Promise<WorkspaceSnapshotResponse> {
  const response = await fetch(`/api/projects/${projectId}/workspace`, {
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`workspace snapshot refresh failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as WorkspaceSnapshotResponse;
}

export function WorkspaceShell({
  detail,
  children,
  initialEvents,
  members,
  projection,
  session,
}: {
  detail: ProjectDetailResponse;
  children: ReactNode;
  initialEvents: ProjectEvent[];
  members: ProjectMemberRead[];
  projection: ProjectWorkspaceProjection;
  session: SessionRead | null;
}) {
  const router = useRouter();
  const [liveDetail, setLiveDetail] = useState(detail);
  const [liveEvents, setLiveEvents] = useState(initialEvents.slice(0, MAX_PROJECT_EVENTS));
  const [liveMembers, setLiveMembers] = useState(members);
  const [liveProjection, setLiveProjection] = useState(projection);
  const [liveSession, setLiveSession] = useState(session);
  const refreshTimerRef = useRef<number | null>(null);
  const refreshAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setLiveDetail(detail);
    setLiveEvents(initialEvents.slice(0, MAX_PROJECT_EVENTS));
    setLiveMembers(members);
    setLiveProjection(projection);
    setLiveSession(session);
  }, [detail, initialEvents, members, projection, session]);

  useEffect(() => {
    const gateway = createGatewayClient();
    return gateway.subscribeProjectEvents(detail.project.id, (event) => {
      startTransition(() => {
        setLiveEvents((current) => mergeProjectEvents(current, event));
      });

      if (!shouldRefreshWorkspaceForEvent(event)) {
        return;
      }

      if (refreshTimerRef.current !== null) {
        window.clearTimeout(refreshTimerRef.current);
      }

      refreshTimerRef.current = window.setTimeout(() => {
        if (refreshAbortRef.current) {
          refreshAbortRef.current.abort();
        }

        const controller = new AbortController();
        refreshAbortRef.current = controller;
        void fetchWorkspaceSnapshot(detail.project.id, controller.signal)
          .then((snapshot) => {
            if (controller.signal.aborted) {
              return;
            }
            startTransition(() => {
              setLiveDetail(snapshot.detail);
              setLiveMembers(snapshot.members);
              setLiveProjection(snapshot.projection);
              setLiveSession(snapshot.session);
              setLiveEvents((current) =>
                mergeProjectEventSnapshot(current, snapshot.initialEvents.slice(0, MAX_PROJECT_EVENTS)),
              );
            });
          })
          .catch(() => {
            if (!controller.signal.aborted) {
              startTransition(() => {
                router.refresh();
              });
            }
          })
          .finally(() => {
            if (refreshAbortRef.current === controller) {
              refreshAbortRef.current = null;
            }
          });

        refreshTimerRef.current = null;
      }, 150);
    });
  }, [detail.project.id, router]);

  useEffect(() => {
    return () => {
      if (refreshTimerRef.current !== null) {
        window.clearTimeout(refreshTimerRef.current);
      }
      if (refreshAbortRef.current) {
        refreshAbortRef.current.abort();
      }
    };
  }, []);

  const sections = useMemo(
    () => buildInspectorSections(liveDetail, liveSession),
    [liveDetail, liveSession],
  );

  const workspaceValue = useMemo(
    () => ({
      detail: liveDetail,
      events: liveEvents,
      members: liveMembers,
      projection: liveProjection,
      session: liveSession,
    }),
    [liveDetail, liveEvents, liveMembers, liveProjection, liveSession],
  );

  return (
    <WorkspaceDataProvider value={workspaceValue}>
      <div className="space-y-6">
        <ProjectHeader detail={liveDetail} />
        <WorkspaceChrome
          detail={liveDetail}
          events={liveEvents}
          projection={liveProjection}
          sections={sections}
        >
          {children}
        </WorkspaceChrome>
      </div>
    </WorkspaceDataProvider>
  );
}

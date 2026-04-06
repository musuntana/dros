"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import type { ProjectDetailResponse } from "@/lib/api/generated/control-plane";
import type { ProjectEvent } from "@/lib/api/gateway";
import { formatDateTime } from "@/lib/format/date";

import { InspectorPanel, type InspectorFocus, type InspectorSection } from "@/components/shell/inspector-panel";
import { ObjectRail } from "@/components/shell/object-rail";
import {
  buildProjectEventLinks,
  summarizeProjectEventPayload,
} from "@/components/shell/project-event-utils";
import {
  buildWorkspaceRouteFocus,
  classifyWorkspaceRouteStage,
  parseWorkspaceRouteObject,
} from "@/components/shell/workspace-object-focus";
import { ProjectStageTimeline } from "@/components/shell/project-stage-timeline";
import type {
  ProjectWorkspaceProjection,
  WorkspaceStage,
  WorkspaceStageKey,
} from "@/features/projects/workspace-projection";
import { buildWorkspaceStages, getDefaultWorkspaceStageKey } from "@/features/projects/workspace-projection";

type WorkspaceSelection =
  | { kind: "event"; eventId: string }
  | { kind: "stage"; stageKey: WorkspaceStageKey };

function buildEventFocus(projectId: string, event: ProjectEvent | null): InspectorFocus | null {
  if (!event) {
    return null;
  }

  return {
    id: `event:${event.event_id}`,
    eyebrow: "Selected Event",
    title: event.event_name,
    summary: summarizeProjectEventPayload(event.payload),
    items: [
      { label: "Producer", value: event.produced_by },
      { label: "Occurred", value: formatDateTime(event.occurred_at) },
      { label: "Trace", value: event.trace_id },
      { label: "Request", value: event.request_id },
      { label: "Event Id", value: event.event_id },
    ],
    actions: buildProjectEventLinks(projectId, event),
    payload: event.payload,
  };
}

function buildStageFocus(stage: WorkspaceStage | null): InspectorFocus | null {
  if (!stage) {
    return null;
  }

  return {
    id: `stage:${stage.key}`,
    eyebrow: stage.eyebrow,
    title: stage.title,
    summary: stage.summary,
    items: [
      { label: "Status", value: stage.status },
      { label: "Projection", value: stage.description },
      ...(stage.updatedAt ? [{ label: "Updated", value: formatDateTime(stage.updatedAt) }] : []),
      ...stage.metrics,
    ],
    actions: stage.actions,
    payload: stage.details,
  };
}

export function WorkspaceChrome({
  children,
  detail,
  events,
  projection,
  sections,
}: {
  children: ReactNode;
  detail: ProjectDetailResponse;
  events: ProjectEvent[];
  projection: ProjectWorkspaceProjection;
  sections: InspectorSection[];
}) {
  const pathname = usePathname();
  const [selection, setSelection] = useState<WorkspaceSelection | null>(null);

  const stages = buildWorkspaceStages({
    detail,
    projectId: detail.project.id,
    projection,
  });
  const defaultStageKey = getDefaultWorkspaceStageKey(stages);
  const routeObject = parseWorkspaceRouteObject(pathname, detail.project.id);
  const routeFocus = buildWorkspaceRouteFocus({
    detail,
    projectId: detail.project.id,
    projection,
    routeObject,
  });
  const routeStageKey = classifyWorkspaceRouteStage(routeObject, projection);

  useEffect(() => {
    setSelection(null);
  }, [pathname]);

  useEffect(() => {
    if (selection?.kind === "event" && !events.some((event) => event.event_id === selection.eventId)) {
      setSelection(null);
      return;
    }

    if (selection?.kind === "stage" && !stages.some((stage) => stage.key === selection.stageKey)) {
      setSelection(null);
    }
  }, [events, selection, stages]);

  const selectedEvent = selection?.kind === "event"
    ? events.find((event) => event.event_id === selection.eventId) ?? null
    : null;
  const selectedStage = selection?.kind === "stage"
    ? stages.find((stage) => stage.key === selection.stageKey) ?? null
    : null;
  const defaultStage = stages.find((stage) => stage.key === (routeStageKey ?? defaultStageKey)) ?? null;
  const focus = selectedEvent
    ? buildEventFocus(detail.project.id, selectedEvent)
    : selectedStage
      ? buildStageFocus(selectedStage)
      : routeFocus ?? buildStageFocus(defaultStage);
  const resetFocusLabel = selection
    ? routeFocus
      ? "Inspect current object"
      : "Return to stage"
    : null;

  return (
    <div className="space-y-6">
      <ObjectRail projectId={detail.project.id} projectStatus={detail.project.status} />
      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)_360px]">
        <aside className="space-y-6 xl:col-start-1">
          <ProjectStageTimeline
            events={events}
            onSelectEvent={(eventId) => setSelection({ kind: "event", eventId })}
            onSelectStage={(stageKey) => setSelection({ kind: "stage", stageKey })}
            selectedEventId={selection?.kind === "event" ? selection.eventId : null}
            selectedStageKey={selection?.kind === "stage" ? selection.stageKey : routeStageKey ?? defaultStageKey}
            stages={stages}
          />
        </aside>
        <div className="xl:col-start-3">
          <InspectorPanel
            focus={focus}
            onResetFocus={selection ? () => setSelection(null) : null}
            resetFocusLabel={resetFocusLabel}
            sections={sections}
          />
        </div>
        <main className="min-w-0 xl:col-start-2 xl:row-start-1">{children}</main>
      </div>
    </div>
  );
}

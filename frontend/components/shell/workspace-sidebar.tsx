"use client";

import { startTransition, useEffect, useState } from "react";

import type { ProjectEvent } from "@/lib/api/gateway";
import { createGatewayClient } from "@/lib/api/gateway";
import { formatDateTime } from "@/lib/format/date";
import type { ProjectDetailResponse } from "@/lib/api/generated/control-plane";

import {
  buildProjectEventLinks,
  MAX_PROJECT_EVENTS,
  mergeProjectEvents,
  summarizeProjectEventPayload,
} from "@/components/shell/project-event-utils";
import { InspectorPanel, type InspectorFocus, type InspectorSection } from "@/components/shell/inspector-panel";
import { ObjectRail } from "@/components/shell/object-rail";
import { ProjectEventsFeed } from "@/components/shell/project-events-feed";

function buildEventFocus(projectId: string, event: ProjectEvent | null): InspectorFocus | null {
  if (!event) {
    return null;
  }

  return {
    id: event.event_id,
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

export function WorkspaceSidebar({
  detail,
  initialEvents,
  sections,
}: {
  detail: ProjectDetailResponse;
  initialEvents: ProjectEvent[];
  sections: InspectorSection[];
}) {
  const [events, setEvents] = useState<ProjectEvent[]>(initialEvents.slice(0, MAX_PROJECT_EVENTS));
  const [selectedEventId, setSelectedEventId] = useState<string | null>(initialEvents[0]?.event_id ?? null);

  useEffect(() => {
    const nextEvents = initialEvents.slice(0, MAX_PROJECT_EVENTS);
    setEvents(nextEvents);
    setSelectedEventId(nextEvents[0]?.event_id ?? null);
  }, [initialEvents]);

  useEffect(() => {
    const gateway = createGatewayClient();
    return gateway.subscribeProjectEvents(detail.project.id, (event) => {
      startTransition(() => {
        setEvents((current) => mergeProjectEvents(current, event));
      });
    });
  }, [detail.project.id]);

  useEffect(() => {
    setSelectedEventId((current) => {
      if (current && events.some((event) => event.event_id === current)) {
        return current;
      }

      return events[0]?.event_id ?? null;
    });
  }, [events]);

  const selectedEvent = events.find((event) => event.event_id === selectedEventId) ?? null;

  return (
    <div className="space-y-6">
      <ObjectRail projectId={detail.project.id} projectStatus={detail.project.status} />
      <InspectorPanel focus={buildEventFocus(detail.project.id, selectedEvent)} sections={sections} />
      <ProjectEventsFeed events={events} onSelectEvent={setSelectedEventId} selectedEventId={selectedEventId} />
    </div>
  );
}

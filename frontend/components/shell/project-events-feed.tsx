"use client";

import type { ProjectEvent } from "@/lib/api/gateway";
import { formatDateTime } from "@/lib/format/date";
import { cn } from "@/lib/utils";

import { summarizeProjectEventPayload } from "@/components/shell/project-event-utils";

export function ProjectEventsFeed({
  events,
  onSelectEvent,
  selectedEventId,
}: {
  events: ProjectEvent[];
  onSelectEvent: (eventId: string) => void;
  selectedEventId: string | null;
}) {
  return (
    <section
      className="rounded-card border border-subtle bg-surface p-5 shadow-soft"
      data-testid="workspace-live-events"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Realtime</p>
          <h3 className="mt-2 font-serif text-2xl text-strong">Project events</h3>
        </div>
        <span className="rounded-pill border border-subtle bg-app px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-strong">
          live
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {events.length > 0 ? (
          events.map((event) => (
            <button
              key={event.event_id}
              aria-pressed={selectedEventId === event.event_id}
              className={cn(
                "block w-full rounded-2xl border px-4 py-4 text-left transition",
                selectedEventId === event.event_id
                  ? "border-primary/30 bg-primary/10 text-primary shadow-soft"
                  : "border-subtle bg-app text-strong hover:border-primary/20 hover:bg-primary/5",
              )}
              data-testid={`workspace-live-event:${event.event_name}`}
              onClick={() => onSelectEvent(event.event_id)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{event.event_name}</p>
                  <p className="mt-2 text-sm font-medium text-strong">{summarizeProjectEventPayload(event.payload)}</p>
                </div>
                <span className="rounded-full border border-subtle bg-white/70 px-3 py-1 text-[11px] font-semibold text-strong">
                  {event.produced_by}
                </span>
              </div>
              <p className="mt-3 text-xs text-muted">{formatDateTime(event.occurred_at)}</p>
            </button>
          ))
        ) : (
          <p className="text-sm text-muted">No project event has been emitted yet.</p>
        )}
      </div>
    </section>
  );
}

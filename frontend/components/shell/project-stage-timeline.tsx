"use client";

import type { ProjectEvent } from "@/lib/api/gateway";
import { formatDateTime } from "@/lib/format/date";
import { cn } from "@/lib/utils";

import type { WorkspaceStage, WorkspaceStageKey } from "@/features/projects/workspace-projection";
import { groupProjectEventsByStage } from "@/features/projects/workspace-projection";

import { StatusBadge } from "@/components/status/status-badge";
import { summarizeProjectEventPayload } from "@/components/shell/project-event-utils";

export function ProjectStageTimeline({
  events,
  onSelectEvent,
  onSelectStage,
  selectedEventId,
  selectedStageKey,
  stages,
}: {
  events: ProjectEvent[];
  onSelectEvent: (eventId: string) => void;
  onSelectStage: (stageKey: WorkspaceStageKey) => void;
  selectedEventId: string | null;
  selectedStageKey: WorkspaceStageKey | null;
  stages: WorkspaceStage[];
}) {
  const eventsByStage = groupProjectEventsByStage(events);

  return (
    <section
      className="rounded-card border border-subtle bg-surface p-5 shadow-soft"
      data-testid="workspace-stage-timeline"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Timeline</p>
          <h2 className="mt-2 font-serif text-3xl text-strong">Stage projection</h2>
        </div>
        <span className="rounded-pill border border-subtle bg-app px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-strong">
          live
        </span>
      </div>
      <ol className="mt-5 space-y-4">
        {stages.map((stage, index) => {
          const stageEvents = eventsByStage[stage.key].slice(0, 2);

          return (
            <li key={stage.key} className="relative pl-8">
              {index < stages.length - 1 ? (
                <span className="absolute left-[11px] top-10 h-[calc(100%+0.75rem)] w-px bg-border" />
              ) : null}
              <span
                className={cn(
                  "absolute left-0 top-3 inline-flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-semibold",
                  selectedStageKey === stage.key ? "border-primary bg-primary/15 text-primary" : "border-subtle bg-app text-muted",
                )}
              >
                {stage.step}
              </span>
              <button
                className={cn(
                  "block w-full rounded-3xl border px-4 py-4 text-left transition",
                  selectedStageKey === stage.key
                    ? "border-primary/30 bg-primary/10 shadow-soft"
                    : "border-subtle bg-app hover:border-primary/20 hover:bg-primary/5",
                )}
                data-testid={`workspace-stage:${stage.key}`}
                onClick={() => onSelectStage(stage.key)}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{stage.eyebrow}</p>
                    <h3 className="mt-2 font-serif text-2xl text-strong">{stage.title}</h3>
                  </div>
                  <StatusBadge label={stage.status} />
                </div>
                <p className="mt-3 text-sm leading-6 text-muted">{stage.summary}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {stage.metrics.slice(0, 4).map((metric) => (
                    <span
                      key={`${stage.key}:${metric.label}`}
                      className="rounded-pill border border-subtle bg-surface px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-strong"
                    >
                      {metric.label}: {metric.value}
                    </span>
                  ))}
                </div>
                {stage.updatedAt ? <p className="mt-4 text-xs text-muted">{formatDateTime(stage.updatedAt)}</p> : null}
              </button>
              {stageEvents.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {stageEvents.map((event) => (
                    <button
                      key={event.event_id}
                      className={cn(
                        "ml-1 block w-[calc(100%-0.25rem)] rounded-2xl border px-3 py-3 text-left transition",
                        selectedEventId === event.event_id
                          ? "border-primary/30 bg-primary/10"
                          : "border-subtle bg-surface hover:border-primary/20 hover:bg-primary/5",
                      )}
                      data-testid={`workspace-live-event:${event.event_name}`}
                      onClick={() => onSelectEvent(event.event_id)}
                      type="button"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                            {event.event_name}
                          </p>
                          <p className="mt-2 text-sm font-medium text-strong">
                            {summarizeProjectEventPayload(event.payload)}
                          </p>
                        </div>
                        <span className="rounded-full border border-subtle bg-app px-3 py-1 text-[11px] font-semibold text-strong">
                          {event.produced_by}
                        </span>
                      </div>
                      <p className="mt-3 text-xs text-muted">{formatDateTime(event.occurred_at)}</p>
                    </button>
                  ))}
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

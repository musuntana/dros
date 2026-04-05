"use client";

import { useActionState } from "react";

import type { AuditEventRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import { replayAuditAction } from "@/features/audit/actions";

const initialAuditReplayActionState = {
  message: null,
  status: "idle" as const,
};

export function AuditDashboard({ events }: { events: AuditEventRead[] }) {
  const [state, action, pending] = useActionState(replayAuditAction, initialAuditReplayActionState);

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Audit</p>
        <h1 className="mt-3 font-serif text-4xl text-strong">Project event trail</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
          Audit events are the visible execution trail for uploads, workflow transitions, verification, and export.
        </p>
      </section>

      <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Replay</p>
        <h2 className="mt-3 font-serif text-2xl text-strong">Replay the audit chain hash</h2>
        <button
          className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={pending}
          type="submit"
        >
          {pending ? "Replaying..." : "Replay audit chain"}
        </button>
        {state.message ? <p className="mt-3 text-sm text-danger">{state.message}</p> : null}
      </form>

      <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Events</p>
        <div className="mt-4 space-y-4">
          {events.length > 0 ? (
            events.map((event) => (
              <article key={event.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{event.event_type}</p>
                    <p className="mt-2 break-all text-sm font-medium text-strong">
                      {event.target_kind} · {event.target_id ?? "n/a"}
                    </p>
                    <p className="mt-2 text-xs text-muted">{formatDateTime(event.created_at)}</p>
                  </div>
                  <span className="rounded-pill border border-subtle bg-white/70 px-3 py-1 text-xs font-semibold text-strong">
                    {event.actor_type}
                  </span>
                </div>
                <pre className="mt-4 overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs text-strong">
                  {JSON.stringify(event.payload_json, null, 2)}
                </pre>
              </article>
            ))
          ) : (
            <p className="text-sm text-muted">No audit event is available yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

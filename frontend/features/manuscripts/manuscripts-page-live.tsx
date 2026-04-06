"use client";

import { ManuscriptList } from "@/features/manuscripts/manuscript-list";
import { ManuscriptCreationPanel } from "@/features/manuscripts/manuscript-panels";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function ManuscriptsPageLive({ projectId }: { projectId: string }) {
  const { projection } = useWorkspaceData();

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Manuscripts</p>
        <h1 className="mt-3 font-serif text-4xl text-strong">Assertion-backed writing targets</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
          Manuscript objects track versioned block composition. Export remains a later gate and does not bypass review.
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <ManuscriptCreationPanel projectId={projectId} />
        <ManuscriptList manuscripts={projection.manuscripts} projectId={projectId} />
      </section>
    </div>
  );
}

"use client";

import type { AnalysisTemplateRead } from "@/lib/api/generated/control-plane";

import { AnalysisPlanPanel, AnalysisRunRequestPanel, WorkflowCreationPanel } from "@/features/workflows/panels";
import type { WorkflowSnapshotOption } from "@/features/workflows/types";
import { AnalysisRunIndex, WorkflowList } from "@/features/workflows/workflow-list";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function WorkflowsPageLive({
  projectId,
  snapshotOptions,
  templateOptions,
}: {
  projectId: string;
  snapshotOptions: WorkflowSnapshotOption[];
  templateOptions: AnalysisTemplateRead[];
}) {
  const { projection } = useWorkspaceData();

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Workflows</p>
        <h1 className="mt-3 font-serif text-4xl text-strong">State-machine entry points</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
          Planning, workflow orchestration, and analysis run request stay split. The UI reflects the actual backend
          model instead of inventing an extra plan registry.
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <AnalysisPlanPanel projectId={projectId} snapshotOptions={snapshotOptions} />
        <WorkflowCreationPanel projectId={projectId} />
        <AnalysisRunRequestPanel
          projectId={projectId}
          snapshotOptions={snapshotOptions}
          templateOptions={templateOptions}
        />
      </section>

      <section className="space-y-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Workflow Index</p>
          <h2 className="mt-2 font-serif text-2xl text-strong">Workflow instances</h2>
        </div>
        <WorkflowList projectId={projectId} workflows={projection.workflows} />
      </section>

      <section className="space-y-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Analysis Runs</p>
          <h2 className="mt-2 font-serif text-2xl text-strong">Project lineage run index</h2>
        </div>
        <AnalysisRunIndex projectId={projectId} runs={projection.analysisRuns} />
      </section>
    </div>
  );
}

import { ErrorCard } from "@/components/status/error-card";
import { AnalysisPlanPanel, AnalysisRunRequestPanel, WorkflowCreationPanel } from "@/features/workflows/panels";
import { AnalysisRunIndex, WorkflowList } from "@/features/workflows/workflow-list";
import { getWorkflowsPageData } from "@/features/workflows/server";

export default async function WorkflowsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { analysisRuns, snapshots, templates, workflows } = await getWorkflowsPageData(projectId);

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
          <AnalysisPlanPanel projectId={projectId} snapshotOptions={snapshots} />
          <WorkflowCreationPanel projectId={projectId} />
          <AnalysisRunRequestPanel
            projectId={projectId}
            snapshotOptions={snapshots}
            templateOptions={templates}
          />
        </section>

        <section className="space-y-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Workflow Index</p>
            <h2 className="mt-2 font-serif text-2xl text-strong">Workflow instances</h2>
          </div>
          <WorkflowList projectId={projectId} workflows={workflows} />
        </section>

        <section className="space-y-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Analysis Runs</p>
            <h2 className="mt-2 font-serif text-2xl text-strong">Project lineage run index</h2>
          </div>
          <AnalysisRunIndex projectId={projectId} runs={analysisRuns} />
        </section>
      </div>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Workflows failed to load" />;
  }
}

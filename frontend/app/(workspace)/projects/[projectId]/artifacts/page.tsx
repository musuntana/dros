import { ErrorCard } from "@/components/status/error-card";
import { ArtifactCreationPanel } from "@/features/artifacts/artifact-panel";
import { ArtifactList } from "@/features/artifacts/artifact-list";
import { getArtifactsPageData } from "@/features/artifacts/server";

export default async function ArtifactsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { analysisRuns, artifacts } = await getArtifactsPageData(projectId);

    return (
      <div className="space-y-6">
        <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Artifacts</p>
          <h1 className="mt-3 font-serif text-4xl text-strong">Result objects and export payloads</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
            Artifacts are immutable object-storage references. They can feed assertion extraction, export output, or
            evidence attachment, but they are not narrative content by themselves.
          </p>
        </section>

        <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <ArtifactCreationPanel analysisRuns={analysisRuns} projectId={projectId} />
          <ArtifactList artifacts={artifacts} projectId={projectId} />
        </section>
      </div>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Artifacts failed to load" />;
  }
}

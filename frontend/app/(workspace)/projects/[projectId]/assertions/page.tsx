import { ErrorCard } from "@/components/status/error-card";
import { AssertionDetail } from "@/features/assertions/assertion-detail";
import { AssertionCreationPanel } from "@/features/assertions/assertion-panel";
import { AssertionList } from "@/features/assertions/assertion-list";
import { getAssertionsPageData } from "@/features/assertions/server";

export default async function AssertionsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { analysisRuns, artifacts, assertions } = await getAssertionsPageData(projectId);

    return (
      <div className="space-y-6">
        <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Assertions</p>
          <h1 className="mt-3 font-serif text-4xl text-strong">Verified claims before writing</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
            Assertions are the boundary between raw outputs and prose. This page keeps source object selection and
            derived claim creation explicit.
          </p>
        </section>

        <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <AssertionCreationPanel analysisRuns={analysisRuns} artifacts={artifacts} projectId={projectId} />
          <AssertionList assertions={assertions} projectId={projectId} />
        </section>
      </div>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Assertions failed to load" />;
  }
}

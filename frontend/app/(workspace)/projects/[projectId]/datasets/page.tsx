import { ErrorCard } from "@/components/status/error-card";
import { EmptyState } from "@/components/status/empty-state";
import { DatasetIntakePanel } from "@/features/datasets/dataset-intake-panel";
import { DatasetList } from "@/features/datasets/dataset-list";
import { getDatasetsPageData } from "@/features/datasets/server";

export default async function DatasetsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { datasets } = await getDatasetsPageData(projectId);

    return (
      <div className="space-y-6">
        <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Datasets</p>
          <h1 className="mt-3 font-serif text-4xl text-strong">Dataset intake and snapshot readiness</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
            This page keeps `dataset`, `dataset_snapshot`, and policy state visible before workflow execution. Upload
            intake now runs through the real `GatewayClient` sign-upload-complete flow instead of a placeholder
            `file_ref`.
          </p>
        </section>

        <DatasetIntakePanel projectId={projectId} />

        {datasets.length > 0 ? (
          <DatasetList datasets={datasets} />
        ) : (
          <EmptyState
            title="No dataset in this project"
            description="Register a public accession or upload a local file to create the first dataset and immutable dataset_snapshot."
          />
        )}
      </div>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Datasets failed to load" />;
  }
}

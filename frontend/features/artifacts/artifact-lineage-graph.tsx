"use client";

import type { ReactNode } from "react";
import Link from "next/link";

import { useWorkspaceData } from "@/features/projects/workspace-context";

function truncateId(value: string): string {
  return value.slice(0, 8);
}

export function ArtifactLineageGraph({
  artifactId,
  projectId,
}: {
  artifactId: string;
  projectId: string;
}) {
  const { projection } = useWorkspaceData();
  const artifact = projection.artifacts.find((item) => item.id === artifactId) ?? null;

  if (!artifact) {
    return (
      <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft" data-testid="artifact-lineage-graph">
        <p className="text-sm text-muted">Artifact lineage graph is unavailable because the artifact is not in the current workspace projection.</p>
      </section>
    );
  }

  const emittingRun = artifact.run_id ? projection.analysisRuns.find((item) => item.id === artifact.run_id) ?? null : null;
  const workflow = emittingRun?.workflow_instance_id
    ? projection.workflows.find((item) => item.id === emittingRun.workflow_instance_id) ?? null
    : null;
  const supersededFrom = projection.artifacts.find((item) => item.superseded_by === artifact.id) ?? null;

  // For figure/table artifacts, trace the "derives" edge back to the parent
  // result_json so users can see the full chain:
  //   figure/table → result_json → assertion → evidence → manuscript block
  const isFigureOrTable = artifact.artifact_type === "figure" || artifact.artifact_type === "table";
  const derivedFromEdges = projection.edges.filter(
    (edge) => edge.edge_type === "derives" && edge.to_id === artifact.id && edge.to_kind === "artifact",
  );
  const parentArtifacts = derivedFromEdges
    .map((edge) => projection.artifacts.find((a) => a.id === edge.from_id))
    .filter((a): a is NonNullable<typeof a> => a != null);
  const parentResultJson = parentArtifacts.find((a) => a.artifact_type === "result_json") ?? null;

  // Direct assertions on this artifact
  const directAssertions = projection.assertions.filter((item) => item.source_artifact_id === artifact.id);

  // When this is a figure/table derived from result_json, also include assertions
  // grounded on the parent result_json to surface the full evidence chain.
  const parentAssertions = parentResultJson
    ? projection.assertions.filter((item) => item.source_artifact_id === parentResultJson.id)
    : [];
  const allRelatedAssertionMap = new Map(
    [...directAssertions, ...parentAssertions].map((a) => [a.id, a]),
  );
  const relatedAssertions = [...allRelatedAssertionMap.values()];
  const relatedAssertionIds = new Set(relatedAssertions.map((item) => item.id));
  const relatedEvidenceLinks = projection.evidenceLinks.filter((item) => relatedAssertionIds.has(item.assertion_id));
  const evidenceCountByAssertion = new Map<string, number>();
  for (const link of relatedEvidenceLinks) {
    evidenceCountByAssertion.set(link.assertion_id, (evidenceCountByAssertion.get(link.assertion_id) ?? 0) + 1);
  }

  const consumingBlocks = projection.manuscriptBlocks.filter((block) =>
    (block.assertion_ids ?? []).some((assertionId) => relatedAssertionIds.has(assertionId)),
  );
  const manuscriptBlockCount = new Map<string, number>();
  for (const block of consumingBlocks) {
    manuscriptBlockCount.set(block.manuscript_id, (manuscriptBlockCount.get(block.manuscript_id) ?? 0) + 1);
  }
  const consumingManuscripts = projection.manuscripts.filter((manuscript) => manuscriptBlockCount.has(manuscript.id));
  // Derived children: artifacts that were derived from this artifact (e.g. result_json → figure/table)
  const derivedToEdges = projection.edges.filter(
    (edge) => edge.edge_type === "derives" && edge.from_id === artifact.id && edge.from_kind === "artifact",
  );
  const derivedChildren = derivedToEdges
    .map((edge) => projection.artifacts.find((a) => a.id === edge.to_id))
    .filter((a): a is NonNullable<typeof a> => a != null);

  const exportJobs = projection.exports.filter((job) => job.output_artifact_id === artifact.id);
  const sourceManuscripts = projection.manuscripts.filter((manuscript) =>
    exportJobs.some((job) => job.manuscript_id === manuscript.id),
  );

  return (
    <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft" data-testid="artifact-lineage-graph">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Lineage Graph</p>
          <h2 className="mt-2 font-serif text-2xl text-strong">Canonical object adjacency</h2>
        </div>
        <span className="rounded-pill border border-subtle bg-app px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-strong">
          live
        </span>
      </div>
      <div className="mt-5 grid gap-6 xl:grid-cols-3">
        <Column title="Upstream">
          {workflow ? (
            <GraphLink
              description={`${workflow.state} · ${workflow.current_step ?? "no current step"}`}
              href={`/projects/${projectId}/workflows/${workflow.id}`}
              label={`Workflow ${truncateId(workflow.id)}`}
            />
          ) : null}
          {emittingRun ? (
            <GraphLink
              description={`${emittingRun.state} · ${emittingRun.template_id}`}
              href={`/projects/${projectId}/analysis-runs/${emittingRun.id}`}
              label={`Run ${truncateId(emittingRun.id)}`}
            />
          ) : null}
          {parentResultJson ? (
            <GraphLink
              description={`Derives from ${parentResultJson.artifact_type}`}
              href={`/projects/${projectId}/artifacts/${parentResultJson.id}`}
              label={`Source ${parentResultJson.artifact_type} ${truncateId(parentResultJson.id)}`}
            />
          ) : null}
          {parentArtifacts
            .filter((a) => a.id !== parentResultJson?.id)
            .map((a) => (
              <GraphLink
                key={a.id}
                description={`Derives from ${a.artifact_type}`}
                href={`/projects/${projectId}/artifacts/${a.id}`}
                label={`Source ${a.artifact_type} ${truncateId(a.id)}`}
              />
            ))}
          {supersededFrom ? (
            <GraphLink
              description={`Superseded by current ${artifact.artifact_type}`}
              href={`/projects/${projectId}/artifacts/${supersededFrom.id}`}
              label={`Previous ${truncateId(supersededFrom.id)}`}
            />
          ) : null}
          {sourceManuscripts.map((manuscript) => (
            <GraphLink
              key={manuscript.id}
              description={`${manuscript.state} · version ${manuscript.current_version_no}`}
              href={`/projects/${projectId}/manuscripts/${manuscript.id}`}
              label={manuscript.title}
            />
          ))}
          {!workflow && !emittingRun && !supersededFrom && !parentResultJson && parentArtifacts.length === 0 && sourceManuscripts.length === 0 ? (
            <EmptyState text="No upstream workflow, run, or prior artifact is recorded." />
          ) : null}
        </Column>

        <Column title="Grounding">
          {directAssertions.map((assertion) => (
            <GraphLink
              key={assertion.id}
              description={`${assertion.state} · ${evidenceCountByAssertion.get(assertion.id) ?? 0} evidence link(s)`}
              href={`/projects/${projectId}/assertions/${assertion.id}`}
              label={`Assertion ${truncateId(assertion.id)}`}
            />
          ))}
          {isFigureOrTable && parentAssertions.length > 0 ? (
            <>
              {parentAssertions.slice(0, 3).map((assertion) => (
                <GraphLink
                  key={assertion.id}
                  description={`via result_json · ${assertion.state} · ${evidenceCountByAssertion.get(assertion.id) ?? 0} evidence link(s)`}
                  href={`/projects/${projectId}/assertions/${assertion.id}`}
                  label={`Inherited ${truncateId(assertion.id)}`}
                />
              ))}
              {parentAssertions.length > 3 ? (
                <GraphLink
                  description={`${parentAssertions.length - 3} more assertion(s) from parent result_json`}
                  href={`/projects/${projectId}/assertions`}
                  label="All assertions"
                />
              ) : null}
            </>
          ) : null}
          {relatedEvidenceLinks.length > 0 ? (
            <>
              {relatedEvidenceLinks.slice(0, 3).map((link) => (
                <GraphLink
                  key={link.id}
                  description={`${link.verifier_status} · confidence ${link.confidence?.toFixed(2) ?? "N/A"}`}
                  href={`/projects/${projectId}/evidence-links/${link.id}`}
                  label={`${link.relation_type} ${truncateId(link.id)}`}
                />
              ))}
              {relatedEvidenceLinks.length > 3 ? (
                <GraphLink
                  description={`${relatedEvidenceLinks.length - 3} more evidence link(s)`}
                  href={`/projects/${projectId}/evidence`}
                  label="Evidence Registry"
                />
              ) : null}
            </>
          ) : null}
          {relatedAssertions.length === 0 ? <EmptyState text="No assertion currently cites this artifact." /> : null}
        </Column>

        <Column title="Consumers">
          {derivedChildren.map((child) => (
            <GraphLink
              key={child.id}
              description={`Derived ${child.artifact_type}`}
              href={`/projects/${projectId}/artifacts/${child.id}`}
              label={`${child.artifact_type} ${truncateId(child.id)}`}
            />
          ))}
          {consumingManuscripts.map((manuscript) => (
            <GraphLink
              key={manuscript.id}
              description={`${manuscript.state} · ${manuscriptBlockCount.get(manuscript.id) ?? 0} block(s)`}
              href={`/projects/${projectId}/manuscripts/${manuscript.id}`}
              label={manuscript.title}
            />
          ))}
          {exportJobs.map((job) => (
            <GraphLink
              key={job.id}
              description={`${job.state} · ${job.format}`}
              href={`/projects/${projectId}/exports/${job.id}`}
              label={`Export ${truncateId(job.id)}`}
            />
          ))}
          {artifact.superseded_by ? (
            <GraphLink
              description="Replacement artifact on the same lineage branch"
              href={`/projects/${projectId}/artifacts/${artifact.superseded_by}`}
              label={`Replacement ${truncateId(artifact.superseded_by)}`}
            />
          ) : null}
          {derivedChildren.length === 0 && consumingManuscripts.length === 0 && exportJobs.length === 0 && !artifact.superseded_by ? (
            <EmptyState text="No downstream manuscript, export job, or replacement artifact is recorded." />
          ) : null}
        </Column>
      </div>
    </section>
  );
}

function Column({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <div className="space-y-3">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{title}</p>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function GraphLink({
  description,
  href,
  label,
}: {
  description: string;
  href: string;
  label: string;
}) {
  return (
    <Link
      className="block rounded-2xl border border-subtle bg-app px-4 py-4 transition hover:border-primary/20 hover:bg-primary/5"
      href={href}
    >
      <p className="text-sm font-semibold text-primary">{label}</p>
      <p className="mt-2 text-xs text-muted">{description}</p>
    </Link>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-2xl border border-dashed border-subtle bg-app px-4 py-4 text-sm text-muted">{text}</div>;
}

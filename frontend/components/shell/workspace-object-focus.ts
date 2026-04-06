import type {
  ArtifactRead,
  ManuscriptRead,
  ProjectDetailResponse,
} from "@/lib/api/generated/control-plane";
import type {
  InspectorAction,
  InspectorFocus,
  InspectorRelationItem,
} from "@/components/shell/inspector-panel";
import {
  getCurrentManuscriptReviews,
  type ProjectWorkspaceProjection,
  type WorkspaceStageKey,
} from "@/features/projects/workspace-projection";
import { buildEvidencePreview, summarizeEvidencePreview } from "@/features/evidence/evidence-preview";

export type WorkspaceRouteObjectKind = "artifact" | "assertion" | "analysisRun" | "evidenceLink" | "exportJob" | "manuscript" | "workflow";

export interface WorkspaceRouteObject {
  id: string;
  kind: WorkspaceRouteObjectKind;
}

function truncateId(value: string | null | undefined): string {
  if (!value) {
    return "none";
  }

  return value.slice(0, 8);
}

function formatCount(value: number, noun: string): string {
  return `${value} ${noun}${value === 1 ? "" : "s"}`;
}

function pushAction(actions: InspectorAction[], href: string, label: string) {
  if (actions.some((action) => action.href === href && action.label === label)) {
    return;
  }

  actions.push({ href, label });
}

function appendOverflowItem(
  items: InspectorRelationItem[],
  total: number,
  visibleCount: number,
  href: string,
  label: string,
) {
  if (total <= visibleCount) {
    return;
  }

  items.push({
    href,
    label,
    meta: `${total - visibleCount} more`,
  });
}

function buildArtifactHref(projectId: string, artifactId: string) {
  return `/projects/${projectId}/artifacts/${artifactId}`;
}

function buildAssertionHref(projectId: string, assertionId: string) {
  return `/projects/${projectId}/assertions/${assertionId}`;
}

function buildAnalysisRunHref(projectId: string, runId: string) {
  return `/projects/${projectId}/analysis-runs/${runId}`;
}

function buildWorkflowHref(projectId: string, workflowId: string) {
  return `/projects/${projectId}/workflows/${workflowId}`;
}

function buildManuscriptHref(projectId: string, manuscriptId: string) {
  return `/projects/${projectId}/manuscripts/${manuscriptId}`;
}

function buildEvidenceLinkHref(projectId: string, linkId: string) {
  return `/projects/${projectId}/evidence-links/${linkId}`;
}

function buildExportJobHref(projectId: string, exportJobId: string) {
  return `/projects/${projectId}/exports/${exportJobId}`;
}

function classifyArtifactStage(artifact: ArtifactRead): WorkspaceStageKey {
  if (artifact.artifact_type === "docx" || artifact.artifact_type === "pdf" || artifact.artifact_type === "zip") {
    return "export";
  }

  if (artifact.artifact_type === "evidence_attachment") {
    return "grounding";
  }

  return "analysis";
}

function buildManuscriptItems(
  projectId: string,
  manuscriptIds: string[],
  manuscripts: ManuscriptRead[],
  blockCountsByManuscript: Map<string, number>,
  visibleCount = 3,
): InspectorRelationItem[] {
  const visible = manuscriptIds.slice(0, visibleCount).map((manuscriptId) => {
    const manuscript = manuscripts.find((candidate) => candidate.id === manuscriptId) ?? null;
    return {
      href: buildManuscriptHref(projectId, manuscriptId),
      label: manuscript?.title ?? `Manuscript ${truncateId(manuscriptId)}`,
      meta: `${blockCountsByManuscript.get(manuscriptId) ?? 0} block(s)`,
    };
  });

  appendOverflowItem(
    visible,
    manuscriptIds.length,
    visibleCount,
    `/projects/${projectId}/manuscripts`,
    "All manuscripts",
  );
  return visible;
}

export function parseWorkspaceRouteObject(pathname: string, projectId: string): WorkspaceRouteObject | null {
  const prefix = `/projects/${projectId}`;
  if (!pathname.startsWith(prefix)) {
    return null;
  }

  const segments = pathname
    .slice(prefix.length)
    .split("/")
    .filter((segment) => segment.length > 0);

  if (segments.length < 2) {
    return null;
  }

  if (segments[0] === "artifacts") {
    return { id: segments[1], kind: "artifact" };
  }

  if (segments[0] === "assertions") {
    return { id: segments[1], kind: "assertion" };
  }

  if (segments[0] === "analysis-runs") {
    return { id: segments[1], kind: "analysisRun" };
  }

  if (segments[0] === "evidence-links") {
    return { id: segments[1], kind: "evidenceLink" };
  }

  if (segments[0] === "exports") {
    return { id: segments[1], kind: "exportJob" };
  }

  if (segments[0] === "workflows") {
    return { id: segments[1], kind: "workflow" };
  }

  if (segments[0] === "manuscripts") {
    return { id: segments[1], kind: "manuscript" };
  }

  return null;
}

export function classifyWorkspaceRouteStage(
  routeObject: WorkspaceRouteObject | null,
  projection: ProjectWorkspaceProjection,
): WorkspaceStageKey | null {
  if (!routeObject) {
    return null;
  }

  if (routeObject.kind === "workflow") {
    return "workflow";
  }

  if (routeObject.kind === "analysisRun") {
    return "analysis";
  }

  if (routeObject.kind === "assertion" || routeObject.kind === "evidenceLink") {
    return "grounding";
  }

  if (routeObject.kind === "manuscript") {
    return "review";
  }

  if (routeObject.kind === "exportJob") {
    return "export";
  }

  const artifact = projection.artifacts.find((candidate) => candidate.id === routeObject.id);
  return artifact ? classifyArtifactStage(artifact) : "analysis";
}

function buildArtifactFocus({
  projectId,
  projection,
  routeObject,
}: {
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject;
}): InspectorFocus | null {
  const artifact = projection.artifacts.find((candidate) => candidate.id === routeObject.id);
  if (!artifact) {
    return null;
  }

  const emittingRun = artifact.run_id
    ? projection.analysisRuns.find((run) => run.id === artifact.run_id) ?? null
    : null;
  const workflow = emittingRun?.workflow_instance_id
    ? projection.workflows.find((candidate) => candidate.id === emittingRun.workflow_instance_id) ?? null
    : null;
  const relatedAssertions = projection.assertions.filter((assertion) => assertion.source_artifact_id === artifact.id);
  const relatedAssertionIds = new Set(relatedAssertions.map((assertion) => assertion.id));
  const relatedEvidence = projection.evidenceLinks.filter((link) => relatedAssertionIds.has(link.assertion_id));
  const consumingBlocks = projection.manuscriptBlocks.filter((block) =>
    (block.assertion_ids ?? []).some((assertionId) => relatedAssertionIds.has(assertionId)),
  );
  const blockCountsByManuscript = new Map<string, number>();
  for (const block of consumingBlocks) {
    blockCountsByManuscript.set(block.manuscript_id, (blockCountsByManuscript.get(block.manuscript_id) ?? 0) + 1);
  }
  const manuscriptIds = [...new Set(consumingBlocks.map((block) => block.manuscript_id))];
  const exportJobs = projection.exports.filter((job) => job.output_artifact_id === artifact.id);
  const sourceManuscripts = projection.manuscripts.filter((manuscript) =>
    exportJobs.some((job) => job.manuscript_id === manuscript.id),
  );
  const replacementArtifact = artifact.superseded_by
    ? projection.artifacts.find((candidate) => candidate.id === artifact.superseded_by) ?? null
    : null;

  const sourceItems: InspectorRelationItem[] = [];
  if (emittingRun) {
    sourceItems.push({
      href: buildAnalysisRunHref(projectId, emittingRun.id),
      label: `Run ${truncateId(emittingRun.id)}`,
      meta: `${emittingRun.state} · ${emittingRun.template_id}`,
    });
  }
  if (workflow) {
    sourceItems.push({
      href: buildWorkflowHref(projectId, workflow.id),
      label: `Workflow ${truncateId(workflow.id)}`,
      meta: `${workflow.state} · ${workflow.current_step ?? "no current step"}`,
    });
  }
  sourceItems.push(
    ...sourceManuscripts.map((manuscript) => ({
      href: buildManuscriptHref(projectId, manuscript.id),
      label: manuscript.title,
      meta: `${manuscript.state} · v${manuscript.current_version_no}`,
    })),
  );

  const groundingItems = relatedAssertions.slice(0, 3).map((assertion) => ({
    href: buildAssertionHref(projectId, assertion.id),
    label: `Assertion ${truncateId(assertion.id)}`,
    meta: `${assertion.state} · ${assertion.assertion_type}`,
  }));
  appendOverflowItem(groundingItems, relatedAssertions.length, 3, `/projects/${projectId}/assertions`, "All assertions");
  if (relatedEvidence.length > 0) {
    groundingItems.push({
      href: `/projects/${projectId}/evidence`,
      label: "Evidence registry",
      meta: `${formatCount(relatedEvidence.length, "evidence link")}`,
    });
  }

  const consumerItems = buildManuscriptItems(
    projectId,
    manuscriptIds,
    projection.manuscripts,
    blockCountsByManuscript,
  );
  if (replacementArtifact) {
    consumerItems.push({
      href: buildArtifactHref(projectId, replacementArtifact.id),
      label: `Replacement ${truncateId(replacementArtifact.id)}`,
      meta: replacementArtifact.artifact_type,
    });
  }
  if (exportJobs.length > 0) {
    consumerItems.push(
      ...exportJobs.slice(0, 2).map((job) => ({
        href: buildExportJobHref(projectId, job.id),
        label: `Export ${truncateId(job.id)}`,
        meta: `${job.state} · ${job.format}`,
      })),
    );
    appendOverflowItem(consumerItems, exportJobs.length, 2, `/projects/${projectId}/exports`, "All exports");
  }

  const actions: InspectorAction[] = [];
  pushAction(actions, `/projects/${projectId}/artifacts`, "Artifacts");
  if (emittingRun) {
    pushAction(actions, buildAnalysisRunHref(projectId, emittingRun.id), "Open analysis run");
  }
  if (relatedAssertions.length > 0) {
    pushAction(actions, buildAssertionHref(projectId, relatedAssertions[0].id), "Open first assertion");
  } else {
    pushAction(actions, `/projects/${projectId}/assertions`, "Assertions");
  }

  return {
    actions,
    eyebrow: "Current Object",
    id: `route:artifact:${artifact.id}`,
    items: [
      { label: "Artifact Type", value: artifact.artifact_type },
      { label: "Run", value: artifact.run_id ?? "Manual registration" },
      { label: "SHA256", value: artifact.sha256 },
      { label: "Storage", value: artifact.storage_uri },
      { label: "Size", value: artifact.size_bytes?.toString() ?? "Unknown" },
    ],
    payload: {
      metadata_json: artifact.metadata_json,
      superseded_by: artifact.superseded_by,
    },
    relations: [
      {
        empty: "No upstream workflow or analysis run is recorded for this artifact.",
        items: sourceItems,
        title: "Upstream",
      },
      {
        empty: "No assertion currently cites this artifact.",
        items: groundingItems,
        title: "Grounding",
      },
      {
        empty: "No manuscript or export currently consumes this artifact.",
        items: consumerItems,
        title: "Consumers",
      },
    ],
    summary: `${formatCount(relatedAssertions.length, "assertion")}, ${formatCount(relatedEvidence.length, "evidence link")} and ${formatCount(consumingBlocks.length, "manuscript block")} currently depend on this artifact.`,
    title: `Artifact ${artifact.artifact_type}`,
  };
}

function buildAssertionFocus({
  projectId,
  projection,
  routeObject,
}: {
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject;
}): InspectorFocus | null {
  const assertion = projection.assertions.find((candidate) => candidate.id === routeObject.id);
  if (!assertion) {
    return null;
  }

  const sourceArtifact = assertion.source_artifact_id
    ? projection.artifacts.find((candidate) => candidate.id === assertion.source_artifact_id) ?? null
    : null;
  const sourceRunId = assertion.source_run_id ?? sourceArtifact?.run_id ?? null;
  const sourceRun = sourceRunId
    ? projection.analysisRuns.find((candidate) => candidate.id === sourceRunId) ?? null
    : null;
  const evidenceLinks = projection.evidenceLinks.filter((link) => link.assertion_id === assertion.id);
  const consumingBlocks = projection.manuscriptBlocks.filter((block) => (block.assertion_ids ?? []).includes(assertion.id));
  const blockCountsByManuscript = new Map<string, number>();
  for (const block of consumingBlocks) {
    blockCountsByManuscript.set(block.manuscript_id, (blockCountsByManuscript.get(block.manuscript_id) ?? 0) + 1);
  }
  const manuscriptIds = [...new Set(consumingBlocks.map((block) => block.manuscript_id))];

  const sourceItems: InspectorRelationItem[] = [];
  if (sourceArtifact) {
    sourceItems.push({
      href: buildArtifactHref(projectId, sourceArtifact.id),
      label: `Artifact ${truncateId(sourceArtifact.id)}`,
      meta: sourceArtifact.artifact_type,
    });
  }
  if (sourceRun) {
    sourceItems.push({
      href: buildAnalysisRunHref(projectId, sourceRun.id),
      label: `Run ${truncateId(sourceRun.id)}`,
      meta: `${sourceRun.state} · ${sourceRun.template_id}`,
    });
  }

  const evidenceItems: InspectorRelationItem[] = evidenceLinks.slice(0, 3).map((link) => ({
    href: buildEvidenceLinkHref(projectId, link.id),
    label: `${link.relation_type} ${truncateId(link.id)}`,
    meta: link.verifier_status,
  }));
  appendOverflowItem(evidenceItems, evidenceLinks.length, 3, `/projects/${projectId}/evidence`, "Evidence registry");

  const consumerItems = buildManuscriptItems(
    projectId,
    manuscriptIds,
    projection.manuscripts,
    blockCountsByManuscript,
  );

  const actions: InspectorAction[] = [];
  pushAction(actions, `/projects/${projectId}/assertions`, "Assertions");
  if (sourceArtifact) {
    pushAction(actions, buildArtifactHref(projectId, sourceArtifact.id), "Source artifact");
  }
  if (evidenceLinks.length > 0) {
    pushAction(actions, `/projects/${projectId}/evidence`, "Evidence");
  }

  return {
    actions,
    eyebrow: "Current Object",
    id: `route:assertion:${assertion.id}`,
    items: [
      { label: "Assertion Type", value: assertion.assertion_type },
      { label: "State", value: assertion.state },
      { label: "Claim Hash", value: assertion.claim_hash },
      { label: "Source Artifact", value: assertion.source_artifact_id ?? "None" },
      { label: "Source Run", value: sourceRunId ?? "None" },
    ],
    payload: {
      numeric_payload_json: assertion.numeric_payload_json,
      source_span_json: assertion.source_span_json,
      text_norm: assertion.text_norm,
    },
    relations: [
      {
        empty: "No upstream artifact or analysis run is recorded for this assertion.",
        items: sourceItems,
        title: "Sources",
      },
      {
        empty: "No evidence link is attached to this assertion.",
        items: evidenceItems,
        title: "Evidence",
      },
      {
        empty: "No manuscript block currently consumes this assertion.",
        items: consumerItems,
        title: "Consumption",
      },
    ],
    summary: `${formatCount(evidenceLinks.length, "evidence link")} and ${formatCount(consumingBlocks.length, "manuscript block")} currently consume this assertion.`,
    title: `Assertion ${assertion.assertion_type}`,
  };
}

function buildAnalysisRunFocus({
  projectId,
  projection,
  routeObject,
}: {
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject;
}): InspectorFocus | null {
  const run = projection.analysisRuns.find((candidate) => candidate.id === routeObject.id);
  if (!run) {
    return null;
  }

  const workflow = run.workflow_instance_id
    ? projection.workflows.find((candidate) => candidate.id === run.workflow_instance_id) ?? null
    : null;
  const emittedArtifacts = projection.artifacts.filter((artifact) => artifact.run_id === run.id);
  const emittedArtifactIds = new Set(emittedArtifacts.map((artifact) => artifact.id));
  const derivedAssertions = projection.assertions.filter(
    (assertion) => assertion.source_run_id === run.id || (assertion.source_artifact_id ? emittedArtifactIds.has(assertion.source_artifact_id) : false),
  );

  const orchestrationItems: InspectorRelationItem[] = [];
  if (workflow) {
    orchestrationItems.push({
      href: buildWorkflowHref(projectId, workflow.id),
      label: `Workflow ${truncateId(workflow.id)}`,
      meta: `${workflow.state} · ${workflow.current_step ?? "no current step"}`,
    });
  }
  orchestrationItems.push({
    href: `/projects/${projectId}/datasets`,
    label: "Snapshot registry",
    meta: `snapshot ${truncateId(run.snapshot_id)}`,
  });

  const outputItems = emittedArtifacts.slice(0, 4).map((artifact) => ({
    href: buildArtifactHref(projectId, artifact.id),
    label: `Artifact ${truncateId(artifact.id)}`,
    meta: artifact.artifact_type,
  }));
  appendOverflowItem(outputItems, emittedArtifacts.length, 4, `/projects/${projectId}/artifacts`, "All artifacts");

  const groundingItems = derivedAssertions.slice(0, 4).map((assertion) => ({
    href: buildAssertionHref(projectId, assertion.id),
    label: `Assertion ${truncateId(assertion.id)}`,
    meta: `${assertion.state} · ${assertion.assertion_type}`,
  }));
  appendOverflowItem(groundingItems, derivedAssertions.length, 4, `/projects/${projectId}/assertions`, "All assertions");

  const actions: InspectorAction[] = [];
  pushAction(actions, `/projects/${projectId}/workflows`, "Workflows");
  if (workflow) {
    pushAction(actions, buildWorkflowHref(projectId, workflow.id), "Open workflow");
  }
  pushAction(actions, `/projects/${projectId}/artifacts`, "Artifacts");

  return {
    actions,
    eyebrow: "Current Object",
    id: `route:analysis-run:${run.id}`,
    items: [
      { label: "State", value: run.state },
      { label: "Template", value: run.template_id },
      { label: "Snapshot", value: run.snapshot_id },
      { label: "Workflow", value: run.workflow_instance_id ?? "Standalone" },
      { label: "Image Digest", value: run.container_image_digest },
    ],
    payload: {
      params_json: run.params_json,
      runtime_manifest_json: run.runtime_manifest_json,
    },
    relations: [
      {
        empty: "No workflow or snapshot registry is attached to this run.",
        items: orchestrationItems,
        title: "Orchestration",
      },
      {
        empty: "No artifact has been emitted by this run yet.",
        items: outputItems,
        title: "Outputs",
      },
      {
        empty: "No assertion has been grounded from this run yet.",
        items: groundingItems,
        title: "Grounding",
      },
    ],
    summary: `This run is ${run.state} on template ${run.template_id} and has emitted ${formatCount(emittedArtifacts.length, "artifact")}.`,
    title: "Analysis Run",
  };
}

function buildWorkflowFocus({
  projectId,
  projection,
  routeObject,
}: {
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject;
}): InspectorFocus | null {
  const workflow = projection.workflows.find((candidate) => candidate.id === routeObject.id);
  if (!workflow) {
    return null;
  }

  const parentWorkflow = workflow.parent_workflow_id
    ? projection.workflows.find((candidate) => candidate.id === workflow.parent_workflow_id) ?? null
    : null;
  const relatedRuns = projection.analysisRuns.filter((run) => run.workflow_instance_id === workflow.id);
  const relatedRunIds = new Set(relatedRuns.map((run) => run.id));
  const relatedArtifacts = projection.artifacts.filter((artifact) => (artifact.run_id ? relatedRunIds.has(artifact.run_id) : false));

  const lineageItems: InspectorRelationItem[] = [];
  if (parentWorkflow) {
    lineageItems.push({
      href: buildWorkflowHref(projectId, parentWorkflow.id),
      label: `Parent ${truncateId(parentWorkflow.id)}`,
      meta: `${parentWorkflow.state} · ${parentWorkflow.workflow_type}`,
    });
  }

  const executionItems = relatedRuns.slice(0, 4).map((run) => ({
    href: buildAnalysisRunHref(projectId, run.id),
    label: `Run ${truncateId(run.id)}`,
    meta: `${run.state} · ${run.template_id}`,
  }));
  appendOverflowItem(executionItems, relatedRuns.length, 4, `/projects/${projectId}/workflows`, "All runs");

  const outputItems = relatedArtifacts.slice(0, 4).map((artifact) => ({
    href: buildArtifactHref(projectId, artifact.id),
    label: `Artifact ${truncateId(artifact.id)}`,
    meta: artifact.artifact_type,
  }));
  appendOverflowItem(outputItems, relatedArtifacts.length, 4, `/projects/${projectId}/artifacts`, "All artifacts");

  const actions: InspectorAction[] = [];
  pushAction(actions, `/projects/${projectId}/workflows`, "Workflows");
  pushAction(actions, `/projects/${projectId}/artifacts`, "Artifacts");
  if (relatedRuns.length > 0) {
    pushAction(actions, buildAnalysisRunHref(projectId, relatedRuns[0].id), "Open latest run");
  }

  return {
    actions,
    eyebrow: "Current Object",
    id: `route:workflow:${workflow.id}`,
    items: [
      { label: "Workflow Type", value: workflow.workflow_type },
      { label: "State", value: workflow.state },
      { label: "Current Step", value: workflow.current_step ?? "Unrecorded" },
      { label: "Backend", value: workflow.runtime_backend },
      { label: "Parent", value: workflow.parent_workflow_id ?? "None" },
    ],
    payload: {
      started_by: workflow.started_by,
      started_at: workflow.started_at,
    },
    relations: [
      {
        empty: "No parent workflow lineage is recorded for this branch.",
        items: lineageItems,
        title: "Lineage",
      },
      {
        empty: "No analysis run has started from this workflow yet.",
        items: executionItems,
        title: "Execution",
      },
      {
        empty: "No artifact has been produced by runs attached to this workflow.",
        items: outputItems,
        title: "Outputs",
      },
    ],
    summary: `${formatCount(relatedRuns.length, "analysis run")} and ${formatCount(relatedArtifacts.length, "artifact")} currently hang off this workflow branch.`,
    title: "Workflow",
  };
}

function buildManuscriptFocus({
  detail,
  projectId,
  projection,
  routeObject,
}: {
  detail: ProjectDetailResponse;
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject;
}): InspectorFocus | null {
  const manuscript =
    projection.manuscripts.find((candidate) => candidate.id === routeObject.id) ??
    (detail.active_manuscript?.id === routeObject.id ? detail.active_manuscript : null);
  if (!manuscript) {
    return null;
  }

  const blocks = projection.manuscriptBlocks.filter(
    (block) => block.manuscript_id === manuscript.id && block.version_no === manuscript.current_version_no,
  );
  const assertionIds = [...new Set(blocks.flatMap((block) => block.assertion_ids ?? []))];
  const assertions = projection.assertions.filter((assertion) => assertionIds.includes(assertion.id));
  const reviews = getCurrentManuscriptReviews(manuscript, projection.reviews, projection.manuscriptBlocks);
  const exports = projection.exports.filter((job) => job.manuscript_id === manuscript.id);

  const groundingItems = assertions.slice(0, 4).map((assertion) => ({
    href: buildAssertionHref(projectId, assertion.id),
    label: `Assertion ${truncateId(assertion.id)}`,
    meta: `${assertion.state} · ${assertion.assertion_type}`,
  }));
  appendOverflowItem(groundingItems, assertions.length, 4, `/projects/${projectId}/assertions`, "All assertions");

  const reviewItems: InspectorRelationItem[] = [];
  if (reviews.length > 0) {
    reviewItems.push({
      href: `/projects/${projectId}/reviews`,
      label: "Review queue",
      meta: `${formatCount(reviews.length, "review")}`,
    });
  }

  const deliveryItems: InspectorRelationItem[] = [];
  if (exports.length > 0) {
    deliveryItems.push(
      ...exports.slice(0, 3).map((job) => ({
        href: buildExportJobHref(projectId, job.id),
        label: `Export ${truncateId(job.id)}`,
        meta: `${job.state} · ${job.format}`,
      })),
    );
    appendOverflowItem(deliveryItems, exports.length, 3, `/projects/${projectId}/exports`, "All exports");
  }

  const actions: InspectorAction[] = [];
  pushAction(actions, `/projects/${projectId}/manuscripts`, "Manuscripts");
  pushAction(actions, `/projects/${projectId}/reviews`, "Reviews");
  pushAction(actions, `/projects/${projectId}/exports`, "Exports");

  return {
    actions,
    eyebrow: "Current Object",
    id: `route:manuscript:${manuscript.id}`,
    items: [
      { label: "State", value: manuscript.state },
      { label: "Version", value: manuscript.current_version_no.toString() },
      { label: "Type", value: manuscript.manuscript_type },
      { label: "Target Journal", value: manuscript.target_journal ?? "Unassigned" },
      { label: "Title", value: manuscript.title },
    ],
    payload: {
      style_profile_json: manuscript.style_profile_json,
    },
    relations: [
      {
        empty: "No assertion-backed block is currently attached to this manuscript.",
        items: groundingItems,
        title: "Grounding",
      },
      {
        empty: "No review currently targets this manuscript.",
        items: reviewItems,
        title: "Review Gate",
      },
      {
        empty: "No export job has been requested for this manuscript.",
        items: deliveryItems,
        title: "Delivery",
      },
    ],
    summary: `${formatCount(blocks.length, "block")}, ${formatCount(assertions.length, "assertion")} and ${formatCount(exports.length, "export job")} currently attach to this manuscript.`,
    title: "Manuscript",
  };
}

function buildEvidenceLinkFocus({
  projectId,
  projection,
  routeObject,
}: {
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject;
}): InspectorFocus | null {
  const link = projection.evidenceLinks.find((candidate) => candidate.id === routeObject.id);
  if (!link) {
    return null;
  }

  const assertion = projection.assertions.find((candidate) => candidate.id === link.assertion_id) ?? null;
  const evidenceSource = projection.evidenceSources.find((candidate) => candidate.id === link.evidence_source_id) ?? null;
  const preview = evidenceSource ? buildEvidencePreview(link, evidenceSource) : null;
  const previewSummary = preview ? summarizeEvidencePreview(preview) : null;
  const previewItemLabel = preview?.highlightText ? "Quoted Span" : "Source Preview";
  const sourceArtifact = assertion?.source_artifact_id
    ? projection.artifacts.find((candidate) => candidate.id === assertion.source_artifact_id) ?? null
    : null;
  const consumingBlocks = assertion
    ? projection.manuscriptBlocks.filter((block) => (block.assertion_ids ?? []).includes(assertion.id))
    : [];
  const blockCountsByManuscript = new Map<string, number>();
  for (const block of consumingBlocks) {
    blockCountsByManuscript.set(block.manuscript_id, (blockCountsByManuscript.get(block.manuscript_id) ?? 0) + 1);
  }
  const manuscriptIds = [...new Set(consumingBlocks.map((block) => block.manuscript_id))];

  const upstreamItems: InspectorRelationItem[] = [];
  if (assertion) {
    upstreamItems.push({
      href: buildAssertionHref(projectId, assertion.id),
      label: `Assertion ${truncateId(assertion.id)}`,
      meta: `${assertion.state} · ${assertion.assertion_type}`,
    });
  }
  if (sourceArtifact) {
    upstreamItems.push({
      href: buildArtifactHref(projectId, sourceArtifact.id),
      label: `Artifact ${truncateId(sourceArtifact.id)}`,
      meta: sourceArtifact.artifact_type,
    });
  }

  const sourceItems: InspectorRelationItem[] = [
    {
      href: `/projects/${projectId}/evidence`,
      label: evidenceSource?.title ?? `Source ${truncateId(link.evidence_source_id)}`,
      meta: [
        evidenceSource?.source_type,
        evidenceSource?.license_class,
        link.source_chunk_id ? `chunk ${truncateId(link.source_chunk_id)}` : "full source",
      ]
        .filter(Boolean)
        .join(" · "),
    },
  ];

  const consumerItems = buildManuscriptItems(
    projectId,
    manuscriptIds,
    projection.manuscripts,
    blockCountsByManuscript,
  );

  const actions: InspectorAction[] = [];
  pushAction(actions, buildEvidenceLinkHref(projectId, link.id), "Evidence link detail");
  pushAction(actions, `/projects/${projectId}/evidence`, "Evidence registry");
  if (assertion) {
    pushAction(actions, buildAssertionHref(projectId, assertion.id), "Open assertion");
  }

  return {
    actions,
    eyebrow: "Current Object",
    id: `route:evidence-link:${link.id}`,
    items: [
      { label: "Relation Type", value: link.relation_type },
      { label: "Verifier Status", value: link.verifier_status },
      { label: "Confidence", value: link.confidence?.toString() ?? "N/A" },
      { label: "Assertion", value: link.assertion_id },
      { label: "Source", value: evidenceSource?.title ?? link.evidence_source_id },
      ...(previewSummary ? [{ label: previewItemLabel, value: previewSummary }] : []),
    ],
    payload: {
      excerpt_hash: link.excerpt_hash,
      source_chunk_id: link.source_chunk_id,
      source_span_end: link.source_span_end,
      source_span_start: link.source_span_start,
    },
    relations: [
      {
        empty: "No upstream assertion could be resolved for this evidence link.",
        items: upstreamItems,
        title: "Upstream",
      },
      {
        empty: "Evidence source could not be resolved in the current projection.",
        items: sourceItems,
        title: "Evidence Source",
      },
      {
        empty: "No manuscript block currently consumes the linked assertion.",
        items: consumerItems,
        title: "Consumers",
      },
    ],
    summary: previewSummary
      ? `Evidence link ${link.relation_type} with verifier status ${link.verifier_status}. ${previewSummary}`
      : `Evidence link ${link.relation_type} with verifier status ${link.verifier_status}.`,
    title: "Evidence Link",
  };
}

function buildExportJobFocus({
  projectId,
  projection,
  routeObject,
}: {
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject;
}): InspectorFocus | null {
  const exportJob = projection.exports.find((candidate) => candidate.id === routeObject.id);
  if (!exportJob) {
    return null;
  }

  const manuscript = projection.manuscripts.find((candidate) => candidate.id === exportJob.manuscript_id) ?? null;
  const outputArtifact = exportJob.output_artifact_id
    ? projection.artifacts.find((candidate) => candidate.id === exportJob.output_artifact_id) ?? null
    : null;

  const sourceItems: InspectorRelationItem[] = manuscript
    ? [
        {
          href: buildManuscriptHref(projectId, manuscript.id),
          label: manuscript.title,
          meta: `${manuscript.state} · v${manuscript.current_version_no}`,
        },
      ]
    : [];
  const deliveryItems: InspectorRelationItem[] = outputArtifact
    ? [
        {
          href: buildArtifactHref(projectId, outputArtifact.id),
          label: `Artifact ${truncateId(outputArtifact.id)}`,
          meta: outputArtifact.artifact_type,
        },
      ]
    : [];

  const actions: InspectorAction[] = [];
  pushAction(actions, `/projects/${projectId}/exports`, "Exports");
  if (manuscript) {
    pushAction(actions, buildManuscriptHref(projectId, manuscript.id), "Open manuscript");
  }
  if (outputArtifact) {
    pushAction(actions, buildArtifactHref(projectId, outputArtifact.id), "Open output artifact");
  }
  pushAction(actions, `/projects/${projectId}/audit`, "Audit trail");

  return {
    actions,
    eyebrow: "Current Object",
    id: `route:export-job:${exportJob.id}`,
    items: [
      { label: "State", value: exportJob.state },
      { label: "Format", value: exportJob.format },
      { label: "Requested", value: exportJob.requested_at },
      { label: "Manuscript", value: exportJob.manuscript_id },
      { label: "Output Artifact", value: exportJob.output_artifact_id ?? "None" },
    ],
    payload: {
      completed_at: exportJob.completed_at,
      requested_by: exportJob.requested_by,
    },
    relations: [
      {
        empty: "No manuscript source could be resolved for this export job.",
        items: sourceItems,
        title: "Source",
      },
      {
        empty: "This export job has not produced an output artifact yet.",
        items: deliveryItems,
        title: "Output",
      },
    ],
    summary: `Export job ${truncateId(exportJob.id)} is ${exportJob.state} in ${exportJob.format} format.`,
    title: "Export Job",
  };
}

export function buildWorkspaceRouteFocus({
  detail,
  projectId,
  projection,
  routeObject,
}: {
  detail: ProjectDetailResponse;
  projectId: string;
  projection: ProjectWorkspaceProjection;
  routeObject: WorkspaceRouteObject | null;
}): InspectorFocus | null {
  if (!routeObject) {
    return null;
  }

  if (routeObject.kind === "artifact") {
    return buildArtifactFocus({ projectId, projection, routeObject });
  }

  if (routeObject.kind === "assertion") {
    return buildAssertionFocus({ projectId, projection, routeObject });
  }

  if (routeObject.kind === "analysisRun") {
    return buildAnalysisRunFocus({ projectId, projection, routeObject });
  }

  if (routeObject.kind === "evidenceLink") {
    return buildEvidenceLinkFocus({ projectId, projection, routeObject });
  }

  if (routeObject.kind === "workflow") {
    return buildWorkflowFocus({ projectId, projection, routeObject });
  }

  if (routeObject.kind === "exportJob") {
    return buildExportJobFocus({ projectId, projection, routeObject });
  }

  return buildManuscriptFocus({ detail, projectId, projection, routeObject });
}

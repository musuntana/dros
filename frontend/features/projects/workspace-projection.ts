import type {
  AnalysisRunRead,
  ArtifactRead,
  AssertionRead,
  EvidenceLinkRead,
  EvidenceSourceRead,
  ExportJobRead,
  LineageEdgeRead,
  ManuscriptBlockRead,
  ManuscriptRead,
  ProjectDetailResponse,
  ReviewRead,
  WorkflowInstanceRead,
} from "@/lib/api/generated/control-plane";
import type { ProjectEvent } from "@/lib/api/gateway";

export type WorkspaceStageKey =
  | "intake"
  | "workflow"
  | "analysis"
  | "grounding"
  | "review"
  | "export";

export interface WorkspaceStageMetric {
  label: string;
  value: string;
}

export interface WorkspaceStageLink {
  href: string;
  label: string;
}

export interface WorkspaceStage {
  actions: WorkspaceStageLink[];
  description: string;
  details: Record<string, unknown>;
  eyebrow: string;
  key: WorkspaceStageKey;
  metrics: WorkspaceStageMetric[];
  status: string;
  step: number;
  summary: string;
  title: string;
  updatedAt?: string | null;
}

export interface ProjectWorkspaceProjection {
  analysisRuns: AnalysisRunRead[];
  artifacts: ArtifactRead[];
  assertions: AssertionRead[];
  edges: LineageEdgeRead[];
  evidenceLinks: EvidenceLinkRead[];
  evidenceSources: EvidenceSourceRead[];
  exports: ExportJobRead[];
  manuscriptBlocks: ManuscriptBlockRead[];
  manuscripts: ManuscriptRead[];
  reviews: ReviewRead[];
  workflows: WorkflowInstanceRead[];
}

const STAGE_ORDER: WorkspaceStageKey[] = ["intake", "workflow", "analysis", "grounding", "review", "export"];

function countBy<T>(items: T[], toKey: (item: T) => string): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const item of items) {
    const key = toKey(item);
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

function firstDefined<T>(...values: Array<T | null | undefined>): T | null {
  for (const value of values) {
    if (value !== undefined && value !== null) {
      return value;
    }
  }
  return null;
}

function formatCount(value: number, noun: string): string {
  return `${value} ${noun}${value === 1 ? "" : "s"}`;
}

function joinCountSummary(counts: Record<string, number>): string {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return "none";
  }

  return entries
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}:${value}`)
    .join(" · ");
}

function pushAction(actions: WorkspaceStageLink[], href: string | null, label: string) {
  if (!href || actions.some((action) => action.href === href)) {
    return;
  }
  actions.push({ href, label });
}

function earliestDate(...values: Array<string | null | undefined>): string | null {
  let earliest: string | null = null;
  for (const value of values) {
    if (!value) {
      continue;
    }
    if (!earliest || value < earliest) {
      earliest = value;
    }
  }
  return earliest;
}

export function getCurrentManuscriptVersionBoundary(
  manuscript: ManuscriptRead | null | undefined,
  blocks: ManuscriptBlockRead[],
): string | null {
  if (!manuscript) {
    return null;
  }

  const currentVersionBlocks = blocks.filter(
    (block) => block.manuscript_id === manuscript.id && block.version_no === manuscript.current_version_no,
  );
  const earliestBlockTimestamp = currentVersionBlocks.reduce<string | null>(
    (earliest, block) => (earliest && earliest < block.created_at ? earliest : block.created_at),
    null,
  );
  const versionAnchor =
    manuscript.current_version_no > 1
      ? manuscript.updated_at
      : firstDefined(manuscript.updated_at, manuscript.created_at);

  return earliestDate(earliestBlockTimestamp, versionAnchor);
}

export function getCurrentManuscriptReviews(
  manuscript: ManuscriptRead | null | undefined,
  reviews: ReviewRead[],
  blocks: ManuscriptBlockRead[],
): ReviewRead[] {
  if (!manuscript) {
    return [];
  }

  const versionBoundary = getCurrentManuscriptVersionBoundary(manuscript, blocks);
  return reviews
    .filter((review) => {
      if (review.target_kind !== "manuscript" || review.target_id !== manuscript.id) {
        return false;
      }

      if (typeof review.target_version_no === "number") {
        return review.target_version_no === manuscript.current_version_no;
      }

      return !versionBoundary || review.created_at >= versionBoundary;
    })
    .sort((left, right) => right.created_at.localeCompare(left.created_at));
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

export function classifyProjectEventStage(event: ProjectEvent): WorkspaceStageKey {
  const name = event.event_name;
  const payload = event.payload;
  const artifactType = typeof payload.artifact_type === "string" ? payload.artifact_type : null;

  if (name === "project.created" || name.startsWith("dataset.")) {
    return "intake";
  }

  if (name.startsWith("workflow.")) {
    return "workflow";
  }

  if (name.startsWith("analysis.run")) {
    return "analysis";
  }

  if (name.startsWith("artifact.")) {
    if (artifactType === "docx" || artifactType === "pdf" || artifactType === "zip") {
      return "export";
    }
    return artifactType === "evidence_attachment" ? "grounding" : "analysis";
  }

  if (name.startsWith("assertion.") || name.startsWith("evidence.")) {
    return "grounding";
  }

  if (name.startsWith("review.") || name.startsWith("verify.")) {
    return "review";
  }

  if (name.startsWith("export.")) {
    return "export";
  }

  if (payload.export_job_id || payload.output_artifact_id) {
    return "export";
  }

  if (payload.review_id) {
    return "review";
  }

  if (payload.assertion_id || payload.evidence_source_id) {
    return "grounding";
  }

  if (payload.analysis_run_id || payload.artifact_id || payload.artifact_ids) {
    return "analysis";
  }

  if (payload.workflow_instance_id) {
    return "workflow";
  }

  if (payload.dataset_id || payload.snapshot_id) {
    return "intake";
  }

  return "workflow";
}

export function groupProjectEventsByStage(events: ProjectEvent[]): Record<WorkspaceStageKey, ProjectEvent[]> {
  const grouped = Object.fromEntries(STAGE_ORDER.map((key) => [key, [] as ProjectEvent[]])) as Record<
    WorkspaceStageKey,
    ProjectEvent[]
  >;

  for (const event of events) {
    grouped[classifyProjectEventStage(event)].push(event);
  }

  for (const key of STAGE_ORDER) {
    grouped[key].sort((left, right) => right.occurred_at.localeCompare(left.occurred_at));
  }

  return grouped;
}

export function buildWorkspaceStages({
  detail,
  projectId,
  projection,
}: {
  detail: ProjectDetailResponse;
  projectId: string;
  projection: ProjectWorkspaceProjection;
}): WorkspaceStage[] {
  const snapshot = detail.latest_snapshot;
  const latestWorkflow = firstDefined(projection.workflows[0], detail.active_workflows?.[0]);
  const latestRun = projection.analysisRuns[0] ?? null;
  const latestAnalysisArtifact = projection.artifacts.find((artifact) => classifyArtifactStage(artifact) === "analysis") ?? null;
  const latestGroundingArtifact =
    projection.artifacts.find((artifact) => classifyArtifactStage(artifact) === "grounding") ?? latestAnalysisArtifact;
  const currentManuscriptReviews = getCurrentManuscriptReviews(
    detail.active_manuscript,
    projection.reviews,
    projection.manuscriptBlocks,
  );
  const latestReview = currentManuscriptReviews[0] ?? null;
  const latestExport = projection.exports[0] ?? null;
  const latestExportArtifact =
    (latestExport?.output_artifact_id
      ? projection.artifacts.find((artifact) => artifact.id === latestExport.output_artifact_id)
      : null) ?? null;

  const blockedAssertions = projection.assertions.filter((assertion) => assertion.state === "blocked");
  const staleAssertions = projection.assertions.filter((assertion) => assertion.state === "stale");
  const draftAssertions = projection.assertions.filter((assertion) => assertion.state === "draft");
  const verifiedAssertions = projection.assertions.filter((assertion) => assertion.state === "verified");
  const blockedEvidence = projection.evidenceLinks.filter((link) => link.verifier_status === "blocked");
  const pendingEvidence = projection.evidenceLinks.filter((link) => link.verifier_status === "pending");
  const warningEvidence = projection.evidenceLinks.filter((link) => link.verifier_status === "warning");
  const passedEvidence = projection.evidenceLinks.filter((link) => link.verifier_status === "passed");
  const reviewCounts = countBy(currentManuscriptReviews, (review) => review.state);
  const activeManuscript = detail.active_manuscript;
  const activeManuscriptBlocks = activeManuscript
    ? projection.manuscriptBlocks.filter(
        (block) =>
          block.manuscript_id === activeManuscript.id && block.version_no === activeManuscript.current_version_no,
      )
    : [];
  const assertionBackedBlocks = activeManuscriptBlocks.filter(
    (block) => Array.isArray(block.assertion_ids) && block.assertion_ids.length > 0,
  );

  const intakeActions: WorkspaceStageLink[] = [];
  pushAction(
    intakeActions,
    snapshot ? `/projects/${projectId}/datasets/${snapshot.dataset_id}` : `/projects/${projectId}/datasets`,
    snapshot ? "Open snapshot dataset" : "Go to datasets",
  );
  pushAction(intakeActions, `/projects/${projectId}/datasets`, "Datasets");

  let intakeStatus = "pending";
  let intakeSummary = "No dataset_snapshot exists yet. Register intake data before workflow orchestration can start.";
  if (snapshot) {
    if (snapshot.phi_scan_status === "blocked") {
      intakeStatus = "blocked";
      intakeSummary = "PHI scan blocked the latest dataset_snapshot. Intake must be repaired before any downstream stage.";
    } else if (snapshot.phi_scan_status === "needs_human") {
      intakeStatus = "needs_human";
      intakeSummary = "The latest dataset_snapshot needs human review before workflow planning can continue.";
    } else if (snapshot.deid_status === "failed") {
      intakeStatus = "failed";
      intakeSummary = "De-identification failed on the latest dataset_snapshot.";
    } else if (snapshot.phi_scan_status === "pending" || snapshot.deid_status === "pending") {
      intakeStatus = "running";
      intakeSummary = "Dataset intake is still resolving policy checks and de-identification status.";
    } else {
      intakeStatus = "completed";
      intakeSummary = `Snapshot #${snapshot.snapshot_no} is ready for workflow planning.`;
      pushAction(intakeActions, `/projects/${projectId}/workflows`, "Plan workflow");
    }
  }

  const workflowActions: WorkspaceStageLink[] = [];
  pushAction(
    workflowActions,
    latestWorkflow ? `/projects/${projectId}/workflows/${latestWorkflow.id}` : `/projects/${projectId}/workflows`,
    latestWorkflow ? "Open workflow" : "Go to workflows",
  );
  if (snapshot) {
    pushAction(workflowActions, `/projects/${projectId}/datasets/${snapshot.dataset_id}`, "Snapshot source");
  }

  let workflowStatus = snapshot ? "pending" : "pending";
  let workflowSummary = snapshot
    ? "No workflow_instance has started yet. The project is ready to enter deterministic orchestration."
    : "Workflow planning remains gated until dataset intake produces a usable snapshot.";
  if (latestWorkflow) {
    if (latestWorkflow.state === "blocked" || latestWorkflow.state === "needs_human" || latestWorkflow.state === "failed") {
      workflowStatus = latestWorkflow.state;
      workflowSummary = `Workflow ${latestWorkflow.id.slice(0, 8)} is ${latestWorkflow.state}. Current step: ${latestWorkflow.current_step ?? "unrecorded"}.`;
    } else if (
      latestWorkflow.state === "created" ||
      latestWorkflow.state === "retrieving" ||
      latestWorkflow.state === "retrieved" ||
      latestWorkflow.state === "structuring" ||
      latestWorkflow.state === "structured"
    ) {
      workflowStatus = "running";
      workflowSummary = `Workflow ${latestWorkflow.id.slice(0, 8)} is advancing through ${latestWorkflow.current_step ?? latestWorkflow.state}.`;
    } else {
      workflowStatus = "completed";
      workflowSummary = `Workflow orchestration has advanced into downstream analysis and grounding stages.`;
    }
  }

  const analysisArtifactCount = latestRun
    ? projection.artifacts.filter((artifact) => artifact.run_id === latestRun.id).length
    : projection.artifacts.filter((artifact) => classifyArtifactStage(artifact) === "analysis").length;
  const analysisActions: WorkspaceStageLink[] = [];
  pushAction(
    analysisActions,
    latestRun ? `/projects/${projectId}/analysis-runs/${latestRun.id}` : `/projects/${projectId}/workflows`,
    latestRun ? "Open analysis run" : "Go to workflow plan",
  );
  pushAction(
    analysisActions,
    latestAnalysisArtifact ? `/projects/${projectId}/artifacts/${latestAnalysisArtifact.id}` : `/projects/${projectId}/artifacts`,
    latestAnalysisArtifact ? "Open latest artifact" : "Go to artifacts",
  );

  let analysisStatus = latestWorkflow ? "pending" : "pending";
  let analysisSummary = latestWorkflow
    ? "No analysis_run has been created yet."
    : "Analysis remains pending until workflow orchestration schedules a run.";
  if (latestRun) {
    if (latestRun.state === "failed" || latestRun.state === "blocked" || latestRun.state === "canceled") {
      analysisStatus = latestRun.state;
      analysisSummary = `Analysis run ${latestRun.id.slice(0, 8)} ended in ${latestRun.state}.`;
    } else if (
      latestRun.state === "created" ||
      latestRun.state === "requested" ||
      latestRun.state === "queued" ||
      latestRun.state === "running"
    ) {
      analysisStatus = "running";
      analysisSummary = `Analysis run ${latestRun.id.slice(0, 8)} is ${latestRun.state} on template ${latestRun.template_id}.`;
    } else {
      analysisStatus = "completed";
      analysisSummary = `Analysis run ${latestRun.id.slice(0, 8)} succeeded and produced ${analysisArtifactCount} artifact(s).`;
    }
  }

  const groundingActions: WorkspaceStageLink[] = [];
  pushAction(
    groundingActions,
    latestGroundingArtifact ? `/projects/${projectId}/artifacts/${latestGroundingArtifact.id}` : `/projects/${projectId}/artifacts`,
    latestGroundingArtifact ? "Open grounding artifact" : "Go to artifacts",
  );
  pushAction(groundingActions, `/projects/${projectId}/assertions`, "Assertions");
  pushAction(groundingActions, `/projects/${projectId}/evidence`, "Evidence");
  if (detail.active_manuscript) {
    pushAction(groundingActions, `/projects/${projectId}/manuscripts/${detail.active_manuscript.id}`, "Active manuscript");
  }

  let groundingStatus = "pending";
  let groundingSummary = "No assertion or evidence binding has been recorded yet.";
  if (blockedAssertions.length > 0 || blockedEvidence.length > 0) {
    groundingStatus = "blocked";
    groundingSummary = `${formatCount(blockedAssertions.length, "blocked assertion")} and ${formatCount(blockedEvidence.length, "blocked evidence link")} require repair before writing can continue.`;
  } else if (draftAssertions.length > 0 || pendingEvidence.length > 0) {
    groundingStatus = "running";
    groundingSummary = `${formatCount(draftAssertions.length, "draft assertion")} and ${formatCount(pendingEvidence.length, "pending evidence link")} are still being grounded.`;
  } else if (warningEvidence.length > 0 || staleAssertions.length > 0) {
    groundingStatus = "warning";
    groundingSummary = `${formatCount(staleAssertions.length, "stale assertion")} and ${formatCount(warningEvidence.length, "warning evidence link")} need curator attention.`;
  } else if (verifiedAssertions.length > 0 || passedEvidence.length > 0) {
    groundingStatus = "completed";
    groundingSummary = `${formatCount(verifiedAssertions.length, "verified assertion")} and ${formatCount(passedEvidence.length, "passed evidence link")} are available to the writing surface.`;
  } else if (latestAnalysisArtifact) {
    groundingStatus = "pending";
    groundingSummary = "Artifacts exist, but assertion extraction has not started yet.";
  }

  const reviewActions: WorkspaceStageLink[] = [];
  if (detail.active_manuscript) {
    pushAction(reviewActions, `/projects/${projectId}/manuscripts/${detail.active_manuscript.id}`, "Open manuscript");
  } else {
    pushAction(reviewActions, `/projects/${projectId}/manuscripts`, "Go to manuscripts");
  }
  pushAction(reviewActions, `/projects/${projectId}/reviews`, "Reviews");
  pushAction(reviewActions, `/projects/${projectId}/audit`, "Audit trail");

  let reviewStatus = detail.active_manuscript ? "pending" : "pending";
  let reviewSummary = detail.active_manuscript
    ? "No review ticket is currently open."
    : "No active manuscript is selected for review.";
  if ((reviewCounts.changes_requested ?? 0) > 0) {
    reviewStatus = "changes_requested";
    reviewSummary = `${reviewCounts.changes_requested} review(s) requested changes before verify/export can continue.`;
  } else if ((reviewCounts.rejected ?? 0) > 0) {
    reviewStatus = "rejected";
    reviewSummary = `${reviewCounts.rejected} review(s) were rejected and require manual correction.`;
  } else if ((reviewCounts.pending ?? 0) > 0 || detail.project.status === "review_required") {
    reviewStatus = "running";
    reviewSummary = `${reviewCounts.pending ?? 0} review(s) are still pending on the current manuscript chain.`;
  } else if ((reviewCounts.approved ?? 0) > 0 || detail.active_manuscript?.state === "approved") {
    reviewStatus = "completed";
    reviewSummary = `Review gate is currently approved for the active manuscript path.`;
  }

  const exportActions: WorkspaceStageLink[] = [];
  pushAction(exportActions, `/projects/${projectId}/exports`, "Exports");
  if (latestExportArtifact) {
    pushAction(exportActions, `/projects/${projectId}/artifacts/${latestExportArtifact.id}`, "Output artifact");
  }
  pushAction(exportActions, `/projects/${projectId}/audit`, "Audit trail");

  let exportStatus = "pending";
  let exportSummary = "No export_job has been created yet.";
  if (latestExport) {
    if (latestExport.state === "blocked" || latestExport.state === "failed") {
      exportStatus = latestExport.state;
      exportSummary = `Export job ${latestExport.id.slice(0, 8)} ended in ${latestExport.state}.`;
    } else if (latestExport.state === "pending" || latestExport.state === "running") {
      exportStatus = "running";
      exportSummary = `Export job ${latestExport.id.slice(0, 8)} is ${latestExport.state}.`;
    } else {
      exportStatus = "completed";
      exportSummary = `Export job ${latestExport.id.slice(0, 8)} completed and produced a deliverable artifact.`;
    }
  }

  return [
    {
      actions: intakeActions,
      description: "Snapshot creation, PHI scan, and de-identification readiness gate.",
      details: {
        dataset_id: snapshot?.dataset_id ?? null,
        deid_status: snapshot?.deid_status ?? null,
        phi_scan_status: snapshot?.phi_scan_status ?? null,
        row_count: snapshot?.row_count ?? null,
        snapshot_id: snapshot?.id ?? null,
        snapshot_no: snapshot?.snapshot_no ?? null,
      },
      eyebrow: "Stage 01",
      key: "intake",
      metrics: [
        { label: "Snapshot", value: snapshot ? `#${snapshot.snapshot_no}` : "none" },
        { label: "PHI", value: snapshot?.phi_scan_status ?? "unrecorded" },
        { label: "Deid", value: snapshot?.deid_status ?? "unrecorded" },
        { label: "Rows", value: snapshot?.row_count?.toString() ?? "unknown" },
      ],
      status: intakeStatus,
      step: 1,
      summary: intakeSummary,
      title: "Dataset Intake",
      updatedAt: snapshot?.created_at ?? null,
    },
    {
      actions: workflowActions,
      description: "Deterministic orchestration state before compute and writing surfaces begin.",
      details: {
        current_step: latestWorkflow?.current_step ?? null,
        started_at: latestWorkflow?.started_at ?? null,
        workflow_id: latestWorkflow?.id ?? null,
        workflow_state: latestWorkflow?.state ?? null,
        workflow_type: latestWorkflow?.workflow_type ?? null,
      },
      eyebrow: "Stage 02",
      key: "workflow",
      metrics: [
        { label: "Workflow", value: latestWorkflow?.id.slice(0, 8) ?? "none" },
        { label: "State", value: latestWorkflow?.state ?? "pending" },
        { label: "Step", value: latestWorkflow?.current_step ?? "unrecorded" },
        { label: "Type", value: latestWorkflow?.workflow_type ?? "n/a" },
      ],
      status: workflowStatus,
      step: 2,
      summary: workflowSummary,
      title: "Workflow Planning",
      updatedAt: latestWorkflow?.started_at ?? null,
    },
    {
      actions: analysisActions,
      description: "Template execution, run state, and output artifacts for the current project path.",
      details: {
        analysis_run_id: latestRun?.id ?? null,
        artifact_count: analysisArtifactCount,
        run_state: latestRun?.state ?? null,
        template_id: latestRun?.template_id ?? null,
      },
      eyebrow: "Stage 03",
      key: "analysis",
      metrics: [
        { label: "Run", value: latestRun?.id.slice(0, 8) ?? "none" },
        { label: "State", value: latestRun?.state ?? "pending" },
        { label: "Template", value: latestRun?.template_id ?? "unassigned" },
        { label: "Artifacts", value: analysisArtifactCount.toString() },
      ],
      status: analysisStatus,
      step: 3,
      summary: analysisSummary,
      title: "Analysis Run",
      updatedAt: firstDefined(latestRun?.finished_at, latestRun?.started_at),
    },
    {
      actions: groundingActions,
      description: "Artifact to assertion to evidence to manuscript adjacency for traceable writing.",
      details: {
        assertion_backed_block_count: assertionBackedBlocks.length,
        assertion_state_summary: joinCountSummary(countBy(projection.assertions, (assertion) => assertion.state)),
        evidence_state_summary: joinCountSummary(countBy(projection.evidenceLinks, (link) => link.verifier_status)),
        latest_artifact_id: latestGroundingArtifact?.id ?? null,
      },
      eyebrow: "Stage 04",
      key: "grounding",
      metrics: [
        { label: "Assertions", value: projection.assertions.length.toString() },
        { label: "Evidence", value: projection.evidenceLinks.length.toString() },
        { label: "Blocks", value: assertionBackedBlocks.length.toString() },
        { label: "Artifact", value: latestGroundingArtifact?.artifact_type ?? "none" },
      ],
      status: groundingStatus,
      step: 4,
      summary: groundingSummary,
      title: "Assertion Grounding",
      updatedAt: firstDefined(
        projection.evidenceLinks[0]?.created_at,
        projection.assertions[0]?.created_at,
        latestGroundingArtifact?.created_at,
      ),
    },
    {
      actions: reviewActions,
      description: "Manuscript state, human review decisions, and verify blockers before export.",
      details: {
        active_manuscript_id: detail.active_manuscript?.id ?? null,
        manuscript_state: detail.active_manuscript?.state ?? null,
        review_summary: reviewCounts,
      },
      eyebrow: "Stage 05",
      key: "review",
      metrics: [
        { label: "Manuscript", value: detail.active_manuscript?.title ?? "none" },
        { label: "State", value: detail.active_manuscript?.state ?? "pending" },
        { label: "Reviews", value: currentManuscriptReviews.length.toString() },
        { label: "Summary", value: joinCountSummary(reviewCounts) },
      ],
      status: reviewStatus,
      step: 5,
      summary: reviewSummary,
      title: "Review Gate",
      updatedAt: firstDefined(latestReview?.decided_at, latestReview?.created_at, detail.active_manuscript?.updated_at),
    },
    {
      actions: exportActions,
      description: "Final deliverable output, signed download path, and append-only audit trail.",
      details: {
        export_job_id: latestExport?.id ?? null,
        export_state: latestExport?.state ?? null,
        format: latestExport?.format ?? null,
        output_artifact_id: latestExport?.output_artifact_id ?? null,
      },
      eyebrow: "Stage 06",
      key: "export",
      metrics: [
        { label: "Exports", value: projection.exports.length.toString() },
        { label: "Latest", value: latestExport?.id.slice(0, 8) ?? "none" },
        { label: "State", value: latestExport?.state ?? "pending" },
        { label: "Format", value: latestExport?.format ?? "n/a" },
      ],
      status: exportStatus,
      step: 6,
      summary: exportSummary,
      title: "Export Delivery",
      updatedAt: firstDefined(latestExport?.completed_at, latestExport?.requested_at),
    },
  ];
}

export function getDefaultWorkspaceStageKey(stages: WorkspaceStage[]): WorkspaceStageKey {
  const blockingStage = stages.find(
    (stage) => stage.status === "blocked" || stage.status === "needs_human" || stage.status === "failed",
  );
  if (blockingStage) {
    return blockingStage.key;
  }

  const activeStage = stages.find((stage) => stage.status === "running" || stage.status === "warning");
  if (activeStage) {
    return activeStage.key;
  }

  const completedStages = stages.filter((stage) => stage.status === "completed");
  if (completedStages.length > 0) {
    return completedStages[completedStages.length - 1].key;
  }

  return stages[0]?.key ?? "intake";
}

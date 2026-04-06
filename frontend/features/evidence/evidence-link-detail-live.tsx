"use client";

import type { EvidenceLinkDetailResponse } from "@/lib/api/generated/control-plane";

import { EvidenceLinkDetail } from "@/features/evidence/evidence-link-detail";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function EvidenceLinkDetailLive({
  initialDetail,
  linkId,
  projectId,
}: {
  initialDetail: EvidenceLinkDetailResponse;
  linkId: string;
  projectId: string;
}) {
  const { projection } = useWorkspaceData();
  const evidenceLink = projection.evidenceLinks.find((item) => item.id === linkId) ?? initialDetail.evidence_link;
  const assertion = projection.assertions.find((item) => item.id === evidenceLink.assertion_id) ?? initialDetail.assertion;
  const evidenceSource =
    projection.evidenceSources.find((item) => item.id === evidenceLink.evidence_source_id) ?? initialDetail.evidence_source;
  const sourceChunk = initialDetail.source_chunk ?? null;
  const sourceArtifact =
    (assertion.source_artifact_id
      ? projection.artifacts.find((item) => item.id === assertion.source_artifact_id) ?? null
      : null) ?? initialDetail.source_artifact ?? null;
  const sourceRunId = assertion.source_run_id ?? sourceArtifact?.run_id ?? initialDetail.source_run?.id ?? null;
  const sourceRun =
    (sourceRunId ? projection.analysisRuns.find((item) => item.id === sourceRunId) ?? null : null) ??
    initialDetail.source_run ??
    null;
  const consumerBlocks = projection.manuscriptBlocks.filter((block) => (block.assertion_ids ?? []).includes(assertion.id));
  const consumerManuscripts = projection.manuscripts.filter((manuscript) =>
    consumerBlocks.some((block) => block.manuscript_id === manuscript.id),
  );

  return (
    <EvidenceLinkDetail
      assertionText={assertion.text_norm}
      consumerBlocks={consumerBlocks}
      consumerManuscripts={consumerManuscripts}
      evidenceLink={evidenceLink}
      evidenceSource={evidenceSource}
      projectId={projectId}
      sourceChunk={sourceChunk}
      sourceArtifact={sourceArtifact}
      sourceRun={sourceRun}
    />
  );
}

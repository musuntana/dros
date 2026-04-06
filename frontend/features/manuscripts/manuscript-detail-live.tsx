"use client";

import { useEffect, useMemo, useState } from "react";

import type { RenderManuscriptResponse } from "@/lib/api/generated/control-plane";
import { controlPlaneRoutes } from "@/lib/api/control-plane/endpoints";
import { parseError } from "@/lib/api/control-plane/errors";
import { getControlPlaneBaseUrl } from "@/lib/config";

import { ManuscriptDetail } from "@/features/manuscripts/manuscript-detail";
import { useWorkspaceData } from "@/features/projects/workspace-context";

async function renderManuscriptPreview(
  projectId: string,
  manuscriptId: string,
  signal: AbortSignal,
): Promise<RenderManuscriptResponse> {
  const url = new URL(controlPlaneRoutes.projects.manuscriptRender(projectId, manuscriptId), getControlPlaneBaseUrl());
  const response = await fetch(url, {
    method: "POST",
    signal,
  });
  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as RenderManuscriptResponse;
}

export function ManuscriptDetailLive({
  manuscriptId,
  projectId,
}: {
  manuscriptId: string;
  projectId: string;
}) {
  const { projection } = useWorkspaceData();

  const manuscript = useMemo(
    () => projection.manuscripts.find((m) => m.id === manuscriptId) ?? null,
    [projection.manuscripts, manuscriptId],
  );

  const blocks = useMemo(() => {
    if (!manuscript) return [];
    return projection.manuscriptBlocks
      .filter(
        (b) =>
          b.manuscript_id === manuscriptId &&
          b.version_no === manuscript.current_version_no,
      )
      .sort((a, b) => {
        if (a.section_key !== b.section_key)
          return a.section_key.localeCompare(b.section_key);
        if (a.block_order !== b.block_order) return a.block_order - b.block_order;
        return a.created_at.localeCompare(b.created_at);
      });
  }, [projection.manuscriptBlocks, manuscriptId, manuscript]);

  const verifiedAssertions = useMemo(
    () => projection.assertions.filter((a) => a.state === "verified"),
    [projection.assertions],
  );

  // Call the backend render endpoint to preserve its semantics: returns
  // existing current-version blocks when present, otherwise synthesizes
  // preview blocks from verified assertions.
  const [preview, setPreview] = useState<RenderManuscriptResponse>({
    blocks: [],
  });
  const blockFingerprint = useMemo(() => blocks.map((b) => b.id).join(","), [blocks]);
  const assertionFingerprint = useMemo(
    () => verifiedAssertions.map((a) => a.id).join(","),
    [verifiedAssertions],
  );
  useEffect(() => {
    if (!manuscript) return;
    const controller = new AbortController();
    renderManuscriptPreview(projectId, manuscriptId, controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) {
          setPreview(response);
        }
      })
      .catch(() => {
        // Fallback: echo stored blocks so the section is never empty after
        // a transient backend failure.
        if (!controller.signal.aborted) {
          setPreview({ blocks, warnings: ["Render preview could not be refreshed."] });
        }
      });
    return () => controller.abort();
  }, [projectId, manuscriptId, manuscript, blockFingerprint, assertionFingerprint, blocks]);

  if (!manuscript) {
    return (
      <div className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="text-sm text-muted">
          Manuscript <code className="font-mono text-xs">{manuscriptId.slice(0, 8)}</code> was not
          found in the workspace projection.
        </p>
      </div>
    );
  }

  return (
    <ManuscriptDetail
      blocks={blocks}
      manuscript={manuscript}
      preview={preview}
      projectId={projectId}
      verifiedAssertions={verifiedAssertions}
    />
  );
}

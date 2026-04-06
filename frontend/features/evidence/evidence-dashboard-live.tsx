"use client";

import { EvidenceDashboard } from "@/features/evidence/evidence-dashboard";
import type { EvidenceLinkRecord } from "@/features/evidence/types";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function EvidenceDashboardLive({ projectId }: { projectId: string }) {
  const { projection } = useWorkspaceData();
  const assertionById = new Map(projection.assertions.map((assertion) => [assertion.id, assertion]));
  const sourceById = new Map(projection.evidenceSources.map((source) => [source.id, source]));

  const linkRecords: EvidenceLinkRecord[] = projection.evidenceLinks
    .flatMap((link) => {
      const assertion = assertionById.get(link.assertion_id);
      if (!assertion) {
        return [];
      }

      return [
        {
          assertion,
          link,
          source: sourceById.get(link.evidence_source_id) ?? null,
        },
      ];
    })
    .sort((left, right) => right.link.created_at.localeCompare(left.link.created_at));

  return (
    <EvidenceDashboard
      assertions={projection.assertions}
      linkRecords={linkRecords}
      projectId={projectId}
      sources={projection.evidenceSources}
    />
  );
}

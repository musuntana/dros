import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type { AssertionRead, EvidenceLinkDetailResponse, EvidenceSourceRead } from "@/lib/api/generated/control-plane";
import type { EvidenceLinkRecord } from "@/features/evidence/types";

export async function getEvidencePageData(projectId: string): Promise<{
  assertions: AssertionRead[];
  linkRecords: EvidenceLinkRecord[];
  sources: EvidenceSourceRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [linkResponse, sourceResponse, assertionResponse] = await Promise.all([
    client.listEvidenceLinks(projectId, { limit: 100, offset: 0 }),
    client.listEvidenceSources(projectId, { limit: 100, offset: 0 }),
    client.listAssertions(projectId, { limit: 100, offset: 0 }),
  ]);

  const assertions = assertionResponse.items.items;
  const assertionById = new Map(assertions.map((assertion) => [assertion.id, assertion]));
  const sources = sourceResponse.items.items;
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const linkRecords = linkResponse.items.items
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

  return {
    assertions,
    linkRecords,
    sources,
  };
}

export async function getEvidenceLinkDetailPageData(
  projectId: string,
  linkId: string,
): Promise<EvidenceLinkDetailResponse> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  return client.getEvidenceLink(projectId, linkId);
}

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type {
  AssertionRead,
  ManuscriptBlockRead,
  ManuscriptRead,
  RenderManuscriptResponse,
} from "@/lib/api/generated/control-plane";

export async function getManuscriptsPageData(projectId: string): Promise<{
  manuscripts: ManuscriptRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const response = await client.listManuscripts(projectId);

  return {
    manuscripts: response.items,
  };
}

export async function getManuscriptDetailPageData(
  projectId: string,
  manuscriptId: string,
): Promise<{
  blocks: ManuscriptBlockRead[];
  manuscript: ManuscriptRead;
  preview: RenderManuscriptResponse;
  verifiedAssertions: AssertionRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [detail, blocksResponse, preview, assertionResponse] = await Promise.all([
    client.getManuscript(projectId, manuscriptId),
    client.listManuscriptBlocks(projectId, manuscriptId),
    client.renderManuscript(projectId, manuscriptId),
    client.listAssertions(projectId, { limit: 100, offset: 0 }),
  ]);

  return {
    blocks: blocksResponse.items,
    manuscript: detail.manuscript,
    preview,
    verifiedAssertions: assertionResponse.items.items.filter((assertion) => assertion.state === "verified"),
  };
}

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import type {
  ArtifactRead,
  AssertionRead,
  ManuscriptRead,
  ReviewRead,
} from "@/lib/api/generated/control-plane";

export async function getReviewsPageData(projectId: string): Promise<{
  artifacts: ArtifactRead[];
  assertions: AssertionRead[];
  manuscripts: ManuscriptRead[];
  reviews: ReviewRead[];
}> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  const [reviewResponse, manuscriptResponse, assertionResponse, artifactResponse] = await Promise.all([
    client.listReviews(projectId, { limit: 100, offset: 0 }),
    client.listManuscripts(projectId),
    client.listAssertions(projectId, { limit: 100, offset: 0 }),
    client.listArtifacts(projectId, { limit: 100, offset: 0 }),
  ]);

  return {
    artifacts: artifactResponse.items.items,
    assertions: assertionResponse.items.items,
    manuscripts: manuscriptResponse.items,
    reviews: reviewResponse.items.items,
  };
}

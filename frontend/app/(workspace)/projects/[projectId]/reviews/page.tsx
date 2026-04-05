import { ErrorCard } from "@/components/status/error-card";
import { ReviewsDashboard } from "@/features/reviews/reviews-dashboard";
import { getReviewsPageData } from "@/features/reviews/server";

export default async function ReviewsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { artifacts, assertions, manuscripts, reviews } = await getReviewsPageData(projectId);

    return (
      <ReviewsDashboard
        artifacts={artifacts}
        assertions={assertions}
        manuscripts={manuscripts}
        projectId={projectId}
        reviews={reviews}
      />
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Reviews failed to load" />;
  }
}

import { ReviewsDashboardLive } from "@/features/reviews/reviews-dashboard-live";

export default async function ReviewsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <ReviewsDashboardLive projectId={projectId} />;
}

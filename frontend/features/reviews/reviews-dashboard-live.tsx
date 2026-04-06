"use client";

import { ReviewsDashboard } from "@/features/reviews/reviews-dashboard";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function ReviewsDashboardLive({ projectId }: { projectId: string }) {
  const { projection } = useWorkspaceData();

  return (
    <ReviewsDashboard
      artifacts={projection.artifacts}
      assertions={projection.assertions}
      manuscripts={projection.manuscripts}
      projectId={projectId}
      reviews={projection.reviews}
    />
  );
}

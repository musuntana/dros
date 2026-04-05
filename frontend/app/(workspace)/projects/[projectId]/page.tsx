import { ErrorCard } from "@/components/status/error-card";
import { ProjectOverview } from "@/features/projects/project-overview";
import { getProjectWorkspaceData } from "@/features/projects/server";

export default async function ProjectOverviewPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { detail, members } = await getProjectWorkspaceData(projectId);

    return <ProjectOverview detail={detail} members={members} />;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Project overview failed to load" />;
  }
}

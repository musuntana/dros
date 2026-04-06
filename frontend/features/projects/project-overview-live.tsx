"use client";

import { ProjectOverview } from "@/features/projects/project-overview";
import { useWorkspaceData } from "@/features/projects/workspace-context";

export function ProjectOverviewLive() {
  const { detail, members } = useWorkspaceData();
  return <ProjectOverview detail={detail} members={members} />;
}

import type { ReactNode } from "react";

import { WorkspaceShell } from "@/components/shell/workspace-shell";
import { ErrorCard } from "@/components/status/error-card";
import { getProjectWorkspaceData } from "@/features/projects/server";

export default async function ProjectLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  try {
    const { projectId } = await params;
    const { detail, initialEvents, session } = await getProjectWorkspaceData(projectId);

    return (
      <WorkspaceShell detail={detail} initialEvents={initialEvents} session={session}>
        {children}
      </WorkspaceShell>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return <ErrorCard message={message} title="Project workspace failed to load" />;
  }
}

"use client";

import type { ReactNode } from "react";
import { createContext, useContext } from "react";

import type { ProjectMemberRead, ProjectDetailResponse } from "@/lib/api/generated/control-plane";
import type { ProjectEvent, SessionRead } from "@/lib/api/gateway";
import type { ProjectWorkspaceProjection } from "@/features/projects/workspace-projection";

export interface WorkspaceDataValue {
  detail: ProjectDetailResponse;
  events: ProjectEvent[];
  members: ProjectMemberRead[];
  projection: ProjectWorkspaceProjection;
  session: SessionRead | null;
}

const WorkspaceDataContext = createContext<WorkspaceDataValue | null>(null);

export function WorkspaceDataProvider({
  children,
  value,
}: {
  children: ReactNode;
  value: WorkspaceDataValue;
}) {
  return <WorkspaceDataContext.Provider value={value}>{children}</WorkspaceDataContext.Provider>;
}

export function useWorkspaceData(): WorkspaceDataValue {
  const value = useContext(WorkspaceDataContext);
  if (value === null) {
    throw new Error("useWorkspaceData must be used within a WorkspaceDataProvider");
  }
  return value;
}

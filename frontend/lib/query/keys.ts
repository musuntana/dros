export const queryKeys = {
  projects: ["projects"] as const,
  project: (projectId: string) => ["projects", projectId] as const,
  projectMembers: (projectId: string) => ["projects", projectId, "members"] as const,
  workflows: (projectId: string) => ["projects", projectId, "workflows"] as const,
  analysisRun: (projectId: string, runId: string) => ["projects", projectId, "analysis-runs", runId] as const,
  reviews: (projectId: string) => ["projects", projectId, "reviews"] as const,
  exports: (projectId: string) => ["projects", projectId, "exports"] as const,
};

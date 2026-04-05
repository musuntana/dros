export interface PaginationParams {
  [key: string]: string | number | boolean | null | undefined;
  limit?: number;
  offset?: number;
}

export const controlPlaneRoutes = {
  healthz: () => "/healthz",
  internalAuditReplay: () => "/v1/internal/audit/replay",
  templates: {
    list: () => "/v1/templates",
    detail: (templateId: string) => `/v1/templates/${templateId}`,
  },
  projects: {
    list: () => "/v1/projects",
    create: () => "/v1/projects",
    detail: (projectId: string) => `/v1/projects/${projectId}`,
    update: (projectId: string) => `/v1/projects/${projectId}`,
    members: (projectId: string) => `/v1/projects/${projectId}/members`,
    analysisPlans: (projectId: string) => `/v1/projects/${projectId}/analysis/plans`,
    workflows: (projectId: string) => `/v1/projects/${projectId}/workflows`,
    workflow: (projectId: string, workflowId: string) =>
      `/v1/projects/${projectId}/workflows/${workflowId}`,
    workflowAdvance: (projectId: string, workflowId: string) =>
      `/v1/projects/${projectId}/workflows/${workflowId}/advance`,
    workflowCancel: (projectId: string, workflowId: string) =>
      `/v1/projects/${projectId}/workflows/${workflowId}/cancel`,
    analysisRuns: (projectId: string) => `/v1/projects/${projectId}/analysis-runs`,
    analysisRun: (projectId: string, runId: string) =>
      `/v1/projects/${projectId}/analysis-runs/${runId}`,
    datasets: (projectId: string) => `/v1/projects/${projectId}/datasets`,
    importPublicDataset: (projectId: string) => `/v1/projects/${projectId}/datasets/import-public`,
    registerUploadDataset: (projectId: string) => `/v1/projects/${projectId}/datasets/register-upload`,
    dataset: (projectId: string, datasetId: string) =>
      `/v1/projects/${projectId}/datasets/${datasetId}`,
    datasetSnapshots: (projectId: string, datasetId: string) =>
      `/v1/projects/${projectId}/datasets/${datasetId}/snapshots`,
    datasetPolicyChecks: (projectId: string, datasetId: string) =>
      `/v1/projects/${projectId}/datasets/${datasetId}/policy-checks`,
    artifacts: (projectId: string) => `/v1/projects/${projectId}/artifacts`,
    artifact: (projectId: string, artifactId: string) =>
      `/v1/projects/${projectId}/artifacts/${artifactId}`,
    lineageEdges: (projectId: string) => `/v1/projects/${projectId}/lineage-edges`,
    lineage: (projectId: string) => `/v1/projects/${projectId}/lineage`,
    assertions: (projectId: string) => `/v1/projects/${projectId}/assertions`,
    assertion: (projectId: string, assertionId: string) =>
      `/v1/projects/${projectId}/assertions/${assertionId}`,
    evidenceSearch: (projectId: string) => `/v1/projects/${projectId}/evidence/search`,
    evidenceResolve: (projectId: string) => `/v1/projects/${projectId}/evidence/resolve`,
    evidence: (projectId: string) => `/v1/projects/${projectId}/evidence`,
    evidenceLinks: (projectId: string) => `/v1/projects/${projectId}/evidence-links`,
    verifyEvidenceLink: (projectId: string, linkId: string) =>
      `/v1/projects/${projectId}/evidence-links/${linkId}/verify`,
    manuscripts: (projectId: string) => `/v1/projects/${projectId}/manuscripts`,
    manuscript: (projectId: string, manuscriptId: string) =>
      `/v1/projects/${projectId}/manuscripts/${manuscriptId}`,
    manuscriptBlocks: (projectId: string, manuscriptId: string) =>
      `/v1/projects/${projectId}/manuscripts/${manuscriptId}/blocks`,
    manuscriptVersions: (projectId: string, manuscriptId: string) =>
      `/v1/projects/${projectId}/manuscripts/${manuscriptId}/versions`,
    manuscriptRender: (projectId: string, manuscriptId: string) =>
      `/v1/projects/${projectId}/manuscripts/${manuscriptId}/render`,
    reviews: (projectId: string) => `/v1/projects/${projectId}/reviews`,
    reviewDecision: (projectId: string, reviewId: string) =>
      `/v1/projects/${projectId}/reviews/${reviewId}/decisions`,
    verify: (projectId: string) => `/v1/projects/${projectId}/verify`,
    exports: (projectId: string) => `/v1/projects/${projectId}/exports`,
    exportJob: (projectId: string, exportJobId: string) =>
      `/v1/projects/${projectId}/exports/${exportJobId}`,
    auditEvents: (projectId: string) => `/v1/projects/${projectId}/audit-events`,
    auditEvent: (projectId: string, eventId: string) =>
      `/v1/projects/${projectId}/audit-events/${eventId}`,
  },
};

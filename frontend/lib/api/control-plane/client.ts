import type {
  AddProjectMemberRequest,
  AddProjectMemberResponse,
  AdvanceWorkflowRequest,
  AnalysisRunDetailResponse,
  AnalysisRunListResponse,
  ArtifactDetailResponse,
  ArtifactListResponse,
  AssertionDetailResponse,
  AssertionListResponse,
  AuditEventDetailResponse,
  AuditEventListResponse,
  AuditReplayResponse,
  CreateAnalysisPlanRequest,
  CreateAnalysisPlanResponse,
  CreateAnalysisRunRequest,
  CreateAnalysisRunResponse,
  CreateArtifactRequest,
  CreateArtifactResponse,
  CreateAssertionRequest,
  CreateAssertionResponse,
  CreateDatasetSnapshotRequest,
  CreateDatasetSnapshotResponse,
  CreateDatasetResponse,
  CreateEvidenceChunkRequest,
  CreateEvidenceChunkResponse,
  CreateEvidenceLinkRequest,
  CreateEvidenceLinkResponse,
  CreateExportJobRequest,
  CreateExportJobResponse,
  CreateLineageEdgeRequest,
  CreateLineageEdgeResponse,
  CreateManuscriptBlockRequest,
  CreateManuscriptBlockResponse,
  CreateManuscriptRequest,
  CreateManuscriptResponse,
  CreateManuscriptVersionRequest,
  CreateManuscriptVersionResponse,
  CreateProjectRequest,
  CreateProjectResponse,
  CreateReviewRequest,
  CreateReviewResponse,
  CreateWorkflowRequest,
  CreateWorkflowResponse,
  CancelWorkflowRequest,
  DatasetDetailResponse,
  DatasetListResponse,
  DatasetPolicyCheckResponse,
  DatasetSnapshotListResponse,
  EvidenceChunkDetailResponse,
  EvidenceChunkListResponse,
  EvidenceLinkDetailResponse,
  EvidenceSearchRequest,
  EvidenceSearchResponse,
  EvidenceLinkListResponse,
  EvidenceSourceListResponse,
  ExportJobDetailResponse,
  ExportJobListResponse,
  ImportPublicDatasetRequest,
  LineageQueryResponse,
  ManuscriptBlockListResponse,
  ManuscriptDetailResponse,
  ManuscriptListResponse,
  ProjectDetailResponse,
  ProjectListResponse,
  ProjectMemberListResponse,
  RegisterUploadDatasetRequest,
  RenderManuscriptResponse,
  ResolveEvidenceRequest,
  ResolveEvidenceResponse,
  ReviewDecisionRequest,
  ReviewDecisionResponse,
  ReviewListResponse,
  RunVerificationRequest,
  RunVerificationResponse,
  TemplateDetailResponse,
  TemplateListResponse,
  UpdateProjectRequest,
  UpsertEvidenceSourceRequest,
  UpsertEvidenceSourceResponse,
  VerifyEvidenceLinkResponse,
  WorkflowDetailResponse,
  WorkflowListResponse,
} from "@/lib/api/generated/control-plane";
import { getControlPlaneBaseUrl } from "@/lib/config";

import { controlPlaneRoutes, type PaginationParams } from "@/lib/api/control-plane/endpoints";
import { parseError } from "@/lib/api/control-plane/errors";

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;
type QueryInput = QueryParams | PaginationParams;

interface NextFetchOptions {
  revalidate?: number | false;
  tags?: string[];
}

interface RequestOptions {
  body?: unknown;
  cache?: RequestCache;
  headers?: HeadersInit;
  next?: NextFetchOptions;
  query?: QueryInput;
  signal?: AbortSignal;
}

export interface ControlPlaneClientConfig {
  baseUrl?: string;
  cache?: RequestCache;
  headers?: HeadersInit;
  next?: NextFetchOptions;
}

function mergeHeaders(...headerSets: Array<HeadersInit | undefined>): Headers {
  const headers = new Headers();
  for (const headerSet of headerSets) {
    if (!headerSet) {
      continue;
    }
    new Headers(headerSet).forEach((value, key) => headers.set(key, value));
  }
  return headers;
}

export class ControlPlaneClient {
  private readonly baseUrl: string;
  private readonly cache: RequestCache | undefined;
  private readonly headers: HeadersInit | undefined;
  private readonly next: NextFetchOptions | undefined;

  constructor(config: ControlPlaneClientConfig = {}) {
    this.baseUrl = config.baseUrl ?? getControlPlaneBaseUrl();
    this.cache = config.cache;
    this.headers = config.headers;
    this.next = config.next;
  }

  async healthz(): Promise<{ status: string }> {
    return this.request("GET", controlPlaneRoutes.healthz());
  }

  async createProject(payload: CreateProjectRequest): Promise<CreateProjectResponse> {
    return this.request("POST", controlPlaneRoutes.projects.create(), { body: payload });
  }

  async listProjects(params: PaginationParams = {}): Promise<ProjectListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.list(), { query: params });
  }

  async getProject(projectId: string): Promise<ProjectDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.detail(projectId));
  }

  async updateProject(projectId: string, payload: UpdateProjectRequest): Promise<ProjectDetailResponse> {
    return this.request("PATCH", controlPlaneRoutes.projects.update(projectId), { body: payload });
  }

  async addProjectMember(projectId: string, payload: AddProjectMemberRequest): Promise<AddProjectMemberResponse> {
    return this.request("POST", controlPlaneRoutes.projects.members(projectId), { body: payload });
  }

  async listProjectMembers(projectId: string): Promise<ProjectMemberListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.members(projectId));
  }

  async listTemplates(): Promise<TemplateListResponse> {
    return this.request("GET", controlPlaneRoutes.templates.list());
  }

  async getTemplate(templateId: string): Promise<TemplateDetailResponse> {
    return this.request("GET", controlPlaneRoutes.templates.detail(templateId));
  }

  async importPublicDataset(
    projectId: string,
    payload: ImportPublicDatasetRequest,
  ): Promise<CreateDatasetResponse> {
    return this.request("POST", controlPlaneRoutes.projects.importPublicDataset(projectId), { body: payload });
  }

  async registerUploadDataset(
    projectId: string,
    payload: RegisterUploadDatasetRequest,
  ): Promise<CreateDatasetResponse> {
    return this.request("POST", controlPlaneRoutes.projects.registerUploadDataset(projectId), { body: payload });
  }

  async listDatasets(projectId: string, params: PaginationParams = {}): Promise<DatasetListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.datasets(projectId), { query: params });
  }

  async getDataset(projectId: string, datasetId: string): Promise<DatasetDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.dataset(projectId, datasetId));
  }

  async createDatasetSnapshot(
    projectId: string,
    datasetId: string,
    payload: CreateDatasetSnapshotRequest,
  ): Promise<CreateDatasetSnapshotResponse> {
    return this.request("POST", controlPlaneRoutes.projects.datasetSnapshots(projectId, datasetId), {
      body: payload,
    });
  }

  async listDatasetSnapshots(projectId: string, datasetId: string): Promise<DatasetSnapshotListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.datasetSnapshots(projectId, datasetId));
  }

  async runDatasetPolicyChecks(projectId: string, datasetId: string): Promise<DatasetPolicyCheckResponse> {
    return this.request("POST", controlPlaneRoutes.projects.datasetPolicyChecks(projectId, datasetId));
  }

  async createAnalysisPlan(
    projectId: string,
    payload: CreateAnalysisPlanRequest,
  ): Promise<CreateAnalysisPlanResponse> {
    return this.request("POST", controlPlaneRoutes.projects.analysisPlans(projectId), { body: payload });
  }

  async createWorkflow(projectId: string, payload: CreateWorkflowRequest): Promise<CreateWorkflowResponse> {
    return this.request("POST", controlPlaneRoutes.projects.workflows(projectId), { body: payload });
  }

  async listWorkflows(projectId: string, params: PaginationParams = {}): Promise<WorkflowListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.workflows(projectId), { query: params });
  }

  async getWorkflow(projectId: string, workflowId: string): Promise<WorkflowDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.workflow(projectId, workflowId));
  }

  async advanceWorkflow(
    projectId: string,
    workflowId: string,
    payload: AdvanceWorkflowRequest,
  ): Promise<WorkflowDetailResponse> {
    return this.request("POST", controlPlaneRoutes.projects.workflowAdvance(projectId, workflowId), {
      body: payload,
    });
  }

  async cancelWorkflow(
    projectId: string,
    workflowId: string,
    payload: CancelWorkflowRequest,
  ): Promise<WorkflowDetailResponse> {
    return this.request("POST", controlPlaneRoutes.projects.workflowCancel(projectId, workflowId), {
      body: payload,
    });
  }

  async createAnalysisRun(
    projectId: string,
    payload: CreateAnalysisRunRequest,
  ): Promise<CreateAnalysisRunResponse> {
    return this.request("POST", controlPlaneRoutes.projects.analysisRuns(projectId), { body: payload });
  }

  async listAnalysisRuns(projectId: string, params: PaginationParams = {}): Promise<AnalysisRunListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.analysisRuns(projectId), { query: params });
  }

  async getAnalysisRun(projectId: string, runId: string): Promise<AnalysisRunDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.analysisRun(projectId, runId));
  }

  async createArtifact(projectId: string, payload: CreateArtifactRequest): Promise<CreateArtifactResponse> {
    return this.request("POST", controlPlaneRoutes.projects.artifacts(projectId), { body: payload });
  }

  async listArtifacts(projectId: string, params: PaginationParams = {}): Promise<ArtifactListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.artifacts(projectId), { query: params });
  }

  async getArtifact(projectId: string, artifactId: string): Promise<ArtifactDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.artifact(projectId, artifactId));
  }

  async createLineageEdge(
    projectId: string,
    payload: CreateLineageEdgeRequest,
  ): Promise<CreateLineageEdgeResponse> {
    return this.request("POST", controlPlaneRoutes.projects.lineageEdges(projectId), { body: payload });
  }

  async getLineage(projectId: string): Promise<LineageQueryResponse> {
    return this.request("GET", controlPlaneRoutes.projects.lineage(projectId));
  }

  async createAssertion(projectId: string, payload: CreateAssertionRequest): Promise<CreateAssertionResponse> {
    return this.request("POST", controlPlaneRoutes.projects.assertions(projectId), { body: payload });
  }

  async listAssertions(projectId: string, params: PaginationParams = {}): Promise<AssertionListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.assertions(projectId), { query: params });
  }

  async getAssertion(projectId: string, assertionId: string): Promise<AssertionDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.assertion(projectId, assertionId));
  }

  async searchEvidence(
    projectId: string,
    payload: EvidenceSearchRequest,
  ): Promise<EvidenceSearchResponse> {
    return this.request("POST", controlPlaneRoutes.projects.evidenceSearch(projectId), { body: payload });
  }

  async resolveEvidence(
    projectId: string,
    payload: ResolveEvidenceRequest,
  ): Promise<ResolveEvidenceResponse> {
    return this.request("POST", controlPlaneRoutes.projects.evidenceResolve(projectId), { body: payload });
  }

  async upsertEvidenceSource(
    projectId: string,
    payload: UpsertEvidenceSourceRequest,
  ): Promise<UpsertEvidenceSourceResponse> {
    return this.request("POST", controlPlaneRoutes.projects.evidence(projectId), { body: payload });
  }

  async listEvidenceSources(projectId: string, params: PaginationParams = {}): Promise<EvidenceSourceListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.evidence(projectId), { query: params });
  }

  async createEvidenceChunk(
    projectId: string,
    evidenceSourceId: string,
    payload: CreateEvidenceChunkRequest,
  ): Promise<CreateEvidenceChunkResponse> {
    return this.request("POST", controlPlaneRoutes.projects.evidenceChunks(projectId, evidenceSourceId), {
      body: payload,
    });
  }

  async listEvidenceChunks(
    projectId: string,
    evidenceSourceId: string,
    params: PaginationParams = {},
  ): Promise<EvidenceChunkListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.evidenceChunks(projectId, evidenceSourceId), {
      query: params,
    });
  }

  async getEvidenceChunk(projectId: string, chunkId: string): Promise<EvidenceChunkDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.evidenceChunk(projectId, chunkId));
  }

  async listEvidenceLinks(projectId: string, params: PaginationParams = {}): Promise<EvidenceLinkListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.evidenceLinks(projectId), { query: params });
  }

  async getEvidenceLink(projectId: string, linkId: string): Promise<EvidenceLinkDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.evidenceLink(projectId, linkId));
  }

  async createEvidenceLink(
    projectId: string,
    payload: CreateEvidenceLinkRequest,
  ): Promise<CreateEvidenceLinkResponse> {
    return this.request("POST", controlPlaneRoutes.projects.evidenceLinks(projectId), { body: payload });
  }

  async verifyEvidenceLink(projectId: string, linkId: string): Promise<VerifyEvidenceLinkResponse> {
    return this.request("POST", controlPlaneRoutes.projects.verifyEvidenceLink(projectId, linkId));
  }

  async createManuscript(
    projectId: string,
    payload: CreateManuscriptRequest,
  ): Promise<CreateManuscriptResponse> {
    return this.request("POST", controlPlaneRoutes.projects.manuscripts(projectId), { body: payload });
  }

  async listManuscripts(projectId: string): Promise<ManuscriptListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.manuscripts(projectId));
  }

  async getManuscript(projectId: string, manuscriptId: string): Promise<ManuscriptDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.manuscript(projectId, manuscriptId));
  }

  async createManuscriptBlock(
    projectId: string,
    manuscriptId: string,
    payload: CreateManuscriptBlockRequest,
  ): Promise<CreateManuscriptBlockResponse> {
    return this.request("POST", controlPlaneRoutes.projects.manuscriptBlocks(projectId, manuscriptId), {
      body: payload,
    });
  }

  async listManuscriptBlocks(projectId: string, manuscriptId: string): Promise<ManuscriptBlockListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.manuscriptBlocks(projectId, manuscriptId));
  }

  async createManuscriptVersion(
    projectId: string,
    manuscriptId: string,
    payload: CreateManuscriptVersionRequest,
  ): Promise<CreateManuscriptVersionResponse> {
    return this.request("POST", controlPlaneRoutes.projects.manuscriptVersions(projectId, manuscriptId), {
      body: payload,
    });
  }

  async renderManuscript(projectId: string, manuscriptId: string): Promise<RenderManuscriptResponse> {
    return this.request("POST", controlPlaneRoutes.projects.manuscriptRender(projectId, manuscriptId));
  }

  async createReview(projectId: string, payload: CreateReviewRequest): Promise<CreateReviewResponse> {
    return this.request("POST", controlPlaneRoutes.projects.reviews(projectId), { body: payload });
  }

  async listReviews(projectId: string, params: PaginationParams = {}): Promise<ReviewListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.reviews(projectId), { query: params });
  }

  async decideReview(
    projectId: string,
    reviewId: string,
    payload: ReviewDecisionRequest,
  ): Promise<ReviewDecisionResponse> {
    return this.request("POST", controlPlaneRoutes.projects.reviewDecision(projectId, reviewId), { body: payload });
  }

  async runVerification(
    projectId: string,
    payload: RunVerificationRequest,
  ): Promise<RunVerificationResponse> {
    return this.request("POST", controlPlaneRoutes.projects.verify(projectId), { body: payload });
  }

  async createExportJob(
    projectId: string,
    payload: CreateExportJobRequest,
  ): Promise<CreateExportJobResponse> {
    return this.request("POST", controlPlaneRoutes.projects.exports(projectId), { body: payload });
  }

  async getExportJob(projectId: string, exportJobId: string): Promise<ExportJobDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.exportJob(projectId, exportJobId));
  }

  async listExportJobs(projectId: string, params: PaginationParams = {}): Promise<ExportJobListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.exports(projectId), { query: params });
  }

  async listAuditEvents(projectId: string, params: PaginationParams = {}): Promise<AuditEventListResponse> {
    return this.request("GET", controlPlaneRoutes.projects.auditEvents(projectId), { query: params });
  }

  async getAuditEvent(projectId: string, eventId: string): Promise<AuditEventDetailResponse> {
    return this.request("GET", controlPlaneRoutes.projects.auditEvent(projectId, eventId));
  }

  async replayAuditChain(): Promise<AuditReplayResponse> {
    return this.request("POST", controlPlaneRoutes.internalAuditReplay());
  }

  private async request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
    const url = this.buildUrl(path, options.query);
    const headers = new Headers(this.headers);
    if (options.headers) {
      new Headers(options.headers).forEach((value, key) => headers.set(key, value));
    }

    const init: RequestInit & { next?: NextFetchOptions } = {
      method,
      headers,
      cache: options.cache ?? this.cache,
      next: options.next ?? this.next,
      signal: options.signal,
    };

    if (options.body !== undefined) {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, init);
    if (!response.ok) {
      throw await parseError(response);
    }

    return (await response.json()) as T;
  }

  private buildUrl(path: string, query?: QueryParams): string {
    const url = new URL(path, this.baseUrl);
    if (!query) {
      return url.toString();
    }

    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null) {
        continue;
      }
      url.searchParams.set(key, String(value));
    }

    return url.toString();
  }
}

export function createControlPlaneClient(config: ControlPlaneClientConfig = {}): ControlPlaneClient {
  return new ControlPlaneClient(config);
}

export async function createServerControlPlaneClient(
  config: ControlPlaneClientConfig = {},
): Promise<ControlPlaneClient> {
  const { getForwardedAuthHeaders } = await import("@/lib/api/auth-headers.server");
  return new ControlPlaneClient({
    ...config,
    headers: mergeHeaders(await getForwardedAuthHeaders(), config.headers),
  });
}

import type { GatewayClient } from "@/lib/api/gateway/interface";
import type {
  ProjectEvent,
  SessionRead,
  SignUploadInput,
  SignedArtifactUrlResult,
  SignedUploadResult,
  UploadCompleteInput,
  UploadCompleteResult,
} from "@/lib/api/gateway/types";

const mockSession: SessionRead = {
  actor_id: "principal_mock_user",
  principal_id: "principal_mock_user",
  tenant_id: "tenant_mock",
  scopes_json: {
    role: "owner",
  },
};

export const mockGatewayClient: GatewayClient = {
  async getSession(): Promise<SessionRead | null> {
    return mockSession;
  },
  async signUpload(input: SignUploadInput): Promise<SignedUploadResult> {
    return {
      upload_url: "https://example.invalid/upload",
      object_key: `mock/${input.filename}`,
      expires_in_seconds: 900,
    };
  },
  async completeUpload(input: UploadCompleteInput): Promise<UploadCompleteResult> {
    return {
      file_ref: `file://${input.object_key}`,
    };
  },
  subscribeProjectEvents(projectId: string, onEvent: (event: ProjectEvent) => void): () => void {
    const timer = setTimeout(() => {
      onEvent({
        event_id: "evt_mock",
        event_name: "workflow.started",
        schema_version: "1.0.0",
        produced_by: "gateway.mock",
        trace_id: "trace_mock",
        request_id: "req_mock",
        tenant_id: mockSession.tenant_id,
        project_id: projectId,
        idempotency_key: "workflow_mock",
        occurred_at: new Date().toISOString(),
        payload: {
          note: "Mock project event",
        },
      });
    }, 500);

    return () => clearTimeout(timer);
  },
  async getArtifactDownloadUrl(_: string, artifactId: string): Promise<SignedArtifactUrlResult> {
    return {
      download_url: `https://example.invalid/artifacts/${artifactId}`,
      expires_in_seconds: 900,
    };
  },
};

import type {
  ProjectEvent,
  SessionRead,
  SignUploadInput,
  SignedArtifactUrlResult,
  SignedUploadResult,
  UploadCompleteInput,
  UploadCompleteResult,
} from "@/lib/api/gateway/types";

export interface GatewayClient {
  getSession(): Promise<SessionRead | null>;
  signUpload(input: SignUploadInput): Promise<SignedUploadResult>;
  completeUpload(input: UploadCompleteInput): Promise<UploadCompleteResult>;
  subscribeProjectEvents(projectId: string, onEvent: (event: ProjectEvent) => void): () => void;
  getArtifactDownloadUrl(projectId: string, artifactId: string): Promise<SignedArtifactUrlResult>;
}

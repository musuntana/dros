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

function notReady(feature: string): never {
  throw new Error(`Gateway adapter is not configured for ${feature}.`);
}

export const disabledGatewayClient: GatewayClient = {
  async getSession(): Promise<SessionRead | null> {
    return null;
  },
  async signUpload(_: SignUploadInput): Promise<SignedUploadResult> {
    return notReady("signed uploads");
  },
  async completeUpload(_: UploadCompleteInput): Promise<UploadCompleteResult> {
    return notReady("upload completion");
  },
  subscribeProjectEvents(_: string, __: (event: ProjectEvent) => void): () => void {
    return () => undefined;
  },
  async getArtifactDownloadUrl(_: string, __: string): Promise<SignedArtifactUrlResult> {
    return notReady("artifact download URLs");
  },
};

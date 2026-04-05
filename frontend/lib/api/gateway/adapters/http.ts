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
import { parseError } from "@/lib/api/control-plane/errors";
import { getGatewayBaseUrl } from "@/lib/config";

interface HttpGatewayClientConfig {
  headers?: HeadersInit;
}

interface RequestOptions {
  body?: unknown;
  headers?: HeadersInit;
}

function buildBrowserProjectEventsUrl(projectId: string): string {
  if (typeof window === "undefined") {
    return new URL(`/v1/projects/${projectId}/events`, getGatewayBaseUrl()).toString();
  }

  return new URL(`/api/projects/${projectId}/events`, window.location.origin).toString();
}

async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const url = new URL(path, getGatewayBaseUrl());
  const headers = new Headers(options.headers);
  const init: RequestInit = { method, headers };

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

export function createHttpGatewayClient(config: HttpGatewayClientConfig = {}): GatewayClient {
  return {
    async getSession(): Promise<SessionRead | null> {
      return request<SessionRead>("GET", "/v1/session", { headers: config.headers });
    },
    async signUpload(input: SignUploadInput): Promise<SignedUploadResult> {
      return request<SignedUploadResult>("POST", "/v1/uploads/sign", {
        body: input,
        headers: config.headers,
      });
    },
    async completeUpload(input: UploadCompleteInput): Promise<UploadCompleteResult> {
      return request<UploadCompleteResult>("POST", "/v1/uploads/complete", {
        body: input,
        headers: config.headers,
      });
    },
    subscribeProjectEvents(projectId: string, onEvent: (event: ProjectEvent) => void): () => void {
      if (typeof window === "undefined") {
        return () => undefined;
      }

      const source = new EventSource(buildBrowserProjectEventsUrl(projectId));
      source.onmessage = (message) => {
        try {
          onEvent(JSON.parse(message.data) as ProjectEvent);
        } catch {
          // Ignore malformed frames so the stream can continue.
        }
      };

      return () => source.close();
    },
    async getArtifactDownloadUrl(projectId: string, artifactId: string): Promise<SignedArtifactUrlResult> {
      return request<SignedArtifactUrlResult>(
        "GET",
        `/v1/projects/${projectId}/artifacts/${artifactId}/download-url`,
        { headers: config.headers },
      );
    },
  };
}

export const httpGatewayClient: GatewayClient = createHttpGatewayClient();

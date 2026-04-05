import { disabledGatewayClient } from "@/lib/api/gateway/adapters/disabled";
import { createHttpGatewayClient, httpGatewayClient } from "@/lib/api/gateway/adapters/http";
import { mockGatewayClient } from "@/lib/api/gateway/adapters/mock";
import type { GatewayClient } from "@/lib/api/gateway/interface";

interface GatewayClientConfig {
  headers?: HeadersInit;
  mode?: string;
}

function normalizeGatewayClientConfig(config: GatewayClientConfig | string | undefined): GatewayClientConfig {
  if (typeof config === "string" || config === undefined) {
    return { mode: config };
  }
  return config;
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

export function createGatewayClient(config?: GatewayClientConfig | string): GatewayClient {
  const resolved = normalizeGatewayClientConfig(config);
  const mode = resolved.mode ?? process.env.NEXT_PUBLIC_GATEWAY_MODE ?? "http";
  if (mode === "mock") {
    return mockGatewayClient;
  }

  if (mode === "disabled") {
    return disabledGatewayClient;
  }

  if (!resolved.headers) {
    return httpGatewayClient;
  }

  return createHttpGatewayClient({ headers: resolved.headers });
}

export { mergeHeaders };

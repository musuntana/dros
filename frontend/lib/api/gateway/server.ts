import "server-only";

import { getForwardedAuthHeaders } from "@/lib/api/auth-headers.server";
import { createGatewayClient, mergeHeaders } from "@/lib/api/gateway/client";
import type { GatewayClient } from "@/lib/api/gateway/interface";

interface GatewayClientConfig {
  headers?: HeadersInit;
  mode?: string;
}

export async function createServerGatewayClient(config?: GatewayClientConfig | string): Promise<GatewayClient> {
  const resolved = typeof config === "string" || config === undefined ? { mode: config } : config;
  return createGatewayClient({
    ...resolved,
    headers: mergeHeaders(await getForwardedAuthHeaders(), resolved.headers),
  });
}

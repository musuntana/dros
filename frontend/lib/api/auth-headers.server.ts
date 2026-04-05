import "server-only";

import { headers } from "next/headers";

type ForwardedAuthHeaderName = (typeof FORWARDED_AUTH_HEADERS)[number];

const FORWARDED_AUTH_HEADERS = [
  "x-dros-tenant-id",
  "x-dros-actor-id",
  "x-dros-principal-id",
  "x-dros-project-role",
  "x-dros-scopes",
  "x-request-id",
  "x-trace-id",
] as const;

function resolveEnvHeaderValue(headerName: ForwardedAuthHeaderName): string | undefined {
  switch (headerName) {
    case "x-dros-tenant-id":
      return process.env.DROS_AUTH_TENANT_ID;
    case "x-dros-actor-id":
      return process.env.DROS_AUTH_ACTOR_ID ?? process.env.DROS_AUTH_PRINCIPAL_ID;
    case "x-dros-principal-id":
      return process.env.DROS_AUTH_PRINCIPAL_ID ?? process.env.DROS_AUTH_ACTOR_ID;
    case "x-dros-project-role":
      return process.env.DROS_AUTH_PROJECT_ROLE;
    case "x-dros-scopes":
      return process.env.DROS_AUTH_SCOPES;
    case "x-request-id":
      return process.env.DROS_AUTH_REQUEST_ID;
    case "x-trace-id":
      return process.env.DROS_AUTH_TRACE_ID;
    default:
      return undefined;
  }
}

export function buildForwardedAuthHeaders(sourceHeaders?: HeadersInit): Headers {
  const requestHeaders = new Headers(sourceHeaders);
  const forwarded = new Headers();

  for (const headerName of FORWARDED_AUTH_HEADERS) {
    const value = requestHeaders.get(headerName) ?? resolveEnvHeaderValue(headerName);
    if (value) {
      forwarded.set(headerName, value);
    }
  }

  if (!forwarded.has("x-dros-actor-id") && forwarded.has("x-dros-principal-id")) {
    forwarded.set("x-dros-actor-id", forwarded.get("x-dros-principal-id") ?? "");
  }

  if (!forwarded.has("x-dros-principal-id") && forwarded.has("x-dros-actor-id")) {
    forwarded.set("x-dros-principal-id", forwarded.get("x-dros-actor-id") ?? "");
  }

  return forwarded;
}

export async function getForwardedAuthHeaders(): Promise<Headers> {
  return buildForwardedAuthHeaders(await headers());
}

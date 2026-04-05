import { buildForwardedAuthHeaders } from "@/lib/api/auth-headers.server";
import { getGatewayBaseUrl } from "@/lib/config";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
): Promise<Response> {
  const { projectId } = await context.params;
  const incomingUrl = new URL(request.url);
  const upstreamUrl = new URL(`/v1/projects/${projectId}/events`, getGatewayBaseUrl());

  if (incomingUrl.searchParams.has("once")) {
    upstreamUrl.searchParams.set("once", incomingUrl.searchParams.get("once") ?? "false");
  }

  const upstreamResponse = await fetch(upstreamUrl, {
    cache: "no-store",
    headers: buildForwardedAuthHeaders(request.headers),
    signal: request.signal,
  });

  if (!upstreamResponse.ok || upstreamResponse.body === null) {
    return new Response(await upstreamResponse.text(), {
      headers: {
        "Content-Type": upstreamResponse.headers.get("content-type") ?? "text/plain; charset=utf-8",
      },
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
    });
  }

  return new Response(upstreamResponse.body, {
    headers: {
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Type": upstreamResponse.headers.get("content-type") ?? "text/event-stream; charset=utf-8",
      "X-Accel-Buffering": "no",
    },
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
  });
}

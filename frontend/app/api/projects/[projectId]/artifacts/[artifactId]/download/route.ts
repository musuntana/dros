import { readFile } from "node:fs/promises";
import { extname } from "node:path";
import { fileURLToPath } from "node:url";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import { createServerGatewayClient } from "@/lib/api/gateway/server";

export const runtime = "nodejs";

function buildFilename(artifactId: string, artifactType: string, downloadUrl: string): string {
  const extension = extname(fileURLToPath(downloadUrl));
  return `${artifactType}-${artifactId.slice(0, 8)}${extension}`;
}

export async function GET(
  _: Request,
  context: { params: Promise<{ artifactId: string; projectId: string }> },
): Promise<Response> {
  try {
    const { artifactId, projectId } = await context.params;
    const gateway = await createServerGatewayClient();
    const controlPlane = await createServerControlPlaneClient({ cache: "no-store" });
    const [signedUrl, artifactDetail] = await Promise.all([
      gateway.getArtifactDownloadUrl(projectId, artifactId),
      controlPlane.getArtifact(projectId, artifactId),
    ]);

    if (!signedUrl.download_url.startsWith("file://")) {
      return Response.redirect(signedUrl.download_url, 302);
    }

    const buffer = await readFile(fileURLToPath(signedUrl.download_url));
    const filename = buildFilename(artifactId, artifactDetail.artifact.artifact_type, signedUrl.download_url);
    return new Response(buffer, {
      headers: {
        "Cache-Control": "no-store",
        "Content-Disposition": `attachment; filename="${filename}"`,
        "Content-Type": artifactDetail.artifact.mime_type ?? "application/octet-stream",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Artifact download failed";
    return Response.json({ detail: message }, { status: 404 });
  }
}

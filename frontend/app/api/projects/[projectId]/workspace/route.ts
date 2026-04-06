import { getProjectWorkspaceData } from "@/features/projects/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ projectId: string }> },
): Promise<Response> {
  const { projectId } = await context.params;

  try {
    const workspace = await getProjectWorkspaceData(projectId);
    return Response.json(workspace, {
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown request failure";
    return Response.json({ detail: message }, { status: 500 });
  }
}

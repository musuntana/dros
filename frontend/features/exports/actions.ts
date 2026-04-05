"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { ExportFormat } from "@/lib/api/generated/control-plane";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import {
  type FormActionState,
  getErrorMessage,
  getString,
} from "@/lib/server-actions/forms";

export type ExportActionState = FormActionState;

const EXPORT_FORMATS = new Set<ExportFormat>(["docx", "pdf", "zip"]);

export async function createExportJobAction(
  projectId: string,
  _: ExportActionState,
  formData: FormData,
): Promise<ExportActionState> {
  const manuscriptId = getString(formData, "manuscript_id");
  const formatRaw = getString(formData, "format");
  const format = EXPORT_FORMATS.has(formatRaw as ExportFormat) ? (formatRaw as ExportFormat) : undefined;

  if (manuscriptId === "" || formatRaw === "") {
    return {
      message: "manuscript_id and format are required.",
      status: "error",
    };
  }

  if (format === undefined) {
    return {
      message: "format is invalid.",
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.createExportJob(projectId, {
      format,
      manuscript_id: manuscriptId,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/exports`);
  revalidatePath(`/projects/${projectId}/artifacts`);

  if (response.export_job.output_artifact_id) {
    redirect(`/projects/${projectId}/artifacts/${response.export_job.output_artifact_id}`);
  }

  return {
    message: `Export job ${response.export_job.id.slice(0, 8)} created with state ${response.export_job.state}.`,
    status: "success",
  };
}

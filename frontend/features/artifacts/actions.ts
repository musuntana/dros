"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { ArtifactType } from "@/lib/api/generated/control-plane";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import {
  deriveSha256,
  type FormActionState,
  getErrorMessage,
  getOptionalNumber,
  getOptionalString,
  getString,
  parseJsonObject,
} from "@/lib/server-actions/forms";

export type ArtifactActionState = FormActionState;

const ARTIFACT_TYPES = new Set<ArtifactType>([
  "dataset_snapshot",
  "result_json",
  "table",
  "figure",
  "log",
  "manifest",
  "docx",
  "pdf",
  "zip",
  "evidence_attachment",
]);

export async function createArtifactAction(
  projectId: string,
  _: ArtifactActionState,
  formData: FormData,
): Promise<ArtifactActionState> {
  const artifactTypeRaw = getString(formData, "artifact_type");
  const storageUri = getString(formData, "storage_uri");
  const sha256 = getOptionalString(formData, "sha256");
  const runId = getOptionalString(formData, "run_id");
  const mimeType = getOptionalString(formData, "mime_type");
  const sizeBytes = getOptionalNumber(formData, "size_bytes");
  const metadataInput = getString(formData, "metadata_json");
  const artifactType = ARTIFACT_TYPES.has(artifactTypeRaw as ArtifactType)
    ? (artifactTypeRaw as ArtifactType)
    : undefined;

  if (artifactTypeRaw === "" || storageUri === "") {
    return {
      message: "artifact_type and storage_uri are required.",
      status: "error",
    };
  }

  if (artifactType === undefined) {
    return {
      message: "artifact_type is invalid.",
      status: "error",
    };
  }

  let metadataJson: Record<string, unknown>;
  try {
    metadataJson = parseJsonObject(metadataInput, "metadata_json");
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.createArtifact(projectId, {
      artifact_type: artifactType,
      metadata_json: metadataJson,
      mime_type: mimeType,
      run_id: runId,
      sha256: sha256 ?? deriveSha256(`${artifactType}:${storageUri}`),
      size_bytes: sizeBytes,
      storage_uri: storageUri,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/artifacts`);
  redirect(`/projects/${projectId}/artifacts/${response.artifact.id}`);
}

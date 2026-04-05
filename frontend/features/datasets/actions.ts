"use server";

import { createHash } from "node:crypto";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import { ControlPlaneError } from "@/lib/api/control-plane/errors";
import { createServerGatewayClient } from "@/lib/api/gateway/server";
import { uploadSignedBuffer } from "@/lib/api/gateway/upload";

export interface DatasetActionState {
  message: string | null;
  status: "idle" | "error";
}

function getString(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function getFile(formData: FormData, key: string): File | null {
  const value = formData.get(key);
  if (!(value instanceof File) || value.size === 0) {
    return null;
  }
  return value;
}

function getOptionalNumber(formData: FormData, key: string): number | undefined {
  const value = getString(formData, key);
  if (value === "") {
    return undefined;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function parseColumnSchema(input: string): Record<string, unknown> {
  if (input.trim() === "") {
    return {};
  }

  const parsed = JSON.parse(input);
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("column_schema_json must be a JSON object.");
  }

  return parsed as Record<string, unknown>;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ControlPlaneError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown request failure";
}

export async function importPublicDatasetAction(
  projectId: string,
  _: DatasetActionState,
  formData: FormData,
): Promise<DatasetActionState> {
  const accession = getString(formData, "accession");
  const sourceKind = getString(formData, "source_kind");

  if (accession === "" || sourceKind === "") {
    return {
      message: "accession and source_kind are required.",
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.importPublicDataset(projectId, {
      accession,
      source_kind: sourceKind,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/datasets`);
  redirect(`/projects/${projectId}/datasets/${response.dataset.id}`);
}

export async function registerUploadDatasetAction(
  projectId: string,
  _: DatasetActionState,
  formData: FormData,
): Promise<DatasetActionState> {
  const displayName = getString(formData, "display_name");
  const file = getFile(formData, "file");
  const fallbackFileRef = getString(formData, "file_ref");

  if (displayName === "" || (file === null && fallbackFileRef === "")) {
    return {
      message: "display_name and an uploaded file are required.",
      status: "error",
    };
  }

  let response;
  try {
    let fileRef = fallbackFileRef;
    if (file !== null) {
      const gateway = await createServerGatewayClient();
      const buffer = Buffer.from(await file.arrayBuffer());
      const sha256 = createHash("sha256").update(buffer).digest("hex");
      const signedUpload = await gateway.signUpload({
        filename: file.name || `${displayName}.bin`,
        content_type: file.type || "application/octet-stream",
        size_bytes: file.size,
      });
      await uploadSignedBuffer(signedUpload.upload_url, buffer, file.type || "application/octet-stream");
      const completedUpload = await gateway.completeUpload({
        object_key: signedUpload.object_key,
        sha256,
      });
      fileRef = completedUpload.file_ref;
    }

    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.registerUploadDataset(projectId, {
      display_name: displayName,
      file_ref: fileRef,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/datasets`);
  redirect(`/projects/${projectId}/datasets/${response.dataset.id}`);
}

export async function createSnapshotAction(
  projectId: string,
  datasetId: string,
  _: DatasetActionState,
  formData: FormData,
): Promise<DatasetActionState> {
  const objectUri = getString(formData, "object_uri");
  const providedHash = getString(formData, "input_hash_sha256");
  const rowCount = getOptionalNumber(formData, "row_count");
  const columnSchemaInput = getString(formData, "column_schema_json");

  if (objectUri === "") {
    return {
      message: "object_uri is required.",
      status: "error",
    };
  }

  let columnSchemaJson: Record<string, unknown>;
  try {
    columnSchemaJson = parseColumnSchema(columnSchemaInput);
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  const inputHashSha256 =
    providedHash !== "" ? providedHash : createHash("sha256").update(objectUri).digest("hex");

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    await client.createDatasetSnapshot(projectId, datasetId, {
      object_uri: objectUri,
      input_hash_sha256: inputHashSha256,
      row_count: rowCount,
      column_schema_json: columnSchemaJson,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/datasets`);
  revalidatePath(`/projects/${projectId}/datasets/${datasetId}`);
  redirect(`/projects/${projectId}/datasets/${datasetId}`);
}

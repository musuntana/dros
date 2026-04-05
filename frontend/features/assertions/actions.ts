"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { AssertionType } from "@/lib/api/generated/control-plane";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import {
  deriveSha256,
  type FormActionState,
  getErrorMessage,
  getOptionalString,
  getString,
  parseJsonObject,
} from "@/lib/server-actions/forms";

export type AssertionActionState = FormActionState;

const ASSERTION_TYPES = new Set<AssertionType>(["background", "method", "result", "limitation"]);

export async function createAssertionAction(
  projectId: string,
  _: AssertionActionState,
  formData: FormData,
): Promise<AssertionActionState> {
  const assertionTypeRaw = getString(formData, "assertion_type");
  const textNorm = getString(formData, "text_norm");
  const claimHash = getOptionalString(formData, "claim_hash");
  const numericPayloadInput = getString(formData, "numeric_payload_json");
  const sourceArtifactId = getOptionalString(formData, "source_artifact_id");
  const sourceRunId = getOptionalString(formData, "source_run_id");
  const sourceSpanInput = getString(formData, "source_span_json");
  const supersedesAssertionId = getOptionalString(formData, "supersedes_assertion_id");
  const assertionType = ASSERTION_TYPES.has(assertionTypeRaw as AssertionType)
    ? (assertionTypeRaw as AssertionType)
    : undefined;

  if (assertionTypeRaw === "" || textNorm === "") {
    return {
      message: "assertion_type and text_norm are required.",
      status: "error",
    };
  }

  if (assertionType === undefined) {
    return {
      message: "assertion_type is invalid.",
      status: "error",
    };
  }

  if (!sourceArtifactId && !sourceRunId) {
    return {
      message: "Provide source_artifact_id or source_run_id.",
      status: "error",
    };
  }

  let numericPayloadJson: Record<string, unknown>;
  let sourceSpanJson: Record<string, unknown>;
  try {
    numericPayloadJson = parseJsonObject(numericPayloadInput, "numeric_payload_json");
    sourceSpanJson = parseJsonObject(sourceSpanInput, "source_span_json");
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.createAssertion(projectId, {
      assertion_type: assertionType,
      claim_hash: claimHash ?? deriveSha256(textNorm),
      numeric_payload_json: numericPayloadJson,
      source_artifact_id: sourceArtifactId,
      source_run_id: sourceRunId,
      source_span_json: sourceSpanJson,
      supersedes_assertion_id: supersedesAssertionId,
      text_norm: textNorm,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/assertions`);
  redirect(`/projects/${projectId}/assertions/${response.assertion.id}`);
}

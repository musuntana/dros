"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { LineageKind, ReviewType } from "@/lib/api/generated/control-plane";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import {
  type FormActionState,
  getErrorMessage,
  getOptionalNumber,
  getOptionalString,
  getString,
  getStringList,
  parseJsonArray,
} from "@/lib/server-actions/forms";

export type ReviewActionState = FormActionState;

const REVIEW_TYPES = new Set<ReviewType>(["evidence", "analysis", "manuscript", "export"]);
const REVIEW_TARGET_KINDS = new Set<LineageKind>(["manuscript", "assertion", "artifact", "export_job"]);

export async function createReviewAction(
  projectId: string,
  _: ReviewActionState,
  formData: FormData,
): Promise<ReviewActionState> {
  const reviewTypeRaw = getString(formData, "review_type");
  const targetKindRaw = getString(formData, "target_kind");
  const targetId = getString(formData, "target_id");
  const targetVersionNoRaw = getOptionalString(formData, "target_version_no");
  const reviewerId = getOptionalString(formData, "reviewer_id");
  const comments = getOptionalString(formData, "comments");
  const checklistInput = getString(formData, "checklist_json");
  const reviewType = REVIEW_TYPES.has(reviewTypeRaw as ReviewType) ? (reviewTypeRaw as ReviewType) : undefined;
  const targetKind = REVIEW_TARGET_KINDS.has(targetKindRaw as LineageKind)
    ? (targetKindRaw as LineageKind)
    : undefined;
  const targetVersionNo = getOptionalNumber(formData, "target_version_no");

  if (reviewTypeRaw === "" || targetKindRaw === "" || targetId === "") {
    return {
      message: "review_type, target_kind, and target_id are required.",
      status: "error",
    };
  }

  if (reviewType === undefined) {
    return {
      message: "review_type is invalid.",
      status: "error",
    };
  }

  if (targetKind === undefined) {
    return {
      message: "target_kind is invalid.",
      status: "error",
    };
  }

  if (
    targetVersionNoRaw !== undefined &&
    (targetVersionNo === undefined || !Number.isInteger(targetVersionNo) || targetVersionNo < 1)
  ) {
    return {
      message: "target_version_no must be a positive integer.",
      status: "error",
    };
  }

  let checklistJson;
  try {
    checklistJson = parseJsonArray(checklistInput, "checklist_json");
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    await client.createReview(projectId, {
      checklist_json: checklistJson,
      comments,
      review_type: reviewType,
      reviewer_id: reviewerId,
      target_id: targetId,
      target_kind: targetKind,
      target_version_no: targetVersionNo,
    });
    revalidatePath(`/projects/${projectId}`);
    revalidatePath(`/projects/${projectId}/reviews`);
    return {
      message: "Review created.",
      status: "success",
    };
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }
}

export async function decideReviewAction(
  projectId: string,
  reviewId: string,
  action: string,
  formData: FormData,
): Promise<void> {
  const comments = getOptionalString(formData, "comments");
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  await client.decideReview(projectId, reviewId, {
    action,
    comments,
  });
  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/reviews`);
  redirect(`/projects/${projectId}/reviews`);
}

export async function runVerificationAction(
  projectId: string,
  _: ReviewActionState,
  formData: FormData,
): Promise<ReviewActionState> {
  const manuscriptId = getOptionalString(formData, "manuscript_id");
  const targetIds = getStringList(formData, "target_ids");

  if (!manuscriptId && targetIds.length === 0) {
    return {
      message: "Provide manuscript_id or target_ids.",
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.runVerification(projectId, {
      manuscript_id: manuscriptId,
      target_ids: targetIds,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}/reviews`);
  revalidatePath(`/projects/${projectId}/workflows`);
  redirect(`/projects/${projectId}/workflows/${response.workflow_instance_id}`);
}

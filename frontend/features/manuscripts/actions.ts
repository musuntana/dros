"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { BlockType, ManuscriptType, SectionKey } from "@/lib/api/generated/control-plane";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import {
  type FormActionState,
  getErrorMessage,
  getOptionalNumber,
  getOptionalString,
  getString,
  getStringList,
  parseJsonObject,
} from "@/lib/server-actions/forms";

export type ManuscriptActionState = FormActionState;

const MANUSCRIPT_TYPES = new Set<ManuscriptType>(["manuscript", "abstract", "grant_response"]);
const BLOCK_TYPES = new Set<BlockType>(["text", "figure", "table", "citation_list"]);
const SECTION_KEYS = new Set<SectionKey>([
  "title",
  "abstract",
  "introduction",
  "methods",
  "results",
  "discussion",
  "conclusion",
  "figure_legend",
  "table_note",
  "appendix",
]);

export async function createManuscriptAction(
  projectId: string,
  _: ManuscriptActionState,
  formData: FormData,
): Promise<ManuscriptActionState> {
  const title = getString(formData, "title");
  const manuscriptTypeRaw = getOptionalString(formData, "manuscript_type");
  const targetJournal = getOptionalString(formData, "target_journal");
  const styleProfileInput = getString(formData, "style_profile_json");
  const manuscriptType =
    manuscriptTypeRaw && MANUSCRIPT_TYPES.has(manuscriptTypeRaw as ManuscriptType)
      ? (manuscriptTypeRaw as ManuscriptType)
      : undefined;

  if (title === "") {
    return {
      message: "title is required.",
      status: "error",
    };
  }

  if (manuscriptTypeRaw && manuscriptType === undefined) {
    return {
      message: "manuscript_type is invalid.",
      status: "error",
    };
  }

  let styleProfileJson: Record<string, unknown>;
  try {
    styleProfileJson = parseJsonObject(styleProfileInput, "style_profile_json");
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.createManuscript(projectId, {
      manuscript_type: manuscriptType,
      style_profile_json: styleProfileJson,
      target_journal: targetJournal,
      title,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/manuscripts`);
  redirect(`/projects/${projectId}/manuscripts/${response.manuscript.id}`);
}

export async function createManuscriptBlockAction(
  projectId: string,
  manuscriptId: string,
  _: ManuscriptActionState,
  formData: FormData,
): Promise<ManuscriptActionState> {
  const sectionKeyRaw = getString(formData, "section_key");
  const contentMd = getString(formData, "content_md");
  const assertionIds = getStringList(formData, "assertion_ids");
  const blockOrder = getOptionalNumber(formData, "block_order");
  const blockTypeRaw = getOptionalString(formData, "block_type");
  const sectionKey = SECTION_KEYS.has(sectionKeyRaw as SectionKey) ? (sectionKeyRaw as SectionKey) : undefined;
  const blockType =
    blockTypeRaw && BLOCK_TYPES.has(blockTypeRaw as BlockType)
      ? (blockTypeRaw as BlockType)
      : undefined;

  if (sectionKeyRaw === "" || contentMd === "") {
    return {
      message: "section_key and content_md are required.",
      status: "error",
    };
  }

  if (sectionKey === undefined) {
    return {
      message: "section_key is invalid.",
      status: "error",
    };
  }

  if (blockTypeRaw && blockType === undefined) {
    return {
      message: "block_type is invalid.",
      status: "error",
    };
  }

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    await client.createManuscriptBlock(projectId, manuscriptId, {
      assertion_ids: assertionIds,
      block_order: blockOrder,
      block_type: blockType,
      content_md: contentMd,
      section_key: sectionKey,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/manuscripts`);
  revalidatePath(`/projects/${projectId}/manuscripts/${manuscriptId}`);
  redirect(`/projects/${projectId}/manuscripts/${manuscriptId}`);
}

export async function createManuscriptVersionAction(
  projectId: string,
  manuscriptId: string,
  _: ManuscriptActionState,
  formData: FormData,
): Promise<ManuscriptActionState> {
  const baseVersionNo = getOptionalNumber(formData, "base_version_no");
  const reason = getOptionalString(formData, "reason");

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    await client.createManuscriptVersion(projectId, manuscriptId, {
      base_version_no: baseVersionNo,
      reason,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  revalidatePath(`/projects/${projectId}`);
  revalidatePath(`/projects/${projectId}/manuscripts`);
  revalidatePath(`/projects/${projectId}/manuscripts/${manuscriptId}`);
  redirect(`/projects/${projectId}/manuscripts/${manuscriptId}`);
}

"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type {
  EvidenceRelationType,
  EvidenceSourceRead,
  EvidenceSourceType,
  LicenseClass,
  SearchResultItem,
} from "@/lib/api/generated/control-plane";
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

export type EvidenceSearchActionState = FormActionState<{
  results: SearchResultItem[];
  workflowInstanceId: string;
}>;

export type EvidenceResolveActionState = FormActionState<{
  resolved: EvidenceSourceRead[];
  unresolved: string[];
}>;

export type EvidenceMutationActionState = FormActionState<{ id?: string }>;

const EVIDENCE_SOURCE_TYPES = new Set<EvidenceSourceType>(["pubmed", "pmc", "geo", "tcga", "manual"]);
const LICENSE_CLASSES = new Set<LicenseClass>([
  "unknown",
  "public",
  "metadata_only",
  "pmc_oa_subset",
  "restricted",
  "internal",
]);
const EVIDENCE_RELATION_TYPES = new Set<EvidenceRelationType>([
  "supports",
  "contradicts",
  "method_ref",
  "background_ref",
]);

export async function searchEvidenceAction(
  projectId: string,
  _: EvidenceSearchActionState,
  formData: FormData,
): Promise<EvidenceSearchActionState> {
  const query = getOptionalString(formData, "query");
  const picoQuestion = getOptionalString(formData, "pico_question");

  if (!query && !picoQuestion) {
    return {
      message: "Provide query or pico_question.",
      status: "error",
    };
  }

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    const response = await client.searchEvidence(projectId, {
      pico_question: picoQuestion,
      query,
    });
    return {
      message: `Search workflow ${response.workflow_instance_id.slice(0, 8)} returned ${response.results?.length ?? 0} cached match(es).`,
      result: {
        results: response.results ?? [],
        workflowInstanceId: response.workflow_instance_id,
      },
      status: "success",
    };
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }
}

export async function resolveEvidenceAction(
  projectId: string,
  _: EvidenceResolveActionState,
  formData: FormData,
): Promise<EvidenceResolveActionState> {
  const identifiers = getStringList(formData, "identifiers");

  if (identifiers.length === 0) {
    return {
      message: "At least one identifier is required.",
      status: "error",
    };
  }

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    const response = await client.resolveEvidence(projectId, {
      identifiers,
    });
    revalidatePath(`/projects/${projectId}/evidence`);
    return {
      message: `Resolved ${response.resolved?.length ?? 0} identifier(s).`,
      result: {
        resolved: response.resolved ?? [],
        unresolved: response.unresolved ?? [],
      },
      status: "success",
    };
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }
}

export async function upsertEvidenceSourceAction(
  projectId: string,
  _: EvidenceMutationActionState,
  formData: FormData,
): Promise<EvidenceMutationActionState> {
  const externalIdNorm = getString(formData, "external_id_norm");
  const sourceTypeRaw = getString(formData, "source_type");
  const title = getString(formData, "title");
  const doiNorm = getOptionalString(formData, "doi_norm");
  const pmid = getOptionalString(formData, "pmid");
  const pmcid = getOptionalString(formData, "pmcid");
  const journal = getOptionalString(formData, "journal");
  const pubYear = getOptionalNumber(formData, "pub_year");
  const licenseClassRaw = getOptionalString(formData, "license_class");
  const oaSubsetFlag = getString(formData, "oa_subset_flag") === "true";
  const metadataInput = getString(formData, "metadata_json");
  const sourceType = EVIDENCE_SOURCE_TYPES.has(sourceTypeRaw as EvidenceSourceType)
    ? (sourceTypeRaw as EvidenceSourceType)
    : undefined;
  const licenseClass =
    licenseClassRaw && LICENSE_CLASSES.has(licenseClassRaw as LicenseClass)
      ? (licenseClassRaw as LicenseClass)
      : undefined;

  if (externalIdNorm === "" || sourceTypeRaw === "" || title === "") {
    return {
      message: "external_id_norm, source_type, and title are required.",
      status: "error",
    };
  }

  if (sourceType === undefined) {
    return {
      message: "source_type is invalid.",
      status: "error",
    };
  }

  if (licenseClassRaw && licenseClass === undefined) {
    return {
      message: "license_class is invalid.",
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

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    const response = await client.upsertEvidenceSource(projectId, {
      doi_norm: doiNorm,
      external_id_norm: externalIdNorm,
      journal,
      license_class: licenseClass,
      metadata_json: metadataJson,
      oa_subset_flag: oaSubsetFlag,
      pmcid,
      pmid,
      pub_year: pubYear,
      source_type: sourceType,
      title,
    });
    revalidatePath(`/projects/${projectId}/evidence`);
    return {
      message: `Evidence source ${response.evidence_source.id.slice(0, 8)} saved.`,
      result: { id: response.evidence_source.id },
      status: "success",
    };
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }
}

export async function createEvidenceLinkAction(
  projectId: string,
  _: EvidenceMutationActionState,
  formData: FormData,
): Promise<EvidenceMutationActionState> {
  const assertionId = getString(formData, "assertion_id");
  const evidenceSourceId = getString(formData, "evidence_source_id");
  const relationTypeRaw = getString(formData, "relation_type");
  const confidence = getOptionalNumber(formData, "confidence");
  const sourceSpanStart = getOptionalNumber(formData, "source_span_start");
  const sourceSpanEnd = getOptionalNumber(formData, "source_span_end");
  const sourceChunkId = getOptionalString(formData, "source_chunk_id");
  const excerptHash = getOptionalString(formData, "excerpt_hash");
  const relationType = EVIDENCE_RELATION_TYPES.has(relationTypeRaw as EvidenceRelationType)
    ? (relationTypeRaw as EvidenceRelationType)
    : undefined;

  if (assertionId === "" || evidenceSourceId === "" || relationTypeRaw === "") {
    return {
      message: "assertion_id, evidence_source_id, and relation_type are required.",
      status: "error",
    };
  }

  if (relationType === undefined) {
    return {
      message: "relation_type is invalid.",
      status: "error",
    };
  }

  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    const response = await client.createEvidenceLink(projectId, {
      assertion_id: assertionId,
      confidence,
      evidence_source_id: evidenceSourceId,
      excerpt_hash: excerptHash,
      relation_type: relationType,
      source_chunk_id: sourceChunkId,
      source_span_end: sourceSpanEnd,
      source_span_start: sourceSpanStart,
    });
    revalidatePath(`/projects/${projectId}/evidence`);
    revalidatePath(`/projects/${projectId}/assertions/${assertionId}`);
    return {
      message: `Evidence link ${response.evidence_link.id.slice(0, 8)} created.`,
      result: { id: response.evidence_link.id },
      status: "success",
    };
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }
}

export async function verifyEvidenceLinkAction(projectId: string, linkId: string): Promise<void> {
  const client = await createServerControlPlaneClient({ cache: "no-store" });
  await client.verifyEvidenceLink(projectId, linkId);
  revalidatePath(`/projects/${projectId}/evidence`);
  redirect(`/projects/${projectId}/evidence`);
}

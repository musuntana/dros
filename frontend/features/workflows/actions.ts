"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { WorkflowBackend } from "@/lib/api/generated/control-plane";

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

export type WorkflowActionState = FormActionState;

const WORKFLOW_BACKENDS = new Set<WorkflowBackend>(["queue_workers", "temporal"]);

function workflowPaths(projectId: string, workflowId?: string): string[] {
  return [
    `/projects/${projectId}`,
    `/projects/${projectId}/workflows`,
    workflowId ? `/projects/${projectId}/workflows/${workflowId}` : "",
  ].filter(Boolean);
}

export async function createAnalysisPlanAction(
  projectId: string,
  _: WorkflowActionState,
  formData: FormData,
): Promise<WorkflowActionState> {
  const studyGoal = getString(formData, "study_goal");
  const datasetIds = getStringList(formData, "dataset_ids");
  const candidateTemplates = getStringList(formData, "candidate_templates");
  const assumptions = getStringList(formData, "assumptions");

  if (studyGoal === "" || datasetIds.length === 0) {
    return {
      message: "study_goal and at least one dataset_id are required.",
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.createAnalysisPlan(projectId, {
      assumptions,
      candidate_templates: candidateTemplates,
      dataset_ids: datasetIds,
      study_goal: studyGoal,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  for (const path of workflowPaths(projectId, response.workflow_instance_id)) {
    revalidatePath(path);
  }
  redirect(`/projects/${projectId}/workflows/${response.workflow_instance_id}`);
}

export async function createWorkflowAction(
  projectId: string,
  _: WorkflowActionState,
  formData: FormData,
): Promise<WorkflowActionState> {
  const workflowType = getString(formData, "workflow_type");
  const runtimeBackendRaw = getOptionalString(formData, "runtime_backend");
  const startedBy = getOptionalString(formData, "started_by");
  const parentWorkflowId = getOptionalString(formData, "parent_workflow_id");
  const runtimeBackend =
    runtimeBackendRaw && WORKFLOW_BACKENDS.has(runtimeBackendRaw as WorkflowBackend)
      ? (runtimeBackendRaw as WorkflowBackend)
      : undefined;

  if (workflowType === "") {
    return {
      message: "workflow_type is required.",
      status: "error",
    };
  }

  if (runtimeBackendRaw && runtimeBackend === undefined) {
    return {
      message: "runtime_backend must be queue_workers or temporal.",
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.createWorkflow(projectId, {
      parent_workflow_id: parentWorkflowId,
      runtime_backend: runtimeBackend,
      started_by: startedBy,
      workflow_type: workflowType,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  for (const path of workflowPaths(projectId, response.workflow.id)) {
    revalidatePath(path);
  }
  redirect(`/projects/${projectId}/workflows/${response.workflow.id}`);
}

export async function advanceWorkflowAction(
  projectId: string,
  workflowId: string,
  _: WorkflowActionState,
  formData: FormData,
): Promise<WorkflowActionState> {
  const action = getOptionalString(formData, "action");
  const comments = getOptionalString(formData, "comments");
  const taskId = getOptionalString(formData, "task_id");

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.advanceWorkflow(projectId, workflowId, {
      action,
      comments,
      task_id: taskId,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  for (const path of workflowPaths(projectId, response.workflow.id)) {
    revalidatePath(path);
  }
  redirect(`/projects/${projectId}/workflows/${response.workflow.id}`);
}

export async function cancelWorkflowAction(
  projectId: string,
  workflowId: string,
  _: WorkflowActionState,
  formData: FormData,
): Promise<WorkflowActionState> {
  const reason = getString(formData, "reason");
  const requestedBy = getOptionalString(formData, "requested_by");

  if (reason === "") {
    return {
      message: "reason is required.",
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.cancelWorkflow(projectId, workflowId, {
      reason,
      requested_by: requestedBy,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  for (const path of workflowPaths(projectId, response.workflow.id)) {
    revalidatePath(path);
  }
  redirect(`/projects/${projectId}/workflows/${response.workflow.id}`);
}

export async function createAnalysisRunAction(
  projectId: string,
  workflowId: string | null,
  _: WorkflowActionState,
  formData: FormData,
): Promise<WorkflowActionState> {
  const snapshotId = getString(formData, "snapshot_id");
  const templateId = getString(formData, "template_id");
  const paramsInput = getString(formData, "params_json");
  const randomSeed = getOptionalNumber(formData, "random_seed");
  const workflowInstanceId = workflowId ?? getOptionalString(formData, "workflow_instance_id");

  if (snapshotId === "" || templateId === "") {
    return {
      message: "snapshot_id and template_id are required.",
      status: "error",
    };
  }

  let paramsJson: Record<string, unknown>;
  try {
    paramsJson = parseJsonObject(paramsInput, "params_json");
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  let response;
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    response = await client.createAnalysisRun(projectId, {
      params_json: paramsJson,
      random_seed: randomSeed,
      snapshot_id: snapshotId,
      template_id: templateId,
      workflow_instance_id: workflowInstanceId,
    });
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }

  for (const path of workflowPaths(projectId, workflowInstanceId ?? undefined)) {
    revalidatePath(path);
  }
  revalidatePath(`/projects/${projectId}/analysis-runs/${response.analysis_run.id}`);
  redirect(`/projects/${projectId}/analysis-runs/${response.analysis_run.id}`);
}

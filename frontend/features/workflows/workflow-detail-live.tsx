"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  AnalysisTemplateRead,
  DatasetDetailResponse,
  DatasetListResponse,
  GateEvaluationRead,
  TemplateListResponse,
  WorkflowDetailResponse,
  WorkflowInstanceRead,
  WorkflowTaskRead,
} from "@/lib/api/generated/control-plane";
import { controlPlaneRoutes } from "@/lib/api/control-plane/endpoints";
import { parseError } from "@/lib/api/control-plane/errors";
import { getControlPlaneBaseUrl } from "@/lib/config";

import { WorkflowDetail } from "@/features/workflows/workflow-detail";
import { useWorkspaceData } from "@/features/projects/workspace-context";
import { isWorkflowRelevantEvent } from "@/features/workflows/workflow-event-match";
import type { WorkflowSnapshotOption } from "@/features/workflows/types";

async function requestControlPlaneJson<T>(
  path: string,
  input: {
    query?: Record<string, string | number | boolean | null | undefined>;
    signal: AbortSignal;
  },
): Promise<T> {
  const url = new URL(path, getControlPlaneBaseUrl());
  for (const [key, value] of Object.entries(input.query ?? {})) {
    if (value === undefined || value === null) {
      continue;
    }
    url.searchParams.set(key, String(value));
  }

  const response = await fetch(url, { signal: input.signal });
  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

export function WorkflowDetailLive({
  projectId,
  workflowInstanceId,
}: {
  projectId: string;
  workflowInstanceId: string;
}) {
  const { events, projection } = useWorkspaceData();

  // The projection is capped (limit 20), so the workflow may be absent for
  // older instances.  We always perform an authoritative detail fetch; the
  // projection entry is only used as one of two refresh signals.
  const projectedWorkflow = useMemo(
    () => projection.workflows.find((w) => w.id === workflowInstanceId) ?? null,
    [projection.workflows, workflowInstanceId],
  );

  const relatedRuns = useMemo(
    () =>
      projection.analysisRuns
        .filter((r) => r.workflow_instance_id === workflowInstanceId)
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [projection.analysisRuns, workflowInstanceId],
  );

  // Two independent refresh signals, so the detail fetch fires when *either*
  // changes:
  //  (a) projectedState — covers workflows inside the projection window
  //  (b) lastRelevantEventId — covers workflows outside the projection window
  //      by watching SSE events whose payload references this workflow.
  //
  // Events like workflow.advanced / workflow.canceled go through the gateway
  // fallback path; they may carry target_id (enriched by _enrich_fallback_payload)
  // or only event_name.  We match all three shapes:
  //   - payload.workflow_instance_id / payload.workflow_id  (structured events)
  //   - payload.target_id                                   (enriched fallback)
  //   - event_name starts with "workflow."                  (defense-in-depth)
  const projectedState = projectedWorkflow?.state;
  const lastRelevantEventId = useMemo(() => {
    const match = events.find((e) =>
      isWorkflowRelevantEvent(e, workflowInstanceId, !!projectedWorkflow),
    );
    return match?.event_id ?? null;
  }, [events, workflowInstanceId, projectedWorkflow]);

  const [workflow, setWorkflow] = useState<WorkflowInstanceRead | null>(null);
  const [tasks, setTasks] = useState<WorkflowTaskRead[]>([]);
  const [gateEvaluations, setGateEvaluations] = useState<GateEvaluationRead[]>([]);
  const [snapshots, setSnapshots] = useState<WorkflowSnapshotOption[]>([]);
  const [templates, setTemplates] = useState<AnalysisTemplateRead[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Fetch full workflow detail (workflow + tasks + gates) on mount and whenever
  // either refresh signal changes.
  useEffect(() => {
    const controller = new AbortController();
    requestControlPlaneJson<WorkflowDetailResponse>(controlPlaneRoutes.projects.workflow(projectId, workflowInstanceId), {
      signal: controller.signal,
    })
      .then((detail) => {
        if (controller.signal.aborted) return;
        setWorkflow(detail.workflow);
        setTasks(detail.tasks ?? []);
        setGateEvaluations(detail.gate_evaluations ?? []);
        setFetchError(null);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setFetchError(err instanceof Error ? err.message : "Failed to load workflow detail");
      });
    return () => controller.abort();
  }, [projectId, workflowInstanceId, projectedState, lastRelevantEventId]);

  // Fetch snapshot options and templates once on mount.
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      requestControlPlaneJson<TemplateListResponse>(controlPlaneRoutes.templates.list(), {
        signal: controller.signal,
      }),
      requestControlPlaneJson<DatasetListResponse>(controlPlaneRoutes.projects.datasets(projectId), {
        query: { limit: 50, offset: 0 },
        signal: controller.signal,
      }),
    ])
      .then(async ([templateResponse, datasetResponse]) => {
        if (controller.signal.aborted) return;
        setTemplates(templateResponse.items);
        const datasets = datasetResponse.items.items.filter((d) => d.current_snapshot_id);
        const snapshotOptions: WorkflowSnapshotOption[] = [];
        for (const dataset of datasets) {
          if (controller.signal.aborted) return;
          try {
            const detail = await requestControlPlaneJson<DatasetDetailResponse>(
              controlPlaneRoutes.projects.dataset(projectId, dataset.id),
              { signal: controller.signal },
            );
            if (detail.current_snapshot) {
              snapshotOptions.push({
                datasetId: dataset.id,
                datasetName: dataset.display_name,
                deidStatus: detail.current_snapshot.deid_status,
                phiScanStatus: detail.current_snapshot.phi_scan_status,
                snapshotId: detail.current_snapshot.id,
                snapshotNo: detail.current_snapshot.snapshot_no,
              });
            }
          } catch {
            /* skip dataset on error */
          }
        }
        if (!controller.signal.aborted) {
          setSnapshots(snapshotOptions.sort((a, b) => a.datasetName.localeCompare(b.datasetName)));
        }
      })
      .catch(() => {
        /* non-critical */
      });
    return () => controller.abort();
  }, [projectId]);

  if (fetchError) {
    return (
      <div className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="text-sm text-danger">{fetchError}</p>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="text-sm text-muted">Loading workflow detail...</p>
      </div>
    );
  }

  return (
    <WorkflowDetail
      detail={{ workflow, tasks, gateEvaluations }}
      projectId={projectId}
      relatedRuns={relatedRuns}
      snapshots={snapshots}
      templates={templates}
    />
  );
}

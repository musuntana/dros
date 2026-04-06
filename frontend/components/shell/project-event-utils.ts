"use client";

import type { ProjectEvent } from "@/lib/api/gateway";

export interface ProjectEventLink {
  label: string;
  href: string;
}

export const MAX_PROJECT_EVENTS = 8;

function stringifyPayloadValue(value: unknown): string {
  if (value === undefined || value === null || value === "") {
    return "";
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function readPayloadString(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  if (typeof value === "string" && value.length > 0) {
    return value;
  }

  return null;
}

function readPayloadStringArray(payload: Record<string, unknown>, key: string): string[] {
  const value = payload[key];
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

export function mergeProjectEvents(current: ProjectEvent[], incoming: ProjectEvent): ProjectEvent[] {
  const withoutDuplicate = current.filter((event) => event.event_id !== incoming.event_id);
  return [incoming, ...withoutDuplicate]
    .sort((left, right) => right.occurred_at.localeCompare(left.occurred_at))
    .slice(0, MAX_PROJECT_EVENTS);
}

export function mergeProjectEventSnapshot(current: ProjectEvent[], incomingEvents: ProjectEvent[]): ProjectEvent[] {
  const byId = new Map(current.map((event) => [event.event_id, event]));

  for (const incoming of incomingEvents) {
    const existing = byId.get(incoming.event_id);
    if (!existing) {
      byId.set(incoming.event_id, incoming);
      continue;
    }

    const keepExisting = existing.produced_by !== "audit.seed" && incoming.produced_by === "audit.seed";
    byId.set(incoming.event_id, keepExisting ? existing : incoming);
  }

  return [...byId.values()]
    .sort((left, right) => right.occurred_at.localeCompare(left.occurred_at))
    .slice(0, MAX_PROJECT_EVENTS);
}

export function summarizeProjectEventPayload(payload: Record<string, unknown>): string {
  const priorityKeys = [
    "workflow_type",
    "state",
    "snapshot_no",
    "artifact_type",
    "format",
    "review_type",
    "reason",
  ];

  for (const key of priorityKeys) {
    const value = stringifyPayloadValue(payload[key]);
    if (value) {
      return `${key}: ${value}`;
    }
  }

  const firstEntry = Object.entries(payload)[0];
  if (!firstEntry) {
    return "No payload summary";
  }

  return `${firstEntry[0]}: ${stringifyPayloadValue(firstEntry[1])}`;
}

export function buildProjectEventLinks(projectId: string, event: ProjectEvent): ProjectEventLink[] {
  const links: ProjectEventLink[] = [];
  const seen = new Set<string>();
  const { payload } = event;

  const pushLink = (label: string, href: string) => {
    const key = `${label}:${href}`;
    if (seen.has(key)) {
      return;
    }

    seen.add(key);
    links.push({ label, href });
  };

  const workflowInstanceId = readPayloadString(payload, "workflow_instance_id");
  if (workflowInstanceId) {
    pushLink("Workflow", `/projects/${projectId}/workflows/${workflowInstanceId}`);
  }

  const analysisRunId = readPayloadString(payload, "analysis_run_id") ?? readPayloadString(payload, "run_id");
  if (analysisRunId) {
    pushLink("Analysis run", `/projects/${projectId}/analysis-runs/${analysisRunId}`);
  }

  const artifactId = readPayloadString(payload, "artifact_id") ?? readPayloadString(payload, "output_artifact_id");
  if (artifactId) {
    pushLink("Artifact", `/projects/${projectId}/artifacts/${artifactId}`);
  }

  const artifactIds = readPayloadStringArray(payload, "artifact_ids");
  if (!artifactId && artifactIds.length === 1) {
    pushLink("Artifact", `/projects/${projectId}/artifacts/${artifactIds[0]}`);
  } else if (artifactIds.length > 1) {
    pushLink("Artifacts", `/projects/${projectId}/artifacts`);
  }

  if (readPayloadString(payload, "snapshot_id")) {
    pushLink("Datasets", `/projects/${projectId}/datasets`);
  }

  if (readPayloadString(payload, "review_id")) {
    pushLink("Reviews", `/projects/${projectId}/reviews`);
  }

  const evidenceLinkId = readPayloadString(payload, "link_id");
  if (evidenceLinkId) {
    pushLink("Evidence link", `/projects/${projectId}/evidence-links/${evidenceLinkId}`);
  }

  if (readPayloadString(payload, "export_job_id")) {
    pushLink("Exports", `/projects/${projectId}/exports`);
  }

  pushLink("Audit trail", `/projects/${projectId}/audit`);

  return links;
}

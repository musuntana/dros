/**
 * Pure predicate: does a given SSE event relate to a specific workflow instance?
 *
 * Extracted from WorkflowDetailLive so the matching logic can be regression-tested
 * without rendering React components.
 */

export interface SseEventLike {
  event_id: string;
  event_name: string;
  payload?: Record<string, unknown>;
}

/**
 * Returns true when `event` should trigger a detail-refresh for
 * `workflowInstanceId`.
 *
 * @param isProjected  Whether the workflow currently exists in the projection
 *   window.  When false, any `workflow.*` event is treated as potentially
 *   relevant (defense-in-depth).
 */
export function isWorkflowRelevantEvent(
  event: SseEventLike,
  workflowInstanceId: string,
  isProjected: boolean,
): boolean {
  const p = event.payload;
  if (
    String(p?.workflow_instance_id ?? "") === workflowInstanceId ||
    String(p?.workflow_id ?? "") === workflowInstanceId ||
    String(p?.target_id ?? "") === workflowInstanceId
  ) {
    return true;
  }
  // Fallback: any workflow.* event in this project is a potential match
  // for an out-of-projection workflow whose ID wasn't in the payload.
  if (!isProjected && event.event_name.startsWith("workflow.")) {
    return true;
  }
  return false;
}

/**
 * Regression tests for workflow SSE event matching.
 *
 * Covers two scenarios:
 *   1. Fallback workflow SSE with enriched target_id must match the detail page.
 *   2. Out-of-projection workflow detail must refresh on any workflow.* event.
 */
import { describe, expect, it } from "vitest";

import { isWorkflowRelevantEvent, type SseEventLike } from "./workflow-event-match";

const WF_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

function makeEvent(overrides: Partial<SseEventLike> & { event_name: string }): SseEventLike {
  return { event_id: "evt-1", payload: {}, ...overrides };
}

// ---------------------------------------------------------------------------
// Scenario 1 — enriched fallback payload carries target_id
// ---------------------------------------------------------------------------
describe("fallback SSE with target_id (enriched by _enrich_fallback_payload)", () => {
  it("matches when payload.target_id equals workflowInstanceId", () => {
    const event = makeEvent({
      event_name: "workflow.advanced",
      payload: { target_id: WF_ID, target_kind: "workflow_instance" },
    });
    expect(isWorkflowRelevantEvent(event, WF_ID, true)).toBe(true);
  });

  it("matches workflow.canceled with target_id", () => {
    const event = makeEvent({
      event_name: "workflow.canceled",
      payload: { target_id: WF_ID, target_kind: "workflow_instance" },
    });
    expect(isWorkflowRelevantEvent(event, WF_ID, true)).toBe(true);
  });

  it("does not match when target_id is a different workflow", () => {
    const event = makeEvent({
      event_name: "workflow.advanced",
      payload: { target_id: "other-id", target_kind: "workflow_instance" },
    });
    expect(isWorkflowRelevantEvent(event, WF_ID, true)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Scenario 2 — out-of-projection workflow detail refreshes on any workflow.* event
// ---------------------------------------------------------------------------
describe("out-of-projection workflow detail refresh", () => {
  it("matches any workflow.* event when not projected (defense-in-depth)", () => {
    const event = makeEvent({
      event_name: "workflow.advanced",
      payload: {}, // no target_id at all
    });
    // isProjected = false → should match
    expect(isWorkflowRelevantEvent(event, WF_ID, false)).toBe(true);
  });

  it("does NOT match workflow.* when the workflow IS projected", () => {
    const event = makeEvent({
      event_name: "workflow.advanced",
      payload: {}, // no target_id
    });
    // isProjected = true → bare workflow.* should NOT match
    expect(isWorkflowRelevantEvent(event, WF_ID, true)).toBe(false);
  });

  it("does NOT match non-workflow events even when not projected", () => {
    const event = makeEvent({
      event_name: "analysis_run.succeeded",
      payload: {},
    });
    expect(isWorkflowRelevantEvent(event, WF_ID, false)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Structured event paths (not fallback) — existing behavior preserved
// ---------------------------------------------------------------------------
describe("structured event matching", () => {
  it("matches payload.workflow_instance_id", () => {
    const event = makeEvent({
      event_name: "workflow.started",
      payload: { workflow_instance_id: WF_ID },
    });
    expect(isWorkflowRelevantEvent(event, WF_ID, true)).toBe(true);
  });

  it("matches payload.workflow_id", () => {
    const event = makeEvent({
      event_name: "workflow.started",
      payload: { workflow_id: WF_ID },
    });
    expect(isWorkflowRelevantEvent(event, WF_ID, true)).toBe(true);
  });
});

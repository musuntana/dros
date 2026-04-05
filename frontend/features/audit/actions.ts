"use server";

import { createServerControlPlaneClient } from "@/lib/api/control-plane/client";
import {
  type FormActionState,
  getErrorMessage,
} from "@/lib/server-actions/forms";

export type AuditReplayActionState = FormActionState<{
  checkedCount: number;
  firstInvalidEventId: string | null;
  valid: boolean;
}>;

export async function replayAuditAction(
  _: AuditReplayActionState,
): Promise<AuditReplayActionState> {
  try {
    const client = await createServerControlPlaneClient({ cache: "no-store" });
    const response = await client.replayAuditChain();
    return {
      message: response.valid
        ? `Audit chain valid across ${response.checked_count} event(s).`
        : `Audit chain invalid at ${response.first_invalid_event_id}.`,
      result: {
        checkedCount: response.checked_count,
        firstInvalidEventId: response.first_invalid_event_id ?? null,
        valid: response.valid,
      },
      status: response.valid ? "success" : "error",
    };
  } catch (error) {
    return {
      message: getErrorMessage(error),
      status: "error",
    };
  }
}

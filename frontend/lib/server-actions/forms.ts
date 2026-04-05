import { createHash } from "node:crypto";

import { ControlPlaneError } from "@/lib/api/control-plane/errors";

export interface FormActionState<Result = undefined> {
  message: string | null;
  result?: Result;
  status: "idle" | "error" | "success";
}

export function createInitialFormActionState<Result = undefined>(): FormActionState<Result> {
  return {
    message: null,
    status: "idle",
  };
}

export function getString(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

export function getOptionalString(formData: FormData, key: string): string | undefined {
  const value = getString(formData, key);
  return value === "" ? undefined : value;
}

export function getOptionalNumber(formData: FormData, key: string): number | undefined {
  const value = getOptionalString(formData, key);
  if (!value) {
    return undefined;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function getStringList(formData: FormData, key: string): string[] {
  return parseStringList(getString(formData, key));
}

export function parseStringList(input: string): string[] {
  return Array.from(
    new Set(
      input
        .split(/[\n,]/)
        .map((item) => item.trim())
        .filter((item) => item.length > 0),
    ),
  );
}

export function parseJsonObject(
  input: string,
  fieldName: string,
): Record<string, unknown> {
  if (input.trim() === "") {
    return {};
  }

  const parsed = JSON.parse(input);
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(`${fieldName} must be a JSON object.`);
  }

  return parsed as Record<string, unknown>;
}

export function parseJsonArray(
  input: string,
  fieldName: string,
): Array<Record<string, unknown>> {
  if (input.trim() === "") {
    return [];
  }

  const parsed = JSON.parse(input);
  if (!Array.isArray(parsed)) {
    throw new Error(`${fieldName} must be a JSON array.`);
  }

  return parsed.map((entry) => {
    if (entry === null || Array.isArray(entry) || typeof entry !== "object") {
      throw new Error(`${fieldName} entries must be JSON objects.`);
    }
    return entry as Record<string, unknown>;
  });
}

export function deriveSha256(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ControlPlaneError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown request failure";
}

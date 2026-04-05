export class ControlPlaneError extends Error {
  readonly detail: unknown;
  readonly status: number;
  readonly url: string;

  constructor(message: string, input: { detail: unknown; status: number; url: string }) {
    super(message);
    this.name = "ControlPlaneError";
    this.detail = input.detail;
    this.status = input.status;
    this.url = input.url;
  }
}

export async function parseError(response: Response): Promise<ControlPlaneError> {
  let detail: unknown = null;

  try {
    detail = await response.json();
  } catch {
    detail = await response.text();
  }

  const message =
    typeof detail === "object" &&
    detail !== null &&
    "detail" in detail &&
    typeof detail.detail === "string"
      ? detail.detail
      : `${response.status} ${response.statusText}`;

  return new ControlPlaneError(message, {
    detail,
    status: response.status,
    url: response.url,
  });
}

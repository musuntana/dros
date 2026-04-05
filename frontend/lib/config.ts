const DEFAULT_CONTROL_PLANE_BASE_URL = "http://127.0.0.1:8000";

export function getControlPlaneBaseUrl(): string {
  return (
    process.env.CONTROL_PLANE_BASE_URL ??
    process.env.NEXT_PUBLIC_CONTROL_PLANE_BASE_URL ??
    DEFAULT_CONTROL_PLANE_BASE_URL
  );
}

export function getGatewayBaseUrl(): string {
  return (
    process.env.GATEWAY_BASE_URL ??
    process.env.NEXT_PUBLIC_GATEWAY_BASE_URL ??
    process.env.CONTROL_PLANE_BASE_URL ??
    process.env.NEXT_PUBLIC_CONTROL_PLANE_BASE_URL ??
    DEFAULT_CONTROL_PLANE_BASE_URL
  );
}

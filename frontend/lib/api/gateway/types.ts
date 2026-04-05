export interface SessionRead {
  actor_id: string;
  principal_id: string;
  tenant_id: string;
  scopes_json: Record<string, unknown>;
}

export interface SignUploadInput {
  filename: string;
  content_type: string;
  size_bytes: number;
}

export interface UploadCompleteInput {
  object_key: string;
  sha256: string;
}

export interface ProjectEvent {
  event_id: string;
  event_name: string;
  schema_version: string;
  produced_by: string;
  trace_id: string;
  request_id: string;
  tenant_id: string;
  project_id: string;
  idempotency_key: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface SignedUploadResult {
  upload_url: string;
  object_key: string;
  expires_in_seconds: number;
}

export interface UploadCompleteResult {
  file_ref: string;
}

export interface SignedArtifactUrlResult {
  download_url: string;
  expires_in_seconds: number;
}

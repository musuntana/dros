-- Canonical SQL design baseline for the current DR-OS research ledger.
-- This file is the only schema draft that should be used for architecture,
-- data modeling, and migration planning.
-- It supersedes legacy schema sketches and transitional init files.
-- It is not an incremental migration over any legacy init draft.

BEGIN;

CREATE SCHEMA IF NOT EXISTS dr_os;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  CREATE TYPE dr_os.tenant_tier AS ENUM ('community', 'professional', 'enterprise');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.deployment_mode AS ENUM ('saas', 'private_vpc', 'on_prem');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.tenant_status AS ENUM ('active', 'suspended', 'archived');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.principal_subject_type AS ENUM ('user', 'service');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.principal_status AS ENUM ('active', 'disabled', 'invited');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.project_type AS ENUM ('public_omics', 'clinical_retrospective', 'case_report', 'grant');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.project_state AS ENUM ('draft', 'running', 'review_required', 'approved', 'archived');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.compliance_level AS ENUM ('public', 'internal', 'clinical');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.project_role AS ENUM ('owner', 'admin', 'editor', 'reviewer', 'viewer');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.dataset_source_kind AS ENUM ('upload', 'geo', 'tcga', 'seer', 'manual');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.pii_level AS ENUM ('none', 'limited', 'direct');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.license_class AS ENUM ('unknown', 'public', 'metadata_only', 'pmc_oa_subset', 'restricted', 'internal');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.deid_status AS ENUM ('not_required', 'pending', 'completed', 'failed');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.phi_scan_status AS ENUM ('pending', 'passed', 'blocked', 'needs_human');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.template_review_status AS ENUM ('draft', 'approved', 'retired');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.workflow_state AS ENUM (
    'created',
    'retrieving',
    'retrieved',
    'structuring',
    'structured',
    'analyzing',
    'analyzed',
    'asserting',
    'asserted',
    'writing',
    'verifying',
    'approved',
    'blocked',
    'needs_human',
    'exported',
    'failed'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.workflow_backend AS ENUM ('queue_workers', 'temporal');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.task_state AS ENUM ('pending', 'running', 'completed', 'blocked', 'needs_human', 'failed', 'canceled');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.analysis_run_state AS ENUM ('created', 'requested', 'queued', 'running', 'succeeded', 'failed', 'blocked', 'canceled');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.artifact_type AS ENUM (
    'dataset_snapshot',
    'result_json',
    'table',
    'figure',
    'log',
    'manifest',
    'docx',
    'pdf',
    'zip',
    'evidence_attachment'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.lineage_kind AS ENUM (
    'tenant',
    'principal',
    'project',
    'dataset',
    'dataset_snapshot',
    'workflow_instance',
    'workflow_task',
    'analysis_template',
    'analysis_run',
    'artifact',
    'assertion',
    'evidence_source',
    'evidence_chunk',
    'manuscript',
    'manuscript_block',
    'review',
    'export_job'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.lineage_edge_type AS ENUM (
    'input_of',
    'emits',
    'derives',
    'supersedes',
    'grounds',
    'cited_by',
    'attached_to',
    'reviewed_by',
    'exports'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.evidence_source_type AS ENUM ('pubmed', 'pmc', 'geo', 'tcga', 'manual');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.assertion_type AS ENUM ('background', 'method', 'result', 'limitation');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.assertion_state AS ENUM ('draft', 'verified', 'blocked', 'stale');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.evidence_relation_type AS ENUM ('supports', 'contradicts', 'method_ref', 'background_ref');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.verifier_status AS ENUM ('pending', 'passed', 'warning', 'blocked');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.manuscript_type AS ENUM ('manuscript', 'abstract', 'grant_response');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.manuscript_state AS ENUM ('draft', 'review_required', 'approved', 'exported', 'archived');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.block_type AS ENUM ('text', 'figure', 'table', 'citation_list');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.block_state AS ENUM ('draft', 'verified', 'blocked', 'superseded');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.review_type AS ENUM ('evidence', 'analysis', 'manuscript', 'export');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.review_state AS ENUM ('pending', 'approved', 'rejected', 'changes_requested');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.export_format AS ENUM ('docx', 'pdf', 'zip');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.export_state AS ENUM ('pending', 'running', 'completed', 'failed', 'blocked');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE dr_os.actor_type AS ENUM ('user', 'agent', 'system');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE OR REPLACE FUNCTION dr_os.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION dr_os.prevent_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'table % is append-only', TG_TABLE_NAME;
END;
$$;

CREATE OR REPLACE FUNCTION dr_os.current_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION dr_os.current_principal_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.principal_id', true), '')::uuid
$$;

CREATE TABLE IF NOT EXISTS dr_os.tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  tier dr_os.tenant_tier NOT NULL DEFAULT 'community',
  deployment_mode dr_os.deployment_mode NOT NULL DEFAULT 'saas',
  status dr_os.tenant_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS dr_os.principals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  subject_type dr_os.principal_subject_type NOT NULL,
  external_sub TEXT NOT NULL,
  email TEXT,
  display_name TEXT NOT NULL,
  status dr_os.principal_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, external_sub)
);

CREATE UNIQUE INDEX IF NOT EXISTS principals_tenant_email_uniq
  ON dr_os.principals (tenant_id, lower(email))
  WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS dr_os.projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  project_type dr_os.project_type NOT NULL,
  status dr_os.project_state NOT NULL DEFAULT 'draft',
  compliance_level dr_os.compliance_level NOT NULL DEFAULT 'internal',
  owner_id UUID NOT NULL REFERENCES dr_os.principals(id),
  active_manuscript_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS projects_tenant_created_idx
  ON dr_os.projects (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS projects_tenant_status_idx
  ON dr_os.projects (tenant_id, status);

CREATE TABLE IF NOT EXISTS dr_os.project_members (
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  principal_id UUID NOT NULL REFERENCES dr_os.principals(id) ON DELETE CASCADE,
  role dr_os.project_role NOT NULL,
  scopes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (project_id, principal_id)
);

CREATE INDEX IF NOT EXISTS project_members_principal_idx
  ON dr_os.project_members (tenant_id, principal_id);

CREATE TABLE IF NOT EXISTS dr_os.datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  source_kind dr_os.dataset_source_kind NOT NULL,
  display_name TEXT NOT NULL,
  source_ref TEXT,
  pii_level dr_os.pii_level NOT NULL DEFAULT 'none',
  license_class dr_os.license_class NOT NULL DEFAULT 'unknown',
  current_snapshot_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS datasets_project_source_idx
  ON dr_os.datasets (project_id, source_kind);

CREATE TABLE IF NOT EXISTS dr_os.dataset_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  dataset_id UUID NOT NULL REFERENCES dr_os.datasets(id) ON DELETE CASCADE,
  snapshot_no INTEGER NOT NULL,
  object_uri TEXT NOT NULL,
  input_hash_sha256 TEXT NOT NULL,
  row_count BIGINT,
  column_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  deid_status dr_os.deid_status NOT NULL DEFAULT 'pending',
  phi_scan_status dr_os.phi_scan_status NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (dataset_id, snapshot_no),
  UNIQUE (dataset_id, input_hash_sha256),
  CONSTRAINT dataset_snapshots_hash_len CHECK (length(input_hash_sha256) = 64),
  CONSTRAINT dataset_snapshots_row_count_nonnegative CHECK (row_count IS NULL OR row_count >= 0)
);

CREATE TABLE IF NOT EXISTS dr_os.analysis_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  version TEXT NOT NULL,
  name TEXT NOT NULL,
  image_digest TEXT NOT NULL,
  script_hash TEXT NOT NULL,
  param_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  golden_dataset_uri TEXT,
  expected_outputs_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  doc_template_uri TEXT,
  review_status dr_os.template_review_status NOT NULL DEFAULT 'draft',
  approved_by UUID REFERENCES dr_os.principals(id),
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS analysis_templates_scope_code_version_uniq
  ON dr_os.analysis_templates ((COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid)), code, version);

CREATE TABLE IF NOT EXISTS dr_os.workflow_instances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  workflow_type TEXT NOT NULL,
  state dr_os.workflow_state NOT NULL DEFAULT 'created',
  current_step TEXT,
  parent_workflow_id UUID REFERENCES dr_os.workflow_instances(id) ON DELETE SET NULL,
  started_by UUID REFERENCES dr_os.principals(id),
  runtime_backend dr_os.workflow_backend NOT NULL DEFAULT 'queue_workers',
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS workflow_instances_project_state_idx
  ON dr_os.workflow_instances (project_id, state);

CREATE INDEX IF NOT EXISTS workflow_instances_parent_idx
  ON dr_os.workflow_instances (parent_workflow_id);

CREATE TABLE IF NOT EXISTS dr_os.workflow_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  workflow_instance_id UUID NOT NULL REFERENCES dr_os.workflow_instances(id) ON DELETE CASCADE,
  task_key TEXT NOT NULL,
  task_type TEXT NOT NULL,
  state dr_os.task_state NOT NULL DEFAULT 'pending',
  assignee_id UUID REFERENCES dr_os.principals(id),
  input_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  retry_count INTEGER NOT NULL DEFAULT 0,
  scheduled_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workflow_instance_id, task_key),
  CONSTRAINT workflow_tasks_retry_nonnegative CHECK (retry_count >= 0)
);

CREATE INDEX IF NOT EXISTS workflow_tasks_instance_state_idx
  ON dr_os.workflow_tasks (workflow_instance_id, state);

CREATE TABLE IF NOT EXISTS dr_os.analysis_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  workflow_instance_id UUID REFERENCES dr_os.workflow_instances(id) ON DELETE SET NULL,
  snapshot_id UUID NOT NULL REFERENCES dr_os.dataset_snapshots(id) ON DELETE RESTRICT,
  template_id UUID NOT NULL REFERENCES dr_os.analysis_templates(id) ON DELETE RESTRICT,
  state dr_os.analysis_run_state NOT NULL DEFAULT 'created',
  params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  param_hash TEXT NOT NULL,
  random_seed BIGINT NOT NULL DEFAULT 0,
  container_image_digest TEXT NOT NULL,
  repro_fingerprint TEXT NOT NULL,
  runtime_manifest_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  input_artifact_manifest_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  exit_code INTEGER,
  rerun_of_run_id UUID REFERENCES dr_os.analysis_runs(id) ON DELETE SET NULL,
  job_ref TEXT,
  error_class TEXT,
  error_message_trunc TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (repro_fingerprint),
  CONSTRAINT analysis_runs_param_hash_len CHECK (length(param_hash) = 64),
  CONSTRAINT analysis_runs_repro_fingerprint_len CHECK (length(repro_fingerprint) = 64)
);

CREATE INDEX IF NOT EXISTS analysis_runs_project_state_idx
  ON dr_os.analysis_runs (project_id, state);

CREATE INDEX IF NOT EXISTS analysis_runs_snapshot_idx
  ON dr_os.analysis_runs (snapshot_id);

CREATE INDEX IF NOT EXISTS analysis_runs_template_idx
  ON dr_os.analysis_runs (template_id);

CREATE TABLE IF NOT EXISTS dr_os.artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  run_id UUID REFERENCES dr_os.analysis_runs(id) ON DELETE CASCADE,
  artifact_type dr_os.artifact_type NOT NULL,
  storage_uri TEXT NOT NULL,
  mime_type TEXT,
  sha256 TEXT NOT NULL,
  size_bytes BIGINT,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  superseded_by UUID REFERENCES dr_os.artifacts(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (sha256, storage_uri),
  CONSTRAINT artifacts_sha256_len CHECK (length(sha256) = 64),
  CONSTRAINT artifacts_size_nonnegative CHECK (size_bytes IS NULL OR size_bytes >= 0)
);

CREATE INDEX IF NOT EXISTS artifacts_run_type_idx
  ON dr_os.artifacts (run_id, artifact_type);

CREATE TABLE IF NOT EXISTS dr_os.lineage_edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  from_kind dr_os.lineage_kind NOT NULL,
  from_id UUID NOT NULL,
  edge_type dr_os.lineage_edge_type NOT NULL,
  to_kind dr_os.lineage_kind NOT NULL,
  to_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (from_kind, from_id, edge_type, to_kind, to_id)
);

CREATE TABLE IF NOT EXISTS dr_os.evidence_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type dr_os.evidence_source_type NOT NULL,
  external_id_norm TEXT NOT NULL,
  doi_norm TEXT,
  title TEXT NOT NULL,
  journal TEXT,
  pub_year INTEGER,
  pmid TEXT,
  pmcid TEXT,
  license_class dr_os.license_class NOT NULL DEFAULT 'metadata_only',
  oa_subset_flag BOOLEAN NOT NULL DEFAULT FALSE,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT evidence_sources_year_range CHECK (pub_year IS NULL OR pub_year BETWEEN 1800 AND 2200)
);

CREATE UNIQUE INDEX IF NOT EXISTS evidence_sources_external_uniq
  ON dr_os.evidence_sources (source_type, external_id_norm);

CREATE INDEX IF NOT EXISTS evidence_sources_pmid_idx
  ON dr_os.evidence_sources (pmid);

CREATE INDEX IF NOT EXISTS evidence_sources_doi_idx
  ON dr_os.evidence_sources (doi_norm);

CREATE TABLE IF NOT EXISTS dr_os.evidence_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_source_id UUID NOT NULL REFERENCES dr_os.evidence_sources(id) ON DELETE CASCADE,
  chunk_no INTEGER NOT NULL,
  section_label TEXT,
  text TEXT NOT NULL,
  char_start INTEGER NOT NULL DEFAULT 0,
  char_end INTEGER NOT NULL DEFAULT 0,
  token_count INTEGER NOT NULL DEFAULT 0,
  embedding vector(1536),
  lexical_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (evidence_source_id, chunk_no),
  CONSTRAINT evidence_chunks_char_order CHECK (char_end >= char_start),
  CONSTRAINT evidence_chunks_token_nonnegative CHECK (token_count >= 0)
);

CREATE INDEX IF NOT EXISTS evidence_chunks_lexical_idx
  ON dr_os.evidence_chunks USING GIN (lexical_tsv);

CREATE INDEX IF NOT EXISTS evidence_chunks_embedding_idx
  ON dr_os.evidence_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS dr_os.assertions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  assertion_type dr_os.assertion_type NOT NULL,
  text_norm TEXT NOT NULL,
  numeric_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_run_id UUID REFERENCES dr_os.analysis_runs(id) ON DELETE SET NULL,
  source_artifact_id UUID REFERENCES dr_os.artifacts(id) ON DELETE SET NULL,
  source_span_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  claim_hash TEXT NOT NULL,
  state dr_os.assertion_state NOT NULL DEFAULT 'draft',
  supersedes_assertion_id UUID REFERENCES dr_os.assertions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT assertions_text_nonempty CHECK (length(trim(text_norm)) > 0),
  CONSTRAINT assertions_claim_hash_len CHECK (length(claim_hash) = 64)
);

CREATE INDEX IF NOT EXISTS assertions_project_state_idx
  ON dr_os.assertions (project_id, state);

CREATE INDEX IF NOT EXISTS assertions_source_run_idx
  ON dr_os.assertions (source_run_id);

CREATE INDEX IF NOT EXISTS assertions_claim_hash_idx
  ON dr_os.assertions (claim_hash);

CREATE TABLE IF NOT EXISTS dr_os.evidence_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  assertion_id UUID NOT NULL REFERENCES dr_os.assertions(id) ON DELETE CASCADE,
  evidence_source_id UUID NOT NULL REFERENCES dr_os.evidence_sources(id) ON DELETE RESTRICT,
  relation_type dr_os.evidence_relation_type NOT NULL,
  source_chunk_id UUID REFERENCES dr_os.evidence_chunks(id) ON DELETE SET NULL,
  source_span_start INTEGER,
  source_span_end INTEGER,
  excerpt_hash TEXT,
  verifier_status dr_os.verifier_status NOT NULL DEFAULT 'pending',
  confidence NUMERIC(4, 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (assertion_id, evidence_source_id, relation_type, source_span_start, source_span_end),
  CONSTRAINT evidence_links_span_order CHECK (
    source_span_start IS NULL OR source_span_end IS NULL OR source_span_end >= source_span_start
  ),
  CONSTRAINT evidence_links_confidence_range CHECK (
    confidence IS NULL OR (confidence >= 0 AND confidence <= 1)
  )
);

CREATE TABLE IF NOT EXISTS dr_os.manuscripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  manuscript_type dr_os.manuscript_type NOT NULL DEFAULT 'manuscript',
  title TEXT NOT NULL,
  state dr_os.manuscript_state NOT NULL DEFAULT 'draft',
  current_version_no INTEGER NOT NULL DEFAULT 1,
  style_profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  target_journal TEXT,
  created_by UUID REFERENCES dr_os.principals(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT manuscripts_version_positive CHECK (current_version_no >= 1)
);

CREATE INDEX IF NOT EXISTS manuscripts_project_state_idx
  ON dr_os.manuscripts (project_id, state);

CREATE TABLE IF NOT EXISTS dr_os.manuscript_blocks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  manuscript_id UUID NOT NULL REFERENCES dr_os.manuscripts(id) ON DELETE CASCADE,
  version_no INTEGER NOT NULL,
  section_key TEXT NOT NULL,
  block_order INTEGER NOT NULL,
  block_type dr_os.block_type NOT NULL,
  content_md TEXT NOT NULL,
  status dr_os.block_state NOT NULL DEFAULT 'draft',
  supersedes_block_id UUID REFERENCES dr_os.manuscript_blocks(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (manuscript_id, version_no, section_key, block_order),
  CONSTRAINT manuscript_blocks_version_positive CHECK (version_no >= 1),
  CONSTRAINT manuscript_blocks_order_nonnegative CHECK (block_order >= 0)
);

CREATE TABLE IF NOT EXISTS dr_os.block_assertion_links (
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  block_id UUID NOT NULL REFERENCES dr_os.manuscript_blocks(id) ON DELETE CASCADE,
  assertion_id UUID NOT NULL REFERENCES dr_os.assertions(id) ON DELETE RESTRICT,
  render_role TEXT NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (block_id, assertion_id),
  CONSTRAINT block_assertion_links_display_nonnegative CHECK (display_order >= 0)
);

CREATE TABLE IF NOT EXISTS dr_os.reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  review_type dr_os.review_type NOT NULL,
  target_kind dr_os.lineage_kind NOT NULL,
  target_id UUID NOT NULL,
  state dr_os.review_state NOT NULL DEFAULT 'pending',
  reviewer_id UUID REFERENCES dr_os.principals(id),
  checklist_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  comments TEXT,
  decided_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS reviews_project_state_idx
  ON dr_os.reviews (project_id, state);

CREATE INDEX IF NOT EXISTS reviews_target_idx
  ON dr_os.reviews (target_kind, target_id);

CREATE TABLE IF NOT EXISTS dr_os.export_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  manuscript_id UUID NOT NULL REFERENCES dr_os.manuscripts(id) ON DELETE RESTRICT,
  format dr_os.export_format NOT NULL,
  state dr_os.export_state NOT NULL DEFAULT 'pending',
  output_artifact_id UUID REFERENCES dr_os.artifacts(id) ON DELETE SET NULL,
  requested_by UUID REFERENCES dr_os.principals(id),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS export_jobs_project_state_idx
  ON dr_os.export_jobs (project_id, state);

CREATE TABLE IF NOT EXISTS dr_os.audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES dr_os.tenants(id) ON DELETE CASCADE,
  project_id UUID REFERENCES dr_os.projects(id) ON DELETE CASCADE,
  actor_id UUID REFERENCES dr_os.principals(id),
  actor_type dr_os.actor_type NOT NULL,
  event_type TEXT NOT NULL,
  target_kind dr_os.lineage_kind NOT NULL,
  target_id UUID,
  request_id TEXT,
  trace_id TEXT,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prev_hash TEXT,
  event_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (event_hash),
  CONSTRAINT audit_events_event_hash_len CHECK (length(event_hash) = 64),
  CONSTRAINT audit_events_prev_hash_len CHECK (prev_hash IS NULL OR length(prev_hash) = 64)
);

CREATE INDEX IF NOT EXISTS audit_events_project_created_idx
  ON dr_os.audit_events (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS audit_events_request_idx
  ON dr_os.audit_events (request_id);

ALTER TABLE dr_os.projects
  ADD CONSTRAINT projects_active_manuscript_fk
  FOREIGN KEY (active_manuscript_id)
  REFERENCES dr_os.manuscripts(id)
  ON DELETE SET NULL;

ALTER TABLE dr_os.datasets
  ADD CONSTRAINT datasets_current_snapshot_fk
  FOREIGN KEY (current_snapshot_id)
  REFERENCES dr_os.dataset_snapshots(id)
  ON DELETE SET NULL;

CREATE TRIGGER touch_tenants_updated_at
  BEFORE UPDATE ON dr_os.tenants
  FOR EACH ROW EXECUTE FUNCTION dr_os.touch_updated_at();

CREATE TRIGGER touch_principals_updated_at
  BEFORE UPDATE ON dr_os.principals
  FOR EACH ROW EXECUTE FUNCTION dr_os.touch_updated_at();

CREATE TRIGGER touch_projects_updated_at
  BEFORE UPDATE ON dr_os.projects
  FOR EACH ROW EXECUTE FUNCTION dr_os.touch_updated_at();

CREATE TRIGGER touch_datasets_updated_at
  BEFORE UPDATE ON dr_os.datasets
  FOR EACH ROW EXECUTE FUNCTION dr_os.touch_updated_at();

CREATE TRIGGER touch_manuscripts_updated_at
  BEFORE UPDATE ON dr_os.manuscripts
  FOR EACH ROW EXECUTE FUNCTION dr_os.touch_updated_at();

CREATE TRIGGER artifacts_append_only_no_update
  BEFORE UPDATE OR DELETE ON dr_os.artifacts
  FOR EACH ROW EXECUTE FUNCTION dr_os.prevent_append_only_mutation();

CREATE TRIGGER assertions_append_only_no_update
  BEFORE UPDATE OR DELETE ON dr_os.assertions
  FOR EACH ROW EXECUTE FUNCTION dr_os.prevent_append_only_mutation();

CREATE TRIGGER evidence_links_append_only_no_update
  BEFORE UPDATE OR DELETE ON dr_os.evidence_links
  FOR EACH ROW EXECUTE FUNCTION dr_os.prevent_append_only_mutation();

CREATE TRIGGER audit_events_append_only_no_update
  BEFORE UPDATE OR DELETE ON dr_os.audit_events
  FOR EACH ROW EXECUTE FUNCTION dr_os.prevent_append_only_mutation();

ALTER TABLE dr_os.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.tenants FORCE ROW LEVEL SECURITY;
CREATE POLICY tenants_isolation ON dr_os.tenants
  USING (id = dr_os.current_tenant_id())
  WITH CHECK (id = dr_os.current_tenant_id());

ALTER TABLE dr_os.principals ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.principals FORCE ROW LEVEL SECURITY;
CREATE POLICY principals_isolation ON dr_os.principals
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.projects FORCE ROW LEVEL SECURITY;
CREATE POLICY projects_isolation ON dr_os.projects
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.project_members FORCE ROW LEVEL SECURITY;
CREATE POLICY project_members_isolation ON dr_os.project_members
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.datasets FORCE ROW LEVEL SECURITY;
CREATE POLICY datasets_isolation ON dr_os.datasets
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.dataset_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.dataset_snapshots FORCE ROW LEVEL SECURITY;
CREATE POLICY dataset_snapshots_isolation ON dr_os.dataset_snapshots
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.analysis_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.analysis_templates FORCE ROW LEVEL SECURITY;
CREATE POLICY analysis_templates_scope ON dr_os.analysis_templates
  USING (tenant_id IS NULL OR tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id IS NULL OR tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.workflow_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.workflow_instances FORCE ROW LEVEL SECURITY;
CREATE POLICY workflow_instances_isolation ON dr_os.workflow_instances
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.workflow_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.workflow_tasks FORCE ROW LEVEL SECURITY;
CREATE POLICY workflow_tasks_isolation ON dr_os.workflow_tasks
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.analysis_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY analysis_runs_isolation ON dr_os.analysis_runs
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.artifacts FORCE ROW LEVEL SECURITY;
CREATE POLICY artifacts_isolation ON dr_os.artifacts
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.lineage_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.lineage_edges FORCE ROW LEVEL SECURITY;
CREATE POLICY lineage_edges_isolation ON dr_os.lineage_edges
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.assertions ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.assertions FORCE ROW LEVEL SECURITY;
CREATE POLICY assertions_isolation ON dr_os.assertions
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.evidence_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.evidence_links FORCE ROW LEVEL SECURITY;
CREATE POLICY evidence_links_isolation ON dr_os.evidence_links
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.manuscripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.manuscripts FORCE ROW LEVEL SECURITY;
CREATE POLICY manuscripts_isolation ON dr_os.manuscripts
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.manuscript_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.manuscript_blocks FORCE ROW LEVEL SECURITY;
CREATE POLICY manuscript_blocks_isolation ON dr_os.manuscript_blocks
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.block_assertion_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.block_assertion_links FORCE ROW LEVEL SECURITY;
CREATE POLICY block_assertion_links_isolation ON dr_os.block_assertion_links
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY reviews_isolation ON dr_os.reviews
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.export_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.export_jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY export_jobs_isolation ON dr_os.export_jobs
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

ALTER TABLE dr_os.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE dr_os.audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_events_isolation ON dr_os.audit_events
  USING (tenant_id = dr_os.current_tenant_id())
  WITH CHECK (tenant_id = dr_os.current_tenant_id());

COMMIT;

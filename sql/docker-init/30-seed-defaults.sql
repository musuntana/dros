-- Seed default tenant and principal for the dr_os row-level schema.
-- These align with backend/app/auth.py DEFAULT_TENANT_ID / DEFAULT_PRINCIPAL_ID
-- so that the postgres_rowlevel backend works out of the box in dev mode.

BEGIN;

INSERT INTO dr_os.tenants (id, name, tier, deployment_mode, status)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'Default Dev Tenant',
  'community',
  'saas',
  'active'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO dr_os.principals (id, tenant_id, subject_type, external_sub, display_name, status)
VALUES (
  '00000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000001',
  'human',
  'dev-default',
  'Dev Default User',
  'active'
)
ON CONFLICT (id) DO NOTHING;

COMMIT;

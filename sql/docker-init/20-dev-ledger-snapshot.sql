BEGIN;

CREATE SCHEMA IF NOT EXISTS dr_os_dev;

CREATE TABLE IF NOT EXISTS dr_os_dev.ledger_snapshots (
  snapshot_key text PRIMARY KEY,
  payload jsonb NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;

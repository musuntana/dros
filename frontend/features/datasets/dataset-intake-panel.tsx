"use client";

import { useActionState } from "react";

import {
  importPublicDatasetAction,
  registerUploadDatasetAction,
} from "@/features/datasets/actions";

const initialDatasetActionState = {
  message: null,
  status: "idle" as const,
};

function ActionMessage({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }

  return <p className="mt-3 text-sm text-danger">{message}</p>;
}

export function DatasetIntakePanel({ projectId }: { projectId: string }) {
  const [importState, importAction, importPending] = useActionState(
    importPublicDatasetAction.bind(null, projectId),
    initialDatasetActionState,
  );
  const [uploadState, uploadAction, uploadPending] = useActionState(
    registerUploadDatasetAction.bind(null, projectId),
    initialDatasetActionState,
  );

  return (
    <section className="grid gap-6 xl:grid-cols-2">
      <form
        action={importAction}
        className="rounded-card border border-subtle bg-surface p-5 shadow-soft"
        data-testid="dataset-import-form"
      >
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Public Import</p>
        <h2 className="mt-3 font-serif text-2xl text-strong">Register a public dataset</h2>
        <p className="mt-3 text-sm leading-7 text-muted">
          This path creates a project-scoped `dataset` plus first immutable `dataset_snapshot`. Use GEO, TCGA, or SEER
          accessions here.
        </p>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Accession</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0"
              defaultValue="GSE000000"
              name="accession"
              placeholder="GSE12345"
              required
              type="text"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Source Kind</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0"
              defaultValue="geo"
              name="source_kind"
            >
              <option value="geo">geo</option>
              <option value="tcga">tcga</option>
              <option value="seer">seer</option>
            </select>
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={importPending}
          type="submit"
        >
          {importPending ? "Registering..." : "Import public dataset"}
        </button>
        <ActionMessage message={importState.message} />
      </form>

      <form
        action={uploadAction}
        className="rounded-card border border-subtle bg-surface p-5 shadow-soft"
        data-testid="dataset-upload-form"
      >
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Upload Intake</p>
        <h2 className="mt-3 font-serif text-2xl text-strong">Upload and register a dataset</h2>
        <p className="mt-3 text-sm leading-7 text-muted">
          This path now runs the real `GatewayClient` sign-upload-complete flow, then registers the resulting `file_ref`
          as a project-scoped dataset with pending PHI and de-identification checks.
        </p>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Display Name</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0"
              defaultValue="Clinical upload"
              name="display_name"
              placeholder="Clinical upload"
              required
              type="text"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Local File</span>
            <input
              accept=".csv,.tsv,.txt,.json,.xlsx,.xls"
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none ring-0 file:mr-4 file:rounded-full file:border-0 file:bg-secondary file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white"
              data-testid="dataset-upload-input"
              name="file"
              required
              type="file"
            />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-secondary px-5 py-3 text-sm font-semibold text-white transition hover:bg-secondary/90 disabled:cursor-not-allowed disabled:opacity-60"
          data-testid="dataset-upload-submit"
          disabled={uploadPending}
          type="submit"
        >
          {uploadPending ? "Uploading..." : "Upload dataset"}
        </button>
        <ActionMessage message={uploadState.message} />
      </form>
    </section>
  );
}

"use client";

import { useActionState } from "react";

import type { AssertionRead, EvidenceSourceRead } from "@/lib/api/generated/control-plane";

import {
  createEvidenceLinkAction,
  resolveEvidenceAction,
  searchEvidenceAction,
  upsertEvidenceSourceAction,
} from "@/features/evidence/actions";

const initialEvidenceSearchActionState = {
  message: null,
  status: "idle" as const,
};

const initialEvidenceResolveActionState = {
  message: null,
  status: "idle" as const,
};

const initialEvidenceMutationActionState = {
  message: null,
  status: "idle" as const,
};

function ActionMessage({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }

  return <p className="mt-3 text-sm text-danger">{message}</p>;
}

export function EvidenceControlPanels({
  assertions,
  projectId,
  sources,
}: {
  assertions: AssertionRead[];
  projectId: string;
  sources: EvidenceSourceRead[];
}) {
  const [searchState, searchAction, searchPending] = useActionState(
    searchEvidenceAction.bind(null, projectId),
    initialEvidenceSearchActionState,
  );
  const [resolveState, resolveAction, resolvePending] = useActionState(
    resolveEvidenceAction.bind(null, projectId),
    initialEvidenceResolveActionState,
  );
  const [sourceState, sourceAction, sourcePending] = useActionState(
    upsertEvidenceSourceAction.bind(null, projectId),
    initialEvidenceMutationActionState,
  );
  const [linkState, linkAction, linkPending] = useActionState(
    createEvidenceLinkAction.bind(null, projectId),
    initialEvidenceMutationActionState,
  );

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <form action={searchAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Search</p>
        <h2 className="mt-3 font-serif text-2xl text-strong">Search cached project evidence</h2>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Query</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="EGFR survival"
              name="query"
              type="text"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">PICO Question</span>
            <textarea
              className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              name="pico_question"
            />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={searchPending}
          type="submit"
        >
          {searchPending ? "Searching..." : "Search evidence"}
        </button>
        <ActionMessage message={searchState.message} />
        {searchState.result?.results?.length ? (
          <div className="mt-4 space-y-3">
            {searchState.result.results.map((result) => (
              <article key={result.dedupe_key} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{result.match_reason}</p>
                <p className="mt-2 text-sm font-medium text-strong">{result.title}</p>
                <p className="mt-2 text-xs text-muted">
                  {result.pmid ?? result.pmcid ?? result.doi ?? "no identifier"} · {result.journal ?? "unknown journal"}
                </p>
              </article>
            ))}
          </div>
        ) : null}
      </form>

      <form action={resolveAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Resolve</p>
        <h2 className="mt-3 font-serif text-2xl text-strong">Bind identifiers into the project</h2>
        <label className="mt-5 grid gap-2">
          <span className="text-sm font-medium text-strong">Identifiers</span>
          <textarea
            className="min-h-28 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
            defaultValue="12345678"
            name="identifiers"
          />
        </label>
        <button
          className="mt-5 rounded-pill bg-secondary px-5 py-3 text-sm font-semibold text-white transition hover:bg-secondary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={resolvePending}
          type="submit"
        >
          {resolvePending ? "Resolving..." : "Resolve evidence"}
        </button>
        <ActionMessage message={resolveState.message} />
        {resolveState.result ? (
          <div className="mt-4 space-y-3 text-sm text-muted">
            <p>Resolved: {resolveState.result.resolved.length}</p>
            <p>Unresolved: {resolveState.result.unresolved.join(", ") || "None"}</p>
          </div>
        ) : null}
      </form>

      <form action={sourceAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Source</p>
        <h2 className="mt-3 font-serif text-2xl text-strong">Upsert an evidence source</h2>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">External ID</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="PMID:12345678"
              name="external_id_norm"
              required
              type="text"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Source Type</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="pubmed"
              name="source_type"
            >
              <option value="pubmed">pubmed</option>
              <option value="pmc">pmc</option>
              <option value="geo">geo</option>
              <option value="tcga">tcga</option>
              <option value="manual">manual</option>
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Title</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="Example evidence source"
              name="title"
              required
              type="text"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">PMID</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="pmid" type="text" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">PMCID</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="pmcid" type="text" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">DOI</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="doi_norm" type="text" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Journal</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="journal" type="text" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Publication Year</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="pub_year" type="number" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">License Class</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="public"
              name="license_class"
            >
              <option value="unknown">unknown</option>
              <option value="public">public</option>
              <option value="metadata_only">metadata_only</option>
              <option value="pmc_oa_subset">pmc_oa_subset</option>
              <option value="restricted">restricted</option>
              <option value="internal">internal</option>
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">OA Subset Flag</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="false"
              name="oa_subset_flag"
            >
              <option value="false">false</option>
              <option value="true">true</option>
            </select>
          </label>
          <label className="grid gap-2 xl:col-span-2">
            <span className="text-sm font-medium text-strong">Metadata JSON</span>
            <textarea
              className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue={'{"source":"manual"}'}
              name="metadata_json"
            />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={sourcePending}
          type="submit"
        >
          {sourcePending ? "Saving..." : "Upsert evidence source"}
        </button>
        <ActionMessage message={sourceState.message} />
      </form>

      <form action={linkAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Link</p>
        <h2 className="mt-3 font-serif text-2xl text-strong">Create an assertion-evidence link</h2>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Assertion</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
              defaultValue={assertions[0]?.id ?? ""}
              name="assertion_id"
            >
              {assertions.map((assertion) => (
                <option key={assertion.id} value={assertion.id}>
                  {assertion.id.slice(0, 8)} · {assertion.assertion_type}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Evidence Source</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
              defaultValue={sources[0]?.id ?? ""}
              name="evidence_source_id"
            >
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.id.slice(0, 8)} · {source.title}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Relation</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="supports"
              name="relation_type"
            >
              <option value="supports">supports</option>
              <option value="contradicts">contradicts</option>
              <option value="method_ref">method_ref</option>
              <option value="background_ref">background_ref</option>
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Confidence</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" defaultValue="1" max="1" min="0" name="confidence" step="0.01" type="number" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Source Span Start</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="source_span_start" type="number" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Source Span End</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="source_span_end" type="number" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Source Chunk ID</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="source_chunk_id" type="text" />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Excerpt Hash</span>
            <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none" name="excerpt_hash" type="text" />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={linkPending || assertions.length === 0 || sources.length === 0}
          type="submit"
        >
          {linkPending ? "Linking..." : "Create evidence link"}
        </button>
        <ActionMessage message={linkState.message} />
      </form>
    </div>
  );
}

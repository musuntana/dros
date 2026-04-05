"use client";

import { useActionState } from "react";

import type { AssertionRead, ManuscriptRead } from "@/lib/api/generated/control-plane";

import {
  createManuscriptAction,
  createManuscriptBlockAction,
  createManuscriptVersionAction,
} from "@/features/manuscripts/actions";

const initialManuscriptActionState = {
  message: null,
  status: "idle" as const,
};

export function ManuscriptCreationPanel({ projectId }: { projectId: string }) {
  const [state, action, pending] = useActionState(
    createManuscriptAction.bind(null, projectId),
    initialManuscriptActionState,
  );

  return (
    <form action={action} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Manuscript</p>
      <h2 className="mt-3 font-serif text-2xl text-strong">Create a manuscript workspace</h2>
      <div className="mt-5 grid gap-4">
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Title</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="Project manuscript"
            name="title"
            required
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Type</span>
          <select
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue="manuscript"
            name="manuscript_type"
          >
            <option value="manuscript">manuscript</option>
            <option value="abstract">abstract</option>
            <option value="grant_response">grant_response</option>
          </select>
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Target Journal</span>
          <input
            className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            name="target_journal"
            type="text"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-medium text-strong">Style Profile JSON</span>
          <textarea
            className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
            defaultValue={'{"tone":"formal","citation_style":"vancouver"}'}
            name="style_profile_json"
          />
        </label>
      </div>
      <button
        className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending}
        type="submit"
      >
        {pending ? "Creating..." : "Create manuscript"}
      </button>
      {state.message ? <p className="mt-3 text-sm text-danger">{state.message}</p> : null}
    </form>
  );
}

export function ManuscriptBlockPanel({
  manuscript,
  projectId,
  verifiedAssertions,
}: {
  manuscript: ManuscriptRead;
  projectId: string;
  verifiedAssertions: AssertionRead[];
}) {
  const [blockState, blockAction, blockPending] = useActionState(
    createManuscriptBlockAction.bind(null, projectId, manuscript.id),
    initialManuscriptActionState,
  );
  const [versionState, versionAction, versionPending] = useActionState(
    createManuscriptVersionAction.bind(null, projectId, manuscript.id),
    initialManuscriptActionState,
  );

  return (
    <div className="space-y-6">
      <form action={blockAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Block</p>
        <h3 className="mt-3 font-serif text-2xl text-strong">Add a manuscript block</h3>
        <p className="mt-3 text-sm leading-7 text-muted">
          Use verified assertion ids only. The backend will reject draft or blocked assertions.
        </p>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Section</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="results"
              name="section_key"
            >
              <option value="title">title</option>
              <option value="abstract">abstract</option>
              <option value="introduction">introduction</option>
              <option value="methods">methods</option>
              <option value="results">results</option>
              <option value="discussion">discussion</option>
              <option value="conclusion">conclusion</option>
              <option value="figure_legend">figure_legend</option>
              <option value="table_note">table_note</option>
              <option value="appendix">appendix</option>
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Block Type</span>
            <select
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="text"
              name="block_type"
            >
              <option value="text">text</option>
              <option value="figure">figure</option>
              <option value="table">table</option>
              <option value="citation_list">citation_list</option>
            </select>
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Block Order</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="0"
              min="0"
              name="block_order"
              type="number"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Content Markdown</span>
            <textarea
              className="min-h-28 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="Cox regression showed the marker was associated with overall survival."
              name="content_md"
              required
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Assertion IDs</span>
            <textarea
              className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
              defaultValue={verifiedAssertions[0]?.id ?? ""}
              name="assertion_ids"
              placeholder="One verified assertion id per line"
            />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={blockPending}
          type="submit"
        >
          {blockPending ? "Creating..." : "Create block"}
        </button>
        {blockState.message ? <p className="mt-3 text-sm text-danger">{blockState.message}</p> : null}
      </form>

      <form action={versionAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Version</p>
        <h3 className="mt-3 font-serif text-2xl text-strong">Advance manuscript version</h3>
        <div className="mt-5 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Base Version</span>
            <input
              className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue={manuscript.current_version_no.toString()}
              min="1"
              name="base_version_no"
              type="number"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-sm font-medium text-strong">Reason</span>
            <textarea
              className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
              defaultValue="Prepare next reviewed version."
              name="reason"
            />
          </label>
        </div>
        <button
          className="mt-5 rounded-pill bg-secondary px-5 py-3 text-sm font-semibold text-white transition hover:bg-secondary/90 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={versionPending}
          type="submit"
        >
          {versionPending ? "Creating..." : "Create new version"}
        </button>
        {versionState.message ? <p className="mt-3 text-sm text-danger">{versionState.message}</p> : null}
      </form>
    </div>
  );
}

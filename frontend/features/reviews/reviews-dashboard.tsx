"use client";

import { useActionState } from "react";

import type { ArtifactRead, AssertionRead, ManuscriptRead, ReviewRead } from "@/lib/api/generated/control-plane";
import { formatDateTime } from "@/lib/format/date";

import {
  createReviewAction,
  decideReviewAction,
  runVerificationAction,
} from "@/features/reviews/actions";

const initialReviewActionState = {
  message: null,
  status: "idle" as const,
};

export function ReviewsDashboard({
  artifacts,
  assertions,
  manuscripts,
  projectId,
  reviews,
}: {
  artifacts: ArtifactRead[];
  assertions: AssertionRead[];
  manuscripts: ManuscriptRead[];
  projectId: string;
  reviews: ReviewRead[];
}) {
  const [createState, createAction, createPending] = useActionState(
    createReviewAction.bind(null, projectId),
    initialReviewActionState,
  );
  const [verifyState, verifyAction, verifyPending] = useActionState(
    runVerificationAction.bind(null, projectId),
    initialReviewActionState,
  );

  return (
    <div className="space-y-6">
      <section className="rounded-card border border-subtle bg-surface p-6 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Reviews</p>
        <h1 className="mt-3 font-serif text-4xl text-strong">Verification and operator decisions</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
          Reviews track explicit human or system decisions. Verification creates gate-backed workflow records rather than
          silently mutating manuscript readiness.
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <form action={createAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Review</p>
          <h2 className="mt-3 font-serif text-2xl text-strong">Create a review item</h2>
          <div className="mt-5 grid gap-4">
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Review Type</span>
              <select className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" defaultValue="manuscript" name="review_type">
                <option value="evidence">evidence</option>
                <option value="analysis">analysis</option>
                <option value="manuscript">manuscript</option>
                <option value="export">export</option>
              </select>
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Target Kind</span>
              <select className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" defaultValue="manuscript" name="target_kind">
                <option value="manuscript">manuscript</option>
                <option value="assertion">assertion</option>
                <option value="artifact">artifact</option>
                <option value="export_job">export_job</option>
              </select>
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Target ID</span>
              <input
                className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
                defaultValue={manuscripts[0]?.id ?? assertions[0]?.id ?? artifacts[0]?.id ?? ""}
                name="target_id"
                required
                type="text"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Reviewer ID</span>
              <input className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="reviewer_id" type="text" />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Checklist JSON</span>
              <textarea
                className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none"
                defaultValue='[{"check":"assertion_traceable","status":"pending"}]'
                name="checklist_json"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Comments</span>
              <textarea className="min-h-20 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm text-strong outline-none" name="comments" />
            </label>
          </div>
          <button
            className="mt-5 rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={createPending}
            type="submit"
          >
            {createPending ? "Creating..." : "Create review"}
          </button>
          {createState.message ? <p className="mt-3 text-sm text-danger">{createState.message}</p> : null}
        </form>

        <form action={verifyAction} className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Verify</p>
          <h2 className="mt-3 font-serif text-2xl text-strong">Run gate verification</h2>
          <p className="mt-3 text-sm leading-7 text-muted">
            Verification creates a workflow trail. For manuscript verification, pass the manuscript id. For targeted
            source checks, pass assertion or artifact ids.
          </p>
          <div className="mt-5 grid gap-4">
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Manuscript ID</span>
              <input
                className="rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
                defaultValue={manuscripts[0]?.id ?? ""}
                name="manuscript_id"
                type="text"
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-medium text-strong">Target IDs</span>
              <textarea
                className="min-h-24 rounded-2xl border border-subtle bg-app px-4 py-3 text-sm font-mono text-strong outline-none"
                defaultValue={assertions.slice(0, 2).map((assertion) => assertion.id).join("\n")}
                name="target_ids"
              />
            </label>
          </div>
          <button
            className="mt-5 rounded-pill bg-secondary px-5 py-3 text-sm font-semibold text-white transition hover:bg-secondary/90 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={verifyPending}
            type="submit"
          >
            {verifyPending ? "Verifying..." : "Run verification"}
          </button>
          {verifyState.message ? <p className="mt-3 text-sm text-danger">{verifyState.message}</p> : null}
        </form>
      </section>

      <section className="rounded-card border border-subtle bg-surface p-5 shadow-soft">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Review Queue</p>
        <div className="mt-4 space-y-4">
          {reviews.length > 0 ? (
            reviews.map((review) => (
              <article key={review.id} className="rounded-2xl border border-subtle bg-app px-4 py-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                      {review.review_type} · {review.target_kind}
                    </p>
                    <p className="mt-2 break-all text-sm font-medium text-strong">{review.target_id}</p>
                    <p className="mt-2 text-xs text-muted">{formatDateTime(review.created_at)}</p>
                  </div>
                  <span className="rounded-pill border border-subtle bg-white/70 px-3 py-1 text-xs font-semibold text-strong">
                    {review.state}
                  </span>
                </div>
                <p className="mt-3 text-sm text-muted">{review.comments ?? "No comments."}</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <form action={decideReviewAction.bind(null, projectId, review.id, "approve")}>
                    <input name="comments" type="hidden" value="Approved from reviews workspace." />
                    <button
                      className="rounded-pill bg-primary px-4 py-2 text-xs font-semibold text-white"
                      type="submit"
                    >
                      Approve
                    </button>
                  </form>
                  <form action={decideReviewAction.bind(null, projectId, review.id, "request_changes")}>
                    <input name="comments" type="hidden" value="Changes requested from reviews workspace." />
                    <button
                      className="rounded-pill border border-warning/30 bg-warning/10 px-4 py-2 text-xs font-semibold text-warning"
                      type="submit"
                    >
                      Request changes
                    </button>
                  </form>
                  <form action={decideReviewAction.bind(null, projectId, review.id, "reject")}>
                    <input name="comments" type="hidden" value="Rejected from reviews workspace." />
                    <button
                      className="rounded-pill border border-danger/30 bg-danger/10 px-4 py-2 text-xs font-semibold text-danger"
                      type="submit"
                    >
                      Reject
                    </button>
                  </form>
                </div>
              </article>
            ))
          ) : (
            <p className="text-sm text-muted">No review record exists yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

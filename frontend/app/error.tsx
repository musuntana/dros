"use client";

import { ErrorCard } from "@/components/status/error-card";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="space-y-4">
      <ErrorCard message={error.message} title="Workspace crashed" />
      <button
        className="rounded-pill bg-primary px-5 py-3 text-sm font-semibold text-white"
        onClick={reset}
        type="button"
      >
        Retry
      </button>
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { StatusBadge } from "@/components/status/status-badge";
import { cn } from "@/lib/utils";

const sections = [
  { label: "Overview", segment: "" },
  { label: "Datasets", segment: "datasets" },
  { label: "Workflows", segment: "workflows" },
  { label: "Artifacts", segment: "artifacts" },
  { label: "Assertions", segment: "assertions" },
  { label: "Evidence", segment: "evidence" },
  { label: "Manuscripts", segment: "manuscripts" },
  { label: "Reviews", segment: "reviews" },
  { label: "Exports", segment: "exports" },
  { label: "Audit", segment: "audit" },
];

export function ObjectRail({
  projectId,
  projectStatus,
}: {
  projectId: string;
  projectStatus: string;
}) {
  const pathname = usePathname();

  return (
    <aside className="rounded-card border border-subtle bg-surface p-4 shadow-soft" data-testid="object-rail">
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Object Chain</p>
        <StatusBadge label={projectStatus} />
      </div>
      <nav className="mt-4 flex gap-2 overflow-x-auto pb-1 xl:block xl:space-y-2 xl:overflow-visible xl:pb-0">
        {sections.map((section) => {
          const href = section.segment
            ? `/projects/${projectId}/${section.segment}`
            : `/projects/${projectId}`;
          const active =
            pathname === href || (section.segment !== "" && pathname.startsWith(`${href}/`));

          return (
            <Link
              key={section.label}
              className={cn(
                "flex min-w-[152px] shrink-0 items-center justify-between rounded-2xl border px-3 py-3 text-sm transition xl:min-w-0",
                active
                  ? "border-primary/30 bg-primary/10 text-primary"
                  : "border-subtle bg-app text-strong hover:border-primary/20 hover:bg-primary/5",
              )}
              href={href}
            >
              <span>{section.label}</span>
              <span className="font-mono text-[11px] uppercase tracking-[0.18em]">
                {section.segment || "root"}
              </span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

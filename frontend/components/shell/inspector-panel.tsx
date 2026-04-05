"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export interface InspectorItem {
  label: string;
  value: string;
}

export interface InspectorAction {
  label: string;
  href: string;
}

export interface InspectorSection {
  title: string;
  items: InspectorItem[];
}

export interface InspectorFocus {
  id: string;
  eyebrow: string;
  title: string;
  summary: string;
  items: InspectorItem[];
  actions: InspectorAction[];
  payload: Record<string, unknown>;
}

export function InspectorPanel({
  focus,
  sections,
}: {
  focus?: InspectorFocus | null;
  sections: InspectorSection[];
}) {
  const [expanded, setExpanded] = useState(false);
  const previousFocusIdRef = useRef<string | null>(focus?.id ?? null);

  useEffect(() => {
    if (focus?.id && previousFocusIdRef.current && previousFocusIdRef.current !== focus.id) {
      setExpanded(true);
    }

    previousFocusIdRef.current = focus?.id ?? null;
  }, [focus?.id]);

  return (
    <aside
      className="rounded-card border border-subtle bg-surface p-5 shadow-soft xl:max-h-[calc(100vh-1.5rem)] xl:overflow-hidden"
      data-testid="workspace-inspector"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Inspector</p>
        <button
          className="rounded-full border border-subtle bg-app px-3 py-2 text-xs font-semibold text-strong xl:hidden"
          data-testid="workspace-inspector-toggle"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? "Hide details" : "Show details"}
        </button>
      </div>
      <div className={`mt-4 space-y-5 ${expanded ? "block" : "hidden"} xl:block xl:overflow-y-auto xl:pr-1`}>
        {focus ? (
          <section
            className="rounded-3xl border border-primary/20 bg-primary/5 px-4 py-4"
            data-testid="workspace-inspector-focus"
          >
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">{focus.eyebrow}</p>
            <h3
              className="mt-2 font-serif text-2xl text-strong"
              data-testid="workspace-inspector-focus-title"
            >
              {focus.title}
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">{focus.summary}</p>
            <ul className="mt-4 space-y-2 text-sm text-muted">
              {focus.items.map((item) => (
                <li
                  key={`focus:${item.label}`}
                  className="rounded-2xl border border-primary/15 bg-surface px-3 py-3 leading-6"
                >
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{item.label}</p>
                  <p className="mt-2 break-all text-sm text-strong">{item.value}</p>
                </li>
              ))}
            </ul>
            {focus.actions.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {focus.actions.map((action) => (
                  <Link
                    key={`${action.label}:${action.href}`}
                    className={cn(
                      "rounded-pill border px-3 py-2 text-xs font-semibold transition",
                      "border-primary/20 bg-surface text-primary hover:border-primary/30 hover:bg-primary/10",
                    )}
                    href={action.href}
                  >
                    {action.label}
                  </Link>
                ))}
              </div>
            ) : null}
            {Object.keys(focus.payload).length > 0 ? (
              <pre className="mt-4 overflow-x-auto whitespace-pre-wrap break-all rounded-2xl border border-subtle bg-surface px-3 py-3 font-mono text-xs text-strong">
                {JSON.stringify(focus.payload, null, 2)}
              </pre>
            ) : null}
          </section>
        ) : null}
        {sections.map((section) => (
          <section key={section.title}>
            <h3 className="font-serif text-xl text-strong">{section.title}</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              {section.items.map((item) => (
                <li
                  key={`${section.title}:${item.label}`}
                  className="rounded-2xl border border-subtle bg-app px-3 py-3 leading-6"
                >
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{item.label}</p>
                  <p className="mt-2 break-all text-sm text-strong">{item.value}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </aside>
  );
}

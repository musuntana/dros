import type { ReactNode } from "react";

import Link from "next/link";

import { StatusBadge } from "@/components/status/status-badge";

export interface EntityColumn<Row> {
  key: string;
  label: string;
  render: (row: Row) => ReactNode;
}

export function EntityTable<Row extends { id: string }>({
  rows,
  columns,
  getHref,
  emptyMessage,
}: {
  rows: Row[];
  columns: Array<EntityColumn<Row>>;
  getHref?: (row: Row) => string;
  emptyMessage: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="rounded-card border border-subtle bg-surface p-6 text-sm text-muted shadow-soft">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-card border border-subtle bg-surface shadow-soft">
      <table className="min-w-full border-collapse text-left">
        <thead className="bg-elevated text-xs uppercase tracking-[0.18em] text-muted">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="px-4 py-3 font-mono font-medium">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-subtle text-sm text-strong">
              {columns.map((column, columnIndex) => {
                const content = column.render(row);
                const cell = (
                  <td key={column.key} className="px-4 py-4 align-top">
                    {columnIndex === 0 && getHref ? (
                      <Link className="font-semibold text-primary hover:text-primary/80" href={getHref(row)}>
                        {content}
                      </Link>
                    ) : (
                      content
                    )}
                  </td>
                );
                return cell;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TableStatusCell({ value }: { value: string }) {
  return <StatusBadge label={value} />;
}

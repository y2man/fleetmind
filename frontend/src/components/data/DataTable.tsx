import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { Skeleton } from "@/components/ui";
import type { Column } from "@/features/resource/types";

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  loading: boolean;
  sort: string;
  order: "asc" | "desc";
  onSort: (key: string) => void;
  rowKey: (row: T) => string;
  actions?: (row: T) => ReactNode;
  empty: ReactNode;
}

export function DataTable<T>({ columns, rows, loading, sort, order, onSort, rowKey, actions, empty }: Props<T>) {
  const reduceMotion = useReducedMotion();
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="text-muted">
          <tr>
            {columns.map((c) => {
              const active = c.sort === sort;
              return (
                <th key={c.header} scope="col" className="whitespace-nowrap p-2 font-medium" aria-sort={c.sort ? (active ? (order === "asc" ? "ascending" : "descending") : "none") : undefined}>
                  {c.sort ? (
                    <button onClick={() => onSort(c.sort!)} className="focus-ring inline-flex items-center gap-1 rounded hover:text-ink">
                      {c.header}
                      {active ? (order === "asc" ? <ArrowUp size={14} /> : <ArrowDown size={14} />) : <ChevronsUpDown size={14} className="opacity-50" />}
                    </button>
                  ) : c.header}
                </th>
              );
            })}
            {actions && <th scope="col" className="p-2"><span className="sr-only">Actions</span></th>}
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0
            ? Array.from({ length: 6 }, (_, i) => (
                <tr key={i} className="border-t border-line"><td colSpan={columns.length + (actions ? 1 : 0)} className="p-2"><Skeleton className="h-6" /></td></tr>
              ))
            : rows.map((r, index) => (
                <motion.tr
                  key={rowKey(r)}
                  initial={reduceMotion ? false : { opacity: 0, y: 16, scale: 0.99 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: reduceMotion ? 0 : 0.42, delay: reduceMotion ? 0 : Math.min(index * 0.04, 0.36), ease: [0.22, 1, 0.36, 1] }}
                  className="border-t border-line align-top hover:bg-electric/5"
                >
                  {columns.map((c) => <td key={c.header} className="p-2">{c.cell(r)}</td>)}
                  {actions && <td className="whitespace-nowrap p-2 text-right">{actions(r)}</td>}
                </motion.tr>
              ))}
        </tbody>
      </table>
      {!loading && rows.length === 0 && <div className="py-10 text-center text-muted">{empty}</div>}
    </div>
  );
}

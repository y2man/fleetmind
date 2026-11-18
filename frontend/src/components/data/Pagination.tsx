import { Button, Dropdown } from "@/components/ui";

const SIZES = [{ value: "10", label: "10 / page" }, { value: "20", label: "20 / page" }, { value: "50", label: "50 / page" }];

interface Props { page: number; pageSize: number; total: number; onPage: (p: number) => void; onPageSize: (s: number) => void }

export function Pagination({ page, pageSize, total, onPage, onPageSize }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
      <span aria-live="polite">{from}–{to} of {total}</span>
      <div className="flex items-center gap-2">
        <Dropdown label="Page size" options={SIZES} value={String(pageSize)} onChange={(v) => onPageSize(Number(v))} />
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</Button>
        <span>Page {page} of {pages}</span>
        <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</Button>
      </div>
    </div>
  );
}

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { DataTable } from "@/components/data/DataTable";
import { Pagination } from "@/components/data/Pagination";
import { Button, Dropdown, GlassCard, Modal } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { useDebounced } from "@/hooks/useDebounced";
import { resource } from "@/services/resources";
import { useAuth } from "@/store/auth";
import { ResourceForm } from "./ResourceForm";
import type { ResourceConfig } from "./types";

/** One config-driven page: search, filters, sortable + paginated table, create/edit modal, delete confirmation. */
export function ResourcePage<T extends { id: string }>({ cfg }: { cfg: ResourceConfig<T> }) {
  const api = useMemo(() => resource<T>(cfg.path), [cfg.path]);
  const { can } = useAuth();
  const canWrite = can(`${cfg.permission}:write`);
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("q") ?? "");
  const q = useDebounced(search.trim());
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sort, setSort] = useState(cfg.defaultSort);
  const [order, setOrder] = useState<"asc" | "desc">(cfg.defaultOrder);
  const [editing, setEditing] = useState<T | "new" | null>(null);
  const [deleting, setDeleting] = useState<T | null>(null);

  const queryParams = { page, page_size: pageSize, q, sort, order, ...filters };
  const list = useQuery({ queryKey: [cfg.path, queryParams], queryFn: () => api.list(queryParams), placeholderData: (prev) => prev });
  const rows = list.data?.items ?? [];
  const total = list.data?.total ?? 0;

  // Global search links here with ?q=...; apply it when it changes (also when this page is already open).
  const urlQuery = searchParams.get("q");
  useEffect(() => { if (urlQuery !== null) { setSearch(urlQuery); setPage(1); } }, [urlQuery]);

  // If the last row of the last page was deleted, step back one page.
  useEffect(() => { if (list.data && rows.length === 0 && page > 1) setPage((p) => p - 1); }, [list.data, rows.length, page]);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: [cfg.path] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["options"] });
  };
  const save = useMutation({
    mutationFn: (a: { id?: string; body: Record<string, unknown> }) => (a.id ? api.update(a.id, a.body) : api.create(a.body)),
    onSuccess: () => { refresh(); setEditing(null); },
  });
  const remove = useMutation({ mutationFn: (id: string) => api.remove(id), onSuccess: () => { refresh(); setDeleting(null); } });

  const onSort = (key: string) => {
    if (key === sort) setOrder((o) => (o === "asc" ? "desc" : "asc"));
    else { setSort(key); setOrder("asc"); }
    setPage(1);
  };
  const filtered = q !== "" || Object.values(filters).some(Boolean);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-gradient text-3xl font-extrabold">{cfg.title}</h1><p className="text-muted">{cfg.subtitle}</p></div>
        {canWrite && <Button onClick={() => { save.reset(); setEditing("new"); }}><Plus size={16} />Add {cfg.singular}</Button>}
      </div>

      <GlassCard hover={false}>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="relative min-w-56 flex-1">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input aria-label={`Search ${cfg.title.toLowerCase()}`} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder={cfg.searchPlaceholder}
              className="focus-ring w-full rounded-xl border border-line bg-bg/60 py-2 pl-9 pr-3 text-ink placeholder:text-muted/60" />
          </div>
          {cfg.filters.map((f) => (
            <Dropdown key={f.name} label={f.label} value={filters[f.name] ?? ""} options={[{ value: "", label: `All ${f.label.toLowerCase()}` }, ...f.options]}
              onChange={(v) => { setFilters((s) => ({ ...s, [f.name]: v })); setPage(1); }} />
          ))}
          {filtered && <Button variant="ghost" size="sm" onClick={() => { setSearch(""); setFilters({}); setPage(1); }}>Clear</Button>}
        </div>

        {list.isError ? (
          <div className="space-y-3"><FormError message={list.error.message} /><Button variant="outline" size="sm" onClick={() => list.refetch()}>Try again</Button></div>
        ) : (
          <>
            <DataTable<T>
              columns={cfg.columns} rows={rows} loading={list.isLoading} sort={sort} order={order} onSort={onSort} rowKey={(r) => r.id}
              empty={filtered ? "No results match your search or filters." : canWrite ? `No ${cfg.title.toLowerCase()} yet. Use “Add ${cfg.singular}” to create the first one.` : `No ${cfg.title.toLowerCase()} yet.`}
              actions={canWrite ? (r) => (
                <span className="inline-flex gap-1">
                  <Button size="sm" variant="ghost" aria-label={`Edit ${cfg.describe(r)}`} onClick={() => { save.reset(); setEditing(r); }}><Pencil size={15} /></Button>
                  <Button size="sm" variant="ghost" aria-label={`Delete ${cfg.describe(r)}`} onClick={() => { remove.reset(); setDeleting(r); }}><Trash2 size={15} /></Button>
                </span>
              ) : undefined}
            />
            <Pagination page={page} pageSize={pageSize} total={total} onPage={setPage} onPageSize={(s) => { setPageSize(s); setPage(1); }} />
          </>
        )}
      </GlassCard>

      <Modal wide open={editing !== null} onClose={() => setEditing(null)} title={editing === "new" ? `Add ${cfg.singular}` : `Edit ${cfg.singular}`}>
        {editing !== null && (
          <ResourceForm
            key={editing === "new" ? "new" : editing.id}
            fields={cfg.fields} defaults={cfg.defaults ?? {}} row={editing === "new" ? null : (editing as unknown as Record<string, unknown>)}
            pending={save.isPending} error={save.error?.message} onCancel={() => setEditing(null)}
            onSubmit={(body) => save.mutate({ id: editing === "new" ? undefined : editing.id, body })}
          />
        )}
      </Modal>

      <Modal open={deleting !== null} onClose={() => setDeleting(null)} title={`Delete ${cfg.singular}?`}>
        {deleting && (
          <div className="space-y-4">
            <p>This permanently deletes <b>{cfg.describe(deleting)}</b>. {cfg.deleteNote}</p>
            <FormError message={remove.error?.message} />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setDeleting(null)}>Cancel</Button>
              <Button variant="danger" disabled={remove.isPending} onClick={() => remove.mutate(deleting.id)}>{remove.isPending ? "Deleting…" : "Delete"}</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Flag, Plus, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { FleetMap, type MapLine, type MapMarker } from "@/components/maps/FleetMap";
import { Badge, Button, GlassCard, Input, Modal, Select, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { fmtNum, titleCase } from "@/features/resource/format";
import { options as loadOptions, resource } from "@/services/resources";
import { routesApi } from "@/services/tracking";
import { useAuth } from "@/store/auth";
import type { Delivery } from "@/types/fleet";
import type { Assumptions, PlanResult, RouteRec, StopIn } from "@/types/tracking";

const DEFAULTS = { road_factor: "1.3", avg_speed_kph: "40", stop_minutes: "10", fuel_l_per_100km: "12" };
type AKey = keyof typeof DEFAULTS;
const FIELDS: { key: AKey; label: string; hint: string; min: number; max: number }[] = [
  { key: "road_factor", label: "Road factor", hint: "Road length ÷ straight-line length (1 to 3)", min: 1, max: 3 },
  { key: "avg_speed_kph", label: "Average speed (km/h)", hint: "Urban delivery speed", min: 5.1, max: 120 },
  { key: "stop_minutes", label: "Minutes per stop", hint: "Applied to every stop after the first", min: 0, max: 240 },
  { key: "fuel_l_per_100km", label: "Fuel use (L/100 km)", hint: "Light commercial vehicle", min: 0.1, max: 100 },
];
const STATUSES = ["draft", "planned", "in_progress", "completed"];
const deliveries = resource<Delivery>("deliveries");
const hrs = (m: number) => (m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`);

function AssumptionsList({ a }: { a: Assumptions }) {
  return (
    <ul className="grid gap-x-4 gap-y-1 text-xs text-muted sm:grid-cols-2">
      <li>Road factor: ×{a.road_factor}</li><li>Average speed: {a.avg_speed_kph} km/h</li>
      <li>Time per stop: {a.stop_minutes} min</li><li>Fuel use: {a.fuel_l_per_100km} L/100 km</li>
    </ul>
  );
}

export function RoutesPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const canWrite = can("routes:write");

  const [name, setName] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [driverId, setDriverId] = useState("");
  const [stops, setStops] = useState<StopIn[]>([]);
  const [asm, setAsm] = useState<Record<AKey, string>>(DEFAULTS);
  const [useOptimized, setUseOptimized] = useState(true);
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [adding, setAdding] = useState(true);
  const [viewing, setViewing] = useState<RouteRec | null>(null);
  const [deleting, setDeleting] = useState<RouteRec | null>(null);
  const [error, setError] = useState("");

  const vehicles = useQuery({ queryKey: ["options", "vehicles"], queryFn: () => loadOptions("vehicles"), enabled: can("vehicles:read") });
  const drivers = useQuery({ queryKey: ["options", "drivers"], queryFn: () => loadOptions("drivers"), enabled: can("drivers:read") });
  const dels = useQuery({ queryKey: ["deliveries", "for-routes"], queryFn: () => deliveries.list({ page_size: 100 }), enabled: can("deliveries:read") });
  const saved = useQuery({ queryKey: ["routes"], queryFn: () => routesApi.list() });

  const usedDeliveries = new Set(stops.map((s) => s.delivery_id).filter(Boolean));
  const available = (dels.data?.items ?? []).filter((d) => d.dest_lat !== null && d.dest_lng !== null && !["delivered", "cancelled"].includes(d.status) && !usedDeliveries.has(d.id));

  const asmNum = useMemo(() => Object.fromEntries(Object.entries(asm).map(([k, v]) => [k, Number(v)])) as unknown as Assumptions, [asm]);
  const asmErrors = FIELDS.filter((f) => asm[f.key].trim() === "" || !Number.isFinite(asmNum[f.key]) || asmNum[f.key] < f.min || asmNum[f.key] > f.max);

  const edit = (fn: () => void) => { fn(); setPlan(null); setViewing(null); setError(""); };
  const addStop = (s: StopIn) => edit(() => setStops((cur) => (cur.length >= 25 ? cur : [...cur, s])));
  const move = (i: number, d: number) => edit(() => setStops((cur) => { const n = [...cur]; [n[i], n[i + d]] = [n[i + d], n[i]]; return n; }));

  const preview = useMutation({ mutationFn: () => routesApi.plan(stops, asmNum), onSuccess: setPlan, onError: (e: Error) => setError(e.message) });
  const save = useMutation({
    mutationFn: () => routesApi.create({ name: name.trim(), stops, assumptions: asmNum, optimize: useOptimized, vehicle_id: vehicleId || undefined, driver_id: driverId || undefined }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["routes"] }); setStops([]); setPlan(null); setName(""); setError(""); },
    onError: (e: Error) => setError(e.message),
  });
  const setStatus = useMutation({ mutationFn: (v: { id: string; status: string }) => routesApi.setStatus(v.id, v.status), onSuccess: () => void qc.invalidateQueries({ queryKey: ["routes"] }) });
  const remove = useMutation({
    mutationFn: (id: string) => routesApi.remove(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["routes"] }); setDeleting(null); setViewing(null); },
    onError: (e: Error) => setError(e.message),
  });
  const view = useMutation({ mutationFn: (id: string) => routesApi.get(id), onSuccess: (r) => { setViewing(r); setPlan(null); } });

  // What the map shows: a saved route, a plan preview, or the stops being collected.
  const { markers, lines } = useMemo(() => {
    const m: MapMarker[] = []; const l: MapLine[] = [];
    if (viewing) {
      const pts = viewing.stops.filter((s) => s.lat !== null && s.lng !== null);
      pts.forEach((s, i) => m.push({ lat: s.lat!, lng: s.lng!, label: String(i + 1), color: i === 0 ? "#12a36b" : "#4d8dff" }));
      l.push({ points: pts.map((s) => [s.lat!, s.lng!]) });
    } else if (plan) {
      l.push({ points: stops.map((s) => [s.lat, s.lng]), color: "#8e98c9", dashed: true });
      l.push({ points: plan.stops.map((s) => [s.lat, s.lng]) });
      plan.stops.forEach((s, i) => m.push({ lat: s.lat, lng: s.lng, label: String(i + 1), color: i === 0 ? "#12a36b" : "#4d8dff" }));
    } else {
      stops.forEach((s, i) => m.push({ lat: s.lat, lng: s.lng, label: String(i + 1), color: i === 0 ? "#12a36b" : "#4d8dff" }));
    }
    return { markers: m, lines: l };
  }, [stops, plan, viewing]);

  const ready = stops.length >= 2 && asmErrors.length === 0;
  const canSave = ready && canWrite && name.trim().length > 0 && plan !== null && !save.isPending;

  return (
    <div className="space-y-4">
      <div><h1 className="text-gradient text-3xl font-extrabold">Routes</h1><p className="text-muted">Plan and save a single route, or use Fleet planner for capacity- and shift-aware assignments.</p></div>
      <p className="text-sm text-muted">Configure OSRM on the backend to use road-network distances and durations. Without it, results use the displayed straight-line assumptions. Use <Link className="text-electric underline" to="/app/fleet-planner">Fleet planner</Link> for multi-vehicle capacity, stop-window and shift constraints.</p>

      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <div className="space-y-4">
          <GlassCard hover={false} className="space-y-3">
            <h2 className="font-semibold">1. Stops</h2>
            <p className="text-xs text-muted">The first stop is the start and stays first. Click the map to add a stop{dels.data ? ", or add a delivery destination" : ""}.</p>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={adding} onChange={(e) => setAdding(e.target.checked)} />Add a stop where I click on the map</label>
            {available.length > 0 && (
              <Select label="Add a delivery destination" placeholder="Choose a delivery…" value="" options={available.map((d) => ({ value: d.id, label: `${d.reference} → ${d.dest_address}` }))}
                onChange={(e) => { const d = available.find((x) => x.id === e.target.value); if (d) addStop({ address: d.dest_address, lat: d.dest_lat!, lng: d.dest_lng!, delivery_id: d.id }); }} />
            )}
            {dels.data && available.length === 0 && <p className="text-xs text-muted">No open deliveries with destination coordinates. Add latitude and longitude on the Deliveries page to use them here.</p>}
            {stops.length === 0 ? <p className="text-sm text-muted">No stops yet.</p> : (
              <ol className="space-y-2">
                {stops.map((s, i) => (
                  <li key={i} className="flex items-center gap-1">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-electric/25 text-xs">{i === 0 ? <Flag size={12} /> : i + 1}</span>
                    <input aria-label={`Stop ${i + 1} name`} value={s.address} maxLength={255} onChange={(e) => edit(() => setStops((cur) => cur.map((x, j) => (j === i ? { ...x, address: e.target.value } : x))))} className="focus-ring min-w-0 flex-1 rounded-lg border border-line bg-bg/60 px-2 py-1 text-sm" />
                    <button aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)} className="focus-ring rounded p-1 text-muted hover:text-ink disabled:opacity-30"><ArrowUp size={14} /></button>
                    <button aria-label="Move down" disabled={i === stops.length - 1} onClick={() => move(i, 1)} className="focus-ring rounded p-1 text-muted hover:text-ink disabled:opacity-30"><ArrowDown size={14} /></button>
                    <button aria-label={`Remove stop ${i + 1}`} onClick={() => edit(() => setStops((cur) => cur.filter((_, j) => j !== i)))} className="focus-ring rounded p-1 text-muted hover:text-danger"><Trash2 size={14} /></button>
                  </li>
                ))}
              </ol>
            )}
            {stops.length >= 25 && <p className="text-xs text-warn">The limit is 25 stops.</p>}
          </GlassCard>

          <GlassCard hover={false} className="space-y-3">
            <h2 className="font-semibold">2. Assumptions</h2>
            <div className="grid grid-cols-2 gap-2">
              {FIELDS.map((f) => (
                <Input key={f.key} label={f.label} type="number" step="any" value={asm[f.key]} onChange={(e) => edit(() => setAsm((a) => ({ ...a, [f.key]: e.target.value })))}
                  error={asmErrors.includes(f) ? `${f.min} to ${f.max}` : undefined} title={f.hint} />
              ))}
            </div>
            <Button variant="outline" disabled={!ready || preview.isPending} onClick={() => { setError(""); preview.mutate(); }}>{preview.isPending ? "Planning…" : "Preview plan"}</Button>
          </GlassCard>

          {canWrite && (
            <GlassCard hover={false} className="space-y-3">
              <h2 className="font-semibold">3. Save</h2>
              <Input label="Route name" value={name} maxLength={160} onChange={(e) => setName(e.target.value)} />
              <Select label="Vehicle" placeholder="None" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)} options={(vehicles.data ?? []).map((o) => ({ value: o.id, label: o.label }))} />
              <Select label="Driver" placeholder="None" value={driverId} onChange={(e) => setDriverId(e.target.value)} options={(drivers.data ?? []).map((o) => ({ value: o.id, label: o.label }))} />
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={useOptimized} onChange={(e) => setUseOptimized(e.target.checked)} />Save with the optimized stop order</label>
              <Button disabled={!canSave} onClick={() => save.mutate()}><Plus size={16} />{save.isPending ? "Saving…" : "Save route"}</Button>
              {plan === null && ready && <p className="text-xs text-muted">Preview the plan first.</p>}
            </GlassCard>
          )}
          <FormError message={error} />
        </div>

        <div className="space-y-4">
          <GlassCard hover={false} className="p-3">
            <FleetMap className="h-[460px]" fit="markers" markers={markers} lines={lines} onMapClick={adding ? (lat, lng) => addStop({ address: `Stop ${stops.length + 1}`, lat: +lat.toFixed(6), lng: +lng.toFixed(6) }) : undefined} />
            {plan && <p className="mt-2 text-xs text-muted"><span className="mr-1 inline-block h-0.5 w-6 bg-electric align-middle" />Optimized order · <span className="mx-1 inline-block h-0.5 w-6 border-t-2 border-dashed border-muted align-middle" />Your order</p>}
          </GlassCard>

          {plan && (
            <GlassCard hover={false} className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-semibold">Plan preview</h2><Badge tone="warn">Estimate</Badge>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-xs text-muted"><th className="py-1">&nbsp;</th><th>Your order</th><th>Optimized</th><th>Saved</th></tr></thead>
                  <tbody>
                    <tr><td className="py-1 text-muted">Distance</td><td>{fmtNum(plan.original.distance_km, 1)} km</td><td>{fmtNum(plan.optimized.distance_km, 1)} km</td><td className="text-ok">{fmtNum(plan.saved.distance_km, 1)} km ({plan.saved_percent}%)</td></tr>
                    <tr><td className="py-1 text-muted">Time</td><td>{hrs(plan.original.duration_min)}</td><td>{hrs(plan.optimized.duration_min)}</td><td className="text-ok">{hrs(Math.max(0, plan.saved.duration_min))}</td></tr>
                    <tr><td className="py-1 text-muted">Fuel</td><td>{fmtNum(plan.original.fuel_l, 1)} L</td><td>{fmtNum(plan.optimized.fuel_l, 1)} L</td><td className="text-ok">{fmtNum(plan.saved.fuel_l, 1)} L</td></tr>
                  </tbody>
                </table>
              </div>
              {plan.saved_percent === 0 && <p className="text-sm text-muted">Your stop order is already the shortest this method found.</p>}
              <ol className="list-inside list-decimal text-sm">{plan.stops.map((s, i) => <li key={i}>{s.address}</li>)}</ol>
              <div><p className="mb-1 text-xs font-medium">Assumptions used</p><AssumptionsList a={plan.assumptions} /></div>
              <p className="text-xs text-muted">Method: {plan.method}. {plan.assumptions.routing_provider === "OSRM" ? "Road-network estimates do not include live traffic." : "Estimate only; not road-network routing."}</p>
            </GlassCard>
          )}

          {viewing && (
            <GlassCard hover={false} className="space-y-2">
              <div className="flex items-center justify-between"><h2 className="font-semibold">{viewing.name}</h2><Button size="sm" variant="ghost" onClick={() => setViewing(null)}>Close</Button></div>
              <ol className="list-inside list-decimal text-sm">{viewing.stops.map((s) => <li key={s.id}>{s.address}</li>)}</ol>
              {viewing.optimization_notes?.assumptions && <div><p className="mb-1 text-xs font-medium">Assumptions used when this route was planned</p><AssumptionsList a={viewing.optimization_notes.assumptions} /></div>}
            </GlassCard>
          )}
        </div>
      </div>

      <GlassCard hover={false}>
        <h2 className="mb-2 font-semibold">Saved routes</h2>
        {saved.isError ? <div className="space-y-2"><FormError message={saved.error.message} /><Button size="sm" variant="outline" onClick={() => saved.refetch()}>Try again</Button></div>
          : !saved.data ? <Skeleton className="h-16" />
          : saved.data.items.length === 0 ? <p className="text-sm text-muted">No saved routes yet.</p> : (
            <ul className="divide-y divide-line">
              {saved.data.items.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                  <div>
                    <b>{r.name}</b>
                    <span className="block text-xs text-muted">{r.stop_count} stops · {fmtNum(r.total_distance_km, 1)} km · {r.est_duration_min !== null ? hrs(r.est_duration_min) : "–"} (estimates){r.vehicle_label ? ` · ${r.vehicle_label}` : ""}{r.driver_label ? ` · ${r.driver_label}` : ""}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {canWrite ? (
                      <select aria-label={`Status of ${r.name}`} value={r.status} onChange={(e) => setStatus.mutate({ id: r.id, status: e.target.value })} className="focus-ring rounded-lg border border-line bg-bg px-2 py-1 text-sm">
                        {STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
                      </select>
                    ) : <Badge>{titleCase(r.status)}</Badge>}
                    <Button size="sm" variant="outline" onClick={() => view.mutate(r.id)}>Show on map</Button>
                    {canWrite && <Button size="sm" variant="ghost" aria-label={`Delete ${r.name}`} onClick={() => setDeleting(r)}><Trash2 size={16} /></Button>}
                  </div>
                </li>
              ))}
            </ul>
          )}
      </GlassCard>

      <Modal open={deleting !== null} onClose={() => setDeleting(null)} title="Delete route?">
        <p className="text-sm text-muted">“{deleting?.name}” and its stops will be deleted. Deliveries on it are kept and unlinked.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setDeleting(null)}>Cancel</Button>
          <Button variant="danger" disabled={remove.isPending} onClick={() => deleting && remove.mutate(deleting.id)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

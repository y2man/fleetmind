import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, MapPin, Plus, ShieldOff, Trash2 } from "lucide-react";
import { FleetMap } from "@/components/maps/FleetMap";
import { Badge, Button, GlassCard, Input, Modal, Select, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { StatusBadge, fmtDateTime } from "@/features/resource/format";
import { useLiveFleet } from "@/hooks/useLiveFleet";
import { api, del, patch, post } from "@/services/api";
import { options } from "@/services/resources";
import { geofenceApi, trackingApi } from "@/services/tracking";
import { useAuth } from "@/store/auth";
import type { Geofence } from "@/types/tracking";

interface GPSCredential {
  id: string;
  vehicle_id: string;
  label: string;
  created_at: string;
  revoked_at: string | null;
  last_used_at: string | null;
}

interface GPSCredentialCreated extends GPSCredential {
  token: string;
}

const STATE_LABEL = { live: "Live", connecting: "Connecting…", offline: "Reconnecting…" } as const;
const STATE_TONE = { live: "ok", connecting: "warn", offline: "danger" } as const;

export function TrackingPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const live = useLiveFleet(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);
  const [draft, setDraft] = useState<{ lat: number; lng: number } | null>(null);
  const [name, setName] = useState("");
  const [radius, setRadius] = useState("500");
  const [formError, setFormError] = useState("");
  const [deleting, setDeleting] = useState<Geofence | null>(null);
  const [deviceVehicleId, setDeviceVehicleId] = useState("");
  const [deviceLabel, setDeviceLabel] = useState("");
  const [issuedToken, setIssuedToken] = useState("");

  const zones = useQuery({ queryKey: ["geofences"], queryFn: () => geofenceApi.list({ page_size: 100 }) });
  const stored = useQuery({ queryKey: ["geo-events"], queryFn: trackingApi.events });
  const gpsCredentials = useQuery({
    queryKey: ["gps-credentials"],
    queryFn: () => api<GPSCredential[]>("/integrations/gps/credentials"),
    enabled: can("vehicles:read"),
  });
  const vehicleOptions = useQuery({
    queryKey: ["options", "vehicles"],
    queryFn: () => options("vehicles"),
    enabled: can("vehicles:write"),
  });
  const selected = live.vehicles.find((v) => v.vehicle_id === selectedId) ?? null;
  const hasRealGPS = live.vehicles.some((vehicle) => !vehicle.simulated);
  const hasSimulatedGPS = live.vehicles.some((vehicle) => vehicle.simulated);
  const history = useQuery({ queryKey: ["history", selectedId], queryFn: () => trackingApi.history(selectedId!), enabled: !!selectedId, refetchInterval: 10_000 });
  const trail = useMemo(() => (history.data ?? []).map((p) => [p.lat, p.lng] as [number, number]), [history.data]);

  const radiusNum = Number(radius);
  const radiusOk = Number.isFinite(radiusNum) && radiusNum > 0 && radiusNum <= 100_000;
  const reset = () => { setPlacing(false); setDraft(null); setName(""); setRadius("500"); setFormError(""); };

  const create = useMutation({
    mutationFn: () => geofenceApi.create({ name: name.trim(), center_lat: draft!.lat, center_lng: draft!.lng, radius_m: radiusNum }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["geofences"] }); reset(); },
    onError: (e: Error) => setFormError(e.message),
  });
  const remove = useMutation({
    mutationFn: (id: string) => geofenceApi.remove(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["geofences"] }); setDeleting(null); },
  });
  const toggle = useMutation({
    mutationFn: (z: Geofence) => patch(`/geofences/${z.id}`, { is_active: !z.is_active }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["geofences"] }),
  });
  const createCredential = useMutation({
    mutationFn: () => post<GPSCredentialCreated>("/integrations/gps/credentials", {
      vehicle_id: deviceVehicleId,
      label: deviceLabel.trim(),
    }),
    onSuccess: async (created) => {
      setIssuedToken(created.token);
      setDeviceLabel("");
      await qc.invalidateQueries({ queryKey: ["gps-credentials"] });
    },
  });
  const revokeCredential = useMutation({
    mutationFn: (id: string) => del(`/integrations/gps/credentials/${id}`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["gps-credentials"] }),
  });

  // Live events in this session first, then stored history (without duplicates).
  const eventList = useMemo(() => {
    const seen = new Set<string>();
    return [...live.events, ...(stored.data ?? [])].filter((e) => { const k = `${e.at}|${e.registration}|${e.geofence}|${e.event}`; if (seen.has(k)) return false; seen.add(k); return true; }).slice(0, 12);
  }, [live.events, stored.data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-gradient text-3xl font-extrabold">Live map</h1><p className="text-muted">Vehicle positions and geofences.</p></div>
        <div className="flex items-center gap-2">
          {hasRealGPS && <Badge tone="ok">Device GPS</Badge>}
          {hasSimulatedGPS && <Badge tone="warn">Simulated GPS · demo</Badge>}
          {!live.vehicles.length && <Badge tone="info">No positions yet</Badge>}
          <Badge tone={STATE_TONE[live.state]}>{STATE_LABEL[live.state]}</Badge>
        </div>
      </div>
      <p className="text-sm text-muted">
        {hasRealGPS && hasSimulatedGPS
          ? "Device feeds and clearly marked demo positions are shown together."
          : hasRealGPS
            ? "Positions are received from connected GPS devices."
            : live.vehicles.length
              ? "No device feeds are active yet, so these positions are simulated."
              : "Add vehicles and connect GPS devices to see live positions here."}
        {" "}Only active demo vehicles move automatically.
      </p>

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <GlassCard hover={false} className="p-3">
          {placing && <p className="mb-2 rounded-lg bg-electric/15 px-3 py-2 text-sm"><MapPin size={14} className="mr-1 inline" />Click the map to place the center of the zone.</p>}
          <FleetMap className="h-[520px]" vehicles={live.vehicles} geofences={zones.data?.items ?? []} selectedId={selectedId} onSelect={setSelectedId}
            trail={trail} draft={draft ? { ...draft, radius: radiusOk ? radiusNum : 1 } : null}
            onMapClick={placing ? (lat, lng) => setDraft({ lat, lng }) : undefined} />
          {live.state === "live" && live.vehicles.length === 0 && <p className="mt-2 text-sm text-muted">No vehicles yet. Add vehicles on the Fleet page and set one to Active to watch it move.</p>}
        </GlassCard>

        <div className="space-y-4">
          <GlassCard hover={false}>
            <h2 className="mb-2 font-semibold">Vehicles ({live.vehicles.length})</h2>
            {live.state !== "live" && live.vehicles.length === 0 ? <Skeleton className="h-24" /> : (
              <ul className="max-h-48 space-y-1 overflow-y-auto text-sm">
                {live.vehicles.map((v) => (
                  <li key={v.vehicle_id}>
                    <button onClick={() => setSelectedId(v.vehicle_id)} className={`focus-ring flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left hover:bg-surface/70 ${v.vehicle_id === selectedId ? "bg-electric/15" : ""}`}>
                      <span>{v.registration}</span><StatusBadge value={v.status} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </GlassCard>

          <GlassCard hover={false}>
            <h2 className="mb-2 font-semibold">Vehicle details</h2>
            {!selected ? <p className="text-sm text-muted">Select a vehicle on the map or in the list.</p> : (
              <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                <dt className="text-muted">Vehicle</dt><dd>{selected.registration}<span className="block text-xs text-muted">{selected.label}</span></dd>
                <dt className="text-muted">Status</dt><dd><StatusBadge value={selected.status} /></dd>
                <dt className="text-muted">Driver</dt><dd>{selected.driver_label ?? "Unassigned"}</dd>
                <dt className="text-muted">Speed</dt><dd>{selected.speed_kph !== null ? `${Math.round(selected.speed_kph)} km/h` : "–"} <span className="text-xs text-muted">({selected.simulated ? "simulated" : "device"})</span></dd>
                <dt className="text-muted">Heading</dt><dd>{selected.heading !== null ? `${Math.round(selected.heading)}°` : "–"}</dd>
                <dt className="text-muted">Position</dt><dd>{selected.lat.toFixed(5)}, {selected.lng.toFixed(5)}</dd>
                <dt className="text-muted">Trail</dt><dd>{trail.length > 1 ? `${trail.length} recent points` : "Builds up while the vehicle moves"}</dd>
              </dl>
            )}
          </GlassCard>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard hover={false}>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-semibold">Geofences</h2>
            {can("routes:write") && !placing && <Button size="sm" variant="outline" onClick={() => setPlacing(true)}><Plus size={16} />Add zone</Button>}
          </div>
          {placing && (
            <div className="mb-3 space-y-2 rounded-xl border border-line p-3">
              <Input label="Zone name" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
              <Input label="Radius (meters)" type="number" min={1} max={100000} value={radius} onChange={(e) => setRadius(e.target.value)} error={radiusOk ? undefined : "Enter 1 to 100000"} />
              <p className="text-xs text-muted">{draft ? `Center: ${draft.lat.toFixed(5)}, ${draft.lng.toFixed(5)}` : "Center: click the map"}</p>
              {formError && <FormError message={formError} />}
              <div className="flex gap-2">
                <Button size="sm" disabled={!draft || !name.trim() || !radiusOk || create.isPending} onClick={() => { setFormError(""); create.mutate(); }}>Save zone</Button>
                <Button size="sm" variant="ghost" onClick={reset}>Cancel</Button>
              </div>
            </div>
          )}
          {zones.isError ? <FormError message={zones.error.message} /> : !zones.data ? <Skeleton className="h-16" /> : zones.data.items.length === 0 ? <p className="text-sm text-muted">No zones yet. A zone raises an event when a vehicle enters or leaves it.</p> : (
            <ul className="space-y-2 text-sm">
              {zones.data.items.map((z) => (
                <li key={z.id} className="flex items-center justify-between gap-2">
                  <span>{z.name}<span className="block text-xs text-muted">{Math.round(z.radius_m)} m radius · {z.is_active ? "active" : "inactive"}</span></span>
                  {can("routes:write") && (
                    <span className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => toggle.mutate(z)}>{z.is_active ? "Pause" : "Resume"}</Button>
                      <Button size="sm" variant="ghost" aria-label={`Delete ${z.name}`} onClick={() => setDeleting(z)}><Trash2 size={16} /></Button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </GlassCard>

        <GlassCard hover={false}>
          <h2 className="mb-2 font-semibold">Geofence events</h2>
          {eventList.length === 0 ? <p className="text-sm text-muted">No events yet. They appear when a moving vehicle crosses a zone boundary (simulated).</p> : (
            <ul className="space-y-2 text-sm">
              {eventList.map((e, i) => (
                <li key={i}><b>{e.registration ?? "Vehicle"}</b> {e.event === "enter" ? "entered" : "left"} {e.geofence ?? "a zone"} <Badge tone="warn">Demo</Badge>
                  <span className="block text-xs text-muted">{fmtDateTime(e.at)}</span>
                  <Badge tone={e.simulated ? "warn" : "ok"}>{e.simulated ? "Demo" : "Device GPS"}</Badge></li>
              ))}
            </ul>
          )}
        </GlassCard>
      </div>

      {can("vehicles:read") && (
        <GlassCard hover={false} className="space-y-3">
          <div>
            <h2 className="font-semibold">GPS devices</h2>
            <p className="text-xs text-muted">Each device gets a one-time token for the authenticated GPS ingestion API.</p>
          </div>
          {can("vehicles:write") && (
            <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
              <Select label="Vehicle" placeholder="Choose a vehicle…" value={deviceVehicleId}
                options={(vehicleOptions.data ?? []).map((vehicle) => ({ value: vehicle.id, label: vehicle.label }))}
                onChange={(event) => setDeviceVehicleId(event.target.value)} />
              <Input label="Device label" value={deviceLabel} maxLength={120}
                onChange={(event) => setDeviceLabel(event.target.value)} placeholder="e.g. Truck tracker" />
              <Button disabled={!deviceVehicleId || !deviceLabel.trim() || createCredential.isPending}
                onClick={() => createCredential.mutate()}>
                <Plus size={16} />{createCredential.isPending ? "Creating…" : "Create device token"}
              </Button>
            </div>
          )}
          {createCredential.error && <FormError message={createCredential.error.message} />}
          {issuedToken && (
            <div className="space-y-2 rounded-xl border border-warn/30 bg-warn/5 p-3">
              <p className="text-sm font-medium">Copy this token now. It cannot be retrieved again.</p>
              <div className="flex flex-wrap gap-2">
                <input aria-label="New GPS device token" readOnly value={issuedToken}
                  className="focus-ring min-w-48 flex-1 rounded-lg border border-line bg-bg px-3 py-2 font-mono text-xs" />
                <Button variant="outline" onClick={() => void navigator.clipboard.writeText(issuedToken)}>
                  <Copy size={15} />Copy
                </Button>
                <Button variant="ghost" onClick={() => setIssuedToken("")}>Dismiss</Button>
              </div>
              <p className="text-xs text-muted">Send position JSON to <code>/api/v1/integrations/gps/positions</code> using this value in <code>X-GPS-Token</code>.</p>
            </div>
          )}
          {gpsCredentials.isError ? <FormError message={gpsCredentials.error.message} />
            : !gpsCredentials.data ? <Skeleton className="h-14" />
              : gpsCredentials.data.length === 0 ? <p className="text-sm text-muted">No GPS device credentials have been created.</p> : (
                <ul className="divide-y divide-line">
                  {gpsCredentials.data.map((credential) => (
                    <li key={credential.id} className="flex flex-wrap items-center justify-between gap-3 py-2 text-sm">
                      <div>
                        <p className="font-medium">{credential.label}{credential.revoked_at && <> <Badge>Revoked</Badge></>}</p>
                        <p className="text-xs text-muted">
                          {vehicleOptions.data?.find((vehicle) => vehicle.id === credential.vehicle_id)?.label ?? "Vehicle"}
                          {" · Created "}{fmtDateTime(credential.created_at)}
                          {" · Last seen "}{fmtDateTime(credential.last_used_at)}
                        </p>
                      </div>
                      {can("vehicles:write") && !credential.revoked_at && (
                        <Button size="sm" variant="outline" disabled={revokeCredential.isPending}
                          onClick={() => revokeCredential.mutate(credential.id)}>
                          <ShieldOff size={15} />Revoke
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
          {revokeCredential.error && <FormError message={revokeCredential.error.message} />}
        </GlassCard>
      )}

      <Modal open={deleting !== null} onClose={() => setDeleting(null)} title="Delete zone?">
        <p className="text-sm text-muted">“{deleting?.name}” will be removed. Past events stay in the audit log.</p>
        {remove.isError && <FormError message={(remove.error as Error).message} />}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setDeleting(null)}>Cancel</Button>
          <Button variant="danger" disabled={remove.isPending} onClick={() => deleting && remove.mutate(deleting.id)}>Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

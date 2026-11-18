import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus, Route, Trash2 } from "lucide-react";
import { Badge, Button, GlassCard, Input, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { fmtNum } from "@/features/resource/format";
import { resource } from "@/services/resources";
import { post } from "@/services/api";
import { useAuth } from "@/store/auth";
import type { Driver, Page, Vehicle } from "@/types/fleet";

interface StopDraft {
  id: string;
  address: string;
  lat: string;
  lng: string;
  demandKg: string;
  windowStart: string;
  windowEnd: string;
  serviceMinutes: string;
}

interface VehicleShift {
  shiftStart: string;
  shiftEnd: string;
  driverId: string;
}

interface FleetPlanResult {
  routes: {
    vehicle_id: string;
    driver_id: string | null;
    stop_indices: number[];
    arrival_minutes: number[];
    distance_km: number;
    elapsed_minutes: number;
    fuel_l: number;
  }[];
  total_distance_km: number;
  total_elapsed_minutes: number;
  total_fuel_l: number;
  routing_provider: string;
  method: string;
}

const vehiclesApi = resource<Vehicle>("vehicles");
const driversApi = resource<Driver>("drivers");

function minuteOfDay(value: string): number | null {
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(value);
  return match ? Number(match[1]) * 60 + Number(match[2]) : null;
}

function timeOfDay(value: number): string {
  const minutes = value % (24 * 60);
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

const emptyStop = (): StopDraft => ({
  id: crypto.randomUUID(),
  address: "",
  lat: "",
  lng: "",
  demandKg: "",
  windowStart: "",
  windowEnd: "",
  serviceMinutes: "10",
});

export function FleetPlannerPage() {
  const { can } = useAuth();
  const canReadVehicles = can("vehicles:read");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [shifts, setShifts] = useState<Record<string, VehicleShift>>({});
  const [depotLat, setDepotLat] = useState("");
  const [depotLng, setDepotLng] = useState("");
  const [stops, setStops] = useState<StopDraft[]>([]);

  const vehicles = useQuery({
    queryKey: ["fleet-plan", "vehicles"],
    queryFn: () => vehiclesApi.list({ page_size: 100 }),
    enabled: canReadVehicles,
  });
  const drivers = useQuery({
    queryKey: ["fleet-plan", "drivers"],
    queryFn: () => driversApi.list({ page_size: 100 }),
    enabled: can("drivers:read"),
  });

  const eligibleVehicles = (vehicles.data?.items ?? []).filter(
    (vehicle) => vehicle.status !== "retired" && vehicle.capacity_kg !== null,
  );
  const availableDrivers = (drivers.data?.items ?? []).filter((driver) => driver.availability === "available");

  const parsedStops = useMemo(() => stops.map((stop) => ({
    address: stop.address.trim(),
    lat: Number(stop.lat),
    lng: Number(stop.lng),
    demand_kg: Number(stop.demandKg),
    window_start_minute: minuteOfDay(stop.windowStart),
    window_end_minute: minuteOfDay(stop.windowEnd),
    service_minutes: Number(stop.serviceMinutes),
  })), [stops]);

  const validStops = stops.length > 0 && parsedStops.every((stop, index) =>
    stops[index].lat !== "" && stops[index].lng !== "" && stops[index].demandKg !== "" && stops[index].serviceMinutes !== "" &&
    stop.address.length > 0 &&
    Number.isFinite(stop.lat) && stop.lat >= -90 && stop.lat <= 90 &&
    Number.isFinite(stop.lng) && stop.lng >= -180 && stop.lng <= 180 &&
    Number.isInteger(stop.demand_kg) && stop.demand_kg >= 0 &&
    stop.window_start_minute !== null && stop.window_end_minute !== null &&
    stop.window_end_minute > stop.window_start_minute &&
    Number.isInteger(stop.service_minutes) && stop.service_minutes >= 0 && stop.service_minutes <= 240
  );
  const validDepot = Number.isFinite(Number(depotLat)) && depotLat !== "" &&
    Number(depotLat) >= -90 && Number(depotLat) <= 90 &&
    Number.isFinite(Number(depotLng)) && depotLng !== "" &&
    Number(depotLng) >= -180 && Number(depotLng) <= 180;
  const validShifts = selectedIds.length > 0 && selectedIds.every((id) => {
    const shift = shifts[id];
    const start = minuteOfDay(shift?.shiftStart ?? "");
    const end = minuteOfDay(shift?.shiftEnd ?? "");
    return start !== null && end !== null && end > start;
  });

  const plan = useMutation({
    mutationFn: () => post<FleetPlanResult>("/routes/plan-fleet", {
      stops: parsedStops.map((stop) => ({
        address: stop.address,
        lat: stop.lat,
        lng: stop.lng,
        demand_kg: stop.demand_kg,
        window_start_minute: stop.window_start_minute,
        window_end_minute: stop.window_end_minute,
        service_minutes: stop.service_minutes,
      })),
      vehicles: selectedIds.map((vehicleId) => {
        const shift = shifts[vehicleId];
        const driverId = shift.driverId;
        return {
          vehicle_id: vehicleId,
          driver_id: driverId || undefined,
          start_lat: Number(depotLat),
          start_lng: Number(depotLng),
          shift_start_minute: minuteOfDay(shift.shiftStart)!,
          shift_end_minute: minuteOfDay(shift.shiftEnd)!,
        };
      }),
    }),
  });

  const toggleVehicle = (vehicle: Vehicle, checked: boolean) => {
    setSelectedIds((ids) => checked ? [...ids, vehicle.id] : ids.filter((id) => id !== vehicle.id));
    if (checked) {
      const currentDriver = availableDrivers.find((driver) => driver.id === vehicle.driver_id);
      setShifts((current) => ({
        ...current,
        [vehicle.id]: current[vehicle.id] ?? {
          shiftStart: "",
          shiftEnd: "",
          driverId: currentDriver?.id ?? "",
        },
      }));
    }
    plan.reset();
  };

  const updateStop = (id: string, field: keyof Omit<StopDraft, "id">, value: string) => {
    setStops((current) => current.map((stop) => stop.id === id ? { ...stop, [field]: value } : stop));
    plan.reset();
  };

  const canPlan = canReadVehicles && validDepot && validStops && validShifts && selectedIds.every((id) =>
    eligibleVehicles.some((vehicle) => vehicle.id === id)
  );

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-gradient text-3xl font-extrabold">Fleet route planner</h1>
        <p className="text-muted">Assign every stop across vehicles while observing load capacities, stop windows, and driver shifts.</p>
      </div>
      <div className="rounded-xl border border-line bg-surface/40 p-3 text-sm text-muted">
        This is a preview only; it does not save or dispatch routes. Start coordinates are shared across selected vehicles.
        Routing uses OSRM when configured by the backend, otherwise estimates from straight-line distance.
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <GlassCard hover={false} className="space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-semibold">Vehicles and shifts</h2>
            <Badge>{selectedIds.length} selected</Badge>
          </div>
          {vehicles.isError ? <FormError message={vehicles.error.message} />
            : !vehicles.data ? <Skeleton className="h-20" />
              : eligibleVehicles.length === 0 ? (
                <p className="text-sm text-muted">Add a vehicle capacity on the Fleet page before planning.</p>
              ) : (
                <ul className="space-y-3">
                  {eligibleVehicles.map((vehicle) => {
                    const selected = selectedIds.includes(vehicle.id);
                    const shift = shifts[vehicle.id] ?? { shiftStart: "", shiftEnd: "", driverId: "" };
                    return (
                      <li key={vehicle.id} className="rounded-xl border border-line p-3">
                        <label className="flex items-center gap-2 text-sm font-medium">
                          <input type="checkbox" checked={selected}
                            disabled={!selected && selectedIds.length >= 10}
                            onChange={(event) => toggleVehicle(vehicle, event.target.checked)} />
                          {vehicle.registration} · {vehicle.capacity_kg?.toLocaleString()} kg
                        </label>
                        {selected && (
                          <div className="mt-3 grid gap-3 sm:grid-cols-3">
                            <Input id={`fleet-shift-start-${vehicle.id}`} label="Shift starts" type="time" value={shift.shiftStart}
                              onChange={(event) => {
                                setShifts((current) => ({ ...current, [vehicle.id]: { ...shift, shiftStart: event.target.value } }));
                                plan.reset();
                              }} />
                            <Input id={`fleet-shift-end-${vehicle.id}`} label="Shift ends" type="time" value={shift.shiftEnd}
                              onChange={(event) => {
                                setShifts((current) => ({ ...current, [vehicle.id]: { ...shift, shiftEnd: event.target.value } }));
                                plan.reset();
                              }} />
                            <label className="space-y-1 text-sm text-muted">
                              <span>Available driver (optional)</span>
                              <select aria-label={`Driver for ${vehicle.registration}`} value={shift.driverId}
                                onChange={(event) => {
                                  setShifts((current) => ({ ...current, [vehicle.id]: { ...shift, driverId: event.target.value } }));
                                  plan.reset();
                                }}
                                className="focus-ring w-full rounded-xl border border-line bg-bg/60 px-3 py-2 text-ink">
                                <option value="">No driver</option>
                                {availableDrivers.map((driver) => <option key={driver.id} value={driver.id}>{driver.full_name}</option>)}
                              </select>
                            </label>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
          {drivers.isError && <FormError message={drivers.error.message} />}
          <div className="grid gap-3 sm:grid-cols-2">
            <Input id="fleet-depot-lat" label="Shared depot latitude" type="number" min={-90} max={90} step="any" value={depotLat}
              onChange={(event) => { setDepotLat(event.target.value); plan.reset(); }} />
            <Input id="fleet-depot-lng" label="Shared depot longitude" type="number" min={-180} max={180} step="any" value={depotLng}
              onChange={(event) => { setDepotLng(event.target.value); plan.reset(); }} />
          </div>
        </GlassCard>

        <GlassCard hover={false} className="space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-semibold">Stops and constraints</h2>
            <Button size="sm" variant="outline" disabled={stops.length >= 50}
              onClick={() => { setStops((current) => [...current, emptyStop()]); plan.reset(); }}>
              <Plus size={15} />Add stop
            </Button>
          </div>
          <p className="text-xs text-muted">Stop windows and shifts use local time-of-day on the same service day. Choose one to ten vehicles and up to 50 stops.</p>
          {stops.length === 0 && <p className="text-sm text-muted">Add a delivery stop to begin.</p>}
          <ul className="space-y-3">
            {stops.map((stop, index) => (
              <li key={stop.id} className="space-y-3 rounded-xl border border-line p-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Stop {index + 1}</h3>
                  <Button size="sm" variant="ghost" aria-label={`Remove stop ${index + 1}`}
                    onClick={() => { setStops((current) => current.filter((item) => item.id !== stop.id)); plan.reset(); }}>
                    <Trash2 size={15} />
                  </Button>
                </div>
                <Input id={`fleet-stop-${stop.id}-address`} label="Address / stop name" value={stop.address} maxLength={255}
                  onChange={(event) => updateStop(stop.id, "address", event.target.value)} />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Input id={`fleet-stop-${stop.id}-lat`} label="Latitude" type="number" min={-90} max={90} step="any" value={stop.lat}
                    onChange={(event) => updateStop(stop.id, "lat", event.target.value)} />
                  <Input id={`fleet-stop-${stop.id}-lng`} label="Longitude" type="number" min={-180} max={180} step="any" value={stop.lng}
                    onChange={(event) => updateStop(stop.id, "lng", event.target.value)} />
                  <Input id={`fleet-stop-${stop.id}-demand`} label="Demand (kg)" type="number" min={0} max={1000000} step={1} value={stop.demandKg}
                    onChange={(event) => updateStop(stop.id, "demandKg", event.target.value)} />
                  <Input id={`fleet-stop-${stop.id}-service`} label="Service time (minutes)" type="number" min={0} max={240} step={1} value={stop.serviceMinutes}
                    onChange={(event) => updateStop(stop.id, "serviceMinutes", event.target.value)} />
                  <Input id={`fleet-stop-${stop.id}-window-start`} label="Window opens" type="time" value={stop.windowStart}
                    onChange={(event) => updateStop(stop.id, "windowStart", event.target.value)} />
                  <Input id={`fleet-stop-${stop.id}-window-end`} label="Window closes" type="time" value={stop.windowEnd}
                    onChange={(event) => updateStop(stop.id, "windowEnd", event.target.value)} />
                </div>
              </li>
            ))}
          </ul>
          <Button disabled={!canPlan || plan.isPending} onClick={() => plan.mutate()}>
            <Route size={16} />{plan.isPending ? "Solving…" : "Preview fleet plan"}
          </Button>
          {!canPlan && <p className="text-xs text-muted">Select a capacity-configured vehicle, enter valid shift and depot coordinates, and add at least one complete stop.</p>}
          {plan.error && <FormError message={plan.error.message} />}
        </GlassCard>
      </div>

      {plan.data && (
        <GlassCard hover={false} className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-semibold">Fleet plan preview</h2>
              <p className="text-xs text-muted">{plan.data.method}</p>
            </div>
            <Badge tone={plan.data.routing_provider === "OSRM" ? "ok" : "warn"}>
              {plan.data.routing_provider === "OSRM" ? "Road network" : "Estimated"}
            </Badge>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <p className="rounded-xl bg-surface/50 p-3 text-sm">Distance <b className="block">{fmtNum(plan.data.total_distance_km, 1)} km</b></p>
            <p className="rounded-xl bg-surface/50 p-3 text-sm">Elapsed time <b className="block">{fmtNum(plan.data.total_elapsed_minutes)} min</b></p>
            <p className="rounded-xl bg-surface/50 p-3 text-sm">Fuel estimate <b className="block">{fmtNum(plan.data.total_fuel_l, 1)} L</b></p>
          </div>
          <ul className="grid gap-3 lg:grid-cols-2">
            {plan.data.routes.map((route) => {
              const vehicle = eligibleVehicles.find((item) => item.id === route.vehicle_id);
              const driver = availableDrivers.find((item) => item.id === route.driver_id);
              return (
                <li key={route.vehicle_id} className="rounded-xl border border-line p-3">
                  <h3 className="font-semibold">{vehicle?.registration ?? "Vehicle"}{driver ? ` · ${driver.full_name}` : ""}</h3>
                  <p className="text-xs text-muted">{fmtNum(route.distance_km, 1)} km · {route.elapsed_minutes} min · {fmtNum(route.fuel_l, 1)} L</p>
                  {route.stop_indices.length === 0 ? <p className="mt-2 text-sm text-muted">No stops assigned.</p> : (
                    <ol className="mt-2 list-inside list-decimal text-sm">
                      {route.stop_indices.map((stopIndex, position) => (
                        <li key={stopIndex}>
                          {stops[stopIndex]?.address || `Stop ${stopIndex + 1}`}
                          <span className="ml-2 text-xs text-muted">arrival {timeOfDay(route.arrival_minutes[position])}</span>
                        </li>
                      ))}
                    </ol>
                  )}
                </li>
              );
            })}
          </ul>
        </GlassCard>
      )}
    </div>
  );
}

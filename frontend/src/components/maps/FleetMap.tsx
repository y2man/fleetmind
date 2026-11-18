import { useEffect, useRef } from "react";
import L from "leaflet";
import { Circle, CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { cn } from "@/utils/cn";
import type { Geofence, LivePosition } from "@/types/tracking";

export interface MapMarker { lat: number; lng: number; label: string; color?: string }
export interface MapLine { points: [number, number][]; color?: string; dashed?: boolean }
export interface DraftZone { lat: number; lng: number; radius: number }

const COLORS: Record<string, string> = { active: "#2fe0a0", idle: "#4d8dff", maintenance: "#ffc04d", retired: "#8e98c9" };
const DEFAULT_CENTER: [number, number] = [9.03, 38.74];

interface Props {
  vehicles?: LivePosition[];
  geofences?: Geofence[];
  draft?: DraftZone | null;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  markers?: MapMarker[];
  lines?: MapLine[];
  trail?: [number, number][];
  onMapClick?: (lat: number, lng: number) => void;
  fit?: "vehicles" | "markers" | "none";
  className?: string;
}

/** Re-fits the view when the number of things to show changes (not on every position update). */
function Fit({ points, mode }: { points: [number, number][]; mode: string }) {
  const map = useMap();
  const key = `${mode}:${points.length}`;
  const last = useRef("");
  useEffect(() => {
    if (mode === "none" || points.length === 0 || last.current === key) return;
    last.current = key;
    map.fitBounds(L.latLngBounds(points).pad(0.25), { maxZoom: 15, animate: false });
  }, [key, map, points, mode]);
  return null;
}

function Clicks({ onMapClick }: { onMapClick?: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onMapClick?.(e.latlng.lat, e.latlng.lng) });
  return null;
}

export function FleetMap({ vehicles = [], geofences = [], draft, selectedId, onSelect, markers = [], lines = [], trail, onMapClick, fit = "vehicles", className }: Props) {
  const fitPoints: [number, number][] = fit === "vehicles" ? vehicles.map((v) => [v.lat, v.lng]) : fit === "markers" ? markers.map((m) => [m.lat, m.lng]) : [];
  return (
    <div className={cn("isolate overflow-hidden rounded-xl border border-line", onMapClick && "cursor-crosshair", className)}>
      <MapContainer center={DEFAULT_CENTER} zoom={12} scrollWheelZoom className="h-full w-full" attributionControl>
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} />
        <Fit points={fitPoints} mode={fit} />
        <Clicks onMapClick={onMapClick} />
        {geofences.map((g) => (
          <Circle key={g.id} center={[g.center_lat, g.center_lng]} radius={g.radius_m} pathOptions={{ color: "#9b6bff", weight: 2, dashArray: g.is_active ? "6" : "2 8", fillOpacity: g.is_active ? 0.12 : 0.04 }}>
            <Tooltip sticky>{g.name}{g.is_active ? "" : " (inactive)"}</Tooltip>
          </Circle>
        ))}
        {draft && <Circle center={[draft.lat, draft.lng]} radius={draft.radius} pathOptions={{ color: "#4d8dff", weight: 2, dashArray: "4", fillOpacity: 0.15 }} />}
        {lines.map((l, i) => <Polyline key={i} positions={l.points} pathOptions={{ color: l.color ?? "#4d8dff", weight: 4, opacity: l.dashed ? 0.6 : 0.9, dashArray: l.dashed ? "8 8" : undefined }} />)}
        {trail && trail.length > 1 && <Polyline positions={trail} pathOptions={{ color: "#ffc04d", weight: 3, opacity: 0.8 }} />}
        {markers.map((m, i) => (
          <CircleMarker key={`${i}-${m.lat}-${m.lng}`} center={[m.lat, m.lng]} radius={11} pathOptions={{ color: "#fff", weight: 2, fillColor: m.color ?? "#4d8dff", fillOpacity: 1 }}>
            <Tooltip permanent direction="center" className="map-label">{m.label}</Tooltip>
          </CircleMarker>
        ))}
        {vehicles.map((v) => {
          const sel = v.vehicle_id === selectedId;
          return (
            <CircleMarker key={v.vehicle_id} center={[v.lat, v.lng]} radius={sel ? 10 : 7}
              pathOptions={{ color: sel ? "#fff" : "#0b1020", weight: sel ? 3 : 1.5, fillColor: COLORS[v.status] ?? "#4d8dff", fillOpacity: 1 }}
              eventHandlers={{ click: () => onSelect?.(v.vehicle_id) }}>
              <Tooltip>{v.registration} · {v.status}{v.speed_kph ? ` · ${Math.round(v.speed_kph)} km/h` : ""}</Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}

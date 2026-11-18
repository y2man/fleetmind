import { useEffect, useState } from "react";
import { API_URL } from "@/config/env";
import { getAccessToken, refreshAccessToken } from "@/services/api";
import type { GeoEvent, LivePosition } from "@/types/tracking";

export type LiveState = "connecting" | "live" | "offline";
// With an empty API_URL (production build served behind the same host) the socket uses the page's own host.
const WS_URL = API_URL
  ? `${API_URL.replace(/^http/, "ws")}/api/v1/ws/tracking`
  : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/api/v1/ws/tracking`;

/**
 * Live vehicle positions over a WebSocket. The server sends SIMULATED GPS (always flagged `simulated`).
 * The access token is sent as the first message, not in the URL. Reconnects with backoff and a fresh token.
 */
export function useLiveFleet(enabled = true) {
  const [vehicles, setVehicles] = useState<LivePosition[]>([]);
  const [events, setEvents] = useState<GeoEvent[]>([]);
  const [state, setState] = useState<LiveState>("connecting");

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let closed = false;
    let retry = 0;
    let timer: number | undefined;

    const schedule = () => {
      if (closed) return;
      setState("offline");
      timer = window.setTimeout(() => void connect(), Math.min(15_000, 1000 * 2 ** retry++));
    };

    const connect = async () => {
      setState("connecting");
      const token = getAccessToken() ?? (await refreshAccessToken());
      if (closed) return;
      if (!token) return schedule();
      const sock = (ws = new WebSocket(WS_URL));
      sock.onopen = () => sock.send(JSON.stringify({ type: "auth", token }));
      sock.onmessage = (e) => {
        try {
          const m = JSON.parse(e.data as string);
          if (m.type === "snapshot" || m.type === "positions") { setVehicles(m.vehicles); setState("live"); retry = 0; }
          else if (m.type === "geofence") setEvents((prev) => [m as GeoEvent, ...prev].slice(0, 30));
        } catch { /* ignore a malformed message */ }
      };
      sock.onclose = (e) => {
        if (closed) return;
        if (e.code === 4401) void refreshAccessToken().then(schedule); // expired token: get a new one first
        else schedule();
      };
    };

    void connect();
    return () => { closed = true; window.clearTimeout(timer); ws?.close(); };
  }, [enabled]);

  return { vehicles, events, state };
}

"""Per-organization WebSocket hub that drives the simulated GPS feed.

One background task per organization runs while at least one browser is connected,
and stops when the last one leaves. State lives in this process: running several
backend instances needs Redis pub/sub in between (planned for the deployment phase).
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import WebSocket

from app.core.config import get_settings
from app.services.live import OrgState, run_tick

log = logging.getLogger("fleetmind.live")


class OrgHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.state = OrgState()
        self.lock = asyncio.Lock()  # one simulation step at a time
        self.task: asyncio.Task | None = None


class Hub:
    def __init__(self) -> None:
        self.hubs: dict[uuid.UUID, OrgHub] = {}

    @staticmethod
    def _step(factory, org_id, state, advance: bool):
        s = get_settings()
        with factory() as db:
            return run_tick(db, org_id, state, advance=advance, dt=s.sim_tick_seconds, boost=s.sim_speed_boost)

    async def connect(self, ws: WebSocket, org_id: uuid.UUID, factory) -> None:
        hub = self.hubs.setdefault(org_id, OrgHub())
        hub.clients.add(ws)
        async with hub.lock:
            positions, _ = await asyncio.to_thread(self._step, factory, org_id, hub.state, False)
        await ws.send_json({"type": "snapshot", "simulated": True, "vehicles": positions})
        if hub.task is None or hub.task.done():
            hub.task = asyncio.create_task(self._loop(org_id, hub, factory))

    def disconnect(self, ws: WebSocket, org_id: uuid.UUID) -> None:
        hub = self.hubs.get(org_id)
        if not hub:
            return
        hub.clients.discard(ws)
        if not hub.clients:
            if hub.task:
                hub.task.cancel()
            self.hubs.pop(org_id, None)

    async def _broadcast(self, hub: OrgHub, message: dict) -> None:
        for ws in list(hub.clients):
            try:
                await ws.send_json(message)
            except Exception:  # a dead socket is removed when its receive loop ends
                hub.clients.discard(ws)

    async def _loop(self, org_id: uuid.UUID, hub: OrgHub, factory) -> None:
        interval = get_settings().sim_tick_seconds
        while hub.clients:
            await asyncio.sleep(interval)
            try:
                async with hub.lock:
                    positions, events = await asyncio.to_thread(self._step, factory, org_id, hub.state, True)
                await self._broadcast(hub, {"type": "positions", "simulated": True, "vehicles": positions})
                for e in events:
                    await self._broadcast(hub, {"type": "geofence", **e})
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("simulation tick failed for organization %s", org_id)


hub = Hub()

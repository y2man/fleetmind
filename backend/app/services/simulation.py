"""Simulated GPS. Every position produced here is labeled as simulated (demo).

Pure functions so they can be tested without a database. A real GPS feed would
replace `step` and write VehicleLocation rows with is_simulated=False.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from app.services.routing import Point, haversine_km

DEFAULT_CENTER: Point = (9.0300, 38.7400)  # Addis Ababa, used when an organization has no positions yet
BOX_DEG = 0.12  # vehicles stay inside this box around the center


@dataclass
class Mover:
    lat: float
    lng: float
    heading: float  # degrees clockwise from north
    speed_kph: float


def new_mover(rng: random.Random, center: Point = DEFAULT_CENTER, at: Point | None = None) -> Mover:
    lat, lng = at if at else (center[0] + rng.uniform(-BOX_DEG, BOX_DEG) * 0.7, center[1] + rng.uniform(-BOX_DEG, BOX_DEG) * 0.7)
    return Mover(lat, lng, rng.uniform(0, 360), rng.uniform(25, 55))


def step(m: Mover, dt_s: float, rng: random.Random, center: Point = DEFAULT_CENTER, boost: float = 1.0) -> Mover:
    """Advance one mover by dt_s seconds. `boost` speeds up the demo (default 1x, real time)."""
    m.heading = (m.heading + rng.uniform(-25, 25)) % 360
    m.speed_kph = min(70.0, max(10.0, m.speed_kph + rng.uniform(-5, 5)))
    dist_km = m.speed_kph * boost * dt_s / 3600
    br = math.radians(m.heading)
    dlat = dist_km * math.cos(br) / 111.32
    dlng = dist_km * math.sin(br) / (111.32 * max(0.2, math.cos(math.radians(m.lat))))
    m.lat += dlat
    m.lng += dlng
    if abs(m.lat - center[0]) > BOX_DEG or abs(m.lng - center[1]) > BOX_DEG:  # turn back toward the center
        m.heading = (math.degrees(math.atan2(center[1] - m.lng, center[0] - m.lat)) + 360) % 360
        m.lat = min(max(m.lat, center[0] - BOX_DEG), center[0] + BOX_DEG)
        m.lng = min(max(m.lng, center[1] - BOX_DEG), center[1] + BOX_DEG)
    return m


def inside(lat: float, lng: float, center_lat: float, center_lng: float, radius_m: float) -> bool:
    return haversine_km((lat, lng), (center_lat, center_lng)) * 1000 <= radius_m

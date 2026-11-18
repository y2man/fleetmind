"""Route planning maths: distance, ordering and the estimates shown with every plan.

Pure functions (no database, no network) so they are easy to test. Distances are
straight-line (haversine) distances multiplied by a road factor, because no road
network or routing engine is connected. They are estimates, and the assumptions
used are returned with every plan so the interface can show them.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import httpx

EARTH_RADIUS_KM = 6371.0088
Point = tuple[float, float]  # (lat, lng)


class RoutingProviderError(Exception):
    pass


@dataclass(frozen=True)
class Assumptions:
    road_factor: float = 1.3  # real roads are longer than straight lines
    avg_speed_kph: float = 40.0  # average urban delivery speed
    stop_minutes: float = 10.0  # time spent at each stop after the first
    fuel_l_per_100km: float = 12.0  # light commercial vehicle

    def as_dict(self) -> dict:
        return asdict(self)


def haversine_km(a: Point, b: Point) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def path_km(points: list[Point], order: list[int]) -> float:
    """Straight-line length of visiting points in `order` (open path, no return)."""
    return sum(haversine_km(points[order[i]], points[order[i + 1]]) for i in range(len(order) - 1))


def osrm_matrices(
    points: list[Point],
    base_url: str,
    profile: str,
    timeout_seconds: float = 8.0,
) -> tuple[list[list[float]], list[list[float]]]:
    coordinates = ";".join(f"{lng},{lat}" for lat, lng in points)
    url = f"{base_url.rstrip('/')}/table/v1/{profile}/{coordinates}"
    try:
        response = httpx.get(url, params={"annotations": "distance,duration"}, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RoutingProviderError("OSRM route matrix request failed") from exc

    if not isinstance(payload, dict) or payload.get("code") != "Ok":
        raise RoutingProviderError("OSRM did not return a usable route matrix")
    size = len(points)

    def matrix_values(matrix: object) -> list[list[float]]:
        if not isinstance(matrix, list) or len(matrix) != size:
            raise RoutingProviderError("OSRM returned a malformed route matrix")
        result: list[list[float]] = []
        for row in matrix:
            if not isinstance(row, list) or len(row) != size:
                raise RoutingProviderError("OSRM returned a malformed route matrix")
            if any(not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in row):
                raise RoutingProviderError("OSRM route matrix contains unreachable or invalid stops")
            result.append([float(value) for value in row])
        return result

    return matrix_values(payload.get("distances")), matrix_values(payload.get("durations"))


def optimize_order(points: list[Point]) -> list[int]:
    """Nearest-neighbour ordering improved with 2-opt. Point 0 is the fixed start."""
    n = len(points)
    if n <= 2:
        return list(range(n))
    left = set(range(1, n))
    order = [0]
    while left:
        last = points[order[-1]]
        nxt = min(left, key=lambda i: (haversine_km(last, points[i]), i))
        order.append(nxt)
        left.remove(nxt)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                cand = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                if path_km(points, cand) < path_km(points, order) - 1e-9:
                    order, improved = cand, True
    return order


def estimate(points: list[Point], order: list[int], a: Assumptions) -> dict:
    km = path_km(points, order) * a.road_factor
    minutes = km / a.avg_speed_kph * 60 + a.stop_minutes * max(0, len(order) - 1)
    return {"distance_km": round(km, 2), "duration_min": int(round(minutes)), "fuel_l": round(km * a.fuel_l_per_100km / 100, 2)}


def plan(points: list[Point], a: Assumptions | None = None) -> dict:
    """Compare the order given by the user with the optimized order."""
    a = a or Assumptions()
    original = list(range(len(points)))
    best = optimize_order(points)
    base, opt = estimate(points, original, a), estimate(points, best, a)
    if opt["distance_km"] > base["distance_km"]:  # never present a worse plan as an optimization
        best, opt = original, base
    saved = {k: round(base[k] - opt[k], 2) if k != "duration_min" else base[k] - opt[k] for k in base}
    pct = round(saved["distance_km"] / base["distance_km"] * 100, 1) if base["distance_km"] > 0 else 0.0
    return {"order": best, "original": base, "optimized": opt, "saved": saved, "saved_percent": pct, "assumptions": a.as_dict()}


def plan_osrm(
    points: list[Point],
    a: Assumptions,
    base_url: str,
    profile: str,
    timeout_seconds: float = 8.0,
) -> dict:
    """Plan a route using OSRM's road-network distance and duration matrix."""
    distance_matrix, duration_matrix = osrm_matrices(points, base_url, profile, timeout_seconds)
    size = len(points)

    def path_cost(matrix: list[list[float]], order: list[int]) -> float:
        return sum(matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))

    order = [0]
    remaining = set(range(1, size))
    while remaining:
        next_stop = min(remaining, key=lambda index: (distance_matrix[order[-1]][index], index))
        order.append(next_stop)
        remaining.remove(next_stop)
    improved = True
    while improved:
        improved = False
        for i in range(1, size - 1):
            for j in range(i + 1, size):
                candidate = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                if path_cost(distance_matrix, candidate) < path_cost(distance_matrix, order) - 1e-6:
                    order, improved = candidate, True

    def estimate_matrix(distance: list[list[float]], duration: list[list[float]], route: list[int]) -> dict:
        km = path_cost(distance, route) / 1000
        minutes = path_cost(duration, route) / 60 + a.stop_minutes * max(0, len(route) - 1)
        return {
            "distance_km": round(km, 2),
            "duration_min": int(round(minutes)),
            "fuel_l": round(km * a.fuel_l_per_100km / 100, 2),
        }

    original = list(range(size))
    baseline = estimate_matrix(distance_matrix, duration_matrix, original)
    optimized = estimate_matrix(distance_matrix, duration_matrix, order)
    if optimized["distance_km"] > baseline["distance_km"]:
        order, optimized = original, baseline
    saved = {
        key: round(baseline[key] - optimized[key], 2) if key != "duration_min"
        else baseline[key] - optimized[key]
        for key in baseline
    }
    pct = round(saved["distance_km"] / baseline["distance_km"] * 100, 1) if baseline["distance_km"] > 0 else 0.0
    assumptions = a.as_dict() | {"routing_provider": "OSRM", "profile": profile}
    return {
        "order": order,
        "original": baseline,
        "optimized": optimized,
        "saved": saved,
        "saved_percent": pct,
        "assumptions": assumptions,
        "method": "nearest-neighbour + 2-opt on OSRM road-network distances",
    }


def plan_fleet_ortools(
    stops: list[dict],
    vehicles: list[dict],
    capacities_kg: list[int],
    assumptions: Assumptions,
    distance_matrix_m: list[list[float]] | None = None,
    duration_matrix_seconds: list[list[float]] | None = None,
    time_limit_seconds: int = 5,
) -> dict:
    """Solve a capacitated, time-windowed vehicle routing problem with OR-Tools."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    vehicle_count = len(vehicles)
    stop_count = len(stops)
    points: list[Point] = [(vehicle["start_lat"], vehicle["start_lng"]) for vehicle in vehicles]
    points.extend((stop["lat"], stop["lng"]) for stop in stops)
    node_count = len(points)

    if distance_matrix_m is None or duration_matrix_seconds is None:
        distance_matrix_m = [
            [haversine_km(a, b) * assumptions.road_factor * 1000 for b in points]
            for a in points
        ]
        duration_matrix_seconds = [
            [distance_matrix_m[i][j] / 1000 / assumptions.avg_speed_kph * 3600 for j in range(node_count)]
            for i in range(node_count)
        ]
    if (
        len(distance_matrix_m) != node_count
        or len(duration_matrix_seconds) != node_count
        or any(len(row) != node_count for row in distance_matrix_m)
        or any(len(row) != node_count for row in duration_matrix_seconds)
    ):
        raise RoutingProviderError("Routing provider returned an invalid fleet matrix")

    manager = pywrapcp.RoutingIndexManager(
        node_count,
        vehicle_count,
        list(range(vehicle_count)),
        list(range(vehicle_count)),
    )
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        source, target = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        return int(round(distance_matrix_m[source][target]))

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

    def demand_callback(index: int) -> int:
        node = manager.IndexToNode(index)
        return 0 if node < vehicle_count else int(stops[node - vehicle_count]["demand_kg"])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        capacities_kg,
        True,
        "Capacity",
    )

    def time_callback(from_index: int, to_index: int) -> int:
        source, target = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        drive_minutes = int(round(duration_matrix_seconds[source][target] / 60))
        service_minutes = (
            0 if source < vehicle_count else int(stops[source - vehicle_count]["service_minutes"])
        )
        return drive_minutes + service_minutes

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_callback_index, 1440, 2880, False, "Time")
    time_dimension = routing.GetDimensionOrDie("Time")

    for vehicle_index, vehicle in enumerate(vehicles):
        time_dimension.CumulVar(routing.Start(vehicle_index)).SetRange(
            vehicle["shift_start_minute"], vehicle["shift_end_minute"]
        )
        time_dimension.CumulVar(routing.End(vehicle_index)).SetRange(
            vehicle["shift_start_minute"], vehicle["shift_end_minute"]
        )

    for stop_index, stop in enumerate(stops):
        index = manager.NodeToIndex(vehicle_count + stop_index)
        time_dimension.CumulVar(index).SetRange(
            stop["window_start_minute"], stop["window_end_minute"]
        )

    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search.time_limit.seconds = time_limit_seconds
    assignment = routing.SolveWithParameters(search)
    if assignment is None:
        raise ValueError("No feasible fleet plan found for the supplied capacities, time windows, and shifts")

    routes = []
    for vehicle_index, vehicle in enumerate(vehicles):
        index = routing.Start(vehicle_index)
        ordered_indices: list[int] = []
        arrivals: list[int] = []
        route_distance_m = 0
        while not routing.IsEnd(index):
            previous = index
            index = assignment.Value(routing.NextVar(index))
            route_distance_m += routing.GetArcCostForVehicle(previous, index, vehicle_index)
            node = manager.IndexToNode(index)
            if node >= vehicle_count:
                ordered_indices.append(node - vehicle_count)
                arrivals.append(assignment.Value(time_dimension.CumulVar(index)))
        start_time = assignment.Value(time_dimension.CumulVar(routing.Start(vehicle_index)))
        end_time = assignment.Value(time_dimension.CumulVar(routing.End(vehicle_index)))
        distance_km = route_distance_m / 1000
        routes.append({
            "vehicle_id": vehicle["vehicle_id"],
            "driver_id": vehicle.get("driver_id"),
            "stop_indices": ordered_indices,
            "arrival_minutes": arrivals,
            "distance_km": round(distance_km, 2),
            "elapsed_minutes": end_time - start_time,
            "fuel_l": round(distance_km * assumptions.fuel_l_per_100km / 100, 2),
        })

    return {
        "routes": routes,
        "total_distance_km": round(sum(route["distance_km"] for route in routes), 2),
        "total_elapsed_minutes": sum(route["elapsed_minutes"] for route in routes),
        "total_fuel_l": round(sum(route["fuel_l"] for route in routes), 2),
    }

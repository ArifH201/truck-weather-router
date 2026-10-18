"""Third-party API clients (no API keys needed).

  * Geocoding: Nominatim (OpenStreetMap). Usage policy: identify yourself via
    User-Agent and keep to ~1 request/second.
  * Routing:   OSRM public demo server, up to 3 alternatives. It is a demo
    server, so for production use a hosted OSRM/ORS/Mapbox instance.
  * Weather:   Open-Meteo hourly forecast, up to 16 days ahead.
"""
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import requests

from .analysis import RawRoute
from .geo import METERS_PER_MILE
from .weather import extract_weather, hourly_window

USER_AGENT = "truck-weather-router/0.1 (assessment project)"
TIMEOUT = int(os.environ.get("WEATHER_TIMEOUT", "25"))
# OSRM uses car speeds; heavy trucks are slower. Stated assumption, tweak freely.
TRUCK_TIME_FACTOR = 1.15
WEATHER_CHUNK = 50          # locations per Open-Meteo request
WEATHER_WORKERS = 4         # parallel Open-Meteo requests
CACHE_TTL = 30 * 60
_cache: dict = {}           # (lat2dp, lon2dp) -> (fetched_at, hourly)
_last_geocode = 0.0         # Nominatim policy: at most 1 request/second


def _is_distinct_route(new_dist: float, routes: list, threshold: float = 0.03) -> bool:
    for r in routes:
        diff = abs(new_dist - r.distance_miles * METERS_PER_MILE) / max(r.distance_miles * METERS_PER_MILE, 1.0)
        if diff < threshold:
            return False
    return True


@lru_cache(maxsize=256)
def geocode(query: str):
    global _last_geocode
    time.sleep(max(0.0, 1.0 - (time.time() - _last_geocode)))
    _last_geocode = time.time()
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": query, "format": "json", "limit": 1},
                     headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    hits = r.json()
    if not hits:
        raise LookupError(f"Could not find location: {query}")
    return float(hits[0]["lat"]), float(hits[0]["lon"])


def fetch_routes(origin, dest) -> list:
    coords = f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
    r = requests.get(f"https://router.project-osrm.org/route/v1/driving/{coords}",
                     params={"alternatives": 3, "overview": "full",
                             "geometries": "geojson"},
                     headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise LookupError(f"No route found: {data.get('code')}")

    routes = []
    seen = set()
    for rt in data.get("routes", []):
        coords_list = [(lat, lon) for lon, lat in rt["geometry"]["coordinates"]]
        # Fingerprint route to discard identical duplicates
        key = (round(rt["distance"], 1), round(rt["duration"], 1), coords_list[0], coords_list[-1], len(coords_list))
        if key in seen:
            continue
        seen.add(key)
        routes.append(RawRoute(
            coords=coords_list,
            distance_miles=rt["distance"] / METERS_PER_MILE,
            duration_hours=rt["duration"] / 3600 * TRUCK_TIME_FACTOR,
        ))
        if len(routes) == 3:
            break

    # If the provider returns fewer than 3 alternatives, use supported corridor via-points
    # to obtain distinct, valid road routes with real geometry and duration.
    if 1 <= len(routes) < 3:
        primary_dist_m = routes[0].distance_miles * METERS_PER_MILE
        lat1, lon1 = origin
        lat2, lon2 = dest
        mid_lat = (lat1 + lat2) / 2.0
        mid_lon = (lon1 + lon2) / 2.0
        dlat = lat2 - lat1
        dlon = (lon2 - lon1) * math.cos(math.radians(mid_lat))
        span = math.hypot(dlat, dlon)

        if span > 0.05:
            # Perpendicular vector to explore lateral corridor options
            nlat = -dlon / span
            nlon = dlat / span
            candidates = []
            for ratio in [0.10, -0.10, 0.18, -0.18, 0.25, -0.25]:
                vlat = mid_lat + ratio * span * nlat
                vlon = mid_lon + (ratio * span * nlon) / math.cos(math.radians(mid_lat))
                candidates.append((round(vlat, 5), round(vlon, 5)))

            for via in candidates:
                via_coords = f"{origin[1]},{origin[0]};{via[1]},{via[0]};{dest[1]},{dest[0]}"
                try:
                    res = requests.get(f"https://router.project-osrm.org/route/v1/driving/{via_coords}",
                                       params={"overview": "full", "geometries": "geojson"},
                                       headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
                    if getattr(res, "status_code", 200) == 200:
                        vdata = res.json()
                        if vdata.get("code") == "Ok" and vdata.get("routes"):
                            cand_rt = vdata["routes"][0]
                            cand_dist = cand_rt["distance"]
                            # Must not be absurdly long (< 35% detour) and must be distinct
                            if cand_dist <= primary_dist_m * 1.35 and _is_distinct_route(cand_dist, routes):
                                cand_coords = [(lat, lon) for lon, lat in cand_rt["geometry"]["coordinates"]]
                                routes.append(RawRoute(
                                    coords=cand_coords,
                                    distance_miles=cand_dist / METERS_PER_MILE,
                                    duration_hours=cand_rt["duration"] / 3600 * TRUCK_TIME_FACTOR,
                                ))
                                if len(routes) == 3:
                                    break
                except Exception:
                    pass

    if not routes:
        raise LookupError(f"No route found: {data.get('code')}")
    return routes


def _fetch_chunk(chunk: list) -> list:
    attempts = 3
    for attempt in range(attempts):
        try:
            r = requests.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": ",".join(str(k[0]) for k in chunk),
                "longitude": ",".join(str(k[1]) for k in chunk),
                "hourly": "wind_speed_10m,rain,showers,snowfall",
                "wind_speed_unit": "mph", "timezone": "GMT", "forecast_days": 16,
            }, timeout=TIMEOUT)
            if getattr(r, "status_code", 200) == 429 and attempt < attempts - 1:
                time.sleep(0.5 * (2 ** attempt))
                continue
            r.raise_for_status()
            payload = r.json()
            payload = payload if isinstance(payload, list) else [payload]  # 1 location -> dict
            return [(k, item["hourly"]) for k, item in zip(chunk, payload)]
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < attempts - 1:
                time.sleep(0.5 * (2 ** attempt))
                continue
            raise


def _fetch_hourly(keys: list) -> None:
    """Fill _cache for any (lat, lon) keys that are missing or stale, fetching
    chunks of locations in parallel."""
    now = time.time()
    todo = [k for k in keys if k not in _cache or now - _cache[k][0] > CACHE_TTL]
    chunks = [todo[i:i + WEATHER_CHUNK] for i in range(0, len(todo), WEATHER_CHUNK)]
    if not chunks:
        return
    with ThreadPoolExecutor(max_workers=min(WEATHER_WORKERS, len(chunks))) as pool:
        for pairs in pool.map(_fetch_chunk, chunks):
            for k, hourly in pairs:
                _cache[k] = (now, hourly)


def fetch_weather(points: list) -> list:
    """points: [(lat, lon, eta_utc), ...] -> [Weather, ...] in the same order.
    Coordinates are rounded to 2 dp (~1 km) so nearby checkpoints share a call."""
    keys = [(round(lat, 2), round(lon, 2)) for lat, lon, _ in points]
    _fetch_hourly(list(dict.fromkeys(keys)))
    return [extract_weather(_cache[k][1], eta)
            for k, (_, _, eta) in zip(keys, points)]


def fetch_weather_window(points: list, start, hours: int) -> list:
    """points: [(lat, lon), ...] -> one list of hourly Weather per point,
    covering `start` .. `start`+hours."""
    keys = [(round(lat, 2), round(lon, 2)) for lat, lon in points]
    _fetch_hourly(list(dict.fromkeys(keys)))
    return [hourly_window(_cache[k][1], start, hours) for k in keys]

"""Request validation and JSON shaping for the API."""
from datetime import datetime, timedelta, timezone

from .recommend import explain, rank_routes
from .risk import classify

MAX_GEOMETRY_POINTS = 1500
ALLOWED_INTERVALS = (10, 25, 50)
MAX_INPUT_POINTS = 5000
MAX_LOAD_LB = 80_000          # US federal gross vehicle weight limit


class ValidationError(Exception):
    def __init__(self, errors: dict):
        super().__init__(errors)
        self.errors = errors


def _parse_departure(raw, now, errors):
    try:
        departure = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        errors["departure"] = "Must be an ISO 8601 date/time."
        return None
    if departure.tzinfo is None:
        errors["departure"] = "Must include a timezone offset (e.g. ...Z)."
        return None
    departure = departure.astimezone(timezone.utc)
    if departure < now - timedelta(hours=1):
        errors["departure"] = "Departure is in the past."
    elif departure > now + timedelta(days=15):
        errors["departure"] = "Forecasts only reach about 15 days ahead."
    return departure


def _parse_load(load, errors):
    if isinstance(load, bool) or not isinstance(load, (int, float)) or load <= 0:
        errors["load_lb"] = "Must be a positive number (pounds)."
    elif load > MAX_LOAD_LB:
        errors["load_lb"] = f"Must be at most {MAX_LOAD_LB:,} lb."
    else:
        return float(load)


def parse_request(body: dict, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    errors = {}

    for key in ("origin", "destination"):
        v = body.get(key)
        if not isinstance(v, str) or not v.strip():
            errors[key] = "Required."

    departure = _parse_departure(body.get("departure"), now, errors)
    load = _parse_load(body.get("load_lb"), errors)

    interval = body.get("interval_miles")
    if interval is not None and interval not in ALLOWED_INTERVALS:
        errors["interval_miles"] = f"Must be one of {list(ALLOWED_INTERVALS)}."

    if errors:
        raise ValidationError(errors)
    return {"origin": body["origin"].strip(), "destination": body["destination"].strip(),
            "departure": departure, "load_lb": load, "interval": interval,
            "demo": body.get("demo") is True}


def parse_heatmap_request(body: dict, now=None) -> dict:
    """`geometries` is the list of route polylines ([[lat, lon], ...]) the
    frontend already received from /api/analyze."""
    now = now or datetime.now(timezone.utc)
    errors = {}
    routes = []
    geoms = body.get("geometries")
    if not isinstance(geoms, list) or not 1 <= len(geoms) <= 3:
        errors["geometries"] = "Provide 1 to 3 route polylines."
    else:
        for g in geoms:
            try:
                pts = [(float(a), float(b)) for a, b in g]
            except (TypeError, ValueError):
                pts = None
            if (not pts or not 2 <= len(pts) <= MAX_INPUT_POINTS
                    or any(not (-90 <= la <= 90 and -180 <= lo <= 180) for la, lo in pts)):
                errors["geometries"] = "Each route needs 2+ valid [lat, lon] points."
                break
            routes.append(pts)

    departure = _parse_departure(body.get("departure"), now, errors)
    load = _parse_load(body.get("load_lb"), errors)
    if errors:
        raise ValidationError(errors)
    return {"routes": routes, "departure": departure, "load_lb": load,
            "demo": body.get("demo") is True}


def serialize_heatmap(points, windows, start, load_lb) -> dict:
    """Compact column-per-metric arrays: one entry per forecast hour, so the
    slider only indexes into data the browser already holds."""
    n = min(len(w) for w in windows)           # shortest window wins
    out = []
    for (lat, lon), w in zip(points, windows):
        w = w[:n]
        out.append({
            "lat": lat, "lon": lon,
            "wind": [round(x.wind_mph, 1) for x in w],
            "rain": [round(x.rain_in_hr, 3) for x in w],
            "snow": [round(x.snow_in_hr, 3) for x in w],
            "risk": [int(classify(x.wind_mph, x.rain_in_hr, x.snow_in_hr, load_lb)) for x in w],
        })
    return {"start": _iso(start), "hours": n, "points": out}


def _decimate(coords, limit=MAX_GEOMETRY_POINTS):
    if len(coords) <= limit:
        return coords
    step = len(coords) / (limit - 1)
    out = [coords[int(i * step)] for i in range(limit - 1)]
    out.append(coords[-1])
    return out


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def serialize_results(results, best, origin, dest) -> dict:
    metrics = [r.metrics for r in results]
    order = rank_routes(metrics)
    runner_up = metrics[order[1]] if len(order) > 1 else None
    routes = []
    for r in results:
        m = r.metrics
        routes.append({
            "index": r.index,
            "rank": order.index(r.index) + 1,
            "recommended": r.index == best,
            "distance_miles": round(r.raw.distance_miles, 1),
            "duration_hours": round(r.raw.duration_hours, 2),
            "arrival": _iso(r.checkpoints[-1].eta),
            "interval_miles": r.interval_miles,
            "geometry": [[round(la, 5), round(lo, 5)] for la, lo in _decimate(r.raw.coords)],
            "metrics": {
                "no_travel_miles": round(m.no_travel_miles, 1),
                "severe_miles": round(m.severe_miles, 1),
                "high_miles": round(m.high_miles, 1),
                "avg_risk": round(m.avg_risk, 2),
                "has_no_travel": m.has_no_travel,
            },
            "checkpoints": [{
                "mile": round(c.mile, 1), "lat": round(c.lat, 5), "lon": round(c.lon, 5),
                "eta": _iso(c.eta), "segment_miles": round(c.segment_miles, 1),
                "wind_mph": round(c.weather.wind_mph, 1),
                "rain_in_hr": round(c.weather.rain_in_hr, 3),
                "snow_in_hr": round(c.weather.snow_in_hr, 3),
                "risk": c.risk.name, "risk_level": int(c.risk),
            } for c in r.checkpoints],
        })
    return {"origin": {"lat": origin[0], "lon": origin[1]},
            "destination": {"lat": dest[0], "lon": dest[1]},
            "recommended_index": best,
            "recommendation_reason": explain(metrics[best], runner_up),
            "routes": routes}

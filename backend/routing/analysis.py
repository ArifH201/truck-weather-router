"""Turns raw routes + a weather source into scored, ranked route results."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

from . import geo
from .recommend import Checkpoint, RouteMetrics, compute_metrics, rank_routes
from .risk import Risk, classify
from .weather import Weather


@dataclass
class RawRoute:
    coords: list            # [(lat, lon), ...]
    distance_miles: float
    duration_hours: float


@dataclass
class CheckpointResult:
    mile: float
    lat: float
    lon: float
    eta: datetime
    segment_miles: float
    weather: Weather
    risk: Risk


@dataclass
class RouteResult:
    index: int
    raw: RawRoute
    interval_miles: float
    checkpoints: list = field(default_factory=list)
    metrics: Optional[RouteMetrics] = None


# fetch_weather([(lat, lon, eta), ...]) -> [Weather, ...]  (same order)
WeatherFetcher = Callable[[list], list]


def analyze_routes(routes: list, departure: datetime, load_lb: float,
                   fetch_weather: WeatherFetcher,
                   interval: Optional[float] = None):
    """Returns (list[RouteResult], recommended_index)."""
    results, requests = [], []
    for i, r in enumerate(routes):
        step = interval or geo.auto_interval(r.distance_miles)
        cum = geo.cumulative_miles(r.coords, r.distance_miles)
        dists = geo.checkpoint_distances(r.distance_miles, step)
        segs = geo.segment_miles(dists, r.distance_miles)
        res = RouteResult(index=i, raw=r, interval_miles=step)
        for d, seg in zip(dists, segs):
            lat, lon = geo.point_at(r.coords, cum, d)
            # ETA assumes constant average speed along the route.
            frac = d / r.distance_miles if r.distance_miles else 0.0
            eta = departure + timedelta(hours=r.duration_hours * frac)
            res.checkpoints.append((d, lat, lon, eta, seg))
            requests.append((lat, lon, eta))
        results.append(res)

    # One batched weather call for every checkpoint on every route.
    weather = iter(fetch_weather(requests))
    for res in results:
        scored = []
        for d, lat, lon, eta, seg in res.checkpoints:
            w = next(weather)
            risk = classify(w.wind_mph, w.rain_in_hr, w.snow_in_hr, load_lb)
            scored.append(CheckpointResult(d, lat, lon, eta, seg, w, risk))
        res.checkpoints = scored
        res.metrics = compute_metrics(
            [Checkpoint(c.segment_miles, c.risk) for c in scored],
            res.raw.duration_hours)

    best = rank_routes([r.metrics for r in results])[0]
    return results, best

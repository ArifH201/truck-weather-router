"""Route metrics and recommendation.

Each checkpoint "owns" the stretch of road it represents (segment_miles), so
Severe/High miles are sums of segment lengths, not checkpoint counts.
"""
from dataclasses import dataclass
from typing import Iterable

from .risk import Risk


@dataclass(frozen=True)
class Checkpoint:
    segment_miles: float
    risk: Risk


@dataclass(frozen=True)
class RouteMetrics:
    no_travel_miles: float
    severe_miles: float
    high_miles: float
    avg_risk: float          # distance-weighted, 0 (Low) .. 4 (No Travel)
    duration_hours: float

    @property
    def has_no_travel(self) -> bool:
        return self.no_travel_miles > 0


def compute_metrics(checkpoints: Iterable[Checkpoint],
                    duration_hours: float) -> RouteMetrics:
    cps = list(checkpoints)
    total = sum(c.segment_miles for c in cps)
    miles = lambda r: sum(c.segment_miles for c in cps if c.risk == r)
    weighted = sum(c.segment_miles * int(c.risk) for c in cps)
    return RouteMetrics(
        no_travel_miles=miles(Risk.NO_TRAVEL),
        severe_miles=miles(Risk.SEVERE),
        high_miles=miles(Risk.HIGH),
        avg_risk=weighted / total if total else 0.0,
        duration_hours=duration_hours,
    )


def sort_key(m: RouteMetrics):
    """Spec order: fewest Severe, fewest High, lowest avg risk, shortest time.
    Routes containing No Travel segments are ranked after all drivable
    routes (then by how much No Travel they contain)."""
    return (m.has_no_travel, m.no_travel_miles, m.severe_miles,
            m.high_miles, round(m.avg_risk, 4), m.duration_hours)


def rank_routes(metrics: list[RouteMetrics]) -> list[int]:
    """Returns route indices, best first."""
    return sorted(range(len(metrics)), key=lambda i: sort_key(metrics[i]))


# (label, metric attribute, unit) in the same priority order as sort_key.
_CRITERIA = [
    ("No Travel miles", "no_travel_miles", "mi"),
    ("Severe miles", "severe_miles", "mi"),
    ("High miles", "high_miles", "mi"),
    ("average risk", "avg_risk", ""),
    ("travel time", "duration_hours", "h"),
]


def explain(best: RouteMetrics, runner_up) -> str:
    """One-sentence reason the best route won, based on the first criterion
    (in spec priority order) where it beats the runner-up."""
    prefix = ("Every route has No Travel conditions; this one has the least. "
              if best.has_no_travel else "")
    if runner_up is None:
        return prefix + "Only one route was available."
    for label, attr, unit in _CRITERIA:
        b, o = getattr(best, attr), getattr(runner_up, attr)
        if round(b, 4) != round(o, 4):
            return (f"{prefix}Lower {label} than the next-best route "
                    f"({b:.1f}{unit} vs {o:.1f}{unit}).")
    return prefix + "Tied with the next-best route on every measure."

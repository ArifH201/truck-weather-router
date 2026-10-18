"""Weather risk classification for a single checkpoint.

Boundary convention (the spec's ranges overlap/have gaps, so we pick one):
  * Each level's lower bound is inclusive, e.g. wind 35.0 -> High.
  * "No Travel" is defined with >= for wind (>=55) and > for rain/snow
    (>1.00, >3.0), exactly as written, so rain 1.00 is still Severe.
  * Fractional values between published ranges (e.g. wind 34.5) fall into
    the lower level: the next level starts at its stated lower bound.
"""
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


def wind_risk(mph: float) -> Risk:
    if mph >= 55: return Risk.NO_TRAVEL
    if mph >= 45: return Risk.SEVERE
    if mph >= 35: return Risk.HIGH
    if mph >= 25: return Risk.MODERATE
    return Risk.LOW


def rain_risk(in_per_hr: float) -> Risk:
    if in_per_hr > 1.00: return Risk.NO_TRAVEL
    if in_per_hr >= 0.50: return Risk.SEVERE
    if in_per_hr >= 0.25: return Risk.HIGH
    if in_per_hr >= 0.10: return Risk.MODERATE
    return Risk.LOW


def snow_risk(in_per_hr: float) -> Risk:
    if in_per_hr > 3.0: return Risk.NO_TRAVEL
    if in_per_hr >= 2.0: return Risk.SEVERE
    if in_per_hr >= 1.0: return Risk.HIGH
    if in_per_hr >= 0.5: return Risk.MODERATE
    return Risk.LOW


def apply_load_rules(wind_mph: float, load_lb: float, base: Risk) -> Risk:
    """Load rules only ever escalate risk, never lower it."""
    if wind_mph >= 55:
        return Risk.NO_TRAVEL                      # any load
    if 45 <= wind_mph < 55 and load_lb > 30_000:
        return Risk.NO_TRAVEL
    if 35 <= wind_mph < 45 and load_lb > 40_000:
        return max(base, Risk.SEVERE)
    return base


def classify(wind_mph: float, rain_in_hr: float, snow_in_hr: float,
             load_lb: float) -> Risk:
    """Overall risk = worst of wind/rain/snow, then escalated by load rules."""
    base = max(wind_risk(wind_mph), rain_risk(rain_in_hr), snow_risk(snow_in_hr))
    return apply_load_rules(wind_mph, load_lb, base)

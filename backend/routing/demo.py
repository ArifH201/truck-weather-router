"""Simulated storm for demos and UI testing. NOT real weather.

Enabled only when settings.DEMO_WEATHER_ENABLED is true AND the request sends
`demo: true`. Routes and geocoding stay real; only the forecast is replaced by a
deterministic storm band that sweeps across the corridor over ~32 hours, so the
heatmap slider visibly passes through every risk level.
"""
import math

from .weather import Weather

STORM_START = 0.20          # storm centre as a fraction of the corridor at hour 0
STORM_SPEED = 1 / 40        # fraction of the corridor covered per hour
STORM_WIDTH = 0.12          # gaussian width, as a fraction of the corridor
CROSS_TILT = 2.0            # storm arrives earlier/later on routes north/south of centre
MIN_SPAN_DEG = 0.5
CALM_WIND = 10.0


def _frame(coords):
    """Return f(lat, lon) -> position along the corridor's longer axis (0..1,
    shifted slightly by how far the point sits across the corridor)."""
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    lat0, lat1, lon0, lon1 = min(lats), max(lats), min(lons), max(lons)
    lat_span = max(lat1 - lat0, MIN_SPAN_DEG)
    lon_span = max(lon1 - lon0, MIN_SPAN_DEG)
    if lon_span >= lat_span:
        return lambda lat, lon: ((lon - lon0) / lon_span
                                 + CROSS_TILT * (lat - (lat0 + lat1) / 2) / lon_span)
    return lambda lat, lon: ((lat - lat0) / lat_span
                             + CROSS_TILT * (lon - (lon0 + lon1) / 2) / lat_span)


def _storm(lat, u, hours) -> Weather:
    centre = STORM_START + hours * STORM_SPEED
    s = math.exp(-(((u - centre) / STORM_WIDTH) ** 2))      # 0 (calm) .. 1 (core)
    return Weather(
        wind_mph=CALM_WIND + 48 * s,                          # core reaches 58 mph
        rain_in_hr=0.75 * s,
        snow_in_hr=2.4 * s if lat >= 41 else 0.0,             # snow in the north only
    )


def fetch_weather(points: list) -> list:
    """Same contract as providers.fetch_weather: [(lat, lon, eta)] -> [Weather]."""
    locate = _frame([(lat, lon) for lat, lon, _ in points])
    anchor = min(eta for _, _, eta in points)
    return [_storm(lat, locate(lat, lon), (eta - anchor).total_seconds() / 3600)
            for lat, lon, eta in points]


def fetch_weather_window(points: list, start, hours: int) -> list:
    """Same contract as providers.fetch_weather_window."""
    locate = _frame(points)
    return [[_storm(lat, locate(lat, lon), h) for h in range(hours)]
            for lat, lon in points]

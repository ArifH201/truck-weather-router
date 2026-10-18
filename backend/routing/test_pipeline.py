from datetime import datetime, timedelta, timezone

import pytest

from . import geo
from .analysis import RawRoute, analyze_routes
from .risk import Risk
from .weather import ForecastRangeError, Weather, extract_weather

T0 = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)


def test_segments_tile_the_route():
    for total in (3, 10, 87.5, 400):
        ds = geo.checkpoint_distances(total, 25)
        assert ds[0] == 0 and ds[-1] == total
        assert sum(geo.segment_miles(ds, total)) == pytest.approx(total)


def test_point_at_interpolates_and_clamps():
    coords = [(0.0, 0.0), (0.0, 1.0)]
    cum = geo.cumulative_miles(coords, 100)
    assert geo.point_at(coords, cum, 50) == pytest.approx((0.0, 0.5))
    assert geo.point_at(coords, cum, -5) == coords[0]
    assert geo.point_at(coords, cum, 500) == coords[-1]


def test_auto_interval():
    assert [geo.auto_interval(m) for m in (150, 300, 900)] == [10, 25, 50]


def test_extract_weather_converts_units():
    hourly = {"time": ["2026-10-12T00:00", "2026-10-12T01:00"],
              "wind_speed_10m": [10, 40], "rain": [0, 2.54], "showers": [0, 2.54],
              "snowfall": [0, 2.54]}
    w = extract_weather(hourly, datetime(2026, 10, 12, 1, 20, tzinfo=timezone.utc))
    assert (w.wind_mph, w.rain_in_hr, w.snow_in_hr) == (40, pytest.approx(0.2), pytest.approx(1.0))
    with pytest.raises(ForecastRangeError):
        extract_weather(hourly, T0 + timedelta(days=3))


def test_eta_uses_time_at_checkpoint_and_picks_safer_route():
    # Two identical-length routes; weather turns bad only after 12:00 UTC.
    # Route B is slower but its checkpoints are reached... later, so test by
    # making weather depend on both ETA and position instead.
    a = RawRoute([(0, 0), (0, 2)], 100, 2)      # fast
    b = RawRoute([(1, 0), (1, 2)], 100, 4)      # slow

    def fake_weather(points):
        out = []
        for lat, lon, eta in points:
            # route A (lat ~0) is stormy; route B (lat ~1) is calm
            out.append(Weather(50, 0, 0) if lat < 0.5 else Weather(5, 0, 0))
        return out

    results, best = analyze_routes([a, b], T0, 20_000, fake_weather, interval=25)
    assert best == 1
    assert results[0].metrics.severe_miles == pytest.approx(100)
    assert results[1].metrics.severe_miles == 0
    # ETAs advance linearly with distance
    etas = [c.eta for c in results[1].checkpoints]
    assert etas[0] == T0 and etas[-1] == T0 + timedelta(hours=4)


def test_heavy_load_escalates_in_pipeline():
    r = RawRoute([(0, 0), (0, 1)], 50, 1)
    fw = lambda pts: [Weather(40, 0, 0)] * len(pts)
    light, _ = analyze_routes([r], T0, 30_000, fw, interval=25)
    heavy, _ = analyze_routes([r], T0, 45_000, fw, interval=25)
    assert all(c.risk == Risk.HIGH for c in light[0].checkpoints)
    assert all(c.risk == Risk.SEVERE for c in heavy[0].checkpoints)

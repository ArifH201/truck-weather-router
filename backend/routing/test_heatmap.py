import json
from datetime import datetime, timedelta, timezone

import pytest
from django.test import Client

from . import providers
from .corridor import MAX_POINTS, sample_corridor
from .weather import ForecastRangeError, Weather, hourly_window

START = datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc)


def fake_hourly(hours=384, wind=10.0):
    times = [(START + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {"time": times, "wind_speed_10m": [wind] * hours, "rain": [0] * hours,
            "showers": [0] * hours, "snowfall": [0] * hours}


# ---- corridor sampling -------------------------------------------------
def line(lat, lon0, lon1, n=200):
    return [(lat, lon0 + (lon1 - lon0) * i / (n - 1)) for i in range(n)]


def test_corridor_is_capped_and_deduped():
    long_routes = [line(0.0, 0, 20), line(0.2, 0, 20), line(0.4, 0, 20)]  # ~1,400 mi each
    pts = sample_corridor(long_routes)
    assert len(pts) <= MAX_POINTS + len(long_routes)
    assert len(pts) == len(set(pts))
    same = sample_corridor([line(0.0, 0, 5)] * 3)           # identical routes
    assert len(same) == len(sample_corridor([line(0.0, 0, 5)]))


def test_corridor_covers_endpoints():
    pts = sample_corridor([line(10.0, 0, 3)])
    assert pts[0] == (10.0, 0.0) and pts[-1] == (10.0, 3.0)


# ---- hourly window -----------------------------------------------------
def test_window_truncates_at_end_of_forecast():
    h = fake_hourly(hours=30)
    assert len(hourly_window(h, START + timedelta(hours=10), 49)) == 20
    with pytest.raises(ForecastRangeError):
        hourly_window(h, START + timedelta(hours=40), 49)


# ---- provider batching/caching (HTTP mocked) -------------------------
class FakeResp:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload


@pytest.fixture
def fake_http(monkeypatch):
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append(params)
        n = len(params["latitude"].split(","))
        items = [{"hourly": fake_hourly()} for _ in range(n)]
        return FakeResp(items if n > 1 else items[0])

    providers._cache.clear()
    monkeypatch.setattr(providers.requests, "get", fake_get)
    return calls


def test_provider_chunks_and_caches(fake_http):
    pts = [(i / 100, 0.0) for i in range(120)]
    out = providers.fetch_weather_window(pts, START, 49)
    assert len(fake_http) == 3 and len(out) == 120 and len(out[0]) == 49   # 50+50+20
    providers.fetch_weather_window(pts, START, 49)
    assert len(fake_http) == 3                                             # all cached


def test_provider_single_location_returns_dict(fake_http):
    out = providers.fetch_weather_window([(1.0, 1.0)], START, 5)
    assert len(out) == 1 and len(out[0]) == 5


# ---- endpoint ----------------------------------------------------------
def depart(hours=24):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def post(body):
    return Client().post("/api/heatmap", data=json.dumps(body), content_type="application/json")


def body(**over):
    b = {"geometries": [[[0, 0], [0, 1], [0, 2]]], "departure": depart(), "load_lb": 45000}
    b.update(over)
    return b


def test_heatmap_happy_path(monkeypatch):
    def fake(points, start, hours):
        return [[Weather(40, 0, 0)] * min(hours, 30) for _ in points]
    monkeypatch.setattr(providers, "fetch_weather_window", fake)
    r = post(body())
    assert r.status_code == 200
    d = r.json()
    assert d["hours"] == 30 and d["points"]
    p = d["points"][0]
    assert len(p["risk"]) == len(p["wind"]) == 30
    assert set(p["risk"]) == {3}          # 40 mph + 45,000 lb -> Severe


@pytest.mark.parametrize("bad", [
    {"geometries": []}, {"geometries": [[[0, 0]]]}, {"geometries": [[[99, 0], [0, 0]]]},
    {"geometries": "x"}, {"departure": "soon"}, {"load_lb": 0},
])
def test_heatmap_validation(bad):
    r = post(body(**bad))
    assert r.status_code == 400 and r.json()["fields"]


def test_heatmap_forecast_out_of_range(monkeypatch):
    def boom(*a): raise ForecastRangeError("too far")
    monkeypatch.setattr(providers, "fetch_weather_window", boom)
    assert post(body()).status_code == 422

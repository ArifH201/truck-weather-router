import json
from datetime import datetime, timedelta, timezone

import pytest
from django.test import Client

from . import demo, providers
from .analysis import RawRoute
from .risk import Risk, classify

START = datetime(2026, 10, 18, 18, 0, tzinfo=timezone.utc)
LINE = [(40.0, -105 + i * 0.5) for i in range(30)]      # ~14.5 degrees of longitude


def levels(window_by_point, load=45_000):
    return {classify(w.wind_mph, w.rain_in_hr, w.snow_in_hr, load)
            for window in window_by_point for w in window}


def test_storm_reaches_every_risk_level_and_then_clears():
    windows = demo.fetch_weather_window(LINE, START, 49)
    assert levels(windows) == set(Risk)
    last = [w[-1] for w in windows]
    assert all(classify(w.wind_mph, w.rain_in_hr, w.snow_in_hr, 45_000) == Risk.LOW for w in last)


def test_storm_is_deterministic_and_moves():
    a = demo.fetch_weather_window(LINE, START, 49)
    assert a == demo.fetch_weather_window(LINE, START, 49)
    hot = lambda h: max(range(len(LINE)), key=lambda i: a[i][h].wind_mph)
    assert hot(30) > hot(0)                      # peak position moves along the corridor


def test_fetch_weather_matches_window_contract():
    pts = [(lat, lon, START + timedelta(hours=i)) for i, (lat, lon) in enumerate(LINE)]
    out = demo.fetch_weather(pts)
    assert len(out) == len(pts) and all(hasattr(w, "wind_mph") for w in out)


def post(path, body):
    return Client().post(f"/api/{path}", data=json.dumps(body), content_type="application/json")


def trip(**over):
    base = {"origin": "A", "destination": "B", "load_lb": 45000, "demo": True,
            "departure": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")}
    base.update(over)
    return base


@pytest.fixture
def fake_trip(monkeypatch):
    monkeypatch.setattr(providers, "geocode", lambda q: (40.0, -105.0) if q == "A" else (40.0, -90.0))
    monkeypatch.setattr(providers, "fetch_routes", lambda o, d: [
        RawRoute([(40.0, -105 + i * 0.25) for i in range(61)], 800, 14),
        RawRoute([(41.5, -105 + i * 0.25) for i in range(61)], 850, 15)])


def test_demo_analyze_and_heatmap(fake_trip, settings):
    settings.DEMO_WEATHER_ENABLED = True
    r = post("analyze", trip())
    assert r.status_code == 200
    data = r.json()
    assert data["demo"] is True
    worst = max(c["risk_level"] for rt in data["routes"] for c in rt["checkpoints"])
    assert worst >= 2                                           # the trip meets the storm
    h = post("heatmap", {"geometries": [rt["geometry"] for rt in data["routes"]],
                         "departure": trip()["departure"], "load_lb": 45000, "demo": True})
    assert h.status_code == 200 and h.json()["demo"] is True
    assert max(max(p["risk"]) for p in h.json()["points"]) == 4


def test_demo_refused_when_disabled(fake_trip, settings):
    settings.DEMO_WEATHER_ENABLED = False
    assert post("analyze", trip()).status_code == 400
    assert Client().get("/api/health").json()["demo_enabled"] is False


def test_real_weather_path_is_not_demo(fake_trip, settings, monkeypatch):
    settings.DEMO_WEATHER_ENABLED = True
    monkeypatch.setattr(providers, "fetch_weather", lambda pts: [__import__("routing.weather", fromlist=["Weather"]).Weather(5, 0, 0)] * len(pts))
    data = post("analyze", trip(demo=False)).json()
    assert data["demo"] is False
    assert max(c["risk_level"] for rt in data["routes"] for c in rt["checkpoints"]) == 0

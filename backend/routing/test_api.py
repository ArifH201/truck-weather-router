import json
from datetime import datetime, timedelta, timezone

import pytest
from django.test import Client

from . import providers, views
from .analysis import RawRoute
from .recommend import RouteMetrics, explain
from .weather import ForecastRangeError, Weather


def depart(hours=24):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def payload(**over):
    base = {"origin": "A", "destination": "B", "departure": depart(), "load_lb": 42000}
    base.update(over)
    return base


def post(body):
    return Client().post("/api/analyze", data=json.dumps(body), content_type="application/json")


@pytest.fixture
def fake_providers(monkeypatch):
    monkeypatch.setattr(providers, "geocode", lambda q: (0.0, 0.0) if q == "A" else (0.0, 2.0))
    monkeypatch.setattr(providers, "fetch_routes", lambda o, d: [
        RawRoute([(0, 0), (0, 2)], 100, 2), RawRoute([(1, 0), (1, 2)], 120, 3)])
    monkeypatch.setattr(providers, "fetch_weather", lambda pts: [
        Weather(40, 0, 0) if lat < 0.5 else Weather(5, 0, 0) for lat, _, _ in pts])


def test_happy_path(fake_providers):
    r = post(payload())
    assert r.status_code == 200
    data = r.json()
    assert data["recommended_index"] == 1
    a, b = data["routes"]
    assert a["metrics"]["severe_miles"] == 100      # 40 mph + 42,000 lb -> Severe
    assert b["metrics"]["severe_miles"] == 0
    assert b["recommended"] and b["rank"] == 1 and a["rank"] == 2
    assert "Severe miles" in data["recommendation_reason"]
    assert a["checkpoints"][0]["risk"] == "SEVERE"


@pytest.mark.parametrize("bad", [
    {"origin": ""}, {"load_lb": -5}, {"load_lb": 90000}, {"load_lb": "heavy"},
    {"departure": "tomorrow"}, {"departure": "2026-10-12T08:00:00"},
    {"departure": depart(-72)}, {"departure": depart(24 * 20)},
    {"interval_miles": 7},
])
def test_validation(bad):
    r = post(payload(**bad))
    assert r.status_code == 400 and r.json()["fields"]


def test_bad_json_and_method():
    assert Client().post("/api/analyze", data="nope", content_type="application/json").status_code == 400
    assert Client().get("/api/analyze").status_code == 405


def test_unknown_place_is_422(monkeypatch):
    def boom(q): raise LookupError(f"Could not find location: {q}")
    monkeypatch.setattr(providers, "geocode", boom)
    assert post(payload()).status_code == 422


def test_forecast_range_is_422(fake_providers, monkeypatch):
    def boom(pts): raise ForecastRangeError("too far")
    monkeypatch.setattr(providers, "fetch_weather", boom)
    assert post(payload()).status_code == 422


def test_explain_picks_first_differing_criterion():
    m = lambda s, h, t: RouteMetrics(0, s, h, 1.0, t)
    assert "Severe" in explain(m(0, 50, 9), m(10, 0, 1))
    assert "High" in explain(m(0, 10, 9), m(0, 40, 1))
    assert "travel time" in explain(m(0, 0, 2), m(0, 0, 3))

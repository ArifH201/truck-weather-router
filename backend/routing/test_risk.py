from .risk import Risk, classify, wind_risk, rain_risk, snow_risk
from .recommend import Checkpoint, compute_metrics, rank_routes


def test_wind_boundaries():
    assert wind_risk(24.9) == Risk.LOW
    assert wind_risk(25) == Risk.MODERATE
    assert wind_risk(35) == Risk.HIGH
    assert wind_risk(45) == Risk.SEVERE
    assert wind_risk(55) == Risk.NO_TRAVEL


def test_rain_snow_no_travel_is_strictly_greater():
    assert rain_risk(1.00) == Risk.SEVERE and rain_risk(1.01) == Risk.NO_TRAVEL
    assert snow_risk(3.0) == Risk.SEVERE and snow_risk(3.01) == Risk.NO_TRAVEL


def test_worst_condition_wins():
    assert classify(10, 0.3, 0.6, 20_000) == Risk.HIGH


def test_load_rules():
    assert classify(55, 0, 0, 1_000) == Risk.NO_TRAVEL
    assert classify(50, 0, 0, 30_001) == Risk.NO_TRAVEL
    assert classify(50, 0, 0, 30_000) == Risk.SEVERE       # not > 30,000
    assert classify(40, 0, 0, 40_001) == Risk.SEVERE
    assert classify(40, 0, 0, 40_000) == Risk.HIGH          # not > 40,000


def test_load_rule_never_downgrades():
    assert classify(40, 0.6, 0, 45_000) == Risk.SEVERE
    assert classify(40, 2, 0, 45_000) == Risk.NO_TRAVEL


def test_segment_miles_weighting():
    m = compute_metrics([Checkpoint(10, Risk.SEVERE), Checkpoint(50, Risk.LOW)], 2)
    assert m.severe_miles == 10 and m.avg_risk == 3 * 10 / 60


def test_ranking_order():
    a = compute_metrics([Checkpoint(100, Risk.SEVERE)], 1)            # fast, severe
    b = compute_metrics([Checkpoint(100, Risk.HIGH)], 5)              # slow, high
    c = compute_metrics([Checkpoint(100, Risk.NO_TRAVEL)], 0.5)       # blocked
    d = compute_metrics([Checkpoint(100, Risk.HIGH)], 3)              # high, faster
    assert rank_routes([a, b, c, d]) == [3, 1, 0, 2]

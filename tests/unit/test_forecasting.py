import pandas as pd
import numpy as np
import pytest

from app.services.forecasting import _forecast_series


def make_series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(values), freq="MS")
    return pd.Series(values, index=idx, dtype=float)


# ── horizon / structure ──────────────────────────────────────────────────────

def test_returns_correct_horizon_length():
    series = make_series([10.0, 12.0, 11.0, 13.0])
    points = _forecast_series(series, horizon=6, z=1.65)
    assert len(points) == 6


def test_each_point_has_required_keys():
    series = make_series([10.0, 12.0, 11.0])
    for pt in _forecast_series(series, horizon=3, z=1.65):
        assert "forecast_qty" in pt
        assert "lower_bound" in pt
        assert "upper_bound" in pt


def test_horizon_one_returns_single_point():
    series = make_series([5.0, 6.0, 5.5, 6.0])
    assert len(_forecast_series(series, horizon=1, z=1.65)) == 1


# ── non-negativity ───────────────────────────────────────────────────────────

def test_lower_bound_never_negative():
    """Even with extreme z and declining values, lower_bound must be >= 0."""
    series = make_series([2.0, 1.0, 0.5, 0.1])
    for pt in _forecast_series(series, horizon=6, z=10.0):
        assert pt["lower_bound"] >= 0.0


def test_forecast_never_negative():
    """Steep downward trend cannot produce a negative forecast."""
    series = make_series([100.0, 50.0, 10.0, 2.0, 0.5])
    for pt in _forecast_series(series, horizon=6, z=0.0):
        assert pt["forecast_qty"] >= 0.0


# ── ordering invariants ──────────────────────────────────────────────────────

def test_upper_bound_gte_forecast():
    series = make_series([10.0, 12.0, 11.0, 13.0, 12.0])
    for pt in _forecast_series(series, horizon=4, z=1.65):
        assert pt["upper_bound"] >= pt["forecast_qty"]


def test_forecast_gte_lower_bound():
    series = make_series([10.0, 12.0, 11.0])
    for pt in _forecast_series(series, horizon=3, z=1.65):
        assert pt["forecast_qty"] >= pt["lower_bound"]


# ── trend detection ──────────────────────────────────────────────────────────

def test_upward_trend_later_horizon_higher():
    """Strongly increasing series → h=3 forecast > h=1 forecast."""
    series = make_series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    points = _forecast_series(series, horizon=3, z=0.0)
    assert points[2]["forecast_qty"] > points[0]["forecast_qty"]


def test_flat_series_forecast_near_constant():
    """Constant series → EMA stays flat, trend ~= 0, forecast ≈ constant."""
    val = 10.0
    series = make_series([val] * 12)
    points = _forecast_series(series, horizon=1, z=0.0)
    assert abs(points[0]["forecast_qty"] - val) < 2.0


# ── edge cases ───────────────────────────────────────────────────────────────

def test_all_zeros_produces_zero_forecast():
    series = make_series([0.0, 0.0, 0.0, 0.0, 0.0])
    for pt in _forecast_series(series, horizon=3, z=1.65):
        assert pt["forecast_qty"] == 0.0
        assert pt["lower_bound"] == 0.0


def test_minimum_length_series_three_points():
    """Three data points (the minimum required by the service) should work."""
    series = make_series([5.0, 7.0, 6.0])
    points = _forecast_series(series, horizon=3, z=1.65)
    assert len(points) == 3


def test_single_spike_does_not_crash():
    series = make_series([0.0, 0.0, 100.0, 0.0, 0.0])
    points = _forecast_series(series, horizon=3, z=1.65)
    assert all(pt["forecast_qty"] >= 0.0 for pt in points)


def test_confidence_band_widens_with_higher_z():
    series = make_series([8.0, 10.0, 9.0, 11.0, 10.0])
    low_z = _forecast_series(series, horizon=1, z=0.5)[0]
    high_z = _forecast_series(series, horizon=1, z=3.0)[0]
    low_width = low_z["upper_bound"] - low_z["lower_bound"]
    high_width = high_z["upper_bound"] - high_z["lower_bound"]
    assert high_width > low_width

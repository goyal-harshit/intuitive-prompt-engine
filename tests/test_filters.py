"""EMA smoothing: pure math, no I/O."""

from __future__ import annotations

import pytest

from backend.gestures.filters import EMAFilter, EMAVec3Filter


def test_first_update_returns_the_raw_value() -> None:
    f = EMAFilter(alpha=0.3)
    assert f.update(5.0) == pytest.approx(5.0)


def test_converges_toward_a_constant_input() -> None:
    f = EMAFilter(alpha=0.5)
    f.update(0.0)
    for _ in range(20):
        val = f.update(10.0)
    assert val == pytest.approx(10.0, abs=1e-3)


def test_smooths_a_single_spike() -> None:
    f = EMAFilter(alpha=0.3)
    f.update(0.0)
    spiked = f.update(100.0)
    assert spiked == pytest.approx(30.0)
    assert spiked < 100.0


def test_reset_forgets_prior_state() -> None:
    f = EMAFilter(alpha=0.3)
    f.update(10.0)
    f.update(10.0)
    f.reset()
    assert f.update(5.0) == pytest.approx(5.0)


def test_vec3_filter_smooths_each_axis_independently() -> None:
    f = EMAVec3Filter(alpha=0.5)
    f.update(0.0, 0.0, 0.0)
    x, y, z = f.update(10.0, -4.0, 2.0)
    assert x == pytest.approx(5.0)
    assert y == pytest.approx(-2.0)
    assert z == pytest.approx(1.0)


def test_vec3_filter_reset() -> None:
    f = EMAVec3Filter(alpha=0.5)
    f.update(10.0, 10.0, 10.0)
    f.reset()
    assert f.update(1.0, 2.0, 3.0) == pytest.approx((1.0, 2.0, 3.0))

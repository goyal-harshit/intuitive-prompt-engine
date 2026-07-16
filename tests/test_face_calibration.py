"""Per-session neutral-face baseline calibration."""

from __future__ import annotations

import pytest

from backend.core.config import FaceCalibrationConfig
from backend.vision.calibration import _DEFAULT_BASELINE, FaceCalibrator


def test_calibrating_until_duration_elapses() -> None:
    cal = FaceCalibrator(FaceCalibrationConfig(enabled=True, calibration_duration_s=1.0))
    assert cal.calibrating is True
    cal.observe(ts=0.0, corner_lift=0.1, mouth_w=0.4, brow_raise=0.03, mouth_open=0.01)
    assert cal.calibrating is True
    cal.observe(ts=1.0, corner_lift=0.1, mouth_w=0.4, brow_raise=0.03, mouth_open=0.01)
    assert cal.calibrating is False


def test_baseline_is_default_before_calibration_completes() -> None:
    cal = FaceCalibrator(FaceCalibrationConfig(enabled=True, calibration_duration_s=1.0))
    assert cal.baseline == _DEFAULT_BASELINE


def test_baseline_is_mean_of_samples_after_calibration() -> None:
    cal = FaceCalibrator(FaceCalibrationConfig(enabled=True, calibration_duration_s=0.5))
    cal.observe(ts=0.0, corner_lift=0.1, mouth_w=0.3, brow_raise=0.02, mouth_open=0.0)
    cal.observe(ts=0.5, corner_lift=0.3, mouth_w=0.5, brow_raise=0.04, mouth_open=0.02)
    assert cal.baseline == pytest.approx((0.2, 0.4, 0.03, 0.01))


def test_disabled_calibration_never_calibrates_and_uses_default_baseline() -> None:
    cal = FaceCalibrator(FaceCalibrationConfig(enabled=False))
    cal.observe(ts=0.0, corner_lift=0.9, mouth_w=0.9, brow_raise=0.9, mouth_open=0.9)
    cal.observe(ts=10.0, corner_lift=0.9, mouth_w=0.9, brow_raise=0.9, mouth_open=0.9)
    assert cal.calibrating is False
    assert cal.baseline == _DEFAULT_BASELINE


def test_default_baseline_reproduces_original_uncalibrated_formula() -> None:
    # Original fixed formula: arousal = brow_raise*12 + mouth_open*4 - 0.35.
    # Baseline-relative math must reproduce it exactly before real samples land.
    _, _, brow_raise0, mouth_open0 = _DEFAULT_BASELINE
    brow_raise, mouth_open = 0.05, 0.02
    baseline_relative = (brow_raise - brow_raise0) * 12 + (mouth_open - mouth_open0) * 4
    original = brow_raise * 12 + mouth_open * 4 - 0.35
    assert baseline_relative == pytest.approx(original)

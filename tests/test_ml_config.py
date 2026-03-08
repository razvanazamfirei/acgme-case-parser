"""Tests for ML runtime configuration helpers."""

from __future__ import annotations

import warnings

import pytest

from case_parser.ml.config import (
    BASE_DEFAULT_ML_INFERENCE_JOBS,
    BASE_DEFAULT_ML_THRESHOLD,
    ML_INFERENCE_JOBS_ENV_VAR,
    ML_THRESHOLD_ENV_VAR,
    get_default_ml_inference_jobs,
    get_default_ml_threshold,
)


def test_get_default_ml_threshold_uses_builtin_default_when_unset():
    assert get_default_ml_threshold({}) == BASE_DEFAULT_ML_THRESHOLD


def test_get_default_ml_threshold_reads_valid_env_value():
    assert get_default_ml_threshold({ML_THRESHOLD_ENV_VAR: "0.75"}) == pytest.approx(
        0.75
    )


def test_get_default_ml_threshold_falls_back_and_warns_on_invalid_value():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        threshold = get_default_ml_threshold({ML_THRESHOLD_ENV_VAR: "invalid"})

    assert threshold == BASE_DEFAULT_ML_THRESHOLD
    assert len(caught) == 1
    assert ML_THRESHOLD_ENV_VAR in str(caught[0].message)


def test_get_default_ml_threshold_falls_back_and_warns_on_out_of_range_value():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        threshold = get_default_ml_threshold({ML_THRESHOLD_ENV_VAR: "1.5"})

    assert threshold == BASE_DEFAULT_ML_THRESHOLD
    assert len(caught) == 1
    assert "out-of-range" in str(caught[0].message)


def test_get_default_ml_inference_jobs_uses_builtin_default_when_unset():
    assert get_default_ml_inference_jobs({}) == BASE_DEFAULT_ML_INFERENCE_JOBS


def test_get_default_ml_inference_jobs_reads_valid_env_value():
    assert get_default_ml_inference_jobs({ML_INFERENCE_JOBS_ENV_VAR: "-1"}) == -1
    assert get_default_ml_inference_jobs({ML_INFERENCE_JOBS_ENV_VAR: "4"}) == 4


def test_get_default_ml_inference_jobs_falls_back_and_warns_on_invalid_value():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        jobs = get_default_ml_inference_jobs({ML_INFERENCE_JOBS_ENV_VAR: "invalid"})

    assert jobs == BASE_DEFAULT_ML_INFERENCE_JOBS
    assert len(caught) == 1
    assert ML_INFERENCE_JOBS_ENV_VAR in str(caught[0].message)


def test_get_default_ml_inference_jobs_falls_back_and_warns_on_out_of_range_value():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        jobs = get_default_ml_inference_jobs({ML_INFERENCE_JOBS_ENV_VAR: "0"})

    assert jobs == BASE_DEFAULT_ML_INFERENCE_JOBS
    assert len(caught) == 1
    assert "out-of-range" in str(caught[0].message)

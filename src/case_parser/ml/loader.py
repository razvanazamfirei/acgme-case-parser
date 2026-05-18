"""Loader functions for ML models and hybrid classifiers."""

from __future__ import annotations

import os
from pathlib import Path

from .config import DEFAULT_ML_THRESHOLD
from .hybrid import HybridClassifier

_DEFAULT_MODEL_PATH = "ml_models/procedure_classifier.pkl"
_MODEL_PATH_ENV_VAR = "CASE_PARSER_MODEL_PATH"


def get_hybrid_classifier(
    model_path: Path | None = None,
    ml_threshold: float = DEFAULT_ML_THRESHOLD,
    inference_jobs: int | None = None,
) -> HybridClassifier:
    """Get hybrid classifier with optional ML model.

    Args:
        model_path: Path to trained model pickle file.
            Takes precedence over environment variable.
            If None, uses CASE_PARSER_MODEL_PATH env var if set,
            otherwise falls back to the default path.
        ml_threshold: Minimum confidence to use ML prediction.
        inference_jobs: Optional sklearn/joblib ``n_jobs`` override used for
            inference-time estimator configuration.

    Returns:
        HybridClassifier instance (rules-only if no model found)
    """
    if model_path is None:
        env_path = os.environ.get(_MODEL_PATH_ENV_VAR)
        model_path = Path(env_path) if env_path else Path(_DEFAULT_MODEL_PATH)

    return HybridClassifier.load(
        model_path,
        ml_threshold,
        inference_jobs=inference_jobs,
    )

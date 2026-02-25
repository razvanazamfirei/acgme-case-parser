"""ML predictor wrapper for trained models."""

from __future__ import annotations

import pickle  # noqa: S403
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class ProcedureMLPipeline:
    """Inference pipeline that combines feature extraction and estimator."""

    def __init__(self, model: Any, features: Any):
        """Initialize the pipeline with a fitted estimator and feature extractor.

        Args:
            model: Fitted sklearn-compatible estimator with predict and
                predict_proba methods.
            features: Fitted feature transformer with a transform method.
        """
        self.model = model
        self.features = features
        self.classes_ = getattr(model, "classes_", [])

    @staticmethod
    def _coerce_inputs(procedures: Iterable[str] | str) -> list[str]:
        """Normalize procedure input to a list of strings.

        Args:
            procedures: Either a single procedure string or an iterable of
                procedure strings.

        Returns:
            List of procedure strings suitable for feature transformation.
        """
        if isinstance(procedures, str):
            return [procedures]
        return [str(proc) for proc in procedures]

    def predict(self, procedures: Iterable[str] | str) -> Any:
        """Predict categories for one or more procedure texts.

        Args:
            procedures: Single procedure string or iterable of strings.

        Returns:
            Array of predicted category labels, one per input procedure.
        """
        texts = self._coerce_inputs(procedures)
        feature_matrix = self.features.transform(texts)
        return self.model.predict(feature_matrix)

    def predict_proba(self, procedures: Iterable[str] | str) -> Any:
        """Return class probability estimates for one or more procedure texts.

        Args:
            procedures: Single procedure string or iterable of strings.

        Returns:
            2-D array of shape (n_samples, n_classes) with class probabilities.
        """
        texts = self._coerce_inputs(procedures)
        feature_matrix = self.features.transform(texts)
        return self.model.predict_proba(feature_matrix)


class MLPredictor:
    """Wrapper for trained ML model."""

    def __init__(self, pipeline: Any, metadata: dict):
        """Initialize predictor.

        Args:
            pipeline: Trained sklearn pipeline
            metadata: Model metadata dict
        """
        self.pipeline = pipeline
        self.metadata = metadata

    @classmethod
    def load(cls, model_path: Path) -> MLPredictor:
        """Load model from pickle file.

        Args:
            model_path: Path to model pickle file

        Returns:
            MLPredictor instance

        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If the pickle artifact is missing the expected
                ``pipeline`` key.
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        with model_path.open("rb") as f:
            model_data = pickle.load(f)  # noqa: S301

        if "pipeline" not in model_data:
            raise ValueError(
                "Unsupported model artifact format. Expected key: ['pipeline']."
            )
        pipeline = model_data["pipeline"]

        return cls(
            pipeline=pipeline,
            metadata=model_data.get("metadata", {}),
        )

    def predict(self, procedure_text: str) -> str:
        """Predict category for procedure text.

        Args:
            procedure_text: Procedure description

        Returns:
            Predicted category string
        """
        return self.pipeline.predict([procedure_text])[0]

    def predict_proba(self, procedure_text: str) -> dict[str, float]:
        """Get prediction probabilities for all categories.

        Args:
            procedure_text: Procedure description

        Returns:
            Dict mapping category to probability
        """
        proba = self.pipeline.predict_proba([procedure_text])[0]
        classes = self.pipeline.classes_

        return dict(zip(classes, proba, strict=False))

    def get_confidence(self, procedure_text: str) -> float:
        """Get confidence (max probability) for prediction.

        Args:
            procedure_text: Procedure description

        Returns:
            Confidence score (0.0-1.0)
        """
        proba = self.pipeline.predict_proba([procedure_text])[0]
        return float(proba.max())

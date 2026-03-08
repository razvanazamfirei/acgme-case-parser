"""Tests for hybrid ML classification flow."""

from __future__ import annotations

import pytest

from case_parser.domain import ProcedureCategory
from case_parser.ml.hybrid import HybridClassifier, _RuleContext


class _StubPredictor:
    def __init__(self, prediction: str, confidence: float):
        self.prediction = prediction
        self.confidence = confidence
        self.single_calls = 0
        self.batch_calls = 0

    def predict_with_confidence(
        self,
        procedure_text: str,
        services: list[str] | None = None,
        rule_category: str | None = None,
        rule_warning_count: int = 0,
    ) -> tuple[str, float]:
        del procedure_text, services, rule_category, rule_warning_count
        self.single_calls += 1
        return self.prediction, self.confidence

    def predict_with_confidence_many(
        self,
        procedure_texts: list[str],
        services_list: list[list[str]] | None = None,
        rule_categories: list[str] | None = None,
        rule_warning_counts: list[int] | None = None,
    ) -> tuple[list[str], list[float]]:
        del services_list, rule_categories, rule_warning_counts
        self.batch_calls += 1
        return [self.prediction for _ in procedure_texts], [
            self.confidence for _ in procedure_texts
        ]


class _ShortBatchPredictor(_StubPredictor):
    def predict_with_confidence_many(
        self,
        procedure_texts: list[str],
        services_list: list[list[str]] | None = None,
        rule_categories: list[str] | None = None,
        rule_warning_counts: list[int] | None = None,
    ) -> tuple[list[str], list[float]]:
        del services_list, rule_categories, rule_warning_counts
        self.batch_calls += 1
        short_count = max(len(procedure_texts) - 1, 0)
        return [self.prediction for _ in range(short_count)], [
            self.confidence for _ in procedure_texts
        ]


def test_classify_uses_single_predict_with_confidence():
    predictor = _StubPredictor(
        prediction=ProcedureCategory.CARDIAC_WITHOUT_CPB.value,
        confidence=0.8,
    )
    classifier = HybridClassifier(ml_predictor=predictor, ml_threshold=0.7)

    result = classifier.classify("completely uncategorized procedure", [])

    assert result["category"] == ProcedureCategory.CARDIAC_WITHOUT_CPB
    assert result["method"] == "ml_fill_other"
    assert predictor.single_calls == 1


def test_classify_many_batches_ml_calls():
    predictor = _StubPredictor(
        prediction=ProcedureCategory.CARDIAC_WITHOUT_CPB.value,
        confidence=0.8,
    )
    classifier = HybridClassifier(ml_predictor=predictor, ml_threshold=0.7)

    results = classifier.classify_many(
        [
            "uncategorized procedure one",
            "uncategorized procedure two",
        ],
        [[], []],
    )

    assert [result["category"] for result in results] == [
        ProcedureCategory.CARDIAC_WITHOUT_CPB,
        ProcedureCategory.CARDIAC_WITHOUT_CPB,
    ]
    assert [result["method"] for result in results] == [
        "ml_fill_other",
        "ml_fill_other",
    ]
    assert predictor.batch_calls == 1


def test_classify_many_rejects_mismatched_service_metadata():
    classifier = HybridClassifier(ml_predictor=None)

    with pytest.raises(ValueError, match="services_list must match"):
        classifier.classify_many(["one", "two"], [[]])


def test_classify_many_rejects_mismatched_batch_ml_output_lengths():
    classifier = HybridClassifier(
        ml_predictor=_ShortBatchPredictor(
            prediction=ProcedureCategory.CARDIAC_WITHOUT_CPB.value,
            confidence=0.8,
        ),
        ml_threshold=0.7,
    )

    with pytest.raises(ValueError, match="Batch ML predictor length mismatch"):
        classifier.classify_many(["one", "two"], [[], []])


def test_medium_confidence_warning_names_ml_and_rule_categories():
    classifier = HybridClassifier(
        ml_predictor=_StubPredictor(
            prediction=ProcedureCategory.MAJOR_VESSELS_OPEN.value,
            confidence=0.75,
        ),
        ml_threshold=0.7,
    )

    result = classifier._classify_with_rule_context(
        _RuleContext(
            procedure_text="placeholder procedure",
            services=[],
            category=ProcedureCategory.CARDIAC_WITHOUT_CPB,
            warnings=[],
        ),
        ml_category_str=ProcedureCategory.MAJOR_VESSELS_OPEN.value,
        ml_confidence=0.75,
    )

    assert result["method"] == "ml_preferred"
    assert result["warnings"] == [
        "ML preferred over rules: Procedures on major vessels (open) over "
        "Cardiac without CPB (conf=0.75)"
    ]


def test_ml_rules_agree_preserves_actual_ml_confidence():
    classifier = HybridClassifier(
        ml_predictor=_StubPredictor(
            prediction=ProcedureCategory.CARDIAC_WITHOUT_CPB.value,
            confidence=0.72,
        ),
        ml_threshold=0.7,
    )

    result = classifier._classify_with_rule_context(
        _RuleContext(
            procedure_text="placeholder procedure",
            services=[],
            category=ProcedureCategory.CARDIAC_WITHOUT_CPB,
            warnings=[],
        ),
        ml_category_str=ProcedureCategory.CARDIAC_WITHOUT_CPB.value,
        ml_confidence=0.72,
    )

    assert result["method"] == "ml_rules_agree"
    assert result["confidence"] == pytest.approx(0.72)

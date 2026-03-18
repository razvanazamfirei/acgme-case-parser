"""Feature engineering for ML classification."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any, TypeVar

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer

from ..domain import ProcedureCategory
from ..patterns.categorization import categorize_procedure
from ..patterns.procedure_patterns import (
    BRONCHOSCOPY_FEATURE_KEYWORDS,
    CARDIAC_SERVICE_HINT_KEYWORDS,
    ELECTROPHYSIOLOGY_FEATURE_KEYWORDS,
    NEURAXIAL_FEATURE_KEYWORDS,
    NEURO_SERVICE_HINT_KEYWORDS,
    OBGYN_SERVICE_KEYWORDS,
    THORACIC_FEATURE_KEYWORDS,
    THORACIC_SERVICE_RULE_KEYWORDS,
    VASCULAR_FEATURE_KEYWORDS,
    VASCULAR_SERVICE_HINT_KEYWORDS,
)
from ..types import Scalar
from .inputs import FeatureInput, normalize_feature_inputs

_T = TypeVar("_T")


class FeatureExtractor:
    """Extract features from procedure text for ML classification."""

    _FEATURE_DTYPE = np.float32

    def __init__(self) -> None:
        """Initialize feature extractors."""
        # Word-level TF-IDF
        self.tfidf_word = TfidfVectorizer(
            max_features=800,
            ngram_range=(1, 4),
            min_df=2,
            stop_words=self._get_medical_stopwords(),
            dtype=self._FEATURE_DTYPE,
        )

        # Character-level TF-IDF (for abbreviations)
        self.tfidf_char = TfidfVectorizer(
            analyzer="char",
            max_features=200,
            ngram_range=(3, 5),
            min_df=2,
            dtype=self._FEATURE_DTYPE,
        )
        self._is_fitted = False

    @staticmethod
    def _get_medical_stopwords() -> list[str]:
        """Return medical-specific stopwords for TF-IDF vectorization."""
        return [
            "procedure",
            "patient",
            "performed",
            "underwent",
            "status",
            "post",
            "pre",
        ]

    def fit(
        self,
        procedures: list[str | FeatureInput | Mapping[str, Scalar]],
    ) -> FeatureExtractor:
        """Fit feature extractors on training data."""
        normalized_inputs = normalize_feature_inputs(procedures)
        texts = [self._compose_text(item) for item in normalized_inputs]
        self.tfidf_word.fit(texts)
        self.tfidf_char.fit(texts)
        self._is_fitted = True
        return self

    def transform(
        self,
        procedures: list[str | FeatureInput | Mapping[str, Scalar]],
    ) -> csr_matrix:
        """Transform procedures to feature matrix."""
        if not self._is_fitted:
            raise ValueError("FeatureExtractor must be fitted before transform")

        normalized_inputs = normalize_feature_inputs(procedures)
        texts = [self._compose_text(item) for item in normalized_inputs]

        word_features = self._transform_text_batch(
            self.tfidf_word,
            texts,
        )
        char_features = self._transform_text_batch(
            self.tfidf_char,
            texts,
        )
        structured_features = csr_matrix(
            self._extract_structured_batch(normalized_inputs),
            dtype=self._FEATURE_DTYPE,
        )

        return hstack(
            [word_features, char_features, structured_features],
            format="csr",
        )

    def fit_transform(
        self,
        procedures: list[str | FeatureInput | Mapping[str, Scalar]],
    ) -> csr_matrix:
        """Fit and transform in one step."""
        return self.fit(procedures).transform(procedures)

    def _extract_structured_batch(
        self,
        procedures: list[FeatureInput],
    ) -> np.ndarray[Any, Any]:
        """Extract structured features for a batch of procedures."""
        unique_procedures, inverse_indices = self._dedupe_preserve_order(procedures)
        unique_features = np.array(
            [
                self._extract_structured_single_v2_cached(
                    item.procedure_text,
                    item.service_text,
                    item.rule_category,
                    int(item.rule_warning_count),
                )
                for item in unique_procedures
            ],
            dtype=self._FEATURE_DTYPE,
        )
        return unique_features[inverse_indices]

    @staticmethod
    def _compose_text(item: FeatureInput) -> str:
        """Build the textual view used by TF-IDF models."""
        if item.service_text:
            return f"{item.procedure_text} SERVICES {item.service_text}"
        return item.procedure_text

    @staticmethod
    def _dedupe_preserve_order(
        values: list[_T],
    ) -> tuple[list[_T], np.ndarray[Any, Any]]:
        """Return unique values and inverse indices while keeping first-seen order."""
        unique_values: list[_T] = []
        inverse_indices: list[int] = []
        value_to_index: dict[_T, int] = {}

        for value in values:
            index = value_to_index.get(value)
            if index is None:
                index = len(unique_values)
                value_to_index[value] = index
                unique_values.append(value)
            inverse_indices.append(index)

        return unique_values, np.array(inverse_indices, dtype=int)

    @classmethod
    def _transform_text_batch(
        cls,
        vectorizer: TfidfVectorizer,
        texts: list[str],
    ) -> csr_matrix:
        """Transform text features once per distinct composed text."""
        unique_texts, inverse_indices = cls._dedupe_preserve_order(texts)
        unique_features = vectorizer.transform(unique_texts)
        return unique_features[inverse_indices]

    @staticmethod
    @lru_cache(maxsize=32768)
    def _extract_structured_single_v2_cached(
        procedure_text: str,
        service_text: str,
        rule_category_text: str,
        rule_warning_count: int,
    ) -> tuple[float, ...]:
        """Enhanced structured feature set for newly trained models."""
        proc_upper = procedure_text.upper()
        service_upper = service_text.upper()

        if rule_category_text:
            rule_category = rule_category_text
        else:
            services = [item for item in service_text.split("\n") if item]
            category, warnings = categorize_procedure(procedure_text, services=services)
            rule_category = (
                category.value if category else ProcedureCategory.OTHER.value
            )
            rule_warning_count = len(warnings)
        rule_category_upper = rule_category.upper()

        return (
            float("CPB" in proc_upper or "CARDIOPULMONARY BYPASS" in proc_upper),
            float("CABG" in proc_upper or "CORONARY ARTERY BYPASS" in proc_upper),
            float("TAVR" in proc_upper or "TAVI" in proc_upper),
            float(
                "TRANSCATHETER" in proc_upper
                and any(term in proc_upper for term in ("VALVE", "VALVULOPLASTY"))
            ),
            float(
                any(term in proc_upper for term in ("OFF-PUMP", "OFF PUMP", "OPCAB"))
            ),
            float("ENDOVASCULAR" in proc_upper or "PERCUTANEOUS" in proc_upper),
            float(
                any(
                    term in proc_upper for term in ("OPEN", "CRANIOTOMY", "CRANIECTOMY")
                )
            ),
            float("LAPAROSCOPIC" in proc_upper),
            float("ROBOTIC" in proc_upper),
            float(
                any(
                    term in proc_upper for term in ("CARDIAC", "HEART", "VALVE", "CABG")
                )
            ),
            float(
                any(
                    term in proc_upper
                    for term in ("CRANI", "INTRACRANIAL", "ANEURYSM", "AVM")
                )
            ),
            float(any(term in proc_upper for term in THORACIC_FEATURE_KEYWORDS)),
            float(any(term in proc_upper for term in VASCULAR_FEATURE_KEYWORDS)),
            float(
                "CESAREAN" in proc_upper
                or "C-SECTION" in proc_upper
                or "LABOR" in proc_upper
            ),
            float("ECMO" in proc_upper or "VENTRICULAR ASSIST DEVICE" in proc_upper),
            float(
                any(term in proc_upper for term in ELECTROPHYSIOLOGY_FEATURE_KEYWORDS)
            ),
            float(any(term in proc_upper for term in BRONCHOSCOPY_FEATURE_KEYWORDS)),
            float(any(term in proc_upper for term in NEURAXIAL_FEATURE_KEYWORDS)),
            float(any(term in service_upper for term in CARDIAC_SERVICE_HINT_KEYWORDS)),
            float(any(term in service_upper for term in NEURO_SERVICE_HINT_KEYWORDS)),
            float(
                any(term in service_upper for term in THORACIC_SERVICE_RULE_KEYWORDS)
            ),
            float(
                any(term in service_upper for term in VASCULAR_SERVICE_HINT_KEYWORDS)
            ),
            float(any(term in service_upper for term in OBGYN_SERVICE_KEYWORDS)),
            float(rule_warning_count),
            float(len(procedure_text) // 100),
            float("CARDIAC" in rule_category_upper or "CPB" in rule_category_upper),
            float("INTRACEREBRAL" in rule_category_upper),
            float("MAJOR VESSELS" in rule_category_upper),
            float("INTRATHORACIC" in rule_category_upper),
            float(
                rule_category_upper
                in {
                    ProcedureCategory.CESAREAN.value.upper(),
                    ProcedureCategory.VAGINAL_DELIVERY.value.upper(),
                }
            ),
        )

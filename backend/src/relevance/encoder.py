"""
Pluggable text encoders for the relevance gate.

The shipping encoder (`TfidfDomainEncoder`) is fully offline — it uses scikit-learn
TF-IDF (word + char n-grams) combined with the rule-based domain features. No model
weights are downloaded and nothing touches the network, so it works behind a
corporate firewall.

The `RelevanceEncoder` ABC + `build_encoder` factory leave room to swap in a
vendored offline embedding encoder later, without changing the filter or trainer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

from src.relevance.features import DomainFeatureExtractor


class RelevanceEncoder(ABC):
    """Maps (headline, source) pairs to a feature matrix for the classifier.

    Implementations must be picklable (joblib) and fully offline.
    """

    #: Stable identifier persisted in the artifact metadata for compatibility checks.
    name: str = "base"

    @abstractmethod
    def fit(self, headlines: Sequence[str], sources: Sequence[str]) -> "RelevanceEncoder":
        ...

    @abstractmethod
    def transform(self, headlines: Sequence[str], sources: Sequence[str]):
        """Return a matrix (sparse or dense) of shape (n_samples, n_features)."""

    def fit_transform(self, headlines: Sequence[str], sources: Sequence[str]):
        return self.fit(headlines, sources).transform(headlines, sources)

    @abstractmethod
    def feature_names(self) -> List[str]:
        """Column names aligned with `transform`; used for top-feature explainability."""


class TfidfDomainEncoder(RelevanceEncoder):
    """Word TF-IDF + char TF-IDF + dense domain features, hstacked."""

    name = "tfidf_domain_v1"

    def __init__(
        self,
        supported_currencies: Sequence[str],
        word_ngram_range=(1, 2),
        char_ngram_range=(3, 5),
        max_word_features: int = 20000,
        max_char_features: int = 20000,
        min_df: int = 1,
    ):
        self.supported_currencies = list(supported_currencies or [])
        self.word_ngram_range = tuple(word_ngram_range)
        self.char_ngram_range = tuple(char_ngram_range)
        self.max_word_features = max_word_features
        self.max_char_features = max_char_features
        self.min_df = min_df

        self._word_vec = TfidfVectorizer(
            analyzer="word",
            ngram_range=self.word_ngram_range,
            lowercase=True,
            min_df=self.min_df,
            max_features=self.max_word_features,
        )
        self._char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=self.char_ngram_range,
            lowercase=True,
            min_df=self.min_df,
            max_features=self.max_char_features,
        )
        self._domain = DomainFeatureExtractor(self.supported_currencies)
        self._fitted = False

    def fit(self, headlines: Sequence[str], sources: Sequence[str]) -> "TfidfDomainEncoder":
        texts = [h or "" for h in headlines]
        self._word_vec.fit(texts)
        self._char_vec.fit(texts)
        self._fitted = True
        return self

    def transform(self, headlines: Sequence[str], sources: Sequence[str]):
        if not self._fitted:
            raise RuntimeError("TfidfDomainEncoder.transform called before fit")
        texts = [h or "" for h in headlines]
        srcs = list(sources) if sources is not None else ["unknown"] * len(texts)

        word_block = self._word_vec.transform(texts)
        char_block = self._char_vec.transform(texts)
        domain_block = sp.csr_matrix(self._domain.extract(texts, srcs))
        return sp.hstack([word_block, char_block, domain_block]).tocsr()

    def feature_names(self) -> List[str]:
        if not self._fitted:
            raise RuntimeError("TfidfDomainEncoder.feature_names called before fit")
        word_names = [f"w:{n}" for n in self._word_vec.get_feature_names_out()]
        char_names = [f"c:{n}" for n in self._char_vec.get_feature_names_out()]
        domain_names = list(self._domain.feature_names())
        return word_names + char_names + domain_names


def build_encoder(name: str, supported_currencies: Sequence[str], **kwargs) -> RelevanceEncoder:
    """Factory: select an encoder implementation by name.

    Only `tfidf_domain_v1` ships today. A future offline embedding encoder would
    register here without touching the filter or trainer.
    """
    if name == TfidfDomainEncoder.name:
        return TfidfDomainEncoder(supported_currencies, **kwargs)
    raise ValueError(f"Unknown relevance encoder: {name!r}")

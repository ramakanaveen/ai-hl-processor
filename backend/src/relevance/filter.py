"""
Runtime relevance gate.

`RelevanceFilter` loads a trained joblib artifact once at startup and scores each
headline in O(ms). It is designed to **fail open**: if the artifact is missing,
incompatible, or anything goes wrong, every headline is sent on to the LLM — the
gate never silently swallows news.

Decision policy (tuned for high recall on "relevant"):
    allowlist hit           -> SEND   (hard override; central banks, traded ccys, ...)
    p >= pass_threshold     -> SEND
    p <= drop_threshold     -> DROP
    drop < p < pass         -> SEND   (uncertain -> fail-safe send)

Only confidently-irrelevant headlines (p <= drop_threshold) are ever dropped, and
only when the caller is running in "enforce" mode.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RelevanceDecision:
    decision: str                                  # "SEND" | "DROP"
    prob: float                                    # P(relevant); 1.0 when fail-open
    reason: str                                    # fail_open_no_model | allowlist:<t> |
                                                   #   pass_threshold | drop_zone |
                                                   #   uncertain_failsafe_send
    top_features: List[Tuple[str, float]] = field(default_factory=list)


class RelevanceFilter:
    """Loads a relevance artifact and evaluates headlines against the gate policy."""

    def __init__(self, config):
        # `config` is a RelevanceFilterConfig (duck-typed to avoid an import cycle).
        self.config = config
        self.drop_threshold = float(config.drop_threshold)
        self.pass_threshold = float(config.pass_threshold)
        self._allowlist = [t.strip().lower() for t in (config.allowlist_terms or []) if t.strip()]

        self._loaded = False
        self._encoder = None
        self._classifier = None
        self._linear_coef = None          # np.ndarray for top-feature explanations
        self._feature_names: Optional[List[str]] = None
        self.metadata: dict = {}

        self._load(config.model_path, config.encoder)

    # ------------------------------------------------------------------ load
    def _load(self, model_path: str, expected_encoder: str) -> None:
        try:
            import joblib  # ships with scikit-learn
        except ImportError:
            logger.warning("relevance: scikit-learn/joblib unavailable — filter fail-open")
            return

        import os
        from pathlib import Path

        # Resolve a relative model_path against the backend root so the gate works
        # regardless of the process's working directory.
        resolved = model_path
        if model_path and not os.path.isabs(model_path) and not os.path.exists(model_path):
            backend_root = Path(__file__).resolve().parents[2]
            alt = backend_root / model_path
            if alt.exists():
                resolved = str(alt)

        if not resolved or not os.path.exists(resolved):
            logger.warning(
                "relevance: no model artifact at %s — filter fail-open (passes everything)",
                model_path,
            )
            return
        model_path = resolved

        try:
            bundle = joblib.load(model_path)
            encoder = bundle["encoder"]
            classifier = bundle["classifier"]
            metadata = bundle.get("metadata", {})
        except Exception as e:  # noqa: BLE001 — never let a bad artifact break the pipeline
            logger.warning("relevance: failed to load artifact %s (%s) — fail-open", model_path, e)
            return

        # Encoder compatibility: refuse a silently mismatched artifact.
        encoder_name = getattr(encoder, "name", None)
        if expected_encoder and encoder_name != expected_encoder:
            logger.warning(
                "relevance: artifact encoder %r != configured %r — fail-open",
                encoder_name, expected_encoder,
            )
            return

        # sklearn version skew is only a warning — pickles are version-sensitive.
        try:
            import sklearn
            trained_version = metadata.get("sklearn_version")
            if trained_version and trained_version != sklearn.__version__:
                logger.warning(
                    "relevance: artifact trained on sklearn %s, runtime is %s — "
                    "scores may differ", trained_version, sklearn.__version__,
                )
        except Exception:  # noqa: BLE001
            pass

        self._encoder = encoder
        self._classifier = classifier
        self._linear_coef = bundle.get("linear_coef")
        self._feature_names = bundle.get("feature_names")
        self.metadata = metadata
        # Prefer thresholds chosen at training time, if present.
        self.drop_threshold = float(metadata.get("drop_threshold", self.drop_threshold))
        self.pass_threshold = float(metadata.get("pass_threshold", self.pass_threshold))
        self._loaded = True
        logger.info(
            "relevance: loaded model %s (drop<=%.3f, pass>=%.3f, trained %s)",
            model_path, self.drop_threshold, self.pass_threshold,
            metadata.get("train_date", "?"),
        )

    @property
    def loaded(self) -> bool:
        return self._loaded

    # -------------------------------------------------------------- evaluate
    def _allowlist_hit(self, headline_lower: str) -> Optional[str]:
        for term in self._allowlist:
            if re.search(rf"\b{re.escape(term)}\b", headline_lower):
                return term
        return None

    def _top_features(self, row, k: int = 5) -> List[Tuple[str, float]]:
        """Top signed feature contributions (coef * value) toward relevance."""
        if self._linear_coef is None or self._feature_names is None:
            return []
        try:
            import numpy as np
            coef = np.asarray(self._linear_coef).ravel()
            dense = np.asarray(row.todense()).ravel() if hasattr(row, "todense") else np.asarray(row).ravel()
            contrib = coef * dense
            idx = np.argsort(np.abs(contrib))[::-1][:k]
            return [(self._feature_names[i], round(float(contrib[i]), 4))
                    for i in idx if contrib[i] != 0.0]
        except Exception:  # noqa: BLE001 — explainability must never break scoring
            return []

    def evaluate(self, headline: str, source: str = "unknown") -> RelevanceDecision:
        if not self._loaded:
            return RelevanceDecision("SEND", 1.0, "fail_open_no_model")

        headline = headline or ""
        hit = self._allowlist_hit(headline.lower())
        if hit is not None:
            return RelevanceDecision("SEND", 1.0, f"allowlist:{hit}")

        try:
            row = self._encoder.transform([headline], [source or "unknown"])
            prob = float(self._classifier.predict_proba(row)[0][1])
        except Exception as e:  # noqa: BLE001 — scoring failure => fail open
            logger.warning("relevance: scoring failed (%s) — fail-open for this headline", e)
            return RelevanceDecision("SEND", 1.0, "fail_open_scoring_error")

        if prob >= self.pass_threshold:
            return RelevanceDecision("SEND", prob, "pass_threshold")
        if prob <= self.drop_threshold:
            return RelevanceDecision("DROP", prob, "drop_zone", self._top_features(row))
        return RelevanceDecision("SEND", prob, "uncertain_failsafe_send")

    @staticmethod
    def should_drop(decision: RelevanceDecision, mode: str) -> bool:
        """A headline is only actually dropped on DROP *and* enforce mode."""
        return decision.decision == "DROP" and mode == "enforce"

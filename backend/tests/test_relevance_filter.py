from types import SimpleNamespace

import joblib
import numpy as np
import sklearn

from src.relevance.encoder import TfidfDomainEncoder
from src.relevance.filter import RelevanceFilter, RelevanceDecision

CURRENCIES = ["EURUSD", "GBPUSD", "USDJPY"]


class _FakeClassifier:
    """Module-level so joblib can pickle it; returns a fixed P(relevant)."""

    def __init__(self, prob):
        self.prob = prob

    def predict_proba(self, X):
        n = X.shape[0]
        return np.tile([1.0 - self.prob, self.prob], (n, 1))


def _make_config(model_path, drop=0.05, pass_=0.5, allowlist=None):
    return SimpleNamespace(
        model_path=str(model_path),
        encoder="tfidf_domain_v1",
        drop_threshold=drop,
        pass_threshold=pass_,
        allowlist_terms=allowlist if allowlist is not None else ["ecb", "fed"],
        min_training_samples=0,
    )


def _build_artifact(tmp_path, prob):
    enc = TfidfDomainEncoder(CURRENCIES).fit(
        ["Fed raises rates", "Celebrity wins award", "ECB tightens policy"],
        ["unknown", "unknown", "unknown"],
    )
    feature_names = enc.feature_names()
    bundle = {
        "encoder": enc,
        "classifier": _FakeClassifier(prob),
        "linear_coef": np.zeros(len(feature_names)),
        "feature_names": feature_names,
        "metadata": {
            "encoder_name": "tfidf_domain_v1",
            "sklearn_version": sklearn.__version__,
            "drop_threshold": 0.05,
            "pass_threshold": 0.5,
            "train_date": "2026-06-14",
        },
    }
    path = tmp_path / "model.joblib"
    joblib.dump(bundle, path)
    return path


def test_fail_open_when_no_artifact(tmp_path):
    cfg = _make_config(tmp_path / "missing.joblib")
    rf = RelevanceFilter(cfg)
    assert rf.loaded is False
    decision = rf.evaluate("anything at all")
    assert decision.decision == "SEND"
    assert decision.prob == 1.0
    assert decision.reason == "fail_open_no_model"


def test_pass_zone(tmp_path):
    path = _build_artifact(tmp_path, prob=0.9)
    rf = RelevanceFilter(_make_config(path))
    d = rf.evaluate("Some clearly relevant macro headline", "Reuters")
    assert d.decision == "SEND"
    assert d.reason == "pass_threshold"


def test_drop_zone(tmp_path):
    path = _build_artifact(tmp_path, prob=0.01)
    rf = RelevanceFilter(_make_config(path))
    d = rf.evaluate("totally unrelated celebrity gossip", "unknown")
    assert d.decision == "DROP"
    assert d.reason == "drop_zone"


def test_uncertain_failsafe_send(tmp_path):
    path = _build_artifact(tmp_path, prob=0.3)
    rf = RelevanceFilter(_make_config(path))
    d = rf.evaluate("ambiguous middling headline", "unknown")
    assert d.decision == "SEND"
    assert d.reason == "uncertain_failsafe_send"


def test_allowlist_overrides_low_score(tmp_path):
    path = _build_artifact(tmp_path, prob=0.01)  # would otherwise DROP
    rf = RelevanceFilter(_make_config(path, allowlist=["ecb"]))
    d = rf.evaluate("ECB does something the model misjudges")
    assert d.decision == "SEND"
    assert d.reason == "allowlist:ecb"


def test_should_drop_only_on_enforce():
    drop = RelevanceDecision("DROP", 0.01, "drop_zone")
    send = RelevanceDecision("SEND", 0.9, "pass_threshold")
    assert RelevanceFilter.should_drop(drop, "enforce") is True
    assert RelevanceFilter.should_drop(drop, "shadow") is False
    assert RelevanceFilter.should_drop(send, "enforce") is False


def test_encoder_mismatch_fails_open(tmp_path):
    path = _build_artifact(tmp_path, prob=0.9)
    cfg = _make_config(path)
    cfg.encoder = "some_other_encoder"
    rf = RelevanceFilter(cfg)
    assert rf.loaded is False
    assert rf.evaluate("x").reason == "fail_open_no_model"

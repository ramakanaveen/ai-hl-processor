import os
from datetime import datetime
from types import SimpleNamespace

from src.core.models import ImpactAnalysisResult, CurrencyImpact
from src.memory.file_store import FileSystemMemory
from src.relevance.train import train_relevance_model
from src.relevance.filter import RelevanceFilter

CURRENCIES = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

RELEVANT = [
    "Fed raises interest rates by {n} basis points",
    "ECB signals tightening as inflation hits {n}%",
    "Bank of Japan intervenes to support the yen at {n}",
    "Bank of England holds rates amid {n}% inflation",
    "USD surges {n}% after hawkish Powell remarks",
]
IRRELEVANT = [
    "Celebrity chef opens new restaurant number {n}",
    "Local football team wins match {n} nil",
    "New superhero movie breaks box office record {n}",
    "Gardening tips for the {n}th week of spring",
    "Famous singer announces world tour stop {n}",
]


def _seed(store, templates, entities, count):
    for i in range(count):
        tmpl = templates[i % len(templates)]
        headline = tmpl.format(n=i + 1)
        store.store_analysis(ImpactAnalysisResult(
            headline=headline,
            timestamp=datetime.utcnow(),
            impacted_entities=[CurrencyImpact(**e) for e in entities],
            processing_time_ms=1.0,
            model_used="test",
        ))


def _filter_config(model_path):
    return SimpleNamespace(
        model_path=str(model_path),
        encoder="tfidf_domain_v1",
        drop_threshold=0.05,
        pass_threshold=0.5,
        allowlist_terms=[],
        min_training_samples=0,
    )


def test_train_load_score_end_to_end(tmp_path):
    store = FileSystemMemory(base_path=str(tmp_path / "mem"))
    _seed(store, RELEVANT, [{"currency": "USD", "confidence": 0.9, "reasoning": "macro fx impact"}], 40)
    _seed(store, IRRELEVANT, [], 80)

    out_dir = tmp_path / "model"
    result = train_relevance_model(
        memory=store,
        supported_currencies=CURRENCIES,
        confidence_threshold=0.7,
        out_dir=str(out_dir),
        min_training_samples=20,
    )

    assert result.trained is True
    assert os.path.exists(result.artifact_path)
    assert os.path.exists(result.metadata_path)
    m = result.metrics
    assert m["sklearn_version"]
    assert m["train_date"]
    assert "drop_threshold" in m and "pass_threshold" in m
    assert m["pct_dropped"] > 0.0

    rf = RelevanceFilter(_filter_config(result.artifact_path))
    assert rf.loaded is True

    # A clearly relevant headline is sent on.
    rel = rf.evaluate("Fed raises interest rates by 50 basis points", "Reuters")
    assert rel.decision == "SEND"
    assert rel.prob > 0.5

    # At least one clearly-irrelevant training headline is dropped.
    drops = [rf.evaluate(t.format(n=99)).decision for t in IRRELEVANT]
    assert "DROP" in drops


def test_too_few_samples_guard_writes_no_artifact(tmp_path):
    store = FileSystemMemory(base_path=str(tmp_path / "mem"))
    _seed(store, RELEVANT, [{"currency": "USD", "confidence": 0.9, "reasoning": "macro fx impact"}], 3)
    _seed(store, IRRELEVANT, [], 2)

    out_dir = tmp_path / "model"
    result = train_relevance_model(
        memory=store,
        supported_currencies=CURRENCIES,
        out_dir=str(out_dir),
        min_training_samples=20,
    )

    assert result.trained is False
    assert "insufficient_data" in result.reason
    assert not os.path.exists(out_dir / "model.joblib")

    # Runtime stays fail-open against the (absent) artifact.
    rf = RelevanceFilter(_filter_config(out_dir / "model.joblib"))
    assert rf.loaded is False
    assert rf.evaluate("anything").decision == "SEND"

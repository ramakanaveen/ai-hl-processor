from datetime import datetime

from src.core.models import ImpactAnalysisResult, CurrencyImpact
from src.memory.file_store import FileSystemMemory
from src.relevance.labels import build_labeled_dataset


def _result(headline, entities, model_used="test", error=None):
    return ImpactAnalysisResult(
        headline=headline,
        timestamp=datetime.utcnow(),
        impacted_entities=[CurrencyImpact(**e) for e in entities],
        processing_time_ms=1.0,
        model_used=model_used,
        error=error,
    )


def _store(tmp_path):
    return FileSystemMemory(base_path=str(tmp_path / "mem"))


def test_relevant_and_not_relevant_labels(tmp_path):
    store = _store(tmp_path)
    store.store_analysis(_result(
        "Fed raises rates", [{"currency": "USD", "confidence": 0.9, "reasoning": "rate hike usd"}]
    ))
    store.store_analysis(_result("Celebrity wins award", []))

    rows, stats = build_labeled_dataset(store, confidence_threshold=0.7)

    labels = {r.headline: r.label for r in rows}
    assert labels["Fed raises rates"] == 1
    assert labels["Celebrity wins award"] == 0
    assert stats.relevant == 1
    assert stats.not_relevant == 1


def test_error_rows_skipped(tmp_path):
    store = _store(tmp_path)
    store.store_analysis(_result("Broken headline", [], model_used="error", error="boom"))
    rows, stats = build_labeled_dataset(store)
    assert rows == []
    assert stats.skipped_error == 1


def test_ambiguous_skipped_by_default_or_forced(tmp_path):
    store = _store(tmp_path)
    store.store_analysis(_result(
        "Mildly relevant", [{"currency": "EUR", "confidence": 0.4, "reasoning": "weak signal eur"}]
    ))

    rows, stats = build_labeled_dataset(store, confidence_threshold=0.7)
    assert rows == []
    assert stats.skipped_ambiguous == 1

    rows2, _ = build_labeled_dataset(store, confidence_threshold=0.7, include_ambiguous_as=0)
    assert len(rows2) == 1
    assert rows2[0].label == 0


def test_correction_overrides_analysis(tmp_path):
    store = _store(tmp_path)
    # Analysis says relevant...
    store.store_analysis(_result(
        "Fed raises rates", [{"currency": "USD", "confidence": 0.9, "reasoning": "usd up rate"}]
    ))
    # ...but a human correction flips it to not-relevant (empty corrected entities).
    store.store_correction(
        headline="Fed raises rates",
        original_entities=[{"currency": "USD", "confidence": 0.9, "reasoning": "usd up rate"}],
        corrected_entities=[],
        note="not actually market-moving",
        corrected_by="reviewer",
    )

    rows, stats = build_labeled_dataset(store, confidence_threshold=0.7)
    assert len(rows) == 1
    assert rows[0].label == 0
    assert rows[0].origin == "correction"
    assert stats.correction_overrides == 1


def test_correction_for_unseen_headline_augments(tmp_path):
    store = _store(tmp_path)
    store.store_correction(
        headline="Surprise BoJ intervention",
        original_entities=[],
        corrected_entities=[{"currency": "JPY", "confidence": 0.95, "reasoning": "boj fx intervention jpy"}],
        corrected_by="reviewer",
    )
    rows, _ = build_labeled_dataset(store)
    assert len(rows) == 1
    assert rows[0].label == 1
    assert rows[0].origin == "correction"


def test_empty_store(tmp_path):
    store = _store(tmp_path)
    rows, stats = build_labeled_dataset(store)
    assert rows == []
    assert stats.total_files == 0

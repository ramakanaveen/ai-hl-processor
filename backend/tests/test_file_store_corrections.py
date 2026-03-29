from datetime import datetime

from src.core.models import ImpactAnalysisResult, CurrencyImpact
from src.memory.file_store import FileSystemMemory


def _make_result(headline: str, currency: str) -> ImpactAnalysisResult:
    return ImpactAnalysisResult(
        headline=headline,
        timestamp=datetime.utcnow(),
        impacted_entities=[
            CurrencyImpact(
                currency=currency,
                confidence=0.8,
                reasoning=f"test impact on {currency}",
            )
        ],
        processing_time_ms=12.0,
        model_used="test",
    )


def test_apply_correction_rewrites_canonical_analysis(tmp_path):
    store = FileSystemMemory(base_path=str(tmp_path / "memory"))
    store.store_analysis(_make_result("Fed raises rates", "USD"))

    updated = store.apply_correction(
        headline="Fed raises rates",
        corrected_entities=[
            {
                "currency": "EUR",
                "confidence": 0.91,
                "reasoning": "Corrected analyst judgment for EUR sensitivity",
            }
        ],
        note="Manual review",
        corrected_by="reviewer",
    )

    assert len(updated) == 1
    result = updated[0]
    assert result.is_corrected is True
    assert result.corrected_by == "reviewer"
    assert result.correction_note == "Manual review"
    assert result.last_modified_at is not None
    assert result.impacted_entities[0].currency.value == "EUR"

    similar = store.search_similar_headlines("Fed raises rates", limit=1, similarity_threshold=0.2)
    assert len(similar) == 1
    assert similar[0].impacted_entities[0].currency.value == "EUR"

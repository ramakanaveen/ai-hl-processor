from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.server.server import _process_message
from src.relevance.filter import RelevanceDecision


def _msg(text, source="unknown"):
    return SimpleNamespace(value={"data": {"text": text, "source": source}})


def _analyzer():
    result = MagicMock()
    result.model_dump.return_value = {"headline": "x", "impacted_entities": []}
    analyzer = MagicMock()
    analyzer.analyze_headline = AsyncMock(return_value=result)
    return analyzer


def _filter(decision):
    return SimpleNamespace(loaded=True, evaluate=lambda h, s="unknown": decision)


def _sent_types(producer):
    return [call.args[1]["type"] for call in producer.send.await_args_list]


@pytest.mark.asyncio
async def test_shadow_drop_still_analyzes_and_emits():
    analyzer = _analyzer()
    producer = MagicMock()
    producer.send = AsyncMock()
    rf = _filter(RelevanceDecision("DROP", 0.01, "drop_zone"))

    action = await _process_message(
        _msg("noise"), analyzer, producer, "out", rf, "shadow"
    )

    assert action == "filtered_shadow"
    analyzer.analyze_headline.assert_awaited_once()
    types = _sent_types(producer)
    assert "relevance_filtered" in types
    assert "analysis_result" in types


@pytest.mark.asyncio
async def test_enforce_drop_skips_analysis():
    analyzer = _analyzer()
    producer = MagicMock()
    producer.send = AsyncMock()
    rf = _filter(RelevanceDecision("DROP", 0.01, "drop_zone"))

    action = await _process_message(
        _msg("noise"), analyzer, producer, "out", rf, "enforce"
    )

    assert action == "filtered_enforce"
    analyzer.analyze_headline.assert_not_awaited()
    types = _sent_types(producer)
    assert types == ["relevance_filtered"]
    # The emitted event marks itself enforced.
    event = producer.send.await_args_list[0].args[1]
    assert event["data"]["enforced"] is True


@pytest.mark.asyncio
async def test_send_decision_runs_normal_path():
    analyzer = _analyzer()
    producer = MagicMock()
    producer.send = AsyncMock()
    rf = _filter(RelevanceDecision("SEND", 0.9, "pass_threshold"))

    action = await _process_message(
        _msg("Fed raises rates"), analyzer, producer, "out", rf, "shadow"
    )

    assert action == "analyzed"
    analyzer.analyze_headline.assert_awaited_once()
    assert _sent_types(producer) == ["analysis_result"]


@pytest.mark.asyncio
async def test_no_filter_is_passthrough():
    analyzer = _analyzer()
    producer = MagicMock()
    producer.send = AsyncMock()

    action = await _process_message(
        _msg("Fed raises rates"), analyzer, producer, "out", None, "off"
    )

    assert action == "analyzed"
    analyzer.analyze_headline.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_headline_skipped():
    analyzer = _analyzer()
    producer = MagicMock()
    producer.send = AsyncMock()

    action = await _process_message(
        _msg("   "), analyzer, producer, "out", None, "off"
    )

    assert action == "empty"
    analyzer.analyze_headline.assert_not_awaited()
    producer.send.assert_not_awaited()

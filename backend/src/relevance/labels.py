"""
Label distillation for the relevance gate.

Training labels are derived from the LLM's own past judgments stored in
`FileSystemMemory`, so no manual labeling is needed:

    relevant (1)     — a stored analysis has >=1 impacted currency with
                       confidence >= confidence_threshold
    not-relevant (0) — empty impacted_entities and no error
    ambiguous        — non-empty entities but all below threshold; excluded by
                       default (configurable via include_ambiguous_as)
    skipped          — rows whose analysis errored (model_used == "error")

User corrections are treated as ground truth: a correction overrides (or augments)
the analysis-derived label for the same headline.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.memory.file_store import FileSystemMemory

logger = logging.getLogger(__name__)


@dataclass
class LabeledRow:
    headline: str
    source: str          # always "unknown" from stored analyses today
    label: int           # 1 relevant, 0 not-relevant
    origin: str          # "analysis" | "correction"


@dataclass
class LabelBuildStats:
    total_files: int = 0
    relevant: int = 0
    not_relevant: int = 0
    skipped_error: int = 0
    skipped_ambiguous: int = 0
    skipped_corrupt: int = 0
    correction_overrides: int = 0


def _label_from_entities(
    entities: list,
    confidence_threshold: float,
    include_ambiguous_as: Optional[int],
) -> Optional[int]:
    """Map an impacted_entities list to a label, or None if it should be skipped.

    Returns 1 / 0, or include_ambiguous_as for the non-empty-but-low-confidence case
    (None there means "skip as ambiguous").
    """
    if entities:
        try:
            max_conf = max(float(e.get("confidence", 0.0)) for e in entities)
        except (TypeError, ValueError):
            max_conf = 0.0
        if max_conf >= confidence_threshold:
            return 1
        # Non-empty but low confidence — ambiguous.
        return include_ambiguous_as
    # Empty entities -> not relevant.
    return 0


def build_labeled_dataset(
    memory: FileSystemMemory,
    confidence_threshold: float = 0.7,
    include_ambiguous_as: Optional[int] = None,
) -> Tuple[List[LabeledRow], LabelBuildStats]:
    """Build (headline, label) rows from stored analyses + corrections.

    De-duplicates by normalized headline, keeping corrections over analyses, so the
    same headline never leaks across cross-validation folds.
    """
    stats = LabelBuildStats()
    # Keyed by normalized headline so corrections can override analyses.
    rows_by_key: Dict[str, LabeledRow] = {}

    # 1. Analyses ------------------------------------------------------------
    for filepath in sorted(memory.analyses_path.glob("*.json")):
        stats.total_files += 1
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            stats.skipped_corrupt += 1
            continue

        if data.get("model_used") == "error" or data.get("error"):
            stats.skipped_error += 1
            continue

        headline = (data.get("headline") or "").strip()
        if not headline:
            continue

        label = _label_from_entities(
            data.get("impacted_entities", []), confidence_threshold, include_ambiguous_as
        )
        if label is None:
            stats.skipped_ambiguous += 1
            continue

        key = memory._normalize_headline(headline)
        rows_by_key[key] = LabeledRow(
            headline=headline, source="unknown", label=label, origin="analysis"
        )

    # 2. Corrections (ground truth — override / augment) ---------------------
    for filepath in sorted(memory.corrections_path.glob("*.json")):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            stats.skipped_corrupt += 1
            continue

        headline = (data.get("headline") or "").strip()
        if not headline:
            continue

        corrected = data.get("corrected_entities", [])
        # A correction is always a definite signal: relevant if any corrected
        # entity clears the threshold, otherwise not-relevant (empty / low).
        label = _label_from_entities(corrected, confidence_threshold, include_ambiguous_as=0)
        if label is None:
            label = 0

        key = memory._normalize_headline(headline)
        if key in rows_by_key and rows_by_key[key].origin == "analysis":
            stats.correction_overrides += 1
        rows_by_key[key] = LabeledRow(
            headline=headline, source="unknown", label=label, origin="correction"
        )

    rows = list(rows_by_key.values())
    stats.relevant = sum(1 for r in rows if r.label == 1)
    stats.not_relevant = sum(1 for r in rows if r.label == 0)

    logger.info(
        "Built relevance dataset: %d rows (%d relevant / %d not-relevant), "
        "skipped %d error / %d ambiguous / %d corrupt, %d correction overrides",
        len(rows), stats.relevant, stats.not_relevant,
        stats.skipped_error, stats.skipped_ambiguous, stats.skipped_corrupt,
        stats.correction_overrides,
    )
    return rows, stats

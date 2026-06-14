"""
Train the relevance gate from distilled labels in FileSystemMemory.

Produces a joblib artifact (encoder + calibrated classifier + linear coefficients
for explainability) and a human-readable metadata.json with counts, metrics, and
the chosen thresholds.

The trainer is conservative by design:
  * it refuses to train on too little data (keeping the runtime fail-open), and
  * it picks `drop_threshold` so that the *precision of dropping* clears a high
    floor (default 0.98) — i.e. very few truly-relevant headlines get dropped.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

import numpy as np

from src.memory.file_store import FileSystemMemory
from src.relevance.encoder import build_encoder
from src.relevance.labels import build_labeled_dataset

logger = logging.getLogger(__name__)

# A class needs at least this many samples for stratified CV to be meaningful.
_MIN_PER_CLASS = 8


@dataclass
class TrainResult:
    trained: bool
    reason: str
    artifact_path: Optional[str] = None
    metadata_path: Optional[str] = None
    metrics: dict = field(default_factory=dict)


def _select_drop_threshold(
    y: np.ndarray,
    oof_prob: np.ndarray,
    precision_floor: float,
    pass_threshold: float,
):
    """Largest p such that, among items with prob <= p, precision-on-drop >= floor.

    Returns (drop_threshold, precision_on_drop, recall_on_drop, floor_met).
    """
    n_neg = int((y == 0).sum())
    best_t = None
    best_prec = 0.0
    best_recall = 0.0

    # Candidate cut points: the observed probabilities strictly below pass_threshold.
    candidates = sorted({round(float(p), 6) for p in oof_prob if p < pass_threshold})
    for t in candidates:
        mask = oof_prob <= t
        n_drop = int(mask.sum())
        if n_drop == 0:
            continue
        precision = float((y[mask] == 0).sum()) / n_drop
        if precision >= precision_floor:
            recall = (float((y[mask] == 0).sum()) / n_neg) if n_neg else 0.0
            # Prefer the largest threshold meeting the floor (drops the most).
            best_t, best_prec, best_recall = t, precision, recall

    if best_t is None:
        return 0.05, 0.0, 0.0, False
    return best_t, best_prec, best_recall, True


def train_relevance_model(
    memory: FileSystemMemory,
    supported_currencies: List[str],
    confidence_threshold: float = 0.7,
    encoder_name: str = "tfidf_domain_v1",
    out_dir: str = "backend/models/relevance",
    min_training_samples: int = 60,
    drop_precision_floor: float = 0.98,
    pass_threshold: float = 0.5,
    random_state: int = 42,
    include_ambiguous_as: Optional[int] = None,
) -> TrainResult:
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    rows, stats = build_labeled_dataset(
        memory, confidence_threshold, include_ambiguous_as=include_ambiguous_as
    )

    n_total = len(rows)
    n_pos = sum(1 for r in rows if r.label == 1)
    n_neg = n_total - n_pos
    min_class = min(n_pos, n_neg)

    # --- Guard: refuse to train on too little / too imbalanced data ---------
    if n_total < min_training_samples or min_class < _MIN_PER_CLASS:
        reason = (
            f"insufficient_data (n={n_total}, pos={n_pos}, neg={n_neg}; "
            f"need >= {min_training_samples} total and >= {_MIN_PER_CLASS}/class)"
        )
        logger.warning("relevance training skipped: %s", reason)
        return TrainResult(trained=False, reason=reason, metrics={
            "n_total": n_total, "n_pos": n_pos, "n_neg": n_neg,
        })

    headlines = [r.headline for r in rows]
    sources = [r.source for r in rows]
    y = np.array([r.label for r in rows], dtype=int)

    encoder = build_encoder(encoder_name, supported_currencies)
    X = encoder.fit_transform(headlines, sources)

    def _make_lr():
        return LogisticRegression(
            class_weight="balanced", max_iter=1000, C=1.0, solver="liblinear",
        )

    # --- Honest out-of-fold probabilities for threshold + metrics -----------
    k = min(5, min_class // 5) if min_class >= 10 else min(5, min_class)
    k = max(2, k)
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=random_state)
    oof_prob = cross_val_predict(_make_lr(), X, y, cv=skf, method="predict_proba")[:, 1]

    # --- Final classifier: calibrate when we have enough per-fold positives --
    calibrate = (min_class // k) >= 2 and k >= 2
    if calibrate:
        classifier = CalibratedClassifierCV(estimator=_make_lr(), method="sigmoid", cv=skf)
    else:
        classifier = _make_lr()
    classifier.fit(X, y)

    # Plain LR on all data for interpretable per-feature coefficients.
    coef_lr = _make_lr().fit(X, y)
    linear_coef = coef_lr.coef_.ravel().astype(float)
    feature_names = encoder.feature_names()

    # --- Threshold selection + metrics --------------------------------------
    drop_threshold, drop_prec, drop_recall, floor_met = _select_drop_threshold(
        y, oof_prob, drop_precision_floor, pass_threshold
    )
    pr_auc = float(average_precision_score(y, oof_prob))
    drop_mask = oof_prob <= drop_threshold
    pct_dropped = float(drop_mask.mean())
    # Recall on relevant under the policy (relevant kept unless in the drop zone).
    pos_mask = y == 1
    recall_relevant = (
        float(((oof_prob > drop_threshold) & pos_mask).sum()) / int(pos_mask.sum())
        if pos_mask.sum() else 1.0
    )

    import sklearn
    metadata = {
        "encoder_name": encoder_name,
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "train_date": date.today().isoformat(),
        "confidence_threshold": confidence_threshold,
        "n_total": n_total,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "n_skipped_error": stats.skipped_error,
        "n_skipped_ambiguous": stats.skipped_ambiguous,
        "n_correction_overrides": stats.correction_overrides,
        "calibrated": bool(calibrate),
        "cv_folds": int(k),
        "drop_threshold": float(drop_threshold),
        "pass_threshold": float(pass_threshold),
        "drop_precision": round(drop_prec, 4),
        "drop_recall": round(drop_recall, 4),
        "drop_floor_met": bool(floor_met),
        "pr_auc": round(pr_auc, 4),
        "recall_relevant": round(recall_relevant, 4),
        "pct_dropped": round(pct_dropped, 4),
        "min_training_samples": min_training_samples,
    }
    if not floor_met:
        logger.warning(
            "relevance: no threshold reached precision floor %.2f; using conservative "
            "drop_threshold=%.3f (drop_floor_met=False)", drop_precision_floor, drop_threshold,
        )

    # --- Persist artifact + metadata ----------------------------------------
    import joblib
    os.makedirs(out_dir, exist_ok=True)
    artifact_path = os.path.join(out_dir, "model.joblib")
    metadata_path = os.path.join(out_dir, "metadata.json")

    joblib.dump(
        {
            "encoder": encoder,
            "classifier": classifier,
            "linear_coef": linear_coef,
            "feature_names": feature_names,
            "metadata": metadata,
        },
        artifact_path,
    )
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "relevance model trained: %d rows, PR-AUC=%.3f, drop<=%.3f "
        "(precision=%.3f, %.1f%% dropped, recall-relevant=%.3f)",
        n_total, pr_auc, drop_threshold, drop_prec, 100 * pct_dropped, recall_relevant,
    )
    return TrainResult(
        trained=True, reason="ok",
        artifact_path=artifact_path, metadata_path=metadata_path, metrics=metadata,
    )

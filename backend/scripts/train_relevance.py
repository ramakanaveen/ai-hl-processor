#!/usr/bin/env python3
"""
Train the news relevance gate from stored analyses + corrections.

Usage:
    python3 backend/scripts/train_relevance.py --environment dev \
        --memory-path memory_store --out-dir backend/models/relevance

Exits non-zero when training is skipped (too little data), so CI / cron can detect it.
"""
import argparse
import logging
import os
import sys

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_ROOT)

from src.config.loader import get_config
from src.memory.file_store import FileSystemMemory
from src.relevance.train import train_relevance_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the news relevance gate")
    parser.add_argument("--environment", "-e", default="dev",
                        choices=["test", "dev", "uat", "prod"])
    parser.add_argument("--memory-path", default="memory_store",
                        help="Path to the FileSystemMemory store (holds analyses/ + corrections/)")
    parser.add_argument("--out-dir", default=os.path.join(BACKEND_ROOT, "models", "relevance"),
                        help="Where to write model.joblib + metadata.json")
    parser.add_argument("--min-training-samples", type=int, default=60)
    parser.add_argument("--drop-precision-floor", type=float, default=0.98)
    parser.add_argument("--include-ambiguous-as", type=int, default=None,
                        choices=[0, 1],
                        help="Bucket non-empty/low-confidence rows as 0 or 1 (default: skip)")
    args = parser.parse_args()

    config = get_config(
        environment=args.environment,
        config_file=os.path.join(BACKEND_ROOT, "config.ini"),
    )
    rf_cfg = config.get_relevance_filter_config()
    business = config.business_config

    memory = FileSystemMemory(base_path=args.memory_path)

    result = train_relevance_model(
        memory=memory,
        supported_currencies=business.supported_currencies,
        confidence_threshold=business.confidence_threshold,
        encoder_name=rf_cfg.encoder,
        out_dir=args.out_dir,
        min_training_samples=args.min_training_samples,
        drop_precision_floor=args.drop_precision_floor,
        pass_threshold=rf_cfg.pass_threshold,
        include_ambiguous_as=args.include_ambiguous_as,
    )

    if not result.trained:
        print(f"\nTraining SKIPPED: {result.reason}")
        print(f"  counts: {result.metrics}")
        return 1

    m = result.metrics
    print("\n=== Relevance model trained ===")
    print(f"  artifact:         {result.artifact_path}")
    print(f"  metadata:         {result.metadata_path}")
    print(f"  rows:             {m['n_total']} ({m['n_pos']} relevant / {m['n_neg']} not-relevant)")
    print(f"  skipped:          {m['n_skipped_error']} error / {m['n_skipped_ambiguous']} ambiguous")
    print(f"  calibrated:       {m['calibrated']} (cv folds={m['cv_folds']})")
    print(f"  PR-AUC:           {m['pr_auc']}")
    print(f"  drop_threshold:   {m['drop_threshold']} (floor met: {m['drop_floor_met']})")
    print(f"  precision-on-drop:{m['drop_precision']}  recall-on-drop: {m['drop_recall']}")
    print(f"  recall-on-relevant:{m['recall_relevant']}")
    print(f"  pct dropped:      {100 * m['pct_dropped']:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

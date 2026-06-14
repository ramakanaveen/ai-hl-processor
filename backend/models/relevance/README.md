# Relevance gate model artifacts

This directory holds the trained **news relevance gate** used to drop headlines
that are confidently irrelevant to the bank's traded currencies *before* the
expensive LLM analysis.

The artifacts here are **build outputs and are not committed** (see `.gitignore`),
because a joblib pickle is tied to the exact scikit-learn version that produced it.
Generate them in your own environment instead:

```bash
# From the repo root — trains on memory_store/ (analyses + corrections)
python3 backend/scripts/train_relevance.py --environment dev --memory-path memory_store
```

This writes:

- `model.joblib` — encoder + calibrated classifier + coefficients
- `metadata.json` — counts, metrics (PR-AUC, precision-on-drop, pct dropped),
  chosen thresholds, scikit-learn/numpy versions, and train date

If no `model.joblib` is present, the runtime filter **fails open** — every headline
is sent on to the LLM, so the pipeline keeps working unchanged.

See `RELEVANCE_FILTER_PLAN.md` (repo root) for the full design and rollout plan.

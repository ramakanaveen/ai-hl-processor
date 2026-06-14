# Plan: Pre-LLM News Relevance Filter (ML gate)

## Context

Today **every** headline in the streaming pipeline goes through the expensive path —
`_analyzer_loop` → `analyzer.analyze_headline()` → Gemini Flash via a LangChain agent
(~1.2s + a paid API call each, capped at 300 rpm in prod). On a real news feed most
headlines are noise to an FX desk (sports, celebrity, local news). The bank wants to
**drop confidently-irrelevant news cheaply, before the LLM call**, to cut cost, latency,
and rate-limit pressure.

Approach: a small, fully-offline ML **relevance gate** that distills the LLM's own
judgment. "Relevant" = "the analysis assigned impact to a traded currency with
confidence ≥ 0.7" — so the gate learns to predict *"will the expensive model find this
relevant?"* It ships in **shadow mode** (scores but does not drop) so precision/recall
can be validated on live traffic before enforcement.

### Locked decisions (from user)
- **Model:** TF-IDF (word 1–2 + char 3–5 grams) + engineered domain features →
  calibrated `LogisticRegression`. scikit-learn only, no network, no model-weight
  download. Encoder is pluggable so a vendored offline embedding model could be swapped
  in later — but only TF-IDF ships.
- **Labels:** distilled from `FileSystemMemory` analyses; corrections are ground truth.
- **Rollout:** shadow mode first; flip to `enforce` per-environment via one config line.
- **Deps:** `scikit-learn` + `numpy` are approved (in artifactory).
- **Constraint:** corporate firewall — nothing may fetch packages or weights at runtime.

### Branch
Base all work on **`origin/phase-3_ui_dashboard`** (the backend/frontend split + combined
server + corrections flow live only there, not on `main`). Step 1: recreate the assigned
branch `claude/news-relevance-ml-model-qv6c29` from `origin/phase-3_ui_dashboard`
(it has no unique commits over `main`, so this is a clean re-base). The eventual diff/PR
targets `phase-3_ui_dashboard`.

### Verified data facts
- `memory_store/analyses/` (repo root, NOT under `backend/`) = 183 JSON files.
- Under the 0.7 rule: **51 relevant / 110 not-relevant / 19 ambiguous (non-empty but
  max conf <0.7) / 3 error**. Default: exclude the 19 ambiguous + 3 error from training
  (configurable via `include_ambiguous_as`).
- Stored analyses have **no `source` field**; corrections dir is currently empty. The
  `source` feature is wired but untrained (constant `"unknown"`) until labeled source
  data exists.

## Changes

### 1. New module `backend/src/relevance/`
- `encoder.py` — `RelevanceEncoder` ABC (`fit/transform/feature_names`, picklable,
  offline) + `TfidfDomainEncoder` (name `tfidf_domain_v1`): hstack of word TF-IDF,
  char_wb TF-IDF, and a dense domain-feature block. `build_encoder(name, config)` factory.
- `features.py` — `DomainFeatureExtractor`: gazetteers derived from
  `business.supported_currencies` + central banks / officials / countries. Features:
  currency-hit count, has-central-bank/official/country, has-percent (`%`/`bps`),
  has-number, source-known, length bucket. Pure Python, easily unit-tested.
- `labels.py` — `build_labeled_dataset(memory, confidence_threshold=0.7,
  include_ambiguous_as=None) -> (list[LabeledRow], LabelBuildStats)`. Iterates
  `analyses_path`, applies the relevance rule, skips error rows, then applies
  **corrections override/augment** keyed by normalized headline; de-dups by normalized
  headline (correction > analysis) to avoid CV-fold leakage.
- `filter.py` — `RelevanceFilter(config)`: loads the joblib bundle at init;
  **fail-open** (SEND everything) if artifact missing / encoder-name or sklearn-version
  mismatch. `evaluate(headline, source) -> RelevanceDecision{decision, prob, reason,
  top_features, mode}`. Decision policy: allowlist hard-override → SEND;
  `p>=pass_threshold` SEND; `p<=drop_threshold` DROP; in-between **fail-safe SEND**.
  `top_features` from `coef*value` for audit. Synchronous/CPU-bound (server wraps in
  `asyncio.to_thread`).

### 2. Training `backend/src/relevance/train.py` + CLI `backend/scripts/train_relevance.py`
- `train_relevance_model(...) -> TrainResult`: build labels → guard (skip + write **no
  artifact** if `< min_training_samples` or any class `< 8`, keeping runtime fail-open)
  → fit `TfidfDomainEncoder` + `LogisticRegression(class_weight="balanced",
  solver="liblinear")` → calibrate with `CalibratedClassifierCV(method="sigmoid")`,
  adaptive `k=min(5, min_class//5)`, fall back to uncalibrated if `k<2` (record
  `calibrated` flag).
- **Threshold selection** via `cross_val_predict` OOF probs: pick the largest
  `drop_threshold` with **precision-on-drop ≥ 0.98**; fall back to a fixed 0.05 with a
  loud warning + `drop_floor_met=False` if unattainable. `pass_threshold` stays 0.5.
- Save `backend/models/relevance/model.joblib` (`{encoder, classifier, metadata}`) +
  `metadata.json` (counts, PR-AUC, recall-on-relevant, precision/recall-on-drop,
  pct_dropped, thresholds, encoder_name, sklearn/numpy versions, train_date, flags).
- CLI: `python backend/scripts/train_relevance.py --environment dev
  --memory-path memory_store`; non-zero exit if `trained=False`.

### 3. Config
- `backend/src/config/loader.py`: `RelevanceFilterConfig` dataclass +
  `get_relevance_filter_config()` (mirrors `get_cache_config` / `_get_value` pattern):
  `enabled, mode, model_path, encoder, drop_threshold, pass_threshold, allowlist_terms,
  min_training_samples`.
- `backend/config.ini`: `[relevance_filter]` defaults + per-env overrides —
  `test` disabled (deterministic tests), `dev/uat/prod` **enabled + shadow**. Allowlist =
  central banks + officials + the traded currency codes.

### 4. Server integration
- `backend/services/server/run_server.py`: build
  `relevance_filter = RelevanceFilter(cfg) if cfg.enabled else None`; pass it +
  `relevance_mode` into `create_app(...)`.
- `backend/services/server/server.py`: thread params through `create_app` → `lifespan`
  → `_analyzer_loop`. In the loop, after `headline_text` (also read `source` now) and
  before `analyze_headline`: if filter loaded, `await asyncio.to_thread(evaluate, ...)`.
  On DROP, emit a new **`relevance_filtered`** event (headline, source, prob_relevant,
  reason, mode, enforced, top_features) to the output topic + SSE. **Shadow:** emit but
  still analyze. **Enforce:** emit then `continue` (skip the LLM). Recommended small
  refactor: extract per-message body into `_process_message(...)` for testability.

### 5. Dependencies
Add `scikit-learn>=1.3.0` and `numpy>=1.24.0` to `backend/requirements.txt`.

### 6. Tests (`backend/tests/`, pytest, run from `backend/`, no network)
- `test_relevance_features.py` — domain feature extraction cases.
- `test_relevance_encoder.py` — shape, unseen tokens, joblib round-trip, `name`.
- `test_relevance_labels.py` — label rule, error skip, ambiguous handling, corrections
  override/augment, stats counts.
- `test_relevance_filter.py` — fail-open (no artifact); zone decisions + allowlist
  override using a tiny in-test artifact; `should_drop` only on DROP+enforce.
- `test_relevance_train.py` — synthetic train→load→score; too-few-samples guard writes
  no artifact and stays fail-open.
- `test_relevance_server_integration.py` — `_process_message` with a stub filter:
  shadow still analyzes + emits; enforce skips analyze + emits; SEND → normal path.

## Verification
1. `pytest backend/tests/ -k relevance` (and full suite) — all green, no network.
2. Train on real data: `python backend/scripts/train_relevance.py --environment dev
   --memory-path memory_store` → ~161 usable rows (51/110); inspect
   `backend/models/relevance/metadata.json` for PR-AUC, precision-on-drop (≥0.98 target),
   recall-on-relevant (~1.0 by policy), and **pct_dropped** (the business win).
3. Shadow dry-run: `[relevance_filter:dev] enabled=true, mode=shadow`, run the combined
   server, feed headlines; confirm `relevance_filtered` events appear on
   `headline-impacts` / SSE while `analysis_result` still flows. Compute precision-on-drop
   by joining would-be-drops to their actual `analysis_result`.
4. Audit: each `relevance_filtered` event carries `prob_relevant` + `top_features` (why it
   scored low); wrong drops get corrected via the existing `/api/corrections` flow and are
   picked up on the next retrain.
5. Only after shadow precision-on-drop ≥ 0.98 on real traffic, flip `mode = enforce`
   (prod last) — a one-line config change.

## Notes / out of scope
- **Redis-independent:** the filter needs no Redis — training reads `memory_store/`
  (file system) and the runtime gate is stateless. An empty Redis store is irrelevant to
  this feature, and no Redis decision-cache will be added (avoids coupling).
- **Redis → Couchbase migration is OUT OF SCOPE** — kept as a separate branch off
  `phase-3_ui_dashboard`. This work will not add or deepen Redis usage, so it won't
  collide with that migration.
- The 19 ambiguous rows are excluded from training by default (configurable).
- `source` feature is wired but untrained today (no stored source data).
- Automated retraining cron and a `/api/relevance/shadow` query endpoint are noted as
  follow-ups, not built here.

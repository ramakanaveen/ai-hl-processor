"""
News relevance filter — a cheap, fully-offline ML gate that runs *before* the
expensive LLM analysis and drops headlines that are confidently irrelevant to the
bank's traded currencies.

The gate distills the LLM's own judgment: a headline is "relevant" if past
analysis assigned impact to a traded currency with confidence >= the configured
threshold. See `labels.build_labeled_dataset`.

Public surface:
    RelevanceFilter      — runtime gate loaded by the server (filter.py)
    RelevanceDecision    — per-headline decision (filter.py)
    train_relevance_model — training entry point (train.py)
    build_encoder        — encoder factory (encoder.py)
"""

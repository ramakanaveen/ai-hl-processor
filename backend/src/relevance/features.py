"""
Deterministic engineered domain features for the relevance gate.

These are cheap, rule-based signals derived from the bank's configured currencies
plus small FX gazetteers (central banks, officials, countries). They inject the
"is this about FX / macro policy" signal that bag-of-words TF-IDF alone misses,
and they need no external model or network access.

Kept free of any sklearn dependency so it can be unit-tested in isolation.
"""
from __future__ import annotations

import re
from typing import Dict, List, Sequence

import numpy as np

# Three-letter ISO currency codes the system understands (matches CurrencyCode).
_KNOWN_CCY_CODES = {
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "CNY",
}

# Central banks — abbreviations and a few common long forms (matched on word stems).
_CENTRAL_BANKS = {
    "fed", "federal reserve", "fomc",
    "ecb", "european central bank",
    "boj", "bank of japan",
    "boe", "bank of england",
    "rba", "reserve bank of australia",
    "boc", "bank of canada",
    "snb", "swiss national bank",
    "rbnz", "reserve bank of new zealand",
    "pboc", "people's bank of china",
}

# Policymakers / officials whose names typically move FX.
_OFFICIALS = {
    "powell", "lagarde", "ueda", "bailey", "macklem", "jordan", "orr",
    "yellen", "kuroda", "draghi",
}

# Country / region terms tied to the supported currencies.
_COUNTRY_TERMS = {
    "united states", "u.s.", "us", "america", "american",
    "eurozone", "euro area", "europe", "european",
    "britain", "british", "uk", "u.k.", "england",
    "japan", "japanese",
    "australia", "australian",
    "canada", "canadian",
    "switzerland", "swiss",
    "new zealand",
    "china", "chinese",
}

_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s?%|\bpercent\b|\bbps\b|\bbasis points?\b", re.I)
_NUMBER_RE = re.compile(r"\d")
_WORD_RE = re.compile(r"[a-z0-9']+")


def _gazetteer_hit(text_lower: str, terms) -> bool:
    """True if any gazetteer term appears as a word-boundary substring."""
    for term in terms:
        # Multi-word terms: plain substring is fine. Single tokens: word boundary.
        if " " in term or "." in term:
            if term in text_lower:
                return True
        elif re.search(rf"\b{re.escape(term)}\b", text_lower):
            return True
    return False


class DomainFeatureExtractor:
    """Maps (headline, source) pairs to a small dense block of FX-domain features."""

    #: Stable column order — must match `extract_one` / `extract`.
    FEATURE_NAMES: List[str] = [
        "dom_ccy_hit_count",
        "dom_has_central_bank",
        "dom_has_official",
        "dom_has_country",
        "dom_has_percent",
        "dom_has_number",
        "dom_source_is_known",
        "dom_len_bucket",
    ]

    def __init__(self, supported_currencies: Sequence[str]):
        # Derive the set of single currency codes from configured pairs, e.g.
        # "EURUSD" -> {"EUR", "USD"}; also accept bare codes like "USD".
        codes = set()
        for item in supported_currencies or []:
            token = (item or "").strip().upper()
            if len(token) == 3 and token in _KNOWN_CCY_CODES:
                codes.add(token)
            else:
                # Split a 6-letter pair into two 3-letter codes when both are known.
                for i in range(0, len(token) - 2, 3):
                    code = token[i:i + 3]
                    if code in _KNOWN_CCY_CODES:
                        codes.add(code)
        # Fall back to the full known set if config gave us nothing usable.
        self.currency_codes = codes or set(_KNOWN_CCY_CODES)
        self._ccy_codes_lower = {c.lower() for c in self.currency_codes}

    def feature_names(self) -> List[str]:
        return list(self.FEATURE_NAMES)

    def extract_one(self, headline: str, source: str = "unknown") -> Dict[str, float]:
        text = headline or ""
        text_lower = text.lower()
        tokens = _WORD_RE.findall(text_lower)
        token_set = set(tokens)

        ccy_hits = sum(1 for code in self._ccy_codes_lower if code in token_set)

        # Length bucket: 0..1 over ~[0, 30) tokens, capped.
        len_bucket = min(len(tokens), 30) / 30.0

        src = (source or "").strip().lower()
        source_known = 1.0 if src and src != "unknown" else 0.0

        return {
            "dom_ccy_hit_count": float(ccy_hits),
            "dom_has_central_bank": 1.0 if _gazetteer_hit(text_lower, _CENTRAL_BANKS) else 0.0,
            "dom_has_official": 1.0 if _gazetteer_hit(text_lower, _OFFICIALS) else 0.0,
            "dom_has_country": 1.0 if _gazetteer_hit(text_lower, _COUNTRY_TERMS) else 0.0,
            "dom_has_percent": 1.0 if _PERCENT_RE.search(text) else 0.0,
            "dom_has_number": 1.0 if _NUMBER_RE.search(text) else 0.0,
            "dom_source_is_known": source_known,
            "dom_len_bucket": float(len_bucket),
        }

    def extract(
        self,
        headlines: Sequence[str],
        sources: Sequence[str],
    ) -> np.ndarray:
        """Return a dense matrix of shape (n_samples, len(FEATURE_NAMES))."""
        rows = []
        for headline, source in zip(headlines, sources):
            feats = self.extract_one(headline, source)
            rows.append([feats[name] for name in self.FEATURE_NAMES])
        if not rows:
            return np.empty((0, len(self.FEATURE_NAMES)), dtype=np.float64)
        return np.asarray(rows, dtype=np.float64)

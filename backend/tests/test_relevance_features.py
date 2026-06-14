from src.relevance.features import DomainFeatureExtractor

CURRENCIES = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]


def _f(headline, source="unknown"):
    return DomainFeatureExtractor(CURRENCIES).extract_one(headline, source)


def test_currency_hit_count():
    feats = _f("EUR and USD slide as traders react")
    # "eur" and "usd" both present as tokens.
    assert feats["dom_ccy_hit_count"] == 2.0


def test_central_bank_and_official_and_country():
    feats = _f("Fed's Powell signals US rate path")
    assert feats["dom_has_central_bank"] == 1.0
    assert feats["dom_has_official"] == 1.0
    assert feats["dom_has_country"] == 1.0


def test_percent_and_number():
    assert _f("ECB hikes by 25 bps")["dom_has_percent"] == 1.0
    assert _f("Inflation rises 3.5%")["dom_has_percent"] == 1.0
    assert _f("Rate held at 50 basis points")["dom_has_percent"] == 1.0
    assert _f("No movement expected")["dom_has_percent"] == 0.0
    assert _f("Rate held at 5 level")["dom_has_number"] == 1.0
    assert _f("Markets calm today")["dom_has_number"] == 0.0


def test_source_known():
    assert _f("anything", source="Reuters")["dom_source_is_known"] == 1.0
    assert _f("anything", source="unknown")["dom_source_is_known"] == 0.0
    assert _f("anything", source="")["dom_source_is_known"] == 0.0


def test_empty_headline_is_safe():
    feats = _f("")
    assert feats["dom_ccy_hit_count"] == 0.0
    assert feats["dom_len_bucket"] == 0.0


def test_feature_names_match_vector_width():
    extractor = DomainFeatureExtractor(CURRENCIES)
    names = extractor.feature_names()
    matrix = extractor.extract(["Fed raises rates", "Celebrity wins award"], ["unknown", "unknown"])
    assert matrix.shape == (2, len(names))


def test_unknown_currency_config_falls_back():
    # Garbage config should not crash and should still detect known codes.
    extractor = DomainFeatureExtractor(["XXXYYY", "notacode"])
    feats = extractor.extract_one("USD jumps")
    assert feats["dom_ccy_hit_count"] >= 1.0

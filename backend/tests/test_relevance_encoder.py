import joblib

from src.relevance.encoder import TfidfDomainEncoder, build_encoder

CURRENCIES = ["EURUSD", "GBPUSD", "USDJPY"]

HEADLINES = [
    "Fed raises rates by 75bps",
    "ECB signals further tightening",
    "Celebrity wins lifetime award",
    "Local team wins the cup final",
]
SOURCES = ["Reuters", "FT", "unknown", "unknown"]


def test_fit_transform_shape_matches_feature_names():
    enc = TfidfDomainEncoder(CURRENCIES)
    X = enc.fit_transform(HEADLINES, SOURCES)
    assert X.shape[0] == len(HEADLINES)
    assert X.shape[1] == len(enc.feature_names())


def test_transform_handles_unseen_tokens_and_sources():
    enc = TfidfDomainEncoder(CURRENCIES).fit(HEADLINES, SOURCES)
    X = enc.transform(["A brand new never-seen headline xyzzy"], ["BrandNewSource"])
    assert X.shape == (1, len(enc.feature_names()))


def test_encoder_name():
    assert TfidfDomainEncoder(CURRENCIES).name == "tfidf_domain_v1"
    assert build_encoder("tfidf_domain_v1", CURRENCIES).name == "tfidf_domain_v1"


def test_build_encoder_rejects_unknown():
    try:
        build_encoder("does_not_exist", CURRENCIES)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_joblib_roundtrip_reproduces_matrix(tmp_path):
    enc = TfidfDomainEncoder(CURRENCIES).fit(HEADLINES, SOURCES)
    before = enc.transform(HEADLINES, SOURCES).todense()

    path = tmp_path / "enc.joblib"
    joblib.dump(enc, path)
    loaded = joblib.load(path)
    after = loaded.transform(HEADLINES, SOURCES).todense()

    assert (before == after).all()

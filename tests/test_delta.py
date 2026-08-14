from edgar_sentinel.pipeline.delta import compute_delta
from edgar_sentinel.schemas import FilingAnalysis, KeyMetrics, PillarScore
from edgar_sentinel.store import LocalStore, _doc
from edgar_sentinel.schemas import FilingRecord


def make_analysis(p=80, b=80, c=80, r=80, m=80, composite=80, classification="Strong"):
    ps = lambda s: PillarScore(score=s, rationale="x")
    return FilingAnalysis(
        profitability=ps(p),
        balance_sheet=ps(b),
        cash_generation=ps(c),
        risk_flags=ps(r),
        management_signal=ps(m),
        composite=composite,
        classification=classification,
        highlights=["a", "b", "c"],
        key_metrics=KeyMetrics(),
        confidence="high",
    )


def make_record(ticker="TEST", accession="0001-26-000001", date="2026-05-01", form="10-Q"):
    return FilingRecord(
        ticker=ticker,
        cik=1,
        company="Test Co",
        form=form,
        accession=accession,
        filing_date=date,
        primary_doc="doc.htm",
        url="https://example.com/doc.htm",
    )


def prior_doc(**kwargs):
    return _doc(make_record(), make_analysis(**kwargs), {})


def test_delta_math_and_no_alert_on_small_move():
    d = compute_delta(prior_doc(composite=80), make_analysis(composite=85, p=85))
    assert d["fhs_delta"] == 5
    assert d["pillar_deltas"]["profitability"] == 5
    assert not d["alert"]


def test_alert_on_threshold_drop():
    d = compute_delta(prior_doc(composite=80), make_analysis(composite=68, classification="Stable"))
    assert d["fhs_delta"] == -12
    assert d["alert"]


def test_alert_on_classification_change_even_if_small_delta():
    d = compute_delta(
        prior_doc(composite=80),
        make_analysis(composite=79, classification="Stable"),
    )
    assert abs(d["fhs_delta"]) < 10
    assert d["alert"]


def test_alert_on_risk_pillar_collapse():
    d = compute_delta(prior_doc(composite=80, r=80), make_analysis(composite=76, r=60))
    assert d["pillar_deltas"]["risk_flags"] == -20
    assert d["alert"]


def test_local_store_prior_lookup(tmp_path, monkeypatch):
    from edgar_sentinel.config import settings

    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    store = LocalStore()
    store.save(make_record(accession="0001-26-000001", date="2026-05-01"), make_analysis(composite=70), {})
    store.save(make_record(accession="0001-26-000002", date="2026-07-31"), make_analysis(composite=85), {})

    prior = store.get_prior("TEST", "2026-07-31")
    assert prior and prior["filing_date"] == "2026-05-01"
    assert prior["analysis"]["composite"] == 70
    assert store.get_prior("TEST", "2026-05-01") is None
    assert store.get_prior("OTHER", "2026-12-31") is None

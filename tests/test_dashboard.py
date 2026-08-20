from fastapi.testclient import TestClient

from edgar_sentinel.config import settings
from edgar_sentinel.dashboard.app import app
from edgar_sentinel.schemas import FilingRecord
from edgar_sentinel.store import LocalStore
from tests.test_delta import make_analysis, make_record


def _seed(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    store = LocalStore()
    store.save(make_record(accession="0001-26-000001", date="2026-05-01"), make_analysis(composite=81), {"risk_factors": "* fine"})
    store.save(make_record(accession="0001-26-000002", date="2026-07-31"), make_analysis(composite=58, r=55, classification="Caution"), {})
    return TestClient(app)


def test_overview_lists_company_and_alert(tmp_path, monkeypatch):
    c = _seed(tmp_path, monkeypatch)
    r = c.get("/")
    assert r.status_code == 200
    assert "TEST" in r.text and "Caution" in r.text
    assert "81 → 58" in r.text  # alert line: -23 trips the threshold
    assert "<svg" in r.text  # sparkline rendered for 2 points


def test_company_and_filing_pages(tmp_path, monkeypatch):
    c = _seed(tmp_path, monkeypatch)
    assert c.get("/c/test").status_code == 200
    r = c.get("/f/TEST/0001-26-000002")
    assert r.status_code == 200
    assert "ALERT" in r.text and "vs. prior filing" in r.text
    assert "Filing Health Score pillars" in r.text
    r1 = c.get("/f/TEST/0001-26-000001")
    assert "* fine" in r1.text  # Gemma note rendered
    assert c.get("/c/NOPE").status_code == 200 and "No analyses" in c.get("/c/NOPE").text
    assert c.get("/healthz").json() == {"ok": True}

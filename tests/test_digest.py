from edgar_sentinel.digest import render_html, render_text, send_digest

ENTRY = {
    "filing": {
        "ticker": "TEST",
        "company": "Test & Co <script>",
        "form": "10-Q",
        "filing_date": "2026-07-31",
    },
    "analysis": {
        "composite": 62,
        "classification": "Stable",
        "confidence": "high",
        "highlights": ["Revenue fell 8%", "Going-concern language added", "CFO resigned"],
    },
    "delta": {
        "fhs_prior": 81,
        "fhs_delta": -19,
        "classification_change": "Strong -> Stable",
        "alert": True,
        "detail": {"narrative": "Sharp deterioration driven by new risk disclosures."},
    },
}


def test_text_digest_leads_with_alerts_and_shows_delta():
    txt = render_text([ENTRY], "2026-08-01")
    assert "*** ALERTS ***" in txt
    assert txt.index("ALERTS") < txt.index("Test & Co")
    assert "81 → 62 (-19)" in txt
    assert "Going-concern language added" in txt
    assert "Not investment advice" in txt


def test_html_digest_escapes_and_colors():
    out = render_html([ENTRY], "2026-08-01")
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert "#0969da" in out  # Stable band color
    assert "ALERTS" in out


def test_empty_run_renders_quiet_message():
    assert "No new 10-K/10-Q filings" in render_text([], "2026-08-01")
    assert "No new 10-K/10-Q filings" in render_html([], "2026-08-01")


def test_send_is_noop_without_config(monkeypatch):
    from edgar_sentinel.config import settings

    monkeypatch.setattr(settings, "sendgrid_api_key", "")
    assert send_digest([ENTRY]) is False

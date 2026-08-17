import glob
from pathlib import Path

import pytest

from edgar_sentinel.pipeline.parser import extract_sections

BODY = "x " * 400  # > _MIN_SECTION chars


def _wrap(*parts: str) -> str:
    return "<html><body>" + "".join(f"<p>{p}</p>" for p in parts) + "</body></html>"


def test_takes_last_match_to_skip_table_of_contents():
    html = _wrap(
        "Item 1A. Risk Factors 12",  # TOC line
        "Item 7. Management's Discussion and Analysis 30",  # TOC line
        "Item 1A. Risk Factors " + "risk body " + BODY,
        "Item 7. Management's Discussion and Analysis " + "mdna body " + BODY,
    )
    s = extract_sections(html)
    assert "risk body" in s["risk_factors"]
    assert "risk_factors" in s and "mdna" in s
    assert "mdna body" not in s["risk_factors"]


def test_loose_gap_between_item_number_and_title():
    html = _wrap("ITEM 1A — RISK FACTORS " + "content " + BODY, "ITEM 7 MANAGEMENT'S DISCUSSION AND ANALYSIS " + BODY)
    s = extract_sections(html)
    assert "content" in s["risk_factors"]


def test_body_fallback_when_item_prefix_missing():
    html = _wrap(
        "See Risk Factors below.",  # cross-reference: short span, must lose
        "RISK FACTORS " + "real risks here " + BODY,
        "Item 7. Management's Discussion and Analysis " + BODY,
    )
    s = extract_sections(html)
    assert "real risks here" in s["risk_factors"]


@pytest.mark.parametrize("path", glob.glob("data/filings/*/*/*.htm"))
def test_real_filings_on_disk_yield_core_sections(path):
    """Regression over whatever real filings the local cache holds."""
    s = extract_sections(Path(path).read_text(encoding="utf-8", errors="replace"))
    assert "mdna" in s, path
    assert "risk_factors" in s, path

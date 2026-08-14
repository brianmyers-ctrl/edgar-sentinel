from edgar_sentinel.edgar.client import EdgarClient, filter_recent

RECENT = {
    "form": ["10-K", "8-K", "10-Q", "10-Q"],
    "accessionNumber": ["0001-25-000001", "0001-25-000002", "0001-25-000003", "0001-25-000004"],
    "filingDate": ["2026-08-01", "2026-08-05", "2026-07-01", "2026-05-01"],
    "reportDate": ["2026-06-30", "", "2026-06-30", "2026-03-31"],
    "primaryDocument": ["a10k.htm", "an8k.htm", "a10q.htm", ""],
}


def test_filters_forms_and_dates():
    rows = filter_recent(RECENT, forms=("10-K", "10-Q"), since="2026-06-01")
    assert [r["form"] for r in rows] == ["10-K", "10-Q"]
    assert rows[0]["accession"] == "0001-25-000001"


def test_drops_rows_without_primary_document():
    rows = filter_recent(RECENT, forms=("10-K", "10-Q"), since="")
    assert all(r["primary_doc"] for r in rows)
    assert len(rows) == 2


def test_filing_url_strips_accession_dashes():
    url = EdgarClient.filing_url(320193, "0000320193-25-000073", "aapl-10q.htm")
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019325000073/aapl-10q.htm"
    )

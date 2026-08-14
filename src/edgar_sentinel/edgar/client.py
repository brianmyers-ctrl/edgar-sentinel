import time
from pathlib import Path

import requests

from ..config import TRACKED_FORMS, settings

SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"

# SEC fair-access policy: stay well under 10 requests/second, declare a User-Agent.
_MIN_INTERVAL_S = 0.15


def filter_recent(recent: dict, forms=TRACKED_FORMS, since: str = "") -> list[dict]:
    """Pure filter over the parallel arrays in EDGAR's submissions JSON."""
    out = []
    rows = zip(
        recent.get("form", []),
        recent.get("accessionNumber", []),
        recent.get("filingDate", []),
        recent.get("reportDate", []),
        recent.get("primaryDocument", []),
    )
    for form, accession, filed, report, doc in rows:
        if forms and form not in forms:
            continue
        if since and filed < since:
            continue
        if not doc:  # no primary document -> nothing to download
            continue
        out.append(
            {
                "form": form,
                "accession": accession,
                "filing_date": filed,
                "report_date": report or "",
                "primary_doc": doc,
            }
        )
    return out


class EdgarClient:
    def __init__(self, user_agent: str | None = None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent or settings.sec_user_agent
        self._last_request = 0.0

    def _get(self, url: str) -> requests.Response:
        wait = _MIN_INTERVAL_S - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        resp = self.session.get(url, timeout=30)
        self._last_request = time.monotonic()
        resp.raise_for_status()
        return resp

    def ticker_map(self) -> dict[str, dict]:
        data = self._get(SEC_TICKER_MAP_URL).json()
        return {
            row["ticker"].upper(): {"cik": int(row["cik_str"]), "title": row["title"]}
            for row in data.values()
        }

    def recent_filings(self, cik: int, forms=TRACKED_FORMS, since: str = "") -> list[dict]:
        data = self._get(SUBMISSIONS_URL.format(cik=cik)).json()
        return filter_recent(data.get("filings", {}).get("recent", {}), forms, since)

    @staticmethod
    def filing_url(cik: int, accession: str, doc: str) -> str:
        return ARCHIVE_URL.format(cik=cik, accession=accession.replace("-", ""), doc=doc)

    def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self._get(url).content)
        return dest

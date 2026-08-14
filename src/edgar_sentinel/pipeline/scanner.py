from datetime import date, timedelta
from pathlib import Path

from ..config import settings
from ..edgar.client import EdgarClient
from ..schemas import FilingRecord


def scan(
    tickers: list[str],
    since_days: int = 30,
    limit: int = 3,
    seen: set[str] | None = None,
) -> list[FilingRecord]:
    """Find new watchlist filings, newest first, excluding already-seen
    accessions. Seen-state persistence lives in the store, not here."""
    client = EdgarClient()
    tmap = client.ticker_map()
    since = (date.today() - timedelta(days=since_days)).isoformat()
    seen = seen or set()

    records: list[FilingRecord] = []
    for ticker in tickers:
        info = tmap.get(ticker.upper())
        if not info:
            print(f"[scan] unknown ticker, skipping: {ticker}")
            continue
        for f in client.recent_filings(info["cik"], since=since):
            if f["accession"] in seen:
                continue
            records.append(
                FilingRecord(
                    ticker=ticker.upper(),
                    cik=info["cik"],
                    company=info["title"],
                    url=EdgarClient.filing_url(info["cik"], f["accession"], f["primary_doc"]),
                    **f,
                )
            )

    records.sort(key=lambda r: r.filing_date, reverse=True)
    return records[:limit]


def download_filings(records: list[FilingRecord]) -> list[FilingRecord]:
    """Download primary documents locally for processing; archive raw copies
    to Cloud Storage when GCS_BUCKET is configured."""
    client = EdgarClient()
    base = Path(settings.data_dir) / "filings"
    bucket = None
    if settings.gcs_bucket:
        from google.cloud import storage

        bucket = storage.Client(project=settings.gcp_project).bucket(settings.gcs_bucket)

    for r in records:
        acc = r.accession.replace("-", "")
        dest = base / r.ticker / acc / r.primary_doc
        if not dest.exists():
            client.download(r.url, dest)
        r.local_path = str(dest)
        if bucket is not None:
            blob = bucket.blob(f"filings/{r.ticker}/{acc}/{r.primary_doc}")
            if not blob.exists():
                blob.upload_from_filename(str(dest))
                print(f"[archive] gs://{settings.gcs_bucket}/{blob.name}")
    return records

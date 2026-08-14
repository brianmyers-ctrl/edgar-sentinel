import json
from pathlib import Path

from .config import settings
from .schemas import FilingAnalysis, FilingRecord


def _doc(record: FilingRecord, analysis: FilingAnalysis, notes: dict) -> dict:
    return {
        "ticker": record.ticker,
        "filing_date": record.filing_date,
        "filing": record.model_dump(),
        "analysis": analysis.model_dump(),
        "gemma_notes": notes,
    }


class LocalStore:
    """Analysis history on local disk: data/analyses/<ticker>/<accession>.json"""

    def __init__(self):
        self.base = Path(settings.data_dir) / "analyses"

    def save(self, record: FilingRecord, analysis: FilingAnalysis, notes: dict) -> None:
        p = self.base / record.ticker / f"{record.accession.replace('-', '')}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(_doc(record, analysis, notes), indent=2))

    def get_prior(self, ticker: str, before_date: str) -> dict | None:
        tdir = self.base / ticker
        if not tdir.exists():
            return None
        docs = [json.loads(f.read_text()) for f in tdir.glob("*.json")]
        prior = [d for d in docs if d["filing_date"] < before_date]
        return max(prior, key=lambda d: d["filing_date"], default=None)

    def load_seen(self) -> set[str]:
        p = Path(settings.data_dir) / "state.json"
        if p.exists():
            return set(json.loads(p.read_text()).get("seen", []))
        return set()

    def save_seen(self, seen: set[str]) -> None:
        p = Path(settings.data_dir) / "state.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"seen": sorted(seen)}, indent=2))


class FirestoreStore:
    """Analysis history in Firestore, collection 'analyses'.

    Documents are keyed <ticker>_<accession> so reprocessing a filing is
    idempotent. Prior lookup pulls the ticker's docs and sorts client-side —
    watchlist-scale data, no composite index needed.
    """

    def __init__(self):
        from google.cloud import firestore

        self.db = firestore.Client(project=settings.gcp_project)
        self.col = self.db.collection("analyses")

    def save(self, record: FilingRecord, analysis: FilingAnalysis, notes: dict) -> None:
        doc_id = f"{record.ticker}_{record.accession.replace('-', '')}"
        self.col.document(doc_id).set(_doc(record, analysis, notes))

    def get_prior(self, ticker: str, before_date: str) -> dict | None:
        from google.cloud.firestore_v1.base_query import FieldFilter

        docs = [
            d.to_dict()
            for d in self.col.where(filter=FieldFilter("ticker", "==", ticker)).stream()
        ]
        prior = [d for d in docs if d["filing_date"] < before_date]
        return max(prior, key=lambda d: d["filing_date"], default=None)

    def load_seen(self) -> set[str]:
        doc = self.db.collection("state").document("seen_accessions").get()
        return set(doc.to_dict().get("seen", [])) if doc.exists else set()

    def save_seen(self, seen: set[str]) -> None:
        self.db.collection("state").document("seen_accessions").set(
            {"seen": sorted(seen)}
        )


def get_store():
    if settings.storage_backend == "firestore":
        return FirestoreStore()
    return LocalStore()

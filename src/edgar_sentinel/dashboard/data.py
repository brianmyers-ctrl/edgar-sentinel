"""Read-only access layer for the dashboard over Firestore (or the local store).

Everything here returns plain dicts; view logic lives in the routes.
"""

from ..config import FHS_WEIGHTS, settings

PILLARS = list(FHS_WEIGHTS)


def _all_docs() -> list[dict]:
    if settings.storage_backend == "firestore":
        from google.cloud import firestore

        col = firestore.Client(project=settings.gcp_project).collection("analyses")
        return [d.to_dict() for d in col.stream()]
    import json
    from pathlib import Path

    base = Path(settings.data_dir) / "analyses"
    return [json.loads(f.read_text()) for f in base.glob("*/*.json")] if base.exists() else []


def _attach_deltas(docs: list[dict]) -> list[dict]:
    """Compute each doc's delta vs. the same ticker's previous filing so the
    dashboard shows movement even for analyses stored before deltas existed."""
    from ..pipeline.delta import compute_delta
    from ..schemas import FilingAnalysis

    by_ticker: dict[str, list[dict]] = {}
    for d in docs:
        by_ticker.setdefault(d["ticker"], []).append(d)
    for docs_t in by_ticker.values():
        docs_t.sort(key=lambda d: d["filing_date"])
        for prev, cur in zip(docs_t, docs_t[1:]):
            try:
                cur["delta"] = compute_delta(prev, FilingAnalysis(**cur["analysis"]))
            except Exception:
                cur["delta"] = None
    return docs


def overview() -> dict:
    docs = _attach_deltas(_all_docs())
    latest: dict[str, dict] = {}
    for d in docs:
        if d["ticker"] not in latest or d["filing_date"] > latest[d["ticker"]]["filing_date"]:
            latest[d["ticker"]] = d
    companies = sorted(latest.values(), key=lambda d: d["analysis"]["composite"])
    alerts = sorted(
        [d for d in docs if d.get("delta") and d["delta"]["alert"]],
        key=lambda d: d["filing_date"],
        reverse=True,
    )
    recent = sorted(docs, key=lambda d: d["filing_date"], reverse=True)[:12]
    trends: dict[str, list[int]] = {}
    for d in sorted(docs, key=lambda d: d["filing_date"]):
        trends.setdefault(d["ticker"], []).append(d["analysis"]["composite"])
    bands = {"Strong": 0, "Stable": 0, "Caution": 0, "Distress": 0}
    for d in latest.values():
        bands[d["analysis"]["classification"]] = bands.get(d["analysis"]["classification"], 0) + 1
    return {
        "companies": companies,
        "alerts": alerts,
        "recent": recent,
        "trends": trends,
        "bands": bands,
        "n_filings": len(docs),
        "n_companies": len(latest),
    }


def company(ticker: str) -> dict | None:
    docs = [d for d in _attach_deltas(_all_docs()) if d["ticker"] == ticker.upper()]
    if not docs:
        return None
    docs.sort(key=lambda d: d["filing_date"])
    return {"ticker": ticker.upper(), "company": docs[-1]["filing"]["company"], "filings": docs}


def filing(ticker: str, accession: str) -> dict | None:
    acc = accession.replace("-", "")
    for d in _attach_deltas(_all_docs()):
        if d["ticker"] == ticker.upper() and d["filing"]["accession"].replace("-", "") == acc:
            return d
    return None

import argparse
import json
from datetime import datetime
from pathlib import Path

from .config import settings
from .pipeline import scanner
from .pipeline.parser import GemmaTriage
from .schemas import FilingRecord


def process_filing(r: FilingRecord, parser: GemmaTriage, store, args) -> dict:
    """Parse, analyze, and delta a single filing. Raises on failure; the
    caller decides what a failure means for the run."""
    html = Path(r.local_path).read_text(encoding="utf-8", errors="replace")
    sections, notes = parser.parse(html)
    got = ", ".join(f"{k}:{len(v):,}ch" for k, v in sections.items())
    print(f"[parse] {r.ticker} {r.form} -> {got}")
    if notes:
        print(f"[gemma] triage notes: {', '.join(notes)}")

    entry = {
        "filing": r.model_dump(),
        "sections_found": sorted(sections),
        "gemma_notes": notes,
    }
    if args.skip_llm:
        print("[analyze] skipped (--skip-llm)")
        return entry
    if not settings.use_vertex and not settings.gemini_api_key:
        print("[analyze] skipped (no Vertex mode and no GEMINI_API_KEY)")
        return entry

    from .pipeline.analyst import analyze
    from .pipeline.delta import compute_delta, narrate_delta

    a = analyze(r, sections, notes)
    entry["analysis"] = a.model_dump()
    print(f"[analyze] {r.ticker} {r.form}: FHS {a.composite} ({a.classification})")
    for h in a.highlights:
        print(f"          • {h}")

    prior = store.get_prior(r.ticker, r.filing_date)
    store.save(r, a, notes)
    if prior:
        delta = compute_delta(prior, a)
        try:
            delta["detail"] = narrate_delta(prior, r, a, delta).model_dump()
        except Exception as e:
            print(f"[delta] narrative unavailable ({e})")
        entry["delta"] = delta
        flag = "  ** ALERT **" if delta["alert"] else ""
        print(
            f"[delta] {r.ticker} vs {delta['against']['form']} filed "
            f"{delta['against']['filing_date']}: FHS {delta['fhs_prior']} -> "
            f"{a.composite} ({delta['fhs_delta']:+d}){flag}"
        )
    return entry


def run(args) -> None:
    tickers = args.tickers or settings.watchlist
    print(f"[run] watchlist={tickers} since={args.since}d limit={args.limit}")

    from .store import get_store

    store = get_store()
    seen = set() if args.ignore_state else store.load_seen()
    records = scanner.scan(tickers, args.since, args.limit, seen)
    if not records:
        print("[run] no new filings found")
        return
    for r in records:
        print(f"[scan] {r.filing_date}  {r.ticker:6} {r.form:5} {r.accession}")

    records = scanner.download_filings(records)
    parser = GemmaTriage()
    results = []

    # Chronological order so a company's earlier filing is stored before its
    # later one — the delta engine compares each filing against its prior.
    for r in sorted(records, key=lambda x: x.filing_date):
        try:
            results.append(process_filing(r, parser, store, args))
            seen.add(r.accession)
        except Exception as e:
            # One bad filing must never kill the daily run; it stays unmarked
            # so the next scheduled run retries it.
            print(f"[error] {r.ticker} {r.form} {r.accession}: {type(e).__name__}: {e}")

    store.save_seen(seen)
    out = Path(settings.data_dir) / "output"
    out.mkdir(parents=True, exist_ok=True)
    digest = out / f"digest-{datetime.now():%Y%m%d-%H%M%S}.json"
    digest.write_text(json.dumps(results, indent=2))
    print(f"[run] digest written: {digest}")
    if not args.skip_llm and (results or settings.digest_always):
        from .digest import send_digest

        send_digest(results)


def main() -> None:
    p = argparse.ArgumentParser(prog="edgar-sentinel")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="scan, download, parse, and analyze new filings")
    r.add_argument("--tickers", nargs="*", help="override watchlist")
    r.add_argument("--since", type=int, default=30, help="lookback window in days")
    r.add_argument("--limit", type=int, default=3, help="max filings this run")
    r.add_argument("--skip-llm", action="store_true", help="skip the Gemini analyst stage")
    r.add_argument("--ignore-state", action="store_true", help="reprocess already-seen filings")
    r.set_defaults(func=run)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

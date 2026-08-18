"""ADK orchestration for EDGAR Sentinel.

The orchestrator is a Gemini-powered ADK agent whose tools are the pipeline
stages. The agent decides the run flow — scan, analyze each new filing in
chronological order, write the digest — and produces the human run report,
leading with any alerts.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from google.genai import types

from .config import settings
from .pipeline import scanner
from .pipeline.parser import GemmaTriage
from .schemas import FilingRecord

# Run-scoped context shared by the tools (one process = one run).
_ctx: dict = {"records": {}, "results": [], "parser": None, "store": None}


def _parser() -> GemmaTriage:
    if _ctx["parser"] is None:
        _ctx["parser"] = GemmaTriage()
    return _ctx["parser"]


def _store():
    if _ctx["store"] is None:
        from .store import get_store

        _ctx["store"] = get_store()
    return _ctx["store"]


def scan_new_filings(
    since_days: int = 30,
    limit: int = 3,
    ignore_state: bool = False,
    tickers: list[str] | None = None,
) -> dict:
    """Scan SEC EDGAR for new 10-K/10-Q filings from the watchlist and download them.

    Args:
        since_days: Lookback window in days.
        limit: Maximum number of filings to process this run.
        ignore_state: Reprocess filings already seen in previous runs.
        tickers: Optional ticker override; defaults to the configured watchlist.

    Returns:
        dict with 'count' and 'filings': list of {accession, ticker, form,
        filing_date}, sorted OLDEST FIRST — analyze them in this order so
        quarter-over-quarter deltas line up.
    """
    seen = set() if ignore_state else _store().load_seen()
    records = scanner.scan(tickers or settings.watchlist, since_days, limit, seen)
    records = scanner.download_filings(records)
    _ctx["records"] = {r.accession: r for r in records}
    filings = [
        {
            "accession": r.accession,
            "ticker": r.ticker,
            "form": r.form,
            "filing_date": r.filing_date,
        }
        for r in sorted(records, key=lambda x: x.filing_date)
    ]
    print(f"[tool] scan_new_filings -> {len(filings)} filing(s)")
    return {"count": len(filings), "filings": filings}


def analyze_filing(accession: str) -> dict:
    """Run the full analysis pipeline for one scanned filing.

    Parses sections, gets Gemma triage notes, scores the filing with the
    Gemini Filing Health Score analyst, stores the result, and computes the
    delta against the company's prior filing when one exists.

    Args:
        accession: Accession number exactly as returned by scan_new_filings.

    Returns:
        Compact result: ticker, form, fhs, classification, highlights, and
        delta (fhs_prior, fhs_delta, classification_change, alert) if available.
    """
    r: FilingRecord | None = _ctx["records"].get(accession)
    if r is None:
        return {"error": f"unknown accession {accession}; call scan_new_filings first"}

    from .pipeline.analyst import analyze
    from .pipeline.delta import compute_delta, narrate_delta

    html = Path(r.local_path).read_text(encoding="utf-8", errors="replace")
    sections, notes = _parser().parse(html)
    print(f"[tool] analyze_filing {r.ticker} {r.form}: sections={sorted(sections)}, gemma_notes={sorted(notes)}")

    a = analyze(r, sections, notes)
    store = _store()
    prior = store.get_prior(r.ticker, r.filing_date)
    store.save(r, a, notes)

    entry = {
        "filing": r.model_dump(),
        "sections_found": sorted(sections),
        "gemma_notes": notes,
        "analysis": a.model_dump(),
    }
    result = {
        "ticker": r.ticker,
        "form": r.form,
        "filing_date": r.filing_date,
        "fhs": a.composite,
        "classification": a.classification,
        "highlights": a.highlights,
    }
    if prior:
        delta = compute_delta(prior, a)
        try:
            delta["detail"] = narrate_delta(prior, r, a, delta).model_dump()
        except Exception as e:
            print(f"[delta] narrative unavailable ({e})")
        entry["delta"] = delta
        result["delta"] = {
            k: delta[k]
            for k in ("fhs_prior", "fhs_delta", "classification_change", "alert")
        }
    _ctx["results"].append(entry)

    seen = store.load_seen()
    seen.add(r.accession)
    store.save_seen(seen)
    return result


def write_digest() -> dict:
    """Write the run digest JSON (all analyses and deltas) and email it to the
    subscriber. Call exactly once, after every filing has been analyzed.

    Returns:
        Digest file path, counts of analyses and alerts, and whether the
        email was sent.
    """
    from .digest import send_digest

    out = Path(settings.data_dir) / "output"
    out.mkdir(parents=True, exist_ok=True)
    digest = out / f"digest-{datetime.now():%Y%m%d-%H%M%S}.json"
    digest.write_text(json.dumps(_ctx["results"], indent=2))
    results = _ctx["results"]
    alerts = sum(1 for e in results if e.get("delta", {}).get("alert"))
    print(f"[tool] write_digest -> {digest} ({len(results)} analyses, {alerts} alerts)")
    # Email when there is something to say; DIGEST_ALWAYS also sends the
    # "nothing new today" heartbeat.
    emailed = send_digest(results) if (results or settings.digest_always) else False
    return {
        "digest_path": str(digest),
        "analyzed": len(results),
        "alerts": alerts,
        "emailed": emailed,
    }


INSTRUCTION = """You are EDGAR Sentinel's orchestrator, an autonomous SEC-filings
research agent. When asked to run:
1. Call scan_new_filings, passing through any parameters given in the request.
2. Call analyze_filing for EVERY filing returned, one at a time, in the order
   provided (oldest first so deltas compare correctly). If one filing errors,
   continue with the rest and mention it in the report.
3. Call write_digest exactly once at the end.
4. Finish with a concise run report: lead with any ALERTS, then one line per
   filing (ticker, form, FHS, classification, delta). You produce research
   summaries, never investment advice."""


def build_agent():
    from google.adk.agents import Agent

    return Agent(
        name="edgar_sentinel_orchestrator",
        model=settings.gemini_model,
        instruction=INSTRUCTION,
        tools=[scan_new_filings, analyze_filing, write_digest],
    )


def run_agent(request: str) -> None:
    import asyncio
    import inspect

    from google.adk.runners import InMemoryRunner

    async def _run() -> None:
        runner = InMemoryRunner(agent=build_agent(), app_name="edgar-sentinel")
        session = runner.session_service.create_session(
            app_name="edgar-sentinel", user_id="local"
        )
        if inspect.isawaitable(session):
            session = await session
        msg = types.Content(role="user", parts=[types.Part(text=request)])
        async for event in runner.run_async(
            user_id="local", session_id=session.id, new_message=msg
        ):
            content = getattr(event, "content", None)
            for part in content.parts if content and content.parts else []:
                if getattr(part, "function_call", None):
                    args = json.dumps(dict(part.function_call.args or {}))
                    print(f"[adk] agent -> {part.function_call.name}({args})")
                elif getattr(part, "text", None) and event.is_final_response():
                    print("\n=== RUN REPORT ===\n" + part.text.strip())

    asyncio.run(_run())


def main() -> None:
    p = argparse.ArgumentParser(prog="edgar-sentinel-agent")
    p.add_argument("--since", type=int, default=30)
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--tickers", nargs="*")
    p.add_argument("--ignore-state", action="store_true")
    args = p.parse_args()

    req = (
        f"Run the daily filing scan with since_days={args.since}, limit={args.limit}"
        + (f", tickers={args.tickers}" if args.tickers else "")
        + (", ignore_state=true" if args.ignore_state else "")
        + "."
    )
    print(f"[adk] request: {req}")
    run_agent(req)


if __name__ == "__main__":
    main()

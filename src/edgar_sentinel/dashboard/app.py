"""EDGAR Sentinel dashboard — read-only web view over the analysis store.

Server-rendered HTML, no client framework. Runs on Cloud Run as a service
(`python -m edgar_sentinel.dashboard.app`) or locally with uvicorn.
"""

import html as _html
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from . import data

app = FastAPI(title="EDGAR Sentinel")
esc = _html.escape

BAND = {"Strong": "#1a7f37", "Stable": "#0969da", "Caution": "#bf8700", "Distress": "#cf222e"}
PILLAR_LABEL = {
    "profitability": "Profitability",
    "balance_sheet": "Balance sheet",
    "cash_generation": "Cash generation",
    "risk_flags": "Risk flags",
    "management_signal": "Mgmt signal",
}

CSS = """
:root{--bg:#0d1117;--card:#161b22;--line:#30363d;--fg:#e6edf3;--muted:#8b949e;--accent:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{display:flex;align-items:baseline;gap:14px;padding:18px 28px;border-bottom:1px solid var(--line)}
header h1{margin:0;font-size:20px}header .sub{color:var(--muted);font-size:13px}
main{max-width:1100px;margin:0 auto;padding:22px 28px}
.grid{display:grid;gap:16px}.g3{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.card h2{margin:0 0 10px;font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.big{font-size:30px;font-weight:700}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:0}.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:700;color:#fff}
.delta-up{color:#3fb950}.delta-down{color:#f85149}.muted{color:var(--muted)}
.alert{border-left:4px solid #f85149;padding-left:12px;margin:8px 0}
.bar{height:8px;background:#21262d;border-radius:4px;overflow:hidden}.bar>i{display:block;height:100%;border-radius:4px}
.kv{display:grid;grid-template-columns:180px 1fr;gap:6px 14px;font-size:14px}
ul{margin:6px 0;padding-left:20px}.foot{color:var(--muted);font-size:12px;margin-top:28px;text-align:center}
pre{white-space:pre-wrap;font:13px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;background:#0d1117;border:1px solid var(--line);border-radius:8px;padding:12px;margin:0}
"""


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)} · EDGAR Sentinel</title><style>{CSS}</style></head><body>"
        "<header><h1><a href='/' style='color:inherit'>EDGAR Sentinel</a></h1>"
        "<span class='sub'>autonomous SEC filing research · runs daily on Google Cloud</span></header>"
        f"<main>{body}<div class='foot'>Automated research summaries derived from SEC filings. "
        "Not investment advice.</div></main></body></html>"
    )


def pill(cls: str) -> str:
    return f"<span class='pill' style='background:{BAND.get(cls, '#57606a')}'>{esc(cls)}</span>"


def band_of(score: int) -> str:
    return "Strong" if score >= 80 else "Stable" if score >= 60 else "Caution" if score >= 40 else "Distress"


def delta_html(d: dict | None) -> str:
    if not d:
        return "<span class='muted'>first</span>"
    v = d["fhs_delta"]
    c = "delta-up" if v > 0 else ("delta-down" if v < 0 else "muted")
    flag = " ⚠" if d["alert"] else ""
    return f"<span class='{c}'>{v:+d}{flag}</span>"


def sparkline(scores: list[int], w: int = 120, h: int = 28) -> str:
    if len(scores) < 2:
        return "<span class='muted' style='font-size:12px'>—</span>"
    lo, hi = min(scores), max(scores)
    span = max(hi - lo, 1)
    pts = " ".join(
        f"{i * (w - 4) / (len(scores) - 1) + 2:.1f},{h - 3 - (s - lo) / span * (h - 6):.1f}"
        for i, s in enumerate(scores)
    )
    color = BAND.get(band_of(scores[-1]), "#58a6ff")
    return (
        f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}'>"
        f"<polyline fill='none' stroke='{color}' stroke-width='2' points='{pts}'/></svg>"
    )


def ul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index():
    o = data.overview()
    bands = "".join(
        f"<div style='display:flex;justify-content:space-between'><span>{pill(b)}</span><b>{n}</b></div>"
        for b, n in o["bands"].items()
    )
    alerts = "".join(
        f"<div class='alert'><b><a href='/c/{esc(d['ticker'])}'>{esc(d['ticker'])}</a></b> "
        f"{esc(d['filing']['form'])} filed {esc(d['filing_date'])}: FHS {d['delta']['fhs_prior']} → "
        f"{d['analysis']['composite']} ({d['delta']['fhs_delta']:+d}) · {esc(d['delta']['classification_change'])}</div>"
        for d in o["alerts"][:8]
    ) or (
        "<span class='muted'>No alerts yet. Alerts fire on a ≥10-point FHS move, a classification "
        "change, or a risk-pillar collapse.</span>"
    )
    rows = []
    for d in o["companies"]:
        a = d["analysis"]
        scores = o["trends"].get(d["ticker"], [a["composite"]])
        rows.append(
            f"<tr><td><b><a href='/c/{esc(d['ticker'])}'>{esc(d['ticker'])}</a></b>"
            f"<div class='muted' style='font-size:12px'>{esc(d['filing']['company'])}</div></td>"
            f"<td>{esc(d['filing']['form'])} · {esc(d['filing_date'])}</td>"
            f"<td class='num big' style='font-size:22px;color:{BAND.get(a['classification'])}'>{a['composite']}</td>"
            f"<td>{pill(a['classification'])}</td><td class='num'>{delta_html(d.get('delta'))}</td>"
            f"<td>{sparkline(scores)}</td></tr>"
        )
    empty = "<tr><td colspan='6' class='muted'>No analyses yet — the daily job populates this.</td></tr>"
    body = (
        "<div class='grid g3'>"
        f"<div class='card'><h2>Companies tracked</h2><div class='big'>{o['n_companies']}</div>"
        f"<div class='muted'>{o['n_filings']} filings analyzed</div></div>"
        f"<div class='card'><h2>Health bands (latest filing)</h2>{bands}</div>"
        "<div class='card'><h2>Pipeline</h2><div style='font-size:13px'>EDGAR scan → section parser → "
        "<b>Gemma</b> triage (Cloud Run) → <b>Gemini 3.5</b> Filing Health Score (Vertex AI) → Firestore → "
        "delta &amp; alerts → email digest</div></div></div>"
        f"<div class='card' style='margin-top:16px'><h2>Alerts</h2>{alerts}</div>"
        "<div class='card' style='margin-top:16px'><h2>Watchlist — sorted weakest first</h2>"
        "<table><thead><tr><th>Company</th><th>Latest filing</th><th class='num'>FHS</th><th>Band</th>"
        f"<th class='num'>Δ vs prior</th><th>Trend</th></tr></thead><tbody>{''.join(rows) or empty}</tbody></table></div>"
    )
    return page("Overview", body)


@app.get("/c/{ticker}", response_class=HTMLResponse)
def company_page(ticker: str):
    c = data.company(ticker)
    if not c:
        return page("Not found", f"<div class='card'>No analyses for {esc(ticker.upper())}.</div>")
    scores = [f["analysis"]["composite"] for f in c["filings"]]
    rows = "".join(
        f"<tr><td><a href='/f/{esc(c['ticker'])}/{esc(f['filing']['accession'])}'>"
        f"{esc(f['filing']['form'])} · {esc(f['filing_date'])}</a></td>"
        f"<td class='num' style='font-weight:700;color:{BAND.get(f['analysis']['classification'])}'>{f['analysis']['composite']}</td>"
        f"<td>{pill(f['analysis']['classification'])}</td><td class='num'>{delta_html(f.get('delta'))}</td>"
        f"<td style='font-size:13px'>{esc(f['analysis']['highlights'][0])}</td></tr>"
        for f in reversed(c["filings"])
    )
    latest = c["filings"][-1]["analysis"]
    n = len(c["filings"])
    body = (
        f"<div class='card'><h2>{esc(c['company'])}</h2>"
        "<div style='display:flex;align-items:center;gap:24px;flex-wrap:wrap'>"
        f"<div class='big' style='font-size:40px'>{esc(c['ticker'])}</div>{sparkline(scores, 320, 60)}"
        f"<div class='muted'>{n} filing{'s' if n != 1 else ''} analyzed · latest FHS "
        f"<b style='color:{BAND.get(latest['classification'])}'>{scores[-1]}</b></div></div></div>"
        "<div class='card' style='margin-top:16px'><h2>Filings</h2><table><thead><tr><th>Filing</th>"
        "<th class='num'>FHS</th><th>Band</th><th class='num'>Δ</th><th>Top highlight</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )
    return page(c["ticker"], body)


@app.get("/f/{ticker}/{accession}", response_class=HTMLResponse)
def filing_page(ticker: str, accession: str):
    d = data.filing(ticker, accession)
    if not d:
        return page("Not found", "<div class='card'>Filing not found.</div>")
    a, f = d["analysis"], d["filing"]
    pillars = "".join(
        f"<div class='kv' style='margin-bottom:10px'><div><b>{PILLAR_LABEL[p]}</b> "
        f"<span class='muted'>{int(data.FHS_WEIGHTS[p] * 100)}%</span>"
        f"<div class='bar' style='margin-top:4px'><i style='width:{a[p]['score']}%;"
        f"background:{BAND.get(band_of(a[p]['score']))}'></i></div>"
        f"<div class='num' style='font-size:13px'>{a[p]['score']}</div></div>"
        f"<div style='font-size:13px'>{esc(a[p]['rationale'])}</div></div>"
        for p in data.PILLARS
    )
    km = "".join(
        f"<div><span class='muted'>{esc(k.replace('_', ' '))}:</span> {esc(str(v))}</div>"
        for k, v in a["key_metrics"].items()
        if v
    )
    delta = d.get("delta")
    delta_block = ""
    if delta:
        det = delta.get("detail") or {}
        pd_ = "".join(
            f"<span style='margin-right:14px'>{PILLAR_LABEL[p]} "
            f"<b class='{'delta-up' if v > 0 else 'delta-down' if v < 0 else 'muted'}'>{v:+d}</b></span>"
            for p, v in delta["pillar_deltas"].items()
        )
        border = ";border-color:#f85149" if delta["alert"] else ""
        flag = " — ⚠ ALERT" if delta["alert"] else ""
        delta_block = (
            f"<div class='card' style='margin-top:16px{border}'><h2>vs. prior filing "
            f"({esc(delta['against']['form'])} filed {esc(delta['against']['filing_date'])}){flag}</h2>"
            f"<div>FHS {delta['fhs_prior']} → <b>{a['composite']}</b> ({delta['fhs_delta']:+d}) · "
            f"{esc(delta['classification_change'])}</div>"
            f"<div style='margin:8px 0;font-size:13px'>{pd_}</div>"
            + (f"<p>{esc(det['narrative'])}</p>" if det.get("narrative") else "")
            + (f"<div><b>New risks</b>{ul(det['new_risks'])}</div>" if det.get("new_risks") else "")
            + (f"<div><b>Metric trends</b>{ul(det['metric_trends'])}</div>" if det.get("metric_trends") else "")
            + "</div>"
        )
    gemma = "".join(
        f"<div style='margin-top:8px'><b class='muted' style='font-size:12px;text-transform:uppercase'>"
        f"{esc(k)}</b><pre>{esc(v)}</pre></div>"
        for k, v in (d.get("gemma_notes") or {}).items()
    )
    body = (
        f"<div class='card'><div class='muted'><a href='/c/{esc(d['ticker'])}'>{esc(d['ticker'])}</a> · "
        f"{esc(f['company'])}</div>"
        "<div style='display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:12px'>"
        f"<h2 style='margin:4px 0;font-size:20px;color:var(--fg);text-transform:none;letter-spacing:0'>"
        f"{esc(f['form'])} filed {esc(f['filing_date'])} <span class='muted' style='font-size:13px'>period "
        f"{esc(f.get('report_date') or 'n/a')}</span></h2>"
        f"<div class='big' style='font-size:36px;color:{BAND.get(a['classification'])}'>{a['composite']} "
        f"{pill(a['classification'])}</div></div>"
        f"<div class='muted' style='font-size:13px'>confidence {esc(a['confidence'])} · "
        f"<a href='{esc(f['url'])}' target='_blank' rel='noopener'>source filing on SEC.gov ↗</a></div>"
        f"<div style='margin-top:10px'>{ul(a['highlights'])}</div></div>"
        f"{delta_block}"
        "<div class='grid g3' style='margin-top:16px'>"
        f"<div class='card' style='grid-column:span 2'><h2>Filing Health Score pillars</h2>{pillars}</div>"
        f"<div class='card'><h2>Key metrics ({esc(a['key_metrics'].get('period', ''))})</h2>"
        f"<div style='font-size:13px'>{km}</div></div></div>"
        "<div class='card' style='margin-top:16px'><h2>Gemma triage notes (pre-analysis, second opinion)</h2>"
        f"{gemma or '<span class=muted>None for this filing.</span>'}</div>"
    )
    return page(f"{d['ticker']} {f['form']}", body)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))

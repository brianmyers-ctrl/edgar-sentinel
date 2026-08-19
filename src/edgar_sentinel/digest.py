"""Daily digest rendering and delivery.

Renders the run's analyses/deltas into a plain-text + HTML email and sends
it via SendGrid. Delivery is best-effort: a mail failure is logged, never
raised, so it can't break the daily run.
"""

import html
import json
from datetime import date

import requests

from .config import settings

_BAND_COLOR = {
    "Strong": "#1a7f37",
    "Stable": "#0969da",
    "Caution": "#bf8700",
    "Distress": "#cf222e",
}


def _delta_str(d: dict | None) -> str:
    if not d:
        return "first analysis"
    return f"{d['fhs_prior']} → {d['fhs_delta'] + d['fhs_prior']} ({d['fhs_delta']:+d})"


def render_text(results: list[dict], run_date: str) -> str:
    alerts = [e for e in results if e.get("delta", {}).get("alert")]
    lines = [f"EDGAR Sentinel — daily digest — {run_date}", ""]
    if not results:
        lines += ["No new 10-K/10-Q filings on the watchlist today.", ""]
    if alerts:
        lines += ["*** ALERTS ***"]
        for e in alerts:
            f, a, d = e["filing"], e["analysis"], e["delta"]
            lines.append(f"  {f['ticker']} {f['form']}: FHS {_delta_str(d)} — {d['classification_change']}")
        lines.append("")
    for e in results:
        f, a = e["filing"], e.get("analysis")
        if not a:
            continue
        lines.append(f"{f['ticker']} — {f['company']} — {f['form']} filed {f['filing_date']}")
        lines.append(f"  FHS {a['composite']} ({a['classification']}), confidence {a['confidence']}, delta: {_delta_str(e.get('delta'))}")
        for h in a["highlights"]:
            lines.append(f"  • {h}")
        det = e.get("delta", {}).get("detail")
        if det:
            lines.append(f"  What changed: {det['narrative']}")
        lines.append("")
    lines += ["—", "Automated research summary derived from SEC filings. Not investment advice."]
    return "\n".join(lines)


def render_html(results: list[dict], run_date: str) -> str:
    esc = html.escape
    alerts = [e for e in results if e.get("delta", {}).get("alert")]
    parts = [
        '<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:680px;margin:auto;color:#1f2328">',
        f'<h2 style="margin:0 0 4px">EDGAR Sentinel</h2><div style="color:#57606a;margin-bottom:16px">Daily digest — {esc(run_date)}</div>',
    ]
    if not results:
        parts.append('<p>No new 10-K/10-Q filings on the watchlist today.</p>')
    if alerts:
        parts.append('<div style="border-left:4px solid #cf222e;background:#fff5f5;padding:10px 14px;margin-bottom:16px"><b>ALERTS</b><ul style="margin:6px 0 0">')
        for e in alerts:
            f, d = e["filing"], e["delta"]
            parts.append(f"<li><b>{esc(f['ticker'])}</b> {esc(f['form'])}: FHS {esc(_delta_str(d))} — {esc(d['classification_change'])}</li>")
        parts.append("</ul></div>")
    for e in results:
        f, a = e["filing"], e.get("analysis")
        if not a:
            continue
        color = _BAND_COLOR.get(a["classification"], "#57606a")
        parts.append('<div style="border:1px solid #d0d7de;border-radius:8px;padding:14px 16px;margin-bottom:14px">')
        parts.append(
            f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<div><b style="font-size:16px">{esc(f["ticker"])}</b> <span style="color:#57606a">{esc(f["company"])} · {esc(f["form"])} filed {esc(f["filing_date"])}</span></div>'
            f'<div style="font-size:20px;font-weight:700;color:{color}">{a["composite"]} <span style="font-size:12px;font-weight:600">{esc(a["classification"])}</span></div></div>'
        )
        parts.append(f'<div style="color:#57606a;font-size:13px;margin:4px 0 8px">delta: {esc(_delta_str(e.get("delta")))} · confidence {esc(a["confidence"])}</div>')
        parts.append("<ul style='margin:0 0 8px;padding-left:20px'>" + "".join(f"<li>{esc(h)}</li>" for h in a["highlights"]) + "</ul>")
        det = e.get("delta", {}).get("detail")
        if det:
            parts.append(f'<div style="background:#f6f8fa;border-radius:6px;padding:8px 10px;font-size:13px"><b>What changed:</b> {esc(det["narrative"])}</div>')
        parts.append("</div>")
    parts.append('<div style="color:#57606a;font-size:12px;margin-top:20px">Automated research summary derived from SEC filings. Not investment advice.</div></div>')
    return "".join(parts)


def send_digest(results: list[dict], run_date: str | None = None) -> bool:
    """Send the digest via SendGrid. Returns True on success. Never raises."""
    if not settings.sendgrid_api_key or not settings.digest_to:
        print("[digest] email not configured (SENDGRID_API_KEY / DIGEST_TO); skipping send")
        return False
    run_date = run_date or date.today().isoformat()
    n_alerts = sum(1 for e in results if e.get("delta", {}).get("alert"))
    n = sum(1 for e in results if e.get("analysis"))
    subject = f"EDGAR Sentinel {run_date}: " + (
        f"{n_alerts} ALERT{'S' if n_alerts != 1 else ''}, {n} filing{'s' if n != 1 else ''}"
        if n_alerts
        else (f"{n} new filing{'s' if n != 1 else ''} analyzed" if n else "no new filings")
    )
    payload = {
        "personalizations": [{"to": [{"email": settings.digest_to}]}],
        "from": {"email": settings.digest_from, "name": "EDGAR Sentinel"},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": render_text(results, run_date)},
            {"type": "text/html", "value": render_html(results, run_date)},
        ],
    }
    try:
        r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
            json=payload,
            timeout=30,
        )
        if r.status_code // 100 == 2:
            print(f"[digest] emailed to {settings.digest_to}: {subject}")
            return True
        print(f"[digest] SendGrid error {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"[digest] send failed: {e}")
    return False

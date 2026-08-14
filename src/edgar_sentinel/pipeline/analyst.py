from ..config import FHS_WEIGHTS, settings
from ..schemas import DISCLAIMER, FilingAnalysis, FilingRecord

_TRUNCATE = {
    "risk_factors": 30_000,
    "mdna": 40_000,
    "financials": 25_000,
    "document_head": 10_000,
}

_BANDS = [(80, "Strong"), (60, "Stable"), (40, "Caution"), (0, "Distress")]


def _prompt(record: FilingRecord, sections: dict[str, str], notes: dict[str, str]) -> str:
    parts = [
        "You are the analyst stage of EDGAR Sentinel, an automated SEC filing "
        "research agent. Score this filing with the Filing Health Score (FHS) "
        "framework. You produce research summaries, never investment advice.",
        f"\nFiling: {record.company} ({record.ticker}) — {record.form}, "
        f"filed {record.filing_date}, period {record.report_date or 'n/a'}.",
        "\nScore five pillars 0-100, each with a 1-2 sentence rationale citing "
        "the section you used:",
        "- profitability: revenue growth, margin levels and direction, operating leverage",
        "- balance_sheet: cash vs total debt, current ratio, interest coverage, share count trend",
        "- cash_generation: operating cash flow vs net income, FCF margin, capex intensity",
        "- risk_flags: 100 = clean, 0 = severe. New/worsened risk factors, going-concern "
        "language, restatements, litigation, customer concentration, control weaknesses",
        "- management_signal: MD&A tone shift, guidance language, segment momentum",
        "\nRules: if the filing contains going-concern doubt or an announced restatement, "
        "score risk_flags at 15 or below. Set composite to the weighted sum "
        f"(weights: {FHS_WEIGHTS}) and classification to Strong (80+), Stable (60-79), "
        "Caution (40-59), or Distress (<40). Give exactly 3 highlights: the most "
        "decision-relevant changes in this filing. Extract key_metrics as reported, "
        "with units and period labels. Set confidence low/medium/high based on how "
        "complete the provided sections are.",
        f'\nSet disclaimer to exactly: "{DISCLAIMER}"',
    ]
    if notes:
        parts.append(
            "\n=== TRIAGE NOTES (from the local Gemma parsing stage; treat as "
            "a second opinion, verify against the sections) ==="
        )
        for key, n in notes.items():
            parts.append(f"[{key}]\n{n}")
    for key, cap in _TRUNCATE.items():
        if key in sections:
            parts.append(f"\n=== SECTION {key} ===\n{sections[key][:cap]}")
    return "\n".join(parts)


def _classify(score: int) -> str:
    return next(label for floor, label in _BANDS if score >= floor)


_client = None


def make_client():
    """One shared client per process. A fresh client per call risks being
    garbage-collected mid-request (its finalizer closes the HTTP pool)."""
    global _client
    if _client is None:
        from google import genai

        if settings.use_vertex:
            _client = genai.Client(
                vertexai=True, project=settings.gcp_project, location=settings.gcp_location
            )
        else:
            _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def analyze(
    record: FilingRecord, sections: dict[str, str], notes: dict[str, str] | None = None
) -> FilingAnalysis:
    resp = make_client().models.generate_content(
        model=settings.gemini_model,
        contents=_prompt(record, sections, notes or {}),
        config={
            "response_mime_type": "application/json",
            "response_schema": FilingAnalysis,
            "temperature": 0,
        },
    )
    analysis: FilingAnalysis = resp.parsed
    if analysis is None:
        raise RuntimeError(
            "analyst response failed schema parsing; raw head: " + (resp.text or "")[:300]
        )

    # Recompute the composite from pillar scores so the weighting in config.py
    # is authoritative, not the model's arithmetic.
    analysis.composite = round(
        sum(getattr(analysis, k).score * w for k, w in FHS_WEIGHTS.items())
    )
    analysis.classification = _classify(analysis.composite)
    analysis.disclaimer = DISCLAIMER
    return analysis

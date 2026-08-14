import json

from ..config import FHS_WEIGHTS, settings
from ..schemas import DeltaNarrative, FilingAnalysis, FilingRecord

_PILLARS = list(FHS_WEIGHTS)


def compute_delta(prior: dict, analysis: FilingAnalysis) -> dict:
    """Deterministic quarter-over-quarter comparison. The alert rule is code,
    not model judgment, so it is reproducible for judges and testable."""
    pa = prior["analysis"]
    fhs_delta = analysis.composite - pa["composite"]
    pillar_deltas = {k: getattr(analysis, k).score - pa[k]["score"] for k in _PILLARS}
    return {
        "against": {
            "form": prior["filing"]["form"],
            "accession": prior["filing"]["accession"],
            "filing_date": prior["filing"]["filing_date"],
        },
        "fhs_prior": pa["composite"],
        "fhs_delta": fhs_delta,
        "pillar_deltas": pillar_deltas,
        "classification_change": f"{pa['classification']} -> {analysis.classification}",
        "alert": (
            abs(fhs_delta) >= settings.alert_threshold
            or pa["classification"] != analysis.classification
            or pillar_deltas["risk_flags"] <= -15
        ),
    }


def narrate_delta(
    prior: dict, record: FilingRecord, analysis: FilingAnalysis, delta: dict
) -> DeltaNarrative:
    """Gemini turns the two analyses + computed deltas into a short
    what-changed report (drivers, new/reduced risks, metric trends)."""
    from .analyst import make_client

    prompt = "\n".join(
        [
            "You compare two consecutive SEC filing analyses for "
            f"{record.company} ({record.ticker}) produced by the Filing Health "
            "Score framework. Explain what changed and why it matters for a "
            "research digest. Never give investment advice.",
            f"\nComputed deltas (authoritative): {json.dumps({k: v for k, v in delta.items() if k != 'against'})}",
            f"\n=== PRIOR ANALYSIS ({prior['filing']['form']} filed {prior['filing']['filing_date']}) ===",
            json.dumps(prior["analysis"], indent=1),
            f"\n=== CURRENT ANALYSIS ({record.form} filed {record.filing_date}) ===",
            json.dumps(analysis.model_dump(), indent=1),
            "\nReturn: drivers (1-4 bullets, what moved the score and why), "
            "new_risks (risks present now but not before), reduced_risks "
            "(risks that eased or resolved), metric_trends (key figures "
            "period-over-period, with numbers), narrative (2-3 sentences, "
            "plain language).",
        ]
    )
    resp = make_client().models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": DeltaNarrative,
        },
    )
    return resp.parsed

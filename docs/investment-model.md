# The Filing Health Score (FHS)

A transparent, filing-derived research framework. Every input comes from the 10-K/10-Q itself (plus the immediately prior filing for trend comparison) — no external market data, no price targets, no buy/sell calls. The output is a research summary of the company's reported condition.

**FHS = 0–100 composite** across five pillars. Each pillar is scored 0–100 by the analyst model with cited evidence, then weighted:

| # | Pillar | Weight | What the analyst extracts and judges |
| :- | :--- | :--- | :--- |
| 1 | Profitability & Trajectory | 25% | Revenue YoY/QoQ, gross/operating/net margins and their direction, operating leverage |
| 2 | Balance Sheet Resilience | 20% | Cash vs. total debt, current ratio, interest coverage, share count trend (dilution vs. buybacks) |
| 3 | Cash Generation Quality | 20% | Operating cash flow vs. net income (earnings quality), free-cash-flow margin, capex intensity |
| 4 | Risk & Red Flags *(inverse)* | 20% | New/changed risk factors vs. prior filing, going-concern language, restatements, material litigation, customer concentration, internal-control weaknesses, auditor changes |
| 5 | Management Signal | 15% | MD&A tone shift vs. prior period, guidance language, segment momentum, notable disclosures |

## Classification bands

| FHS | Label |
| :- | :--- |
| 80–100 | **Strong** — improving fundamentals, low red-flag load |
| 60–79 | **Stable** — sound, watch noted items |
| 40–59 | **Caution** — deteriorating trends or material flags |
| 0–39 | **Distress** — severe flags (going concern, coverage failure, restatement) |

Hard rule: a going-concern qualification or announced restatement caps the composite at 39 regardless of other pillars.

## Output contract (per filing)

The analyst must return structured JSON (schema enforced in `analyst.py`):

- `pillar_scores` — the five scores with 1–2 sentence rationale each, citing the section used
- `composite` + `classification`
- `highlights` — exactly 3 bullets: the most decision-relevant changes in this filing
- `key_metrics` — extracted figures (revenue, net income, OCF, cash, total debt, shares outstanding) with period labels
- `confidence` — low/medium/high, driven by parse quality and disclosure completeness
- `disclaimer` — fixed string: research summary, not investment advice

## Design notes

- Weights are config, not code (`config.py`) — tuning them is a demo moment, not a rewrite.
- 10-Qs score the same pillars with quarter-over-quarter emphasis; pillar 4 compares against the last 10-K's risk factors.
- The model never sees raw HTML: Gemma (or the fallback parser) hands it labeled sections, which keeps Gemini token costs predictable and the analysis grounded.

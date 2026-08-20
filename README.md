# EDGAR Sentinel

An autonomous financial-research agent for the **All Things Agentic Hackathon** (Taskmaster track).

Every day, without supervision, it: scans SEC EDGAR for new 10-K/10-Q filings from a configurable watchlist → downloads and archives the raw filings → parses the messy HTML into clean sections with **Gemma** → scores each filing against a transparent investment-research framework (the [Filing Health Score](docs/investment-model.md)) using **Gemini** → delivers a structured daily digest.

> EDGAR Sentinel produces research summaries, not investment advice.

## Architecture

```
Cloud Scheduler (daily)
        │
        ▼
Cloud Run job ──► EDGAR client ──► Cloud Storage (raw filings)
   (ADK agent)         │
        │              ▼
        │        Firestore (filing metadata + labels)
        ▼
  section parser + Gemma triage (red-flag notes per section)
        ▼
  Gemini analyst (Filing Health Score, structured JSON)
        ▼
  Firestore (analyses) ──► daily digest (email / web view)
```

## Hackathon compliance

| Requirement | Where |
| :--- | :--- |
| Gemini 3.5+ via Gemini API / Vertex AI | `src/edgar_sentinel/pipeline/analyst.py` |
| Google Agent Framework (ADK) | `src/edgar_sentinel/agent.py` — orchestrator agent + pipeline tools |
| Google Cloud service | Cloud Run Job `edgar-sentinel-daily` + Cloud Scheduler (6:30 AM PT) + Firestore (analyses, state) + Cloud Storage (filing archive) + Artifact Registry/Cloud Build |
| Bonus: additional Google model | Gemma triage stage, `pipeline/parser.py` — gemma3:4b served by Ollama on Cloud Run (`edgar-sentinel-gemma`, private, scale-to-zero, `deploy/gemma/`); gemma4:12b via local Ollama for dev |
| New project, built Aug 3–31 2026 | Fresh repo, full history in-window |

## Quickstart (local)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env   # then edit .env
python -m edgar_sentinel.main run --tickers AAPL MSFT --since 45 --limit 2 --skip-llm
```

`--skip-llm` runs the scan → download → parse pipeline with the built-in fallback parser, no API keys needed. Remove it once `GEMINI_API_KEY` is set (and optionally Ollama+Gemma for the parser).

## Roadmap

1. ✅ Local pipeline: EDGAR scanner, section parser, Gemini analyst, JSON digest
2. ✅ Gemma triage stage (local Ollama; `think: false` — Gemma 4 is a thinking model)
3. ✅ Delta engine: Firestore analysis history, quarter-over-quarter pillar deltas,
   deterministic alert rule, Gemini "what changed" narrative
4. ✅ ADK agent orchestration — Gemini-driven orchestrator with scan/analyze/digest
   tools (`python -m edgar_sentinel.agent`); agentic control flow, deterministic
   execution
5. ✅ Cloud deployment — Cloud Run Job (least-privilege service account) triggered
   daily by Cloud Scheduler; filings archived to Cloud Storage; seen-state and
   analyses in Firestore; verified with a full in-cloud MSFT 10-K run
6. ✅ Gemma in the cloud — Ollama + gemma3:4b as a private Cloud Run service; the
   daily job authenticates with its service identity; verified in-cloud
   (`gemma_notes=['risk_factors']` in Cloud Logging)
7. ✅ Digest delivery — SendGrid email from the daily job (alerts banner, color-banded
   FHS cards, what-changed narrative); API key in Secret Manager, mounted on the job
8. ✅ Dashboard — public read-only Cloud Run service over Firestore:
   https://edgar-sentinel-dashboard-69101307007.us-central1.run.app
   (overview with health bands + alerts + FHS sparklines, company trend pages,
   filing drill-downs with pillar bars, delta narratives, and Gemma notes)
9. ⬜ Architecture diagram, demo video (≤4 min), build-in-public post

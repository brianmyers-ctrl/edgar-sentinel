# Devpost submission — paste-ready fields

**Project name:** EDGAR Sentinel
**Tagline (elevator pitch):** Your always-on SEC filings analyst. EDGAR Sentinel autonomously finds new 10-K and 10-Q filings every day, reads them with a Gemma + Gemini 3.5 pipeline, remembers every prior quarter, and emails you what changed — with a live dashboard for everything it knows.
**Category / track:** The Taskmaster
**Startup Excellence:** submitting on behalf of Artificial Systems Integration (asisystems.io) — corporate email: brianmyers@asisystems.io
**Hosted project URL:** https://edgar-sentinel-dashboard-69101307007.us-central1.run.app
**Code repository:** https://github.com/brianmyers-ctrl/edgar-sentinel (public)
**Demo video:** <YouTube URL — public, ≤ 4:00>
**Bonus — build-in-public post:** <blog URL>
**Bonus — social post:** <X/LinkedIn URL with #AllThingsAgenticHackathon>
**Bonus — additional Google model:** Gemma (gemma3:4b on Cloud Run; gemma4:12b locally) — triage stage

---

## Inspiration

Every quarter, every public company files a 10-K or 10-Q — hundreds of pages of
dense disclosure that almost nobody reads end-to-end. The decision-relevant
signal is specific and buried: a margin inflecting, new risk-factor language,
a going-concern sentence on page 60. I wanted an agent that does the reading
every morning, notices what *changed* since last quarter, and only interrupts
me when it matters.

## What it does

EDGAR Sentinel is an autonomous background agent on Google Cloud. Every day at
6:30 AM Pacific, with no human involved, it:

1. **Scans SEC EDGAR** for new 10-K/10-Q filings across a 30-company watchlist
   (SEC-compliant access: declared User-Agent, rate-limited) and archives the
   raw filings to Cloud Storage.
2. **Parses** each filing into its core sections (risk factors, MD&A,
   financial statements) — robust to inline-XBRL quirks like words split
   across spans and running page headers.
3. **Triages with Gemma** — a small open model (own Cloud Run service via
   Ollama) reads the risk factors and writes terse analyst notes: red flags,
   notable changes, tone.
4. **Scores with Gemini 3.5 on Vertex AI** — the Filing Health Score: five
   weighted pillars (profitability, balance sheet, cash generation, risk flags,
   management signal), each 0–100 with cited rationale, plus extracted metrics
   and three decision-relevant highlights. Schema-enforced JSON, temperature 0,
   composite recomputed in code so configuration — not the model — is
   authoritative.
5. **Remembers and compares** — every analysis persists in Firestore; each new
   filing is compared to the company's prior one, pillar by pillar. A
   **deterministic alert rule** (≥10-point move, classification change, or
   risk-pillar collapse) decides what's urgent; Gemini writes a short
   "what changed" narrative.
6. **Delivers** — an email digest (alerts first) via SendGrid, and a public
   read-only dashboard with health bands, alert feed, FHS trend sparklines,
   and per-filing drill-downs showing every pillar's reasoning, the
   quarter-over-quarter delta, and Gemma's notes.

Live right now: 30 companies, 58+ filings, 8+ real alerts — including Plug
Power sliding Caution → Distress, Salesforce and Meta dropping a band, and
Coinbase and AMC genuinely recovering. Running unattended every morning since
August 14.

## How we built it

- **Orchestration:** Google **Agent Development Kit** — a Gemini-powered
  orchestrator agent whose tools are the pipeline stages (`scan_new_filings`,
  `analyze_filing`, `write_digest`). The agent decides the run flow and writes
  the run report; tested Python does the deterministic work. *Agentic control
  flow, deterministic execution.*
- **Models:** Gemini 3.5 Flash via **Vertex AI** (analysis, delta narrative,
  orchestrator); **Gemma** via Ollama on **Cloud Run** (triage notes).
- **Infrastructure:** Cloud Run Job + **Cloud Scheduler** (daily trigger),
  **Firestore** (analyses, state, agent memory), **Cloud Storage** (raw filing
  archive), **Secret Manager** (the single secret), **Artifact Registry / Cloud
  Build** (images), a second Cloud Run service for the dashboard.
- **Security posture:** three service identities with least privilege — the
  job (Vertex user, Firestore user, bucket writer, Gemma invoker, secret
  accessor), the private Gemma service (invoker-only), and the public dashboard
  (Firestore *viewer* only). No credential in code, images, or the repo.
- **Quality:** 20 unit tests (parser regressions over real filings, delta and
  alert rules, store, digest rendering, dashboard pages); per-filing error
  isolation so one bad filing can never kill the daily run.

## Challenges we ran into

- **Gemma 4 is a thinking model:** triage calls returned empty strings — the
  model spent its whole output budget reasoning. `think: false` fixed it, and
  empty notes now log loudly instead of vanishing.
- **Ollama silently truncates long prompts** by default — the "cleaned" text
  from an early full-rewrite design was lossy. That failure reshaped Gemma's
  role from rewriting text to writing *notes about* text: faster, honest, and
  more useful to the downstream model.
- **Inline-XBRL HTML splits words across spans** ("RIS K FACTORS") and repeats
  item headings as page headers — defeating naive section detection. Fix:
  whitespace-tolerant heading matching plus "take the match with the longest
  following body." Microsoft's risk factors went from 0 to 80k characters.
- **A garbage-collection race** in the SDK client (created inline, collected
  mid-request) → cached singleton.
- **Organization policies** blocking Vertex models and stripping default
  service-account grants — solved with scoped, least-privilege IAM.

## Accomplishments that we're proud of

Truly autonomous: it has run itself every morning since deployment. The delta
engine caught Apple's management turning cautious on component costs a full
quarter before it showed up anywhere else in the filing (−10 on the management
signal pillar while the composite barely moved). Every score is auditable
pillar by pillar, and alerts come from a rule you can read, not model mood.

## What we learned

Smaller models are best used to *locate and flag*, not to rewrite; generation
is the expensive direction. Determinism belongs in the layers that judge truth
(section slicing, weighting, alert rules, state), and the LLM belongs in the
layers that judge meaning. And production-mindedness is mostly finding the
silent failures before demo day — five of them, all logged in the build log.

## What's next

An XBRL cross-verification layer (every extracted metric checked against the
SEC's own structured companyfacts data, with a verified badge), an 8-K
material-events lane for near-real-time alerts, and Gemma-as-section-locator
as the fallback when heuristics fail on unusual filer formats.

## Technologies

Python 3.12, Google ADK, google-genai, Vertex AI (Gemini 3.5 Flash), Gemma
(gemma3:4b / gemma4:12b) via Ollama, Cloud Run (jobs + services), Cloud
Scheduler, Firestore, Cloud Storage, Secret Manager, Cloud Build, Artifact
Registry, FastAPI, BeautifulSoup/lxml, pydantic, SendGrid, pytest.

## Data sources

SEC EDGAR (company_tickers.json, submissions API, filing archive) — public
data accessed under the SEC's fair-access policy.

## Disclosure

Built entirely during the submission period (first commit August 13, 2026).
No pre-existing code. AI coding assistance (Claude) was used throughout and is
disclosed via co-author trailers in the commit history. EDGAR Sentinel produces
automated research summaries derived from SEC filings — not investment advice.

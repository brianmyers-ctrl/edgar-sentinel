# Demo video — script & shot list (target 3:45, hard cap 4:00)

**Recording setup:** OBS or Win+G Game Bar, 1080p, capture the browser and one
terminal. Judges explicitly reward a **live, unedited** demo — do the middle
segment in one take, cuts between segments are fine. No third-party logos on
screen (close Slack/Discord/other tabs; a clean browser profile helps).

**Prep before recording (5 min):**
- Open tabs in order: (1) dashboard overview, (2) a Distress filing page
  (PLUG or BYND), (3) Cloud Run console (jobs + services), (4) Cloud Scheduler,
  (5) Firestore `analyses` collection, (6) your gmail inbox, (7) the GitHub repo.
- Terminal ready with this line pre-typed (do NOT run yet):
  `gcloud run jobs execute edgar-sentinel-daily --region us-central1 --project edgar-sentinel --args="--since,150,--limit,1,--tickers,NKE,--ignore-state" --wait`
  (NKE re-analysis takes ~2 min with Gemma — rehearse once the day before to
  confirm timing; any not-yet-refreshed ticker works.)

---

## 0:00–0:25 · The problem (talking over the dashboard overview)

> "Every quarter, every public company files a 10-K or 10-Q — hundreds of pages
> of dense disclosure. The information that moves decisions is in there: margin
> shifts, new risk language, going-concern hints. Nobody has time to read them
> all. So I built an agent that does — every morning, on its own.
> This is EDGAR Sentinel."

## 0:25–1:10 · What it produces (screen: dashboard)

- Scroll the watchlist table slowly (weakest first).
> "It watches thirty companies. Every filing gets a Filing Health Score from
> five weighted pillars — profitability, balance sheet, cash generation, risk
> flags, management signal — scored by Gemini 3.5 with cited rationale, never
> just vibes."
- Point at the alert feed.
> "And because it remembers every prior filing in Firestore, it notices
> *change*. Plug Power sliding from Caution to Distress. AMC climbing out of
> it. These alerts come from a deterministic rule, not model mood — a ten-point
> move, a band change, or a risk-pillar collapse."
- Click into PLUG's filing page: pillar bars, delta block, Gemma notes.
> "Every score is auditable: pillar by pillar, with the model's reasoning, the
> quarter-over-quarter delta, and a second opinion from a Gemma model — plus a
> link to the raw filing on SEC.gov."

## 1:10–2:40 · Live, unedited run (screen: terminal + inbox — ONE TAKE)

- Hit Enter on the pre-typed command.
> "This is the same job Cloud Scheduler fires every morning at 6:30 — running
> right now, live, on Cloud Run. Watch the agent work: it's built on Google's
> Agent Development Kit — a Gemini-powered orchestrator that decides which
> tools to call."
- As logs stream, read them out: `[adk] agent -> scan_new_filings`,
  `[archive] gs://…`, `[gemma] triage notes`, `[analyze] FHS …`.
> "There's the ADK agent choosing its tools… the raw filing archived to Cloud
> Storage… Gemma — running on its own Cloud Run service — writing triage notes
> on the risk factors… and Gemini scoring the filing against the framework."
- When `[digest] emailed` appears, switch to gmail, open the email.
> "And the loop closes with a human: the digest lands in my inbox. That's the
> whole point — I sleep, it reads."

## 2:40–3:25 · Proof it's on Google Cloud (console tabs, brisk)

- Cloud Run tab: show the job + two services (gemma, dashboard).
> "Everything runs on Google Cloud: a Cloud Run job for the daily agent, a
> private Cloud Run service hosting Gemma on Ollama, and the public dashboard."
- Scheduler tab: show the trigger and its run history.
> "Cloud Scheduler has fired it every morning since August 14th — here's the
> history; every run green, no human involved."
- Firestore tab: expand `analyses`.
> "Firestore holds every analysis and the agent's memory across weeks."
- Flash the architecture diagram (GitHub docs/architecture.md).
> "Agentic control flow, deterministic execution: Gemini decides what runs;
> tested code decides what's true."

## 3:25–3:50 · Wrap (dashboard overview again)

> "EDGAR Sentinel: Gemini 3.5 on Vertex AI, orchestrated with the ADK, Gemma
> as a second-opinion triage model, on Cloud Run, Firestore, and Cloud
> Storage. Thirty companies, fifty-six filings analyzed, eight live alerts —
> and by the time you watch this, this morning's run has already added more.
> Everything's open on GitHub, and the dashboard link is in the description.
> Not investment advice — just an agent doing the reading."

---

**Upload:** YouTube, **Public** (not unlisted), title
"EDGAR Sentinel — autonomous SEC filing analysis (All Things Agentic Hackathon)".
Description: dashboard URL + repo URL + "Built for the All Things Agentic
Hackathon". Confirm ≤ 4:00 — anything past 4 minutes is not evaluated.

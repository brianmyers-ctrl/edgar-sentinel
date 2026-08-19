# EDGAR Sentinel — Build Log

Running record of progress, decisions, and lessons. (Also source material for the
build-in-public post — a Stage 3 bonus contribution.)

## Aug 13, 2026 — Day 1: from empty folder to working delta engine

**Groundwork**
- Fact-checked the hackathon against primary sources (Devpost page, Official Rules,
  launch video); corrected a Gemini Deep Research report that had wrong tracks and
  wrong judging weights. Verified facts live in `Information/Official Hackathon
  Facts (Verified).md` (project root).
- Registered intent: **Taskmaster track**, $150 credit form submitted.
- GCP project `edgar-sentinel` created under asisystems.io org; 8 APIs enabled;
  Firestore database created (us-central1).

**Built and verified today**
1. **Scaffold** — SEC-compliant EDGAR client (declared User-Agent, throttling,
   ticker→CIK resolution, submissions API), heuristic section parser
   (risk factors / MD&A / financials), Filing Health Score framework
   (docs/investment-model.md), CLI, Dockerfile.
2. **Gemini 3.5 analyst on Vertex AI** — structured JSON output (pydantic schema
   enforced), pillar scores with cited rationale, composite recomputed in code so
   config weights are authoritative. First real output: Apple 10-Q scored 88/Strong
   with accurate extracted financials.
3. **Gemma triage stage** — local Ollama (gemma4:12b) produces compact red-flag
   notes per section that ride along to Gemini as a second opinion. Scoped to
   sample-scale by design (`GEMMA_SECTIONS`); scale story is Cloud Run.
4. **Delta engine** — Firestore-backed analysis history; each filing compared to
   the company's prior one: FHS/pillar deltas, classification change, deterministic
   alert rule (|ΔFHS| ≥ 10, class change, or risk pillar −15), Gemini "what changed"
   narrative. Live result: Apple QoQ 88→87, no alert, management-signal −10 (caught
   the cautious tone on component costs), metric trends with real period-over-period
   numbers. Both analyses visible in Firestore.
5. **Tests** — 8 passing (EDGAR filter/URL logic, delta math, alert rules, store
   prior-lookup).

**Bugs found & fixed (each one a demo-day landmine defused)**
- Ollama default context window silently truncated large prompts → "cleaned" text
  was actually lossy; redesigned Gemma's job from full-text rewrite to compact
  triage notes (faster, better, honest).
- **Gemma 4 is a thinking model**: without `think: false` it burns the whole output
  budget reasoning and returns an empty string. Empty notes now log loudly.
- Org policy `constraints/vertexai.allowedModels` blocked Gemini 3.5; added a
  project-scoped override (merge-with-parent) after granting Org Policy Admin.
- google-genai client garbage-collected mid-request when created inline
  (`Cannot send a request, as the client has been closed`) → cached singleton.
- Per-filing error isolation: one bad filing logs `[error]` and stays unmarked for
  retry; the daily run continues.
- Analyst temperature pinned to 0 for reproducible scores.

**M1 — ADK orchestration (completed same day, ahead of the Aug 14–15 plan)**
- `agent.py`: Gemini-powered ADK orchestrator (google-adk 2.6.3, async runner)
  with the pipeline stages as function tools (scan_new_filings / analyze_filing /
  write_digest). The agent chose the correct tool sequence and chronological
  order unprompted on its first run and writes the end-of-run report itself.
- Design principle for the video: **agentic control flow, deterministic
  execution** — the LLM decides what runs; tested code decides what's true.
- Two more landmines defused: Windows cp1252 consoles crash on exotic characters
  in model output (now UTF-8 with replacement, set centrally in config), and the
  ADK sync runner is deprecated (moved to run_async).
- Temperature-0 payoff: Apple's two quarters now score an identical, reproducible
  FHS 88/88 (delta 0) — earlier ±1–2 spread was sampling noise.

**M2 — Cloud deployment (completed Aug 13 evening, two days ahead of plan)**
- Storage went cloud-native: seen-state moved from state.json into Firestore
  (`state/seen_accessions`), raw filings archive to `gs://edgar-sentinel-filings`.
- Infra: service account `edgar-sentinel-job` (aiplatform.user, datastore.user,
  logging.logWriter, bucket-scoped objectAdmin, run.invoker for Scheduler),
  Artifact Registry repo, Cloud Build image (59s build), Cloud Run Job
  `edgar-sentinel-daily` (1 CPU / 1 GiB / 20 min timeout), Cloud Scheduler
  trigger `30 6 * * *` America/Los_Angeles.
- One org fight as predicted: Cloud Build's default compute SA had no storage
  access (org strips default grants) → roles/cloudbuild.builds.builder.
- **DoD met:** full in-cloud run analyzed Microsoft's FY2026 10-K (FHS 90,
  Strong — Azure +41%, capex +$51.4B, $28.9B IRS dispute flagged), archived the
  raw filing to GCS, wrote analysis + state to Firestore, exit(0). First fully
  unattended scheduled run: tomorrow 6:30 AM PT.
- Known gap carried forward: the heuristic parser misses `risk_factors` on
  MSFT-format filings (TOC heuristic); Gemma cloud triage (M3) and/or a
  smarter section locator will close it.

**Open items (as of Aug 13 close)**: first commit made (772181c); org policy admin
role can be revoked from the gmail account now that the override is applied.

## Aug 14–17 — the agent ran itself

Cloud Scheduler fired the job at 6:30 AM PT on **Aug 14, 15, 16, and 17 — four
for four, all succeeded, zero human involvement**. Each run: scanned the
watchlist, correctly found no new filings in the 3-day window (none were filed),
wrote a clean digest, reported "no alerts", exit(0). This is the demo line:
*"it has been running every morning since the day I deployed it."*

## Aug 17 — M3 in progress + parser fix

- **Parser gap closed.** Root cause of the missing MSFT risk factors: inline-XBRL
  HTML splits words across spans (`RIS K FACTORS`) and MSFT repeats "Item 1A" as
  a running page header through the whole section, defeating "take the last
  match". Fix: match headings with optional intra-word whitespace, and choose
  the match with the *longest following body*. MSFT risk factors 0 → 80k chars;
  Apple unchanged; 6 new parser tests incl. a regression over cached real
  filings. 14/14 passing.
- Job image v2 (parser fix + identity-token auth to a private Gemma service)
  built and rolled out.

**M3 — Gemma cloud proof: DONE (Aug 17, a day early)**
- `edgar-sentinel-gemma`: Ollama with gemma3:4b baked into the image (no
  cold-start download), private Cloud Run service, 4 CPU / 8 GiB, concurrency 1,
  scale-to-zero, 60×10s startup probe for model load. Job SA granted
  run.invoker; the triage stage sends an identity token (no-op on localhost).
- Cold-start smoke test: 90s to first token (model load), then a sensible
  analyst-grade answer. Warm calls are far faster.
- **DoD met:** cloud execution `edgar-sentinel-daily-7dhxz` on MSFT's 10-K logged
  `sections=[..., 'risk_factors'], gemma_notes=['risk_factors']` — parser fix and
  cloud Gemma both verified in one unattended run. FHS 90 Strong; highlights
  now include the OpenAI recapitalization gain ($6.5B) and capex +79.6% to
  $115.9B. Bonus point (Gemma) is now provable from Cloud Logging + Cloud Run
  console, not just from code.
- Cost posture: Gemma scoped to `risk_factors` only in the cloud job so CPU
  inference stays within a few minutes/filing; scale story = GPU Cloud Run.

## Aug 18–19 — M4: the morning email (DONE)

- SendGrid sender identity verified, Mail-Send-only API key stored in **Secret
  Manager** (`sendgrid-api-key`; empty v1 from a terminal mishap disabled, v2
  live) and mounted on the Cloud Run Job as `SENDGRID_API_KEY` — the job SA has
  `secretmanager.secretAccessor`; no key ever touched the repo or the image.
- `digest.py`: plain-text + HTML renderers (alerts banner first, FHS cards
  color-banded Strong→Distress, three highlights, what-changed narrative),
  best-effort sender that logs and never raises. `write_digest` tool emails
  when there is something to report (`DIGEST_ALWAYS` for a quiet-day heartbeat).
- Bug caught in the cloud, not the demo: first send came back **415** — body was
  passed as a pre-serialized string without a JSON content-type. Fixed with
  `json=payload`. Failure was contained exactly as designed: logged, run still
  exit(0).
- **DoD met (job image v4):** cloud execution analyzed AAPL's two quarters with
  cloud Gemma triage and logged
  `[digest] emailed to brianrmyers0912@gmail.com: EDGAR Sentinel 2026-08-19: 2 new filings analyzed`.
- Milestones M1–M4 complete as of Aug 19; plan had M4 finishing Aug 20.

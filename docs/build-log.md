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

**Open items**: repo has no first commit yet (provenance!); org policy admin role
can be revoked from the gmail account now that the override is applied.

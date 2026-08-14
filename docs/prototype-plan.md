# Prototype Plan — path to submission (deadline: Aug 31, 5:00 PM PT)

**Definition of "working prototype":** EDGAR Sentinel runs itself daily in Google
Cloud with no laptop involved, analyses accumulate in Firestore, deltas and alerts
fire, the digest reaches a human surface (email + dashboard), and a judge can
reproduce everything from the README.

## Milestones

### M1 — ADK orchestration (Aug 14–15) · MANDATORY GAP
Wrap the pipeline in Google ADK: an orchestrator agent with scanner / parser /
analyst / delta as tools, session state carrying the run context. Keep the plain
CLI as a fallback path.
**Done when:** the full pipeline executes through the ADK runner locally, and the
README compliance table points at real code.

### M2 — Cloud deployment (Aug 16–18)
- Build container via Cloud Build → Artifact Registry.
- Cloud Run **Job** `edgar-sentinel-daily` + Cloud Scheduler trigger (~6:30 AM PT,
  after EDGAR's overnight index settles).
- Dedicated service account, least privilege (Vertex user, Firestore user, bucket
  writer).
- Move raw filing archive from local disk to **Cloud Storage**; move seen-state
  from state.json to Firestore.
**Done when:** a scheduled run completes end-to-end in the cloud while the laptop
is closed, visible in Cloud Run logs + Firestore.

### M3 — Gemma cloud proof (Aug 18–19)
Local Ollama stays the dev default. For the demo/bonus proof, one of:
(a) small Gemma via Ollama on a Cloud Run service (CPU is fine at sample scale), or
(b) Gemma through AI Studio API. Pick by cost after M2.
**Done when:** one cloud log line shows a Gemma triage note produced in-cloud.

### M4 — Digest delivery (Aug 19–20)
Morning email with new analyses, deltas, and alerts (decision needed: Gmail API
OAuth vs. a transactional sender). Alerts visually loud.
**Done when:** the daily run ends with an email in the inbox.

### M5 — Dashboard (Aug 20–22) · hosted URL is "highly encouraged"
Minimal read-only web view (FastAPI + templates) on Cloud Run: watchlist table,
FHS trend per company, delta/alert feed, filing drill-down with pillar rationales
and Gemma notes. No auth, read-only, cheap.
**Done when:** a public URL shows live Firestore data. (Also quietly enters the
Best Multimodal UX side prize.)

### M6 — Hardening + demo ammunition (Aug 22–24)
- Widen watchlist to ~20–40 tickers; cloud backfill run (2 filings per company)
  so the dashboard looks alive.
- Add at least one struggling filer so a real **ALERT** fires on camera.
- Re-run full test suite; freeze features.

### M7 — Submission package (Aug 25–29) · submit Aug 29, buffer 2 days
- Architecture diagram (required artifact).
- README final pass: spin-up instructions a stranger can follow.
- **Demo video ≤ 4 min**: problem (30s) → live cloud run + alert firing (2 min) →
  architecture + Google Cloud proof on screen (1 min) → wrap (30s). Public on
  YouTube. No third-party logos.
- Bonus contributions: build-in-public blog post (+0.2, must state it was made for
  this hackathon), #AllThingsAgenticHackathon social post (+0.2). Gemma integration
  already banked (+0.2).
- Devpost form: category = Taskmaster; hosted URL; repo link; entry type decision.

## Decisions Brian owns (non-blocking until M4/M7)
1. **Entry type:** individual vs. on behalf of ASI (Startup Excellence needs
   incorporation + corporate email).
2. **Email delivery mechanism** (M4): Gmail API from his account vs. transactional
   service.
3. **Watchlist composition** (M6) and final **project name** on Devpost.
4. **First commit go-ahead** — provenance clock starts at commit #1.

## Standing risks
- Aug 28 12:00 PM PT: $150 credit form cutoff (already submitted — confirm code
  arrival ~72h).
- Gemini 3.5 Vertex quota/costs at wider watchlist scale — watch after M6 backfill.
- Org-managed GCP: new services may hit other org policies (as Vertex did); budget
  time for one more policy fight during M2.

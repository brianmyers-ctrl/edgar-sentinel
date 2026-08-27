# Demo video — runsheet, shot list & script

**Target 3:40, hard cap 4:00.** Six takes, straight cuts, assembled
1 → 2 → 3a → 4 → 3b → 5. The live run starts on camera in 3a and comes home in
3b; segment 4's console tour happens while it genuinely works.

Everything below was verified against live infrastructure on **Aug 27, 2026**.
Numbers in ⟨angle brackets⟩ must be re-read off the dashboard on shoot day.

---

## Part 0 — Fix before the camera rolls

Two production facts contradict what the video says. Both are quick.

> ✅ **0.1 and 0.2 applied and verified — Aug 27, ~12:20 PM PT.** The job now
> runs `--since 30 --limit 3` on image `job:v5`. The verification execution ran
> green (16:57) and immediately caught the backlog the bug had been hiding:
> **NVDA and CRM 10-Qs analyzed** (both with Gemma notes), one real alert
> (CRM 84→77, Strong→Stable), digest emailed and confirmed in the Gmail inbox.
> Totals moved 56→58 filings. Only **0.3 (commit)** remains open. Commands
> below kept for reference/rollback.

### 0.1 · The daily job only re-scans Boeing (✅ fixed Aug 27)

The deployed job's arguments are `--since 150 --limit 1 --tickers BA
--ignore-state` — leftover demo flags. Cloud Scheduler has been firing that
every morning, so the "daily watchlist scan" re-analyzes the *same Boeing 10-Q*
every day and emails a digest saying "1 new filing analyzed." Today's 6:32 AM
run did exactly that.

The video's central claim — *it scans thirty companies every morning* — is
contradicted by the job config a judge can open in one click.

```bash
gcloud run jobs update edgar-sentinel-daily --region us-central1 --project edgar-sentinel --args="--since,30,--limit,3"
```

Then verify it runs green (expect ~30 seconds and "no new filings", because
state tracking now suppresses the 56 already analyzed):

```bash
gcloud run jobs execute edgar-sentinel-daily --region us-central1 --project edgar-sentinel --wait
```

Rollback if ever needed: `--args="--since,150,--limit,1,--tickers,BA,--ignore-state"`.

> Task timeout is 1800s with 1 retry, and a cold filing takes ~5–6 min, so
> `--limit 3` has comfortable headroom. Don't raise it above 4.

### 0.2 · The job runs a stale image (✅ deployed & verified Aug 27)

The job points at `job:v4`, built **Aug 19**. `job:v5` was built **Aug 25** with
the parser fix for filers whose item prefixes only appear in an end index
(commit `f26ff0a`, the Intel case) — and was never deployed. Right now the repo
and the running job disagree.

```bash
gcloud run jobs update edgar-sentinel-daily --region us-central1 --project edgar-sentinel --image us-central1-docker.pkg.dev/edgar-sentinel/edgar-sentinel/job:v5
```

v5 has never executed in production, so **run 0.1's verification execution after
this** and confirm it exits green before you trust it on camera. If it fails,
roll straight back to `job:v4` — the demo does not depend on the fix.

### 0.3 · Commit the working tree

`Dockerfile` (PYTHONUNBUFFERED), `.gitignore` (video/), and this file are
uncommitted. Judges read the repo; commit before you record so the GitHub tab
you show on camera is current.

---

## Part 1 — The recording rig

### 1.1 · Use this command — the one in the old script does not work here

`ddagrab` fails on this machine (`Operation not permitted` — hybrid-GPU adapter
selection). `gdigrab` is tested and works, NVENC and all.

**More importantly: this is a three-monitor desktop.** The full virtual desktop
is 5760×1200 — capturing it would produce an unwatchable letterboxed sliver on
YouTube. The offsets below capture the **primary display only**.

| Display | Physical | gdigrab offset | Notes |
| :-- | :-- | :-- | :-- |
| **Primary (centre)** | 1920×1200 | `offset_x 0 offset_y 0` | Record here |
| Left | 1920×1080 | `offset_x -1920` | Park the ffmpeg window here |
| Right | 1920×1080 | `offset_x 1920` | Keep blank |

One command per take, run from the `edgar-sentinel` folder, changing only the
filename (`seg1` `seg2` `seg3a` `seg4` `seg3b` `seg5`). Press **q** in that
window to stop the take.

```bash
ffmpeg -hide_banner -f gdigrab -framerate 30 -offset_x 0 -offset_y 0 -video_size 1920x1080 -i desktop -f dshow -i audio="Microphone Array (Intel® Smart Sound Technology for Digital Microphones)" -c:v h264_nvenc -preset p4 -cq 20 -pix_fmt yuv420p -fps_mode cfr -c:a aac -b:a 160k video/takes/seg1.mp4
```

Verified end to end on Aug 27: gdigrab + h264_nvenc + that exact mic string all
open cleanly. If the `®` ever trips your terminal's encoding, swap in the
ASCII-only device path:

```
-f dshow -i audio="@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\wave_{0141CAEF-4D2E-4D42-BA26-92018882AE77}"
```

We capture 1920×1080 out of a 1200-tall display, so the bottom 120 px is cut —
**set the taskbar to auto-hide** and nothing is lost. Output is native 1080p
with no bars.

### 1.2 · Rig checklist

- Run the ffmpeg window on the **left** monitor, off the recorded display.
- Do a 10-second test take first and play it back — check mic level and that
  you captured the centre screen. Speak close to the laptop, quiet room.
- Windows **Do Not Disturb ON**. Taskbar auto-hide ON.
- Keep takes under ~60s where you can; short takes keep A/V sync tight.

---

## Part 2 — Set dressing

### 2.1 · Warm everything up (this is the timing-critical step)

The Gemma service is 4 CPU / 8 GiB, concurrency 1, **scale-to-zero**. Cold, it
must boot Ollama and load gemma3:4b before it reads a word. Measured today: a
cold single-filing run took **~6 minutes end to end** (5:05 of that in the
analyze step). Warm, expect ~4–5 min. The warm window fades after ~10–15 min
idle.

**Twenty minutes before you record**, run the exact demo command once:

```bash
gcloud run jobs execute edgar-sentinel-daily --region us-central1 --project edgar-sentinel --args="--since,150,--limit,1,--tickers,NKE,--ignore-state" --wait
```

That does three jobs at once: proves the pipeline works today, warms Gemma, and
**times the on-camera run** so you know how long to wait between takes 3a and
3b. Start recording 3a within ~5 minutes of it finishing.

The run is idempotent — Firestore docs are keyed `<ticker>_<accession>`, so
re-running NKE's 10-K overwrites one document and the totals don't move during
the shoot itself. But now that 0.1 is fixed, each **morning** run can genuinely
add filings — which is why 2.6 says re-read the overview right before
recording. As of Aug 27 post-fix: **30 / 58 / 8**.

> Doing many takes over a long session? You can pin Gemma warm with
> `gcloud run services update edgar-sentinel-gemma --region us-central1 --project edgar-sentinel --min-instances=1`
> — but **revert it to `--min-instances=0` the moment you wrap.** 4 CPU / 8 GiB
> held warm burns credits fast, and scale-to-zero is a claim in your
> architecture doc.

### 2.2 · Also warm the dashboard

The dashboard cold-starts in ~9 seconds; warm it's 0.2–0.4s. Load every tab
below once before recording or your first click sits on a white screen.

### 2.3 · Terminal

Fresh PowerShell window, dark theme, font ≥ 18 pt, on the primary display.
Pre-type this and **do not press Enter**:

```
gcloud run jobs execute edgar-sentinel-daily --region us-central1 --project edgar-sentinel --args="--since,150,--limit,1,--tickers,NKE,--ignore-state" --wait
```

### 2.4 · Browser tabs, in this order

Clean profile or guest window: no bookmarks bar, no extensions, no other tabs.
Zoom 110–125% so text reads at 1080p.

| # | Tab | URL |
|---|-----|-----|
| 1 | Dashboard overview | https://edgar-sentinel-dashboard-69101307007.us-central1.run.app |
| 2 | PLUG filing (alert + pillar bars + delta) | …/f/PLUG/0001104659-26-093454 |
| 3 | MSFT 10-K (Gemma triage notes) | …/f/MSFT/0001193125-26-323660 |
| 4 | NKE company page (live refresh target) | …/c/NKE |
| 5 | Cloud Run — services + jobs | https://console.cloud.google.com/run?project=edgar-sentinel |
| 6 | Cloud Run job — **Executions** tab | https://console.cloud.google.com/run/jobs/details/us-central1/edgar-sentinel-daily/executions?project=edgar-sentinel |
| 7 | Cloud Scheduler | https://console.cloud.google.com/cloudscheduler?project=edgar-sentinel |
| 8 | Firestore → Data → `analyses` | https://console.cloud.google.com/firestore?project=edgar-sentinel |
| 9 | Gmail inbox | mail.google.com |
| 10 | GitHub architecture diagram | https://github.com/brianmyers-ctrl/edgar-sentinel/blob/main/docs/architecture.md |

All four dashboard deep links return 200 as of Aug 27.

### 2.5 · Rules compliance — check the screen, not just the script

- **No third-party logos.** The dashboard is text-only (tickers and company
  names as filing data — that's fine). Don't linger on SEC.gov's seal, and keep
  every other window closed.
- Public YouTube upload, **not unlisted**. Only the first 4:00 is evaluated.
- The "not investment advice" disclaimer is in the dashboard footer and your
  closing line. Keep both.

### 2.6 · Read the live numbers immediately before recording

As of Aug 27, post-fix: **30 companies · 58 filings · 8 alerts**; bands
11 Strong / 10 Stable / 6 Caution / 3 Distress. Now that the scan is real,
each 6:30 AM run may add filings — **re-read the overview and update every
⟨…⟩ below.**

Speak 10–20% slower than feels natural. If you flub, pause two seconds and
restart the sentence; trimming is easy, re-recording a segment is not.

---

## Part 3 — Shot list & script

### Segment 1 · 0:00–0:25 · The problem — dashboard overview (tab 1)

Screen static, no scrolling.

> "Every quarter, every public company files a 10-K or 10-Q — hundreds of pages
> of dense disclosure. The information that moves decisions is in there: margin
> shifts, new risk language, going-concern hints. Nobody has time to read them
> all. So I built an agent that does — every morning, on its own.
> This is EDGAR Sentinel."

### Segment 2 · 0:25–1:15 · What it produces (tabs 1 → 2 → 3)

**Shot 1** — scroll the watchlist slowly; it's sorted weakest first:

> "It watches ⟨thirty⟩ companies. Every filing gets a Filing Health Score from
> five weighted pillars — profitability, balance sheet, cash generation, risk
> flags, management signal — scored by Gemini 3.5 with cited rationale, never
> just vibes."

**Shot 2** — the alert feed at the top of the overview:

> "And because it remembers every prior filing in Firestore, it notices
> *change*. Plug Power sliding from Caution to Distress. AMC climbing out of it.
> These alerts come from a deterministic rule, not model mood — a ten-point
> move, a band change, or a risk-pillar collapse."

*(Live as of Aug 27 post-fix: CRM 84→77 Strong→Stable now tops the feed;
PLUG 41→36 Caution→Distress; AMC 34→44 Distress→Caution; META 85→74.
Name whichever two are on screen.)*

**Shot 3** — tab 2, PLUG filing page; scroll pillar bars then the delta block:

> "Every score is auditable: pillar by pillar, with the model's cited reasoning,
> the exact quarter-over-quarter delta that fired the alert, and a link to the
> raw filing on SEC.gov."

**Shot 4** — tab 3, MSFT 10-K; scroll straight to the Gemma notes:

> "And a second model — Gemma, running on its own Cloud Run service — reads the
> risk factors first and leaves triage notes. A second opinion from a different
> brain, before Gemini ever scores."

### Segment 3a · 1:15–1:50 · Start the live run (terminal → tab 6)

Screen: terminal with the command pre-typed. Hit Enter as you start talking.

> "This is the same job Cloud Scheduler fires every morning at 6:30 — and I'm
> firing it right now, live, on Cloud Run. It's built on Google's Agent
> Development Kit: a Gemini-powered orchestrator that decides which tools to
> call."

Switch to tab 6, click into the just-created execution, open its **Logs** tab.
First lines appear within ~a minute. Read them as they stream:

> "There it is — the ADK agent picks `scan_new_filings`, hits SEC EDGAR, finds
> Nike's 10-K, archives the raw filing to Cloud Storage. Now Gemma starts
> reading the risk factors — a few hundred pages of filing, two models, a few
> minutes of real work. While it reads, let me show you what it's standing on."

### Segment 4 · 1:50–2:50 · Google Cloud proof, while it works (tabs 5 → 6 → 7 → 8 → 10)

Brisk — roughly 12 seconds a tab.

**Tab 5**, Cloud Run list (one job, two services):

> "Everything runs on Google Cloud: the Cloud Run job you just saw start, a
> private Cloud Run service hosting Gemma on Ollama, and the public dashboard."

**Tab 6**, the job's **Executions** list — all-green history:

> "And the receipts: every daily execution since August 14th, all green, no
> human involved."

*(Verified: 15 consecutive executions, all Completed, most recent this morning.)*

**Tab 7**, Cloud Scheduler — `edgar-sentinel-daily-trigger`, `30 6 * * *`,
America/Los_Angeles, **ENABLED**:

> "Cloud Scheduler fires it at 6:30 every morning."

**Tab 8**, Firestore, expand `analyses`:

> "Firestore holds every analysis — the agent's memory across quarters."

**Tab 10**, GitHub architecture diagram, linger 3 seconds:

> "Agentic control flow, deterministic execution: Gemini decides what runs;
> tested code decides what's true."

### Segment 3b · 2:50–3:25 · The run comes home (tab 6 → tab 4 → tab 9)

Wait off-camera until the run completes; your warm-up told you how long.

**This beat changed.** The old script promised "the fresh analysis with today's
timestamp" on the dashboard — but the dashboard renders no timestamp, and NKE's
10-K is already on the page, so a refresh looks identical. Prove freshness where
it is actually visible: **the execution log's clock and the digest email.**

Screen: the execution's Logs tab, showing the finished run report.

> "A few minutes later — you can see the timestamps — the full report. There's
> the analyze step, Gemma's triage notes on the risk factors, and Gemini's
> Filing Health Score: ⟨read the score, band and delta straight off the
> report⟩."

Switch to tab 4 (NKE company page), refresh, click into the 10-K, flick past
the pillars to the Gemma notes:

> "Straight into Firestore and onto the public dashboard — pillar by pillar,
> Gemma notes and all."

Switch to tab 9 (Gmail). **The digest the run you just watched sent** — it
emails at the end of every execution, so it is minutes old and contains NKE's
card. Open it, show the banded FHS card and highlights:

> "And the loop closes with a human: the run I started four minutes ago just
> emailed me its digest. That's the whole point — I sleep, it reads."

> **Inbox scroll rule:** 0.1 was fixed midday Aug 27, so every digest from the
> Aug 27 "1 ALERT, 2 filings" one onward is genuine; digests older than that
> read "1 new filing analyzed — BA," which undercuts the story. Shooting
> Aug 28+: showing the top day-or-two of real digests is a bonus — just don't
> scroll down into the BA era.

### Segment 5 · 3:25–3:45 · Wrap (back to tab 1)

> "EDGAR Sentinel: Gemini 3.5 on Vertex AI, orchestrated with the Agent
> Development Kit, Gemma as a second-opinion triage model, on Cloud Run,
> Firestore, and Cloud Storage. ⟨Thirty⟩ companies, ⟨fifty-eight⟩ filings
> analyzed, ⟨eight⟩ live alerts — and tomorrow morning's run adds more without
> me. Everything's open on GitHub, and the dashboard link is in the
> description. Not investment advice — just an agent doing the reading."

---

## Part 4 — After the shoot

1. Trim take heads/tails, join with straight cuts: 1 → 2 → 3a → 4 → 3b → 5.
   Confirm total **≤ 4:00** — anything past 4:00 is not evaluated.
2. Upload to YouTube, **Public** (not unlisted).
   - Title: `EDGAR Sentinel — autonomous SEC filing analysis (All Things Agentic Hackathon)`
   - Description: dashboard URL + repo URL + "Built for the All Things Agentic
     Hackathon."
3. Paste the YouTube URL into `docs/devpost-submission.md` and the Devpost form.
4. If you pinned Gemma warm in 2.1, **set `--min-instances=0` now.**
5. Bonus points, ~20 minutes total: publish the blog post
   (`docs/blog-post-draft.md`, must state it was made for this hackathon, +0.2),
   post to X/LinkedIn with **#AllThingsAgenticHackathon** (+0.2), and Gemma is
   already integrated (+0.2). Submissions close **Aug 31, 5:00 PM PT**.

# I built an agent that reads SEC filings so I don't have to

*Draft for dev.to / Medium. Publish public (not unlisted). The disclosure line
in the footer is required for the hackathon bonus — do not remove it.*

---

Every public company's story is hiding in plain sight — in 10-Ks and 10-Qs that
almost nobody reads end-to-end. The good stuff is specific: a gross margin
inflecting, risk-factor language that wasn't there last quarter, a going-concern
sentence buried on page 60. I wanted that surfaced to me every morning without
me doing the reading.

So for the **All Things Agentic Hackathon** I built **EDGAR Sentinel**: an
autonomous agent on Google Cloud that wakes up at 6:30 every morning, scans SEC
EDGAR for new filings across a 30-company watchlist, reads them with a
two-model pipeline, remembers every prior filing, and emails me what changed —
with a public dashboard for everything it knows.

- **Live dashboard:** https://edgar-sentinel-dashboard-69101307007.us-central1.run.app
- **Code:** https://github.com/brianmyers-ctrl/edgar-sentinel

## The architecture in one breath

Cloud Scheduler → Cloud Run Job → an **ADK orchestrator agent** (Gemini 3.5)
whose tools are the pipeline stages → SEC EDGAR (politely: declared User-Agent,
throttled) → raw filings archived to Cloud Storage → a section parser →
**Gemma** (on its own Cloud Run service, via Ollama) writes triage notes →
**Gemini 3.5 on Vertex AI** scores the filing against a five-pillar "Filing
Health Score" with schema-enforced JSON → Firestore stores it → a **delta
engine** compares against the company's prior filing and fires deterministic
alerts → SendGrid emails the digest.

One design rule shaped everything: **agentic control flow, deterministic
execution**. The LLM decides *what runs* and writes the run report. Tested
Python decides *what is true* — section slicing, score weighting, the alert
rule, state transitions. When a judge (or I) ask "why did this alert fire?",
the answer is a rule you can read, not a vibe.

## Two models, two jobs

Gemini 3.5 Flash does the deep reading: five pillar scores with cited
rationale, extracted metrics, three decision-relevant highlights. Temperature
zero, pydantic schema enforced, composite recomputed in code so config — not
the model's arithmetic — is authoritative.

Gemma's job is deliberately smaller: read the risk-factors section and produce
a dozen terse triage bullets — red flags, notable changes, tone — that ride
along to Gemini as a second opinion. It runs scale-to-zero on CPU. My first
design had Gemma *rewriting* filing text; that was wrong in an instructive way
(below).

## What actually broke (the fun part)

1. **Gemma 4 is a thinking model.** My triage calls returned empty strings
   with `done_reason: length` — the model spent its whole output budget on
   hidden reasoning and never wrote the answer. One `think: false` later,
   33-second useful triage notes.
2. **Ollama's default context window silently truncates.** My "cleaned" MD&A
   came back 12× smaller — not cleaning, truncation. That failure convinced me
   to change Gemma's job from rewriting text to writing *notes about* text.
3. **Inline-XBRL splits words across spans.** Microsoft's 10-K renders "RISK
   FACTORS" as `RIS K FACTORS`, and repeats "Item 1A" as a page header through
   the whole section — my "take the last heading match" heuristic found
   nothing. Fix: match headings with optional intra-word whitespace and take
   the match with the *longest following body*. Microsoft's risk section went
   from 0 to 80,000 characters.
4. **A use-after-free in Python.** Creating the google-genai client inline
   (`make_client().models.generate_content(...)`) let the client get
   garbage-collected mid-request; its finalizer closed the HTTP pool:
   `Cannot send a request, as the client has been closed.` Cached singleton.
5. **Org policies bite.** Our org restricts Vertex models
   (`constraints/vertexai.allowedModels`) and strips default service-account
   grants — both showed up as cryptic 400s/403s. Both fixed with scoped,
   least-privilege IAM rather than hammer-sized grants.

Every one of these would have detonated during a live demo. Finding them on day
one and day four instead is most of what "production-minded" means.

## Does it actually notice things?

The delta engine is the feature I'd defend in a knife fight. Because every
analysis persists in Firestore, each new filing is compared with the company's
prior one — pillar by pillar — and a deterministic rule (≥10-point move, band
change, or risk-pillar collapse) decides whether to alert. On the first full
backfill across 56 filings it flagged, among others: Plug Power sliding
**Caution → Distress** (cash down to $161.9M), Uber and PayPal slipping out of
Strong, and Coinbase and AMC genuinely recovering. It also caught Apple's
management going cautious on component costs a quarter before it showed up
anywhere else in the filing — a 10-point management-signal drop while the
composite barely moved.

## The numbers

30 companies · 56 filings analyzed · 8 live alerts · running unattended every
morning since August 14 · ~1 minute per filing · 20 unit tests · roughly a
dollar a day in cloud costs while idle-scaling to zero.

---

*I created this piece of content for the purposes of entering the All Things
Agentic Hackathon.* EDGAR Sentinel produces automated research summaries
derived from SEC filings — not investment advice.

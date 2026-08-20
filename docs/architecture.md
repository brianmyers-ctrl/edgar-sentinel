# Architecture

```mermaid
flowchart TB
    SCHED["Cloud Scheduler<br/>daily 6:30 AM PT"] -->|"OAuth (SA identity)"| JOB

    subgraph JOB["Cloud Run Job · edgar-sentinel-daily"]
        ADK["ADK Orchestrator Agent<br/>(Gemini 3.5 · google-adk)"]
        T1["tool: scan_new_filings"]
        T2["tool: analyze_filing"]
        T3["tool: write_digest"]
        ADK --> T1 --> ADK
        ADK --> T2 --> ADK
        ADK --> T3
    end

    T1 -->|"submissions API<br/>declared UA + throttle"| EDGAR["SEC EDGAR"]
    T1 -->|"raw filing archive"| GCS[("Cloud Storage<br/>edgar-sentinel-filings")]

    T2 --> PARSE["Section parser<br/>(risk factors · MD&A · financials)"]
    PARSE -->|"identity token"| GEMMA["Cloud Run Service<br/>edgar-sentinel-gemma<br/>Ollama · gemma3:4b<br/>(triage notes)"]
    PARSE --> GEMINI["Vertex AI<br/>gemini-3.5-flash<br/>Filing Health Score<br/>(schema-enforced JSON)"]
    GEMMA -.->|"second-opinion notes"| GEMINI
    GEMINI --> DELTA["Delta engine<br/>QoQ pillar deltas ·<br/>deterministic alert rule"]
    DELTA <-->|"prior analysis"| FS[("Firestore<br/>analyses · state")]

    T3 -->|"digest JSON"| FS
    T3 -->|"API key from<br/>Secret Manager"| SG["SendGrid<br/>morning email"]

    FS --> DASH["Cloud Run Service<br/>edgar-sentinel-dashboard<br/>public · read-only SA"]
    DASH --> USER(("Brian / judges"))
    SG --> USER
```

**Design principle: agentic control flow, deterministic execution.** The ADK
orchestrator (Gemini) decides *what* runs and writes the run report; tested
Python decides *what is true* — section slicing, FHS weighting, the alert rule,
and state transitions are all deterministic, reproducible code.

**Isolation:** three service identities — the job (Vertex user + Firestore user +
bucket writer + Gemma invoker + secret accessor), the Gemma service (private,
invoker-only), and the dashboard (public but datastore.viewer *only*). No
credential appears in code, images, or the repo; the only secret lives in
Secret Manager.

**Cost posture:** Gemma runs scale-to-zero on CPU and is scoped to the
risk-factors section; the analyst uses Gemini Flash with temperature 0; the
job runs ~1 minute per filing; the app does not need to stay hot — Cloud Run
scales everything to zero between runs.

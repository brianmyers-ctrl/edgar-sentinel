import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

# Model output reaches Windows consoles (cp1252) and piped log files; UTF-8
# with replacement means an exotic character can never crash a run.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Weights for the Filing Health Score pillars (see docs/investment-model.md)
FHS_WEIGHTS = {
    "profitability": 0.25,
    "balance_sheet": 0.20,
    "cash_generation": 0.20,
    "risk_flags": 0.20,
    "management_signal": 0.15,
}

TRACKED_FORMS = ("10-K", "10-Q")


@dataclass
class Settings:
    sec_user_agent: str = os.getenv(
        "SEC_USER_AGENT", "edgar-sentinel research agent (contact@example.com)"
    )
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    use_vertex: bool = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    gcp_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "edgar-sentinel")
    gcp_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    gemma_enabled: bool = os.getenv("GEMMA_ENABLED", "false").lower() == "true"
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    gemma_model: str = os.getenv("GEMMA_MODEL", "gemma3:4b")
    # Which sections get the Gemma cleanup pass. Local inference is the demo
    # story; at scale this stage moves to Cloud Run GPU, so keep the local
    # default scoped to the sections the analyst leans on hardest.
    gemma_sections: list[str] = field(
        default_factory=lambda: [
            s.strip()
            for s in os.getenv("GEMMA_SECTIONS", "risk_factors,mdna").split(",")
            if s.strip()
        ]
    )
    watchlist: list[str] = field(
        default_factory=lambda: [
            t.strip().upper()
            for t in os.getenv("WATCHLIST", "AAPL,MSFT,NVDA").split(",")
            if t.strip()
        ]
    )
    data_dir: str = os.getenv("DATA_DIR", "data")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local")  # local | firestore
    alert_threshold: int = int(os.getenv("ALERT_THRESHOLD", "10"))
    gcs_bucket: str = os.getenv("GCS_BUCKET", "")  # empty = no cloud archive
    # Digest email (SendGrid). Empty key = delivery disabled.
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
    digest_to: str = os.getenv("DIGEST_TO", "")
    digest_from: str = os.getenv("DIGEST_FROM", "")
    digest_always: bool = os.getenv("DIGEST_ALWAYS", "false").lower() == "true"


settings = Settings()

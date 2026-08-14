import re
import warnings

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Inline-XBRL filings are XML-flavored; lxml handles them fine as HTML.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from ..config import settings

# Section headings for 10-K and 10-Q (matched on normalized lowercase text).
_PATTERNS = {
    "risk_factors": r"item\s*1a\.?\s*[–—:-]?\s*risk\s+factors",
    "mdna": r"item\s*[27]\.?\s*[–—:-]?\s*management['’]?s?\s+discussion\s+and\s+analysis",
    "financials": r"item\s*[18]\.?\s*[–—:-]?\s*financial\s+statements",
}
_SECTION_CAP = 80_000
_MIN_SECTION = 500


def extract_sections(html: str) -> dict[str, str]:
    """Heuristic fallback parser: strip tags, locate item headings, slice sections.

    Filings start with a table of contents that repeats every heading, so we
    take the LAST match of each pattern (the real section body).
    """
    soup = BeautifulSoup(html, "lxml")
    norm = re.sub(r"\s+", " ", soup.get_text(" "))
    low = norm.lower()

    starts: dict[str, int] = {}
    all_positions: list[int] = []
    for key, pat in _PATTERNS.items():
        matches = [m.start() for m in re.finditer(pat, low)]
        if matches:
            starts[key] = matches[-1]
            all_positions.extend(matches)
    all_positions.sort()

    sections: dict[str, str] = {}
    for key, start in starts.items():
        nexts = [p for p in all_positions if p > start]
        end = min(nexts[0] if nexts else len(norm), start + _SECTION_CAP)
        body = norm[start:end].strip()
        if len(body) >= _MIN_SECTION:
            sections[key] = body

    sections["document_head"] = norm[:20_000]
    return sections


class GemmaTriage:
    """Gemma pre-analysis pass over the extracted sections.

    For each configured section, Gemma produces a compact triage note (red
    flags, notable changes, tone) that travels alongside the RAW text to the
    Gemini analyst as a second opinion. Output is capped small so local
    inference stays fast; section text is never replaced, so a Gemma failure
    costs nothing but the note.
    """

    def __init__(self):
        self.enabled = settings.gemma_enabled

    def note(self, section: str, text: str) -> str:
        if not self.enabled:
            return ""
        try:
            resp = requests.post(
                f"{settings.ollama_host}/api/generate",
                json={
                    "model": settings.gemma_model,
                    "prompt": (
                        f"You are a triage analyst reading the {section} section "
                        "of an SEC filing. In at most 12 terse bullet points, "
                        "list: notable changes, red flags (going concern, "
                        "restatement, litigation, customer concentration, control "
                        "weaknesses), and the overall tone. No preamble.\n\n"
                        "=== SECTION TEXT ===\n" + text[:24_000]
                    ),
                    "stream": False,
                    # Gemma 4 is a thinking model; without this it spends the
                    # whole num_predict budget reasoning and returns nothing.
                    "think": False,
                    "options": {"num_ctx": 16384, "num_predict": 600, "temperature": 0},
                },
                timeout=600,
            )
            resp.raise_for_status()
            data = resp.json()
            note = data.get("response", "").strip()
            if not note:
                print(
                    f"[parser] Gemma returned an empty note for {section} "
                    f"(done_reason={data.get('done_reason')})"
                )
            return note
        except Exception as e:
            print(f"[parser] Gemma triage unavailable ({e}); continuing without notes")
            return ""

    def parse(self, html: str) -> tuple[dict[str, str], dict[str, str]]:
        sections = extract_sections(html)
        notes = {
            k: n
            for k in settings.gemma_sections
            if k in sections and (n := self.note(k, sections[k]))
        }
        return sections, notes

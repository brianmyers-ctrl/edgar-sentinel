import re
import warnings

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Inline-XBRL filings are XML-flavored; lxml handles them fine as HTML.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from ..config import settings

# Section headings for 10-K and 10-Q (matched on normalized lowercase text).
# Filers vary: "Item 1A. Risk Factors", "ITEM 1A RISK FACTORS", and inline-XBRL
# HTML often splits words across spans ("RIS K FACTORS"), so headings are
# matched with optional whitespace between every letter.
_GAP = r"[\s\.\:\-–—]{0,40}?"


def _spaced(word: str) -> str:
    return r"\s*".join(map(re.escape, word))


def _phrase(*words: str) -> str:
    return r"\s+".join(_spaced(w) for w in words)


_PATTERNS = {
    "risk_factors": rf"item\s*1a{_GAP}{_phrase('risk', 'factors')}",
    "mdna": rf"item\s*[27]{_GAP}{_spaced('management')}['’]?s?\s+{_phrase('discussion', 'and', 'analysis')}",
    "financials": rf"item\s*[18]{_GAP}{_phrase('financial', 'statements')}",
}
# Fallbacks: some filers (e.g. Intel) omit item prefixes in body headings
# entirely — the item numbers live only in an end-of-document index. Matched
# CASE-SENSITIVELY against the original text so Title Case / ALL CAPS headings
# match but mid-prose references ("these risk factors") do not.
_BODY_FALLBACK = {
    "risk_factors": r"(?:RISK\s+FACTORS|Risk\s+Factors)",
    "mdna": r"(?:MANAGEMENT|Management)['’]?[Ss]?\s+(?:DISCUSSION|Discussion)\s+(?:AND|and)\s+(?:ANALYSIS|Analysis)",
    "financials": r"(?:(?:CONSOLIDATED|Consolidated)\s+)?(?:(?:CONDENSED|Condensed)\s+)?(?:FINANCIAL|Financial)\s+(?:STATEMENTS|Statements)",
}
_SECTION_CAP = 80_000
_MIN_SECTION = 500


def extract_sections(html: str) -> dict[str, str]:
    """Heuristic parser: strip tags, locate item headings, slice sections.

    Each heading appears several times — in the table of contents, in
    cross-references, and (for some filers) in running page headers — so for
    each section we keep the match that begins the LONGEST run of text before
    any other heading: that is the real section body.
    """
    soup = BeautifulSoup(html, "lxml")
    norm = re.sub(r"\s+", " ", soup.get_text(" "))
    low = norm.lower()

    primary = {k: [m.start() for m in re.finditer(p, low)] for k, p in _PATTERNS.items()}
    # Case-sensitive heading matches over the original text (see _BODY_FALLBACK).
    fallback = {k: [m.start() for m in re.finditer(p, norm)] for k, p in _BODY_FALLBACK.items()}

    # SCORING: a candidate heading is judged by how much text follows it before
    # a DIFFERENT section's heading appears. TOC lines sit next to other
    # sections' entries (tiny score); running page headers repeat the section's
    # OWN name, which same-key exclusion ignores — so real section starts win.
    positions_by_key = {
        k: sorted(set(primary[k]) | set(fallback.get(k, []))) for k in _PATTERNS
    }

    starts: dict[str, int] = {}
    for key in _PATTERNS:
        other = sorted(
            p for k2, ps in positions_by_key.items() if k2 != key for p in ps
        )

        def _score(pos: int) -> int:
            nxt = [b for b in other if b > pos]
            return (nxt[0] if nxt else len(norm)) - pos

        # Pool both tiers: some filers' item-prefixed matches exist ONLY in an
        # end-of-document cross-reference index (Intel), so a primary match
        # must still out-score the bare-heading candidates to win.
        cands = sorted(set(primary[key]) | set(fallback.get(key, [])))
        if cands:
            best = max(cands, key=_score)
            if _score(best) >= _MIN_SECTION:
                starts[key] = best

    # SLICING uses only the chosen section starts: stray in-body references
    # (page footers like "Notes to ... Financial Statements") must not
    # truncate a section they merely appear inside.
    chosen = sorted(starts.values())
    sections: dict[str, str] = {}
    for key, start in starts.items():
        nexts = [p for p in chosen if p > start]
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

    @staticmethod
    def _auth_headers() -> dict:
        """On Cloud Run the Gemma service is private; authenticate with an
        identity token for the service URL. Locally (localhost) no auth."""
        host = settings.ollama_host
        if "localhost" in host or "127.0.0.1" in host:
            return {}
        try:
            import google.auth.transport.requests
            import google.oauth2.id_token

            token = google.oauth2.id_token.fetch_id_token(
                google.auth.transport.requests.Request(), host
            )
            return {"Authorization": f"Bearer {token}"}
        except Exception as e:
            print(f"[parser] no identity token for Gemma service ({e}); trying unauthenticated")
            return {}

    def note(self, section: str, text: str) -> str:
        if not self.enabled:
            return ""
        try:
            resp = requests.post(
                f"{settings.ollama_host}/api/generate",
                headers=self._auth_headers(),
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

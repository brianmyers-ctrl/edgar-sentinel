from pydantic import BaseModel, Field

DISCLAIMER = "Automated research summary derived from SEC filings. Not investment advice."


class FilingRecord(BaseModel):
    ticker: str
    cik: int
    company: str
    form: str
    accession: str
    filing_date: str
    report_date: str = ""
    primary_doc: str
    url: str
    local_path: str = ""


class PillarScore(BaseModel):
    score: int = Field(ge=0, le=100)
    rationale: str


class KeyMetrics(BaseModel):
    period: str = ""
    revenue: str = ""
    net_income: str = ""
    operating_cash_flow: str = ""
    cash_and_equivalents: str = ""
    total_debt: str = ""
    shares_outstanding: str = ""


class DeltaNarrative(BaseModel):
    drivers: list[str] = Field(min_length=1, max_length=4)
    new_risks: list[str] = Field(max_length=5)
    reduced_risks: list[str] = Field(max_length=5)
    metric_trends: list[str] = Field(max_length=6)
    narrative: str


class FilingAnalysis(BaseModel):
    profitability: PillarScore
    balance_sheet: PillarScore
    cash_generation: PillarScore
    risk_flags: PillarScore
    management_signal: PillarScore
    composite: int = Field(ge=0, le=100)
    classification: str  # Strong | Stable | Caution | Distress
    highlights: list[str] = Field(min_length=3, max_length=3)
    key_metrics: KeyMetrics
    confidence: str  # low | medium | high
    disclaimer: str = DISCLAIMER

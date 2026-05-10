from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)
    website_url: HttpUrl
    ticker: str | None = Field(default=None, max_length=20)


class EvidenceItem(BaseModel):
    title: str
    source: str
    url: str
    snippet: str


class StockPoint(BaseModel):
    timestamp: str
    close: float


class StockTrend(BaseModel):
    ticker: str
    direction: str
    change_percent: float
    current_price: float | None = None
    previous_close: float | None = None
    today_change_percent: float | None = None
    currency: str | None = None
    exchange: str | None = None
    auto_resolved: bool = False
    points: list[StockPoint]


class ScorePillar(BaseModel):
    key: str
    label: str
    score: int
    note: str = ""


class FinancialSnapshot(BaseModel):
    revenue: str | None = None
    market_cap: str | None = None
    employees: str | None = None
    founded: str | None = None
    headquarters: str | None = None
    ceo: str | None = None
    industry: str | None = None


class AnalyzeResponse(BaseModel):
    company_name: str
    website_url: str
    score: int
    confidence: str
    risk_flags: list[str]
    growth_catalysts: list[str]
    summary: str
    key_facts: list[str] = Field(default_factory=list)
    score_breakdown: list[ScorePillar] = Field(default_factory=list)
    financial_snapshot: FinancialSnapshot = Field(default_factory=FinancialSnapshot)
    evidence: list[EvidenceItem]
    stock_trend: StockTrend | None = None
    diagnostics: dict = Field(default_factory=dict)

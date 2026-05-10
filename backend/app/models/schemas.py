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
    points: list[StockPoint]


class AnalyzeResponse(BaseModel):
    company_name: str
    website_url: str
    score: int
    confidence: str
    risk_flags: list[str]
    growth_catalysts: list[str]
    summary: str
    key_facts: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem]
    stock_trend: StockTrend | None = None
    diagnostics: dict = Field(default_factory=dict)

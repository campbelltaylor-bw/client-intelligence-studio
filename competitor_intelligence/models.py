from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CompetitorProduct(BaseModel):
    name: str
    launched: Optional[str] = None
    target_audience: Optional[str] = None
    primary_users: Optional[str] = None
    use_cases: list[str] = Field(default_factory=list)
    coverage: Optional[str] = None
    deliverable_formats: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None


class NewsItem(BaseModel):
    headline: str
    url: Optional[str] = None


class CompetitorProfile(BaseModel):
    company_name: str
    website: Optional[str] = None
    about: Optional[str] = None
    company_size: Optional[str] = None
    headquarters: Optional[str] = None
    additional_locations: list[str] = Field(default_factory=list)
    founded: Optional[str] = None
    mission_statement: Optional[str] = None
    market_cap: Optional[str] = None
    products: list[CompetitorProduct] = Field(default_factory=list)
    recent_news: list[NewsItem] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    @field_validator('recent_news', mode='before')
    @classmethod
    def coerce_news_items(cls, v):
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({'headline': item})
            else:
                result.append(item)
        return result


class ProductComparison(BaseModel):
    our_product: str
    their_product: Optional[str] = None
    overlap_summary: str
    differentiator: str


class AudienceOverlap(BaseModel):
    shared_segments: list[str] = Field(default_factory=list)
    our_exclusive_segments: list[str] = Field(default_factory=list)
    their_exclusive_segments: list[str] = Field(default_factory=list)


class CompetitiveGaps(BaseModel):
    we_cover_they_dont: list[str] = Field(default_factory=list)
    they_cover_we_dont: list[str] = Field(default_factory=list)


class CompetitiveAnalysis(BaseModel):
    executive_summary: str
    product_comparisons: list[ProductComparison] = Field(default_factory=list)
    audience_overlap: AudienceOverlap
    our_strengths: list[str] = Field(default_factory=list)
    their_strengths: list[str] = Field(default_factory=list)
    gaps: CompetitiveGaps


class ObjectionHandler(BaseModel):
    objection: str
    response: str


class BattleCard(BaseModel):
    positioning_statement: str
    top_differentiators: list[str] = Field(default_factory=list)
    objection_handlers: list[ObjectionHandler] = Field(default_factory=list)
    when_ca_wins: list[str] = Field(default_factory=list)
    when_they_win: list[str] = Field(default_factory=list)
    discovery_questions: list[str] = Field(default_factory=list)


class MarketEntry(BaseModel):
    company: str
    product: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    website: Optional[str] = None


class CompetitorReport(BaseModel):
    competitor_profile: CompetitorProfile
    competitive_analysis: CompetitiveAnalysis
    battle_card: Optional[BattleCard] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str = "claude-sonnet-4-6"
    our_profile_files_loaded: list[str] = Field(default_factory=list)

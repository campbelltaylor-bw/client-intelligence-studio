from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SourceTag = Literal["CRM_FACT", "PUBLIC_FACT", "AI_INFERENCE"]


class TaggedFact(BaseModel):
    value: str
    source: SourceTag
    evidence: Optional[str] = None


class CRMAccount(BaseModel):
    company_name: str
    industry: Optional[TaggedFact] = None
    company_size: Optional[TaggedFact] = None
    products_discussed: list[TaggedFact] = Field(default_factory=list)
    open_questions: list[TaggedFact] = Field(default_factory=list)
    open_followups: list[TaggedFact] = Field(default_factory=list)
    past_conversations: list[TaggedFact] = Field(default_factory=list)
    monday_item_id: Optional[str] = None


class WebResearchResult(BaseModel):
    company_name: str
    company_description: Optional[TaggedFact] = None
    recent_news: list[TaggedFact] = Field(default_factory=list)
    technology_signals: list[TaggedFact] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class BlogRecommendation(BaseModel):
    title: str
    url: str
    reason: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class ProductRecommendation(BaseModel):
    product_name: str
    use_case: str
    reason: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class InternalBrief(BaseModel):
    account_summary: str
    crm_highlights: list[TaggedFact] = Field(default_factory=list)
    key_opportunities: list[TaggedFact] = Field(default_factory=list)
    risks_and_gaps: list[str] = Field(default_factory=list)


class OutreachEmail(BaseModel):
    audience: str
    subject: str
    body: str


class ClientFacingOutputs(BaseModel):
    outreach_email: str
    meeting_prep_brief: str
    blog_recommendations: list[BlogRecommendation] = Field(default_factory=list)
    outreach_emails: list["OutreachEmail"] = Field(default_factory=list)


class PipelineInput(BaseModel):
    company_name: str
    is_new_prospect: bool
    website_url: Optional[str] = None
    monday_item_id: Optional[str] = None


class PipelineOutput(BaseModel):
    input: PipelineInput
    crm_data: Optional[CRMAccount] = None
    web_research: WebResearchResult
    product_recommendations: list[ProductRecommendation] = Field(default_factory=list)
    internal: InternalBrief
    client_facing: ClientFacingOutputs
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = "claude-sonnet-4-6"

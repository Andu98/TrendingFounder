"""Pydantic schemas for opportunity scoring."""

from pydantic import BaseModel, Field, field_validator


class OpportunityScoreResult(BaseModel):
    """Schema for the LLM-generated opportunity score result."""
    
    opportunity_score: int = Field(..., ge=0, le=100)
    confidence: int = Field(..., ge=0, le=100)
    is_global_giant: bool
    is_too_generic: bool
    romania_market_fit: int = Field(..., ge=1, le=5)
    local_gap: int = Field(..., ge=1, le=5)
    buildability: int = Field(..., ge=1, le=5)
    monetization_clarity: int = Field(..., ge=1, le=5)
    novelty: int = Field(..., ge=1, le=5)
    trend_relevance: int = Field(..., ge=1, le=5)
    competition_saturation: int = Field(..., ge=1, le=5)
    complexity: int = Field(..., ge=1, le=5)
    regulatory_risk: int = Field(..., ge=1, le=5)
    recommended_category: str
    opportunity_type: str
    one_sentence_summary: str = Field(..., max_length=200)
    romania_adaptation_idea: str = Field(..., max_length=500)
    why_it_scores_this_way: str = Field(..., max_length=500)
    red_flags: list[str] = Field(default_factory=list)
    suggested_mvp: str = Field(..., max_length=500)

    @field_validator("opportunity_type", mode="before")
    @classmethod
    def normalize_opportunity_type(cls, v: str) -> str:
        if not v or v.strip().lower() in ("", "string", "unknown", "n/a", "none"):
            return "other"
        return v.strip().lower()
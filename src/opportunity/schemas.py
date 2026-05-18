"""Pydantic schemas for opportunity scoring."""

from pydantic import BaseModel, Field, field_validator

TEXT_FALLBACKS = {
    "recommended_category": "Other",
    "one_sentence_summary": "No reliable summary provided by the model.",
    "romania_adaptation_idea": "No specific Romania adaptation identified.",
    "why_it_scores_this_way": "The model did not provide a reliable explanation.",
    "suggested_mvp": "No specific MVP suggested.",
}


def _clean_text(value, fallback: str, max_length: int | None = None) -> str:
    if value is None:
        text = fallback
    else:
        text = str(value).strip()
        if text.lower() in ("", "string", "unknown", "n/a", "none", "null"):
            text = fallback

    if max_length is not None and len(text) > max_length:
        text = text[: max_length - 3].rstrip() + "..."
    return text


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

    @classmethod
    def llm_json_schema(cls) -> dict:
        """Return a compact schema for LM Studio json_schema response_format."""
        return {
            "type": "object",
            "properties": {
                "opportunity_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "is_global_giant": {"type": "boolean"},
                "is_too_generic": {"type": "boolean"},
                "romania_market_fit": {"type": "integer", "minimum": 1, "maximum": 5},
                "local_gap": {"type": "integer", "minimum": 1, "maximum": 5},
                "buildability": {"type": "integer", "minimum": 1, "maximum": 5},
                "monetization_clarity": {"type": "integer", "minimum": 1, "maximum": 5},
                "novelty": {"type": "integer", "minimum": 1, "maximum": 5},
                "trend_relevance": {"type": "integer", "minimum": 1, "maximum": 5},
                "competition_saturation": {"type": "integer", "minimum": 1, "maximum": 5},
                "complexity": {"type": "integer", "minimum": 1, "maximum": 5},
                "regulatory_risk": {"type": "integer", "minimum": 1, "maximum": 5},
                "recommended_category": {"type": "string"},
                "opportunity_type": {"type": "string"},
                "one_sentence_summary": {"type": "string", "maxLength": 200},
                "romania_adaptation_idea": {"type": "string", "maxLength": 500},
                "why_it_scores_this_way": {"type": "string", "maxLength": 500},
                "red_flags": {"type": "array", "items": {"type": "string"}},
                "suggested_mvp": {"type": "string", "maxLength": 500},
            },
            "required": [
                "opportunity_score",
                "confidence",
                "is_global_giant",
                "is_too_generic",
                "romania_market_fit",
                "local_gap",
                "buildability",
                "monetization_clarity",
                "novelty",
                "trend_relevance",
                "competition_saturation",
                "complexity",
                "regulatory_risk",
                "recommended_category",
                "opportunity_type",
                "one_sentence_summary",
                "romania_adaptation_idea",
                "why_it_scores_this_way",
                "red_flags",
                "suggested_mvp",
            ],
            "additionalProperties": False,
        }

    @field_validator("opportunity_type", mode="before")
    @classmethod
    def normalize_opportunity_type(cls, v: str) -> str:
        if not v or str(v).strip().lower() in ("", "string", "unknown", "n/a", "none", "null"):
            return "other"
        return str(v).strip().lower()

    @field_validator("recommended_category", mode="before")
    @classmethod
    def normalize_category(cls, v) -> str:
        return _clean_text(v, TEXT_FALLBACKS["recommended_category"])

    @field_validator("one_sentence_summary", mode="before")
    @classmethod
    def normalize_summary(cls, v) -> str:
        return _clean_text(v, TEXT_FALLBACKS["one_sentence_summary"], 200)

    @field_validator("romania_adaptation_idea", mode="before")
    @classmethod
    def normalize_adaptation(cls, v) -> str:
        return _clean_text(v, TEXT_FALLBACKS["romania_adaptation_idea"], 500)

    @field_validator("why_it_scores_this_way", mode="before")
    @classmethod
    def normalize_explanation(cls, v) -> str:
        return _clean_text(v, TEXT_FALLBACKS["why_it_scores_this_way"], 500)

    @field_validator("suggested_mvp", mode="before")
    @classmethod
    def normalize_mvp(cls, v) -> str:
        return _clean_text(v, TEXT_FALLBACKS["suggested_mvp"], 500)

    @field_validator("red_flags", mode="before")
    @classmethod
    def normalize_red_flags(cls, v) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [] if _clean_text(v, "", 200) == "" else [_clean_text(v, "", 200)]
        if isinstance(v, list):
            return [_clean_text(item, "", 200) for item in v if _clean_text(item, "", 200)]
        return [str(v)]

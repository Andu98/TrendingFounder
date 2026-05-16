from pydantic import BaseModel, Field

VALID_CATEGORIES = frozenset(
    {
        "AI",
        "SaaS",
        "Ecommerce",
        "Community",
        "Entertainment",
        "Finance",
        "Education",
        "Productivity",
        "Developer Tools",
        "Marketplace",
        "Games",
        "Social",
        "Adult",
        "Gambling",
        "Piracy",
        "Scam-risk",
        "Other",
    }
)

VALID_BUSINESS_MODELS = frozenset(
    {
        "ads",
        "subscription",
        "marketplace",
        "ecommerce",
        "lead generation",
        "unknown",
    }
)


class LLMEnrichmentResult(BaseModel):
    summary: str = Field(..., min_length=1, max_length=500)
    category: str
    business_model: str
    target_users: str = Field(..., min_length=1, max_length=300)
    localization_angle: str = Field(..., min_length=1, max_length=300)
    risk_notes: str = Field(default="", max_length=500)
    novelty: int = Field(..., ge=1, le=5)
    idea_potential: int = Field(..., ge=1, le=5)
    confidence: int = Field(..., ge=1, le=5)

    @classmethod
    def failed(cls, domain: str, error: str) -> LLMEnrichmentResult:
        return cls(
            summary=f"LLM enrichment failed for {domain}",
            category="Other",
            business_model="unknown",
            target_users="N/A",
            localization_angle="N/A",
            risk_notes=f"Error: {error}",
            novelty=1,
            idea_potential=1,
            confidence=1,
        )

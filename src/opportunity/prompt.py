"""Prompt builder for opportunity scoring."""

from typing import Optional


def build_opportunity_prompt(
    domain: str,
    display_url: str,
    trend_score: float,
    countries_observed: list[str],
    ranking_types: list[str],
    best_rank: int,
    pct_rank_change: Optional[float],
    first_seen_at: str,
    existing_category: Optional[str],
    existing_summary: Optional[str],
    existing_llm_potential: Optional[int],
    review_status: str,
    romanian_signals: bool,
    homepage_excerpt: Optional[str] = None
) -> str:
    """
    Build the prompt for LLM opportunity scoring.
    
    Args:
        domain: The domain name
        display_url: The display URL
        trend_score: The trend score from Cloudflare observations
        countries_observed: Countries where this domain appeared
        ranking_types: Ranking types observed
        best_rank: Best rank seen
        pct_rank_change: Percentage rank change
        first_seen_at: When the domain was first seen
        existing_category: Existing category from LLM enrichment
        existing_summary: Existing summary from LLM enrichment
        existing_llm_potential: Existing LLM potential score
        review_status: Current review status
        romanian_signals: Whether this domain has Romanian signals
        homepage_excerpt: Optional homepage excerpt for more context
        
    Returns:
        Formatted prompt string for the LLM
    """
    prompt_template = """You are evaluating trending web domains as business/app inspiration for the Romanian market.

The goal is NOT to recommend the biggest websites.
The goal is to identify product ideas, SaaS tools, marketplaces, apps, or business models that could be adapted, localized, cloned, or built for Romania.

You must be strict. Penalize global giants and generic products heavily.

Evaluate the domain using only the provided data. Do not invent facts. If information is missing, say so and reduce confidence.

Romanian market preference:
- Reward small business tools.
- Reward local services.
- Reward home repair and service marketplaces.
- Reward medical/clinic booking or healthcare access tools.
- Reward education/reskilling tools if they are specific and buildable.
- Reward invoicing/accounting/payment tools if they are practical for Romanian businesses.
- Reward used/refurbished goods and value-focused commerce.
- Reward tourism/local experience ideas.
- Reward elderly/family care ideas.
- Reward B2B SaaS that solves concrete operational problems.

Penalize:
- global giants
- generic marketplaces
- generic course platforms
- generic cloud storage
- streaming platforms
- social networks
- crypto/Web3 hype
- ideas requiring massive inventory/logistics
- ideas requiring strong network effects from day one
- ideas already dominated by strong Romanian or global players
- ideas with unclear monetization

Domain data:
- domain: {domain}
- display_url: {display_url}
- trend_score: {trend_score}
- countries_observed: {countries_observed}
- ranking_types: {ranking_types}
- best_rank: {best_rank}
- pct_rank_change: {pct_rank_change}
- first_seen_at: {first_seen_at}
- existing_category: {existing_category}
- existing_summary: {existing_summary}
- existing_llm_potential: {existing_llm_potential}
- review_status: {review_status}
- romanian_signals: {romanian_signals}
- homepage_excerpt: {homepage_excerpt}

Return strict JSON only using this schema:

{{
  "opportunity_score": 0,
  "confidence": 0,
  "is_global_giant": false,
  "is_too_generic": false,
  "romania_market_fit": 1,
  "local_gap": 1,
  "buildability": 1,
  "monetization_clarity": 1,
  "novelty": 1,
  "trend_relevance": 1,
  "competition_saturation": 1,
  "complexity": 1,
  "regulatory_risk": 1,
  "recommended_category": "string",
  "opportunity_type": "local_marketplace|b2b_saas|consumer_app|vertical_saas|content_platform|ecommerce_tool|education_tool|healthcare_tool|logistics_tool|other",
  "one_sentence_summary": "string",
  "romania_adaptation_idea": "string",
  "why_it_scores_this_way": "string",
  "red_flags": ["string"],
  "suggested_mvp": "string"
}}

Metric scales:
- opportunity_score: 0-100 (see guidance below)
- confidence: 0-100
- metrics (romania_market_fit, local_gap, etc.): 1 to 5 (1 = poor/high-risk, 5 = excellent/low-risk)

Scoring guidance:
- 0-10: useless, giant, generic, irrelevant, or impossible
- 11-30: weak opportunity
- 31-50: maybe interesting but has serious issues
- 51-70: good opportunity worth reviewing
- 71-85: strong opportunity
- 86-100: exceptional Romania-focused opportunity

Be harsh with famous global platforms.
Amazon, Udemy, Box, Google, Netflix, Booking, Facebook, Instagram, YouTube, Apple, Microsoft, TikTok, Temu, AliExpress should score very low unless there is a very specific localizable niche pattern.

ANTI-HALLUCINATION POLICY:
If the 'homepage_excerpt' is 'None' and you do not recognize the domain with 100% certainty, you MUST set 'confidence' to 1 and 'opportunity_score' to 0. Do not guess the business model from the domain name alone if context is missing."""

    # Format the prompt with all the context
    return prompt_template.format(
        domain=domain,
        display_url=display_url,
        trend_score=trend_score,
        countries_observed=", ".join(countries_observed) if countries_observed else "None",
        ranking_types=", ".join(ranking_types) if ranking_types else "None",
        best_rank=best_rank,
        pct_rank_change=pct_rank_change if pct_rank_change is not None else "None",
        first_seen_at=first_seen_at,
        existing_category=existing_category if existing_category else "None",
        existing_summary=existing_summary if existing_summary else "None",
        existing_llm_potential=existing_llm_potential if existing_llm_potential is not None else "None",
        review_status=review_status,
        romanian_signals=str(romanian_signals),
        homepage_excerpt=homepage_excerpt if homepage_excerpt else "None"
    )
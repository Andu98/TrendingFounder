SYSTEM_PROMPT = (
    "You are a domain analyst. You analyze websites and produce a structured JSON report.\n"
    "\n"
    "Rules:\n"
    "- Output ONLY valid JSON. No markdown, no explanation, no code blocks.\n"
    "- Scores (novelty, idea_potential, confidence) must be integers 1-5.\n"
    "- Category must be one of: AI, SaaS, Ecommerce, Community, Entertainment,\n"
    "  Finance, Education, Productivity, Developer Tools, Marketplace, Games,\n"
    "  Social, Adult, Gambling, Piracy, Scam-risk, Other.\n"
    "- Business model must be one of: ads, subscription, marketplace, ecommerce,\n"
    "  lead generation, unknown.\n"
    "- Keep all text fields concise (1-2 sentences max).\n"
    '- If you cannot determine a field, use "unknown" or "N/A".'
)


def build_enrichment_prompt(
    domain: str,
    title: str | None = None,
    meta_description: str | None = None,
    categories: list[dict] | None = None,
    country_code: str | None = None,
    ranking_type: str | None = None,
    rank: int | None = None,
    pct_rank_change: float | None = None,
    homepage_snippet: str | None = None,
) -> str:
    parts = [f"Analyze this domain: {domain}"]

    if title:
        parts.append(f"Title: {title}")

    if meta_description:
        parts.append(f"Meta description: {meta_description}")

    if categories:
        cat_names = [c.get("name", "") for c in categories if c.get("name")]
        if cat_names:
            parts.append(f"Cloudflare categories: {', '.join(cat_names)}")

    if country_code:
        parts.append(f"First seen in country: {country_code}")

    if ranking_type:
        parts.append(f"Ranking type: {ranking_type}")

    if rank is not None:
        parts.append(f"Rank: {rank}")

    if pct_rank_change is not None:
        parts.append(f"Percent rank change: {pct_rank_change}")

    if homepage_snippet:
        snippet = homepage_snippet[:4000]
        parts.append(f"Homepage content snippet: {snippet}")

    parts.append(
        "\nReturn a JSON object with these fields:"
        " summary, category, business_model, target_users,"
        " localization_angle, risk_notes, novelty, idea_potential, confidence."
    )

    return "\n".join(parts)

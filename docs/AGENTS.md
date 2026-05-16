# AGENTS.md

## Role of agent

- Build carefully.
- Do not invent Cloudflare params.
- Update TASKS.md after each completed task.
- Update DECISIONS.md when making architecture choices.
- Update CHANGELOG.md after every meaningful code change.
- Run tests after changing domain normalization, scoring, DB mappings, Cloudflare parsing.
- Never expose API tokens.
- Prefer small, reviewable changes.

## Strict rules

Do not guess API parameters.

Before changing Cloudflare code:
1. read Cloudflare Radar llms.txt or endpoint markdown docs;
2. verify endpoint path;
3. verify query params;
4. verify auth;
5. verify response shape;
6. update API_CONTRACTS.md.

After every code change:
1. update TASKS.md;
2. update CHANGELOG.md;
3. if architecture changed, update DECISIONS.md;
4. run relevant tests.

Never run LLM enrichment for an already known normalized_domain.

Never create duplicate domain rows.

Always create observations for repeated appearances.

Store timestamps in UTC. Convert to Europe/Bucharest only for display.

Use review_status as the source of truth. UI checkboxes are only presentation.

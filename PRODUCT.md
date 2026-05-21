# Product

## Register

product

## Users

TrendingFounder is used by a founder-operator or product researcher who checks global trend signals, usually during focused triage sessions on a laptop and occasional mobile review. They need to scan fresh domains quickly, understand why a domain is interesting, mark review decisions, capture notes, and return to unresolved opportunities without losing context.

## Product Purpose

TrendingFounder discovers trending domains from Cloudflare Radar, stores unique normalized domains with repeated observations, enriches them with LLM context, scores opportunity potential, and presents the result in a Streamlit dashboard. Success means a user can move from noisy global trend data to a small set of actionable product or localization opportunities, with review status and comments preserving the decision trail.

## Brand Personality

Calm, analytical, decisive. The product should feel like an operations console for market signal review: quiet enough for repeated use, sharp enough to support quick decisions, and trustworthy enough that status changes feel final.

## Anti-references

Do not make the app feel like a marketing landing page, crypto dashboard, decorative AI SaaS template, or spreadsheet clone. Avoid purple-blue gradient spectacle, glassmorphism, oversized hero sections, decorative animation, vague status checkboxes, hidden review state, and modal-heavy workflows that slow triage.

## Design Principles

- **Triage is the product.** The first screen should prioritize scanning, comparing, marking, and annotating domains.
- **Status is a decision, not decoration.** `review_status` is the source of truth; controls must make the current state obvious and prevent ambiguous repeated actions.
- **Freshness and evidence stay visible.** Scores, countries, observations, comments, and range metadata should remain close to each domain.
- **Dense, not cramped.** The interface should support many rows and repeated daily use while preserving touch targets and readable summaries.
- **Async work should feel immediate.** Optimistic UI changes are appropriate when persistence happens in the background, but the interface must not imply writes are complete before state is queued.

## Accessibility & Inclusion

Target WCAG 2.1 AA for color contrast and keyboard-operable controls. Status, score, and category meaning must not rely on color alone. Motion should be restrained and state-driven, with no required animation. Mobile layouts must keep controls readable and tappable without horizontal scrolling in normal use.

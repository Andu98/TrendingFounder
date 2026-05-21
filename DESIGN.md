---
name: TrendingFounder
description: A restrained product dashboard for discovering, scoring, and triaging trending domains.
colors:
  dark-bg: "#071114"
  dark-bg-soft: "#0b171b"
  dark-surface: "#0f1d22"
  dark-surface-2: "#13252b"
  dark-border: "#21363e"
  dark-card-border: "#2f4a53"
  dark-text: "#e7f2f4"
  dark-muted: "#8fa3aa"
  dark-accent: "#18c4c7"
  dark-accent-2: "#3fe6c7"
  light-bg: "#f5f9fb"
  light-bg-soft: "#edf5f7"
  light-surface: "#ffffff"
  light-surface-2: "#f1f7f9"
  light-border: "#d5e3e8"
  light-card-border: "#b6d3dc"
  light-text: "#17252b"
  light-muted: "#667982"
  light-accent: "#11b9bd"
  light-accent-2: "#078f99"
  semantic-ok: "#43d990"
  semantic-pending: "#d6a33d"
  semantic-exists: "#a98dff"
  semantic-bad: "#ef6363"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 850
    lineHeight: 1.08
    letterSpacing: "0"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "1.28rem"
    fontWeight: 900
    lineHeight: 1.1
    letterSpacing: "0"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "1.08rem"
    fontWeight: 850
    lineHeight: 1.2
    letterSpacing: "0"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.88rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0"
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 850
    lineHeight: 1
    letterSpacing: "0.04em"
rounded:
  sm: "6px"
  md: "8px"
  pill: "999px"
spacing:
  xs: "0.35rem"
  sm: "0.55rem"
  md: "0.85rem"
  lg: "1rem"
  xl: "2.25rem"
components:
  button-primary:
    backgroundColor: "{colors.dark-accent}"
    textColor: "{colors.dark-bg}"
    rounded: "{rounded.sm}"
    padding: "0 0.62rem"
    height: "2.25rem"
  button-secondary:
    backgroundColor: "{colors.dark-surface-2}"
    textColor: "{colors.dark-muted}"
    rounded: "{rounded.sm}"
    padding: "0 0.42rem"
    height: "2rem"
  card:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-text}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  chip:
    backgroundColor: "{colors.dark-surface-2}"
    textColor: "{colors.dark-text}"
    rounded: "{rounded.pill}"
    padding: "0.34rem 0.55rem"
---

# Design System: TrendingFounder

## 1. Overview

**Creative North Star: "The Signal Desk"**

TrendingFounder should feel like a calm market-signal desk: dense enough to process many domains, restrained enough for daily use, and precise enough that every action has a clear outcome. The app is not a landing page or decorative AI demo; it is a working review surface where status, score, evidence, and notes are the core material.

The visual system uses cool tinted surfaces, a narrow cyan accent, and semantic status colors for decisions. Both dark and light themes are first-class, but the dark theme carries the default operations-console mood for long review sessions.

**Key Characteristics:**
- Compact product UI with predictable top navigation and card rows.
- One primary accent for navigation, focus, and selected actions.
- Semantic colors for review and operational states.
- Flat-by-default surfaces with subtle border and shadow separation.
- Mobile layouts that preserve the triage workflow instead of hiding it.

## 2. Colors

The palette is restrained cyan over tinted blue-green neutrals, with semantic colors reserved for review decisions and health states.

### Primary
- **Radar Cyan** (`#18c4c7` dark, `#11b9bd` light): Used for active navigation, primary actions, links, focus rings, and selected controls.
- **Electric Mint** (`#3fe6c7` dark, `#078f99` light): Used as the second accent stop in the brand mark and for hover emphasis.

### Secondary
- **Decision Green** (`#43d990`): Positive review status, high scores, and completed operational states.
- **Watch Amber** (`#d6a33d`): Pending review status and cautionary supporting metadata.
- **Known Purple** (`#a98dff`): Existing product status, ranking metadata, and in-progress/partial states.
- **Reject Red** (`#ef6363`): Bad status, failed states, and global-giant warnings.

### Neutral
- **Night Console** (`#071114`, `#0f1d22`, `#13252b`): Dark theme background and raised surfaces.
- **Mist Console** (`#f5f9fb`, `#ffffff`, `#f1f7f9`): Light theme background and raised surfaces.
- **Dark Ink** (`#e7f2f4`, `#8fa3aa`): Dark theme primary and secondary text.
- **Light Ink** (`#17252b`, `#667982`): Light theme primary and secondary text.
- **Structural Borders** (`#21363e`, `#2f4a53`, `#d5e3e8`, `#b6d3dc`): Separates cards, filters, inputs, and table headers.

### Named Rules

**The Narrow Accent Rule.** Cyan is for current selection, focus, primary action, and links. It should not become a decorative wash across cards.

**The Semantic Status Rule.** OK, Pending, Exists, and Bad must retain distinct color treatments plus text labels. Color can reinforce the state, but the label carries the meaning.

## 3. Typography

**Display Font:** System UI (`-apple-system`, BlinkMacSystemFont, `Segoe UI`, system-ui, sans-serif)  
**Body Font:** System UI (`-apple-system`, BlinkMacSystemFont, `Segoe UI`, system-ui, sans-serif)  
**Label/Mono Font:** System UI, no mono face currently used

**Character:** Native, compact, and task-focused. Type hierarchy comes from weight and modest size changes, not display fonts or decorative letterforms.

### Hierarchy
- **Display** (850, `2rem`, 1.08): Page titles such as Collected Data and Reports.
- **Headline** (900, `1.28rem`, 1.1): Metric values and prominent numeric signals.
- **Title** (850, `1.08rem`, 1.2): Section titles, note headers, and compact panel headings.
- **Body** (400-650, `0.88rem` to `0.94rem`, 1.45): Summaries, details, notes, and form input text. Prose should stay near 65-75ch when it becomes paragraph-like.
- **Label** (850, `0.72rem` to `0.78rem`, 0.03-0.04em): Table headers, filter group labels, KPI labels, and metadata captions.

### Named Rules

**The Native Tool Rule.** Use the system type stack everywhere. Avoid display fonts in buttons, labels, data, or controls.

## 4. Elevation

Depth is conveyed through tonal layering, borders, and restrained shadows. Domain cards and metric panels sit on the surface with a light operational lift; nested details flatten back down with borders instead of stacking card shadows inside card shadows.

### Shadow Vocabulary
- **Surface Shadow** (`0 12px 36px rgba(2, 13, 17, 0.2)` dark, `0 12px 32px rgba(26, 62, 72, 0.1)` light): Default card and filter-panel separation.
- **Strong Surface Shadow** (`0 16px 44px rgba(2, 13, 17, 0.24)` dark, `0 16px 40px rgba(26, 62, 72, 0.12)` light): Expanders and heavier panels.
- **Brand Mark Glow** (`0 12px 35px rgba(24, 196, 199, 0.24)`): Reserved for the small brand mark only.

### Named Rules

**The Flat Detail Rule.** Details inside a domain card should use separators and tonal panels, not nested card shadows.

## 5. Components

### Buttons
- **Shape:** Compact rounded rectangles (`6px`) for workflow actions; pills (`999px`) for navigation.
- **Primary:** Cyan background, strong text contrast, 850 weight. Used for active navigation, selected statuses, and primary form submission.
- **Hover / Focus:** State changes use 150-180ms color and border transitions. Focus rings use a translucent cyan outline.
- **Secondary:** Surface-2 background, border, muted text. Used for inactive status options and pagination.

### Chips
- **Style:** Pill shape with tinted background, 1px border, compact label text.
- **State:** Category, business model, ranking, country, and score chips each keep distinct semantic color roles.

### Cards / Containers
- **Corner Style:** `8px`, never oversized.
- **Background:** Theme surface with card-border outlines.
- **Shadow Strategy:** Surface shadow on outer panels only.
- **Border:** 1px borders define hierarchy more than shadow.
- **Internal Padding:** Domain cards use about `1rem`; metric cards use `1rem 1.05rem`.

### Inputs / Fields
- **Style:** Theme input background, 1px border, system font at `0.94rem`.
- **Focus:** Accent border plus a subtle cyan focus halo.
- **Disabled / Placeholder:** Muted text values must remain readable in both themes.

### Navigation
- **Style:** A full-width top bar with centered pill navigation and a right-aligned theme toggle on desktop.
- **Mobile Treatment:** Brand plus compact menu popover. The mobile flow should expose navigation and theme without consuming the screen.

### Domain Review Card

The domain card is the signature component. It combines domain identity, review status actions, score, summary, country signal, notes, and details. The status control should occupy the second visual slot and clearly show the selected `review_status`; actions should feel immediate because the app queues optimistic persistence.

## 6. Do's and Don'ts

### Do:
- **Do** keep the dashboard dense and scannable; this is a triage tool, not a storytelling page.
- **Do** keep `review_status` visibly attached to each domain card.
- **Do** use cyan sparingly for selection, focus, primary action, and links.
- **Do** preserve semantic labels beside color-coded states.
- **Do** favor borders and tonal surfaces over heavy nested shadows.

### Don't:
- **Don't** use purple-blue gradient spectacle, glassmorphism, or decorative animation.
- **Don't** turn app screens into marketing hero sections.
- **Don't** use status checkboxes when the interaction is a mutually exclusive review decision.
- **Don't** hide the current status or make clicking the selected status cause a meaningless rerun.
- **Don't** use side-stripe borders, gradient text, oversized radii, or card-in-card layouts.

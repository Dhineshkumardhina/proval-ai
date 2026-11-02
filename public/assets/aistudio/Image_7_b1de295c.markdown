---
name: PropVal AI
colors:
  surface: '#f9f9ff'
  surface-dim: '#d1daf4'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#e9edff'
  surface-container-high: '#e1e8ff'
  surface-container-highest: '#d9e2fc'
  on-surface: '#121b2e'
  on-surface-variant: '#44474e'
  inverse-surface: '#273044'
  inverse-on-surface: '#edf0ff'
  outline: '#74777e'
  outline-variant: '#c4c6ce'
  surface-tint: '#4a5f81'
  primary: '#001632'
  on-primary: '#ffffff'
  primary-container: '#142b4a'
  on-primary-container: '#7d93b7'
  inverse-primary: '#b2c7ee'
  secondary: '#0051d5'
  on-secondary: '#ffffff'
  secondary-container: '#316bf3'
  on-secondary-container: '#fefcff'
  tertiary: '#001a18'
  on-tertiary: '#ffffff'
  tertiary-container: '#00312d'
  on-tertiary-container: '#48a097'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#b2c7ee'
  on-primary-fixed: '#021c3a'
  on-primary-fixed-variant: '#324768'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#003ea8'
  tertiary-fixed: '#9cf2e8'
  tertiary-fixed-dim: '#80d5cb'
  on-tertiary-fixed: '#00201d'
  on-tertiary-fixed-variant: '#00504a'
  background: '#f9f9ff'
  on-background: '#121b2e'
  surface-variant: '#d9e2fc'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  display-sm:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  title-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
  numeric-metric-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  numeric-metric-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  numeric-table:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-sm: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 1.75rem
---

## Brand & Style

This design system establishes an institutional, mathematically grounded, and transparent interface tailored for credit underwriters, risk committees, and valuation officers across Indian Housing Finance Companies (HFCs) and retail banking institutions. 

The aesthetic is **Corporate / Modern Enterprise SaaS with High-Information Density**. It abandons consumer-grade fluff in favor of rigorous precision, defensible explainability, and analytical calm. Every screen emphasizes high data integrity, audit trails, and clarity under high-pressure decision-making. 

Visual mechanics prioritize:
- **Financial Credibility**: Structural lines, controlled color coding, and explicit validation states replace decorative patterns.
- **Explainable Intelligence**: Dedicated visual treatments for model confidence, risk intervals, and comparable property weights to ensure algorithmic transparency.
- **Ergonomic Data Scanning**: Optimized for split-screen document evaluation, geospatial comparables, and multi-tier tabular records under sustained professional use.

## Colors

The palette combines authoritative banking deep tones with technical clarity and domain-specific semantic feedback:

- **Primary / Brand Navy (`#142B4A`)**: Anchor tone for structural framing, persistent side navigation, top-level headers, and executive summary headers.
- **Secondary / Tech Blue (`#2563EB`)**: Interactive vehicle reserved for primary CTAs, active pagination steps, linked property folios, and focus rings.
- **Tertiary / Intelligence Teal (`#0F766E`)**: Dedicated indicator for AI explainability, feature attribution (e.g., floor rise factor, locality indices, road-width multipliers), and automated inference tags.
- **Neutral Core**:
  - `Surface Background`: `#F5F7FA` (Calibrated cool light neutral reducing eye fatigue across multi-hour appraisal shifts).
  - `Surface Cards & Panels`: `#FFFFFF` (Pristine background for dense data rendering).
  - `Text Primary`: `#172033` (High-contrast charcoal navy).
  - `Text Secondary & Meta`: `#64748B` (Neutral slate for column headers, units, and structural metadata).
  - `Hairline Borders & Structural Dividers`: `#E2E8F0` (Crisp 1px delimiters).
- **Domain Semantics & Risk Tiers**:
  - `Success / Validated`: `#15803D` (High comparable density, title chain verified, physical inspection congruent).
  - `Warning / Discrepancy`: `#D97706` (Moderate confidence interval, low registry liquidity, municipal boundary variance).
  - `Critical / Breach`: `#DC2626` (Valuation deviation >15%, unauthorized construction alert, flood-zone tag).

## Typography

Typography relies entirely on **Inter** to ensure maximum legibility at compact scales, utilizing OpenType feature `tnum` (tabular numbers) and `cv05` universally across financial tables, Indian Rupee (`₹`) denominations, and per-square-foot ratios.

### Numerical Standards & Formats
- Always render Indian numeric systems with proper commas: Hundreds, Thousands, Lakhs, Crores (e.g., `₹1,42,50,000` / `₹1.42 Cr` and `₹12,450 / sq ft`).
- All numeric appraisal outputs and table cells must employ `numeric-table` with `font-feature-settings: "tnum" 1` to guarantee vertical decimal alignment across row comparisons.
- `label-caps` is uppercase only, reserved for table headers, metadata tags, status categorizations, and system timestamps.

## Layout & Spacing

The system leverages a compact, high-density layout paradigm optimized for 1440px and 1920px professional desktop workspaces, while maintaining graceful responsiveness down to mobile field-inspection tools.

### Grid & Density Principles
- **Global Frame**: Fixed 260px collapsible brand navigation sidebar (`#142B4A`) flanking a fluid analytical canvas (`#F5F7FA`) bounded by a default 24px (`1.5rem`) outer margin.
- **Split-Screen Valuation Studio**: A standard 50/50 or 60/40 asynchronous layout pattern:
  - Left pane: Registry documentation, geo-tagged survey photos, and satellite GIS overlays.
  - Right pane: Machine-learning factor decomposition, comparable sales grid, and manual underwriter override inputs.
- **Rhythm**: Micro-scale 4px/8px incremental rhythm for interior component paddings (`space-xs` to `space-md`) ensures maximum data visibility without vertical bloating.

## Elevation & Depth

To sustain credibility and focus, the system relies on **low-contrast hairlines and calibrated structural elevations** rather than soft, diffuse drop shadows.

- **Level 0 (Base Canvas)**: `#F5F7FA` flat surface.
- **Level 1 (Card & Content Blocks)**: `#FFFFFF` bounded by a solid 1px border of `#E2E8F0`. Shadow: `0 1px 2px 0 rgba(20, 43, 74, 0.04)`.
- **Level 2 (Active Inspection Cards, Hovered Rows, Dropdowns)**: `#FFFFFF` with 1px border of `#CBD5E1`. Shadow: `0 4px 6px -1px rgba(20, 43, 74, 0.08), 0 2px 4px -2px rgba(20, 43, 74, 0.04)`.
- **Level 3 (Valuation Overlays, Underwriter Sign-off Modals)**: `#FFFFFF` with 1px border of `#94A3B8`. Shadow: `0 12px 24px -4px rgba(20, 43, 74, 0.14)`. Backdrop filter: `blur(2px)` over `rgba(20, 43, 74, 0.45)`.

## Shapes

The geometric framework is conservative and architectural. A soft micro-radius (`roundedness: 1`, base 4px to 6px) guarantees a modern, clean posture without appearing informal or consumer-oriented.

- **Base Radius (`4px`)**: Input controls, table row hover indicators, mini badge markers, and tooltips.
- **Container Radius (`6px` to `8px`)**: Analytic cards, KPI stat blocks, document viewers, and modal containers.
- **Pill Radius (`9999px`)**: Dedicated solely to status badges, AI confidence flags, and filter trigger chips.

## Components

### Buttons
- **Primary CTA**: `#2563EB` solid fill, white text, 6px border-radius, font weight 600. Active state transitions to `#1D4ED8`. Focus ring: 2px offset with `rgba(37, 99, 235, 0.35)`.
- **Secondary / Audit Button**: `#FFFFFF` background, `#142B4A` text, 1px border `#CBD5E1`. Subtle hover background `#F8FAFC`.
- **Tertiary / Explainability Action**: Borderless with `#0F766E` text, subtle icon glyph (e.g., sparkline or tree diagram).

### KPI Stat Widgets
- Pure white background cards with a crisp top or left accent hairline denoting status.
- Primary metric in `numeric-metric-lg` accompanied by a localized sub-label in `label-caps` (e.g., `ESTIMATED BASE VALUE`, `ALGORITHMIC CONFIDENCE SCORE: 94.2%`).
- Integral tags indicating Indian real estate metrics: `₹/sq ft Carpet Area` alongside `₹/sq ft Super Built-Up`.

### Tabular Data Grid
- **Header**: `#F8FAFC` background with a solid 1px bottom border (`#CBD5E1`). Column labels set in `label-caps`, uppercase, `#64748B`.
- **Rows**: Fixed 40px height for dense view, 48px for standard. Zebra hover in `#F1F5F9`. Selected row marked with a 2px left border in `#2563EB`.
- **Cell Alignment**: Text left-aligned; all numeric currencies, area values, and variance percentages right-aligned using tabular figures.

### Status & Explainability Badges
- Pill-shaped (`rounded-full`), 20px height, 8px horizontal padding.
- `Confidence: High`: Background `#DCFCE7`, text `#15803D`, 1px border `#BBF7D0`.
- `Review Required`: Background `#FEF3C7`, text `#B45309`, 1px border `#FDE68A`.
- `Discrepancy / Alert`: Background `#FEE2E2`, text `#B91C1C`, 1px border `#FECACA`.
- `AI Model Signal`: Background `#CCFBF1`, text `#0F766E`, 1px border `#99F6E4`.

### Form & Underwriter Input Fields
- Micro-radius (4px), 36px standard height for enterprise efficiency.
- Border `#CBD5E1`, background `#FFFFFF`. Active focus border `#2563EB` with zero horizontal blur.
- Mandatory prefix/suffix containers with integrated currency symbols (`₹`) or units (`sq ft`, `sq m`, `guntas`).
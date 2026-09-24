---
name: Civic Shield Guard
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d5e3fc'
  on-surface: '#0d1c2e'
  on-surface-variant: '#44474d'
  inverse-surface: '#233144'
  inverse-on-surface: '#eaf1ff'
  outline: '#74777e'
  outline-variant: '#c4c6ce'
  surface-tint: '#4d5f7c'
  primary: '#000d20'
  on-primary: '#ffffff'
  primary-container: '#0f233d'
  on-primary-container: '#788baa'
  inverse-primary: '#b5c7e9'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#1f0400'
  on-tertiary: '#ffffff'
  tertiary-container: '#451000'
  on-tertiary-container: '#e95d29'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#b5c7e9'
  on-primary-fixed: '#071c36'
  on-primary-fixed-variant: '#354763'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59d'
  on-tertiary-fixed: '#390c00'
  on-tertiary-fixed-variant: '#832600'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d5e3fc'
typography:
  headline-xl:
    fontFamily: Noto Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 52px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Noto Sans
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Noto Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 42px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Noto Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Noto Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 34px
  headline-sm:
    fontFamily: Noto Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Noto Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-sm:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  label-md:
    fontFamily: Noto Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Noto Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.03em
  caption:
    fontFamily: Noto Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

The design system embodies a modern, approachable civic-technology standard tailored for public digital defense. It blends the institutional authority of a public service with the direct clarity of contemporary consumer security utilities.

### Personality & Emotional Response
- **Trustworthy & Unflinching:** Evokes institutional safety and technical competence without resorting to alarmist tropes, skull-and-crossbones icons, or dark neon "cyber" motifs.
- **Calm & Instructive:** Transforms panic and uncertainty into actionable, step-by-step resolution. Scam alerts and risk matrices communicate urgency through clear hierarchy and unambiguous semantics, never fear-mongering.
- **Inclusive & Civic-First:** Built for diverse literacy levels across India, balancing dense forensic analysis with plain-language risk indicators in both English and Tamil.

### Design Movement
The visual language operates under **Modern Civic Editorialism**—crisp content containers, high-contrast readable typography, subtle borders, and intentional tonal layering. Surfaces rely on bright, clean canvases with structured borders rather than heavy ambient blurs or skeuomorphic styling.

## Colors

The palette establishes grounded state-level credibility through deep nautical navy, tempered by affirmative sea-teal, structured warning amber, and high-urgency vermilion. Every color role conforms to WCAG 2.1 AA (4.5:1 minimum contrast for body text) on its matched background. Color is never used as the sole conveyor of risk or system state; explicit text badges, iconography, and structured borders always accompany color indicators.

### Palette Architecture
- **Primary Navy (`#0f233d`):** Represents institutional permanence, primary actions, deep headlines, and solid navigational anchors. Contrast-safe against white surfaces.
- **Secondary Teal (`#0d9488`):** Applied to affirmative safety states, verified domain badges, auxiliary call-to-actions, and positive verification steps.
- **Tertiary Vermilion (`#c2410c`):** Reserved strictly for critical scam detections, urgent containment actions, and deceptive risk vectors.
- **Warning Amber (`#d97706`):** Dedicated to unverified items, suspicious anomalies, and pending user investigations.
- **Neutral Canvas (`#f8fafc` to `#f1f5f9`):** Slate-tinted warm light foundations that eliminate glare while providing soft contrast against elevated pure-white `#ffffff` cards.
- **Border & Separator Tone (`#e2e8f0` / `#cbd5e1`):** Structural, low-noise dividers maintaining card geometry across all ambient lighting conditions.

## Typography

The type stack is standardized on `Noto Sans` (with Latin and Tamil glyph support prioritized in CSS `@font-face` definitions, falling back seamlessly to `Noto Sans Tamil`, `IBM Plex Sans`, and `system-ui`). 

### Tamil & Bilingual Script Tuning
- **Line Heights:** Tamil glyphs require elevated ascender and descender clearances. The line-height ratios throughout the hierarchy are locked at a minimum of `1.45` to `1.65` to prevent diacritic clipping in conjunct ligatures (e.g., க், ஸ்ரீ, ணூ).
- **Weight Pairing:** Avoid hairline or ultra-light weights. Headings leverage bold (`700`) and semi-bold (`600`) for immediate recognition across mobile viewports, while body copy remains solid regular (`400`).
- **Bilingual Synchronicity:** When rendering English and Tamil side-by-side or within identical container flexboxes, optical baseline alignment must be enforced over absolute cap-height centering.

## Layout & Spacing

The layout is constructed on an adaptable fluid grid with fixed maximum container constraints to maintain optimal reading widths for assessment logs and incident forensics.

### Breakpoints & Container Model
- **Mobile (< 640px):** 4-column layout. Section margins drop to `1rem` (`margin-mobile`), and column gutters scale to `1rem` (`gutter-mobile`). Assessment inputs, evidence screenshots, and risk gauges collapse into a single vertical stack.
- **Tablet (640px – 1024px):** 8-column layout. Section margins expand to `1.5rem`. Input panels and result sidebars sit in a 5:3 column split.
- **Desktop (> 1024px, max-width 1280px):** 12-column layout. Centered canvas with `2rem` margin. Complex triage views utilize a 7:5 asymmetric structure (primary threat analysis stream on the left, procedural emergency hotline and step-by-step mitigation cards pinned on the right).

### Spacing Rhythm
Vertical padding within risk assessment modules strictly utilizes multiples of `0.5rem` (`space-sm`), standardizing inner card padding at `1.5rem` (`space-lg`) on desktop and `1rem` (`space-md`) on handheld viewports.

## Elevation & Depth

This design system rejects heavy, dramatic, or neon-tinted shadows in favor of **low-contrast structural outlines paired with light tonal layering**. This keeps the interface clean, official, and easily readable on low-cost screens or outdoors under bright sunlight.

### Depth Hierarchy
- **Canvas Base (Tier 0):** Background field colored `#f8fafc`. Completely flat.
- **Card Surface (Tier 1):** Solid `#ffffff` background bounded by a `1px` crisp border of `#e2e8f0`. Shadow is microscopic: `0 1px 2px 0 rgba(15, 35, 61, 0.04)`.
- **Active / Interactive Card (Tier 2):** Elevated interactive components (such as a hovered scan result or focused evidence card) transition to `0 4px 12px -2px rgba(15, 35, 61, 0.08)` while borders shift to `#cbd5e1`.
- **Floating Modals & Urgent Takeovers (Tier 3):** Modal containment sheets use `0 12px 28px -4px rgba(15, 35, 61, 0.16)` with an underlying tinted scrim (`rgba(15, 35, 61, 0.45)`).
- **Risk Insets:** Warning and high-risk message blocks do not use drop shadows. Instead, they use structural tinted surface backgrounds (e.g., `#fff1f2` for vermilion risk, `#fffbeb` for amber caution) with thick `3px` solid left indicator borders.

## Shapes

The geometric framework uses **Soft (`1`)** curvature. 

- Base UI elements (inputs, badges, table containers, and buttons) employ `0.25rem` (`rounded`) to `0.375rem`.
- Standard content cards, triage summary boxes, and modal panels use `0.5rem` (`rounded-lg`).
- Feature banners or focal callout containers cap at `0.75rem` (`rounded-xl`).
- Micro status tags, pill indicators, and the Tamil/English language switcher utilize full circular radius (`rounded-full`) to cleanly separate functional state tags from actionable structural cards.

Excessive roundedness is avoided to prevent the platform from feeling like a casual toy, while sharp 90-degree corners are softened just enough to ensure human warmth and civic approachability.

## Components

### 1. Buttons
- **Primary Action (Scan / Report):** Solid Primary Navy (`#0f233d`) fill, white text, `0.375rem` roundedness, font weight 600. Focus ring: `2px` offset with `#0d9488`.
- **Secondary Action (Verify / Copy):** `#ffffff` background with `1px` border of `#cbd5e1`, primary navy text, hover state transitions to `#f1f5f9`.
- **Destructive / High Alert Action:** Solid Vermilion (`#c2410c`) fill with white text, used solely for reporting active cyber fraud or blocking contacts.
- **Tamil Language Considerations:** Horizontal padding on all buttons must be minimum `1.25rem` (`space-md`+) to accommodate wider translated character strings without wrapping.

### 2. Risk Badges & Status Chips
- **High Risk:** Background `#fef2f2`, border `#fecaca`, text `#991b1b`, prefixed with an alert triangle icon.
- **Suspicious / Caution:** Background `#fffbeb`, border `#fde68a`, text `#92400e`, prefixed with an eye/caution icon.
- **Safe / Verified:** Background `#f0fdfa`, border `#99f6e4`, text `#115e59`, prefixed with a check-shield icon.
- **Structure:** `rounded-full`, inline-flex, `0.25rem` vertical by `0.75rem` horizontal padding, paired with `label-sm` typography.

### 3. Transparent Evidence Cards
- Built on `#ffffff` surfaces with a standard `1px` border (`#e2e8f0`).
- Divided into three distinct horizontal sections:
  1. *Observed Signal:* The exact SMS text, APK permission, or UPI identifier analyzed.
  2. *Reasoning Matrix:* Plain-language bullet points explaining why the pattern triggered a flag.
  3. *Action Mandate:* Plain-text instruction (e.g., "Do not click link. Forward to 1930 immediately").

### 4. Input Fields & Analysis Area
- Input text fields and textareas feature a distinct `1.5px` border in `#cbd5e1`, changing to Primary Navy (`#0f233d`) with a subtle teal outline glow on focus.
- Clear bilingual placeholder strings: `Paste message, URL, or UPI ID here... / செய்தி, இணைய முகவரி அல்லது UPI ஐடியை ஒட்டவும்...`.
- Accompanying file upload dropzones use dashed borders (`2px dashed #94a3b8`) over `#f8fafc`.

### 5. Checkboxes & Radio Elements
- Custom `1.25rem` square elements with `0.25rem` border-radius.
- Checked state uses Primary Navy fill with a crisp white geometric checkmark. Radio buttons use a centered `6px` teal dot.
- Tap targets are expanded to an absolute minimum of `44px x 44px` on mobile viewports for ease of use by senior citizens.

### 6. Honest Limitations & AI Disclaimer Callouts
- Dedicated full-width banner at the foot of risk reports using background `#f1f5f9` with border `#cbd5e1`.
- Informational icon paired with explicit copy: "Namma Kavacham AI provides automated probabilistic assessments. It does not replace official advice from the National Cyber Crime Reporting Portal (cybercrime.gov.in) or local law enforcement."
- Tamil translation mirrored underneath in `body-sm`.

### 7. Bilingual Language Toggle
- Compact segmented control embedded within the global header.
- Enclosed in a `rounded-full` container (`#e2e8f0` border, `#f8fafc` background).
- Active state displays as a clean white pill with elevated micro-shadow (`#0f233d` text weight 600), enabling 1-click toggling between `English` and `தமிழ்`.
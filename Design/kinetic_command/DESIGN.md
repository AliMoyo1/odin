---
name: Kinetic Command
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#20201f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353535'
  on-surface: '#e5e2e1'
  on-surface-variant: '#e2bfb0'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#a98a7d'
  outline-variant: '#5a4136'
  surface-tint: '#ffb693'
  primary: '#ffb693'
  on-primary: '#561f00'
  primary-container: '#ff6b00'
  on-primary-container: '#572000'
  inverse-primary: '#a04100'
  secondary: '#c9c6c5'
  on-secondary: '#313030'
  secondary-container: '#4a4949'
  on-secondary-container: '#bab8b7'
  tertiary: '#ffba20'
  on-tertiary: '#412d00'
  tertiary-container: '#c78f00'
  on-tertiary-container: '#422d00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbcc'
  primary-fixed-dim: '#ffb693'
  on-primary-fixed: '#351000'
  on-primary-fixed-variant: '#7a3000'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c9c6c5'
  on-secondary-fixed: '#1c1b1b'
  on-secondary-fixed-variant: '#474646'
  tertiary-fixed: '#ffdea8'
  tertiary-fixed-dim: '#ffba20'
  on-tertiary-fixed: '#271900'
  on-tertiary-fixed-variant: '#5e4200'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353535'
  system-amber: '#FFB800'
  terminal-black: '#050505'
  status-critical: '#FF3D00'
  status-safe: '#00E676'
  glass-border: rgba(255, 107, 0, 0.15)
typography:
  headline-lg:
    fontFamily: JetBrains Mono
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.1em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-mobile: 12px
  margin-desktop: 24px
  sidebar-width: 280px
  console-height: 200px
---

## Brand & Style

The brand personality is **omniscient, technical, and authoritative**. It is designed for power users who require absolute situational awareness and high-speed data orchestration. The UI should evoke the feeling of a "Modular Monolith"—a secure, indestructible command center that processes vast amounts of intelligence in real-time.

The design style is a hybrid of **Minimalist Brutalism** and **Modern HUD (Heads-Up Display)**. It prioritizes information density and technical utility over decorative whitespace. Visual elements are sharp and structured, using high-contrast "Vibrant Orange" against "Deep Matte Black" to create a sense of urgency and precision. The "Hermes" orb serves as a focal point of intelligence, represented by a glowing, interactive amber element that breathes with system activity.

## Colors

The palette is strictly high-contrast to ensure legibility in low-light environments and to maintain a technical "system" feel.

- **Primary (Vibrant Orange):** Used for critical CTAs, active states, and high-priority data points.
- **Secondary (Deep Matte Black):** The base canvas. It provides a non-reflective, deep surface that recedes, allowing data to pop.
- **Neutral (Dark Charcoal):** Used for container backgrounds and UI chrome to create subtle separation between modules.
- **Accent (Amber Glow):** Reserved for the "Hermes" orb and subtle status indicators. It should be implemented with a soft outer glow (drop-shadow or box-shadow) to simulate a light source.

## Typography

The system employs a dual-font strategy. **JetBrains Mono** is used for headings, labels, and all data-driven content to reinforce the "terminal" aesthetic and ensure perfect character alignment in logs. **Inter** is used for body copy and chat messages to maintain high readability during long periods of technical review.

- **Scale:** Sizes are kept compact to support high information density. 
- **Hierarchy:** Use `label-caps` for section headers and metadata to provide a structured, "scannable" interface.
- **Color:** Headlines and primary labels use the primary orange or pure white; secondary data uses a muted grey or amber.

## Layout & Spacing

This design system uses a **Fixed Grid Strategy** on desktop to ensure that widgets and metric panels remain in consistent, predictable locations—critical for "muscle memory" in a command-center environment.

- **Modular Monolith:** The layout is divided into three primary vertical zones: a collapsed sidebar for navigation, a central flexible chat/workspace, and a fixed right-hand metrics panel.
- **Console:** A bottom-pinned panel is dedicated to live logs and terminal output.
- **Density:** We use a 4px base unit. Panning and margins are kept tight (8px-16px) to maximize the "Real Estate Schema," allowing the user to view dozens of metrics simultaneously without scrolling.
- **Breakpoints:** On mobile, the sidebars collapse into a drawer system, prioritizing the central chat and "Hermes" orb interactions.

## Elevation & Depth

Visual hierarchy is achieved through **Tonal Layering** and **Subtle Glows** rather than traditional drop shadows.

- **Layers:** Surface containers use `#1A1A1A` to sit slightly above the `#0D0D0D` background. Higher-priority "Safety Intercepts" or modals use a thin `1px` border of `glass-border` to define their boundaries.
- **Glow Effects:** Interactive elements (like the Hermes orb) use a `0px 0px 20px` amber outer glow to indicate activity and "intelligence."
- **Focus States:** Active inputs or selected cards are indicated by a sharp primary orange border and a low-opacity orange inner tint.

## Shapes

The shape language is **Soft-Brutalist**. UI elements use a small `4px` (0.25rem) radius to feel modern and professional without losing the "hard" edge of a technical system.

- **Buttons & Cards:** Use a consistent `rounded-sm` (4px) profile.
- **The Hermes Orb:** The only exception to the rule, the orb is a perfect circle, representing a central core of intelligence that stands out against the rectangular grid of the UI.
- **Data Bars:** Progress indicators and budget bars are rectangular with sharp or minimally rounded edges to maximize pixel alignment.

## Components

- **Buttons:** Primary buttons are solid `primary_color_hex` with black text. Secondary buttons use an outline style with orange text. 
- **The Hermes Orb:** A persistent floating action button (FAB) or header element. It should have a "breathing" animation (pulsing scale/glow) when the system is processing information.
- **Input Fields:** Dark backgrounds (`#050505`) with subtle 1px borders. The cursor should be a solid orange block, mimicking a terminal.
- **Cards/Widgets:** Modular containers with a `label-caps` header area. Use thin dividers to separate internal data points.
- **Safety Intercepts:** A unique "Gate Locked" component for tool execution. It features a high-visibility orange header, a summary of the pending action, and a large [APPROVE] button that requires a deliberate interaction.
- **Progress Bars:** Thin, flat bars. Use orange for standard progress and amber for "proactive monitoring" metrics.
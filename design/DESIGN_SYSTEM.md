# SkillPulse Design System — "Playful Brutalist"

Mockup: [mockup.html](mockup.html) (open it in a browser with internet, so the Google Fonts load).

**The idea:** a serious data tool that feels friendly. Giant ink-black type, flat bold colours,
thin black borders, hard offset shadows, and four mascot "gadget friends" that stand for parts
of the product.

## Colours

| Token | Hex | Used for |
|---|---|---|
| `--bg` | `#D7E1E1` | page background (pale slate) |
| `--bg-shadow` | `#BCC9C9` | offset shadows under cards & mascots |
| `--paper` | `#FFFFFF` | cards, inputs |
| `--ink` | `#1C1C1C` | text, borders, primary button |
| `--ink-2` / `--ink-3` | `#3D4242` / `#6A7272` | body text / captions |
| `--sun` | `#FFB000` | illustration, "skills to learn" chips |
| `--tangerine` | `#F2541B` | illustration, "falling" values |
| `--sky` | `#2BA8F0` | illustration |
| `--navy` | `#2B2D8E` | illustration |
| `--forest` / `--good` | `#0E6B47` | illustration, "rising" values, ✓ marks |

**Chart palette** (checked for colourblind safety and 3:1 contrast on white; always in this order):
`#4A4FD6` → `#F2541B` → `#168BCC`. A single-series chart uses `#4A4FD6` only.

## Fonts (Google Fonts, free)

| Role | Font | Example |
|---|---|---|
| Mega title | **Anton** | SKILL PULSE |
| Headings, buttons, chips, ribbon | **Bowlby One** | GET YOUR MATCH SCORE |
| Body, numbers in tables | **Inter** | paragraphs, captions |

## Components

- **Card:** white, `2px solid ink` border, shadow `6px 6px 0 #BCC9C9`, square corners.
- **Button (outline):** white, ink border, shadow `4px 4px 0 ink`; lifts on hover, presses on click.
- **Button (primary):** ink background, white Bowlby text, full width in forms.
- **Chip (filter):** outlined; selected = ink background.
- **Ribbon:** tilted −4°, white strip with ink borders, scrolling **live trending skills**.
- **Divider:** 1.5px ink line, 520px wide, centred, big vertical space around it.

## Mascots (original, inline SVG, in `mockup.html`)

| Name | What it is | Stands for |
|---|---|---|
| Chartie | retro monitor with a "LIVE" strip | live market trends |
| Resumo | clipboard with a checklist | your resume |
| Lensy | magnifying glass | finding skills / gaps |
| Baseo | database cylinder | the job database |

Style rules: 5px ink outline, flat fills from the palette, one grey offset shadow, simple face.

## How this maps to Streamlit (Phase 3)

- `.streamlit/config.toml` sets the base colours and fonts.
- A `theme.css` file injected with `st.markdown(..., unsafe_allow_html=True)` adds borders,
  shadows, Bowlby headings and button styles.
- Hero, ribbon, mascots and job cards are rendered as small HTML blocks (`st.html`).
- Charts use Plotly with a custom template: these colours, Inter font, light grid, no chart border.
- Not possible in Streamlit: fully custom layout animations. Everything else in the mockup is doable.

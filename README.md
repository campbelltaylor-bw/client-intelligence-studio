# Competitor Intelligence Studio

AI-powered competitive research for sales and product teams. Enter a competitor name — Claude searches the web, builds a structured profile, runs a comparative analysis against your company, and produces a sales-ready battle card.

![Python](https://img.shields.io/badge/python-3.11+-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red) ![Claude](https://img.shields.io/badge/claude-sonnet--4--6-blueviolet)

---

## What it does

**Per competitor run:**
1. **Web Research** (Claude Haiku) — tool-use loop, up to 5 searches → structured `CompetitorProfile`
2. **Profile Load** — reads your company's YAML, markdown, and PDF files from the profile directory
3. **Analysis** (Claude Sonnet) — comparative analysis against your products and positioning
4. **Battle Card** (Claude Sonnet) — objection handlers, differentiators, win/loss scenarios
5. **Cache** — saved to `competitor_intelligence/outputs/{mode}/` for instant reload

---

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

streamlit run competitor_intelligence/Competitor_Landscape.py
```

---

## Pages

| Page | File | Description |
|------|------|-------------|
| Competitor Landscape | `Competitor_Landscape.py` | Research a single competitor — profile, analysis, battle card |
| Product Landscape | `pages/1_Product_Landscape.py` | Scan the market for competitors in a given product category |

---

## Company modes

Toggle between modes in the sidebar. Each mode has its own profile library, product catalog, watchlist, and output cache.

| Mode | Profile Dir | Products | Watchlist | Output Cache |
|------|-------------|----------|-----------|--------------|
| **Context Analytics** | `our_profile/` | `data/context_analytics_products.yaml` | `competitors_to_watch.yaml` | `outputs/ca/` |
| **Bridgewise** | `bridgewise_profile/` | `data/bridgewise_products.yaml` | `bridgewise_competitors_to_watch.yaml` | `outputs/bridgewise/` |

Bridgewise mode draws on a curated profile library: ICP, company segments, buying personas, positioning/moat, sales cycle mechanics, and brand assets.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |

---

## Project structure

```
competitor_intelligence/
  Competitor_Landscape.py        — main Streamlit entry point
  pages/
    1_Product_Landscape.py       — market scanner page
  config.py                      — multi-mode config (CA vs Bridgewise)
  models.py                      — Pydantic models (CompetitorProfile, BattleCard, …)
  researcher.py                  — web research agent (Haiku, tool-use loop)
  analyzer.py                    — comparative analysis + battle card (Sonnet)
  profile_loader.py              — loads YAML/MD/PDF from profile directory
  watchlist.py                   — watchlist CRUD + AI-assisted discovery
  renderer.py                    — Streamlit UI components
  pdf_exporter.py                — PDF report export
  prompts.py                     — all Claude prompt templates
  data/
    context_analytics_products.yaml
    bridgewise_products.yaml
  assets/
    context_analytics_logo.png
  our_profile/                   — CA reference materials (drop folder)
  bridgewise_profile/            — Bridgewise reference materials (drop folder)
  outputs/
    ca/                          — cached CA reports (gitignored)
    bridgewise/                  — cached Bridgewise reports (gitignored)
  competitors_to_watch.yaml
  bridgewise_competitors_to_watch.yaml
  README.md                      — full app documentation
  METHODOLOGY.md                 — technical methodology and architecture
```

See [`competitor_intelligence/README.md`](competitor_intelligence/README.md) for full documentation.

---

## Legacy

The original CRM-based collateral generation app (Client Intelligence Studio) is archived under [`legacy/`](legacy/). It is not actively maintained.

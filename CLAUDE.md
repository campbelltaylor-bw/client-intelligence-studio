# Competitor Intelligence Studio

AI-powered competitive research tool. The primary app is `competitor_intelligence/`.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
streamlit run competitor_intelligence/Competitor_Landscape.py
```

## Running Legacy Tests

```bash
pytest legacy/tests/
```

## Key Conventions (Competitor Intelligence)

- All prompt templates live in `competitor_intelligence/prompts.py` as module-level string constants.
- Company modes: `"ca"` (Context Analytics) and `"bridgewise"`. Config loaded via `competitor_intelligence/config.py`.
- Product YAMLs live in `competitor_intelligence/data/`. Profile markdown/PDFs live in `our_profile/` or `bridgewise_profile/`.
- Reports are cached to `competitor_intelligence/outputs/{mode}/`. The app reloads from cache on repeat visits.
- The web research stage uses a tool-use loop (max 10 iterations, up to 5 searches per call) via Claude Haiku.
- Analysis and battle cards use Claude Sonnet.

## Environment Variables

Required:
- `ANTHROPIC_API_KEY`

## Project Structure

```
competitor_intelligence/         — PRIMARY APP
  Competitor_Landscape.py        — Streamlit entry point
  pages/1_Product_Landscape.py   — market scanner page
  config.py                      — multi-mode config
  models.py                      — Pydantic data models
  researcher.py                  — web research agent (Haiku)
  analyzer.py                    — analysis + battle cards (Sonnet)
  profile_loader.py              — loads YAML/MD/PDF profile files
  watchlist.py                   — watchlist CRUD + AI discovery
  renderer.py                    — Streamlit UI
  pdf_exporter.py                — PDF export
  prompts.py                     — all Claude prompts
  data/                          — product catalogs (CA + Bridgewise)
  assets/                        — logos
  our_profile/                   — CA reference materials
  bridgewise_profile/            — Bridgewise reference materials
  outputs/                       — cached reports (gitignored)

legacy/                          — archived Client Intelligence Studio
  app/main.py                    — original Streamlit entry point
  src/                           — pipeline, models, providers
  tests/                         — pytest suite
  data/                          — mock data and catalogs
  config/                        — config.yaml
```

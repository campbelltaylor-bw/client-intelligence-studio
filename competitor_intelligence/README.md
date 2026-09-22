# Competitor Intelligence

AI-powered competitive research tool built on Claude. Generates structured competitor profiles, side-by-side comparative analyses, and sales battle cards — with a toggle to run as either **Context Analytics** or **Bridgewise**.

## Quick Start

```bash
# From the project root
.venv/bin/streamlit run competitor_intelligence/Competitor_Landscape.py
```

Then open http://localhost:8501.

---

## Pages

### Competitor Landscape (`Competitor_Landscape.py`)
Main app. Enter a competitor name → Claude searches the web → generates a profile, comparative analysis, and battle card.

- **View as** toggle (sidebar) switches between Context Analytics and Bridgewise modes
- Results are cached to `outputs/ca/` or `outputs/bridgewise/` and reloaded instantly on repeat visits
- **Watchlist** shows curated competitors by category; click Research to run a fresh report or Load to pull from cache
- **Discover more with AI** asks Claude to suggest new competitors relevant to the active company

### Product Landscape (`pages/1_Product_Landscape.py`)
Market scanner. Select one of our product categories → Claude finds all companies competing in that space. Also respects the active company mode.

---

## Company Modes

| Mode | Profile dir | Products YAML | Watchlist | Outputs |
|------|-------------|---------------|-----------|---------|
| Context Analytics | `our_profile/` | `data/context_analytics_products.yaml` | `competitors_to_watch.yaml` | `outputs/ca/` |
| Bridgewise | `bridgewise_profile/` | `data/bridgewise_products.yaml` | `bridgewise_competitors_to_watch.yaml` | `outputs/bridgewise/` |

Switch mode using the **View as** radio at the top of the sidebar. The watchlist, recent searches, AI suggestions, and analysis prompts all update to reflect the active company.

---

## Profile Directories

### `our_profile/` — Context Analytics reference materials
Drop any files here to give Claude more context about CA when generating analyses. The loader picks up `.yaml`, `.md`, and `.pdf` files automatically (alphabetical, YAML first). `README.md` is skipped.

The master CA product catalog (`data/context_analytics_products.yaml`) is always loaded first — no need to duplicate it here.

### `bridgewise_profile/` — Bridgewise reference materials
Same behaviour as above, but used when the app is in Bridgewise mode. Currently contains the Bridgewise logo and product slides. Add more `.yaml`/`.md`/`.pdf` files here to enrich BW analysis.

---

## Architecture

```
Competitor_Landscape.py   — Streamlit entry point + mode toggle
config.py                 — Per-mode config (paths, model, company name)
researcher.py             — Claude web search tool loop (Haiku, max 5 searches)
analyzer.py               — Comparative analysis + battle card (Sonnet)
profile_loader.py         — Loads our profile dir (YAML + MD + PDF)
prompts.py                — All Claude prompt templates (parameterized)
renderer.py               — Streamlit UI components for reports
watchlist.py              — Load/add/discover competitors in YAML watchlist
models.py                 — Pydantic data models
pdf_exporter.py           — PDF report export
pages/
  1_Product_Landscape.py  — Market scanner page
our_profile/              — CA reference materials (PDFs, decks, guides)
bridgewise_profile/       — Bridgewise reference materials
outputs/
  ca/                     — Cached CA competitor reports (gitignored)
  bridgewise/             — Cached BW competitor reports (gitignored)
```

### Pipeline per research run

1. **Research** — `CompetitorResearcher` (Haiku) runs a web search tool loop, up to 5 searches, returns a structured `CompetitorProfile`
2. **Profile load** — `load_our_profile()` reads the active company's profile dir (YAML → MD → PDF)
3. **Analysis** — `CompetitorAnalyzer` (Sonnet) compares competitor vs. our profile, returns `CompetitiveAnalysis`
4. **Battle card** — `generate_battle_card()` (Sonnet) distills the analysis into a rep-ready card
5. **Cache** — Full report saved to `outputs/{mode}/competitor_{slug}_{timestamp}.json`

### Model split

| Stage | Model | Why |
|-------|-------|-----|
| Web research | `claude-haiku-4-5-20251001` | Fast, cheap; web search doesn't need deep reasoning |
| Analysis + battle card | `claude-sonnet-4-6` | Quality matters; generates nuanced comparisons and sales copy |

---

## Watchlists

- `competitors_to_watch.yaml` — 20+ CA competitors across NLP, sentiment, alt-data, document intelligence
- `bridgewise_competitors_to_watch.yaml` — 13 BW competitors across AI ratings, wealth tech, embedded fintech

Add a company via the sidebar expander, or click **Discover more with AI** to have Claude suggest additions. Both actions write directly to the active mode's YAML file.

---

## Configuration

Configured via `config.py`. Key fields on `AppConfig`:

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `claude-sonnet-4-6` | Model for analysis and battle cards |
| `research_model` | `claude-haiku-4-5-20251001` | Model for web research |
| `our_company_name` | set by mode | Used in all prompts and UI labels |
| `products_yaml_path` | set by mode | Master product catalog fed to analysis |
| `our_profile_dir` | set by mode | Reference materials directory |
| `outputs_dir` | set by mode | Where reports are cached |
| `watchlist_path` | set by mode | Competitor watchlist YAML |

Requires `ANTHROPIC_API_KEY` in `.env`.

# Competitor Intelligence Studio — Technical Methodology

## Overview

A Streamlit application that generates on-demand structured competitor profiles, comparative analyses, and sales battle cards. It supports two independent company modes (Context Analytics and Bridgewise), each with its own product catalog, reference profile, watchlist, and outputs directory.

---

## Architecture

```
Competitor_Landscape.py        — Streamlit entry point, UI and orchestration
competitor_intelligence/
  config.py                    — multi-company AppConfig (ca / bridgewise)
  models.py                    — Pydantic schemas for all structured outputs
  researcher.py                — Stage 1: web research via Claude tool use
  profile_loader.py            — Stage 1b: loads our own reference profile
  analyzer.py                  — Stage 2: comparative analysis + battle card
  watchlist.py                 — watchlist CRUD + AI-assisted discovery
  renderer.py                  — Streamlit UI rendering
  pdf_exporter.py              — PDF export
  prompts.py                   — all Claude prompt templates
```

---

## Pipeline (per research run)

### Stage 1 — Web Research (`researcher.py`)

- Instantiates `CompetitorResearcher` with `claude-haiku-4-5` (fast/cheap for open-ended search)
- Calls `client.beta.messages.create` with the `web_search_20250305` tool enabled (up to 5 uses per call) inside a 10-iteration tool-use loop
- The loop: sends a prompt → checks the response; if `stop_reason == "end_turn"` or no tool calls remain, collects all text blocks and exits; otherwise appends assistant + empty `tool_result` messages and continues
- The prompt instructs the model to return a specific JSON schema covering: company overview, products (with use cases, deliverable formats, source URLs), recent news, and all cited source URLs
- Output is parsed from a fenced code block via regex → `CompetitorProfile` Pydantic model

### Optional — Product-specific search

- If the user enables "Search for product equivalents", a second pass runs `researcher.research_products()` using the same tool-use loop but a different prompt that queries each of our product categories against the competitor explicitly
- New products are merged into the profile, deduped by name

### Stage 1b — Our Profile Loading (`profile_loader.py`)

- Reads `data/<company>_products.yaml` (structured product catalog)
- Reads all `.yaml`, `.md`, and `.pdf` files from `our_profile/` (persona docs, pitch decks, field guides) — PDFs are text-extracted page by page via `pypdf`
- All content is concatenated into a single context string passed to the analysis prompt

### Stage 2 — Competitive Analysis (`analyzer.py`)

- Instantiates `CompetitorAnalyzer` with `claude-sonnet-4-6` (stronger model for nuanced reasoning)
- Uses `client.messages.stream()` — streams the full response and reads it at completion
- Prompt provides both the serialized `CompetitorProfile` JSON and our full profile text, asking for a structured JSON analysis covering: executive summary, per-product comparisons (one row per our product), audience overlap by job title, our strengths, their strengths, and capability gaps
- Output is parsed → `CompetitiveAnalysis` Pydantic model

### Stage 3 — Battle Card (`analyzer.py` → `generate_battle_card`)

- Separate Sonnet call; takes the `CompetitiveAnalysis` JSON as its only input
- Prompt is written for sales rep consumption: concise differentiators (one sentence each), objection handlers scoped to audiences identified in the analysis, when-we-win vs. when-they-win scenarios, and plain-language discovery questions
- Output parsed → `BattleCard` Pydantic model

### Persistence

- The complete `CompetitorReport` (profile + analysis + battle card + metadata) is serialized to JSON and saved to `outputs/<mode>/competitor_<slug>_<timestamp>.json`
- On subsequent requests for the same company, the app loads the most recent cached file rather than re-running — a "Re-run" button forces a fresh pass

---

## Watchlist & Discovery

- Competitors are tracked in per-mode `competitors_to_watch.yaml` files
- "Discover more with AI" calls a plain (no-tool-use) Sonnet call with a prompt that includes the existing watchlist names and asks for 5 new suggestions as a JSON array, using a hardcoded company context block per mode
- New entries are written back to YAML via `watchlist.add_to_watchlist()`

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Two-model split (Haiku for research, Sonnet for analysis) | Web research is quantity-oriented; Haiku handles it cheaply. Analysis requires structured reasoning; Sonnet is used there. |
| Tool-use loop capped at 10 iterations | Prevents runaway calls; web search typically resolves in 2–4 turns. |
| All prompts return raw JSON | Eliminates a parsing tier; regex extracts fenced blocks, Pydantic validates structure. |
| `our_profile/` is a drop folder | Any PDF, YAML, or Markdown added to the directory is automatically ingested — no code change needed when the reference profile is updated. |
| Per-company-mode isolation | Config, watchlist, outputs, and profile are entirely separate per mode, so CA and Bridgewise reports never mix. |

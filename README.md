# Client Intelligence Studio

AI-powered collateral generation for sales and account teams. Combines CRM data, live web research, and a curated product and blog catalog to produce personalized, evidence-backed client briefs and outreach emails — all in a clean Streamlit interface.

![Python](https://img.shields.io/badge/python-3.11+-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red) ![Claude](https://img.shields.io/badge/claude-sonnet--4--6-blueviolet)

---

## What it does

1. **Select an account** — load from Monday.com CRM or mock data
2. **Run the pipeline** — 6 stages: CRM enrichment, web research, product scoring, blog matching, AI generation, assembly
3. **Review outputs** across four tabs:
   - **Internal Brief** — account summary, CRM highlights, key opportunities (never shared with clients)
   - **Web Research** — company overview, recent news, technology signals
   - **Products** — ranked product recommendations with relevance scores
   - **Outreach Emails** — three audience-specific drafts (Portfolio Manager, Quantitative Analyst, Risk Officer) generated from live blog content

All facts carry a source tag (`CRM_FACT`, `PUBLIC_FACT`, `AI_INFERENCE`) that propagates through the entire pipeline.

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# 3. Run the app (mock data by default)
streamlit run app/main.py
```

The app runs in mock mode out of the box — no CRM credentials required.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `MONDAY_API_KEY` | No | Monday.com API key (real CRM mode only) |
| `MONDAY_BOARD_ID` | No | Monday.com board ID (real CRM mode only) |

To switch from mock to real integrations, set `USE_MOCK_DATA=false` in `.env`.

---

## Project structure

```
app/
  main.py                  — Streamlit entry point
  views/                   — Page views (account selection, intelligence report)
  components/              — UI helpers, theme CSS, output renderers

src/
  config.py                — Config loading and env var validation
  models.py                — Pydantic data models
  ai_client.py             — Anthropic SDK wrapper
  pipeline/                — 6-stage pipeline (runner.py is the entry point)
  prompts/prompts.py       — All Claude prompt templates
  providers/               — CRM, web research, and blog catalog providers

data/
  blog_catalog.csv         — Research content catalog
  context_analytics_products.yaml — Product definitions
  mock_monday_accounts.json       — Mock CRM accounts
  mock_web_research.json          — Mock web research results

tests/                     — pytest suite
```

---

## Running tests

```bash
pytest tests/
```

---

## Deployment

### Streamlit Community Cloud

1. Fork or push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo
3. Set main file: `app/main.py`
4. Add `ANTHROPIC_API_KEY` under Secrets
5. Deploy

### Docker

```bash
docker build -t client-intelligence-studio .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... client-intelligence-studio
```

---

## Security notes

- `ClientFacingOutputs` structurally excludes all CRM fields — internal data cannot leak into client-facing content
- No email sending capability — outputs are copy-only
- No CRM write-back — all CRM provider methods are read-only
- API keys are never logged or surfaced in the UI

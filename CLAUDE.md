# Client Intelligence Studio

Hackathon MVP — generates personalized, evidence-backed client collateral for sales and account teams.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
streamlit run app/main.py
```

## Running Tests

```bash
pytest tests/
```

## Key Conventions

- All source tags (`CRM_FACT`, `PUBLIC_FACT`, `AI_INFERENCE`) propagate from raw data through the entire pipeline.
- `ClientFacingOutputs` structurally cannot contain CRM fields — never add CRM data there.
- All prompt templates live in `src/prompts/prompts.py` as module-level string constants.
- Mock data is the default (`USE_MOCK_DATA=true` in config.yaml). Flip to `false` in `.env` for real integrations.
- There is no email sending capability anywhere in this codebase. "Copy to Clipboard" only.
- There is no Monday write-back. `MondayCRMProvider` base class has read-only methods only.

## Environment Variables

Required:
- `ANTHROPIC_API_KEY`

Optional (only when USE_MOCK_DATA=false):
- `MONDAY_API_KEY`
- `MONDAY_BOARD_ID`

## Project Structure

```
src/config.py          — config loading (validates all env vars at startup)
src/models.py          — all Pydantic data models
src/ai_client.py       — Anthropic SDK wrapper
src/providers/         — CRM, web research, blog catalog providers (mock + real)
src/pipeline/          — 6-stage pipeline (runner.py is the entry point)
src/prompts/prompts.py — all Claude prompt templates
app/main.py            — Streamlit entry point
app/pages/             — 3 Streamlit pages
tests/                 — pytest suite
data/                  — mock data and catalogs
outputs/               — saved pipeline outputs (gitignored)
```

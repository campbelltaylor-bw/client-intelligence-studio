# Legacy: Client Intelligence Studio

This folder contains the original Client Intelligence Studio — an AI-powered collateral generation tool for sales teams that combined CRM data (Monday.com), live web research, and a curated product/blog catalog to produce personalized client briefs and outreach emails.

It is archived here for reference. The active application is the [Competitor Intelligence Studio](../competitor_intelligence/README.md) at the repo root.

## Running the legacy app

```bash
pip install -r ../requirements.txt
cp ../.env.example ../.env
# Add ANTHROPIC_API_KEY to .env

streamlit run app/main.py
```

## Running legacy tests

```bash
pytest tests/
```

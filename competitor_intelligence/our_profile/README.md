# our_profile/

This directory holds reference material about Context Analytics that the competitor intelligence tool uses when generating comparative analysis.

## What to put here

Drop any `.yaml` or `.md` files describing:

- Audience personas (see `audience_personas.yaml` for the template)
- Pricing tiers or go-to-market positioning
- Partnership or integration details
- Competitive positioning narratives
- Data coverage maps
- Any other context you want Claude to use when comparing us to a competitor

The tool loads all `.yaml` and `.md` files in this directory automatically at runtime (alphabetical order, YAML first). `README.md` is skipped.

## What's already loaded automatically

In addition to files here, the tool always loads:

```
../data/context_analytics_products.yaml
```

This is the master product catalog with full descriptions, use cases, and coverage for all Context Analytics products. You do not need to duplicate that content here.

## Tips

- Keep files focused — one topic per file is easier to maintain
- YAML is preferred for structured data; Markdown is fine for narrative context
- Files are passed verbatim to Claude, so clear headings and labels help the model reason about them

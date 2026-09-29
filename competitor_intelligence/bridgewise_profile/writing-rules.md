# Writing rules

**Owner:** Michelle Bitran · **review_by:** 2027-03-02 · **sources:** `Brand Messaging Book Update` (Michelle Bitran, July 2026, supersedes the earlier working draft routed in by Shahar Heimann 2026-09-02, archived at `docs/brand-messaging-book-2026-07-source.md`); `references/review-cadences.md` (brand rules = semi-annual)

The mechanical half of how we write: which words are ours, which are banned, how we name things, and the pass every draft goes through before it ships. The feel behind these rules is in [`voice-and-tone.md`](voice-and-tone.md).

**Any skill in this repo that generates external-facing copy should load this file before drafting.**

## Words we use

investment AI · guided investment experience · embedded · compliant · enterprise-ready · transparent · explainable · activate · LTV · share of wallet

*Carried over from the original working draft. The July 2026 update doesn't repeat this list, so it's treated as still standing rather than dropped — flag to Michelle if any of these are stale.*

## Words and patterns we ban

The AI-cliché blacklist. These are the tells that a machine wrote the draft.

- **Fake contrast** — "it's not just X, it's Y"
- **Landscape openers** — "in an era where…"
- **Symmetrical bookends** — an opening line the closing line mirrors
- **Three abstract nouns in a row**
- **"delve"**
- **"unlock"**
- **"in today's fast-paced world"**
- **Sweeping philosophical wrap-ups**

**Em-dashes, updated 2026-09-08.** The original rule banned em-dashes outright in original drafts. The July 2026 update reframes this as "minimize overuse of em-dashes" instead. Treating the newer, dated ruling as current — but flagging the change explicitly since it loosens a rule rather than tightens it, in case that wasn't the intent.

**Primary source on all data, added 2026-09-08.** Before any statistic ships, trace it back to where it came from. This is stricter than a general reminder to cite sources — it means the check happens per draft, not just per file.

## Jargon discipline

Don't stack product trademarks into a name parade. Plain, precise language beats a wall of ™s.

## Grammar and mechanics

- **US English** — not British or Canadian spelling.
- **Sentence case for titles** — don't capitalize every word.
  - Title case (don't do this): "Why Most First-Time Investors Underestimate Risk"
  - Sentence case (do this): "Why most first-time investors underestimate risk"
  - Exception: design contexts (e.g. ad creative) may need title case, but each exception needs individual approval — it isn't a standing carve-out.
- **Numbers** — spell out one through nine; use digits for 10 and up.

## Naming

Resolves the casing question flagged 2026-09-02 — see the note in [`boilerplate.md`](boilerplate.md) for the ripple effect on the rest of the repo.

- **Bridgewise** — capital B, lowercase w.
- **Bridget™** — always carry the trademark sign.
- **pAI** — lowercase p, uppercase AI.
- **Bridgewise for Retail Brokerages**, **Bridgewise for Wealth Advisory** — capitalize on first mention; on later mentions in the same piece, the vertical name may drop capitalization (e.g. "Bridgewise for wealth advisory").
- **Bridgewise Frontier for Retail Brokerages**, **Bridgewise Frontier for Wealth Advisory** — same capitalization rule as above.

Product names, descriptions and benefit statements to pair with these are in [`boilerplate.md`](boilerplate.md#product-boilerplate).

## Best practices

- **Active voice**, wherever possible.
  - Passive (avoid): "Risk is often underestimated by first-time investors."
  - Active (prefer): "First-time investors often underestimate risk."
- **Vary sentence length.**
- **Punctuate generously** — if a sentence is hard to read aloud, split it.
- **Avoid overusing adverbs** (e.g. "loudly", "easily") — they tend to weaken a sentence.

## The AI-Squeegee pass

Before anything ships, go through the draft line by line:

1. Hunt algorithmic phrasing, predictable structure and symmetry. Remove them.
2. Sharpen the verbs.
3. Cut the fluff.
4. Open with a hook.
5. Close forward-looking.

## Compliance language

- **Never guarantee returns or market movements.** Approved framing: "historical outperformance," "identifies potential opportunities," "mitigates risk."
- **Approved trust claims:**
  - transparent and traceable AI
  - every score and recommendation is fully explainable and auditable
  - deterministic models delivering objective, uniform, repeatable ratings
- **Certifications we can cite:** GDPR, ISO 27001, Investment Advisory License, APIMEC Registration (Brazil).

## Claims

Any external-facing financial claim needs sign-off before it publishes. That is standing rule 1 in `CLAUDE.md`, and it applies to every draft this file governs. The approved figures and the order they are stated in live in `spaces/product-marketing/knowledge/icp/README.md#the-approved-proof-chain`, which is Shany Vinokur's to change.

## Open, routed to Michelle 2026-09-02 — still open

**Scope of the ban list.** These rules were written for copy we publish. It is not yet settled whether they also govern internal Brain prose: this repo's own files, including `CLAUDE.md` and the ICP set, currently use em-dashes and fake contrast freely. The July 2026 update didn't rule on this either way. Michelle still to rule. Until she does, treat the list as binding on external-facing copy only.

# content-component-scorer

**A reusable AI skill for evaluating product page content modularization readiness before an AI-powered paid social ad generation pipeline runs.**

## What It Does

Takes a product page's body content and scores it across five components required for paid social ad generation (Facebook/Instagram):

| Component | What It Checks |
|---|---|
| `headline` | Is there a discrete, self-contained claim extractable for a 27-char ad headline? |
| `short_description` | Is there an independent sentence usable in a 125-char primary text field? |
| `feature_list` | Are product features enumerable and individually extractable? |
| `audience_statement` | Is there clear language identifying who this product is for? |
| `cta` | Is there an action directive that stands alone without surrounding context? |

It also checks metadata completeness (seo_title, seo_description, image_url, image_alt_text, tags).

Output is a structured JSON readiness report per page, including a `pipeline_ready` flag.

## Why I Built This

In my consulting work, teams discover that their AI-generated ad copy is generic or truncated after the pipeline runs. The root cause is almost always structural: the source content was not modular to begin with. Headline, description, and CTA are fused into narrative prose that a model cannot cleanly extract.

This skill surfaces those failures before the pipeline runs. It is the readiness check that has to happen first.

This skill is also designed to be directly reusable in a larger final project: a full Streamlit-based scoring dashboard for a 15-page synthetic product catalog, where this skill becomes the per-row scoring engine.

## How to Use It

### In an agent (Claude Code, Codex, etc.)

The agent discovers this skill through its name and description in SKILL.md. Trigger phrases:
- "Score this product page for paid social readiness"
- "Check if this content is ready for the ad generation pipeline"
- "Which components are missing from this product description?"

### Directly via script

```bash
# Score a single page (plain text)
python scripts/score_components.py \
  --product_name "NovaPack Pro" \
  --body_content "Your product page content here"

# Score a row from a CSV
python scripts/score_components.py \
  --csv_path references/test_pages.csv \
  --row_index 0

# Validate model output schema
python scripts/score_components.py \
  --validate_model_output path/to/model_scores.json
```

## What the Script Does

The Python script handles everything that must be deterministic:

1. **HTML stripping** — CMS exports contain HTML blobs. The script removes tags and decodes entities before the content reaches the model.
2. **Character limit enforcement** — Checks whether any candidate string in the content fits within paid social hard limits (headline: 27 chars, primary text: 125 chars, CTA: 20 chars). A model cannot reliably count characters at scale.
3. **Metadata completeness check** — Field presence check on all required metadata columns. Simple and deterministic.
4. **Output schema validation** — After the model scores, validates that all five components were scored with allowed status values and required reason strings.

The model handles semantic judgment: is a component present, separable, and independently functional?

## Folder Structure

```
.agents/skills/content-component-scorer/
├── SKILL.md                          # Skill metadata, instructions, activation logic
├── scripts/
│   └── score_components.py           # Deterministic pre-check and schema validation
└── references/
    ├── scoring_rubric.md             # System prompt and component definitions for model
    └── test_pages.csv                # Synthetic test data (5 pages, varied failure patterns)
```

## Test Cases

The `references/test_pages.csv` file contains 5 synthetic product pages covering:

| Page | Expected Pattern |
|---|---|
| NovaPack Pro | All five components present and well-structured. Positive control. |
| Lumio Desk Lamp | Headline is dependent ("This changes everything" requires surrounding context). Missing image_url, image_alt_text. |
| ClearSkin Serum | All components pass. Metadata complete. Second positive control with different content structure. |
| Bolt Wireless Charger | Short description embedded (features fused into a single run-on sentence). Missing metadata fields. |
| TrailReady Insoles | Strong feature list and audience statement. Missing CTA. |

## What Worked Well

- The decision tree in the rubric (present → separable → independent → pass) gives the model a clear, consistent path that reduces ambiguity
- Keeping the script and model responsibilities cleanly separated makes the skill easy to test and debug independently
- The `pipeline_ready` flag gives a clear yes/no signal that downstream automation can act on without parsing the full report

## Known Limitations

- Ambiguous separation (a component that exists but is grammatically fused) is the hardest case. The model may classify as `embedded` when the correct label is `dependent`, or vice versa. Low temperature reduces but does not eliminate this variance.
- Shared content (one sentence functioning as both headline and short_description) is not handled. The scorer will credit one and may mark the other missing.
- The scorer does not assess brand voice, creative quality, or legal compliance. A `pipeline_ready: true` result means structurally ready only.
- Character limit checks are candidates-based (shortest sentences in the content). They do not guarantee the actual headline or CTA will fit — only that some string of appropriate length exists in the content.

## Video Walkthrough

[[Watch the demo](YOUR_YOUTUBE_LINK_HERE)](https://youtu.be/w_TAhTj3ndQ)

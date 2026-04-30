---
name: content-component-scorer
description: Scores product page content for modular readiness before it enters an AI-powered paid social ad generation pipeline. Use when a user wants to evaluate whether a product page body content contains the five required components (headline, short_description, feature_list, audience_statement, cta) and whether each component is independently extractable for use in Facebook/Instagram ad formats. Also checks metadata fields for completeness. Do NOT use for general content quality reviews, SEO audits, brand voice checks, or creative feedback.
---

# Content Component Scorer

## Purpose

Determines whether a product page body content is structurally ready to serve as source material for an AI-powered paid social ad generation pipeline. Surfaces component-level failures before the pipeline runs.

## When to Use

- User wants to evaluate whether product page content is ready for AI ad generation
- User asks which components are missing or not extractable from a product description
- User wants to know why AI-generated ad copy came out generic or truncated
- User wants a readiness score before running a content generation pipeline

## When NOT to Use

- General copywriting feedback or creative review
- SEO or GEO optimization
- Brand voice or tone analysis
- Legal or compliance checks
- Evaluating ad performance or creative quality

## Expected Inputs

Either:
- A single product page as plain text
- A CSV with columns: product_name, body_content, product_category, tags, seo_title, seo_description, image_url, image_alt_text

## Character Limit Reference

| Component | Ad Field | Limit |
|---|---|---|
| headline | Facebook/Instagram Headline | 27 characters |
| short_description | Primary Text | 125 characters |
| cta | Call to Action | 20 characters |

## Step-by-Step Instructions

### Step 1: Run the deterministic pre-check

```bash
python scripts/score_components.py --csv_path PATH --row_index N
```

The script strips HTML, checks character limits, and validates metadata completeness.

### Step 2: Score with the model

Send cleaned body_content to the model using the system prompt in references/scoring_rubric.md. The model calls the score_component tool for each of the five components using this decision tree:

1. Is the component present? If NO: missing
2. Is it syntactically separable? If NO: embedded
3. Does it function independently? If NO: dependent
4. All pass: pass

### Step 3: Output the report

Merge model scores with script output into the final JSON report.

## Output Format

```json
{
  "product_name": "string",
  "readiness_score": "N/5 components passing",
  "components": {
    "headline": { "status": "pass|missing|embedded|dependent", "reason": "string or null" },
    "short_description": { "status": "...", "reason": "..." },
    "feature_list": { "status": "...", "reason": "..." },
    "audience_statement": { "status": "...", "reason": "..." },
    "cta": { "status": "...", "reason": "..." }
  },
  "metadata": {
    "seo_title": true,
    "seo_description": true,
    "image_url": true,
    "image_alt_text": true,
    "tags": true
  },
  "metadata_complete": true,
  "pipeline_ready": true
}
```

## Limitations

- Evaluates structural modularity only. A pass score does not mean content is on-brand or legally compliant.
- Ambiguous cases may be scored embedded or dependent inconsistently. Low temperature reduces but does not eliminate this.
- Shared content serving multiple components is not handled by the rubric.
- The scorer does not rewrite or suggest edits. Score and explain only.

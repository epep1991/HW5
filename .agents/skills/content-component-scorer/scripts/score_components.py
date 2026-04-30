#!/usr/bin/env python3
"""
score_components.py
Deterministic pre-check for content modularization readiness.
Handles HTML stripping, character limit checks, metadata validation,
and output schema validation.

Usage:
    python score_components.py --product_name "NAME" --body_content "CONTENT"
    python score_components.py --csv_path data.csv --row_index 0
    python score_components.py --validate_model_output scores.json
"""

import argparse, json, re, sys, csv

CHAR_LIMITS = {"headline": 27, "short_description": 125, "cta": 20}
REQUIRED_METADATA = ["seo_title", "seo_description", "image_url", "image_alt_text", "tags"]
VALID_COMPONENTS = {"headline", "short_description", "feature_list", "audience_statement", "cta"}
VALID_STATUSES = {"missing", "embedded", "dependent", "pass"}

def strip_html(text):
    if not text: return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    for e, c in {"&amp;":"&","&lt;":"<","&gt;":">","&quot;":'"',"&nbsp;":" "}.items():
        clean = clean.replace(e, c)
    return re.sub(r"\s+", " ", clean).strip()

def check_char_limits(body):
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    results = {}
    for comp, limit in CHAR_LIMITS.items():
        fits = [s for s in sentences if len(s) <= limit]
        shortest = min(sentences, key=len) if sentences else ""
        results[comp] = {
            "limit": limit,
            "any_candidate_fits": len(fits) > 0,
            "candidates_within_limit": len(fits),
            "note": f"{len(fits)} candidate(s) fit within {limit} chars" if fits else f"No candidates fit within {limit} char limit (shortest: {len(shortest)} chars)"
        }
    return results

def check_metadata(row):
    fields = {f: bool(row.get(f,"").strip()) for f in REQUIRED_METADATA}
    return {"fields": fields, "metadata_complete": all(fields.values())}

def validate_model_output(scores):
    errors, seen = [], set()
    for s in scores:
        name, status, reason = s.get("component_name",""), s.get("status",""), s.get("reason","")
        if name not in VALID_COMPONENTS: errors.append(f"Invalid component_name: {name}")
        if status not in VALID_STATUSES: errors.append(f"Invalid status {status} for {name}")
        if status != "pass" and not reason: errors.append(f"{name} missing reason")
        if name in seen: errors.append(f"Duplicate: {name}")
        seen.add(name)
    missing = VALID_COMPONENTS - seen
    if missing: errors.append(f"Missing scores for: {missing}")
    return len(errors) == 0, errors

def load_csv_row(path, idx):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if idx >= len(rows): raise ValueError(f"Row {idx} out of range. CSV has {len(rows)} rows.")
    return rows[idx]

def run_precheck(product_name, body_content, metadata_row=None):
    cleaned = strip_html(body_content)
    return {
        "product_name": product_name,
        "cleaned_body_content": cleaned,
        "char_limit_checks": check_char_limits(cleaned),
        "metadata_check": check_metadata(metadata_row or {}),
        "word_count": len(cleaned.split()),
        "char_count": len(cleaned)
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product_name", type=str)
    parser.add_argument("--body_content", type=str)
    parser.add_argument("--csv_path", type=str)
    parser.add_argument("--row_index", type=int, default=0)
    parser.add_argument("--validate_model_output", type=str)
    args = parser.parse_args()

    if args.validate_model_output:
        with open(args.validate_model_output) as f: scores = json.load(f)
        is_valid, errors = validate_model_output(scores)
        print(json.dumps({"valid": is_valid, "errors": errors}, indent=2))
        sys.exit(0 if is_valid else 1)

    if args.csv_path:
        row = load_csv_row(args.csv_path, args.row_index)
        product_name = row.get("product_name", f"Row {args.row_index}")
        body_content = row.get("body_content", "")
        metadata_row = row
    elif args.product_name and args.body_content:
        product_name, body_content, metadata_row = args.product_name, args.body_content, {}
    else:
        parser.print_help(); sys.exit(1)

    print(json.dumps(run_precheck(product_name, body_content, metadata_row), indent=2))

if __name__ == "__main__":
    main()

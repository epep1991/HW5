#!/usr/bin/env python3
"""
demo.py

Demonstrates the content-component-scorer skill end to end.

Workflow:
1. Load a product page from the test CSV
2. Run the deterministic pre-check (score_components.py logic)
3. Call the Anthropic API with the scoring rubric
4. Print the final readiness report

Usage:
    python demo.py                  # scores all 5 test pages
    python demo.py --row 0          # scores a specific row (0-4)
    python demo.py --row 2 --verbose
"""

import argparse
import csv
import json
import os
import re
import sys
import anthropic

# ── Paths ──────────────────────────────────────────────────────────────────────
SKILL_DIR = ".agents/skills/content-component-scorer"
CSV_PATH = f"{SKILL_DIR}/references/test_pages.csv"
RUBRIC_PATH = f"{SKILL_DIR}/references/scoring_rubric.md"

# ── Paid social character limits ───────────────────────────────────────────────
CHAR_LIMITS = {"headline": 27, "short_description": 125, "cta": 20}
REQUIRED_METADATA = ["seo_title", "seo_description", "image_url", "image_alt_text", "tags"]
VALID_COMPONENTS = {"headline", "short_description", "feature_list", "audience_statement", "cta"}
VALID_STATUSES = {"missing", "embedded", "dependent", "pass"}

STATUS_COLORS = {
    "pass": "\033[92m",       # green
    "missing": "\033[91m",    # red
    "embedded": "\033[93m",   # yellow
    "dependent": "\033[93m",  # yellow
}
RESET = "\033[0m"
BOLD = "\033[1m"


def strip_html(text):
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    for entity, char in {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&nbsp;": " "}.items():
        clean = clean.replace(entity, char)
    return re.sub(r"\s+", " ", clean).strip()


def check_char_limits(body_content):
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body_content) if s.strip()]
    results = {}
    for component, limit in CHAR_LIMITS.items():
        candidates = [s for s in sentences if len(s) <= limit]
        shortest = min(sentences, key=len) if sentences else ""
        results[component] = {
            "limit": limit,
            "any_candidate_fits": len(candidates) > 0,
            "note": (
                f"{len(candidates)} candidate(s) fit within {limit} chars"
                if candidates
                else f"No candidates fit within {limit} char limit (shortest: {len(shortest)} chars)"
            ),
        }
    return results


def check_metadata(row):
    fields = {f: bool(row.get(f, "").strip()) for f in REQUIRED_METADATA}
    return {"fields": fields, "metadata_complete": all(fields.values())}


def load_rubric():
    with open(RUBRIC_PATH) as f:
        content = f.read()
    # Extract just the system prompt section
    match = re.search(r"## System Prompt.*?```\n(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: return full rubric
    return content


def score_with_api(product_name, cleaned_content, system_prompt, verbose=False):
    """Call Anthropic API with tool use to score the five components."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    tools = [
        {
            "name": "score_component",
            "description": "Score a single content component for paid social readiness.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "component_name": {
                        "type": "string",
                        "enum": ["headline", "short_description", "feature_list", "audience_statement", "cta"],
                        "description": "The component being scored."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["missing", "embedded", "dependent", "pass"],
                        "description": "The modularization status of this component."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Required for non-pass statuses. Explain the specific structural issue."
                    }
                },
                "required": ["component_name", "status", "reason"]
            }
        }
    ]

    user_message = f"""Product name: {product_name}

Body content:
{cleaned_content}

Score all five components: headline, short_description, feature_list, audience_statement, cta.
Call score_component once for each component."""

    if verbose:
        print(f"\n  [API] Sending to claude-haiku-4-5-20251001 with tool use...")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        temperature=0.1,
        system=system_prompt,
        tools=tools,
        messages=[{"role": "user", "content": user_message}]
    )

    # Extract tool call results
    scores = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "score_component":
            scores.append(block.input)

    return scores


def build_report(product_name, model_scores, char_limits, metadata):
    components = {}
    for score in model_scores:
        name = score["component_name"]
        status = score["status"]
        entry = {
            "status": status,
            "reason": score.get("reason") if status != "pass" else None,
        }
        if name in char_limits:
            entry["char_limit_ok"] = char_limits[name]["any_candidate_fits"]
            entry["char_limit_note"] = char_limits[name]["note"]
        components[name] = entry

    passing = sum(1 for c in components.values() if c["status"] == "pass")
    pipeline_ready = passing == 5 and metadata["metadata_complete"]

    return {
        "product_name": product_name,
        "readiness_score": f"{passing}/5 components passing",
        "components": components,
        "metadata": metadata["fields"],
        "metadata_complete": metadata["metadata_complete"],
        "pipeline_ready": pipeline_ready,
    }


def print_report(report):
    ready_str = f"{BOLD}\033[92mYES{RESET}" if report["pipeline_ready"] else f"{BOLD}\033[91mNO{RESET}"
    print(f"\n{'='*60}")
    print(f"{BOLD}{report['product_name']}{RESET}")
    print(f"Readiness score: {BOLD}{report['readiness_score']}{RESET}")
    print(f"Pipeline ready:  {ready_str}")
    print(f"\nComponent breakdown:")

    for name, data in report["components"].items():
        status = data["status"]
        color = STATUS_COLORS.get(status, "")
        status_label = f"{color}{status.upper()}{RESET}"
        print(f"  {name:<22} {status_label}")
        if data.get("reason"):
            print(f"  {'':22} {data['reason']}")
        if "char_limit_note" in data:
            print(f"  {'':22} Char limit: {data['char_limit_note']}")

    print(f"\nMetadata completeness: {'COMPLETE' if report['metadata_complete'] else 'INCOMPLETE'}")
    missing_meta = [k for k, v in report["metadata"].items() if not v]
    if missing_meta:
        print(f"  Missing: {', '.join(missing_meta)}")
    print(f"{'='*60}")


def load_csv():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def score_row(row, system_prompt, verbose=False):
    product_name = row.get("product_name", "Unknown")
    body_content = row.get("body_content", "")

    print(f"\nScoring: {BOLD}{product_name}{RESET}...")

    cleaned = strip_html(body_content)
    char_limits = check_char_limits(cleaned)
    metadata = check_metadata(row)

    model_scores = score_with_api(product_name, cleaned, system_prompt, verbose)

    if not model_scores:
        print("  [ERROR] No scores returned from API.")
        return None

    report = build_report(product_name, model_scores, char_limits, metadata)
    print_report(report)
    return report


def main():
    parser = argparse.ArgumentParser(description="Demo: content-component-scorer skill")
    parser.add_argument("--row", type=int, default=None, help="Score a specific row index (0-4). Default: all rows.")
    parser.add_argument("--verbose", action="store_true", help="Show API call details.")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    print(f"\n{BOLD}Content Component Scorer — Demo{RESET}")
    print("Skill: .agents/skills/content-component-scorer")
    print("Script: runs deterministic pre-check, then calls Anthropic API with tool use")

    rows = load_csv()
    system_prompt = load_rubric()

    if args.row is not None:
        if args.row >= len(rows):
            print(f"Error: row {args.row} out of range. CSV has {len(rows)} rows.")
            sys.exit(1)
        score_row(rows[args.row], system_prompt, args.verbose)
    else:
        reports = []
        for row in rows:
            report = score_row(row, system_prompt, args.verbose)
            if report:
                reports.append(report)

        # Summary
        print(f"\n{BOLD}SUMMARY{RESET}")
        print(f"{'Product':<30} {'Score':<20} {'Ready'}")
        print("-" * 60)
        for r in reports:
            ready = "\033[92mYES\033[0m" if r["pipeline_ready"] else "\033[91mNO\033[0m"
            print(f"{r['product_name']:<30} {r['readiness_score']:<20} {ready}")


if __name__ == "__main__":
    main()

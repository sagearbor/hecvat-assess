#!/usr/bin/env python3
"""Compare two HECVAT assessments and show what changed.

Usage:
    python3 generate_delta.py <before_json> <after_json> <weights_yaml> [<output_md>]

Outputs:
    - Questions that improved (No -> Yes)
    - Questions that regressed (Yes -> No)
    - Questions newly assessed (blank -> Yes/No)
    - Score delta by category
"""

import json
import sys
import os
from collections import defaultdict


def load_weights(weights_path: str) -> dict:
    """Load category weights from scoring-weights.yaml."""
    try:
        import yaml
    except ImportError:
        # Fallback: parse the simple YAML structure manually
        weights = {}
        with open(weights_path) as f:
            current_cat = None
            for line in f:
                line = line.strip()
                if line.endswith(':') and not line.startswith('#') and not line.startswith('-'):
                    key = line[:-1].strip()
                    if key.isupper() and 2 <= len(key) <= 4:
                        current_cat = key
                elif current_cat and line.startswith('weight:'):
                    weights[current_cat] = int(line.split(':')[1].strip())
                    current_cat = None
                elif line == '' or line.startswith('#'):
                    if not (current_cat and line == ''):
                        current_cat = None
        return weights

    with open(weights_path) as f:
        data = yaml.safe_load(f)
    return {
        cat: info['weight']
        for cat, info in data.get('category_weights', {}).items()
    }


def generate_delta(before_path, after_path, weights_path, output_path=None):
    """Compare two assessments and generate a delta report."""
    with open(before_path) as f:
        before = json.load(f)
    with open(after_path) as f:
        after = json.load(f)

    before_answers = before.get("answers", {})
    after_answers = after.get("answers", {})

    weights = load_weights(weights_path)

    improvements = []  # No -> Yes
    regressions = []   # Yes -> No
    newly_assessed = []  # blank -> Yes/No
    unchanged_yes = 0
    unchanged_no = 0

    all_qids = sorted(set(list(before_answers.keys()) + list(after_answers.keys())))

    for qid in all_qids:
        b = before_answers.get(qid, {}).get("answer", "").strip()
        a = after_answers.get(qid, {}).get("answer", "").strip()

        if b == a:
            if a == "Yes":
                unchanged_yes += 1
            elif a == "No":
                unchanged_no += 1
            continue

        if b == "No" and a == "Yes":
            improvements.append(qid)
        elif b == "Yes" and a == "No":
            regressions.append(qid)
        elif b in ("", "N/A") and a in ("Yes", "No"):
            newly_assessed.append((qid, a))

    # Compute score deltas by category
    cat_deltas = defaultdict(lambda: {"before_yes": 0, "before_total": 0, "after_yes": 0, "after_total": 0})

    for qid in all_qids:
        cat = qid.rsplit("-", 1)[0] if "-" in qid else qid
        b = before_answers.get(qid, {}).get("answer", "").strip()
        a = after_answers.get(qid, {}).get("answer", "").strip()

        if b in ("Yes", "No"):
            cat_deltas[cat]["before_total"] += 1
            if b == "Yes":
                cat_deltas[cat]["before_yes"] += 1
        if a in ("Yes", "No"):
            cat_deltas[cat]["after_total"] += 1
            if a == "Yes":
                cat_deltas[cat]["after_yes"] += 1

    lines = []
    lines.append("# HECVAT Assessment Delta Report")
    lines.append("")
    lines.append(f"**Before**: {before.get('assessment_date', '?')} on `{before.get('branch', '?')}`")
    lines.append(f"**After**: {after.get('assessment_date', '?')} on `{after.get('branch', '?')}`")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Improvements (No -> Yes): **{len(improvements)}**")
    lines.append(f"- Regressions (Yes -> No): **{len(regressions)}**")
    lines.append(f"- Newly assessed: **{len(newly_assessed)}**")
    lines.append(f"- Unchanged Yes: {unchanged_yes}")
    lines.append(f"- Unchanged No: {unchanged_no}")
    lines.append("")

    if improvements:
        lines.append("## Improvements (No -> Yes)")
        lines.append("")
        lines.append("| Question | Category | Detail |")
        lines.append("|----------|----------|--------|")
        for qid in improvements:
            cat = qid.rsplit("-", 1)[0]
            detail = after_answers.get(qid, {}).get("additional_info", "")[:80]
            lines.append(f"| {qid} | {cat} | {detail} |")
        lines.append("")

    if regressions:
        lines.append("## Regressions (Yes -> No)")
        lines.append("")
        lines.append("| Question | Category | Detail |")
        lines.append("|----------|----------|--------|")
        for qid in regressions:
            cat = qid.rsplit("-", 1)[0]
            detail = after_answers.get(qid, {}).get("additional_info", "")[:80]
            lines.append(f"| {qid} | {cat} | {detail} |")
        lines.append("")

    if newly_assessed:
        lines.append("## Newly Assessed")
        lines.append("")
        lines.append("| Question | Answer | Category |")
        lines.append("|----------|--------|----------|")
        for qid, ans in newly_assessed:
            cat = qid.rsplit("-", 1)[0]
            lines.append(f"| {qid} | {ans} | {cat} |")
        lines.append("")

    # Category score deltas
    cats_with_change = {cat: d for cat, d in cat_deltas.items()
                        if d["before_total"] > 0 or d["after_total"] > 0}
    if cats_with_change:
        lines.append("## Category Score Deltas")
        lines.append("")
        lines.append("| Category | Before | After | Delta |")
        lines.append("|----------|--------|-------|-------|")
        for cat in sorted(cats_with_change.keys()):
            d = cats_with_change[cat]
            b_pct = round(d["before_yes"] / d["before_total"] * 100, 1) if d["before_total"] > 0 else 0
            a_pct = round(d["after_yes"] / d["after_total"] * 100, 1) if d["after_total"] > 0 else 0
            delta = round(a_pct - b_pct, 1)
            if delta != 0:
                lines.append(f"| {cat} | {d['before_yes']}/{d['before_total']} ({b_pct}%) | {d['after_yes']}/{d['after_total']} ({a_pct}%) | {delta:+.1f}% |")
        lines.append("")

    output = "\n".join(lines)
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(output)
        print(f"Delta report: {output_path}")
    else:
        print(output)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compare two HECVAT assessments")
    parser.add_argument("before_json", help="Earlier assessment JSON")
    parser.add_argument("after_json", help="Later assessment JSON")
    parser.add_argument("weights_yaml", help="Path to scoring-weights.yaml")
    parser.add_argument("output_md", nargs="?", help="Output path (default: stdout)")
    args = parser.parse_args()
    generate_delta(args.before_json, args.after_json, args.weights_yaml, args.output_md)

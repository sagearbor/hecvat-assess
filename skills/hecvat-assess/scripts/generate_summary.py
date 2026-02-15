#!/usr/bin/env python3
"""Generate a human-readable HECVAT assessment summary.

Usage:
    python3 generate_summary.py <assessment_json> <weights_yaml> [<output_md>]
    python3 generate_summary.py <assessment_json> <weights_yaml> [<output_md>] --compare <other_assessment_json>

If output_md is not provided, prints to stdout.
If --compare is provided, includes a delta table showing what changed between assessments.
"""

import json
import sys
import os
from collections import defaultdict
from datetime import datetime


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


def load_category_names(weights_path: str) -> dict:
    """Load category full names from scoring-weights.yaml."""
    try:
        import yaml
        with open(weights_path) as f:
            data = yaml.safe_load(f)
        return {
            cat: info['name']
            for cat, info in data.get('category_weights', {}).items()
        }
    except ImportError:
        # Fallback
        names = {}
        with open(weights_path) as f:
            current_cat = None
            for line in f:
                line = line.strip()
                if line.endswith(':') and not line.startswith('#') and not line.startswith('-'):
                    key = line[:-1].strip()
                    if key.isupper() and 2 <= len(key) <= 4:
                        current_cat = key
                elif current_cat and line.startswith('name:'):
                    name = line.split(':', 1)[1].strip().strip('"').strip("'")
                    names[current_cat] = name
                    current_cat = None
        return names


def analyze_assessment(assessment: dict) -> dict:
    """Analyze an assessment JSON and produce summary statistics."""
    answers = assessment.get("answers", {})

    # Per-category tallies
    categories = defaultdict(lambda: {"yes": 0, "no": 0, "na": 0, "blank": 0, "gaps": [], "fix_types": defaultdict(int)})

    for qid, ans in answers.items():
        # Extract category prefix (e.g., "AAAI" from "AAAI-01")
        cat = qid.rsplit("-", 1)[0] if "-" in qid else qid

        answer = ans.get("answer", "").strip()
        if answer == "Yes":
            categories[cat]["yes"] += 1
        elif answer == "No":
            categories[cat]["no"] += 1
            categories[cat]["gaps"].append(qid)
            fix_type = ans.get("fix_type", "unknown")
            categories[cat]["fix_types"][fix_type] += 1
        elif answer in ("N/A", "NA"):
            categories[cat]["na"] += 1
        else:
            categories[cat]["blank"] += 1

    return dict(categories)


def compute_scores(category_stats: dict, weights: dict) -> dict:
    """Compute raw and weighted scores."""
    total_yes = 0
    total_assessed = 0
    weighted_num = 0.0
    weighted_den = 0.0

    for cat, stats in category_stats.items():
        assessed = stats["yes"] + stats["no"]
        if assessed == 0:
            continue
        total_yes += stats["yes"]
        total_assessed += assessed

        w = weights.get(cat, 0)
        if w > 0:
            cat_pct = stats["yes"] / assessed
            weighted_num += cat_pct * w
            weighted_den += w

    raw_pct = (total_yes / total_assessed * 100) if total_assessed > 0 else 0
    weighted_score = (weighted_num / weighted_den * 100) if weighted_den > 0 else 0

    return {
        "raw_yes": total_yes,
        "raw_assessed": total_assessed,
        "raw_pct": round(raw_pct, 1),
        "weighted_score": round(weighted_score, 1),
        "weighted_num": round(weighted_num, 2),
        "weighted_den": round(weighted_den, 2),
    }


def compute_confidence_adjusted_score(assessment: dict, weights: dict) -> float:
    """Compute confidence-adjusted score using evidence_quality fields."""
    answers = assessment.get("answers", {})
    quality_map = {"Strong": 1.0, "Moderate": 0.75, "Weak": 0.5, "Inferred": 0.25}

    has_quality = False
    total_quality = 0.0
    assessed_count = 0

    for qid, ans in answers.items():
        answer = ans.get("answer", "").strip()
        if answer not in ("Yes", "No"):
            continue
        assessed_count += 1
        eq = ans.get("evidence_quality")
        if eq:
            has_quality = True
            if answer == "Yes":
                total_quality += quality_map.get(eq, 0.5)
        elif answer == "Yes":
            total_quality += 1.0  # Default to full credit if no evidence_quality

    if not has_quality or assessed_count == 0:
        return -1  # Sentinel: no evidence_quality data available

    return round(total_quality / assessed_count * 100, 1)


def generate_summary(
    assessment_path: str,
    weights_path: str,
    output_path: str = None,
    compare_path: str = None
):
    """Generate the full summary report."""
    with open(assessment_path) as f:
        assessment = json.load(f)

    weights = load_weights(weights_path)
    names = load_category_names(weights_path)
    stats = analyze_assessment(assessment)
    scores = compute_scores(stats, weights)

    # Confidence-adjusted score
    conf_score = compute_confidence_adjusted_score(assessment, weights)

    # Comparison data if provided
    compare_stats = None
    compare_scores = None
    if compare_path:
        with open(compare_path) as f:
            compare_assessment = json.load(f)
        compare_stats = analyze_assessment(compare_assessment)
        compare_scores = compute_scores(compare_stats, weights)

    lines = []
    lines.append("# HECVAT Assessment Summary")
    lines.append("")
    lines.append(f"**Repository**: {assessment.get('repository', 'unknown')}")
    lines.append(f"**Date**: {assessment.get('assessment_date', 'unknown')} | **HECVAT**: v{assessment.get('hecvat_version', '4.1.4')} | **Branch**: {assessment.get('branch', 'unknown')}")
    lines.append("")

    # Overall scores
    lines.append("## Overall Scores")
    lines.append("")
    lines.append("| Metric | Score |")
    lines.append("|--------|-------|")
    lines.append(f"| Raw compliance | {scores['raw_yes']}/{scores['raw_assessed']} ({scores['raw_pct']}%) |")
    lines.append(f"| Weighted score | {scores['weighted_score']} / 100 |")

    # Count org attestation
    org_count = sum(s["blank"] for s in stats.values())
    lines.append(f"| Org attestation (not code-assessable) | {org_count} questions |")

    if conf_score >= 0:
        lines.append(f"| Confidence-adjusted score | {conf_score} / 100 (conservative — weights by evidence strength) |")

    lines.append("")

    if compare_scores:
        lines.append("### Comparison")
        lines.append("")
        lines.append("| Metric | Before | After | Delta |")
        lines.append("|--------|--------|-------|-------|")
        lines.append(f"| Raw | {compare_scores['raw_yes']}/{compare_scores['raw_assessed']} ({compare_scores['raw_pct']}%) | {scores['raw_yes']}/{scores['raw_assessed']} ({scores['raw_pct']}%) | {scores['raw_pct'] - compare_scores['raw_pct']:+.1f}% |")
        lines.append(f"| Weighted | {compare_scores['weighted_score']} | {scores['weighted_score']} | {scores['weighted_score'] - compare_scores['weighted_score']:+.1f} |")
        lines.append("")

    # Category breakdown
    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| Category | Full Name | Wt | Yes | No | N/A | Score | Wtd | Top Gaps |")
    lines.append("|----------|-----------|-----|-----|-----|-----|-------|-----|----------|")

    # Sort by weight descending, then alphabetical
    sorted_cats = sorted(
        stats.items(),
        key=lambda x: (-weights.get(x[0], 0), x[0])
    )

    for cat, s in sorted_cats:
        w = weights.get(cat, 0)
        if w == 0:
            continue  # Skip org-attestation-only categories
        assessed = s["yes"] + s["no"]
        if assessed == 0:
            continue
        pct = round(s["yes"] / assessed * 100, 1) if assessed > 0 else 0
        wtd = round(pct / 100 * w, 2)
        full_name = names.get(cat, cat)
        # Show up to 3 gap IDs
        gap_preview = ", ".join(s["gaps"][:3])
        if len(s["gaps"]) > 3:
            gap_preview += f" (+{len(s['gaps']) - 3} more)"
        lines.append(f"| {cat} | {full_name} | {w} | {s['yes']} | {s['no']} | {s['na']} | {pct}% | {wtd} | {gap_preview} |")

    lines.append("")

    # Fix type breakdown
    all_fix_types = defaultdict(int)
    for s in stats.values():
        for ft, count in s["fix_types"].items():
            all_fix_types[ft] += count

    if all_fix_types:
        lines.append("## Gaps by Fix Type")
        lines.append("")
        lines.append("| Type | Count | Description |")
        lines.append("|------|-------|-------------|")
        type_descriptions = {
            "code": "Patchable code change (auto-generated in .patch file)",
            "config": "Configuration file change (auto-generated in .patch file)",
            "new_file": "New file to create (auto-generated in .patch file)",
            "documentation": "Documentation to add/update in the repo",
            "policy": "Organizational policy or process needed",
            "organizational": "Requires business/legal attestation",
            "unknown": "Not yet classified",
        }
        for ft in ["code", "config", "new_file", "documentation", "policy", "organizational", "unknown"]:
            if ft in all_fix_types:
                lines.append(f"| {ft} | {all_fix_types[ft]} | {type_descriptions.get(ft, '')} |")
        patchable = all_fix_types.get("code", 0) + all_fix_types.get("config", 0) + all_fix_types.get("new_file", 0)
        lines.append(f"| **Total patchable** | **{patchable}** | **Can be applied via `git apply`** |")
        lines.append("")

    # Top remediation priorities
    lines.append("## Top Remediation Priorities")
    lines.append("")
    lines.append("Ranked by gap impact: `weight * (gaps / assessed)` — higher means more impactful to fix.")
    lines.append("")

    priorities = []
    for cat, s in stats.items():
        w = weights.get(cat, 0)
        assessed = s["yes"] + s["no"]
        if w > 0 and s["no"] > 0 and assessed > 0:
            impact = round(w * (s["no"] / assessed), 2)
            full_name = names.get(cat, cat)
            priorities.append((impact, cat, full_name, s["no"], assessed))

    priorities.sort(reverse=True)
    for i, (impact, cat, full_name, gaps, assessed) in enumerate(priorities[:10], 1):
        lines.append(f"{i}. **{cat}** ({full_name}) — {gaps} gaps / {assessed} assessed, impact: {impact}")
    lines.append("")

    # Glossary
    lines.append("## Glossary")
    lines.append("")
    lines.append("| Term | Meaning |")
    lines.append("|------|---------|")
    lines.append("| HECVAT | Higher Education Community Vendor Assessment Toolkit (by EDUCAUSE) |")
    lines.append("| EDUCAUSE | Nonprofit association for higher education IT professionals |")
    lines.append("| Weighted score | Score adjusted by category importance (auth matters more than docs) |")
    lines.append("| Raw score | Simple ratio: compliant questions / total assessed questions |")
    lines.append("| N/A | Question does not apply to this product/service |")
    lines.append("| Org attestation | Question requires organizational (not code) answer |")
    lines.append("| Patchable | Gap that can be fixed by applying the auto-generated .patch file |")
    lines.append("| AAAI | Authentication, Authorization, and Accounting / Identity |")
    lines.append("| APPL | Application Security (input validation, XSS, injection, headers) |")
    lines.append("| DATA | Data Security (encryption, key management, backups, retention) |")
    lines.append("| VULN | Vulnerability Management (scanning, patching, dependency audits) |")
    lines.append("| CHNG | Change Management (CI/CD, code review, release process) |")
    lines.append("| ITAC | IT Accessibility (WCAG compliance, screen readers, keyboard nav) |")
    lines.append("| AISC | AI Security Controls (prompt injection, model poisoning defenses) |")
    lines.append("| AILM | AI Language Models (LLM-specific risks: hallucination, leakage) |")
    lines.append("| AIGN | AI Governance (risk assessment, responsible AI, oversight) |")
    lines.append("| DPAI | Data Privacy — AI (AI-specific data handling and consent) |")
    lines.append("| DCTR | Data Center (cloud/hosting infrastructure security) |")
    lines.append("| OPEM | Operational Management (monitoring, alerting, incident response) |")
    lines.append("| DRPV | Disaster Recovery / Privacy (backups, DPIA, privacy notices) |")
    lines.append("| PDAT | Privacy Data (data residency, demographics, cross-border) |")
    lines.append("| WAF | Web Application Firewall — filters malicious HTTP traffic |")
    lines.append("| RBAC | Role-Based Access Control — permissions tied to user roles |")
    lines.append("| SSO | Single Sign-On — one login for multiple systems |")
    lines.append("| OIDC | OpenID Connect — modern authentication protocol built on OAuth2 |")
    lines.append("| SAML | Security Assertion Markup Language — enterprise SSO protocol |")
    lines.append("| MFA | Multi-Factor Authentication — requires 2+ verification methods |")
    lines.append("| CSP | Content Security Policy — browser header preventing XSS attacks |")
    lines.append("| HSTS | HTTP Strict Transport Security — forces HTTPS connections |")
    lines.append("| SAST | Static Application Security Testing — code scanning for vulns |")
    lines.append("| DAST | Dynamic Application Security Testing — runtime vulnerability scanning |")
    lines.append("| WCAG | Web Content Accessibility Guidelines (target: 2.1 AA) |")
    lines.append("| VPAT | Voluntary Product Accessibility Template — accessibility report |")
    lines.append("| DPIA | Data Privacy Impact Assessment — formal privacy risk analysis |")
    lines.append("| NIST AI RMF | NIST AI Risk Management Framework — AI governance standard |")
    lines.append("| SOC 2 | Service Organization Control 2 — security audit certification |")
    lines.append("")

    lines.append("---")
    lines.append(f"*Generated by HECVAT Assessment Skill on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    output = "\n".join(lines)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(output)
        print(f"Summary written to: {output_path}")
    else:
        print(output)

    # Also print score summary to stdout regardless
    print(f"\nScore: {scores['raw_yes']}/{scores['raw_assessed']} ({scores['raw_pct']}%) raw, {scores['weighted_score']}/100 weighted")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate HECVAT assessment summary")
    parser.add_argument("assessment_json", help="Path to assessment-current.json")
    parser.add_argument("weights_yaml", help="Path to scoring-weights.yaml")
    parser.add_argument("output_md", nargs="?", help="Output markdown path (default: stdout)")
    parser.add_argument("--compare", help="Path to second assessment JSON for delta comparison")
    args = parser.parse_args()

    generate_summary(args.assessment_json, args.weights_yaml, args.output_md, args.compare)

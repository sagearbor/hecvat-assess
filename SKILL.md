---
name: hecvat-assess
description: "Evaluate a GitHub or Azure DevOps repository against the HECVAT (Higher Education Community Vendor Assessment Toolkit) v4.1.4 from EDUCAUSE. Scans source code, config files, CI/CD pipelines, IaC, dependencies, and documentation to auto-assess ~40-50% of HECVAT questions, generates compliance reports as filled xlsx files, and produces patch files for remediable gaps. Use when: (1) user invokes /hecvat-assess, (2) user asks to 'evaluate this repo for HECVAT compliance', (3) user needs to 'fill out a HECVAT', (4) user mentions HECVAT, EDUCAUSE vendor assessment, or higher education security assessment, (5) user asks about compliance readiness for higher ed procurement."
---

# HECVAT Repository Assessment

Assess a code repository against the EDUCAUSE HECVAT v4.1.4 (332 questions across 7 categories). Produce two filled HECVAT xlsx reports (current state + projected post-patch) and a unified diff patch file for remediable gaps.

## Workflow

1. **Bootstrap** — Parse xlsx into JSON cache
2. **Version check** — Verify HECVAT version is current
3. **Repo scan** — Deep scan codebase by HECVAT category
4. **Assessment mapping** — Map findings to questions with evidence
5. **Patch generation** — Generate fixes for remediable gaps
6. **Report generation** — Produce current + projected xlsx reports

All outputs go to `./hecvat-output/` in the repo root.

## Step 1: Bootstrap

Check if `hecvat-questions.json` exists in the skill directory alongside the xlsx.

```python
# Skill directory (where SKILL.md lives)
SKILL_DIR = "<skill_directory>"
XLSX = SKILL_DIR + "/HECVAT414.xlsx"
CACHE = SKILL_DIR + "/hecvat-questions.json"
```

If the cache is missing or its `source_file` field doesn't match the xlsx filename:

```bash
python3 SKILL_DIR/scripts/parse_hecvat.py SKILL_DIR/HECVAT414.xlsx SKILL_DIR/hecvat-questions.json
```

Then read the JSON cache for all subsequent steps. The JSON contains every question with: `id`, `question`, `category`, `compliant_response`, `default_importance`, `repo_assessable`, and guidance fields.

## Step 2: Version Check

Use WebFetch to scrape `https://www.educause.edu/higher-education-community-vendor-assessment-toolkit` and look for a version number newer than the current xlsx filename (e.g., "4.1.4").

- **If newer version found**: Alert the user. Ask if they want to auto-download. If yes, download via `curl`, replace the xlsx, re-run `parse_hecvat.py`, and continue with the new version.
- **If current or check fails**: Continue with the existing version.

## Step 3: Repo Scan

Perform a deep scan of the repository. Read [references/scan-patterns.md](references/scan-patterns.md) for the complete set of Glob patterns and Grep patterns organized by HECVAT category.

**Pass 1 — File discovery**: Use Glob to build a file inventory (configs, source, CI/CD, IaC, docs, dependencies, frontend).

**Pass 2 — Content analysis**: Use Grep across discovered files for category-specific patterns (auth, encryption, CSRF, accessibility, AI governance, etc.).

Collect all findings as structured evidence:
```json
{
  "question_id": "AAAI-01",
  "files": ["src/auth/middleware.ts:42", "config/auth.yml:8"],
  "finding": "OAuth2 with PKCE configured via passport.js",
  "assessment": "Yes",
  "confidence": "High"
}
```

## Step 4: Assessment Mapping

Read [references/scoring-rubric.md](references/scoring-rubric.md) for the scoring rubric, confidence levels, and evidence quality requirements.

For each question in the JSON cache:

**If `repo_assessable: true`**: Map scan findings to an answer (Yes/No/N/A) with evidence citations (file paths, line numbers, config values). Include a confidence level (High/Medium/Low).

**If `repo_assessable: false`**: Mark as `"Requires organizational attestation"` in the Additional Information column. Do not guess at organizational practices.

Build the assessment JSON:
```json
{
  "answers": {
    "AAAI-01": {
      "answer": "Yes",
      "additional_info": "[Confidence: High] OAuth2 with PKCE flow implemented via passport.js. Session timeout configured at 30 minutes.",
      "evidence": "src/auth/middleware.ts:42, config/auth.yml:8"
    },
    "COMP-01": {
      "answer": "",
      "additional_info": "Requires organizational attestation — cannot be determined from code.",
      "evidence": ""
    }
  }
}
```

Write this to `./hecvat-output/assessment-current.json`.

## Step 5: Patch Generation

For questions where `answer: "No"` and a code/config fix exists, generate a unified diff patch. Group patches by file.

Consult the "Patch Generation Patterns" section of [references/scan-patterns.md](references/scan-patterns.md) for common remediation patterns (security headers, dependency scanning, input validation, encryption config, accessibility attributes).

Write the combined patch to `./hecvat-output/hecvat-remediation.patch`.

Then create `assessment-projected.json` — a copy of the current assessment with patched questions flipped from "No" to "Yes" and updated evidence noting the patch.

## Step 6: Report Generation

Use the report generator script to produce filled xlsx files:

```bash
# Current state report
python3 SKILL_DIR/scripts/generate_report.py \
  SKILL_DIR/HECVAT414.xlsx \
  ./hecvat-output/assessment-current.json \
  ./hecvat-output/hecvat-report-current.xlsx

# Projected post-patch report
python3 SKILL_DIR/scripts/generate_report.py \
  SKILL_DIR/HECVAT414.xlsx \
  ./hecvat-output/assessment-projected.json \
  ./hecvat-output/hecvat-report-projected.xlsx
```

## Output Summary

After completion, print a summary:

```
HECVAT Assessment Complete
==========================
Version: 4.1.4
Questions assessed from code: X / 332
Questions requiring org attestation: Y / 332
Compliant (current): Z / X assessed
Remediation patches: N questions

Deliverables in ./hecvat-output/:
  hecvat-report-current.xlsx     — Current state HECVAT report
  hecvat-report-projected.xlsx   — Projected report (post-patch)
  hecvat-remediation.patch       — Unified diff for remediable gaps
  assessment-current.json        — Machine-readable current assessment
  assessment-projected.json      — Machine-readable projected assessment
```

## Resources

### scripts/
- **parse_hecvat.py** — Parse HECVAT xlsx into `hecvat-questions.json`. Extracts all 332 questions with metadata, repo-assessability flags, and guidance.
- **generate_report.py** — Fill the HECVAT xlsx template with assessment answers and evidence. Writes to Answer (col C) and Additional Information (col D) across all response sheets.

### references/
- **[scoring-rubric.md](references/scoring-rubric.md)** — Scoring rubric with answer values, confidence levels, repo-assessability decision tree, evidence quality requirements, and category-specific scoring notes. Read before assessment mapping (Step 4).
- **[scan-patterns.md](references/scan-patterns.md)** — Complete Glob and Grep patterns for every HECVAT category, organized by security domain. Includes patch generation patterns. Read before repo scanning (Step 3).

### Assets
- **HECVAT414.xlsx** — The EDUCAUSE HECVAT v4.1.4 template (15 sheets, 332 questions). Used as the source for JSON parsing and as the template for report generation.

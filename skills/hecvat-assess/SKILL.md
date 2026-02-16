---
name: hecvat-assess
description: "Evaluate a GitHub or Azure DevOps repository against the HECVAT (Higher Education Community Vendor Assessment Toolkit) v4.1.4 from EDUCAUSE. Scans source code, config files, CI/CD pipelines, IaC, dependencies, and documentation to auto-assess ~40-50% of HECVAT questions, generates compliance reports as filled xlsx files, and produces patch files for remediable gaps. Use when: (1) user invokes /hecvat-assess, (2) user asks to 'evaluate this repo for HECVAT compliance', (3) user needs to 'fill out a HECVAT', (4) user mentions HECVAT, EDUCAUSE vendor assessment, or higher education security assessment, (5) user asks about compliance readiness for higher ed procurement."
---

# HECVAT Repository Assessment

Assess a code repository against the EDUCAUSE HECVAT v4.1.4 (332 questions across 7 categories). Produce three filled HECVAT xlsx reports (current state, post-patch, and post-checklist), a unified diff patch file for remediable gaps, and a developer improvement checklist for AI-assisted remediation.

## Workflow

```
  /hecvat-assess
       |
       v
 +--------------+
 |0.Archive Prev|
 | if exists,   |
 | mv to archive|
 +--------------+
       |
       v
 +-----------+     +--------------+     +------------+
 | 1.Bootstrap|---->|2.Version Chk |---->| 3.Repo Scan|
 | xlsx->JSON |     | EDUCAUSE.edu |     | Glob + Grep|
 | 332 questions    | newer? alert |     | by category|
 +-----------+     +--------------+     +------------+
                                              |
       +--------------------------------------+
       |
       v
 +----------------+     +-------------------+     +------------------+
 |4.Assessment Map|---->|5.Patch Generation |---->|6.Dev Checklist   |
 | findings->      |     | edit-diff-revert  |     | deduped tasks    |
 | Yes/No/N/A     |     | real git patches  |     | parallel streams |
 | + fix_type     |     | + manual items    |     | + resolves_count |
 | + evidence_q   |     | + post-patch JSON |     |                  |
 |                |     | + post-checklist  |     |                  |
 +----------------+     +-------------------+     +------------------+
                                                        |
       +------------------------------------------------+
       |
       v
 +-------------------+
 |7.Reports & Summary|
 | fill xlsx (x3)    |
 | summary markdown  |
 | 3-tier scoring    |
 +-------------------+
       |
       v
 ./docs/hecvat/
  |- hecvat-report-current.xlsx          — Filled HECVAT xlsx (current state)
  |- hecvat-report-post-patch.xlsx       — Filled HECVAT xlsx (after git apply only)
  |- hecvat-report-post-checklist.xlsx   — Filled HECVAT xlsx (after all checklist tasks)
  |- hecvat-remediation.patch            — git apply-able patch for code/config fixes
  |- hecvat-remediation-manual.md        — Non-patchable gaps requiring human action
  |- hecvat-improvement-developer-checklist.yaml  — Developer/AI agent task list
  |- hecvat-summary.md                   — Human-readable summary with 3-tier table + glossary
  |- hecvat-delta-from-previous.md       — Delta from last run (if archived run exists)
  |- assessment-current.json             — Machine-readable current assessment
  |- assessment-post-patch.json          — Machine-readable post-patch assessment
  |- assessment-post-checklist.json      — Machine-readable post-checklist assessment
  |- archive/                            — Previous runs (auto-archived on re-run)
      |- YYYYMMDD-HHMM/                 — Timestamped snapshot of prior results
```

0. **Archive previous** — If re-running, archive prior results to `archive/YYYYMMDD-HHMM/`
1. **Bootstrap** — Parse xlsx into JSON cache
2. **Version check** — Verify HECVAT version is current
3. **Repo scan** — Deep scan codebase by HECVAT category
4. **Assessment mapping** — Map findings to questions with evidence + fix classification
5. **Patch generation** — Generate real `git apply`-able patches via edit-diff-revert cycle, plus 3-tier projected assessments
6. **Developer checklist** — Generate deduplicated improvement checklist for AI agents
7. **Reports & summary** — Produce 3 xlsx reports, markdown summary with 3-tier scoring, and delta from previous run

All outputs go to `./docs/hecvat/` in the repo being assessed. If a `./docs/` directory already exists, write directly into `./docs/hecvat/`. If it does not exist, create `./docs/` first, then `./docs/hecvat/`.

## Partial Re-run (--from-step)

The skill accepts an optional `--from-step` argument to skip earlier steps when their outputs already exist. Steps are identified by **name** (stable across versions) or by number (for convenience).

**Usage:** `/hecvat-assess --from-step patch`

### Step names

| Name | Number | What it does |
|------|--------|-------------|
| `archive` | 0 | Archive previous results |
| `bootstrap` | 1 | Parse xlsx → JSON cache |
| `version` | 2 | Check EDUCAUSE for newer HECVAT |
| `scan` | 3 | Glob + Grep repo scan |
| `assess` | 4 | Map findings → Yes/No/N/A |
| `patch` | 5 | Generate patches + projected assessments |
| `checklist` | 6 | Generate developer checklist |
| `reports` | 7 | Generate xlsx reports + summary |

Both forms are equivalent: `--from-step patch` and `--from-step 5`.

### Entry points

| Start from | Requires | Skips | Use case |
|------------|----------|-------|----------|
| (default) | nothing | nothing | Full assessment from scratch |
| `patch` | `assessment-current.json` | archive → assess | Re-generate patches, projections, checklist, and reports after plugin update |
| `reports` | `assessment-current.json` + `assessment-post-patch.json` + `assessment-post-checklist.json` | archive → checklist | Re-generate xlsx reports and summary only |

### Validation

Before skipping steps, verify that all required files exist in `./docs/hecvat/`. If any required file is missing, warn the user and fall back to the earliest step that can produce it. For example, if `--from-step reports` is requested but `assessment-post-patch.json` does not exist, fall back to `patch` (which generates the post-patch and post-checklist JSONs).

```
Required files by entry point:
  --from-step patch:   ./docs/hecvat/assessment-current.json
  --from-step reports: ./docs/hecvat/assessment-current.json
                       ./docs/hecvat/assessment-post-patch.json
                       ./docs/hecvat/assessment-post-checklist.json
```

### Common scenario

`--from-step patch` is the most common re-run entry point. Use it after updating the plugin to re-generate patches, projected assessments (3-tier scoring), the developer checklist, and xlsx reports from an existing `assessment-current.json` — without re-scanning the entire repo.

## Help (--help)

If the user passes `--help`, `-h`, or `help` as an argument, print the following help text and do not proceed with the assessment:

```
HECVAT Assessment Skill v3.1.0

Usage:
  /hecvat-assess                       Full assessment from scratch
  /hecvat-assess --from-step patch     Re-run from patch generation (skips scan)
  /hecvat-assess --from-step reports   Re-run report generation only
  /hecvat-assess --help                Show this help

Options:
  --from-step <name|number>   Start from a specific step (see below)
  --help, -h                  Show this help message

Steps:
  archive (0)    Archive previous results
  bootstrap (1)  Parse HECVAT xlsx template
  version (2)    Check for newer HECVAT version
  scan (3)       Scan repo (Glob + Grep)
  assess (4)     Map findings to Yes/No/N/A
  patch (5)      Generate patches + projected assessments
  checklist (6)  Generate developer checklist
  reports (7)    Generate xlsx reports + summary

Common workflows:
  First run          /hecvat-assess
  After plugin update /hecvat-assess --from-step patch
  Regenerate reports  /hecvat-assess --from-step reports

Pre-filled template (optional):
  Org-wide:  ~/.config/hecvat/hecvat-prefilled.xlsx
  Per-repo:  ./docs/hecvat/hecvat-prefilled.xlsx
  Fill in org answers once, reuse across all repo assessments.

Outputs (written to ./docs/hecvat/):
  3 filled HECVAT spreadsheets (current, post-patch, post-checklist)
  Remediation patch file (git apply compatible)
  Developer improvement checklist (YAML)
  Human-readable summary with 3-tier scoring
```

## Step 0: Archive Previous Results

Before writing any new outputs, check if a previous assessment exists. If so, archive it so re-runs don't destroy historical data.

```bash
if [ -f "./docs/hecvat/assessment-current.json" ]; then
    # Timestamp from the existing assessment, fallback to file modification time
    ARCHIVE_TS=$(python3 -c "
import json, os
from datetime import datetime
try:
    with open('./docs/hecvat/assessment-current.json') as f:
        d = json.load(f)
    ts = d.get('assessment_date', '')
    if ts:
        # Parse ISO date and format as YYYYMMDD-HHMM
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        print(dt.strftime('%Y%m%d-%H%M'))
    else:
        raise ValueError()
except:
    # Fallback: use file modification time
    mt = os.path.getmtime('./docs/hecvat/assessment-current.json')
    print(datetime.fromtimestamp(mt).strftime('%Y%m%d-%H%M'))
")

    ARCHIVE_DIR="./docs/hecvat/archive/${ARCHIVE_TS}"
    mkdir -p "$ARCHIVE_DIR"

    # Move all assessment outputs (not the archive dir itself, not prefilled template)
    for f in ./docs/hecvat/assessment-*.json \
             ./docs/hecvat/hecvat-report-*.xlsx \
             ./docs/hecvat/hecvat-remediation.patch \
             ./docs/hecvat/hecvat-remediation-manual.md \
             ./docs/hecvat/hecvat-improvement-developer-checklist.yaml \
             ./docs/hecvat/hecvat-summary*.md \
             ./docs/hecvat/hecvat-delta-from-previous.md; do
        [ -f "$f" ] && mv "$f" "$ARCHIVE_DIR/"
    done

    echo "Archived previous assessment to: $ARCHIVE_DIR"
fi
```

After archiving, the agent should inform the user:
- That previous results were archived and where
- That `generate_delta.py` can compare the archived assessment with the new one after the run completes

The archive directory structure:
```
docs/hecvat/
  |- assessment-current.json          <- always the latest run
  |- hecvat-report-current.xlsx
  |- ...
  |- archive/
      |- 20260215-1505/               <- first run, archived automatically
      |   |- assessment-current.json
      |   |- hecvat-report-current.xlsx
      |   |- ...
      |- 20260301-0930/               <- second run, archived on third run
          |- ...
```

## Step 1: Bootstrap

### Template resolution

The skill supports organization-specific pre-filled HECVAT templates. This lets orgs fill in their standard organizational answers once (company name, contacts, insurance, certifications, etc.) and reuse that template across all repo assessments — so the 52% of questions that require org attestation aren't blank.

**Template priority order** (first match wins):

1. **Repo-level override**: `./docs/hecvat/hecvat-prefilled.xlsx` in the repo being assessed
2. **Org-level default**: `~/.config/hecvat/hecvat-prefilled.xlsx` (shared across all repos)
3. **Blank template**: `SKILL_DIR/HECVAT414.xlsx` (ships with the skill)

```python
import os

SKILL_DIR = "<skill_directory>"

# Check for org/repo pre-filled template (survives skill updates)
REPO_TEMPLATE = "./docs/hecvat/hecvat-prefilled.xlsx"
ORG_TEMPLATE = os.path.expanduser("~/.config/hecvat/hecvat-prefilled.xlsx")
DEFAULT_TEMPLATE = SKILL_DIR + "/HECVAT414.xlsx"

if os.path.exists(REPO_TEMPLATE):
    XLSX = REPO_TEMPLATE
    print(f"Using repo-level pre-filled template: {REPO_TEMPLATE}")
elif os.path.exists(ORG_TEMPLATE):
    XLSX = ORG_TEMPLATE
    print(f"Using org-level pre-filled template: {ORG_TEMPLATE}")
else:
    XLSX = DEFAULT_TEMPLATE
    print("Using blank HECVAT template (no pre-filled template found)")

CACHE = SKILL_DIR + "/hecvat-questions.json"
```

**How orgs set up a pre-filled template:**

1. Copy the blank template: `cp SKILL_DIR/HECVAT414.xlsx ~/.config/hecvat/hecvat-prefilled.xlsx`
2. Open the copy in Excel and fill in organizational answers (company info, contacts, certifications, insurance, etc.)
3. Save. All future assessments across any repo will use this as the base template.

For repo-specific overrides (e.g., a product that has different answers than the org default), place a copy at `./docs/hecvat/hecvat-prefilled.xlsx` in that repo instead.

Neither location is inside the skill directory, so `hecvat-prefilled.xlsx` is never overwritten when the skill is updated.

### JSON cache

Check if `hecvat-questions.json` exists in the skill directory:

If the cache is missing or its `source_file` field doesn't match the current xlsx filename:

```bash
python3 SKILL_DIR/scripts/parse_hecvat.py SKILL_DIR/HECVAT414.xlsx SKILL_DIR/hecvat-questions.json
```

Note: The JSON cache is always parsed from the blank template (not the pre-filled one) so question metadata stays consistent. The pre-filled template is only used during report generation (Step 7) as the base workbook.

Then read the JSON cache for all subsequent steps. The JSON contains every question with: `id`, `question`, `category`, `compliant_response`, `default_importance`, `repo_assessable`, and guidance fields.

## Step 2: Version Check

Use WebFetch to scrape `https://www.educause.edu/higher-education-community-vendor-assessment-toolkit` and look for a version number newer than the current xlsx filename (e.g., "4.1.4").

- **If newer version found**: Alert the user. Ask if they want to auto-download. If yes, download via `curl`, replace the xlsx, re-run `parse_hecvat.py`, and continue with the new version.
- **If current or check fails**: Continue with the existing version.

## Step 3: Repo Scan

Perform a deep scan of the repository. Read [references/scan-patterns.yaml](references/scan-patterns.yaml) for the complete set of Glob patterns and Grep patterns organized by HECVAT category.

**Pass 1 — File discovery**: Use Glob to build a file inventory (configs, source, CI/CD, IaC, docs, dependencies, frontend).

**Pass 2 — Content analysis**: Use Grep across discovered files for category-specific patterns (auth, encryption, CSRF, accessibility, AI governance, etc.).

**Language detection**: Before Pass 2, detect the repo's primary language(s) and framework(s) using the indicators in [references/language-patterns.yaml](references/language-patterns.yaml). Use language-specific patterns to supplement generic patterns for higher detection accuracy. If the language cannot be determined, fall back to generic patterns only and flag findings as lower confidence.

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

Read [references/context-analysis.yaml](references/context-analysis.yaml) for context-aware analysis rules. For each grep match, read 10-20 lines of surrounding code and apply the false-positive/true-positive rules before assigning a confidence level.

For each question in the JSON cache:

**If `repo_assessable: true`**: Map scan findings to an answer (Yes/No/N/A) with evidence citations (file paths, line numbers, config values). Include a confidence level (High/Medium/Low).

**If `repo_assessable: false`**: Mark as `"Requires organizational attestation"` in the Additional Information column. Do not guess at organizational practices.

For each "No" answer, also determine:

1. **fix_type**: What kind of remediation is needed (code/config/new_file/documentation/policy/organizational)
2. **fix_complexity**: How much effort the fix requires (small/medium/large)
3. **evidence_quality**: How strong the evidence is for the assessment (Strong/Moderate/Weak/Inferred)

For "Yes" answers, include `evidence_quality` but omit `fix_type` and `fix_complexity`.
For "N/A" and org-attestation answers, omit all three fields.

See [references/scoring-rubric.md](references/scoring-rubric.md) for evidence quality levels and fix-type classification rules.

Build the assessment JSON:
```json
{
  "answers": {
    "AAAI-01": {
      "answer": "No",
      "additional_info": "[Confidence: High] No SSO integration found. Only basic username/password auth.",
      "evidence": "app/main.py:2863, requirements.txt:1-53",
      "fix_type": "code",
      "fix_complexity": "large",
      "evidence_quality": "Strong"
    },
    "APPL-05": {
      "answer": "Yes",
      "additional_info": "[Confidence: High] CSP headers configured via helmet middleware.",
      "evidence": "src/middleware/security.ts:12",
      "evidence_quality": "Strong"
    },
    "COMP-01": {
      "answer": "",
      "additional_info": "Requires organizational attestation — cannot be determined from code.",
      "evidence": ""
    }
  }
}
```

Write this to `./docs/hecvat/assessment-current.json`.

## Step 5: Patch Generation

Generate a real, `git apply`-able unified diff patch for code-fixable HECVAT gaps. Not all gaps can be patched — many require organizational policy, documentation, or manual processes. This step produces patches ONLY for gaps where a concrete code/config change exists.

Consult the "patch_generation" section of [references/scan-patterns.yaml](references/scan-patterns.yaml) for common remediation patterns and fix-type classifications.

### 5a. Classify each gap

Before generating patches, classify each "No" answer from Step 4 by `fix_type`:

| fix_type | Description | Goes in .patch? | Example |
|----------|-------------|-----------------|---------|
| `code` | Change to existing source code | Yes | Add security middleware, input validation |
| `config` | Change to existing config file | Yes | CI pipeline step, Dockerfile directive |
| `new_file` | Create a new file | Yes | `.github/dependabot.yml`, policy doc |
| `documentation` | Add/update documentation in repo | Maybe (if simple) | Add SECURITY.md, update README |
| `policy` | Requires organizational process/policy | No | Change management policy, training |
| `organizational` | Requires org attestation, legal, business | No | Insurance, certifications, staffing |

Add the `fix_type` field to each answer in `assessment-current.json` (see Step 4 schema).

### 5b. Safety checks

Before making any edits, verify the working tree is clean:

```bash
# Verify clean state
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree is dirty. Stashing changes first."
    git stash push -m "hecvat-assess: pre-patch stash"
fi
```

### 5c. Generate patches via edit-diff-revert cycle

For each gap where `fix_type` is `code`, `config`, or `new_file`:

1. **Read the target file** (the agent should already have context from Step 3, but re-read if needed)
2. **Make the minimal fix** using the Edit tool (for existing files) or Write tool (for new files)
3. **Capture the diff**: `git diff -- path/to/file >> docs/hecvat/hecvat-remediation.patch`
   - For new files, use: `git diff --no-index /dev/null path/to/file >> docs/hecvat/hecvat-remediation.patch` OR stage with `git add path/to/file && git diff --cached -- path/to/file >> docs/hecvat/hecvat-remediation.patch`
4. **Immediately revert**: `git checkout -- path/to/file` (for modified files) or `rm path/to/file && git reset HEAD path/to/file` (for new files)
5. **Verify clean state**: `git status --porcelain` should show no changes

Repeat for each patchable gap. Process files in alphabetical order so the patch is deterministic.

### 5d. Validate the patch

After generating all hunks, validate the complete patch:

```bash
git apply --check docs/hecvat/hecvat-remediation.patch
```

If validation fails:
1. Identify which hunk(s) failed from the error output
2. Re-read the affected file(s)
3. Re-generate just the failing hunk(s) with corrected context
4. Re-validate until `--check` passes

### 5e. Add patch header

Prepend a header comment block to the patch file:

```
# HECVAT Remediation Patch
# Generated: <ISO date>
# Repository: <repo name>
# Branch: <branch name>
# HECVAT Version: 4.1.4
#
# This patch addresses <N> code/config gaps identified by HECVAT assessment.
# Remaining <M> gaps require manual action (see hecvat-remediation-manual.md).
#
# To apply:  git apply docs/hecvat/hecvat-remediation.patch
# To review: git apply --stat docs/hecvat/hecvat-remediation.patch
# To test:   git apply --check docs/hecvat/hecvat-remediation.patch
#
# REVIEW BEFORE APPLYING — patches are auto-generated and may need adjustment.
# After applying, run your test suite to verify nothing broke.
```

### 5f. Generate manual remediation file

For gaps where `fix_type` is `documentation`, `policy`, or `organizational`, generate a separate human-readable file at `docs/hecvat/hecvat-remediation-manual.md`:

```markdown
# HECVAT Manual Remediation Items

These items cannot be auto-patched and require human action.

## Documentation Tasks (can be done by developers)

| ID | Question | What to Do | Affected Files |
|----|----------|------------|----------------|
| AIGN-01 | AI risk assessment | Create formal AI risk assessment doc following NIST AI RMF | README.md, new doc |

## Policy Tasks (require organizational process)

| ID | Question | What to Do | Owner |
|----|----------|------------|-------|
| CHNG-01 | Change notification policy | Define major change criteria, stakeholder list, timelines | Project Manager |

## Organizational Attestation (require business/legal)

| ID | Question | What to Do | Owner |
|----|----------|------------|-------|
| COMP-01 | Company information | Fill in organizational details in HECVAT template | Management |
```

### 5g. Build projected assessments (3-tier model)

Generate **two** projected assessments to give an honest picture of remediation effort:

| Tier | File | What gets flipped | Represents |
|------|------|-------------------|------------|
| Current | `assessment-current.json` | — | Code as-is |
| Post-patch | `assessment-post-patch.json` | Only `fix_type` in (`code`, `config`, `new_file`) that are IN the `.patch` file | Running `git apply` — minutes of effort |
| Post-checklist | `assessment-post-checklist.json` | All of post-patch PLUS `documentation` gaps | Completing the full developer checklist — hours/days of effort |

**assessment-post-patch.json** — Copy `assessment-current.json` and:
- For each gap with `fix_type` in (`code`, `config`, `new_file`): flip answer from "No" to "Yes", update `additional_info` with "[Post-patch] Fixed via hecvat-remediation.patch"
- Leave ALL other gaps (documentation, policy, organizational) as "No"
- Add a top-level `flipped_questions` array listing all changed question IDs
- Add a top-level `projected_methodology` field: "Only questions fixable by git apply of the auto-generated patch"

**assessment-post-checklist.json** — Copy `assessment-post-patch.json` and:
- For `documentation` gaps: flip to "Yes" with "[Post-checklist] Manual documentation task from developer checklist"
- Leave `policy` and `organizational` gaps as "No"
- Update `flipped_questions` to include documentation flips
- Update `projected_methodology` field: "All questions resolvable by completing the developer checklist (patch + documentation tasks). Policy and organizational gaps remain."

### 5h. Restore working tree

If changes were stashed in 5b, restore them:

```bash
git stash pop 2>/dev/null || true
```

## Step 6: Developer Checklist

Generate `./docs/hecvat/hecvat-improvement-developer-checklist.yaml` — a structured developer checklist that AI agents (or human developers) can use to systematically improve the repo's HECVAT compliance score.

Build the checklist from all questions where `answer: "No"` and remediation is possible. Structure it as follows:

```yaml
# hecvat-improvement-developer-checklist.yaml
# Generated by HECVAT Assessment Skill
# This checklist is designed for AI agents and developers to systematically
# improve HECVAT compliance. Tasks are grouped into parallel work streams
# where possible. Each task includes acceptance criteria and test expectations.

metadata:
  generated_at: "<ISO 8601 timestamp>"
  hecvat_version: "4.1.4"
  repo: "<repo name>"
  current_score: "<compliant> / <assessed>"
  post_patch_score: "<post-patch compliant> / <assessed>"
  post_checklist_score: "<post-checklist compliant> / <assessed>"
  total_tasks: <N>

# Work streams that can be executed in parallel.
# Tasks within a stream are sequential (ordered by dependency).
# Streams themselves have no cross-dependencies unless noted.
work_streams:

  - name: "CI/CD & Vulnerability Scanning"
    description: "Add automated security scanning and dependency management to the CI/CD pipeline."
    can_parallel_with: ["Security Headers & Middleware", "Documentation & Policy"]
    tasks:
      - id: "VULN-01-fix"
        title: "Add dependency scanning (Dependabot / Renovate)"
        hecvat_questions: ["VULN-01", "VULN-02"]
        priority: high  # high | medium | low
        effort: small   # small (< 1 hr) | medium (1-4 hrs) | large (4+ hrs)
        description: |
          Create .github/dependabot.yml (or equivalent for the repo's CI system)
          to enable automated dependency vulnerability scanning.
        files_to_create:
          - ".github/dependabot.yml"
        files_to_modify: []
        acceptance_criteria:
          - "Dependabot config file exists and targets correct package ecosystems"
          - "CI pipeline includes a dependency audit step"
          - "Vulnerable dependency alerts are enabled"
        tests_to_add:
          - "Verify dependabot.yml is valid YAML with correct schema"
          - "Verify CI pipeline runs dependency audit on PR"
        depends_on: []  # task IDs this depends on

      - id: "VULN-03-fix"
        title: "Add SAST scanning to CI pipeline"
        hecvat_questions: ["VULN-03"]
        priority: high
        effort: medium
        description: |
          Add a static analysis security testing step to the CI pipeline
          using semgrep, CodeQL, or bandit (depending on language).
        files_to_create: []
        files_to_modify:
          - ".github/workflows/ci.yml"
        acceptance_criteria:
          - "SAST tool runs on every PR"
          - "Build fails on high-severity findings"
        tests_to_add:
          - "Verify SAST step exists in CI workflow"
          - "Verify SAST exit code blocks merge on findings"
        depends_on: []

  - name: "Security Headers & Middleware"
    description: "Add security headers and protective middleware to the application."
    can_parallel_with: ["CI/CD & Vulnerability Scanning", "Documentation & Policy"]
    tasks: []  # Populate from APPL-* "No" answers

  - name: "Authentication & Session Management"
    description: "Implement or harden authentication, MFA, and session controls."
    can_parallel_with: ["Data Security & Encryption"]
    tasks: []  # Populate from AAAI-* "No" answers

  - name: "Data Security & Encryption"
    description: "Add encryption at rest/transit, key management, and data classification."
    can_parallel_with: ["Authentication & Session Management"]
    tasks: []  # Populate from DATA-* "No" answers

  - name: "Accessibility"
    description: "Improve WCAG compliance and add accessibility testing."
    can_parallel_with: ["all"]  # No deps on security streams
    tasks: []  # Populate from ITAC-* "No" answers

  - name: "Documentation & Policy"
    description: "Add security policies, architecture docs, and compliance documentation."
    can_parallel_with: ["all"]
    tasks: []  # Populate from DOCU-* "No" answers

# Summary of organizational attestation gaps (not fixable via code)
org_attestation_gaps:
  total: <N>
  note: "These questions require organizational attestation and cannot be resolved through code changes."
  categories:
    - category: "COMP"
      count: <N>
      description: "Company information and legal"
    - category: "GNRL"
      count: <N>
      description: "General vendor information"
    # ... etc
```

Each task should also include:
- `patchable: true/false` — whether the task is already handled by the auto-generated `.patch` file
- `fix_type` — matches the fix_type from the assessment (code/config/new_file/documentation/policy)
- `fix_complexity` — matches the fix_complexity from the assessment (small/medium/large)
- `resolves_count` — number of HECVAT questions this single task resolves

Example task with these fields:
```yaml
      - id: "VULN-03-fix"
        title: "Add SAST scanning to CI pipeline"
        hecvat_questions: ["VULN-03"]
        patchable: true
        fix_type: config
        fix_complexity: small
        priority: high
        effort: medium
        ...
```

### Task deduplication

Before creating individual tasks, identify questions that share the same remediation:

1. Group questions where the fix is substantially the same implementation
2. Create ONE task that references ALL related question IDs in `hecvat_questions`
3. Title the task by the shared implementation, not the individual question
4. Document which specific questions are resolved by the task

Example: Questions AAAI-01, AAAI-06, AAAI-12, AAAI-15 all require SSO implementation.
Create one task:

```yaml
      - id: "SSO-implementation"
        title: "Implement SSO via OIDC/SAML integration"
        hecvat_questions: ["AAAI-01", "AAAI-06", "AAAI-12", "AAAI-15"]
        patchable: false
        fix_type: code
        fix_complexity: large
        priority: high
        effort: large
        description: |
          Implement OAuth2/OIDC and optionally SAML2 support to resolve 4 related
          HECVAT authentication questions. Use authlib or python-social-auth.
        resolves_count: 4
```

Common deduplication groups to watch for:
- SSO/OIDC/SAML/federated auth → single "Implement SSO" task
- RBAC/role separation/least privilege → single "Implement RBAC" task
- Backup strategy/off-site/encryption/scheduling → single "Implement backup system" task
- WCAG audit/VPAT/accessibility testing → single "Accessibility audit + remediation" task
- Key management/rotation/lifecycle → single "Implement key management" task
- Change management policy/notification/emergency → single "Create change management docs" task

### Checklist metadata

Include deduplication metrics in the metadata section:

```yaml
metadata:
  ...
  total_tasks: <N>
  total_hecvat_questions_resolved: <M>  # M >= N because tasks are deduplicated
  deduplication_ratio: <M/N>  # e.g., 1.5 means each task resolves 1.5 questions on average
```

**Key rules for checklist generation:**

1. **Group tasks into parallel work streams** by HECVAT category. Tasks within different streams should be executable concurrently by different agents/developers.
2. **Order tasks within each stream** by dependency — if task B requires task A's output, A comes first and B lists A in `depends_on`.
3. **Include acceptance criteria** that are concrete and testable — an AI agent should be able to verify each criterion programmatically.
4. **Include `tests_to_add`** — specific tests that should be created alongside the fix, so the improvement is validated as it's built.
5. **Mark effort and priority** — `priority` reflects HECVAT importance/risk; `effort` reflects implementation complexity for this specific repo.
6. **List `files_to_create` and `files_to_modify`** — so agents know exactly what they'll touch and can plan accordingly.
7. **Include the org attestation summary** at the bottom so developers understand what's out of scope for code fixes.
8. **Only include tasks where code remediation is possible** — don't create tasks for questions that require business process changes, legal agreements, or organizational attestation.
9. **Deduplicate tasks** — group questions that share the same fix into a single task with all related question IDs.
10. **Mark patchable status** — indicate whether each task is already handled by the auto-generated patch file.

## Step 7: Reports & Summary

Use the report generator script to produce filled xlsx files. Use the resolved template from Step 1 (pre-filled if available, blank otherwise) so that org answers carry through:

```bash
# XLSX is the resolved template path from Step 1 (repo-level > org-level > blank)

# Current state report
python3 SKILL_DIR/scripts/generate_report.py \
  "$XLSX" \
  ./docs/hecvat/assessment-current.json \
  ./docs/hecvat/hecvat-report-current.xlsx

# Post-patch report (git apply only)
python3 SKILL_DIR/scripts/generate_report.py \
  "$XLSX" \
  ./docs/hecvat/assessment-post-patch.json \
  ./docs/hecvat/hecvat-report-post-patch.xlsx

# Post-checklist report (all developer tasks completed)
python3 SKILL_DIR/scripts/generate_report.py \
  "$XLSX" \
  ./docs/hecvat/assessment-post-checklist.json \
  ./docs/hecvat/hecvat-report-post-checklist.xlsx
```

### Generate human-readable summary

```bash
python3 SKILL_DIR/scripts/generate_summary.py \
  ./docs/hecvat/assessment-current.json \
  SKILL_DIR/references/scoring-weights.yaml \
  ./docs/hecvat/hecvat-summary.md
```

The summary should include a **3-tier scoring table** showing current, post-patch, and post-checklist scores side by side. Include all three tiers in the main summary file rather than generating separate summary files per tier.

After writing `hecvat-summary.md`, also print the 3-tier table in the output summary:

```
Compliance Scores (3-tier):
  Tier              | Raw Score       | Weighted
  Current           | 27/81 (33.3%)   | 36.3 / 100
  Post-patch        | 39/81 (48.1%)   | 52.1 / 100    ← git apply only
  Post-checklist    | 60/81 (74.1%)   | 68.7 / 100    ← all dev tasks done
```

To generate the scores for each tier, run `generate_summary.py` for each assessment JSON.
The main `hecvat-summary.md` should include all three tiers' scores in its "Overall Scores" section.

### Generate delta from previous run (if archived)

If Step 0 archived a previous assessment, automatically generate a delta report showing what improved:

```bash
# Find the most recent archive
LATEST_ARCHIVE=$(ls -d ./docs/hecvat/archive/*/ 2>/dev/null | sort | tail -1)

if [ -n "$LATEST_ARCHIVE" ] && [ -f "${LATEST_ARCHIVE}assessment-current.json" ]; then
    python3 SKILL_DIR/scripts/generate_delta.py \
      "${LATEST_ARCHIVE}assessment-current.json" \
      ./docs/hecvat/assessment-current.json \
      SKILL_DIR/references/scoring-weights.yaml \
      ./docs/hecvat/hecvat-delta-from-previous.md

    echo "Delta report generated: docs/hecvat/hecvat-delta-from-previous.md"
fi
```

## Output Summary

After completion, print a summary:

```
HECVAT Assessment Complete
==========================
Version: 4.1.4
Questions assessed from code: X / 332
Questions requiring org attestation: Y / 332

Compliance Scores (3-tier):
  Tier              | Raw Score        | Weighted  | What it takes
  Current           | ZZ / X (PP%)     | WW.W / 100 | —
  Post-patch        | PP / X (PP%)     | WW.W / 100 | git apply (minutes)
  Post-checklist    | CC / X (PP%)     | WW.W / 100 | Complete dev checklist (hours/days)
  Confidence-adj:   CC.C / 100 (conservative — weights by evidence strength)

Patch Results:
  Auto-patchable gaps:  AA (applied via hecvat-remediation.patch)
  Manual action items:  BB (see hecvat-remediation-manual.md)
  Checklist tasks:      TT (resolving QQ questions, dedup ratio: R.Rx)
  Patch validation:     PASSED (git apply --check)

Category Breakdown:
  Category                   | Score  | Weight | Gaps | Fix Types
  Authentication (AAAI)      | 3/17   |   10   |  14  | 8 code, 4 policy, 2 org
  Application Security (APPL)| 7/13   |    9   |   6  | 3 code, 2 config, 1 doc
  ...

Top Remediation Priorities (by gap impact):
  1. AAAI — SSO + RBAC (impact: 8.2, resolves 14 questions)
  2. DATA — Encryption + backups (impact: 5.6, resolves 13 questions)
  ...

Deliverables in ./docs/hecvat/:
  hecvat-report-current.xlsx                    — Current state HECVAT report
  hecvat-report-post-patch.xlsx                 — Post-patch report (git apply only)
  hecvat-report-post-checklist.xlsx             — Post-checklist report (all dev tasks)
  hecvat-remediation.patch                      — git apply-able patch (AA fixes)
  hecvat-remediation-manual.md                  — Manual action items (BB items)
  hecvat-improvement-developer-checklist.yaml   — Developer task list (TT tasks)
  hecvat-summary.md                             — Human-readable summary with 3-tier scoring
  assessment-current.json                       — Machine-readable current assessment
  assessment-post-patch.json                    — Machine-readable post-patch assessment
  assessment-post-checklist.json                — Machine-readable post-checklist assessment
```

## Resources

### scripts/
- **parse_hecvat.py** — Parse HECVAT xlsx into `hecvat-questions.json`. Extracts all 332 questions with metadata, repo-assessability flags, and guidance.
- **generate_report.py** — Fill the HECVAT xlsx template with assessment answers and evidence. Writes to Answer (col C) and Additional Information (col D) across all response sheets.
- **generate_summary.py** — Generate a human-readable HECVAT assessment summary with category breakdown tables, fix-type analysis, remediation priorities, and glossary. Supports `--compare` mode for delta between two assessments.
- **generate_delta.py** — Compare two HECVAT assessments and produce a delta report showing improvements (No→Yes), regressions (Yes→No), newly assessed questions, and per-category score changes.

### references/
- **[scoring-rubric.md](references/scoring-rubric.md)** — Scoring rubric with answer values, confidence levels, repo-assessability decision tree, evidence quality requirements, weighted scoring methodology, and category-specific scoring notes. Read before assessment mapping (Step 4).
- **[scoring-weights.yaml](references/scoring-weights.yaml)** — Category weights for weighted compliance scoring. Reflects relative security impact (auth=10, accessibility=3, etc.).
- **[scan-patterns.yaml](references/scan-patterns.yaml)** — Complete Glob and Grep patterns for every HECVAT category, organized by security domain. Includes patch generation patterns. Read before repo scanning (Step 3).
- **[language-patterns.yaml](references/language-patterns.yaml)** — Language and framework-specific detection patterns. Maps HECVAT categories to library/package names for JavaScript, Python, Go, Java, Ruby, Rust, C#, and PHP. Supplements generic patterns for higher accuracy.
- **[context-analysis.yaml](references/context-analysis.yaml)** — Context-aware analysis rules for evaluating grep matches. Defines false-positive indicators (comments, TODOs, disabled code) and true-positive strengtheners (active middleware, CI steps). Category-specific rules for AAAI, APPL, DATA, VULN, CHNG, and ITAC.

### Assets
- **HECVAT414.xlsx** — The EDUCAUSE HECVAT v4.1.4 template (15 sheets, 332 questions). Used as the source for JSON parsing and as the template for report generation.

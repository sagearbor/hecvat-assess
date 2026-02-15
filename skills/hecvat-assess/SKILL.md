---
name: hecvat-assess
description: "Evaluate a GitHub or Azure DevOps repository against the HECVAT (Higher Education Community Vendor Assessment Toolkit) v4.1.4 from EDUCAUSE. Scans source code, config files, CI/CD pipelines, IaC, dependencies, and documentation to auto-assess ~40-50% of HECVAT questions, generates compliance reports as filled xlsx files, and produces patch files for remediable gaps. Use when: (1) user invokes /hecvat-assess, (2) user asks to 'evaluate this repo for HECVAT compliance', (3) user needs to 'fill out a HECVAT', (4) user mentions HECVAT, EDUCAUSE vendor assessment, or higher education security assessment, (5) user asks about compliance readiness for higher ed procurement."
---

# HECVAT Repository Assessment

Assess a code repository against the EDUCAUSE HECVAT v4.1.4 (332 questions across 7 categories). Produce two filled HECVAT xlsx reports (current state + projected post-patch), a unified diff patch file for remediable gaps, and a developer improvement checklist for AI-assisted remediation.

## Workflow

```
  /hecvat-assess
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
 | + evidence_q   |     | + projected       |     |                  |
 +----------------+     +-------------------+     +------------------+
                                                        |
       +------------------------------------------------+
       |
       v
 +-------------------+
 |7.Reports & Summary|
 | fill xlsx         |
 | summary markdown  |
 | current+projected |
 +-------------------+
       |
       v
 ./docs/hecvat/
  |- hecvat-report-current.xlsx          — Filled HECVAT xlsx (current state)
  |- hecvat-report-projected.xlsx        — Filled HECVAT xlsx (post-remediation)
  |- hecvat-remediation.patch            — git apply-able patch for code/config fixes
  |- hecvat-remediation-manual.md        — Non-patchable gaps requiring human action
  |- hecvat-improvement-developer-checklist.yaml  — Developer/AI agent task list
  |- hecvat-summary.md                   — Human-readable summary with tables + glossary
  |- assessment-current.json             — Machine-readable current assessment
  |- assessment-projected.json           — Machine-readable projected assessment
```

1. **Bootstrap** — Parse xlsx into JSON cache
2. **Version check** — Verify HECVAT version is current
3. **Repo scan** — Deep scan codebase by HECVAT category
4. **Assessment mapping** — Map findings to questions with evidence + fix classification
5. **Patch generation** — Generate real `git apply`-able patches via edit-diff-revert cycle
6. **Developer checklist** — Generate deduplicated improvement checklist for AI agents
7. **Reports & summary** — Produce xlsx reports + human-readable markdown summary

All outputs go to `./docs/hecvat/` in the repo being assessed. If a `./docs/` directory already exists, write directly into `./docs/hecvat/`. If it does not exist, create `./docs/` first, then `./docs/hecvat/`.

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

### 5g. Build projected assessment

Create `assessment-projected.json` by copying `assessment-current.json` and:
- For each gap with `fix_type` in (`code`, `config`, `new_file`): flip answer from "No" to "Yes", update `additional_info` with "[Projected] Fixed via hecvat-remediation.patch"
- For `documentation` gaps: flip to "Yes" with "[Projected] Manual documentation task"
- Leave `policy` and `organizational` gaps as "No"
- Add a top-level `flipped_questions` array listing all changed question IDs
- Add a top-level `projected_methodology` field explaining what was flipped and why

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
  projected_score: "<projected compliant> / <assessed>"
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

# Projected post-patch report
python3 SKILL_DIR/scripts/generate_report.py \
  "$XLSX" \
  ./docs/hecvat/assessment-projected.json \
  ./docs/hecvat/hecvat-report-projected.xlsx
```

### Generate human-readable summary

```bash
python3 SKILL_DIR/scripts/generate_summary.py \
  ./docs/hecvat/assessment-current.json \
  SKILL_DIR/references/scoring-weights.yaml \
  ./docs/hecvat/hecvat-summary.md
```

If a projected assessment exists, include it as a comparison:

```bash
python3 SKILL_DIR/scripts/generate_summary.py \
  ./docs/hecvat/assessment-projected.json \
  SKILL_DIR/references/scoring-weights.yaml \
  ./docs/hecvat/hecvat-summary-projected.md \
  --compare ./docs/hecvat/assessment-current.json
```

## Output Summary

After completion, print a summary:

```
HECVAT Assessment Complete
==========================
Version: 4.1.4
Questions assessed from code: X / 332
Questions requiring org attestation: Y / 332

Compliance Scores:
  Raw score:            Z / X assessed (PP%)
  Weighted score:       WW.W / 100
  Confidence-adjusted:  CC.C / 100 (conservative)

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
  hecvat-report-projected.xlsx                  — Projected report (post-patch)
  hecvat-remediation.patch                      — git apply-able patch (AA fixes)
  hecvat-remediation-manual.md                  — Manual action items (BB items)
  hecvat-improvement-developer-checklist.yaml   — Developer task list (TT tasks)
  hecvat-summary.md                             — Human-readable summary
  assessment-current.json                       — Machine-readable current assessment
  assessment-projected.json                     — Machine-readable projected assessment
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

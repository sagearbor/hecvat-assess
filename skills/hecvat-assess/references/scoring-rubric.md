# HECVAT Scoring Rubric

## Table of Contents
- [Answer Values](#answer-values)
- [Confidence Levels](#confidence-levels)
- [Repo-Assessable Decision Tree](#repo-assessable-decision-tree)
- [Evidence Quality Requirements](#evidence-quality-requirements)
- [Evidence Quality Scoring](#evidence-quality-scoring)
- [Fix-Type Classification](#fix-type-classification)
- [Category-Specific Scoring Notes](#category-specific-scoring-notes)

## Answer Values

Each HECVAT question expects one of these responses:

| Answer | When to use |
|--------|------------|
| **Yes** | Code evidence clearly demonstrates compliance |
| **No** | Code evidence shows non-compliance or feature is absent |
| **N/A** | Question does not apply to this product/service type |
| *(text)* | Free-text questions (GNRL, COMP sections) — provide descriptive answer |

## Confidence Levels

Assign confidence to each repo-assessed answer:

| Level | Criteria | Example |
|-------|----------|---------|
| **High** | Direct code evidence: config file, explicit implementation | `FORCE_SSL=true` in env config |
| **Medium** | Indirect evidence: patterns suggest compliance but not explicit | Uses HTTPS URLs throughout but no explicit TLS enforcement |
| **Low** | Inferred: best-guess based on framework defaults or conventions | Django project (CSRF protection on by default) but no explicit config |

Include confidence in the `additional_info` field: `[Confidence: High] Found explicit TLS configuration in nginx.conf:42`

## Repo-Assessable Decision Tree

A question is **repo-assessable** if ANY of these apply:

1. **Config-verifiable**: Answer can be confirmed from config files, env vars, IaC templates
   - Examples: TLS settings, auth config, CORS policy, CSP headers
2. **Code-verifiable**: Answer can be confirmed from source code patterns
   - Examples: Input validation, parameterized queries, encryption usage, logging
3. **Dependency-verifiable**: Answer can be confirmed from dependency manifests
   - Examples: Known-vulnerable packages, outdated frameworks, security libraries
4. **CI/CD-verifiable**: Answer can be confirmed from pipeline definitions
   - Examples: SAST scanning, automated testing, deployment processes
5. **Doc-verifiable**: Answer can be confirmed from repo documentation
   - Examples: Architecture docs, security policies checked into repo, API docs

A question requires **organizational attestation** if it asks about:
- Business processes, staffing, or organizational structure
- Legal agreements, insurance, or certifications
- Physical security or data center operations (unless IaC is present)
- Historical events (breaches, audits, uptime)
- Vendor relationships not visible in code

## Evidence Quality Requirements

### Minimum evidence for a "Yes" answer:
- At least one file path with line number
- Specific config value or code pattern found
- Brief explanation of how it satisfies the requirement

### Minimum evidence for a "No" answer:
- Description of what was searched for
- Confirmation it was not found
- Suggested remediation (what to add/change)

### Format:
```
[Confidence: High|Medium|Low]
Finding: <what was found or not found>
Files: <file:line, file:line, ...>
Remediation: <if non-compliant, what to fix>
```

## Weighted Scoring

Read [scoring-weights.yaml](scoring-weights.yaml) for category weights. Compute two scores:

### Raw Score
Simple compliance ratio: `compliant / assessed` (e.g., 92/158 = 58%)

### Weighted Score
Category-weighted score that reflects security impact (0-100):
- For each category, compute: `(compliant_in_category / total_in_category) * category_weight`
- Sum all category scores and divide by sum of applicable weights
- Categories with weight 0 (org attestation only) are excluded

### Category Breakdown

Include a per-category compliance breakdown in the output summary:

```
Category Breakdown
==================
Category                  | Score | Weight | Weighted | Status
Authentication (AAAI)     | 15/18 |   10   |   8.3    | Gaps in MFA, session timeout
Application Security (APPL)| 12/15 |    9   |   7.2    | Missing CSP, rate limiting
Data Security (DATA)      |  8/12 |    9   |   6.0    | No encryption at rest
Vulnerability Mgmt (VULN) |  4/6  |    8   |   5.3    | No SAST scanning
Change Management (CHNG)  |  5/8  |    6   |   3.8    | No branch protection
Accessibility (ITAC)      |  3/10 |    3   |   0.9    | Low WCAG compliance
...

Raw Score:     92/158 (58%)
Weighted Score: 67/100
```

### Risk Priority

The category breakdown reveals where to focus remediation:
- Categories with high weight and low score are the highest priority
- "Gap Impact" = weight * (1 - category_score) — higher means more impactful to fix

## Evidence Quality Scoring

Each assessed answer includes an `evidence_quality` rating that indicates how strong
the supporting evidence is. This helps reviewers know where to double-check.

### Evidence Quality Levels

| Level | Numeric | Criteria | When to Assign |
|-------|---------|----------|----------------|
| Strong | 1.0 | Direct implementation + tests or verified-active config | Found code AND test, or config confirmed via runtime check |
| Moderate | 0.75 | Implementation found, no tests or not confirmed active | Found middleware but no test file, or config exists but not verified |
| Weak | 0.5 | Reference exists but not confirmed functional | Env var defined but never read, or TODO comment, or disabled code |
| Inferred | 0.25 | No direct evidence; based on framework defaults or absence | Framework provides feature by default (e.g., Django CSRF) |

### Confidence-Adjusted Scoring (Optional)

For a more honest compliance picture, weight "Yes" answers by evidence quality:
- Strong "Yes" = 1.0 toward compliance
- Moderate "Yes" = 0.75
- Weak "Yes" = 0.5
- Inferred "Yes" = 0.25

Confidence-adjusted raw score: `sum(quality_weight for each Yes) / assessed_count`

This is OPTIONAL — the standard scoring uses binary Yes/No. The confidence-adjusted
score is an additional metric for teams that want a more conservative assessment.

## Fix-Type Classification

Each "No" answer should include a `fix_type` field indicating how the gap can be remediated:

| fix_type | Description | Goes in .patch? | Example |
|----------|-------------|-----------------|---------|
| `code` | Change to existing source code | Yes | Add security middleware, input validation |
| `config` | Change to existing config file | Yes | CI pipeline step, Dockerfile directive |
| `new_file` | Create a new file | Yes | `.github/dependabot.yml`, policy doc |
| `documentation` | Add/update documentation in repo | Maybe (if simple) | Add SECURITY.md, update README |
| `policy` | Requires organizational process/policy | No | Change management policy, training |
| `organizational` | Requires org attestation, legal, business | No | Insurance, certifications, staffing |

### Fix Complexity

Each "No" answer should also include a `fix_complexity` field:

| Complexity | Estimated Effort | Example |
|------------|-----------------|---------|
| `small` | Less than 1 hour | Add a config file, enable a flag |
| `medium` | 1-4 hours | Add middleware with configuration, write a policy doc |
| `large` | 4+ hours | Implement SSO, build RBAC system, full accessibility audit |

### Classification Rules

- `code`: The fix requires changing existing source code (add middleware, validation, sanitization, etc.)
- `config`: The fix requires changing existing config files (CI pipeline, Dockerfile, nginx config, etc.)
- `new_file`: The fix requires creating a new file (`.github/dependabot.yml`, `SECURITY.md`, etc.)
- `documentation`: The fix requires adding/updating documentation checked into the repo
- `policy`: The fix requires organizational process or policy (change management policy, training, etc.)
- `organizational`: The question requires business/legal attestation (insurance, certifications, staffing)

For "Yes" and "N/A" answers, `fix_type` should be omitted or set to `null`.

## Category-Specific Scoring Notes

### AAAI (Authentication/Authorization)
- Look for: OAuth/OIDC config, session management, MFA enforcement, RBAC/ABAC patterns
- High-value files: auth middleware, login handlers, session config, JWT settings
- Common "No" triggers: no MFA, no session timeout config, no account lockout

### APPL (Application Security)
- Look for: input validation, output encoding, CSP headers, CSRF tokens, parameterized queries
- High-value files: middleware, request handlers, ORM config, security headers
- Common "No" triggers: raw SQL, missing CSRF, no rate limiting

### CHNG (Change Management)
- Look for: CI/CD pipeline definitions, branch protection evidence, code review config
- High-value files: .github/workflows/, .gitlab-ci.yml, Jenkinsfile, azure-pipelines.yml
- Partially assessable: process questions require org attestation

### DATA (Data Security)
- Look for: encryption at rest/transit config, key management, data classification
- High-value files: database config, TLS certs, KMS config, encryption utilities
- Common "No" triggers: plaintext credentials, no encryption config

### VULN (Vulnerability Management)
- Look for: dependency scanning (Dependabot, Snyk), SAST tools, security testing
- High-value files: .github/dependabot.yml, security scanning CI steps, test suites

### ITAC (IT Accessibility)
- Look for: WCAG compliance markers, aria attributes, accessibility testing
- High-value files: frontend components, CSS, accessibility test configs
- Note: full WCAG audit is beyond repo scanning; flag for manual review

### AI* (AI Categories)
- Look for: model versioning, bias testing, data lineage, AI governance docs
- High-value files: model configs, training pipelines, evaluation scripts, AI policies
- Many questions require org attestation about AI practices

### Privacy/HIPAA/FERPA/PCI
- Look for: data handling patterns, PII detection, consent management, audit logging
- High-value files: data models, API handlers, logging config, privacy policies
- Regulatory compliance often requires org attestation beyond code

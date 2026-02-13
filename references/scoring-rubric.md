# HECVAT Scoring Rubric

## Table of Contents
- [Answer Values](#answer-values)
- [Confidence Levels](#confidence-levels)
- [Repo-Assessable Decision Tree](#repo-assessable-decision-tree)
- [Evidence Quality Requirements](#evidence-quality-requirements)
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

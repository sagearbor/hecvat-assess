# Repo Scan Patterns

## Table of Contents
- [Scan Strategy](#scan-strategy)
- [File Discovery Patterns](#file-discovery-patterns)
- [Category: Authentication & Authorization (AAAI)](#category-authentication--authorization-aaai)
- [Category: Application Security (APPL)](#category-application-security-appl)
- [Category: Change Management (CHNG)](#category-change-management-chng)
- [Category: Data Security (DATA)](#category-data-security-data)
- [Category: Vulnerability Management (VULN)](#category-vulnerability-management-vuln)
- [Category: IT Accessibility (ITAC)](#category-it-accessibility-itac)
- [Category: AI (AIML/AILM/AISC/AIGN/AIQU/DPAI)](#category-ai)
- [Category: Infrastructure (DCTR/OPEM)](#category-infrastructure-dctropem)
- [Category: Privacy & Compliance (HIPA/PCID/FIDP/PDAT/PPPR/DRPV)](#category-privacy--compliance)
- [Category: Third Party (THRD/CONS)](#category-third-party-thrdcons)
- [Patch Generation Patterns](#patch-generation-patterns)

## Scan Strategy

Scan in two passes:

**Pass 1 — File discovery:** Use Glob to build a file inventory by type.
**Pass 2 — Content analysis:** Use Grep on discovered files for category-specific patterns.

Prioritize breadth over depth. Cover all categories before deep-diving into any one.

## File Discovery Patterns

Run these Glob patterns first to map the repo structure:

```
# Dependencies
**/package.json, **/requirements.txt, **/Pipfile, **/pyproject.toml
**/Gemfile, **/go.mod, **/pom.xml, **/build.gradle, **/Cargo.toml

# Config
**/.env*, **/config/**, **/settings.*, **/*.config.*, **/*.yml, **/*.yaml, **/*.toml

# CI/CD
**/.github/workflows/**, **/.gitlab-ci.yml, **/Jenkinsfile, **/azure-pipelines.yml
**/Dockerfile*, **/docker-compose*, **/.dockerignore

# IaC
**/terraform/**, **/*.tf, **/cloudformation/**, **/pulumi/**, **/cdk/**
**/ansible/**, **/helm/**, **/k8s/**, **/kubernetes/**

# Security
**/.snyk, **/.trivyignore, **/security.*, **/.github/dependabot.yml
**/SECURITY.md, **/.bandit, **/.eslintrc*, **/.semgreprc

# Docs
**/docs/**, **/README*, **/ARCHITECTURE*, **/CONTRIBUTING*
**/API*, **/*.api.*, **/openapi.*, **/swagger.*

# Frontend (accessibility)
**/src/**/*.tsx, **/src/**/*.jsx, **/src/**/*.vue, **/src/**/*.svelte
**/public/**, **/static/**
```

## Category: Authentication & Authorization (AAAI)

### Grep patterns:
```
# Auth mechanisms
oauth|oidc|saml|ldap|active.directory|sso
jwt|jsonwebtoken|bearer.token|access.token|refresh.token
passport|auth0|okta|cognito|firebase.auth|supabase.auth

# MFA
mfa|multi.factor|two.factor|2fa|totp|authenticator
webauthn|fido|u2f

# Session management
session.timeout|session.expir|idle.timeout|max.age
cookie.*(secure|httponly|samesite)
express-session|flask-session|django.session

# Account management
account.lockout|failed.attempts|brute.force|rate.limit
password.policy|password.complex|bcrypt|argon2|scrypt|pbkdf2
```

### Key files to read:
- Auth middleware/config files
- Login/registration handlers
- Session configuration
- User model/schema

## Category: Application Security (APPL)

### Grep patterns:
```
# Input validation
sanitiz|validat|escape|encode|purif
zod|joi|yup|cerberus|marshmallow|pydantic

# SQL injection
parameterized|prepared.statement|bind.param|placeholder
raw.query|raw.sql|execute.*%s|execute.*\+|string.format.*SELECT

# XSS
dangerouslySetInnerHTML|v-html|innerHTML|document\.write
DOMPurify|bleach|sanitize-html|helmet

# CSRF
csrf|xsrf|anti.forgery|csurf
SameSite|double.submit

# Security headers
helmet|Content-Security-Policy|X-Frame-Options|X-Content-Type
Strict-Transport-Security|hsts|Referrer-Policy

# Rate limiting
rate.limit|throttl|express-rate-limit|flask-limiter|django-ratelimit

# Logging/monitoring
winston|pino|bunyan|logging|log4j|serilog|structlog
audit.log|security.log|access.log
```

## Category: Change Management (CHNG)

### Grep patterns (CI/CD files):
```
# Testing in pipeline
pytest|jest|mocha|rspec|junit|go.test|cargo.test
coverage|codecov|coveralls|sonar

# Code review
pull_request|merge_request|required_reviewers|branch_protection
CODEOWNERS|required.approving.reviews

# Deployment
deploy|release|rollback|canary|blue.green|rolling.update
staging|production|environment
```

### Key files:
- `.github/workflows/*.yml`
- `.gitlab-ci.yml`
- `Jenkinsfile`
- `CODEOWNERS`

## Category: Data Security (DATA)

### Grep patterns:
```
# Encryption at rest
encrypt|AES|KMS|vault|sealed.secret
ENCRYPTION_KEY|DATA_ENCRYPTION|at.rest

# Encryption in transit
TLS|SSL|HTTPS|FORCE_SSL|SECURE_SSL_REDIRECT
ssl_certificate|tls.crt|cert.pem

# Key management
key.rotation|key.management|kms|vault
AWS_KMS|AZURE_KEY_VAULT|GCP_KMS|HashiCorp

# Data classification
PII|PHI|sensitive|confidential|restricted
data.classification|data.label

# Backup
backup|snapshot|replication|disaster.recovery
pg_dump|mongodump|mysqldump
```

## Category: Vulnerability Management (VULN)

### Grep patterns:
```
# Dependency scanning
dependabot|renovate|snyk|whitesource|mend
npm.audit|pip.audit|bundle.audit|safety.check

# SAST
semgrep|sonarqube|sonar-scanner|codeql|bandit|brakeman
eslint-plugin-security|gosec|clippy

# Container scanning
trivy|grype|anchore|clair|twistlock|prisma.cloud

# Penetration testing evidence
pentest|penetration|security.assessment|bug.bounty
```

## Category: IT Accessibility (ITAC)

### Grep patterns:
```
# WCAG/ARIA
aria-|role=|alt=|tabindex|focus.trap|skip.nav
aria-label|aria-describedby|aria-live|aria-hidden

# Accessibility testing
axe|pa11y|lighthouse|wave|jest-axe|cypress-axe
a11y|accessibility|wcag

# Accessibility features
prefers-reduced-motion|prefers-color-scheme|prefers-contrast
focus-visible|:focus|screen.reader|sr-only
lang=|xml:lang
```

## Category: AI

### Grep patterns:
```
# Model management
model.version|model.registry|mlflow|wandb|neptune
model.card|model.metadata

# Training/evaluation
training.data|test.data|evaluation|bias.test|fairness
confusion.matrix|precision|recall|f1.score

# AI governance
ai.policy|responsible.ai|ethical.ai|ai.governance
explainab|interpretab|transparency

# Data lineage
data.lineage|data.provenance|dvc|data.version
feature.store|feature.engineering

# LLM specific
openai|anthropic|langchain|llama|huggingface
prompt|embedding|vector.store|rag
temperature|max_tokens|system.prompt
guardrail|content.filter|moderation
```

## Category: Infrastructure (DCTR/OPEM)

### Grep patterns:
```
# Cloud provider
aws|azure|gcp|cloud|iaas|paas|saas
terraform|cloudformation|pulumi|cdk|bicep

# Monitoring
prometheus|grafana|datadog|newrelic|cloudwatch
alert|monitor|uptime|health.check|readiness|liveness

# Container/orchestration
docker|kubernetes|k8s|helm|ecs|fargate
pod.security|network.policy|resource.limit
```

## Category: Privacy & Compliance

### Grep patterns:
```
# HIPAA
hipaa|phi|protected.health|baa|covered.entity
hl7|fhir|dicom|medical.record

# FERPA
ferpa|education.record|student.data|directory.information

# PCI
pci.dss|cardholder|credit.card|payment.card
stripe|braintree|square|adyen|payment.gateway
tokeniz|mask|redact

# GDPR/Privacy
gdpr|ccpa|privacy.policy|data.subject|consent
right.to.delete|data.portability|data.retention
cookie.consent|opt.in|opt.out

# Audit logging
audit.trail|audit.log|immutable.log|tamper.proof
```

## Category: Third Party (THRD/CONS)

### Grep patterns:
```
# Subprocessors/vendors
vendor|subprocessor|third.party|external.service
api.key|client.id|client.secret

# Dependency inventory
package.json|requirements.txt|go.mod|Cargo.toml
license|SPDX|SBOM|software.bill.of.materials
cyclonedx|spdx-sbom
```

## Patch Generation Patterns

When generating `.patch` files for non-compliant findings, follow these patterns:

### Security headers (missing CSP, HSTS, etc.)
- Add middleware configuration for the detected framework
- Include all recommended headers, not just the missing one

### Missing dependency scanning
- Add `.github/dependabot.yml` or equivalent
- Add scanning step to existing CI pipeline

### Missing input validation
- Add validation library to dependencies
- Add validation middleware/decorators to affected routes

### Missing encryption config
- Add TLS/SSL configuration
- Add encryption-at-rest settings for database connections

### Missing accessibility attributes
- Add aria labels to interactive elements
- Add alt text placeholders for images
- Add lang attribute to HTML root

### Patch format
Generate unified diff format compatible with `git apply`:
```diff
--- a/path/to/file
+++ b/path/to/file
@@ -line,count +line,count @@
 context line
-removed line
+added line
 context line
```

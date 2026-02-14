# Language Detection Implementation Guide

This guide explains how to implement language/framework detection using `language-patterns.yaml` during HECVAT assessment.

## Overview

Language-specific patterns supplement generic patterns to improve detection accuracy. For example:

- **Generic pattern**: `oauth|oidc|saml` (catches keyword mentions)
- **Language-specific pattern**: `passport-oauth2` for Node.js or `django-allauth` for Python (catches actual implementations)

## Implementation Flow

### Step 1: Detect Languages (Before Pass 2)

```python
import yaml
import os
from pathlib import Path

def detect_languages(repo_path):
    """Detect primary language(s) in the repository."""

    with open('references/language-patterns.yaml') as f:
        patterns = yaml.safe_load(f)

    detected = {}
    indicators = patterns['language_detection']['indicators']

    for lang, config in indicators.items():
        score = 0

        # Check for indicator files (package.json, go.mod, etc.)
        for indicator_file in config['files']:
            if '*' in indicator_file:
                # Glob pattern (e.g., "*.csproj")
                if list(Path(repo_path).glob(f"**/{indicator_file}")):
                    score += 10
            else:
                # Exact file
                if (Path(repo_path) / indicator_file).exists():
                    score += 10

        # Count files with language extensions
        for ext in config['extensions']:
            file_count = len(list(Path(repo_path).glob(f"**/*{ext}")))
            score += min(file_count, 50)  # Cap at 50 to avoid skew

        if score > 0:
            detected[lang] = score

    # Sort by score, return top 3
    return sorted(detected.items(), key=lambda x: x[1], reverse=True)[:3]

# Example usage
languages = detect_languages('/path/to/repo')
print(f"Detected languages: {languages}")
# Output: [('python', 45), ('javascript', 30), ('go', 12)]
```

### Step 2: Detect Frameworks

```python
def detect_frameworks(repo_path, language):
    """Detect frameworks for a given language."""

    with open('references/language-patterns.yaml') as f:
        patterns = yaml.safe_load(f)

    framework_detection = patterns['language_detection']['framework_detection']

    if language not in framework_detection:
        return []

    detected_frameworks = []

    # Read dependency file based on language
    dependency_files = {
        'javascript': 'package.json',
        'python': 'requirements.txt',
        'go': 'go.mod',
        'java': 'pom.xml',
        'ruby': 'Gemfile',
        'rust': 'Cargo.toml',
        'php': 'composer.json',
        'csharp': '*.csproj'
    }

    dep_file = dependency_files.get(language)
    if not dep_file:
        return []

    # Read dependency file content
    dep_path = Path(repo_path) / dep_file
    if not dep_path.exists():
        return []

    content = dep_path.read_text()

    # Check for framework indicators
    for framework, indicators in framework_detection[language].items():
        for indicator in indicators:
            if indicator in content:
                detected_frameworks.append(framework)
                break

    return detected_frameworks

# Example usage
frameworks = detect_frameworks('/path/to/repo', 'javascript')
print(f"Detected frameworks: {frameworks}")
# Output: ['express', 'nextjs']
```

### Step 3: Build Language-Specific Patterns

```python
def get_language_patterns(language, category):
    """Get language-specific patterns for a HECVAT category."""

    with open('references/language-patterns.yaml') as f:
        patterns = yaml.safe_load(f)

    category_patterns = patterns['categories'].get(category, {})
    lang_patterns = category_patterns.get('languages', {}).get(language, {})

    # Flatten all pattern lists for this language/category
    all_patterns = []
    for pattern_type, pattern_list in lang_patterns.items():
        all_patterns.extend(pattern_list)

    return all_patterns

# Example usage
patterns = get_language_patterns('python', 'AAAI')
print(f"Python auth patterns: {patterns[:5]}")
# Output: ['django-allauth', 'django-oauth-toolkit', 'python-social-auth', ...]
```

### Step 4: Combine Generic + Language-Specific Grep

```python
def scan_with_language_awareness(repo_path, category, languages):
    """Scan repo using both generic and language-specific patterns."""

    # Load generic patterns from scan-patterns.yaml
    with open('references/scan-patterns.yaml') as f:
        generic_patterns = yaml.safe_load(f)

    generic_grep = generic_patterns['categories'][category]['grep_patterns']

    # Build language-specific patterns
    lang_specific = []
    for lang, _ in languages:
        lang_patterns = get_language_patterns(lang, category)
        lang_specific.extend(lang_patterns)

    # Run both pattern sets
    findings = []

    # Generic patterns (high recall, lower precision)
    for pattern in generic_grep:
        # Use Grep tool with pattern
        result = grep_repo(repo_path, pattern)
        findings.append({
            'pattern': pattern,
            'type': 'generic',
            'confidence': 'medium',
            'matches': result
        })

    # Language-specific patterns (lower recall, high precision)
    for pattern in lang_specific:
        result = grep_repo(repo_path, pattern)
        findings.append({
            'pattern': pattern,
            'type': 'language-specific',
            'confidence': 'high',  # Higher confidence for exact matches
            'matches': result
        })

    return findings
```

## Confidence Scoring

Use language detection to adjust confidence levels:

- **High confidence**: Language-specific pattern match in detected language
  - Example: Found `django-allauth` in a Python repo with Django detected

- **Medium confidence**: Generic pattern match in known language
  - Example: Found `oauth` keyword in a JavaScript repo

- **Low confidence**: Generic pattern match in unknown language
  - Example: Found `encrypt` keyword but couldn't detect repo language

## Fallback Strategy

If language detection fails (no indicator files found):

```python
languages = detect_languages(repo_path)

if not languages:
    print("Warning: Could not detect primary language")
    print("Falling back to generic patterns only")
    print("Confidence will be marked as 'Low' for all findings")

    # Use only generic patterns from scan-patterns.yaml
    # Do NOT skip assessment
```

## Example: Full Language-Aware Scan

```python
def assess_aaai_category(repo_path):
    """Assess AAAI (Authentication & Authorization) with language awareness."""

    # Step 1: Detect languages
    languages = detect_languages(repo_path)
    print(f"Detected: {languages}")

    if not languages:
        print("Using generic patterns only (low confidence)")
        languages = []

    # Step 2: Detect frameworks
    frameworks = {}
    for lang, _ in languages:
        frameworks[lang] = detect_frameworks(repo_path, lang)
    print(f"Frameworks: {frameworks}")

    # Step 3: Scan with language-specific patterns
    findings = scan_with_language_awareness(repo_path, 'AAAI', languages)

    # Step 4: Aggregate findings by confidence
    high_confidence = [f for f in findings if f['confidence'] == 'high']
    medium_confidence = [f for f in findings if f['confidence'] == 'medium']
    low_confidence = [f for f in findings if f['confidence'] == 'low']

    print(f"\nFindings:")
    print(f"  High confidence: {len(high_confidence)}")
    print(f"  Medium confidence: {len(medium_confidence)}")
    print(f"  Low confidence: {len(low_confidence)}")

    return {
        'languages': languages,
        'frameworks': frameworks,
        'findings': findings
    }
```

## Pattern Selection Guidelines

When choosing patterns for a specific repo:

1. **Primary language patterns are mandatory** — always check
2. **Secondary language patterns are optional** — check if file count > 20% of primary
3. **Framework patterns override language patterns** — if Express detected, use Express-specific patterns instead of generic Node.js
4. **Generic patterns always run** — they catch non-library implementations

## Testing Language Detection

```python
def test_language_detection():
    """Test language detection on known repos."""

    test_cases = [
        {
            'repo': '/path/to/django-project',
            'expected_lang': 'python',
            'expected_framework': 'django'
        },
        {
            'repo': '/path/to/express-api',
            'expected_lang': 'javascript',
            'expected_framework': 'express'
        }
    ]

    for case in test_cases:
        langs = detect_languages(case['repo'])
        assert langs[0][0] == case['expected_lang'], \
            f"Expected {case['expected_lang']}, got {langs[0][0]}"

        frameworks = detect_frameworks(case['repo'], case['expected_lang'])
        assert case['expected_framework'] in frameworks, \
            f"Expected framework {case['expected_framework']} not detected"

    print("All language detection tests passed!")
```

## Common Issues

### Issue: False Positives from Package Names

**Problem**: Finding `passport` in package-lock.json doesn't mean it's used.

**Solution**: Weight dependency file mentions lower than source code usage. Check for actual import/require statements:

```python
# Lower confidence for dependency file mentions
if 'package-lock.json' in file_path:
    confidence = 'medium'
elif 'src/' in file_path or 'lib/' in file_path:
    confidence = 'high'
```

### Issue: Monorepo with Multiple Languages

**Problem**: Repo has Python backend + JavaScript frontend.

**Solution**: Detect and scan both. Run language-specific patterns for each:

```python
languages = detect_languages(repo_path)
# [('python', 60), ('javascript', 55)]

# Scan with both sets of patterns
for lang, score in languages:
    patterns = get_language_patterns(lang, category)
    # ... scan with patterns
```

### Issue: Language Without Framework

**Problem**: Python repo with no Django/Flask/FastAPI.

**Solution**: Fall back to language-generic patterns (e.g., `PyJWT`, `python-jose`) which work across frameworks.

## Performance Considerations

- **Language detection is O(1)** — just check for indicator files
- **Framework detection is O(n)** — reads one dependency file
- **Pattern scanning is O(m)** — where m = number of patterns × files

For large repos (>10k files):
1. Limit Glob patterns to specific directories (`src/`, `lib/`, `app/`)
2. Use `--max-count` with Grep to stop after first N matches
3. Cache language detection results between runs

## Integration with Existing Assessment

Add language detection before Step 3, Pass 2 in SKILL.md:

```python
# In assess_repository():

# Step 3: Repo Scan
print("Step 3: Repository Scan")

# NEW: Detect languages before Pass 2
languages = detect_languages(repo_path)
print(f"Detected languages: {[l[0] for l in languages]}")

# Pass 1: File discovery (unchanged)
file_inventory = discover_files(repo_path)

# Pass 2: Content analysis (NOW language-aware)
findings = {}
for category in HECVAT_CATEGORIES:
    findings[category] = scan_with_language_awareness(
        repo_path,
        category,
        languages
    )
```

## Extending to New Languages

To add support for a new language (e.g., Swift):

1. Add language detection indicators:
```yaml
language_detection:
  indicators:
    swift:
      files: ["Package.swift", "Podfile"]
      extensions: [".swift"]
```

2. Add framework detection:
```yaml
  framework_detection:
    swift:
      vapor: ["Vapor"]
      perfect: ["PerfectHTTPServer"]
```

3. Add category patterns:
```yaml
categories:
  AAAI:
    languages:
      swift:
        auth_libraries:
          - "OAuth2"
          - "OAuthSwift"
          - "SwiftKeychainWrapper"
```

4. Test on a real Swift repo and iterate.

# Changelog

## [3.0.0] - 2026-02-15

### Fixed
- **Marketplace source path**: Changed `source` from `"./skills/hecvat-assess"` to `"."` so the cached plugin directory includes `.claude-plugin/plugin.json`. Single-plugin repos must cache the entire repo for Claude Code to register the skill.

### Migration
- Users must uninstall and reinstall the plugin for the fix to take effect

## [2.0.0] - 2026-02-15

### Breaking Changes
- Assessment JSON schema now includes `fix_type`, `fix_complexity`, and `evidence_quality` fields on each answer object. Consumers of `assessment-current.json` from v1.x will encounter new fields.

### Added
- **Assessment enrichment** (Step 4): Each "No" answer now includes `fix_type` (code/config/new_file/documentation/policy/organizational), `fix_complexity` (small/medium/large), and `evidence_quality` (Strong/Moderate/Weak/Inferred)
- **Real patch generation** (Step 5): Edit-diff-revert cycle produces actual `git apply`-able patches instead of hand-written diffs. Includes safety checks, patch validation, and a separate `hecvat-remediation-manual.md` for non-patchable gaps
- **Task deduplication** (Step 6): Overlapping HECVAT questions (e.g., SSO/OIDC/SAML) collapse into single checklist tasks with `resolves_count` and `patchable` fields
- **Archive previous results**: Re-runs automatically archive prior `docs/hecvat/` results to `docs/hecvat/archive/YYYYMMDD-HHMM/` before writing new outputs
- `scripts/generate_summary.py` — Human-readable markdown summary with category breakdown, fix-type analysis, remediation priorities, confidence-adjusted scoring, comparison mode, and glossary
- `scripts/generate_delta.py` — Compare two assessments to show improvements (No→Yes), regressions (Yes→No), newly assessed questions, and per-category score changes
- Evidence quality scoring and confidence-adjusted scoring methodology in `references/scoring-rubric.md`
- Fix-type classification rules in `references/scoring-rubric.md`
- Patchable/non-patchable pattern structure in `references/scan-patterns.yaml`

### Changed
- SKILL.md workflow diagram updated to reflect new steps and outputs
- Step 7 now generates human-readable summary via `generate_summary.py`
- Output summary includes confidence-adjusted score, patch results, and fix-type breakdown
- Deliverables list expanded: `hecvat-remediation-manual.md`, `hecvat-summary.md`

## [1.0.0] - 2026-02-14

### Changed
- Restructured repository into Claude Code plugin format
- Moved skill files into `skills/hecvat-assess/` directory
- Added `.claude-plugin/plugin.json` manifest
- Updated installation instructions to use `/plugin marketplace add`

### Added
- Plugin manifest (`.claude-plugin/plugin.json`)
- Marketplace catalog (`.claude-plugin/marketplace.json`) for `/plugin marketplace add` discoverability
- This changelog

### Migration
- Skill files (SKILL.md, HECVAT414.xlsx, hecvat-questions.json) moved from root to `skills/hecvat-assess/`
- `scripts/` moved to `skills/hecvat-assess/scripts/`
- `references/` moved to `skills/hecvat-assess/references/`
- Test commands now use `pytest skills/hecvat-assess/scripts/tests/ -v`

# Changelog

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

# HECVAT Assessment Skill - Test Suite

Comprehensive test suite for the HECVAT assessment skill's Python scripts.

## Overview

This test suite validates:
- **parse_hecvat.py** - HECVAT xlsx to JSON parsing
- **generate_report.py** - Filling xlsx reports from assessment data

## Requirements

```bash
pip install pytest openpyxl
```

**Note**: openpyxl version 3.1.5 is already installed and working.

## Running Tests

From the repository root:

```bash
# Run all tests
pytest scripts/tests/

# Run with verbose output
pytest scripts/tests/ -v

# Run specific test file
pytest scripts/tests/test_parse_hecvat.py -v

# Run specific test class
pytest scripts/tests/test_parse_hecvat.py::TestParseHecvatSchema -v

# Run specific test
pytest scripts/tests/test_parse_hecvat.py::TestParseHecvatSchema::test_output_has_required_top_level_keys -v
```

## Test Coverage

### test_parse_hecvat.py (23 tests)

**Schema Validation (3 tests)**
- `test_output_has_required_top_level_keys` - Validates JSON structure
- `test_questions_array_structure` - Validates question object schema
- `test_output_file_is_valid_json` - Ensures parseable JSON output

**Data Integrity (4 tests)**
- `test_question_count_is_332` - Validates expected question count
- `test_no_duplicate_question_ids` - Prevents ID collisions
- `test_repo_assessable_plus_org_attestation_equals_total` - Math consistency
- `test_no_questions_have_none_or_empty_ids` - ID validity

**Business Logic (6 tests)**
- `test_category_matches_question_id_prefix` - Category derivation
- `test_aaai_questions_are_repo_assessable` - Auth questions classification
- `test_gnrl_questions_are_not_repo_assessable` - General info classification
- `test_comp_questions_are_not_repo_assessable` - Company info classification
- `test_docu_05_is_repo_assessable` - Special case handling
- `test_thrd_01_is_repo_assessable` - Dependency tracking classification

**Column Mapping (4 tests)**
- `test_score_mapping_field_populated` - Column extraction validation
- `test_score_location_field_populated` - Column extraction validation
- `test_question_text_is_not_empty` - Question text extraction
- `test_sheets_field_is_list` - Data type validation

**Output Behavior (4 tests)**
- `test_output_file_is_created` - File creation
- `test_idempotency_excluding_timestamp` - Deterministic parsing
- `test_categories_are_sorted` - Predictable output
- `test_version_field_is_4_1_4` - Version tracking

**Edge Cases (2 tests)**
- `test_source_file_is_basename_not_full_path` - Path sanitization
- `test_parsed_at_is_iso8601_utc` - Timestamp format

### test_generate_report.py (20 tests)

**File Creation (3 tests)**
- `test_output_file_is_created` - Basic file generation
- `test_output_file_is_valid_xlsx` - No corruption
- `test_template_sheets_are_preserved` - Sheet integrity

**Answer Filling (5 tests)**
- `test_answer_fills_column_c` - Answer placement
- `test_additional_info_fills_column_d` - Additional info placement
- `test_evidence_fills_column_d` - Evidence formatting
- `test_both_additional_info_and_evidence_combined` - Combined formatting
- `test_multiple_sheets_are_filled` - Multi-sheet handling

**Date Completion (2 tests)**
- `test_date_completed_is_filled` - Date field population
- `test_date_is_current_date` - Date accuracy

**Edge Cases (5 tests)**
- `test_empty_assessment_produces_valid_file` - Empty data handling
- `test_invalid_question_ids_are_skipped` - Unknown ID handling
- `test_missing_answer_field_handled_gracefully` - Malformed data
- `test_none_values_handled_gracefully` - Null value handling
- `test_all_response_sheets_are_processed` - Complete sheet coverage

**Sheet Coverage (3 tests)**
- `test_find_question_cells_returns_dict` - Helper function validation
- `test_at_least_one_question_filled_per_sheet` - Sheet processing
- Test helper function behavior

**Helper Function Tests (3 tests)**
- `test_identifies_valid_question_ids` - ID pattern matching
- `test_maps_to_correct_row_numbers` - Row mapping accuracy
- `test_handles_empty_worksheet` - Edge case handling

## Test Philosophy

Tests follow QA engineering best practices:

1. **Adversarial Mindset** - Tests try to break the code
2. **Realistic Data** - Uses actual HECVAT414.xlsx for integration tests
3. **Clear Documentation** - Each test has WHY comments explaining what it catches
4. **Fast Execution** - Uses tmp_path for isolation, runs in ~100 seconds
5. **Deterministic** - No flaky tests, no external dependencies beyond the xlsx

## What These Tests Catch

### Schema Changes
- Missing or renamed fields in JSON output
- Type mismatches (list vs dict, string vs int)
- Structural changes that would break downstream code

### Logic Bugs
- Off-by-one errors in row/column indexing
- Incorrect categorization of repo-assessable questions
- Math errors in counting/aggregation
- ID extraction failures

### Data Integrity Issues
- Duplicate question IDs
- Missing or empty required fields
- Inconsistent categorization
- Column misalignment after xlsx updates

### Edge Cases
- Empty assessments
- Invalid question IDs
- Missing data fields
- None/null values
- Malformed JSON

### Regression Prevention
- Question count changes (HECVAT version updates)
- Business rule changes (repo-assessability logic)
- Output format changes (breaking API consumers)

## Fixtures (conftest.py)

**hecvat_xlsx_path**
- Provides path to real HECVAT414.xlsx
- Used for integration tests with actual data

**sample_assessment_data**
- Realistic assessment JSON with various answer types
- Tests all answer/evidence/additional_info combinations

**empty_assessment_data**
- Assessment with no answers
- Tests handling of blank reports

**assessment_with_invalid_ids**
- Assessment with non-existent question IDs
- Tests error handling and graceful degradation

## Test Execution Time

Typical run time: ~100 seconds for 43 tests

- Most time spent loading/parsing xlsx files (openpyxl warnings are normal)
- Tests are isolated using pytest's tmp_path fixture
- No shared state between tests
- Can run in parallel with `pytest -n auto` if pytest-xdist is installed

## Maintenance

### When HECVAT is Updated

If HECVAT is updated to a new version:

1. Update `test_question_count_is_332` with new count
2. Update `test_version_field_is_4_1_4` with new version
3. Review repo-assessability rules if question categories change
4. Check that all tests still pass

### When Adding New Features

1. Add tests BEFORE implementing features (TDD)
2. Ensure new tests document WHY they exist
3. Keep tests isolated and deterministic
4. Update this README with new test descriptions

## Known Issues

- Openpyxl warnings about unsupported extensions are expected and harmless
  (Data Validation, Unknown extension, Conditional Formatting)
- Tests assume HECVAT414.xlsx exists at repo root
- Tests require Python 3.10+ and openpyxl 3.1+

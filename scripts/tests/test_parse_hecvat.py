"""Comprehensive test suite for parse_hecvat.py

Tests cover:
- Schema validation: Ensures output JSON has required structure
- Data integrity: Question counts, no duplicates, mathematical consistency
- Business logic: Repo-assessability classification, category mapping
- Edge cases: Column index changes, malformed data handling
- Integration: Real HECVAT414.xlsx parsing
- Idempotency: Repeated parsing produces consistent results
"""

import json
import sys
import os
from pathlib import Path
import pytest

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from parse_hecvat import parse_hecvat


class TestParseHecvatSchema:
    """Tests validating the output JSON schema structure.

    These tests catch breaking changes to the JSON output format that would
    break downstream consumers (like the assessment skill or report generator).
    """

    def test_output_has_required_top_level_keys(self, hecvat_xlsx_path, tmp_path):
        """Verify output JSON contains all required top-level keys.

        WHY: Downstream code expects these keys to exist. Missing keys would
        cause AttributeError or KeyError exceptions in consuming code.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        required_keys = {
            "source_file",
            "parsed_at",
            "version",
            "total_questions",
            "repo_assessable_count",
            "org_attestation_count",
            "categories",
            "questions"
        }

        assert set(result.keys()) == required_keys, \
            f"Missing or extra keys. Expected: {required_keys}, Got: {set(result.keys())}"

    def test_questions_array_structure(self, hecvat_xlsx_path, tmp_path):
        """Verify each question object has required fields.

        WHY: Catches schema changes where fields are renamed or removed.
        Missing fields would break code that accesses question attributes.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        required_question_keys = {
            "id", "category", "question", "sheets", "repo_assessable"
        }

        # Check first few questions (representative sample)
        for i, q in enumerate(result["questions"][:10]):
            missing_keys = required_question_keys - set(q.keys())
            assert not missing_keys, \
                f"Question {i} ({q.get('id', 'unknown')}) missing keys: {missing_keys}"

    def test_output_file_is_valid_json(self, hecvat_xlsx_path, tmp_path):
        """Verify output file can be loaded as valid JSON.

        WHY: Corrupted JSON would break all downstream processing. This test
        ensures the file is syntactically valid and can be loaded by json.load().
        """
        output_file = tmp_path / "test_output.json"
        parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        # Reload from file to verify it's valid JSON
        with open(output_file) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "questions" in data
        assert isinstance(data["questions"], list)


class TestParseHecvatDataIntegrity:
    """Tests validating data consistency and mathematical correctness.

    These tests catch logic errors in counting, filtering, or categorization
    that would produce incorrect statistics or inconsistent data.
    """

    def test_question_count_is_332(self, hecvat_xlsx_path, tmp_path):
        """Verify total question count matches expected 332 from HECVAT 4.1.4.

        WHY: Catches changes to the xlsx file (questions added/removed) or
        parsing logic that skips valid questions. If HECVAT is updated to a
        new version, this test documents the change.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        assert result["total_questions"] == 332, \
            f"Expected 332 questions, got {result['total_questions']}. " \
            f"Has HECVAT been updated or is parsing logic broken?"

    def test_no_duplicate_question_ids(self, hecvat_xlsx_path, tmp_path):
        """Verify each question ID appears exactly once.

        WHY: Duplicate IDs would break lookup logic and cause ambiguity when
        filling reports. This catches parsing bugs where rows are processed
        multiple times or ID extraction is incorrect.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        question_ids = [q["id"] for q in result["questions"]]
        unique_ids = set(question_ids)

        assert len(question_ids) == len(unique_ids), \
            f"Found {len(question_ids) - len(unique_ids)} duplicate IDs"

        # Find and report duplicates if any
        duplicates = [qid for qid in unique_ids if question_ids.count(qid) > 1]
        assert not duplicates, f"Duplicate question IDs found: {duplicates}"

    def test_repo_assessable_plus_org_attestation_equals_total(self, hecvat_xlsx_path, tmp_path):
        """Verify mathematical consistency: repo_assessable + org_attestation = total.

        WHY: This is a fundamental invariant. If this fails, the categorization
        logic is broken - questions are being double-counted or lost.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        repo_count = result["repo_assessable_count"]
        org_count = result["org_attestation_count"]
        total = result["total_questions"]

        assert repo_count + org_count == total, \
            f"Math error: {repo_count} repo + {org_count} org != {total} total"

    def test_no_questions_have_none_or_empty_ids(self, hecvat_xlsx_path, tmp_path):
        """Verify all questions have non-empty IDs.

        WHY: None or empty IDs would break lookup and matching logic in
        report generation. This catches parsing bugs where ID extraction fails.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        for q in result["questions"]:
            assert q["id"], f"Question has None or empty ID: {q}"
            assert isinstance(q["id"], str), f"Question ID is not a string: {q['id']}"
            assert "-" in q["id"], f"Question ID missing hyphen: {q['id']}"


class TestParseHecvatBusinessLogic:
    """Tests validating business rules and categorization logic.

    These tests ensure the repo-assessability classification and category
    mapping work correctly according to the documented rules.
    """

    def test_category_matches_question_id_prefix(self, hecvat_xlsx_path, tmp_path):
        """Verify each question's category matches its ID prefix.

        WHY: Category should always be derived from the ID prefix (e.g., AAAI-01
        has category AAAI). Mismatches indicate parsing or extraction bugs.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        for q in result["questions"]:
            prefix = q["id"].split("-")[0]
            assert q["category"] == prefix, \
                f"Question {q['id']} has category '{q['category']}' but prefix is '{prefix}'"

    def test_aaai_questions_are_repo_assessable(self, hecvat_xlsx_path, tmp_path):
        """Verify AAAI-* questions are marked repo_assessable=True.

        WHY: AAAI (Authentication, Authorization, Account Management) questions
        can typically be answered by analyzing code. This is a core business rule.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        aaai_questions = [q for q in result["questions"] if q["category"] == "AAAI"]
        assert len(aaai_questions) > 0, "No AAAI questions found"

        for q in aaai_questions:
            assert q["repo_assessable"], \
                f"Question {q['id']} should be repo_assessable but is marked False"

    def test_gnrl_questions_are_not_repo_assessable(self, hecvat_xlsx_path, tmp_path):
        """Verify GNRL-* questions are marked repo_assessable=False.

        WHY: GNRL (General Info) questions are organizational attestation
        (company name, contacts). These can't be answered from code.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        gnrl_questions = [q for q in result["questions"] if q["category"] == "GNRL"]
        assert len(gnrl_questions) > 0, "No GNRL questions found"

        for q in gnrl_questions:
            assert not q["repo_assessable"], \
                f"Question {q['id']} should NOT be repo_assessable but is marked True"

    def test_comp_questions_are_not_repo_assessable(self, hecvat_xlsx_path, tmp_path):
        """Verify COMP-* questions are marked repo_assessable=False.

        WHY: COMP (Company Info) questions are organizational attestation.
        Tests the NEVER_ASSESSABLE_PREFIXES logic.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        comp_questions = [q for q in result["questions"] if q["category"] == "COMP"]
        assert len(comp_questions) > 0, "No COMP questions found"

        for q in comp_questions:
            assert not q["repo_assessable"], \
                f"Question {q['id']} should NOT be repo_assessable but is marked True"

    def test_docu_05_is_repo_assessable(self, hecvat_xlsx_path, tmp_path):
        """Verify DOCU-05 is marked repo_assessable=True (special case).

        WHY: DOCU-05 (architecture diagrams) is a special case ID that's
        repo-assessable even though most DOCU questions aren't. Tests the
        REPO_ASSESSABLE_IDS exception list.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        docu_05 = next((q for q in result["questions"] if q["id"] == "DOCU-05"), None)
        assert docu_05 is not None, "DOCU-05 question not found"
        assert docu_05["repo_assessable"], \
            "DOCU-05 should be repo_assessable (special case for architecture docs)"

    def test_thrd_01_is_repo_assessable(self, hecvat_xlsx_path, tmp_path):
        """Verify THRD-01 is marked repo_assessable=True (special case).

        WHY: THRD-01 (third-party dependencies) can be answered from package
        manifests. Tests REPO_ASSESSABLE_IDS for dependency tracking questions.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        thrd_01 = next((q for q in result["questions"] if q["id"] == "THRD-01"), None)
        assert thrd_01 is not None, "THRD-01 question not found"
        assert thrd_01["repo_assessable"], \
            "THRD-01 should be repo_assessable (dependency manifests)"


class TestParseHecvatColumnMapping:
    """Tests validating that column data is extracted correctly.

    These tests catch bugs where column indices are off by one, or where
    columns are remapped in the xlsx file.
    """

    def test_score_mapping_field_populated(self, hecvat_xlsx_path, tmp_path):
        """Verify score_mapping field exists and contains valid data.

        WHY: If column indices change in the xlsx, this field would get data
        from the wrong column. This validates the field is being extracted.

        NOTE: Not all questions have score_mapping - many are None. This is
        expected. We verify that when present, values are valid (e.g., "NA").
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        # Verify score_mapping field exists on all questions
        for q in result["questions"]:
            assert "score_mapping" in q, \
                f"Question {q['id']} missing score_mapping field"

        # Check that some questions have non-None score_mapping
        with_score_mapping = [q for q in result["questions"]
                              if q.get("score_mapping") is not None]

        assert len(with_score_mapping) > 0, \
            "No questions have score_mapping data - column extraction may be broken"

        # Verify valid values when present
        for q in with_score_mapping:
            assert isinstance(q["score_mapping"], str), \
                f"Question {q['id']} has non-string score_mapping: {q['score_mapping']}"

    def test_score_location_field_populated(self, hecvat_xlsx_path, tmp_path):
        """Verify score_location field is extracted for questions.

        WHY: Same as score_mapping - validates column extraction is correct.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        with_score_location = [q for q in result["questions"] if q.get("score_location")]
        coverage = len(with_score_location) / len(result["questions"])

        assert coverage > 0.9, \
            f"Only {coverage:.0%} of questions have score_location. Column indices may be wrong."

    def test_question_text_is_not_empty(self, hecvat_xlsx_path, tmp_path):
        """Verify all questions have non-empty question text.

        WHY: Empty question text indicates column extraction failure or that
        we're reading the wrong column for question text.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        empty_questions = [q["id"] for q in result["questions"] if not q.get("question")]
        assert not empty_questions, \
            f"Questions with empty text: {empty_questions}. Column mapping may be wrong."

    def test_sheets_field_is_list(self, hecvat_xlsx_path, tmp_path):
        """Verify sheets field is a list for all questions.

        WHY: Downstream code expects sheets to be iterable. Type mismatches
        would cause runtime errors.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        for q in result["questions"]:
            assert isinstance(q["sheets"], list), \
                f"Question {q['id']} sheets field is not a list: {type(q['sheets'])}"


class TestParseHecvatOutputBehavior:
    """Tests validating file creation and idempotency.

    These tests ensure the parser behaves correctly as a CLI tool - creating
    output files, producing consistent results, etc.
    """

    def test_output_file_is_created(self, hecvat_xlsx_path, tmp_path):
        """Verify output JSON file is created on disk.

        WHY: If file creation fails silently, downstream processes would fail
        to find the expected output file.
        """
        output_file = tmp_path / "test_output.json"
        assert not output_file.exists(), "Output file already exists before test"

        parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        assert output_file.exists(), "Output file was not created"
        assert output_file.stat().st_size > 0, "Output file is empty"

    def test_idempotency_excluding_timestamp(self, hecvat_xlsx_path, tmp_path):
        """Verify repeated parsing produces identical results (except timestamp).

        WHY: Non-deterministic parsing would make it impossible to detect
        real changes vs. spurious diffs. This ensures parsing is stable.
        """
        output_file1 = tmp_path / "output1.json"
        output_file2 = tmp_path / "output2.json"

        result1 = parse_hecvat(str(hecvat_xlsx_path), str(output_file1))
        result2 = parse_hecvat(str(hecvat_xlsx_path), str(output_file2))

        # Remove timestamps for comparison
        result1_copy = dict(result1)
        result2_copy = dict(result2)
        result1_copy.pop("parsed_at")
        result2_copy.pop("parsed_at")

        assert result1_copy == result2_copy, \
            "Repeated parsing produced different results. Parsing is non-deterministic."

    def test_categories_are_sorted(self, hecvat_xlsx_path, tmp_path):
        """Verify categories array is sorted alphabetically.

        WHY: Sorted output makes diffs predictable and enables binary search.
        Unsorted output suggests a logic change or Python version difference.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        categories = result["categories"]
        sorted_categories = sorted(categories)

        assert categories == sorted_categories, \
            f"Categories are not sorted. Got: {categories}"

    def test_version_field_is_4_1_4(self, hecvat_xlsx_path, tmp_path):
        """Verify version field matches expected HECVAT version.

        WHY: Version mismatches would indicate we're parsing the wrong file
        or the version field isn't being set correctly.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        assert result["version"] == "4.1.4", \
            f"Version mismatch. Expected 4.1.4, got {result['version']}"


class TestParseHecvatEdgeCases:
    """Tests for edge cases and error handling.

    These tests ensure the parser handles unusual inputs gracefully.
    """

    def test_source_file_is_basename_not_full_path(self, hecvat_xlsx_path, tmp_path):
        """Verify source_file contains only the filename, not full path.

        WHY: Full paths in output would leak system information and make
        output non-portable between machines.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        assert result["source_file"] == "HECVAT414.xlsx", \
            f"source_file should be basename only, got: {result['source_file']}"
        assert "/" not in result["source_file"], \
            "source_file contains path separators"
        assert "\\" not in result["source_file"], \
            "source_file contains Windows path separators"

    def test_parsed_at_is_iso8601_utc(self, hecvat_xlsx_path, tmp_path):
        """Verify parsed_at timestamp is in ISO8601 UTC format.

        WHY: Standardized timestamps enable sorting and parsing across systems.
        Non-standard formats would break date parsing in downstream tools.
        """
        output_file = tmp_path / "test_output.json"
        result = parse_hecvat(str(hecvat_xlsx_path), str(output_file))

        timestamp = result["parsed_at"]
        assert timestamp.endswith("Z"), \
            "Timestamp should end with 'Z' (UTC indicator)"

        # Verify it can be parsed as ISO8601
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as e:
            pytest.fail(f"Timestamp is not valid ISO8601: {timestamp}. Error: {e}")

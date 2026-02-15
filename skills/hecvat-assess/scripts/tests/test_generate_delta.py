"""Comprehensive test suite for generate_delta.py

Tests cover:
- Identical assessments produce zero changes
- No->Yes improvements detected correctly
- Yes->No regressions detected correctly
- Newly assessed questions detected (blank->Yes or blank->No)
- Category score deltas computed correctly
- Output file creation when path provided
- Markdown output has correct sections and tables
- Empty assessments handled gracefully

NOTE: These tests use the real scoring-weights.yaml to validate weight loading.
"""

import json
import sys
import os
from pathlib import Path
import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_delta import generate_delta, load_weights

# Path constants — SKILL_ROOT points to skills/hecvat-assess/ (2 levels up from tests/)
SKILL_ROOT = Path(__file__).parent.parent.parent
WEIGHTS_YAML = SKILL_ROOT / "references" / "scoring-weights.yaml"


@pytest.fixture
def weights_yaml_path():
    """Absolute path to the real scoring-weights.yaml file.

    This fixture provides the actual weights file for integration tests.
    Tests can use this to validate weight loading against real data.
    """
    assert WEIGHTS_YAML.exists(), f"scoring-weights.yaml not found at {WEIGHTS_YAML}"
    return str(WEIGHTS_YAML)


@pytest.fixture
def before_assessment():
    """A baseline assessment with known answers for delta comparison.

    Contains a mix of Yes, No, and blank answers across several categories
    so we can test all transition types (improvement, regression, newly assessed).
    """
    return {
        "assessment_date": "2026-01-15",
        "branch": "main",
        "answers": {
            "AAAI-01": {"answer": "Yes", "additional_info": "MFA enabled"},
            "AAAI-02": {"answer": "No", "additional_info": "Password-only auth"},
            "AAAI-03": {"answer": "No", "additional_info": ""},
            "APPL-01": {"answer": "Yes", "additional_info": "Input validation"},
            "APPL-02": {"answer": "Yes", "additional_info": "XSS protection"},
            "DATA-01": {"answer": "No", "additional_info": "Unencrypted at rest"},
            "DATA-02": {"answer": "No", "additional_info": ""},
            "COMP-01": {"answer": "Yes", "additional_info": "50 employees"},
        }
    }


@pytest.fixture
def after_assessment():
    """A later assessment with known changes relative to before_assessment.

    Changes from before:
    - AAAI-01: Yes -> Yes (unchanged)
    - AAAI-02: No -> Yes (improvement)
    - AAAI-03: No -> No (unchanged)
    - APPL-01: Yes -> No (regression)
    - APPL-02: Yes -> Yes (unchanged)
    - DATA-01: No -> Yes (improvement)
    - DATA-02: No -> No (unchanged)
    - COMP-01: Yes -> Yes (unchanged)
    - VULN-01: (new) -> Yes (newly assessed)
    - VULN-02: (new) -> No (newly assessed)
    """
    return {
        "assessment_date": "2026-02-15",
        "branch": "feature/security-hardening",
        "answers": {
            "AAAI-01": {"answer": "Yes", "additional_info": "MFA enabled"},
            "AAAI-02": {"answer": "Yes", "additional_info": "Added MFA support"},
            "AAAI-03": {"answer": "No", "additional_info": ""},
            "APPL-01": {"answer": "No", "additional_info": "Removed validation layer"},
            "APPL-02": {"answer": "Yes", "additional_info": "XSS protection"},
            "DATA-01": {"answer": "Yes", "additional_info": "AES-256 encryption added"},
            "DATA-02": {"answer": "No", "additional_info": ""},
            "COMP-01": {"answer": "Yes", "additional_info": "50 employees"},
            "VULN-01": {"answer": "Yes", "additional_info": "Automated scanning"},
            "VULN-02": {"answer": "No", "additional_info": "Manual process only"},
        }
    }


@pytest.fixture
def identical_assessment():
    """An assessment identical to before_assessment for zero-delta testing.

    WHY: Using the same data ensures the comparison logic correctly identifies
    that nothing changed, rather than false-positive detecting changes.
    """
    return {
        "assessment_date": "2026-01-15",
        "branch": "main",
        "answers": {
            "AAAI-01": {"answer": "Yes", "additional_info": "MFA enabled"},
            "AAAI-02": {"answer": "No", "additional_info": "Password-only auth"},
            "AAAI-03": {"answer": "No", "additional_info": ""},
            "APPL-01": {"answer": "Yes", "additional_info": "Input validation"},
            "APPL-02": {"answer": "Yes", "additional_info": "XSS protection"},
            "DATA-01": {"answer": "No", "additional_info": "Unencrypted at rest"},
            "DATA-02": {"answer": "No", "additional_info": ""},
            "COMP-01": {"answer": "Yes", "additional_info": "50 employees"},
        }
    }


@pytest.fixture
def empty_assessment():
    """An assessment with no answers.

    Tests that delta generation handles empty assessments gracefully
    without crashing or producing incorrect output.
    """
    return {
        "assessment_date": "2026-01-01",
        "branch": "empty",
        "answers": {}
    }


def _write_assessment(tmp_path, filename, data):
    """Helper to write assessment JSON to a temp file and return its path."""
    path = tmp_path / filename
    with open(path, "w") as f:
        json.dump(data, f)
    return str(path)


class TestLoadWeights:
    """Tests validating that scoring weights are loaded correctly.

    Weight loading is critical for category score deltas. Both the PyYAML
    path and the manual fallback parser must produce correct results.
    """

    def test_loads_weights_from_real_file(self, weights_yaml_path):
        """Verify weights load from the actual scoring-weights.yaml.

        WHY: If weight loading fails, all category score deltas would be
        wrong or missing. This validates against the real file.
        """
        weights = load_weights(weights_yaml_path)

        assert isinstance(weights, dict)
        assert len(weights) > 0, "No weights loaded"

    def test_known_weight_values(self, weights_yaml_path):
        """Verify specific known weights match expected values.

        WHY: Spot-checking known values catches parsing bugs that produce
        the wrong numbers even when the structure looks correct.
        """
        weights = load_weights(weights_yaml_path)

        assert weights.get("AAAI") == 10, "AAAI should have weight 10"
        assert weights.get("APPL") == 9, "APPL should have weight 9"
        assert weights.get("GNRL") == 0, "GNRL should have weight 0"
        assert weights.get("ITAC") == 3, "ITAC should have weight 3"

    def test_all_categories_have_integer_weights(self, weights_yaml_path):
        """Verify every loaded weight is an integer.

        WHY: Non-integer weights would cause floating-point issues in
        score calculations and unexpected formatting in reports.
        """
        weights = load_weights(weights_yaml_path)

        for cat, weight in weights.items():
            assert isinstance(weight, int), \
                f"Category {cat} has non-integer weight: {weight} ({type(weight)})"


class TestIdenticalAssessments:
    """Tests confirming identical assessments produce zero-delta output.

    This is the baseline correctness check: if nothing changed, the report
    should show zero improvements, regressions, and newly assessed items.
    """

    def test_no_improvements_when_identical(self, before_assessment, identical_assessment, weights_yaml_path, tmp_path):
        """Verify zero improvements when both assessments are the same.

        WHY: False-positive improvements would mislead stakeholders into
        thinking progress was made when nothing changed.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", identical_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "Improvements (No -> Yes): **0**" in content
        assert "Regressions (Yes -> No): **0**" in content
        assert "Newly assessed: **0**" in content

    def test_no_category_deltas_when_identical(self, before_assessment, identical_assessment, weights_yaml_path, tmp_path):
        """Verify no category score delta rows when assessments are identical.

        WHY: If category deltas show non-zero values for identical data,
        the score calculation is broken.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", identical_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        # The Category Score Deltas table should exist but have no data rows
        # (only categories with non-zero delta get rows)
        if "## Category Score Deltas" in content:
            # Find the table section and check it has no data rows with +/- deltas
            lines = content.split("\n")
            in_delta_section = False
            data_rows = []
            for line in lines:
                if "## Category Score Deltas" in line:
                    in_delta_section = True
                    continue
                if in_delta_section and line.startswith("## "):
                    break
                if in_delta_section and line.startswith("| ") and "Category" not in line and "---" not in line:
                    data_rows.append(line)

            assert len(data_rows) == 0, \
                f"Expected no delta rows for identical assessments, got: {data_rows}"


class TestImprovements:
    """Tests validating detection of No->Yes improvements.

    Improvements are the most important metric for tracking security posture
    progress over time.
    """

    def test_improvements_detected(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify No->Yes transitions are counted as improvements.

        WHY: Missing improvements would undercount progress and mislead
        stakeholders about the security posture trend.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        # AAAI-02 (No->Yes) and DATA-01 (No->Yes) = 2 improvements
        assert "Improvements (No -> Yes): **2**" in content

    def test_improvement_questions_listed_in_table(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify improved question IDs appear in the improvements table.

        WHY: The table provides actionable detail. Missing question IDs
        would prevent reviewers from understanding what specifically improved.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "AAAI-02" in content, "AAAI-02 improvement should be listed"
        assert "DATA-01" in content, "DATA-01 improvement should be listed"

    def test_improvement_detail_includes_after_info(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify improvement table shows additional_info from the after assessment.

        WHY: The detail column helps reviewers understand what was done to
        achieve the improvement, providing context for the change.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "Added MFA support" in content, \
            "AAAI-02 detail from after assessment should appear"
        assert "AES-256 encryption added" in content, \
            "DATA-01 detail from after assessment should appear"


class TestRegressions:
    """Tests validating detection of Yes->No regressions.

    Regressions are critical to flag because they indicate security posture
    degradation that may need immediate attention.
    """

    def test_regressions_detected(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify Yes->No transitions are counted as regressions.

        WHY: Missed regressions could hide security posture degradation,
        leaving vulnerabilities unaddressed.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        # APPL-01 (Yes->No) = 1 regression
        assert "Regressions (Yes -> No): **1**" in content

    def test_regression_questions_listed_in_table(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify regressed question IDs appear in the regressions table.

        WHY: Identifying the specific regression lets teams prioritize
        remediation efforts on the right questions.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "APPL-01" in content, "APPL-01 regression should be listed"


class TestNewlyAssessed:
    """Tests validating detection of newly assessed questions.

    Newly assessed questions track coverage expansion — going from blank
    to Yes or No means a question was evaluated for the first time.
    """

    def test_newly_assessed_detected(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify blank->Yes and blank->No transitions are counted.

        WHY: Tracking newly assessed questions shows assessment coverage
        growth, which is important for compliance completeness.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        # VULN-01 (new->Yes) and VULN-02 (new->No) = 2 newly assessed
        assert "Newly assessed: **2**" in content

    def test_newly_assessed_questions_listed_with_answer(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify newly assessed table includes both question ID and answer.

        WHY: Knowing whether a new question was answered Yes or No is
        critical — a newly assessed No still needs remediation.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "VULN-01" in content, "VULN-01 should be listed as newly assessed"
        assert "VULN-02" in content, "VULN-02 should be listed as newly assessed"

    def test_na_to_answer_counts_as_newly_assessed(self, weights_yaml_path, tmp_path):
        """Verify N/A->Yes or N/A->No transitions count as newly assessed.

        WHY: N/A answers are treated as unanswered. When they become Yes or
        No, the question was effectively assessed for the first time.
        """
        before = {
            "assessment_date": "2026-01-01", "branch": "main",
            "answers": {
                "AAAI-01": {"answer": "N/A", "additional_info": ""},
            }
        }
        after = {
            "assessment_date": "2026-02-01", "branch": "main",
            "answers": {
                "AAAI-01": {"answer": "Yes", "additional_info": "Now applicable"},
            }
        }
        before_path = _write_assessment(tmp_path, "before.json", before)
        after_path = _write_assessment(tmp_path, "after.json", after)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "Newly assessed: **1**" in content


class TestCategoryScoreDeltas:
    """Tests validating category-level score delta computation.

    Category deltas show the percentage-point change per category, helping
    teams understand which areas improved or degraded most.
    """

    def test_category_deltas_computed(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify category score deltas appear in the report.

        WHY: Category-level deltas provide the strategic view of where
        security posture is improving or degrading.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "## Category Score Deltas" in content

    def test_aaai_category_delta_correct(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify AAAI category delta is calculated correctly.

        Before: AAAI-01=Yes, AAAI-02=No, AAAI-03=No -> 1/3 = 33.3%
        After:  AAAI-01=Yes, AAAI-02=Yes, AAAI-03=No -> 2/3 = 66.7%
        Delta: +33.3%

        WHY: Verifying a specific calculation catches math errors in the
        percentage computation logic.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        # Find the AAAI row specifically in the Category Score Deltas section
        lines = content.split("\n")
        in_delta_section = False
        aaai_row = None
        for line in lines:
            if "## Category Score Deltas" in line:
                in_delta_section = True
                continue
            if in_delta_section and line.startswith("## "):
                break
            if in_delta_section and line.startswith("| AAAI "):
                aaai_row = line
                break

        assert aaai_row is not None, "AAAI should appear in category deltas"
        assert "1/3" in aaai_row, f"Before should show 1/3, got: {aaai_row}"
        assert "2/3" in aaai_row, f"After should show 2/3, got: {aaai_row}"
        assert "+33.3%" in aaai_row or "+33.4%" in aaai_row, \
            f"Delta should be ~+33.3%, got: {aaai_row}"

    def test_appl_category_delta_correct(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify APPL category delta shows regression.

        Before: APPL-01=Yes, APPL-02=Yes -> 2/2 = 100%
        After:  APPL-01=No, APPL-02=Yes  -> 1/2 = 50%
        Delta: -50.0%

        WHY: Regression deltas must be negative to correctly flag degradation.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        # Find the APPL row specifically in the Category Score Deltas section
        lines = content.split("\n")
        in_delta_section = False
        appl_row = None
        for line in lines:
            if "## Category Score Deltas" in line:
                in_delta_section = True
                continue
            if in_delta_section and line.startswith("## "):
                break
            if in_delta_section and line.startswith("| APPL "):
                appl_row = line
                break

        assert appl_row is not None, "APPL should appear in category deltas"
        assert "-50.0%" in appl_row, f"Delta should be -50.0%, got: {appl_row}"

    def test_unchanged_category_not_in_delta_table(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify categories with zero delta are excluded from the table.

        COMP has Yes->Yes (unchanged), so its delta is 0 and should not
        appear as a row.

        WHY: Zero-delta rows add noise. Only categories with actual changes
        should appear, making the report actionable.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        lines = content.split("\n")
        for line in lines:
            if line.startswith("| COMP"):
                pytest.fail(f"COMP should not appear in delta table (zero delta), but found: {line}")


class TestOutputFileCreation:
    """Tests validating output file creation and stdout behavior.

    The generate_delta function should write to a file when given a path,
    or print to stdout when no path is given.
    """

    def test_output_file_created(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify output markdown file is created at the specified path.

        WHY: If file creation fails, downstream workflows that depend on
        the delta report file would break.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        assert not os.path.exists(output_path), "Output file should not exist yet"

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        assert os.path.exists(output_path), "Output file was not created"
        assert os.path.getsize(output_path) > 0, "Output file is empty"

    def test_output_file_in_nested_directory(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify output file creation works with nested directories.

        WHY: The function uses os.makedirs to create parent directories.
        This tests that nested paths work correctly.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "reports" / "delta" / "output.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        assert os.path.exists(output_path), "Output file was not created in nested dir"

    def test_stdout_when_no_output_path(self, before_assessment, after_assessment, weights_yaml_path, tmp_path, capsys):
        """Verify report is printed to stdout when no output path given.

        WHY: Stdout output is useful for piping into other tools or for
        quick visual inspection without creating files.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)

        generate_delta(before_path, after_path, weights_yaml_path)

        captured = capsys.readouterr()
        assert "# HECVAT Assessment Delta Report" in captured.out
        assert "## Summary" in captured.out


class TestMarkdownOutput:
    """Tests validating the markdown output structure and formatting.

    Correct markdown structure is important because the report may be rendered
    in GitHub, documentation systems, or other markdown viewers.
    """

    def test_report_has_title(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify report starts with the expected H1 title.

        WHY: The title identifies the document type. Missing titles make
        reports harder to identify in a collection of documents.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert content.startswith("# HECVAT Assessment Delta Report")

    def test_report_includes_metadata(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify report includes before/after assessment metadata.

        WHY: Metadata (dates, branches) provides context for the comparison
        and helps reviewers understand what changed and when.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "2026-01-15" in content, "Before date should appear"
        assert "2026-02-15" in content, "After date should appear"
        assert "main" in content, "Before branch should appear"
        assert "feature/security-hardening" in content, "After branch should appear"

    def test_report_has_summary_section(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify report has a Summary section with all expected counters.

        WHY: The summary gives a quick overview. Missing counters would
        force reviewers to manually count rows in tables.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "## Summary" in content
        assert "Improvements (No -> Yes):" in content
        assert "Regressions (Yes -> No):" in content
        assert "Newly assessed:" in content
        assert "Unchanged Yes:" in content
        assert "Unchanged No:" in content

    def test_improvements_table_has_correct_headers(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify improvements table has the expected column headers.

        WHY: Table headers define the data structure. Wrong headers would
        misalign data and confuse readers.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "| Question | Category | Detail |" in content

    def test_newly_assessed_table_has_correct_headers(self, before_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify newly assessed table has the expected column headers.

        WHY: The newly assessed table has a different structure (includes
        Answer column). Verifying headers catches column layout errors.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "| Question | Answer | Category |" in content


class TestEmptyAssessments:
    """Tests for edge cases with empty or minimal assessments.

    These tests ensure the generator handles unusual inputs gracefully
    without crashing or producing misleading output.
    """

    def test_both_empty_assessments(self, empty_assessment, weights_yaml_path, tmp_path):
        """Verify comparing two empty assessments does not crash.

        WHY: Empty assessments can occur at the start of a new project
        before any questions have been evaluated.
        """
        before_path = _write_assessment(tmp_path, "before.json", empty_assessment)
        after_path = _write_assessment(tmp_path, "after.json", empty_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "Improvements (No -> Yes): **0**" in content
        assert "Regressions (Yes -> No): **0**" in content
        assert "Newly assessed: **0**" in content

    def test_empty_before_all_new_after(self, empty_assessment, after_assessment, weights_yaml_path, tmp_path):
        """Verify all questions in after are counted as newly assessed when before is empty.

        WHY: First assessment after an empty baseline means everything is new.
        All Yes/No answers should be treated as newly assessed.
        """
        before_path = _write_assessment(tmp_path, "before.json", empty_assessment)
        after_path = _write_assessment(tmp_path, "after.json", after_assessment)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        # All 10 questions in after_assessment have Yes or No answers,
        # and none exist in the empty before -> all newly assessed
        assert "Improvements (No -> Yes): **0**" in content
        assert "Regressions (Yes -> No): **0**" in content
        # All 10 answers should be newly assessed
        assert "Newly assessed: **10**" in content

    def test_all_answers_removed(self, before_assessment, empty_assessment, weights_yaml_path, tmp_path):
        """Verify report handles case where all answers are removed.

        WHY: Removing all answers (answered -> empty) is an edge case that
        should not crash. Questions that go from Yes/No to missing should
        not produce false improvements or regressions.
        """
        before_path = _write_assessment(tmp_path, "before.json", before_assessment)
        after_path = _write_assessment(tmp_path, "after.json", empty_assessment)
        output_path = str(tmp_path / "delta.md")

        # Should not raise exception
        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        assert os.path.exists(output_path), "Output file should still be created"

    def test_missing_metadata_uses_fallback(self, weights_yaml_path, tmp_path):
        """Verify report uses '?' fallback when metadata fields are missing.

        WHY: Assessments may lack metadata fields. The report should still
        generate, using placeholder values instead of crashing.
        """
        before = {"answers": {}}
        after = {"answers": {}}
        before_path = _write_assessment(tmp_path, "before.json", before)
        after_path = _write_assessment(tmp_path, "after.json", after)
        output_path = str(tmp_path / "delta.md")

        generate_delta(before_path, after_path, weights_yaml_path, output_path)

        with open(output_path) as f:
            content = f.read()

        assert "**Before**: ? on `?`" in content
        assert "**After**: ? on `?`" in content

"""Comprehensive test suite for generate_summary.py

Tests cover:
- Weight loading from scoring-weights.yaml (fallback parser, no PyYAML needed)
- Category statistics computation from assessment JSON
- Raw and weighted score computation
- Summary markdown generation (headings, tables, glossary)
- Comparison/delta mode between two assessments
- Confidence-adjusted score computation
- Empty and edge-case assessment handling
"""

import json
import sys
import os
from pathlib import Path
import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_summary import (
    load_weights,
    load_category_names,
    analyze_assessment,
    compute_scores,
    compute_confidence_adjusted_score,
    generate_summary,
)

# Path to the real scoring-weights.yaml
SKILL_ROOT = Path(__file__).parent.parent.parent
WEIGHTS_YAML = SKILL_ROOT / "references" / "scoring-weights.yaml"


@pytest.fixture
def weights_yaml_path():
    """Absolute path to the real scoring-weights.yaml file.

    Uses the actual weights file so tests validate against real category
    definitions rather than synthetic data that could drift out of sync.
    """
    assert WEIGHTS_YAML.exists(), f"scoring-weights.yaml not found at {WEIGHTS_YAML}"
    return str(WEIGHTS_YAML)


@pytest.fixture
def minimal_assessment():
    """Minimal assessment with a few Yes/No answers across two weighted categories.

    Provides a controlled, predictable dataset for verifying score math.
    AAAI: 2 Yes, 1 No  -> 66.7% raw in category (weight 10)
    APPL: 1 Yes, 0 No  -> 100% raw in category (weight 9)
    GNRL: 1 blank       -> weight 0, should be excluded from scoring
    """
    return {
        "repository": "test/repo",
        "assessment_date": "2026-02-15",
        "hecvat_version": "4.1.4",
        "branch": "main",
        "answers": {
            "AAAI-01": {"answer": "Yes"},
            "AAAI-02": {"answer": "Yes"},
            "AAAI-03": {"answer": "No", "fix_type": "code"},
            "APPL-01": {"answer": "Yes"},
            "GNRL-01": {"answer": "Test Vendor"},
        },
    }


@pytest.fixture
def assessment_with_evidence_quality():
    """Assessment with evidence_quality fields for confidence-adjusted scoring.

    Tests that Strong/Moderate/Weak/Inferred quality levels correctly
    discount the confidence-adjusted score relative to the raw score.
    """
    return {
        "repository": "test/repo",
        "assessment_date": "2026-02-15",
        "branch": "main",
        "answers": {
            "AAAI-01": {"answer": "Yes", "evidence_quality": "Strong"},
            "AAAI-02": {"answer": "Yes", "evidence_quality": "Moderate"},
            "AAAI-03": {"answer": "Yes", "evidence_quality": "Weak"},
            "AAAI-04": {"answer": "No", "evidence_quality": "Strong"},
        },
    }


@pytest.fixture
def comparison_before_assessment():
    """'Before' assessment for delta comparison tests.

    Has lower compliance than the 'after' assessment so we can verify
    positive deltas in the comparison table.
    """
    return {
        "repository": "test/repo",
        "assessment_date": "2026-02-01",
        "branch": "main",
        "answers": {
            "AAAI-01": {"answer": "Yes"},
            "AAAI-02": {"answer": "No", "fix_type": "code"},
            "AAAI-03": {"answer": "No", "fix_type": "config"},
            "APPL-01": {"answer": "No", "fix_type": "code"},
        },
    }


@pytest.fixture
def comparison_after_assessment():
    """'After' assessment for delta comparison tests.

    Fixes some gaps from the 'before' assessment to show improvement.
    """
    return {
        "repository": "test/repo",
        "assessment_date": "2026-02-15",
        "branch": "main",
        "answers": {
            "AAAI-01": {"answer": "Yes"},
            "AAAI-02": {"answer": "Yes"},
            "AAAI-03": {"answer": "No", "fix_type": "config"},
            "APPL-01": {"answer": "Yes"},
        },
    }


@pytest.fixture
def empty_assessment():
    """Assessment with no answers at all.

    Tests that the summary generator handles the zero-division edge case
    and produces valid output rather than crashing.
    """
    return {
        "repository": "test/repo",
        "assessment_date": "2026-02-15",
        "branch": "main",
        "answers": {},
    }


class TestLoadWeights:
    """Tests for loading category weights from scoring-weights.yaml.

    The fallback parser (no PyYAML) must correctly extract weight integers
    for each uppercase category key. These tests use the real weights file.
    """

    def test_loads_known_categories(self, weights_yaml_path):
        """Verify high-priority categories are present with expected weights.

        WHY: If the parser misses categories, scoring will silently drop them
        from the weighted calculation, producing incorrect scores.
        """
        weights = load_weights(weights_yaml_path)

        assert "AAAI" in weights, "AAAI category missing from weights"
        assert "APPL" in weights, "APPL category missing from weights"
        assert "DATA" in weights, "DATA category missing from weights"
        assert "VULN" in weights, "VULN category missing from weights"

    def test_weight_values_are_integers(self, weights_yaml_path):
        """Verify all weights are integers (not strings or floats).

        WHY: String weights would cause type errors in arithmetic. Float
        weights would indicate a parsing bug since all weights are whole numbers.
        """
        weights = load_weights(weights_yaml_path)

        for cat, w in weights.items():
            assert isinstance(w, int), f"{cat} weight should be int, got {type(w)}: {w}"

    def test_weights_in_valid_range(self, weights_yaml_path):
        """Verify weights are between 0 and 10 inclusive.

        WHY: The weight scale is documented as 1-10 (plus 0 for org-only).
        Values outside this range indicate a parsing error.
        """
        weights = load_weights(weights_yaml_path)

        for cat, w in weights.items():
            assert 0 <= w <= 10, f"{cat} weight {w} out of range [0, 10]"

    def test_org_attestation_categories_have_zero_weight(self, weights_yaml_path):
        """Verify org-attestation-only categories are weighted zero.

        WHY: GNRL, COMP, and similar categories are not scored from code.
        Non-zero weights would inflate scores with non-assessable questions.
        """
        weights = load_weights(weights_yaml_path)

        for cat in ["GNRL", "COMP", "REQU"]:
            assert weights.get(cat) == 0, f"{cat} should have weight 0, got {weights.get(cat)}"

    def test_security_critical_categories_have_high_weight(self, weights_yaml_path):
        """Verify security-critical categories have weight >= 8.

        WHY: AAAI (auth), APPL (app sec), DATA (data sec) are documented as
        weight 8-10. Lower weights would under-prioritize critical gaps.
        """
        weights = load_weights(weights_yaml_path)

        assert weights["AAAI"] >= 8, f"AAAI weight too low: {weights['AAAI']}"
        assert weights["APPL"] >= 8, f"APPL weight too low: {weights['APPL']}"
        assert weights["DATA"] >= 8, f"DATA weight too low: {weights['DATA']}"


class TestLoadCategoryNames:
    """Tests for loading category display names from scoring-weights.yaml."""

    def test_loads_names_for_weighted_categories(self, weights_yaml_path):
        """Verify display names are loaded for key categories.

        WHY: Missing names would show raw category codes in the summary table,
        making the report less readable for non-technical reviewers.
        """
        names = load_category_names(weights_yaml_path)

        assert "AAAI" in names, "AAAI name missing"
        assert "Authentication" in names["AAAI"], \
            f"AAAI name should mention Authentication, got: {names['AAAI']}"

    def test_names_are_non_empty_strings(self, weights_yaml_path):
        """Verify all names are non-empty strings.

        WHY: Empty names would produce blank cells in the summary table.
        """
        names = load_category_names(weights_yaml_path)

        for cat, name in names.items():
            assert isinstance(name, str), f"{cat} name should be str, got {type(name)}"
            assert len(name) > 0, f"{cat} has empty name"


class TestAnalyzeAssessment:
    """Tests for category statistics computation from assessment JSON.

    analyze_assessment() tallies Yes/No/N-A/blank counts per category and
    collects gap IDs. These tallies drive all downstream scoring.
    """

    def test_counts_yes_answers(self, minimal_assessment):
        """Verify Yes answers are tallied correctly per category.

        WHY: Yes count is the numerator of the compliance ratio. Miscounting
        would directly produce wrong scores.
        """
        stats = analyze_assessment(minimal_assessment)

        assert stats["AAAI"]["yes"] == 2, f"AAAI yes count wrong: {stats['AAAI']['yes']}"
        assert stats["APPL"]["yes"] == 1, f"APPL yes count wrong: {stats['APPL']['yes']}"

    def test_counts_no_answers(self, minimal_assessment):
        """Verify No answers are tallied and gap IDs collected.

        WHY: No count is used for gap identification and score denominator.
        Missing gaps would hide remediation priorities.
        """
        stats = analyze_assessment(minimal_assessment)

        assert stats["AAAI"]["no"] == 1, f"AAAI no count wrong: {stats['AAAI']['no']}"
        assert "AAAI-03" in stats["AAAI"]["gaps"], "AAAI-03 should be in gaps list"

    def test_blank_answers_categorized(self, minimal_assessment):
        """Verify non-Yes/No/NA answers are counted as blank.

        WHY: Blank answers represent org-attestation questions that cannot be
        scored from code. They must be excluded from the assessed count.
        """
        stats = analyze_assessment(minimal_assessment)

        # GNRL-01 has answer "Test Vendor" which is not Yes/No/NA -> blank
        assert stats["GNRL"]["blank"] == 1, f"GNRL blank count wrong: {stats['GNRL']['blank']}"

    def test_fix_types_tracked(self, minimal_assessment):
        """Verify fix_type field is tracked for No answers.

        WHY: Fix types drive the 'Gaps by Fix Type' section, helping users
        understand what kind of remediation work is needed.
        """
        stats = analyze_assessment(minimal_assessment)

        assert stats["AAAI"]["fix_types"]["code"] == 1, \
            f"AAAI code fix_type count wrong: {stats['AAAI']['fix_types']}"

    def test_na_answers_counted(self):
        """Verify N/A answers are counted separately from blank.

        WHY: N/A means 'not applicable' and should not count toward the
        assessed total. Confusing N/A with blank would skew org attestation counts.
        """
        assessment = {
            "answers": {
                "AAAI-01": {"answer": "N/A"},
                "AAAI-02": {"answer": "NA"},
            }
        }
        stats = analyze_assessment(assessment)

        assert stats["AAAI"]["na"] == 2, f"AAAI N/A count wrong: {stats['AAAI']['na']}"
        assert stats["AAAI"]["yes"] == 0
        assert stats["AAAI"]["no"] == 0


class TestComputeScores:
    """Tests for raw and weighted score computation.

    These tests verify the scoring math with controlled inputs where
    expected results can be calculated by hand.
    """

    def test_raw_score_calculation(self, minimal_assessment, weights_yaml_path):
        """Verify raw score is (total yes) / (total yes + no) * 100.

        WHY: Raw score is the headline metric. Wrong math would misrepresent
        the overall compliance posture.

        Expected: 3 Yes (AAAI-01, AAAI-02, APPL-01) out of 4 assessed
        (GNRL-01 is blank, not Yes/No) = 75.0%
        """
        weights = load_weights(weights_yaml_path)
        stats = analyze_assessment(minimal_assessment)
        scores = compute_scores(stats, weights)

        assert scores["raw_yes"] == 3, f"raw_yes wrong: {scores['raw_yes']}"
        assert scores["raw_assessed"] == 4, f"raw_assessed wrong: {scores['raw_assessed']}"
        assert scores["raw_pct"] == 75.0, f"raw_pct wrong: {scores['raw_pct']}"

    def test_weighted_score_calculation(self, minimal_assessment, weights_yaml_path):
        """Verify weighted score accounts for category weights.

        WHY: Weighted score ensures high-impact categories (auth, app sec)
        count more than low-impact ones. Wrong weighting would mis-prioritize.

        AAAI: 2/3 * 10 = 6.667
        APPL: 1/1 * 9 = 9.0
        GNRL: weight 0, excluded
        Weighted = (6.667 + 9.0) / (10 + 9) * 100 = 82.5% (rounded to 1 decimal)
        """
        weights = load_weights(weights_yaml_path)
        stats = analyze_assessment(minimal_assessment)
        scores = compute_scores(stats, weights)

        # AAAI weight=10, 2/3 compliance; APPL weight=9, 1/1 compliance
        # weighted_num = (2/3)*10 + (1/1)*9 = 6.667 + 9 = 15.667
        # weighted_den = 10 + 9 = 19
        # weighted_score = 15.667/19 * 100 = 82.5 (rounded)
        assert scores["weighted_score"] == 82.5, \
            f"weighted_score wrong: {scores['weighted_score']}, expected 82.5"

    def test_zero_weight_categories_excluded_from_weighted(self, weights_yaml_path):
        """Verify categories with weight=0 do not affect weighted score.

        WHY: Org-attestation categories (GNRL, COMP) have weight 0 and must
        not influence the weighted score denominator.
        """
        weights = load_weights(weights_yaml_path)
        # Assessment with only GNRL answers (weight 0)
        stats = {"GNRL": {"yes": 5, "no": 0, "na": 0, "blank": 0, "gaps": [], "fix_types": {}}}
        scores = compute_scores(stats, weights)

        assert scores["weighted_score"] == 0, \
            f"Zero-weight-only categories should produce 0 weighted score, got {scores['weighted_score']}"

    def test_empty_stats_produce_zero_scores(self, weights_yaml_path):
        """Verify empty statistics produce zero scores without division errors.

        WHY: Empty assessment (no answers) must not crash with ZeroDivisionError.
        """
        weights = load_weights(weights_yaml_path)
        scores = compute_scores({}, weights)

        assert scores["raw_pct"] == 0
        assert scores["weighted_score"] == 0
        assert scores["raw_assessed"] == 0


class TestComputeConfidenceAdjustedScore:
    """Tests for confidence-adjusted scoring using evidence_quality fields.

    Confidence-adjusted score discounts Yes answers based on evidence strength:
    Strong=1.0, Moderate=0.75, Weak=0.5, Inferred=0.25.
    """

    def test_returns_sentinel_when_no_evidence_quality(self, weights_yaml_path):
        """Verify returns -1 when no answers have evidence_quality.

        WHY: The sentinel value tells the summary generator to skip the
        confidence-adjusted row rather than showing misleading data.
        """
        weights = load_weights(weights_yaml_path)
        assessment = {
            "answers": {
                "AAAI-01": {"answer": "Yes"},
                "AAAI-02": {"answer": "No"},
            }
        }
        score = compute_confidence_adjusted_score(assessment, weights)

        assert score == -1, f"Expected -1 sentinel, got {score}"

    def test_strong_evidence_gets_full_credit(self, weights_yaml_path):
        """Verify Strong evidence_quality gives 1.0 credit per Yes answer.

        WHY: Strong evidence means high confidence -- should not discount.
        """
        weights = load_weights(weights_yaml_path)
        assessment = {
            "answers": {
                "AAAI-01": {"answer": "Yes", "evidence_quality": "Strong"},
                "AAAI-02": {"answer": "Yes", "evidence_quality": "Strong"},
            }
        }
        score = compute_confidence_adjusted_score(assessment, weights)

        assert score == 100.0, f"All-Strong should be 100, got {score}"

    def test_mixed_quality_discounts_score(self, assessment_with_evidence_quality, weights_yaml_path):
        """Verify mixed evidence quality produces score lower than raw.

        WHY: Weak/Moderate evidence should reduce confidence-adjusted score
        below the raw score. This tests the discounting math.

        4 assessed: Strong Yes (1.0) + Moderate Yes (0.75) + Weak Yes (0.5) + Strong No (0)
        total_quality = 1.0 + 0.75 + 0.5 + 0 = 2.25
        score = 2.25 / 4 * 100 = 56.2
        """
        weights = load_weights(weights_yaml_path)
        score = compute_confidence_adjusted_score(assessment_with_evidence_quality, weights)

        assert score == 56.2, f"Mixed quality score wrong: {score}, expected 56.2"

    def test_returns_sentinel_for_empty_assessment(self, weights_yaml_path):
        """Verify empty assessment returns sentinel -1.

        WHY: No assessed questions means no denominator for the calculation.
        """
        weights = load_weights(weights_yaml_path)
        score = compute_confidence_adjusted_score({"answers": {}}, weights)

        assert score == -1, f"Empty assessment should return -1, got {score}"


class TestGenerateSummaryOutput:
    """Tests for the full summary markdown generation.

    These tests verify the generated markdown contains all expected sections,
    proper formatting, and correct data.
    """

    def test_output_contains_required_headings(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify all required markdown headings are present.

        WHY: Missing sections would make the report incomplete. Reviewers
        expect a standard structure.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "# HECVAT Assessment Summary" in content, "Missing main heading"
        assert "## Overall Scores" in content, "Missing Overall Scores section"
        assert "## Category Breakdown" in content, "Missing Category Breakdown section"
        assert "## Top Remediation Priorities" in content, "Missing Remediation Priorities section"
        assert "## Glossary" in content, "Missing Glossary section"

    def test_output_contains_markdown_tables(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify markdown tables are properly formatted with pipe separators.

        WHY: Malformed tables would not render correctly in markdown viewers.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        # Check for table header separators (---|---)
        assert "|--------|" in content, "Missing table separator row"
        # Check for table data rows with pipe separators
        assert "| Raw compliance |" in content, "Missing Raw compliance row"
        assert "| Weighted score |" in content, "Missing Weighted score row"

    def test_glossary_contains_key_terms(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify glossary includes essential terms for non-technical readers.

        WHY: The glossary makes the report self-contained. Missing definitions
        would force readers to look up terms elsewhere.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "HECVAT" in content, "Glossary missing HECVAT definition"
        assert "EDUCAUSE" in content, "Glossary missing EDUCAUSE definition"
        assert "MFA" in content, "Glossary missing MFA definition"
        assert "WCAG" in content, "Glossary missing WCAG definition"
        assert "SOC 2" in content, "Glossary missing SOC 2 definition"

    def test_output_file_is_created(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify output file is created at the specified path.

        WHY: Basic file creation is the most fundamental requirement. If this
        fails, no downstream processing can occur.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        assert output_file.exists(), "Output file was not created"
        assert output_file.stat().st_size > 0, "Output file is empty"

    def test_category_breakdown_shows_weighted_categories(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify category breakdown table includes assessed weighted categories.

        WHY: The breakdown table is the primary detail view. Missing categories
        would hide important compliance data from reviewers.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        # AAAI and APPL should appear in the category breakdown
        assert "| AAAI |" in content, "AAAI missing from category breakdown"
        assert "| APPL |" in content, "APPL missing from category breakdown"

    def test_gaps_by_fix_type_present_when_gaps_exist(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify fix type breakdown appears when there are No answers.

        WHY: Fix types help users plan remediation work. The section should
        only appear when there are actual gaps to report.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "## Gaps by Fix Type" in content, "Missing Gaps by Fix Type section"
        assert "| code |" in content, "Missing code fix type row"
        assert "Total patchable" in content, "Missing patchable total"

    def test_metadata_in_header(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify repository and date metadata appear in the header.

        WHY: Metadata identifies which assessment this report covers. Missing
        metadata would make the report ambiguous.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "test/repo" in content, "Repository name missing from header"
        assert "2026-02-15" in content, "Assessment date missing from header"


class TestComparisonMode:
    """Tests for delta comparison between two assessments.

    Comparison mode shows what changed between a 'before' and 'after'
    assessment, helping users track improvement over time.
    """

    def test_comparison_includes_delta_table(
        self, comparison_before_assessment, comparison_after_assessment, weights_yaml_path, tmp_path
    ):
        """Verify comparison mode produces a delta table with Before/After/Delta columns.

        WHY: The delta table is the primary output of comparison mode. Without it,
        users cannot see what improved.
        """
        before_file = tmp_path / "before.json"
        after_file = tmp_path / "after.json"
        output_file = tmp_path / "summary.md"

        with open(before_file, "w") as f:
            json.dump(comparison_before_assessment, f)
        with open(after_file, "w") as f:
            json.dump(comparison_after_assessment, f)

        generate_summary(str(after_file), weights_yaml_path, str(output_file), compare_path=str(before_file))

        content = output_file.read_text()

        assert "### Comparison" in content, "Missing Comparison heading"
        assert "| Before |" in content or "Before" in content, "Missing Before column"
        assert "| After |" in content or "After" in content, "Missing After column"
        assert "| Delta |" in content or "Delta" in content, "Missing Delta column"

    def test_comparison_shows_positive_delta(
        self, comparison_before_assessment, comparison_after_assessment, weights_yaml_path, tmp_path
    ):
        """Verify improvement is shown as positive delta.

        WHY: After fixing gaps, the delta should be positive (improvement).
        A negative delta when things improved would confuse users.

        Before: 1 Yes / 4 assessed = 25.0%
        After:  3 Yes / 4 assessed = 75.0%
        Delta: +50.0%
        """
        before_file = tmp_path / "before.json"
        after_file = tmp_path / "after.json"
        output_file = tmp_path / "summary.md"

        with open(before_file, "w") as f:
            json.dump(comparison_before_assessment, f)
        with open(after_file, "w") as f:
            json.dump(comparison_after_assessment, f)

        generate_summary(str(after_file), weights_yaml_path, str(output_file), compare_path=str(before_file))

        content = output_file.read_text()

        assert "+50.0%" in content, \
            f"Expected +50.0% delta in comparison. Content:\n{content}"

    def test_no_comparison_section_without_compare_flag(self, minimal_assessment, weights_yaml_path, tmp_path):
        """Verify comparison section is absent when no compare path is given.

        WHY: Showing an empty or broken comparison table when not requested
        would be confusing.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "### Comparison" not in content, \
            "Comparison section should not appear without --compare"


class TestEmptyAssessment:
    """Tests for edge cases with empty or minimal assessment data.

    These tests ensure the generator handles degenerate inputs gracefully
    without crashing or producing invalid output.
    """

    def test_empty_assessment_produces_valid_markdown(self, empty_assessment, weights_yaml_path, tmp_path):
        """Verify empty assessment generates valid markdown without errors.

        WHY: An assessment with no answers should produce a valid (if sparse)
        report, not crash with ZeroDivisionError or KeyError.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(empty_assessment, f)

        # Should not raise any exception
        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "# HECVAT Assessment Summary" in content, "Missing main heading"
        assert "## Glossary" in content, "Missing glossary even for empty assessment"

    def test_empty_assessment_shows_zero_scores(self, empty_assessment, weights_yaml_path, tmp_path):
        """Verify empty assessment shows 0/0 (0%) scores.

        WHY: Zero scores are the correct representation of 'no data assessed'.
        Any non-zero score would be misleading.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(empty_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "0/0" in content, "Empty assessment should show 0/0"
        assert "0.0%" in content or "0%" in content, "Empty assessment should show 0%"

    def test_empty_assessment_no_fix_type_section(self, empty_assessment, weights_yaml_path, tmp_path):
        """Verify Gaps by Fix Type section is absent when no gaps exist.

        WHY: An empty fix type table would be confusing and add noise.
        """
        assessment_file = tmp_path / "assessment.json"
        output_file = tmp_path / "summary.md"

        with open(assessment_file, "w") as f:
            json.dump(empty_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path, str(output_file))

        content = output_file.read_text()

        assert "## Gaps by Fix Type" not in content, \
            "Gaps by Fix Type should not appear for empty assessment"

    def test_analyze_empty_returns_empty_dict(self):
        """Verify analyze_assessment returns empty dict for no answers.

        WHY: Downstream code iterates over the stats dict. An empty dict
        is the correct base case -- not None or an exception.
        """
        stats = analyze_assessment({"answers": {}})

        assert stats == {}, f"Expected empty dict, got {stats}"

    def test_stdout_output_when_no_output_path(self, minimal_assessment, weights_yaml_path, tmp_path, capsys):
        """Verify summary prints to stdout when no output path is given.

        WHY: stdout mode is the default for quick terminal use. If it fails,
        users cannot preview summaries without creating files.
        """
        assessment_file = tmp_path / "assessment.json"

        with open(assessment_file, "w") as f:
            json.dump(minimal_assessment, f)

        generate_summary(str(assessment_file), weights_yaml_path)

        captured = capsys.readouterr()

        assert "# HECVAT Assessment Summary" in captured.out, "Summary not printed to stdout"
        assert "Score:" in captured.out, "Score line not printed to stdout"
